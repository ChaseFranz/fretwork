// rich(): the one place markup becomes HTML; and every prose link on the page
// points where it should.
import { say, done, wait, click } from "./lib.js";
import { rich } from "./src/dom.js";

say("renders an https link", rich("see [fretwork](https://x.test/a) now") === 'see <a href="https://x.test/a" target="_blank" rel="noopener">fretwork</a> now',
    rich("see [fretwork](https://x.test/a) now"));
say("escapes text around it", rich('a <b> & "c"') === 'a &lt;b> &amp; &quot;c&quot;', rich('a <b> & "c"'));
say("escapes the link text", !/<script/.test(rich("[<script>x</script>](https://x.test/)")), rich("[<script>x</script>](https://x.test/)"));
say("a non-http target is plain text", rich("see [x](javascript:alert(1))") === "see x", rich("see [x](javascript:alert(1))"));
say("a relative target is plain text too", rich("[x](../y.html)") === "x", rich("[x](../y.html)"));
say("balanced parentheses stay in the url", rich("[p](https://x.test/a_(b))") === '<a href="https://x.test/a_(b)" target="_blank" rel="noopener">p</a>',
    rich("[p](https://x.test/a_(b))"));
say("leaves plain text alone", rich("no links here") === "no links here");

click(document.getElementById("how"));
await wait(400);
const named = el => [...el.querySelectorAll("a")].map(a => [a.textContent, a.getAttribute("href") || ""]);
const panel = named(document.getElementById("about"));
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
// the raw markup lives in the JSON island, which is not rendered text
const shown = [document.querySelector(".fw-head"), document.getElementById("body"), document.getElementById("about"), document.getElementById("foot")]
  .map(e => e.textContent).join(" ");
say("no unrendered [text](url) in anything visible", !/\[[^\]]+\]\(https?:/.test(shown));
done();
