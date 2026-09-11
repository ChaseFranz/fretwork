// Compare (section 06): up to three charts on one graph, shareable as
// ?code=A&vs=B,C, chosen from the picker or from the table. Opened by the
// runner with compare_query: an Expert chart and the same song's Hard.
import { BOOT, rows as sheetRows, say, skip, done, wait, click, key, ready, params } from "./lib.js";
await ready();

const { ui: UI, render: RENDER } = BOOT;
const p = params();
const sheet = p.get("sheet") || Object.keys(BOOT.data)[0];
const rows = await sheetRows(sheet);
const cols = BOOT.data[sheet].columns;
const col = n => cols.indexOf(n);
const modal = document.getElementById("modal");
const gbody = () => modal.querySelector(".gbody");
const legend = () => [...modal.querySelectorAll(".legend li")];
const readout = () => modal.querySelector(".readout").textContent;
const code = p.get("code"), vs = p.get("vs");
await wait(700);

say("the link named two charts", !!code && !!vs && !vs.includes(","), code + " vs " + vs);
say("the graph opened on the primary", modal.classList.contains("on") && modal.getAttribute("aria-label").endsWith(": " + code), modal.getAttribute("aria-label"));
say("two charts are mounted", gbody().fw && gbody().fw.charts.length === 2 && gbody().fw.charts.map(c => c.code).join() === code + "," + vs,
    gbody().fw && gbody().fw.charts.map(c => c.code).join());
say("the legend has one entry per chart, lettered", legend().length === 2 && legend()[0].textContent.trim().startsWith("A ") &&
    legend()[1].textContent.trim().startsWith("B "), legend().map(l => l.textContent.trim()).join(" | "));
say("each entry has a remove button", legend().every(l => l.querySelector("button.rm[data-rm]")));
say("the series colours are the profile's, in order", legend()[0].querySelector(".sw").style.borderColor !== legend()[1].querySelector(".sw").style.borderColor);
const many = new RegExp("^" + UI.graph_readout_many.replace(/[.*+?^${}()|[\]\\]/g, "\\$&").replace(/\\\{\w+\\\}/g, ".+") + "$");
say("the readout carries a ~D per chart", many.test(readout()) && /A \S+\s+B \S+/.test(readout()), JSON.stringify(readout()));
await wait(400);
say("the URL carries vs", params().get("vs") === vs && params().get("code") === code, location.search);

// --- the picker -------------------------------------------------------------------
const cmp = modal.querySelector('[data-act="compare"]');
click(cmp);
await wait(400);
const picker = modal.querySelector(".picker");
say("Compare reveals the picker", !picker.classList.contains("d-none") && cmp.getAttribute("aria-expanded") === "true");
say("focus moves to the search box", document.activeElement && document.activeElement.id === "cmpq", document.activeElement && document.activeElement.id);
const listed = () => [...modal.querySelectorAll("#cmpr [data-add]")].map(b => b.dataset.add);
const stem = code.slice(0, 8);
const sameSong = rows.filter(r => String(r[col("Code")]).slice(0, 8) === stem && r[col("Code")] !== code && r[col("Code")] !== vs).map(r => r[col("Code")]);
say("an empty box lists the same song's other charts", listed().length > 0 && listed().every(c => c.slice(0, 8) === stem) &&
    sameSong.every(c => listed().includes(c)) && !listed().includes(code) && !listed().includes(vs), listed().join());
// a chart from the sheet's top rows (the runner stages the curve files of the
// first 40 rows of each sheet), found by typing part of its title
const other = rows.slice(0, 40).find(r => String(r[col("Code")]).slice(0, 8) !== stem);
const q = document.getElementById("cmpq");
q.value = String(other[col("Song Title")]).slice(0, 8); q.dispatchEvent(new Event("input", { bubbles: true }));
await wait(50);
const artistRows = rows.filter(r => String(r[col("Artist")]).toLowerCase().includes(q.value.toLowerCase()) ||
  String(r[col("Song Title")]).toLowerCase().includes(q.value.toLowerCase()) || String(r[col("Code")]).toLowerCase().includes(q.value.toLowerCase()))
  .map(r => r[col("Code")]).filter(c => c !== code && c !== vs);
say("typing narrows the list to matching charts, twelve at most", listed().length > 0 && listed().length <= 12 &&
    listed().every(c => artistRows.includes(c) || !rows.some(r => r[col("Code")] === c)), q.value + " -> " + listed().join());
const third = listed().includes(other[col("Code")]) ? other[col("Code")] : listed()[0];
click(modal.querySelector('#cmpr [data-add="' + third + '"]'));
await wait(600);
say("adding a third draws three charts", gbody().fw && gbody().fw.charts.length === 3 && legend().length === 3, gbody().fw && gbody().fw.charts.length);
await wait(400);
say("the URL names both extras", params().get("vs") === vs + "," + third, params().get("vs"));
click(modal.querySelector('[data-act="compare"]'));
await wait(400);
say("the picker is full at three", document.getElementById("cmpq").disabled && modal.querySelector("#cmpr").textContent.includes(UI.compare_full),
    modal.querySelector("#cmpr").textContent);

// --- remove: an extra, then the primary, which promotes ------------------------------
click(modal.querySelector('.legend .rm[data-rm="' + third + '"]'));
await wait(600);
say("removing an extra leaves two", gbody().fw.charts.map(c => c.code).join() === code + "," + vs, gbody().fw.charts.map(c => c.code).join());
click(modal.querySelector('.legend .rm[data-rm="' + code + '"]'));
await wait(600);
say("removing the primary promotes the first extra", modal.getAttribute("aria-label").endsWith(": " + vs) && gbody().fw.charts.length === 1 &&
    legend().length === 3, modal.getAttribute("aria-label") + " " + legend().length);
await wait(400);
say("and the URL follows", params().get("code") === vs && params().get("vs") === null, location.search);

// --- pick from the table ----------------------------------------------------------------
click(modal.querySelector('[data-act="pick"]'));
await wait(100);
const bar = document.getElementById("pick");
say("picking hides the graph and shows the bar", !modal.classList.contains("on") && !bar.classList.contains("d-none") &&
    bar.textContent.includes(UI.compare_cancel), bar.textContent);
const target = [...document.querySelectorAll("#body tr[data-code]")].find(tr => tr.dataset.code !== vs);
if (!target) {
  skip("pick from the table", "only one row on screen");
} else {
  click(target);
  await wait(700);
  say("a row click adds it and brings the graph back", modal.classList.contains("on") && bar.classList.contains("d-none") &&
      gbody().fw && gbody().fw.charts.map(c => c.code).join() === vs + "," + target.dataset.code, gbody().fw && gbody().fw.charts.map(c => c.code).join());
  click(modal.querySelector('[data-act="pick"]'));
  await wait(100);
  key("Escape");
  await wait(600);
  say("Escape while picking brings the graph back unchanged", modal.classList.contains("on") && gbody().fw.charts.length === 2 &&
      params().get("vs") === target.dataset.code, location.search);
}
key("Escape");
await wait(400);
say("closing clears the comparison", !modal.classList.contains("on") && params().get("code") === null && params().get("vs") === null, location.search);
done();
