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
- A too-small `--virtual-time-budget` gives `NO RESULTS` and nothing else. 30 s covers the 11,904-row library.
- `--dump-dom` HTML-escapes the results block; the runner unescapes before matching. Never put `</pre>` in a detail string.
- Inject only into a pristine copy. The runner asserts the module tag appears once, the page holds exactly two `<script` tags, and no suite name is already in the source.
- A synthetic `click()` does not move focus. Suites that assert focus return call `el.focus()` first; the page records `document.activeElement` as the opener.
- Turning off the only lit Level chip lights all four. Toggle a chip that can go dark.
- Official is on at launch and tri-state; a URL without `f.Official` lights neither chip.
- The raw `[text](url)` markup legitimately lives in the `#fw-boot` island; `links.js` scans rendered regions only.
- The cross-origin YouTube `contentWindow` cannot be assigned; `video.js` shadows the getter with `Object.defineProperty`.
- Injected pages are staged as `suite-<name>.html` so a suite called `about.js` cannot overwrite `about.html`.
- Windows Chrome cannot write to a WSL path, so the profile directory it is given is a Windows path asked of `cmd.exe`.
- The pipeline test refuses a `--keep` directory whose `caches/` or `metrics/` is not empty: output names are minute-resolution and would collide.
- `config.DIFF_WRITE_MODE` must be `None`: the two write modes touch `song.ini` files and `Restore` writes no spreadsheet.
