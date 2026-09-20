# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Fretwork computes difficulty scores for rhythm-game charts from `song.ini` + `notes.chart` / `notes.mid` files: the five 5-fret instruments (Guitar/Co-op/Rhythm/Bass/Keys at Easy/Medium/Hard/Expert), Drums (the same four levels, with a 1x and a 2x kick reading) and Vocals (one level, read as Expert, from `.mid` only). Three metric families (`instruments.FAMILY`: `fret`, `drums`, `vocals`), each a density module and a formula module. The formulas and calibration are documented in `Methodology.md`; user-facing usage is in `README.md`. Read those before changing metrics or calibration constants.

## Commands

Plain Python 3 scripts, no packaging config, no linter. Tests are stdlib `unittest` plus two scripts under `tests/` (see below); `.github/workflows/ci.yml` runs them on every push. Always work inside the project virtualenv at `.venv/` (gitignored); never install into or run against the system interpreter.

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

`serve.py` is an optional fourth entry point that browses an existing metrics `.xlsx` in a browser instead of Excel. Clicking a row opens the details pane under the table (`static/js/pane.js`, `#pane`, `state.graph`, `?code=`; section 14): a `region`, not a dialog, so there is no backdrop and no focus trap, the table shrinks to make room, the chart's row is highlighted (`table.markRows`, drawn from `state.graph` after every repaint and by the pane after every swap, so it survives a sort or a filter and the pane stays open through both and through a sheet switch; in compare mode every row on the graph wears its series colour on the left edge and its legend letter after the rank, as the song grid's cells do), focus stays on the row so the arrow keys keep moving and the graph follows them (`router.js`, debounced), a click on the open row or Escape closes it and hands focus back to the row that opened it, remembered by code and painted again if the table's window has moved on (never by node, since section 17's window repaints rows); a row click or an arrow key always shows one chart, dropping any comparison, since comparisons are built only in the pane (a grid cell, Compare all levels, Compare with a row), so the row is always the chart on the graph and in the song grid, the top edge drags its height (`fw.pane`) and the heading's caret collapses it to a strip. Its left half is the chart's graph, drawn on a canvas by `static/js/graph.js` from `graph/<code>.json` (the raw window counts of the family's lines, named, smoothed in the browser with the same EMA as `functions/curves.py` and summed or multiplied into ~D by the file's recipe; the legend, readout and alt text take the lines' words and colour tokens from `labels.CURVE_FAMILIES`, booted as `curves`, so a drum chart reads Hands, Travel and Kicks and a vocals chart Pitch, Syllables and Percussion; the line width, grid alpha and fill are `boot.render`, the four numbers of `plot.resolve_profile()`, and the colours are the page's own tokens read at each paint (`gPalette`), so the graph follows the theme and is painted on the page's ground rather than in a box; `tests/test_graph_json.py` pins the numbers and the smoothing against the Python side and every token the canvas reads against both theme blocks of `app.css`; `mountGraph`'s `fill` option makes the canvas take the pane's height beside the song grid, and its aspect when stacked under 900 px), with a readout under the cursor, up to three charts overlaid (`state.compare`, `?vs=`; the legend names only what tells the charts apart, so two levels of one song read "Expert" and "Hard"; the three compare series are their own trio, `--fw-series-a/b/c`, never the curve colours, so blue is always Notes and never "chart B"), chosen by picking a row from the table (`state.picking`, the `#pick` bar; the pane stays while a row is chosen; there is no picker of the pane's own, since the table's search and filters are the picker and the song grid lists the song's other charts) and a PNG export named by a twin of `plot.output_filename`; its right half (`static/js/song.js`, markup only) is every chart of the song as instruments by levels from the rows already loaded (`loadAll()` first), keyed on the content hash so it survives a re-download, with the folder the open chart is in heading it and the others under "Also in"; the cells are the compare controls too (`song.onGraph`, `router.chooseCell`): with one chart up a cell opens its chart, in compare mode each cell on the graph wears its series colour as a top bar and its legend letter (`G_LETTERS`, `G_SERIES`, `G_MOST` in `graph.js`, shared by the pane and the grid so the three agree; `G_SERIES` names the stylesheet tokens and a mark is written as `var(--fw-series-b)`, so it follows the theme by itself; the colour is never text) and a click toggles the chart on or off, the cells not on the graph disabled at three, and "Compare all levels" is a pressed toggle; `?song=<SongKey>` is read and never written, resolved by `song.primaryCode` to the song's first instrument at Expert and then carried as `?code=`. `song.js` imports nothing above it and `pane.js` imports it, which keeps the bundle acyclic; `overlay.js` is now only the toast and the explainer, the one dialog left. Columns have Excel-style filter dropdowns, can be hidden individually, dragged into any order in the column chooser, and resized by dragging the right edge of a header. All three preferences are remembered per browser in `localStorage` (`fw.hidden`, `fw.order`, `fw.widths`) and "Reset columns" clears all three. It reads the spreadsheet, not the cache, for the table, so `analyze.py` must have run first; the cache is loaded at startup when present, for the pack join (the `Added` column and the changelog), and a graph click reuses it. Without a cache the page serves with neither. It serves exactly the four pages publish writes (`page.site_pages`: `index.html`, `about.html`, `404.html`, `robots.txt`) and answers an unknown path with the 404 page, so the footer's About link works locally; a code whose cache entry is not the shape its family's metrics read (a cache built before that family was scored) answers 404 rather than crashing, because `GraphRenderer.lookup` returns `None` when `difficulty.scorable` rejects it. A synthetic `Rank` column leads the table, numbering rows in the current view; it has no slot in the row arrays, so `state.visible()` pairs it with index -1. Long titles wrap rather than truncate, and a footer carries attribution and the licence. The level chips are a multi-select shortcut into the `Level` filter: a lit chip is a level on screen, so with no filter all four are lit, and clicking one adds or removes just that level. The Official/Custom pair beside them stays single-select, since its two values are complements and lighting both would mean the same thing as lighting neither. Switching sheets keeps the filters, the search and the sort (`router.render`, `query.carryFilters`): a level chosen on Guitar is still the level wanted on Bass, and only a filter that could match nothing on the new sheet is dropped once its rows are here, a column it lacks or a set filter none of whose values it has (a Part of Lead on Bass), since an empty table with no chip or caret saying why is worse than a dropped filter. Stdlib `http.server` plus pandas, binds `127.0.0.1` only, nothing added to `requirements.txt`:

```
python serve.py [--header NAME] [--xlsx FILE.xlsx] [--cache FILE.pkl] [--port 8000] [--packs FILE] [--no-bootstrap]
```

`publish.py` is the fifth entry point: the same page, written to `SITE_DIR/<header>/` as a static site so it can be hosted with no server-side code. The bundle is three cache classes over four folders: the entry pages (`index.html`, about, changelog, library, methodology, 404, robots.txt, `sitemap.xml`, and the IndexNow key file `<key>.txt` when `.env` names a key), rewritten in place and deployed `no-cache`; `static/` and `data/`, every file named by the first eight hex of the SHA-1 of its bytes (`static/app.<h>.js` is the 17 ES modules concatenated by `web/bundler.py`, plus `app.<h>.css`, `favicon.<h>.svg`, `bootstrap.<h>.css`; `data/<sheet>.<h>.json` is each sheet's rows, which the page fetches on demand, so `index.html` is about 14 KB and carries only a manifest `{sheet: {file, rows, columns}}`), deployed immutable for a year; and the week class (`assets.CACHE_WEEK`, `WEEK_DIRS`): `graph/`, holding `<code>.json` (the raw window counts of each line under ~D, named, the recipe that makes ~D of them and the header numbers, which the page smooths and draws itself; section 23) and the PNGs publish draws, the social preview `page.OG_IMAGE` and one picture per song (`publish.py` passes `Built.png_codes` to `bundle.render_graphs`; a library without the preview chart says so); `song/`, a page per song (sections 16, 21 and 22; `page.render_song_pages`, `page.song_facts`): `song/<SongKey>.html`, about 6.5 KB, carrying the Open Graph tags a shared link previews with (the primary folder's title and artist, one line per part with its Expert D, tier and percentile, and the song's own graph as `og:image`), a page a search engine can read (one sentence per part in words, the graph as an `<img>` with alt text, every level of every part in a table with each cell a link into the table on that chart, the facts, the game it came in linked to its page, a note with links to the methodology and the library page, a `MusicRecording` JSON-LD block, `<base href="../">` so its links resolve from the root, and since section 25 a ladder under the table (`page.song_ladders`, `song_ladder_html`): its rank among the site's songs and its source's on its primary Expert part, its notes and length, the two songs above and below on each and the artist's other songs, every name a link to its song page, so the song folder is a graph a crawler walks rather than leaves off two hubs; the `<img>` carries the PNG's real size, read by `bundle.png_size` off a picture the previous publish left), and a forward to the app only when the URL carries a query, which is what Copy link produces (`song/<key>.html?code=A&vs=B` opens that comparison; a bare URL, the sitemap's and the songs index's, renders); `game/<slug>.html`, a page per registered pack, which the site calls a **source**, never a game: a source is a game, a game's DLC, or a custom pack (BITCRUSHER, the CSC quarterlies), and the folder's name is older than the distinction (`page.render_game_pages`, `pack_slugs`, `charts_by_folder`): its songs ranked by Expert guitar D with the tier and one column per other sheet's part beside (`page.OTHER_PARTS`: Bass, Keys, Drums, Vocals), each song linking its page; and `list/<kind>-<sheet>.html` (`page.render_list_pages`, `LISTS`, `LIST_MOST` 100): per sheet the hardest official songs, the hardest customs and the easiest official on Expert, one entry per song, the game linked. All three folders are swept by `bundle.prune_page` like `static/` and synced with `--delete` like `graph/` (`assets.WEEK_DIRS`). The pictures: publish draws one PNG per song, the chart `song_image_code` names (the first part's Expert, else its highest level), through the same manifest and fingerprint as the preview (1,748 on the Local library, about 170 KB each), and `robots.txt` allows `graph/*.png` so they index as images while the curve files stay out. `songs.html` (`page.render_songs_index`) lists every song A to Z with a link to its page, in the footer, so the pages have a crawl path and internal links; the library page links the packs to their pages, the hardest to the song pages and each block to its three lists. Every document page has its own title and description (`render_doc(page_title, description)`, `meta_head(title, description)`, `UI.*_title`/`*_desc`), and one under a folder gets `<base href="../">` and may carry no fragment link. `robots.txt` allows `data/` on purpose: a crawler that renders the page needs the rows or it indexes an empty table; the rest of `graph/` stays disallowed. The pane's Copy link button (`pane.shareLink`) hands those out: `boot['siteUrl']` is `config.SITE_URL` on publish and null on serve, which copies its own address instead. With both `song` and `code` in a link the code opens when its row exists and the song stands in when it does not (`main.js`), since a code moves with its folder and a key survives. `sitemap.xml` (`page.render_sitemap`) names the charts page, the document pages, the game and list pages and every song page, each with the day its bytes last moved (`page.PageDates`, kept in `caches/<header>_pagedates.json` between publishes, read by serve too and written only by publish; a page that did not change keeps its `lastmod`, so the date is selective), and `page.robots_txt()` names it. Section 24 is what a crawler gets: `index.html` carries a site guide above the footer, `<details id="static" open>` (`page.static_section`: a summary line, one `h1` in the query's words, an intro, the hardest Expert charts per instrument linking their song pages, every source page, every list and the document pages, plus a `WebSite`/`SearchAction` JSON-LD block in the head), closed by the inline script right after it before the first paint and never removed, since Google indexes the DOM it renders and a block removed at boot would be invisible to it (the pre-deploy review of section 24 reproduced exactly that); the brand in the header is a `<p>`, so the page has one `h1` and 100 links with or without JavaScript, the same content for everyone; every link from a document page into the app is by fragment (`page.app_link`: `./#code=X`, `./#song=K`, `./#f.Added=...`), which `url.js readUrl` reads as the query and `writeUrl` then writes as `?code=`, so a crawler sees one front page rather than a query variant per chart; song pages are titled `{song} by {artist}: {source} chart difficulty` with no site suffix (the release for an official chart, a game or its DLC, `Clone Hero` for a custom, the pack added when a custom is in two packs; a result shows the site name from the `WebSite` block and `og:site_name`), headed `{song} by {artist}` with the source on the line under, described from the question people type (`song_desc_lead`, whole parts within 155 characters), and carry a `BreadcrumbList` beside the `MusicRecording`; source pages are `{source} song list ranked by difficulty` with an `ItemList`, a breadcrumb and a More block (`page.more_html`, every source and list); lists carry a method paragraph, their top three songs' pictures, an `ItemList`, a breadcrumb through the library and the More block, and exist only with three or more songs (`LIST_LEAST`); the library page carries a `Dataset` block (no `distribution`: the sheet files are hashed and the next deploy deletes them). Every document page has its heading as the page's own title, the brand a link above it (`doc.html`). A JSON-LD `<script type="application/ld+json">` is data: the suites and the pipeline count running scripts as `<script>` without a type, so the document pages still run one script, the theme's. The front page's `<title>` and `og:title` are `page.site_title()`, the name plus `UI.site_title`, the words a search carries; the brand `h1` is in the HTML (`__BRAND__`), and `document.title` follows the open chart while the pane is up (`pane.js`, `BASE_TITLE`). `web/assets.cache_class` is the one place the class rule lives. The page's URLs are relative, so the bundle works at a domain root or under a sub-path. Re-publishing is incremental: files are rewritten only when their bytes change (so `aws s3 sync` uploads only what moved), and `graph/manifest.json` holds a fingerprint of each chart's render inputs - notes, Expert anchor, the difficulty numbers the header prints, the metadata the header prints (`difficulty.HEADER_META_KEYS`), `source_format`, the curve constants and the render theme - so unchanged charts skip the render; `graph/curves-manifest.json` does the same for the JSON, fingerprinted on the notes, the difficulty block and the constants alone, so a theme edit rewrites no JSON. Safety rules in `web/bundle.py`: a chart that cannot be rendered keeps its previous PNG, only graphs a previous publish recorded are ever pruned, nothing is pruned when no code resolves (a cache/xlsx mismatch), and the manifest is saved every 200 charts so an interrupted run keeps its work. `--force` rewrites everything (the one PNG and every curve file), which a change to a density module's windowing requires since the fingerprint cannot see code; a change to `functions/plot.py` or the theme now changes nothing the site serves, because the page draws. `caches/Local_manifest_pre06.json` is the PNG manifest from before the prune, kept for a rollback to the PNG page (README section 7). Publish refuses a spreadsheet and cache from different builds (`check_pair` raises `SystemExit`) unless `--allow-mismatch`, a flag `deploy.py` deliberately does not take, and warns when the newest file by mtime is not the newest by name. `site/` is gitignored:

```
python publish.py [--header NAME] [--xlsx FILE.xlsx] [--cache FILE.pkl] [--out-dir DIR] [--packs FILE] [--no-bootstrap] [--force] [--allow-mismatch]
```

The full pack-to-published sequence is section 7 of `README.md`: three commands,
`tools/ingest_pack.py` (stage a pack chart-only under `songs/<name>/`, record it in
`packs.toml`, run build and analyze, print the diff against the previous cache),
`publish.py`, `deploy.py`. Keep it in step with these scripts when their flags
change. `tools/` holds operator scripts, not entry points: `sanitize_songs.py`
(also callable as `sanitize()`), `check_site.py`, `www_redirect.sh` (the one-off
that makes `www.fretladder.com` answer a 301 to the apex: the CloudFront Function
in `tools/cloudfront/www-to-apex.js`, the distribution's second alias, the Route 53
alias records; a production change, so the maintainer runs it) and `ingest_pack.py`, which is run
from the directory where `caches/` and `metrics/` should land, refuses everything it
can before touching a byte, and makes the rename into the library its one commit
point so a crash never leaves audio or a half-extracted pack there.

`deploy.py` ends every real run by asking S3 what Content-Type it will serve for
one object of each kind, and exits non-zero if any is wrong; `tools/check_site.py
--site site/Local` is the post-deploy check from the visitor's side (fifteen GETs
through CloudFront, the live strapline matched against the bundle just written, the
front page's guide as a crawler reads it, and the IndexNow key file when the bundle
holds one). That check exists
because `aws s3 cp --metadata-directive REPLACE` (what `--set-headers` uses)
replaces *all* metadata and does **not** re-derive the content type the way an
upload does - so a headers pass that does not name `--content-type` writes
`binary/octet-stream` over every object, and the browser then refuses to run the
page's ES modules. The bucket looks fine from the AWS side when this happens.

`deploy.py` is the sixth entry point and the only one that talks to AWS: it calls `publish()` and then shells out to the AWS CLI, eleven commands in an order that keeps a page in flight consistent (`deploy.plan()`: `graph/`, `song/`, `game/` and `list/` with `--delete` at the week class; `static/` and `data/` without `--delete`; the entry pages with `--delete`, excluding the six directories; the CloudFront invalidation and a wait for it to complete; then `static/` and `data/` again with `--delete`, so the previous generation goes only once no edge can serve the page that named it; then, with `FRETWORK_INDEXNOW_KEY` in `.env`, one POST to `api.indexnow.org` naming the pages this publish rewrote (`deploy.indexnow`, every sitemap URL on `--no-publish`), which is how Bing, Yandex and the engines that read them learn of a change the same day; Google takes no part in IndexNow and reads the sitemap. The key is 32 hex digits, not a credential (publish writes it at the root as `<key>.txt`, public by design, and `deploy.KEY_FILE` lets it past the site-folder guard); a dry run prints the count and sends nothing). Never sync `static/` while it holds unhashed names: the immutable header cannot be undone from the server side. No boto3, nothing added to `requirements.txt`. Settings come from a gitignored `.env` in the repo root read by `functions/envfile.py` (a ten-line KEY=VALUE reader; `.env.example` is committed). Only `FRETWORK_*` keys and `AWS_PROFILE`/`AWS_REGION`/`AWS_DEFAULT_REGION` are read (the `.env` value overrides the shell for those); **credentials never go in `.env`** and a file containing any is refused - the AWS CLI's own profile/SSO chain supplies them. Because the sync uses `--delete`, two guards protect the bucket: the site folder may hold only what publish writes (`deploy.BUNDLE_TOP`: the entry pages, `static/`, `data/`, `graph/`, `song/`, `game/`, `list/`; a new page must be added there and to `bundle.PAGE_TOP` in the same change, and a new folder to `assets.WEEK_DIRS` and `bundle.SWEPT_DIRS`), so `FRETWORK_SITE_DIR=.` is refused instead of uploading the repo, and it must contain a publish output before anything is sent. `--dry-run` publishes nothing and sends nothing:

```
python deploy.py [--env FILE] [--no-publish] [--dry-run]
```

Bootstrap 5.3 supplies the base CSS. It is downloaded once into `OUTPUT_DIRS['cache']` as `bootstrap-<version>.min.css` (gitignored with the rest of `caches/`) and served same-origin as `static/bootstrap.<hash>.css`, so the page never contacts a CDN at view time and works offline after the first run. If the fetch fails or `--no-bootstrap` is passed, the page inlines `FALLBACK_CSS` instead, which covers layout plus the `d-none` / `dropdown-menu.show` state classes the page's JS toggles. There is no JS framework and no Bootstrap JS; interaction is plain DOM code that toggles Bootstrap's own classes.

### The public site is `fretladder`

The hosted site is named *fretladder* (`config.SITE_NAME`, `SITE_URL`); the engine and
this repo stay *fretwork*, and the footer credits it. `page.build(..., public=True)` is
the only difference between what serve shows and what publish writes: a published page
names no internal file (the title is just the site name and the strapline is
"Updated 7 September 2026 - 4,634 charts", read back from the spreadsheet's own
timestamp), and it emits Open Graph / Twitter tags, which need `SITE_URL` because a
social preview cannot use a relative image. `page.OG_IMAGE` picks the chart that serves
as that preview.

A chart links out to where it is published, when that is known, in two places: a
`Chart` column (labelled "Chart page") right after Artist, and a `Leaderboard` one
(labelled Scores) once that half lands, page-built columns joined by `SongKey`
(`links.link_columns`, `frames.with_links`, after `Pct`; a column exists only for a
link kind some song has; off a phone's table under 640 px, where D would otherwise
leave the screen), whose cells draw the arrow from the links file (`links.linkCell`,
filled in place by `fillLinkCells` on the `fw:links` event when the file lands after
the rows); and the accent buttons that lead the pane's tool row (`linkAnchors`). The
hosts a chart can be on are `labels.CHART_HOSTS`, one entry per host (label, tip, URL
template, id character class), booted to the page as `hosts`: the `Chart` value is
the key of the first host in that order the song is on (null for none, which the
filter list shows as the dash), the links file carries `{key: {<host>: id, lb: hash}}`,
and both `web/links.py` and `static/js/links.js` build a link only from a host's own
template and only for an id in its class. Adding a host is one entry there plus the
lookup tool that fills its registry section; Chorus Encore (`enchor`) is the only
host today. `tools/enchor_lookup.py` resolves each song against Chorus Encore offline (exact
title and artist, then the Expert guitar note count, then the charter; the probe in
`tools/enchor_probe.py` showed Enchor's hash filter is not the notes file's MD5) into
`caches/<header>_links.json`, keyed by `SongKey`, and `web/links.py` publishes the sure
answers as `data/links.<hash8>.json` (immutable class, `boot['links']`, `state.links`
after `load.js`'s `loadLinks()`). The page never contacts either service: the anchors
(`static/js/links.js`, `linkAnchors()`) are built from that file, each value checked
against its character class before it enters a URL template, so a hand-edited
registry can cost a link and never point at another host. The leaderboard half
(`tools/leaderboards_lookup.py`, `lb` in the file, `LEADERBOARD_INSTRUMENT` in
`instruments.py`) waits on the leaderboards maintainer's answer about batch reads of
api.clonehero.net; `web/links.py` and the page already handle an `lb` value.

Three explanatory surfaces, and the split is deliberate. The "How it works" panel
on the charts page is `labels.EXPLAINER` - what D measures, how the tiers read,
what the formula cannot see, where the numbers come from - led by the engine
author's explainer video. `about.html` is `labels.ABOUT`, a page of its own
because the people who need it are not the people asking what D means: they want
to know whether this is the official site, whether songs can be downloaded here,
and who to complain to, and all three answers deserve a URL to point at. Keep its
independence wording accurate if the relationship to upstream ever changes.
`methodology.html` is upstream's `Methodology.md` itself, rendered at publish (and
at serve start) by `web/markdown.py`, a stdlib subset renderer that supports
exactly the constructs the file uses and raises `MarkdownError` naming the line
on anything else (a list, a link, fenced code, an unknown LaTeX command), so an
upstream edit fails publish loudly rather than shipping literal asterisks; the
seven display formulas become MathML Core through its own typesetter, no CDN. The
page names the upstream file as the source of truth (`labels.METHODOLOGY_SOURCE`)
and this fork never edits `Methodology.md`; a correction goes upstream. A fourth
page, `library.html` (`page.render_library`, section 20), is the library in
numbers: charts per sheet and level with the distinct count under each, the
Expert charts per Calc Tier as bar tables (a `span` of the brand colour, no
script), official against custom, the ten highest D per sheet linked into the
table, and the packs in the registry's order; every number is `frames.counts`
over the same frames the page serves, so the page and the table cannot disagree.
It exists exactly when the changelog does (both need the pack join), and the
footer lists only the document pages the site has (`boot['docPages']`, filtered
in `page.build`), so a serve with no cache links neither. The document pages are
static text with one script, the theme's (`page.THEME_SCRIPT`).

The video iframe is built on first open and never before, so a visitor who does
not open the panel makes no request to YouTube; it is the no-cookie host, with no
autoplay. Closing the panel posts a `pauseVideo` command to it - `display:none`
does not stop an iframe playing audio - which is why the embed URL carries
`enablejsapi=1` and the command names YouTube's origin rather than `*`.

Every mention of fretwork or its author in the prose is a link, to the engine's
repository or to the channel. Those strings carry a minimal `[text](url)` markup
rather than HTML: `rich()` in `static/js/dom.js` and `rich_text()` in
`web/page.py` are the two renderers, they escape every character, they build the
anchors themselves, and they emit an anchor only for an `http(s)` target (a new
tab) or a bare same-site page name such as `methodology.html#calctier-calibration`
(the same tab; never a path or a query, so data could not smuggle `javascript:`).
Keep them in step - the same strings go through both, one for the panel and one
for `about.html`. The four URLs are named once at the top of `labels.py`
(`ENGINE_REPO`, `CHANNEL`, `FORK_REPO`, `VIDEO`).

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

The table's DOM is a window of the view, not the view (section 17):
`table.compute()` sorts and filters into `state.view` and `table.paint()` writes
the rows around the scroll position, `OVERSCAN` (40) rows beyond each edge of
the screen, between two spacer rows (`markup.padRow`, class `empty pad` so the
widths stylesheet skips them) standing for the rest at an estimated row
height. Rows wrap, so the estimate is measured from each paint
(`state.window.next`) and used by the next one, while `state.window.avg` is
what the current spacers were built with and the only thing that maps a scroll
position back to a row index (`wanted`); after every paint the scroller is put
right for the new geometry by the table itself (`overflow-anchor: none` on
`.fw-wrap` keeps the browser from adding its own correction): a scroll-driven
paint keeps the row under the screen's top where it was (the anchor), and when
nothing painted before is painted now (a long jump, a sort) the row the
position asked for goes to the top, so a changed estimate never leaves the
screen over unpainted rows and a sort keeps the place in the list. `draw()` is both, and every caller that changes what
the table shows still calls `draw()`. The scroll listener paints synchronously
when a row on screen comes within half the overscan of a painted edge
(`windowStale`: the screen's rows, unclamped, never the wanted window's,
which is clamped at the view's ends and would leave the first rows a spacer
after a fast scroll down and back). Anything that needs a row that may not be painted goes
through the view: the arrow keys, PageUp/Down, Home and End walk `state.view`
by index (`router.moveTo`, `table.viewIndexOf`) and `table.revealIndex(i)`
paints the window around the row first and scrolls to it second, since a scroll
position set before the paint is clamped to the old height; a shared `?code=`
reveals the same way. Rank is the index in the view, so it is continuous
across paints. Focus and the tab stop survive a paint while their row is
painted; a suite that reads every row must read the data, not the DOM
(`tests/page/window.js` is the contract, and only the `--site site/Local` run
exercises the real case, since the fixture's sheets are painted whole).

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

The palette is a set of roles, not colours, with two values each (section 15;
the tokens and their ratios are the top of `static/css/app.css`). Magenta is the
brand and means only "on" or "do this": an active chip, a pressed toggle, the
primary button, the sorted header, the open row's edge. Links are the blue
(`--fw-link`), the code column included. The graph's four curve colours (~D and
the three lines under it, `--fw-curve-d/nps/vps/kps`, which every family shares
in `plot.py`'s assignment) and the three compare series (`--fw-series-a/b/c`,
magenta, cyan, gold) are two separate sets, so no colour changes meaning when
a second chart is added. The four level colours (`--fw-easy/medium/hard/expert`)
keep `xlsx_format.py`'s hue families, saturated for each ground. `--fw-brand`
(`#b71fb7`) is a **fill**: white on it is 5.4:1, but as text on the dark ground
it is under 3:1, so text in the brand colour is `--fw-brand-text`. `--fw-dim`
replaces Bootstrap's `#6c757d`, which its `.text-secondary` utility and its
outline buttons hardcode. Bootstrap's own variables (`--bs-body-bg`,
`--bs-tertiary-bg`, `--bs-border-color`, the link and primary colours) are
bridged to the tokens once in `app.css`, so its table, form controls and
dropdowns stand on the page's ground in both themes; its button colours are
baked into the compiled CSS rather than read from `--bs-primary`, so the button
overrides set `--bs-btn-*` per variant, and its focus glow, checked box and
focused search box are blue unless overridden, which they are. There is one
ground: the pane and the canvas paint `--fw-bg`, never a colour of their own.
Two themes: `data-bs-theme` on `<html>`, dark or light, decided before the first
paint by `page.THEME_SCRIPT` (a stored `fw.theme`, else the OS) on every page
including the document pages and the 404, which carry their own two palettes;
`static/js/theme.js` is the header's toggle and the `fw:theme` event the pane
redraws on. Everything the page renders as text measures 4.5:1 or better on its
own ground in both themes and every swatch or clickable thing 3:1;
`tests/page/contrast.js` audits both. Keep it there.

### `packs.toml` is the registry of what is on the site

Every top-level folder under the library is a pack, and `packs.toml` at the repo
root names each one (`name`, `folder`, `source`, `added`, `notes`) and carries the
site's own dated `[[change]]` entries. `functions/packs.py` (stdlib only) loads and
validates it, joins it to the cache by folder (`resolve()`: the first path
component of each `song_path` under the library root, recovered from the songs
when the stored `search_path` is relative), counts songs and charts from the cache
(never stored in the file), and is the one writer (`append_pack`, which proves the
result with a re-read before renaming it into place). Publish refuses a folder
the registry does not name or a registered folder the cache does not have; serve
only warns, since it is for looking at any header's library. The join produces
the page-built `Added` column (`frames.with_added`, appended before `Pct`),
`changelog.html` (`page.render_changelog`) and `library.html`
(`page.render_library`), and links the strapline to the changelog.
`instruments.SCORED_INSTRUMENTS` is what "charts on the site" counts through; no
instrument name is spelled outside `instruments.py`.

### `web/` is the viewer, and only the viewer

Root `serve.py` and `publish.py` are thin entry points in the same shape as the other three: docstring, one orchestration function, `main()`. They share everything below; publish writes what serve serves. Everything else lives in `web/`, a namespace package (no `__init__.py`, matching `functions/` and `parsers/`). It is named `web/` rather than `serve/` because a `serve/` directory beside `serve.py` loses to the module in Python's import resolution and would be silently unimportable.

| Module | Responsibility |
|---|---|
| `web/frames.py` | Reads the metrics `.xlsx` into JSON-safe rows, and lists its codes. `unify()` (section 23) gives every sheet one shape whatever its profile calls the columns: the Drums sheet's `D_1x` and `NoteCount_1x` are read as `D` and `NoteCount` (the 1x reading is what the site ranks; `D_2x` and `NoteCount_2x` stay beside them) and the Vocals sheet, Expert only and without a `Level` column, gets one reading `Expert`, so the page, the percentile, the counts and the song pages key on `D` and `Level` alone. Adds the page-built `Pct` column (a per-sheet, per-level percentile of `D`, `rank(method='max')` floored to 0-100, `Int64`), which exists on the site and in serve and never in the spreadsheet; `counts()` is the library page's numbers. The only pandas importer. |
| `web/boot.py` | Builds the JSON payload the page reads (the sheet manifest, never the rows; `render` is the four numbers that shape the graph, no colour), and escapes `</` in it. |
| `web/page.py` | `build()` composes a header's page; substitutes `index.html`'s placeholders in one regex pass. `render_doc()` fills `doc.html` for the document pages (`about.html`, `changelog.html`, `library.html`, `methodology.html`). |
| `web/markdown.py` | The markdown subset renderer behind `methodology.html`: block and inline allow-lists, the LaTeX-to-MathML typesetter, `MarkdownError` on anything else. `python -m web.markdown FILE`. |
| `web/methodology.py` | `load()` parses `Methodology.md` and `check_tables()` compares its six calibration tables to the three formula modules (each remap table is headed by its constant's name, the CalcTier table names each family's module in its Home column), raising `MethodologyDrift` for a table it cannot read and returning the numbers that differ as a list of drifts. This fork never edits `Methodology.md`, so a drift is printed at publish and serve and put on the page as a note, never fixed here; `KNOWN_DRIFT` is the set upstream has been told about, `tests/test_methodology.py` pins it and `python -m web.methodology` exits non-zero on any other, for CI and after an upstream merge. |
| `web/links.py` | The offline link registry's published form: `data/links.<hash8>.json` with each song's Enchor md5 and sure leaderboard hash, values filtered by character class; `None` when nothing is known. |
| `web/bootstrap.py` | Bootstrap fetch/cache plus `FALLBACK_CSS`, its own fallback branch. |
| `web/assets.py` | `load_assets()`: the bundle, stylesheet, favicon and Bootstrap under hashed names; the content-type table and `cache_class()`. |
| `web/bundler.py` | Concatenates the ES modules into one file, refusing any import or export form outside its whitelist. |
| `web/graph.py` | `GraphRenderer`: lazy cache load, `lookup`/`render` per code (the same per-family calls `render.py` makes), memoised `png` and `curves` for serve; `curves_bytes()` is the curve JSON, v2: `{v, family, step, window, tau, n, head, series: {key: counts}, d: {geo: [...]} | {sum: {key: weight}}}`, one shape for the three families (`FAMILY_SERIES`). |
| `web/bundle.py` | Publish only: write-if-changed, the two products per chart (PNG and curve JSON) with their manifests, and the never-delete-what-we-did-not-write rules. |
| `web/handler.py` | `MetricsHandler`: routing and response writing only. |
| `web/server.py` | `MetricsServer`: carries the handler's dependencies. |
| `web/banner.py` | The terminal output: serve's startup/shutdown, publish's summary. |

The page's markup, CSS and 23 ES modules live under `web/static/`; `page.build()` returns `Built.files`, `{relative name: bytes}` for every file the site is (graphs excepted), which publish writes and serve serves from memory at `'/' + name`, so the two answer the same bytes with the same cache headers. Keys never derive from a request path, so traversal is impossible by construction rather than by guard. Server data reaches the JS through a `<script type="application/json" id="fw-boot">` island that `boot.js` parses once and re-exports; `boot.py` escapes `</` so spreadsheet text can never close the tag. The rows are not in it: `state.data` fills from `load.js` (`loadSheet`, one in-flight promise per sheet, a `fw:sheet` event on arrival, an idle prefetch of the other sheets, none under Save-Data), `cols()` reads the manifest so the header and chooser paint before any row, and `draw()` shows a loading row (class `empty loading`, so the widths stylesheet skips it) until then. `readUrl()` picks a shared `?code=`'s sheet from its instrument letter (`sheetOfCode`). All mutable page state lives in one exported `state` object because ES module imports are read-only bindings. `labels.PREFS_VERSION` is stamped into `localStorage` as `fw.v`; bump it when `DEFAULT_HIDDEN` changes and a returning visitor's saved column set is replaced by the new default once (order and widths are kept).

Two things must stay off the server's startup import path: matplotlib (via `functions/plot.py`) and openpyxl (via `functions/xlsx_format.py`). `GraphRenderer` imports plot inside its method bodies, and nothing in `web/` imports `xlsx_format`.

Before running Build, `config.SEARCH_PATH` must point at a real song library (the committed value is a Windows placeholder). Build on a ~3k-song library takes several minutes; midi parsing dominates.

`--diff-mode CalcTier|RemapDiff` and `config.DIFF_WRITE_MODE` **write to the user's `song.ini` files**. `Restore` rewrites them from the backup CSV and skips analysis entirely. Treat these as destructive to user data.

Three test commands, all stdlib plus the venv, mirrored in `.github/workflows/ci.yml`:

```
python -m unittest discover -s tests -t . -v
python tests/pipeline_test.py --keep /tmp/fw-ci --bootstrap-css caches/bootstrap-5.3.8.min.css
python tests/page/run.py --site /tmp/fw-ci/site/Fixture
```

`tests/fixture.py` generates a synthetic 15-song library (nothing real, never committed; its `SONGS` table is the interface every count derives from). `tests/pipeline_test.py` runs build, analyze, publish and deploy against it as subprocesses from a temporary directory with a stub `aws` on `PATH`. `tests/page/run.py` stages a published bundle, injects one suite module per page, and drives it in headless Chrome (Windows Chrome from WSL), reading results out of a `<pre id="results">` block; every suite reads its expectations from the boot payload, so `--site site/Local` runs the same twenty-five suites against the real library. The 390 px layout is measured inside an iframe (`tests/page/narrow.js`) because headless Chrome floors its viewport at 500 px; the spec calls that measurement `frame.html`. `tests/README.md` lists the harness gotchas.

The fixture does not exercise real-library shapes, so a change to parsing or metrics is still checked by building, analyzing and inspecting the terminal summary / xlsx / error CSV against a small local library. The convention is a gitignored `songs/` folder at the repo root holding song folders copied from a real library, then stripped to chart-only with `tools/sanitize_songs.py` (it deletes audio, art, video and editor scratch from song folders and leaves `song.ini`, `notes.chart`, `notes.mid` and anything it does not recognise; dry run by default, `--apply` to delete). So do not expect audio in `songs/`, and the pipeline does not need it, since build, analyze and render only ever open those three files; `tools/ingest_pack.py` runs the sanitizer on every pack before it lands there. It still must never be committed:

```
python build.py --search-path songs --header Local
python analyze.py --header Local
```

## Architecture

### Three-stage pipeline keyed by HEADER + timestamp

`build.py` -> cache `.pkl` -> `analyze.py` -> metrics `.xlsx`; `render.py` reads the same cache to draw PNGs. Every output is named `{header}_{kind}_{timestamp}.{ext}` via `functions/timestamp.py`, and `config.OUTPUT_DIRS` routes each kind to a folder (`caches/` for cache, errors CSV, and backup; `metrics/` for xlsx; `renders/` for PNG). Analyze and Render locate the *newest* cache for a header by globbing `{header}_{kind}_*` and taking the newest **mtime** (`timestamp.latest_output`), so the filename prefix is load-bearing and a copied or touched old file wins. Analyze reuses the cache's timestamp for its xlsx so the pair can be matched.

All of these outputs are gitignored (`*.pkl`, `*.csv`, `*.xlsx`, `*.png`, `caches/`). The `.xlsx` and `.png` files under `metrics/` and `renders/` are committed examples that were force-added; don't expect new outputs to show up in `git status`.

### The cache is the data contract

The pickled cache shape is documented at the top of `functions/cache.py`. Everything downstream (analyze, render, curves, density) consumes `notes = {'time_ms': ndarray, 'lanes': ndarray uint8}` per (song, instrument, level); drums entries instead carry `notes = {'hand_mask': {...}, 'kick_mask': {...}}`, two streams of that same shape, with the song's `roll_spans` beside them in `entries_by_code`; vocals entries carry a sung stream (`time_ms`, `end_ms`, `pitch`, `is_placeholder`, `is_slide`) with `talkie` and `percussion` streams beside it, at Expert only. `difficulty.FAMILY_KEYS` names each family's shape and `difficulty.scorable(entry)` checks it. Star-power and solo spans are no longer parsed or cached (upstream dropped them in the 2026-09-10 merge; the publish fingerprint stopped reading them at the same time). Both parsers must emit exactly that shape. Each song's `meta` holds nine keys from `song.ini` (`build.META_KEYS`): `Name`, `Artist`, `Charter`, `Release`, `Official`, `Genre`, `Year`, `Album`, plus `Difficulty`; only the six `difficulty.HEADER_META_KEYS` reach the graph header and its fingerprint, so a cache rebuilt for the other three re-renders nothing.

**Lane encoding**: one `uint8` bitmask per note timestamp. Bits 0-4 are GRBYO frets, bit 7 is open. Bits 5-6 are reserved (chart tap/force modifiers) and unused. Strum/HOPO/tap state is deliberately discarded by both parsers.

**Retrieval codes** (`04821993XG`): 8 digits from a SHA1 of the resolved song folder path (with linear probing on collision), then a level letter (E/M/H/X) and an instrument letter (G/C/R/B/K/D/V). Assigned in `cache.assign_codes` at build time and stored in `cache['codes']`. Render accepts codes without leading zeros. A code moves when its folder does; `song_key` (`cache.song_key`, 12 hex over every 5-fret stream, `SongKey` in the xlsx, hidden) does not: it is the identity that survives a re-download, and two folders holding the same charts share one. Each level entry also carries `notes_hash` (`cache.notes_hash`, 12 hex over `cache.stream_bytes(notes)`, `NotesHash` in the xlsx, hidden): the identity of one chart, which is what the page's `Copies` column and the distinct-chart percentile group on, keyed with `Type` and `Level` because a song's Hard often equals its Expert byte for byte and a Lead its own Rhythm. A vocals chart's hash covers its talkie and percussion streams too (`notes_hash(notes, *sides)`), so two spoken-only charts with different lyrics differ. `bundle.fingerprint` hashes the notes through `stream_bytes` as well, since the 2026-09-19 merge, when formula v2 moved every fingerprint anyway. Neither hash survives a change to `parsers/timing.py`, so never persist them across builds.

### Parsers (`parsers/`)

Build runs them in a fixed order: `ini_parser` first, then `mid_parser`, then `chart_parser`. When a song folder has both formats, **chart wins** (`build.build_note_index`).

- `parsers/timing.py` holds the shared tempo-map and tick-to-ms conversion used by both formats. Use `ticks_to_ms` (vectorized) for note arrays.
- `.chart` distinguishes level by section-name prefix (`ExpertSingle`, `HardDoubleBass`); `.mid` distinguishes level by pitch block within one track per instrument (`instruments.MID_PITCH_BASE`). Star power and solos are per-section in `.chart` but track-wide (shared across levels) in `.mid`.
- Songs that fail to parse are appended to an `errors` list as `(path, ErrorType, message)` and written to the errors CSV; a single bad file never aborts a build.

### `functions/instruments.py` is the single source of truth

Every instrument/level table lives there: canonical keys and iteration order, `.mid` track names, `.chart` section names (with legacy fallbacks), pitch bases, `song.ini` `diff_*` tags, code suffixes, open-note support, xlsx sheet grouping, and display labels. Adding an instrument means adding it here (and to `FAMILY`) and adding a calibration group in its family's formula module; nothing else should hardcode instrument names. `SCORED_INSTRUMENTS` is every instrument since the 2026-09-19 merge; `SONG_KEY_INSTRUMENTS` stays the five 5-fret keys forever, so `SongKey` (the song page URLs) never moved.

### `functions/difficulty.py` holds the shared difficulty block

`entry_difficulty(entry)` is one function per family (`FAMILY_DIFFICULTY`): the fret block (N, V, CoV, STAM, D) with the Expert-anchored `RemapDiff`/`CalcTier`; the drums block (H, T, K, CoV, STAM, D at the 1x reading, `D_2x` when the chart has double-pedal kicks) anchored the same way; the vocals block (P, R, A, S, CoV, STAM, D) whose tiers come straight from D, since vocals have one level. Every block carries `D`, so the site has one number to rank by. `web/graph.py` and `web/bundle.py` call it; `render.py` and `analyze.py` are upstream's and make the same calls themselves.

### `functions/labels.py` holds every human-facing string

The abbreviated keys (`pNPS`, `medVPS`, `CoV`, `DurationS`, and the drum and vocal modules' `pHPS`, `K_1x`, `pPPS`, `R`) are the data contract: they come out of the density and formula modules, flow through the dataframes in `analyze.py`, and become the xlsx headers. Nothing keyed off a column name should change. `labels.py` maps those keys to readable text at display time only, via `COLUMN_LABELS`, `COLUMN_HELP` (tooltips), `TIME_COLUMNS` (seconds shown as m:ss), `DISPLAY_ORDER` (left-to-right column order on the page, which is deliberately not `analyze.COLUMN_ORDER`, so the site can lead with `D` and seat the page-built `Pct` beside it without touching the spreadsheet), `DEFAULT_HIDDEN` (the columns a first visit does not show; search still looks inside a hidden column, and a filter set on one still applies, so hiding is display-only; `PREFS_VERSION` moves by one whenever this tuple changes, or a returning visitor never sees the new default), `VALUE_ORDER` (columns whose values are neither numeric nor alphabetical - `Level` and `Type`, both derived from `instruments.py` rather than respelled, and used for the filter list and the column's sort alike), `VALUE_LABELS` (display text for a stored value, currently Official/Custom for the `Official` booleans; the filter still matches the stored key), `FOOTER_LINKS` (the attribution links), `CURVE_FAMILIES` (per family, the lines under ~D on the graph: the curve file's key, the legend word, which is `plot.py`'s label, the readout word and the colour token; the three tokens `--fw-curve-nps/vps/kps` serve every family in `plot.py`'s own assignment, notes/hands/syllables, variability/travel/pitch, kicks/percussion) and `UI` (interface wording, including the copyright and licence lines). `label()` falls back to the raw key, so a new metric column degrades gracefully instead of raising. `boot.py` sends the labels and help for the columns the sheets have (`columns_present`), so the diagnostic columns `EXTRA_METRICS` drops cost the island nothing.

`serve.py` and `publish.py` consume it through `web/boot.py`; the pipeline itself does not. The xlsx headers and the render header are deliberately still raw keys, since changing them would alter committed example outputs and anything downstream that reads the spreadsheet by column name. Wiring either one up is a display-layer change through this module, not a rename in the pipeline.

### Metrics pipeline (`functions/*_density.py` -> `functions/*_formula.py`)

Three families, one density and one formula module each. `fret_density.window_arrays` slides a 1000 ms window in 250 ms steps from t=0 to the last note and produces raw NPS (note timestamps per window) and VPS (fret-change per window; see `fret_var`) samples; `calc_metrics` reduces those to peak/avg/median/std (the median and std over active windows only, formula v2); `fret_formula.calc_nvcov` turns them into `D = N * V * CoV * STAM` (the stamina term is a slow curve of the length, 1 at 230 s) and is instrument-agnostic within the family. `drum_density` windows the hand stream (hits per second, roll spans capped, and travel between pads) and each kick reading (1x single pedal, 2x every kick) on one grid; `drum_formula.calc_drum_d(metrics, mode)` is `D = (H + T + K) * CoV * STAM`, additive across limbs. `vocal_density` windows pitch travel and syllables over the sung and talkie streams with an occupancy gate; `vocal_formula.calc_vocal_d` is `D = (P * R * A + S) * CoV * STAM`, and returns its own `RemapDiff`/`CalcTier`.

**Expert anchoring**: `D` is computed per level, but `RemapDiff` (0-6 bins, per calibration group) and `CalcTier` (uncapped log tier) are computed once per (song, instrument) from the **Expert** level's D via each module's `anchor_remap_tier` (drums anchor to the 1x reading), and that pair is shown on every E/M/H/X row. If an instrument has no Expert chart, both are `None`/NaN. This is because `song.ini` only has one `diff_*` tag per instrument. Guitar, Co-op, and Rhythm share the `guitar` calibration group; vocals have one level, so theirs come straight from D.

The bin edges (`GUITAR/BASS/KEYS_REMAP_BINS` in `fret_formula.py`, `DRUM_REMAP_BINS`, `VOCAL_REMAP_BINS`) and the CalcTier constants (a `BASE_D`/`LN_INC` pair per module) are mirrored as tables in `Methodology.md`, both upstream's. `web/methodology.check_tables` compares them with exact equality on every publish and serve start (`python -m web.methodology` runs it alone) and reports the numbers that differ; upstream's document lags its code today (the Guitar bins and the drums `LN_INC`, `methodology.KNOWN_DRIFT`), which the page says under its source line. `labels.py` prints the CalcTier constants from the modules rather than as literals, so the page and the explainer cannot drift from the code either.

### Render path (`functions/curves.py` -> `functions/plot.py`)

Render recomputes from the cache rather than reading stored metrics. `curves.calc_curves` (fret), `calc_drum_curves` and `calc_vocal_curves` reuse their density module's window arrays, convert to rates, and apply a zero-phase EMA (`TAU_MS = 2000`). The plotted "~D" line is an approximation for display that omits CoV and STAM: `sqrt(nps * vps)` for the fret family, `hps + tps + kps` for drums (per kick reading; the PNG stacks 2x under 1x), `R * A * pps + S_WEIGHT * sps` for vocals, while the header's `D` comes from the real formula. Appearance comes entirely from `config.RENDER_DEFAULT` + `config.RENDER_THEMES`; `plot.py` uses the Agg backend and never opens a window. The site's page draws the same picture itself (`web/static/js/graph.js`, `smooth()` is the EMA in doubles, byte-for-byte equal to the Python loop, then ~D by the file's recipe) from the curve JSON `web/graph.py` writes (v2: named series and a `geo` or `sum` recipe; the drums file is the 1x picture, the site's D), so a change to `curves.py` or to the profile must keep the two in step: `tests/test_graph_json.py` and `tests/page/graph.js` share one pinned vector, and `tests/test_bundle.py` reconstructs every family's ~D from its JSON against `curves.py`. Never use `color_d` or `color_nps` as text: they are 3.09:1 and 3.67:1 on the figure background, enough for a line and a swatch, not for words.

### `song.ini` backup and write-back (`functions/ini_updater.py`)

Build **always** appends new songs to `caches/{header}_BackupData.csv` (append-only, deduplicated by `song_path`, one column per `diff_*` tag) regardless of config. It never writes to `song.ini`. When an instrument joins `DIFF_TAGS` after the file was written, `migrate_backup_header` rewrites the header once (run from `backup_data`, `restore_from_backup` and the top of `build_cache`), keeps every row, recovers a row already appended with the longer shape by position, leaves a longer header alone and refuses one it does not recognise; it is upstream's file, and the migration went upstream as PR #9, merged 2026-09-11. Analyze's write modes and Restore both go through `update_ini_values`, which patches matching `key = value` lines inside the `[song]` section in place, appends missing keys at the end of the section, and preserves the file's original encoding (utf-8 / utf-8-sig / utf-16 / cp1252) and newline style. Don't replace it with `configparser`; `song.ini` files routinely contain `%` and other characters that break it, which is also why `ini_parser.parse_ini` is hand-rolled.

## Conventions worth knowing

- `config.py` is user-edited configuration (paths, header, theme), not library code. The committed `SEARCH_PATH`/`HEADER` values are placeholders. `instrument_scan.py` is gitignored local scratch.
- `Difficulty` of `'-1'` (string in cache, int in xlsx) is the sentinel for "no `diff_*` tag in song.ini", and `Year` of `-1` (int in both) is the same sentinel for no four-digit year in the `year` tag; `labels.MISSING_VALUES` is where the page learns both, so a sentinel prints as a dash, sorts last and is in no range. `xlsx_format.BLANK_PREDICATES` keeps sentinels out of the color scales.
- `analyze.COLUMN_ORDER` defines xlsx column order; `xlsx_format.DEFAULT_HIDDEN_COLS` lists the diagnostic columns that are dropped unless `config.EXTRA_METRICS` is True, and `xlsx_format.HIDDEN_COLS` the identity columns (`SongKey`, `NotesHash`) that are always written but hidden in Excel. Excel sheet names are truncated to 31 chars. The page-build columns come after the xlsx ones in a fixed order, `Added`, `Copies`, `Pct` (`web/page.build`), and `frames.load_frames` reads the two hash columns as text so a one-row sheet whose hash is all digits keeps its leading zeros.
- Song identity everywhere is the resolved absolute folder path (`song_path`), which is also the join key between the ini table, note streams, backup CSV, and codes.
- Terminal progress uses `tqdm`; keep long loops wrapped so multi-minute builds stay observable.

## Working with the repo

This is a fork. `origin` is `github.com/ChaseFranz/fretwork`, the main line for the
web viewer and, on its own branch, the player rating. `upstream` is
`github.com/Staycation44/fretwork`, the original project (single maintainer, no CI,
no branch protection), and the source of parser, instrument and difficulty-formula
improvements. The viewer was offered upstream as PR #6 and closed unmerged on
2026-09-07; it is this fork's project now. Releases of the hosted site are tagged
`fretladder-vX.Y.Z` - a separate namespace from upstream's `vX.Y` tags, which
arrive with every fetch and must not be reused. Releases are few and meaningful,
not one per deploy (the maintainer collapsed a day's eleven into three): a tag at
the commit whose sources produced the live bundle, whose message is the release
notes, since pushing it publishes a GitHub Release from that message
(`.github/workflows/release.yml`). The `/release` skill (`.claude/skills/release/`)
is the procedure, with its two gotchas: a tag on a commit older than the workflow
file publishes nothing, and `gh` in this clone defaulted to the parent repository
until `gh repo set-default ChaseFranz/fretwork`, so check `gh repo set-default
--view` before any `gh release` command and never create a release or a tag on
upstream.

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
- **Never open a pull request against any repository without the maintainer's
  explicit approval for that specific PR.** A blanket "go ahead and implement" does
  not cover it: opening a PR publishes work under the maintainer's name to someone
  else's tracker, so ask, name the target repo, branch and what the PR would carry,
  and wait for a yes. Never open pull requests against `upstream` for viewer, scores
  or rating work at all. A genuine fix to the shared tooling (parsers, formula) can
  go upstream as a fork PR once approved, from a branch cut off `upstream/main`
  rather than off `main`.
- **`elo` is the rating branch**, secondary to the viewer: `ScoreData.md` and
  `SkillRating.md` so far. Merge `main` into it periodically; it merges to `main`
  only when there is code worth shipping. The rating never touches `web/`.
  `screenshots` is an orphan branch holding the four PNGs upstream PR #6 embeds
  by URL and is kept for that reason; `hosting` was merged in `5e9f6b7` and
  deleted. `backup-header` was the branch behind upstream PR #9, merged on
  2026-09-11, and is deleted.
- **Merge commits only, short informal one-line messages**, matching upstream.
  Example outputs under `metrics/` and `renders/` are force-added; if you regenerate
  them, `git add -f` the new files and remove the stale ones in the same commit.
  Never commit caches, backup CSVs, `songs/`, or a real library's metrics.
- **CI runs the tests on every push**, but the fixture is synthetic. After merging
  parser or metrics changes from upstream, still run build, analyze and render
  against `songs/` and compare the terminal summary and error CSV with the previous
  run, since the fixture cannot see a real library's shapes.
- **The plan for the site is `docs/spec/`**: the numbered sections, one per
  piece of work, and a `README.md` index with the implementation order, the
  cross-section decisions and the follow-ups that wait on information we do not
  have. Pick up a section by reading the index, then `05-data-model-v2.md` (the
  data model every section conforms to), then the section. When a section lands,
  update its status row in the index and keep this file in step with what changed.
