# 18. Small things

**Status:** Ready. Written 2026-09-12 against `main` at `e23f592`. Six independent items, each S, each its own commit; any subset can land in any order.

**Effort:** S each; about M together.

**Depends on:** nothing new. (d) and (e) touch the pane (14); (c) touches the pack join (03).

## Goal

Six things the follow-up lists of earlier sections named and nothing blocked: search that ignores accents and case, genre spellings folded, a `Pack` column, a shareable readout position with the hardest stretch marked, the pane grip from the keyboard, and a CSV of the current view.

## The items

### (a) Search folding

**Why.** `matchesSearch` (`static/js/query.js:46-51`) lowercases both sides and tests `includes`. Measured on the Local library's Expert rows: 30 carry a combining mark in the title or artist (`Mötley Crüe`, `Beyoncé`), 105 carry an ampersand. A visitor typing `motley` finds nothing; `tom petty and the heartbreakers` finds nothing against `Tom Petty & The Heartbreakers`. The search also rebuilds six strings per row per keystroke.

**Design.** `fold(s)`: NFKD, strip marks (`/\p{M}/gu`), lowercase, `&` to ` and `, collapse whitespace, trim. Each sheet gets a folded search string per row once when it arrives (`state.data[sheet].search[i]`, the six `SEARCH_COLS` joined with `\n`), built in `load.js` after the fetch; the query is folded once per keystroke and tested with `includes` against that string. Same columns, same substring rule, so nothing that matched stops matching. The Rank pairing (`state.visible()` index -1) is untouched. `keys.js` or `fields.js` gains: a query with a diacritic stripped finds the row that has it, `and` finds `&`, and the reverse.

### (b) Genre spellings

**Why.** `Genre` is the charter's text (`labels.COLUMN_HELP['Genre']`, `functions/labels.py:93`): 212 spellings over 1,758 songs, `Pop Rock` 79 beside `Pop-Rock`, `Alternative` 195 beside `Alternative Rock` 182, in a checkbox list that runs to 212 entries. Section 08 named the fold and left the choosing.

**Design.** Two layers. Mechanical first: at page build (`frames.with_genres`, in the same place `with_added` joins), fold case, hyphens, slashes and `&` so `Pop-Rock`, `pop rock` and `Pop/Rock` are one value, spelled as the most frequent original. Then a hand table, `sources/genres.txt`, `Alias = Canonical` lines in the shape of `sources/sources.txt`, applied after the mechanical fold, empty at first; the spreadsheet keeps the charter's spelling, the page shows the folded one, and `COLUMN_HELP['Genre']` says so. Whether `Alternative` and `Alternative Rock` are one genre is a taste call the table exists for and this section does not make. A unit test folds a fixed list; the fixture gains two spellings of one genre and `fields.js` sees one filter value.

### (c) `Pack` column

**Why.** `Release` is the source label from `sources/` (24 values for 26 packs on the Local library) and is what the heading and the song grid name; two packs share a label and a custom pack's rows read `Custom`. The registry knows the folder (`packs.resolve`, `functions/packs.py:196-214`, `folder_by_code` at `:71`), and the changelog names packs, but no row says which pack it is in.

**Design.** `frames.with_pack(frames, folder_by_code, registry)` after `with_added`: the pack's `name` from `packs.toml`, the dash for a folder the registry does not name (serve only; publish refuses one). Hidden by default (`DEFAULT_HIDDEN`, `PREFS_VERSION` bumped by one), filterable as a set, searchable? No: `Release` covers search. Labelled `Pack`, help "The pack this folder arrived in, from packs.toml". The song section's meta line does not change (Release stays the label people know).

### (d) The readout position in the link, and the hardest stretch

**Why.** Section 06's follow-up: "look at 2:41" needs a link that opens there. And the question a graph is opened to answer, "where is the hard part", is answered today by dragging the cursor.

**Design.** `?t=<seconds>` written by `writeUrl` when the pane is open and the cursor has been moved off zero (an integer, the readout's own step is 250 ms so seconds are enough), read by `readUrl`, applied by `openPane` after the mount (`controller.setCursor(t * 1000)`, `static/js/graph.js:313`). And the hardest stretch: for the primary chart, the 30-second window (120 samples at the 250 ms step) with the highest mean of `curves.d`, drawn on the canvas as a band of the ground's text colour at 6% under the curves, and named in a line under the readout, `Hardest 30 s: 2:41 to 3:11`, which is a button that sets the cursor to its start. One chart only; in compare mode the band is not drawn (three bands would say nothing). The Save as PNG export draws the band too. `graph.js` suite: the band's bounds equal the argmax of a 120-sample mean over the pinned vector's longer cousin; the button moves the cursor; `?t=` round-trips.

### (e) The grip from the keyboard

**Why.** Section 14's follow-up. `.pgrip` is `role="separator"` (`static/index.html:44`) and drags with a pointer (`pane.gripDown`, `static/js/pane.js:326`); Escape and the caret are the keyboard's only reach.

**Design.** The ARIA pattern for a focusable separator: `tabindex="0"`, `aria-valuenow` the pane's height in px, `aria-valuemin` `PANE_MIN`, `aria-valuemax` the room the drag already computes; ArrowUp and ArrowDown 24 px, with Shift 120 px, Home the maximum, End the minimum, through the same `state.paneH` and `savePane` path the pointer uses. `pane.js` suite: the grip is focusable, the arrows change the height and `aria-valuenow`, the bounds hold.

### (f) Download this view

**Why.** Charters and spreadsheet people ask for the numbers; the xlsx is the engine's whole output, not this view.

**Design.** "Download CSV" at the foot of the column chooser (`#cd`, beside Reset columns): the visible columns in their current order, then `Code` if hidden, the rows in the current sort and filter, values as displayed (the same formatters the cells use, the dash for a missing value), UTF-8 with a BOM so Excel reads the accents, RFC 4180 quoting, named `fretladder-<sheet>-<YYYY-MM-DD>.csv`, downloaded the way Save as PNG downloads (a blob URL, `pane.savePng`, `static/js/pane.js:350-365`). Client-side only; nothing is published. `chooser.js` suite or a new `csv.js`: the header row equals the visible columns, the row count equals `#count`, a quoted title with a comma survives, the BOM is first.

## Files touched

(a) `web/static/js/query.js`, `load.js`, `state.js`, `tests/page/fields.js`. (b) `web/frames.py`, `sources/genres.txt` (new), `functions/labels.py`, `tests/fixture.py`, `tests/test_labels.py` or a new `tests/test_genres.py`, `tests/page/fields.js`. (c) `web/frames.py`, `web/page.py`, `functions/labels.py`, `tests/pipeline_test.py`, `tests/page/fields.js`. (d) `web/static/js/url.js`, `pane.js`, `graph.js`, `functions/labels.py`, `tests/page/graph.js`. (e) `web/static/js/pane.js`, `web/static/index.html`, `functions/labels.py`, `tests/page/pane.js`. (f) `web/static/js/chooser.js`, a new `csv.js`, `functions/labels.py`, `tests/page/csv.js`. Each: `README.md` section 5 and `CLAUDE.md` where the rule lives, `docs/spec/README.md` once.

## Steps

One commit per item, in the order (a) (e) (f) (d) (c) (b): the ones with no data change first, the two that touch the spreadsheet join last. Commit messages: `search folds accents, case and the ampersand`; `the pane grip works from the keyboard`; `Download CSV of the current view from the column chooser`; `?t= carries the readout position, and the hardest 30 seconds are marked`; `a Pack column from packs.toml, hidden by default`; `genre spellings folded at page build, with sources/genres.txt for the rest`. Then `spec index: 18 on main`.

## Verification

The suites named per item; `python -m unittest` for (b) and (c); the pipeline test for (c) (`Pack` after `Copies` in the page-build order, the count of columns); `contrast.js` picks up the new button and the band's text through the pane it already opens.

## Risks and gotchas

- (a) `\p{M}` needs the `u` flag; every browser the page targets has it. The folded strings add about 1.3 MB of memory for the Guitar sheet; built once, on arrival.
- (b) Folding at page build means the URL's `f.Genre=` values are the folded spellings; a link shared before the fold that names `Pop-Rock` shows nothing after it. Accepted: genre links are rare and the fold is a one-time change.
- (c) `PREFS_VERSION` moves, so a returning visitor's hidden set is replaced once (the rule in CLAUDE.md).
- (d) `?t=` beyond the chart's length clamps to the end, as `setCursor` already does.
- (f) A blob download is blocked in some in-app browsers; the toast says so, as Save as PNG's does.

## Out of scope

- A song search box in the pane, a previous/next control, near-duplicate detection, genre as a searched column (08's measured flood: `rock` alone would match 558 of 1,758 rows).
