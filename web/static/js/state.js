// All mutable page state, in one object because ES module imports are
// read-only bindings and several of these are reassigned wholesale.
import { DATA, ORDER, HIDDEN_DEFAULT } from "./boot.js";

const STORAGE_KEY = "fw.hidden";
const ORDER_KEY = "fw.order";
const WIDTH_KEY = "fw.widths";

// An absent key means a first visit, which gets the site's defaults; a stored
// empty list means someone deliberately turned every column on.
function loadHidden() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    return new Set(saved === null ? HIDDEN_DEFAULT : JSON.parse(saved));
  } catch (e) { return new Set(HIDDEN_DEFAULT); }
}

function loadOrder() {
  try { return JSON.parse(localStorage.getItem(ORDER_KEY) || "[]"); }
  catch (e) { return []; }
}

function loadWidths() {
  try { return JSON.parse(localStorage.getItem(WIDTH_KEY) || "{}"); }
  catch (e) { return {}; }
}

export const state = {
  sheet: Object.keys(DATA)[0],
  sortCol: "D",
  sortAsc: false,
  filters: {},        // column -> {type:"set", sel:Set} | {type:"range", lo, hi}
  ddCol: null,        // column whose filter dropdown is open
  hidden: loadHidden(),
  order: loadOrder(),   // viewer's own column order; [] means the site default
  widths: loadWidths(), // column -> pixels, only for columns dragged wider or narrower
};

// Remember hidden columns per browser; storage may be unavailable.
export function saveHidden() {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify([...state.hidden])); }
  catch (e) {}
}

export function saveOrder() {
  try { localStorage.setItem(ORDER_KEY, JSON.stringify(state.order)); }
  catch (e) {}
}

export function saveWidths() {
  try { localStorage.setItem(WIDTH_KEY, JSON.stringify(state.widths)); }
  catch (e) {}
}

// Back to the columns, order and widths the site ships with.
export function resetColumns() {
  state.hidden = new Set(HIDDEN_DEFAULT);
  state.order = [];
  state.widths = {};
  saveHidden();
  saveOrder();
  saveWidths();
}

// Leading column showing a row's place in the current view. Synthetic: it has
// no slot in the row arrays, so visible() pairs it with -1.
export const RANK_COL = "Rank";

export const cols = () => DATA[state.sheet].columns;
export const rowsAll = () => DATA[state.sheet].rows;
export const idx = name => cols().indexOf(name);

// Left-to-right column names: whatever the viewer dragged into place first, then
// anything they have not moved, in the site's default order.
export const ordered = () => {
  const all = [RANK_COL, ...cols()];
  const chosen = state.order.filter(c => all.includes(c));
  const rest = [RANK_COL, ...ORDER, ...cols()]
    .filter(c => all.includes(c) && !chosen.includes(c));
  return [...chosen, ...new Set(rest)];
};

// Everything the column chooser lists, in the order it lists them.
export const allCols = ordered;

// [column, index-into-row] for every column still on screen. The index is the
// position in the row arrays, which display order must not disturb; rank has
// no slot there and resolves to -1.
export const visible = () => {
  const columns = cols();
  return ordered().filter(c => !state.hidden.has(c))
    .map(c => [c, columns.indexOf(c)]);
};
