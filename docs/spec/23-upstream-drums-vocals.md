# 23. Drums, vocals and formula v2 from upstream

**Status:** Implemented 2026-09-19 on the `upstream-merge` branch, from the merge of `upstream/main` at `ff14725` (38 commits, 2026-09-10 to 2026-09-19) into the fork's `main` at `3643dc9`. Written the same day, after the code, from the maintainer's "the parent project we forked off of has new commits. We need to incorporate that into our fork and website". Section 11 was the plan for this day, written before upstream had chosen a shape; what upstream chose is recorded here and 11 is closed by it.

**Effort:** L. The merge itself (five conflicts, upstream's `render.py`, `analyze.py` and `xlsx_format.py` taken whole with the fork's columns ported into every profile), then the site: one difficulty block per family, a curve file with named lines, the graph drawing any family, one shape for every sheet, the methodology check over three modules with upstream's own drift reported rather than fixed, the fixture growing vocals, and every string that said drums and vocals were not scored.

**Depends on:** 00 (`difficulty.scorable`, now per family), 05 (the data model: `SongKey` unchanged, the curve files), 06 (the canvas graph), 12 (the methodology page), 20 and 22 (the library, game and list pages, which gain the two sheets), all live as fretladder-v1.5.0.

## Goal

Every chart the engine scores is on the site: drums at every level with the 1x and 2x readings, vocals at their one level, each with a graph the page draws from its own lines, a row on its own sheet, a cell on the song page and a column on the game page, and the fret family rescored by formula v2 (`D = N * V * CoV * STAM`, the median and std over active windows), so the site says what `analyze.py` says.

## Why

Upstream rebuilt the formulas (2026-09-12 to 09-18): the fret formula gained the stamina term and active-window gating, and every D on the site moved with it; drums got a formula of their own (`D = (H + T + K) * CoV * STAM`, additive across limbs, at a single-pedal and a double-pedal reading); vocals got a parser, a density module and a formula (`D = (P * R * A + S) * CoV * STAM`). The fork's value is the viewer; its data is upstream's, unchanged. A site still on v1 would rank charts by numbers the engine no longer produces.

## Current state

Measured on the merged tree with the Local library rebuilt 2026-09-19 17:55 (2,272 songs): 18,807 rows on five sheets (Guitar 8,781, Bass 5,102, Keys 256, Drums 3,789, Vocals 879; 18,695 distinct charts), against 14,139 on three before. Drums Expert CalcTier runs 0 to 7 (median 4), vocals 0 to 6 (median 2), guitar Expert 0 to 12 as before, with every fret D moved by v2 (the hardest guitar chart reads 1,233.95 where it read about 1,000).

Before this section the site had the three fret sheets, `functions/difficulty.py` imported `density` and `formula` (renamed upstream), `web/graph.py` wrote a v1 curve file (`win`, `var`), `graph.js` drew exactly Notes and Variability under ~D, `web/methodology.py` checked three tables against one module, and eleven strings said drums and vocals were not scored (section 11 Design 5 lists them). Upstream's `Methodology.md` has two tables that lag its code: the Guitar remap bins (refit in ef0f1f8 without the table) and the drums `LN_INC` (0.196 in `drum_formula.py`, 0.20 in the table).

## Design

1. **One family key.** `instruments.FAMILY` maps every instrument to `fret`, `drums` or `vocals` and `SCORED_INSTRUMENTS` is every instrument; `SONG_KEY_INSTRUMENTS` stays the five 5-fret keys, so no `SongKey`, and so no song page URL, moved. `difficulty.FAMILY_KEYS` names each family's stream shape and `scorable(entry)` checks it; `entry_difficulty` is one function per family (`FAMILY_DIFFICULTY`), the same calls `render.py` and `analyze.py` make, and every block carries `D` (drums: the 1x reading, `D_2x` beside it when the chart has double-pedal kicks), `RemapDiff` and `CalcTier`. Rejected: a merged drums stream through the fret formula (section 11's plan A), since upstream scored the limbs separately; scoring in the fork at all.

2. **A curve file with named lines (v2).** `{v: 2, family, step, window, tau, n, head, series: {key: counts}, d: {geo: [keys]} | {sum: {key: weight}}}`. The lines are the family's (`nps`, `vps`; `hps`, `tps`, `kps`; `pps`, `sps`, `perc` when the chart has percussion) and the recipe is `curves.py`'s `d_raw` line: the geometric mean for the fret family, the sum for drums (at the 1x reading; the 2x picture is a follow-up), `R * A` and `S_WEIGHT` as weights for vocals, whose register and articulation are the chart's own numbers and ride in the file. Counts stay integers where the module keeps them so, else four places. `graph.js smooth()` smooths each line and makes ~D by the recipe; `gLines(curves)` gives the family's lines in order, with their words and colour tokens from `labels.CURVE_FAMILIES` (booted as `curves`), for the legend, the readout, the alt text and the export. The three line tokens `--fw-curve-nps/vps/kps` serve every family in `plot.py`'s own assignment (`color_nps` is notes, hands and syllables; `color_vps` variability, travel and pitch; `color_kps` kicks and percussion), so the palette grows one token, the green, and no colour changes meaning. Rejected: one file shape per family (three drawing paths); a fixed trio with the third line optional (vocals without percussion would draw an empty line); v1 kept for the fret family (every fret file rewrites anyway, since the head's numbers moved).

3. **One shape for every sheet.** `frames.unify` reads the Drums sheet's `D_1x` and `NoteCount_1x` as `D` and `NoteCount` (the 1x reading is the sheet's sort column and the site's rank; `D_2x` and `NoteCount_2x` stay beside them) and gives the Vocals sheet, Expert only and without a `Level` column, one reading `Expert` after Artist. The spreadsheet keeps its profile's names; the page, the percentile, the counts, the song, game and list pages key on `D` and `Level` alone, so the pane's line 2, the song grid, `charts_by_folder`, the lists per sheet and the library page needed no branch. Rejected: teaching the page a D column per sheet (every module that reads `D` would branch); a `D` column beside `D_1x` (the same number twice on the Drums sheet).

4. **The game page and the lists.** `page.OTHER_PARTS` is one column per part of every sheet but the Guitar sheet's, in sheet order (Bass, Keys, Drums, Vocals), so the game page shows them all and ranks by the guitar parts; the lists run per sheet, so `list/hardest-drums.html` and `list/hardest-vocals.html` exist from the same loop. The song page's picture alt names the chart family's lines (`labels.t_graph_alt(song, code)`).

5. **The methodology check over three modules, drift reported.** `web/methodology.MODULES` names the three formula modules; each remap table is found by the constant its heading names and checked against the module that holds it, and the CalcTier table, now five columns, names each family's module in its Home column and is checked row by row, the step column against `exp(LN_INC) - 1`. A table that cannot be read raises; a number that differs is a drift, returned as a sentence. This fork never edits `Methodology.md`, so a drift is printed at publish and serve and put on the page under the source line (`labels.METHODOLOGY_DRIFT`, one sentence each), since the code is what scored the charts and the document is upstream's; `KNOWN_DRIFT` is the set upstream has been told about, the test pins it, and `python -m web.methodology` exits non-zero on any other, so a merge notices a new one and a fix. Rejected: failing publish on drift (the site would wait on upstream's document for numbers the site already prints from the code); editing the table here (the fork's rule); silence (the page would show a visitor the wrong Guitar bins with no word).

6. **The renderer keeps up with the document.** Upstream's `Methodology.md` grew lists, links, rules, comments, inline formulas, `\left` and `\right`, `\approx` and `\;`; `web/markdown.py` accepts each (a same-page anchor link, a flat bullet list, a rule, inline `$...$` through the typesetter, comments stripped) and still refuses what it does not know (ordered and nested lists, setext headings, fenced code, an unknown command), naming the line.

7. **Identity for a vocals chart.** `cache.stream_bytes` hashes a vocals chart's sung arrays with its talkie and percussion streams (`notes_hash(notes, *sides)`), so two spoken-only charts with different lyrics do not read as copies. `bundle.fingerprint` hashes the notes through `stream_bytes` as well, with a drum chart's roll spans and a vocals chart's side streams, since formula v2 moved every stored fingerprint anyway; `fingerprint_curves` carries the file version.

8. **The words.** `labels.py` labels and explains every column of the two new profiles (the diagnostic ones too, though `EXTRA_METRICS` keeps them out of the spreadsheet), and `boot.columns_present` sends the island only the words for the columns the sheets have, so the island stays about 29 KB with five manifests. The explainer says what each family multiplies and adds, the CalcTier help prints all three constant pairs from the modules, the about page names the five instruments, the beta note no longer says "guitar, bass and keys for now", and the drums caveats (rolls capped, the 1x reading) and the vocals caveat (the loosest fit) are said where the fret caveats are.

9. **The fixture.** Two `.mid` songs carry vocals (a sung line over an octave with a slide every fifth note, a talkie every seventh and a percussion tap every eleventh), so every family runs through build, analyze, publish, serve and the page suites; `graph.js` runs on the Drums and Vocals sheets as well as the first.

## Data and interfaces

- `instruments.FAMILY`, `instruments.FAMILIES`, `instruments.SCORED_INSTRUMENTS` (every key).
- `difficulty.FAMILY_KEYS`, `difficulty.family(entry)`, `difficulty.scorable(entry)` (takes the entry, not its notes), `difficulty.FAMILY_DIFFICULTY`, `entry_difficulty(entry)`.
- `cache.VOCAL_KEYS`, `cache.SIDE_KEYS`, `cache.stream_bytes(notes, *sides)`, `cache.notes_hash(notes, *sides)`; `build.py` passes a vocals entry's `talkie` and `percussion`.
- `graph.CURVES_VERSION` 2, `graph.FAMILY_SERIES`, `graph.curves_bytes(entry)`; `GraphRenderer.render` per family.
- `bundle._notes_bytes(entry)`, `fingerprint`, `fingerprint_curves`.
- `frames.unify(frames)`, `frames.UNIFY_RENAMES`, `frames.EXPERT`; `load_frames` returns unified frames.
- `labels.CURVE_FAMILIES`, `labels.METHODOLOGY_DRIFT`, `labels.t_graph_alt(song, code)`; `UI.graph_readout` (`{t}  ~D {d}  {lines}`), `graph_readout_line`, `graph_alt` (`{lines}`); `graph_nps` and `graph_vps` are gone.
- `boot.columns_present(manifest)`, `boot['curves']`.
- `page.GUITAR_SHEET`, `page.OTHER_PARTS`.
- `methodology.MODULES`, `methodology.KNOWN_DRIFT`, `methodology.check_tables(blocks) -> [drift]`, `methodology.load(path) -> (blocks, drifts)`, `methodology.plain(drift)`.
- `graph.js`: `smooth(json) -> {lines, keys, d}`, `gLines(curves)`, `gPalette().line(token)`, `gPalette().kps`; `app.css`: `--fw-curve-kps`.
- `tests/page/run.py`: a dump without the results block is retried once.

## Files touched

Merge: `analyze.py`, `build.py`, `render.py`, `functions/instruments.py`, `functions/xlsx_format.py`, `functions/cache.py`, the parsers, `.gitignore`, `README.md`, `Methodology.md` (upstream's), `functions/fret_density.py`, `fret_formula.py`, `drum_*`, `vocal_*`, `parsers/vocal_parser.py` (new, upstream's). Site: `functions/difficulty.py`, `functions/labels.py`, `web/graph.py`, `web/bundle.py`, `web/frames.py`, `web/boot.py`, `web/page.py`, `web/methodology.py`, `web/markdown.py`, `web/static/js/graph.js`, `boot.js`, `web/static/css/app.css`, `web/static/doc.html`, `tools/ingest_pack.py`, `tests/fixture.py`, `tests/test_fixture.py`, `tests/test_bundle.py`, `tests/test_graph_json.py`, `tests/test_methodology.py`, `tests/test_copies.py`, `tests/test_page.py`, `tests/pipeline_test.py`, `tests/page/graph.js`, `narrow.js`, `contrast.js`, `run.py`, `CLAUDE.md`, `README.md`, `docs/spec/README.md`.

## Verification

- Unit: `test_bundle` (the v2 shape per family, every family's ~D reconstructed from its JSON against `curves.py`, the difficulty block per family, a wrong shape not scorable, the fingerprints seeing roll spans and side streams), `test_graph_json` (every token the canvas reads and every family's line tokens in both theme blocks; each family's legend words are `plot.py` labels and its tokens `plot.py`'s colours), `test_methodology` (the file's drift equals `KNOWN_DRIFT`; a moved number is one more drift; an unreadable table raises; the page carries the note), `test_copies` (the vocals hash covers the side streams), `test_page` (`unify`), `test_fixture` (52 codes, five sheets).
- Pipeline: five sheets with their profiles' columns, the unified frames, the drums and vocals rows, every family resolving in `GraphRenderer` and serving a PNG and its v2 curve file, the drums and vocals lists, a column per other part on the game page, the vocals sentence on a song page, the drift on the methodology page.
- Page suites: `graph.js` on the first sheet, Drums and Vocals (the legend is ~D and the family's lines, each swatch its token, the readout every line's word, the alt text the family's words, the geometric mean and the weighted sums through `smooth()`), `contrast.js` (the kicks token), `narrow.js` (six tables, 29 formulas; a formula wider than the screen scrolls in its own box).
- The real library: `python build.py --search-path songs --header Local`, `analyze.py`, `publish.py`, the suites against `site/Local`, `deploy.py --dry-run`; then the maintainer deploys and tags v1.6.0.

## Risks and gotchas

- Every D moved. The release notes must say so: percentiles and tiers on the fret sheets are not comparable to v1.5.0's, and every curve file and picture is rewritten (18,807 JSON files and 2,272 PNGs uploaded once).
- The drums `D` on the site is the 1x reading; a double-pedal player wants `D_2x`, which is a column (shown by default) and not the graph's picture.
- Upstream's Methodology.md lags its code; the page says so. The correction is upstream's (an issue or a PR from a branch off `upstream/main`, with the maintainer's approval), and `KNOWN_DRIFT` shrinks when it lands.
- `git stash` in a merge in progress drops `MERGE_HEAD`; it was restored by hand this time (`.git/MERGE_HEAD`, `MERGE_MODE` `no-ff`, `MERGE_MSG`). Never stash mid-merge.
- The headless runner's first launch on a fresh profile now and then dumps the page before the suite runs; a dump without the results block is retried once, since a suite that ran always writes the block.

## Out of scope and follow-ups

- Optional follow-up: the 2x picture on the drums graph (a toggle, or a second ~D line from `kps2`), which needs the file to carry the 2x kicks; the site's D stays 1x.
- Optional follow-up: the leaderboard instrument literals for drums and vocals (`instruments.LEADERBOARD_INSTRUMENT`), which wait on the leaderboards half of section 13.
- Optional follow-up: a vocals-specific word for the empty level cells of the song grid ("No Easy chart" reads oddly for an instrument with one level).
- Upstream's `render.py` and `analyze.py` count and skip in their own words (analyze's "Rows written" counts attempted rows, 32 drum rows of the Local library skipped for having no hand hits at that level); not the fork's to change.
