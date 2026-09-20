// The opening view, the explainer panel, the URL the page writes, and the graph
// deep link. Every expected value comes from the boot payload or the DOM.
import { BOOT, rows as sheetRows, say, done, wait, key, click, chip, lit, shown, params, ready } from "./lib.js";
await ready();

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
// section 24: the section a crawler reads is gone once the app has booted, and the brand is not a heading
const guide = document.getElementById("static");
say("the guide is in the DOM, closed, between the table and the footer", guide && guide.tagName === "DETAILS" && !guide.open &&
    (guide.compareDocumentPosition(document.getElementById("foot")) & Node.DOCUMENT_POSITION_FOLLOWING) && (document.getElementById("body").compareDocumentPosition(guide) & Node.DOCUMENT_POSITION_FOLLOWING),
    guide && (guide.tagName + " open=" + guide.open));
say("it holds the page's one h1 and the brand is a paragraph", document.querySelectorAll("h1").length === 1 && guide.querySelector("h1") !== null && document.getElementById("brand").tagName === "P",
    document.querySelectorAll("h1").length + " " + document.getElementById("brand").tagName);
say("its summary is one short line and it opens on a click", guide.querySelector("summary").getBoundingClientRect().height < 40 && (click(guide.querySelector("summary")), guide.open),
    guide.querySelector("summary").getBoundingClientRect().height);
guide.open = false;
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
const docPages = (BOOT.docPages || [["about.html"]]).length;
const strapAnchors = document.querySelectorAll("#src2 a").length;      // the strapline links to the changelog when there is one
const wantLinks = 1 + docPages + FOOTER.length + richLinks(UI.copyright) + 1 + strapAnchors;   // request link, document pages, FOOTER, copyright anchors, licence
say("footer link count", footLinks.length === wantLinks, footLinks.length + " vs " + wantLinks);
say("request link is the pack form", /issues\/new\?template=song-pack\.yml$/
    .test(document.querySelector("#foot a.req").href));
say("about link is same-site", document.querySelector('#foot a[href="about.html"]') !== null);
say("footer strapline mirrors the header", document.getElementById("src2").textContent ===
    document.getElementById("src").textContent);

// --- the pack registry (section 03): strapline link, Added column -------------------
if (col("Added") >= 0) {
  const srcLink = document.querySelector('#src a[href="changelog.html"]');
  say("strapline is an anchor to changelog.html in the header", srcLink !== null);
  say("and in the footer copy", document.querySelector('#src2 a[href="changelog.html"]') !== null);
  say("changelog is linked from the footer", document.querySelector('#foot a[href="changelog.html"]') !== null);
  say("Added is hidden by default", !headCols.includes("Added") && HIDDEN_DEFAULT.includes("Added"));
  const dates = [...new Set(rows.map(r => r[col("Added")]).filter(v => typeof v === "string"))];
  say("every row carries a registry date", rows.every(r => typeof r[col("Added")] === "string"), dates.length + " distinct");
}

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
// the columns query.js's SEARCH_COLS names, Album included (section 08)
const wantSearch = rows.filter(r =>
    ["Song Title", "Artist", "Album", "Charter", "Release", "Code"].some(n =>
      String(r[col(n)] ?? "").toLowerCase().includes(title)) &&
    ["Expert", "Hard"].includes(r[col("Level")]) && r[col("Official")] === true).length;
say("rows match the search", shown() === wantSearch && wantSearch > 0, shown() + " vs " + wantSearch);

// --- filtering on an Added date (section 03) ----------------------------------------
// The changelog's date links are ?f.Added=<date>&f.Level=Expert; roundtrip.js covers
// the URL side, so here the same state is driven through the filter panel.
if (col("Added") >= 0) {
  const dates = [...new Set(rows.map(r => r[col("Added")]).filter(v => typeof v === "string"))].sort();
  const date = dates[dates.length - 1];
  const wantDate = rows.filter(r => r[col("Added")] === date).length;
  const wantDateExpert = rows.filter(r => r[col("Added")] === date && r[col("Level")] === "Expert").length;
  document.getElementById("clear").click();                          // no filters at all
  q.value = ""; q.dispatchEvent(new Event("input", { bubbles: true })); await wait(50);
  click(document.getElementById("cols")); await wait(30);
  document.querySelector('#cd input[data-col="Added"]').click();      // show the column so its caret exists
  document.body.click(); await wait(30);
  click(document.querySelector('#head th[data-c="Added"] .flt')); await wait(50);
  for (const v of document.querySelectorAll("#dd .v")) {             // a checklist applies on change
    const box = v.closest(".form-check").querySelector("input");
    if ((v.textContent === date) !== box.checked) box.click();
  }
  document.body.click(); await wait(100);
  say("filtering on one Added date shows every row of that update", shown() === wantDate, shown() + " vs " + wantDate);
  if (dates.length > 1)   // with one registry date, ticking the only value is no filter at all (by design)
    say("the Clear button counts one filter", /\b1\b/.test(document.getElementById("clear").textContent), document.getElementById("clear").textContent);
  for (const name of ["Hard", "Medium", "Easy"]) { click(chip("levels", name)); await wait(20); }   // all lit means no filter: switch the others off, re-querying since each click repaints

  say("plus Expert is the changelog's own link, official and custom", shown() === wantDateExpert, shown() + " vs " + wantDateExpert);
  await wait(400);
  if (dates.length > 1) say("the URL carries f.Added", params().get("f.Added") === date, location.search);
  // back to the state the deep-link block below expects: the search, Expert and Hard, Official, NoteCount sorted
  document.getElementById("clear").click(); await wait(50);
  click(document.getElementById("cols")); await wait(30);
  document.querySelector('#cd input[data-col="Added"]').click(); document.body.click(); await wait(30);
  q.value = title; q.dispatchEvent(new Event("input", { bubbles: true }));
  click(chip("levels", "Expert")); click(chip("levels", "Hard")); click(chip("official", UI.official_chip)); await wait(100);
}

// --- the details pane (section 14) ------------------------------------------------
const row = document.querySelector("#body tr[data-code]");
if (row) {
  row.focus();                                     // rows carry tabindex; the opener must hold focus
  click(row);
  await wait(400);
  const modal = document.getElementById("pane");
  say("row click opens the details pane under the table", modal.classList.contains("on") && modal.getAttribute("role") === "region" &&
      modal.compareDocumentPosition(document.getElementById("grid")) & Node.DOCUMENT_POSITION_PRECEDING);
  say("the table is still on screen, shorter", document.querySelector(".fw-wrap").getBoundingClientRect().height > 0 &&
      document.querySelector(".fw-wrap").getBoundingClientRect().bottom <= modal.getBoundingClientRect().top + 1);
  say("pane is labelled by code", modal.getAttribute("aria-label").endsWith(": " + row.dataset.code),
      modal.getAttribute("aria-label"));
  say("code is in the URL", params().get("code") === row.dataset.code, params().get("code"));
  const rpt = modal.querySelector(".mhead a.rpt");
  say("report link names the chart", rpt && /template=rating\.yml/.test(rpt.href) &&
      rpt.href.includes(encodeURIComponent(row.dataset.code)), rpt && rpt.href);
  say("heading carries title, artist, level, part, charter",
      modal.querySelectorAll(".mhead > *").length >= 5, modal.querySelectorAll(".mhead > *").length);
  say("the graph is a canvas drawn from the curve file, not an image",
      !!modal.querySelector(".gbody canvas") && !modal.querySelector("img"), modal.querySelector(".gbody") && modal.querySelector(".gbody").innerHTML.slice(0, 60));
  say("the row tip says what a click does", row.title.endsWith(UI.row_tip), JSON.stringify(row.title));
  if (col("Pct") >= 0) {
    const sentence = new RegExp(UI.pct_of.replace(/\{\w+\}/g, ".+?"));
    const links = rpt.closest(".lnk") || rpt;
    say("heading says where the chart sits, before the link group",
        sentence.test(modal.querySelector(".mhead").textContent) && links.previousElementSibling &&
        sentence.test(links.previousElementSibling.textContent) && (modal.querySelector(".mhead").lastElementChild === links ||
        modal.querySelector(".mhead").lastElementChild.classList.contains("copies")),
        modal.querySelector(".mhead").textContent);
  }
  key("Escape");
  await wait(400);
  say("Escape closes and clears the code", !modal.classList.contains("on") && params().get("code") === null);
  say("focus returns to the row", document.activeElement === row, document.activeElement.tagName);
  say("no graph or song dialog is in the page", !document.getElementById("modal") && !document.getElementById("song"));
} else {
  say("a row exists to click", false, "no #body tr[data-code]");
}

done();
