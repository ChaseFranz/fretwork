// One repaint: filter, sort, then paint the rows on screen, and refresh the
// footer and level chips. The DOM holds a window of the view, not the view
// (section 17): the rows around the scroll position, OVERSCAN rows either side,
// between two spacer rows standing for the rest at the measured average row
// height, so the table costs the same to paint at 6,000 rows as at 60,000.
// compute() is the view, paint() the window; draw() is both, and every caller
// that changed what the table shows calls draw() as before.
import { LEVELS, SHEETS, UI } from "./boot.js";
import { chips } from "./chips.js";
import { el, esc } from "./dom.js";
import { t } from "./format.js";
import { headerCell, bodyRow, emptyRow, loadingRow, padRow } from "./markup.js";
import { passing, compare } from "./query.js";
import { onGraph } from "./song.js";
import { state, cols, idx, rowsAll, visible, loaded } from "./state.js";
import { refreshFades } from "./scroll.js";
import { writeUrl } from "./url.js";
import { applyWidths } from "./widths.js";

const OVERSCAN = 40;      // rows painted beyond each edge of the screen
const ROW_SEED = 44;      // px, the average row height until one is measured
const wrap = () => document.querySelector(".fw-wrap");

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

// The table is one tab stop with the arrows moving inside it, rather than
// thousands of them: a roving tabindex, so Tab still reaches the pane and the
// footer in one press each.
export function holdRow(row) {
  const had = el("body").querySelector('tr[tabindex="0"]');
  if (had && had !== row) had.tabIndex = -1;
  row.tabIndex = 0;
}

// The rows the graph holds, marked wherever they are on screen: the open
// chart's row (.sel: the tint, aria-current, and the table's tab stop) and,
// in compare mode, every chart's row with its series colour on the left edge
// and its legend letter after the first cell's text, so the table mirrors the
// legend as the song grid does. Drawn after every repaint and by the pane
// after every swap, so the marks follow a row through a sort or a filter.
// Returns the open chart's row, or null when it is not on screen.
export function markRows() {
  const body = el("body");
  for (const tr of body.querySelectorAll("tr.sel, tr.on")) {
    tr.classList.remove("sel", "on");
    tr.removeAttribute("aria-current");
    tr.style.removeProperty("--sc");
    tr.querySelectorAll(".sl").forEach(i => i.remove());
  }
  const { codes, mark } = onGraph();
  let primary = null;
  codes.forEach((code, k) => {
    const tr = body.querySelector('tr[data-code="' + CSS.escape(code) + '"]');
    if (!tr) return;
    if (k === 0) { tr.classList.add("sel"); tr.setAttribute("aria-current", "true"); primary = tr; }
    const m = mark.get(code);
    if (m) {
      tr.classList.add("on");
      tr.style.setProperty("--sc", m.colour);
      if (tr.firstElementChild) tr.firstElementChild.insertAdjacentHTML("beforeend", '<i class="sl">' + esc(m.letter) + "</i>");
    }
  });
  if (primary) holdRow(primary);
  return primary;
}

// The view: the rows passing the search and filters, in sort order, into
// state.view; the header; then the window.
export function compute() {
  const vis = visible();
  const sortIdx = idx(state.sortCol);
  const was = state.graph ? viewIndexOf(state.graph) : -1;
  const rows = passing(null);
  if (sortIdx >= 0) rows.sort((a, b) => compare(a[sortIdx], b[sortIdx]));
  state.view = rows;

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
  paint();
  // the open chart's row stays in sight through a sort or a filter that moved
  // it (a sort takes it deep into a long view; a cleared search brings it
  // back): revealed when its place in the view changed, never for a repaint
  // that left the view alone, such as a column shown or hidden
  const now = state.graph ? viewIndexOf(state.graph) : -1;
  if (now >= 0 && now !== was) revealIndex(now);
  applyWidths();
  writeUrl();
}

// Where the window should be: the rows whose estimated top is within
// OVERSCAN rows of the screen, for the scroller's position, or around a row
// index that must be painted (revealIndex); avg is the estimate the current
// spacers stand at, the only one that maps this scroll position to a row. The
// header is sticky inside the scroller, so the first row's top is the header's
// height.
function wanted(avg, around) {
  const w = wrap(), n = state.view.length;
  const screen = Math.ceil(w.clientHeight / avg);
  let first;
  if (around === undefined) first = Math.floor(Math.max(0, w.scrollTop - el("head").offsetHeight) / avg);
  else first = around - Math.floor(screen / 2);
  first = Math.max(0, Math.min(first, n - screen));
  return { from: Math.max(0, first - OVERSCAN), to: Math.max(0, Math.min(n, first + screen + OVERSCAN)),
           first, last: Math.min(n, first + screen) };
}

// The window: the rows from `from` to `to` between two spacers, the rank
// numbers their place in the view. The scroll position is read against the
// estimate the current spacers stand at (state.window.avg), the new spacers
// are built at the one the previous paint measured (state.window.next), and
// the paint records that as the new avg. The two differ, so the scroller is
// put right afterwards: the row that was under the screen's top stays there
// when it is still painted, and otherwise (a long jump, when nothing painted
// before is painted now) the first row the scroll position asked for is put
// at the top, so a changed estimate never moves the page under the visitor
// and a jump to the end lands on the last rows. Focus and the tab stop
// survive when their row is still painted; the marks are redrawn, since a
// marked row may have just entered.
export function paint(around, fromScroll = false) {
  const vis = visible();
  const body = el("body"), w = wrap();
  const pending = !loaded(state.sheet);
  const view = state.view;
  if (pending || !view.length) {
    body.innerHTML = pending ? loadingRow(vis.length, state.loadError) : emptyRow(vis.length);
    state.window = { from: 0, to: 0, avg: state.window.avg, next: state.window.next };
    return;
  }
  const mapAvg = state.window.avg || ROW_SEED;              // what the scroller's position means today
  const avg = state.window.next || mapAvg;                  // what the new spacers stand at
  const { from, to, first: asked } = wanted(mapAvg, around);
  const rowOf = code => code ? body.querySelector('tr[data-code="' + CSS.escape(code) + '"]') : null;
  const active = document.activeElement;
  const focused = active && active.closest && body.contains(active) ? active.closest("tr[data-code]") : null;
  const focusedCode = focused ? focused.dataset.code : null;
  const stop = body.querySelector('tr[tabindex="0"]');
  const stopCode = stop ? stop.dataset.code : null;
  // the row under the screen's top, and where it sits, to put it back after a
  // scroll-driven paint; at the very top of the scroller there is nothing to
  // keep in place, and holding the first painted row where a spacer had put it
  // would scroll the visitor off the first rows, so the top stays the top. A
  // sort or a filter keeps the pixel position instead: its rows are new, and
  // following one that happens to be painted again would jump the page
  const screenTop = w.getBoundingClientRect().top + el("head").offsetHeight;
  let anchor = null;
  if (fromScroll && w.scrollTop > el("head").offsetHeight) {
    for (const tr of body.querySelectorAll("tr[data-code]")) {
      const box = tr.getBoundingClientRect();
      if (box.bottom > screenTop) { anchor = { code: tr.dataset.code, delta: box.top - screenTop }; break; }
    }
  }

  // The hover text says where the chart sits before the click that opens it.
  const codeIdx = cols().indexOf("Code"), keyIdx = cols().indexOf("SongKey");
  const pctIdx = cols().indexOf("Pct"), levelIdx = cols().indexOf("Level");
  const tipFor = r => pctIdx >= 0 && levelIdx >= 0 && typeof r[pctIdx] === "number"
    ? t("pct_of", { pct: r[pctIdx], level: r[levelIdx], sheet: state.sheet }) + "\n" + UI.row_tip
    : UI.row_tip;
  let html = from > 0 ? padRow(vis.length, from, from * avg) : "";
  for (let i = from; i < to; i++) {
    const r = view[i];
    html += bodyRow(r, vis, r[codeIdx], i + 1, tipFor(r), keyIdx < 0 ? undefined : r[keyIdx]);
  }
  if (to < view.length) html += padRow(vis.length, view.length - to, (view.length - to) * avg);
  body.innerHTML = html;
  state.window = { from, to, avg, next: state.window.next };

  // measured: the painted rows' height over their number, for the next paint
  const painted = body.querySelectorAll("tr[data-code]");
  if (painted.length) {
    const first = painted[0].getBoundingClientRect().top, last = painted[painted.length - 1].getBoundingClientRect().bottom;
    if (last > first) state.window.next = (last - first) / painted.length;
  }
  // the scroller put right for the new geometry (the browser's own scroll
  // anchoring is off on .fw-wrap, so nothing else moves it): the held row
  // back where it was, else the row the scroll position asked for at the top,
  // which is what a long jump and a sort at a changed estimate both need, or
  // the screen would sit over rows that are not painted
  const held = anchor && rowOf(anchor.code);
  if (held) w.scrollTop += (held.getBoundingClientRect().top - screenTop) - anchor.delta;
  else if (around === undefined && w.scrollTop > el("head").offsetHeight) {
    const top = rowOf(view[asked][codeIdx]);
    if (top) w.scrollTop += top.getBoundingClientRect().top - screenTop;
  }

  // One tab stop for the whole table; the arrow keys move within it. The row
  // open in the pane takes it when it is on screen, so Tab from the pane
  // lands back on it; else the row that had it, else the first painted.
  const first = markRows() || rowOf(stopCode) || body.querySelector("tr[data-code]");
  if (first) first.tabIndex = 0;
  const again = rowOf(focusedCode);
  if (again) { holdRow(again); again.focus({ preventScroll: true }); }
}

// True when the scroller has moved far enough that the window should follow:
// a row on screen is within half the overscan of a painted edge that is not
// the view's own edge, measured at the estimate the spacers stand at. The
// screen's rows, not the wanted window's: the window is clamped at the view's
// ends, so at the top it always starts at 0 and would never look stale
// against a painted window starting a few rows down, which left the first
// rows a blank spacer after a fast scroll down and back.
function windowStale() {
  const { first, last } = wanted(state.window.avg || ROW_SEED);
  const half = OVERSCAN / 2;
  return (first - half < state.window.from && state.window.from > 0) ||
         (last + half > state.window.to && state.window.to < state.view.length);
}

// Synchronous: the browser already delivers scroll once a frame, a stale
// check is arithmetic, and a paint is about a hundred rows.
function onScroll() {
  if (state.view.length && windowStale()) paint(undefined, true);
}

// The row at index i of the view, painted and on screen: when it is not in
// the window, the window is painted around it first and the scroller then
// brought to it, in that order, since a scroll position set before the paint
// would be clamped to the old height. null when the index is out of the view.
export function revealIndex(i) {
  if (i < 0 || i >= state.view.length) return null;
  const body = el("body");
  const codeIdx = cols().indexOf("Code");
  const code = state.view[i][codeIdx];
  const rowOf = () => body.querySelector('tr[data-code="' + CSS.escape(code) + '"]');
  let row = rowOf();
  if (!row) {
    paint(i);
    row = rowOf();
  }
  if (row) {
    const box = row.getBoundingClientRect(), edge = wrap().getBoundingClientRect(), headH = el("head").offsetHeight;
    if (box.top < edge.top + headH || box.bottom > edge.bottom) row.scrollIntoView({ block: "center" });
  }
  return row;
}

export const viewIndexOf = code => {
  const codeIdx = cols().indexOf("Code");
  return codeIdx < 0 ? -1 : state.view.findIndex(r => r[codeIdx] === code);
};

export function initTable() {
  wrap().addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", onScroll);
}

export function draw() {
  compute();
  const rows = state.view;
  const pending = !loaded(state.sheet);
  if (pending) el("count").textContent = state.loadError ? UI.load_failed : t("loading", { n: SHEETS[state.sheet].rows });
  else paintFooter(rows.length, rowsAll().length);
  paintLevelChips();
  paintOfficialChips();
  refreshFades();   // after the chips: they are what makes the control strip wide
}
