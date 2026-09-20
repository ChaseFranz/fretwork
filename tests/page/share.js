// Copy link (section 16): the pane's button puts the song page's address on
// the clipboard with the exact chart and comparison in its query; the song
// page carries the preview tags and forwards to the app. Launched with
// ?code=A&vs=B, so the comparison is on the graph when the button is pressed.
import { BOOT, rows as sheetRows, say, done, wait, click, ready, params } from "./lib.js";
await ready();
await wait(1200);

const { ui: UI } = BOOT;
const pane = document.getElementById("pane");
const code = params().get("code"), vs = params().get("vs");
say("the launch opened a comparison", pane.classList.contains("on") && !!vs, location.search);
const btn = pane.querySelector('.gtools [data-act="share"]');
say("the tool row has Copy link, after Save as PNG", btn && btn.textContent === UI.share && btn.title === UI.share_tip &&
    btn.previousElementSibling && btn.previousElementSibling.dataset.act === "save", btn && btn.textContent);

// the clipboard: captured, since headless Chrome grants no permission
let captured = null;
Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText: t => { captured = t; return Promise.resolve(); } } });
click(btn);
await wait(200);
const siteUrl = BOOT.siteUrl;
say("the page boots the site's address", typeof siteUrl === "string" && /^https?:\/\//.test(siteUrl), siteUrl);
// the key from the data, since the opening filters may hide the row
const sheet = BOOT.sheetOfCode[code.slice(-1)];
const rows = await sheetRows(sheet);
const cols = BOOT.data[sheet].columns;
const row = rows.find(r => r[cols.indexOf("Code")] === code);
const key = row && row[cols.indexOf("SongKey")];
const title = row && row[cols.indexOf("Song Title")];
const artist = row && row[cols.indexOf("Artist")];
say("the link is the song page with this chart and comparison", captured === siteUrl.replace(/\/+$/, "") + "/song/" + key + ".html?code=" + code + "&vs=" + vs, captured);
say("and the toast says so", document.getElementById("hint").textContent === UI.share_copied, document.getElementById("hint").textContent);

// the song page itself, fetched from the bundle
const res = await fetch("song/" + key + ".html");
say("the song page is in the bundle", res.status === 200 && (res.headers.get("content-type") || "").startsWith("text/html"), res.status);
const text = await res.text();
const doc = new DOMParser().parseFromString(text, "text/html");
const tag = p => { const m = doc.querySelector('meta[property="' + p + '"]'); return m && m.content; };
say("its og:title names the song", tag("og:title") && title && tag("og:title").startsWith(title), tag("og:title") + " vs " + title);
say("its og:description asks the question and gives the parts' facts", /^How hard is .+ in .+\? (Expert|Hard|Medium|Easy) \S+: D \d/.test(tag("og:description") || ""), tag("og:description"));
say("its og:url is its own address", tag("og:url") === siteUrl.replace(/\/+$/, "") + "/song/" + key + ".html", tag("og:url"));
// section 22: the picture is the first part's Expert graph, as og:image and on the page
say("its og:image is the song's own graph", /\/graph\/[A-Za-z0-9]{10}\.png$/.test(tag("og:image") || ""), tag("og:image"));
const img = doc.querySelector("p.pic img");
say("the page shows that graph with alt text", img && img.getAttribute("src") === "graph/" + tag("og:image").split("/").pop() && img.alt.startsWith("Difficulty graph of"), img && img.getAttribute("src"));
const pic = img && await fetch(img.getAttribute("src"));
say("and the PNG is in the bundle", pic && pic.status === 200 && (pic.headers.get("content-type") || "").startsWith("image/png"), pic && pic.status);
say("it says what the numbers are, in words", /it scores D \d/.test(doc.body.textContent));
say("no placeholder", !/__[A-Z][A-Z_]*__/.test(text));
// section 21: a page that forwards only when a shared link's query is on it
say("it forwards to the app only with a query, and is a page otherwise", text.includes('if(location.search)location.replace(location.search)') &&
    !text.includes('http-equiv="refresh"') && doc.querySelector("h1") && doc.querySelector("h1").textContent === title + (artist ? " by " + artist : "") &&
    doc.querySelectorAll('a[href^="./#code="]').length >= 1 && doc.querySelector('a[href="./#song=' + key + '"]') && !text.includes('href="./?'), doc.querySelector("h1") && doc.querySelector("h1").textContent);
say("three scripts: the forward, the theme and the JSON-LD", doc.querySelectorAll("script").length === 3 &&
    doc.querySelector('script[type="application/ld+json"]') && JSON.parse(doc.querySelector('script[type="application/ld+json"]').textContent).map(b => b["@type"]).join() === "MusicRecording,BreadcrumbList");
say("its base is the site root, so its links resolve as the other pages' do", doc.querySelector("base") && doc.querySelector("base").getAttribute("href") === "../");

// with one chart up the link carries the code alone
key && click(pane.querySelector('.legend [data-rm="' + vs.split(",")[0] + '"]'));
await wait(600);
captured = null;
click(pane.querySelector('.gtools [data-act="share"]'));
await wait(200);
say("with one chart up the link carries the code alone", captured === siteUrl.replace(/\/+$/, "") + "/song/" + key + ".html?code=" + code, captured);

// the failure path: a refused clipboard falls back to execCommand, and says so either way
Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText: () => Promise.reject(new Error("denied")) } });
const before = document.getElementById("hint").textContent;
click(pane.querySelector('.gtools [data-act="share"]'));
await wait(300);
const after = document.getElementById("hint").textContent;
say("a refused clipboard still ends in a toast", after === UI.share_copied || after === UI.share_failed, after);
done();
