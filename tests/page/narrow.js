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
done();
