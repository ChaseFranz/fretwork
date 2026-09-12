// Album, Year and Genre (section 08): three more columns, hidden until chosen,
// a sentinel year that no range admits, and a search that reads Album but
// never Genre. The runner launches this five times: once plain, and once per
// query string below.
import { BOOT, rows as sheetRows, say, done, wait, click, key, shown, painted, params, ready } from "./lib.js";
await ready();

const { labels: LABELS, missText: DASH } = BOOT;
const p = params();
const sheet = p.get("sheet") || Object.keys(BOOT.data)[0];
const rows = await sheetRows(sheet);
const cols = BOOT.data[sheet].columns;
const col = n => cols.indexOf(n);
const headCols = () => [...document.querySelectorAll("#head th")].map(th => th.dataset.c);
const seq = a => JSON.stringify(a);
const THREE = ["Album", "Year", "Genre"];

// Tick a column in the chooser so its cells can be read.
async function show(c) {
  if (!headCols().includes(c)) {
    if (!document.getElementById("cd").classList.contains("show")) { click(document.getElementById("cols")); await wait(50); }
    document.querySelector('#cd input[data-col="' + c + '"]').click();
    await wait(50);
  }
}
const cells = c => [...document.querySelectorAll("#body tr[data-code]")].map(tr => tr.children[headCols().indexOf(c)].textContent);

say("the sheet carries the three columns", THREE.every(c => cols.includes(c)), seq(cols));

if (!p.toString()) {
  // --- the default view ---------------------------------------------------------
  say("the default header lacks Album, Year and Genre", THREE.every(c => !headCols().includes(c)), seq(headCols()));
  click(document.getElementById("cols"));
  await wait(50);
  const items = [...document.querySelectorAll("#cd .cc[data-col]")].map(e => e.dataset.col);
  const at = items.indexOf("Release");
  say("the chooser lists them immediately after Source", at >= 0 && seq(items.slice(at, at + 4)) === seq(["Release", ...THREE]),
      seq(items.slice(Math.max(0, at), at + 4)));
  say("and unticked", THREE.every(c => !document.querySelector('#cd input[data-col="' + c + '"]').checked));
  say("their labels are the plain words", LABELS.Album === "Album" && LABELS.Year === "Year" && LABELS.Genre === "Genre");
  await show("Album");
  // every painted row has the cell (the DOM is a window of the view, section 17)
  const album = document.querySelectorAll("#body tr[data-code] td.album");
  say("ticking Album yields td.album cells", album.length === painted() && painted() > 0, album.length + " of " + painted());
  await show("Genre");
  const genre = document.querySelectorAll("#body tr[data-code] td.genre");
  say("ticking Genre yields td.genre cells", genre.length === painted(), genre.length + " of " + painted());
  await show("Year");
  document.body.click();
  await wait(50);
  const year = cells("Year");
  const sentinel = rows.filter(r => r[col("Year")] === -1).length;
  say("a year of -1 prints as the dash", year.every(v => /^\d{4}$/.test(v) || v === DASH), seq([...new Set(year)]));
  say("(the fixture has a sentinel year on this sheet)", sentinel > 0, sentinel);
  // sort by Year both ways: the dashes are last in both
  const sortBtn = () => document.querySelector('#head th[data-c="Year"] .lbl');   // the header is rebuilt on every draw
  click(sortBtn()); await wait(50);
  const official = document.querySelector("#official button.active");
  if (official) { click(official); await wait(50); }   // every row, so the -1s are on screen
  const lastDash = a => a.indexOf(DASH) < 0 || a.slice(a.indexOf(DASH)).every(v => v === DASH);
  // the DOM holds a window of the view (section 17): End paints its tail, where the dashes are
  const tail = () => { const r = document.querySelector("#body tr[data-code]"); r.focus(); key("End", r); return cells("Year"); };
  const asc = tail();
  click(sortBtn()); await wait(50);
  const desc = tail();
  say("sorting by Year puts the dashes last in both directions",
      asc.includes(DASH) && lastDash(asc) && lastDash(desc) && asc[0] !== desc[0], seq(asc.slice(-3)) + " " + seq(desc.slice(-3)));
} else if (p.get("r.Difficulty")) {
  // --- a hi-only range on a column with a sentinel ---------------------------------
  await show("Difficulty");
  document.body.click();
  const seen = cells("Difficulty");
  const hi = parseInt(p.get("r.Difficulty").split(":")[1], 10);
  const want = rows.filter(r => r[col("Difficulty")] !== -1 && r[col("Difficulty")] <= hi).length;
  say("?r.Difficulty=:N shows rows", shown() > 0, shown());
  say("and no unrated row", !seen.includes(DASH) && seen.every(v => parseInt(v, 10) <= hi), seq([...new Set(seen)]));
  say("count equals the rated rows at or below N", shown() === want, shown() + " vs " + want);
} else if (p.get("r.Year")) {
  // --- a year range ------------------------------------------------------------------
  await show("Year");
  document.body.click();
  const [lo, hi] = p.get("r.Year").split(":").map(v => parseInt(v, 10));
  const seen = cells("Year");
  say("Year header is marked filtered", document.querySelector('#head th[data-c="Year"]').classList.contains("filtered"));
  say("the view is filtered", shown() > 0 && shown() < rows.length, shown() + " of " + rows.length);
  say("no dash in the Year column", !seen.includes(DASH) && seen.every(v => +v >= lo && +v <= hi), seq([...new Set(seen)]));
  say("count equals the rows in range", shown() === rows.filter(r => r[col("Year")] >= lo && r[col("Year")] <= hi).length, shown());
  await wait(400);
  say("the page writes the range back", params().get("r.Year") === p.get("r.Year"), location.search);
} else if (p.get("q")) {
  // --- search: Album is read, Genre is not ---------------------------------------------
  const q = p.get("q").toLowerCase();
  const inAlbum = rows.filter(r => String(r[col("Album")] ?? "").toLowerCase().includes(q));
  const inGenre = rows.filter(r => String(r[col("Genre")] ?? "").toLowerCase().includes(q));
  const elsewhere = rows.filter(r => ["Song Title", "Artist", "Charter", "Release", "Code"]
    .some(n => String(r[col(n)] ?? "").toLowerCase().includes(q)));
  if (inAlbum.length) {
    say("the album text is not elsewhere in these rows", elsewhere.length === 0, elsewhere.length);
    say("?q=<album> finds its rows through Album alone", shown() === inAlbum.length && shown() > 0, shown() + " vs " + inAlbum.length);
  } else {
    say("the genre text is in some row's Genre and nowhere else", inGenre.length > 0 && elsewhere.length === 0, inGenre.length + " " + elsewhere.length);
    say("?q=<genre> finds none: Genre is not searched", shown() === 0 && !!document.querySelector("#body tr.empty"), shown());
  }
}

done();
