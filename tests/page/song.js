// The song half of the details pane (sections 07 and 14): every chart of the
// open chart's song, instruments by level, beside the graph; a cell swaps the
// graph in place, the instrument's compare button overlays its levels, the
// folder the chart is in heads the list and the others are "Also in".
// Derives everything from the payload.
import { BOOT, say, skip, done, wait, click, key, ready, params } from "./lib.js";
await ready();

const { ui: UI, valueOrder: VALUE_ORDER } = BOOT;
const LEVELS = ["Expert", "Hard", "Medium", "Easy"];
const here = () => document.activeElement;
const pane = document.getElementById("pane");
const sbody = () => pane.querySelector(".sbody");
const gbody = () => pane.querySelector(".gbody");

// every sheet, as the idle prefetch delivers them
const sheets = Object.keys(BOOT.data);
const data = {};
await Promise.all(sheets.map(s => fetch(BOOT.data[s].file).then(r => r.json()).then(j => { data[s] = j; })));
const rowsOf = key => sheets.flatMap(s => data[s].rows.filter(r => r[data[s].columns.indexOf("SongKey")] === key)
  .map(r => ({ sheet: s, columns: data[s].columns, row: r })));
const get = (c, n) => c.row[c.columns.indexOf(n)];

// the key with the most rows across the sheets, and one of its codes on the opening view
const counts = new Map();
for (const s of sheets) for (const r of data[s].rows) { const k = r[data[s].columns.indexOf("SongKey")]; counts.set(k, (counts.get(k) || 0) + 1); }
const onScreen = new Set([...document.querySelectorAll("#body tr[data-code]")].map(tr => tr.dataset.code));
const key0 = [...counts.entries()].filter(([k]) => rowsOf(k).some(c => onScreen.has(get(c, "Code")))).sort((a, b) => b[1] - a[1])[0][0];
const charts = rowsOf(key0);
const first = charts.find(c => onScreen.has(get(c, "Code")));
const code = get(first, "Code");
say("a song with several charts is on screen", charts.length > 1, key0 + " " + charts.length);

// --- the row opens the pane with the song section in it -----------------------------
const row = document.querySelector('#body tr[data-code="' + code + '"]');
row.focus();
click(row);
await wait(800);
say("the pane opens on the row's chart", pane.classList.contains("on") && pane.getAttribute("aria-label").endsWith(": " + code), pane.getAttribute("aria-label"));
say("the URL names the code, never a song", params().get("code") === code && params().get("song") === null, location.search);
say("the song section is filled beside the graph", !!sbody().querySelector(".sgrid") && !!gbody().querySelector("canvas"));
say("no title pip and no song dialog remain", !document.querySelector("td.song .sp") && !document.getElementById("song"));

// --- the grid -----------------------------------------------------------------------
const prefix = code.slice(0, 8);
const own = charts.filter(c => String(get(c, "Code")).slice(0, 8) === prefix);
const insts = [...sbody().querySelectorAll(".sgrid .inst")].map(e => { const c = e.cloneNode(true); c.querySelectorAll(".tier, .cmp").forEach(x => x.remove()); return c.textContent.trim(); });
const wantTypes = VALUE_ORDER.Type.filter(ty => own.some(c => get(c, "Type") === ty));
say("instrument rows in VALUE_ORDER order", insts.join() === wantTypes.join(), insts.join() + " vs " + wantTypes.join());
say("level headings are the chips' order", [...sbody().querySelectorAll(".sgrid .lvlh")].map(e => e.textContent).join() === LEVELS.join());
const cells = () => [...sbody().querySelectorAll(".sgrid .cell:not(.none)")];
say("one cell per chart of this folder", cells().length === own.length, cells().length + " vs " + own.length);
say("each cell names a chart at its column's level", cells().every(c => {
  const chart = own.find(x => get(x, "Code") === c.dataset.code);
  const col = [...c.parentElement.children].indexOf(c) % 5;   // corner + 4 levels per row on a desktop grid
  return chart && LEVELS[col - 1] === get(chart, "Level") && c.dataset.code[8] === { Expert: "X", Hard: "H", Medium: "M", Easy: "E" }[get(chart, "Level")];
}), cells().map(c => c.dataset.code).join());
say("every cell prints D to two places or none", cells().every(c => /^\d+(\.\d{2})?$/.test(c.querySelector("b").textContent)), cells().map(c => c.querySelector("b").textContent).join());
if (own.some(c => c.columns.includes("Pct"))) {
  say("and the percentile beneath it", cells().every(c => /^\d+$/.test((c.querySelector("small") || {}).textContent || "")), cells().map(c => (c.querySelector("small") || {}).textContent).join());
}
say("the open chart's cell is marked", !!sbody().querySelector('.cell.here[data-code="' + code + '"][aria-current="true"]') && sbody().querySelectorAll(".cell.here").length === 1);
const tiers = [...sbody().querySelectorAll(".sgrid .inst")].map(e => !!e.querySelector(".tier"));
const wantTiers = wantTypes.map(ty => own.some(c => get(c, "Type") === ty && typeof get(c, "CalcTier") === "number"));
say("the tier appears once per instrument that has an Expert chart", tiers.join() === wantTiers.join(), tiers.join() + " vs " + wantTiers.join());
say("blank cells say which level is missing", [...sbody().querySelectorAll(".sgrid .cell.none")].every(c => new RegExp(UI.song_no_level.replace("{level}", "(Expert|Hard|Medium|Easy)")).test(c.title)));
say("the meta line names the folder", !!sbody().querySelector("p.meta") && sbody().querySelector("p.meta").textContent.includes(String(get(first, "Charter"))), sbody().querySelector("p.meta") && sbody().querySelector("p.meta").textContent);
const otherFolders = new Set(charts.map(c => String(get(c, "Code")).slice(0, 8))).size - 1;
say("the other folders are listed under Also in, or the line is absent", otherFolders ? !!sbody().querySelector("p.also") : !sbody().querySelector("p.also"), otherFolders);
const multi = wantTypes.filter(ty => own.filter(c => get(c, "Type") === ty).length > 1);
say("a compare button per instrument with more than one level", sbody().querySelectorAll(".sgrid .cmp").length === multi.length &&
    [...sbody().querySelectorAll(".sgrid .cmp")].every(b => b.dataset.cmp.split(",").length >= 2 && b.dataset.cmp.split(",").length <= 3), sbody().querySelectorAll(".sgrid .cmp").length + " vs " + multi.length);

// --- a cell swaps the graph in place -------------------------------------------------
say("with one chart up the cells offer to open", cells().filter(c => c.dataset.code !== code).every(c => c.title === UI.song_open && !c.disabled && !c.classList.contains("on")));
const other = cells().find(c => c.dataset.code !== code) || cells()[0];
click(other);
await wait(700);
const swapped = other.dataset.code;
say("a cell opens that chart in the same pane", pane.classList.contains("on") && pane.getAttribute("aria-label").endsWith(": " + swapped), pane.getAttribute("aria-label"));
say("the URL follows", params().get("code") === swapped, location.search);
say("the mark moves to that cell", !!sbody().querySelector('.cell.here[data-code="' + swapped + '"]') && sbody().querySelectorAll(".cell.here").length === 1);
const selRow = document.querySelector("#body tr.sel");
say("the table's highlight follows when its row is on screen", onScreen.has(swapped) ? !!selRow && selRow.dataset.code === swapped : selRow === null, selRow && selRow.dataset.code);

// --- compare mode: the grid mirrors the legend, the cells toggle ---------------------------
if (multi.length) {
  const cmp = () => sbody().querySelector(".sgrid .cmp");
  const codes = cmp().dataset.cmp.split(",");
  say("the instrument's button is not pressed with one chart up", cmp().getAttribute("aria-pressed") === "false" && cmp().title.startsWith(UI.song_compare_tip.split("{")[0]), cmp().title);
  click(cmp());
  await wait(800);
  say("Compare all levels overlays the instrument's levels", pane.classList.contains("on") &&
      gbody().fw && gbody().fw.charts.map(c => c.code).join() === codes.join(), gbody().fw && gbody().fw.charts.map(c => c.code).join());
  say("the legend names the levels alone", [...pane.querySelectorAll(".legend .lt")].every(e => LEVELS.includes(e.textContent.trim().split(" ").slice(1).join(" "))),
      [...pane.querySelectorAll(".legend .lt")].map(e => e.textContent.trim()).join(" | "));
  say("the button is pressed while its levels are up", cmp().getAttribute("aria-pressed") === "true" && cmp().title === UI.song_compare_off, cmp().title);
  const on = () => [...sbody().querySelectorAll(".sgrid .cell.on")];
  say("each chart on the graph is marked in the grid, in legend order", on().map(c => c.dataset.code).join() === codes.join() &&
      on().map(c => c.querySelector(".sl").textContent).join() === ["A", "B", "C"].slice(0, codes.length).join(), on().map(c => c.dataset.code + c.querySelector(".sl").textContent).join());
  const swatches = [...pane.querySelectorAll(".legend .sw")].map(e => e.style.borderColor);
  say("with the legend's colours", on().every((c, k) => c.style.getPropertyValue("--sc") && getComputedStyle(c).borderTopColor === swatches[k]),
      on().map(c => getComputedStyle(c).borderTopColor).join(" | ") + " vs " + swatches.join(" | "));
  say("the primary keeps its ring as well", sbody().querySelector(".cell.here.on") && sbody().querySelector(".cell.here").dataset.code === codes[0]);
  say("an on-graph cell offers to take its chart off", on().every(c => c.title === UI.song_on_graph.replace("{letter}", c.querySelector(".sl").textContent)), on()[0].title);
  const others = () => cells().filter(c => !c.classList.contains("on"));
  if (codes.length >= 3) {
    say("at three the other cells are disabled and say why", others().length === 0 || others().every(c => c.disabled && c.title === UI.compare_full), others().map(c => c.title).join(" | "));
  } else {
    say("under three the other cells offer to add", others().every(c => !c.disabled && c.title === UI.song_add), others().map(c => c.title).join(" | "));
  }
  // an on-graph extra clicked: off it comes, the graph and the marks follow
  const extra = on()[1];
  click(extra);
  await wait(700);
  say("clicking an on-graph cell takes it off the graph", gbody().fw.charts.map(c => c.code).join() === codes.filter(c => c !== extra.dataset.code).join() &&
      !sbody().querySelector('.cell.on[data-code="' + extra.dataset.code + '"]'), gbody().fw.charts.map(c => c.code).join());
  say("the button is no longer pressed", cmp().getAttribute("aria-pressed") === "false");
  // a cell not on the graph clicked in compare mode: on it goes
  const back = cells().find(c => c.dataset.code === extra.dataset.code);
  say("its cell now offers to add", back.title === UI.song_add && !back.disabled, back.title);
  click(back);
  await wait(700);
  say("clicking it again adds it back, as the last letter", gbody().fw.charts.map(c => c.code).pop() === extra.dataset.code &&
      sbody().querySelector('.cell.on[data-code="' + extra.dataset.code + '"] .sl').textContent === ["A", "B", "C"][gbody().fw.charts.length - 1],
      gbody().fw.charts.map(c => c.code).join());
  // the primary clicked in compare mode: off it comes and the next is promoted
  const primary = sbody().querySelector(".cell.here");
  const next = gbody().fw.charts[1].code;
  click(primary);
  await wait(700);
  say("clicking the primary's cell promotes the next chart", pane.getAttribute("aria-label").endsWith(": " + next) && sbody().querySelector(".cell.here").dataset.code === next, pane.getAttribute("aria-label"));
  // the pressed button, pressed again: one chart
  click(cmp());
  await wait(700);
  click(cmp());
  await wait(700);
  say("the pressed button takes its levels down to one chart", gbody().fw.charts.length === 1 && cmp().getAttribute("aria-pressed") === "false" && !sbody().querySelector(".cell.on"),
      gbody().fw.charts.length);
  say("and the cells offer to open again", cells().filter(c => !c.classList.contains("here")).every(c => c.title === UI.song_open && !c.disabled));
}

// --- Escape closes the pane and hands focus back ----------------------------------------
key("Escape");
await wait(400);
say("Escape closes the pane", !pane.classList.contains("on") && params().get("code") === null, location.search);
say("and focus returns to a table row", here() && here().matches("tbody tr"), here() && here().tagName);
say("no row stays highlighted", !document.querySelector("#body tr.sel"));

// the phone layout is measured in narrow.js, inside its 390px iframe
click(row);
await wait(800);
say("every cell is a touch target", cells().every(c => c.getBoundingClientRect().height >= 44), cells().map(c => Math.round(c.getBoundingClientRect().height)).join());
key("Escape");
done();
