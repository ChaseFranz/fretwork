"""
RUN - drive the published page in headless Chrome and read the results out of the DOM.

Stages a copy of a published bundle into a temporary directory, injects one
suite module after the page's single module tag, serves the copy with
http.server on a free 127.0.0.1 port, launches one Chrome process per suite
with --dump-dom, and parses the <pre id="results"> block the suite appends.
Every expectation in a suite is read from the page's own boot payload, so the
same suites run against the 47-row fixture in CI and the real library here.

    python tests/page/run.py --site /tmp/fw-ci/site/Fixture
    python tests/page/run.py --site site/Local --suite launch.js
    python tests/page/run.py --site site/Local --keep         # leave the staged copy behind

Chrome: $CHROME, then google-chrome / chromium / chromium-browser on PATH, then
the Windows binary under /mnt/c (WSL). No CDP and no driver: Chrome's debugging
port is unreachable from WSL, and the DOM readback needs neither.
"""

import argparse
import contextlib
import html
import json
import os
import pathlib
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))   # the repo root, for `import config`

import config      # noqa: E402
import deploy      # noqa: E402

# One module tag, whatever it is called: static/js/main.js today, static/app.<hash8>.js after section 05.
ANCHOR = re.compile(r'<script type="module" src="static/[^"]+\.js"></script>')
ISLAND = re.compile(r'<script type="application/json" id="fw-boot">(.*?)</script>', re.S)
RESULTS = re.compile(r'<pre id="results">(.*?)</pre>', re.S)
BAD = ("FAIL", "ERROR", "MISSING")
WSL_CHROME = "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe"
HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]


def roundtrip_query(plain):
    """A query string that shows at least one row and fewer than all: composed from the payload."""
    data = json.loads(ISLAND.search(plain.read_text(encoding="utf-8")).group(1))["data"]
    sheet = list(data)[1]
    cols, rows = data[sheet]["columns"], data[sheet]["rows"]     # section 05: read data/<slug>.<hash>.json instead
    row = next(r for r in rows if r[cols.index("Level")] == "Hard")
    word = str(row[cols.index("Song Title")]).split()[0].lower()
    return "?" + urllib.parse.urlencode({"sheet": sheet, "q": word, "sort": "NoteCount",
                                         "dir": "asc", "f.Level": "Hard"}) + "&r.Pct=90:"


# Optional keys: queries (strings or callables taking plain.html; one launch each),
# windows (one launch per size), window, page (a page of its own, not injected),
# needs_bootstrap, storage (seeded into localStorage before the modules run),
# delay ({url-prefix: ms} the server waits before answering a matching request).
SUITES = [
    ("test.js",      {}),
    ("order.js",     {}),
    ("keys.js",      {}),
    ("launch.js",    {}),
    ("roundtrip.js", {"queries": [roundtrip_query]}),
    ("fade.js",      {"windows": ["700,900", "1000,900", "1440,900"]}),
    ("video.js",     {}),
    ("links.js",     {}),
    ("about.js",     {}),
    ("notfound.js",  {}),
    ("contrast.js",  {"needs_bootstrap": True}),
    ("narrow.js",    {"needs_bootstrap": True}),                # the 390px measurement, inside an iframe
]


def find_chrome(explicit):
    for candidate in ([explicit] if explicit else []) + [os.environ.get("CHROME")]:
        if candidate and (shutil.which(candidate) or os.path.isfile(candidate)):
            return shutil.which(candidate) or candidate
    for name in ("google-chrome", "chromium", "chromium-browser"):
        if shutil.which(name):
            return shutil.which(name)
    if os.path.isfile(WSL_CHROME):
        return WSL_CHROME
    sys.exit("no Chrome found: set CHROME or pass --chrome")


# A classic script runs during parsing, before any deferred module, so main.js
# always reads a clean localStorage; `seeds` is the manifest's optional storage dict.
def storage_script(seeds):
    sets = "".join(f"localStorage.setItem({json.dumps(k)},{json.dumps(v)});" for k, v in (seeds or {}).items())
    return "<script>try{localStorage.clear();" + sets + "}catch(e){}</script>\n"


def stage(site, work, suites):
    src = (site / "index.html").read_text(encoding="utf-8")
    found = ANCHOR.findall(src)
    assert len(found) == 1, f"module tag found {len(found)} times, expected once"
    anchor = found[0]
    assert src.count("<script") == 2, "index.html should hold the island and one module tag"
    assert not any(name in src for name, _ in suites), "index.html is not pristine"
    for name in sorted(deploy.BUNDLE_TOP - {"index.html", "static", "data", "graph"}):   # every entry page
        if (site / name).is_file():
            shutil.copy(site / name, work / name)
    if (site / "bootstrap.css").is_file():                                            # until 05 moves it under static/
        shutil.copy(site / "bootstrap.css", work / "bootstrap.css")
    shutil.copytree(site / "static", work / "static")
    (work / "graph").mkdir()
    shutil.copy(site / "graph" / "manifest.json", work / "graph" / "manifest.json")
    for png in sorted((site / "graph").glob("*.png"))[:40]:
        shutil.copy(png, work / "graph" / png.name)
    (work / "src").mkdir()
    shutil.copy(REPO / "web" / "static" / "js" / "dom.js", work / "src" / "dom.js")   # links.js tests rich()
    (work / "plain.html").write_text(src.replace(anchor, storage_script(None) + anchor), encoding="utf-8")
    shutil.copy(HERE / "lib.js", work / "lib.js")
    for name, opts in suites:
        shutil.copy(HERE / name, work / name)
        if opts.get("page"):
            continue
        page = src.replace(anchor, storage_script(opts.get("storage")) + anchor +
                           '\n<script type="module" src="' + name + '"></script>')
        (work / suite_page(name)).write_text(page, encoding="utf-8")
    return 'href="bootstrap.css"' in src           # False means FALLBACK_CSS is inlined


# Injected pages are named apart from the bundle's own files: a suite called
# about.js must not stage over about.html.
def suite_page(name):
    return "suite-" + pathlib.Path(name).stem + ".html"


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# The server is a subprocess the runner owns and terminates; delay is applied by
# a tiny handler subclass so a suite can watch a file arrive late.
SERVER = r'''
import http.server, sys, time, json
delay = json.loads(sys.argv[3])
class H(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        for prefix, ms in delay.items():
            if self.path.lstrip("/").startswith(prefix):
                time.sleep(ms / 1000)
        super().do_GET()
    def log_message(self, *a): pass
http.server.ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1])), lambda *a, **k: H(*a, directory=sys.argv[2], **k)).serve_forever()
'''


@contextlib.contextmanager
def served(work, delay=None):
    port = free_port()
    proc = subprocess.Popen([sys.executable, "-c", SERVER, str(port), str(work), json.dumps(delay or {})],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):                  # up to 5 s for the socket to open
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/plain.html", timeout=1).read(1)
                break
            except (urllib.error.URLError, ConnectionError, TimeoutError):
                time.sleep(0.1)
        else:
            raise RuntimeError("http.server did not come up")
        yield f"http://127.0.0.1:{port}"
    finally:
        proc.terminate()
        proc.wait(timeout=10)


# A profile directory Chrome can use: a WSL path for a Linux binary, a Windows
# path for chrome.exe (asked of cmd.exe), or none, with a note, if there is no cmd.exe.
def make_profile(chrome):
    if not chrome.endswith(".exe"):
        d = tempfile.mkdtemp(prefix="fretwork-chrome-")
        return d, d
    if not shutil.which("cmd.exe"):
        print("note: no cmd.exe on PATH, running chrome.exe on its default profile")
        return None, None
    win_tmp = subprocess.run(["cmd.exe", "/c", "echo %TEMP%"], capture_output=True, text=True).stdout.strip()
    wsl_tmp = subprocess.run(["wslpath", "-u", win_tmp], capture_output=True, text=True).stdout.strip()
    local = tempfile.mkdtemp(prefix="fretwork-chrome-", dir=wsl_tmp)
    return subprocess.run(["wslpath", "-w", local], capture_output=True, text=True).stdout.strip(), local


def run_suite(chrome, url, budget, window, profile):
    cmd = [chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
           f"--virtual-time-budget={budget}", f"--window-size={window}"]
    if profile:
        cmd.append(f"--user-data-dir={profile}")
    dom = subprocess.run(cmd + ["--dump-dom", url], capture_output=True, text=True,
                         timeout=180).stdout
    found = RESULTS.search(dom)
    if not found:
        return ["NO RESULTS"]
    return html.unescape(found.group(1)).splitlines()


def report(name, lines):
    bad = [l for l in lines if l.startswith(BAD) or l == "NO RESULTS"]
    checks = sum(1 for l in lines if l.startswith(("PASS", "ok")))
    skipped = sum(1 for l in lines if l.startswith("SKIP"))
    if not bad and not checks:               # a block that never got written must not read as green
        bad = ["NO CHECKS  " + (lines[0] if lines else "(empty block)")]
    if bad:
        print(f"{name}\n  " + "\n  ".join(bad))
    else:
        print(f"{name}  {checks} checks, all pass" + (f", {skipped} skipped" if skipped else ""))
    return not bad


def parse_args():
    ap = argparse.ArgumentParser(description="Run the page suites against a published bundle in headless Chrome.")
    ap.add_argument("--site", help="published bundle (default site/<header>)")
    ap.add_argument("--header", default=None)
    ap.add_argument("--suite", action="append", help="run only this suite (repeatable)")
    ap.add_argument("--chrome", help="Chrome binary (default: $CHROME, PATH, then the Windows binary)")
    ap.add_argument("--budget", type=int, default=30000, help="--virtual-time-budget in ms")
    ap.add_argument("--keep", action="store_true", help="leave the staged copy behind and print its path")
    ap.add_argument("--allow-fallback", action="store_true", help="run against a --no-bootstrap bundle")
    ap.add_argument("--verbose", action="store_true", help="print every result line")
    return ap.parse_args()


def main():
    args = parse_args()
    site = pathlib.Path(args.site or pathlib.Path(config.SITE_DIR) / (args.header or config.HEADER))
    chrome = find_chrome(args.chrome)
    suites = [s for s in SUITES if not args.suite or s[0] in args.suite]
    missing = [n for n, _ in suites if not (HERE / n).is_file()]
    if missing:
        sys.exit(f"no such suite file(s): {missing}")
    work = pathlib.Path(tempfile.mkdtemp(prefix="fretwork-page-"))
    profile, profile_local = make_profile(chrome)
    failed = 0
    try:
        has_bootstrap = stage(site, work, suites)
        if not has_bootstrap and not args.allow_fallback:
            sys.exit(f"{site} was published with --no-bootstrap; pass --allow-fallback to skip "
                     "the suites that measure Bootstrap")
        delay = {}
        for _, opts in suites:
            delay.update(opts.get("delay", {}))
        with served(work, delay) as base:
            for name, opts in suites:
                if opts.get("needs_bootstrap") and not has_bootstrap:
                    print(f"{name}  SKIP  fallback CSS")
                    continue
                page = name if opts.get("page") else suite_page(name)
                queries = [q(work / "plain.html") if callable(q) else q for q in opts.get("queries", [""])]
                windows = opts.get("windows", [opts.get("window", "1440,900")])
                for query in queries:
                    for window in windows:
                        lines = run_suite(chrome, f"{base}/{page}{query}", args.budget, window, profile)
                        label = name + (f" @{window}" if len(windows) > 1 else "") + (f" {query}" if len(queries) > 1 else "")
                        if args.verbose:
                            print("\n".join("    " + l for l in lines))
                        failed += 0 if report(label, lines) else 1
    finally:
        if args.keep:
            print(f"staged copy kept at {work}")
        else:
            shutil.rmtree(work, ignore_errors=True)
        if profile_local:
            shutil.rmtree(profile_local, ignore_errors=True)
    print(f"\n{len(suites)} suites, {failed} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
