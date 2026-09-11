// The right-edge fade appears only while there is more table to the right, is a
// mask on the scroller rather than an element over the rows, and leaves the
// sticky header stuck. Run at three widths by the runner.
import { say, done, wait } from "./lib.js";

await wait(300);
const wrap = document.querySelector(".fw-wrap");
const th = () => document.querySelector("#head th");
const wide = wrap.scrollWidth > wrap.clientWidth;
say("fade class equals overflow", wrap.classList.contains("more") === wide,
    wrap.clientWidth + " of " + wrap.scrollWidth + "px, more=" + wrap.classList.contains("more"));
const mask = getComputedStyle(wrap).maskImage || getComputedStyle(wrap).webkitMaskImage;
say("the fade is a mask, set only while there is more", (mask !== "none" && mask !== "") === wide, String(mask).slice(0, 40));
const headTop = th().getBoundingClientRect().top;
wrap.scrollTop = 900;
wrap.dispatchEvent(new Event("scroll"));
await wait(50);
say("the header is still stuck after scrolling down", Math.abs(th().getBoundingClientRect().top - headTop) < 2,
    headTop + " -> " + th().getBoundingClientRect().top);
wrap.scrollLeft = wrap.scrollWidth;
wrap.dispatchEvent(new Event("scroll"));
await wait(50);
say("fade clears at the right-hand end", !wrap.classList.contains("more"));
wrap.scrollLeft = 0;
wrap.dispatchEvent(new Event("scroll"));
await wait(50);
say("and comes back when you scroll away from it", wrap.classList.contains("more") === wide);
done();
