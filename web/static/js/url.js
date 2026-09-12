// The shareable half of the page state, mirrored into the query string so a link
// carries what the sender was looking at. Column visibility, order and widths are
// per-viewer preferences and stay in localStorage: they belong to the reader, not
// to the link.
import { SHEETS, SHEET_OF_CODE } from "./boot.js";
import { state } from "./state.js";

const SET = "f.";     // f.Level=Expert,Hard
const RANGE = "r.";   // r.D=120:400

let pending = null;

function params() {
  const out = new URLSearchParams();
  const sheets = Object.keys(SHEETS);
  if (state.sheet !== sheets[0]) out.set("sheet", state.sheet);
  const q = document.getElementById("q").value.trim();
  if (q) out.set("q", q);
  if (state.sortCol !== "D" || state.sortAsc) {
    out.set("sort", state.sortCol);
    out.set("dir", state.sortAsc ? "asc" : "desc");
  }
  for (const [col, f] of Object.entries(state.filters)) {
    if (f.type === "set") out.set(SET + col, [...f.sel].join(","));
    else out.set(RANGE + col, (f.lo ?? "") + ":" + (f.hi ?? ""));
  }
  if (state.graph) {
    out.set("code", state.graph);
    if (state.compare.length) out.set("vs", state.compare.join(","));
  }
  return out;
}

// Every repaint calls this, including one per keystroke in the search box, so it
// is coalesced: replaceState is rate-limited in some browsers, and a link that
// updates a frame late is indistinguishable from one that updates instantly.
export function writeUrl() {
  clearTimeout(pending);
  pending = setTimeout(() => {
    const query = params().toString();
    history.replaceState(null, "", query ? "?" + query : location.pathname);
  }, 250);
}

// A link's own state replaces the site's opening filters rather than adding to
// them, so "everything, unfiltered" is a shareable view too. Returns what the
// link asked to open: {code, song}, either null; a malformed song key is null.
// ?song= is read and never written: the page resolves it to the song's primary
// chart and the URL then carries that code.
export function readUrl() {
  const got = new URLSearchParams(location.search);
  if (!got.toString()) return { code: null, song: null };

  const sheet = got.get("sheet");
  if (sheet && SHEETS[sheet]) state.sheet = sheet;
  // a shared code without a sheet: its instrument letter says which sheet it is on
  const code = got.get("code");
  if (code && !sheet) {
    const guess = SHEET_OF_CODE[code.slice(-1).toUpperCase()];
    if (guess && SHEETS[guess]) state.sheet = guess;
  }
  // the charts drawn beside it: at most two, well-formed, not the code itself
  const vs = got.get("vs");
  if (code && vs) {
    state.compare = [...new Set(vs.split(",").filter(c => /^[A-Za-z0-9]{10}$/.test(c) && c !== code))].slice(0, 2);
  }
  const q = got.get("q");
  if (q) document.getElementById("q").value = q;
  const sort = got.get("sort");
  if (sort) {
    state.sortCol = sort;
    state.sortAsc = got.get("dir") === "asc";
  }

  const named = [...got.keys()].some(k => k.startsWith(SET) || k.startsWith(RANGE));
  if (named) state.filters = {};
  for (const [key, value] of got.entries()) {
    if (key.startsWith(SET))
      state.filters[key.slice(SET.length)] = { type: "set", sel: new Set(value.split(",")) };
    else if (key.startsWith(RANGE)) {
      const [lo, hi] = value.split(":");
      state.filters[key.slice(RANGE.length)] = {
        type: "range", lo: lo === "" ? null : +lo, hi: hi === "" ? null : +hi };
    }
  }
  const song = got.get("song");
  return { code: code || null, song: song && /^[0-9a-f]{12}$/.test(song) ? song : null };
}
