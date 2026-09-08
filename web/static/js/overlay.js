// The graph lightbox and the transient hint, the page's two overlays.
import { EXPLAINER, FOOTER, UI } from "./boot.js";
import { el, esc } from "./dom.js";
import { cols, rowsAll, state } from "./state.js";
import { writeUrl } from "./url.js";

let hintTimer = null;
let opener = null;      // what to hand focus back to when the graph closes

export function toast(message) {
  const hint = el("hint");
  hint.firstElementChild.textContent = message;
  hint.classList.add("on");
  clearTimeout(hintTimer);
  hintTimer = setTimeout(() => hint.classList.remove("on"), 1400);
}

// Names the chart being shown, so the graph is never unlabelled.
function heading(code) {
  const columns = cols();
  const row = rowsAll().find(r => r[columns.indexOf("Code")] === code);
  const get = name => {
    const i = columns.indexOf(name);
    return i < 0 || row === undefined ? "" : row[i];
  };
  // The report link carries the code and the song, so a rating complaint arrives
  // pointing at an exact chart instead of "the Dragonforce one".
  const report = UI.report_url + "&code=" + encodeURIComponent(code) +
    "&song=" + encodeURIComponent(get("Song Title") + " - " + get("Artist"));
  return '<div class="mhead"><strong>' + esc(get("Song Title")) + '</strong>' +
    '<span class="text-secondary">' + esc(get("Artist")) + '</span>' +
    '<span class="badge rounded-pill lvl ' + esc(get("Level")) + '">' +
    esc(get("Level")) + '</span>' +
    '<span class="text-secondary">' + esc(get("Type")) + '</span>' +
    '<span class="text-secondary">' + esc(get("Charter")) + '</span>' +
    '<a class="ms-auto rpt" target="_blank" rel="noopener" href="' + esc(report) +
    '">' + esc(UI.report) + "</a></div>";
}

export function openGraph(code) {
  const modal = el("modal"), card = modal.querySelector(".mcard");
  const head = heading(code);
  const message = text => head + '<div class="text-secondary py-4">' + esc(text) + "</div>";

  opener = document.activeElement;
  state.graph = code;
  writeUrl();
  modal.setAttribute("aria-label", UI.graph_label + ": " + code);
  modal.classList.add("on");
  modal.focus();
  card.innerHTML = message(UI.rendering);

  const img = new Image();
  img.onload = () => { card.innerHTML = head; card.appendChild(img); };
  img.onerror = () => { card.innerHTML = message(UI.render_failed); };
  img.src = "graph/" + code + ".png";
}

export function closeGraph() {
  el("modal").classList.remove("on");
  state.graph = null;
  writeUrl();
  if (opener && opener.isConnected) opener.focus();
  opener = null;
}

export const graphIsOpen = () => el("modal").classList.contains("on");


// The explainer: what D is, and what it is not. Static text, built once.
export function openAbout() {
  const panel = el("about");
  opener = document.activeElement;
  if (!panel.querySelector(".mhead")) {
    const out = (text, href) => '<a target="_blank" rel="noopener" href="' + esc(href) +
      '">' + esc(text) + "</a>";
    panel.querySelector(".mcard").innerHTML =
      '<div class="mhead"><strong>' + esc(UI.explainer_title) + "</strong>" +
      '<button type="button" class="x" data-act="close" aria-label="' +
      esc(UI.close_tip) + '" title="' + esc(UI.close_tip) + '">&times;</button></div>' +
      EXPLAINER.map(([heading, body]) =>
        "<h2>" + esc(heading) + "</h2><p>" + esc(body) + "</p>").join("") +
      '<p class="more">' + out(UI.explainer_more, FOOTER[0][1]) +
      '<span class="sep">/</span>' + out(UI.explainer_method, UI.method_url) + "</p>";
  }
  panel.setAttribute("aria-label", UI.explainer_title);
  panel.classList.add("on");
  panel.focus();
}

export function closeAbout() {
  el("about").classList.remove("on");
  if (opener && opener.isConnected) opener.focus();
  opener = null;
}

export const aboutIsOpen = () => el("about").classList.contains("on");
