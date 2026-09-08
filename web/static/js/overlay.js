// The graph lightbox and the transient hint, the page's two overlays.
import { UI } from "./boot.js";
import { el, esc } from "./dom.js";
import { cols, rowsAll } from "./state.js";

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
  return '<div class="mhead"><strong>' + esc(get("Song Title")) + '</strong>' +
    '<span class="text-secondary">' + esc(get("Artist")) + '</span>' +
    '<span class="badge rounded-pill lvl ' + esc(get("Level")) + '">' +
    esc(get("Level")) + '</span>' +
    '<span class="text-secondary">' + esc(get("Type")) + '</span></div>';
}

export function openGraph(code) {
  const modal = el("modal"), card = modal.querySelector(".mcard");
  const head = heading(code);
  const message = text => head + '<div class="text-secondary py-4">' + esc(text) + "</div>";

  opener = document.activeElement;
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
  if (opener && opener.isConnected) opener.focus();
  opener = null;
}

export const graphIsOpen = () => el("modal").classList.contains("on");
