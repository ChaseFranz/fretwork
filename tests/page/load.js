// The loading contract (section 05): the header and count paint before the
// rows arrive, the rows follow fw:sheet, a shared ?code= picks its sheet from
// the instrument letter and survives the loading state. The runner delays
// data/ requests for this suite so the loading state can be observed, and
// launches it once per query.
import { BOOT, say, done, wait, ready, params } from "./lib.js";

const sheets = Object.keys(BOOT.data);
const code = params().get("code");
const sheetParam = params().get("sheet");

// before the rows: painted at module evaluation, which runs after main.js's first render
say("count says loading before the rows", /^Loading \d+ charts/.test(document.getElementById("count").textContent),
    document.getElementById("count").textContent);
say("a loading row stands in for the table", document.querySelector("#body tr.empty.loading") !== null);
say("the header is painted already", document.querySelectorAll("#head th").length > 3, document.querySelectorAll("#head th").length);
say("the sheet chips are painted already", document.querySelectorAll("#sheets button").length === sheets.length);
if (code) say("the shared code survives the loading state", params().get("code") === code, location.search);

await ready();
const active = document.querySelector("#sheets .active").textContent;
say("rows painted after the sheet arrived", document.querySelectorAll("#body tr[data-code]").length > 0);
say("count is a real count now", new RegExp("^\\d+ of " + BOOT.data[active].rows + " charts").test(document.getElementById("count").textContent),
    document.getElementById("count").textContent);
if (code) {
  const want = BOOT.sheetOfCode[code.slice(-1)];
  say("the shared code's sheet is active" + (sheetParam ? " (named)" : " (from the instrument letter)"), active === want, active + " vs " + want);
  await wait(500);
  const modal = document.getElementById("pane");
  say("the shared chart's pane opened", modal.classList.contains("on"));
  const strong = modal.querySelector(".mhead strong");
  say("its heading is filled from the right sheet", strong && strong.textContent.length > 0, strong && strong.textContent);
  say("the code is still in the URL", params().get("code") === code, location.search);
  const sel = document.querySelector("#body tr.sel");
  say("its row is highlighted and holds the tab stop when on screen", !sel || (sel.dataset.code === code && sel.tabIndex === 0), sel && sel.dataset.code);
}
done();
