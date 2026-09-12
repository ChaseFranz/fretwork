// Every chart of a song at once, for the details pane: instruments down and
// levels across, D and Percentile in each cell, the Expert-anchored tier by
// each instrument, and the other folders that carry the same charts. Keyed by
// SongKey, which names the charts and survives a re-download; folders are told
// apart by the code prefix, and the one the open chart is in heads the list.
// Markup only, from the rows already loaded (the pane calls loadAll() first):
// nothing here imports pane.js, so the bundle has no cycle.
import { SHEETS, UI, LEVELS, VALUE_ORDER, VALUE_LABELS, MISS_TEXT, RENDER } from "./boot.js";
import { esc } from "./dom.js";
import { t, lab, decimals, isMissing } from "./format.js";
import { G_LETTERS, G_SERIES, G_MOST } from "./graph.js";
import { state } from "./state.js";

// What the graph holds, so the grid can mirror the legend: in compare mode
// (two or more charts) each code's letter and colour; one chart alone is
// browsing, not comparing, and gets the ring and nothing else.
export function onGraph() {
  const codes = [state.graph, ...state.compare].filter(Boolean);
  const comparing = codes.length > 1;
  return { codes, comparing, full: codes.length >= G_MOST,
    mark: new Map(comparing ? codes.map((c, k) => [c, { letter: G_LETTERS[k], colour: RENDER[G_SERIES[k]] }]) : []) };
}

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

// The folders sharing the key, primary first: the one the open chart is in,
// else Official, then Release, then title, then the code prefix, so a bare
// link always heads with the same folder.
export function folders(charts, from) {
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

// The charts of the primary folder, in the grid's order: instruments in
// VALUE_ORDER order, levels Expert first.
function ownCharts(key, from) {
  const charts = chartsOf(key);
  if (!charts.length) return [];
  const list = folders(charts, from);
  return charts.filter(c => prefix(c) === list[0].prefix);
}

function typesOf(charts) {
  const types = (VALUE_ORDER.Type || []).filter(ty => charts.some(c => cell(c, "Level") && cell(c, "Type") === ty));
  for (const c of charts) if (!types.includes(cell(c, "Type"))) types.push(cell(c, "Type"));
  return types;
}

// The chart a ?song= link opens: the primary folder's first instrument, at
// Expert when it has one, else its first level. null when no loaded row has
// the key.
export function primaryCode(key) {
  const own = ownCharts(key, null);
  if (!own.length) return null;
  const mine = own.filter(c => cell(c, "Type") === typesOf(own)[0]);
  const pick = LEVELS.map(l => mine.find(c => cell(c, "Level") === l)).find(Boolean) || mine[0];
  return cell(pick, "Code");
}

// The grid for the primary folder's charts: a blank for a level the
// instrument lacks, the tier once per instrument, since it is the same number
// on every level of one. The cells are the compare controls too: in compare
// mode a cell on the graph wears its series colour and letter (its click takes
// it off), one not on it adds itself (disabled at three, with the tip saying
// so); with one chart up a cell just opens its chart. The instrument's button
// puts its levels up, three at most, and is pressed while they are, when it
// takes them down again.
function grid(charts, here) {
  const { comparing, full, mark } = onGraph();
  const types = typesOf(charts);
  let out = '<div class="sgrid" role="grid" aria-label="' + esc(UI.song_grid_label) + '"><div class="corner"></div>' +
    LEVELS.map(l => '<div class="lvlh ' + esc(l) + '">' + esc(l) + "</div>").join("");
  for (const ty of types) {
    const own = charts.filter(c => cell(c, "Type") === ty);
    const tier = own.map(c => cell(c, "CalcTier")).find(v => typeof v === "number");
    out += '<div class="inst">' + esc(ty) + (typeof tier === "number" ? ' <span class="tier">' + esc(t("song_tier", { n: tier })) + "</span>" : "");
    const levels = LEVELS.map(l => own.find(c => cell(c, "Level") === l)).filter(Boolean);
    const codes = levels.slice(0, G_MOST).map(c => cell(c, "Code"));
    if (codes.length > 1) {
      const pressed = comparing && codes.every(c => mark.has(c));
      const names = levels.slice(0, G_MOST).map(c => cell(c, "Level"));
      const tip = pressed ? UI.song_compare_off
        : t("song_compare_tip", { levels: names.slice(0, -1).join(", ") + " and " + names[names.length - 1] });
      out += ' <button type="button" class="cmp" data-cmp="' + esc(codes.join(",")) + '" aria-pressed="' + (pressed ? "true" : "false") +
        '" title="' + esc(tip) + '">' + esc(UI.song_compare) + "</button>";
    }
    out += "</div>";
    for (const level of LEVELS) {
      const c = own.find(x => cell(x, "Level") === level);
      if (!c) {
        out += '<div class="cell none" title="' + esc(t("song_no_level", { level })) + '">' + esc(MISS_TEXT) + "</div>";
        continue;
      }
      const code = cell(c, "Code"), d = cell(c, "D"), pct = cell(c, "Pct");
      const m = mark.get(code);
      const off = comparing && full && !m;
      const tip = m ? t("song_on_graph", { letter: m.letter }) : off ? UI.compare_full : comparing ? UI.song_add : UI.song_open;
      out += '<button type="button" class="cell' + (code === here ? " here" : "") + (m ? " on" : "") + '" data-code="' + esc(code) + '"' +
        (code === here ? ' aria-current="true"' : "") + (m ? ' style="--sc:' + esc(m.colour) + '"' : "") + (off ? " disabled" : "") +
        ' title="' + esc(tip) + '"><b>' + (m ? '<i class="sl">' + esc(m.letter) + "</i>" : "") +
        (typeof d === "number" ? esc(d.toFixed(decimals("D", c.sheet))) : esc(MISS_TEXT)) + "</b>" +
        (typeof pct === "number" ? "<small>" + esc(pct.toFixed(decimals("Pct", c.sheet))) + "</small>" : "") + "</button>";
    }
  }
  return out + "</div>";
}

// The song half of the pane for the chart `here`: the folder's charter,
// source, date, album and year, the other folders carrying the key, the grid.
// "" when no loaded row has the key.
export function songSection(key, here) {
  const charts = chartsOf(key);
  if (!charts.length) return "";
  const list = folders(charts, here);
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
  return '<p class="meta">' + meta.join('<span class="sep">/</span>') + "</p>" +
    (also.length ? '<p class="also"><span class="text-secondary">' + esc(UI.song_also_in) + ":</span> " + also.join("; ") + "</p>" : "") +
    grid(own, here || null);
}
