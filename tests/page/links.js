// rich(): the one place markup becomes HTML; and every prose link on the page
// points where it should.
import { BOOT, rows as sheetRows, say, skip, done, wait, click, key, ready } from "./lib.js";
import { rich } from "./src/dom.js";
await ready();

// --- where to get this chart (sections 13, 14): the pane's link buttons and the link columns ---
// The runner delays the links file 800 ms, so a pane opened as soon as the rows
// are here has no anchors until the file lands, and they must appear without
// the pane being reopened; this block therefore runs before anything else waits.
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
  // the link columns (section 14): Chart names the first host (BOOT.hosts
  // order) the song is on, null for none; Leaderboard is a bit; each agrees
  // with the file, and a column exists only for a kind some song has (the
  // Local library has no leaderboard answers yet, so it has Chart alone)
  const hosts = BOOT.hosts.map(([key]) => key);
  say("the page carries the host table", hosts.length >= 1 && hosts.includes("enchor") && BOOT.hosts.every(([, h]) => h.label && h.tip && h.url.includes("{id}") && h.id), JSON.stringify(hosts));
  const hostOf = key => hosts.find(h => (linksDoc.songs[key] || {})[h]) || null;
  const anyChart = Object.values(linksDoc.songs).some(v => hosts.some(h => h in v));
  const anyLb = Object.values(linksDoc.songs).some(v => "lb" in v);
  const present = [anyChart && "Chart", anyLb && "Leaderboard"].filter(Boolean);
  say("a link column exists for each link kind the file has, after Pct", present.length > 0 && present.every((c, i) => cols.indexOf(c) === cols.indexOf("Pct") + 1 + i) &&
      ["Chart", "Leaderboard"].every(c => cols.includes(c) === present.includes(c)), cols.slice(-3).join() + " for " + present.join());
  say("each row's Chart is its song's first host, and Leaderboard its bit", rows.every(r =>
      (!present.includes("Chart") || r[at("Chart")] === hostOf(r[at("SongKey")])) &&
      (!present.includes("Leaderboard") || r[at("Leaderboard")] === !!(linksDoc.songs[r[at("SongKey")]] || {}).lb)));
  say("the Chart column's filter list labels the hosts", present.includes("Chart") ? BOOT.valueLabels.Chart && BOOT.valueLabels.Chart.enchor === "Chorus Encore" : true, JSON.stringify(BOOT.valueLabels.Chart));
  const headCols = [...document.querySelectorAll("#head th")].map(th => th.dataset.c);
  say("the link columns are on by default, right after Artist", present.every((c, i) => headCols.indexOf(c) === headCols.indexOf("Artist") + 1 + i), headCols.join());
  const KINDS = { Chart: "enchor", Leaderboard: "lb" };
  const onScreen = new Set([...document.querySelectorAll("#body tr[data-code]")].map(tr => tr.dataset.code));
  const withBoth = rows.find(r => onScreen.has(r[at("Code")]) && linksDoc.songs[r[at("SongKey")]] && present.every(c => linksDoc.songs[r[at("SongKey")]][KINDS[c]]));
  const withNone = rows.find(r => onScreen.has(r[at("Code")]) && !linksDoc.songs[r[at("SongKey")]]);
  if (!withBoth) {
    skip("linked chart", "no chart on the opening view has every link");
  } else {
    const pane = document.getElementById("pane");
    const row = document.querySelector('#body tr[data-code="' + withBoth[at("Code")] + '"]');
    const cellOf = (tr, c) => tr.children[headCols.indexOf(c)];
    const earlyCell = cellOf(row, "Chart").innerHTML;
    click(row);
    await wait(300);
    const early = pane.querySelectorAll(".gtools a.ext").length;
    await wait(1200);
    const ext = [...pane.querySelectorAll(".gtools a.ext")];
    const song = linksDoc.songs[withBoth[at("SongKey")]];
    // whether the delayed file lands before or after the click depends on the
    // virtual clock; either way the open pane must end up with both anchors
    say("the link buttons are on the open pane once the file has landed", ext.length === present.length, early + " at open, then " + ext.length);
    say("Chorus Encore links the chart's page", ext[0] && ext[0].textContent.startsWith(BOOT.hosts[0][1].label) && ext[0].href === "https://enchor.us/chart/" + song.enchor, ext[0] && ext[0].href);
    if (present.includes("Leaderboard"))
      say("Leaderboard links the scores page", ext[1] && ext[1].textContent.startsWith(BOOT.ui.leaderboard) && ext[1].href === "https://leaderboards.clonehero.net/scores/" + song.lb, ext[1] && ext[1].href);
    say("all open a new tab safely", ext.every(a => a.target === "_blank" && a.rel.includes("noopener")));
    say("they lead the tool row, before Compare with a row", pane.querySelector(".gtools").firstElementChild === ext[0] && ext[ext.length - 1].nextElementSibling.dataset.act === "pick");
    say("the heading keeps the report link last in its group", pane.querySelector(".mhead .lnk") && pane.querySelector(".mhead .lnk").lastElementChild.classList.contains("rpt"));
    // the row's own cells: the arrow became an anchor in place, without a redraw
    const enchorCell = cellOf(row, "Chart"), lbCell = cellOf(row, "Leaderboard");
    say("the Chart cell is an arrow to the same page", enchorCell.querySelector("a.ext") && enchorCell.querySelector("a.ext").href === ext[0].href && enchorCell.textContent.trim() === "\u2197",
        enchorCell.innerHTML + " (was " + earlyCell + ")");
    if (lbCell) say("the Scores cell is an arrow to the scores page", lbCell.querySelector("a.ext") && lbCell.querySelector("a.ext").href === ext[1].href);
    say("no waiting arrow is left in the table", !document.querySelector("#body td.lnkc .wait, #body td.lnkc[data-k]"));
    say("the arrow opens a new tab and does not choose the row", enchorCell.querySelector("a.ext").target === "_blank" && row.isConnected && document.querySelector("#body tr.sel") === row);
    // clicking the arrow itself routes to the browser, not the row
    const before = pane.getAttribute("aria-label");
    const a = enchorCell.querySelector("a.ext");
    const ev = new MouseEvent("click", { bubbles: true, cancelable: true });
    a.addEventListener("click", e => e.preventDefault(), { once: true });   // no real navigation in the harness
    a.dispatchEvent(ev);
    await wait(200);
    say("a click on the arrow leaves the pane where it was", pane.classList.contains("on") && pane.getAttribute("aria-label") === before, pane.getAttribute("aria-label"));
    key("Escape");
    await wait(200);
    if (withNone) {
      const bare = document.querySelector('#body tr[data-code="' + withNone[at("Code")] + '"]');
      say("a song not in the file has empty link cells", present.every(c => cellOf(bare, c).textContent.trim() === ""));
      click(bare);
      await wait(400);
      say("and no link button, the tools starting with Compare with a row", pane.querySelectorAll(".gtools a.ext").length === 0 && pane.querySelector(".gtools").firstElementChild.dataset.act === "pick");
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
      [...doc.querySelectorAll("h2 a")].every(a => /^\.\/#f\.Added=\d{4}-\d{2}-\d{2}&f\.Level=Expert$/.test(a.getAttribute("href"))));
}
// the raw markup lives in the JSON island, which is not rendered text
const shown = [document.querySelector(".fw-head"), document.getElementById("body"), document.getElementById("about"), document.getElementById("foot")]
  .map(e => e.textContent).join(" ");
say("no unrendered [text](url) in anything visible", !/\[[^\]]+\]\(https?:/.test(shown));
done();
