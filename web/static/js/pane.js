// The details pane under the table (section 14): one chart's graph (the
// canvas, readout, legend, compare-with-a-row and Save as PNG of graph.js) beside every
// chart of its song (song.js), with where it is published up front. The table
// shrinks to make room and the open chart's row is highlighted; the pane is
// keyed on state.graph, not on a row, so it survives a sort, a filter that
// hides the row and a sheet switch, and a shared ?code= always has somewhere
// to open. Not a dialog: no backdrop, no focus trap, focus stays on the row
// that opened it so the arrow keys keep moving (and the graph follows), and
// Escape closes it and returns to the row. The height is dragged at the top
// edge and remembered (fw.pane); the heading's caret collapses it.
import { UI, VALUE_LABELS, MISS_TEXT, SHEET_OF_CODE, SHEETS, SITE_URL } from "./boot.js";
import { el, esc } from "./dom.js";
import { t, lab, isMissing } from "./format.js";
import { cols, state, findRow, savePane } from "./state.js";
import { writeUrl } from "./url.js";
import { loadSheet, loadAll, loadLinks } from "./load.js";
import { linkAnchors } from "./links.js";
import { loadCurves, mountGraph, exportPng, outputFilename, G_MOST } from "./graph.js";
import { songSection } from "./song.js";
import { markRows, revealIndex, viewIndexOf } from "./table.js";
import { toast } from "./overlay.js";

let controller = null;  // the mounted graph, while one is open
let paneOpener = null;  // the row that opened the pane, for Escape
const BASE_TITLE = document.title;   // the tab reads as the open chart while one is up, and as the site again after
const PANE_MIN = 140;                                   // px; the smallest the grip drags to
const SIDE_BY_SIDE = "(min-width: 900px)";              // the graph beside the song grid, else stacked

const pane = () => el("pane");
const card = () => pane().querySelector(".pcard");
export const paneIsOpen = () => pane().classList.contains("on");

// The other rows on this sheet with exactly these notes at this level and
// part: the same chart in another folder. Copies are always on the chart's own
// sheet (same instrument), so the loaded sheet is the only place to look.
function copies(code, found) {
  if (!found) return [];
  const { columns, row } = found;
  const key = ["Type", "Level", "NotesHash"].map(c => columns.indexOf(c));
  const codeAt = columns.indexOf("Code");
  if (key.some(i => i < 0)) return [];
  const hash = row[key[2]];
  if (hash === null || hash === undefined || hash === "") return [];
  return state.data[found.sheet].rows.filter(r => r[codeAt] !== code && key.every(i => r[i] === row[i]));
}

// What a copy is called: its pack and whether it is official. A folder with
// no matched icon carries the literal default "Custom" as its source, which
// would read "Custom (Custom)", so the charter stands in there, and the code
// when that is empty too.
function copyText(row, columns) {
  const get = name => row[columns.indexOf(name)];
  let release = get("Release");
  if (release === "Custom") release = get("Charter") || get("Code");
  const kind = (VALUE_LABELS.Official || {})[String(get("Official"))] ?? String(get("Official"));
  return esc(release) + " (" + esc(kind) + ")";
}

const getter = code => {
  const found = findRow(code);
  const columns = found ? found.columns : cols();
  const row = found ? found.row : undefined;
  return { found, row, get: name => { const i = columns.indexOf(name); return i < 0 || row === undefined ? "" : row[i]; } };
};

// Names the chart being shown, so the graph is never unlabelled. Line 1 is
// the row's words; a row that has not arrived yet (a ?vs= code from a sheet
// still loading) shows the code and is rebuilt when it does.
function heading(code) {
  const { found, row, get } = getter(code);
  // The report link carries the code and the song, so a rating complaint arrives
  // pointing at an exact chart instead of "the Dragonforce one".
  const report = UI.report_url + "&code=" + encodeURIComponent(code) +
    "&song=" + encodeURIComponent(get("Song Title") + " - " + get("Artist"));
  // "At or above N%": the pool the row is ranked in is the current sheet at the
  // row's level, and the chart itself is in it, so "harder than" would be wrong.
  const pct = get("Pct");
  const place = typeof pct === "number"
    ? '<span class="text-secondary">' +
      esc(t("pct_of", { pct: pct, level: get("Level"), sheet: found ? found.sheet : state.sheet })) + "</span>"
    : "";
  // Two folders in one pack read the same, so the code then says which one.
  const own = row === undefined ? "" : copyText(row, found.columns);
  const others = copies(code, found).map(r => {
    const c = r[found.columns.indexOf("Code")], text = copyText(r, found.columns);
    return '<a href="?code=' + esc(c) + '" data-code="' + esc(c) + '" title="' + esc(UI.copies_tip) + '">' +
      text + (text === own ? " " + esc(c) : "") + "</a>";
  });
  const same = others.length
    ? '<div class="copies"><span class="text-secondary">' + esc(UI.copies_label) + "</span> " +
      others.join('<span class="sep">/</span>') + "</div>"
    : "";
  return '<div class="mhead"><strong>' + esc(row === undefined ? code : get("Song Title")) + '</strong>' +
    '<span class="text-secondary">' + esc(get("Artist")) + '</span>' +
    '<span class="badge rounded-pill lvl ' + esc(get("Level")) + '">' +
    esc(get("Level")) + '</span>' +
    '<span class="text-secondary">' + esc(get("Type")) + '</span>' +
    '<span class="text-secondary">' + esc(get("Charter")) + '</span>' + place +
    '<span class="ms-auto lnk"><a class="rpt" target="_blank" rel="noopener" href="' + esc(report) + '">' + esc(UI.report) + "</a></span>" +
    same + "</div>";
}

// Line 2, what the PNG's metadata line said: the difficulty numbers, the
// source and the file format. From the row, or from the curve file's head
// while the row is not here yet; a null or a sentinel prints as the dash.
function metaLine(code, head) {
  const found = findRow(code);
  const get = name => {
    if (found) { const i = found.columns.indexOf(name); return i < 0 ? null : found.row[i]; }
    return head && name in head ? head[name] : null;
  };
  const num = (col, places) => {
    const v = get(col);
    return typeof v === "number" && !isMissing(col, v) ? (places ? v.toFixed(places) : String(v)) : MISS_TEXT;
  };
  const bits = [
    [lab("D"), num("D", 2)], [lab("Difficulty"), num("Difficulty")],
    [lab("RemapDiff"), num("RemapDiff")], [lab("CalcTier"), num("CalcTier")],
  ].map(([k, v]) => "<span>" + esc(k) + " <b>" + esc(v) + "</b></span>");
  if (found) {
    const kind = (VALUE_LABELS.Official || {})[String(get("Official"))] ?? "";
    bits.push("<span>" + esc(get("Release") ?? "") + (kind ? " (" + esc(kind) + ")" : "") + "</span>");
  }
  const source = head && head.source;
  if (source) bits.push("<span>" + esc(t("graph_source", { source })) + "</span>");
  return '<div class="mmeta">' + bits.join('<span class="sep">|</span>') + "</div>";
}

// The pane's own buttons, out of the heading's flow at the card's corner.
const paneButtons = () =>
  '<div class="pbtns"><button type="button" class="pmin" data-act="min" aria-expanded="' + (state.paneMin ? "false" : "true") +
  '" aria-label="' + esc(state.paneMin ? UI.pane_expand : UI.pane_collapse) + '" title="' + esc(state.paneMin ? UI.pane_expand : UI.pane_collapse) +
  '">' + (state.paneMin ? "&#9650;" : "&#9660;") + "</button>" +
  '<button type="button" class="x" data-act="close" aria-label="' + esc(UI.close_tip) + '" title="' + esc(UI.close_tip) + '">&times;</button></div>';

const codesOpen = () => [state.graph, ...state.compare];

// Where the chart is published first, in the accent, then the graph's tools.
// Compare is pick-from-the-table alone: the table's own search and filters
// are the picker, and the song grid beside the graph lists the song's other
// charts, so a search box of its own would only duplicate both. With three
// charts up the button is disabled and its tip says so; the row is rebuilt on
// every add or remove, so the state is never stale. Copy link (section 16)
// puts the song page's address with this exact view on the clipboard.
function toolRow(code) {
  const key = getter(code).get("SongKey");
  const full = codesOpen().length >= G_MOST;
  return '<div class="gtools">' + linkAnchors(key, "btn btn-sm btn-outline-primary ext") +
    '<button type="button" class="btn btn-sm btn-outline-secondary" data-act="pick"' + (full ? " disabled" : "") +
    ' title="' + esc(full ? UI.compare_full : UI.compare_pick_tip) + '">' + esc(UI.compare_pick) + "</button>" +
    '<button type="button" class="btn btn-sm btn-outline-secondary" data-act="save">' + esc(UI.save_png) + "</button>" +
    '<button type="button" class="btn btn-sm btn-outline-secondary" data-act="share" title="' + esc(UI.share_tip) + '">' + esc(UI.share) + "</button>" +
    "</div>";
}

// The link Copy link hands out: the song's page on the published site, which
// previews as the song when pasted, with this chart and comparison in its
// query so it opens exactly this view; a stale code falls back to the song
// there (main.js). On serve, or for a chart whose song has no key, the app's
// own address with the same query.
export function shareLink() {
  const key = getter(state.graph).get("SongKey");
  const query = "?code=" + encodeURIComponent(state.graph) +
    (state.compare.length ? "&vs=" + state.compare.map(encodeURIComponent).join(",") : "");
  if (SITE_URL && typeof key === "string" && /^[0-9a-f]{12}$/.test(key))
    return SITE_URL.replace(/\/+$/, "") + "/song/" + key + ".html" + query;
  return location.origin + location.pathname + query;
}

// The clipboard API needs a secure context and permission; a hidden input
// and execCommand is the fallback, and the toast says which way it went.
function clipboardFallback(text) {
  const input = document.createElement("input");
  input.value = text; input.readOnly = true;
  input.style.cssText = "position:fixed;opacity:0;top:0;left:0";
  document.body.appendChild(input);
  input.select();
  let ok = false;
  try { ok = document.execCommand("copy"); } catch (e) { ok = false; }
  input.remove();
  return ok;
}

function paneShare() {
  if (!state.graph) return;
  const url = shareLink();
  const done = () => toast(UI.share_copied), fail = () => toast(UI.share_failed);
  if (navigator.clipboard && navigator.clipboard.writeText)
    navigator.clipboard.writeText(url).then(done, () => (clipboardFallback(url) ? done() : fail()));
  else (clipboardFallback(url) ? done() : fail());
}

function applyHeight() {
  const p = pane();
  p.classList.toggle("min", state.paneMin);
  p.style.height = state.paneH && !state.paneMin ? state.paneH + "px" : "";
}

// The song half: every chart of the key, once every sheet is here. Only
// while this chart is still the one open.
function fillSong(code) {
  const key = getter(code).get("SongKey");
  const host = card().querySelector(".sbody");
  if (typeof key !== "string" || !key) { host.innerHTML = ""; return; }
  host.innerHTML = '<p class="meta text-secondary">' + esc(UI.song_loading) + "</p>";
  loadAll().then(() => {
    if (state.graph !== code || !paneIsOpen()) return;
    const box = card().querySelector(".sbody");
    if (box) box.innerHTML = songSection(key, code);
  });
}

// Opens the pane on a chart, or swaps the chart in place; vs is the whole
// comparison, so a caller that does not name one shows the chart alone.
// opts.follow: the arrow keys moved the selection, so focus stays where it is
// and a collapsed pane stays collapsed. opts.reveal: a shared link, so the
// row is scrolled into view and focused.
export function openPane(code, vs = [], opts = {}) {
  const p = pane(), c = card();
  const wasOpen = paneIsOpen();
  if (controller) { controller.destroy(); controller = null; }
  state.graph = code;
  state.compare = [...new Set((vs || []).filter(x => x && x !== code))].slice(0, 2);
  if (!opts.follow && state.paneMin) state.paneMin = false;
  writeUrl();
  p.setAttribute("aria-label", UI.pane_label + ": " + code);
  const { get } = getter(code);
  document.title = get("Song Title") ? get("Song Title") + " - " + get("Artist") + " - " + UI.title : code + " - " + UI.title;
  p.classList.add("on");
  applyHeight();
  c.innerHTML = heading(code) + paneButtons() + metaLine(code, null) + toolRow(code) +
    '<div class="pbody"><div class="gbody"><div class="text-secondary py-4">' + esc(UI.rendering) + "</div></div>" +
    '<div class="sbody"></div></div>';
  // a shared link: the row is painted and scrolled to first, since the DOM
  // holds a window of the view (section 17), then marked
  const shown = opts.reveal ? revealIndex(viewIndexOf(code)) : null;
  const row = markRows();          // between repaints: a swap from a cell, a row, a copy's link
  if (!wasOpen) paneOpener = row || document.activeElement;
  if (shown) shown.focus({ preventScroll: true });
  fillSong(code);
  // the tools are a function of state: when the links file lands after the
  // open, the row is redrawn, and only while this chart is still up
  if (!state.links) loadLinks().then(() => refreshTools(code), () => {});

  const codes = codesOpen();
  Promise.all(codes.map(x => loadCurves(x).then(curves => ({ code: x, curves }), () => ({ code: x })))).then(results => {
    if (state.graph !== code || !paneIsOpen()) return;         // closed or swapped meanwhile
    const primary = results[0];
    if (!primary.curves) {
      c.querySelector(".gbody").innerHTML = '<div class="text-secondary py-4">' + esc(UI.render_failed) + "</div>";
      return;
    }
    const lost = results.slice(1).filter(r => !r.curves).map(r => r.code);
    if (lost.length) {
      lost.forEach(x => toast(t("compare_missing", { code: x })));
      state.compare = state.compare.filter(x => !lost.includes(x));
      writeUrl();
      refreshTools(code);
      fillSong(code);
      markRows();
    }
    // in series order: charts[k] is drawn and marked as series k
    const charts = results.filter(r => r.curves).map(r => {
      const found = findRow(r.code);
      return { code: r.code, row: found && found.row, columns: found && found.columns, curves: r.curves };
    });
    c.querySelector(".mmeta").outerHTML = metaLine(code, primary.curves.head);
    controller = mountGraph(c.querySelector(".gbody"), charts, {
      onRemove: removeCompare, fill: () => matchMedia(SIDE_BY_SIDE).matches });
    // a chart from a sheet not yet loaded draws now and gets its name later
    for (const chart of charts) {
      if (chart.row) continue;
      const sheet = SHEET_OF_CODE[chart.code.slice(-1).toUpperCase()];
      if (!sheet || !SHEETS[sheet]) continue;
      loadSheet(sheet).then(() => {
        if (state.graph !== code || controller === null || controller.charts !== charts) return;
        const found = findRow(chart.code);
        if (!found) return;
        chart.row = found.row; chart.columns = found.columns;
        c.querySelector(".mhead").outerHTML = heading(code);
        c.querySelector(".mmeta").outerHTML = metaLine(code, primary.curves.head);
        controller.redraw();
      }, () => {});
    }
  });
}

// The tool row is a function of state: rebuilt in place when the links file
// lands after the open, and when a compared chart is dropped for want of a
// curve file, so the anchors and the disabled state are never stale.
export function refreshTools(code = state.graph) {
  if (!paneIsOpen() || state.graph !== code) return;
  const old = card().querySelector(".gtools");
  if (old) old.outerHTML = toolRow(code);
}

export function closePane() {
  if (!paneIsOpen()) return;
  pane().classList.remove("on");
  document.title = BASE_TITLE;
  if (controller) { controller.destroy(); controller = null; }
  state.graph = null;
  if (!state.picking) state.compare = [];
  writeUrl();
  markRows();                      // nothing is on the graph: every mark goes
  const back = paneOpener && paneOpener.isConnected && !pane().contains(paneOpener) ? paneOpener : el("body").querySelector('tr[tabindex="0"]');
  if (back) back.focus();
  paneOpener = null;
}

// --- compare: another chart on the same axes ---------------------------------------

export function addCompare(code) {
  if (codesOpen().includes(code)) { toast(UI.compare_dup); return false; }
  if (codesOpen().length >= G_MOST) { toast(UI.compare_full); return false; }
  openPane(state.graph, [...state.compare, code], { follow: true });
  return true;
}

// Removing the primary promotes the first extra; removing the last extra
// leaves a plain graph.
export function removeCompare(code) {
  if (code === state.graph) {
    const [next, ...rest] = state.compare;
    if (next) openPane(next, rest, { follow: true });
    return;
  }
  openPane(state.graph, state.compare.filter(c => c !== code), { follow: true });
}

// --- pick from the table -------------------------------------------------------------

// The table is right there, so choosing from it is a mode rather than a
// hidden graph: a bar above the table says what is waiting, and the next row
// click joins the graph (or Escape cancels). The pane stays, so the second
// chart is seen landing on the graph.
export function startPicking() {
  if (codesOpen().length >= G_MOST) { toast(UI.compare_full); return; }
  const found = findRow(state.graph);
  const song = found ? found.row[found.columns.indexOf("Song Title")] : state.graph;
  state.picking = true;
  const bar = el("pick");
  bar.innerHTML = "<span>" + esc(t("compare_picking", { song })) + "</span> " +
    '<button type="button" class="btn btn-sm btn-outline-secondary" data-act="unpick">' + esc(UI.compare_cancel) + "</button>";
  bar.classList.remove("d-none");
  const row = el("body").querySelector('tr[tabindex="0"]');
  (row || bar.querySelector("button")).focus();
}

export function stopPicking() {
  state.picking = false;
  el("pick").classList.add("d-none");
  el("pick").innerHTML = "";
}

export const isPicking = () => state.picking;

// --- collapse and resize -----------------------------------------------------------------

function toggleMin() {
  state.paneMin = !state.paneMin;
  applyHeight();
  const b = card().querySelector(".pbtns");
  if (b) b.outerHTML = paneButtons();
  const again = card().querySelector(".pmin");
  if (again) again.focus();
  if (controller && !state.paneMin) controller.redraw();
}

// The grip drags the top edge; the table keeps at least a few rows.
let paneDrag = null;
function gripDown(e) {
  if (state.paneMin) return;
  e.preventDefault();
  const p = pane();
  paneDrag = { from: e.clientY, height: p.getBoundingClientRect().height };
  document.body.classList.add("resizing-v");
  p.querySelector(".pgrip").setPointerCapture?.(e.pointerId);
}
function gripMove(e) {
  if (!paneDrag) return;
  const head = document.querySelector(".fw-head"), foot = document.querySelector(".fw-foot");
  const room = window.innerHeight - (head ? head.offsetHeight : 0) - (foot ? foot.offsetHeight : 0) - 120;
  state.paneH = Math.round(Math.max(PANE_MIN, Math.min(Math.max(room, PANE_MIN), paneDrag.height + (paneDrag.from - e.clientY))));
  pane().style.height = state.paneH + "px";
}
function gripUp() {
  if (!paneDrag) return;
  paneDrag = null;
  document.body.classList.remove("resizing-v");
  savePane();
}

// --- save ------------------------------------------------------------------------------

function savePng() {
  if (!controller) return;
  const primary = controller.charts[0];
  const c = card();
  const text = sel => { const n = c.querySelector(sel); return n ? n.textContent.replace(/\s+/g, " ").trim() : ""; };
  const title = primary.row ? text(".mhead strong") + " - " + (primary.row[primary.columns.indexOf("Artist")] ?? "") : primary.code;
  const head = { title, meta: text(".mmeta") };
  const name = outputFilename(controller.charts.map(x => x.code), primary.row, primary.columns);
  exportPng(controller.charts, head).then(blob => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = name;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }, () => toast(UI.render_failed));
}

// The pane's own controls; the document router keeps the cells, the copies
// links and the grid's compare buttons, which route to a chart.
export function initPane() {
  const p = pane();
  p.querySelector(".pgrip").title = UI.pane_resize_tip;
  p.querySelector(".pgrip").setAttribute("aria-label", UI.pane_resize_tip);
  p.addEventListener("click", e => {
    const act = e.target.closest("[data-act]");
    if (!act) return;
    if (act.dataset.act === "pick") startPicking();
    else if (act.dataset.act === "save") savePng();
    else if (act.dataset.act === "share") paneShare();
    else if (act.dataset.act === "min") toggleMin();
    else if (act.dataset.act === "close") closePane();
  });
  p.querySelector(".pgrip").addEventListener("pointerdown", gripDown);
  document.addEventListener("pointermove", gripMove);
  document.addEventListener("pointerup", gripUp);
  document.addEventListener("pointercancel", gripUp);
  el("pick").addEventListener("click", e => { if (e.target.closest('[data-act="unpick"]')) stopPicking(); });
  document.addEventListener("fw:links", () => refreshTools());
  // the canvas reads its colours at each paint, so a theme switch is a redraw
  document.addEventListener("fw:theme", () => { if (controller && !state.paneMin) controller.redraw(); });
}
