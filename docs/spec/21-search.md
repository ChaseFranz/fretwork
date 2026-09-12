# 21. Search: the site as a crawler sees it

**Status:** Landed (2026-09-12, e8ca2d6; awaiting the maintainer's deploy, and the maintainer's part in README's "After it is live"). Written 2026-09-12 against `main` at `52dc6d5`, from the live site fetched the way a crawler fetches it. As landed: the song page carries `<base href="../">` so `rich_text`'s bare page links and the favicon resolve from the root, and the forward is `location.replace(location.search)`; the percentile in a cell is the bare number under D; the pages are about 4 KB.

**Effort:** M. One robots line, the song pages made pages, a songs index, titles, a `document.title` that follows the chart, a live check; and two things only the maintainer can do, written up in the README.

**Depends on:** 16 (the song pages, the sitemap), 20 (the library page), both live as v1.4.0.

## Goal

Someone searching for a song's difficulty finds it. The front page indexes with its content, every song has a page a search engine can read and reach, the titles say what the pages are, and the domain answers at `www` too.

## Why

Measured on the live v1.4.0 site, 2026-09-12:

- `https://fretladder.com/` serves 26 words of visible text outside the JSON island. The `<h1 id="brand">` is empty in the HTML (`static/js/main.js:20` fills it), `<title>` is `Fretladder` (`page.build`, `title = config.SITE_NAME` when public), and `labels.EXPLAINER`'s prose is in the island, which is `<script type="application/json">` and not indexed.
- `robots.txt` says `Disallow: /data/` (`page.ROBOTS`, `web/page.py:28-33`), where the rows are since section 05. Googlebot renders JavaScript but obeys robots for the resources a page fetches, so the rendered front page is the chrome and an empty table.
- Every song page carries `location.replace(...)` and a `<meta http-equiv="refresh" content="0; ...">` (`static/song.html`), so a crawler treats it as a redirect to the front page, not as content. The 1,748 pages that would answer "*song* difficulty" answer nothing.
- Nothing links to a song page but `sitemap.xml`; a page with no internal links carries little weight.
- `www.fretladder.com` does not resolve (no DNS answer; `http://fretladder.com/` redirects to `https` correctly).

## Design

1. **Crawlers may fetch `data/`.** `Disallow: /data/` goes; `graph/` stays disallowed (11,904 files, meaningless out of context). Googlebot fetches the three sheet files now and then; the CDN cost is nothing.
2. **A song page is a page, and forwards only when told to.** The forward script runs only when the URL carries a query: `if (location.search) location.replace("../" + location.search)`. Copy link always produces a query (`?code=`), so a shared link still opens the app on the exact chart; a bare `song/<key>.html`, which is what the sitemap and the songs index give a crawler, renders. The `<meta refresh>` goes (a no-script visitor gets the page and its link). The page gains what a landing page needs: `<title>` `<Song> by <Artist>: chart difficulty - Fretladder`, an `h1` of the song and a line of the artist, a table of every level of every part (D with the percentile beneath, the tier per part, each cell a link into the table on that chart), the song's facts (charter, source, official or custom, album, year, genre), one sentence on what D and the tier are with links to the methodology and the library page, "Open in the table", and a `MusicRecording` JSON-LD block (name, artist, album, url). About 4 KB a page; 1,748 unique pages targeting the one query that matters.
3. **A songs index.** `songs.html`: every song, A to Z by title (digits under "0-9", the rest under "#"), each an anchor to its song page reading `Song by Artist`, in the footer as "Songs" (`labels.DOC_PAGES`), in the sitemap like the other document pages. About 150 KB. The library page's hardest lists link the title to the song page and keep D linking into the table, so the pages have internal links from two places and a crawl path from the footer.
4. **Titles that say what the page is.** The front page: `Fretladder: difficulty ratings for Clone Hero and Guitar Hero charts` (`UI.site_title`, the `og:title` too), with the brand's text in the HTML so the `h1` is never empty (`__BRAND__` in `index.html`, then JS adds the beta pill as now). In the app, `document.title` follows the open chart (`Song - Artist - Fretladder`) and returns when the pane closes, so a shared tab, a bookmark and the history read as the chart.
5. **A live check for the song pages.** `check_site.py` gains check 13: the first song URL in `sitemap.xml` answers 200 as HTML with an `og:title`, so the watch (19) notices if the folder ever stops serving.
6. **The maintainer's part**, written into README's "After it is live": verify the domain in Google Search Console with a DNS TXT record and submit `sitemap.xml`; the same in Bing Webmaster Tools; `www`: a DNS record, the alternate domain name on the CloudFront distribution, the certificate reissued to cover it, and a redirect to the apex (a CloudFront Function on the viewer request, or an S3 redirect bucket).

Rejected: prerendering the table into the HTML (megabytes on every visit for a page the song pages now cover); a page per chart (11,904 pages of the same six facts; the song page lists every level); AMP; keyword copy on the front page; structured data on the front page.

## Data and interfaces

- `page.ROBOTS` without the `data/` line; `page.robots_txt()` unchanged otherwise.
- `page.song_facts(sheets) -> {key: {'title', 'artist', 'charter', 'release', 'official', 'album', 'year', 'genre', 'parts': [{'type', 'tier', 'levels': {level: {'code', 'd', 'pct'}}}]}}`; `share_line` reads the part's Expert (else highest) level as before.
- `static/song.html`: `__TITLE__`, `__FAVICON__`, `__META__`, `__THEME__`, `__KEY__`, `__SONG__`, `__ARTIST__`, `__FACTS__`, `__TABLE__`, `__NOTE__`, `__OPEN__`, `__LD__`.
- `page.render_songs_index(facts, names)`; `SONGS_PAGE = 'songs.html'`; `labels.DOC_PAGES` gains `('songs.html', 'songs')`; `UI`: `songs`, `songs_tip`, `songs_intro`, `song_page_title`, `song_open`, `song_note`, `site_title`.
- `deploy.BUNDLE_TOP`, `bundle.PAGE_TOP` gain `songs.html`.
- `pane.js`: `document.title` set in `openPane`, restored in `closePane`; `main.js` keeps the base title.

## Files touched

`web/page.py`, `web/static/song.html`, `web/static/index.html`, `web/static/js/main.js`, `pane.js`, `functions/labels.py`, `deploy.py`, `web/bundle.py`, `tools/check_site.py`, `tests/test_page.py`, `tests/pipeline_test.py`, `tests/page/share.js`, `about.js`, `launch.js`, `pane.js`, `README.md`, `CLAUDE.md`, `docs/spec/README.md`.

## Steps

1. Robots, the front page title and brand, `document.title`. Commit: `crawlers may read data/; the front page says what it is; the tab names the open chart`.
2. The song page as a page: facts, the table, the note, JSON-LD, the conditional forward. Commit: `a song page is a page: every level of every part, the facts, and a forward only for a shared link`.
3. The songs index and the library links. Commit: `songs.html, every song A to Z, and the library's hardest linking to the song pages`.
4. Check 13, the README paragraph, the docs. Commit: `spec index: 21 on main`.

## Verification

- `tests/test_page.py`: the facts carry every level and part; the page has no refresh, forwards only on a query, has three scripts (forward, theme, JSON-LD), the title shape, one link per chart; the index groups and sorts; robots has no `data/` line.
- `tests/pipeline_test.py`: `songs.html` present with one link per song page, the song page shape, `<title>` of the front page, the brand in the HTML.
- `share.js`: the song page still forwards with a query (the test reads the script text); `about.js`: the footer's Songs page resolves; `pane.js`: `document.title` follows and returns; `launch.js`: the brand in the HTML before JS.
- `python tools/check_site.py --site site/Local` after the deploy: 13 checks.
- By hand, after the deploy: `curl -A Googlebot https://fretladder.com/song/<key>.html` shows the page, not a redirect; Search Console's URL inspection on one song page once the domain is verified.

## Risks and gotchas

- A song title of `__SHOUT__` (the fixture's) is placeholder-shaped; the pipeline test checks the template's names, not any `__X__`.
- The JSON-LD block is a third `<script>`; the pipeline and the suites count three on a song page and one on the other document pages.
- Google may take weeks to index 1,748 new pages; the songs index and the sitemap are what make it happen at all.

## Out of scope

- Content beyond what the data holds (no descriptions, no reviews); a blog; backlinks; per-chart pages; a `hreflang` set (one language).
