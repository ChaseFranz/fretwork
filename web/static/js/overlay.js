// The graph lightbox and the transient hint, the page's two overlays.
import { EXPLAINER, FOOTER, UI, VALUE_LABELS, LABELS, MISS_TEXT, SHEET_OF_CODE, SHEETS, RENDER, LEVELS } from "./boot.js";
import { el, esc, rich } from "./dom.js";
import { t, lab, isMissing } from "./format.js";
import { cols, state, findRow } from "./state.js";
import { writeUrl } from "./url.js";
import { loadSheet, loadAll } from "./load.js";
import { loadCurves, mountGraph, exportPng, outputFilename } from "./graph.js";

let hintTimer = null;
let opener = null;      // what to hand focus back to when the graph closes
let controller = null;  // the mounted graph, while one is open
const SERIES = ["color_d", "color_nps", "color_vps"];   // a compare's three colours, in order

export function toast(message) {
  const hint = el("hint");
  hint.firstElementChild.textContent = message;
  hint.classList.add("on");
  clearTimeout(hintTimer);
  hintTimer = setTimeout(() => hint.classList.remove("on"), 1400);
}

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

// Names the chart being shown, so the graph is never unlabelled. Line 1 is
// the row's words; a row that has not arrived yet (a ?vs= code from a sheet
// still loading) shows the code and is rebuilt when it does.
function heading(code) {
  const found = findRow(code);
  const columns = found ? found.columns : cols();
  const row = found ? found.row : undefined;
  const get = name => {
    const i = columns.indexOf(name);
    return i < 0 || row === undefined ? "" : row[i];
  };
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
  const own = row === undefined ? "" : copyText(row, columns);
  const others = copies(code, found).map(r => {
    const c = r[columns.indexOf("Code")], text = copyText(r, columns);
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
    '<a class="ms-auto rpt" target="_blank" rel="noopener" href="' + esc(report) +
    '">' + esc(UI.report) + "</a>" + same + "</div>";
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

const closeButton = () => '<button type="button" class="x" data-act="close" aria-label="' +
  esc(UI.close_tip) + '" title="' + esc(UI.close_tip) + '">&times;</button>';

function tools() {
  return '<div class="gtools">' +
    '<button type="button" class="btn btn-sm btn-outline-secondary" data-act="compare" aria-expanded="false">' + esc(UI.compare) + "</button>" +
    '<button type="button" class="btn btn-sm btn-outline-secondary" data-act="pick">' + esc(UI.compare_pick) + "</button>" +
    '<button type="button" class="btn btn-sm btn-outline-secondary" data-act="save">' + esc(UI.save_png) + "</button>" +
    "</div>" +
    '<div class="picker d-none"><input type="search" class="form-control form-control-sm" id="cmpq" placeholder="' +
    esc(UI.compare_search) + '" aria-label="' + esc(UI.compare_search) + '"><ul id="cmpr"></ul></div>';
}

const codesOpen = () => [state.graph, ...state.compare];

// The graph: line 1, the close button, line 2, the canvas and its readout and
// legend, the tools, the picker. The card takes the canvas's own background,
// so the legend and readout sit on the colour the palette was measured on.
export function openGraph(code, vs = state.compare) {
  const modal = el("modal"), card = modal.querySelector(".mcard");
  // Swapping to a copy keeps the opener: the link clicked is about to be
  // replaced with the card, and Escape should still return to the table row.
  if (!graphIsOpen()) opener = document.activeElement;
  if (controller) { controller.destroy(); controller = null; }
  state.graph = code;
  state.compare = [...new Set((vs || []).filter(c => c && c !== code))].slice(0, 2);
  writeUrl();
  modal.setAttribute("aria-label", UI.graph_label + ": " + code);
  modal.classList.add("on");
  card.style.background = RENDER.figure_bg;
  card.innerHTML = heading(code) + closeButton() + metaLine(code, null) +
    '<div class="gbody"><div class="text-secondary py-4">' + esc(UI.rendering) + "</div></div>" + tools();
  modal.focus();

  const codes = codesOpen();
  Promise.all(codes.map(c => loadCurves(c).then(curves => ({ code: c, curves }), () => ({ code: c })))).then(results => {
    if (state.graph !== code || !graphIsOpen()) return;         // closed or swapped meanwhile
    const primary = results[0];
    if (!primary.curves) {
      card.querySelector(".gbody").innerHTML = '<div class="text-secondary py-4">' + esc(UI.render_failed) + "</div>";
      return;
    }
    const lost = results.slice(1).filter(r => !r.curves).map(r => r.code);
    if (lost.length) {
      lost.forEach(c => toast(t("compare_missing", { code: c })));
      state.compare = state.compare.filter(c => !lost.includes(c));
      writeUrl();
    }
    const charts = results.filter(r => r.curves).map((r, k) => {
      const found = findRow(r.code);
      return { code: r.code, row: found && found.row, columns: found && found.columns,
               curves: r.curves, colour: RENDER[SERIES[k]] };
    });
    card.querySelector(".mmeta").outerHTML = metaLine(code, primary.curves.head);
    controller = mountGraph(card.querySelector(".gbody"), charts, { onRemove: removeCompare });
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
        card.querySelector(".mhead").outerHTML = heading(code);
        card.querySelector(".mmeta").outerHTML = metaLine(code, primary.curves.head);
        controller.redraw();
      }, () => {});
    }
  });
}

export function closeGraph() {
  if (!graphIsOpen()) return;
  el("modal").classList.remove("on");
  if (controller) { controller.destroy(); controller = null; }
  state.graph = null;
  if (!state.picking) state.compare = [];
  writeUrl();
  if (opener && opener.isConnected) opener.focus();
  opener = null;
}

export const graphIsOpen = () => el("modal").classList.contains("on");

// --- compare: another chart on the same axes ---------------------------------------

export function addCompare(code) {
  if (codesOpen().includes(code)) { toast(UI.compare_dup); return false; }
  if (codesOpen().length >= 3) { toast(UI.compare_full); return false; }
  openGraph(state.graph, [...state.compare, code]);
  return true;
}

// Removing the primary promotes the first extra; removing the last extra
// leaves a plain graph.
export function removeCompare(code) {
  if (code === state.graph) {
    const [next, ...rest] = state.compare;
    if (next) openGraph(next, rest);
    return;
  }
  openGraph(state.graph, state.compare.filter(c => c !== code));
}

// The picker: the other charts of this song with an empty box, a search over
// title, artist and code across every loaded sheet otherwise, twelve at most.
function pickerRows(query) {
  const q = query.trim().toLowerCase();
  const out = [];
  const seen = new Set(codesOpen());
  const sheets = Object.keys(SHEETS).filter(s => state.data[s]);
  const rowsOf = sheet => {
    const d = state.data[sheet];
    const at = n => d.columns.indexOf(n);
    return d.rows.map(r => ({ sheet, columns: d.columns, row: r, code: r[at("Code")],
      title: String(r[at("Song Title")] ?? ""), artist: String(r[at("Artist")] ?? ""),
      level: r[at("Level")], type: r[at("Type")], d: r[at("D")] }));
  };
  if (!q) {
    const stem = String(state.graph).slice(0, 8);
    for (const sheet of sheets)
      for (const item of rowsOf(sheet)) if (item.code.slice(0, 8) === stem && !seen.has(item.code)) out.push(item);
    out.sort((a, b) => LEVELS.indexOf(a.level) - LEVELS.indexOf(b.level) || sheets.indexOf(a.sheet) - sheets.indexOf(b.sheet));
    return out;
  }
  for (const sheet of sheets) {
    for (const item of rowsOf(sheet)) {
      if (seen.has(item.code)) continue;
      if (item.title.toLowerCase().includes(q) || item.artist.toLowerCase().includes(q) || item.code.toLowerCase().includes(q)) {
        out.push(item);
        if (out.length >= 12) return out;
      }
    }
  }
  return out;
}

function paintPicker(loading) {
  const list = el("cmpr"), box = el("cmpq");
  if (!list) return;
  if (codesOpen().length >= 3) {
    box.disabled = true;
    list.innerHTML = '<li class="note">' + esc(UI.compare_full) + "</li>";
    return;
  }
  box.disabled = false;
  const items = pickerRows(box.value);
  if (!items.length) {
    list.innerHTML = '<li class="note">' + esc(loading ? UI.compare_loading : UI.compare_none) + "</li>";
    return;
  }
  const lead = box.value.trim() ? "" : '<li class="note">' + esc(UI.compare_same_song) + "</li>";
  list.innerHTML = lead + items.map(i =>
    '<li><button type="button" data-add="' + esc(i.code) + '"><span class="tt">' + esc(i.title) + " - " + esc(i.artist) +
    '</span> <span class="badge rounded-pill lvl ' + esc(i.level) + '">' + esc(i.level) + "</span> " +
    '<span class="text-secondary">' + esc(i.type) + "</span> " +
    '<span class="dv">' + esc(typeof i.d === "number" ? i.d.toFixed(2) : "") + "</span></button></li>").join("");
}

function togglePicker(button) {
  const picker = el("modal").querySelector(".picker");
  const open = picker.classList.toggle("d-none") === false;
  button.setAttribute("aria-expanded", open ? "true" : "false");
  if (!open) return;
  paintPicker(true);
  el("cmpq").focus();
  loadAll().then(() => { if (graphIsOpen()) paintPicker(false); });
}

// --- pick from the table -------------------------------------------------------------

// The modal is a full-screen backdrop, so choosing from the table hides it:
// the graph and its comparison are kept, a bar above the table says what is
// waiting, and the next row click (or Escape) brings the graph back.
export function startPicking() {
  const found = findRow(state.graph);
  const song = found ? found.row[found.columns.indexOf("Song Title")] : state.graph;
  state.picking = true;
  el("modal").classList.remove("on");
  if (controller) { controller.destroy(); controller = null; }
  const bar = el("pick");
  bar.innerHTML = "<span>" + esc(t("compare_picking", { song })) + "</span> " +
    '<button type="button" class="btn btn-sm btn-outline-secondary" data-act="unpick">' + esc(UI.compare_cancel) + "</button>";
  bar.classList.remove("d-none");
  const row = el("body").querySelector('tr[tabindex="0"]');
  (row || bar.querySelector("button")).focus();
}

export function stopPicking(reopen) {
  state.picking = false;
  el("pick").classList.add("d-none");
  el("pick").innerHTML = "";
  if (reopen && state.graph) openGraph(state.graph, state.compare);
}

export const isPicking = () => state.picking;

// --- save ------------------------------------------------------------------------------

function savePng() {
  if (!controller) return;
  const primary = controller.charts[0];
  const card = el("modal").querySelector(".mcard");
  const text = sel => { const n = card.querySelector(sel); return n ? n.textContent.replace(/\s+/g, " ").trim() : ""; };
  const title = primary.row ? text(".mhead strong") + " - " + (primary.row[primary.columns.indexOf("Artist")] ?? "") : primary.code;
  const heading = { title, meta: text(".mmeta") };
  const name = outputFilename(controller.charts.map(c => c.code), primary.row, primary.columns);
  exportPng(controller.charts, heading).then(blob => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = name;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }, () => toast(UI.render_failed));
}

// The modal's own controls; the document router keeps the backdrop, the close
// button and the copies links.
export function initGraphModal() {
  const modal = el("modal");
  modal.addEventListener("click", e => {
    const add = e.target.closest("[data-add]");
    if (add) { addCompare(add.dataset.add); return; }
    const act = e.target.closest("[data-act]");
    if (!act) return;
    if (act.dataset.act === "compare") togglePicker(act);
    else if (act.dataset.act === "pick") startPicking();
    else if (act.dataset.act === "save") savePng();
  });
  modal.addEventListener("input", e => { if (e.target.id === "cmpq") paintPicker(false); });
  el("pick").addEventListener("click", e => { if (e.target.closest('[data-act="unpick"]')) stopPicking(true); });
}


// The explainer: what D is, and what it is not. Static text, built once.
export function openAbout() {
  const panel = el("about");
  opener = document.activeElement;
  if (!panel.querySelector(".mhead")) {
    const out = (text, href) => '<a target="_blank" rel="noopener" href="' + esc(href) +
      '">' + esc(text) + "</a>";
    panel.querySelector(".mcard").innerHTML =
      '<div class="mhead"><strong>' + esc(UI.explainer_title) + "</strong>" +
      '<button type="button" class="x" data-act="close" aria-label="' +
      esc(UI.close_tip) + '" title="' + esc(UI.close_tip) + '">&times;</button></div>' +
      '<div class="vid"><iframe src="' + esc(UI.video_embed) + '" title="' +
      esc(UI.video_title) + '" loading="lazy" allowfullscreen ' +
      'referrerpolicy="strict-origin-when-cross-origin" ' +
      'allow="encrypted-media; picture-in-picture; fullscreen"></iframe></div>' +
      '<p class="cap">' + rich(UI.video_caption) + "</p>" +
      EXPLAINER.map(([heading, body]) =>
        "<h2>" + esc(heading) + "</h2><p>" + rich(body) + "</p>").join("") +
      '<p class="more">' + out(UI.explainer_more, FOOTER[0][1]) +
      '<span class="sep">/</span>' + out(UI.explainer_method, UI.method_url) +
      '<span class="sep">/</span><a href="about.html">' + esc(UI.about) + "</a></p>";
  }
  panel.setAttribute("aria-label", UI.explainer_title);
  panel.classList.add("on");
  panel.focus();
}

// Hiding the panel does not stop the player: an iframe goes on playing audio
// while display:none, so closing the panel has to say so. The IFrame API's pause
// command keeps the viewer's place in the video, which blanking the src would
// not - reopening would drop them back at the start.
function pauseVideo() {
  const frame = el("about").querySelector("iframe");
  if (!frame || !frame.contentWindow) return;
  frame.contentWindow.postMessage(
    JSON.stringify({ event: "command", func: "pauseVideo", args: [] }),
    "https://www.youtube-nocookie.com");
}

export function closeAbout() {
  pauseVideo();
  el("about").classList.remove("on");
  if (opener && opener.isConnected) opener.focus();
  opener = null;
}

export const aboutIsOpen = () => el("about").classList.contains("on");
