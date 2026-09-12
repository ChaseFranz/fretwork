// A shared link restores the state it names, and replaces the opening defaults
// rather than merging with them. The runner composes the query from the payload.
import { BOOT, rows as sheetRows, say, done, wait, lit, shown, params, ready } from "./lib.js";
await ready();

await wait(300);
const p = params();
const sheet = p.get("sheet");
const rows = await sheetRows(sheet);
say("a query string was supplied", p.get("q") !== null && sheet !== null, location.search);
say("search box restored", document.getElementById("q").value === p.get("q"), document.getElementById("q").value);
say("levels restored", JSON.stringify(lit("levels")) === JSON.stringify(p.get("f.Level").split(",")), JSON.stringify(lit("levels")));
say("the official default was replaced, not merged", lit("official").length === 0, JSON.stringify(lit("official")));
const th = document.querySelector('#head th[aria-sort="ascending"]');
say("sort column and direction restored", th && th.dataset.c === p.get("sort") && p.get("dir") === "asc", th && th.dataset.c);
say("sheet restored", document.querySelector("#sheets .active").textContent === sheet, document.querySelector("#sheets .active").textContent);
say("the view is filtered", shown() > 0 && shown() < rows.length, shown() + " of " + rows.length);
if (p.get("r.Pct")) {
  const cols = BOOT.data[sheet].columns;
  const headCols = [...document.querySelectorAll("#head th")].map(t => t.dataset.c);
  const cells = [...document.querySelectorAll("#body tr[data-code]")].map(tr => parseInt(tr.children[headCols.indexOf("Pct")].textContent, 10));
  const lo = parseInt(p.get("r.Pct").split(":")[0], 10);
  say("Percentile header is marked filtered", document.querySelector('#head th[data-c="Pct"]').classList.contains("filtered"));
  say("every visible Percentile is at or above the range floor", cells.length > 0 && cells.every(v => v >= lo), JSON.stringify(cells.slice(0, 8)));
  const want = rows.filter(r => r[cols.indexOf("Level")] === "Hard" && r[cols.indexOf("Pct")] >= lo &&
    ["Song Title", "Artist", "Album", "Charter", "Release", "Code"].some(n => String(r[cols.indexOf(n)] ?? "").toLowerCase().includes(p.get("q")))).length;
  say("count equals the rows the query names", shown() === want, shown() + " vs " + want);
}
// preference version (section 05): a saved fw.hidden with no fw.v is replaced by the default once
say("a stale saved column set is replaced by the default", localStorage.getItem("fw.hidden") === null &&
    [...document.querySelectorAll("#head th")].some(th => th.dataset.c === "Artist"), localStorage.getItem("fw.hidden"));
say("the version stamp is written", localStorage.getItem("fw.v") === String(BOOT.prefsVersion), localStorage.getItem("fw.v"));
// writing back: the URL the page writes equals what it read
await wait(400);
const q2 = params();
say("the page writes the same state back", ["sheet", "q", "sort", "dir", "f.Level"].every(k => q2.get(k) === p.get(k)), location.search);
done();
