// Entry module: label the chrome, wire the panels, then first paint.
import { DOC_PAGES, FOOTER, UI, SHEETS, SHEET_OF_CODE } from "./boot.js";
import { el, esc, rich } from "./dom.js";
import { initDropdown } from "./dropdown.js";
import { initChooser } from "./chooser.js";
import { openGraph, initGraphModal } from "./overlay.js";
import { openSong } from "./song.js";
import { initRouter, render } from "./router.js";
import { edgeFade } from "./scroll.js";
import { loadSheet, prefetchIdle } from "./load.js";
import { readUrl } from "./url.js";
import { initWidths } from "./widths.js";
import { state } from "./state.js";

function labelChrome() {
  el("brand").innerHTML = esc(UI.title) +
    ' <span class="beta" title="' + esc(UI.beta_tip) + '">' + esc(UI.beta) + "</span>";
  el("q").placeholder = UI.search;
  el("q").setAttribute("aria-label", UI.search);
  el("grid").setAttribute("aria-label", UI.grid_label);
  el("cols").textContent = UI.columns;
  el("cols").title = UI.columns_tip;
  el("how").innerHTML = '<span aria-hidden="true">&#9432;</span> ' + esc(UI.explainer);
  el("how").title = UI.explainer_tip;
}

const link = (text, href, cls) =>
  '<a class="' + (cls || "") + '" href="' + esc(href) +
  '" target="_blank" rel="noopener">' + esc(text) + "</a>";

// Same site, so it stays in the tab it was opened from.
const here = (text, href) => '<a href="' + esc(href) + '">' + esc(text) + "</a>";

// The one thing a visitor can ask us for, then attribution, the explainer that
// says what D means, and the licence.
function buildFooter() {
  const links = [link(UI.request, UI.request_url, "req")]
    .concat(DOC_PAGES.map(([href, key]) => here(UI[key], href)))
    .concat(FOOTER.map(([text, href]) => link(text, href)))
    .join('<span class="sep">/</span>');
  el("foot").innerHTML =
    // server-built and already escaped: an anchor exactly when the header copy is
    '<div id="src2" class="mb-1">' + el("src").innerHTML + "</div>" +
    '<div class="beta-note mb-1">' + esc(UI.beta_note) + "</div>" +
    '<div class="d-flex flex-wrap align-items-center gap-1">' + links + "</div>" +
    '<div class="mt-1">' + rich(UI.copyright) + " " +
    link(UI.license_label, UI.license_url) + "</div>";
}

labelChrome();
buildFooter();
initDropdown();
initChooser();
initWidths();
initRouter();
initGraphModal();
edgeFade(el("tools"));
edgeFade(document.querySelector(".fw-wrap"));

// Open on Expert charts from official releases: the widest-recognised slice of
// the library, and the one a first-time visitor can calibrate against. Both
// chip rows read their state back out of these, and either clears in one click.
state.filters["Level"] = { type: "set", sel: new Set(["Expert"]) };
state.filters["Official"] = { type: "set", sel: new Set(["true"]) };

// A shared link describes a view, so whatever it names wins over those defaults.
// The header, chips and controls paint at once; the rows follow their fetch,
// and a shared graph opens only once its row is here to name it (its own
// sheet is loaded too, in case the link names another) and, when a song
// panel is named as well, once that panel has filled, so the graph's opener is
// the cell it belongs to. state.graph and state.song are set first so the
// first draw's writeUrl keeps them in the address bar.
const shared = readUrl();
if (shared.code) state.graph = shared.code;
if (shared.song) state.song = shared.song;
render();           // the loading row; draw() refreshes both fades once there is content to measure
const panel = shared.song ? openSong(shared.song, { from: shared.code }) : Promise.resolve();
const codeSheet = shared.code ? SHEET_OF_CODE[shared.code.slice(-1).toUpperCase()] : null;
Promise.all([loadSheet(state.sheet), codeSheet && codeSheet in SHEETS ? loadSheet(codeSheet) : null, panel])
  .then(() => {
    render();
    if (shared.code) openGraph(shared.code);
    prefetchIdle();
  }, () => { state.loadError = true; render(); });
