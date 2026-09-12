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

// The methodology page at 390px (section 12): nothing scrolls sideways, the
// tables and formulas fit their wrappers, and the headings keep their order.
const m = await narrowFrame("methodology.html");
const md = m.contentDocument, mw = m.contentWindow;
say("methodology.html: the body does not scroll sideways", md.documentElement.scrollWidth <= 390, md.documentElement.scrollWidth);
say("every table and formula fits at 390px", [...md.querySelectorAll(".tbl, .eq")].every(e => e.scrollWidth <= e.clientWidth),
    [...md.querySelectorAll(".tbl, .eq")].map(e => e.scrollWidth + "/" + e.clientWidth).join(" "));
const px = sel => parseFloat(mw.getComputedStyle(md.querySelector(sel)).fontSize);
say("heading sizes step down h2 > h3 > h4 > h5", px(".md h2") > px(".md h3") && px(".md h3") > px(".md h4") && px(".md h4") > px(".md h5"),
    [".md h2", ".md h3", ".md h4", ".md h5"].map(px).join(" > "));
say("it holds the four tables and seven formulas", md.querySelectorAll(".md table").length === 4 && md.querySelectorAll('math[display="block"]').length === 7);
m.remove();

// The details pane on a phone (sections 06, 07, 14): a bottom sheet under the
// table, the table keeping some rows above it, the canvas the full width less
// the padding, the buttons and tools on screen, the readout at most two lines,
// the song grid stacked under the graph with four cells across, and picking
// from the table widening nothing.
const d = f.contentDocument, w = f.contentWindow;
const row = d.querySelector("#body tr[data-code]");
const wrap = d.querySelector(".fw-wrap");
const wrapWidth = wrap.scrollWidth;
row.dispatchEvent(new w.MouseEvent("click", { bubbles: true, cancelable: true }));
await wait(900);
const modal = d.getElementById("pane");
const canvas = modal.querySelector("canvas");
say("the pane opens at 390px", modal.classList.contains("on") && !!canvas);
if (canvas) {
  const pb = modal.getBoundingClientRect(), wb = wrap.getBoundingClientRect();
  say("it is a sheet at the bottom, under the table", pb.top >= wb.bottom - 1 && pb.bottom <= w.innerHeight + 1, Math.round(wb.bottom) + " -> pane " + Math.round(pb.top) + ".." + Math.round(pb.bottom));
  say("the table keeps at least two rows on screen", wb.height >= 2 * row.getBoundingClientRect().height, Math.round(wb.height) + "px for " + Math.round(row.getBoundingClientRect().height) + "px rows");
  say("the pane takes under 60% of the screen", pb.height < 0.6 * w.innerHeight, Math.round(pb.height) + " of " + w.innerHeight);
  const cb = canvas.getBoundingClientRect();
  const pcard = modal.querySelector(".pcard");
  say("the canvas is the card's width less the padding", Math.round(cb.width) === pcard.clientWidth - 16 && cb.left >= 0 && cb.right <= 390 && pcard.clientWidth >= 359,
      Math.round(cb.left) + " -> " + Math.round(cb.right) + " = " + Math.round(cb.width) + " in " + pcard.clientWidth);
  say("the link columns are off a phone's table", [...d.querySelectorAll("#head th")].filter(th => ["Chart", "Leaderboard"].includes(th.dataset.c)).every(th => th.offsetParent === null));
  const on = el => { const b = el.getBoundingClientRect(); return b.left >= 0 && b.right <= 390 && b.width > 0; };
  say("the close button is on screen", on(modal.querySelector(".pbtns .x")));
  say("the collapse button is on screen", on(modal.querySelector(".pbtns .pmin")));
  say("Save as PNG is on screen", on(modal.querySelector('[data-act="save"]')));
  const ro = modal.querySelector(".readout").getBoundingClientRect();
  note("readout " + Math.round(ro.width) + "x" + Math.round(ro.height) + "px: " + modal.querySelector(".readout").textContent);
  say("the readout is at most two lines", ro.height < 40, Math.round(ro.height));
  const card = modal.querySelector(".pcard");
  say("the card does not scroll sideways", card.scrollWidth <= card.clientWidth + 1, card.scrollWidth + " vs " + card.clientWidth);
  say("the graph and the song grid are stacked", modal.querySelector(".sbody").getBoundingClientRect().top >= modal.querySelector(".gbody").getBoundingClientRect().bottom - 1);
  // the song grid: four cells across the card, the instrument heading on its own line
  const grid = modal.querySelector(".sgrid");
  say("the song grid is there", !!grid);
  if (grid) {
    say("the grid does not scroll sideways", grid.scrollWidth <= grid.clientWidth, grid.scrollWidth + " vs " + grid.clientWidth);
    say("the instrument heading spans the grid", [...modal.querySelectorAll(".sgrid .inst")].every(e => Math.abs(e.getBoundingClientRect().width - grid.clientWidth) <= 2),
        [...modal.querySelectorAll(".sgrid .inst")].map(e => Math.round(e.getBoundingClientRect().width)).join() + " vs " + grid.clientWidth);
    say("every cell is at least 44px tall", [...modal.querySelectorAll(".sgrid .cell")].every(c => c.getBoundingClientRect().height >= 44));
    say("no value is clipped", [...modal.querySelectorAll(".sgrid .cell b")].every(b => b.scrollWidth <= b.clientWidth + 1));
    note("cells " + [...modal.querySelectorAll(".sgrid .cell")].slice(0, 4).map(c => Math.round(c.getBoundingClientRect().width) + "x" + Math.round(c.getBoundingClientRect().height)).join(" "));
  }
  // pick from the table: the bar must not widen the table
  modal.querySelector('[data-act="pick"]').dispatchEvent(new w.MouseEvent("click", { bubbles: true, cancelable: true }));
  await wait(100);
  const bar = d.getElementById("pick");
  say("the pick bar shows", !bar.classList.contains("d-none") && bar.getBoundingClientRect().height > 0);
  say("and does not widen the table", wrap.scrollWidth === wrapWidth, wrap.scrollWidth + " vs " + wrapWidth);
  say("and stays within the viewport", bar.scrollWidth <= 390, bar.scrollWidth);
  d.dispatchEvent(new w.KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
  await wait(300);
  say("Escape ends the picking and keeps the pane", modal.classList.contains("on") && bar.classList.contains("d-none"));
  // collapsed, the pane is its heading alone and the table gets the room back
  modal.querySelector(".pbtns .pmin").dispatchEvent(new w.MouseEvent("click", { bubbles: true, cancelable: true }));
  await wait(200);
  say("collapsed, the pane is its wrapped heading alone", modal.classList.contains("min") && modal.getBoundingClientRect().height < 130 && !modal.querySelector(".gbody").offsetParent,
      Math.round(modal.getBoundingClientRect().height));
  say("and the table grows", wrap.getBoundingClientRect().height > wb.height, Math.round(wrap.getBoundingClientRect().height) + " from " + Math.round(wb.height));
  d.dispatchEvent(new w.KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
  await wait(300);
  say("Escape closes it", !modal.classList.contains("on"));
}
done();
