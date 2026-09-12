# Fretwork - 5-Fret Difficulty Analyzer <!-- omit in toc -->

Fretwork is an analysis tool to calculate difficulty values across Easy/Medium/Hard/Expert for Guitar/Bass/Keys from notes.chart & notes.mid files (Guitar Hero, Rock Band, Clone Hero, YARG) using Notes Per Second (note density) & Variability Per Second (fret change) metrics.

[Explainer video with some historical context](https://youtu.be/emoWMpDJ4ls)

Libraries required: **pandas, numpy, tqdm, mido, matplotlib, and openpyxl** 

![Render Example](https://github.com/Staycation44/fretwork/blob/main/renders/02139802G_Guitar_Dragonforce%20-%20Through%20The%20Fire%20Flames.png)

## Using Fretwork <!-- omit in toc -->
To use the tool setup **config** and run these in order:

1. **Build** - Scan a library, save everything into a cache file, & creates a backup of original difficulties
2. **Analyze** - Turn Build's cache into an .xlsx spreadsheet including song metadata and calculated metrics for every song/instrument combo. 
Optionally, applies calculated difficulty to `song.ini` files for use in-game, or restores them back to their originals from the backup
3. **Render** - Output a PNG graph of metrics over time for one or more song/instrument combos based on a retrieval code from the spreadsheet
4. **Serve** *(optional)* - Browse the spreadsheet in a browser instead of Excel, with per-column filters and a details pane for the chart under the cursor
5. **Publish** *(optional)* - Write the viewer as a static site to host anywhere
6. **Deploy** *(optional)* - Push that site to S3 and refresh the CDN in front of it

Python 3.11 or newer (the pack registry is read with the standard library's `tomllib`). In a hurry? [7. Updating the live site, start to finish](#7-updating-the-live-site-start-to-finish) is the whole rescan-to-published sequence as numbered steps.

## Index <!-- omit in toc -->
- [1. Setup your Config](#1-setup-your-config)
- [2. Building a cache](#2-building-a-cache)
- [3. Analyzing a cache](#3-analyzing-a-cache)
- [4. Rendering song graphs](#4-rendering-song-graphs)
- [5. Browsing in a browser](#5-browsing-in-a-browser)
- [6. Publishing a static site](#6-publishing-a-static-site)
- [7. Updating the live site, start to finish](#7-updating-the-live-site-start-to-finish)
- [8. Fixes/Extension Ideas](#8-fixesextension-ideas)
- [9. Tests](#9-tests)
- [License](#license)

---

## 1. Setup your Config

Before running anything, open `config.py` and check these values:

| Setting | What it does | Example |
|---|---|---|
| `SEARCH_PATH` | Sets the folder to cache/analyze | `r"C:\Users\[user]\Documents\Clone Hero\Songs"` |
| `HEADER` | A short name for the library, becomes the prefix on every output file | `"Library"` |
| `DIFF_WRITE_MODE` | Change from None to allow Analyze to write/restore your `song.ini` files | `"CalcTier"` |

`SEARCH_PATH` - this tool has only been tested on windows devices, but should work on Mac/Linux with OS-correct file paths.

`HEADER` is how Build defines a cache of song data, and how Analyze & Render search that cache. If you keep multiple libraries, give each one its own `HEADER`.

All outputs are named: `{header}_{kind}_{timestamp}.{ext}`

ex. `Library_cache_08052026-0330.pkl`, `Library_metrics_08052026-0330.xlsx`.

**Render appearance settings**

Under `RENDER_DEFAULT` and `RENDER_THEMES`, you can tweak how `render.py's` PNGs look:

- `mode`: `"dark"` or `"light"` to set overall color theme
- adjust hex value colors

---

## 2. Building a cache

`build.py` walks `SEARCH_PATH`, finds every `song.ini`, `notes.chart`, and `notes.mid`, reads them, and writes one cache file containing every song's note timing and metadata. Note state (strum/hopo/tap), note length, and star power/solo phrases are not parsed. Every level (Easy/Medium/Hard/Expert) charted for each instrument is cached. Currently caches drum notes, but doesn't do anything with them downstream in Analyze/Render.

By default this will run on the `SEARCH_PATH` & `HEADER` set in the config.

Additionally, this always backs up your original difficulties as it scans - Build never writes to `song.ini` itself, it only records what's there so Analyze can restore it later if you want to.

**Outputs:**

- A `{header}_cache_{timestamp}.pkl` file, the main output used by Analyze and Render
- A `{header}_errors_{timestamp}.csv` file, only generated if some songs failed to parse, this lists which file failed and why (e.g. missing guitar track, corrupt midi file)
- A `{header}_BackupData.csv` file, which is a back up that stores all difficulties that were found at the time of building

Cache, errors, and backup all land in `caches/`; the metrics spreadsheet lands in `metrics/`. Both are set in `OUTPUT_DIRS` in `config.py`.

**Optional arguments:**
- `--search-path`: scan a different folder than the one in `config.py`
- `--header`: name this run something other than `config.header`

---

## 3. Analyzing a cache

`analyze.py` loads the most recent cache for your config's `HEADER`, computes difficulty metrics for every song/instrument/selected level combo, and writes a **.xlsx spreadsheet**. This is the main output for browsing the library.

Optionally, `analyze.py` can also update each instrument's `song.ini` `diff_*` tag for use in-game. You can also restore all of them to the original assigned value. This option runs via args or `DIFF_WRITE_MODE` in the config.

**Outputs:**

An .xlsx spreadsheet named `{header}_metrics_{timestamp}.xlsx` with:
- One tab per instrument group that has data in the cache (`Guitar` - combining Guitar/Co-op/Rhythm, `Bass`, `Keys`). Easy/Medium/Hard/Expert share the same tab in the `Level` column
- **Retrieval codes** - an 8-digit song hash plus a level letter (`E`/`M`/`H`/`X`) and an instrument letter (`G`/`C`/`R`/`B`/`K`), e.g. `04821993XG` for an Expert Guitar song - used to render graphs
- Metadata: Song Title, Artist, Level, Type (Lead/Co-op/Rhythm/Bass/Keys), Charter, Release/Source, Album, Year, Genre, Difficulty (song.ini diff tags). Year is the four-digit year found in the `year` tag, `-1` when it holds none
- The difficulty metrics & updated Remap/CalcTier numbers
- Two hidden identity columns: `SongKey`, one hash over every chart in the song, and `NotesHash`, a 12-hex hash of one chart's notes. Two folders carrying the same chart share a `NotesHash` whatever they are called; the analyze summary's `Distinct charts` line counts (part, level, hash) once, and a `COUNTIFS` over those three columns is the spreadsheet's own copies count

Each tab is formatted for browsing using `xlsx_format.py`

Using `XLSX_LEVELS` in the config you can adjust the mix of Easy/Medium/Hard/Expert you want in the sheet.

The raw NPS/VPS details and N/V/COV formula components are dropped, but they can be included as hidden columns by using `EXTRA_METRICS = True` in the config for diagnostics/comparison.

**Full D formula, Remap tables, & CalcTier detail in `Methodology.md`** (also published as the site's methodology page, checked against `formula.py` at every publish)

In the metrics spreadsheet / render header, you'll see D translated two ways:
- **RemapDiff (0–6):** A manual grouping, calibrated to roughly match the percentage of official releases across the seven tiers. Roughly, how would this have been tiered in a Rock Band game (capped at 6). Guitar (plus Co-op/Rhythm), Bass, and Keys each have their own bin edges, fit against that instrument's own `diff_*` distribution.
- **CalcTier:** A continuous, log-scaled tiering calculation. Every 0.44 natural-log increase in D over a baseline value increments the tier by one. This value is not capped, so officials at Dragonforce level end up in 7+, and a lot of notable customs are 10+. Unlike RemapDiff, the baseline/increment constants are currently shared across all instruments rather than fit per-instrument.

**RemapDiff and CalcTier are computed once per song/instrument, from the Expert level's D only**

**Optional arguments:**

- `--header`: analyze a different library's most recent cache
- `--cache`: point at a specific cache file, instead of most recent for the header
- `--diff-mode`: `CalcTier`, `RemapDiff`, or `Restore`.
  - `CalcTier`/`RemapDiff` writes selected value into every song's own `diff_*` tag, per instrument
  - `Restore` returns every instrument's `diff_*` values back to its `{header}_BackupData.csv` original, throws errors for songs moved/deleted
  - If not supplied, falls back to `config.DIFF_WRITE_MODE` (default `None`, which leaves song.ini alone)
- `--xlsx-levels`: which EMHX levels to write rows for. If not supplied, falls back to `config.XLSX_LEVELS`

**Note: After updating `song.ini` data, you MUST SCAN SONGS for the new metadata to work.**

---

## 4. Rendering song graphs

`python render.py [retrieval code]`

`render.py` draws one PNG graph of difficulty over time for a specific song/instrument/level combo, using its retrieval code. A retrieval code is an 8-digit song hash plus a level letter (`E`/`M`/`H`/`X`) then an instrument letter (`G`, `C`, `R`, `B`, `K`) available on the metrics spreadsheet from Analyze. 

**Make sure the header in config matches the spreadsheet/library you are rendering from.**

**You can render several at once, any mix of instruments and levels:**

`python render.py 04821993XG 71620045HB 09933120EK`

**Or from a text file, one code per line:**

`python render.py --codes-file picks.txt`

**Outputs:**

One PNG per code, named `{code}_{Artist} - {Song}.png`, showing three lines:

- **D** - overall difficulty over time (approx since it does not include CoV & has to be rescaled to fit on the same axis as N & V)
- **Notes** - note density per second
- **Variability** - how much the fret pattern is changing per second

Graphs are available in light or dark mode depending on the config.

**Optional arguments:**
- `--header` / `--cache`: pick which library/cache to pull from
- `--out-dir`: where to save the PNGs (defaults to `render_dir` in `config.py`)

---

## 5. Browsing in a browser

`python serve.py [--header NAME] [--xlsx FILE] [--cache FILE] [--port 8000] [--packs FILE] [--no-bootstrap]`

`serve.py` serves the most recent metrics spreadsheet for your header as a local web page, so you can sort and filter without opening Excel. It reads the **spreadsheet**, so run Analyze first. It serves exactly what Publish writes: `index.html`, `about.html`, `404.html` and `robots.txt`, and an unknown path gets the 404 page.

Open **http://localhost:8000** once it starts. It binds `127.0.0.1` only, so nothing outside your machine can reach it. On WSL the URL works in a Windows browser as-is.

**What the page does:**

- **Sort** by clicking a column header, click again to flip direction. Opens sorted by D, hardest first
- **Added** (hidden by default) is the date the chart's pack was registered in `packs.toml`, joined when the page is built; the header's "Updated" line links to the "What's new" page, which lists every pack with its counts and the site's own changes
- **Percentile**, beside D: where the chart sits among the charts on its sheet at the same level, officials and customs together, as a whole number (100 is the hardest). It is computed when the page is built, so it moves as the library grows and is not in the spreadsheet; the graph heading and each row's hover text spell it out. A chart counts once however many packs carry it
- **Copies** (hidden by default) is how many charts on the sheet have exactly these notes at this level and part, this one included: 1 is unique, 2 means the same chart is in another folder, usually another pack. Rows are never merged, since each copy has its own code, graph and report link; the graph heading lists the other folders under "Same chart in", each a link that opens that copy's graph. `?f.Copies=2` is the view of every duplicated chart
- **Filter** any column from the caret next to its name - a checkbox list for things like Part or Remap Tier, a min/max box for wide numeric columns like D or Length. Value counts reflect your other active filters
- **Search** song, artist, album, charter or source from the box in the toolbar
- **Click a row** to open its details in a pane under the table, which shrinks to make room; the row stays highlighted through a sort or a filter, the arrow keys move from chart to chart with the pane following, clicking the row again or Escape closes it, the top edge drags its height and the caret collapses it to a strip. The pane's left half is the chart's graph: the same three curves `render.py` draws, drawn in the browser from the chart's curve file, with the values under the cursor read out below (hover, or the arrow keys once the graph has focus; Shift with them jumps ten seconds). **Compare with a row** overlays up to three charts' D curves (the button is disabled at three): find the other chart with the table's own search and filters and click its row (an instrument's "Compare all levels" in the song grid overlays its levels in one click); the link carries them as `?code=A&vs=B,C`, and the legend names only what tells the charts apart. **Save as PNG** downloads the graph at the figure's own size, named the way `render.py` names its files. The copy icon on a Code cell copies the retrieval code instead
- **Every chart of a song** in the pane's right half (under the graph on a phone): instruments down, levels across, `D` and the percentile in each cell, the Expert-anchored tier beside each instrument, "Compare all levels" per instrument, and the other folders that carry the same charts under "Also in". With one chart up a cell opens that chart. "Compare all levels" overlays an instrument's levels (three at most) and stays pressed while they are up; the grid then mirrors the legend, each chart on the graph wearing its colour and letter, a cell click takes a chart off the graph or adds one (the cells not on it are disabled at three), and the pressed button returns to one chart. `?song=<key>`, the song's content hash, opens the song's first instrument at Expert and the link then carries that chart's `?code=`
- **Where a chart is published**: the "Chart page" column's arrow opens the chart's page on the host it was found on (Chorus Encore today; the column's filter lists the hosts, and the dash is the charts the offline lookup did not find), and the same links lead the pane's tool row. A Scores column and button follow when the leaderboard lookup lands. The column leaves the table on a phone, where the pane's buttons carry the links
- **Columns** button hides any column you do not want, remembered in your browser
- Friendly column names throughout, with the metric definitions on hover. Unrated songs (`diff_*` of -1) show a dash rather than the raw number

**Optional arguments:**
- `--header` / `--xlsx`: pick which library's spreadsheet to serve
- `--cache`: explicit cache path, used for the on-demand graphs
- `--out-dir`: where rendered PNGs are written (defaults to `render_dir` in `config.py`)
- `--port`: something other than 8000
- `--no-bootstrap`: skip the Bootstrap download and use the built-in styles

**Note:** the page's CSS comes from Bootstrap, downloaded once into your cache folder the first time you run Serve and then served from your own machine. After that first run it works offline. If the download fails it falls back to built-in styles and still works.

Stop the server with Ctrl+C.

---

## 6. Publishing a static site

`python publish.py`

`publish.py` writes the same page `serve.py` serves into a folder - `site/<header>/` by default - as plain files: `index.html` and the sheet files, the scripts and styles, Bootstrap, and **every chart's curve file** under `graph/<code>.json`, from which the page draws the graph itself; the one PNG it renders is the social-preview chart (`page.OG_IMAGE`) that link previews need. The result needs no server-side code, and its URLs are relative, so it works from a domain root, a sub-path like `user.github.io/fretwork/`, or any static file host. It reads the **spreadsheet** for the table and the **cache** for the graphs, so run Analyze first; it stops if the two are from different builds, unless you pass `--allow-mismatch` on purpose.

The first publish of a large library takes seconds (the curve files are about 4 KB each, 48 MB for 12,000 charts). After that it is incremental:

- files whose bytes did not change are left alone, so a sync to your host uploads only what moved
- a chart whose notes, Expert anchor and difficulty block are unchanged keeps its curve file, tracked in `graph/curves-manifest.json`; the preview PNG's own inputs (those plus the metadata the graph header prints, and the render theme) are tracked in `graph/manifest.json`
- a chart that cannot be written this time keeps the file an earlier publish made
- only files an earlier publish recorded are ever removed; nothing else in the folder is touched. A library without the preview chart publishes no PNG and removes none

**Optional arguments:**
- `--header` / `--xlsx`: pick which library's spreadsheet to publish
- `--cache`: explicit cache path, used for the graphs
- `--out-dir`: the folder to write (default `site/<header>/`, from `site_dir` in `config.py`)
- `--no-bootstrap`: skip the Bootstrap download and inline the built-in styles instead
- `--packs`: the pack registry to join and list (default `packs.toml` in the repo root)
- `--force`: re-render the preview PNG and rewrite every curve file. Needed after a change to `functions/density.py`'s windowing, which the manifests cannot see; a change to the page's drawing or the theme needs nothing, since the page draws
- `--allow-mismatch`: publish even though the spreadsheet and the cache carry different build timestamps. Without it the run stops, because a table computed from one build beside graphs rendered from another is not a site anyone meant to publish

To check a bundle locally, serve the folder with any static server, for example `python -m http.server 8000 --directory site/Main`, and open **http://localhost:8000**. Opening `index.html` straight from the filesystem will not work: the page uses ES modules, which browsers refuse to load from `file://`.

**Deploying to S3:** `python deploy.py` publishes and then pushes the folder to a bucket through the AWS CLI, invalidating CloudFront if you have it in front. Settings live in a `.env` file in the repo root - copy `.env.example`, set `FRETWORK_BUCKET`, and optionally `FRETWORK_DISTRIBUTION`, `FRETWORK_HEADER` and `AWS_PROFILE`. Credentials never go in that file - `deploy.py` refuses a `.env` that contains any. Configure an AWS CLI profile or `aws configure sso` and name the profile in `.env` instead; for the `AWS_*` keys the `.env` value wins over one exported in your shell, so the deploy always uses the profile you wrote down for it. `.env` and any `.env.*` are gitignored. `--dry-run` lists what the sync would upload and publishes nothing; `--no-publish` syncs what is already in the folder.

The sync runs with `--delete`, mirroring publish's own pruning, so the bucket must hold nothing but this site. Two guards enforce that: the site folder may contain only what publish writes (so pointing it at the repo root is refused rather than uploaded), and it must hold a publish output before anything is sent.

---

## 7. Updating the live site, start to finish

Everything between "there is a pack to add" and "the website shows it". Three commands: `tools/ingest_pack.py` puts the pack under `songs/<name>/` chart-only, records it in `packs.toml`, and runs build and analyze for you (the two commands from sections 2 and 3, printed as it runs them, so the manual route is still there when the library changed some other way); `publish.py` writes the site; `deploy.py` pushes it. The sanitise, build and analyze steps this section used to list are inside the first command, and the checks it asked you to make by hand are in its summary: the song count moved by the size of the pack, the errors CSV did not jump, every instrument gained what the pack charts, and the pack is registered.

Run every command from the repo root with the virtualenv active:

```
source .venv/bin/activate          # Windows: .venv\Scripts\activate
```

The examples use `Local` as the header and `songs/` as the library. Substitute your own; the header is what ties a cache, a spreadsheet and a published site together, so **use the same one at every step**, and `deploy.py` reads its header from `.env` (`FRETWORK_HEADER`) rather than a flag, so that must name the same one.

### Before the first run

Three things need to be right once, and then never again:

1. `config.py` - `SEARCH_PATH` and `HEADER` if you would rather not pass them on the command line. See [1. Setup your Config](#1-setup-your-config).
2. `.env` in the repo root - copy `.env.example` and set `FRETWORK_BUCKET`, and `FRETWORK_DISTRIBUTION` if CloudFront is in front of it. **No credentials go in this file**; `deploy.py` refuses one that has any.
3. An AWS login the CLI can find - `aws configure sso` then `aws sso login`, or a named profile. Name it in `.env` as `AWS_PROFILE` so the deploy always uses the same one. Check it works: `aws sts get-caller-identity`.

### Step 1 - ingest the pack

```
python tools/ingest_pack.py "~/Downloads/Some Pack.zip" --name "Some Pack" --source https://where.it/lives
```

`SOURCE` is a `.zip`, `.rar` or `.7z`, a folder, or a direct download URL to one of those (a Google Drive, Mega or Discord link is a page, not a download: fetch it in a browser and pass the file). The tool refuses anything it can refuse before touching a byte, then extracts or copies the pack under `caches/ingest/`, lower-cases `Song.ini` and friends so the parsers find them, strips a wrapper folder that repeats the pack name, runs the sanitizer (audio, art, video and editor scratch go; `song.ini`, `notes.chart`, `notes.mid` and anything unrecognised stay), and only then renames the chart-only tree to `songs/<name>/`. That rename is the one commit point: a crash before it leaves nothing under `songs/`. A folder `SOURCE` is copied without its audio and never modified, so a pack in your Downloads or the read-only Clone Hero library is left as it was.

It then appends the `[[pack]]` block to `packs.toml` (`name` and `folder` are `--name`, `source` is `--source` or the URL, `added` is today; `--notes` for free text), runs `build.py --search-path songs --header Local` and `analyze.py --header Local` exactly as sections 2 and 3 describe, and prints a summary against the previous cache: songs and charts before and after, Expert charts per instrument, and a block for this pack (song.ini found, cached, charts, no usable chart or mid, build errors in the pack, `.sng` files it cannot read, what the sanitizer removed). **Check before moving on:** the pack's `cached` equals its `song.ini found` unless you expected otherwise, `build errors in pack` is zero or explained, and the Expert rows moved by what the pack charts. `--dry-run` does everything up to the rename and then reports; `--replace` re-downloads a pack that is already there (the registry entry is kept, since it describes the same pack).

Site changes worth a line on the "What's new" page go in `packs.toml` as `[[change]]` blocks with a `date` and a `text`. One rule for a change to the parsers or `functions/timing.py`: the rebuild after it moves every song's key, so add a `[[change]]` saying so, because `?song=` links from before it stop resolving. If the library changed some other way (a pack removed, a folder renamed), register it by hand (copy the last `[[pack]]` block) and run the two commands from sections 2 and 3 yourself; `python -m functions.packs --header Local` then prints every pack's counts and names any folder publish would refuse.

### Step 2 - look at the result before anyone else does *(optional)*

```
python serve.py --header Local
```

Opens the same viewer the website runs, against your local spreadsheet, at http://127.0.0.1:8000. Worth a minute: sort by D and check the top of the list is plausible, and search for a song from whatever pack you just added to confirm it is there.

### Step 2b - resolve where each chart is published *(optional)*

```
python tools/enchor_lookup.py --header Local
```

Asks Chorus Encore (api.enchor.us), once per song not yet answered, whether it publishes the chart, and records the answer in `caches/Local_links.json` keyed by the song's content hash: the chart page's id, or "asked, not found". The match is an exact title and artist search narrowed by the Expert guitar note count and the charter, because Enchor's hash filter is not the notes file's MD5 (`tools/enchor_probe.py` records the experiment); a chart that cannot be singled out gets no link, since a wrong link is worse than none. 48 requests a minute (the service allows 50), so a 1,800-song library takes about 40 minutes the first time and seconds afterwards: the registry persists across builds like the backup CSV, `--recheck` re-asks the misses, `--recheck-all` everything, `--limit N` stops after N. Publish then writes `data/links.<hash>.json` and every graph whose song is in it carries an "On Chorus Encore" link beside "Report this rating"; without the registry, publish writes no file and the page shows no link. The registry is not committed and lives in `caches/`, so copy it somewhere before clearing that folder (`--links FILE` points at a copy).

The leaderboard half (`tools/leaderboards_lookup.py`, a "Leaderboard" link per song) is not built: api.clonehero.net has no documented public status, and the spec (section 13) waits on the maintainer's answer before any batch tool reads it. `web/links.py` already publishes an `lb` value when a registry carries a sure match, so the tool is the only missing piece.

### Step 3 - build the site

```
python publish.py --header Local
```

Writes `site/Local/` - `index.html` and the sheet files, `404.html`, `about.html`, `changelog.html`, `methodology.html` (the engine's `Methodology.md`, rendered), `robots.txt`, the assets, Bootstrap, a curve file per chart under `graph/` and the one preview PNG. Publish stops with `MethodologyDrift` if a calibration table in `Methodology.md` disagrees with `functions/formula.py`, and with `MarkdownError` naming the line if the file uses a markdown construct the renderer does not know; both are fixed in the source, never by loosening the check. Seconds, first run or not; only charts whose notes changed get a new curve file. The summary's `social preview <code>:` line says whether the PNG was rendered, unchanged or (for a library without that chart) not published.

Publish stops if the spreadsheet and the cache carry different build timestamps (`spreadsheet is from X but the cache is from Y`), because that means Analyze has not run since the last Build; run it and publish again. `--allow-mismatch` exists for the deliberate exception, and `deploy.py` does not take it: a mismatched bundle is published by hand and then sent with `deploy.py --no-publish`, so the decision is taken twice. One more thing that looks like a fault and is not: a commit that changes what a manifest fingerprint is made of invalidates every stored hash, so the next publish rewrites every curve file once (seconds; the bytes are compared before writing, so the sync uploads only what changed).

You can skip this step: `deploy.py` publishes first anyway. Run it separately when you want to look at the bundle before it goes anywhere.

### Step 4 - preview the exact bundle *(optional)*

```
python -m http.server 8000 --directory site/Local
```

Then open http://localhost:8000. Opening `index.html` from the filesystem will **not** work - the page uses ES modules, which browsers refuse to load over `file://`.

### Step 5 - deploy

```
python deploy.py --dry-run     # lists what would upload; sends nothing
python deploy.py               # publish, sync, invalidate
```

`--dry-run` first is a good habit when the library changed a lot (and `python tests/pipeline_test.py` before that, if code changed: it runs this whole sequence on a synthetic library in seconds, see [9. Tests](#9-tests)): the upload list is the clearest confirmation that publish produced what you expected. The real run publishes again, syncs to S3 in two passes (graphs with a week of caching, the page and assets with `no-cache`), and invalidates CloudFront so the new page is live immediately.

### Step 6 - confirm it landed

```
python tools/check_site.py --site site/Local
```

Ten checks against the live site, one line each (add `curl -s https://fretladder.com/changelog.html | grep -c '<h2'` for the changelog, which should print at least 1), and `--site` makes the first of them insist that the live strapline is the one in the bundle you just published, so a deploy that did not actually land fails here rather than in a browser. It also checks compression, the about page, `robots.txt`, the social-preview image, that the module script and every stylesheet are served with the right content type, that an unknown path gets our 404 page, and that a `?code=` link answers. It exits with the number of failures. CloudFront invalidation usually takes under a minute; if only the strapline check fails right after a deploy, wait and run it again. The two curl lines it replaces still work on any machine: `curl -s -o /dev/null -w "%{http_code}\n" https://fretladder.com/` and `curl -s https://fretladder.com/ | grep -o "Updated [^\"]*charts"`.

`deploy.py` ends by asking S3 what content type it will serve for one file of each kind, and refuses to call the deploy done if any is wrong. A file served as `binary/octet-stream` is not a cosmetic problem: browsers refuse to run an ES module with the wrong type, so the page loads and then does nothing.

### After it is live

Three things to look at, weekly, for the first couple of weeks after any announcement, and after every deploy. Everything here needs `aws sso login --profile <the AWS_PROFILE in .env>` first (the CLI's own message calls it `aws login`; same thing).

```
python tools/check_site.py --site site/Local          # the ten live checks; the live strapline must match the one just published
gh issue list --repo ChaseFranz/fretwork --label "song pack"
gh issue list --repo ChaseFranz/fretwork --label rating
gh issue list --repo ChaseFranz/fretwork --label accessibility
gh issue list --repo ChaseFranz/fretwork --search "no:label"
D=$(python -c "from functions import envfile; print(envfile.load('.env')['FRETWORK_DISTRIBUTION'])")
export AWS_PROFILE=$(python -c "from functions import envfile; print(envfile.load('.env').get('AWS_PROFILE', ''))")   # deploy.py reads it from .env; a bare aws does not
aws cloudwatch get-metric-statistics --region us-east-1 --namespace AWS/CloudFront \
  --metric-name Requests --statistics Sum --period 86400 \
  --dimensions Name=DistributionId,Value=$D Name=Region,Value=Global \
  --start-time $(date -u -d '30 days ago' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --query 'sort_by(Datapoints,&Timestamp)[].[Timestamp,Sum]' --output text
```

Run the same call with `--metric-name BytesDownloaded` for bytes. CloudFront's metrics live in `us-east-1` whatever the bucket's region, and the `Region=Global` dimension is required. The date arithmetic is GNU `date` (Linux and WSL); elsewhere type the two ISO timestamps by hand.

**The allowance.** The distribution is on CloudFront's Free flat-rate plan: 1,000,000 requests and 100 GB a month, no overage billing, a short spike absorbed. A cold page view is six requests (the page, Bootstrap, the stylesheet, the favicon, the script bundle and the first sheet's rows) plus two idle prefetches and one per graph opened; everything but the page carries a year of caching, so a returning visitor costs one request. That is about 160,000 cold page views a month with no graphs opened, and requests bind long before bytes do. The plan's own usage view is CloudFront console > Pricing plans. Two thresholds mean it is time to think about the plan: 700,000 requests in any 30-day window, or one day over 35,000. The AWS Budget `fretladder-monthly` ($50 a month) e-mails at 50% and 100% actual and 80% forecast; the plan itself cannot bill, so a budget e-mail means S3 or Route 53, and Cost Explorer's breakdown is the first thing to read.

**What each channel yields.** A `song pack` issue is an entry for the pack registry and a job for the ingest tool (sections 03 and 09 of the spec); until those exist, triage by hand: is the pack public, is it already in the Release column, how big is it. A `rating` issue is calibration evidence: if it describes flow (strumming, HOPOs, anchoring) it is the known gap the "How it works" panel names, and gets a link to that section; if it describes a density or length effect it goes to upstream's tracker with the code, because the formula is theirs. Either way it stays open on the fork until the number moves or the explainer covers it. A blank issue is a bug or an accessibility report; label it at triage, which is why the block above searches `no:label` too.

**Browser checks**, which no script can make:

- `https://fretladder.com/?code=10145439XG` opens with Through The Fire & Flames (Expert, Lead) in the details pane, its row highlighted and scrolled into view, and the pane's `aria-label` ends with the code.
- The graph's "Report this rating" link opens the rating form on GitHub with the code and the song already filled in (GitHub fills issue-form fields from the query string).
- The footer's "Request a song pack" opens the pack form with the two acknowledgement boxes and no attachment control.
- Paste `https://fretladder.com/` into a Discord message to yourself: the preview shows the title, description and the graph. Discord caches previews per URL, so a changed preview image needs a query string to re-check.
- On the fork's GitHub page the Watch button reads "Unwatch" with "All activity", so new issues arrive by e-mail.

### When something is off

| What you see | What it is | Fix |
|---|---|---|
| Publish stops: "spreadsheet is from X but the cache is from Y" | Analyze has not run since the last Build | `python analyze.py --header Local`, then publish again (`--allow-mismatch` only if you mean it) |
| Publish warns: "newest by mtime is A but newest by name is B" | An older cache or spreadsheet was copied or touched, so it looks newest | Delete or re-date the copy, or name the file you want with `--cache` / `--xlsx` |
| Publish stops: "folder(s) not registered in packs.toml" | A pack folder under the library has no `[[pack]]` entry | Add the entry (step 0), then publish again |
| Publish or serve stops: `MethodologyDrift: ... in Methodology.md but ... in formula.py` | An upstream merge changed the bins or constants in one file and not the other | Fix whichever is wrong (the code is usually right; the table then goes upstream as a fork PR), `python -m web.methodology` to confirm |
| Publish or serve stops: `MarkdownError: Methodology.md: line N: ...` | Upstream used a markdown construct `web/markdown.py` does not render | Extend the renderer for that construct, deliberately, and add the case to `tests/test_methodology.py` |
| Publish stops: "registered folder(s) with no songs in this cache" | A `folder` in `packs.toml` is misspelled, or the cache is another library's | Fix the spelling, or point `--packs` at that library's registry |
| `refused: ... not a direct download` | The link is a Google Drive, Mega or Discord page, not an archive | Download it in a browser and pass the file to `ingest_pack.py` |
| `refused: found 0 song folders and N .sng files` | Enchor serves `.sng`, a single-file format the parsers cannot read yet | Get the pack from its release thread as song folders, or convert it |
| `refused: config.DIFF_WRITE_MODE is set` | A write-back mode was left on in `config.py` | Set it back to `None`; ingest never writes `song.ini` |
| Site shows an old date | The invalidation has not finished, or the browser cached the page | Wait a minute, then hard-reload |
| A graph looks stale after changing plotting code | The manifest fingerprints data, not code | `python publish.py --header Local --force` |
| `deploy.py` refuses: "holds files publish did not write" | `FRETWORK_SITE_DIR` points at the wrong folder | Point it at `site/<header>` |
| `deploy.py` refuses: a credential in `.env` | Keys were pasted into `.env` | Remove them; use an AWS profile or SSO |
| Cache headers wrong on files already in the bucket | `sync` only sets headers on files it uploads | `python deploy.py --set-headers` |
| A code rollback to before the `data/` split | The old `deploy.py` refuses `data/` as a stray and the old `prune_page` does not know the curve files | `rm -rf site/Local/data site/Local/graph/*.json site/Local/graph/curves-manifest.json`, then the old `publish.py` and `deploy.py` |
| A code rollback to the PNG-per-chart page (before `fretladder-v1.6.0`) | `graph/manifest.json` records only the preview PNG now, so the old publish would render all 11,903 others (about 24 minutes, a 2.2 GB upload) | `cp caches/Local_manifest_pre06.json site/Local/graph/manifest.json` first (saved when the PNGs were pruned), so only files that are actually missing render |
| Blank page, console says "Expected a JavaScript-or-Wasm module script" | Objects are served as `binary/octet-stream` | `python deploy.py --set-headers`, then hard-reload |

**Rolling back:** every build's outputs are kept, so the previous site is one command away. Point publish at the older pair and deploy that:

```
python publish.py --header Local --xlsx metrics/Local_metrics_<older>.xlsx --cache caches/Local_cache_<older>.pkl
python deploy.py --no-publish
```

---

## 8. Fixes/Extension Ideas

The engine ideas below are upstream's list. The fork's own plan for the hosted site, fretladder, is in [`docs/spec/`](docs/spec/README.md): fourteen sections with an implementation order, from the small fixes owed today through client-side graphs, a per-song view and pack ingestion.

**Fixes:**
- Midi files misbehaving - *possibly parser drift / file corrruption/truncation?*

**Extension Ideas:**
- Vocals (Unique data, new metric needs, new difficulty logic/calcs) - *design in progress*
- Drums (similar data, new metric needs, new difficulty logic/calcs) - *design in progress*
- RB style band diff once all instruments are in
- Retesting duration and ways to include it (GHVH outliers) - *very annoying, short song downscaling is not bad but calibration for long is tough*
  
**Bigger rebuilds**
- Scoring by totals (as opposed to average), type of notes (singles by type/state, chords by type)
- D by section + Section names for renders - *parsing sections is a lot of extra data for the cache*
- Including strum/hopo/tap state by note in the cache - *not adding until there's plan to use them*
- Actually doing something with note state once it exists - *Ratios over the song was a good suggestion*
- Star Power Difficulty (how hard are SP phrases to hit?) - *SP no longer parsed*
- Rhythm changes/variability possibly easier than pattern recognition?
- Pattern recognition (chords, trills, runs, zigs, quads, quints, anchoring, etc)
- A strain-based difficulty metric splitting strum vs fret
- DDR Groove Radar style scoring (probably tied to patterns)

---

## 9. Tests

Three commands, all stdlib plus the venv, and the same three run in GitHub Actions on every push:

```
python -m unittest discover -s tests -t . -v
python tests/pipeline_test.py --keep /tmp/fw-ci --bootstrap-css caches/bootstrap-5.3.8.min.css
python tests/page/run.py --site /tmp/fw-ci/site/Fixture
```

The first imports every module and checks the small pure functions. The second builds, analyzes, publishes and deploys a synthetic 15-song library from a temporary directory, with a stub `aws` on `PATH` so the deploy path runs without credentials, and asserts every count against the fixture's own table. The third drives the published page in headless Chrome: twelve suites read their expectations out of the page's data island, so `--site site/Local` runs the same checks against the real library. On WSL the runner uses Windows Chrome from `/mnt/c`. `tests/README.md` has the details and the harness gotchas.

## License
**MIT** - see LICENSE for details.
