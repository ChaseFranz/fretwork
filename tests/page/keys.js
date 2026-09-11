// Keyboard access: one tab stop for the table, arrows inside it, Enter opens,
// Escape returns focus, and the chrome reports its state to a screen reader.
import { say, done, wait, key, click, chip } from "./lib.js";

const here = () => document.activeElement;
const rowOf = el => el && el.closest ? el.closest("tr[data-code]") : null;

const stops = [...document.querySelectorAll('a[href],button,input,[tabindex="0"]')].filter(e => e.offsetParent !== null);
say("the table is one tab stop", stops.filter(e => e.matches("tr")).length === 1,
    stops.filter(e => e.matches("tr")).length + " row(s) in the tab order");

const first = document.querySelector("#body tr[data-code]");
first.focus();
say("a row takes focus", here() === first, here().tagName);
key("ArrowDown");
say("ArrowDown moves down a row", rowOf(here()) === first.nextElementSibling, rowOf(here()) && rowOf(here()).dataset.code);
say("focus does not multiply tab stops", document.querySelectorAll('#body tr[tabindex="0"]').length === 1);
key("ArrowUp");
say("ArrowUp comes back", here() === first);
key("End");
say("End jumps to the last row", here() === document.querySelector("#body tr[data-code]:last-child"));
key("Home");
say("Home jumps back to the first", here() === first);
key("ArrowUp");
say("ArrowUp at the top stays put", here() === first);
key("PageDown");
say("PageDown moves several rows", rowOf(here()) && rowOf(here()) !== first, rowOf(here()) && rowOf(here()).dataset.code);
key("Home");

// --- Enter opens the graph, Escape gives focus back ------------------------------
key("Enter");
await wait(200);
const modal = document.getElementById("modal");
say("Enter opens the graph", modal.classList.contains("on"));
say("focus moves into the dialog", here().id === "modal", here().id || here().tagName);
say("dialog is labelled with the code", (modal.getAttribute("aria-label") || "").endsWith(": " + first.dataset.code),
    modal.getAttribute("aria-label"));
say("Tab cannot wander out of the dialog", !key("Tab"));
key("Escape");
await wait(200);
say("Escape closes it", !modal.classList.contains("on"));
say("focus returns to the row you opened", here() === first, here().tagName);

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
