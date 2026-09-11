// The one document-level click handler, and the page's keyboard map. Order is
// behaviour: each branch returns so a more specific target wins over the row
// click beneath it.
import { DATA } from "./boot.js";
import { chips } from "./chips.js";
import { el } from "./dom.js";
import { t } from "./format.js";
import { openDD, closeDD } from "./dropdown.js";
import { toggleCD, closeCD } from "./chooser.js";
import { openGraph, closeGraph, graphIsOpen, openAbout, closeAbout, aboutIsOpen,
         toast } from "./overlay.js";
import { state, idx } from "./state.js";
import { draw } from "./table.js";

function sortBy(col) {
  if (col === state.sortCol) state.sortAsc = !state.sortAsc;
  else { state.sortCol = col; state.sortAsc = false; }
  draw();
}

function copyCode(event, cell) {
  event.stopPropagation();
  navigator.clipboard?.writeText(cell.dataset.copy);
  toast(t("copied", { code: cell.dataset.copy }));
}

function onClick(e) {
  if (e.target.closest("#dd") || e.target.closest("#cd")) return;

  if (e.target.closest("#how")) { closeDD(); closeCD(); openAbout(); return; }
  if (aboutIsOpen()) {
    if (!e.target.closest(".mcard") || e.target.dataset.act === "close") closeAbout();
    return;
  }

  if (e.target.closest("#cols")) { closeDD(); toggleCD(el("cols")); return; }
  closeCD();

  const flt = e.target.closest("[data-flt]");
  if (flt) {
    const col = flt.dataset.flt;
    if (state.ddCol === col) closeDD(); else openDD(col, flt.closest("th"));
    return;
  }
  closeDD();

  const label = e.target.closest("[data-sort]");
  if (label) { sortBy(label.dataset.sort); return; }

  const pip = e.target.closest("[data-copy]");
  if (pip) { copyCode(e, pip); return; }

  const row = e.target.closest("tbody tr[data-code]");
  if (row) { holdRow(row); openGraph(row.dataset.code); return; }

  if (e.target.closest("#modal") && !e.target.closest(".mhead a")) closeGraph();
}

// The table is one tab stop with the arrows moving inside it, rather than 875
// of them: a roving tabindex, so Tab still reaches the footer in one press.
const STEP = { ArrowDown: 1, ArrowUp: -1, PageDown: 12, PageUp: -12 };
const ENDS = { Home: -Infinity, End: Infinity };

function holdRow(row) {
  const had = el("body").querySelector('tr[tabindex="0"]');
  if (had) had.tabIndex = -1;
  row.tabIndex = 0;
}

function moveTo(row, delta) {
  const rows = [...el("body").querySelectorAll("tr[data-code]")];
  const to = rows[Math.max(0, Math.min(rows.length - 1, rows.indexOf(row) + delta))];
  if (!to || to === row) return;
  holdRow(to);
  to.focus();
}

// True when the key belonged to the table, so the caller stops there.
function onGridKey(e) {
  const row = e.target.closest ? e.target.closest("tbody tr[data-code]") : null;
  if (!row) return false;
  if (e.key in STEP) { e.preventDefault(); moveTo(row, STEP[e.key]); return true; }
  if (e.key in ENDS) { e.preventDefault(); moveTo(row, ENDS[e.key]); return true; }
  if (e.key === "Enter" || e.key === " ") {
    e.preventDefault();
    openGraph(row.dataset.code);
    return true;
  }
  return false;
}

function onKeydown(e) {
  // Nothing inside the graph is focusable, so Tab would leave it open behind you.
  if ((graphIsOpen() || aboutIsOpen()) && e.key === "Tab") { e.preventDefault(); return; }
  if (e.key === "Escape") {
    closeDD();
    closeCD();
    closeGraph();
    closeAbout();
    return;
  }
  onGridKey(e);
}

// Repaint the sheet chips too, since switching sheets re-enters here.
export function render() {
  chips("sheets", Object.keys(DATA), state.sheet, v => {
    state.sheet = v;
    state.filters = {};
    if (idx(state.sortCol) < 0) state.sortCol = "D";
    render();
  });
  draw();
}

export function initRouter() {
  document.addEventListener("click", onClick);
  document.addEventListener("keydown", onKeydown);
  el("q").addEventListener("input", draw);
  el("clear").addEventListener("click", () => { state.filters = {}; draw(); });
}
