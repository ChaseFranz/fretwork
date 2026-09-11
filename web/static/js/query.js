// Selecting and ordering rows: what the active filters and sort resolve to.
import { RANGE_MIN_DISTINCT, VALUE_ORDER } from "./boot.js";
import { el } from "./dom.js";
import { isMissing, key } from "./format.js";
import { state, cols, idx, rowsAll } from "./state.js";

const SEARCH_COLS = ["Song Title", "Artist", "Charter", "Release", "Code"];

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
  // Number(), not parseFloat(): a date like 2026-09-07 or a code like 12345678XG
  // is text, and parseFloat would read a number off its front.
  return values.sort((a, b) => {
    const x = Number(a), y = Number(b);
    return a !== "" && b !== "" && !isNaN(x) && !isNaN(y) ? x - y : a.localeCompare(b);
  });
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
  if (typeof v !== "number") return false;
  return (filter.lo === null || v >= filter.lo) &&
         (filter.hi === null || v <= filter.hi);
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
