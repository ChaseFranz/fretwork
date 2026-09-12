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
import { openGraph, closeGraph, graphIsOpen, openAbout, closeAbout, aboutIsOpen,
         toast, addCompare, stopPicking } from "./overlay.js";
import { openSong, closeSong, songIsOpen } from "./song.js";
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

  // the song panel's compare button: an instrument's levels on one graph
  const cmp = e.target.closest("[data-cmp]");
  if (cmp) {
    const codes = cmp.dataset.cmp.split(",").filter(Boolean);
    if (codes.length) openGraph(codes[0], codes.slice(1));
    return;
  }
  // the song panel, from a graph heading or a title pip; the href is real, so no navigation
  const song = e.target.closest("[data-song]");
  if (song) {
    e.preventDefault();
    const from = graphIsOpen() ? state.graph : (song.closest("tr[data-code]") || {}).dataset?.code;
    if (graphIsOpen()) closeGraph();
    openSong(song.dataset.song, { from });
    return;
  }
  // the dialogs, topmost first: the graph covers everything when it is open
  if (graphIsOpen()) {
    // a copy's link swaps the graph in place; the href is real for a new tab
    const alt = e.target.closest("#modal .mhead a[data-code]");
    if (alt) { e.preventDefault(); openGraph(alt.dataset.code); return; }
    // the card has controls, so only the backdrop itself and the close button close
    if (e.target.closest('#modal [data-act="close"]') || e.target === el("modal")) closeGraph();
    return;
  }
  if (songIsOpen()) {
    const cell = e.target.closest("#song .cell[data-code]");
    if (cell) { openGraph(cell.dataset.code); return; }
    if (e.target.closest('#song [data-act="close"]') || !e.target.closest("#song .mcard")) closeSong();
    return;
  }
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
  if (row) { holdRow(row); chooseRow(row.dataset.code); return; }

}

// A row opens its graph, or, while a comparison is being picked, joins the
// graph that is waiting and brings it back.
function chooseRow(code) {
  if (state.picking) { if (addCompare(code)) stopPicking(false); else stopPicking(true); return; }
  openGraph(code);
}

// Tab stays inside the open dialog: wrap from its last focusable to its first
// and back. With nothing focusable (a graph still rendering) it is swallowed,
// as before, so focus cannot land on the table behind the backdrop.
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
    chooseRow(row.dataset.code);
    return true;
  }
  return false;
}

// Tab stays in the topmost dialog; Escape closes one layer at a time, so a
// graph over the song panel takes two presses back to the table.
function onKeydown(e) {
  if (e.key === "Tab") {
    if (graphIsOpen()) { trapTab(el("modal"), e); return; }
    if (songIsOpen()) { trapTab(el("song"), e); return; }
    if (aboutIsOpen()) { trapTab(el("about"), e); return; }
  }
  if (e.key === "Escape") {
    closeDD();
    closeCD();
    if (state.picking) { stopPicking(true); return; }
    if (graphIsOpen()) closeGraph();
    else if (songIsOpen()) closeSong();
    else closeAbout();
    return;
  }
  onGridKey(e);
}

// Repaint the sheet chips too, since switching sheets re-enters here.
export function render() {
  chips("sheets", Object.keys(SHEETS), state.sheet, v => {
    state.sheet = v;
    state.filters = {};
    state.loadError = null;
    if (idx(state.sortCol) < 0) state.sortCol = "D";
    render();                                   // the loading row, at once
    loadSheet(v).then(render, () => { state.loadError = true; render(); });
  });
  draw();
}

export function initRouter() {
  document.addEventListener("click", onClick);
  document.addEventListener("keydown", onKeydown);
  el("q").addEventListener("input", draw);
  el("clear").addEventListener("click", () => { state.filters = {}; draw(); });
}
