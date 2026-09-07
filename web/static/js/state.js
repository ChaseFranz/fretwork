// All mutable page state, in one object because ES module imports are
// read-only bindings and several of these are reassigned wholesale.
import { DATA, ORDER } from "./boot.js";

const STORAGE_KEY = "fw.hidden";

function loadHidden() {
  try { return new Set(JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]")); }
  catch (e) { return new Set(); }
}

export const state = {
  sheet: Object.keys(DATA)[0],
  sortCol: "D",
  sortAsc: false,
  filters: {},        // column -> {type:"set", sel:Set} | {type:"range", lo, hi}
  ddCol: null,        // column whose filter dropdown is open
  hidden: loadHidden(),
};

// Remember hidden columns per browser; storage may be unavailable.
export function saveHidden() {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify([...state.hidden])); }
  catch (e) {}
}

// Leading column showing a row's place in the current view. Synthetic: it has
// no slot in the row arrays, so visible() pairs it with -1.
export const RANK_COL = "Rank";

export const cols = () => DATA[state.sheet].columns;
export const rowsAll = () => DATA[state.sheet].rows;
export const idx = name => cols().indexOf(name);

// Column names in display order; unlisted columns keep their position, at the end.
export const ordered = () => {
  const columns = cols();
  return [...ORDER.filter(c => columns.includes(c)),
          ...columns.filter(c => !ORDER.includes(c))];
};

// Everything the column chooser can toggle: the data columns plus rank.
export const allCols = () => [RANK_COL, ...ordered()];

// [column, index-into-row] for every column still on screen. The index is the
// position in the row arrays, which display order must not disturb.
export const visible = () => {
  const columns = cols();
  const shown = ordered().map(c => [c, columns.indexOf(c)])
    .filter(([c]) => !state.hidden.has(c));
  return state.hidden.has(RANK_COL) ? shown : [[RANK_COL, -1], ...shown];
};
