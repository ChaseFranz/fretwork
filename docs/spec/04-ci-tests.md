# 04. Tests and CI

**Status:** Ready

**Effort:** L, dominated by the eleven page suites: nine are reconstructed from transcript fragments rather than copied from disk, two are new, and every expectation in them has to be re-derived from the page's own boot payload so the same suite runs against a 47-row fixture and an 11,904-row library.

**Depends on:** none. Section 00's fixes each gain an assertion here once they land (listed under Verification, under the names section 00 uses), but nothing in this section waits for them: the pipeline test runs in a fresh working directory (no backup-CSV drift), publishes only spreadsheet codes (no drums code reaches the renderer), serves the bundle with `http.server` (never `serve.py`), and keeps `__CAPS__` out of the fixture titles until `page.fill` is fixed.

## Goal

A committed `tests/` tree that a fresh clone can run end to end with nothing but the venv and a Chrome binary: a deterministic synthetic song library, an integration script that runs `build.py`, `analyze.py`, `publish.py` and `deploy.py` against it with a stub `aws` on `PATH`, a headless-Chrome runner that drives the published page from injected ES modules and reads results back out of the DOM, eleven page suites plus a 390 px measurement, four stdlib `unittest` modules, and a GitHub Actions workflow that runs all of it on every push and pull request.

## Why

- The repo has no tests and no CI (`CLAUDE.md` says so three times; `.github/` holds only issue forms). The last upstream merge broke publish with a `KeyError` on `entry['spans']` (`web/bundle.py`, fixed in 69b5a8f) and nothing caught it until a publish was attempted; the `CACHE_DIR` to `OUTPUT_DIRS` rename before it broke `web/` the same way. A pipeline run on a 14-song fixture takes seconds and would have caught both.
- The page harness that verified the site on 2026-09-07 and 08 ("126 checks green across seven suites") was never committed and no longer exists anywhere on disk; it survives only as tool inputs in a 27 MB transcript (Appendix H says where). Every later section (02, 05, 06, 07) names assertions its suites should gain, so the suites have to exist first.
- Section 05 changes the loading contract of every JS module and names `tests/test_bundle.py` and `tests/test_deploy_plan.py` against a `deploy.plan()` that this section introduces.

## Current state

**Nothing to run against.** `songs/` (1,758 real songs, gitignored) and `caches/` are the only inputs; the two committed spreadsheets under `metrics/` are upstream's runs and have no cache. `.gitignore:2-12` ignores `*.pkl`, `caches/`, `*.csv`, `*.png`, `*.xlsx`, `songs/`, `site/`, so nothing the pipeline produces can be committed, and a committed fixture may contain only `song.ini`, `notes.chart` and `notes.mid` (the three names `tools/sanitize_songs.py:32` keeps).

**What the entry points need.** `build.py:43` takes `search_path` and `header` and writes to `config.OUTPUT_DIRS` (`caches/`, `metrics/`, `config.py:128-133`), which are relative paths resolved against the working directory; `ini_parser.SOURCES_DIR` and `assets.STATIC_DIR` resolve from `__file__` (`parsers/ini_parser.py:20-21`, `web/assets.py:11`). Running the scripts by absolute path from a temporary working directory therefore isolates every output without touching the repo. `build.py:111-124` always appends to `caches/<header>_BackupData.csv`, handing `backup_data` the `diff_*` value of every instrument the song has streams for; `build.py:159-165` writes the errors CSV only when there are errors. `analyze.py:97-98` read `config.DIFF_WRITE_MODE` and `config.XLSX_LEVELS` when the flags are absent, `analyze.py:178` reads `config.EXTRA_METRICS` with no flag at all, `analyze.py:126` skips drums, `analyze.py:206-207` rounds every float column to 2 places and sorts each sheet by `D` descending, and `analyze.py:174-175` reuses the cache timestamp for the xlsx. `publish.py:52` loads the cache before writing anything, `publish.py:53` calls `bootstrap.ensure_bootstrap`, which reads `caches/bootstrap-5.3.8.min.css` or fetches from jsdelivr (`web/bootstrap.py:16-18`, `:67-96`), and `--no-bootstrap` inlines `FALLBACK_CSS`. `bundle.render_graphs` walks `frames.codes_in(sheets)` (`publish.py:63`, `web/frames.py:25-28`), so only spreadsheet codes are rendered. `boot.boot_json` (`web/boot.py:35`) rewrites every `<` in the island as `\u003c`.

**Deploy cannot be dry-run offline.** `deploy.py:167` requires `aws` on `PATH`; `deploy.py:177-178` makes `--dry-run` skip publish and require an existing output; `deploy.py:187-193` runs `aws s3 sync ... --dryrun`, which authenticates and lists the bucket; `deploy.py:112-113` skips only the CloudFront call; `deploy.py:197` skips `verify()`. `verify()` (`deploy.py:137-160`) head-objects five fixed keys and compares `ContentType` by prefix. `ENV_FILE` is `.env` relative to the working directory (`deploy.py:50`, `:204`); a missing file reads as empty (`functions/envfile.py:14-15`) and deploy exits with `FRETWORK_BUCKET is not set`. The commands are assembled inline in `deploy()`, so there is no way to inspect them without running them.

**The old harness, from the transcript.** One HTML file per suite, made by replacing the page's single module tag `<script type="module" src="static/js/main.js"></script>` (`web/static/index.html:50`, the same template for serve and publish; `site/Local/index.html:57`; the published page has exactly 2 `<script` tags) with itself plus a second module tag; a copy of the bundle served by `python3 -m http.server --bind 127.0.0.1`; Chrome launched once per suite with `--headless=new --disable-gpu --no-sandbox --virtual-time-budget=25000 --window-size=1440,900 --dump-dom`; results read from `<pre id="results">` with `html.unescape`. Two facts shaped it: headless Chrome floors the layout viewport at 500 px whatever `--window-size` says, so 390 px was measured inside an iframe (`frame.html`), and only a synchronous measurement in the outer window's `load` handler ever produced output under `--dump-dom`. Chrome's remote-debugging port is unreachable from WSL, which is why there is no CDP and no driver. Suite sizes at the last run: test.js 18, order.js 12, keys.js 23, launch.js 17, roundtrip.js 6, fade.js 5 per width, video.js 15, links.js 12, contrast.js 28 pairs. At 390 px the transcript measured `D` at x 262 to 358 (on screen) and `CalcTier` at 358 to 419 (off).

**On this box today.** No Linux Chrome (`which google-chrome chromium chromium-browser` finds nothing); Windows Chrome 152.0.7977.83 at `/mnt/c/Program Files/Google/Chrome/Application/chrome.exe`, which fetched `http://127.0.0.1:<port>` served from WSL throughout the transcript (WSL2 forwards ports bound in WSL to Windows localhost). Python 3.12.3; pandas 3.0.5, numpy 2.5.3, mido 1.3.3, matplotlib 3.11.1, openpyxl 3.1.5, tqdm 4.70.0. `caches/bootstrap-5.3.8.min.css` is present (232,111 bytes). Importing all 33 modules (`build analyze render serve publish deploy config` plus every module under `web/`, `functions/`, `parsers/`) takes 0.40 s and succeeds; `import serve, web.server, web.handler, web.page, web.graph` leaves `matplotlib` and `openpyxl` out of `sys.modules`, as CLAUDE.md requires. `assets.load_static()` returns 19 files (17 modules, `app.css`, `favicon.svg`). Python's `mimetypes` reads `/etc/mime.types` first when it exists (it does here and on Ubuntu runners), so its answer for `.js` is the OS's, not the interpreter version's.

**Measured for the fixture design.** A generator-shaped `notes.chart` (one tempo, resolution 192, `N lane 0` lines, 28,526 bytes) parses through `chart_parser.chart_notes` in 1.3 ms to guitar Expert 705 / Hard 353, bass 235, drums 353 notes; the same notes written with mido as `notes.mid` (13,666 bytes) parse in 8.2 ms and the Expert guitar streams are identical (`np.allclose` on `time_ms`, `array_equal` on `lanes`). `calc_metrics` and `calc_nvcov` give D 70.18 (Expert), 19.25 (Hard), 10.23 (bass Expert), RemapDiff/CalcTier 6/6 and 2/1, so synthetic charts land inside the calibrated range. `ini_parse` on `name = <b>Fixture</b> & Co` with `icon = gh3` returns `Fixture & Co`, `Guitar Hero III: Legends Of Rock`, `Official=True`. `ini_parse` defaults every absent `diff_*` tag to `'-1'` (`parsers/ini_parser.py:103-106`), and `backup_data` writes `''` only for an instrument the song has no stream for (`functions/ini_updater.py:152`).

## Design

**1. Plain scripts and stdlib `unittest`; nothing added to `requirements.txt`.** Unit tests are `tests/test_*.py` modules run by `python -m unittest discover -s tests -t .`; the two slow, flag-bearing programs (`tests/pipeline_test.py`, `tests/page/run.py`) are scripts that exit non-zero on failure. Both scripts start with `sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[N]))` (`N` = 1 for `pipeline_test.py`, 2 for `run.py`) before any repo import, because `python tests/page/run.py` puts the script's own directory, not the repo root, at `sys.path[0]`. `tests/__init__.py` exists and is empty, the one regular package beside three namespace packages, because `unittest` discovery has required it since Python 3.11. Rejected: pytest, because the repo's rule is no test dependencies and `unittest` covers what is needed; a Node test runner, because there is no Node toolchain and the page is driven from inside Chrome anyway.

**2. One synthetic library, generated, never committed.** `tests/fixture.py` writes 14 song folders across 3 packs into a directory from a seeded `random.Random(20260911)`: 13 with a chart (9 `notes.chart` written as text, 4 `notes.mid` written with mido) and 1 with only a `song.ini`. Every pack, title, artist and charter is invented; no note stream comes from any real chart. No folder name uses `<>:"/\|?*`, so the fixture writes on a Windows checkout too; the `<` the escape test needs is in a `song.ini` `name`, not a folder. The table is below and is the interface: `test_fixture.py` pins its totals, `pipeline_test.py` derives every count from it. Rejected: committing a few freely licensed real song folders, because provenance would need checking forever and the folder names would carry a real library's shape; a generated library with hundreds of songs, because 47 rows already exceeds `RANGE_MIN_DISTINCT` (25, `boot.js:24`) on the Guitar sheet, which is the one threshold the page's behaviour changes at.

**3. Run the real entry points as subprocesses from a temporary working directory.** `pipeline_test.py` runs, with `cwd=<work>` and `sys.executable`, in this order: `<repo>/build.py --search-path library --header Fixture`; `<repo>/analyze.py --header Fixture --xlsx-levels ALL`; `<repo>/publish.py --header Fixture --no-bootstrap`; `<repo>/publish.py --header Fixture`; `<repo>/deploy.py --env deploy.env --dry-run`; `<repo>/deploy.py --env deploy.env --no-publish`; then the two guard cases. `caches/`, `metrics/` and `site/Fixture/` land under `<work>` (`site/Fixture` comes from `config.SITE_DIR`, no `--out-dir`), so the repo is never written to. Before running analyze it asserts `config.DIFF_WRITE_MODE is None` and exits with a message naming `config.py` if not (`Restore` would skip the spreadsheet entirely), and it computes the expected column list from `config.EXTRA_METRICS` rather than assuming the committed `False`. It parses the terminal summaries the scripts already print and reads the outputs back with `functions.cache.load`, `pandas.read_excel` and `json`. Rejected: calling `build_cache()` and friends in-process, because the process pools, `config` relative paths and `argparse` wiring are exactly what a regression would break.

**4. Deploy runs against a stub `aws` on `PATH`.** `tests/bin/aws` is a Python script that appends `shlex.join(argv[1:])` to the file named by `AWS_STUB_LOG`, answers `s3api head-object` from its own fixed extension table (`TYPES` in Appendix E) so `verify()` passes for a correct site and fails for a wrong extension, and exits 2 with a message on stderr if `AWS_STUB_LOG` is unset so it can never be mistaken for the real CLI. It never consults `mimetypes`: that table is the OS's on Linux and the interpreter's elsewhere, and the stub's job is to answer what a correct upload produces, not what this box thinks. `pipeline_test.py` copies it to `<work>/bin/aws` with a first line of `#!` + `sys.executable`, so it runs in the venv rather than the system interpreter, which CLAUDE.md forbids. `deploy.py --dry-run` is then a real dry run (the two `sync --dryrun` commands are recorded, no invalidation, no verify), and `deploy.py --no-publish` against the stub exercises the whole non-dry path including `verify()` and the CloudFront invalidation, without credentials. `deploy.plan()` is extracted so the same command list is also asserted in-process, and `deploy.samples(site_dir)` is extracted from `verify()` so the pipeline test derives the head-object keys rather than typing them. Rejected: an OIDC role and a real bucket for CI, because a test that needs AWS to pass is a test that gets skipped; stopping at `settings()` and `check_site()`, because the sync flags (`--delete`, the `graph/*` exclusion, the two cache classes) are the part worth proving.

**5. The page runner is the transcript's harness, made to own its lifetime.** `tests/page/run.py` stages a copy of a published bundle into `tempfile.mkdtemp()`, injects one suite module after the page's one module tag, serves the copy with `http.server` on a free `127.0.0.1` port from a `subprocess.Popen` it terminates in `finally`, launches one Chrome process per suite and parses `<pre id="results">`. The anchor is a regex, `<script type="module" src="static/[^"]+\.js"></script>`, matched exactly once, so section 05's `static/app.<hash8>.js` needs no runner change. Every staged page, `plain.html` included, gets a classic inline `<script>` immediately before the anchor that clears `localStorage` (and seeds it, when a manifest entry asks) before any module runs: a classic script runs during parsing and a module is deferred, so `main.js` reads clean storage, and a reused port or a reused Chrome profile cannot leak `fw.hidden` from a previous run. Suites share `tests/page/lib.js` for `say`/`done`/the error listener rather than repeating the preamble eleven times. `lib.js` parses `#fw-boot` itself and exports `BOOT`, plus `rows(sheet)` (async, today a resolved `BOOT.data[sheet].rows`), so no suite imports a page module; every expectation comes from that payload and from the DOM, never from a literal about a library, so the same run works against `site/Fixture` in CI and `site/Local` on the dev box. `links.js` is the one exception: it unit-tests `rich()`, so the runner copies `web/static/js/dom.js` from the repo into the staged directory as `src/dom.js` (it has no imports, so it loads standalone, and it keeps loading after section 05 removes the modules from the bundle). Rejected: `serve.py` as the server, because the point is to test the bytes S3 serves, and because serve answers 404 for `about.html`, `404.html` and `robots.txt` until section 00 lands (`web/handler.py:17`, `:34`); CDP or Playwright, because the debugging port is unreachable from WSL and the DOM readback needs no driver; screenshots in the committed runner, because Windows Chrome cannot write to a WSL path and a PNG is not an assertion.

**6. 390 px is measured inside an iframe, from two candidate pages.** `tests/page/frame.html` holds a `390x820` iframe of the pristine page and measures `contentDocument` synchronously in the outer window's `load` handler; it is not injected, the runner copies it beside `plain.html` and launches Chrome at `1200,900`. That is the form the transcript proved, and it is also the form section 05 breaks: once the rows arrive by `fetch()` after the iframe's `load` event, the outer handler finds no `#body tr`. So step 4 also writes `narrow.js`, an injected module that creates the same iframe from inside the page, awaits its `load` plus `wait(600)`, and measures the same things; `await wait()` chains in injected modules are proven to produce output under `--virtual-time-budget`. Both run on the dev box in step 4. The rule: if `narrow.js` produces output, it is the 390 px path, `frame.html` is deleted before the commit, and section 05 re-measures with `narrow.js`; if it does not, `frame.html` stays, the outcome is written in `tests/README.md`, and section 05 owns making the measurement wait for its rows. Either way there is one 390 px file in the tree, not two. Every other section names this measurement `frame.html`; if `narrow.js` is the survivor, read those references as `narrow.js` (the assertions and the `ok` lines are identical), and section 12's second iframe of `methodology.html` becomes a second created iframe inside `narrow.js`'s `measure()`.

**7. Bootstrap is real in the page suites and absent in the fallback check.** `pipeline_test.py` publishes twice into the same folder: first with `--no-bootstrap` (asserts the fallback branch: `<style>` inlined, no `bootstrap.css`, `BUNDLE_TOP` minus one), then with the Bootstrap file copied into `<work>/caches/` from `--bootstrap-css PATH` (asserts the link, the file, and that graphs report `0 rendered`). The page suites run against the second publish; `contrast.js` and the 390 px page measure Bootstrap's colours and button geometry and are meaningless against `FALLBACK_CSS`, so `run.py` refuses a fallback bundle unless `--allow-fallback` is passed, and then prints `SKIP` for those two. In CI the file comes from `actions/cache` keyed on `bootstrap-5.3.8`, fetched with `curl -fsSL` from the URL `web/bootstrap.py:17` names when the cache is cold; a failed fetch fails the job rather than degrading it. Rejected: `--no-bootstrap` everywhere, because it would test a page nobody sees.

**8. CI is the local run, with one deliberate difference.** `.github/workflows/ci.yml` runs the same five commands a developer runs, in the same order, on `ubuntu-latest` with Python 3.12 and the runner image's preinstalled Google Chrome. The one difference: `pip install -r requirements.txt` goes into `actions/setup-python`'s interpreter, not a `.venv/`, because the runner is disposable and the CLAUDE.md rule about the system interpreter protects a developer's machine, not a container that is deleted after the job. Nothing else in the workflow is CI-only except the cache step and the `CHROME` variable. This is the one part of the section that cannot be verified before pushing: Actions is checked by pushing the branch and watching the run, and that is a step, not a follow-up.

## Data and interfaces

**Fixture table** (`tests/fixture.SONGS`; `G` guitar, `C` co-op, `R` rhythm, `B` bass, `K` keys, `D` drums; levels as `EMHX` letters):

| Pack folder | `icon` | Release / Official | Song folder | Format | Instruments and levels | Rows |
|---|---|---|---|---|---|---|
| `Fixture Pack A` | `gh3` | Guitar Hero III: Legends Of Rock / True | `A1 - Grid Runner` | chart | G:EMHX B:X | 5 |
| | | | `A2 - Two Tier` | chart | G:HX | 2 |
| | | | `A3 - Midi Mirror` | mid | G:EMHX B:HX | 6 |
| | | | `A4 - Keys Only Once` | chart | G:X K:X | 2 |
| `Fixture Pack B` | `rb2` | Rock Band 2 / True | `B1 - Half Medium` | chart | G:MX B:X | 3 |
| | | | `B2 - Drum Mid` | mid | G:EMHX D:X | 4 (+1 drums code) |
| | | | `B3 - Co-op Lead` | chart | G:EX C:X | 3 |
| | | | `B4 - Ini Only` | none | (song.ini only) | 0 |
| `Fixture Pack C` | `fixturepack` | Custom / False | `C1 - Legacy Bass` | chart | G:MHX B:X (section `ExpertSingleBass`) D:X | 4 (+1 drums code) |
| | | | `C2 - Mid Pair` | mid | G:X B:X | 2 |
| | | | `C3 - Hard Without Expert` | chart | G:H | 1 |
| | | | `C4 - Less Than More` | chart | G:X R:X B:X | 3 |
| | | | `C5 - Every Level` | chart | G:EMHX B:EMHX | 8 |
| | | | `C6 - Enhanced Opens` | mid | G:EMHX (`[ENHANCED_OPENS]`, open pitch 95) | 4 |

Totals, pinned in `test_fixture.py`: 14 `song.ini`, 13 cached songs, 1 "no usable chart/mid", 0 errors, 49 codes (47 five-fret + 2 drums), xlsx rows Guitar 35 / Bass 11 / Keys 1 = 47, sheets `['Guitar', 'Bass', 'Keys']` (Drums absent: `analyze.py:126`), 25 Official rows and 22 Custom, landing view on Guitar (Expert + Official) 8 rows, Guitar `D` values distinct after rounding to 2 places (`analyze.py:206` rounds before writing, and `query.distinct` at `web/static/js/query.js:23-33` counts the stored values, so distinctness at full precision is not the number that matters; the test wants at least 30 so a small drift cannot land on the 25 threshold). `C3` has no Expert anchor (`RemapDiff`/`CalcTier` NaN). `C4`'s `song.ini` name is `<b>Less</b> < More` (DETAG leaves `Less < More`, which proves the `<` escape at `web/boot.py:35`), its `loading_phrase` carries `%` and `=`, and its `artist` is written in cp1252 with an accented character; `A3`'s `song.ini` is utf-8-sig with CRLF line endings. `diff_guitar` is set on A1 (4), A3 (6), C5 (2), set to `-1` on B1, and absent everywhere else; `diff_bass` on A1 (3) only. Every `song.ini` also carries `genre`, `year` and `album` (section 08 reads them; nothing here asserts them) and `song_length`. Chart text: `[Song]` with `Name` and `Resolution = 192`; `[SyncTrack]` with `0 = TS 4` and one `0 = B <bpm*1000>` (bpm per song from 100 to 180); an empty `[Events]`; per section one `<tick> = N <lane> 0` line per lane of a chord, plus in `A1`'s `ExpertSingle` one `N 7 0` open note, one `N 5 0` and `N 6 0` modifier pair, one `S 2 768` and an `E solo` line, all of which the parser must ignore or fold (`parsers/chart_parser.py:140-146`). MIDI: type 1, `ticks_per_beat=192`, track 0 with `set_tempo` only, one track per part named exactly as `instruments.MID_TRACK_NAMES`, `note_on` velocity 100 and `note_off` a 24-tick later, pitches `MID_PITCH_BASE[level] + lane`; drums pitch 96 kick and 97 to 100 hands. Charts run 60 to 150 s and 150 to 900 notes; lower levels are strided subsets of Expert.

**Which row a search picks.** Any suite or runner that types into `#q` and then asserts on the rows shown must take its search text from a row that passes the filters it asserts under, and the text is the first whitespace-delimited word of that row's title, lower-cased (`url.js:17` trims `q`, so a fixed-length slice ending in a space would not round-trip). `launch.js` picks the first row whose `Level` is `Expert` and `Official` is `true`; `run.py`'s `roundtrip_query` picks the first row of the second sheet whose `Level` is `Hard`. Sheets are sorted by `D` descending (`analyze.py:207`), so "first row" alone can be a Custom song or a level the filter hides.

**`tests/fixture.py` API**: `write(dest: Path, seed: int = 20260911) -> Library`; `Library` is a dataclass with `root`, `songs` (list of `Song(pack, folder, fmt, parts: dict[str, str], official: bool, release: str)`) and properties `ini_count`, `charted`, `codes`, `rows_by_sheet`, `official_rows`, `backup_rows` (the expected `diff_*` cell per song and tag, derived from `parts` and the tags in the table by the rule at `functions/ini_updater.py:152`); `python tests/fixture.py DEST` writes it and prints the totals. Generation is deterministic: the same seed writes byte-identical files (asserted by `test_fixture.py` on two runs).

**`tests/pipeline_test.py` CLI**: `--keep DIR` (use and keep `DIR` as the working directory instead of a deleted temp dir), `--bootstrap-css PATH` (copied to `<work>/caches/bootstrap-5.3.8.min.css` before the second publish; when absent the second publish is skipped and the run notes it), `--header` (default `Fixture`), `--python` (default `sys.executable`). Layout under `<work>`: `library/` (the fixture), `caches/`, `metrics/`, `site/Fixture/`, `bin/aws`, `deploy.env`, `aws.log`. `deploy.env` content: `FRETWORK_BUCKET=fixture-bucket`, `FRETWORK_DISTRIBUTION=E1FIXTURE0000`, `FRETWORK_HEADER=Fixture`, `FRETWORK_SITE_DIR=site/Fixture`; every deploy invocation passes `--env deploy.env`, since the default `.env` resolves against `<work>` and does not exist there. Environment for every subprocess: `PATH=<work>/bin:$PATH`, `AWS_STUB_LOG=<work>/aws.log`, `PYTHONUNBUFFERED=1`. Exit 0 with a one-line summary per stage; exit 1 on the first failed assertion, printing the stage's captured stdout. Linux and WSL only: the stub is a shebang script named `aws` with no extension, which Windows will not execute however its mode is set; the unit tests and the fixture run anywhere.

**`tests/bin/aws`**: committed with mode 100755; the `chmod 0o755` the test applies to its copy covers a Linux checkout that lost the bit (a zip download, `core.fileMode=false`). Log format: one `shlex.join` line per invocation. `head-object` answer: `TYPES.get(os.path.splitext(key)[1], 'binary/octet-stream')` printed to stdout (`--output text` shape), where `TYPES = {'.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml', '.png': 'image/png', '.json': 'application/json', '.txt': 'text/plain'}`; `verify()` compares by `startswith` (`deploy.py:154`), so the bare types match its `text/html` and the `; charset=utf-8` forms alike.

**`deploy.plan(bucket, distribution, site_dir, dry_run) -> list[list[str]]`** (new in `deploy.py`): the graph sync, the page sync, then the invalidation when `distribution` is set; `--dryrun` appended to each sync when `dry_run`. `deploy()` iterates it through `run()`, which keeps its dry-run skip of the CloudFront command and still prints the command first. **`deploy.samples(site_dir) -> dict[str, str]`** (new, extracted from `verify()` lines 139-146): the key-to-expected-type map `verify()` checks. Today's plan output, `<site>` and `<b>` as in section 05:

```
aws s3 sync <site>/graph/ s3://<b>/graph/ --delete --cache-control "public, max-age=604800"
aws s3 sync <site>/ s3://<b>/ --delete --exclude "graph/*" --cache-control no-cache
aws cloudfront create-invalidation --distribution-id <id> --paths /*
```

Section 05 extends `plan()` to its full sequence (its current text: eight commands with a distribution, six without) and rewrites `tests/test_deploy_plan.py` to match; both signatures stay.

**Suite result contract** (`<pre id="results">`, appended to `document.body` by `done()`): one line per check, `PASS <name>` or `PASS <name>  <detail>` (two spaces), `FAIL <name>  <detail>`, `ERROR <message>` (from the `error` and `unhandledrejection` listeners), `ok   <line>` for measurement-only output, `SKIP <name>  <reason>`. `contrast.js` emits `ok   <name padEnd 24><ratio padStart 8>  <#fg on #bg padEnd 22><px>[ note]` or `FAIL`/`MISSING` in the same shape. The runner fails a suite on any line starting `FAIL`, `ERROR` or `MISSING`, when the block is absent (`NO RESULTS`), or when the block holds no `PASS` or `ok` line at all (`NO CHECKS`, printed with the block's first line: `frame.html` ships with `waiting` in the block, and a load handler that never ran must not read as green). `--dump-dom` HTML-escapes the block (`->` arrives as `-&gt;`), so it is `html.unescape`d before matching.

**`tests/page/run.py` CLI**: `--site DIR` (default `site/<header>`), `--header` (default `config.HEADER`), `--suite NAME` (repeatable; default all), `--chrome PATH` (default: `$CHROME`, then `shutil.which` over `google-chrome`, `chromium`, `chromium-browser`, then `/mnt/c/Program Files/Google/Chrome/Application/chrome.exe`), `--budget MS` (default 30000), `--keep` (leave the staged copy behind and print its path), `--allow-fallback`. Staged files: `index.html` is never copied under that name; the pristine page is `plain.html`, each suite gets `<stem>.html` (`launch.html` for `launch.js`), suites and `lib.js` sit beside them, `src/dom.js` is copied from `web/static/js/dom.js`, `static/`, `bootstrap.css`, `about.html`, `404.html`, `robots.txt`, `graph/manifest.json` and up to 40 PNGs are copied. Anchor: the regex `ANCHOR` in Appendix D; the runner asserts one match, `src.count('<script') == 2`, and that no suite file name occurs in the source before injecting. Storage: the classic `<script>` inserted before the anchor is `try{localStorage.clear();<seeds>}catch(e){}` where `<seeds>` is one `localStorage.setItem(JSON key, JSON value);` per entry of the manifest's optional `storage` dict (this is also how section 05 seeds `fw.hidden` for its `fw.v` migration case). Chrome flags, in order: `--headless=new --disable-gpu --no-sandbox --virtual-time-budget=<budget> --window-size=<w>,<h> --dump-dom <url>`, preceded by `--user-data-dir=<profile>` when the runner has one: on a Linux binary a `tempfile.mkdtemp()`; on the Windows binary a directory made under Windows' own temp folder (`cmd.exe /c "echo %TEMP%"`, `\r` stripped, converted with `wslpath -u` for `mkdtemp` and passed to Chrome in the form `cmd.exe` printed), and no profile at all, with a note printed, if `cmd.exe` is not on `PATH`. The storage script is what guarantees a clean start; the profile is hygiene, so the developer's real Chrome profile does not collect one origin per run. Manifest:

```python
SUITES = [
    ("test.js",      {}),
    ("order.js",     {}),
    ("keys.js",      {}),
    ("launch.js",    {}),
    ("roundtrip.js", {"queries": [roundtrip_query]}),     # composed from the boot payload
    ("fade.js",      {"windows": ["700,900", "1000,900", "1440,900"]}),
    ("video.js",     {}),
    ("links.js",     {}),
    ("about.js",     {}),
    ("notfound.js",  {}),
    ("contrast.js",  {"needs_bootstrap": True}),
    ("narrow.js",    {"needs_bootstrap": True}),           # or ("frame.html", {"page": True, "window": "1200,900", "needs_bootstrap": True}); Design 6
]
```

Optional keys, defined once here and reused unchanged by every later section: `queries` (a list of strings or callables taking the staged bundle's `plain.html` and returning a query string; one Chrome launch per entry, each appended to the URL), `windows` (run once per size), `window` (one size), `page` (the file is a page of its own, not injected), `needs_bootstrap`, `storage` (dict seeded into `localStorage` before the modules run), `delay` (a `{url-prefix: ms}` map the runner's server applies before answering a matching request, for suites that must see a file arrive late). `roundtrip_query` is built by the runner from the boot island it parses out of `plain.html`: `?sheet=<second sheet>&q=<first word of the title of the first Hard row in that sheet, lower-cased>&sort=NoteCount&dir=asc&f.Level=Hard`; the picked row guarantees at least one match, and `rowsAll().length` bounds it from above, which is what `roundtrip.js`'s `0 < shown() < rowsAll().length` asserts.

**`tests/page/lib.js`** exports `BOOT` (the parsed island), `rows(sheet)` (async; `BOOT.data[sheet].rows` today), `levels()` (the `#levels` button labels in DOM order, which is `LEVELS` without importing `boot.js`), `say(name, ok, detail)`, `note(line)`, `skip(name, reason)`, `done()`, `wait(ms)`, `key(k, target)` (returns the `dispatchEvent` result, so `!key("Tab")` means the page called `preventDefault`), `pt(type, clientX, target)`, `click(el)`, `chip(hostId, text)`, `lit(hostId)`, `shown()`, `params()`; installs the two error listeners at import. Nothing in `lib.js` imports a page module: `RANGE_MIN_DISTINCT` and `LEVELS` live in `boot.js:20-24` and not in the island, so suites assert relatively where those matter (`order.js`: Guitar gets the range box, Keys does not, with the 25 named in a comment).

**DOM the suites depend on** (`web/static/index.html`, `markup.js`, `chooser.js`, `dropdown_view.js`, `overlay.js`): ids `brand src how q tools sheets levels official cols clear count grid head body dd cd modal about foot hint`; `#head th[data-c]` with `aria-sort`, `.lbl[data-sort]`, `.flt[data-flt][aria-expanded]`, `.rz[data-rz]`; `#body tr[data-code][tabindex]`, `td.rank`, `td.headline` (D), `td.title.song`, `td.artist`, `td.code .cp[data-copy]`, `.lvl.<Level>`; `#cd .cc[data-col][draggable]`, `#cd input[data-col]`, `#cd [data-act=showall]`; `#dd .list .v`, `#dd [data-act=all|none|apply|clear]`; `#modal.on[aria-label$=": <code>"] .mhead a.rpt`; `#about.on iframe`, `#about p.cap`, `#about h2`, `#about .more a`; `#foot a.req`, `#foot a[href="about.html"]`; `.fw-wrap.more`, `#tools.more`. Storage keys `fw.hidden`, `fw.order`, `fw.widths`. A change to any of these is a change to the suites in the same commit. Three of them have a second consumer: the leaderboards userscript (`../fretladder-leaderboards.user.js`, the Tampermonkey prototype kept beside the repo, untracked) reads the `#fw-boot` island, hooks `#modal .mhead`, and parses the code out of the modal's aria-label, so a red in `launch.js`'s aria-label or `.mhead` checks means that script is broken too; sections 05 and 13 keep those three stable or update the script.

**Environment variables**: `CHROME` (runner), `AWS_STUB_LOG` (stub), nothing else. Ports: always a free one from `socket.bind(("127.0.0.1", 0))`, never fixed.

**Workflow** (`.github/workflows/ci.yml`): triggers `push` and `pull_request` (a branch with an open PR runs twice per push; accepted, so a feature branch is checked before its PR exists); one job `test` on `ubuntu-latest`; steps in order: checkout, `actions/setup-python` 3.12 with pip cache, `pip install -r requirements.txt`, unit tests (which include the import check), `actions/cache` on `caches/bootstrap-5.3.8.min.css` with key `bootstrap-5.3.8`, `curl -fsSL` of that file when absent, `python tests/pipeline_test.py --keep ci-work --bootstrap-css caches/bootstrap-5.3.8.min.css`, `python tests/page/run.py --site ci-work/site/Fixture` with `CHROME: google-chrome`. Assumption stated in the file: `ubuntu-latest` images ship Google Chrome stable on `PATH` as `google-chrome`; the fallback if that ever stops being true is `browser-actions/setup-chrome@v1` before the page step, which is a two-line change and is written in a comment beside the step.

**What section 05 changes here** (so its implementer has one list): `lib.js` keeps parsing `#fw-boot` for `SHEETS` (the renamed `data`), `UI`, `FOOTER`, `EXPLAINER`, `HIDDEN_DEFAULT`, and its `rows(sheet)` becomes a `fetch()` of `SHEETS[sheet].file`, awaited before any row-derived expectation (or the suite awaits the `fw:sheet` event section 05 dispatches); `run.py`'s `roundtrip_query` reads `data/<slug>.<hash8>.json` from the staged copy instead of the island's rows, and `stage()` copies `data/` and `graph/curves-manifest.json`; the anchor regex already matches `static/app.<hash8>.js`; `tests/bin/aws` answers `--query '[ContentType,CacheControl]'` with both values from the key's directory (`static/` and `data/` immutable, `graph/` a week, else `no-cache`, the same rule as `assets.cache_class`); `pipeline_test.py`'s listdir and static-count assertions already derive from `deploy.BUNDLE_TOP` and `assets.load_static()` (05 renames the latter `load_assets`); `plan()` grows to 05's sequence and `test_deploy_plan.py` follows; the 390 px measurement is whichever file Design 6 left in the tree.

**Later sections add to this tree.** The footer anchor count is asserted in one place only, `launch.js`, from the payload (`test.js` carries no copy), so a section that adds a footer link changes nothing here. Each later section names its additions in its own Verification; this table is the one list, so the runner's vocabulary above is never extended ad hoc:

| Section | Python tests | Page suites and runner | Pipeline stages and fixture |
|---|---|---|---|
| 01 launch | `tests/test_check_site.py` | | a check-site stage over the served fixture bundle; three `html.parser` assertions over `about.html` in the publish stage |
| 02 percentile | `tests/test_percentile.py` | cases in `test.js`, `order.js`, `launch.js`, `roundtrip.js` | |
| 03 changelog | `tests/test_packs.py` | `launch.js` cases; a `links.js` case fetching `changelog.html` | `--packs <work>/packs.toml` on the pipeline's publish (publish refuses the fixture without it once 03 lands); a seeded `packs.toml` in the fixture |
| 05 data model | `tests/test_bundle.py`; `test_deploy_plan.py` rewritten | `lib.js` fetches `SHEETS[sheet].file`; the anchor regex; `launch.js` and `roundtrip.js` cases | |
| 06 graphs | `tests/test_graph_json.py` | `graph.js`; `compare.js` with `queries: [compare_query]` | PNG assertions become "only the OG code's PNG" |
| 07 song view | | `song.js`; `song_url.js` with `queries: [song_query, "?song=000000000000"]`; `keys.js` cases; the 390 px page gains the panel | |
| 08 ini fields | `tests/test_fingerprint.py` | `test.js` cases | fixture songs with `album`, `year`, `genre`; xlsx column assertions |
| 09 ingest | `tests/test_ingest.py` | | an `ingest` stage on a fixture archive |
| 10 duplicates | `tests/test_copies.py` | `launch.js`, `roundtrip.js` cases | +1 song, +1 code, +1 Guitar row (a byte-identical copy) |
| 11 drums | | `graph.js` case (a drums code draws) | +4 drums codes, a Drums sheet of 6 rows, once upstream ships |
| 12 methodology | `tests/test_methodology.py` | `links.js` cases; the 390 px page measures `methodology.html` too | `methodology.html` staged through `BUNDLE_TOP` |
| 13 links | `tests/test_links.py` | `links.js` cases with `delay: {"data/links": 800}` | `LINKS_FAKE` in `tests/fixture.py`; a registry stage |

Fixture totals are pinned once, in `tests/test_fixture.py`, derived from the fixture table (`len(Library.codes)` and the per-sheet counts), never as typed numbers; a later section that adds a fixture song states its delta against the table and updates the table, and the pins follow.

## Files touched

- `tests/__init__.py` (new): empty; makes `unittest` discovery work.
- `tests/README.md` (new): how to run everything locally (WSL and Linux), the harness gotchas listed under Risks so nobody rediscovers them, and the Design 6 outcome.
- `tests/fixture.py` (new): the table, the chart and MIDI writers, `write()`, CLI.
- `tests/test_fixture.py` (new): determinism, parsers accept every generated file in-process (no pools), the pinned totals, at least 30 distinct Guitar `D` values at 2 decimal places via `density`/`formula`.
- `tests/test_imports.py` (new): imports the 33 modules; a fresh subprocess proves `serve`'s startup path excludes matplotlib and openpyxl.
- `tests/test_deploy_plan.py` (new): `deploy.plan()` for the four (`dry_run`, `distribution`) combinations, flag by flag; `deploy.samples()` on a temp site folder with and without a PNG.
- `tests/test_labels.py` (new): the copyright and licence strings against `LICENSE`, and `page.rich_text` on the same four cases `links.js` gives `rich()`.
- `tests/pipeline_test.py` (new): the integration run, including the two section 00 assertions that need outputs.
- `tests/bin/aws` (new, executable): the stub.
- `tests/page/run.py` (new): stage, serve, launch, parse, report.
- `tests/page/lib.js` (new): the shared suite preamble.
- `tests/page/frame.html` or `tests/page/narrow.js` (new): the 390 px measurement, per Design 6.
- `tests/page/test.js`, `order.js`, `keys.js`, `launch.js`, `roundtrip.js`, `fade.js`, `video.js`, `links.js`, `contrast.js` (new): the reconstructed suites; `about.js`, `notfound.js` (new): the two section 00 asked for.
- `deploy.py`: extract `plan()` from `deploy()` lines 187-196 and `samples()` from `verify()` lines 139-146; no behaviour change.
- `.github/workflows/ci.yml` (new).
- `README.md`: a short section 9, "Tests", with the five commands and the WSL note, and its Index entry (`README.md:24-33`); section 7 gains one line pointing at it.
- `CLAUDE.md`: replace "no test suite" in Commands, the "There are no automated tests" paragraph, and the "No tests, no CI" bullet with what exists; keep the sentence about running against `songs/` after an upstream merge, since the fixture does not exercise real-library shapes.

## Steps

1. **`deploy.plan()`, `deploy.samples()`, the stub, and the first unit tests.** Extract the command list from `deploy()` into `plan()` and the sample map from `verify()` into `samples()`, leaving `run()` and its dry-run CloudFront skip alone. Add `tests/bin/aws`, `tests/__init__.py`, `tests/test_deploy_plan.py` (asserts the three commands above, `--dryrun` placement, no invalidation without a distribution, `--exclude graph/*` on the page sync and not the graph sync, both cache strings verbatim, and `samples()` on a temp folder with and without a PNG), `tests/test_imports.py` and `tests/test_labels.py`. Check: `python -m unittest discover -s tests -t . -v` prints `OK` with 8 or more tests; from a folder that holds a publish output (`site/Local` through a two-line env file naming `FRETWORK_SITE_DIR`), `PATH=tests/bin:$PATH AWS_STUB_LOG=/tmp/aws.log python deploy.py --env /tmp/stub.env --dry-run` exits 0, prints the three commands, and `/tmp/aws.log` holds exactly the two `s3 sync ... --dryrun` lines; no real profile, no network. Commit: `deploy: assemble the aws commands in plan(), and start a tests/ tree`.

2. **The fixture.** `tests/fixture.py` and `tests/test_fixture.py`. Check: `python tests/fixture.py /tmp/fx` prints `14 song.ini, 13 charted, 49 codes, rows Guitar 35 Bass 11 Keys 1`; running it twice into two directories gives identical `sha1sum` lists; `python -m unittest tests.test_fixture -v` passes, including `test_parsers_accept_every_file` and `test_guitar_d_values_distinct`. Commit: `tests: a synthetic 14-song library generator, nothing real in it`.

3. **The pipeline test.** `tests/pipeline_test.py` with the assertions listed under Verification. Check: `python tests/pipeline_test.py --bootstrap-css caches/bootstrap-5.3.8.min.css` exits 0 and prints one summary line per stage; `--keep /tmp/fw-ci` leaves a folder whose `site/Fixture` `deploy.check_site` accepts. Commit: `tests: build, analyze, publish and deploy the fixture end to end, with a stub aws`.

4. **The runner, the library, the 390 px page and one suite.** `tests/page/run.py`, `lib.js`, `frame.html`, `narrow.js`, `launch.js`. Run both 390 px candidates and apply the Design 6 rule; delete the loser. Check: `python tests/page/run.py --site /tmp/fw-ci/site/Fixture --suite launch.js --suite <the 390 px file>` reports every check passing under Windows Chrome from WSL; `--site site/Local --suite launch.js` passes against the real bundle; `--keep` and a deliberate `say("x", false)` shows a `FAIL` line and exit 1; a deliberate `<pre id="results">waiting</pre>` with no handler prints `NO CHECKS`. Commit: `tests: a headless-Chrome runner for the published page, and its first suite`.

5. **The other ten suites.** Reconstruct the eight from the transcript lines in Appendix H, write `about.js` and `notfound.js` fresh, one commit per two or three suites if the diffs get long, each run against both bundles before it lands. Check: `python tests/page/run.py --site /tmp/fw-ci/site/Fixture` and `--site site/Local` both end `12 suites, 0 failed`. Commit: `tests: the page suites, every expectation read from the page's own data`.

6. **Workflow and docs.** `.github/workflows/ci.yml`, `README.md` section 9 and its Index entry, `CLAUDE.md`, `tests/README.md`. Check: push the branch and open the Actions run; the job goes green in under ten minutes; then merge with `git merge --no-ff`. Commit: `ci: import check, unit tests, the fixture pipeline and the page suites on every push`.

## Verification

**Unit** (`python -m unittest discover -s tests -t . -v`): `test_imports` (33 modules; `serve` startup path clean), `test_deploy_plan` (4 combinations, `samples()`), `test_labels` (the rendered `UI['copyright']` and the Licence entry of `ABOUT`, tags stripped, each contain LICENSE line 3 case-insensitively, `copyright (c) 2026 Staycation`, with `Staycation` followed by a non-alphanumeric so `Staycation44` cannot pass, since `labels.py:297-299` writes "Engine copyright (c) 2026 [Staycation](...)" and `:262-263` quotes the notice in full; `page.rich_text` gives an anchor for `https`, escapes `<>&"`, gives no anchor for `javascript:`, and keeps balanced parentheses inside a URL), `test_fixture` (determinism, parser acceptance of all 13 charts in-process, totals, at least 30 distinct rounded `D` values). Under 5 s.

**Pipeline** (`python tests/pipeline_test.py --bootstrap-css caches/bootstrap-5.3.8.min.css`), stage by stage, what is asserted:

- build: stdout has `Song.ini count        14`, `No usable chart/mid   1`, `Errors                0`, `Cached songs          13`; no `caches/Fixture_errors_*.csv`; exactly one `caches/Fixture_cache_*.pkl`; loaded, `len(songs) == 13`, `len(codes) == 49`, every code ends in `[EMHX][GCRBKD]`, every 5-fret stream is `float64` sorted with a `uint8` mask, `source_format` per song matches the table, `meta['Name']` for C4 is `Less < More`, `meta['Official']` and `Release` per pack; `caches/Fixture_BackupData.csv` header equals `ini_updater.BACKUP_COLUMNS` and has 13 rows whose cells equal `Library.backup_rows`, which spells out: `diff_guitar` is `4` for A1, `6` for A3, `2` for C5 and `-1` for the other ten (B1's explicit `-1` and the parser's default are indistinguishable, `parsers/ini_parser.py:104`); `diff_bass` is `3` for A1, `-1` for A3, B1, C1, C2, C4 and C5, and `''` for the rest; `diff_drums` is `-1` for B2 and C1 and `''` elsewhere; `diff_keys` is `-1` for A4 only, `diff_guitar_coop` `-1` for B3 only, `diff_rhythm` `-1` for C4 only, `''` everywhere else. That `''` means "no stream" and `-1` means "no tag" is exactly the reading section 00's header migration must keep.
- analyze: `config.DIFF_WRITE_MODE is None` was asserted before the run; exactly one `metrics/Fixture_metrics_<ts>.xlsx` with `<ts>` equal to the cache's; sheets `['Guitar', 'Bass', 'Keys']`; columns exactly `analyze.COLUMN_ORDER` (25 names) when `config.EXTRA_METRICS` is True, otherwise minus `xlsx_format.DEFAULT_HIDDEN_COLS` (14 names), in order; row counts 35/11/1; `Official` sums to 25; C3's row has NaN `RemapDiff` and `CalcTier` and every other row has both; every `D > 0`; `Difficulty` is `-1` wherever the table has no tag; every `Code` in the xlsx is in the cache and no drums code is.
- publish, `--no-bootstrap`: stdout has no `spreadsheet is from` note; `sorted(os.listdir('site/Fixture')) == sorted(deploy.BUNDLE_TOP - {'bootstrap.css'})`; `index.html` has `id="fw-boot"`, no match for `__[A-Z][A-Z_]*__`, `<style>` from `FALLBACK_CSS` and no `href="bootstrap.css"`, `<title>Fretladder</title>`, a strapline matching `Updated \d{1,2} [A-Z][a-z]+ \d{4}  -  47 charts`, the string `Less \u003c More` (the six characters `\u003c`, `web/boot.py:35`) and not `Less < More`; the boot island parses, its C4 row reads `Less < More`, and its `data` keys and row counts match the xlsx; `graph/manifest.json` keys equal `frames.codes_in(sheets)` (47) and each `graph/<code>.png` starts with `\x89PNG`; banner has `graphs: 47 rendered, 0 unchanged`; `about.html` and `404.html` have no placeholder left, every `href` in `about.html` is `http(s)`, `./` or `static/favicon.svg`, and `404.html` links `/static/favicon.svg` and `/`; `robots.txt` equals `page.ROBOTS`; the files under `static/` are exactly the keys of `assets.load_static()` with `/static/` stripped (19 today).
- publish, with Bootstrap: `bootstrap.css` present and byte-equal to the `--bootstrap-css` file (232,111 bytes for 5.3.8), `index.html` links it and has no inlined `<style>` fallback, banner has `graphs: 0 rendered, 47 unchanged` and `page files: 2 written` (index and bootstrap) or fewer; `sorted(os.listdir('site/Fixture')) == sorted(deploy.BUNDLE_TOP)`.
- deploy `--env deploy.env --dry-run`: exit 0; `aws.log` has exactly two lines, both `s3 sync` ending in `--dryrun`, the first `<site>/graph/ s3://fixture-bucket/graph/ --delete --cache-control 'public, max-age=604800'`, the second with `--exclude 'graph/*' --cache-control no-cache`; no `cloudfront` line; stdout still prints the invalidation command (it is planned, then skipped, `deploy.py:111-113`).
- deploy `--env deploy.env --no-publish`: exit 0; `aws.log` gains two syncs without `--dryrun`, one `cloudfront create-invalidation --distribution-id E1FIXTURE0000 --paths /*`, then one `s3api head-object` line per key of `deploy.samples('site/Fixture')` in that order (five today: `index.html`, `static/js/main.js`, `static/css/app.css`, `static/favicon.svg`, the first `graph/*.png`); stdout has as many `ok  ` lines and `Done`.
- deploy guards: a stray file dropped into `site/Fixture` makes `--env deploy.env --no-publish` exit non-zero with `holds files publish did not write`; a `deploy.env` with `AWS_SECRET_ACCESS_KEY=x` exits with `contains AWS credentials`.
- section 00, once it lands (functions in `pipeline_test.py` under these names, run after the second publish): `test_lookup_returns_none_for_drums_code` (`GraphRenderer('Fixture', <cache>).lookup('<B2 drums code>')` is `None` while a guitar code resolves; section 11 flips it) and `test_serve_pages_match_publish` (`MetricsServer` on port 0 built from the same xlsx and cache answers `/about.html`, `/robots.txt` and `/nope` with 200/200/404, the first two byte-equal to `site/Fixture`'s files).

Estimated wall time under 60 s (parse cost measured above; 47 renders at the documented 0.12 s; two process-pool start-ups). Not measured here because build and publish were not run.

**Page** (`python tests/page/run.py --site /tmp/fw-ci/site/Fixture`, then `--site site/Local`): twelve suites, each ending `N checks, all pass`; the run ends `12 suites, 0 failed`. Assertion families per suite, all data-derived:

- `test.js`: default visible columns equal `ORDER` minus `HIDDEN_DEFAULT` (with `Rank` first); every `td.headline` prints `decimals("D")` places and they all agree; Official chip on by default, clicking it clears, Official then Custom shows every row; drag on `.rz` widens by the pointer delta within 3 px and stores `fw.widths`; drag below `MIN_PX` stores 48; dblclick clears; column reorder: `dragstart` on the first `#cd .cc[data-col]`, `dragover` on the third with `clientY` below its midpoint, then `dragend` (the three events `chooser.js:38-57` listens for; there is no `drop` handler), after which the `#head th` order has moved that column two places and `fw.order` holds the new list (source: TRANSCRIPT:3269); chooser `showall` empties all three keys; `#foot a.req` href ends `issues/new?template=song-pack.yml`; footer link count equals `2 + FOOTER.length + links in UI.copyright + 1`.
- `order.js`: after clearing the official chip, the Level filter list is `levels()` in `VALUE_ORDER` order, Type is `Lead, Co-op, Rhythm` on Guitar, Official is `Official, Custom`; sorting Level once puts `Expert` first and twice `Easy`; first click on Official puts ticks on top; a range box appears for `D` on Guitar and a checkbox list on Keys (the threshold is `RANGE_MIN_DISTINCT`, 25, in `boot.js:24`; the fixture and Local both straddle it).
- `keys.js`: one `tabindex="0"` row, ArrowDown/ArrowUp/End/Home/PageDown move it, Enter opens `#modal` with focus on it and `aria-label` ending in the code, Tab is trapped, Escape closes and returns focus to the row; keyboard sort keeps focus on the `.lbl` and sets `aria-sort`; chips toggle `aria-pressed`; `#cols` `aria-expanded` follows open, Escape, close.
- `launch.js`: given in full below.
- `roundtrip.js`: state equals `location.search` for `sheet`, `q`, `sort`, `dir`, `f.Level`; `lit("official")` is empty (a link replaces the defaults); `0 < shown() < rowsAll().length`.
- `fade.js` at 700, 1000 and 1440: `.fw-wrap.more` equals `scrollWidth > clientWidth`; `mask-image` set only then; scrolling to the far right clears it and back restores it; the sticky `th` top is unchanged within 2 px after `scrollTop = 900`.
- `video.js`: zero iframes before `#how`; after, one iframe whose `src` starts with `https://www.youtube-nocookie.com/embed/`, has `enablejsapi=1` and `start=`, no `autoplay=1`, a non-empty `title`; `.vid` box within 0.1 of 16:9; Escape posts `pauseVideo` to origin `https://www.youtube-nocookie.com` through a `contentWindow` getter shadowed with `Object.defineProperty`; `p.cap` text contains `Staycation44`.
- `links.js`: `rich()` unit cases from `./src/dom.js` (anchor for `https`, escaping of `<>&"`, no anchor for `javascript:`, balanced parentheses in a URL); every anchor in `.fw-head`, `#about`, `#foot` and the rendered explainer has an `http(s)` or same-site `href`; `fretwork` and `Staycation44` are linked wherever they appear; no raw `[text](url)` remains in those four regions.
- `about.js` (new, section 00's ask): `fetch` of the `#foot a[href="about.html"]` href resolves 200 with `text/html`; the body parsed with `DOMParser` has one `h1`, a link back to `./` whose text is `UI.about_back`, and no `__[A-Z_]+__` text.
- `notfound.js` (new, section 00's ask): `fetch("nope")` under the staged bundle is 404 (`http.server`'s own; the status is the assertion); `fetch("404.html")` is 200 and parses to `p.code` reading `404`, an `a[href="/"]` whose text is `UI.not_found_link`, and `<meta name="robots" content="noindex">`.
- `contrast.js`: every named pair at 4.5:1 for text and 3:1 for clickable chrome, measured from computed styles with alpha and opacity flattened over the nearest opaque ancestor, chooser and a filter dropdown open, worst `.lvl` badge included; prints the ratio table as `ok` lines.
- the 390 px page (`frame.html` or `narrow.js`): layout viewport `390 x 820`, `(max-width:640px)` active, `#tools` scrollable with `.more` set and cleared at the far right, the first five `th` positions printed as `ok` measurement lines (CalcTier is off screen at 390 px by design, 358 to 419 last measured), the one assertion `D is on screen without a swipe` (`D` right edge at or under 390), header plus footer under 35 % of the screen.

**390 px re-measure**: the Design 6 survivor is the re-measure; sections that change layout run it and read the `D` column line.

**What section 00 gains here once it lands**, under section 00's names, which this section adopts verbatim so the two lists agree: `tests/test_fixes.py` (new when 00 lands) with `test_fill_rejects_missing_and_unused`, `test_fill_keeps_placeholder_shaped_data` (a value containing `__REMIX__` survives unchanged), `test_scorable_rejects_drums_shape`, `test_check_pair_refuses_and_allows` (names only; `check_pair` reads no file, `publish.py:35-43`), `test_backup_header_migration` (the missing-file, fresh-header, drifted-row, already-current, longer-header and unknown-header cases in a temp directory); the two that need outputs, `test_lookup_returns_none_for_drums_code` and `test_serve_pages_match_publish`, live in `pipeline_test.py` as listed above; the page suites `about.js` and `notfound.js` are written in step 5 of this section, before 00, because the bundle under `http.server` already has both pages, and gain nothing at 00 except that the same checks then also hold under `serve.py` through `test_serve_pages_match_publish`. Two more: a fixture title `__SHOUT__ Fixture` (added to A2 when 00 lands, not before, since today's `fill` would abort publish on it) with the assertion that publish still succeeds; and a pre-seeded five-column `Fixture_BackupData.csv` in `<work>/caches/` before build with the assertion that build prints `Backup CSV header updated` and the file's header then equals `BACKUP_COLUMNS`. Section 00's list is the contract; this section owns where each item lives.

**Actions**: verified only by pushing. The first push of step 6 is the check; a red run is fixed on the branch before merge.

## Risks and gotchas

- **Headless Chrome floors the layout viewport at 500 px** (all of `--headless=new`, `--headless=old`, `--headless`; measured `innerWidth 500` for `--window-size=390,820`). Never assert a phone layout from `--window-size`; the iframe is the only 390 px path.
- **`frame.html` must measure synchronously in the outer window's `load` handler.** Two earlier versions (iframe `onload` plus `setTimeout(900)`; `requestAnimationFrame` polling) left `<pre>waiting</pre>` under `--dump-dom`. Inside injected page modules, `await wait(300..600)` chains do work under `--virtual-time-budget`, which is what `narrow.js` relies on.
- **A too-small `--virtual-time-budget` gives `NO RESULTS` and nothing else.** 30,000 ms covers 11,904 rows (60 to 71 ms repaints measured); the fixture needs far less, and virtual time does not cost wall time.
- **`--dump-dom` escapes the results block** (`&gt;`, `&quot;`); unescape before matching, and never put `</pre>` in a detail string.
- **Inject only into a pristine copy.** The old harness once regenerated suite pages from an already-injected file and a suite silently reported another suite's passes; the runner's three anchor assertions exist for that.
- **Synthetic clicks do not move focus.** `openAbout` and `openGraph` record `opener = document.activeElement` (`overlay.js:45`, `:73`) and close by focusing it; a `dispatchEvent(new MouseEvent("click"))` leaves `activeElement` on `body`, so any focus-return assertion must `el.focus()` before `click(el)`. `#how` is a button and rows carry `tabindex="-1"` (`markup.js:83`), so both take focus.
- **Turning off the only lit Level chip lights all four** (`table.js:32`), so toggle a chip that can go dark (`Hard` with `Expert` lit), not `Expert` alone.
- **Official is on at launch** (`main.js:58-59`) and tri-state: counts are a slice until the chip is cleared, and a URL without `f.Official` lights neither chip.
- **The raw `[text](url)` markup legitimately lives in the `#fw-boot` island**; `links.js` scans rendered regions only.
- **Cross-origin `contentWindow.postMessage` cannot be assigned**; shadow the `contentWindow` getter on the iframe element with `Object.defineProperty(..., {configurable: true})`.
- **Expectation drift is the usual failure.** Footer link counts went 6 to 7 to 9 and `h2` counts 4 to 5 to 4 during one week; that is why every count is computed from `FOOTER`, `EXPLAINER`, `HIDDEN_DEFAULT` and `UI` rather than typed. A test bug reads exactly like a product bug in the results; the detail column is the only clue.
- **Windows Chrome from WSL**: reachable over `http://127.0.0.1:<port>` because WSL2 forwards WSL ports to Windows localhost; cannot write a WSL path (`--screenshot` silently produces nothing), so a `--user-data-dir` must be a Windows path or absent. `--no-sandbox` is needed in containers and harmless elsewhere; `--disable-gpu` always.
- **Storage is per origin and origins are `127.0.0.1:<port>`**: without the clearing script a reused port would hand a run the previous run's `fw.*` keys; with it, the profile only matters for tidiness.
- **Kill servers by handle, never `pkill -f`**: a `pkill -f serve` once matched the shell running it. The runner holds the `Popen` and terminates it in `finally`; nothing is left on a port between runs.
- **Process pools on a 4-core runner**: `chart_loop`/`mid_loop` spawn `cpu_count() - 1` workers; with 9 charts and 4 MIDIs the pools cost more than the parsing, which is fine but is where a "why is build 3 s" question ends.
- **Timestamps are minute-resolution** (`TS_FORMAT`); two pipeline runs into the same kept `--keep` directory inside one minute overwrite the cache and xlsx by name. The test starts from an empty `caches/` and `metrics/` and refuses a `--keep` directory that already holds either.
- **`config.py` is user-edited and analyze reads it**: `--xlsx-levels ALL` is passed explicitly, `EXTRA_METRICS` decides the expected column list, and a `DIFF_WRITE_MODE` other than `None` stops the test before analyze with a message, because `Restore` writes no spreadsheet and the two write modes would touch the fixture's `song.ini` files.
- **The stub's `head-object` answer is a fixed table**, never `mimetypes`: the test asserts `verify()` printed `ok` for every sample, so a wrong extension in `samples()` shows up as a `WRONG` line, not a silent pass.
- **Bootstrap fetch in CI is a network call** to jsdelivr, once per cache miss; a failed `curl -fsSL` fails the job on purpose. Re-run.
- **`ubuntu-latest` Chrome is an assumption** about the runner image, stated in the workflow next to its fallback (`browser-actions/setup-chrome@v1`).
- **Actions itself is unverifiable before the push.** Everything else in this section runs on the dev box today.
- **The suites are white-box** against the DOM contract above and the island's shape; nothing imports a page module, so section 05's bundle needs only the changes listed under "What section 05 changes here".

## Out of scope and follow-ups

- Screenshots as artefacts (the transcript's `--screenshot` workflow): not part of the runner. A `--shots DIR` flag that names a Windows path on WSL and a native path on Linux is a small addition if a visual diff is ever wanted.
- Running the suites against `site/Local` in CI: impossible (the library is not committed) and unnecessary (the suites are data-independent).
- Pinning `requirements.txt`: the workflow installs whatever pip resolves, as the dev box does; a pin is a policy change for the whole repo, not a test concern. If a resolver drift ever breaks CI, pin then.
- A Windows-native pipeline run: needs an `aws.cmd` shim beside the stub; not wanted today.
- Optional follow-up: a `pull_request` run from a fork restores the base branch's `actions/cache` entry but cannot write one, so the curl step runs only when `main` has no entry for `bootstrap-5.3.8`. If the fetch ever flakes, commit the Bootstrap file under `tests/` (it is MIT) so no network is needed at all.

## Open questions

None.

---

## Appendix A: `tests/page/lib.js` in full

```js
// Shared by every suite: results go into <pre id="results">, which run.py reads
// out of --dump-dom. Anything that throws lands as an ERROR line rather than as
// silence, which is the failure mode that costs the most time to diagnose.
// Nothing here imports a page module: the island is parsed again, so the suites
// keep working when section 05 bundles the modules away.
export const BOOT = JSON.parse(document.getElementById("fw-boot").textContent);

// Async from day one: section 05 turns this into a fetch of BOOT.data[sheet].file.
export async function rows(sheet) {
  return BOOT.data[sheet].rows;
}
export const levels = () =>
  [...document.querySelectorAll("#levels button")].map(b => b.textContent);

const out = [];
let reported = false;

export function say(name, ok, detail) {
  out.push((ok ? "PASS " : "FAIL ") + name + (detail === undefined ? "" : "  " + String(detail)));
}
export const note = line => out.push("ok   " + line);
export const skip = (name, reason) => out.push("SKIP " + name + "  " + reason);

export function done() {
  if (reported) return;
  reported = true;
  const pre = document.createElement("pre");
  pre.id = "results";
  pre.textContent = out.join("\n");
  document.body.appendChild(pre);
}

window.addEventListener("error", e => { out.push("ERROR " + e.message); done(); });
window.addEventListener("unhandledrejection", e => {
  out.push("ERROR " + ((e.reason && e.reason.message) || e.reason)); done();
});

export const wait = ms => new Promise(resolve => setTimeout(resolve, ms));

// Returns dispatchEvent's result: false when the page called preventDefault.
export const key = (k, target) => (target || document.activeElement).dispatchEvent(
  new KeyboardEvent("keydown", { key: k, bubbles: true, cancelable: true }));
export const pt = (type, clientX, target) => target.dispatchEvent(
  new PointerEvent(type, { clientX, bubbles: true, cancelable: true, pointerId: 1 }));
// A synthetic click does not move focus; suites that assert focus return call
// el.focus() first (overlay.js records document.activeElement as the opener).
export const click = el => el.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));

export const chip = (hostId, text) =>
  [...document.querySelectorAll("#" + hostId + " button")].find(b => b.textContent === text);
export const lit = hostId =>
  [...document.querySelectorAll("#" + hostId + " button.active")].map(b => b.textContent);
export const shown = () => document.querySelectorAll("#body tr[data-code]").length;
export const params = () => new URLSearchParams(location.search);
```

## Appendix B: `tests/page/launch.js` in full

```js
// The opening view, the explainer panel, the URL the page writes, and the graph
// deep link. Every expected value comes from the boot payload or the DOM.
import { BOOT, rows as sheetRows, say, done, wait, key, click, chip, lit, shown, params } from "./lib.js";

const { ui: UI, footer: FOOTER, explainer: EXPLAINER, hiddenDefault: HIDDEN_DEFAULT } = BOOT;
const sheet = Object.keys(BOOT.data)[0];
const cols = BOOT.data[sheet].columns;
const rows = await sheetRows(sheet);
const col = name => cols.indexOf(name);
const richLinks = text => (String(text).match(/\]\(https?:\/\//g) || []).length;

// --- the opening view ---------------------------------------------------------
say("no query string on the opening view", location.search === "", location.search);
say("brand is the site name", document.getElementById("brand").textContent.startsWith(UI.title),
    document.getElementById("brand").textContent);
say("strapline is a public one", /^Updated \d{1,2} [A-Z][a-z]+ \d{4}  -  [\d,]+ charts$/
    .test(document.getElementById("src").textContent), document.getElementById("src").textContent);
say("Expert is the only lit level", JSON.stringify(lit("levels")) === '["Expert"]', lit("levels"));
say("Official is lit", JSON.stringify(lit("official")) === '["' + UI.official_chip + '"]', lit("official"));

const landing = r => r[col("Level")] === "Expert" && r[col("Official")] === true;
const wantShown = rows.filter(landing).length;
say("row count is Expert and Official", shown() === wantShown, shown() + " vs " + wantShown);
say("count text says so", document.getElementById("count").textContent ===
    UI.count.replace("{shown}", wantShown).replace("{total}", rows.length),
    document.getElementById("count").textContent);

const headCols = [...document.querySelectorAll("#head th")].map(th => th.dataset.c);
const hiddenShown = headCols.filter(c => HIDDEN_DEFAULT.includes(c));
say("default-hidden columns are hidden", hiddenShown.length === 0, hiddenShown);
say("Rank leads the table", headCols[0] === "Rank", headCols[0]);
say("D is sorted descending", document.querySelector('#head th[data-c="D"]').getAttribute("aria-sort")
    === "descending");

// --- footer ---------------------------------------------------------------------
const footLinks = [...document.querySelectorAll("#foot a")];
const docPages = (BOOT.docPages || ["about.html"]).length;   // 12 adds DOC_PAGES to the payload; until then about.html alone
const wantLinks = 1 + docPages + FOOTER.length + richLinks(UI.copyright) + 1;   // request link, document pages, FOOTER, copyright anchors, licence
say("footer link count", footLinks.length === wantLinks, footLinks.length + " vs " + wantLinks);
say("request link is the pack form", /issues\/new\?template=song-pack\.yml$/
    .test(document.querySelector("#foot a.req").href));
say("about link is same-site", document.querySelector('#foot a[href="about.html"]') !== null);
say("footer strapline mirrors the header", document.getElementById("src2").textContent ===
    document.getElementById("src").textContent);

// --- explainer panel ----------------------------------------------------------
const how = document.getElementById("how");
say("How it works is an underlined text link", /How it works/.test(how.textContent) &&
    getComputedStyle(how).textDecorationLine === "underline");
how.focus();                                       // the opener is whatever has focus at open time
click(how);
const about = document.getElementById("about");
say("panel opens as a dialog", about.classList.contains("on") && about.getAttribute("role") === "dialog");
say("panel takes focus", document.activeElement === about, document.activeElement.id);
say("one heading per explainer entry", about.querySelectorAll("h2").length === EXPLAINER.length,
    about.querySelectorAll("h2").length);
say("explainer text is the payload's", EXPLAINER.every(([h]) =>
    [...about.querySelectorAll("h2")].some(el => el.textContent === h)));
key("Escape");
say("Escape closes the panel", !about.classList.contains("on"));
say("focus returns to the opener", document.activeElement === how, document.activeElement.id);

// --- URL state ------------------------------------------------------------------
// A row that passes the filters asserted below, so the search shows at least it;
// the first word, because url.js trims q.
const seed = rows.find(landing);
const title = String(seed[col("Song Title")]).split(/\s+/)[0].toLowerCase();
const q = document.getElementById("q");
q.value = title;
q.dispatchEvent(new Event("input", { bubbles: true }));
click(chip("levels", "Hard"));
click(document.querySelector('#head th[data-c="NoteCount"] .lbl'));
await wait(400);                                   // writeUrl is debounced 250 ms
let p = params();
say("q is written", p.get("q") === title, p.get("q"));
say("levels are written", p.get("f.Level") === "Expert,Hard", p.get("f.Level"));
say("official is written", p.get("f.Official") === "true", p.get("f.Official"));
say("sort and direction are written", p.get("sort") === "NoteCount" && p.get("dir") === "desc",
    p.get("sort") + " " + p.get("dir"));
say("sheet is not written for the first sheet", p.get("sheet") === null);
const wantSearch = rows.filter(r =>
    ["Song Title", "Artist", "Charter", "Release", "Code"].some(n =>
      String(r[col(n)] ?? "").toLowerCase().includes(title)) &&
    ["Expert", "Hard"].includes(r[col("Level")]) && r[col("Official")] === true).length;
say("rows match the search", shown() === wantSearch && wantSearch > 0, shown() + " vs " + wantSearch);

// --- graph deep link ------------------------------------------------------------
const row = document.querySelector("#body tr[data-code]");
if (row) {
  row.focus();                                     // rows carry tabindex; the opener must hold focus
  click(row);
  await wait(400);
  const modal = document.getElementById("modal");
  say("row click opens the graph", modal.classList.contains("on"));
  say("graph is labelled by code", modal.getAttribute("aria-label").endsWith(": " + row.dataset.code),
      modal.getAttribute("aria-label"));
  say("code is in the URL", params().get("code") === row.dataset.code, params().get("code"));
  const rpt = modal.querySelector(".mhead a.rpt");
  say("report link names the chart", rpt && /template=rating\.yml/.test(rpt.href) &&
      rpt.href.includes(encodeURIComponent(row.dataset.code)), rpt && rpt.href);
  say("heading carries title, artist, level, part, charter",
      modal.querySelectorAll(".mhead > *").length >= 5, modal.querySelectorAll(".mhead > *").length);
  key("Escape");
  await wait(400);
  say("Escape closes and clears the code", !modal.classList.contains("on") && params().get("code") === null);
  say("focus returns to the row", document.activeElement === row, document.activeElement.tagName);
} else {
  say("a row exists to click", false, "no #body tr[data-code]");
}

done();
```

## Appendix C: `tests/page/frame.html` in full

```html
<!doctype html><meta charset="utf-8">
<title>frame</title>
<style>html,body{margin:0;background:#111}iframe{border:0;display:block}</style>
<iframe id="f" src="plain.html" style="width:390px;height:820px"></iframe>
<pre id="results">waiting</pre>
<script>
// Measured synchronously on the outer load event: timers and rAF in this
// document never produce output under --dump-dom, this does.
window.addEventListener("load", function () {
  const pre = document.getElementById("results");
  const out = [];
  const say = (name, ok, detail) => out.push((ok ? "PASS " : "FAIL ") + name + "  " + detail);
  const note = line => out.push("ok   " + line);
  try {
    const f = document.getElementById("f");
    const d = f.contentDocument, w = f.contentWindow;
    if (!d.querySelector("#body tr")) { pre.textContent = "FAIL iframe has no rows yet"; return; }
    say("layout viewport is 390 wide", w.innerWidth === 390, w.innerWidth + " x " + w.innerHeight);
    say("narrow rules are active", w.matchMedia("(max-width:640px)").matches, "");
    const tools = d.getElementById("tools");
    const scrollable = tools.scrollWidth > tools.clientWidth + 4;
    say("control strip fades while there is more", tools.classList.contains("more") === scrollable,
        tools.clientWidth + " of " + tools.scrollWidth + "px visible");
    tools.scrollLeft = tools.scrollWidth;
    tools.dispatchEvent(new Event("scroll"));
    say("fade clears at the far right", !tools.classList.contains("more"), "");
    // Measurements, not assertions: the fifth column (CalcTier) is off screen at
    // 390 px by design; CLAUDE.md's rule is only that D stays on screen.
    const ths = [...d.querySelectorAll("#head th")];
    ths.slice(0, 5).forEach(th => {
      const b = th.getBoundingClientRect();
      const on = b.left >= -1 && b.right <= w.innerWidth + 1;
      note("th " + th.dataset.c + " x " + Math.round(b.left) + " -> " + Math.round(b.right) +
           (on ? " on screen" : " OFF SCREEN"));
    });
    const dTh = ths.find(th => th.dataset.c === "D");
    say("D is on screen without a swipe", dTh && dTh.getBoundingClientRect().right <= w.innerWidth,
        dTh && Math.round(dTh.getBoundingClientRect().right));
    const head = d.querySelector(".fw-head").getBoundingClientRect().height;
    const foot = d.querySelector(".fw-foot").getBoundingClientRect().height;
    const pct = Math.round(100 * (head + foot) / w.innerHeight);
    say("chrome under 35% of the screen", pct < 35, "header " + Math.round(head) + "px, footer " +
        Math.round(foot) + "px, " + pct + "%");
  } catch (err) { out.push("ERROR " + err.message); }
  pre.textContent = out.join("\n");
});
</script>
```

`narrow.js` (Design 6) is the same body as a function `measure(d, w, say, note)`, called from an injected module after `const f = document.createElement("iframe"); f.src = "plain.html"; f.style.cssText = "width:390px;height:820px;border:0"; document.body.appendChild(f); await new Promise(r => f.onload = r); await wait(600);`, then `done()`.

## Appendix D: `tests/page/run.py`, the key code

```python
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))   # the repo root, for `import config`
import config

# One module tag, whatever it is called: static/js/main.js today, static/app.<hash8>.js after section 05.
ANCHOR = re.compile(r'<script type="module" src="static/[^"]+\.js"></script>')
RESULTS = re.compile(r'<pre id="results">(.*?)</pre>', re.S)
BAD = ("FAIL", "ERROR", "MISSING")
WSL_CHROME = "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe"
HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]


def find_chrome(explicit):
    for candidate in ([explicit] if explicit else []) + [os.environ.get("CHROME")]:
        if candidate and shutil.which(candidate):
            return shutil.which(candidate)
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
    for name in sorted(deploy.BUNDLE_TOP - {"index.html", "static", "data", "graph"}):   # every entry page, so 03 and 12 stage without a runner edit
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
        if opts.get("page"):
            shutil.copy(HERE / name, work / name)
            continue
        shutil.copy(HERE / name, work / name)
        page = src.replace(anchor, storage_script(opts.get("storage")) + anchor +
                           '\n<script type="module" src="' + name + '"></script>')
        (work / (pathlib.Path(name).stem + ".html")).write_text(page, encoding="utf-8")
    return "bootstrap.css" in src           # False means FALLBACK_CSS is inlined


def roundtrip_query(plain):
    island = re.search(r'<script type="application/json" id="fw-boot">(.*?)</script>',
                       plain.read_text(encoding="utf-8"), re.S).group(1)
    data = json.loads(island)["data"]
    sheet = list(data)[1]
    cols, rows = data[sheet]["columns"], data[sheet]["rows"]     # section 05: read data/<slug>.<hash>.json instead
    row = next(r for r in rows if r[cols.index("Level")] == "Hard")
    word = str(row[cols.index("Song Title")]).split()[0].lower()
    return "?" + urllib.parse.urlencode({"sheet": sheet, "q": word, "sort": "NoteCount",
                                         "dir": "asc", "f.Level": "Hard"})


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@contextlib.contextmanager
def served(work):
    port = free_port()
    proc = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1",
                             "--directory", str(work)],
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
        return tempfile.mkdtemp(prefix="fretwork-chrome-"), None
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


def main():
    args = parse_args()
    site = pathlib.Path(args.site or pathlib.Path(config.SITE_DIR) / (args.header or config.HEADER))
    chrome = find_chrome(args.chrome)
    suites = [s for s in SUITES if not args.suite or s[0] in args.suite]
    work = pathlib.Path(tempfile.mkdtemp(prefix="fretwork-page-"))
    profile, profile_local = make_profile(chrome)
    failed = 0
    try:
        has_bootstrap = stage(site, work, suites)
        if not has_bootstrap and not args.allow_fallback:
            sys.exit(f"{site} was published with --no-bootstrap; pass --allow-fallback to skip "
                     "the suites that measure Bootstrap")
        query = roundtrip_query(work / "plain.html")
        with served(work) as base:
            for name, opts in suites:
                if opts.get("needs_bootstrap") and not has_bootstrap:
                    print(f"{name}  SKIP  fallback CSS"); continue
                page = name if opts.get("page") else pathlib.Path(name).stem + ".html"
                url = f"{base}/{page}" + (query if opts.get("query") else "")
                for window in opts.get("windows", [opts.get("window", "1440,900")]):
                    lines = run_suite(chrome, url, args.budget, window, profile)
                    label = name if len(opts.get("windows", [])) < 2 else f"{name} @{window}"
                    failed += 0 if report(label, lines) else 1
    finally:
        if args.keep:
            print(f"staged copy kept at {work}")
        else:
            shutil.rmtree(work, ignore_errors=True)
        for d in (profile_local, profile if profile and not chrome.endswith(".exe") else None):
            if d:
                shutil.rmtree(d, ignore_errors=True)
    print(f"\n{len(suites)} suites, {failed} failed")
    sys.exit(1 if failed else 0)
```

## Appendix E: `tests/bin/aws` in full

```python
#!/usr/bin/env python3
# pipeline_test.py rewrites the line above to "#!" + sys.executable when it copies
# this file into <work>/bin, so the stub runs in the venv, never the system python.
"""A stand-in for the AWS CLI: records what deploy.py asked for, changes nothing.

Refuses to run without AWS_STUB_LOG so it can never be mistaken for the real
thing. Answers `s3api head-object` from a fixed table of what a correct upload
gives each extension; it never asks mimetypes, whose answer is the OS's.
"""
import os, shlex, sys

TYPES = {'.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css',
         '.svg': 'image/svg+xml', '.png': 'image/png', '.json': 'application/json',
         '.txt': 'text/plain'}

log = os.environ.get("AWS_STUB_LOG")
if not log:
    print("aws stub: AWS_STUB_LOG is not set", file=sys.stderr)
    sys.exit(2)
args = sys.argv[1:]
with open(log, "a", encoding="utf-8") as f:
    f.write(shlex.join(args) + "\n")
if args[:2] == ["s3api", "head-object"]:
    key = args[args.index("--key") + 1]
    print(TYPES.get(os.path.splitext(key)[1], "binary/octet-stream"))
```

## Appendix F: `.github/workflows/ci.yml` in full

```yaml
name: ci
# Both triggers: a branch with an open PR runs twice per push, accepted so a
# feature branch is checked before its PR exists.
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      # Into the runner's interpreter, not .venv/: the machine is disposable.
      - run: pip install -r requirements.txt

      # test_imports imports every top-level script and every module under
      # web/, functions/ and parsers/, and proves serve's startup path has no
      # matplotlib or openpyxl in it.
      - name: unit tests
        run: python -m unittest discover -s tests -t . -v

      # The page suites measure Bootstrap's colours and geometry, so the
      # pipeline publishes with the real stylesheet; publish would fetch it
      # itself, but fetching here keeps the network step visible and cached.
      - uses: actions/cache@v4
        with:
          path: caches/bootstrap-5.3.8.min.css
          key: bootstrap-5.3.8
      - name: bootstrap css
        run: |
          mkdir -p caches
          test -s caches/bootstrap-5.3.8.min.css || \
            curl -fsSL https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css \
              -o caches/bootstrap-5.3.8.min.css

      - name: pipeline
        run: python tests/pipeline_test.py --keep ci-work --bootstrap-css caches/bootstrap-5.3.8.min.css

      # ubuntu-latest ships Google Chrome stable as `google-chrome`. If that
      # ever changes, add `- uses: browser-actions/setup-chrome@v1` above this
      # step and set CHROME to its output path.
      - name: page suites
        env:
          CHROME: google-chrome
        run: python tests/page/run.py --site ci-work/site/Fixture
```

## Appendix G: running it locally (WSL, Windows Chrome)

```
source .venv/bin/activate
python -m unittest discover -s tests -t . -v
python tests/pipeline_test.py --keep /tmp/fw-ci --bootstrap-css caches/bootstrap-5.3.8.min.css
python tests/page/run.py --site /tmp/fw-ci/site/Fixture          # finds chrome.exe under /mnt/c
python tests/page/run.py --site site/Local --suite launch.js      # the real bundle, one suite
```

On Linux with a native Chrome the same commands work; set `CHROME=/path/to/chrome` if it is not one of the three names the runner tries. `--keep` on the runner prints the staged directory so a failing suite's page can be opened in a normal browser with `python -m http.server --directory <that dir>`.

## Appendix H: where the old suites are

The transcript is the Claude Code session log on the dev box that produced these maps (under `~/.claude/projects/`, session `6c7b982d`, one JSON object per line); it and is append-only, so the line numbers below (taken at 27,024,965 bytes and 6,869 lines; 27,877,627 bytes and 7,163 lines when re-checked) stay valid as it grows. Each cited line is an `assistant` message whose `tool_use` block carries a Bash command of the form `cat > $SP/uxtest/<file> <<'JS' ... JS`; the suite source is the heredoc body. To extract one: `sed -n '<line>p' <file> | python -c 'import sys,json; [print(b["input"]["command"]) for b in json.loads(sys.stdin.read())["message"]["content"] if b.get("type")=="tool_use"]'`. Later lines for the same file are later versions; take the last one, then re-derive every literal from the payload as Design 5 requires.

| Suite | Lines |
|---|---|
| `test.js` | 4596, 5414, 5645, 6147 |
| `order.js` | 4774, 4794, 4803, 5414 |
| `contrast.js` | 4851, 4891, 5253, 5760, 5801, 5868 |
| `keys.js` | 5070, 5075 |
| `launch.js` | 5615, 5631, 5801, 6045 |
| `roundtrip.js` | 5636, 5641 |
| `fade.js` | 5848, 5864 |
| `video.js` | 5950, 6034, 6045, 6147 |
| `links.js` | 6147, 6155 |
| `frame.html` | 5128, 5730 |
| column drag block (for `test.js`) | 3269 |

Lines 3381 to 4344 are a byte-identical replay of lines 46 to 1360 (a compaction re-injection) and hold nothing the table does not. If the file is ever gone, the assertion families under Verification are the specification and the suites are written fresh against them; nothing in them depends on the old text.
