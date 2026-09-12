# 16. Share previews and permalinks

**Status:** Ready. Written 2026-09-12 against `main` at `e23f592`, from the code and the Local library (1,748 songs by `SongKey`, 11,904 charts).

**Effort:** M. One new render in `web/page.py` writing a page per song, a sitemap, a fourth deploy class for the `song/` folder, a Share button in the pane, one rule in `main.js`, a suite and the allow-lists.

**Depends on:** 05 (`SongKey`, the sheet files), 14 (the pane, `?song=` resolution), both landed.

## Goal

A link to a chart pasted into Discord, Slack or a tweet previews as the song: its title and artist, and its Expert difficulty on each instrument, rather than as "fretladder" with the site's one preview image. A Share button in the pane puts such a link on the clipboard. The same pages give crawlers a URL per song.

## Why

Links are how a site like this spreads: someone asks "how hard is this chart" and someone answers with a link. Today every link previews the same way, because a static site serves one `index.html` and one set of tags (`page.meta_head`, `web/page.py:73-85`): `og:title` is `config.SITE_NAME`, `og:description` the site's description and `og:image` the one chart publish still renders as a PNG (`page.OG_IMAGE`, `web/page.py:21`). The state a link carries lives in the query string (`url.writeUrl`, `static/js/url.js:37-43`), which an unfurler never reads. Section 07 named this as a follow-up when `?song=` arrived; the pane made the chart URL the thing people copy from the address bar, so the gap is what a visitor now sees first.

## Current state

- `page.build` (`web/page.py:273-307`) writes the entry pages into `Built.files`; `render_doc` (`:170`) fills `doc.html`; `changelog_pages` (`:247`) is the model for a page that exists only when its data does.
- `ROBOTS` (`web/page.py:28-33`) allows `/` and the preview image, disallows `graph/` and `data/`; no sitemap.
- The allow-lists a new folder must join: `deploy.BUNDLE_TOP` (`deploy.py:65-66`), `bundle.PAGE_TOP` (`web/bundle.py:47`) and `prune_page` (`:50-62`), `assets.cache_class` (`web/assets.py:44-50`) with its three classes (`:33-37`), and `deploy.plan` (`deploy.py:192-212`), which syncs `graph/` with `--delete` at the week class, the immutable folders without, and the page class with `--delete` excluding the three.
- `main.js:77-88`: a shared `?code=` opens the pane on that code once its sheet is here; `?song=` alone resolves through `song.primaryCode` once every sheet is here; a code wins over a song unconditionally.
- The pane's tool row (`pane.toolRow`, `static/js/pane.js:143-151`): the host links, Compare with a row, Save as PNG. `savePng` (`:350-365`) is the model for a client-side action with a toast on failure.
- `serve.py` serves `Built.files` at `'/' + name`, so anything publish writes under a folder is served locally too.

## Design

1. **One page per song, under `song/`.** `song/<SongKey>.html`, rendered by `page.render_song_pages(sheets, names)` from the rows: the primary folder's title and artist (the same choice as `song.folders`, official first, then Release, then title), and one line per instrument at Expert, `Expert Guitar: D 169.93, Calc Tier 8, at or above 97%`. `<title>` is `<Title> - <Artist> - fretladder`; `og:title` the title and artist; `og:description` the instrument lines joined with `; `; `og:url` and `canonical` the page's own absolute URL; `og:type` `website`; `twitter:card` `summary`. **No image**: the only PNG the site has is another song's graph, and a preview showing the wrong chart is worse than text; per-song PNGs are what section 06 retired (2.2 GB). 1,748 pages of about 900 bytes.
2. **The page forwards, and carries the exact view.** The body repeats the facts as text with one link, "Open on fretladder", so the page is not blank for a crawler or a visitor with no script. A `<meta http-equiv="refresh" content="0; url=../?song=<key>">` opens the app on the song. Before it, one inline script: `location.replace("../" + (location.search || "?song=<key>"))`, so `song/<key>.html?code=A&vs=B,C` opens exactly that comparison, and a link with no query opens the song's primary chart. Unfurlers read the tags and do not follow either; browsers follow the script, then the refresh.
3. **A moved code falls back to the song.** `main.js` learns one rule: with both `code` and `song` in the query, the code opens when its row exists once its sheet is here, else the song resolves as `?song=` does today. A code moves when its folder does (CLAUDE.md, retrieval codes); a `SongKey` survives a re-download. So a share link is stable by song and exact by code, and a stale one degrades to the song rather than to "render failed".
4. **Share is a button, not the address bar.** In the tool row after Save as PNG: `data-act="share"`, `UI.share` "Copy link", tip `share_tip`. It writes `config.SITE_URL/song/<key>.html?code=<state.graph>[&vs=...]` to the clipboard (`navigator.clipboard.writeText`) and toasts `share_copied`; when the clipboard API is refused (an insecure context, a denied permission) it falls back to selecting the URL in a prompt-free way: a temporary read-only input and `execCommand("copy")`, and toasts `share_failed` if that fails too. `SITE_URL` reaches the page as `boot['siteUrl']` (publish only; serve boots `null` and the button copies the address bar's URL instead, so the local page still works). The address bar keeps carrying the view as before.
5. **A sitemap.** `sitemap.xml`: the four document pages, `index.html`, every song page, `lastmod` the spreadsheet's date. `ROBOTS` gains `Sitemap: <SITE_URL>/sitemap.xml`. About 150 KB for 1,748 songs; the entry class, rewritten in place.
6. **A fourth deploy class.** `song/` is derived per song the way `graph/` is per chart and changes with the library, so it takes the week class: `assets.WEEK_DIRS = ('graph', 'song')` (`CACHE_GRAPHS` renamed `CACHE_WEEK`, the value unchanged), `cache_class` answering the week for both; `deploy.plan` syncs `song/` with `--delete` at the week class right after `graph/`, and excludes it from the page sync; `BUNDLE_TOP` and `prune_page` gain it (the pages are in `files`, so `write_page` writes them and prunes the stale ones the way it prunes `static/`). CloudFront's invalidation of `/*` covers a changed page within the week. First deploy: 1,748 PUTs, a fraction of a percent of the plan's monthly requests.
7. **Numbers on the page are the rows' numbers.** The instrument lines are built from the same `D`, `CalcTier` and `Pct` cells the table shows, formatted by the same rules (`D` to two places), so a preview never disagrees with the page it opens.

Rejected: a page per chart (11,904 files for the same preview text 6.8 times over; the code rides in the query instead); the site's preview image on every song page (misleading, see 1); serving the song pages at the entry class (1,748 `no-cache` objects revalidated on every hit, for pages that change with the library); a CloudFront function rewriting tags at the edge (it cannot read the data, and the per-song file is the data); `song/<key>` without `.html` (S3 static hosting needs the object name, and CloudFront's default root object applies only at the root).

## Data and interfaces

- `page.render_song_pages(sheets, names) -> {f'song/{key}.html': bytes}`; `page.render_sitemap(files, stamp) -> bytes`; `page.SONG_DIR = 'song'`.
- `page.song_facts(sheets) -> {key: {'title', 'artist', 'lines': [(sheet, level, D, tier, pct)]}}`, the one place the preview text is composed; `labels.UI['share_line']` `'Expert {sheet}: D {d}, Calc Tier {tier}, at or above {pct}%'` and `share_line_no_tier` for a tier of the dash.
- `assets.WEEK_DIRS`, `assets.CACHE_WEEK`; `deploy.BUNDLE_TOP` gains `'song'`; `bundle.prune_page` prunes `song/`.
- `boot['siteUrl']`: `config.SITE_URL` when `public`, else `None`; `boot.js` exports `SITE_URL`.
- `labels.UI`: `share`, `share_tip`, `share_copied`, `share_failed`.
- `pane.shareLink() -> string`; the `share` action in `initPane`.
- `main.js`: the code-else-song rule, in the place `shared.code` is read today (`:77-88`).

## Files touched

`web/page.py`, `web/assets.py`, `web/bundle.py`, `deploy.py`, `web/boot.py`, `functions/labels.py`, `web/static/js/boot.js`, `pane.js`, `main.js`, `web/static/song.html` (new template, self-contained like `doc.html`, no stylesheet link), `tests/test_page.py` (new: the song page and the sitemap), `tests/pipeline_test.py` (the folder, the class, the count against the fixture's songs), `tests/test_deploy_plan.py` (`plan` with the fourth class), `tests/page/share.js` (new), `song_url.js` (the fallback rule), `CLAUDE.md` (the bundle's four classes, the allow-lists sentence), `README.md` section 5 (Share) and 6 (the class), `docs/spec/README.md`.

## Steps

1. `song_facts` and `render_song_pages` with the template; `python -m unittest tests.test_page` checks one page per key, the title, the two tags, the refresh target and that no page names a file. Commit: `a page per song under song/, with the preview tags a shared link needs`.
2. The sitemap and the robots line; the unit test counts its URLs. Commit: `sitemap.xml over the document pages and the song pages`.
3. `WEEK_DIRS`, `cache_class`, `prune_page`, `BUNDLE_TOP`, `plan`; `tests/pipeline_test.py` sees `song/` written, pruned when a song leaves the fixture, synced with `--delete` at the week class and excluded from the page sync. Commit: `song/ is the fourth deploy class, a week, synced like graph/`.
4. `boot['siteUrl']`, the Share button, `shareLink`, the four strings; `share.js`: the button exists, its link names the song page with the code and the comparison, the toast, serve's fallback (`siteUrl` null in the fixture's serve-parity stage). Commit: `Copy link in the pane: the song page with the exact chart`.
5. The `main.js` rule; `song_url.js` gains a launch with `?song=<key>&code=00000000XG` that opens the song. Commit: `a shared code that has moved falls back to its song`.
6. `CLAUDE.md`, `README.md`, the index row. Commit: `spec index: 16 on main`.

## Verification

- Unit: `tests/test_page.py`, new (a page per key, the tags, the refresh, the sitemap count, no placeholder survives, the text equals the rows' numbers); `tests/test_deploy_plan.py` (`plan` has the `song/` sync with `--delete` at the week class, before the page sync, which excludes it).
- Pipeline: `song/` present with as many pages as the fixture has keys, each under 2 KB, `cache_class('song/x.html')` the week, the stub `aws` log showing the sync.
- Page: `share.js` (the button, the link's shape for one chart and for a comparison, the toast); `song_url.js` (the fallback).
- By hand after the deploy: paste a link into Discord and read the embed; `curl -sI https://fretladder.com/song/<key>.html` shows the week's `cache-control`.

## Risks and gotchas

- Discord caches an unfurl per URL for a long time; a page's text changing with the library does not refresh an already-posted embed. Acceptable: the numbers in an embed are the numbers at the time of the post.
- `navigator.clipboard` needs a secure context; serve on `http://127.0.0.1` is one (localhost is secure), the fallback covers the rest.
- A `SongKey` that is all digits is text in the rows (`frames.load_frames` reads it as text); the file name must be the string, never a number.
- `check_site.py` check 5 asserts the robots text equals `page.ROBOTS`; the sitemap line changes both.

## Out of scope and follow-ups

- A preview image per song: would need a PNG per song (1,748, not 11,904) drawn at publish from the curve JSON by the Python side; about 300 MB. Possible later; not until someone misses it.
- A page per pack under `pack/`: the changelog already anchors each.
- Structured data (`schema.org/MusicRecording`): no consumer is known.
