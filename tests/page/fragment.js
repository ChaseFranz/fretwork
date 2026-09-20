// A document page links into the app by fragment (section 24): ./#code=X opens
// that chart as ?code=X would, and the address bar then carries the query
// form, so a crawler sees one front page and a visitor sees the same URL as
// before. Launched with a #code= fragment naming a chart on the second sheet.
import { BOOT, rows as sheetRows, say, done, wait, ready } from "./lib.js";

const asked = location.hash.length > 1 ? new URLSearchParams(location.hash.slice(1)).get("code") : null;
say("the page was opened with a code in the fragment and no query", !!asked && location.search === "", location.hash + " " + location.search);
await ready();
await wait(600);
const params = new URLSearchParams(location.search);
say("the fragment was read as the query", params.get("code") === asked, location.search);
say("and the fragment is gone from the address", location.hash === "", location.hash);
const modal = document.getElementById("pane");
say("the chart's pane opened", modal.classList.contains("on"));
const want = BOOT.sheetOfCode[asked.slice(-1)];
say("on its own sheet", document.querySelector("#sheets .active").textContent === want, document.querySelector("#sheets .active").textContent + " vs " + want);
// the opening filters (Expert, Official) still apply, as they do to a ?code= link, so the row is on
// screen only when the chart passes them; the pane names the chart either way
const rows = await sheetRows(want);
const cols = BOOT.data[want].columns;
const row = rows.find(r => r[cols.indexOf("Code")] === asked);
const head = modal.querySelector(".mhead") ? modal.querySelector(".mhead").textContent : "";
say("the pane names the asked chart's song", !!row && head.includes(row[cols.indexOf("Song Title")]), head.slice(0, 60));
const painted = document.querySelector('#body tr[data-code="' + asked + '"]');
say("and its row is marked when it is on the opening view", !painted || (painted.classList.contains("sel") && painted.getAttribute("aria-current") === "true"),
    painted ? "painted" : "filtered out by the opening view, as a ?code= link's would be");
done();
