// The song panel (section 07): every chart of a song, opened from a graph
// heading, stacked under a graph opened from a cell, closed one layer at a
// time, and laid out for a phone. Derives everything from the payload.
import { BOOT, say, skip, done, wait, click, key, ready, params } from "./lib.js";
await ready();

const { ui: UI, valueOrder: VALUE_ORDER } = BOOT;
const LEVELS = ["Expert", "Hard", "Medium", "Easy"];
const here = () => document.activeElement;
const modal = document.getElementById("modal"), panel = document.getElementById("song");

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

// --- from the graph heading -------------------------------------------------------
const row = document.querySelector('#body tr[data-code="' + code + '"]');
row.focus();
click(row);
await wait(500);
const sng = modal.querySelector(".mhead a.sng[data-song]");
say("the graph heading links to the song", !!sng && sng.dataset.song === key0 && sng.getAttribute("href") === "?song=" + key0, sng && sng.outerHTML);
say("the two links share one right-aligned group", !!sng && sng.closest(".lnk") && !!sng.closest(".lnk").querySelector("a.rpt"));
click(sng);
await wait(600);
say("the panel opens and the graph closes", panel.classList.contains("on") && !modal.classList.contains("on"));
say("the URL names the song, not the code", params().get("song") === key0 && params().get("code") === null, location.search);
say("focus is on the cell the reader came from", here() && here().matches('#song .cell.here[data-code="' + code + '"]'), here() && here().outerHTML);
say("the panel is labelled with the song", (panel.getAttribute("aria-label") || "").startsWith(UI.song_label + ": " + get(first, "Song Title")), panel.getAttribute("aria-label"));

// --- the grid -----------------------------------------------------------------------
const prefix = code.slice(0, 8);
const own = charts.filter(c => String(get(c, "Code")).slice(0, 8) === prefix);
const insts = [...panel.querySelectorAll(".sgrid .inst")].map(e => { const c = e.cloneNode(true); c.querySelectorAll(".tier, .cmp").forEach(x => x.remove()); return c.textContent.trim(); });
const wantTypes = VALUE_ORDER.Type.filter(ty => own.some(c => get(c, "Type") === ty));
say("instrument rows in VALUE_ORDER order", insts.join() === wantTypes.join(), insts.join() + " vs " + wantTypes.join());
say("level headings are the chips' order", [...panel.querySelectorAll(".sgrid .lvlh")].map(e => e.textContent).join() === LEVELS.join());
const cells = [...panel.querySelectorAll(".sgrid .cell:not(.none)")];
say("one cell per chart of this folder", cells.length === own.length, cells.length + " vs " + own.length);
say("each cell names a chart at its column's level", cells.every(c => {
  const chart = own.find(x => get(x, "Code") === c.dataset.code);
  const col = [...c.parentElement.children].indexOf(c) % 5;   // corner + 4 levels per row on a desktop grid
  return chart && LEVELS[col - 1] === get(chart, "Level") && c.dataset.code[8] === { Expert: "X", Hard: "H", Medium: "M", Easy: "E" }[get(chart, "Level")];
}), cells.map(c => c.dataset.code).join());
say("every cell prints D to two places or none", cells.every(c => /^\d+(\.\d{2})?$/.test(c.querySelector("b").textContent)), cells.map(c => c.querySelector("b").textContent).join());
if (own.some(c => c.columns.includes("Pct"))) {
  say("and the percentile beneath it", cells.every(c => /^\d+$/.test((c.querySelector("small") || {}).textContent || "")), cells.map(c => (c.querySelector("small") || {}).textContent).join());
}
const tiers = [...panel.querySelectorAll(".sgrid .inst")].map(e => !!e.querySelector(".tier"));
const wantTiers = wantTypes.map(ty => own.some(c => get(c, "Type") === ty && typeof get(c, "CalcTier") === "number"));
say("the tier appears once per instrument that has an Expert chart", tiers.join() === wantTiers.join(), tiers.join() + " vs " + wantTiers.join());
say("blank cells say which level is missing", [...panel.querySelectorAll(".sgrid .cell.none")].every(c => new RegExp(UI.song_no_level.replace("{level}", "(Expert|Hard|Medium|Easy)")).test(c.title)));
say("no report or song link inside the panel", !panel.querySelector(".rpt, .sng"));
const multi = wantTypes.filter(ty => own.filter(c => get(c, "Type") === ty).length > 1);
say("a compare button per instrument with more than one level", panel.querySelectorAll(".sgrid .cmp").length === multi.length &&
    [...panel.querySelectorAll(".sgrid .cmp")].every(b => b.dataset.cmp.split(",").length >= 2 && b.dataset.cmp.split(",").length <= 3), panel.querySelectorAll(".sgrid .cmp").length + " vs " + multi.length);

// --- Tab stays inside ---------------------------------------------------------------
const inside = [...panel.querySelectorAll('a[href], button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])')].filter(e => e.offsetParent !== null);
for (let i = 0; i < inside.length + 1; i++) key("Tab");
say("Tab from the cell stays inside the panel and wraps", panel.contains(here()) && inside.includes(here()), here().className);

// --- a cell opens the graph over the panel -------------------------------------------
const other = cells.find(c => c.dataset.code !== code) || cells[0];
other.focus();
click(other);
await wait(600);
say("a cell opens the graph over the panel", modal.classList.contains("on") && panel.classList.contains("on") &&
    modal.getAttribute("aria-label").endsWith(": " + other.dataset.code), modal.getAttribute("aria-label"));
key("Escape");
await wait(300);
say("Escape closes the graph only and focuses the cell", !modal.classList.contains("on") && panel.classList.contains("on") && here() === other, here().outerHTML && here().outerHTML.slice(0, 60));
if (multi.length) {
  const cmp = panel.querySelector(".sgrid .cmp");
  click(cmp);
  await wait(700);
  const codes = cmp.dataset.cmp.split(",");
  say("Compare all levels opens the instrument's levels on one graph", modal.classList.contains("on") &&
      modal.querySelector(".gbody").fw && modal.querySelector(".gbody").fw.charts.map(c => c.code).join() === codes.join(),
      modal.querySelector(".gbody").fw && modal.querySelector(".gbody").fw.charts.map(c => c.code).join());
  key("Escape");
  await wait(300);
}
key("Escape");
await wait(500);
say("Escape again closes the panel", !panel.classList.contains("on") && params().get("song") === null && params().get("code") === null, location.search);
say("and focus returns to a table row", here() && here().matches("tbody tr"), here() && here().tagName);

// --- the title pip -------------------------------------------------------------------
const pip = row.querySelector("td.song .sp[data-song]");
say("the title cell carries the pip", !!pip && pip.dataset.song === key0 && pip.title === UI.song_view, pip && pip.outerHTML);
click(pip);
await wait(600);
say("the pip opens the panel without a graph", panel.classList.contains("on") && !modal.classList.contains("on") && params().get("song") === key0);
say("reopening for the same key keeps the folder", panel.querySelector(".sgrid .cell.here") && panel.querySelector(".sgrid .cell.here").dataset.code === code);

// the phone layout is measured in narrow.js, inside its 390px iframe
say("every cell is a touch target", [...panel.querySelectorAll(".sgrid .cell")].every(c => c.getBoundingClientRect().height >= 44));
key("Escape");
done();
