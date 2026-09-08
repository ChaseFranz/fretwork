// One repaint: filter, sort, render, then refresh the footer and level chips.
import { LEVELS, UI } from "./boot.js";
import { chips } from "./chips.js";
import { el } from "./dom.js";
import { t } from "./format.js";
import { headerCell, bodyRow, emptyRow } from "./markup.js";
import { passing, compare } from "./query.js";
import { state, cols, idx, rowsAll, visible } from "./state.js";
import { writeUrl } from "./url.js";
import { applyWidths } from "./widths.js";

function paintFooter(shown, total) {
  el("count").textContent = t("count", { shown: shown, total: total });
  const n = Object.keys(state.filters).length;
  const clear = el("clear");
  clear.textContent = n === 1 ? UI.clear_one : t("clear_many", { n: n });
  clear.classList.toggle("d-none", n === 0);
}

// The level chips are a shortcut into the Level column filter, so they read
// their active state back out of it. They stack: a lit chip is a level the table
// is showing, and clicking one adds or removes just that level. With no filter
// every level is on screen, so every chip is lit - which is also what makes
// "everything except Easy" a single click.
function paintLevelChips() {
  const f = state.filters["Level"];
  const on = f && f.type === "set" ? f.sel : new Set(LEVELS);
  chips("levels", LEVELS, on, v => {
    const next = new Set(on);
    if (next.has(v)) next.delete(v); else next.add(v);
    if (next.size === 0 || next.size === LEVELS.length) delete state.filters["Level"];
    else state.filters["Level"] = { type: "set", sel: next };
    draw();
  });
}

// Official is a chip rather than a column: it is one bit, and it is the cut
// people want most. Same shortcut-into-a-column-filter shape as the levels.
function paintOfficialChips() {
  if (idx("Official") < 0) { el("official").innerHTML = ""; return; }
  const f = state.filters["Official"];
  const on = f && f.type === "set" && f.sel.size === 1 ? [...f.sel][0] : null;
  const names = [UI.official_chip, UI.custom_chip];
  chips("official", names, on === null ? null : names[on === "true" ? 0 : 1], v => {
    const want = v === UI.official_chip ? "true" : "false";
    if (on === want) delete state.filters["Official"];
    else state.filters["Official"] = { type: "set", sel: new Set([want]) };
    draw();
  });
}

export function draw() {
  const vis = visible();
  const sortIdx = idx(state.sortCol);
  const rows = passing(null);
  if (sortIdx >= 0) rows.sort((a, b) => compare(a[sortIdx], b[sortIdx]));

  // Sorting from the keyboard rewrites this row, which would drop focus back to
  // the top of the page, so note where it was and put it back afterwards.
  const held = document.activeElement;
  const heldTh = held && held.closest ? held.closest("#head th") : null;
  const heldFor = heldTh ? [heldTh.dataset.c, held.dataset.sort ? "sort" : "flt"] : null;

  el("head").innerHTML = vis.map(([c]) => headerCell(c, {
    sorted: c === state.sortCol,
    ascending: state.sortAsc,
    filtered: Boolean(state.filters[c]),
    expanded: c === state.ddCol,
  })).join("");
  if (heldFor) {
    const back = el("head").querySelector(
      '[data-' + heldFor[1] + '="' + CSS.escape(heldFor[0]) + '"]');
    if (back) back.focus();
  }

  const codeIdx = cols().indexOf("Code");
  el("body").innerHTML = rows.length
    ? rows.map((r, n) => bodyRow(r, vis, r[codeIdx], n + 1)).join("")
    : emptyRow(vis.length);

  // One tab stop for the whole table; the arrow keys move within it.
  const first = el("body").querySelector("tr[data-code]");
  if (first) first.tabIndex = 0;

  applyWidths();
  writeUrl();
  paintFooter(rows.length, rowsAll().length);
  paintLevelChips();
  paintOfficialChips();
}
