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
say("the link is the song page with this chart and comparison", captured === siteUrl.replace(/\/+$/, "") + "/song/" + key + ".html?code=" + code + "&vs=" + vs, captured);
say("and the toast says so", document.getElementById("hint").textContent === UI.share_copied, document.getElementById("hint").textContent);

// the song page itself, fetched from the bundle
const res = await fetch("song/" + key + ".html");
say("the song page is in the bundle", res.status === 200 && (res.headers.get("content-type") || "").startsWith("text/html"), res.status);
const text = await res.text();
const doc = new DOMParser().parseFromString(text, "text/html");
const tag = p => { const m = doc.querySelector('meta[property="' + p + '"]'); return m && m.content; };
say("its og:title names the song", tag("og:title") && title && tag("og:title").startsWith(title), tag("og:title") + " vs " + title);
say("its og:description is the parts' facts", /^(Expert|Hard|Medium|Easy) \S+: D \d/.test(tag("og:description") || ""), tag("og:description"));
say("its og:url is its own address", tag("og:url") === siteUrl.replace(/\/+$/, "") + "/song/" + key + ".html", tag("og:url"));
say("no image, no placeholder", !tag("og:image") && !/__[A-Z][A-Z_]*__/.test(text));
say("it forwards to the app with its query, else the song", text.includes('location.replace("../"+(location.search||"?song=' + key + '"))') &&
    text.includes('content="0; url=../?song=' + key + '"'));
say("two scripts: the forward and the theme", doc.querySelectorAll("script").length === 2);

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
