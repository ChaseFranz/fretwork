# 08. Genre, Year and Album

**Status:** Ready after 00

**Effort:** S, dominated by the build and analyze runs against `songs/` and the browser checks, not by the code, which is under a hundred lines across thirteen files. The one full re-render of every graph is section 00's, not this section's; this section is designed so it renders nothing.

**Depends on:** 00 (its step 6 pays the full re-render and writes the `09102026-2324` pair this section measures against; `check_pair` must refuse a mismatched cache and xlsx before the rebuild here; `page.fill` must stop tripping on data before album titles enter the boot JSON). Section 05 is not a dependency: whichever of 05 and 08 lands second carries the one `labels.PREFS_VERSION` bump (see Design item 3). Section 04 is not a dependency either, but if it has landed, the files under `tests/` listed in Files touched are edited in the same steps.

## Goal

Read `genre`, `year` and `album` out of every `song.ini`, carry them through the cache and the spreadsheet, and put them on the page as three more columns: `Album` and `Genre` as text with checkbox filters, `Year` as a number with a min/max box, Album searchable from the toolbar box, all three hidden until chosen. Do it without re-rendering a single PNG.

## Why

- A viewer who wants "the hardest thrash charts" or "anything from Death Magnetic" has no handle today: the table knows a song's title, artist, charter and pack, and nothing about the record it came from. `song.ini` already carries the answer in every one of the 1,758 files in `songs/` (`genre`, `year` and `album` are each present in 100% of them, the same coverage as `name` and `artist`); `parse_ini` already reads them (`parsers/ini_parser.py:77-87`) and `ini_parse` throws them away (`:96-106`).
- Year is the one axis the site has no way to express at all. Every other question a visitor asks can be approximated with search; "charts from the 1980s" cannot.
- The cost is one rebuild. The trap is that `bundle.fingerprint` hashes the whole `meta` dict (`web/bundle.py:76`), so three new keys would re-render all 11,904 graphs at 0.12 s each on the next publish, for headers that print none of the new values. That fingerprint is narrowed first, and the narrowing is byte-identical on today's caches, so the publish after the rebuild renders nothing.

## Current state

**Parsing.** `parse_ini` (`parsers/ini_parser.py:77-87`) keeps every `key = value` line, keys lower-cased, last duplicate wins. `ini_parse` (`:90-127`) then selects `name`, `artist`, `charter` (each through `DETAG`, `:56`, which strips `<...>` markup such as `Harm<color=#0072bc>o</color>nix`), `icon`, and the six `diff_*` tags, and returns exactly `SongPath, Name, Artist, Charter, Difficulty, Release, Official` (`:119-127`). `build.META_KEYS` (`build.py:27`) is `('Name', 'Artist', 'Charter', 'Release', 'Official')`, and `build.py:106` copies those plus `Difficulty` into the song's `meta`. Nothing else from the ini survives; the newest cache (`caches/Local_cache_09102026-2324.pkl`) has exactly those six meta keys per song, 1,758 songs and 15,660 codes.

**Spreadsheet.** `analyze.song_row` (`analyze.py:45-71`) copies a hand-picked slice of `meta` into `row_meta` (`:53-62`), `COLUMN_ORDER` (`:37-42`) fixes the xlsx column order, `Difficulty` is coerced to int with `-1` for missing at `:202`, and `xlsx_format.style_sheet` widths every column to `min(max(longest + 2, 6), 40)` (`functions/xlsx_format.py:163-166`). The xlsx is named from the cache's filename timestamp (`analyze.py:174-175`, through `timestamp.ext_ts`, which raises unless the cache name starts with `{header}_cache_`); `analyze()` accepts `out_dir` (`:95`) but the CLI has no `--out-dir` flag (`:235-242`).

**Pair on disk.** The newest cache is `Local_cache_09102026-2324.pkl`; the newest spreadsheet is `Local_metrics_09072026-2031.xlsx`; no `Local_metrics_09102026-2324.xlsx` exists yet. Section 00 step 6 creates it (`python analyze.py --header Local`) and publishes from it. Until that has happened there is no matched pair and section 00's `check_pair` refuses to publish.

**Page.** `web/frames.frames_payload` (`web/frames.py:31-38`) emits whatever columns the xlsx has; there is no allow-list. `state.ordered()` (`web/static/js/state.js:76-82`) places a column the display order does not name after every ordered column, and `format.lab()` falls back to the raw key, so a new xlsx column appears on the far right with no JS change. `query.isNumeric()` (`query.js:9-13`) decides number-or-text by inspecting values; `useRange()` (`:36-37`) gives a numeric column a min/max box once it has more than `RANGE_MIN_DISTINCT = 25` distinct values, else a checkbox list, which grows a search box above 12 values (`dropdown_view.js:46`). `SEARCH_COLS` (`query.js:7`) is a hardcoded five: Song Title, Artist, Charter, Release, Code. `TEXT_CLASS` (`markup.js:40-45`) names the four wrapping columns; `bodyCell` prints a `TEXT_CLASS` column as `esc(v ?? "")` (`:63-65`, an empty cell for `null`) and every other column's `null` as the dash through `isMissing` (`:66-70`); every non-`title` cell is `white-space:nowrap` (`app.css:68`). `loadHidden()` (`state.js:11-16`) uses `HIDDEN_DEFAULT` only when no `fw.hidden` key is stored. `boot_json` (`web/boot.py:35`) serialises the island with `json.dumps` defaults (`", "` and `": "` separators, `ensure_ascii=True`).

**Two sentinel warts that Year would make visible.** The range branch of `matchesFilter` (`query.js:51`) accepts any number, so a hi-only filter such as `r.Difficulty=:3` includes the `-1` rows. `rangeBody` (`dropdown_view.js:17-19`) takes min and max over every number, sentinel included, and prints them with `toFixed(2)`, so a Year box would read `min -1.00`.

**Graph fingerprint.** `bundle.fingerprint` (`web/bundle.py:69-81`) hashes, among other things, `repr(sorted(entry['meta'].items()))` (`:76`). What the PNG actually prints from `meta` is `Name` and `Artist` in the title (`functions/plot.py:167-168`), `Charter` (`:79`), `Release` and `Official` through `release_label` (`:65-70`, `:80`), and `Difficulty[instrument]` (`:88`). `output_filename` (`:41`) uses `Artist` and `Name` too. Measured with `.venv/bin/python` on every 40th code of `site/Local/graph/manifest.json` (298 codes) against both the 09072026-2031 and the 09102026-2324 caches: a fingerprint over only those six keys equals the current fingerprint for 298 of 298; a fingerprint costs 0.2 ms. Also measured: the current fingerprint matches the live manifest for 0 of 298, because commit 69b5a8f removed `spans` from the tuple after the manifest was written (2026-09-10 23:03). `_save_manifest` (`:91-93`) writes with `sort_keys=True`, so a byte-identical manifest is an observable check. `functions/plot.py` imports matplotlib at module level (`:14-17`); `web/graph.py:48-49` imports it inside `render` for that reason, and nothing on `serve.py`'s startup path imports `web/bundle.py`.

**The values, measured read-only over `songs/` with `parse_ini`:**

| Key | Present | Distinct | Notes |
|---|---|---|---|
| `year` | 1,758 | 64 years, 1962 to 2026 | 1,755 are exactly four digits; `2007 (re-issue)` once; `Unknown Year` twice |
| `genre` | 1,758 | 212 | none empty, none carry markup, longest 23 chars; Rock 246, Hard Rock 142, Alternative Rock 95, Alternative 94, Metal 75, Classic Rock 75 |
| `album` | 1,758 | 1,261 | one empty, none carry markup, longest 87 chars, 95th percentile 35; 24 distinct titles (42 songs) contain a comma; Death Magnetic 22 songs |

Joined to the rows of `metrics/Local_metrics_09072026-2031.xlsx` (11,904 rows) and serialised the way section 05 serialises a sheet (`separators=(',', ':')`, UTF-8): Guitar 905,579 bytes becomes 1,147,462 (+26.7%; gzipped about 225 KB to about 306 KB), Bass 665,622 to 845,150 (+27.0%; about 159 KB to about 217 KB), Keys 31,132 to 40,347 (about 6 KB to about 8 KB). The gzip figures are Python's `gzip` at its default level; section 05 quotes 230,099 for the same Guitar baseline under a different setting, so compare deltas (about +80 KB gzipped on Guitar), not absolutes. In the `#fw-boot` island, which uses `json.dumps` defaults, the three sheets add about 465 KB to `index.html` (the compact 430,626 plus one space per new cell). An unstyled xlsx of the same frames grows from 1,052,832 to 1,350,249 bytes (+28.1%). Rows whose Year is the sentinel: Guitar 5, Bass 4, Keys 0. Distinct Year values per sheet including the sentinel: 65, 64, 34, all above the range threshold of 25. Distinct Album on Guitar: 1,260; distinct Song Title on Guitar: 1,602. Smallest NoteCount: 2 on Guitar and Bass, 24 on Keys.

## Design

**1. Selection at `ini_parse`, not a new reader.** `ini_parse` gains three entries: `Genre` and `Album` through `DETAG` like Name, Artist and Charter, and `Year` through a `_year()` helper that returns an int or `-1`. `build.META_KEYS` gains the three names, and `build.py:106` copies them unchanged. Rejected: reading the ini again in analyze (the cache is the data contract; analyze must run from a cache alone); a separate metadata table in the cache (three scalars per song do not justify a second shape).

**2. Year is an int with the `-1` sentinel.** `_year()` takes the first run of exactly four digits anywhere in the value, first digit 1 to 9, not touching another digit on either side (`(?<!\d)([1-9]\d{3})(?!\d)` with `re.search`), so `2007 (re-issue)` gives 2007, `Vol. 2 (2001)` gives 2001, `1999-2000` gives 1999, and `Unknown Year`, `199`, `19999` and `0999` give `-1`. On `songs/` that is 1,756 parsed and 2 sentinels, the same counts a leading-run rule gives, because all 1,755 four-digit values and `2007 (re-issue)` match either way; the anywhere rule is what `COLUMN_HELP['Year']` promises ("no four-digit year"). The sentinel goes through `labels.MISSING_VALUES`, the same channel as `Difficulty`, so the page prints the dash, sorts it last in both directions and, after the fix in item 8, keeps it out of every range. Rejected: Year as text (sorts `2007 (re-issue)` beside `2007` as a different value, gets a 65-entry checkbox list instead of a min/max box, and `1990 < 2010` stops being a number comparison); `None`/NaN for missing (pandas turns an int column with a NaN into float and every year prints as `1998.0` in Excel; `-1` is already the convention the reader knows); a strict four-digit fullmatch (drops `2007 (re-issue)` for nothing); a leading-run rule with `re.match` (drops `Vol. 2 (2001)` and contradicts the help text).

**3. Hidden on the page by default, visible in the spreadsheet.** The page's first-visit view is already ten columns and at 390 px `D` sits at x 262 to 358 with nothing to spare (section 04's `frame.html`). Album wraps and would cost a line height per row. All three therefore join `DEFAULT_HIDDEN`; search still reads Album and a filter set on any of them still applies, because hiding is display-only (CLAUDE.md, `functions/labels.py:189-198`). A changed default only reaches a visitor with a stored `fw.hidden` through section 05's preference version, and the rule is that whichever of 05 and 08 lands second carries the one bump: if 05 has landed, this section sets `PREFS_VERSION = 2` and every stored hidden set is reset once; if 05 lands after this section, its own `PREFS_VERSION = 1` migration re-applies this `DEFAULT_HIDDEN` and nothing further is owed here. Until one of those happens, only visitors who have touched the chooser see the three columns, until they press Reset columns. The xlsx shows them: Excel has no width problem, the autofilter handles them, and `DEFAULT_HIDDEN_COLS` (`xlsx_format.py:34-36`) is the wrong tool because analyze deletes those columns outright unless `EXTRA_METRICS` is on (`analyze.py:178-180`). Rejected: shown by default on the page (the reasons above); hidden in Excel (nobody asked, and `-1` years would be invisible to the person checking the build).

**4. Column order Album, Year, Genre, after Release, in both the xlsx and the page** (the composed page order once 03 and 10 have landed is fixed in section 10: `Release`, `Album`, `Year`, `Genre`, `Added`, `Copies`). They read as a discography line, and Genre, the coarsest attribute, sits last. In the xlsx they are columns H, I, J, between `Release` and `Official`; `FREEZE_AT = "D2"` (`xlsx_format.py:53`) still freezes Code, Song Title and Artist. On the page they go after `Release` in `DISPLAY_ORDER`, so `D` stays third and nothing left of it moves. Rejected: after Artist (would push `D` right, which the display order exists to prevent); the xlsx order left as-is with a page-only order (one order is easier to explain in README).

**5. The fingerprint reads only what the header prints.** `functions/difficulty.py` (the fork's file, already the home of the difficulty block the same fingerprint hashes) gains `HEADER_META_KEYS = ('Name', 'Artist', 'Charter', 'Release', 'Official', 'Difficulty')`; `bundle.fingerprint` hashes `repr(sorted((k, v) for k, v in entry['meta'].items() if k in difficulty.HEADER_META_KEYS))` and imports nothing from matplotlib. `functions/plot.py` is upstream's and byte-identical to `upstream/main` (sections 06 and 11 rely on that), so the tuple cannot sit beside `meta_header`; what keeps it honest instead is a test in the style 06 uses for plot literals: `tests/test_fingerprint.py` asserts that each key in the tuple appears in the source of `plot.meta_header`, the title row or `plot.output_filename`, and that no other `meta` key does. On today's caches the six keys are the whole dict, so the string is byte-identical and no fingerprint moves; after the rebuild, Genre, Year and Album are outside it and no fingerprint moves either. Rejected: putting the tuple in `functions/plot.py` beside `meta_header` (upstream's file; a fork edit there is a merge conflict on every upstream pull, and CLAUDE.md routes shared-tooling changes upstream as a PR, which this is not); hashing only `Difficulty[instrument]` rather than the whole dict (tighter, but changes every fingerprint today and buys a re-render only when someone edits another instrument's `diff_*`, which happens never); leaving meta out entirely (a retitled song would keep a stale header on its PNG).

**6. Search covers Album; Genre and Year do not.** `SEARCH_COLS` becomes Song Title, Artist, Album, Charter, Release, Code, and `UI['search']` says so. Genre is not searched: by the counts above, `rock` typed into the box would match at least 558 of 1,758 songs (32%) through the Genre column alone (Rock, Hard Rock, Alternative Rock, Classic Rock), and `metal`, `pop` and `punk` behave the same, so the box would stop meaning "songs and people called this"; the leaderboards userscript's deep links are `/?q=<title>&code=<code>` (`../fretladder-leaderboards.user.js:183`), so a song titled `Rock` would flood the table under its own graph. The Genre filter's 212-value checkbox list already has its own search box (`dropdown_view.js:46`), which is the right tool. Year stays out of search too: `1999` typed into the box should not silently mean a year, and the range box is the right tool. Rejected: a per-column search syntax (nothing else on the page has one).

**7. Album wraps, Genre does not; both print an absent value as an empty cell.** `TEXT_CLASS` gains `Album` with the classes `title album` and `Genre` with the class `genre`; `app.css` caps `td.album` at 220 px, and at 100 px inside the 640 px media query, the same caps as Artist; nothing styles `td.genre`, so it stays a nowrap cell (Genre's longest value is 23 characters). Both empty values reach the xlsx as an empty cell, come back from `read_excel` as NaN and land in the row JSON as `null`; the `TEXT_CLASS` branch of `bodyCell` prints `null` as an empty cell, the same way an absent Charter or Release would print, and the checkbox filter lists it as the dash through `key(null)`. Rejected: leaving Genre out of `TEXT_CLASS` (its `null` would then fall through to the `isMissing` branch and print a right-aligned dash while an empty Album printed nothing, two conventions for one kind of gap); `'unk'` as a default the way Name, Artist and Charter do it (it would become a searchable, filterable value); wrapping Genre too (nothing to wrap); no cap on Album (an 87-character album would widen the table on a phone).

**8. Two page fixes that Year makes necessary.** The range branch of `matchesFilter` rejects a sentinel (`isMissing(col, v)`), so `r.Year=:1989` no longer includes unknown years, and `r.Difficulty=:3` stops including unrated rows, which was the same bug. `rangeBody` computes its placeholders over non-missing numbers and prints them with `decimals(col)`, so the Year box reads `min 1962` and `max 2026`; NoteCount's box changes from `min 2.00` to `min 2` at the same time. Rejected: leaving the sentinel in the range and documenting it (a "before 1990" filter that lists songs of unknown year is wrong to any reader).

**9. `song_length` is deliberately not read.** `DurationS` already exists and is what the metrics use: the time from t=0 to the last note of that chart (`labels.COLUMN_HELP['DurationS']`). `song_length` is the audio length in milliseconds as the charter typed it (1,739 of 1,758 inis carry it), which includes the intro and the outro and is sometimes wrong. A second length column would only invite the question which one is right.

## Data and interfaces

**`ini_parse` return dict** (`parsers/ini_parser.py`) gains, after `Charter`:

```python
'Genre':  DETAG.sub('', ini.get('genre', '')).strip(),    # str, '' when absent
'Year':   _year(ini.get('year', '')),                       # int, -1 when no four-digit year
'Album':  DETAG.sub('', ini.get('album', '')).strip(),    # str, '' when absent
```

```python
# the first run of exactly four digits anywhere in the value, first digit 1-9:
# '2007 (re-issue)' -> 2007, 'Vol. 2 (2001)' -> 2001, 'Unknown Year' -> -1
YEAR = re.compile(r'(?<!\d)([1-9]\d{3})(?!\d)')

def _year(text):
    match = YEAR.search(str(text))
    return int(match.group(1)) if match else -1
```

**`build.META_KEYS`** = `('Name', 'Artist', 'Charter', 'Release', 'Official', 'Genre', 'Year', 'Album')`. **Cache `meta`** (`functions/cache.py:15` docstring) is therefore `{'Name': str, 'Artist': str, 'Charter': str, 'Release': str, 'Official': bool, 'Genre': str, 'Year': int, 'Album': str, 'Difficulty': {instrument_key: str}}`. `Year` is the second sentinel in the cache after `Difficulty`, and unlike `Difficulty` it is an int in the cache as well as in the xlsx. Caches built before this section lack the three keys; analyze must not fail on them (next paragraph), and `entries_by_code` copies `meta` whole (`functions/cache.py:168`) so nothing else cares.

**`analyze.COLUMN_ORDER`**: insert `'Album', 'Year', 'Genre'` between `'Release'` and `'Official'`; everything else, including section 05's `'SongKey'` after `'CalcTier'` if present, is unchanged. Before 05 the list reads:

```python
COLUMN_ORDER = [
    'Code', 'Song Title', 'Artist', 'Level', 'Type', 'Charter', 'Release',
    'Album', 'Year', 'Genre', 'Official',
    'NoteCount', 'DurationS', 'Difficulty', 'D', 'RemapDiff', 'CalcTier',
    'pNPS', 'aNPS', 'medNPS', 'stdNPS', 'pVPS', 'aVPS', 'medVPS', 'stdVPS',
    'N', 'V', 'COV',
]
```

`song_row.row_meta` gains `'Album': meta.get('Album', '')`, `'Year': meta.get('Year', -1)`, `'Genre': meta.get('Genre', '')` (the defaults are what an old cache produces: empty text and the sentinel). After the `Difficulty` coercion at `analyze.py:202`, one mirror line: `df['Year'] = pd.to_numeric(df['Year'], errors='coerce').fillna(-1).astype(int)`. Section 05's "column O" for `SongKey` reads R after this section; any assertion should locate `SongKey` by name, not by letter.

**xlsx columns**: `Album` (H), `Year` (I), `Genre` (J). `Year` is an integer column, not in `FLOAT_COLS`, no colour scale, no hidden flag. Widths by the existing rule: Album capped at 40, Genre 25, Year 6.

**`functions/labels.py`**, stated as insertions so they compose with section 05 in either order:

| Table | Change |
|---|---|
| `COLUMN_LABELS` | add `'Album': 'Album'`, `'Year': 'Year'`, `'Genre': 'Genre'` |
| `COLUMN_HELP` | add `'Album': 'Album from song.ini, as the charter wrote it. Empty when the file has none.'`; `'Year': 'Release year from song.ini. A dash means the file has no four-digit year.'`; `'Genre': 'Genre from song.ini, as the charter wrote it. Spellings vary between charters; empty when the file has none.'` |
| `MISSING_VALUES` | add `'Year': (-1,)` |
| `MISSING_HELP` | add `'Year': 'No four-digit year in song.ini'` |
| `DISPLAY_ORDER` | insert `'Album', 'Year', 'Genre'` immediately after `'Release'`; the rest, including 05's trailing `'SongKey'` if present, unchanged |
| `DEFAULT_HIDDEN` | prepend `'Album', 'Year', 'Genre'`, with a comment line per new entry in the block at `:189-198` (Album: wraps, and the first view is full at 390 px; Year and Genre: filters on them work while hidden); 05's `'SongKey'` if present, unchanged |
| `UI['search']` | `'Search song, artist, album, charter or source...'` |
| `PREFS_VERSION` | `2`, only if section 05 has landed |

Before 05 the two tuples read `DISPLAY_ORDER = ('Song Title', 'Artist', 'D', 'CalcTier', 'Level', 'Type', 'DurationS', 'NoteCount', 'Charter', 'Release', 'Album', 'Year', 'Genre', 'Difficulty', 'RemapDiff', 'Official', 'Code')` and `DEFAULT_HIDDEN = ('Album', 'Year', 'Genre', 'Difficulty', 'RemapDiff', 'Official', 'Code')`.

These reach the page through `web/boot.py` unchanged. Column keys on the page are the xlsx headers, `Album`, `Year`, `Genre`; the URL uses them verbatim: `f.Genre=Rock,Heavy%20Metal`, `f.Album=Death%20Magnetic`, `r.Year=1980:1989`, and `q=` now matches Album text.

**`web/static/js`**:

- `query.js`: `SEARCH_COLS = ["Song Title", "Artist", "Album", "Charter", "Release", "Code"]`; `matchesFilter` range branch becomes `if (typeof v !== "number" || isMissing(col, v)) return false;` (`isMissing` is already imported at `:4`).
- `dropdown_view.js`: `rangeBody` filters `vals` with `typeof v === "number" && !isMissing(col, v)` (this section's change) on the same line where section 02 formats the placeholders with `v.toFixed(decimals(col))` (02's change; made here too if 02 has not landed); imports `isMissing` and `decimals` from `./format.js`.
- `markup.js`: `TEXT_CLASS["Album"] = "title album"`, `TEXT_CLASS["Genre"] = "genre"`.
- `app.css`: `td.album { max-width:220px; }` beside `td.artist` (`:77`); `td.album { max-width:100px; }` inside the 640 px block beside `td.artist` (`:166`).

**`functions/difficulty.py`**: `HEADER_META_KEYS = ('Name', 'Artist', 'Charter', 'Release', 'Official', 'Difficulty')`, with a comment that `bundle.fingerprint` reads it, that `plot.meta_header`, `plot.output_filename` and the title row are what it mirrors, that `tests/test_fingerprint.py` checks the mirror against `plot.py`'s source, and that adding a printed key means a full re-render.

**`web/bundle.fingerprint`**: the `:76` line becomes

```python
repr(sorted((k, v) for k, v in entry['meta'].items() if k in difficulty.HEADER_META_KEYS)),
```

with `from functions import plot` as the first statement of the function body and a comment beside it: plot pulls matplotlib, publish renders through it anyway, serve never imports this module. Everything else in the tuple is unchanged; `graph/manifest.json` keeps its `{code: sha1}` shape.

**Section 05 interfaces this section relies on, nothing to add.** The per-sheet JSON `columns` list picks the three up from the xlsx automatically; `prefsVersion` carries the bump. Section 05's size table (Guitar 1,004,739 bytes with `SongKey`) should be re-measured after this lands: expect about +242 KB raw and +80 KB gzipped on Guitar. Section 05 must add: nothing.

**Section 04 fixture contract.** Every synthetic `song.ini` carries `genre`, `year` and `album` (04 says so and pins nothing about them); this section prescribes the values: at least one song has `year = Unknown Year`, one has `year = 2007 (re-issue)`, one has `year = Vol. 2 (2001)`, one album contains a comma, and one genre carries `<color=#ff0000>...</color>` markup, so the pipeline test can assert the sentinel, the anywhere rule, the comma and the DETAG strip. 04's totals do not move (no song is added; the sha1 lists it compares run to run are over note streams, which these values do not touch).

## Files touched

- `parsers/ini_parser.py`: `YEAR`, `_year()`, three entries in the `ini_parse` return dict; docstring line 2 lists the new fields.
- `build.py`: `META_KEYS` gains `'Genre', 'Year', 'Album'`.
- `functions/cache.py`: docstring `meta` line spells out the nine keys.
- `analyze.py`: `COLUMN_ORDER`; three `row_meta` entries; the `Year` coercion line.
- `functions/difficulty.py`: `HEADER_META_KEYS`.
- `web/bundle.py`: `fingerprint` filters `meta` by `difficulty.HEADER_META_KEYS`; the comment at `:67-68` says so.
- `functions/labels.py`: the seven table entries above; `PREFS_VERSION` incremented by one if section 05 has landed (03 and 10 bump it too, so the value is whatever it is plus one, never a literal).
- `web/static/js/query.js`: `SEARCH_COLS`; range branch rejects a sentinel.
- `web/static/js/dropdown_view.js`: placeholders skip sentinels and use the column's decimals.
- `web/static/js/markup.js`: `TEXT_CLASS` gains `Album` and `Genre`.
- `web/static/css/app.css`: two `td.album` rules.
- `README.md`: line 97 (the metadata list gains Album, Year, Genre and says Year is `-1` when the ini has no four-digit year); line 172 (search names album); line 199 (the section 6 bullet: `metadata` becomes `the metadata the graph header prints`); section 7 step 4 gains one sentence: a metadata-only change re-renders no graphs.
- `CLAUDE.md`: line 42, "metadata" becomes "the metadata the header prints (`difficulty.HEADER_META_KEYS`)"; line 190 (the cache contract paragraph) names the nine meta keys; line 237 gains one clause: `Year` of `-1` (int in both) is the same sentinel for no four-digit year, and `labels.MISSING_VALUES` is where the page learns both.
- If section 04 has landed: `tests/fixture.py` (the five prescribed ini values), `tests/pipeline_test.py`, `tests/page/test.js`, `tests/page/roundtrip.js`, and a new `tests/test_fingerprint.py` (new; or the cases go in `tests/test_bundle.py` if section 05 has landed).

No new files outside `tests/`.

## Steps

Every commit in this sequence is one `publish.py` could ship, in this order: the fingerprint narrowing is invisible on a six-key cache, the page changes are inert until the sheet has the columns, and the sheet gains the columns last. The one state to know about is between steps 3 and 5, when the newest cache has nine keys and the newest spreadsheet does not: section 00's `check_pair` refuses to publish that pair, which is the intended safety net, and step 5's analyze run clears it.

1. **Narrow the fingerprint, before any publish.** First, on the unedited code, run the Verification snippet in `save` mode against `caches/Local_cache_09102026-2324.pkl`; it writes the 298 sampled fingerprints to the scratchpad. Then add `difficulty.HEADER_META_KEYS`, the filtered `repr` in `bundle.fingerprint` and `tests/test_fingerprint.py`'s source check, and run the snippet in `before` mode: it must print `before identical 298 of 298`. That compares the new code with the hashes the old code produced on the same six-key cache, so a `HEADER_META_KEYS` that lost one of the six keys would fail it. Commit: `publish: fingerprint only the metadata the graph header prints`.
2. **Confirm the baseline.** Section 00 step 6 is the one full re-render: `python analyze.py --header Local` (writes `metrics/Local_metrics_09102026-2324.xlsx`; the terminal summary prints `11904 Rows written:` over the per-instrument level matrix, and `pd.read_excel(..., sheet_name=None)` gives Guitar 6,610, Bass 5,038, Keys 256, which the cache's non-drum level entries confirm) and then `python publish.py --header Local`, which renders all 11,904 from the 2324 cache in about 24 minutes. If it has already run, `site/Local/graph/manifest.json` is newer than commit 69b5a8f (2026-09-11 00:11) and `python publish.py --header Local` reports `rendered 0, unchanged 11904` in seconds; if it has not, run it now. Then the snippet in `manifest` mode prints `manifest identical 298 of 298`. The 2324 pair is the baseline every later `rendered 0` is measured against, and the row counts in Verification are compared against this analyze run, not the 2031 spreadsheet. Step 1 may land before or after this publish (the narrowed hash is byte-identical on a six-key cache); it must land before the first publish after step 3's rebuild. No commit.
3. **Read the three keys.** `ini_parser`, `build.META_KEYS`, the `cache.py` docstring. Check: a one-off `.venv/bin/python` loop calling `ini_parse` over `songs/**/song.ini` counts 1,756 int years and 2 sentinels, 212 distinct genres, 1,261 distinct albums, and no value containing `<`. Then `python build.py --search-path songs --header Local`: the summary reports Song.ini count 1758, No usable chart/mid and Errors as the previous build printed them, Diffs backed up 0, Cached songs 1758 and the same instrument/level matrix; no `Local_errors_*.csv` appears; `caches/Local_BackupData.csv` gains no rows; `len(cache_mod.load(<new cache>)['codes'])` is 15,660 and every `songs[p]['meta']` has nine keys. The snippet in `manifest` mode against the new cache prints `manifest identical 298 of 298`: the nine-key cache hashes to what the six-key baseline recorded, which is the proof the three keys are outside the fingerprint. Commit: `read genre, year and album from song.ini into the cache`.
4. **The page, inert until the sheet has the columns.** `labels.py` (all seven table entries, and `PREFS_VERSION` incremented by one if 05 has landed), `query.js`, `dropdown_view.js`, `markup.js`, `app.css`. Every labels entry for a column the sheet lacks is inert: `ordered()` and the chooser list only columns present, `matchesSearch` skips absent columns (`query.js:42`). `python serve.py --header Local` (it serves the 2324 spreadsheet). Check, with `localStorage` cleared: the chooser lists no Album, Year or Genre; with Difficulty ticked in the chooser, `?r.Difficulty=:3` shows the same count as `?r.Difficulty=0:3` and no dash in the Difficulty column (before the fix the hi-only form was larger by the unrated rows); NoteCount's filter box reads `min 2` on Guitar; the range placeholders for `D` still show two decimals. Commit: `page: album, year and genre columns, and keep sentinels out of ranges`.
5. **Spreadsheet columns.** `analyze.COLUMN_ORDER`, `song_row`, the `Year` coercion. `python analyze.py --header Local` (pairs with step 3's cache). Check: `pd.read_excel(..., sheet_name=None)` shows columns 7 to 9 as `Album, Year, Genre` on every sheet, `Year` dtype `int64`, `(Year == -1).sum()` of 5, 4, 0 on Guitar, Bass, Keys, row counts 6,610 / 5,038 / 256 as in step 2, and the xlsx name carries the new cache's timestamp. Old-cache compatibility, into the scratchpad so `metrics/` and the baseline pair are untouched: `.venv/bin/python -c "import analyze; analyze.analyze(cache_path='caches/Local_cache_09102026-2324.pkl', header='Local', out_dir='<scratch>')"`, then read `<scratch>/Local_metrics_09102026-2324.xlsx` with pandas and confirm Album and Genre are empty and Year is `-1` throughout (`analyze.py` has no `--out-dir` flag, and `--header OldCache` would fail in `timestamp.ext_ts` because the cache name starts with `Local_`). Then `python serve.py --header Local` and, with `localStorage` cleared: the default header shows no Album, Year or Genre; the chooser lists all three unchecked immediately after Source; ticking Year gives a `min 1962` to `max 2026` box; `1980:1989` shrinks the count and no dash appears in the Year column; ticking Genre gives a checkbox list with a search box; typing `death magnetic` in the search matches rows with Album hidden; typing `rock` matches only titles, artists, albums, charters and sources containing it; sorting by Year puts the dashes last in both directions; the address bar carries `r.Year=1980:1989` after 250 ms. Commit: `analyze: Album, Year and Genre columns after Release`.
6. **Docs, and the proof that nothing re-renders.** README and CLAUDE.md as listed. `python publish.py --header Local` against the new pair. Check: the summary reads `rendered 0, unchanged 11904, pruned 0`; `index.html` grows by about 465 KB (or, under section 05, the three `data/*.json` files carry the growth and `index.html` does not move); `graph/manifest.json` is byte-identical to the one from step 2 (`sha1sum` before and after; `_save_manifest` sorts keys, so this is a fair comparison). Commit: `docs: the three song.ini columns, and what the graph fingerprint now reads`.
7. **Deploy.** `python deploy.py --dry-run` lists `index.html` (plus the hashed `data/` and `static/` files under 05) and no `graph/` uploads; then `python deploy.py`; `verify` passes. Tag `fretladder-v<next>`. No commit.

## Verification

- Fingerprint identity, one snippet with three modes, saved in the scratchpad as `fp_check.py` and run as `.venv/bin/python fp_check.py <mode> <cache.pkl>` from the repo root:

```python
import json, pathlib, sys
sys.path.insert(0, '.')
from functions import cache as cache_mod, ini_updater
from web import bundle
mode, cache_path = sys.argv[1], sys.argv[2]
saved = pathlib.Path(__file__).with_name('fp_before.json')
manifest = json.loads(pathlib.Path('site/Local/graph/manifest.json').read_text())
entries, missing = cache_mod.entries_by_code(cache_mod.load(cache_path), list(manifest)[::40])
diffs = ini_updater.load_backup_diffs('Local')
now = {e['code']: bundle.fingerprint(e, diffs.get(e['song_path'], {}).get(e['instrument']))
       for e in entries}
if mode == 'save':                       # run on the unedited code, before step 1
    saved.write_text(json.dumps(now)); print('saved', len(now))
else:                                    # 'before': against the saved hashes; 'manifest': against the live manifest
    ref = json.loads(saved.read_text()) if mode == 'before' else manifest
    same = sum(now[c] == ref.get(c) for c in now)
    print(mode, 'identical', same, 'of', len(now), 'missing', len(missing))
```

  `save` runs once on the unedited code against the 2324 cache. `before` after step 1's edit must print `before identical 298 of 298`: the narrowed formula reproduces the old one on a six-key cache, so every one of the six keys is still hashed. `manifest` after step 2 (2324 cache) and again after step 3 (the nine-key cache) must print `manifest identical 298 of 298`; the second run is the only observable proof that Genre, Year and Album are outside the fingerprint. `manifest` before step 2 prints `0 of 298`, which is the spans removal, not this section. The snippet imports matplotlib through `plot` on its first `fingerprint` call.
- `python publish.py --header Local` after step 5: `rendered 0`. That number is the section's acceptance test, and it only means something after step 2's baseline exists.
- `python analyze.py --header Local` output and the xlsx checks in step 5; `11904 Rows written:`, the level matrix and the per-sheet counts (Guitar 6,610, Bass 5,038, Keys 256) unchanged from step 2's run.
- 390 px re-measure with section 04's `frame.html`, twice: with storage cleared (the default view), `D` still lands at x 262 to 358 and the header is still 122 px, since no default column changed; then with `fw.hidden` set to `["Difficulty","RemapDiff","Official","Code"]` so Album, Year and Genre show, `td.album` measures at most 100 px wide, the row height is at most two lines for `Metropolis, Pt. 2: Scenes From a Memory`, and `D` is still on screen (it is left of all three, so this is a confirmation, not a search).
- Section 04 suites gain: in `tests/pipeline_test.py`, the fixture xlsx has `Album, Year, Genre` at columns 7 to 9, `Year` is `int64`, the `Unknown Year` song is `-1`, the `2007 (re-issue)` song is 2007, the `Vol. 2 (2001)` song is 2001, and the markup-carrying genre is `Rock`; in `tests/page/test.js`, the default header lacks the three, the chooser lists them unchecked immediately after Source, ticking Album yields `td.album` cells and ticking Genre yields `td.genre` cells, and a `?r.Difficulty=:3` view contains no unrated row; in `tests/page/roundtrip.js`, `?r.Year=1990:1999` restores a range filter whose result set contains no dash in the Year column, `?q=<the fixture's comma album>` finds its rows, and `?q=<the fixture's markup genre>` finds none through Genre alone; in `tests/test_fingerprint.py` (or `tests/test_bundle.py` under 05), `bundle.fingerprint` is unchanged when `'Genre'` is added to or removed from an entry's `meta`, changes when `'Name'` changes, and `set(difficulty.HEADER_META_KEYS)` is a subset of the fixture cache's meta keys. Note for the fixture: with fewer than 26 distinct years the page gives Year a checkbox list, not a range box, so the range assertion must use the URL, not the dropdown.

## Risks and gotchas

- Section 00 step 6 pays the one full re-render (the manifest predates 69b5a8f; 0 of 298 sampled fingerprints match today). Step 1 may land before or after it, since the narrowed hash is byte-identical on a six-key cache, but it must land before the first publish after step 3's rebuild, or the nine-key metas re-render everything and step 1 then re-renders them again. Do not read a first `rendered 11904` as this section's fault, and do not read a later `rendered 0` as proof unless step 2's baseline exists.
- `page.fill` (`web/page.py:36-41`) raises on any `__UPPER__` token in the filled page. No album or genre in `songs/` contains one (measured), but a pack could; section 00 moves the check to the template. Land 00 first.
- An old cache through the new analyze works (defaults in `row_meta`); an old xlsx through the new page works (`ordered()` lists only columns the sheet has, `matchesSearch` drops absent columns at `query.js:42`, `matchesFilter` passes a missing column at `:48`). The two committed example spreadsheets under `metrics/` are upstream's own runs (`684052b`, author Staycation, from a library this repo does not have) and must not be regenerated: `git add -f` of a `Local` xlsx would commit a real library's metrics, which CLAUDE.md forbids. Leave them; they load without the three columns.
- Set filters in the URL split on commas (`url.js:62`), and 24 distinct albums (42 songs) contain one, so `f.Album=Metropolis, Pt. 2...` does not round-trip. This is the same limitation Artist and Release have today (`Crosby, Stills & Nash`); it is not made worse here, and the fix belongs with section 05's URL contract or section 07. The filter works on the page; only the copied link loses it.
- The range fix changes `r.Difficulty=:3` too: unrated rows drop out of a hi-only range. That is the correct reading; a section 04 assertion written against the old behaviour would need updating. The placeholder change also turns NoteCount's `min 2.00` into `min 2`.
- The search placeholder is 48 characters and is clipped at 390 px, where `#q` is about 205 px wide. It is a hint, not content; accepted.
- `_year()` takes the first four-digit run anywhere in the value, so `1999-2000` gives 1999, `Vol. 2 (2001)` gives 2001 and `12345 1987` gives 1987; a value whose only digit runs are three or five long is the sentinel, and `0999` is too (the first digit must be 1 to 9). A year the charter typed in a phrase such as `c. 1990` counts; that is the help text's promise.
- Album's filter dropdown lists 1,260 checkboxes on Guitar. The Song Title dropdown already lists 1,602 on Guitar, so this is within what the page does today, but it is the reason Album gets `title album` and not a value order.
- The boot payload grows about 27% until section 05 moves rows out of `index.html`: from 1.78 MB to about 2.25 MB (about 465 KB with `json.dumps` defaults; 430 KB is the compact figure section 05's `data/` files will carry). With 05, the growth lands in the immutable `data/*.json` files instead.
- The leaderboards userscript (`../fretladder-leaderboards.user.js` (the Tampermonkey prototype kept beside the repo, untracked)) indexes boot rows by column name (`compactRows`, `:107-120`), so the three new columns do not break it; its daily off-site fetch of `index.html` (`:122-133`) grows by the same 465 KB until section 05 moves the rows out of the page.
- `HEADER_META_KEYS` mirrors what `plot.py` prints from another file. An upstream merge that adds a printed field to `meta_header`, the title row or `output_filename` makes the PNGs go stale silently until the tuple follows; `tests/test_fingerprint.py`'s source check (each key appears in those three functions' source, and no other `meta` key does) is what turns that into a red test on the next CI run, and step 1's `before` check catches a key dropped from the tuple.
- `bundle.fingerprint` imports `plot` lazily. Publish already renders through it and serve never imports `web/bundle.py`, so no CLAUDE.md rule moves; a test of the fingerprint does import matplotlib, which `requirements.txt` provides.
- The rebuild is the first build after section 00 corrects the backup CSV header. Confirm `caches/Local_BackupData.csv` still has 1,758 rows and now a seven-column header before trusting the render header's `diff` value.
- An absent Album and an absent Genre both print as an empty cell and both list as the dash in their checkbox filters; an absent Year prints as the dash. The help text for each says which.

## Out of scope and follow-ups

- Showing Year and Album in the graph heading (`overlay.js:19-38`) and in the per-song view: section 07 owns that view, and the heading already lists five fields.
- `song_length`, `album_track`, `playlist_track`, `loading_phrase`, `icon`, `preview_start_time`: not read. `icon` is consumed inside `ini_parse` for Release and Official and does not need a column.
- Genre in the toolbar search: rejected in Design item 6 for the measured flood; if a later section wants it, the number to beat is 558 of 1,758 rows for `rock`.
- Optional follow-up: genre normalisation. 212 spellings over 1,758 songs (`Pop-Rock` beside `Pop Rock`, `Alternative` beside `Alternative Rock`) make the checkbox list long and the counts misleading. A mapping table in `sources/` would fold them, but choosing canonical names is a decision, not a measurement. The fact that would unblock it: the genre facet Enchor exposes for the same songs, which section 13's live experiment can capture.
- Optional follow-up: encoding set-filter values that contain a comma in the URL (`url.js:23-26, :62`); needs a decision about backward compatibility of existing shared links, which belongs with section 05's loading contract.
- Percentile, duplicates and source links do not touch these columns; section 10 may want `Album` in its "same song" heuristics, and gets it from the same row data.

## Open questions

None.
