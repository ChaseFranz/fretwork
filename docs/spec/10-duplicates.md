# 10. Duplicate charts

**Status:** Ready after 05

**Effort:** M, dominated by the rebuild-analyze-publish cycle each step needs to prove itself against `songs/`, not by the code, which is a hash in build, one column in analyze, one derived column in frames, one argument at 02's call site and one line in the graph heading.

**Depends on:** 02 (percentile: `Pct` is ranked by 02's `percentile(df, distinct)`, and this section supplies the `distinct` argument), 05 (data model v2: `SongKey`, `HIDDEN_COLS`, `PREFS_VERSION`, the per-sheet JSON and its `columns` manifest, `SHEET_OF_CODE` so a `?code=` link opens on the right sheet). 06 if it has landed: the copies line then goes on 06's `.mhead` line 1, the click branch sits before 06's backdrop test, and 06's `trapTab` reaches the links; see Design 5 for both orders.

## Goal

Recognise the same chart wherever it appears. Build hashes every chart's notes; analyze writes the hash as a hidden `NotesHash` column; the page derives a `Copies` count per row (1 for unique, hidden by default, one click away), the graph heading lists the other folders that carry the same chart with a link that opens each one's graph, and the percentile of section 02 counts a chart once however many packs it is in. Rows are not merged: every copy keeps its own row, code, PNG and report link.

## Why

- The library already carries the same chart more than once, and the production library will carry more. On the newest cache, 11,904 five-fret charts carry 11,714 distinct note streams and 11,816 distinct (part, level, notes) charts: 176 charts are one of 88 pairs that live in two song folders, across 46 songs. Every pair measured is official against official: Guitar Hero against Guitar Hero II DLC 38 pairs, Guitar Hero against Guitar Hero Encore: Rocks The 80s 30, and 20 pairs that are two folders in one pack (Warriors Of Rock 8, Metallica DLC 4, GH III DLC 4, GH II 4). A custom pack that re-hosts an official chart is the case the production library adds, and the table should say so rather than show two identical `D` values with no explanation.
- A percentile (section 02) over rows counts a duplicated chart twice, so the 19 duplicated Expert Guitar charts each push everything below them down a place twice. Over distinct charts the Guitar Expert population is 1,834, not 1,853.
- Title and artist cannot do this job. 115 title+artist groups cover 237 folders, but only 14 of them have an identical Expert guitar chart: the other 101 are re-charts, re-releases or covers with different notes. In the other direction, 31 of the 88 content pairs spell the title or artist differently even after case and whitespace are normalised (`The Exies (WaveGroup)` against `Exies (WaveGroup)`; 42 on the raw strings, `Bark at the Moon` against `Bark At The Moon`), so a title key would miss a third of the real pairs and merge seven times as many false ones. Content is the only key that is right in both directions.
- `SongKey` (section 05) is a per-song key: two folders share one only when every chart matches. That catches 20 of the 46 songs; the other 26 share some charts and not others (a GH II DLC folder with the same guitar as the GH one but a bass chart the original lacked). Sections 03 and 07 need the song key; this section needs the chart key. They are different things and both are cheap.

## Current state

**Nothing in the cache, the spreadsheet or the page ties two charts together.** Song identity is the resolved folder path (`build.py:55,66`), codes are a SHA-1 of that path (`functions/cache.py:61-63`), and the level entry stored at `build.py:94` is exactly the parser's `{'notes': {...}}` dict. `cache.entries_by_code` spreads that dict into the entry (`functions/cache.py:162-171`), so any key added beside `notes` reaches render, serve and publish for free. The documented shape is the docstring at `functions/cache.py:6-38`.

**Analyze** builds one flat dict per row in `song_row` (`analyze.py:45-71`), called at `analyze.py:153-155` with `song['meta']` and `inst_entry['notes']`, cuts the frame to `COLUMN_ORDER` (`analyze.py:37-42, 204`) minus `xlsx_format.DEFAULT_HIDDEN_COLS` unless `config.EXTRA_METRICS` (`analyze.py:178-180`), and section 05 adds `HIDDEN_COLS` (hidden in Excel, never dropped) for `SongKey`, hidden at `functions/xlsx_format.py:167-168`. The summary block is `analyze.py:222-225`.

**The page** reads whatever columns the xlsx has (`web/frames.py:15-19`, `:31-37`, no allow-list), and section 05 moves the rows into `data/<slug>.<hash8>.json` with the column list in the boot manifest, where `Pct` (02) and `Copies` (this section) are appended at page-build time inside `page.build()` (`web/page.py:144-154` today). A column that is numeric with 25 or fewer distinct values gets a checkbox filter (`web/static/js/boot.js:24`, `query.js:36-37`), prints with 0 decimals when every value is an integer (`format.js:31-39`), sorts numerically (`query.js:75-76`), is shareable as `?f.<col>=` (`url.js:60-62`), and appears in the chooser under its `COLUMN_LABELS` label (`chooser.js:10-21`, `format.js:6`). It is hidden on a first visit only if `labels.DEFAULT_HIDDEN` names it, and for a returning visitor only after section 05's `PREFS_VERSION` bump.

**The graph heading** (`web/static/js/overlay.js:19-38`) finds the row by `Code` in the current sheet and prints title, artist, level badge, part, charter and the report link; `openGraph` (`overlay.js:40-57`) records `document.activeElement` as the element to hand focus back to (`:45`). The router closes the modal on any click inside it except on a `.mhead a` (`router.js:56`), and swallows Tab whole while a dialog is open (`router.js:94`), so the report link is reachable by pointer only. A chart's copies are always in the same sheet as the chart, because the key includes the instrument and `instruments.SHEET_GROUPS` (`functions/instruments.py:157-162`) groups by instrument, so the current sheet is the only one the heading needs to search.

**Fingerprints.** `bundle.fingerprint` (`web/bundle.py:69-81`) pickles a tuple whose elements include `time_ms.tobytes()` and `lanes.tobytes()` as two separate items (`:73-76`), plus the meta, the difficulty block and the render settings. None of what this section adds is printed on the PNG, and a new key on the entry dict is not in `parts`, so no graph re-renders.

**Measured on `caches/Local_cache_09102026-2324.pkl`** (1,758 songs, 15,660 codes; hashed with the key this section uses):

| Measure | Value |
|---|---|
| Five-fret charts, distinct SHA-1 of `time_ms` bytes + `lanes` bytes | 11,904 charts, 11,714 distinct (same count at 12 hex digits and at 40, so no truncation collision) |
| Distinct (instrument, level, hash) | 11,816 |
| Time to hash every chart, drums included | 0.06 s (15,660 entries) |
| Groups keyed by (instrument, level, hash) spanning more than one song | 88, every one a pair, 176 charts, 46 songs |
| Of those, guitar / bass | 76 (Easy 20, Medium 19, Hard 18, Expert 19) / 12 (3 per level) |
| Groups keyed by hash alone | 124 groups, 314 charts: 67 groups (176 charts) span two songs, 57 groups (138 charts) lie inside one song |
| Within one (song, instrument): Hard equals Expert | 58 pairs over 55 songs; all four levels equal in 21 |
| Same song, same level, different instrument, same notes | 21 (Lead = Rhythm 10, Lead = Bass 7, Lead = Co-op 4) |
| Cross-song groups spanning instruments | 0 |
| Pairs whose title or artist text differ | 31 of 88 (lower-cased, trimmed; 42 on the raw strings) |
| Pairs whose two folders share a `Release` | 20 of 88 (Warriors Of Rock 8, Metallica DLC 4, GH III DLC 4, GH II 4) |
| Pairs mixing `.chart` and `.mid`, or differing in the `song.ini` diff tag; pairs involving the `Custom` default release | 0, 0, 0 |
| Title+artist groups (lower-cased, trimmed) | 115 groups, 237 folders, 14 with identical Expert guitar |
| Songs in pairs that are whole-song duplicates (`SongKey` equal) | 20 of 46 |
| Guitar rows per level, and distinct charts | Expert 1,853 / 1,834, Hard 1,584 / 1,566, Medium 1,584 / 1,565, Easy 1,589 / 1,569; Official Expert 1,467 / 1,448 |
| Bass rows per level, and distinct | 3 fewer at every level (Expert 1,266 / 1,263); Keys no duplicates |
| Rows with `Copies` > 1 | Guitar 152, Bass 24, Keys 0; every value is 1 or 2 |
| Rows whose `Release` is the unmatched-icon default `Custom` (`parsers/ini_parser.py:109`) | 31 rows, 7 songs, none in a pair |
| Per-sheet JSON growth for `NotesHash` + `Copies` (raw / gzip) | Guitar +112,391 / +64,320 bytes, Bass +85,667 / +49,599, Keys +4,373 / +2,271; 17 bytes per row raw |
| Unstyled Guitar xlsx growth for `NotesHash` | 592,522 to 676,839 bytes (+14.2%) |
| `add_copies` over all sheets; 02's `add_percentiles` with `distinct` | 7 ms; 16 ms |
| Guitar rows whose `Pct` changes when copies count once | 1,023 of 6,610 |

## Design

**1. One hash per chart, computed in build, stored beside the notes.** This section defines the hashing primitive section 11 names: `cache.stream_bytes(notes) -> bytes` returns `time_ms.tobytes() + lanes.tobytes()` for a flat stream and `b'hand' + stream_bytes(hand_mask) + b'kick' + stream_bytes(kick_mask)` for a drums pair, and `cache.notes_hash(notes)` is the first 12 hex digits of SHA-1 over it. Section 11 then consumes both functions rather than defining them, and every drums entry carries a defined value from today rather than `None`. Build stores the hash as `notes_hash` on the level entry next to `notes` (`build.py:94`), 0.06 s for the whole library. `bundle.fingerprint` is not touched: its tuple holds the two byte strings as separate elements, and replacing them with one concatenation changes the pickle and so every fingerprint (checked: `sha1(pickle(('x', a, b)))` and `sha1(pickle(('x', a + b)))` differ), which would re-render 11,904 PNGs for nothing. Rejected: hashing in analyze instead, because render and the graph route get the entry from the cache and section 07 will want the hash without opening the spreadsheet; hashing quantised milliseconds, because raw float64 bytes already give the same 88 pairs and no pair crosses formats, so there is nothing to gain and a rounding rule to document; separators between `time_ms` and `lanes` in the flat form, because the two arrays have equal length and fixed widths, so the boundary is already determined.

**2. The duplicate key is (part, level, hash) across different songs.** Within one song, Hard equals Expert byte for byte in 58 (song, instrument) pairs and all four levels are equal in 21; a Lead chart equals its own Rhythm, Co-op or Bass chart at the same level in 21 cases. None of those is a duplicate a reader means: they are one song charted lazily. So a copy is another row on the same sheet with the same `Type`, the same `Level` and the same `NotesHash`. The page keys on the xlsx columns `Type` and `Level` (never on the code's suffix letters), and the pipeline never needs the key at all. Rejected: hash alone (merges the within-song groups, 138 charts wrongly); (sheet, level, hash) without part (merges the 14 Lead = Rhythm and Lead = Co-op cases, which sit on the Guitar sheet); title+artist (see Why).

**3. `NotesHash` in the spreadsheet, hidden; `Copies` on the page only.** Analyze writes `NotesHash` as a text column after `SongKey` and section 05's `HIDDEN_COLS` hides it in Excel. `Copies` is derived at page-build time in `web/frames.py`, exactly where 05 says page-only columns go, so the committed spreadsheet format gains one raw key and nothing derivable. A spreadsheet user gets the same count with `COUNTIFS` over `NotesHash`, `Type`, `Level`. Rejected: `Copies` in analyze, because it is a function of the sheet's other rows and would change whenever `XLSX_LEVELS` or `EXTRA_METRICS` change the row set; a `CopyCodes` text column carrying the other codes instead of shipping the hash (smaller by about 100 KB gzipped across the site), because it puts codes in a filter list, gives the chooser a column nobody would show, and leaves section 07 with no hash in the browser.

**4. Rows are not collapsed.** Each copy keeps its row, for four reasons that are each sufficient. Official against Custom is real information: a reader filtering to Custom should see the custom pack's copy, and the Official chip must keep meaning what it means. Each copy has its own code, its own PNG and its own report link, and a rating complaint about "the one in pack X" must arrive naming that copy. `Rank` numbers rows in the view and stays a plain counter; a fold would need a rule for which copy survives and a second count. And the copies sort adjacent anyway, because identical notes give identical `D`, `NoteCount` and `DurationS`, so the table already shows the pair side by side; `Copies` explains why. Rejected: a fold in `draw()` with a "+1 pack" span, because search and filters run before the fold and the count footer, the URL and `Rank` would all need a second notion of "row".

**5. The graph heading names the other folders.** Inside the `.mhead` element the modal shows `Same chart in: Guitar Hero II DLC (Official)`, one link per copy, each opening that copy's graph in place. The link text is the copy's `Release` plus `(Official)` or `(Custom)` through `VALUE_LABELS.Official`. When the copy's `Release` is the unmatched-icon default `Custom` (`parsers/ini_parser.py:109`) the text uses the copy's `Charter` instead, so it reads `Chezy (Custom)` rather than `Custom (Custom)`; when that is empty too, the code. When the copy's text equals the open chart's own (20 of the 88 pairs: two folders in one pack, such as `Sudden Death` and `Sudden Death (Career Version)` in Warriors Of Rock) the copy's code is appended, so the link says which folder it is. The `href` is a real `?code=<code>` link, so open-in-new-tab works and section 05's `SHEET_OF_CODE` puts it on the right sheet; a plain click is intercepted and calls `openGraph` without a navigation. `openGraph` keeps its recorded opener when the graph is already open, so Escape still returns focus to the table row the reader started from rather than to a link that `innerHTML` has since replaced. Placement depends on which of 06 and this section lands first: before 06, the div is the last child of the one `.mhead` element and `flex-wrap` (`app.css:132`) puts it on its own row; after 06, it is the last child of 06's line 1, as 06's header table says, and 06's `openGraph(code, vs = state.compare)` is called with the code alone so `state.compare` is untouched. Nothing here touches the PNG, so no re-render. Rejected: listing the copies in the row's `Release` cell, because it widens a text column that is load-bearing at 390 px and the heading is where the reader is already looking at one chart.

**6. Percentiles count a chart once.** Section 02's `percentile(df, distinct)` already ranks over `drop_duplicates([*distinct, 'Level'])` and joins the value back, treats a row with a null in its identity as its own chart, and falls back to the plain pool when a sheet lacks an identity column. This section only supplies the argument: `page.build()` calls `add_percentiles(sheets, distinct=frames.COPY_KEY)` where `COPY_KEY = ['Type', 'NotesHash']`, so the pool key is exactly the `Copies` key. Both copies of a chart get the same `Pct`; a unique chart's `Pct` no longer depends on how many packs carry its neighbours. Measured: 16 ms, 1,023 Guitar rows change value, `10145439XG` (Through The Fire & Flames) goes from 98 to 97 and `72933816XG` (Beautiful Disaster) from 13 to 12. Rejected: a guard in `page.build()` that drops `distinct` when `NotesHash` is null or absent, because 02's function already handles both (measured on pandas 3.0.5: an all-null `NotesHash` column gives every row the plain rank, and an absent column takes the fall-back path); the rule belongs in one place.

**7. The search box does not change.** `SEARCH_COLS` (`query.js:7`) stays as it is: searching for a pack name already finds the copy in that pack, because it is its own row. `NotesHash` is never searched and never shown unless chosen.

## Data and interfaces

**Cache** (`functions/cache.py` docstring, the level entry):

```python
level_key: {
    'notes':      {'time_ms': ndarray, 'lanes': ndarray uint8},
    'notes_hash': str,   # 12 lowercase hex digits: sha1(stream_bytes(notes))[:12]
},
```

`cache.stream_bytes(notes) -> bytes`: `notes['time_ms'].tobytes() + notes['lanes'].tobytes()` when `'time_ms' in notes`; otherwise `b'hand' + stream_bytes(notes['hand_mask']) + b'kick' + stream_bytes(notes['kick_mask'])`. `cache.notes_hash(notes) -> str` is `hashlib.sha1(stream_bytes(notes)).hexdigest()[:12]`. Present on every level entry of every instrument, drums included. An entry from `entries_by_code` therefore carries `entry['notes_hash']`. A cache built before this section has no key; analyze reads it with `.get` and writes `None`. Section 11 uses `stream_bytes` for its own consumers; `bundle.fingerprint` keeps its two-element form (Design 1).

**xlsx column `NotesHash`**: `analyze.COLUMN_ORDER` gains `'NotesHash'` immediately after `'SongKey'` (column P in a default run, still before the diagnostics). `song_row` gains a keyword `notes_hash=None` and emits `'NotesHash': notes_hash`; the call at `analyze.py:153` passes `inst_entry.get('notes_hash')`, the same way 05 passes `song_key`. `xlsx_format.HIDDEN_COLS = ['SongKey', 'NotesHash']`. Text, never rounded, never scaled. The analyze terminal summary gains one line after the level matrix, `Distinct charts   11,816 of 11,904`: the count of distinct (`Type`, `Level`, `NotesHash`) over rows with a non-null hash across every sheet written, the same key as the page's `Copies`, so the summary and the page agree (an old cache prints `0 of 11,904`). Section 11 must include drums rows when it lands.

**`web/frames.load_frames`**: `pd.read_excel(xlsx_path, sheet_name=None, dtype={'SongKey': str, 'NotesHash': str})`. `read_excel` infers per column, so a sheet whose every hash is all decimal digits comes back as `int64` with leading zeros lost (measured: `'000000000001'` reads as `1`); impossible over 6,610 rows, about 0.4% likely on a one-row sheet such as 04's fixture Keys sheet, and the same hazard applies to 05's `SongKey`. A name in `dtype` that the sheet lacks is ignored (measured, pandas 3.0.5), so the two committed example workbooks still load.

**Page column `Copies`**: appended in `web/frames.py` by `add_copies(df) -> df` (new), called from `page.build()` on every sheet after 05's `load_frames` and before 02's `add_percentiles`:

```python
COPY_KEY = ['Type', 'NotesHash']   # a chart's identity within a level

def add_copies(df):
    if 'NotesHash' not in df.columns:
        return df                      # older spreadsheet: no copies known, no column
    df = df.copy()
    size = df.groupby(COPY_KEY + ['Level'])['Code'].transform('size')   # NaN for rows whose hash is null
    df['Copies'] = size.fillna(1).astype(int)
    return df
```

`groupby` must keep its default `dropna=True`: with `dropna=False` every null-hash row lands in one group and gets `Copies` equal to the number of such rows (pandas 3.0.5, checked). Integer, minimum 1, JSON integer in the row array, `null` never. Position: appended before 02's `add_percentiles` runs, so `Copies` is the column before `Pct` and `Pct` stays last, as 02's `tests/test_percentile.py` asserts; without 02, `Copies` is last. When 03's `with_added` is present it runs before `add_copies`, so the full order is the xlsx columns, `Added`, `Copies`, `Pct`. The manifest's `columns` lists it in that position, as 05 requires.

**Distinct charts for section 02.** `page.build()` becomes:

```python
xlsx_path, sheets = frames.load_frames(header, xlsx_path)
if packs is not None:                                   # section 03
    sheets = frames.with_added(sheets, packs.added_by_code)
sheets = {name: frames.add_copies(df) for name, df in sheets.items()}
frames.add_percentiles(sheets, distinct=frames.COPY_KEY)  # section 02
```

This fixes the page-build column order for every section: the xlsx columns, then `Added` (03), `Copies` (this section), `Pct` (02). Sections 02 and 03 cite this order rather than stating their own.

02's `percentile()` appends `Level` itself, so its pool is `drop_duplicates(['Type', 'NotesHash', 'Level'])`, the same key `add_copies` groups on. The rule (`rank(method='max') * 100 // count`), the `Int64` type, the null-identity handling and the merge-back are 02's; this section changes the argument and nothing else. Measured with 02's function on the newest sheets joined to the cache's hashes: no `NaN` in `Pct`, the Expert Guitar pool is 1,834, every pair shares one value.

**Labels** (`functions/labels.py`; straight apostrophes, the file has no curly ones):

| Table | Entry |
|---|---|
| `COLUMN_LABELS` | `'Copies': 'Copies'`, `'NotesHash': 'Notes hash'` |
| `COLUMN_HELP` | `'Copies': 'How many charts on this sheet have exactly these notes at this level and part, this one included. 1 is unique; 2 means the same chart is in another folder, usually another pack.'`; `'NotesHash': 'Fingerprint of the notes. Two charts with the same hash play identically, whatever they are called.'` |
| `COLUMN_HELP['Pct']` (02's string) | gains `' Each distinct chart counts once, however many packs carry it.'` after `'officials and customs together.'` |
| `EXPLAINER`, the "Reading the tiers" sentence 02 added | gains `', counting a chart once however many packs carry it'` before its full stop |
| `DISPLAY_ORDER` | `'Copies'` after `'Release'`, and after 08's and 03's columns when present. The composed order, fixed here because this section lands last of the three, is `Release`, `Album`, `Year`, `Genre`, `Added`, `Copies` (the pack, its discography line, when it came, how many folders carry the chart); 03 and 08 cite it; `'NotesHash'` last, after 05's `'SongKey'` |
| `DEFAULT_HIDDEN` | gains `'Copies'` and `'NotesHash'` |
| `PREFS_VERSION` | one more than its value when this lands (2 if 05 is the only bump before it) |
| `UI` | `'copies_label': 'Same chart in:'`, `'copies_tip': 'The same notes in another folder. Opens that copy’s graph.'` |

`Copies` is not in `SEARCH_COLS`, not in `TIME_COLUMNS`, not in `MISSING_VALUES`; `NotesHash` likewise. Neither is in `VALUE_ORDER`: `Copies` sorts numerically on its own.

**Graph heading** (`web/static/js/overlay.js`): a new `copies(code, row)` returns the other rows of `rowsAll()` with equal `Type`, `Level` and `NotesHash` and a different `Code`, or `[]` when the sheet has no `NotesHash` column; a new `copyText(row)` returns `esc(release) + ' (' + esc(VALUE_LABELS.Official[String(official)]) + ')'`, with `release` replaced by the row's `Charter` when it is exactly `"Custom"` and by the code when that is empty. `heading()` places the div inside the `.mhead` element (06's line 1 after 06), after the report link and before the closing tag, only when the list is non-empty:

```html
<div class="copies"><span class="text-secondary">Same chart in:</span>
  <a href="?code=26376451EG" data-code="26376451EG" title="The same notes in another folder. Opens that copy’s graph.">Guitar Hero (Official)</a>
</div>
```

The label is `esc(UI.copies_label)` (the colon lives in the string). A copy whose `copyText` equals the open chart's own gets `' ' + esc(code)` appended. Two or more copies are separated by `'<span class="sep">/</span>'`, the existing rule at `app.css:37` that `overlay.js:90` already uses. Every value passes through `esc()`; the attribute is double-quoted as `markup.js` requires. `openGraph(code)` sets `opener` only when `!graphIsOpen()`. `router.onClick` gains, immediately before the modal-close branch (`router.js:56` today; 06's `e.target === el("modal")` test after 06):

```js
const alt = e.target.closest("#modal .mhead a[data-code]");
if (alt) { e.preventDefault(); openGraph(alt.dataset.code); return; }
```

CSS (`web/static/css/app.css`, beside `.mhead .rpt` at `:129`): `.mhead .copies { flex-basis:100%; font-size:11px; }` and `.mhead .copies a { color:var(--fw-accent-text); }`, the text colour CLAUDE.md reserves for accent-coloured text (5.2:1 or better).

**URL parameters**: none added. `?f.Copies=2` is the shareable "every duplicated chart" view and needs no code.

**Section 02 must add:** its Design 8 names "section 10's `KEY` (`['Type', 'Level', 'NotesHash']`)"; the name is `COPY_KEY = ['Type', 'NotesHash']` and `add_copies` groups on `COPY_KEY + ['Level']`. Its `distinct=['Type', 'NotesHash']` sentences are already right. The `COLUMN_HELP['Pct']` and `EXPLAINER` additions above are this section's, as 02 says.

**Section 05 must add:** its boot-payload `columns` example, once every section has landed, ends `..., "SongKey", "NotesHash", "Added", "Copies", "Pct"`. Nothing new in shape otherwise: this section relies on 05's `HIDDEN_COLS`, `PREFS_VERSION`, the manifest `columns` list, `rowsAll()` returning the loaded sheet, and `SHEET_OF_CODE` for the `?code=` href. 05's text already names `Copies` as a page-build column; keep that sentence.

**Section 03 must add:** its `DISPLAY_ORDER` line cites the composed order above; strike "A `Pack` name column" from its Out of scope line that defers it here (this section adds none; see Out of scope).

**Section 04 must add** (fixture delta, `tests/fixture.SONGS`, every name invented as 04 requires): a song `B5 - Grid Runner (Live)` in `Fixture Pack B` (Rock Band 2 / Official), G:X only, whose `notes.chart` carries A1's `[Song]` (Name changed), `[SyncTrack]`, `[Events]` and `ExpertSingle` sections byte for byte and no bass section, so its Expert guitar hashes equal to `A1 - Grid Runner`'s while the title differs and the `SongKey` does not fire (A1 has B:X too); C4's `RhythmSingle` a byte copy of its `ExpertSingle` (Lead = Rhythm, same level); a per-song `stride` field with A2's set to 1 so its `HardSingle` equals its `ExpertSingle` (Hard = Expert). Stated as deltas against 04's fixture table, since 11 may have landed first: +1 `song.ini`, +1 cached song, +1 code, +1 Guitar row, +1 Official row, +1 on the landing view (the absolute pins follow from the table in `tests/test_fixture.py`), and the D invariant becomes "Guitar `D` has 33 distinct values over 36 rows" (still above `RANGE_MIN_DISTINCT`). Section 06, if it lands second: fold the copies line into line 1 of its header table.

## Files touched

- `functions/cache.py`: docstring gains `notes_hash`; `stream_bytes(notes)`, `notes_hash(notes)`.
- `build.py`: sets `level_stream['notes_hash']` before storing at `:94`.
- `analyze.py`: `COLUMN_ORDER` gains `NotesHash`; `song_row` takes `notes_hash`; the call site passes it; the summary prints distinct charts.
- `functions/xlsx_format.py`: `HIDDEN_COLS` gains `NotesHash`.
- `web/frames.py`: `COPY_KEY`, `add_copies()`; `load_frames` passes `dtype` for the two hash columns.
- `web/page.py`: `build()` applies `add_copies` to every sheet, then calls `add_percentiles(sheets, distinct=frames.COPY_KEY)`.
- `functions/labels.py`: the label, help, order, hidden, `PREFS_VERSION`, two `UI` entries, the `Pct` help sentence and the `EXPLAINER` clause above.
- `web/static/js/overlay.js`: `copies()`, `copyText()`, the heading line, the opener guard.
- `web/static/js/router.js`: the `[data-code]` anchor branch.
- `web/static/css/app.css`: two `.mhead .copies` rules.
- `tests/fixture.py`, `tests/test_fixture.py`, `tests/pipeline_test.py` (04's files): the fixture delta and the assertions under Verification; `tests/test_copies.py` (new).
- `README.md` section 3 (the spreadsheet's columns, `:95-104`) and section 5 (the browser, `:160-175`); `CLAUDE.md` "The cache is the data contract" (`:189-195`) and the `labels.py` paragraph (`:212-216`).
- `Methodology.md`: unchanged; the hash is identity, not scoring.
- `web/bundle.py`: unchanged (Design 1).

## Steps

1. **Hash in build.** `cache.stream_bytes`, `cache.notes_hash`, the docstring, `build.py:94`. Rebuild: `python build.py --search-path songs --header Local`. Check: the terminal summary matches the previous run's counts (1,758 songs, 15,660 codes, no errors CSV); a one-liner over the new cache reports 11,904 five-fret entries with a 12-hex `notes_hash`, 11,714 distinct, and 3,756 drums entries each with a 12-hex hash over the `hand`/`kick` layout; `bundle.fingerprint` on any entry from the new cache equals its value from the previous cache for the same code (nothing re-renders). Commit: `cache a 12-hex hash of every chart's notes at build time`.
2. **`NotesHash` in the spreadsheet.** `COLUMN_ORDER`, `song_row`, the call site, `HIDDEN_COLS`, the summary line, the `dtype` in `load_frames`. `python analyze.py --header Local`. Check: the xlsx has a hidden `NotesHash` column after `SongKey`, 11,714 distinct values over 11,904 rows, 0 blanks; `Distinct charts   11,816 of 11,904` printed; the Guitar sheet's `A1:P6611` dimension (one column more than 05's run); `load_frames` returns a string column on every sheet. Commit: `analyze: write NotesHash beside SongKey, hidden in the spreadsheet`.
3. **`Copies` on the page.** `frames.add_copies`, `page.build`, labels, `DEFAULT_HIDDEN`, `PREFS_VERSION`. `python serve.py --header Local`. Check: the chooser lists "Copies" and "Notes hash" unchecked on a fresh profile and on a profile with a stale `fw.hidden` (the version bump); ticking "Copies" shows a 0-decimal column whose filter is a two-item checkbox list, 1 and 2; `?f.Copies=2&f.Level=Expert&f.Official=true` on Guitar shows 38 rows (the 19 Expert pairs) and its adjacent rows share `D`; `?f.Copies=2` with no level filter shows 152 on Guitar and 24 on Bass; an older xlsx without `NotesHash` (the local `metrics/Local_metrics_09072026-2031.xlsx`, or the committed `metrics/MainEMHX5f_metrics_09062026-0936.xlsx` via `--xlsx`) loads with no `Copies` column and no console error. Commit: `Copies: how many charts share these notes at this level and part`.
4. **Copies in the graph heading.** `overlay.copies`, `copyText`, the heading line, the opener guard, the router branch, the CSS. Check on `serve.py`: opening `26376451XG` (StarPower 2 Combos, Guitar Hero) shows `Same chart in: Guitar Hero Encore: Rocks The 80s (Official)`; clicking it swaps the graph to `84387440XG`, the URL's `code` follows, the heading now names Guitar Hero, and Escape returns focus to the original table row; a Metallica DLC pair (`92154429XB` Suicide And Redemption J.H. against `63885037XB` K.H., Bass sheet) shows the copy's code after `Guitar Hero: Metallica DLC (Official)`; a unique chart shows no line; middle-click opens `?code=84387440XG` in a new tab on the Guitar sheet with a filled heading. Commit: `graph heading lists the other folders the same chart is in`.
5. **Percentile over distinct charts.** Pass `distinct=frames.COPY_KEY` at the call site in `page.build()`; the `Pct` help sentence and the `EXPLAINER` clause. Check, read-only, with the venv, `s` being the sheets after `build()`: `g = s['Guitar'].query("Level == 'Expert'")`; `g.drop_duplicates(frames.COPY_KEY)['Pct'].size == 1834`; `g.loc[g.Code == '85221549XG', 'Pct'].item() == g.loc[g.Code == '63446491XG', 'Pct'].item() == 85` (Bark At The Moon, Guitar Hero against GH II DLC); `g.loc[g.Code == '10145439XG', 'Pct'].item() == 97` (was 98) and `g.loc[g.Code == '72933816XG', 'Pct'].item() == 12` (was 13); `g['Pct'].max() == 100`; no `null` in `Pct`; the synthetic frame from 02 with `Key` renamed to `NotesHash` gives `[66, 66, 100, 33, 50, 100, <NA>]`; an xlsx whose `NotesHash` is blank throughout gives the same `Pct` as before this section. On serve: `?code=85221549XG` and `?code=63446491XG` both read "At or above 85% of Expert Guitar charts". Commit: `percentiles count a chart once however many packs carry it`.
6. **Fixture and tests.** The 04 fixture delta, the new pins, `tests/test_copies.py`, the `pipeline_test.py` assertions. Check: `python -m unittest discover -s tests -t .` and `python tests/pipeline_test.py --bootstrap-css caches/bootstrap-5.3.8.min.css` pass. Commit: `tests: a planted cross-pack pair, Hard = Expert and Lead = Rhythm in the fixture`.
7. **Docs.** README sections 3 and 5, the two CLAUDE.md paragraphs. Commit: `docs: NotesHash in the cache and spreadsheet, Copies on the page`.
8. **Publish and deploy.** `python publish.py --header Local`: the banner reports 0 graphs rendered (the fingerprint is unchanged) and only the data JSON, bundle and `index.html` rewritten. `python deploy.py --dry-run`, then `python deploy.py` through section 01's checklist; tag `fretladder-v<next>`.

## Verification

- After step 1, read-only, with the venv: load the newest cache, assert every non-drums level entry has `notes_hash` matching `hashlib.sha1(time_ms.tobytes() + lanes.tobytes()).hexdigest()[:12]`, every drums entry matches the `hand`/`kick` layout, 11,714 distinct five-fret hashes, and grouping by (instrument, level, hash) across songs yields 88 groups of size 2 covering 176 charts.
- After step 2, `frames.load_frames('Local')`: `NotesHash` present on every sheet, `pd.api.types.is_string_dtype(df['NotesHash'])` and `df['NotesHash'].str.fullmatch('[0-9a-f]{12}').all()` on every sheet (pandas 3.0.5 reads text as dtype `str`, so do not assert `object`), `nunique()` summing to 11,714, and `openpyxl` reports `column_dimensions['P'].hidden is True` on Guitar.
- After step 3, on the published `data/guitar.<hash8>.json`: `columns[-2] == 'Copies'` and `columns[-1] == 'Pct'` (without 02, `columns[-1] == 'Copies'`), every `Copies` value an integer 1 or 2, 152 rows at 2, and the Guitar JSON is 05's 1,004,739 + 02's 18,974 (`Pct`) + 112,391 = about 1,136,000 bytes raw, within 2 KB of that.
- 390 px re-measure (section 04's `frame.html`): the first-visit column set is unchanged, so `D` stays on screen where it was (last measured 262 to 358 px). With `Copies` shown it is a two-character numeric column after Source and must not push `D` off screen; and with the graph open on a duplicated chart, `.mcard` must not exceed the viewport width (the copies line wraps, `flex-basis:100%`, and its links are `white-space:normal`).
- Section 04 suites: `launch.js` gains "Copies and Notes hash are unchecked in the chooser on first visit" and "`?f.Copies=2` shows only rows whose `Copies` cell reads 2"; `roundtrip.js` gains the `fw.v` bump case for this section's `PREFS_VERSION`; `keys.js` (the dialog suite) gains "a synthetic click on the copies link inside the modal opens the other copy without closing the modal, the URL `code` changes, and Escape restores focus to the row", and, if 06 has landed, "Tab from the modal reaches the copies link and Enter on it swaps the graph". `tests/pipeline_test.py`'s analyze stage asserts `NotesHash` is hidden in the fixture xlsx and reads back as a string column even though the Keys sheet has one row; its publish stage asserts on the published Guitar JSON that the B5/A1 pair has `Copies == 2` on both rows and equal `Pct`, that A2 and C4 have `Copies == 1` on every row, and that the manifest lists `Copies` immediately before `Pct`. A new `tests/test_copies.py` asserts `add_copies` on a synthetic frame (a pair, a Hard = Expert song, a Lead = Rhythm song, a null-hash row), that a frame without `NotesHash` passes through unchanged, and that `add_percentiles(sheets, distinct=COPY_KEY)` over an all-null `NotesHash` equals the plain rank. `copyText`'s equal-text case is the Metallica DLC check in step 4; its `Custom` fallback has no live case (see Out of scope).
- `python publish.py --header Local` twice: the second run rewrites nothing and renders nothing.

## Risks and gotchas

- The hash is over float64 milliseconds, so it is exactly as stable as `parsers/timing.py`: a tick-to-ms change alters every hash and every pair still matches afterwards, because both copies move together. Never persist hashes across builds (section 05 says the same of `SongKey`); `Copies` is recomputed from the xlsx at every page build and stores nothing.
- `bundle.fingerprint` must keep `time_ms.tobytes()` and `lanes.tobytes()` as two tuple elements. Routing it through `stream_bytes` changes every fingerprint and re-renders every PNG; section 11 keeps the two-element form for the same reason.
- `Copies` counts within one sheet and one row set. With `XLSX_LEVELS = 'X'` only Expert copies are counted, which is correct for the rows shown. With `EXTRA_METRICS` the count is unchanged.
- A cache from before step 1 analysed with the new analyze writes a blank `NotesHash`; `add_copies` then gives every row `Copies = 1`, the heading shows no line, and `Pct` falls back to the row-wise rank because 02's function treats each null-identity row as its own chart. Correct, and silent: the analyze summary's `Distinct charts   0 of 11,904` is the tell for all three.
- `groupby(COPY_KEY + ['Level'])` with the default `dropna=True` is load-bearing (see Data and interfaces). Do not "fix" the `fillna(1)` by passing `dropna=False`. `drop_duplicates` and `merge` do the opposite (NaN matches NaN, measured on pandas 3.0.5), which is why 02's function separates null-identity rows before deduplicating; do not simplify it.
- The copies line reads `rowsAll()`, which under 05 is the loaded sheet. The row that opened the graph is by construction in that sheet, and so are its copies (same instrument, same `SHEET_GROUPS` entry), so there is no cross-sheet search and no race with the idle prefetch.
- Before 06, `router.js:56` exempts `.mhead a` from closing the modal, which is why the report link works; the new branch must come before that line and call `preventDefault()`, or the browser follows the `href` and reloads the page. After 06 the exemption is gone (backdrop-only close) and the branch must still come before 06's test, for the same reason. The div must be inside the `.mhead` element: appended after it, a click on the link closes the modal.
- The links are pointer-only until 06 lands: `router.js:94` swallows Tab inside the modal, as it does for the report link today. Keyboard reach is 06's `trapTab`, not this section.
- `openGraph` replaces `.mcard`'s `innerHTML`, which removes the link that was clicked. Recording it as the opener would make `closeGraph` find `opener.isConnected === false` and drop focus to `body`; the guard keeps the original row. 06's `openGraph` still rebuilds the card, so the guard stays under 06.
- The leaderboards userscript (a prototype outside the repo) hooks `#modal .mhead`, reads the code from the modal's `aria-label` with `/:\s*([0-9A-Z]+)\s*$/` and watches that attribute with a `MutationObserver`; the copies line is a child of `.mhead`, the label still ends with the code and `openGraph` rewrites it on every swap, so it should follow; it is not checked here (section 13 owns the userscript's fate as a follow-up).
- `esc()` (`dom.js:5-6`) does not escape `>` or `'`; the copies markup uses double-quoted attributes only, like the rest of `markup.js`.
- `Copies` joins `DEFAULT_HIDDEN`, so `PREFS_VERSION` must move or returning visitors see two new columns. If this section lands in the same release as 05, one bump covers both; if later, a second.
- The committed example spreadsheets under `metrics/` gain no `NotesHash`; do not regenerate them for this section. The page treats the missing column as "no copies known" and 02's function keeps ranking rows.
- The percentile change alters `Pct` for 1,023 of 6,610 Guitar rows, by a point or two. Ship 02 and this section in the same release if possible so the number changes once.
- Drums entries get a hash but analyze still skips them (`analyze.py:126`); section 11 inherits `NotesHash` for free and must include drums in the distinct-charts summary line when it lands.

## Out of scope and follow-ups

- Merging copies into one row, a "canonical copy" rule, or hiding the custom copy of an official chart: decided against in Design 4; revisit only if the production library shows hundreds of pairs rather than tens.
- A `Pack` column naming the `packs.toml` entry a folder belongs to: not here, and not in 03 (which rejects it in its Design 5). The heading names `Release`, the source label from `sources/`, with `Charter` as the fallback in Design 5.
- A per-song view over `SongKey` and the "other levels and parts of this song" list: section 07. The 21 same-song cross-instrument matches and the 58 Hard = Expert (song, instrument) pairs (63 groups keyed by (song, instrument, hash), counting the all-four-equal songs once) belong to that view as a note ("Hard is identical to Expert"), not to `Copies`; 07 lists this as an optional follow-up reading `NotesHash` by column name.
- The strapline's "11,904 charts" counts rows. Leaving it: it is the number of rows the reader can open. If it should read distinct charts, that is one `drop_duplicates` in `page.public_source` and a wording decision for section 01.
- Cross-format duplicates (the same chart as `.chart` in one pack and `.mid` in another) are not detected when the conversion moves a timestamp by a fraction of a millisecond. Measured: no pair in the Local library crosses formats, so there is no evidence either way. Optional follow-up: if a production pack pair is known to be the same chart in both formats, compare their `time_ms` arrays; if they differ only below 0.1 ms, hash `np.round(time_ms, 1)` instead and re-measure the 88.
- Optional follow-up: the `Custom`-release fallback in Design 5 (`Charter` in place of the literal `Custom`) has no pair to show it on, in the Local library or in 04's fixture, whose only pair is official against official. A custom pack re-hosting an official chart in `songs/`, or a fixture custom pair, would give it a check; until then it is read-only code with no observed case.
- Optional follow-up: near-duplicates (a re-chart with a handful of changed notes) need a similarity measure, not a hash, and a use case; none is known.

## Open questions

None.
