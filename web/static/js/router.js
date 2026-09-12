// The one document-level click handler, and the page's keyboard map. Order is
// behaviour: each branch returns so a more specific target wins over the row
// click beneath it.
import { SHEETS } from "./boot.js";
import { loadSheet } from "./load.js";
import { chips } from "./chips.js";
import { el } from "./dom.js";
import { t } from "./format.js";
import { openDD, closeDD } from "./dropdown.js";
import { toggleCD, closeCD } from "./chooser.js";
import { openAbout, closeAbout, aboutIsOpen, toast } from "./overlay.js";
import { openPane, closePane, paneIsOpen, addCompare, removeCompare, stopPicking } from "./pane.js";
import { carryFilters } from "./query.js";
import { state, idx } from "./state.js";
import { draw, holdRow, revealIndex, viewIndexOf } from "./table.js";

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

// A click that ends a drag-select of a row's text is not a choice.
const selecting = row => {
  const s = getSelection();
  return s && !s.isCollapsed && row.contains(s.anchorNode);
};

function onClick(e) {
  if (e.target.closest("#dd") || e.target.closest("#cd")) return;

  if (e.target.closest("#how")) { closeDD(); closeCD(); openAbout(); return; }
  // the explainer is the one dialog left: it covers everything while it is open
  if (aboutIsOpen()) {
    if (!e.target.closest(".mcard") || e.target.dataset.act === "close") closeAbout();
    return;
  }

  // the pane's links to other charts: a grid cell, a copy's link (a real href,
  // for a new tab), an instrument's compare button; the pane's own controls
  // are wired in pane.js
  const cmp = e.target.closest("#pane [data-cmp]");
  if (cmp) {
    const codes = cmp.dataset.cmp.split(",").filter(Boolean);
    if (!codes.length) return;
    // pressed: its levels are up, so take them down to one chart, the primary
    // when it is one of them
    if (cmp.getAttribute("aria-pressed") === "true") openPane(codes.includes(state.graph) ? state.graph : codes[0], [], { follow: true });
    else openPane(codes[0], codes.slice(1), { follow: true });
    return;
  }
  const cellBtn = e.target.closest("#pane .cell[data-code]");
  if (cellBtn) { chooseCell(cellBtn.dataset.code); return; }
  const alt = e.target.closest("#pane .copies a[data-code]");
  if (alt) { e.preventDefault(); openPane(alt.dataset.code, []); return; }
  if (e.target.closest("#pane") || e.target.closest("#pick")) return;

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

  // a link column's arrow: the browser follows it, the row is not chosen
  if (e.target.closest("tbody a.ext")) return;

  const row = e.target.closest("tbody tr[data-code]");
  if (row && !selecting(row)) { holdRow(row); chooseRow(row.dataset.code); return; }
}

// A grid cell: with one chart up it opens its chart; in compare mode it
// toggles its chart on or off the graph (the primary off promotes the next).
function chooseCell(code) {
  const comparing = state.compare.length > 0;
  if (!comparing) { if (code !== state.graph) openPane(code, [], { follow: true }); return; }
  if (code === state.graph || state.compare.includes(code)) removeCompare(code);
  else addCompare(code);
}

// A row shows its one chart: a comparison up goes, since comparisons are
// built in the pane (a grid cell, Compare all levels, Compare with a row) and
// the row is always the chart on the graph and in the song grid. The open
// row clicked again drops a comparison to that chart alone, then closes the
// pane. While a comparison is being picked the row joins the graph instead.
function chooseRow(code) {
  if (state.picking) { addCompare(code); stopPicking(); return; }
  if (paneIsOpen() && state.graph === code) {
    if (state.compare.length) openPane(code, [], { follow: true }); else closePane();
    return;
  }
  openPane(code, []);
}

// Tab stays inside the explainer: wrap from its last focusable to its first
// and back. With nothing focusable it is swallowed, so focus cannot land on
// the table behind the backdrop.
const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])';

function trapTab(dialog, e) {
  const items = [...dialog.querySelectorAll(FOCUSABLE)].filter(x => x.offsetParent !== null);
  if (!items.length) { e.preventDefault(); return; }
  const i = items.indexOf(document.activeElement);
  const to = e.shiftKey ? (i <= 0 ? items[items.length - 1] : items[i - 1])
                        : (i < 0 || i === items.length - 1 ? items[0] : items[i + 1]);
  e.preventDefault();
  to.focus();
}

const STEP = { ArrowDown: 1, ArrowUp: -1, PageDown: 12, PageUp: -12 };
const ENDS = { Home: -Infinity, End: Infinity };
const FOLLOW_MS = 160;   // the graph follows the arrow keys once they pause, not per press
let follow = null;

// The arrows walk the view, not the DOM (section 17): the target row is
// painted on demand, since the DOM holds a window of the view.
function moveTo(row, delta) {
  const i = viewIndexOf(row.dataset.code);
  if (i < 0) return;
  const j = Math.max(0, Math.min(state.view.length - 1, i + delta));
  if (j === i) return;
  const to = revealIndex(j);
  if (!to || to === row) return;
  holdRow(to);
  to.focus({ preventScroll: true });
  // with the pane open, the selection is the focused row: the graph follows,
  // one chart, as a row click would show
  if (paneIsOpen() && !state.picking) {
    clearTimeout(follow);
    follow = setTimeout(() => { if (paneIsOpen() && !state.picking) openPane(to.dataset.code, [], { follow: true }); }, FOLLOW_MS);
  }
}

// True when the key belonged to the table, so the caller stops there.
function onGridKey(e) {
  const row = e.target.closest ? e.target.closest("tbody tr[data-code]") : null;
  if (!row) return false;
  if (e.key in STEP) { e.preventDefault(); moveTo(row, STEP[e.key]); return true; }
  if (e.key in ENDS) { e.preventDefault(); moveTo(row, ENDS[e.key]); return true; }
  if (e.key === "Enter" || e.key === " ") {
    e.preventDefault();
    chooseRow(row.dataset.code);
    return true;
  }
  return false;
}

// Escape closes one thing at a time: the explainer, a dropdown, the picking
// mode, then the pane, which hands focus back to its row.
function onKeydown(e) {
  if (e.key === "Tab" && aboutIsOpen()) { trapTab(el("about"), e); return; }
  if (e.key === "Escape") {
    if (aboutIsOpen()) { closeAbout(); return; }
    const had = state.ddCol !== null || el("cd").classList.contains("show");
    closeDD();
    closeCD();
    if (had) return;
    if (state.picking) { stopPicking(); return; }
    if (paneIsOpen()) closePane();
    return;
  }
  onGridKey(e);
}

// Repaint the sheet chips too, since switching sheets re-enters here. The
// filters, the search and the sort carry across the switch; a filter that
// could match nothing on the new sheet is dropped once its rows are here
// (carryFilters), and a sort column it lacks falls back to D.
export function render() {
  chips("sheets", Object.keys(SHEETS), state.sheet, v => {
    state.sheet = v;
    state.loadError = null;
    if (idx(state.sortCol) < 0) state.sortCol = "D";
    render();                                   // the loading row, at once
    loadSheet(v).then(() => { carryFilters(); render(); }, () => { state.loadError = true; render(); });
  });
  draw();
}

export function initRouter() {
  document.addEventListener("click", onClick);
  document.addEventListener("keydown", onKeydown);
  el("q").addEventListener("input", draw);
  el("clear").addEventListener("click", () => { state.filters = {}; draw(); });
}
