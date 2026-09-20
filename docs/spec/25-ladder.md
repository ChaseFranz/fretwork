# 25. The ladder: every song page links its neighbours

**Status:** Implemented 2026-09-19, awaiting the maintainer's deploy. Written from the first Search Console Pages report (exported 2026-09-19, data to 2026-09-13: 1 page indexed, 2,308 "Discovered - currently not indexed", 1 "Page with redirect") and a five-agent panel over it (three lenses proposing, two judges scoring; the transcript is the session's, the verdicts are summarised under Why).

**Effort:** S. One computation over the facts every song page already has, one block on the song page, the picture's real size, one live check.

**Depends on:** 24 (live as v1.7.1).

## Goal

A song page is a node in a graph a crawler can walk, not a leaf off two hubs, and every sentence on it is a number only that page can state: where the song stands among the site's songs and its source's on its primary Expert part, how many notes over how long, which songs sit just above and below it, and what else its artist has.

## Why

The Pages report says the site is discovered (every URL known from the sitemap) and not crawled (one page fetched: the front page). Google's own definition of "Discovered - currently not indexed" is a crawl deferred, and for a twelve-day-old domain with no inbound links the crawl demand is at its floor; the on-site levers are all set since 24 (measured by the panel: every URL within two clicks of `/`, 200 in 130 to 300 ms, brotli, honest `lastmod`, one home URL). What remained on-site, and what the panel ranked first for code, is the shape of the song folder: 1,475 of 2,260 song pages had exactly two inbound links, both from pages of 75 to 2,260 links, and no song page linked another, so Google's scheduler saw 2,260 equal leaves. The panel scored the sitemap split at zero crawl effect (a reporting convenience), the picture quantisation as optional, and any prose per song as scaled content; it agreed on links from the data.

## Design

1. **The primary Expert chart.** `page.primary_expert(fact)`: the first part with an Expert level that has a D (the same chart the picture and the preview line name). `song_facts` now carries each level's `notes` and `secs` (NoteCount, DurationS) so the page can say the chart's shape.
2. **The ladders**, `page.song_ladders(facts, resolved)`, computed once for every song: on its primary sheet, the song's rank among the site's songs by that chart's D (ties by title), the two above and two below (`LADDER_NEAR`); the same within its source (the registry folder its primary code is in) when the source has three or more songs on that sheet (`LADDER_SOURCE_LEAST`); and up to five other songs by the same artist, case-folded (`LADDER_ARTIST`). Songs without an Expert chart have no ladder and their pages are as before.
3. **The block**, `page.song_ladder_html`, under the table and before the source line: a rank sentence ("Ranked #4 of 75 songs in Guitar Hero: Smash Hits on Expert guitar, and #37 of the 2,283 songs on the site with an Expert guitar chart. 3,722 notes over 7:24, 8.4 a second on average."), then "Nearby on Expert guitar: harder: A by B (D 160.10, tier 8), C by D (...); easier: ...", "In {source}: ..." and "More by {artist}: ...", every name a link to its song page with its Expert D and tier. Every word is a number or a name; there is no adjective anywhere.
4. **The picture's real size.** `plot.py` saves with a tight bounding box, so the PNG is 1908 by 774, not the figure's 1920 by 840 the `<img>` claimed; `bundle.png_size(out_dir)` reads it off a PNG the previous publish left and `page.build` threads it to the song and list pages (`page.PNG_SIZE` is the measured default for serve and the tests), so the page does not shift when the picture lands.
5. **The live check.** `tools/check_site.py` #13 now also requires the first sitemap song page to carry a `song/` link, so a ladder that renders empty is seen from outside.

Rejected: a sitemap index split by folder (Google documents that sitemaps carry no crawl priority; the panel scored it zero; the per-sitemap reporting it would give is available today by exporting the Pages report's URL sample and counting by path); per-song prose, templated or generated (scaled content by Google's definition, and the project's rule that the data is the content); level-by-level sentences (the table says it; repeating it with the numbers swapped lowers the page's density); a `noindex` on the long tail (there is no quality signal yet to act on; Google has crawled none of them); renaming `game/` (34 URLs in Google's queue would become redirects during the first crawl).

## Data and interfaces

- `page.primary_expert(fact)`, `page.song_ladders(facts, resolved) -> {key: {sheet, d, tier, notes, secs, site: {rank, n, harder, easier}, source: {...} | None, artist: [keys]}}`, `page.song_ladder_html(key, ladder, facts, game)`, `page.LADDER_NEAR`, `page.LADDER_ARTIST`, `page.LADDER_SOURCE_LEAST`.
- `render_song_page(..., ladder=None, facts=None, png_size=PNG_SIZE)`, `render_song_pages(..., png_size)`, `render_list_pages(..., png_size)`, `build(..., png_size)`; `page.PNG_SIZE`; `bundle.png_size(out_dir)`.
- `labels.UI`: `song_rank`, `song_rank_site`, `song_shape`, `song_nearby`, `song_in_source`, `song_harder`, `song_easier`, `song_more_by`, `song_neighbour`, `song_neighbour_tier`.
- `song.html`: `__LADDER__`, `.rank`, `.ladder`.

## Verification

- Unit (`tests/test_page.py`, `LadderTest`): the primary chart, the ranks and neighbours on the site and in the source (the source needs three), ties by title, the artist's other songs, no source ladder without a pack join, the block's exact sentences, the pages carrying the block in order and the real picture size, `png_size` reading a header and skipping a bad file.
- Pipeline: a song page carries `song/` links; the live check's #13.
- Page suites: `share.js` (the song page is still a page with its forward and its h1) on the fixture and on `site/Local`.
- After the deploy: the Pages report of about 2026-10-03 is the first that can show a crawl of the hubs; the URL sample of "Discovered - currently not indexed" counted by path says whether songs lag hubs.

## Risks and gotchas

- Every song page's bytes move, so every `lastmod` moves on this deploy (a template change is a real change; the date is still honest). Two such deploys a week apart would read as the deploy date again, so the ladder ships with nothing else pending on the song pages.
- The rank is among songs, one primary chart each, not among charts; the percentile beside it is among charts of that level. The two sentences say which.
- A song whose primary part is drums or vocals ranks on that sheet; the picture is that chart's too.

## Out of scope and follow-ups

- Optional follow-up: the picture quantised to a 64-colour palette (143 KB to about 45 KB, no visible loss), with `--force`, once the pages are indexed and the image channel is worth the re-upload.
- Optional follow-up: a sitemap index by folder, if the Pages report's URL sample stops being enough to tell hubs from songs.
