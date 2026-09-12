# 14. Details pane and the link columns

**Status:** Written after the fact, on 2026-09-11 evening, from the maintainer's feedback on the live `fretladder-v1.7.0` site and the decisions taken in that conversation; implemented the same evening on `main`. The other sections were written before their code; this one is the record of a change that was designed and built in one sitting, kept in the section format so the index has a row to cite.

**Effort:** L. One new module (`pane.js`) replacing the graph half of `overlay.js` and the whole of the song dialog, `song.js` reduced to markup, the router's click and key maps rewritten, two page-built columns, and ten of the twenty page suites rewritten around a region instead of two dialogs.

**Depends on:** 06 (the canvas graph, compare, pick-from-table, Save as PNG), 07 (the song grid), 13 (the links file), all landed.

## Goal

Three pieces of feedback on the v1.7.0 site, taken together: the Chorus Encore link was hard to find; a small icon on the song title that opened a dialog whose cells opened a second dialog was clunky; a comparison of one song's levels named the title, artist and part three times over in the legend when only the level differed.

## Why

The graph, the song grid and the outbound links are one thing, "details of this chart", and the site had grown them as three surfaces in two stacked dialogs with a pip to reach one of them. The dialogs also hid the table, so scanning was a click, look, close, click loop, and every dialog carried a focus trap, a z-order and its own Escape layer. Putting the details in one place that does not cover the table removes the loop, the trap and the stacking, and gives the site the interaction it most wants: move down the ladder and watch the curve change.

## Current state

As landed by sections 06, 07 and 13 on `main` at `9a4add5` (the legend fix, the first commit of this section): `#modal` (z 1060) held the graph, `#song` (z 1055) the grid, `router.js` handled them topmost first with `trapTab`, `song.js` opened its dialog and wrote `?song=` to the URL, the title cell carried a `.sp` pip, and the two `.ext` anchors sat in the graph heading's link group at 11 px. `state.song` existed beside `state.graph`.

## Design

1. **A docked pane, not a row expansion and not a merged dialog.** `#pane` is a flex sibling under `.fw-wrap`; the table shrinks, nothing is positioned over it. Row expansion was considered and rejected for this table specifically: it scrolls sideways whenever it is wider than the window, so an inline panel needs sticky-left plumbing and the widths stylesheet must skip it; the panel is rebuilt on every `tbody` repaint; and a shared `?code=` whose row is filtered out has nowhere to open. A pane keyed on `state.graph` has none of those problems: it survives a sort, a filter that hides the row and a sheet switch, and a shared link always opens. The decision was the maintainer's, from a three-way comparison with mockups.
2. **Not a dialog.** `role="region"`, no backdrop, no focus trap. Focus stays on the row that opened it, so the arrow keys keep moving rows and the graph follows (`router.moveTo`, debounced 160 ms so a held key fetches one curve file, not twenty); a click on the open row, the close button or Escape closes it and hands focus back to the row. Tab walks into the pane in document order. `trapTab` remains for the explainer alone.
3. **The selected row is the mark.** `markup.bodyRow` adds `.sel` and `aria-current` to the row whose code is `state.graph`, so every repaint redraws the mark for free; `pane.markRow` covers a swap between repaints (a grid cell, a copy's link). The row with the mark holds the table's roving tab stop.
4. **Graph beside the song grid.** `.pbody` is a row flex at 900 px and up, the graph filling the height it is given (`mountGraph`'s `fill` option, which measures the host after the legend is written) and the grid scrolling on its own; under 900 px the two stack and the graph draws at its aspect; under 640 px the pane is 44 vh, a bottom sheet the table keeps a few rows above. The top edge is a grip that drags the height (`fw.pane`, clamped so the table keeps 120 px), and the heading's caret collapses the pane to its heading alone.
5. **Links up front, twice.** The pane's tool row leads with the outbound links as accent buttons, before Compare. And the table carries them as page-built boolean columns, `Enchor` (labelled Chorus Encore) after Artist and `Leaderboard` (labelled Scores) after that, joined by `SongKey` at page build (`links.link_columns`, `frames.with_links`, after `Pct` in the column list); a column exists only for a link kind some song has. The cell is an arrow drawn from the links file, dim until the file lands and then filled in place (`fillLinkCells` on `fw:links`), never a redraw, so focus and scroll are not disturbed. One bit per row rather than the hash keeps the sheet files small; the file already carries the hash. A boolean column gets the filter dropdown, the chooser, ordering and widths for nothing, so "No" lists the lookup's misses. On a phone the two columns leave the table (they would push D off the screen) and the tool row carries the links.
6. **`?song=` becomes an alias.** Read and never written: `song.primaryCode` resolves it to the song's first instrument at Expert (its first level otherwise) once every sheet is here, the pane opens on that code and the URL carries `?code=`. A key nobody has gives a toast. `state.song` is gone.
7. **The compared charts' legend names only what differs** (`graph.gNames`): two levels of one song and part read "Expert" and "Hard"; two parts of one song keep the part; two songs keep everything. Applied to the on-screen legend and the exported PNG alike.
8. **Escape closes one thing at a time:** the explainer, an open dropdown, the pick mode, the compare picker (focus returns to its button), then the pane.

Rejected: a merged single dialog (smallest change, but the table still vanished); the arrow inside the title cell (no width, but the same small-icon-on-the-song-field the feedback named); carrying the md5 in the rows (about 200 KB compressed across the sheets for nothing the file does not already give).

## Data and interfaces

- `web/links.py`: `LINK_COLS = (('Enchor', 'enchor'), ('Leaderboard', 'lb'))`, `link_columns(songs) -> {column: set of keys}`, `publish_songs(songs)`; `published(registry)` is now a wrapper.
- `web/frames.py`: `with_links(frames, link_columns)`, after `add_percentiles` in `page.build`.
- `labels.py`: `COLUMN_LABELS['Enchor'] = 'Chorus Encore'`, `['Leaderboard'] = 'Scores'`, help text for both, `VALUE_LABELS` Yes/No for both, `DISPLAY_ORDER` seats them after Artist; UI `pane_label`, `pane_resize_tip`, `pane_collapse`, `pane_expand`, `links_pending`, `graph_legend_part`, `graph_legend_level`; `row_tip`, `enchor`, `compare_cancel`, `compare_picking` reworded; `song_view`, `song_label`, `graph_label`, `code_tip` removed. `PREFS_VERSION` unchanged: a new column absent from a saved hidden set is shown.
- `state`: `paneH` (px or null, `fw.pane`), `paneMin`; `song` removed.
- `pane.js` exports `openPane(code, vs, {follow, reveal})`, `closePane`, `paneIsOpen`, `addCompare`, `removeCompare`, `startPicking`, `stopPicking`, `closePicker`, `refreshLinks`, `initPane`. `song.js` exports `chartsOf`, `folders`, `primaryCode`, `songSection`. `links.js` exports `LINK_COLS`, `linkFor`, `linkAnchors`, `linkCell`, `fillLinkCells`. `table.js` exports `holdRow`. `load.js` dispatches `fw:links`.
- Markup: `#pane.fw-pane > .pgrip + .pcard`; inside `.pcard`: `.mhead`, `.pbtns` (`.pmin`, `.x`), `.mmeta`, `.gtools`, `.picker`, `.pbody > .gbody + .sbody`. Rows: `tr.sel[aria-current]`, `tr[data-key]`, `td.lnkc` with `a.ext` or `.wait`.

## Files touched

`web/links.py`, `web/frames.py`, `web/page.py`, `functions/labels.py`; `web/static/index.html`, `css/app.css`; `js/pane.js` (new), `js/overlay.js`, `js/song.js`, `js/links.js`, `js/router.js`, `js/main.js`, `js/markup.js`, `js/table.js`, `js/state.js`, `js/url.js`, `js/load.js`, `js/graph.js`; `tests/test_links.py`, `tests/pipeline_test.py`, `tests/page/run.py`, and the suites `graph.js`, `compare.js`, `song.js`, `song_url.js`, `keys.js`, `launch.js`, `load.js`, `links.js`, `contrast.js`, `narrow.js`, `copies.js`, plus `pane.js` (new); `CLAUDE.md`, `README.md`, `tests/README.md`, this index.

## Steps

As committed: the legend wording (`9a4add5`), then the pane, the columns and the suites in one commit, since the dialogs could not be half-removed.

## Verification

`pane.js` (36 checks: region, table shrinks, mark survives sort, filter and sheet switch, toggle on the open row, collapse, grip drag and its memory and clamps, Escape order), the rewritten suites above, `tests/test_links.py::test_link_columns`, the pipeline test's column-order and per-song bit checks. All twenty suites pass against the fixture and against `site/Local`.

## Risks and gotchas

- The pane card keeps `scrollbar-gutter: stable`: without it a scrollbar's arrival shrank the host 15 px after the canvas had been sized, and the resize observer chased it.
- `mountGraph` writes the legend before it sizes the canvas, so `fill` mode measures the legend's real height; `writeLegend` must therefore not read `geom`.
- The bundle is one scope: `pane.js`'s `paneOpener` and `paneDrag` are named apart from `overlay.js`'s `opener` and `widths.js`'s `drag`.
- A drag-select of a row's text ends with a click; the router ignores a click whose selection is inside the row.

## Out of scope and follow-ups

- Per-instrument leaderboard links in the Scores column (13's follow-up).
- Sharing the readout position (06's follow-up).
- A keyboard affordance for the grip; Escape and the caret cover the keyboard today.

## Open questions

None.
