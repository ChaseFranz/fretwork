// The 390px measurement. Headless Chrome floors its own layout viewport at
// 500px whatever --window-size says, so a phone layout can only be measured
// inside an iframe. Design 6 of the tests spec tried two forms: an outer page
// measuring synchronously on load (the transcript's frame.html), and this one,
// an injected module that creates the iframe, awaits its load and measures.
// Both produced output under --dump-dom; this one survives section 05, where
// the rows arrive by fetch after the iframe's load event, because it can wait.
// Other spec sections call this measurement "frame.html"; read that as this file.
import { say, note, done, wait } from "./lib.js";

export function measure(d, w) {
  if (!d.querySelector("#body tr[data-code]")) { say("iframe has rows", false, "no #body tr[data-code]"); return; }
  say("layout viewport is 390 wide", w.innerWidth === 390, w.innerWidth + " x " + w.innerHeight);
  say("narrow rules are active", w.matchMedia("(max-width:640px)").matches, "");
  const tools = d.getElementById("tools");
  const scrollable = tools.scrollWidth > tools.clientWidth + 4;
  say("control strip fades while there is more", tools.classList.contains("more") === scrollable,
      tools.clientWidth + " of " + tools.scrollWidth + "px visible");
  tools.scrollLeft = tools.scrollWidth;
  tools.dispatchEvent(new Event("scroll"));
  say("fade clears at the far right", !tools.classList.contains("more"), "");
  // Measurements, not assertions: the columns after D are off screen at 390px
  // by design; CLAUDE.md's rule is only that D stays on screen.
  const ths = [...d.querySelectorAll("#head th")];
  ths.slice(0, 6).forEach(th => {
    const b = th.getBoundingClientRect();
    const on = b.left >= -1 && b.right <= w.innerWidth + 1;
    note("th " + th.dataset.c + " x " + Math.round(b.left) + " -> " + Math.round(b.right) +
         (on ? " on screen" : " OFF SCREEN"));
  });
  const dTh = ths.find(th => th.dataset.c === "D");
  say("D is on screen without a swipe", dTh && dTh.getBoundingClientRect().right <= w.innerWidth,
      dTh && Math.round(dTh.getBoundingClientRect().right));
  const head = d.querySelector(".fw-head").getBoundingClientRect().height;
  const foot = d.querySelector(".fw-foot").getBoundingClientRect().height;
  const pct = Math.round(100 * (head + foot) / w.innerHeight);
  say("chrome under 35% of the screen", pct < 35, "header " + Math.round(head) + "px, footer " +
      Math.round(foot) + "px, " + pct + "%");
}

// Pinned to the viewport, so the host page's layout cannot squeeze it.
export async function narrowFrame(src) {
  const f = document.createElement("iframe");
  f.src = src;
  f.style.cssText = "position:fixed;top:0;left:0;width:390px;height:820px;border:0";
  document.body.appendChild(f);
  await new Promise(r => f.onload = r);
  await wait(600);
  return f;
}

const f = await narrowFrame("plain.html");
measure(f.contentDocument, f.contentWindow);

// The graph on a phone (section 06): the card takes the full width, the canvas
// is 358px, the close button and the tools are on screen, the readout wraps to
// at most two lines, and picking from the table widens nothing.
const d = f.contentDocument, w = f.contentWindow;
const row = d.querySelector("#body tr[data-code]");
const wrap = d.querySelector(".fw-wrap");
const wrapWidth = wrap.scrollWidth;
row.dispatchEvent(new w.MouseEvent("click", { bubbles: true, cancelable: true }));
await wait(700);
const modal = d.getElementById("modal");
const canvas = modal.querySelector("canvas");
say("graph opens at 390px", modal.classList.contains("on") && !!canvas);
if (canvas) {
  const cb = canvas.getBoundingClientRect();
  say("the canvas is 358px wide", Math.round(cb.width) === 358 && cb.left >= 0 && cb.right <= 390, Math.round(cb.left) + " -> " + Math.round(cb.right));
  const on = el => { const b = el.getBoundingClientRect(); return b.left >= 0 && b.right <= 390 && b.width > 0; };
  say("the close button is on screen", on(modal.querySelector(".x")));
  say("Save as PNG is on screen", on(modal.querySelector('[data-act="save"]')));
  const ro = modal.querySelector(".readout").getBoundingClientRect();
  note("readout " + Math.round(ro.width) + "x" + Math.round(ro.height) + "px: " + modal.querySelector(".readout").textContent);
  say("the readout is at most two lines", ro.height < 40, Math.round(ro.height));
  const card = modal.querySelector(".mcard").getBoundingClientRect();
  say("the card does not exceed the viewport", card.left >= 0 && card.right <= 390, Math.round(card.left) + " -> " + Math.round(card.right));
  // pick from the table: the bar must not widen the table
  modal.querySelector('[data-act="pick"]').dispatchEvent(new w.MouseEvent("click", { bubbles: true, cancelable: true }));
  await wait(100);
  const bar = d.getElementById("pick");
  say("the pick bar shows", !bar.classList.contains("d-none") && bar.getBoundingClientRect().height > 0);
  say("and does not widen the table", wrap.scrollWidth === wrapWidth, wrap.scrollWidth + " vs " + wrapWidth);
  say("and stays within the viewport", bar.scrollWidth <= 390, bar.scrollWidth);
  d.dispatchEvent(new w.KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
  await wait(600);
  say("Escape brings the graph back", modal.classList.contains("on"));
  d.dispatchEvent(new w.KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
  await wait(300);
}

// The song panel on a phone (section 07): a 374px card, four cells across it,
// the instrument heading on its own line, nothing clipped; and the title
// pip is out of flow, so the rows are no taller for it.
const rowsBefore = [...d.querySelectorAll("#body tr[data-code]")].slice(0, 40).reduce((a, tr) => a + tr.getBoundingClientRect().height, 0);
d.querySelectorAll("td.song .sp").forEach(e => e.remove());
const rowsAfter = [...d.querySelectorAll("#body tr[data-code]")].slice(0, 40).reduce((a, tr) => a + tr.getBoundingClientRect().height, 0);
say("the title pip adds no height to the rows", Math.abs(rowsBefore - rowsAfter) < 1, rowsBefore + " vs " + rowsAfter);
const link = (() => { const tr = d.querySelector("#body tr[data-code]"); return tr; })();
link.dispatchEvent(new w.MouseEvent("click", { bubbles: true, cancelable: true }));
await wait(600);
const sng = d.querySelector("#modal .mhead a.sng");
if (!sng) {
  say("song link in the heading", false, "no a.sng");
} else {
  sng.dispatchEvent(new w.MouseEvent("click", { bubbles: true, cancelable: true }));
  await wait(700);
  const panel = d.getElementById("song");
  const card = panel.querySelector(".mcard").getBoundingClientRect();
  say("the song panel opens at 390px within the viewport", panel.classList.contains("on") && card.left >= 0 && card.right <= 390, Math.round(card.left) + " -> " + Math.round(card.right));
  const grid = panel.querySelector(".sgrid");
  say("the grid does not scroll sideways", grid.scrollWidth <= grid.clientWidth, grid.scrollWidth + " vs " + grid.clientWidth);
  say("the instrument heading spans the grid", [...panel.querySelectorAll(".sgrid .inst")].every(e => Math.abs(e.getBoundingClientRect().width - grid.clientWidth) <= 2),
      [...panel.querySelectorAll(".sgrid .inst")].map(e => Math.round(e.getBoundingClientRect().width)).join() + " vs " + grid.clientWidth);
  say("every cell is at least 44px tall", [...panel.querySelectorAll(".sgrid .cell")].every(c => c.getBoundingClientRect().height >= 44));
  say("no value is clipped", [...panel.querySelectorAll(".sgrid .cell b")].every(b => b.scrollWidth <= b.clientWidth + 1));
  note("cells " + [...panel.querySelectorAll(".sgrid .cell")].slice(0, 4).map(c => Math.round(c.getBoundingClientRect().width) + "x" + Math.round(c.getBoundingClientRect().height)).join(" "));
}
done();
