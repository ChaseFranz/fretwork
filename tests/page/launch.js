// The opening view, the explainer panel, the URL the page writes, and the graph
// deep link. Every expected value comes from the boot payload or the DOM.
import { BOOT, rows as sheetRows, say, done, wait, key, click, chip, lit, shown, params } from "./lib.js";

const { ui: UI, footer: FOOTER, explainer: EXPLAINER, hiddenDefault: HIDDEN_DEFAULT } = BOOT;
const sheet = Object.keys(BOOT.data)[0];
const cols = BOOT.data[sheet].columns;
const rows = await sheetRows(sheet);
const col = name => cols.indexOf(name);
const richLinks = text => (String(text).match(/\]\(https?:\/\//g) || []).length;

// --- the opening view ---------------------------------------------------------
say("no query string on the opening view", location.search === "", location.search);
say("brand is the site name", document.getElementById("brand").textContent.startsWith(UI.title),
    document.getElementById("brand").textContent);
say("strapline is a public one", /^Updated \d{1,2} [A-Z][a-z]+ \d{4}  -  [\d,]+ charts$/
    .test(document.getElementById("src").textContent), document.getElementById("src").textContent);
say("Expert is the only lit level", JSON.stringify(lit("levels")) === '["Expert"]', lit("levels"));
say("Official is lit", JSON.stringify(lit("official")) === '["' + UI.official_chip + '"]', lit("official"));

const landing = r => r[col("Level")] === "Expert" && r[col("Official")] === true;
const wantShown = rows.filter(landing).length;
say("row count is Expert and Official", shown() === wantShown, shown() + " vs " + wantShown);
say("count text says so", document.getElementById("count").textContent ===
    UI.count.replace("{shown}", wantShown).replace("{total}", rows.length),
    document.getElementById("count").textContent);

const headCols = [...document.querySelectorAll("#head th")].map(th => th.dataset.c);
const hiddenShown = headCols.filter(c => HIDDEN_DEFAULT.includes(c));
say("default-hidden columns are hidden", hiddenShown.length === 0, hiddenShown);
say("Rank leads the table", headCols[0] === "Rank", headCols[0]);
say("D is sorted descending", document.querySelector('#head th[data-c="D"]').getAttribute("aria-sort")
    === "descending");

// --- percentile (section 02) ---------------------------------------------------
if (col("Pct") >= 0) {
  say("Percentile sits right after D", headCols[headCols.indexOf("D") + 1] === "Pct", headCols.join());
  const first = document.querySelector("#body tr[data-code]");
  const pctText = first.children[headCols.indexOf("Pct")].textContent;
  say("Percentile prints a whole number", /^\d+$/.test(pctText), pctText);
  say("row tip says where the chart sits", new RegExp("^" + UI.pct_of.replace(/\{\w+\}/g, ".+") + "\\n").test(first.title),
      JSON.stringify(first.title));
}

// --- footer ---------------------------------------------------------------------
const footLinks = [...document.querySelectorAll("#foot a")];
const docPages = (BOOT.docPages || ["about.html"]).length;   // 12 adds DOC_PAGES to the payload; until then about.html alone
const wantLinks = 1 + docPages + FOOTER.length + richLinks(UI.copyright) + 1;   // request link, document pages, FOOTER, copyright anchors, licence
say("footer link count", footLinks.length === wantLinks, footLinks.length + " vs " + wantLinks);
say("request link is the pack form", /issues\/new\?template=song-pack\.yml$/
    .test(document.querySelector("#foot a.req").href));
say("about link is same-site", document.querySelector('#foot a[href="about.html"]') !== null);
say("footer strapline mirrors the header", document.getElementById("src2").textContent ===
    document.getElementById("src").textContent);

// --- explainer panel ----------------------------------------------------------
const how = document.getElementById("how");
say("How it works is an underlined text link", /How it works/.test(how.textContent) &&
    getComputedStyle(how).textDecorationLine === "underline");
how.focus();                                       // the opener is whatever has focus at open time
click(how);
const about = document.getElementById("about");
say("panel opens as a dialog", about.classList.contains("on") && about.getAttribute("role") === "dialog");
say("panel takes focus", document.activeElement === about, document.activeElement.id);
say("one heading per explainer entry", about.querySelectorAll("h2").length === EXPLAINER.length,
    about.querySelectorAll("h2").length);
say("explainer text is the payload's", EXPLAINER.every(([h]) =>
    [...about.querySelectorAll("h2")].some(el => el.textContent === h)));
key("Escape");
say("Escape closes the panel", !about.classList.contains("on"));
say("focus returns to the opener", document.activeElement === how, document.activeElement.id);

// --- URL state ------------------------------------------------------------------
// A row that passes the filters asserted below, so the search shows at least it;
// the first word, because url.js trims q.
const seed = rows.find(landing);
const title = String(seed[col("Song Title")]).split(/\s+/)[0].toLowerCase();
const q = document.getElementById("q");
q.value = title;
q.dispatchEvent(new Event("input", { bubbles: true }));
click(chip("levels", "Hard"));
click(document.querySelector('#head th[data-c="NoteCount"] .lbl'));
await wait(400);                                   // writeUrl is debounced 250 ms
let p = params();
say("q is written", p.get("q") === title, p.get("q"));
say("levels are written", p.get("f.Level") === "Expert,Hard", p.get("f.Level"));
say("official is written", p.get("f.Official") === "true", p.get("f.Official"));
say("sort and direction are written", p.get("sort") === "NoteCount" && p.get("dir") === "desc",
    p.get("sort") + " " + p.get("dir"));
say("sheet is not written for the first sheet", p.get("sheet") === null);
const wantSearch = rows.filter(r =>
    ["Song Title", "Artist", "Charter", "Release", "Code"].some(n =>
      String(r[col(n)] ?? "").toLowerCase().includes(title)) &&
    ["Expert", "Hard"].includes(r[col("Level")]) && r[col("Official")] === true).length;
say("rows match the search", shown() === wantSearch && wantSearch > 0, shown() + " vs " + wantSearch);

// --- graph deep link ------------------------------------------------------------
const row = document.querySelector("#body tr[data-code]");
if (row) {
  row.focus();                                     // rows carry tabindex; the opener must hold focus
  click(row);
  await wait(400);
  const modal = document.getElementById("modal");
  say("row click opens the graph", modal.classList.contains("on"));
  say("graph is labelled by code", modal.getAttribute("aria-label").endsWith(": " + row.dataset.code),
      modal.getAttribute("aria-label"));
  say("code is in the URL", params().get("code") === row.dataset.code, params().get("code"));
  const rpt = modal.querySelector(".mhead a.rpt");
  say("report link names the chart", rpt && /template=rating\.yml/.test(rpt.href) &&
      rpt.href.includes(encodeURIComponent(row.dataset.code)), rpt && rpt.href);
  say("heading carries title, artist, level, part, charter",
      modal.querySelectorAll(".mhead > *").length >= 5, modal.querySelectorAll(".mhead > *").length);
  if (col("Pct") >= 0) {
    const sentence = new RegExp(UI.pct_of.replace(/\{\w+\}/g, ".+?"));
    say("heading says where the chart sits, before the report link",
        sentence.test(modal.querySelector(".mhead").textContent) && modal.querySelector(".mhead").lastElementChild === rpt,
        modal.querySelector(".mhead").textContent);
  }
  key("Escape");
  await wait(400);
  say("Escape closes and clears the code", !modal.classList.contains("on") && params().get("code") === null);
  say("focus returns to the row", document.activeElement === row, document.activeElement.tagName);
} else {
  say("a row exists to click", false, "no #body tr[data-code]");
}

done();
