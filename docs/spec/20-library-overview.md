# 20. The library overview page

**Status:** Landed (2026-09-12, 0265e58; awaiting the maintainer's deploy). Written 2026-09-12 against `main` at `e23f592`, from the Local library's sheets. As landed: the distinct count sits under each count as the smaller number rather than a "distinct" word (the table has to fit `doc.html`'s 64ch column); pack dates are ISO in the packs table for the same reason; the footer lists only the document pages the site has (`boot['docPages']` filtered in `page.build`), which fixed the changelog's own case too; bars are a tenth of a percent wide at least so a tier of one chart is still a mark.

**Effort:** M. One document page rendered at publish from the frames, in `doc.html`, no script; a footer link; one label block; tests.

**Depends on:** 03 (`packs.toml`, the changelog, `doc.html`), 02 (`Pct`), 10 (distinct charts), all landed.

## Goal

One page that says what the library is: how many charts of each instrument at each level, how they spread over the tiers, official against custom, the ten hardest per instrument, and which packs it is built from. The explainer can then point at real numbers instead of describing them, and a visitor can see at a glance whether the site covers what they play.

## Why

The strapline says "11,904 charts" and the changelog lists 26 packs; nothing says that the Guitar sheet's Expert charts sit mostly in tiers 3 to 5 (488, 443 and 308 of 1,853), that Keys is 256 rows, or that 2,756 of the 3,183 Expert charts are official. The explainer describes the tiers in words. A reader deciding whether "tier 6" is hard has no picture of the distribution behind the number. And a charter or a pack maintainer asking "is my pack in" has the changelog, which is by date, not by name. The numbers exist in the frames at publish time; the page is a table of them.

## Current state

- `render_doc` (`web/page.py:170`) fills `doc.html` (self-contained, the theme script, no other script); `render_changelog` (`:214`) is the model for a page built from `resolved` and the sheets; `changelog_pages` (`:247`) adds it to `files` exactly when the pack join exists.
- `labels.DOC_PAGES` lists the document pages the footer links (`main.js buildFooter`), and `deploy.BUNDLE_TOP` and `bundle.PAGE_TOP` name every entry page.
- Measured on the Local library: Guitar 6,610 rows (Lead 6,339, Rhythm 267, Co-op 4), Bass 5,038, Keys 256; Expert `CalcTier` on Guitar: 0: 40, 1: 69, 2: 248, 3: 488, 4: 443, 5: 308, 6: 142, 7: 76, 8: 26, 9: 4, 10: 2, 11: 5, 12: 2; Bass 0 to 6 with one at 11; Keys 0 to 6; 24 `Release` values over 26 packs; 2,756 official and 427 custom Expert rows.

## Design

1. **`library.html`, a document page.** Rendered by `page.render_library(resolved, sheets, names)` into `doc.html`, with `render_changelog`'s shape: a heading per block, tables, no script. Added to `files` beside the changelog when `resolved` is not `None` (the pack block needs it; the count blocks would stand without it, but one rule is simpler than two).
2. **Five blocks.** *Charts*: a table of sheets by levels, the distinct-chart count in a second line per cell (the `Copies` key, section 10), and the row and song totals. *Tiers*: per sheet, Expert charts per `CalcTier` as a bar table (a `<td>` with an inline-width `<span>`, no image, no script) with the count beside each bar, and the two calibration sentences from the explainer linked to `methodology.html#calctier-calibration`. *Official and custom*: per sheet at Expert. *The ten hardest* per sheet at Expert: rank, title, artist, D, tier, each a link to `index.html?code=`. *Packs*: name, added, songs, charts, official or custom, source when the registry has one, each name a link to the table filtered to the pack's `Added` date as the changelog links today, in the registry's order.
3. **Numbers from the same frames the page serves.** Everything is computed in `web/frames.py` helpers from the sheets `page.build` already holds (`frames.counts(sheets) -> {...}`), so the page and the table cannot disagree, and the strapline's total is the same number.
4. **Linked from the footer and the explainer.** `DOC_PAGES` gains `('library.html', 'library')`; the explainer's tier paragraph gains one link, "how the library spreads over the tiers".
5. **Serve parity.** Serve shows it when it has a cache (as with the changelog); without one, the footer link is absent rather than a 404 (the same rule the strapline follows).

Rejected: a chart drawn on a canvas (a document page has no script by design; the bars are `<span>` widths); putting the numbers on the charts page (it is already the busiest surface); a JSON endpoint of the counts (no consumer).

## Data and interfaces

- `frames.counts(sheets) -> {'levels': {sheet: {level: (rows, distinct)}}, 'tiers': {sheet: {tier: n}}, 'official': {sheet: (official, custom)}, 'hardest': {sheet: [rows]}}`.
- `page.render_library(resolved, sheets, names) -> bytes`; `page.library_pages(resolved, sheets, names)`, the `changelog_pages` twin.
- `labels.UI`: `library`, `library_tip`, the five headings and the column labels; `labels.DOC_PAGES` gains the page.
- `deploy.BUNDLE_TOP`, `bundle.PAGE_TOP` gain `library.html`; `check_site.py`'s about-page check does not change (the page is another document page).

## Files touched

`web/frames.py`, `web/page.py`, `functions/labels.py`, `deploy.py`, `web/bundle.py`, `web/static/js/main.js` (nothing: the footer reads `DOC_PAGES`), `tests/test_page.py` (with 16's, or new), `tests/pipeline_test.py` (the page exists, its totals equal the sheets'), `tests/page/about.js` (the footer link, as for the changelog), `README.md`, `CLAUDE.md` (the document pages sentence), `docs/spec/README.md`.

## Steps

1. `frames.counts` with a unit test on a three-row frame. Commit: `frames.counts: the library's numbers from the sheets`.
2. `render_library`, the strings, the allow-lists; the pipeline test reads the fixture's totals off the page. Commit: `library.html: charts, tiers, official and custom, the hardest, the packs`.
3. The footer entry and the explainer link; `about.js`. Commit: `the library page in the footer and the explainer`.
4. Docs. Commit: `spec index: 20 on main`.

## Verification

Unit and pipeline as above; `about.js` for the footer; `contrast.js` does not load document pages (section 12's note), and the page inherits `doc.html`'s two palettes, so no new pair exists.

## Risks and gotchas

- The ten hardest are the ten highest D, which on Guitar are stunt charts (the rating research excludes `CalcTier >= 10`); the block says "by D" and nothing more, since the site ranks by D everywhere.
- `Pct` is per sheet and level, so the page must not compare a Bass percentile with a Guitar one; the blocks are per sheet.

## Out of scope

- Charts over time (the changelog is that, by date); per-charter counts (a `Charter` filter is one click); a public API.
