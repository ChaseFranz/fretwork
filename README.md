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
4. **Serve** *(optional)* - Browse the spreadsheet in a browser instead of Excel, with per-column filters and click-a-row-to-see-its-graph
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
- Metadata: Song Title, Artist, Level, Type (Lead/Co-op/Rhythm/Bass/Keys), Charter, Release/Source, Difficulty (song.ini diff tags)
- The difficulty metrics & updated Remap/CalcTier numbers

Each tab is formatted for browsing using `xlsx_format.py`

Using `XLSX_LEVELS` in the config you can adjust the mix of Easy/Medium/Hard/Expert you want in the sheet.

The raw NPS/VPS details and N/V/COV formula components are dropped, but they can be included as hidden columns by using `EXTRA_METRICS = True` in the config for diagnostics/comparison.

**Full D formula, Remap tables, & CalcTier detail in `Methodology.md`**

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
- **Percentile**, beside D: where the chart sits among the charts on its sheet at the same level, officials and customs together, as a whole number (100 is the hardest). It is computed when the page is built, so it moves as the library grows and is not in the spreadsheet; the graph heading and each row's hover text spell it out
- **Filter** any column from the caret next to its name - a checkbox list for things like Part or Remap Tier, a min/max box for wide numeric columns like D or Length. Value counts reflect your other active filters
- **Search** song, artist, charter or source from the box in the toolbar
- **Click a row** to render that chart's graph and see it in a lightbox - the same PNG `render.py` produces, written to your render folder. The copy icon on a Code cell copies the retrieval code instead
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

`publish.py` writes the same page `serve.py` serves into a folder - `site/<header>/` by default - as plain files: `index.html` with the table's data baked in, the scripts and styles, Bootstrap, and **every chart's graph pre-rendered** under `graph/<code>.png`. The result needs no server-side code, and its URLs are relative, so it works from a domain root, a sub-path like `user.github.io/fretwork/`, or any static file host. It reads the **spreadsheet** for the table and the **cache** for the graphs, so run Analyze first; it stops if the two are from different builds, unless you pass `--allow-mismatch` on purpose.

The first publish of a large library takes a while - measured at about 0.12 seconds per chart, so around ten minutes for 4,600 charts. After that it is incremental:

- files whose bytes did not change are left alone, so a sync to your host uploads only what moved
- a chart whose notes, header numbers, metadata, curve settings and render theme are unchanged skips its render, tracked in `graph/manifest.json`
- a chart that cannot be rendered this time keeps the graph an earlier publish made
- only graphs an earlier publish recorded are ever removed; nothing else in the folder is touched

**Optional arguments:**
- `--header` / `--xlsx`: pick which library's spreadsheet to publish
- `--cache`: explicit cache path, used for the graphs
- `--out-dir`: the folder to write (default `site/<header>/`, from `site_dir` in `config.py`)
- `--no-bootstrap`: skip the Bootstrap download and inline the built-in styles instead
- `--packs`: the pack registry to join and list (default `packs.toml` in the repo root)
- `--force`: re-render every graph. Needed after a change to `functions/plot.py` or a matplotlib upgrade, which the manifest cannot see
- `--allow-mismatch`: publish even though the spreadsheet and the cache carry different build timestamps. Without it the run stops, because a table computed from one build beside graphs rendered from another is not a site anyone meant to publish

To check a bundle locally, serve the folder with any static server, for example `python -m http.server 8000 --directory site/Main`, and open **http://localhost:8000**. Opening `index.html` straight from the filesystem will not work: the page uses ES modules, which browsers refuse to load from `file://`.

**Deploying to S3:** `python deploy.py` publishes and then pushes the folder to a bucket through the AWS CLI, invalidating CloudFront if you have it in front. Settings live in a `.env` file in the repo root - copy `.env.example`, set `FRETWORK_BUCKET`, and optionally `FRETWORK_DISTRIBUTION`, `FRETWORK_HEADER` and `AWS_PROFILE`. Credentials never go in that file - `deploy.py` refuses a `.env` that contains any. Configure an AWS CLI profile or `aws configure sso` and name the profile in `.env` instead; for the `AWS_*` keys the `.env` value wins over one exported in your shell, so the deploy always uses the profile you wrote down for it. `.env` and any `.env.*` are gitignored. `--dry-run` lists what the sync would upload and publishes nothing; `--no-publish` syncs what is already in the folder.

The sync runs with `--delete`, mirroring publish's own pruning, so the bucket must hold nothing but this site. Two guards enforce that: the site folder may contain only what publish writes (so pointing it at the repo root is refused rather than uploaded), and it must hold a publish output before anything is sent.

---

## 7. Updating the live site, start to finish

Everything between "I changed what is in the song library" and "the website shows it", in order. Run every command from the repo root with the virtualenv active:

```
source .venv/bin/activate          # Windows: .venv\Scripts\activate
```

The examples use `Local` as the header and `songs/` as the library. Substitute your own; the header is what ties a cache, a spreadsheet and a published site together, so **use the same one at every step**.

The `songs/` library on the dev box is kept chart-only: `python tools/sanitize_songs.py songs --apply` strips audio, art, video and editor scratch out of every song folder and keeps only `song.ini`, `notes.chart` and `notes.mid` (plus anything it does not recognise). That is all the pipeline reads, so a library sanitized this way builds to the same cache as the full one; a dry run without `--apply` shows what would go.

### Before the first run

Three things need to be right once, and then never again:

1. `config.py` - `SEARCH_PATH` and `HEADER` if you would rather not pass them on the command line. See [1. Setup your Config](#1-setup-your-config).
2. `.env` in the repo root - copy `.env.example` and set `FRETWORK_BUCKET`, and `FRETWORK_DISTRIBUTION` if CloudFront is in front of it. **No credentials go in this file**; `deploy.py` refuses one that has any.
3. An AWS login the CLI can find - `aws configure sso` then `aws sso login`, or a named profile. Name it in `.env` as `AWS_PROFILE` so the deploy always uses the same one. Check it works: `aws sts get-caller-identity`.

### Step 0 - register the pack

Every top-level folder under the library is a pack, and every pack must be in `packs.toml` at the repo root, or publish refuses to run. A new pack is one `[[pack]]` block: `name` (as the changelog prints it), `folder` (the directory under `songs/`), `source` (where it is published, or `""`), `added` (today, as a bare `2026-09-11`), `notes`. `tools/ingest_pack.py` writes the block for you; by hand, copy the last one. Site changes worth a line on the "What's new" page go in the same file as `[[change]]` blocks with a `date` and a `text`. One rule for a change to the parsers or `functions/timing.py`: the rebuild after it moves every song's key, so add a `[[change]]` saying so, because `?song=` links from before it stop resolving.

### Step 1 - rescan the library

```
python build.py --search-path songs --header Local
```

Walks every folder under the search path, parses each `notes.chart` / `notes.mid`, and writes a cache to `caches/Local_cache_<timestamp>.pkl`. It also appends any new songs to `caches/Local_BackupData.csv`, so the original `song.ini` difficulties are recoverable. If an instrument has joined the tool since that file was written, build prints `Backup CSV header updated` once and adds the column; a header it does not recognise stops the build before parsing. Nothing is written back to the library.

Several minutes on a few thousand songs; MIDI parsing dominates. **Check before moving on:**

- the song count in the summary is what you expect - if you added a pack and the number did not move, `--search-path` is pointing somewhere else
- `caches/Local_errors_<timestamp>.csv` - one row per song that failed to parse. A handful is normal; a sudden jump means a bad download, not a bad build

### Step 2 - recompute the metrics

```
python analyze.py --header Local
```

Reads the newest cache **for that header** and writes `metrics/Local_metrics_<timestamp>.xlsx`, reusing the cache's timestamp so the pair can be matched later. This is the step that computes D, RemapDiff and CalcTier.

Run it with no `--diff-mode` unless you specifically want to write difficulties back into your `song.ini` files; those modes change your library.

Then `python -m functions.packs --header Local` prints one row per registered pack with its songs and charts counted from the cache, and either `unregistered: none` or the folders publish will refuse. If a pack is missing from the table, register it (step 0) before going on.

### Step 3 - look at the result before anyone else does *(optional)*

```
python serve.py --header Local
```

Opens the same viewer the website runs, against your local spreadsheet, at http://127.0.0.1:8000. Worth a minute: sort by D and check the top of the list is plausible, and search for a song from whatever pack you just added to confirm it is there.

### Step 4 - build the site

```
python publish.py --header Local
```

Writes `site/Local/` - `index.html` with the table baked in, `404.html`, `about.html`, `robots.txt`, the assets, Bootstrap, and a PNG per chart under `graph/`. The first run on a large library takes around ten minutes; after that only charts whose inputs changed are re-rendered, so it is usually seconds. Add `--force` only after changing `functions/plot.py`, the render theme, or upgrading matplotlib - the manifest cannot see code changes.

Publish stops if the spreadsheet and the cache carry different build timestamps (`spreadsheet is from X but the cache is from Y`), because that means Analyze has not run since the last Build; run it and publish again. `--allow-mismatch` exists for the deliberate exception, and `deploy.py` does not take it: a mismatched bundle is published by hand and then sent with `deploy.py --no-publish`, so the decision is taken twice. One more thing that looks like a fault and is not: a commit that changes what the manifest fingerprint is made of (as `69b5a8f` did, when upstream dropped star-power spans from the cache) invalidates every stored hash, so the next publish re-renders every chart once, about 24 minutes for 12,000 charts.

You can skip this step: `deploy.py` publishes first anyway. Run it separately when you want to look at the bundle before it goes anywhere.

### Step 5 - preview the exact bundle *(optional)*

```
python -m http.server 8000 --directory site/Local
```

Then open http://localhost:8000. Opening `index.html` from the filesystem will **not** work - the page uses ES modules, which browsers refuse to load over `file://`.

### Step 6 - deploy

```
python deploy.py --dry-run     # lists what would upload; sends nothing
python deploy.py               # publish, sync, invalidate
```

`--dry-run` first is a good habit when the library changed a lot (and `python tests/pipeline_test.py` before that, if code changed: it runs this whole sequence on a synthetic library in seconds, see [9. Tests](#9-tests)): the upload list is the clearest confirmation that publish produced what you expected. The real run publishes again, syncs to S3 in two passes (graphs with a week of caching, the page and assets with `no-cache`), and invalidates CloudFront so the new page is live immediately.

### Step 7 - confirm it landed

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

**The allowance.** The distribution is on CloudFront's Free flat-rate plan: 1,000,000 requests and 100 GB a month, no overage billing, a short spike absorbed. A cold page view is 21 requests (the page, Bootstrap, the stylesheet, the favicon and 17 script modules) plus one per graph opened, and because everything but `graph/` is deployed `no-cache`, a returning visitor costs the same 21. That is about 47,000 page views a month with no graphs opened, and requests bind long before bytes do. The plan's own usage view is CloudFront console > Pricing plans. Two thresholds mean it is time to move the row data out of the page (section 05 of `docs/spec/`): 700,000 requests in any 30-day window, or one day over 35,000. The AWS Budget `fretladder-monthly` ($50 a month) e-mails at 50% and 100% actual and 80% forecast; the plan itself cannot bill, so a budget e-mail means S3 or Route 53, and Cost Explorer's breakdown is the first thing to read.

**What each channel yields.** A `song pack` issue is an entry for the pack registry and a job for the ingest tool (sections 03 and 09 of the spec); until those exist, triage by hand: is the pack public, is it already in the Release column, how big is it. A `rating` issue is calibration evidence: if it describes flow (strumming, HOPOs, anchoring) it is the known gap the "How it works" panel names, and gets a link to that section; if it describes a density or length effect it goes to upstream's tracker with the code, because the formula is theirs. Either way it stays open on the fork until the number moves or the explainer covers it. A blank issue is a bug or an accessibility report; label it at triage, which is why the block above searches `no:label` too.

**Browser checks**, which no script can make:

- `https://fretladder.com/?code=10145439XG` opens with the graph of Through The Fire & Flames (Expert, Lead) and the dialog's `aria-label` ends with the code.
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
| Publish stops: "registered folder(s) with no songs in this cache" | A `folder` in `packs.toml` is misspelled, or the cache is another library's | Fix the spelling, or point `--packs` at that library's registry |
| Site shows an old date | The invalidation has not finished, or the browser cached the page | Wait a minute, then hard-reload |
| A graph looks stale after changing plotting code | The manifest fingerprints data, not code | `python publish.py --header Local --force` |
| `deploy.py` refuses: "holds files publish did not write" | `FRETWORK_SITE_DIR` points at the wrong folder | Point it at `site/<header>` |
| `deploy.py` refuses: a credential in `.env` | Keys were pasted into `.env` | Remove them; use an AWS profile or SSO |
| Cache headers wrong on files already in the bucket | `sync` only sets headers on files it uploads | `python deploy.py --set-headers` |
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
