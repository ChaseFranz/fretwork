// The per-song panel: every chart of a song at once, instruments down and
// levels across, D and Percentile in each cell, the Expert-anchored tier by
// each instrument, and the other folders that carry the same charts. Keyed by
// SongKey (?song=<key>), which names the charts and survives a re-download;
// folders are told apart by the code prefix, and the one the reader came from
// heads the panel. A third fixed dialog under the graph (z 1055 against
// 1060), so a graph opened from a cell draws over it and the panel is still
// there when the graph closes. Nothing here imports overlay.js: the heading's
// link is markup that router.js routes to openSong, so the bundle has no cycle.
import { SHEETS, UI, LEVELS, VALUE_ORDER, VALUE_LABELS, MISS_TEXT } from "./boot.js";
import { el, esc } from "./dom.js";
import { t, lab, decimals, isMissing } from "./format.js";
import { loadAll } from "./load.js";
import { state } from "./state.js";
import { writeUrl } from "./url.js";

let songOpener = null;    // its own, not overlay.js's opener: a graph opened from a cell must not reuse it

// Every row carrying the key, in sheet order, as {sheet, columns, row}.
export function chartsOf(key) {
  const out = [];
  for (const sheet of Object.keys(SHEETS)) {
    const data = state.data[sheet];
    if (!data) continue;
    const at = data.columns.indexOf("SongKey");
    if (at < 0) continue;
    for (const row of data.rows) if (row[at] === key) out.push({ sheet, columns: data.columns, row });
  }
  return out;
}

const cell = (chart, name) => { const i = chart.columns.indexOf(name); return i < 0 ? null : chart.row[i]; };
const prefix = chart => String(cell(chart, "Code")).slice(0, 8);
const byText = (a, b) => a === b ? 0 : a === null || a === undefined ? 1 : b === null || b === undefined ? -1 : String(a).localeCompare(String(b));

// The folders sharing the key, primary first: the one the reader came from,
// else Official, then Release, then title, then the code prefix, so a bare
// link always heads with the same folder.
function folders(charts, from) {
  const seen = new Map();
  for (const c of charts) if (!seen.has(prefix(c))) seen.set(prefix(c), c);
  const list = [...seen.entries()].map(([p, c]) => ({ prefix: p, chart: c }));
  const came = from ? String(from).slice(0, 8) : null;
  list.sort((a, b) =>
    (came ? (b.prefix === came) - (a.prefix === came) : 0) ||
    ((cell(b.chart, "Official") === true) - (cell(a.chart, "Official") === true)) ||
    byText(cell(a.chart, "Release"), cell(b.chart, "Release")) ||
    byText(cell(a.chart, "Song Title"), cell(b.chart, "Song Title")) ||
    a.prefix.localeCompare(b.prefix));
  return list;
}

const songCloseButton = () => '<button type="button" class="x" data-act="close" aria-label="' +
  esc(UI.close_tip) + '" title="' + esc(UI.close_tip) + '">&times;</button>';

function shell(title, artist, body) {
  return '<div class="mhead"><strong>' + esc(title) + "</strong>" +
    (artist ? '<span class="text-secondary">' + esc(artist) + "</span>" : "") + songCloseButton() + "</div>" + body;
}

// The grid for the primary folder's charts: instruments in VALUE_ORDER order,
// levels in the chips' order (Expert first), a blank for a level the
// instrument lacks, the tier once per instrument, since it is the same number
// on every level of one.
function grid(charts, here) {
  const types = (VALUE_ORDER.Type || []).filter(ty => charts.some(c => cell(c, "Level") && cell(c, "Type") === ty));
  for (const c of charts) if (!types.includes(cell(c, "Type"))) types.push(cell(c, "Type"));
  let out = '<div class="sgrid" role="grid" aria-label="' + esc(UI.song_grid_label) + '"><div class="corner"></div>' +
    LEVELS.map(l => '<div class="lvlh ' + esc(l) + '">' + esc(l) + "</div>").join("");
  for (const ty of types) {
    const own = charts.filter(c => cell(c, "Type") === ty);
    const tier = own.map(c => cell(c, "CalcTier")).find(v => typeof v === "number");
    out += '<div class="inst">' + esc(ty) + (typeof tier === "number" ? ' <span class="tier">' + esc(t("song_tier", { n: tier })) + "</span>" : "");
    const codes = LEVELS.map(l => own.find(c => cell(c, "Level") === l)).filter(Boolean).map(c => cell(c, "Code"));
    if (codes.length > 1)
      out += ' <button type="button" class="cmp" data-cmp="' + esc(codes.slice(0, 3).join(",")) + '">' + esc(UI.song_compare) + "</button>";
    out += "</div>";
    for (const level of LEVELS) {
      const c = own.find(x => cell(x, "Level") === level);
      if (!c) {
        out += '<div class="cell none" title="' + esc(t("song_no_level", { level })) + '">' + esc(MISS_TEXT) + "</div>";
        continue;
      }
      const code = cell(c, "Code"), d = cell(c, "D"), pct = cell(c, "Pct");
      out += '<button type="button" class="cell' + (code === here ? " here" : "") + '" data-code="' + esc(code) + '"><b>' +
        (typeof d === "number" ? esc(d.toFixed(decimals("D", c.sheet))) : esc(MISS_TEXT)) + "</b>" +
        (typeof pct === "number" ? "<small>" + esc(pct.toFixed(decimals("Pct", c.sheet))) + "</small>" : "") + "</button>";
    }
  }
  return out + "</div>";
}

function fill(key, from) {
  const card = el("song").querySelector(".mcard");
  const charts = chartsOf(key);
  if (!charts.length) {
    card.innerHTML = shell(UI.song_not_found, "", "");
    return false;
  }
  const list = folders(charts, from);
  const main = list[0].chart;
  const own = charts.filter(c => prefix(c) === list[0].prefix);
  const kind = (VALUE_LABELS.Official || {})[String(cell(main, "Official"))];
  // a folder with no matched icon carries the literal default "Custom" as its
  // source, which beside the Custom label would read twice; the label suffices
  const release = cell(main, "Release") === "Custom" ? null : cell(main, "Release");
  const meta = [cell(main, "Charter"), release, kind].filter(v => v !== null && v !== undefined && v !== "")
    .map(v => esc(v));
  const added = cell(main, "Added");
  if (added) meta.push(esc(lab("Added")) + " " + esc(added));
  for (const name of ["Album", "Year"]) {
    const v = cell(main, name);
    if (v !== null && v !== undefined && v !== "" && !isMissing(name, v)) meta.push(esc(v));
  }
  const also = list.slice(1).map(({ chart }) => {
    const release = cell(chart, "Release"), charter = cell(chart, "Charter"), title = cell(chart, "Song Title");
    return esc(release ?? MISS_TEXT) + (charter ? " (" + esc(charter) + ")" : "") +
      (title !== cell(main, "Song Title") ? ", " + esc(title ?? "") : "");
  });
  card.innerHTML = shell(cell(main, "Song Title") ?? "", cell(main, "Artist") ?? "",
    '<p class="meta">' + meta.join('<span class="sep">/</span>') + "</p>" +
    (also.length ? '<p class="also"><span class="text-secondary">' + esc(UI.song_also_in) + ":</span> " + also.join("; ") + "</p>" : "") +
    grid(own, from || null));
  el("song").setAttribute("aria-label", UI.song_label + ": " + (cell(main, "Song Title") ?? key));
  return true;
}

export const songIsOpen = () => el("song").classList.contains("on");

// Opens at once with a loading heading, fills when every sheet is here.
// Resolves after the fill, never rejects. Called again for the key already
// open, it only re-marks the cell the reader came from.
export function openSong(key, { from } = {}) {
  const panel = el("song");
  if (songIsOpen() && state.song === key) {
    const cells = panel.querySelectorAll(".cell.here");
    cells.forEach(c => c.classList.remove("here"));
    const mine = from && panel.querySelector('.cell[data-code="' + from + '"]');
    if (mine) { mine.classList.add("here"); mine.focus(); }
    return Promise.resolve();
  }
  songOpener = document.activeElement;
  state.song = key;
  writeUrl();
  panel.querySelector(".mcard").innerHTML = shell(UI.song_loading, "", "");
  panel.setAttribute("aria-label", UI.song_label);
  panel.classList.add("on");
  panel.focus();
  return loadAll().then(() => {
    if (!songIsOpen() || state.song !== key) return;
    const failed = Object.keys(SHEETS).some(s => !state.data[s]);
    if (failed && !chartsOf(key).length) {
      panel.querySelector(".mcard").innerHTML = shell(UI.load_failed, "", "") +
        '<p class="meta"><a href="">' + esc(UI.reload) + "</a></p>";
      return;
    }
    if (!fill(key, from)) {
      state.song = null;          // the parameter leaves the URL: nothing answers to it
      writeUrl();
      return;
    }
    const here = panel.querySelector(".cell.here");
    if (!el("modal").classList.contains("on")) (here || panel).focus();
  });
}

export function closeSong() {
  if (!songIsOpen()) return;
  el("song").classList.remove("on");
  state.song = null;
  writeUrl();
  const back = songOpener && songOpener.isConnected && !el("song").contains(songOpener)
    ? songOpener : el("body").querySelector('tr[tabindex="0"]');
  if (back) back.focus();
  songOpener = null;
}
