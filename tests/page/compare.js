// Compare (section 06): up to three charts on one graph, shareable as
// ?code=A&vs=B,C, chosen by picking a row from the table. Opened by the
// runner with compare_query: an Expert chart and the same song's Hard.
import { BOOT, rows as sheetRows, say, skip, done, wait, click, key, ready, params } from "./lib.js";
await ready();

const { ui: UI, render: RENDER } = BOOT;
const p = params();
const sheet = p.get("sheet") || Object.keys(BOOT.data)[0];
const rows = await sheetRows(sheet);
const cols = BOOT.data[sheet].columns;
const col = n => cols.indexOf(n);
const modal = document.getElementById("pane");
const gbody = () => modal.querySelector(".gbody");
const legend = () => [...modal.querySelectorAll(".legend li")];
const readout = () => modal.querySelector(".readout").textContent;
const code = p.get("code"), vs = p.get("vs");
await wait(700);

say("the link named two charts", !!code && !!vs && !vs.includes(","), code + " vs " + vs);
say("the pane opened on the primary", modal.classList.contains("on") && modal.getAttribute("aria-label").endsWith(": " + code), modal.getAttribute("aria-label"));
say("two charts are mounted", gbody().fw && gbody().fw.charts.length === 2 && gbody().fw.charts.map(c => c.code).join() === code + "," + vs,
    gbody().fw && gbody().fw.charts.map(c => c.code).join());
say("the legend has one entry per chart, lettered", legend().length === 2 && legend()[0].textContent.trim().startsWith("A ") &&
    legend()[1].textContent.trim().startsWith("B "), legend().map(l => l.textContent.trim()).join(" | "));
say("each entry has a remove button", legend().every(l => l.querySelector("button.rm[data-rm]")));
// the same song and part twice: the entries name only the level (Expert, Hard)
const rowOf = c => rows.find(r => r[col("Code")] === c);
const levelOnly = (li, r) => li.querySelector(".lt").textContent.trim().split(" ").slice(1).join(" ") ===
  UI.graph_legend_level.replace("{level}", r[col("Level")]);
say("two levels of one song and part are named by level alone", rowOf(code) && rowOf(vs) &&
    rowOf(code)[col("Type")] === rowOf(vs)[col("Type")] && levelOnly(legend()[0], rowOf(code)) && levelOnly(legend()[1], rowOf(vs)),
    legend().map(l => l.querySelector(".lt").textContent.trim()).join(" | "));
say("the series colours are the profile's, in order", legend()[0].querySelector(".sw").style.borderColor !== legend()[1].querySelector(".sw").style.borderColor);
const many = new RegExp("^" + UI.graph_readout_many.replace(/[.*+?^${}()|[\]\\]/g, "\\$&").replace(/\\\{\w+\\\}/g, ".+") + "$");
say("the readout carries a ~D per chart", many.test(readout()) && /A \S+\s+B \S+/.test(readout()), JSON.stringify(readout()));
await wait(400);
say("the URL carries vs", params().get("vs") === vs && params().get("code") === code, location.search);

// --- a third chart, picked from the table -------------------------------------------
// there is no picker of the pane's own: the table's search is the search, so
// a third chart is found by typing in the page's box and clicking its row
const stem = code.slice(0, 8);
say("the tools are the links, Compare with a row, and Save", [...modal.querySelectorAll(".gtools button")].map(b => b.dataset.act).join() === "pick,save" &&
    !modal.querySelector(".picker, #cmpq"), [...modal.querySelectorAll(".gtools button")].map(b => b.dataset.act).join());
const pick = () => modal.querySelector('[data-act="pick"]');   // re-queried: every swap rebuilds the card
say("the button says what it does", pick().textContent === UI.compare_pick && pick().title === UI.compare_pick_tip, pick().textContent);
click(pick());
await wait(100);
const bar = document.getElementById("pick");
say("picking keeps the pane and shows the bar", modal.classList.contains("on") && !bar.classList.contains("d-none") &&
    bar.textContent.includes(UI.compare_cancel), bar.textContent);
say("focus is on a table row, ready to choose", document.activeElement && document.activeElement.matches("#body tr[data-code]"), document.activeElement && document.activeElement.tagName);
// a chart of another song that is on the opening view and in the sheet's top
// rows (the runner stages the curve files of the first 40 rows of each sheet),
// found by typing part of its title into the page's own search box
const onScreen = new Set([...document.querySelectorAll("#body tr[data-code]")].map(tr => tr.dataset.code));
const other = rows.slice(0, 40).find(r => String(r[col("Code")]).slice(0, 8) !== stem && onScreen.has(r[col("Code")]));
const q = document.getElementById("q");
q.value = String(other[col("Song Title")]).slice(0, 8); q.dispatchEvent(new Event("input", { bubbles: true }));
await wait(100);
const searched = ["Song Title", "Artist", "Album", "Charter", "Release", "Code"].map(col);
const matches = r => searched.some(i => String(r[i] ?? "").toLowerCase().includes(q.value.toLowerCase()));
say("the table's search narrows the rows while picking", document.querySelectorAll("#body tr[data-code]").length > 0 &&
    [...document.querySelectorAll("#body tr[data-code]")].every(tr => matches(rows.find(r => r[col("Code")] === tr.dataset.code))), q.value);
say("the pane is still open on the primary through the repaint", modal.classList.contains("on") && modal.getAttribute("aria-label").endsWith(": " + code));
const target = document.querySelector('#body tr[data-code="' + other[col("Code")] + '"]') || document.querySelector("#body tr[data-code]");
const third = target.dataset.code;
click(target);
await wait(700);
say("clicking a row adds it as the third chart and ends the picking", bar.classList.contains("d-none") && gbody().fw && gbody().fw.charts.length === 3 && legend().length === 3,
    gbody().fw && gbody().fw.charts.map(c => c.code).join());
say("the primary's row stays the selected one", !document.querySelector("#body tr.sel") || document.querySelector("#body tr.sel").dataset.code === code,
    document.querySelector("#body tr.sel") && document.querySelector("#body tr.sel").dataset.code);
q.value = ""; q.dispatchEvent(new Event("input", { bubbles: true }));
await wait(100);
// a different song on the graph: every entry names its song again
const full = (li, r) => li.querySelector(".lt").textContent.trim().includes(String(r[col("Song Title")]));
say("with another song on the graph the entries carry the titles", !rowOf(third) || (rowOf(third)[col("Song Title")] !== rowOf(code)[col("Song Title")]
    ? full(legend()[0], rowOf(code)) && full(legend()[2], rowOf(third)) : true),
    legend().map(l => l.querySelector(".lt").textContent.trim()).join(" | "));
await wait(400);
say("the URL names both extras", params().get("vs") === vs + "," + third, params().get("vs"));
click(pick());
await wait(100);
const fourth = [...document.querySelectorAll("#body tr[data-code]")].find(tr => ![code, vs, third].includes(tr.dataset.code));
if (fourth) {
  click(fourth);
  await wait(500);
  say("a fourth is refused with a hint, and the picking ends", gbody().fw.charts.length === 3 && bar.classList.contains("d-none") &&
      document.getElementById("hint").textContent === UI.compare_full, document.getElementById("hint").textContent);
} else {
  key("Escape");
  await wait(100);
}

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

// --- Escape cancels the picking ------------------------------------------------------------
click(modal.querySelector('[data-act="pick"]'));
await wait(100);
say("picking again shows the bar", !bar.classList.contains("d-none"));
key("Escape");
await wait(300);
say("Escape while picking cancels it and leaves the graph unchanged", modal.classList.contains("on") && bar.classList.contains("d-none") &&
    gbody().fw.charts.length === 1 && params().get("vs") === null, location.search);
done();
