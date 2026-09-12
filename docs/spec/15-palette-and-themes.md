# 15. Palette roles and the two themes

**Status:** Landed (2026-09-11, 3361aac; live as fretladder-v1.3.0). Written after the fact the same night, from the maintainer's "I think we need to revisit the color scheme and themes of this website" against the live v1.2.0 site, the analysis below, and a yes to all of it.

**Effort:** M. One new module (`theme.js`), the stylesheet's colour rules rewritten onto role tokens with two values each, `graph.js` reading its colours from the tokens instead of `boot.render`, a head script on every page, the document pages and the 404 given a light palette, one new suite and the contrast suite run twice.

**Depends on:** 06 (the canvas draws the graph, so the page can own its colours), 14 (the pane on the page's ground; the compare marks the tokens now colour), both landed.

## Goal

A colour means one thing. Magenta is the brand and says "on" or "do this"; links are one blue; the graph's three curves and the three compare series are two separate trios; the four level colours read as four; there is one ground, so the graph is not a box on the page; and the site has a light theme, following the OS and switchable from the header, with every pair still at AA.

## Why

The v1.2.0 site measured AA everywhere and had one hue doing six jobs. In one screenshot of the pane open on a compare, `#b71fb7`/`#e879e8` was: the active sheet, the active level chip, the Official chip, the Clear filters outline, the Chorus Encore button, the open row's 22% wash and its edge, the `here` cell's ring, the pressed Compare button, the sorted header, three kinds of link, the D curve and series A. State, action, link and data were one colour, so the eye could not separate them. `G_SERIES` was `["color_d", "color_nps", "color_vps"]`, so with one chart up blue was Notes and with two it was "chart B's D", one click apart. The canvas painted `RENDER.figure_bg` (`#1E1E1E`, upstream's matplotlib theme) on a `#212529` Bootstrap body, the faint darker box around every graph; that parity was section 06's design when the page still served PNGs, and the PNG is now one social preview. The level badges were `xlsx_format.py`'s pastel fills used as text on dark, four near-whites, with Expert pink an inch from the brand. And `data-bs-theme="dark"` was hard-coded.

## Current state

As landed: `web/static/css/app.css` opens with the two theme blocks and the Bootstrap bridge; every colour rule below them names a role. `boot['render']` carries four numbers (`linewidth`, `grid_alpha`, `fill_curves`, `fill_alpha`) and no colour. `page.THEME_SCRIPT` is in the head of `index.html`, `doc.html` and `404.html`. `static/js/theme.js` is the toggle. `tests/page/theme.js` is the suite; `contrast.js` audits both themes.

## Design

1. **Roles, not colours.** `--fw-bg`, `--fw-bg-raised` (the sticky header, the grip strip, the pick bar), `--fw-bg-hover`, `--fw-border`, `--fw-text`, `--fw-strong`, `--fw-dim`, `--fw-brand` (a fill) and `--fw-brand-text`, `--fw-link`, `--fw-select` (the open row's wash), `--fw-backdrop`, `--fw-curve-d/nps/vps`, `--fw-series-a/b/c`, `--fw-easy/medium/hard/expert`. A rule names the role it needs; the two theme blocks give each role its value. The `-rgb` twins exist only where Bootstrap wants a triplet.
2. **The brand means "on".** Active chips, the pressed Compare, `.btn-primary` and `.btn-outline-primary` (the pane's link buttons, the page's one call to action, and Clear filters, which clears magenta things), the sorted or filtered header, the beta pill, the focus ring, the open row's edge and the `here` cell's ring. Nothing else. The open row's wash is neutral (`--fw-select`, 12% white or 8% black over the ground), as a selection in an editor: the colour is the edge.
3. **Links are the blue.** "How it works", "Request a song pack", "Report this rating", the copies, the about page's links, the Chart column's arrow, the code column on hover, the footer on hover, the document pages' links. `--bs-link-color` is bridged to it, and the five rules that overrode links back to magenta are gone.
4. **Two trios.** `G_SERIES` is `["--fw-series-a", "--fw-series-b", "--fw-series-c"]`: magenta (A is a D line, so it keeps D's colour), cyan, gold. Blue and orange are Notes and Variability and appear only with one chart up; cyan and gold appear only in a compare. The pane, the song grid and the table write a mark as `var(--fw-series-b)`, so the marks follow the theme with no code; only the canvas resolves the values (`gPalette`).
5. **One ground.** The canvas paints `--fw-bg`, the pane card paints nothing, `openPane` no longer sets a background. The grid lines are the text colour at `grid_alpha`; spines and the cursor hairline are `--fw-dim`. Save as PNG exports in the theme the page is in, since that is the picture the visitor is looking at.
6. **Level colours saturated per ground.** The spreadsheet's hue families (green, blue, amber, rose) at values that read as four: dark `#7fd8a3 #8ec0f2 #f4ad52 #f78aa0`, light `#186f42 #1f63a8 #8a5a00 #c02a4c`, all 4.5:1 or better on the ground, the raised ground and the hover row. The grid's level headings carry the same classes.
7. **A tinted neutral, not Bootstrap's grey.** Dark `#1a1920` / `#23222b` / `#2c2b36`, light `#fbfafd` / `#f1eff6` / `#e7e4ee`, a violet cast the brand sits in. Bootstrap's `--bs-body-bg`, `--bs-tertiary-bg`, `--bs-secondary-bg`, `--bs-border-color`, the emphasis, secondary and link colours and `--bs-primary` are bridged to the tokens in one block after both of its theme blocks, so its table, form controls and dropdowns stand on the page's ground; its blue focus glow, checked box and focused search box are overridden to the brand.
8. **Two themes, decided before the first paint.** `page.THEME_SCRIPT`, one inline script in the head of every page before the stylesheets: a stored `fw.theme` of `light` or `dark`, else `prefers-color-scheme`, stamped on `<html>` as `data-bs-theme`. The templates keep `data-bs-theme="dark"` for a visitor with no script. `theme.js` is the header's toggle (a small icon button at the right of the brand row, labelled with the action it offers, so a plain button and not a pressed one), stores the choice, updates `theme-color`, follows the OS live while no choice is stored, and dispatches `fw:theme`, on which the pane redraws. Transitions are off for the frame of the switch (`html.theming`), or Bootstrap's buttons fade a beat behind the body.
9. **The document pages and the 404 stand alone still.** Each declares its own two palettes (the same values) keyed on the same attribute, and carries the same script, so a choice made on the charts page holds on About and on a missing page.
10. **The social preview keeps upstream's theme.** `render.py` and the one PNG publish draws use `config.RENDER_THEMES` as before; the page's colours are the page's. The four numbers that shape the lines stay shared, so the canvas and the PNG draw the same picture in different colours.

Rejected: "themes" plural (skins are maintenance with no reader benefit); a third "auto" state on the button (removing the stored key is the auto state, and a toggle with three states needs a menu); a CSS-only auto theme (Bootstrap defines its dark variables only under the attribute, so an inline script is the only way to have no flash); keeping the canvas on `boot.render` with a second colour set booted per theme (the stylesheet already is that set, and `getComputedStyle` reads it).

## Data and interfaces

- Dark: bg `#1a1920`, raised `#23222b`, hover `#2c2b36`, border `#3b3945`, text `#e4e2ea`, strong `#ffffff`, dim `#a3a1ad`, brand `#b71fb7`, brand-text `#e879e8`, link `#5eaee8`, select `rgba(255,255,255,.12)`, curves `#c93cc9 #3b9ee0 #e58a3c`, series `#c93cc9 #2fc7c7 #e6c03f`, levels as above.
- Light: bg `#fbfafd`, raised `#f1eff6`, hover `#e7e4ee`, border `#d3cfdc`, text `#232030`, strong `#000000`, dim `#5f5b6b`, brand `#b71fb7`, brand-text `#9a189a`, link `#1a67b0`, select `rgba(0,0,0,.08)`, curves `#b71fb7 #1a6fc0 #c85f14`, series `#b71fb7 #0e8a8a #9a7200`.
- Ratios, worst case per role over the three grounds (bg, raised, hover): dark text 10.9, dim 5.5, brand-text 5.5, link 5.8, levels 6.0 or better, dim on the selected row 4.8; curves and series as swatches 3.3 or better on the ground. Light text 12.7, dim 5.2, brand-text 5.6, link 4.6, levels 4.6 or better, dim on the selected row 5.3; swatches 3.3 or better (series B cyan 4.0, series C gold 4.2 on the ground). White on the brand fill 5.4 in both.
- `boot['render']`: `{linewidth, grid_alpha, fill_curves, fill_alpha}` from `plot.resolve_profile()`; `boot.WEB_RENDER_KEYS`.
- `graph.js`: `G_SERIES` (token names), `seriesVar(k)` (`"var(--fw-series-a)"`), `gPalette()` (`{bg, text, dim, d, nps, vps, series[3]}` from the root's computed style); `mountGraph` charts carry no colour, `charts[k]` is series `k`.
- `theme.js`: `currentTheme()`, `setTheme(theme, remember)`, `initTheme()`; `fw.theme` in `localStorage`; the `fw:theme` event with the theme as `detail`.
- `page.THEME_SCRIPT`; the `__THEME__` placeholder in the three templates; `<meta name="theme-color">` in `index.html`.
- `labels.UI`: `theme_to_light`, `theme_to_dark`.

## Files touched

`web/static/css/app.css`, `web/static/index.html`, `web/static/doc.html`, `web/static/404.html`, `web/page.py`, `web/boot.py`, `web/bootstrap.py` (the fallback sheet's literals onto the tokens), `web/static/js/graph.js`, `song.js`, `pane.js`, `main.js`, `theme.js` (new), `functions/labels.py`, `tools/check_site.py` (the about page carries one script now), `tests/test_graph_json.py`, `tests/test_methodology.py`, `tests/pipeline_test.py`, `tests/page/run.py` (the storage seed moves to the top of the head so it precedes the theme script; three scripts in `index.html`), `tests/page/theme.js` (new), `contrast.js`, `graph.js`, `song.js`, `compare.js`, `about.js`, `notfound.js`, `CLAUDE.md`, `README.md`, this file and the index.

## Verification

- `python -m unittest discover -s tests -t .`: `RenderProfileTest` pins the four numbers to `plot.resolve_profile()`, that no colour key reaches the page, and that every `--fw-*` token `graph.js` reads is defined in both theme blocks of `app.css`.
- `tests/pipeline_test.py`: the theme script before the styles in `index.html` (three `<script` tags), one script and only that one on `about.html`, `methodology.html` and `404.html`.
- `tests/page/theme.js` (21 checks, seeded `fw.theme=light`): opens light whatever the OS prefers; the toggle's label; Bootstrap's ground is the page's; the canvas corner pixel is `--fw-bg`; a click switches, stores, announces, relabels, repaints the canvas and `theme-color`; a marked cell's bar is series A's value in each theme; fresh documents in iframes follow the OS with no key stored and the stored choice on `about.html` and `404.html`.
- `tests/page/contrast.js` (137 checks): the whole audit twice, the toggle between; the six swatches, the open row's edge and white on the brand fill at 3:1; every text pair at 4.5:1; both themes reached.
- `graph.js` suite: the card has no background; the canvas is painted on the ground. `song.js` and `compare.js`: marks and swatches compared as computed colours, the swatches written as the tokens.

## Risks and gotchas

- Under `--virtual-time-budget`, CSS transitions do not advance while `setTimeout` does: a computed colour read 200 ms after a theme switch was still the old one on every `.btn`, which is what `html.theming` (transitions off for the switch) fixed, and it is a real fix too.
- `run.py`'s storage seed used to sit at the module tag, after the head; the theme script reads `fw.theme` in the head, so the seed now goes right after `<head>`. `plain.html` clears the store as it loads, so a suite that wants a stored theme in a fresh document loads a document page, not `plain.html`.
- Headless Chrome reports the OS's `prefers-color-scheme` (light on CI's Linux, whatever Windows says on the dev box). No suite assumes a theme: `theme.js` seeds one, `contrast.js` audits both, the rest compare computed values.
- `color-mix()` is used for the filtered header's tint and the primary button's hover; it is in every browser since 2023 and headless Chrome.
- The `-rgb` twins must be literal triplets: a `var()` holding a hex is not a triplet, which is why the theme blocks carry both.

## Out of scope and follow-ups

- The social preview PNG in the page's dark palette: one more entry in `config.RENDER_THEMES` and `mode` set to it would do it, but that file is upstream's and `render.py`'s local renders would follow; left as it is.
- The README screenshots (`fretladder-pane.png`, `fretladder-pane-light.png` on the `screenshots` branch, de406c3) were retaken from `site/Local` at this commit, before the deploy; the live site catches up when the maintainer deploys.
- A high-contrast or reduced-transparency variant: nothing on the page depends on transparency except the open row's wash and the fills under the curves.
