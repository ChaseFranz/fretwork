// Entry module: label the chrome, wire the panels, then first paint.
import { FOOTER, UI } from "./boot.js";
import { el, esc } from "./dom.js";
import { initDropdown } from "./dropdown.js";
import { initChooser } from "./chooser.js";
import { initRouter, render } from "./router.js";
import { state } from "./state.js";

function labelChrome() {
  el("brand").innerHTML = esc(UI.title) +
    ' <span class="fw-accent">&#9679;</span> <span class="fw-normal">' +
    esc(UI.subtitle) + "</span>";
  el("q").placeholder = UI.search;
  el("cols").textContent = UI.columns;
  el("cols").title = UI.columns_tip;
}

const link = (text, href) =>
  '<a href="' + esc(href) + '" target="_blank" rel="noopener">' + esc(text) + "</a>";

// Attribution, the explainer that says what D means, and the licence.
function buildFooter() {
  const links = FOOTER.map(([text, href]) => link(text, href)).join('<span class="sep">/</span>');
  el("foot").innerHTML =
    '<div class="d-flex flex-wrap align-items-center gap-1">' + links + "</div>" +
    '<div class="mt-1">' + esc(UI.copyright) + " " +
    link(UI.license_label, UI.license_url) + "</div>";
}

labelChrome();
buildFooter();
initDropdown();
initChooser();
initRouter();

// Open on Expert only; the chips read this back as their active state.
state.filters["Level"] = { type: "set", sel: new Set(["Expert"]) };
render();
