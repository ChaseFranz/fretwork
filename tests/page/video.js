// The explainer's video: nothing from YouTube until the panel opens, the
// no-cookie host, no autoplay, a labelled 16:9 box, and a pause on close.
import { BOOT, say, done, wait, key, click } from "./lib.js";

say("no iframe before the panel is opened", document.querySelectorAll("iframe").length === 0, document.querySelectorAll("iframe").length);
const how = document.getElementById("how");
how.focus();
click(how);
await wait(400);
const f = document.querySelector("#about iframe");
say("the panel embeds the video", Boolean(f));
say("served from the no-cookie host", f && f.src.startsWith("https://www.youtube-nocookie.com/embed/"), f && f.src);
say("the embed asks for the JS API, so it can be paused", f && /[?&]enablejsapi=1\b/.test(f.src));
say("it starts where the explanation does", f && /[?&]start=\d+/.test(f.src));
say("it does not autoplay", f && !/autoplay=1/.test(f.src));
say("the iframe is labelled for screen readers", f && f.title.length > 10, f && f.title);
say("it keeps a 16:9 box", f && Math.abs(f.getBoundingClientRect().width / f.getBoundingClientRect().height - 16 / 9) < 0.1,
    f && Math.round(f.getBoundingClientRect().width) + "x" + Math.round(f.getBoundingClientRect().height));
say("the video is credited under it", /Staycation44/.test(document.querySelector("#about p.cap").textContent));
say("the caption's embed url is the payload's", f && f.src === BOOT.ui.video_embed, f && f.src);

// Closing must post pauseVideo to YouTube's origin. The cross-origin contentWindow
// cannot be assigned, so shadow the getter with a stub that records the call.
const calls = [];
const stub = { postMessage: (msg, origin) => calls.push([msg, origin]) };
Object.defineProperty(f, "contentWindow", { get: () => stub, configurable: true });
key("Escape");
await wait(100);
say("Escape closes the panel", !document.getElementById("about").classList.contains("on"));
const pause = calls.find(([msg]) => { try { return JSON.parse(msg).func === "pauseVideo"; } catch (e) { return false; } });
say("closing posts pauseVideo", Boolean(pause), JSON.stringify(calls));
say("to YouTube's origin, not *", pause && pause[1] === "https://www.youtube-nocookie.com", pause && pause[1]);
say("the iframe stays built for the next open", document.querySelectorAll("#about iframe").length === 1);
done();
