// ?song= links (sections 07, 14 and 16): a key alone resolves to the song's
// primary chart and the pane opens on it, the URL then carrying that code; a
// key with a code opens the code; a key with a code no row has (the folder
// moved) opens the song instead; a key nobody has says so and leaves the URL.
import { BOOT, say, done, wait, ready, params } from "./lib.js";
await ready();
const { ui: UI } = BOOT;
const p = params();
const pane = document.getElementById("pane");
await wait(1200);
if (p.get("song") === "000000000000") {
  say("an unknown key says so", document.getElementById("hint").textContent.includes(UI.song_not_found) || !pane.classList.contains("on"),
      document.getElementById("hint").textContent);
  say("the pane did not open", !pane.classList.contains("on"));
  say("and the parameter has left the URL", params().get("song") === null && params().get("code") === null, location.search);
} else if (p.get("code") === "00000000XG") {
  // a stale code beside a live key: the song stands in (section 16)
  const key = p.get("song");
  say("the link named a song and a code no row has", !!key, location.search);
  say("the pane opened on one of the song's charts", pane.classList.contains("on") && /: [A-Za-z0-9]{10}$/.test(pane.getAttribute("aria-label") || "") &&
      !(pane.getAttribute("aria-label") || "").endsWith(": 00000000XG"), pane.getAttribute("aria-label"));
  say("the URL carries that chart's code and no song", params().get("code") && params().get("code") !== "00000000XG" && params().get("song") === null, location.search);
} else if (p.get("code")) {
  const code = p.get("code");
  say("the link named a song and a code", !!p.get("song") && !!code, location.search);
  say("the pane is open on the named code", pane.classList.contains("on") && pane.getAttribute("aria-label").endsWith(": " + code), pane.getAttribute("aria-label"));
  say("with the song section filled", !!pane.querySelector(".sbody .sgrid"));
  say("the URL keeps the code and drops the song", params().get("code") === code && params().get("song") === null, location.search);
} else {
  const key = p.get("song");
  say("the link named a song alone", !!key, location.search);
  say("the pane opened on one of its charts", pane.classList.contains("on") && /: [A-Za-z0-9]{10}$/.test(pane.getAttribute("aria-label") || ""), pane.getAttribute("aria-label"));
  const code = params().get("code");
  say("the URL now carries that code and no song", !!code && params().get("song") === null, location.search);
  // the primary chart: Expert when the first instrument has one
  const cells = [...pane.querySelectorAll(".sbody .sgrid .cell:not(.none)")];
  const here = pane.querySelector(".sbody .sgrid .cell.here");
  say("the open cell is the grid's first row at its highest level", here && cells[0] === here, here && here.dataset.code);
  say("its row is highlighted when on screen", !document.querySelector("#body tr.sel") || document.querySelector("#body tr.sel").dataset.code === code);
}
done();
