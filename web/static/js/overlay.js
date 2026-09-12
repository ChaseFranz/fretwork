// The page's two overlays: the transient hint, and the explainer dialog. The
// graph and the song grid are not overlays since section 14; they are the
// details pane (pane.js), which sits under the table rather than over it.
import { EXPLAINER, FOOTER, UI } from "./boot.js";
import { el, esc, rich } from "./dom.js";

let hintTimer = null;
let opener = null;      // what to hand focus back to when the explainer closes

export function toast(message) {
  const hint = el("hint");
  hint.firstElementChild.textContent = message;
  hint.classList.add("on");
  clearTimeout(hintTimer);
  hintTimer = setTimeout(() => hint.classList.remove("on"), 1400);
}

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
      '<span class="sep">/</span><a href="' + esc(UI.method_url) + '">' + esc(UI.explainer_method) + "</a>" +
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
