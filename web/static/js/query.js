// Selecting and ordering rows: what the active filters and sort resolve to.
import { MISS_TEXT, RANGE_MIN_DISTINCT, VALUE_ORDER } from "./boot.js";
import { el } from "./dom.js";
import { isMissing, key } from "./format.js";
import { state, cols, idx, rowsAll } from "./state.js";

// Genre stays out: "rock" alone would match a third of the library through it.
const SEARCH_COLS = ["Song Title", "Artist", "Album", "Charter", "Release", "Code"];

function isNumeric(col) {
  const i = idx(col);
  return rowsAll().some(r => typeof r[i] === "number") &&
         rowsAll().every(r => r[i] === null || typeof r[i] === "number");
}

// Where a column's values are declared to have an order of their own, that is
// the order; anything the list does not name falls in after it, alphabetically.
const rank = (order, v) => {
  const at = order.indexOf(v);
  return at < 0 ? order.length : at;
};

// Every distinct value in a column, in the order it should be read.
export function distinct(col) {
  const i = idx(col);
  const values = [...new Set(rowsAll().map(r => key(r[i])))];
  const order = VALUE_ORDER[col];
  if (order)
    return values.sort((a, b) => rank(order, a) - rank(order, b) || a.localeCompare(b));
  // Decided once per column, so the comparator is transitive: a list is numeric
  // only when every value is (the dash for a missing value aside), else it is
  // text in localeCompare order. Number(), not parseFloat(): a date like
  // 2026-09-07 or a code like 12345678XG is text, and parseFloat would read a
  // number off its front; and mixing the two rules per pair would put 999
  // before 1000 before "18 And Life" before 999.
  const isNum = v => v !== "" && !isNaN(Number(v));
  if (values.every(v => v === MISS_TEXT || isNum(v)))
    return values.sort((a, b) => (a === MISS_TEXT) - (b === MISS_TEXT) || Number(a) - Number(b));
  return values.sort((a, b) => a.localeCompare(b));
}

// A min/max box suits a numeric column with too many values to list.
export const useRange = col =>
  isNumeric(col) && distinct(col).length > RANGE_MIN_DISTINCT;

function matchesSearch(row, columns) {
  const q = el("q").value.trim().toLowerCase();
  if (!q) return true;
  return SEARCH_COLS.map(n => columns.indexOf(n)).filter(i => i >= 0)
    .some(i => String(row[i] ?? "").toLowerCase().includes(q));
}

function matchesFilter(row, columns, col, filter) {
  const i = columns.indexOf(col);
  if (i < 0) return true;
  const v = row[i];
  if (filter.type === "set") return filter.sel.has(key(v));
  if (typeof v !== "number" || isMissing(col, v)) return false;   // a sentinel is not in any range
  return (filter.lo === null || v >= filter.lo) &&
         (filter.hi === null || v <= filter.hi);
}

// The filters after a sheet switch: they carry over (a level chosen on
// Guitar is still the level wanted on Bass, and the search and the sort carry
// too), except one that could match nothing here, which would leave an empty
// table with no chip or caret saying why: a column the sheet lacks, or a set
// filter none of whose values the sheet has (a Part of Lead on Bass). A range
// is kept as set. Called once the sheet's rows are here.
export function carryFilters() {
  for (const [col, f] of Object.entries(state.filters)) {
    if (idx(col) < 0) { delete state.filters[col]; continue; }
    if (f.type === "set" && !distinct(col).some(v => f.sel.has(v))) delete state.filters[col];
  }
}

// Rows passing the search and every filter except exceptCol, so a dropdown
// can count values in the context of the other active filters.
export function passing(exceptCol) {
  const columns = cols();
  return rowsAll().filter(row =>
    matchesSearch(row, columns) &&
    Object.entries(state.filters).every(([col, f]) =>
      col === exceptCol || matchesFilter(row, columns, col, f)));
}

// Missing values sort last in both directions.
export function compare(a, b) {
  const am = isMissing(state.sortCol, a), bm = isMissing(state.sortCol, b);
  if (am || bm) return am && bm ? 0 : (am ? 1 : -1);
  const order = VALUE_ORDER[state.sortCol];
  if (order) {
    const d = rank(order, key(a)) - rank(order, key(b));
    return state.sortAsc ? d : -d;
  }
  if (typeof a === "number" && typeof b === "number")
    return state.sortAsc ? a - b : b - a;
  return state.sortAsc
    ? String(a).localeCompare(String(b))
    : String(b).localeCompare(String(a));
}
