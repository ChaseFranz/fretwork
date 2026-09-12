// Copies (section 10): the count of folders carrying exactly these notes at
// this level and part, hidden until chosen; ?f.Copies=2 is the shareable view
// of every duplicated chart. Launched twice: plain, and with that query.
import { BOOT, rows as sheetRows, say, skip, done, wait, click, shown, params, ready } from "./lib.js";
await ready();

const { labels: LABELS, hiddenDefault: HIDDEN_DEFAULT } = BOOT;
const p = params();
const sheet = p.get("sheet") || Object.keys(BOOT.data)[0];
const rows = await sheetRows(sheet);
const cols = BOOT.data[sheet].columns;
const col = n => cols.indexOf(n);
const headCols = () => [...document.querySelectorAll("#head th")].map(th => th.dataset.c);
const seq = a => JSON.stringify(a);
const cells = c => [...document.querySelectorAll("#body tr[data-code]")].map(tr => tr.children[headCols().indexOf(c)].textContent);

say("the sheet carries Copies and NotesHash", col("Copies") >= 0 && col("NotesHash") >= 0, seq(cols));
// the link columns (section 14) come after these three when the registry has them
const pageBuilt = cols.filter(c => ["Added", "Copies", "Pct", "Chart", "Leaderboard"].includes(c));
say("Copies sits right before Percentile, after Added", pageBuilt.slice(0, 3).join() === "Added,Copies,Pct" && cols.slice(-pageBuilt.length).join() === pageBuilt.join(), seq(cols.slice(-5)));
say("every Copies value is a positive integer", rows.every(r => Number.isInteger(r[col("Copies")]) && r[col("Copies")] >= 1));
say("both are hidden by default", HIDDEN_DEFAULT.includes("Copies") && HIDDEN_DEFAULT.includes("NotesHash"));
say("their labels", LABELS.Copies === "Copies" && LABELS.NotesHash === "Notes hash", LABELS.Copies + " / " + LABELS.NotesHash);

if (!p.toString()) {
  say("neither is in the default header", !headCols().includes("Copies") && !headCols().includes("NotesHash"), seq(headCols()));
  click(document.getElementById("cols"));
  await wait(50);
  say("the chooser lists both unticked", ["Copies", "NotesHash"].every(c => {
    const box = document.querySelector('#cd input[data-col="' + c + '"]');
    return box && !box.checked;
  }));
  document.querySelector('#cd input[data-col="Copies"]').click();
  await wait(50);
  document.body.click();
  await wait(50);
  const seen = cells("Copies");
  say("ticking Copies shows a whole-number column", seen.length > 0 && seen.every(v => /^\d+$/.test(v)), seq([...new Set(seen)]));
  click(document.querySelector('#head th[data-c="Copies"] .flt'));
  await wait(50);
  const boxes = [...document.querySelectorAll("#dd .form-check-input")].map(b => b.dataset.v);
  say("its filter is a checkbox list of the values, not a range box", boxes.length > 0 && !document.getElementById("ddLo") &&
      seq(boxes) === seq([...new Set(rows.map(r => String(r[col("Copies")])))].sort()), seq(boxes));
  document.body.click();
} else if (p.get("f.Copies")) {
  const want = rows.filter(r => r[col("Copies")] === 2);
  if (!want.length) {
    skip("?f.Copies=2", "no duplicated chart on this sheet");
  } else {
    click(document.getElementById("cols")); await wait(50);
    document.querySelector('#cd input[data-col="Copies"]').click(); await wait(50);
    document.body.click(); await wait(50);
    const seen = cells("Copies");
    say("?f.Copies=2 shows only rows whose Copies cell reads 2", seen.length > 0 && seen.every(v => v === "2"), seq([...new Set(seen)]));
    say("and all of them", shown() === want.length, shown() + " vs " + want.length);
    say("Copies header is marked filtered", document.querySelector('#head th[data-c="Copies"]').classList.contains("filtered"));
    // identical notes give identical D and, counted once, one percentile
    const groups = new Map();
    for (const r of want) {
      const k = ["Type", "Level", "NotesHash"].map(c => r[col(c)]).join("\u0000");
      if (!groups.has(k)) groups.set(k, []);
      groups.get(k).push(r);
    }
    const agree = [...groups.values()].every(g => g.length === g[0][col("Copies")] &&
      new Set(g.map(r => r[col("D")])).size === 1 && new Set(g.map(r => r[col("Pct")])).size === 1);
    say("each group of copies is as big as its Copies value and shares D and Percentile", agree, groups.size + " groups");
  }
}

done();
