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
    file = json.loads((plain.parent / data[sheet]["file"]).read_text(encoding="utf-8"))   # the rows live in data/
    cols, rows = file["columns"], file["rows"]
    row = next(r for r in rows if r[cols.index("Level")] == "Hard")
    word = str(row[cols.index("Song Title")]).split()[0].lower()
    return "?" + urllib.parse.urlencode({"sheet": sheet, "q": word, "sort": "NoteCount",
                                         "dir": "asc", "f.Level": "Hard"}) + "&r.Pct=90:"


def _second_sheet_code(plain):
    data = json.loads(ISLAND.search(plain.read_text(encoding="utf-8")).group(1))["data"]
    sheet = list(data)[1]
    file = json.loads((plain.parent / data[sheet]["file"]).read_text(encoding="utf-8"))
    return sheet, file["rows"][0][file["columns"].index("Code")]


# every code on a sheet, in the sheet's own order
def _sheet_codes(plain, sheet):
    data = json.loads(ISLAND.search(plain.read_text(encoding="utf-8")).group(1))["data"]
    file = json.loads((plain.parent / data[sheet]["file"]).read_text(encoding="utf-8"))
    at = file["columns"].index("Code")
    return [r[at] for r in file["rows"]]


# All levels named, so the opening chips (Official, Expert) do not narrow the view.
ALL_LEVELS = "&f.Level=Expert,Hard,Medium,Easy"


def album_query(plain):
    """A search for the fixture's comma album, on the sheet that holds it."""
    data = json.loads(ISLAND.search(plain.read_text(encoding="utf-8")).group(1))["data"]
    for sheet in data:
        file = json.loads((plain.parent / data[sheet]["file"]).read_text(encoding="utf-8"))
        i = file["columns"].index("Album")
        row = next((r for r in file["rows"] if "," in str(r[i])), None)
        if row:
            return "?" + urllib.parse.urlencode({"sheet": sheet, "q": row[i]}) + ALL_LEVELS
    raise SystemExit("no album with a comma in the fixture")


def compare_query(plain):
    """?code=<an Expert code>&vs=<the same song's Hard, else the second row>, from the first sheet."""
    data = json.loads(ISLAND.search(plain.read_text(encoding="utf-8")).group(1))["data"]
    sheet = list(data)[0]
    file = json.loads((plain.parent / data[sheet]["file"]).read_text(encoding="utf-8"))
    cols, rows = file["columns"], file["rows"]
    at = lambda n: cols.index(n)   # noqa: E731
    for r in rows:
        if r[at("Level")] != "Expert":
            continue
        # the same folder and the same part: the suite expects the legend to name the levels alone
        hard = next((h for h in rows if h[at("Level")] == "Hard" and str(h[at("Code")])[:8] == str(r[at("Code")])[:8]
                     and h[at("Type")] == r[at("Type")]), None)
        if hard:
            return "?" + urllib.parse.urlencode({"code": r[at("Code")], "vs": hard[at("Code")]})
    return "?" + urllib.parse.urlencode({"code": rows[0][at("Code")], "vs": rows[1][at("Code")]})


def song_query(plain):
    """?song=<the first SongKey in the first sheet>&code=<that row's Code>."""
    data = json.loads(ISLAND.search(plain.read_text(encoding="utf-8")).group(1))["data"]
    sheet = list(data)[0]
    file = json.loads((plain.parent / data[sheet]["file"]).read_text(encoding="utf-8"))
    cols, row = file["columns"], file["rows"][0]
    return "?" + urllib.parse.urlencode({"song": row[cols.index("SongKey")], "code": row[cols.index("Code")]})


def song_stale_query(plain):
    """?song=<the first SongKey>&code=00000000XG: a code no row has beside a live key (section 16)."""
    return song_only_query(plain) + "&code=00000000XG"


def song_only_query(plain):
    """?song=<the first SongKey in the first sheet> alone: the page resolves it to a code (section 14)."""
    data = json.loads(ISLAND.search(plain.read_text(encoding="utf-8")).group(1))["data"]
    sheet = list(data)[0]
    file = json.loads((plain.parent / data[sheet]["file"]).read_text(encoding="utf-8"))
    return "?" + urllib.parse.urlencode({"song": file["rows"][0][file["columns"].index("SongKey")]})


def carry_query(plain):
    """Two levels, the first sheet's first Part (which the second sheet lacks), a range, a sort and a search, for sheets.js."""
    data = json.loads(ISLAND.search(plain.read_text(encoding="utf-8")).group(1))["data"]
    first, second = list(data)[:2]
    parts = {}
    for sheet in (first, second):
        file = json.loads((plain.parent / data[sheet]["file"]).read_text(encoding="utf-8"))
        parts[sheet] = [r[file["columns"].index("Type")] for r in file["rows"]]
    part = parts[first][0]
    if part in parts[second]:
        raise SystemExit(f"{part!r} is on both {first} and {second}; sheets.js needs a Part the second sheet lacks")
    return "?" + urllib.parse.urlencode({"f.Level": "Hard,Medium", "f.Type": part, "sort": "NoteCount", "q": "a"}) + "&r.NoteCount=1:"


def deep_code_query(plain):
    """?code=<the official Expert chart with the lowest D on the first sheet>: the last row of the opening view (section 17)."""
    data = json.loads(ISLAND.search(plain.read_text(encoding="utf-8")).group(1))["data"]
    sheet = list(data)[0]
    file = json.loads((plain.parent / data[sheet]["file"]).read_text(encoding="utf-8"))
    cols, rows = file["columns"], file["rows"]
    at = lambda n: cols.index(n)   # noqa: E731
    pool = [r for r in rows if r[at("Level")] == "Expert" and r[at("Official")] is True and isinstance(r[at("D")], (int, float))]
    lowest = min(pool, key=lambda r: r[at("D")])
    return "?" + urllib.parse.urlencode({"code": lowest[at("Code")]})


def genre_query(plain):
    """A search for a genre that no searched column on the first sheet contains."""
    data = json.loads(ISLAND.search(plain.read_text(encoding="utf-8")).group(1))["data"]
    sheet = list(data)[0]
    file = json.loads((plain.parent / data[sheet]["file"]).read_text(encoding="utf-8"))
    cols, rows = file["columns"], file["rows"]
    searched = [cols.index(c) for c in ("Song Title", "Artist", "Album", "Charter", "Release", "Code")]
    for genre in sorted({str(r[cols.index("Genre")]) for r in rows if r[cols.index("Genre")]}, key=len, reverse=True):
        if not any(genre.lower() in str(r[i]).lower() for r in rows for i in searched):
            return "?" + urllib.parse.urlencode({"sheet": sheet, "q": genre}) + ALL_LEVELS
    raise SystemExit("every genre on the first sheet is also in a searched column")


def bass_code_query(plain):
    return "?code=" + _second_sheet_code(plain)[1]


def bass_code_query_with_sheet(plain):
    sheet, code = _second_sheet_code(plain)
    return "?" + urllib.parse.urlencode({"sheet": sheet, "code": code})


# the fragment form a document page links (section 24): ./#code=X, and a comparison, ./#code=X&vs=Y
def bass_code_fragment(plain):
    return "#code=" + _second_sheet_code(plain)[1]


def bass_code_fragment_with_vs(plain):
    sheet, code = _second_sheet_code(plain)
    codes = _sheet_codes(plain, sheet)
    other = next((c for c in codes if c != code), code)
    return "#code=" + code + "&vs=" + other


# Optional keys: queries (strings or callables taking plain.html; one launch each),
# windows (one launch per size), window, page (a page of its own, not injected),
# needs_bootstrap, storage (seeded into localStorage before the modules run),
# delay ({url-prefix: ms} the server waits before answering a matching request).
SUITES = [
    ("test.js",      {}),
    ("order.js",     {}),
    ("keys.js",      {}),
    ("launch.js",    {}),
    ("fragment.js",  {"queries": [bass_code_fragment, bass_code_fragment_with_vs]}),
    ("roundtrip.js", {"queries": [roundtrip_query], "storage": {"fw.hidden": '["Artist"]'}}),   # a stale saved hidden set, no fw.v
    ("load.js",      {"queries": [bass_code_query, bass_code_query_with_sheet, ""], "delay": {"data/": 2000}}),   # long enough for a slow CI runner to evaluate the suite first
    ("fields.js",    {"queries": ["", "?r.Difficulty=:3", "?r.Year=2000:2010", album_query, genre_query]}),
    ("copies.js",    {"queries": ["", "?f.Copies=2" + ALL_LEVELS]}),
    ("sheets.js",    {"queries": [carry_query]}),
    ("window.js",    {"queries": ["", deep_code_query]}),
    ("graph.js",     {"queries": ["", "?sheet=Drums", "?sheet=Vocals", "?code=00000000XD"]}),
    ("compare.js",   {"queries": [compare_query]}),
    ("song.js",      {}),
    ("song_url.js",  {"queries": [song_query, song_only_query, song_stale_query, "?song=000000000000"]}),
    ("share.js",     {"queries": [compare_query]}),
    ("pane.js",      {}),
    ("theme.js",     {"storage": {"fw.theme": "light"}}),      # opens light whatever the OS prefers
    ("fade.js",      {"windows": ["700,900", "1000,900", "1440,900"]}),
    ("video.js",     {}),
    ("links.js",     {"delay": {"data/links.": 800}}),
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


def seeded(src, storage):
    assert src.count("<head>") == 1
    return src.replace("<head>", "<head>\n" + storage_script(storage), 1)


def stage(site, work, suites):
    src = (site / "index.html").read_text(encoding="utf-8")
    found = ANCHOR.findall(src)
    assert len(found) == 1, f"module tag found {len(found)} times, expected once"
    anchor = found[0]
    assert src.count("<script") == 5, "index.html should hold the theme script, the WebSite block, the island, one module tag and the guide's closer"
    assert not any(name in src for name, _ in suites), "index.html is not pristine"
    for name in sorted(deploy.BUNDLE_TOP - {"index.html", "static", "data", "graph"}):   # every entry page
        if (site / name).is_file():
            shutil.copy(site / name, work / name)
    if (site / "bootstrap.css").is_file():                                            # until 05 moves it under static/
        shutil.copy(site / "bootstrap.css", work / "bootstrap.css")
    shutil.copytree(site / "static", work / "static")
    if (site / "data").is_dir():
        shutil.copytree(site / "data", work / "data")
    # every graph file: the curve JSON the page draws from (about 4 KB each, 48 MB
    # for the Local library) and the one PNG, the social preview
    shutil.copytree(site / "graph", work / "graph")
    for folder in ("song", "game", "list"):                                            # the pages per song, per pack, the lists (16, 22)
        if (site / folder).is_dir():
            shutil.copytree(site / folder, work / folder)
    (work / "src").mkdir()
    shutil.copy(REPO / "web" / "static" / "js" / "dom.js", work / "src" / "dom.js")   # links.js tests rich()
    # the storage script goes at the top of the head: it must run before the
    # theme script reads fw.theme, so a seeded theme is the one the page opens in
    (work / "plain.html").write_text(seeded(src, None), encoding="utf-8")
    shutil.copy(HERE / "lib.js", work / "lib.js")
    for name, opts in suites:
        shutil.copy(HERE / name, work / name)
        if opts.get("page"):
            continue
        page = seeded(src, opts.get("storage")).replace(anchor, anchor + '\n<script type="module" src="' + name + '"></script>')
        (work / suite_page(name)).write_text(page, encoding="utf-8")
    return 'static/bootstrap.' in src              # False means FALLBACK_CSS is inlined


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


# A dump without the results block is Chrome finishing before the suite ran
# (its first launch on a fresh profile now and then dumps the page before the
# module scripts have run; a suite that ran always writes the block, through
# done() or the error handlers), so it is retried once before it counts.
def run_suite(chrome, url, budget, window, profile, tries=2):
    cmd = [chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
           f"--virtual-time-budget={budget}", f"--window-size={window}"]
    if profile:
        cmd.append(f"--user-data-dir={profile}")
    for attempt in range(tries):
        dom = subprocess.run(cmd + ["--dump-dom", url], capture_output=True, text=True,
                             timeout=180).stdout
        found = RESULTS.search(dom)
        if found:
            return html.unescape(found.group(1)).splitlines()
    return ["NO RESULTS"]


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
    ap.add_argument("--budget", type=int, default=60000, help="--virtual-time-budget in ms")
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
