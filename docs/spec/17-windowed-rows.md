# 17. Paint only what is on screen

**Status:** Landed (2026-09-12, c414bf8; awaiting the maintainer's deploy). Written 2026-09-12 against `main` at `e23f592`, from the code and measurements of the Local library in headless Chrome (node counts and pixel heights; the harness's virtual clock does not advance while a script runs, so the timings were not measured there). As landed, three things differ from the design below: the overscan is 40 rows a side rather than 600 px, which keeps every fixture sheet painted whole so the existing suites hold unchanged; the spacers stand at the estimate the previous paint measured (`state.window.next`) while `state.window.avg` is what the current spacers were built with, and a scroll-driven paint keeps the row under the screen's top where it was, which is what makes a changed estimate invisible; and `revealIndex` paints the window around the target before it scrolls, since a scroll position set first is clamped to the old height (the first cut did it the other way and lost the row). The scroll listener paints synchronously; a `requestAnimationFrame` did not fire under the harness's clock and the browser already delivers scroll once a frame.

**Effort:** L. `draw()` split into "compute the view" and "paint the window", a scroll handler, spacer rows, the keyboard and reveal paths taught about rows that are not in the DOM, and the twelve suites that today read every passing row from the DOM.

**Depends on:** 05 (the rows arrive by fetch), 14 (the pane marks rows by code), both landed.

## Goal

The table costs the same to paint whether the sheet has 1,000 rows or 50,000: the DOM holds the rows on screen and a margin either side, and scrolling, sorting, filtering and the arrow keys behave exactly as they do now.

## Why

`table.draw` (`static/js/table.js:95-140`) sorts every passing row and writes them all as one `innerHTML` (`:126-130`). Measured on the Local library at 1440 px: the opening view (Expert, official) is 1,467 rows and 24,865 nodes under `#body`; with the filters cleared the Guitar sheet is 6,610 rows, 112,028 nodes and a scroll height of 357,388 px (54 px a row on average, because titles and sources wrap: `td.title { white-space:normal }`, `static/css/app.css`). Every keystroke in the search box, every sort and every chip repaints all of it. The library is 26 packs; the plan is for it to grow by an order of magnitude, and section 05 set its own threshold at about 20,000 charts for the data model. The DOM is the next wall, and a phone hits it first. Doing it now costs nothing on a phone today and means the growth never has to wait on it.

## Current state

- `draw()` computes `vis` (the visible columns), sorts `passing(null)` by the sort column, rewrites `#head`, then `#body` as `loadingRow`, every `bodyRow` (`static/js/markup.js:85`) or `emptyRow`; `markRows()` (`table.js:70-92`) marks the open chart's row and the compare rows by `data-code`; `holdRow` (`:57`) gives one row the tab stop; `applyWidths()` writes the nth-child stylesheet (`static/js/widths.js:26`); `writeUrl()`; `#count`.
- `router.onGridKey` (`static/js/router.js:146`) moves focus row to row with the arrow keys, Home and End, and the pane follows (debounced 160 ms).
- `openPane(code, vs, {reveal})` (`static/js/pane.js:178`) scrolls the marked row into view and focuses it; the row is found by `body.querySelector('tr[data-code=...]')`.
- `edgeFade` (`static/js/scroll.js:13`) watches `.fw-wrap`, the scroller; the sticky header is inside it.
- `tests/page/narrow.js` measures the 390 px layout inside an iframe; every suite reads rows from `#body tr[data-code]`, and several treat that as every passing row: `order.js`, `fields.js` (`cells()`), `copies.js`, `compare.js`, `contrast.js` (every level badge), `sheets.js`, `keys.js`, `load.js`, `roundtrip.js`, `links.js`, `song.js`, `pane.js` and `lib.js` itself.

## Design

1. **The view is computed once, the window painted often.** `draw()` becomes `compute()` (sort and filter into `state.view`, an array of rows; the header; `#count`; `writeUrl`) plus `paint()` (the window). `state.view` replaces the local `rows`; `visible()` and `passing()` are unchanged. Anything that changes the view calls `compute()` then `paint()` with the scroll reset to the top; a scroll calls `paint()` alone.
2. **A window of rows and two spacers.** `paint()` writes `#body` as a top spacer row, the rows from `from` to `to`, and a bottom spacer row. `from` and `to` come from the scroll position: the row whose estimated top is `scrollTop - OVERSCAN` to the row past `scrollTop + clientHeight + OVERSCAN`, `OVERSCAN` 600 px. The spacers are `<tr class="empty pad"><td colspan=N style="height:Hpx">` with `H` the number of rows they stand for times the running average row height; `empty` is the class the widths stylesheet already skips for the loading row.
3. **Row height is measured, not assumed.** After each paint, the average is `(tbody height - the two spacers) / rows painted`, seeded at 44 px. Rows wrap, so it drifts; a drift moves the scroll thumb a little as the visitor scrolls, which is the accepted cost of keeping wrapped titles. A fixed height with ellipsis was rejected: "long titles wrap rather than truncate" is a decision on the record (CLAUDE.md, the table's three details).
4. **Scroll repaints only when the window moves.** A `scroll` listener on `.fw-wrap`, one `requestAnimationFrame` at a time; the window is recomputed and painted only when `from` or `to` has moved by more than `OVERSCAN / 2` worth of rows, so a slow scroll paints nothing and a fling paints a few times. `markRows()` runs after every paint, since a marked row may have just entered the window.
5. **The arrow keys walk the view, not the DOM.** `onGridKey` finds the focused row's index in `state.view` (by `data-code`, stored on the row as today), moves the index, then calls `revealIndex(i)`: if row `i` is painted, focus it; else set `scrollTop` to `i * average`, paint, then focus. Home and End are `revealIndex(0)` and `revealIndex(view.length - 1)`. The pane's debounce and `holdRow` are unchanged: the focused row always exists once revealed.
6. **Reveal by code goes through the view.** `openPane(..., {reveal})` and the `?code=` open find the code's index in `state.view` (a linear scan over the sheet's rows, once) and call `revealIndex`, then mark. A code not in the view (filtered out) is not scrolled to, as today.
7. **Rank is the index in the view.** `bodyRow`'s `rank` argument is `i + 1`, so the numbers are continuous across paints.
8. **Everything else reads the same.** The sticky header, the widths stylesheet, the edge fade, the link cells (`fillLinkCells` runs on the painted rows and again after every paint, cheaply), the row tips, `aria-current`, the tab stop, the empty row, the loading row.

Rejected: chunked painting on idle (the DOM still ends at 112,028 nodes and the memory with it; it only moves the freeze); a fixed row height with truncation (see 3); pagination (breaks the one long table and the rank a shared sort implies); a canvas table (no text to select, no accessibility tree).

## Data and interfaces

- `state.view: row[]`, `state.window: {from, to, avg}`.
- `table.compute()`, `table.paint()`, `table.revealIndex(i)`, `table.viewIndexOf(code) -> number`; `draw()` stays as `compute(); paint()` so every caller is unchanged.
- `OVERSCAN = 600` (px), `ROW_SEED = 44` (px) in `table.js`.
- `markup.padRow(n, height)`.
- `router.onGridKey`: index arithmetic in place of `nextElementSibling`.

## Files touched

`web/static/js/table.js`, `markup.js`, `router.js`, `pane.js` (reveal), `state.js`, `main.js` (the scroll listener), `web/static/css/app.css` (`tr.pad td { padding:0; border:0 }`), `tests/page/window.js` (new), the twelve suites above (expectations from `sheetRows` and `#count`, not from the DOM; the DOM asserted only for what is on screen), `tests/README.md` (the gotcha: the DOM holds a window), `CLAUDE.md`, `docs/spec/README.md`.

## Steps

1. Measure by hand in DevTools on `serve.py` with the Local library: the Performance panel for a search keystroke and a sort with the filters cleared, on a desktop and on a phone over the LAN; record the numbers here. Commit: `spec 17: the paint measurements`.
2. `compute()`/`paint()` with the whole view as the window (`from` 0, `to` length): no behaviour change, every suite green. Commit: `table: the view computed once, painted by paint()`.
3. The spacers, the window from the scroll position, the scroll listener, the average; `window.js`: the DOM holds fewer rows than `#count` when the view is long, spacer heights sum to the estimate, a scroll to the middle paints rows whose rank matches their position, the total scroll height is within 10% of rows times the average. Commit: `table: only the rows on screen and a margin are in the DOM`.
4. `revealIndex`, the keys, End, reveal by code; `window.js`: ArrowDown from the last painted row focuses the next row, End focuses the last row of the view, a `?code=` deep in the view opens with its row on screen. Commit: `the arrow keys and a shared code reach rows that are not painted`.
5. The twelve suites. Commit: `suites: expectations from the data, the DOM for what is on screen`.
6. Docs. Commit: `spec index: 17 on main`.

## Verification

- `window.js` as above, run on the fixture (15 songs, so the window is the whole view: the spacers are 0 px and every row is painted, which is the degenerate case) and on `site/Local` (6,610 rows, the real case); the runner's `--site site/Local` run is the one that proves it.
- `keys.js`, `pane.js`, `compare.js`, `sheets.js` unchanged in intent: the arrows, the marks and the pane behave as before.
- `narrow.js`: the 390 px measurement inside the iframe, with the window in place.
- Step 1's numbers repeated after step 4, on the same machine.

## Risks and gotchas

- The average row height is per sheet and per width; a column shown or hidden changes it. `paint()` re-measures after every paint, so it converges within a screen or two.
- `find` in the browser (Ctrl+F) only sees painted rows. The search box is the search; this is the trade every windowed table makes.
- `contrast.js` measured every level badge in the DOM; with a window it measures the badges on screen, which is every level once the Level filter is lifted at the top of the sort.
- The runner's suites run at 1440 by 900; a window of 600 px overscan on either side is about 45 rows, so a fixture sheet (a few dozen rows) is painted whole. Assertions about the window need the Local run.

## Out of scope and follow-ups

- Horizontal windowing of columns: the widest view is 22 columns; not needed.
- A "load more" or infinite-scroll fetch: the rows are already all here; this is about the DOM, not the network.
