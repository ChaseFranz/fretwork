# Tests

Everything here runs on a fresh clone with the venv and a Chrome binary; nothing is added to `requirements.txt`.

```
source .venv/bin/activate
python -m unittest discover -s tests -t . -v                                            # unit tests, under 5 s
python tests/pipeline_test.py --keep /tmp/fw-ci --bootstrap-css caches/bootstrap-5.3.8.min.css   # build, analyze, publish, deploy the fixture
python tests/page/run.py --site /tmp/fw-ci/site/Fixture                                  # the page suites in headless Chrome
python tests/page/run.py --site site/Local --suite launch.js                              # one suite against the real bundle
```

`.github/workflows/ci.yml` runs the same commands on every push and pull request.

## What is where

- `fixture.py` writes a synthetic 15-song library from a seeded generator: 13 charts the parsers accept, one `song.ini`-only folder, one truncated `notes.mid` so the errors path runs. Nothing in it is real, and it is never committed; `SONGS` is the table every count derives from.
- `pipeline_test.py` runs `build.py`, `analyze.py`, `publish.py` (twice: fallback CSS, then Bootstrap) and `deploy.py` (dry, then wet) as subprocesses from a temporary working directory, with `bin/aws` on `PATH`: a stub that records every call and answers `head-object` from a fixed table, so deploy's whole path runs without credentials.
- `page/run.py` stages a published bundle, injects one suite module after the page's module tag, serves the copy on a free port, launches Chrome once per suite with `--dump-dom`, and reads `<pre id="results">`. `page/lib.js` is the shared preamble; every suite's expectations come from the boot payload, so the same suites run against the fixture and the real library.
- `test_*.py` are stdlib `unittest` modules; `python -m unittest discover` needs the empty `__init__.py`.

## Chrome on WSL

There is no Linux Chrome on the dev box; the runner finds Windows Chrome at `/mnt/c/Program Files/Google/Chrome/Application/chrome.exe` and reaches the WSL server over `http://127.0.0.1:<port>`, which WSL2 forwards. Set `CHROME` to use another binary.

## Gotchas that cost time before, so nobody rediscovers them

- Headless Chrome floors its layout viewport at 500 px whatever `--window-size` says. A phone layout is measured inside a 390 px iframe (`page/narrow.js`), never from the window size. The spec's other sections call this measurement `frame.html`; `narrow.js` is that file. It won over an outer-page `frame.html` because an injected module can await the rows once section 05 loads them by fetch.
- A too-small `--virtual-time-budget` gives `NO RESULTS` and nothing else. The default is 60 s since the library reached 18,807 rows (30 s dropped `launch.js` on `site/Local` one run in three; virtual time is fast-forwarded when the page is idle, so the larger budget costs little real time). Chrome's first launch on a fresh profile now and then dumps the page before the module scripts have run, which reads the same way; `run_suite` retries a dump without the results block once, since a suite that ran always writes the block (`done()` or the error handlers).
- `graph.js` takes `?sheet=` to run on another family's sheet (Drums, Vocals); the legend, readout and alt text it expects come from `boot.curves` (labels.CURVE_FAMILIES) and the family the curve file names.
- `fragment.js` is launched with `#code=X` rather than `?code=X` (section 24): the runner appends the query string to the URL as given, so a fragment works the same way. The opening filters still apply to a fragment link as to a query one, so the asked row is on screen only when the chart passes them; the suite checks the pane's heading and the rewritten address instead.
- A `<script type="application/ld+json">` block is data, not a script that runs: a check that a document page runs one script (the theme's) counts `script` elements whose `type` is not `application/ld+json` (`about.js`), or `<script>` without a type (the pipeline test).
- `load.js` observes the loading state at module evaluation, so the runner delays `data/` for it; 600 ms was a race on a slow CI runner (one of two runs of the same commit saw the rows first), 2,000 ms is not.
- `--dump-dom` HTML-escapes the results block; the runner unescapes before matching. Never put `</pre>` in a detail string.
- Inject only into a pristine copy. The runner asserts the module tag appears once, the page holds exactly three `<script` tags (the theme script in the head, the island, the module tag), and no suite name is already in the source.
- The storage seed (`storage` in `SUITES`) is written right after `<head>`, before the theme script reads `fw.theme`; `plain.html` clears the store as it loads, so a suite that wants a stored theme in a fresh document loads `about.html` or `404.html` in an iframe, not `plain.html`.
- Headless Chrome reports the OS's `prefers-color-scheme` (light on CI, whatever Windows says on the dev box), so the page may open in either theme: no suite assumes one. `theme.js` seeds `fw.theme=light`; `contrast.js` audits both, toggling between; the others compare computed colours to the tokens.
- Under `--virtual-time-budget`, CSS transitions do not advance while timers do: a colour read after a theme switch was still the old one on every `.btn`. The page switches with transitions off (`html.theming`), which is also why a switch does not fade piecemeal.
- A synthetic `click()` does not move focus. Suites that assert focus return call `el.focus()` first; the page records `document.activeElement` as the opener.
- The details pane (section 14) opens with focus still on the row and the arrow keys move the chart, debounced 160 ms: a suite that presses an arrow with the pane open waits 400 ms before reading the pane's `aria-label`. The pane's height is remembered in `fw.pane`; `pane.js` removes it after the drag checks so the next suite starts on the stylesheet's height.
- Turning off the only lit Level chip lights all four. Toggle a chip that can go dark.
- Official is on at launch and tri-state; a URL without `f.Official` lights neither chip.
- The raw `[text](url)` markup legitimately lives in the `#fw-boot` island; `links.js` scans rendered regions only.
- The cross-origin YouTube `contentWindow` cannot be assigned; `video.js` shadows the getter with `Object.defineProperty`.
- Injected pages are staged as `suite-<name>.html` so a suite called `about.js` cannot overwrite `about.html`.
- Windows Chrome cannot write to a WSL path, so the profile directory it is given is a Windows path asked of `cmd.exe`.
- The table's DOM is a window of the view (section 17): `#body tr[data-code]` is the painted rows, not every passing row. On the fixture the sheets are small enough to paint whole, so the existing suites hold; on `site/Local` only `window.js` asserts about rows beyond the window, and a new suite that needs every row reads `sheetRows()` and `#count`. A programmatic scroll delivers no scroll event under the virtual clock: dispatch one (`window.js`, `fade.js`).
- `share.js` replaces `navigator.clipboard` with a capturing stub: headless Chrome grants no clipboard permission, and the page's fallback (`execCommand`) copies nothing a suite can read.
- The pipeline test refuses a `--keep` directory whose `caches/` or `metrics/` is not empty: output names are minute-resolution and would collide.
- `config.DIFF_WRITE_MODE` must be `None`: the two write modes touch `song.ini` files and `Restore` writes no spreadsheet.
