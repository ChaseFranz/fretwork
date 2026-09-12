// Columns, chips, widths and the chooser: the table's interaction contract.
import { BOOT, rows as sheetRows, say, done, wait, pt, click, chip, lit, shown, ready } from "./lib.js";
await ready();

const { ui: UI, order: ORDER, hiddenDefault: HIDDEN_DEFAULT } = BOOT;
const sheet = Object.keys(BOOT.data)[0];
const rows = await sheetRows(sheet);
const cols = BOOT.data[sheet].columns;
const col = n => cols.indexOf(n);
const headCols = () => [...document.querySelectorAll("#head th")].map(th => th.dataset.c);
const seq = a => JSON.stringify(a);

// --- default columns ------------------------------------------------------------
const want = ["Rank", ...ORDER.filter(c => cols.includes(c) && !HIDDEN_DEFAULT.includes(c)),
              ...cols.filter(c => !ORDER.includes(c) && !HIDDEN_DEFAULT.includes(c))];
say("default visible columns are ORDER minus HIDDEN_DEFAULT, Rank first", seq(headCols()) === seq(want),
    seq(headCols()) + " vs " + seq(want));

// --- D prints the same number of decimals in every row ---------------------------
const dCells = [...document.querySelectorAll("#body td.headline")].map(td => td.textContent);
const places = t => (t.split(".")[1] || "").length;
const anyFraction = rows.some(r => typeof r[col("D")] === "number" && !Number.isInteger(r[col("D")]));
say("D cells exist", dCells.length > 0, dCells.length);
say("D decimals agree across rows and match the column rule",
    dCells.every(t => places(t) === (anyFraction ? 2 : 0)), seq([...new Set(dCells.map(places))]));

// --- the Official chip pair -------------------------------------------------------
const expertRows = rows.filter(r => r[col("Level")] === "Expert");
say("Official chip is lit at launch", seq(lit("official")) === seq([UI.official_chip]), seq(lit("official")));
click(chip("official", UI.official_chip));
say("clicking the lit chip clears the filter", lit("official").length === 0 && shown() === expertRows.length,
    seq(lit("official")) + " " + shown() + " vs " + expertRows.length);
click(chip("official", UI.official_chip));
click(chip("official", UI.custom_chip));
say("Official then Custom shows only customs", seq(lit("official")) === seq([UI.custom_chip]) &&
    shown() === expertRows.filter(r => r[col("Official")] === false).length, shown());
click(chip("official", UI.custom_chip));

// --- level chips are a multi-select ---------------------------------------------
click(chip("levels", "Hard"));
say("a second level adds to the first", seq(lit("levels")) === seq(["Expert", "Hard"]), seq(lit("levels")));
click(chip("levels", "Expert"));
say("dropping one keeps the other", seq(lit("levels")) === seq(["Hard"]), seq(lit("levels")));
click(chip("levels", "Hard"));
say("the last one off means every level", lit("levels").length === 4 && shown() === rows.length,
    seq(lit("levels")) + " " + shown());
say("and counts as no filter at all", document.getElementById("clear").classList.contains("d-none"));
click(chip("levels", "Expert"));

// --- column widths ----------------------------------------------------------------
const th = () => document.querySelector('#head th[data-c="Artist"]');
const rz = () => th().querySelector(".rz");
const before = th().getBoundingClientRect().width;
pt("pointerdown", 500, rz());
pt("pointermove", 560, document.body);
pt("pointerup", 560, document.body);
await wait(50);
const after = th().getBoundingClientRect().width;
say("dragging the grip widens the column by the pointer delta", Math.abs(after - before - 60) <= 3,
    before + " -> " + after);
say("the width is remembered", JSON.parse(localStorage.getItem("fw.widths") || "{}").Artist === Math.round(after),
    localStorage.getItem("fw.widths"));
pt("pointerdown", 500, rz());
pt("pointermove", 100, document.body);
pt("pointerup", 100, document.body);
await wait(50);
say("a drag below the minimum stores the minimum (48)", JSON.parse(localStorage.getItem("fw.widths")).Artist === 48,
    localStorage.getItem("fw.widths"));
rz().dispatchEvent(new MouseEvent("dblclick", { bubbles: true }));
await wait(50);
say("double-click hands the width back", !("Artist" in JSON.parse(localStorage.getItem("fw.widths") || "{}")),
    localStorage.getItem("fw.widths"));

// --- the chooser: hide, reorder, reset ------------------------------------------
click(document.getElementById("cols"));
await wait(50);
const box = document.querySelector('#cd input[data-col="Artist"]');
box.click();
await wait(50);
say("unticking a column hides it", !headCols().includes("Artist") &&
    JSON.parse(localStorage.getItem("fw.hidden")).includes("Artist"), seq(headCols()));
box.click();
await wait(50);
const items = [...document.querySelectorAll("#cd .cc[data-col]")];
const first = items[0], third = items[2];
const mid = third.getBoundingClientRect();
first.dispatchEvent(new DragEvent("dragstart", { bubbles: true }));
third.dispatchEvent(new DragEvent("dragover", { bubbles: true, cancelable: true, clientY: mid.top + mid.height - 1 }));
first.dispatchEvent(new DragEvent("dragend", { bubbles: true }));
await wait(50);
const order = JSON.parse(localStorage.getItem("fw.order") || "[]");
say("dragging a chooser row two places down reorders the header", headCols().indexOf(first.dataset.col) === 2 &&
    order.indexOf(first.dataset.col) === 2, seq(headCols().slice(0, 5)) + " order " + seq(order.slice(0, 4)));
click(document.querySelector('#cd [data-act="showall"]'));
await wait(50);
const stored = k => JSON.parse(localStorage.getItem(k) || "null");
say("Reset columns puts all three preferences back to their defaults",
    seq((stored("fw.hidden") || HIDDEN_DEFAULT).slice().sort()) === seq(HIDDEN_DEFAULT.slice().sort()) &&
    (stored("fw.order") || []).length === 0 && Object.keys(stored("fw.widths") || {}).length === 0 && seq(headCols()) === seq(want),
    ["fw.hidden", "fw.order", "fw.widths"].map(k => localStorage.getItem(k)).join(" | "));
document.body.click();

// --- footer request link -----------------------------------------------------------
say("request link is the pack form", /issues\/new\?template=song-pack\.yml$/.test(document.querySelector("#foot a.req").href));

done();
