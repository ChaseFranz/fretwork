// The details pane (section 14): a region under the table rather than a
// dialog. The open chart's row is highlighted and the mark survives a sort,
// a filter and a sheet switch; the pane stays open through all three; the
// heading's caret collapses it to a strip; the grip drags its height and the
// height is remembered; Escape closes one thing at a time.
import { BOOT, rows as sheetRows, say, skip, done, wait, click, key, pt, chip, ready, params } from "./lib.js";
await ready();

const { ui: UI } = BOOT;
const here = () => document.activeElement;
const pane = document.getElementById("pane");
const wrap = document.querySelector(".fw-wrap");
const sel = () => document.querySelector("#body tr.sel");
const label = () => pane.getAttribute("aria-label") || "";

say("the pane is a labelled region, closed to start", pane.getAttribute("role") === "region" && !pane.classList.contains("on"));
say("it follows the table in the document", !!(document.getElementById("grid").compareDocumentPosition(pane) & Node.DOCUMENT_POSITION_FOLLOWING));

// --- open, and the table shrinks -------------------------------------------------------
const tableBefore = wrap.getBoundingClientRect().height;
const rows = [...document.querySelectorAll("#body tr[data-code]")];
const second = rows[1] || rows[0];
second.focus();
click(second);
await wait(600);
say("a row click opens the pane on its chart", pane.classList.contains("on") && label().endsWith(": " + second.dataset.code), label());
say("the table is shorter by the pane's height", wrap.getBoundingClientRect().height < tableBefore && Math.abs(tableBefore - wrap.getBoundingClientRect().height - pane.getBoundingClientRect().height) <= 2,
    Math.round(tableBefore) + " -> " + Math.round(wrap.getBoundingClientRect().height) + " with a " + Math.round(pane.getBoundingClientRect().height) + "px pane");
say("the pane stands on the stylesheet's height", Math.abs(pane.getBoundingClientRect().height - 0.46 * innerHeight) <= 2, Math.round(pane.getBoundingClientRect().height) + " vs " + Math.round(0.46 * innerHeight));
say("the row is highlighted and current", sel() === second && second.getAttribute("aria-current") === "true");
say("it holds the table's tab stop", second.tabIndex === 0 && document.querySelectorAll('#body tr[tabindex="0"]').length === 1);
say("focus stayed on the row", here() === second, here().tagName);
say("the row tip no longer promises a graph alone", second.title.endsWith(UI.row_tip), JSON.stringify(second.title));

// --- the mark survives a sort, a filter and a sheet switch -----------------------------
const code = second.dataset.code;
click(document.querySelector('#head th[data-c="Song Title"] .lbl'));
await wait(100);
say("sorted, the pane is still open on the same chart", pane.classList.contains("on") && label().endsWith(": " + code));
say("and the mark is on the same row, wherever it went", sel() && sel().dataset.code === code, sel() && sel().dataset.code);
say("which holds the tab stop", sel() && sel().tabIndex === 0);
const q = document.getElementById("q");
q.value = "zzzz-no-such-song"; q.dispatchEvent(new Event("input", { bubbles: true }));
await wait(100);
say("filtered away, the pane stays open", pane.classList.contains("on") && label().endsWith(": " + code) && !sel(), label());
q.value = ""; q.dispatchEvent(new Event("input", { bubbles: true }));
await wait(100);
say("and the mark is back once the row is", sel() && sel().dataset.code === code);
const sheets = [...document.querySelectorAll("#sheets button")];
if (sheets.length > 1) {
  click(sheets[1]);
  await wait(800);
  say("on another sheet the pane is still open", pane.classList.contains("on") && label().endsWith(": " + code) && !sel());
  click(sheets[0]);
  await wait(800);
  say("and the mark returns with the sheet", sel() && sel().dataset.code === code, sel() && sel().dataset.code);
}
click(document.querySelector('#head th[data-c="D"] .lbl'));
await wait(100);

// --- clicking the open row again closes; a different row swaps -----------------------------
const selRow = sel();
click(selRow);
await wait(300);
say("clicking the open row closes the pane", !pane.classList.contains("on") && !sel() && params().get("code") === null);
say("the table has its height back", Math.abs(wrap.getBoundingClientRect().height - tableBefore) <= 2, Math.round(wrap.getBoundingClientRect().height));
const first = document.querySelector("#body tr[data-code]");
click(first);
await wait(500);
const other = [...document.querySelectorAll("#body tr[data-code]")].find(tr => tr !== first);
click(other);
await wait(500);
say("clicking another row swaps the chart in place", pane.classList.contains("on") && label().endsWith(": " + other.dataset.code) && sel() === other && !first.classList.contains("sel"));

// --- collapse -------------------------------------------------------------------------
const pmin = () => pane.querySelector(".pbtns .pmin");
say("the collapse button reports the pane expanded", pmin().getAttribute("aria-expanded") === "true" && pmin().getAttribute("aria-label") === UI.pane_collapse);
click(pmin());
await wait(200);
say("collapsed, the pane is its heading", pane.classList.contains("min") && pane.getBoundingClientRect().height < 80 && !pane.querySelector(".gbody").offsetParent, Math.round(pane.getBoundingClientRect().height));
say("the button now offers to expand", pmin().getAttribute("aria-expanded") === "false" && pmin().getAttribute("aria-label") === UI.pane_expand);
say("the heading is still there", pane.querySelector(".mhead strong") && pane.querySelector(".mhead").offsetParent !== null);
// arrows move the selection while collapsed and it stays collapsed
other.focus();
key("ArrowDown", other);
await wait(400);
say("the arrows still move the selection while collapsed", sel() && sel() !== other && label().endsWith(": " + sel().dataset.code) && pane.classList.contains("min"), label());
// a click on a new row expands it
const third = [...document.querySelectorAll("#body tr[data-code]")].find(tr => tr !== sel() && tr !== other);
click(third);
await wait(500);
say("a click on a new row expands it again", !pane.classList.contains("min") && label().endsWith(": " + third.dataset.code));

// --- the grip drags the height, and it is remembered ---------------------------------------
const grip = pane.querySelector(".pgrip");
say("the grip is a separator with a tip", grip.getAttribute("role") === "separator" && grip.title === UI.pane_resize_tip);
const h0 = pane.getBoundingClientRect().height;
const top = pane.getBoundingClientRect().top;
grip.dispatchEvent(new PointerEvent("pointerdown", { clientY: top, bubbles: true, cancelable: true, pointerId: 1 }));
document.dispatchEvent(new PointerEvent("pointermove", { clientY: top - 60, bubbles: true, pointerId: 1 }));
document.dispatchEvent(new PointerEvent("pointerup", { clientY: top - 60, bubbles: true, pointerId: 1 }));
await wait(100);
const h1 = pane.getBoundingClientRect().height;
say("dragging the grip up makes the pane taller", Math.abs(h1 - (h0 + 60)) <= 2, Math.round(h0) + " -> " + Math.round(h1));
say("the canvas followed the new height", pane.querySelector(".gbody canvas") && pane.querySelector(".gbody canvas").getBoundingClientRect().bottom <= pane.getBoundingClientRect().bottom + 1);
let stored = null;
try { stored = localStorage.getItem("fw.pane"); } catch (e) {}
say("the height is remembered in fw.pane", stored === String(Math.round(h1)), stored + " vs " + Math.round(h1));
grip.dispatchEvent(new PointerEvent("pointerdown", { clientY: top - 60, bubbles: true, cancelable: true, pointerId: 1 }));
document.dispatchEvent(new PointerEvent("pointermove", { clientY: innerHeight, bubbles: true, pointerId: 1 }));
document.dispatchEvent(new PointerEvent("pointerup", { clientY: innerHeight, bubbles: true, pointerId: 1 }));
await wait(100);
say("it cannot be dragged below its minimum", pane.getBoundingClientRect().height >= 140 && pane.getBoundingClientRect().height < h0, Math.round(pane.getBoundingClientRect().height));
grip.dispatchEvent(new PointerEvent("pointerdown", { clientY: pane.getBoundingClientRect().top, bubbles: true, cancelable: true, pointerId: 1 }));
document.dispatchEvent(new PointerEvent("pointermove", { clientY: -500, bubbles: true, pointerId: 1 }));
document.dispatchEvent(new PointerEvent("pointerup", { clientY: -500, bubbles: true, pointerId: 1 }));
await wait(100);
say("nor over the table's last rows", wrap.getBoundingClientRect().height >= 100, Math.round(wrap.getBoundingClientRect().height) + " left for the table");
try { localStorage.removeItem("fw.pane"); } catch (e) {}

// --- Escape closes one thing at a time --------------------------------------------------------
click(pane.querySelector('[data-act="compare"]'));
await wait(300);
say("Compare opens the picker with the box focused", here() && here().id === "cmpq");
key("Escape");
await wait(100);
say("Escape closes the picker, not the pane", pane.classList.contains("on") && pane.querySelector(".picker").classList.contains("d-none") && here() && here().dataset.act === "compare");
click(document.querySelector('#head th[data-c="Level"] .flt'));
await wait(100);
key("Escape");
say("Escape closes a filter dropdown, not the pane", pane.classList.contains("on") && !document.getElementById("dd").classList.contains("show"));
key("Escape");
await wait(300);
say("the next Escape closes the pane and focuses its row", !pane.classList.contains("on") && here() === third, here().tagName);

// --- the close button ------------------------------------------------------------------------
click(third);
await wait(400);
click(pane.querySelector('.pbtns [data-act="close"]'));
await wait(300);
say("the close button closes it too", !pane.classList.contains("on") && here() === third);
done();
