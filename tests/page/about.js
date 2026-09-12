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

// every document page the footer lists is there, worded from the payload, one h1, the theme script and nothing else
for (const [page, key] of BOOT.docPages || []) {
  // the strapline's copy in the footer links the changelog too, so pick the links row's anchor by its text
  const a = [...document.querySelectorAll('#foot a[href="' + page + '"]')].find(x => x.textContent === BOOT.ui[key]);
  const r = a && await fetch(a.getAttribute("href"));
  const d = r && r.status === 200 ? new DOMParser().parseFromString(await r.text(), "text/html") : null;
  say("footer page " + page + " resolves, named " + JSON.stringify(BOOT.ui[key]), a && a.textContent === BOOT.ui[key] && d &&
      d.querySelectorAll("h1").length === 1 && d.querySelectorAll("script").length === 1, a ? (r && r.status) : "no link");
}
// the library page (section 20): five blocks, a bar per tier, the hardest linked into the table
{
  const r = await fetch("library.html");
  const d = new DOMParser().parseFromString(await r.text(), "text/html");
  say("the library page has its five blocks", d.querySelectorAll("h2").length === 5, d.querySelectorAll("h2").length);
  say("a bar per tier, the widest full", d.querySelectorAll(".bar").length > 0 && [...d.querySelectorAll(".bar")].some(b => b.style.width === "100%"));
  say("the hardest charts link into the table", [...d.querySelectorAll('a[href^="./?code="]')].length >= 1);
  say("the totals are the strapline's count", d.querySelector("p.totals") && d.querySelector("p.totals").textContent.includes(
      Object.values(BOOT.data).reduce((n, s) => n + s.rows, 0).toLocaleString("en-US") + " charts"), d.querySelector("p.totals") && d.querySelector("p.totals").textContent);
}
done();
