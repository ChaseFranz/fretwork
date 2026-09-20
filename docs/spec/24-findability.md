# 24. Findability: getting indexed, and matching the words people type

**Status:** In progress (2026-09-19). Written the evening of the v1.6.0 deploy, from the maintainer's "really think hard about the SEO of this website, I want it really easy to find", against `main` at `88eee92`, with the live site measured from the outside.

**Effort:** M for the on-site half (this section); the off-site half is the maintainer's and is listed at the end.

**Depends on:** 21 (the site as a crawler sees it) and 22 (the pages for the queries), both live. This section is what those two left undone, measured twelve days after launch.

## Goal

A search for a song, a game's setlist, or "hardest Guitar Hero / Clone Hero songs" finds the site. Concretely: every page of the site indexed by Google and Bing within a few weeks, each page titled and worded in the vocabulary people type, the front page readable and linked without JavaScript, and the crawl budget of a new domain spent on the 2,315 real pages rather than on 18,766 duplicates of the front page.

## Why

Sections 21 and 22 made the pages readable and gave them titles; they did not check whether anyone could find them. Twelve days after launch and seven after the sitemap was submitted, nobody can.

## Current state

Measured 2026-09-19 from outside, on the v1.6.0 bundle:

- **Indexing.** `site:fretladder.com` on Google returns nothing, and so does a search for a song page's exact title (`site:customsongscentral.com` through the same tool returns pages, so the operator works). Bing returns nothing. DuckDuckGo has three pages (`/`, `about.html`, `changelog.html`). Search Console was verified and the sitemap submitted on 2026-09-12; its coverage report is the maintainer's to read.
- **The front page without JavaScript** (what a crawler fetches first, and what Bing mostly indexes): 25,708 bytes, 18 words, one link (the strapline to the changelog), no `<noscript>`. After rendering, 1,271 words and 58 links, but rendering is queued and rationed for a domain with no authority. The one `h1` is the brand, "Fretladder". Every link from the front page to a song, game or list page exists only in the footer `main.js` builds.
- **Duplicate URLs.** Every number on a song, game, list or library page links `./?code=<code>`: 18,766 distinct query variants of the front page, each canonicalised back to `/`, each a URL Googlebot queues and fetches before it learns that. A new domain is crawled at tens to hundreds of URLs a day.
- **Titles against the query vocabulary.** Google autocomplete for the niche's seeds gives: "clone hero difficulty chart / spreadsheet / list / levels", "clone hero hardest song", "hardest clone hero chart", "guitar hero hardest song on expert", "guitar hero difficulty chart", "rock band hardest drum song", "rock band 4 hardest guitar songs", "guitar hero 3 songs list", "guitar hero 3 songs clone hero", "clone hero charts spreadsheet", "through the fire and flames clone hero chart". The song pages are titled "{song} by {artist}: chart difficulty - Fretladder", with no game and no "Clone Hero" or "Guitar Hero" in the title or the `h1` (the `h1` is the song name alone); 110 of the 2,260 titles are duplicates (a song in two games), of which one stays ambiguous once the game is in the title. Game pages are "{game} setlist by difficulty" with the `h1` "Fretladder – {game}"; people type "song list". The lists are titled well.
- **Depth.** Song pages are 126 to 275 words (median 176), two sentences of prose and a table. The pages that rank for "hardest guitar hero songs" are 1,400-word listicles with an `h2` and a picture per song (TheGamer, Attack of the Fanboy, 2021); the Wikipedia setlist pages are tables with tiers and prose. Our lists are 1,582-word tables with no picture, though the site draws a picture of every song.
- **Sitemap.** 2,315 URLs, every `lastmod` the publish date, so every deploy says every page changed; Google discounts a `lastmod` that is never selective.
- **Structured data.** `MusicRecording` on song pages, which no search feature reads; no `BreadcrumbList`, `ItemList`, `WebSite` or `Dataset`.
- **Links to the site.** The fork's README and the closed upstream PR #6 comment, both on GitHub. No forum, wiki, Discord or YouTube mention found; upstream's README does not link the fork. No community post has been made (section 01's are the maintainer's).
- **Speed.** PageSpeed Insights answered 429 without an API key; unmeasured here. The pages are small and brotli-compressed, the assets immutable; the front page fetches the 452 KB (compressed) Guitar sheet before it paints rows.
- **Plumbing that is right:** `http` and `www` answer 301 to the apex, canonical on every page, `robots.txt` allows `data/` and the pictures, the document pages carry `<base>`, no `x-robots-tag`, `lang="en"`.

## Design

1. **The front page is a page without JavaScript, and the same page with it.** `index.html` gains a site guide, `<details id="static" open>` above the footer: a summary line, an `h1` that says what the site is in the query's words ("Difficulty ratings for Guitar Hero, Rock Band and Clone Hero charts"), a paragraph on how the ratings are made and what the site holds (the counts from the frames), the ten hardest Expert charts per instrument as a real table with each song linking its page (`frames.counts`'s `hardest`, which the library page already draws), and a link to every game page, every list and every document page. The brand in the header becomes a `<p>`, so the page has one `h1`. It is open in the HTML, so a crawler that does not run scripts, a reader mode and a visitor without scripts get a page; the inline script right after it closes it before the first paint, so the app shows one summary line under the table that a visitor can open; open, it takes at most 45vh and scrolls. It is never removed: the first design removed it at boot, and the pre-deploy review reproduced what that means, that the DOM Google renders and indexes had no `h1`, eight words and one link, the opposite of the goal, and a shape close to cloaking (one page for the crawler, another for the visitor). A `<details>` block is the same content for everyone, and Google indexes what a closed `details` holds. About 14 KB. Rejected: removing it at boot (above); `<noscript>` (not in the rendered DOM either); a separate landing page (the home URL is the one every link will point at); prerendering the app's table (the rows are 1.4 MB).

2. **Titles and headings carry the game and the words.** Song page: `{song} by {artist}: {game} chart difficulty` for a chart matched to a game, `{song} by {artist}: Clone Hero chart difficulty` for a custom (`fact['release']` is the game or the literal `Custom`), with the pack in brackets when the same custom is in two packs, so no two song pages share a title; no site suffix on the song pages, since they are the site's longest titles (median 79 characters with the game) and a result shows the site's name on a line of its own from the `WebSite` block and `og:site_name`. The `h1` becomes "{song} by {artist}" and a line under it names the game and the pack. The description opens with the question people type, "How hard is {song} by {artist} in {game}?", then the parts, whole ones only, while they fit 155 characters (`song_description`), so a result never cuts it mid-list. Game page: title `{game} song list ranked by difficulty - Fretladder`, the `h1` the title without the brand (the brand becomes a link above it on every document page, as on the song pages). The list intros gain a sentence saying the list is computed from the chart files, not voted, in the words "difficulty list" and "difficulty chart".

3. **No query variants of the front page.** Every `./?code=X` and `./?song=K` link on a song, game, list or library page becomes `./#code=X` and `./#song=K`. A fragment is not a URL to a crawler, so the front page has one crawlable address. `url.js readUrl` reads `location.hash` as the query when there is no search string, and `writeUrl` then writes the query form as before, so the app's own state, Copy link and every existing shared link are unchanged. Rejected: `rel="nofollow"` (a hint, not a rule); dropping the links (the numbers should open the graph).

4. **An honest sitemap.** `lastmod` per page is the day the page's bytes last changed: publish keeps `caches/<header>_pagedates.json`, `{path: [hash8, date]}`, compares each page file's hash with the previous publish's and moves the date only when the bytes moved. A song page whose numbers did not change keeps its date across deploys; a full re-render (v1.6.0's) moves them all, which is true. Serve has no manifest and keeps the sheet date.

5. **IndexNow on deploy.** Bing, Yandex, Seznam, Naver and (through Bing) DuckDuckGo take a list of changed URLs by one POST. `FRETWORK_INDEXNOW_KEY` in `.env` (32 hex; not a credential, the key file is public by design) makes publish write `<key>.txt` at the root and deploy POST the pages this publish rewrote (every sitemap URL on `--no-publish`) to `api.indexnow.org` after the invalidation completes. No key, no file, no call. Google does not take IndexNow; for Google the sitemap, the links and Search Console's "Request indexing" on the hub pages are the levers.

6. **Structured data a search feature reads.** `BreadcrumbList` on song, game and list pages (Charts > Game > Song; Charts > The library > List, since the library page is where the lists are linked from); `ItemList` on the lists and the game pages (position, name, url for each entry, which is what a ranked list is); `WebSite` with a `SearchAction` on the front page (`/?q={search_term_string}`, which the app already reads; Google no longer shows the sitelinks search box, but the block is what names the site in results) and `og:site_name` on every public page; `Dataset` on the library page, which Google Dataset Search indexes and which is a channel of its own for "guitar hero difficulty data", with what it measures and no `distribution` (the sheet files are hashed and the next deploy deletes them) and no licence claim over the charts. `MusicRecording` stays. A list page exists only with three or more songs (`LIST_LEAST`): "The 1 hardest ..." is not a list.

7. **The lists carry pictures and a method paragraph.** The top three entries of each list get their song's picture above the table with a caption, the alt text naming the song and its lines, so the list pages have images to rank in image search and a shape closer to what ranks; the intro says in one paragraph what the numbers are and why the list differs from a poll. No hand-written prose per song: the data is the content.

8. **Every game and list page links the others.** A "More" block under the table on game and list pages lists every game page and every list, so a crawler that lands on one reaches all 49 and the link equity spreads; song pages keep their game link and the library link (49 more links on 2,260 pages would be bloat).

Rejected for now: splitting `songs.html` by letter (2,301 links on one page is within what crawlers follow); artist pages (thin); a blog; `hreflang`; paid tools.

## Data and interfaces

- `page.render_page(title, source, names, boot_json, public, linked, static_html)`; `page.static_section(sheets, resolved, names)`; `labels.UI['home_h1']`, `home_intro`, `home_hardest`, `home_games`, `home_lists`, `home_more`.
- `labels.UI['song_page_title']` takes `{game}` and drops the site suffix; `song_custom_game`; `song_desc_lead` ("How hard is {song} by {artist} in {game}?"); `song_where*` (the line under the h1); `game_title` becomes "{game} song list ranked by difficulty"; `list_method`, `list_short_*`; `more_games`, `more_lists`; `breadcrumb_home`; `home_summary`, `home_h1`, `home_intro`, `home_hardest`, `home_games`, `home_lists`, `home_more`; `site_title` and `description` name Rock Band too. `page.song_description(lead, lines)`, `page.DESCRIPTION_MOST`, `page.LIST_LEAST`.
- `page.frag(query)`: the fragment form of an app link; `url.js readUrl` accepts `location.hash`.
- `page.PageDates`: `load(path)`, `stamp(files)`, `save(path)`; `page.build(..., page_dates=None)`; `Built.page_dates`; `publish.py` loads and saves `caches/<header>_pagedates.json`.
- `bundle.write_page` returns the names it wrote; `publish()` returns them; `publish.py --indexnow-key` (validated and lowercased as `deploy.settings` does); `deploy.indexnow(key, host, urls, dry_run)` (never `404.html`, which is noindex; the 10,000 cap said when it cuts; a reset or a bad status line printed, never raised); `deploy.KEY_FILE` lets the key file past the site-folder guard; `bundle.KEY_FILE` sweeps a stale one; `envfile` key `FRETWORK_INDEXNOW_KEY`; `tools/check_site.py` checks 14 (the guide, the h1, the `WebSite` block, no query links) and 15 (the key file served as text, from the bundle's root when `--site` is given).
- `page.breadcrumb_ld(items)`, `page.itemlist_ld(name, entries)`, `page.website_ld()`, `page.dataset_ld(stats)`.

## Files touched

`web/page.py`, `web/static/index.html`, `web/static/doc.html`, `web/static/song.html`, `web/static/js/main.js`, `web/static/js/url.js`, `web/static/css/app.css`, `web/bundle.py`, `publish.py`, `deploy.py`, `functions/labels.py`, `.env.example`, `tests/test_page.py`, `tests/test_deploy_plan.py`, `tests/pipeline_test.py`, `tests/page/launch.js`, `about.js`, `share.js`, `load.js`, `run.py`, `CLAUDE.md`, `README.md`, `docs/spec/README.md`.

## Verification

- Unit: the static section's words, links and one `h1`; the song title per game and per custom, the description's lead, the `h1`; the game title and `h1`; fragment links and no `./?code=` on any document page; `PageDates` keeping a date when bytes do not move and moving it when they do; the sitemap's `lastmod` per page; the JSON-LD blocks parse and carry the right types; `deploy.indexnow` builds the request and is skipped without a key; `BUNDLE_TOP` admits the key file.
- Pipeline: the front page's raw HTML has the section (words, links to every game and list), the key file when the fixture `.env` sets one, the dates manifest written and reused (second publish keeps every date), the sitemap's `lastmod` values, no `?code=` link on any document page.
- Page suites: `launch.js` (the section is gone once the app boots, one `h1` before, the brand is not an `h1` after), `load.js` (a `#code=` fragment opens the chart and the URL becomes `?code=`), `share.js` and `about.js` (fragment links).
- After the deploy, the maintainer's side: Search Console's Pages report (indexed against not indexed, with reasons) and "Request indexing" on `/`, the five hardest lists, `library.html`, `songs.html` and the three biggest game pages; Bing Webmaster Tools (one click to import from Search Console); PageSpeed Insights in the browser for the front page and a song page.

## Risks and gotchas

- The guide must be closed by the inline script right after it, before the first paint; closing it from `main.js` alone (a deferred module) would show it open for a moment on every cold load and shift the layout when it closed. `main.js` closes it too, in case the inline script did not run.
- A fragment link is client-side only: a visitor without JavaScript who clicks a number lands on the front page's guide, which is the right fallback. A fragment pasted into a tab where the app is already open changes only the hash, so `main.js` listens for `hashchange` and navigates to the query form.
- `lastmod` moves for every song page on a full re-render, which is correct; a change to `song.html`'s template moves them all too, and that is also correct.
- The IndexNow key file is a top-level `.txt` in the bundle: it must pass `deploy.BUNDLE_TOP`'s guard and `bundle.prune_page`'s sweep by pattern, since its name is the key.

## Off-site: the maintainer's half

None of this ranks a page on a domain nobody links to. In order of value, all the maintainer's to do or not:

1. Ask [Staycation44](https://github.com/Staycation44/fretwork) to link fretladder from the fretwork README or the video's description: the engine's author linking the site that runs it is the most relevant link this site can get.
2. Post the site in r/CloneHero and the Clone Hero Discord's tools or resources channel, and on the Custom Songs Central Discord, with the hardest-customs list as the hook; a pinned or wiki mention is a lasting link.
3. Ask Custom Songs Central (every pack page of theirs is linked from ours), Chorus Encore (every chart's page is linked from ours) and Fullcombo.net (which keeps a difficulty index page and links tools) for a link back.
4. Search Console: read the Pages report; request indexing on the hub pages; add the site to Bing Webmaster Tools by importing from Search Console.
5. A short YouTube video or a post on the fretwork video's comments showing the site, with the link in the description.

## Out of scope and follow-ups

- Optional follow-up: a page per artist for artists with five or more songs, once the song pages are indexed and the Performance report shows artist queries.
- Optional follow-up: per-page descriptions written from the data for the game pages (the hardest song, the spread of tiers), once the pages are indexed and their impressions can be read.
- Optional follow-up: Core Web Vitals from the field, once there is traffic for CrUX to report.
