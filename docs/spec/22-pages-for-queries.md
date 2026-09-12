# 22. Pages for the queries people type

**Status:** Landed (2026-09-12, a20fef2; awaiting the maintainer's deploy). Written 2026-09-12 against `main` at `47e6240`, from the maintainer's question "what else do we need to do to improve SEO", after 21 had made the site readable.

**Effort:** M. Three renderers in `web/page.py` (a page per pack, the lists, a richer song page), the picture per song drawn by publish, per-page titles and descriptions on every document page, two more folders in the week class, and the tests.

**Depends on:** 16 (the song pages), 20 (the library page, the pack join), 21 (the song page as a page), all on `main`; 16 and 20 live.

## Goal

The site has a page for each thing people search for in this niche: a game's setlist ranked by difficulty, the hardest and easiest songs per instrument, and a song, each saying in words and in a picture what the table says in numbers, each linking the others, each with a title and a description of its own.

## Why

Section 21 made the site readable to a crawler; it did not give a crawler anything to rank for the queries that exist. Nobody searches "difficulty ratings". They search "gh3 setlist by difficulty", "hardest guitar hero songs", "rock band 3 hardest songs", "*song* clone hero difficulty": games, lists, songs. The site held every number those queries want and had pages only for the songs, and those were a table and a note. Every document page shared one meta description (`page.meta_head`, `web/page.py:89-104`), and the song page's `og:image` was absent by section 16's design (the site's one PNG was another song's graph), so a shared song link previewed as text alone. Outbound links (Chorus Encore) do nothing for ranking; the maintainer asked, and the answer is recorded: keep them for visitors, and the link that would help is the reverse, from Enchor's chart pages or the fretwork README to fretladder.

## Design

1. **A page per pack: `game/<slug>.html`.** One per registered pack with songs (`page.render_game_pages`, `pack_slugs` from the pack's name, unique in registry order): title `<Pack> setlist by difficulty`, an intro sentence, the pack's facts (songs, charts, official or custom or mixed, on the site since), the source link when the registry has one, and every song ranked by its Expert guitar D (the highest of Lead, Rhythm, Co-op) with the Calc Tier, and the Bass and Keys Expert charts beside; songs with no Expert guitar chart follow, by their best other part, with a line saying so. A song links its page, a number the chart's graph. `charts_by_folder` joins every Expert row to its folder through `resolved.folder_by_code`, so a song shipped in two packs appears on both pages.
2. **The lists: `list/<kind>-<sheet>.html`.** Per sheet: the hardest official songs, the hardest customs, the easiest official songs on Expert (`LISTS`, `LIST_MOST` 100), one entry per song at its hardest (or easiest) part, with the artist, the game (linked), the part, D with the percentile, and the tier. The titles carry the words: `The 100 hardest Guitar Hero and Rock Band songs on Expert guitar`, `The 100 hardest Clone Hero custom charts on Expert guitar`. The library page's hardest blocks link "the full list" three ways, and its packs table links the pack's page (the date now carries the link into the table).
3. **The song page says it in words and shows it.** One sentence per part (`song_sentences`): "On Expert Lead it scores D 169.93, Calc Tier 8, at or above 97% of the site's Expert Guitar charts." Then the picture: the first part's Expert graph (`song_image_code`, the same chart the preview line names) as an `<img>` with the graph's alt text, linked to the chart in the table, and as `og:image` (`twitter:card` `summary_large_image`) and the JSON-LD's `image`. Then the table as before, then "From *Game*, with every song of that setlist ranked by difficulty" linking the pack's page.
4. **The pictures.** Publish draws a PNG per song, 1,748 on the Local library, at the figure's own size (about 170 KB each, 300 MB in all on the Local library, against the 2.2 GB of 11,904 that section 06 retired): `Built.png_codes` is the social preview plus each song's picture code, `publish.py` passes it to `bundle.render_graphs`, the manifest and the fingerprint rules of `web/bundle.py` apply unchanged, so a song whose chart did not change is not redrawn. `robots.txt` allows `graph/*.png` so the pictures index as images; the curve files stay out. The banner prints the picture counts and whether the preview is among them.
5. **Titles and descriptions per page.** `render_doc` takes `page_title` and `description`; `meta_head` emits them as the `<title>`, `og:title`, `description` and `og:description`, and `og:url` is the page's own address. About, the changelog, the library, the songs index and the methodology each have theirs (`UI.*_title`, `UI.*_desc`): "How Guitar Hero chart difficulty is scored" for the methodology, "The library: Guitar Hero and Clone Hero charts by instrument, level and tier".
6. **Folders under the week class.** `game/` and `list/` join `song/` in `assets.WEEK_DIRS`, synced with `--delete` like `graph/`, swept by `bundle.prune_page`, excluded from the page sync; `deploy.plan` is eleven commands. A document page under a folder gets `<base href="../">` from `render_doc`, so its relative links resolve from the root; such a page carries no fragment links, since a base breaks them (the songs index, at the root, keeps its letter anchors). The sitemap lists the game and list pages before the songs.

Rejected: artist pages (about 800, thin: two or three songs each, the songs index and the lists cover the tail); a page per chart (11,904 near-duplicates); pages per tier; prose written by hand per game (the numbers are the content, and hand copy would age); an image per chart rather than per song.

## Data and interfaces

- `page.pack_slugs(resolved) -> {folder: slug}`, `page.slug(name)`; `page.charts_by_folder(sheets, resolved) -> {folder: {key: {title, artist, official, parts: {type: {code, d, pct, tier, sheet}}}}}`.
- `page.render_game_pages(sheets, resolved, names)`, `page.render_list_pages(sheets, resolved, names)`, `page.list_slug(kind, sheet)`, `page.LISTS`, `page.LIST_MOST`, `page.GAME_DIR`, `page.LIST_DIR`.
- `page.song_facts` gains `code` (the primary folder's first chart) and each level's `sheet`; `page.song_image_code(fact)`, `page.song_sentences(fact)`; `render_song_pages(sheets, names, facts, resolved)` passes each song its game; `song_meta` and `song_ld` take the image.
- `Built.png_codes`; `page.render_doc(name, title, body, names, page_title=None, description=None)`; `page.meta_head(public, canonical, title, description)`; `doc.html` gains `__BASE__`.
- `assets.GAME_DIR`, `assets.LIST_DIR`, `assets.WEEK_DIRS`; `deploy.BUNDLE_TOP`, `deploy.HEADER_PASSES`, `deploy.SAMPLES`; `bundle.SWEPT_DIRS`.
- `labels.UI`: `song_sentence`, `song_sentence_pct`, `song_sentence_tier`, `song_sentence_d`, `song_game`, `game_title`, `game_intro`, `game_facts`, `game_no_guitar`, `list_hardest`, `list_hardest_custom`, `list_easiest`, `list_intro_official`, `list_intro_custom`, `list_game`, `list_full`, `*_title` and `*_desc` per document page; `labels.t_graph_alt(song)`.

## Files touched

`web/page.py`, `web/assets.py`, `web/bundle.py`, `web/banner.py`, `deploy.py`, `publish.py`, `functions/labels.py`, `web/static/song.html`, `web/static/doc.html`, `tests/bin/aws`, `tests/test_page.py`, `tests/test_deploy_plan.py`, `tests/pipeline_test.py`, `tests/page/run.py`, `share.js`, `about.js`, `CLAUDE.md`, `README.md`, `docs/spec/README.md`.

## Verification

- Unit (`tests/test_page.py`): the slugs, `charts_by_folder`, the game pages (ranked by Expert guitar D, the base, the facts, the links), the lists (official against custom, one entry per song, the game linked, easiest ascending), the song page's picture in three places and its sentences, the library's links to the pages and the lists, the sitemap's order; `tests/test_deploy_plan.py`: eleven commands with the two folders.
- Pipeline: one PNG per charted song (the fixture's Expert-less song gets its Hard chart), unchanged on the second publish, the three game pages and the lists, the song page's picture and words, twelve deploy samples, nine dry syncs.
- Page suites: `share.js` (the `og:image` is the song's own graph, the `<img>` and its PNG in the bundle, the sentence), `about.js` (the library links a game page and a list, both resolve with a base and song links).
- After the deploy: Search Console's URL inspection on a game page and a list; the Performance report's queries, which decide the next lists.

## Risks and gotchas

- The pictures are 300 MB the first deploy uploads once (1,748 PUTs, about 170 KB each at the figure's 1920 by 840); after that only changed charts. A song page lazy-loads its one image, so the page itself stays under 6 KB.
- A pack name that slugs to an existing slug gets `-2`; renaming a pack moves its page, and the old one is pruned and deleted from the bucket by the week sync.
- `<base href="../">` on a folder page: any `#fragment` link on such a page would resolve to the root; none exists there.
- The fixture's `__SHOUT__` title is placeholder-shaped; the pipeline checks strip it before looking for placeholders on the game page.

## Out of scope

- Artist pages; hand-written copy; a per-chart page; a hard-coded "top 10" on the front page (the library page and the lists are one click from the footer).
