// The graph on a canvas (section 06): drawn from graph/<code>.json, smoothed
// in the browser to the pinned vector, read out under the pointer and the
// arrow keys, and exported as a PNG named the way render.py names its files.
// Since section 14 it lives in the details pane under the table (#pane).
import { BOOT, rows as sheetRows, say, done, wait, click, key, ready, params } from "./lib.js";
await ready();

const { ui: UI, render: RENDER } = BOOT;
const sheet = Object.keys(BOOT.data)[0];
const rows = await sheetRows(sheet);
const cols = BOOT.data[sheet].columns;
const col = n => cols.indexOf(n);
const modal = document.getElementById("pane");
const gbody = () => modal.querySelector(".gbody");
const readout = () => modal.querySelector(".readout");
const near = (a, b) => Math.abs(a - b) < 1e-9;

say("the page carries the render profile", RENDER && typeof RENDER.color_d === "string" && RENDER.mode === "dark", JSON.stringify(RENDER));

// --- a drums code, or any code with no curve file, is a plain message ------------
if (params().get("code") === "00000000XD") {
  await wait(600);
  say("a code with no curve file shows render_failed", modal.classList.contains("on") &&
      gbody().textContent.includes(UI.render_failed) && !gbody().querySelector("canvas"), gbody().textContent);
  done();
} else {

// --- open the first row's graph ---------------------------------------------------
const row = document.querySelector("#body tr[data-code]");
row.focus();
click(row);
await wait(600);
const canvas = () => gbody().querySelector("canvas");
say("a canvas is mounted", !!canvas(), gbody().innerHTML.slice(0, 80));
say("it is an application for the arrow keys", canvas().getAttribute("role") === "application" &&
    canvas().getAttribute("aria-roledescription") === "difficulty graph" && canvas().tabIndex === 0);
say("it is described by the readout", canvas().getAttribute("aria-describedby") === readout().id && readout().getAttribute("aria-live") === "polite");
say("it is labelled with the song", (canvas().getAttribute("aria-label") || "").startsWith("Difficulty graph of "), canvas().getAttribute("aria-label"));
const card = modal.querySelector(".pcard");
say("the card takes the figure background", getComputedStyle(card).backgroundColor === (() => {
  const s = document.createElement("span"); s.style.color = RENDER.figure_bg; document.body.appendChild(s);
  const c = getComputedStyle(s).color; s.remove(); return c; })(), getComputedStyle(card).backgroundColor);
say("the canvas fills the card's width", Math.abs(canvas().getBoundingClientRect().width - gbody().getBoundingClientRect().width) <= 1,
    canvas().getBoundingClientRect().width + " vs " + gbody().getBoundingClientRect().width);
say("its backing store follows devicePixelRatio", canvas().width === Math.round(canvas().getBoundingClientRect().width * (window.devicePixelRatio || 1)),
    canvas().width + " for " + canvas().getBoundingClientRect().width + " at " + window.devicePixelRatio);

// line 2: the difficulty numbers and the file format
const meta = modal.querySelector(".mmeta");
say("line 2 names D, the tiers and the file", meta && meta.textContent.includes(BOOT.labels.D) && /\.(chart|mid) file/.test(meta.textContent), meta && meta.textContent);
const dCell = row.querySelector("td.headline").textContent;
say("line 2's D agrees with the row", meta.textContent.includes(dCell), dCell);

// legend: the three series, in the profile's colours
const legend = modal.querySelectorAll(".legend li");
say("the legend names the three series", legend.length === 3 && [...legend].map(l => l.textContent.trim()).join() === [UI.graph_d, UI.graph_nps, UI.graph_vps].join(),
    [...legend].map(l => l.textContent.trim()).join());

// --- the pinned vector through the page's own smoothing ---------------------------
const fw = gbody().fw;
say("the test hook is there", !!fw && typeof fw.smooth === "function" && Array.isArray(fw.charts));
const got = fw.smooth({ v: 1, step: 250, window: 1000, tau: 2000, n: 6, win: [0, 1, 3, 2, 0, 4], var: [0, 1, 2, 2, 0, 3] });
const NPS = [0.206319956884, 0.233791139980, 0.249274712958, 0.221722210520, 0.166347919619, 0.113576201083];
const VPS = [0.168201115681, 0.190596834038, 0.200329151998, 0.181904979485, 0.135036063769, 0.090279835296];
const D = [0.186288075129, 0.211092044157, 0.223465862854, 0.200829216391, 0.149876510106, 0.101260262331];
say("smooth() reproduces the pinned vector", [...got.nps].every((v, i) => near(v, NPS[i])) && [...got.vps].every((v, i) => near(v, VPS[i])) &&
    [...got.d].every((v, i) => near(v, D[i])), JSON.stringify([...got.d].map(v => +v.toFixed(12))));
say("the chart's curves are as long as its file says", fw.charts[0].curves.d.length === fw.charts[0].curves.n && fw.charts[0].curves.n > 0, fw.charts[0].curves.n);

// --- readout: pointer, keys -----------------------------------------------------------
const box = canvas().getBoundingClientRect();
const pattern = new RegExp("^" + UI.graph_readout.replace(/[.*+?^${}()|[\]\\]/g, "\\$&").replace(/\\\{\w+\\\}/g, ".+") + "$");
const at0 = readout().textContent;
say("the readout starts at 0:00", at0.startsWith("0:00") && pattern.test(at0), JSON.stringify(at0));
canvas().dispatchEvent(new PointerEvent("pointermove", { clientX: box.left + box.width / 2, clientY: box.top + box.height / 2, bubbles: true }));
const mid = readout().textContent;
say("a pointer at the middle moves the readout", mid !== at0 && pattern.test(mid) && !mid.startsWith("0:00"), JSON.stringify(mid));
say("and quietens the live region while it moves", readout().getAttribute("aria-live") === "off");
canvas().dispatchEvent(new PointerEvent("pointerleave", { bubbles: true }));
say("which is polite again once it leaves", readout().getAttribute("aria-live") === "polite");
canvas().focus();
key("Home", canvas());
say("Home returns to 0:00", readout().textContent.startsWith("0:00"), readout().textContent);
key("ArrowRight", canvas());
const oneStep = readout().textContent;
say("Right moves the cursor by one step", oneStep !== readout.at0 && oneStep.startsWith("0:00") && oneStep !== at0 || fw.charts[0].curves.n < 2, JSON.stringify(oneStep));
for (let i = 0; i < 5; i++) key("ArrowRight", canvas());
say("six steps is 0:02", readout().textContent.startsWith("0:02") || fw.charts[0].curves.n < 7, readout().textContent);
key("End", canvas());
const last = readout().textContent;
say("End jumps to the last sample", last.startsWith(mmssOf((fw.charts[0].curves.n - 1) * fw.charts[0].curves.step)), last);
say("the cursor stays after the pointer leaves", readout().textContent === last);

// --- export --------------------------------------------------------------------------
say("the canvas can be exported as a PNG", canvas().toDataURL("image/png").startsWith("data:image/png"));
const safe = s => (String(s ?? "").replace(/[^A-Za-z0-9 _.-]/g, "").trim().replace(/\s+/g, " ").slice(0, 60)) || "unknown";
const r = rows.find(x => x[col("Code")] === row.dataset.code);
const want = row.dataset.code + "_" + safe(r[col("Artist")]) + " - " + safe(r[col("Song Title")]) + ".png";
say("the export file name is render.py's", fw.outputFilename([row.dataset.code], r, cols) === want, fw.outputFilename([row.dataset.code], r, cols) + " vs " + want);
const blob = await fw.exportPng(fw.charts, { title: "t", meta: "m" });
say("exportPng gives a PNG blob", blob && blob.type === "image/png" && blob.size > 1000, blob && blob.size);

// the heading, the pane's buttons, the meta line, the tools, the picker, then the body: graph beside the song grid
const order = [...modal.querySelectorAll(".pcard > *")].map(e => e.className.split(" ")[0]);
say("the card's order is heading, buttons, meta, tools, picker, body", order.join() === "mhead,pbtns,mmeta,gtools,picker,pbody", order.join());
say("the tools are Compare, Pick and Save", [...modal.querySelectorAll(".gtools button")].map(b => b.textContent).join() === [UI.compare, UI.compare_pick, UI.save_png].join());
say("the body is the graph and the song section", modal.querySelector(".pbody > .gbody") && modal.querySelector(".pbody > .sbody"));

key("Escape");
await wait(200);
say("Escape closes it and focus returns to the row", !modal.classList.contains("on") && document.activeElement === row, document.activeElement.tagName);
say("the hook is cleared on close", gbody() === null || !gbody().fw);
done();
}

function mmssOf(ms) {
  const whole = Math.max(0, Math.round(ms / 1000));
  return Math.floor(whole / 60) + ":" + String(whole % 60).padStart(2, "0");
}
