// The about page is a page of its own: reachable from the footer, scriptless but for the theme,
// with a way back. Fetched from the served bundle and parsed, since the runner
// cannot inject into a page that has no module tag.
import { BOOT, say, done } from "./lib.js";

const href = document.querySelector('#foot a[href="about.html"]').getAttribute("href");
const res = await fetch(href);
say("the footer's about link resolves", res.status === 200, res.status);
say("as html", (res.headers.get("content-type") || "").startsWith("text/html"), res.headers.get("content-type"));
const doc = new DOMParser().parseFromString(await res.text(), "text/html");
say("one h1", doc.querySelectorAll("h1").length === 1, doc.querySelectorAll("h1").length);
say("a heading per entry", doc.querySelectorAll("h2").length >= 3, doc.querySelectorAll("h2").length);
say("one script on the page, the theme's", doc.querySelectorAll("script").length === 1 && doc.head.innerHTML.includes('localStorage.getItem("fw.theme")'));
const back = [...doc.querySelectorAll("a")].find(a => a.getAttribute("href") === "./");
say("a link back to the charts, worded from the payload", back && back.textContent === BOOT.ui.about_back, back && back.textContent);
say("no placeholder survived", !/__[A-Z][A-Z_]*__/.test(doc.body.textContent));
say("the copyright notice quotes the licence holder", /Copyright \(c\) \d{4} Staycation\b/.test(doc.body.textContent));
done();
