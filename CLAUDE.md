# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Fretwork computes difficulty scores for 5-fret rhythm-game charts (Guitar/Co-op/Rhythm/Bass/Keys at Easy/Medium/Hard/Expert) from `song.ini` + `notes.chart` / `notes.mid` files. The formula and calibration are documented in `Methodology.md`; user-facing usage is in `README.md`. Read those before changing metrics or calibration constants.

## Commands

Plain Python 3 scripts, no packaging config, no test suite, no linter. Always work inside the project virtualenv at `.venv/` (gitignored); never install into or run against the system interpreter.

```
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

If `python3 -m venv` fails with an ensurepip error (Debian/Ubuntu and WSL without `python3-venv`), use `uv` instead; it needs no system packages and is what created the venv on the WSL dev box:

```
uv venv .venv
uv pip install --python .venv/bin/python -r requirements.txt
```

A uv-created venv has no `pip` inside it, so add packages with `uv pip install --python .venv/bin/python <pkg>`. Either way, run the scripts with the venv active or as `.venv/bin/python build.py`.

The three entry points run in order and are glued together by `config.HEADER` (see Architecture):

```
python build.py [--search-path DIR] [--header NAME]
python analyze.py [--header NAME] [--cache FILE.pkl] [--diff-mode CalcTier|RemapDiff|Restore] [--xlsx-levels X|EX|EMHX|ALL]
python render.py CODE [CODE ...] [--codes-file FILE] [--header NAME] [--cache FILE.pkl] [--out-dir DIR]
```

`serve.py` is an optional fourth entry point that browses an existing metrics `.xlsx` in a browser instead of Excel. Clicking a row renders that chart's graph on demand; columns have Excel-style filter dropdowns, can be hidden individually, dragged into any order in the column chooser, and resized by dragging the right edge of a header. All three preferences are remembered per browser in `localStorage` (`fw.hidden`, `fw.order`, `fw.widths`) and "Reset columns" clears all three. It reads the spreadsheet, not the cache, so `analyze.py` must have run first; the cache is loaded lazily only when a graph is clicked. A synthetic `Rank` column leads the table, numbering rows in the current view; it has no slot in the row arrays, so `state.visible()` pairs it with index -1. Long titles wrap rather than truncate, and a footer carries attribution and the licence. The level chips are a multi-select shortcut into the `Level` filter: a lit chip is a level on screen, so with no filter all four are lit, and clicking one adds or removes just that level. The Official/Custom pair beside them stays single-select, since its two values are complements and lighting both would mean the same thing as lighting neither. Stdlib `http.server` plus pandas, binds `127.0.0.1` only, nothing added to `requirements.txt`:

```
python serve.py [--header NAME] [--xlsx FILE.xlsx] [--cache FILE.pkl] [--port 8000] [--no-bootstrap]
```

`publish.py` is the fifth entry point: the same page, written to `SITE_DIR/<header>/` as a static site (`index.html` with the data baked in, the assets, Bootstrap, and every chart pre-rendered to `graph/<code>.png`) so it can be hosted with no server-side code. The page's URLs are relative, so the bundle works at a domain root or under a sub-path. Re-publishing is incremental: files are rewritten only when their bytes change (so `aws s3 sync` uploads only what moved), and `graph/manifest.json` holds a fingerprint of each chart's render inputs - notes, Expert anchor, the difficulty numbers the header prints, metadata, `source_format`, the curve constants and the render theme - so unchanged charts skip the render. Safety rules in `web/bundle.py`: a chart that cannot be rendered keeps its previous PNG, only graphs a previous publish recorded are ever pruned, nothing is pruned when no code resolves (a cache/xlsx mismatch), and the manifest is saved every 200 charts so an interrupted run keeps its work. `--force` re-renders everything, which a change to `functions/plot.py` or a matplotlib upgrade requires since the fingerprint cannot see code. Measured at ~0.12 s per chart. `site/` is gitignored:

```
python publish.py [--header NAME] [--xlsx FILE.xlsx] [--cache FILE.pkl] [--out-dir DIR] [--no-bootstrap] [--force]
```

The full rescan-to-published sequence, as numbered steps with the checks worth
making at each one, is section 7 of `README.md`; keep it in step with these
scripts when their flags change.

`deploy.py` ends every real run by asking S3 what Content-Type it will serve for
one object of each kind, and exits non-zero if any is wrong. That check exists
because `aws s3 cp --metadata-directive REPLACE` (what `--set-headers` uses)
replaces *all* metadata and does **not** re-derive the content type the way an
upload does - so a headers pass that does not name `--content-type` writes
`binary/octet-stream` over every object, and the browser then refuses to run the
page's ES modules. The bucket looks fine from the AWS side when this happens.

`deploy.py` is the sixth entry point and the only one that talks to AWS: it calls `publish()` and then shells out to the AWS CLI (`aws s3 sync ... --delete`, then a CloudFront invalidation of `/*`). No boto3, nothing added to `requirements.txt`. Settings come from a gitignored `.env` in the repo root read by `functions/envfile.py` (a ten-line KEY=VALUE reader; `.env.example` is committed). Only `FRETWORK_*` keys and `AWS_PROFILE`/`AWS_REGION`/`AWS_DEFAULT_REGION` are read (the `.env` value overrides the shell for those); **credentials never go in `.env`** and a file containing any is refused - the AWS CLI's own profile/SSO chain supplies them. Because the sync uses `--delete`, two guards protect the bucket: the site folder may hold only the four things publish writes (`index.html`, `bootstrap.css`, `static/`, `graph/`), so `FRETWORK_SITE_DIR=.` is refused instead of uploading the repo, and it must contain a publish output before anything is sent. `--dry-run` publishes nothing and sends nothing:

```
python deploy.py [--env FILE] [--no-publish] [--dry-run]
```

Bootstrap 5.3 supplies the base CSS. It is downloaded once into `CACHE_DIR` as `bootstrap-<version>.min.css` (gitignored with the rest of `caches/`) and served same-origin from `/bootstrap.css`, so the page never contacts a CDN at view time and works offline after the first run. If the fetch fails or `--no-bootstrap` is passed, the page inlines `FALLBACK_CSS` instead, which covers layout plus the `d-none` / `dropdown-menu.show` state classes the page's JS toggles. There is no JS framework and no Bootstrap JS; interaction is plain DOM code that toggles Bootstrap's own classes.

### The public site is `fretladder`

The hosted site is named *fretladder* (`config.SITE_NAME`, `SITE_URL`); the engine and
this repo stay *fretwork*, and the footer credits it. `page.build(..., public=True)` is
the only difference between what serve shows and what publish writes: a published page
names no internal file (the title is just the site name and the strapline is
"Updated 7 September 2026 - 4,634 charts", read back from the spreadsheet's own
timestamp), and it emits Open Graph / Twitter tags, which need `SITE_URL` because a
social preview cannot use a relative image. `page.OG_IMAGE` picks the chart that serves
as that preview.

The footer is assembled in `static/js/main.js` from `labels.FOOTER_LINKS` plus the
`copyright` / `license_label` / `license_url` strings in `UI`. **The fork is MIT and its
`LICENSE` is byte-identical to upstream's, so the copyright line names Staycation, not
this fork** - MIT requires the original notice survive. Check upstream's `LICENSE` before
touching either.

Anything that scrolls sideways - the control strip on a phone, the table itself
whenever it is wider than the window - fades its right edge while there is more
past it, and clears the fade at the end (`static/js/scroll.js`, one `.more`
class, one CSS mask). It is a mask on the scroller rather than an element laid
over the rows, which was checked against the sticky header: masking the scroll
container does not detach it.

Three details of the table are easy to undo by accident. Column widths are
applied as a single generated stylesheet in `static/js/widths.js`, keyed by
`:nth-child`, not as styles on the cells: the table is thousands of rows, and
nth-child follows the visible column order with no bookkeeping. A width pins
`width`, `min-width` and `max-width` together, because in an auto-layout table a
width alone is only a hint and a `max-width` can cap a column but never widen
one. Decimal places are decided per column rather than per value (`format.js`),
so a `D` that lands on exactly 700 still prints 700.00 and the decimal points
stay in a line. And the narrow-screen rules exist to keep `D` on screen without a
sideways swipe - `td.artist`'s cap and the wrapping header labels are load-bearing
for that, not cosmetic; re-measure at 390px after changing any column's width.

The table carries no conditional-formatting fill. `D` is set in semibold
(`td.headline` - not `.lead`, which is a Bootstrap utility at 1.25rem) and the
level badges are outlines in the four colours `xlsx_format.py` uses, so the site
and the spreadsheet still agree on which colour means which level. The green-to-
red ramp that `scale.js` drew was deleted along with the module: the table is
almost always sorted by `D`, so it was colouring a ranking the row order already
gives.

The palette is two magentas and one grey, and the split is deliberate.
`--fw-accent` (`#b71fb7`) is a **fill**: white on it is 5.4:1, but as text on the
dark page it is 2.9:1, so everything the accent colours as text or as an icon
uses `--fw-accent-text` (`#e879e8`) instead. `--fw-dim` (`#9ba3ab`) replaces
Bootstrap's `#6c757d`, which its `.text-secondary` utility and its outline
buttons hardcode in both themes at 3.3:1 here. Bootstrap's button colours are
baked into the compiled CSS rather than read from `--bs-primary`, so the button
overrides set `--bs-btn-*` per variant; setting `--bs-primary` alone leaves them
blue. Everything the page renders as text now measures 5.2:1 or better against
its own background - keep it there: AA wants 4.5:1 for text and 3:1 for anything
clickable. The one palette to leave alone is the D/tier colour ramp in
`static/js/scale.js`, which mirrors the spreadsheet's own scale and is 11.8:1 at
its worst point.

### `web/` is the viewer, and only the viewer

Root `serve.py` and `publish.py` are thin entry points in the same shape as the other three: docstring, one orchestration function, `main()`. They share everything below; publish writes what serve serves. Everything else lives in `web/`, a namespace package (no `__init__.py`, matching `functions/` and `parsers/`). It is named `web/` rather than `serve/` because a `serve/` directory beside `serve.py` loses to the module in Python's import resolution and would be silently unimportable.

| Module | Responsibility |
|---|---|
| `web/frames.py` | Reads the metrics `.xlsx` into JSON-safe rows, and lists its codes. The only pandas importer. |
| `web/boot.py` | Builds the JSON payload the page reads, and escapes `</` in it. |
| `web/page.py` | `build()` composes a header's page; substitutes `index.html`'s placeholders in one regex pass. |
| `web/bootstrap.py` | Bootstrap fetch/cache plus `FALLBACK_CSS`, its own fallback branch. |
| `web/assets.py` | Locates `static/` relative to `__file__` and loads it at startup. |
| `web/graph.py` | `GraphRenderer`: lazy cache load, `lookup`/`render` per code, memoised `png` for serve. |
| `web/bundle.py` | Publish only: write-if-changed, the render-input manifest, and the never-delete-what-we-did-not-write rules. |
| `web/handler.py` | `MetricsHandler`: routing and response writing only. |
| `web/server.py` | `MetricsServer`: carries the handler's dependencies. |
| `web/banner.py` | The terminal output: serve's startup/shutdown, publish's summary. |

The page's markup, CSS and 17 ES modules live under `web/static/`, served from an in-memory dict built by globbing at startup. Keys never derive from a request path, so traversal is impossible by construction rather than by guard. Server data reaches the JS through a `<script type="application/json" id="fw-boot">` island that `boot.js` parses once and re-exports; `boot.py` escapes `</` so spreadsheet text can never close the tag. All mutable page state lives in one exported `state` object because ES module imports are read-only bindings.

Two things must stay off the server's startup import path: matplotlib (via `functions/plot.py`) and openpyxl (via `functions/xlsx_format.py`). `GraphRenderer` imports plot inside its method bodies, and `web/boot.py` keeps a local copy of `SCALED_COLS` rather than importing `xlsx_format` for it.

Before running Build, `config.SEARCH_PATH` must point at a real song library (the committed value is a Windows placeholder). Build on a ~3k-song library takes several minutes; midi parsing dominates.

`--diff-mode CalcTier|RemapDiff` and `config.DIFF_WRITE_MODE` **write to the user's `song.ini` files**. `Restore` rewrites them from the backup CSV and skips analysis entirely. Treat these as destructive to user data.

There are no automated tests. To sanity-check a change to parsing or metrics, build, analyze, and inspect the terminal summary / xlsx / error CSV against a small local library. The convention is a gitignored `songs/` folder at the repo root holding a handful of song folders copied from a real library (song folders contain copyrighted audio and must never be committed):

```
python build.py --search-path songs --header Local
python analyze.py --header Local
```

## Architecture

### Three-stage pipeline keyed by HEADER + timestamp

`build.py` -> cache `.pkl` -> `analyze.py` -> metrics `.xlsx`; `render.py` reads the same cache to draw PNGs. Every output is named `{header}_{kind}_{timestamp}.{ext}` via `functions/timestamp.py`, and `config.KIND_DIRS` routes each kind to a folder (`caches/` for cache, errors CSV, and backup; `metrics/` for xlsx; `renders/` for PNG). Analyze and Render locate the *newest* cache for a header by parsing the timestamp out of the filename (`timestamp.latest_output`), so filename format is load-bearing. Analyze reuses the cache's timestamp for its xlsx so the pair can be matched.

All of these outputs are gitignored (`*.pkl`, `*.csv`, `*.xlsx`, `*.png`, `caches/`). The `.xlsx` and `.png` files under `metrics/` and `renders/` are committed examples that were force-added; don't expect new outputs to show up in `git status`.

### The cache is the data contract

The pickled cache shape is documented at the top of `functions/cache.py`. Everything downstream (analyze, render, curves, density) consumes `notes = {'time_ms': ndarray, 'lanes': ndarray uint8}` plus `spans = {'star_power': [(ms, ms)], 'solo': [...]}` per (song, instrument, level). Both parsers must emit exactly that shape.

**Lane encoding**: one `uint8` bitmask per note timestamp. Bits 0-4 are GRBYO frets, bit 7 is open. Bits 5-6 are reserved (chart tap/force modifiers) and unused. Strum/HOPO/tap state is deliberately discarded by both parsers.

**Retrieval codes** (`04821993XG`): 8 digits from a SHA1 of the resolved song folder path (with linear probing on collision), then a level letter (E/M/H/X) and an instrument letter (G/C/R/B/K). Assigned in `cache.assign_codes` at build time and stored in `cache['codes']`. Render accepts codes without leading zeros.

### Parsers (`parsers/`)

Build runs them in a fixed order for a reason: `ini_parser` first, because `multiplier_note`/`star_power_note` from `song.ini` tells `mid_parser` whether MIDI pitch 103 means star power (legacy) or solo. Then `mid_parser`, then `chart_parser`. When a song folder has both formats, **chart wins** (`build.build_note_index`).

- `parsers/timing.py` holds the shared tempo-map and tick-to-ms conversion used by both formats. Use `ticks_to_ms` (vectorized) for note arrays and `tick_to_ms` for the handful of span endpoints.
- `.chart` distinguishes level by section-name prefix (`ExpertSingle`, `HardDoubleBass`); `.mid` distinguishes level by pitch block within one track per instrument (`instruments.MID_PITCH_BASE`). Star power and solos are per-section in `.chart` but track-wide (shared across levels) in `.mid`.
- Songs that fail to parse are appended to an `errors` list as `(path, ErrorType, message)` and written to the errors CSV; a single bad file never aborts a build. Non-fatal data loss (unclosed solos, malformed SP, unknown-channel legacy opens) is tallied in `dropped` counters instead.

### `functions/instruments.py` is the single source of truth

Every instrument/level table lives there: canonical keys and iteration order, `.mid` track names, `.chart` section names (with legacy fallbacks), pitch bases, `song.ini` `diff_*` tags, code suffixes, open-note support, xlsx sheet grouping, and display labels. Adding an instrument means adding it here and adding a calibration group in `functions/formula.py`; nothing else should hardcode instrument names.

### `functions/difficulty.py` holds the shared difficulty block

`entry_difficulty(entry)` computes D/N/V/COV for the entry's own level plus the Expert-anchored `RemapDiff`/`CalcTier`. `render.py` and `web/graph.py` both call it; it was duplicated verbatim between them before.

### `functions/labels.py` holds every human-facing string

The abbreviated keys (`pNPS`, `medVPS`, `COV`, `DurationS`) are the data contract: they come out of `density.calc_metrics` and `formula.calc_nvcov`, flow through the dataframes in `analyze.py`, and become the xlsx headers. Nothing keyed off a column name should change. `labels.py` maps those keys to readable text at display time only, via `COLUMN_LABELS`, `COLUMN_HELP` (tooltips), `TIME_COLUMNS` (seconds shown as m:ss), `DISPLAY_ORDER` (left-to-right column order on the page, which is deliberately not `analyze.COLUMN_ORDER`, so the site can lead with `D` without touching the spreadsheet), `DEFAULT_HIDDEN` (the columns a first visit does not show; search still looks inside a hidden column, and a filter set on one still applies, so hiding is display-only), `VALUE_ORDER` (columns whose values are neither numeric nor alphabetical - `Level` and `Type`, both derived from `instruments.py` rather than respelled, and used for the filter list and the column's sort alike), `VALUE_LABELS` (display text for a stored value, currently Official/Custom for the `Official` booleans; the filter still matches the stored key), `FOOTER_LINKS` (the attribution links), and `UI` (interface wording, including the copyright and licence lines). `label()` falls back to the raw key, so a new metric column degrades gracefully instead of raising.

`serve.py` and `publish.py` consume it through `web/boot.py`; the pipeline itself does not. The xlsx headers and the render header are deliberately still raw keys, since changing them would alter committed example outputs and anything downstream that reads the spreadsheet by column name. Wiring either one up is a display-layer change through this module, not a rename in the pipeline.

### Metrics pipeline (`functions/density.py` -> `functions/formula.py`)

`density.window_arrays` slides a 1000 ms window in 250 ms steps from t=0 to the last note and produces raw NPS (note timestamps per window) and VPS (fret-change per window; see `fret_var`) samples. `calc_metrics` reduces those to peak/avg/median/std. `formula.calc_nvcov` turns them into `D = N * V * COV` and is instrument-agnostic.

**Expert anchoring**: `D` is computed per level, but `RemapDiff` (0-6 bins, per calibration group) and `CalcTier` (uncapped log tier) are computed once per (song, instrument) from the **Expert** level's D via `formula.anchor_remap_tier`, and that pair is shown on every E/M/H/X row. If an instrument has no Expert chart, both are `None`/NaN. This is because `song.ini` only has one `diff_*` tag per instrument. Guitar, Co-op, and Rhythm share the `guitar` calibration group.

The bin edges and CalcTier constants in `formula.py` are mirrored as tables in `Methodology.md`; update both together.

### Render path (`functions/curves.py` -> `functions/plot.py`)

Render recomputes from the cache rather than reading stored metrics. `curves.calc_curves` reuses `density.window_arrays`, converts to rates, and applies a zero-phase EMA (`TAU_MS = 2000`). The plotted "D" line is `sqrt(nps * vps)`, an approximation for display that omits COV, while the header's `D` value comes from the real formula. Appearance comes entirely from `config.RENDER_DEFAULT` + `config.RENDER_THEMES`; `plot.py` uses the Agg backend and never opens a window.

### `song.ini` backup and write-back (`functions/ini_updater.py`)

Build **always** appends new songs to `caches/{header}_BackupData.csv` (append-only, deduplicated by `song_path`, one column per `diff_*` tag) regardless of config. It never writes to `song.ini`. Analyze's write modes and Restore both go through `update_ini_values`, which patches matching `key = value` lines inside the `[song]` section in place, appends missing keys at the end of the section, and preserves the file's original encoding (utf-8 / utf-8-sig / utf-16 / cp1252) and newline style. Don't replace it with `configparser`; `song.ini` files routinely contain `%` and other characters that break it, which is also why `ini_parser.parse_ini` is hand-rolled.

## Conventions worth knowing

- `config.py` is user-edited configuration (paths, header, theme), not library code. The committed `SEARCH_PATH`/`HEADER` values are placeholders. `instrument_scan.py` is gitignored local scratch.
- `Difficulty` of `'-1'` (string in cache, int in xlsx) is the sentinel for "no `diff_*` tag in song.ini". `xlsx_format.BLANK_PREDICATES` keeps sentinels out of the color scales.
- `analyze.COLUMN_ORDER` defines xlsx column order; `xlsx_format.DEFAULT_HIDDEN_COLS` lists the diagnostic columns that are dropped unless `config.EXTRA_METRICS` is True. Excel sheet names are truncated to 31 chars.
- Song identity everywhere is the resolved absolute folder path (`song_path`), which is also the join key between the ini table, note streams, backup CSV, and codes.
- Terminal progress uses `tqdm`; keep long loops wrapped so multi-minute builds stay observable.

## Working with the repo

This is a fork. `origin` is `github.com/ChaseFranz/fretwork`, the main line for the
web viewer and, on its own branch, the player rating. `upstream` is
`github.com/Staycation44/fretwork`, the original project (single maintainer, no CI,
no branch protection), and the source of parser, instrument and difficulty-formula
improvements. The viewer was offered upstream as PR #6 and closed unmerged on
2026-09-07; it is this fork's project now.

- **`main` on the fork is `upstream/main` plus the viewer.** Feature work branches
  from `main`, is named for the feature (`rank-column`), and merges back with a merge
  commit (`git merge --no-ff`). Delete the branch after it lands.
- **Pulling upstream changes:** `git fetch upstream && git checkout main && git merge
  upstream/main`, then `git push origin main`. Conflicts should only appear in files
  both sides touch (`README.md`, `.gitignore`, `CLAUDE.md`); `serve.py` and `web/`
  do not exist upstream. Never rebase onto upstream - history is merge-only here, as
  it is upstream. `upstream/cleanup` is the maintainer's unmerged work and was copied
  to the fork at fork time; leave it alone and take it via `upstream/main` when it
  lands there.
- **Song pack requests come in as issues** on the fork, through the form in
  `.github/ISSUE_TEMPLATE/song-pack.yml` (labelled `song pack`), which the site's
  footer links to. The form asks for a link to where a pack is already published
  and refuses attachments: no audio or chart files are ever accepted through it,
  which is the same rule the hosting design runs on.
- **Never open pull requests against `upstream` for viewer, scores or rating work.**
  A genuine fix to the shared tooling (parsers, formula) can still go upstream as a
  fork PR, from a branch cut off `upstream/main` rather than off `main`.
- **`elo` is the rating branch**, secondary to the viewer: `ScoreData.md` and
  `SkillRating.md` so far. Merge `main` into it periodically; it merges to `main`
  only when there is code worth shipping. The rating never touches `web/`.
- **Merge commits only, short informal one-line messages**, matching upstream.
  Example outputs under `metrics/` and `renders/` are force-added; if you regenerate
  them, `git add -f` the new files and remove the stale ones in the same commit.
  Never commit caches, backup CSVs, `songs/`, or a real library's metrics.
- **No tests, no CI.** After merging parser or metrics changes from upstream, run
  build, analyze and render against `songs/` and compare the terminal summary and
  error CSV with the previous run, since nothing else will catch a regression.
