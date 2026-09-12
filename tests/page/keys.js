// Keyboard access: one tab stop for the table, arrows inside it, Enter opens,
// Escape returns focus, and the chrome reports its state to a screen reader.
import { BOOT, rows as sheetRows, say, skip, done, wait, key, click, chip, ready, params, shown } from "./lib.js";
await ready();

const here = () => document.activeElement;
const rowOf = el => el && el.closest ? el.closest("tr[data-code]") : null;

const stops = [...document.querySelectorAll('a[href],button,input,[tabindex="0"]')].filter(e => e.offsetParent !== null);
say("the table is one tab stop", stops.filter(e => e.matches("tr")).length === 1,
    stops.filter(e => e.matches("tr")).length + " row(s) in the tab order");

// the DOM holds a window of the view (section 17): End and Home repaint it,
// so rows are compared by code across them and `first` is looked up again
let first = document.querySelector("#body tr[data-code]");
first.focus();
say("a row takes focus", here() === first, here().tagName);
key("ArrowDown");
say("ArrowDown moves down a row", rowOf(here()) === first.nextElementSibling, rowOf(here()) && rowOf(here()).dataset.code);
say("focus does not multiply tab stops", document.querySelectorAll('#body tr[tabindex="0"]').length === 1);
key("ArrowUp");
say("ArrowUp comes back", here() === first);
key("End");
const lastPainted = () => [...document.querySelectorAll("#body tr[data-code]")].pop();
say("End jumps to the last row", rowOf(here()) === lastPainted() && parseInt(lastPainted().querySelector("td.rank").textContent, 10) === shown(),
    lastPainted() && lastPainted().querySelector("td.rank").textContent + " of " + shown());
key("Home");
say("Home jumps back to the first", rowOf(here()) && rowOf(here()).dataset.code === first.dataset.code, rowOf(here()) && rowOf(here()).dataset.code);
first = rowOf(here());
key("ArrowUp");
say("ArrowUp at the top stays put", here() === first);
key("PageDown");
say("PageDown moves several rows", rowOf(here()) && rowOf(here()) !== first, rowOf(here()) && rowOf(here()).dataset.code);
key("Home");
first = rowOf(here());

// --- Enter opens the pane, focus stays on the row, Escape closes -----------------
// (section 14: the pane is a region under the table, not a dialog, so there is
// no trap; Tab walks into it in document order and the arrows keep moving rows)
key("Enter");
await wait(300);
const pane = document.getElementById("pane");
say("Enter opens the pane", pane.classList.contains("on"));
say("focus stays on the row", here() === first, here().id || here().tagName);
say("the pane is labelled with the code", (pane.getAttribute("aria-label") || "").endsWith(": " + first.dataset.code),
    pane.getAttribute("aria-label"));
say("the row is highlighted", first.classList.contains("sel") && first.getAttribute("aria-current") === "true");
say("Tab is not trapped", key("Tab"));
await wait(500);
// with the pane open the arrows move the selection and the graph follows
key("ArrowDown", first);
const second = rowOf(here());
say("ArrowDown still moves the focus", second === first.nextElementSibling, second && second.dataset.code);
await wait(500);
say("and the graph follows the row", (pane.getAttribute("aria-label") || "").endsWith(": " + second.dataset.code) && second.classList.contains("sel") && !first.classList.contains("sel"),
    pane.getAttribute("aria-label"));
say("the URL follows too", params().get("code") === second.dataset.code, location.search);
key("ArrowUp", second);
await wait(500);
say("ArrowUp brings the graph back", (pane.getAttribute("aria-label") || "").endsWith(": " + first.dataset.code));
// Enter on the open chart's row closes the pane
key("Enter", first);
await wait(300);
say("Enter on the open row closes the pane", !pane.classList.contains("on") && here() === first);
key("Enter", first);
await wait(400);
say("and Enter again reopens it", pane.classList.contains("on"));
// the pane's controls are reachable from the row by Tab, in document order
const canvas = pane.querySelector(".gbody canvas");
if (canvas) {
  canvas.focus();
  say("the canvas is an application", here() === canvas && here().getAttribute("role") === "application");
  const before = pane.querySelector(".readout").textContent;
  key("ArrowRight", here());
  say("Right on the canvas changes the readout, not the row", pane.querySelector(".readout").textContent !== before && here() === canvas,
      pane.querySelector(".readout").textContent);
}
key("Escape");
await wait(300);
say("Escape closes it", !pane.classList.contains("on"));
say("focus returns to the row you opened", here() === first, here().tagName);

// --- a copy's link swaps the chart in place (section 10) ---------------------------
const sheet = Object.keys(BOOT.data)[0];
const rows = await sheetRows(sheet);
const columns = BOOT.data[sheet].columns;
const onScreen = new Set([...document.querySelectorAll("#body tr[data-code]")].map(tr => tr.dataset.code));
const dup = columns.includes("Copies") && rows.find(r => r[columns.indexOf("Copies")] > 1 && onScreen.has(r[columns.indexOf("Code")]));
if (!dup) {
  skip("copies link", "no duplicated chart on the opening view");
} else {
  const row = document.querySelector('#body tr[data-code="' + dup[columns.indexOf("Code")] + '"]');
  row.focus();
  key("Enter");
  await wait(300);
  const link = pane.querySelector(".mhead .copies a[data-code]");
  say("the heading lists the other copy", !!link && link.getAttribute("href") === "?code=" + link.dataset.code, link && link.outerHTML);
  click(link);
  await wait(400);
  say("clicking it keeps the pane open on the other code", pane.classList.contains("on") &&
      (pane.getAttribute("aria-label") || "").endsWith(": " + link.dataset.code), pane.getAttribute("aria-label"));
  say("the URL's code follows", params().get("code") === link.dataset.code, location.search);
  say("the new heading points back", !!pane.querySelector('.mhead .copies a[data-code="' + row.dataset.code + '"]'));
  const sel = document.querySelector("#body tr.sel");
  say("the highlight follows to the copy's row when it is on screen", onScreen.has(link.dataset.code) ? sel && sel.dataset.code === link.dataset.code : sel === null,
      sel && sel.dataset.code);
  key("Escape");
  await wait(300);
  say("Escape still returns focus to the row you started from", !pane.classList.contains("on") && here() === row, here().tagName);
}

// --- sorting from the keyboard keeps your place --------------------------------------
const sortBtn = () => document.querySelector('#head th[data-c="CalcTier"] .lbl');
sortBtn().focus();
click(sortBtn());
await wait(50);
say("focus survives the repaint a sort causes", here() === sortBtn() || (here().dataset && here().dataset.sort === "CalcTier"),
    here().tagName + " " + (here().dataset ? here().dataset.sort : ""));
say("the column reports its sort", document.querySelector('#head th[data-c="CalcTier"]').getAttribute("aria-sort") === "descending",
    document.querySelector('#head th[data-c="CalcTier"]').getAttribute("aria-sort"));

// --- chips say what they are (toggle one that can go dark) -----------------------
click(chip("levels", "Hard"));
say("a lit chip is pressed", chip("levels", "Hard").getAttribute("aria-pressed") === "true");
click(chip("levels", "Hard"));
say("and unpressed once it is off", chip("levels", "Hard").getAttribute("aria-pressed") === "false");

// --- the panel triggers report their state ---------------------------------------------
const cols = document.getElementById("cols");
say("Columns starts collapsed", cols.getAttribute("aria-expanded") === "false");
click(cols);
say("and reports itself open", cols.getAttribute("aria-expanded") === "true");
key("Escape");
say("Escape collapses it again", cols.getAttribute("aria-expanded") === "false");
const flt = () => document.querySelector('#head th[data-c="Level"] .flt');
click(flt());
say("a filter caret reports expanded", flt().getAttribute("aria-expanded") === "true", flt().getAttribute("aria-expanded"));
key("Escape");
say("and collapsed after Escape", flt().getAttribute("aria-expanded") === "false", flt().getAttribute("aria-expanded"));

done();
