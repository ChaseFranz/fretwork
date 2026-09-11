// Lists and sorts read in a sensible order, not alphabetically, and the filter
// panel picks the right control for the column.
import { BOOT, rows as sheetRows, say, done, wait, click, chip, levels } from "./lib.js";

const { ui: UI, valueOrder: VALUE_ORDER, valueLabels: VALUE_LABELS } = BOOT;
const sheets = Object.keys(BOOT.data);
const seq = a => JSON.stringify(a);
const headCols = () => [...document.querySelectorAll("#head th")].map(th => th.dataset.c);

async function openFilter(colName) {
  click(document.querySelector('#head th[data-c="' + colName + '"] [data-flt]'));
  await wait(50);
  const vals = [...document.querySelectorAll("#dd .list .v")].map(v => v.textContent);
  const range = document.getElementById("ddLo") !== null;
  const checks = document.querySelectorAll("#dd .form-check").length;
  document.body.click();
  await wait(20);
  return { vals, range, checks };
}

click(chip("official", UI.official_chip));          // clear the landing filter so lists show every value
await wait(50);

const lv = await openFilter("Level");
say("Level list is in VALUE_ORDER", seq(lv.vals) === seq(VALUE_ORDER.Level.filter(v => lv.vals.includes(v))), seq(lv.vals));
say("Level chips are the same set, Expert first", levels()[0] === "Expert" && seq([...levels()].sort()) === seq([...lv.vals].sort()), seq(levels()));

const ty = await openFilter("Type");
say("Type list is in VALUE_ORDER", seq(ty.vals) === seq(VALUE_ORDER.Type.filter(v => ty.vals.includes(v))), seq(ty.vals));

// Official is hidden by default; show it to read its list
click(document.getElementById("cols")); await wait(30);
const box = document.querySelector('#cd input[data-col="Official"]');
if (!box.checked) box.click();
document.body.click(); await wait(30);
const off = await openFilter("Official");
// Official has no VALUE_ORDER entry, so its stored keys sort as text (false, true) and read through VALUE_LABELS
const wantOff = Object.keys(VALUE_LABELS.Official).sort().map(k => VALUE_LABELS.Official[k]);
say("Official list reads as words", seq(off.vals) === seq(wantOff), seq(off.vals) + " vs " + seq(wantOff));

const ch = await openFilter("Charter");
say("free text stays alphabetical", seq(ch.vals) === seq([...ch.vals].sort((a, b) => a.localeCompare(b))), seq(ch.vals.slice(0, 5)));

// Range box versus checkbox list: the threshold is RANGE_MIN_DISTINCT (25 distinct values, boot.js).
const rows = await sheetRows(sheets[0]);
const dIdx = BOOT.data[sheets[0]].columns.indexOf("D");
const distinctD = new Set(rows.map(r => r[dIdx])).size;
const d = await openFilter("D");
say("D gets a min/max box when it has many distinct values", d.range === (distinctD > 25) && d.checks === 0,
    distinctD + " distinct, range " + d.range);
if (headCols().includes("Pct")) {
  const p = await openFilter("Pct");
  const pIdx = BOOT.data[sheets[0]].columns.indexOf("Pct");
  const distinctP = new Set(rows.map(r => r[pIdx])).size;
  say("Percentile filter control follows the same rule", p.range === (distinctP > 25), distinctP + " distinct, range " + p.range);
  if (p.range) {
    click(document.querySelector('#head th[data-c="Pct"] [data-flt]')); await wait(50);
    document.getElementById("ddLo").value = "90";
    click(document.querySelector('#dd [data-act="apply"]')); await wait(100);
    const lvIdx = BOOT.data[sheets[0]].columns.indexOf("Level");
    const wantN = rows.filter(r => r[lvIdx] === "Expert" && r[pIdx] >= 90).length;
    const cells = [...document.querySelectorAll("#body tr[data-code]")].map(tr => parseInt(tr.children[headCols().indexOf("Pct")].textContent, 10));
    say("min 90 leaves only rows at or above 90, and the count agrees", cells.every(v => v >= 90) && cells.length === wantN,
        cells.length + " vs " + wantN);
    click(document.querySelector('#head th[data-c="Pct"] [data-flt]')); await wait(50);
    click(document.querySelector('#dd [data-act="clear"]')); await wait(50);
  }
}
// A small sheet gets the checkbox list for the same column
const small = sheets[sheets.length - 1];
click([...document.querySelectorAll("#sheets button")].find(b => b.textContent === small)); await wait(100);
const rows2 = await sheetRows(small);
const d2Idx = BOOT.data[small].columns.indexOf("D");
const distinct2 = new Set(rows2.map(r => r[d2Idx])).size;
const d2 = await openFilter("D");
say("a sheet with few distinct D values gets the checkbox list", d2.range === (distinct2 > 25), small + ": " + distinct2 + " distinct, range " + d2.range);
click([...document.querySelectorAll("#sheets button")].find(b => b.textContent === sheets[0])); await wait(100);

// --- sorting a categorical column follows its own order ---------------------------------
const cellAt = colName => document.querySelector("#body tr:first-child td:nth-child(" + (headCols().indexOf(colName) + 1) + ")").textContent.trim();
click(document.querySelector('#head th[data-c="Level"] .lbl')); await wait(50);
const first = cellAt("Level");
click(document.querySelector('#head th[data-c="Level"] .lbl')); await wait(50);
const second = cellAt("Level");
say("sorting by Level puts Expert first, then Easy", first === "Expert" && second === "Easy", first + " / " + second);
click(document.querySelector('#head th[data-c="Official"] .lbl')); await wait(50);
say("first click on Official puts the ticks on top", cellAt("Official") !== "", "[" + cellAt("Official") + "]");

done();
