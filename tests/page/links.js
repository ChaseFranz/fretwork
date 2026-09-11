// rich(): the one place markup becomes HTML; and every prose link on the page
// points where it should.
import { BOOT, rows as sheetRows, say, skip, done, wait, click, key, ready } from "./lib.js";
import { rich } from "./src/dom.js";
await ready();

// --- where to get this chart (section 13): two anchors from data/links.<hash>.json ---
// The runner delays that file 800 ms, so a graph opened as soon as the rows are
// here has no anchors until the file lands, and they must appear without the
// graph being reopened; this block therefore runs before anything else waits.
if (!BOOT.links) {
  skip("links file", "this bundle has no links file");
} else {
  const sheet = Object.keys(BOOT.data)[0];
  const rows = await sheetRows(sheet);
  const cols = BOOT.data[sheet].columns;
  const at = n => cols.indexOf(n);
  // the file itself, fetched under a spelling the runner's delay does not match
  const linksDoc = await fetch("%64" + BOOT.links.slice(1)).then(r => r.json());
  say("the links file has the documented shape", linksDoc.v === 1 && typeof linksDoc.songs === "object", JSON.stringify(linksDoc).slice(0, 80));
  const onScreen = new Set([...document.querySelectorAll("#body tr[data-code]")].map(tr => tr.dataset.code));
  const withBoth = rows.find(r => onScreen.has(r[at("Code")]) && linksDoc.songs[r[at("SongKey")]] && linksDoc.songs[r[at("SongKey")]].enchor && linksDoc.songs[r[at("SongKey")]].lb);
  const withNone = rows.find(r => onScreen.has(r[at("Code")]) && !linksDoc.songs[r[at("SongKey")]]);
  if (!withBoth) {
    skip("linked chart", "no chart on the opening view has both links");
  } else {
    const modal = document.getElementById("modal");
    const row = document.querySelector('#body tr[data-code="' + withBoth[at("Code")] + '"]');
    click(row);
    await wait(300);
    const early = modal.querySelectorAll(".mhead a.ext").length;
    await wait(1200);
    const ext = [...modal.querySelectorAll(".mhead a.ext")];
    const song = linksDoc.songs[withBoth[at("SongKey")]];
    // whether the delayed file lands before or after the click depends on the
    // virtual clock; either way the open graph must end up with both anchors
    say("the anchors are on the open graph once the file has landed", ext.length === 2, early + " at open, then " + ext.length);
    say("On Chorus Encore links the chart's page", ext[0] && ext[0].textContent === BOOT.ui.enchor && ext[0].href === "https://enchor.us/chart/" + song.enchor, ext[0] && ext[0].href);
    say("Leaderboard links the scores page", ext[1] && ext[1].textContent === BOOT.ui.leaderboard && ext[1].href === "https://leaderboards.clonehero.net/scores/" + song.lb, ext[1] && ext[1].href);
    say("both open a new tab safely", ext.every(a => a.target === "_blank" && a.rel.includes("noopener")));
    const lnk = modal.querySelector(".mhead .lnk");
    say("they sit in the link group, the report link last", lnk && lnk.contains(ext[0]) && lnk.lastElementChild.classList.contains("rpt"), lnk && lnk.innerHTML.slice(0, 80));
    // the phone: the heading wraps and the card does not scroll sideways
    // (the canvas keeps its width without a frame to resize in, so the heading is what is measured)
    const card = modal.querySelector(".mcard");
    card.style.width = "390px";
    await wait(50);
    const rpt = modal.querySelector(".mhead .rpt"), mhead = modal.querySelector(".mhead");
    say("at 390px the heading wraps and does not scroll sideways",
        mhead.offsetHeight >= 2 * rpt.offsetHeight && mhead.scrollWidth <= mhead.clientWidth,
        mhead.offsetHeight + " vs " + rpt.offsetHeight + ", " + mhead.scrollWidth + "/" + mhead.clientWidth);
    card.style.width = "";
    key("Escape");
    await wait(200);
    if (withNone) {
      click(document.querySelector('#body tr[data-code="' + withNone[at("Code")] + '"]'));
      await wait(400);
      say("a song not in the file shows no anchor", modal.querySelectorAll(".mhead a.ext").length === 0 && modal.querySelector(".mhead a.rpt"));
      key("Escape");
      await wait(200);
    }
  }
}

say("renders an https link", rich("see [fretwork](https://x.test/a) now") === 'see <a href="https://x.test/a" target="_blank" rel="noopener">fretwork</a> now',
    rich("see [fretwork](https://x.test/a) now"));
say("escapes text around it", rich('a <b> & "c"') === 'a &lt;b> &amp; &quot;c&quot;', rich('a <b> & "c"'));
say("escapes the link text", !/<script/.test(rich("[<script>x</script>](https://x.test/)")), rich("[<script>x</script>](https://x.test/)"));
say("a non-http target is plain text", rich("see [x](javascript:alert(1))") === "see x", rich("see [x](javascript:alert(1))"));
say("a relative target is plain text too", rich("[x](../y.html)") === "x", rich("[x](../y.html)"));
say("balanced parentheses stay in the url", rich("[p](https://x.test/a_(b))") === '<a href="https://x.test/a_(b)" target="_blank" rel="noopener">p</a>',
    rich("[p](https://x.test/a_(b))"));
say("leaves plain text alone", rich("no links here") === "no links here");
// a same-site document page (section 12): a same-tab anchor, no target, no rel
say("a document page is a same-tab anchor", rich("[x](methodology.html)") === '<a href="methodology.html">x</a>', rich("[x](methodology.html)"));
say("with an anchor inside it", rich("[x](methodology.html#calctier-calibration)") === '<a href="methodology.html#calctier-calibration">x</a>');
say("but not a path, a query or an upper-case name", rich("[x](a/b.html)") === "x" && rich("[x](b.html?q=1)") === "x" && rich("[x](B.html)") === "x");

click(document.getElementById("how"));
await wait(400);
const named = el => [...el.querySelectorAll("a")].map(a => [a.textContent, a.getAttribute("href") || ""]);
const panel = named(document.getElementById("about"));
const methodInPanel = [...document.querySelectorAll('#about a[href="methodology.html"]')];
say("the explainer links the methodology page twice, in the same tab", methodInPanel.length === 2 && methodInPanel.every(a => !a.target), methodInPanel.length);
const methodInFoot = document.querySelector('#foot a[href="methodology.html"]');
say("the footer links the methodology page in the same tab", !!methodInFoot && !methodInFoot.target);
const foot = named(document.getElementById("foot"));
const head = named(document.querySelector(".fw-head"));
const all = panel.concat(foot, head);
say("the panel links fretwork", panel.some(([t, h]) => t === "fretwork" && /^https?:/.test(h)), JSON.stringify(panel.map(p => p[0])));
say("the panel links the author", panel.some(([t, h]) => /Staycation/.test(t) && /^https?:/.test(h)));
say("the video caption links the channel", panel.some(([t, h]) => t === "Staycation44" && /youtube\.com\/@StaycationGH/.test(h)));
say("the footer copyright links both", foot.some(([t]) => t === "fretwork") && foot.some(([t]) => /^Staycation/.test(t)), JSON.stringify(foot.map(f => f[0])));
say("every external link is YouTube or GitHub", all.every(([, h]) => !/^https?:/.test(h) || /(youtube\.com|youtu\.be|github\.com)/.test(h)),
    JSON.stringify(all.filter(([, h]) => /^https?:/.test(h) && !/(youtube\.com|youtu\.be|github\.com)/.test(h))));
say("every other link is same-site", all.every(([, h]) => /^https?:/.test(h) || /^[\w./-]+(\?.*)?$/.test(h) || h.startsWith("#")),
    JSON.stringify(all.filter(([, h]) => !/^https?:/.test(h)).map(x => x[1])));
say("external links open in a new tab safely", [...document.querySelectorAll('#about a[href^="http"], #foot a[href^="http"]')]
    .every(a => a.rel.includes("noopener")));
// the changelog (section 03) is a page of its own, linked from the footer
const cl = document.querySelector('#foot a[href="changelog.html"]');
if (cl) {
  const res = await fetch("changelog.html");
  say("changelog.html is published", res.status === 200, res.status);
  const doc = new DOMParser().parseFromString(await res.text(), "text/html");
  say("it carries a totals line and at least one date", doc.querySelector("p.totals") !== null && doc.querySelectorAll("h2").length >= 1,
      doc.querySelectorAll("h2").length + " dates");
  say("every date heading links the table filtered to that update",
      [...doc.querySelectorAll("h2 a")].every(a => /^\.\/\?f\.Added=\d{4}-\d{2}-\d{2}&f\.Level=Expert$/.test(a.getAttribute("href"))));
}
// the raw markup lives in the JSON island, which is not rendered text
const shown = [document.querySelector(".fw-head"), document.getElementById("body"), document.getElementById("about"), document.getElementById("foot")]
  .map(e => e.textContent).join(" ");
say("no unrendered [text](url) in anything visible", !/\[[^\]]+\]\(https?:/.test(shown));
done();
