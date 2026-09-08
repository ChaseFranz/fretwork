// Entry module: label the chrome, wire the panels, then first paint.
import { FOOTER, UI } from "./boot.js";
import { el, esc } from "./dom.js";
import { initDropdown } from "./dropdown.js";
import { initChooser } from "./chooser.js";
import { openGraph } from "./overlay.js";
import { initRouter, render } from "./router.js";
import { readUrl } from "./url.js";
import { initWidths } from "./widths.js";
import { state } from "./state.js";

function labelChrome() {
  el("brand").innerHTML = esc(UI.title) +
    ' <span class="fw-accent">&#9679;</span> <span class="fw-normal">' +
    esc(UI.subtitle) + "</span>" +
    ' <span class="beta" title="' + esc(UI.beta_tip) + '">' + esc(UI.beta) + "</span>";
  el("q").placeholder = UI.search;
  el("q").setAttribute("aria-label", UI.search);
  el("grid").setAttribute("aria-label", UI.grid_label);
  el("cols").textContent = UI.columns;
  el("cols").title = UI.columns_tip;
  el("how").textContent = UI.explainer;
  el("how").title = UI.explainer_tip;
}

const link = (text, href, cls) =>
  '<a class="' + (cls || "") + '" href="' + esc(href) +
  '" target="_blank" rel="noopener">' + esc(text) + "</a>";

// The one thing a visitor can ask us for, then attribution, the explainer that
// says what D means, and the licence.
function buildFooter() {
  const links = [link(UI.request, UI.request_url, "req")]
    .concat(FOOTER.map(([text, href]) => link(text, href)))
    .join('<span class="sep">/</span>');
  el("foot").innerHTML =
    '<div id="src2" class="mb-1">' + esc(el("src").textContent) + "</div>" +
    '<div class="beta-note mb-1">' + esc(UI.beta_note) + "</div>" +
    '<div class="d-flex flex-wrap align-items-center gap-1">' + links + "</div>" +
    '<div class="mt-1">' + esc(UI.copyright) + " " +
    link(UI.license_label, UI.license_url) + "</div>";
}

labelChrome();
buildFooter();
initDropdown();
initChooser();
initWidths();
initRouter();

// Open on Expert charts from official releases: the widest-recognised slice of
// the library, and the one a first-time visitor can calibrate against. Both
// chip rows read their state back out of these, and either clears in one click.
state.filters["Level"] = { type: "set", sel: new Set(["Expert"]) };
state.filters["Official"] = { type: "set", sel: new Set(["true"]) };

// A shared link describes a view, so whatever it names wins over those defaults.
const shared = readUrl();
render();
if (shared) openGraph(shared);
