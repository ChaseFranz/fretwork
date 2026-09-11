// The graph lightbox and the transient hint, the page's two overlays.
import { EXPLAINER, FOOTER, UI, VALUE_LABELS } from "./boot.js";
import { el, esc, rich } from "./dom.js";
import { t } from "./format.js";
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

// The other rows on this sheet with exactly these notes at this level and
// part: the same chart in another folder. Copies are always on the chart's own
// sheet (same instrument), so the loaded sheet is the only place to look.
function copies(code, row) {
  const columns = cols();
  const key = ["Type", "Level", "NotesHash"].map(c => columns.indexOf(c));
  const codeAt = columns.indexOf("Code");
  if (row === undefined || key.some(i => i < 0)) return [];
  const hash = row[key[2]];
  if (hash === null || hash === undefined || hash === "") return [];
  return rowsAll().filter(r => r[codeAt] !== code && key.every(i => r[i] === row[i]));
}

// What a copy is called: its pack and whether it is official. A folder with
// no matched icon carries the literal default "Custom" as its source, which
// would read "Custom (Custom)", so the charter stands in there, and the code
// when that is empty too.
function copyText(row) {
  const columns = cols();
  const get = name => row[columns.indexOf(name)];
  let release = get("Release");
  if (release === "Custom") release = get("Charter") || get("Code");
  const kind = (VALUE_LABELS.Official || {})[String(get("Official"))] ?? String(get("Official"));
  return esc(release) + " (" + esc(kind) + ")";
}

// Names the chart being shown, so the graph is never unlabelled.
function heading(code) {
  const columns = cols();
  const row = rowsAll().find(r => r[columns.indexOf("Code")] === code);
  const get = name => {
    const i = columns.indexOf(name);
    return i < 0 || row === undefined ? "" : row[i];
  };
  // Two folders in one pack read the same, so the code then says which one.
  const own = row === undefined ? "" : copyText(row);
  const others = copies(code, row).map(r => {
    const c = r[columns.indexOf("Code")], text = copyText(r);
    return '<a href="?code=' + esc(c) + '" data-code="' + esc(c) + '" title="' + esc(UI.copies_tip) + '">' +
      text + (text === own ? " " + esc(c) : "") + "</a>";
  });
  const same = others.length
    ? '<div class="copies"><span class="text-secondary">' + esc(UI.copies_label) + "</span> " +
      others.join('<span class="sep">/</span>') + "</div>"
    : "";
  // The report link carries the code and the song, so a rating complaint arrives
  // pointing at an exact chart instead of "the Dragonforce one".
  const report = UI.report_url + "&code=" + encodeURIComponent(code) +
    "&song=" + encodeURIComponent(get("Song Title") + " - " + get("Artist"));
  // "At or above N%": the pool the row is ranked in is the current sheet at the
  // row's level, and the chart itself is in it, so "harder than" would be wrong.
  const pct = get("Pct");
  const place = typeof pct === "number"
    ? '<span class="text-secondary">' +
      esc(t("pct_of", { pct: pct, level: get("Level"), sheet: state.sheet })) + "</span>"
    : "";
  return '<div class="mhead"><strong>' + esc(get("Song Title")) + '</strong>' +
    '<span class="text-secondary">' + esc(get("Artist")) + '</span>' +
    '<span class="badge rounded-pill lvl ' + esc(get("Level")) + '">' +
    esc(get("Level")) + '</span>' +
    '<span class="text-secondary">' + esc(get("Type")) + '</span>' +
    '<span class="text-secondary">' + esc(get("Charter")) + '</span>' + place +
    '<a class="ms-auto rpt" target="_blank" rel="noopener" href="' + esc(report) +
    '">' + esc(UI.report) + "</a>" + same + "</div>";
}

export function openGraph(code) {
  const modal = el("modal"), card = modal.querySelector(".mcard");
  const head = heading(code);
  const message = text => head + '<div class="text-secondary py-4">' + esc(text) + "</div>";

  // Swapping to a copy keeps the opener: the link clicked is about to be
  // replaced with the card, and Escape should still return to the table row.
  if (!graphIsOpen()) opener = document.activeElement;
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
      '<div class="vid"><iframe src="' + esc(UI.video_embed) + '" title="' +
      esc(UI.video_title) + '" loading="lazy" allowfullscreen ' +
      'referrerpolicy="strict-origin-when-cross-origin" ' +
      'allow="encrypted-media; picture-in-picture; fullscreen"></iframe></div>' +
      '<p class="cap">' + rich(UI.video_caption) + "</p>" +
      EXPLAINER.map(([heading, body]) =>
        "<h2>" + esc(heading) + "</h2><p>" + rich(body) + "</p>").join("") +
      '<p class="more">' + out(UI.explainer_more, FOOTER[0][1]) +
      '<span class="sep">/</span>' + out(UI.explainer_method, UI.method_url) +
      '<span class="sep">/</span><a href="about.html">' + esc(UI.about) + "</a></p>";
  }
  panel.setAttribute("aria-label", UI.explainer_title);
  panel.classList.add("on");
  panel.focus();
}

// Hiding the panel does not stop the player: an iframe goes on playing audio
// while display:none, so closing the panel has to say so. The IFrame API's pause
// command keeps the viewer's place in the video, which blanking the src would
// not - reopening would drop them back at the start.
function pauseVideo() {
  const frame = el("about").querySelector("iframe");
  if (!frame || !frame.contentWindow) return;
  frame.contentWindow.postMessage(
    JSON.stringify({ event: "command", func: "pauseVideo", args: [] }),
    "https://www.youtube-nocookie.com");
}

export function closeAbout() {
  pauseVideo();
  el("about").classList.remove("on");
  if (opener && opener.isConnected) opener.focus();
  opener = null;
}

export const aboutIsOpen = () => el("about").classList.contains("on");
