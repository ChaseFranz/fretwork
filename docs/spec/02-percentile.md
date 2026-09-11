# 02. Percentile column

**Status:** Ready

**Effort:** S, dominated by the manual browser checks (a throwaway 390 px iframe page and the serve walk-through), not by the code: the Python side is one function and one call, the JavaScript side is four small edits.

**Depends on:** none for the code. Step 5's "zero graphs rendered" holds only after section 00 step 6 (the one full re-render that the `spans` fingerprint change forced); if that publish has not run, the first publish here re-renders every graph once, about 24 minutes. Section 05 inherits this column through the same `frames_payload` path; section 10 passes one argument to the function defined here; section 04 owns `tests/` and gains the assertions listed under Verification.

## Goal

Add a `Pct` column, labelled "Percentile", to every sheet the page shows: an integer 0 to 100 saying what share of that sheet's charts at the same level have a `D` at or below this chart's. It is computed in `web/frames.py` when the page is built, so it exists on the site and in `serve.py`'s local preview and nowhere else: `analyze.py`, the cache and the committed spreadsheets do not change. It is shown by default immediately after `D`, gets a min/max filter without any JavaScript change, and is spelled out in the graph heading ("At or above 98% of Expert Guitar charts") and in the row's hover text.

## Why

- `D` is uncapped and its scale means nothing on first sight: Expert Guitar runs from 0.06 to 1,047.43 with a median of 30.49, Expert Keys from 0.17 to 81.31 with a median of 12.41 (`metrics-render` map, per-(sheet, level) quantiles; re-measured below). A visitor who opens the site to ask "is this chart hard?" gets an answer from `D` only after scrolling to see where it sits. A percentile is that scroll, done once.
- `Rank` already numbers the current view, but it renumbers as filters change and it is not shareable, sortable or filterable (`web/static/js/state.js:66-68`). A percentile is a property of the chart, stored in the row like `D`, so it survives filtering, sorts, takes a range filter and goes in a link as `?r.Pct=90:`.
- `CalcTier` and `RemapDiff` are Expert-anchored and shown on every level of a song; `Pct` is the only per-level comparison the site offers, which is what a Medium player wants.
- Custom charts are the ones whose place matters most: in the Local spreadsheet the live site was published from, the median Expert Guitar custom sits at Pct 84 and the median official at 41 (measured, see Current state). That is a fact the page cannot say today.
- Computing it at page-build time keeps it out of the shared tooling. The spreadsheet's columns are the data contract with upstream and the committed examples under `metrics/`; a column that depends on which other charts happen to be in the library does not belong there.

## Current state

**Where the rows come from.** `page.build()` (`web/page.py:144-154`) calls `frames.load_frames` (`web/frames.py:15-19`, `pd.read_excel(sheet_name=None)`) and passes the sheets straight to `frames.frames_payload` (`web/frames.py:31-38`), which emits `{'columns': list(df.columns), 'rows': json.loads(df.to_json(orient='values'))}` per sheet. `boot.boot_json` (`web/boot.py:34-35`) serialises that with `json.dumps` default separators into the one-line `fw-boot` island. `serve.py:41` and `publish.py:54` both call `page.build`, so anything added to the frames between load and payload reaches both. The xlsx has 14 columns (`Code`, `Song Title`, `Artist`, `Level`, `Type`, `Charter`, `Release`, `Official`, `NoteCount`, `DurationS`, `Difficulty`, `D`, `RemapDiff`, `CalcTier`); `D` has no NaN in any of the 11,904 rows (measured), `RemapDiff`/`CalcTier` are NaN in 4 Guitar rows.

**What the page does with a column it has never seen.** `state.ordered()` (`web/static/js/state.js:76-82`) lists the viewer's saved order, then `DISPLAY_ORDER`, then any sheet column neither names, so a new column lands at the far right unless `DISPLAY_ORDER` places it. `format.lab()` falls back to the key. `query.isNumeric()` (`web/static/js/query.js:9-13`) calls a column numeric when every non-null value is a number; `useRange()` (`query.js:36-37`) then gives it a min/max box instead of a checkbox list once it has more than `RANGE_MIN_DISTINCT = 25` distinct values on the sheet (`web/static/js/boot.js:24`). `format.decimals()` (`web/static/js/format.js:31-39`) prints a numeric column with 2 decimals if any value in it has a fraction and 0 otherwise, memoised per sheet and column. `query.compare()` (`query.js:75-76`) sorts numbers numerically; `matchesFilter()` (`query.js:51-53`) applies a range only to numbers. `url.js:23-26` and `:63-67` write and read `r.<col>=lo:hi`. So an integer column with more than 25 distinct values needs no JavaScript to sort, filter, print or share.

**Where a chart is named.** `overlay.heading()` (`web/static/js/overlay.js:19-38`) builds the graph modal's header from the row found by `Code` in the current sheet (`:21`): title, artist, level badge, part, charter, report link. `markup.bodyRow()` (`web/static/js/markup.js:77-85`) gives every `<tr>` a `title` of `UI.row_tip` ("Click for the difficulty graph", `functions/labels.py:361`); `table.draw()` (`web/static/js/table.js:77-79`) looks up the `Code` index once and passes it per row.

**The range box.** `dropdown_view.rangeBody()` (`web/static/js/dropdown_view.js:15-33`) prints the column's min and max as placeholders with `v.toFixed(2)` (`:19`) regardless of the column's own decimals, so `NoteCount` reads "min 12.00" today and `Pct` would read "max 100.00".

**Measured on `metrics/Local_metrics_09072026-2031.xlsx`** (the pair the live site was published from, not a committed file; `.venv` python, pandas 3.0.5). "Rows sharing a D" counts rows whose `D` equals at least one other row's in the same pool; "tie groups" counts distinct `D` values held by more than one row:

| Sheet, level | n | distinct D | rows sharing a D | tie groups | largest tie | median D |
|---|---|---|---|---|---|---|
| Guitar Expert | 1,853 | 1,599 | 465 | 211 | 5 | 30.49 |
| Guitar Hard | 1,584 | 1,190 | 702 | 308 | 5 | 17.34 |
| Guitar Medium | 1,584 | 973 | 1,010 | 399 | 7 | 8.30 |
| Guitar Easy | 1,589 | 714 | 1,277 | 402 | 9 | 4.23 |
| Bass Expert | 1,266 | 1,032 | 435 | 201 | 4 | 13.09 |
| Bass Hard | 1,257 | 928 | 583 | 254 | 7 | 9.63 |
| Bass Medium | 1,258 | 751 | 837 | 330 | 6 | 5.44 |
| Bass Easy | 1,257 | 562 | 1,027 | 332 | 8 | 2.82 |
| Keys, each level | 64 | 58 to 62 | 4 to 12 | 2 to 6 | 2 | 1.61 to 12.41 |

Ties are real and common: 1,277 of 1,589 Easy Guitar rows share a `D` with another row (402 tie groups; 875 rows would be renumbered by `method='first'`), and the 9-way tie at D 1.98 spans seven releases, from Guitar Hero and Rock Band 2 to a Custom Songs Central chart. The ties exist because analyze rounds `D` to 2 dp before writing (`analyze.py:205`, then sorts by `D` descending on `:206`), which is also what makes "equal printed D, equal Pct" hold. Any percentile that broke ties by row order would hand those nine charts nine different numbers.

The Guitar sheet is 6,339 Lead, 267 Rhythm and 4 Co-op rows (1,753 / 99 / 1 at Expert). Expert Guitar is 1,467 official and 386 custom rows. Computing the column over all three sheets takes about 3 ms (2.2 to 3.4 ms across runs); reading the workbook takes 0.73 s. Size: in today's `boot_json` (default separators) the boot island grows from 1,778,082 to 1,824,555 bytes (+46,473, 2.6%). Serialised compactly, as section 05 will (`separators=(',',':')`), the three sheets grow by 34,566 bytes, Guitar's rows by 19,180.

Worked values from the same spreadsheet, with the rule chosen below: `02780325XG` (Sirius Bismuth, D 1047.43) is 100; `10145439XG` (Through The Fire & Flames, D 169.93) is 98; `72933816XG` (Beautiful Disaster, Expert, D 15.87) is 13, and the same song reads 16 at Hard, 10 at Medium, 18 at Easy. 186 Expert Guitar rows are at 90 or above (44 of them official; 664 across all four Guitar levels); exactly one row per (sheet, level) is 100 except Hard and Medium Guitar, where a two-way tie at the top gives two. The four Guitar rows with no Expert anchor (NaN `RemapDiff`, all Easy) still get a value (7). The column has 101 distinct values on the Guitar and Bass sheets and 64 on Keys.

## Design

**1. Computed in `web/frames.py`, at page-build time, and nowhere else.** A new `add_percentiles(frames)` runs between `load_frames` and `frames_payload` inside `page.build()`. The xlsx, `analyze.COLUMN_ORDER`, `xlsx_format`, the cache and the render header are untouched, so the committed spreadsheets under `metrics/` stay byte-identical and nothing that reads the spreadsheet by column name sees a new column. `serve.py` runs the same `page.build`, so the local preview shows the column too. Rejected: computing in `analyze.py` as an xlsx column, because the value depends on the rest of the library rather than on the chart, and every consumer of the spreadsheet (upstream, Excel users, the committed examples) would carry a site-relative number; computing in the browser, because it would run per sheet per visit on thousands of rows for a value that never changes between publishes, and it would have to be recomputed before `decimals()` memoises.

**2. Population: every row of the sheet at the same `Level`, Official and Custom alike.** The pool is `(sheet, Level)`. Officials and customs are ranked together because the percentile is a property of the chart, not of the view: the opening view filters `Official=true`, but a custom's place among everything scored is exactly the question a custom's percentile answers (the median Expert Guitar custom is at 84 against 41 for officials), and a value that changed with the Official chip would be `Rank` again. The Guitar sheet pools Lead, Rhythm and Co-op because they share the `guitar` calibration group (`functions/formula.py:32-38`, `functions/instruments.py:157-162`): they are already binned by the same `REMAP_BINS`, they sit in the same sheet and the same list, and a per-part pool would give the one Co-op Expert chart a 100 and rank 99 Rhythm charts against each other only. A Rhythm chart therefore reads low (median Expert Rhythm is 33): that is the reading intended, and the help text says so. Rejected: per `(Type, Level)`, for the reasons above; per sheet regardless of level, because a Medium chart's `D` is not comparable with an Expert's.

**3. The rule: pandas `rank(method='max')`, scaled to 100, floored.** For each row, `Pct = (rank_max * 100) // n`, where `rank_max` is the row's `D` rank within its `(sheet, Level)` group with ties taking the highest rank of the group (`method='max'`), and `n` is the group's count of non-null `D`. This is `rank(method='max', pct=True)` scaled to 0 to 100, but floored. `rank()` returns float64, yet rank and count are whole numbers far below 2^53, so the product and the floor division are exact in doubles and no value lands at 96.999. Properties: equal `D` gives equal `Pct` (measured true on every level of every sheet); the top chart reads 100 (n / n); a value never overstates: at least pct% of the pool has a `D` at or below this one, which is what the sentence "at or above 97% of" says; the bottom of a 1,589-row pool reads 0 and the bottom of a 64-row Keys pool reads 1. Rejected: `method='min'` or `'first'`, which would break the 9-way ties; `round()`, which needs a half-to-even footnote (5 rank positions, 2 on Hard and 3 on Medium Guitar, land exactly on .5) and can overstate by half a point; a strict "count with lower D" numerator, which makes the hardest chart of a 64-chart pool read 98.

**4. Stored as a nullable integer.** The column is `Int64` (pandas nullable), which `to_json` emits as a bare integer or `null` (measured). `astype(int)` would raise `IntCastingNaNError` on any NaN `D` (measured); there are none today, but a null row must degrade to the em dash cell that `markup.bodyCell` already draws for `null` rather than fail the publish. Because every value is an integer, `decimals()` prints `97`, not `97.00`; the column has 101 distinct values on Guitar and Bass and 64 on Keys, so `useRange()` gives it a min/max box (25 is the threshold), which is the right control for "at least 90".

**5. Shown by default, immediately after `D`.** `DISPLAY_ORDER` becomes `('Song Title', 'Artist', 'D', 'Pct', 'CalcTier', ...)`; `DEFAULT_HIDDEN` is unchanged, so no preference migration is needed and section 05's `PREFS_VERSION` stays at its own value. A returning visitor who has dragged columns into a saved `fw.order` sees `Pct` after the columns they placed (that is what `ordered()` does with any column the saved list does not name); "Reset columns" puts it beside `D`. At 390 px, `Pct` takes the slot `CalcTier` has today (x 358 onward, off screen) and `D` stays at 262 to 358; the narrow-screen rules in `app.css:135-171` are not touched.

**6. Spelled out where the chart is named.** `overlay.heading()` adds one `text-secondary` span after the charter, `UI.pct_of` filled with the row's `Pct`, its `Level` and the current sheet name: "At or above 98% of Expert Guitar charts". "At or above" rather than "harder than" because the rule counts the chart itself and its tie group: the top row would otherwise claim to be harder than 100% of a pool it belongs to, and each of the nine charts tied at D 1.98 would be announced as harder than the other eight. The sheet name is `state.sheet`, which is the pool's name by construction. The span is emitted only when the row was found and its `Pct` is a number; a `?code=` for another sheet, which finds no row today, must not print "At or above % of  Guitar charts". Beyond the catalogue line: the row tip, because the heading needs a click and the tip answers the question the cursor is already asking; cost measured under Verification. The row's `title` becomes the same sentence, a newline, then `UI.row_tip`, computed once per row in `draw()` from the `Pct` and `Level` indices looked up beside `codeIdx`; when either index is missing the title is `UI.row_tip` alone, as today. Rejected: putting the sentence in the PNG header, because that is `functions/plot.py` (shared tooling) and it would change the fingerprint inputs and re-render 11,904 graphs for a number that changes with every library update.

**7. One line so the range box reads right.** `rangeBody()` formats its placeholders with `decimals(col)` instead of a fixed `toFixed(2)`, so `Pct` offers "min 0" and "max 100", and `NoteCount` stops offering "min 12.00". A one-token change with no other effect: `D` and `DurationS` keep their two places and m:ss.

**8. Ready for section 10.** `percentile(df, distinct=None)` takes the sheet frame and an optional list of identity columns. With `distinct` given, the pool is the rows with a complete identity deduplicated on `[*distinct, 'Level']`, plus every row whose identity has a null in it, untouched; the rank runs over that pool, and the result is joined back onto every complete-identity row by the same key, so copies of one chart share one value and count once in `n`, while a row with no identity ranks as its own chart. Section 10 passes `distinct=frames.COPY_KEY`, which it defines as `['Type', 'NotesHash']`, its per-chart hash plus the part; `percentile()` appends `Level` itself, so the pool key is the one `add_copies` groups on. `Type` is in the key because the Guitar sheet holds Lead, Rhythm and Co-op rows of one song at one level. Section 05's `SongKey` is per song, one hash over every instrument, and must never be passed here: 271 (song, level) pairs on the Guitar sheet hold two rows (100 at Expert), and a per-song key would hand 192 Rhythm rows the Lead row's number and shift 1,867 Lead rows by losing 271 charts from the pool (measured with the 8-digit code as a stand-in). When a sheet lacks any of the identity columns, `add_percentiles` falls back to the plain pool for that sheet, all or nothing: a partial key (`Type` alone) would collapse every chart of a part into one, and a pre-10 workbook is still worth the percentile the page shows today. Section 10's draft offers "skip the column when `NotesHash` is absent" as its recommendation; this section decides the fall-back instead, and section 10 replaces its own reference shape (`rank(pct=True) * 100` as a float) with a call to this function, so floor and `Int64` are decided once. The join path is written and checked now (synthetic cases below) so that section 10's change is an argument, not a rewrite.

**9. Not in the fingerprint.** `bundle.fingerprint` hashes notes, meta, the difficulty block and the theme (`web/bundle.py`); `Pct` is not among them and must not be added, so a publish after this section re-renders no graph, and a library update that shifts every percentile still re-renders only the charts whose own inputs moved.

## Data and interfaces

**Column key and label** (`functions/labels.py`):

| Item | Value |
|---|---|
| Column key | `Pct` (a string, the xlsx-style short key; it is what the URL and filters use: `r.Pct=90:`) |
| `COLUMN_LABELS['Pct']` | `'Percentile'` |
| `COLUMN_HELP['Pct']` | `'Sits at or above N% of the charts on this sheet at the same level, officials and customs together. Ties share a value and the top chart reads 100. The Guitar sheet pools Lead, Rhythm and Co-op, which share one calibration group.'` |
| `DISPLAY_ORDER` | `('Song Title', 'Artist', 'D', 'Pct', 'CalcTier', 'Level', 'Type', 'DurationS', 'NoteCount', 'Charter', 'Release', 'Difficulty', 'RemapDiff', 'Official', 'Code')` |
| `DEFAULT_HIDDEN` | unchanged |
| `UI['pct_of']` | `'At or above {pct}% of {level} {sheet} charts'` |
| `EXPLAINER`, "Reading the tiers" body | one sentence appended: `' Percentile is where a chart’s D sits among the charts on its sheet at the same level, so it moves as the library grows.'` (`labels.py` is ASCII-only and spells every apostrophe as the `’` escape; keep it that way) |

Nothing goes into `MISSING_VALUES`, `TIME_COLUMNS`, `VALUE_ORDER`, `VALUE_LABELS` or `query.SEARCH_COLS`.

**Row value**: integer 0 to 100 inclusive, or `null` when the row's `D` is null. It occupies the last slot of every row array and the last entry of `columns`, because `frames_payload` emits `df.columns` in frame order and the column is appended after the xlsx columns. Today that is index 14: `['02780325XG', 'Sirius Bismuth', 'Blitz Lunar', 'Expert', 'Lead', 'Peddy', 'S Hero', false, 4026, 190, 9, 1047.4300537109, 6.0, 12.0, 100]`. Nothing in the page reads it by position; `idx('Pct')` finds it.

**`web/frames.py`** (new symbols):

```python
PCT_COL = 'Pct'        # the column added to every sheet
PCT_OF = 'D'           # what is ranked
PCT_WITHIN = 'Level'   # the pool a row is ranked within, per sheet


# Share of the sheet's charts at the same level whose D is at or below this
# row's, as a whole number 0-100. Ties take the top rank of their group, so
# equal D means equal percentile, and the division floors, so a value never
# overstates. rank() is float64; the values are whole numbers, so the floor
# division is exact.
# distinct: identity columns; when given, each distinct (identity, level)
# counts once, so copies of one chart share a value and are not counted twice.
# A row with a null anywhere in its identity ranks as its own chart. Section 10
# passes ['Type', 'NotesHash']; a per-song key would merge a song's Lead,
# Rhythm and Co-op rows. Needs a unique index (read_excel gives one).
def percentile(df, distinct=None):
    if distinct is None:
        pool, has = df, None
    else:
        keys = [*distinct, PCT_WITHIN]
        has = df[distinct].notna().all(axis=1)
        pool = pd.concat([df[~has], df[has].drop_duplicates(subset=keys)])
    grouped = pool.groupby(PCT_WITHIN)[PCT_OF]
    pct = (grouped.rank(method='max') * 100 // grouped.transform('count')).astype('Int64')
    if distinct is None:
        return pct
    kept = pool[has.reindex(pool.index)]
    lookup = kept[keys].assign(**{PCT_COL: pct[kept.index]})
    merged = df[keys].merge(lookup, on=keys, how='left')[PCT_COL].set_axis(df.index)
    return merged.where(has, pct.reindex(df.index))


# A sheet without D or Level is left alone. A sheet missing any identity column
# gets the plain pool: a partial key would collapse charts, and an older
# spreadsheet is still worth the percentile it had before section 10.
def add_percentiles(frames, distinct=None):
    for df in frames.values():
        if PCT_OF not in df.columns or PCT_WITHIN not in df.columns:
            continue
        use = distinct if distinct and all(c in df.columns for c in distinct) else None
        df[PCT_COL] = percentile(df, use)
    return frames
```

Verified (pandas 3.0.5) against the synthetic frame `Level = [Expert x4, Easy x2, Expert]`, `D = [10, 10, 20, 5, 1, 2, NaN]`, `Type = Lead x7`, `Key = a a b c d e f`:

| Call | Result |
|---|---|
| `percentile(df)` | `[75, 75, 100, 25, 50, 100, <NA>]` |
| `percentile(df, distinct=['Type', 'Key'])` | `[66, 66, 100, 33, 50, 100, <NA>]` (the Expert pool is a, b, c, f, of which three have a `D`) |
| same, with the two `a` keys set to `None` | `[75, 75, 100, 25, 50, 100, <NA>]` (each null-identity row is its own chart again) |
| `add_percentiles({'x': df.drop(columns=['Key'])}, distinct=['Type', 'Key'])` | the plain `[75, 75, 100, 25, 50, 100, <NA>]`, no error |
| `add_percentiles({'x': df.drop(columns=['D'])})` | the frame back with no `Pct` column |
| `to_json(orient='values')` of the frame with `Pct` | emits `75` and `null` |

**`web/page.py`**: `build()` becomes

```python
xlsx_path, sheets = frames.load_frames(header, xlsx_path)
frames.add_percentiles(sheets)
```

before `total` is counted. The count is unaffected (no rows are added). `frames.codes_in` is unaffected.

**JavaScript** (`web/static/js/`):

- `overlay.js` adds `import { t } from "./format.js";` (it already imports `esc` and `state`); `heading()` computes `const pct = get("Pct")` and, when `typeof pct === "number"`, appends `'<span class="text-secondary">' + esc(t("pct_of", { pct: pct, level: get("Level"), sheet: state.sheet })) + "</span>"` after the charter span and before the report link.
- `markup.js`: `bodyRow(row, visibleCols, code, rank, tip)`; the `<tr>` title is `esc(tip)`. Nothing else in the row changes.
- `table.js`: in `draw()`, beside `codeIdx`, `const pctIdx = cols().indexOf("Pct"), levelIdx = cols().indexOf("Level");` and per row `const tip = pctIdx >= 0 && levelIdx >= 0 && typeof r[pctIdx] === "number" ? t("pct_of", { pct: r[pctIdx], level: r[levelIdx], sheet: state.sheet }) + "\n" + UI.row_tip : UI.row_tip;`. `t` and `UI` are already imported there.
- `dropdown_view.js`: adds `decimals` to its `./format.js` import; `rangeBody`'s `asText` becomes `v => TIMECOLS.has(col) ? mmss(v) : v.toFixed(decimals(col))`.

**URL**: no new parameter. `r.Pct=lo:hi` is the existing range form; `?r.Pct=90:` is "at least 90", `?sort=Pct&dir=asc` sorts by it. A link naming any `f.` or `r.` key replaces both opening filters (`url.js:58-59`; `main.js:58-59` sets `Level=Expert` and `Official=true`), so `?r.Pct=90:` alone shows all four levels; `?f.Level=Expert&r.Pct=90:` is the Expert-only form.

**Interaction with section 05.** `page.build()` applies `add_percentiles` before `sheet_json`, so `data/<slug>.<hash8>.json` carries `Pct` as its last column and the manifest's `columns` lists it last, after `SongKey` once 05's analyze change lands (`SongKey` is an xlsx column; `Pct` is appended after the read). Section 05 must add: `'Pct'` at the end of the `columns` example in its boot payload, and its `tests/test_bundle.py` round-trip must compare `data/*.json` against the frames after `add_percentiles`, not against `load_frames` alone. With 05's `sheetOfCode`, a `?code=<bass>` link selects Bass before `heading()` runs, so the sentence names the right sheet.

**Interaction with section 10.** `add_percentiles(sheets, distinct=['Type', 'NotesHash'])` at the same call site, called after 10's `add_copies`; the help text then needs "counting each chart once however many packs carry it", which section 10 owns. Section 10 drops its own reference shape and its "skip the column when `NotesHash` is absent" recommendation in favour of the function and the fall-back defined here.

**Interaction with sections 03, 06 and 07.** Section 07 prints `Pct` beneath `D` in each cell of the song grid (07, design 4) and section 06 appends it to the second line of the canvas heading (06, line 2 of the heading); both read the column by name from the manifest. Section 03 owns the one sentence telling visitors that percentiles move with every update: it is in its `UI['changelog_intro']`, written by 03 whether or not this section has landed.

## Files touched

- `web/frames.py`: `PCT_COL`, `PCT_OF`, `PCT_WITHIN`, `percentile()`, `add_percentiles()`.
- `web/page.py`: `build()` calls `frames.add_percentiles(sheets)` after `load_frames`.
- `functions/labels.py`: `COLUMN_LABELS['Pct']`, `COLUMN_HELP['Pct']`, `DISPLAY_ORDER`, `UI['pct_of']`, one sentence in `EXPLAINER`.
- `web/static/js/overlay.js`: `heading()` gains the percentile span; imports `t`.
- `web/static/js/markup.js`: `bodyRow` takes the row tip as an argument.
- `web/static/js/table.js`: `draw()` looks up `Pct` and `Level` once and builds the tip per row.
- `web/static/js/dropdown_view.js`: `rangeBody` placeholders use `decimals(col)`.
- `README.md` section 5: one bullet naming the Percentile column and what it compares against.
- `CLAUDE.md`: the `web/frames.py` row of the module table (`CLAUDE.md:154`), and the `functions/labels.py` paragraph's `DISPLAY_ORDER` clause (`CLAUDE.md:214`), mention the page-built percentile.

No new files. `analyze.py`, `functions/xlsx_format.py`, `functions/plot.py`, `web/bundle.py`, `web/boot.py` and `deploy.py` are not touched. The tests named under Verification are section 04's files, not this section's.

## Steps

1. **The column.** Add the three constants and the two functions to `web/frames.py`; call `add_percentiles` in `page.build()`. Check, read-only, with the venv python: `from web import frames; p, s = frames.load_frames('Local'); frames.add_percentiles(s); print([list(d.columns)[-1] for d in s.values()], s['Guitar'].set_index('Code').loc['02780325XG', 'Pct'], s['Guitar'].groupby('Level')['Pct'].max().tolist(), s['Guitar'].groupby(['Level', 'D'])['Pct'].nunique().max())` prints `['Pct', 'Pct', 'Pct'] 100 [100, 100, 100, 100] 1`, and the synthetic frame from Data and interfaces gives every row of that table. On serve the column appears last, headed `Pct` with no tooltip, until step 2 names and seats it; that is expected of this commit. Commit: `frames: a per-sheet, per-level percentile of D, computed when the page is built`
2. **Label, help, order, explainer.** The five `labels.py` edits. Check by hand on `python serve.py --header Local` (section 04's suites do not exist yet): the header reads Rank, Song, Artist, Difficulty (D), Percentile, Calc Tier, ...; the first row (sorted by D, Expert, Official) shows an integer with no decimal point in the Percentile cell; the column's caret opens a min/max box; entering min 90 and Apply leaves 44 rows with the opening Expert and Official filters, 186 once the Official chip is cleared; the header tooltip carries the help text; "How it works" still shows four headings and the new sentence. Commit: `label the percentile, and seat it beside D`
3. **Heading, row tip, range placeholders.** The four JavaScript edits. Check by hand on the same serve: click Through The Fire & Flames, the modal heading ends "At or above 98% of Expert Guitar charts" before the report link; hovering any row shows the same sentence over "Click for the difficulty graph"; the Percentile filter placeholders read "min 0" and "max 100" and Notes' read "min 12" style integers; switch to Bass and open a graph, the sentence says "Bass". Commit: `say where a chart sits in the graph heading and the row tip`
4. **Docs.** README section 5 bullet; CLAUDE.md's two sentences. Commit: `docs: the percentile column`
5. **Publish and deploy.** `python publish.py --header Local` reports zero graphs rendered and `index.html` rewritten; `python deploy.py --dry-run`, then the real deploy through section 01's checklist; tag `fretladder-v<next>`.

## Verification

- Step 1's python check, plus timing: `add_percentiles` over the three sheets in under 10 ms (measured about 3 ms).
- `python publish.py --header Local` after step 3: the banner says every graph is unchanged (0 rendered), and `grep -o '"Pct"' site/Local/index.html | wc -l` prints 6 (three `columns` lists, the `labels` map, the `help` map and the `order` list; the island is one line, so `grep -c` would print 1 whatever it held). `wc -c site/Local/index.html` grows by 46,473 bytes (the boot JSON is `json.dumps` with default separators).
- Serve parity: `python serve.py --header Local` shows the column and the heading sentence; the same spreadsheet published and served with `python -m http.server 8000 --directory site/Local` shows identical values for `02780325XG` (100), `10145439XG` (98), `72933816XG` (13).
- A URL check: open `?f.Level=Expert&r.Pct=90:` and confirm the Percentile header is marked filtered, the count footer reads "186 of 6610" (`paintFooter`, `table.js:14`, prints raw numbers; only the strapline has thousands separators), the Expert chip alone is lit and neither Official chip is, because the link replaced both opening filters (`url.js:58-59`), and every visible Percentile cell is 90 or more. `?r.Pct=90:` alone reads "664 of 6610" with all four level chips lit. `?sort=Pct&dir=asc` puts a 0 first.
- 390 px re-measure, by hand until section 04's `frame.html` exists: a throwaway page holding a `390x820` iframe of the served page, measured synchronously in the outer window's `load` handler (the transcript-era form; headless Chrome floors its own viewport at 500 px). Assert `D`'s right edge at or under 390 and its left edge at or over 0; measured 262 to 358 before this section, recorded as a note, not a threshold. Percentile starts where Calc Tier started (358) and is off screen, as Calc Tier is today. At 1440 px, note whether the table now exceeds the viewport (it was 1,409 px wide at 1,424; the new column adds roughly 60 to 70 px, which the auto layout takes back from the two 300 px title columns by wrapping): either outcome is acceptable, but record which, because section 04's `fade.js` suite (the mask is `static/js/scroll.js`) asserts the fade only when `scrollWidth > clientWidth`.
- Repaint cost with the longer row title: clearing the Official filter on the Guitar sheet in headless Chrome stays under 100 ms (71 ms measured before this section for 6,610 rows).
- For section 04, which owns `tests/`, the assertions this section adds to its deliverables: `test.js`, "Percentile is the fifth header after Rank, Song, Artist, Difficulty (D), and the first row's Percentile cell has no decimal point"; `order.js`, "the Percentile filter opens a min/max box (`#ddLo` present, no `.form-check`), and min 90 plus Apply leaves only rows whose Percentile is at least 90 with the footer count equal to the number of such rows"; `launch.js`, "the graph heading matches `/At or above \d+% of Expert Guitar charts/` and the report link still follows it"; `roundtrip.js`, `&r.Pct=90:` appended to 04's composed `roundtrip_query` (its `f.Level=Hard` already keeps the `named` branch), asserting the Percentile `th` has class `filtered` and the count equals the rows in the view with Percentile at or above 90; `frame.html`, "D right edge at or under 390 and left edge at or over 0". A `tests/test_percentile.py` asserts every row of the synthetic table above, that every level's maximum is 100 on the fixture workbook, that equal `D` gives equal `Pct` in every level, that the last column of every `frames_payload` sheet is `Pct` with integer or null values only, and that a workbook sheet without `D` passes through `add_percentiles` unchanged.

## Risks and gotchas

- A percentile is relative to the library on the day. Adding a pack moves every value on its sheet, including for charts that did not change. The strapline's chart count is the only denominator the page shows; section 03's `UI['changelog_intro']` carries the sentence that percentiles shift with each update. The PNGs do not carry the value, so this costs no render.
- `state.sheet` is the sheet name from the workbook (`Guitar`, `Bass`, `Keys`), so the sentence reads "Expert Guitar charts" on a sheet that also holds Rhythm and Co-op. That is the pool, and the help text says so; do not substitute `Type` into the sentence.
- Keys has 64 charts per level, so its steps are 1.56 wide and its bottom chart reads 1. A future Drums sheet (section 11) gets the column for free the day it exists.
- A sheet with 25 or fewer distinct percentiles gets the checkbox list instead of the min/max box, as any numeric column does (`useRange`, `query.js:36-37`): the local, uncommitted Tiny workbook (`metrics/Tiny_metrics_09072026-1622.xlsx`, 32 Guitar rows, 4 Bass) gives 8 distinct values on Guitar and 1 on Bass. The production sheets have 101, 101 and 64.
- `ordered()` seats an unnamed column after the viewer's saved order, so a visitor who reordered columns sees Percentile to the right of what they moved, not beside `D`, until they reset. Section 05's preference version only re-applies `DEFAULT_HIDDEN`; it must not be bumped for this section, since nothing is hidden.
- `astype('Int64')` is load-bearing: plain `int` raises on a NaN `D`. `D` has no NaN in any analyze output to date, but keep the nullable type so a future one becomes a dash, not a failed publish.
- `heading()` finds the row in the current sheet only (`overlay.js:21`); until section 05 lands, a `?code=` for another sheet gets no sentence rather than a wrong one, because the span is guarded on `typeof pct === "number"`.
- `rank(method='max')` on a group whose `D` is entirely NaN returns NaN and `transform('count')` returns 0; the division then yields NaN, not a ZeroDivisionError, and `Int64` stores it as null. Not reachable today, noted so the guard is not "fixed" away.
- In the `distinct` path, a row with a null anywhere in its identity ranks as its own chart, and a sheet missing any identity column falls back to the plain pool. pandas would otherwise merge NaN keys to NaN (measured: keys `[None, None, 'x']` with D `[10, 20, 30]` give `[50, 50, 100]` under a plain merge) and `df[keys]` raises `KeyError` on a missing column; both are handled in the function, not by the caller. `percentile` also relies on a unique frame index for `pct[kept.index]` and `reindex`; `read_excel` gives a `RangeIndex`, so never pass a concatenated frame without resetting it.
- The row `title` grows from 30 to about 80 characters on 6,610 rows; that is inside the same `innerHTML` string the table already builds, measured under Verification.
- The leaderboards userscript (`../fretladder-leaderboards.user.js` (the Tampermonkey prototype kept beside the repo, untracked)) reads rows by column name through `columns.indexOf` (`user.js:110-116`) and inserts its box after `#modal .mhead` (`user.js:323-331`); an appended column and one more span inside the heading leave it working. `.mhead` has `flex-wrap:wrap` (`app.css:132`), so the extra span wraps rather than pushing the report link off the card.
- `frames_payload` emits `Pct` as the last column; nothing may come to rely on that index. Section 05 appends `SongKey` in the xlsx (before `Pct`), and the page-build columns of 03 (`Added`) and 10 (`Copies`) are appended before it: the composed order, stated once in section 10, is the xlsx columns, `Added`, `Copies`, `Pct`. The page reads by name.
- Sorting by Percentile: `Array.prototype.sort` is stable, and `rowsAll()` is in the spreadsheet's `D`-descending order (checked on the Local workbook), so rows sharing a percentile keep their `D` order within the group. Do not add a secondary key.
- The committed example spreadsheets under `metrics/` do not gain a column and must not be regenerated for this section.

## Out of scope and follow-ups

- Percentile over distinct charts, so a chart shipped in eight packs counts once: section 10, by passing `distinct=['Type', 'NotesHash']` to the function defined here.
- Section 07 prints each level's `Pct` beneath its `D` in the song grid and section 06 appends the sentence to its canvas heading; both read the same row by name and need nothing more from this section.
- A per-part percentile (Lead only, Rhythm only) as a second column: not planned; a `Type` filter plus sorting by `D` already gives a within-part ordering, and a second percentile column would double the explaining for a pool the calibration does not distinguish.
- Optional follow-up: a percentile of the Expert `D` shown on every level, matching how `CalcTier` is anchored. Needs a decision on whether the site wants two percentiles; nothing blocks it technically.

## Open questions

None.
