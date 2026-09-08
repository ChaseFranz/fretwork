// Turning a stored value into the text a person reads.
import { LABELS, UI, MISSING, MISS_TEXT } from "./boot.js";
import { state, idx, rowsAll } from "./state.js";

// Display label for a column key; unknown keys fall back to the key itself.
export const lab = c => LABELS[c] || c;

// UI string with {placeholders} filled from vars.
export const t = (k, vars) => (UI[k] || k)
  .replace(/\{(\w+)\}/g, (_, name) => vars && name in vars ? vars[name] : "");

// Seconds as m:ss.
export const mmss = secs => {
  const whole = Math.max(0, Math.round(secs));
  return Math.floor(whole / 60) + ":" + String(whole % 60).padStart(2, "0");
};

// Stable string form of a cell value, used as a filter key.
export const key = v => v === null ? MISS_TEXT : String(v);

// True for null, or for a column's own "unrated" sentinel.
export const isMissing = (col, v) =>
  v === null || (MISSING[col] || []).indexOf(v) >= 0;

// How many decimals a numeric column prints: two if any value in it has a
// fraction, none otherwise. Deciding per column rather than per value is what
// keeps the decimal points in a line - D holding one exact 700 should still
// read 700.00 beside 662.50. Measured once per sheet and remembered.
const places = new Map();

export function decimals(col) {
  const memo = state.sheet + "\u0000" + col;
  if (!places.has(memo)) {
    const i = idx(col);
    places.set(memo, rowsAll().some(
      r => typeof r[i] === "number" && !Number.isInteger(r[i])) ? 2 : 0);
  }
  return places.get(memo);
}
