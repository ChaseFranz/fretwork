// ?song= links (section 07): a key with a code opens the panel and then the
// graph over it; a key nobody has shows the not-found text and leaves the URL.
import { BOOT, say, done, wait, key, ready, params } from "./lib.js";
await ready();
const { ui: UI } = BOOT;
const p = params();
const modal = document.getElementById("modal"), panel = document.getElementById("song");
await wait(900);
if (p.get("song") === "000000000000") {
  say("an unknown key says so", panel.classList.contains("on") && panel.querySelector(".mhead").textContent.includes(UI.song_not_found), panel.querySelector(".mhead").textContent);
  say("and the parameter has left the URL", params().get("song") === null, location.search);
} else {
  const code = p.get("code");
  say("the link named a song and a code", !!p.get("song") && !!code, location.search);
  say("both the panel and the graph are open", panel.classList.contains("on") && modal.classList.contains("on"));
  say("focus is in the graph", document.activeElement && document.activeElement.id === "modal", document.activeElement && document.activeElement.id);
  say("the graph is the named code", modal.getAttribute("aria-label").endsWith(": " + code), modal.getAttribute("aria-label"));
  key("Escape");
  await wait(300);
  say("Escape closes the graph and focuses the cell it belongs to", !modal.classList.contains("on") && panel.classList.contains("on") &&
      document.activeElement && document.activeElement.matches('#song .cell.here[data-code="' + code + '"]'), document.activeElement && document.activeElement.outerHTML);
  await wait(400);
  say("the URL keeps the song and drops the code", params().get("song") === p.get("song") && params().get("code") === null, location.search);
}
done();
