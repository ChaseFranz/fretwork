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
// the songs index (section 21): every song, a link per song page, from the footer
{
  const r = await fetch("songs.html");
  const d = new DOMParser().parseFromString(await r.text(), "text/html");
  const links = [...d.querySelectorAll('a[href^="song/"]')];
  say("the songs index links every song page", r.status === 200 && links.length > 0 && links.every(a => /^song\/[0-9a-f]{12}\.html$/.test(a.getAttribute("href"))), links.length);
  const first = links[0] && await fetch(links[0].getAttribute("href"));
  say("and its first link is a page, not a redirect", first && first.status === 200 && (await first.text()).includes("<h1>"), first && first.status);
}
// the library page (section 20): five blocks, a bar per tier, the hardest linked into the table
{
  const r = await fetch("library.html");
  const d = new DOMParser().parseFromString(await r.text(), "text/html");
  say("the library page has its five blocks", d.querySelectorAll("h2").length === 5, d.querySelectorAll("h2").length);
  say("a bar per tier, the widest full", d.querySelectorAll(".bar").length > 0 && [...d.querySelectorAll(".bar")].some(b => b.style.width === "100%"));
  say("the hardest charts link into the table and to their song pages", [...d.querySelectorAll('a[href^="./?code="]')].length >= 1 && [...d.querySelectorAll('a[href^="song/"]')].length >= 1);
  // section 22: the packs link their pages, the hardest blocks their lists, and both resolve as pages
  const game = d.querySelector('a[href^="game/"]'), list = d.querySelector('a[href^="list/"]');
  say("the library links the packs to their pages and the hardest to the lists", !!game && !!list, (game && game.getAttribute("href")) + " " + (list && list.getAttribute("href")));
  for (const a of [game, list]) {
    if (!a) continue;
    const rr = await fetch(a.getAttribute("href"));
    const dd = new DOMParser().parseFromString(await rr.text(), "text/html");
    say(a.getAttribute("href") + " is a page with a base, a title and song links", rr.status === 200 && dd.querySelector("base") &&
        dd.querySelector("base").getAttribute("href") === "../" && dd.title.includes("Fretladder") && dd.querySelectorAll('a[href^="song/"]').length >= 1, rr.status);
  }
  say("the totals are the strapline's count", d.querySelector("p.totals") && d.querySelector("p.totals").textContent.includes(
      Object.values(BOOT.data).reduce((n, s) => n + s.rows, 0).toLocaleString("en-US") + " charts"), d.querySelector("p.totals") && d.querySelector("p.totals").textContent);
}
done();
