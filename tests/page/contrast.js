// Every text pair on the page at AA: 4.5:1 for text, 3:1 for large text and
// clickable chrome, measured from computed styles with alpha and opacity
// flattened over the nearest opaque ancestor. Prints the ratio table as ok
// lines. The whole audit runs twice, once per theme, since every token has
// two values (section 15): the header's toggle switches between the runs.
import { BOOT, say, note, done, wait, click, key, ready } from "./lib.js";
await ready();

const lin = c => { c /= 255; return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); };
const lum = ([r, g, b]) => 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
const parse = s => (s.match(/[\d.]+/g) || []).map(Number);
const over = (fg, bg) => { const a = fg.length > 3 ? fg[3] : 1; return [0, 1, 2].map(i => fg[i] * a + bg[i] * (1 - a)); };
function bgOf(el) {
  for (let n = el; n; n = n.parentElement) {
    const c = parse(getComputedStyle(n).backgroundColor);
    if (c.length === 3 || (c[3] ?? 1) > 0.95) return c.slice(0, 3);
  }
  return parse(getComputedStyle(document.body).backgroundColor).slice(0, 3);
}
const ratio = (fg, bg) => { const a = lum(fg), b = lum(bg); return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05); };
const hex = c => "#" + c.map(v => Math.round(v).toString(16).padStart(2, "0")).join("");
// a token's value as rgb, resolved by the browser
const token = name => {
  const s = document.createElement("span"); s.style.color = "var(" + name + ")"; document.body.appendChild(s);
  const c = parse(getComputedStyle(s).color); s.remove(); return c;
};
const theme = () => document.documentElement.getAttribute("data-bs-theme");

let failures = 0, measured = 0;
function check(name, el, clickable) {
  name = theme() + " " + name;
  if (!el) { note(("MISSING " + name).padEnd(36)); failures++; return; }
  const cs = getComputedStyle(el);
  const bg = bgOf(el);
  let fg = over(parse(cs.color), bg);
  const opacity = parseFloat(cs.opacity);
  if (opacity < 1) fg = over([...fg, opacity], bg);
  const px = parseFloat(cs.fontSize);
  const bold = parseInt(cs.fontWeight, 10) >= 700;
  const large = px >= 24 || (bold && px >= 18.66);
  const need = clickable || large ? 3 : 4.5;
  const r = ratio(fg, bg);
  measured++;
  if (r < need) failures++;
  const line = name.padEnd(34) + (r.toFixed(2) + ":1").padStart(8) + "  " + (hex(fg) + " on " + hex(bg)).padEnd(22) + Math.round(px) + "px";
  if (r >= need) note(line); else say("contrast " + name, false, line + " needs " + need);
}
// a swatch, an edge or a fill: not text, so 3:1
function swatch(name, fg, bg) {
  name = theme() + " " + name;
  const r = ratio(fg, bg);
  measured++; if (r < 3) failures++;
  const line = name.padEnd(34) + (r.toFixed(2) + ":1").padStart(8) + "  " + hex(fg) + " on " + hex(bg);
  if (r >= 3) note(line); else say("contrast " + name, false, line + " needs 3");
}

async function audit() {
  click(document.getElementById("cols"));
  click(document.querySelector('#head th[data-c="D"] [data-flt]'));
  await wait(100);
  const cd = document.getElementById("cd");

  check("brand", document.getElementById("brand"));
  check("beta badge", document.querySelector("#brand .beta"), true);
  check("strapline", document.getElementById("src"));
  check("how it works link", document.getElementById("how"), true);
  check("theme toggle", document.getElementById("theme"), true);
  check("chip, active", document.querySelector("#levels .active"), true);
  check("chip, inactive", document.querySelector("#levels button:not(.active)"), true);
  check("chip, sheet inactive", document.querySelector("#sheets button:not(.active)"), true);
  check("Columns button", document.getElementById("cols"), true);
  check("row count", document.getElementById("count"));
  check("search box text", document.getElementById("q"));
  check("header, plain", document.querySelector("#head th:not(.sorted) .lbl"), true);
  check("header, sorted", document.querySelector("#head th.sorted .lbl"), true);
  check("header filter caret", document.querySelector("#head [data-flt]"), true);
  check("cell, plain", document.querySelector("#body td.title"));
  check("cell, rank", document.querySelector("#body td.rank"));
  check("cell, D", document.querySelector("#body td.headline"));
  check("cell, dim text", document.querySelector("#body td.artist"));
  check("footer link", document.querySelector("#foot a:not(.req)"), true);
  check("footer request link", document.querySelector("#foot a.req"), true);
  check("footer text", document.getElementById("foot"));
  check("filter value", document.querySelector("#dd .list .v") || document.getElementById("ddLo"));
  check("filter buttons", document.querySelector("#dd [data-act]"), true);
  check("chooser label", cd.querySelector(".form-check-label"));
  check("chooser grip", cd.querySelector(".grip"), true);
  check("chooser reset button", cd.querySelector("[data-act]"), true);

  // the details pane (sections 06, 07, 14): text on the page's ground, the
  // song grid beside the graph, the link buttons and the link cells
  document.body.click();
  await wait(50);
  const firstRow = document.querySelector("#body tr[data-code]");
  if (firstRow) {
    click(firstRow);
    await wait(800);
    const modal = document.getElementById("pane");
    check("graph readout", modal.querySelector(".readout"));
    check("graph legend", modal.querySelector(".legend li"));
    check("graph meta line", modal.querySelector(".mmeta"));
    check("graph meta value", modal.querySelector(".mmeta b"));
    check("graph heading dim text", modal.querySelector(".mhead .text-secondary"));
    check("report link", modal.querySelector(".mhead .lnk a"), true);
    check("pane close button", modal.querySelector(".pbtns .x"), true);
    check("pane collapse button", modal.querySelector(".pbtns .pmin"), true);
    check("graph tool button", modal.querySelector(".gtools button"), true);
    {   // the grip is a pill, not text: its fill against the strip it sits on
      const pill = modal.querySelector(".pgrip span"), strip = modal.querySelector(".pgrip");
      swatch("pane grip", over([...parse(getComputedStyle(pill).backgroundColor).slice(0, 3), parseFloat(getComputedStyle(pill).opacity)], bgOf(strip)), bgOf(strip));
    }
    check("selected row title", firstRow.querySelector("td.title"));
    check("selected row D", firstRow.querySelector("td.headline"));
    check("selected row rank", firstRow.querySelector("td.rank"));
    check("selected row dim text", firstRow.querySelector("td.artist"));
    // the selected row's edge, and the brand fill under white
    swatch("selected row edge", token("--fw-brand-text"), bgOf(firstRow.querySelector("td")));
    swatch("white on the brand fill", [255, 255, 255], token("--fw-brand"));
    const linkBtn = modal.querySelector(".gtools a.ext");
    if (linkBtn) check("link button", linkBtn, true);
    const linkCell = document.querySelector("#body td.lnkc a.ext");
    if (linkCell) check("link column arrow", linkCell, true);
    // ~D and the three line colours every family shares (notes/hands/syllables,
    // variability/travel/pitch, kicks/percussion) and the three compare series
    // against the pane's ground: 3:1, the floor for non-text; the tokens are
    // what the canvas paints
    const paneBg = bgOf(modal.querySelector(".legend"));
    for (const [name, tok] of [["curve D", "--fw-curve-d"], ["curve Notes", "--fw-curve-nps"], ["curve Variability", "--fw-curve-vps"],
                               ["curve Kicks", "--fw-curve-kps"],
                               ["series A", "--fw-series-a"], ["series B", "--fw-series-b"], ["series C", "--fw-series-c"]]) {
      swatch(name, token(tok), paneBg);
    }
    click(modal.querySelector('[data-act="pick"]'));
    await wait(100);
    check("pick bar text", document.getElementById("pick"));
    check("pick bar button", document.querySelector("#pick button"), true);
    key("Escape");
    await wait(300);
    // the song half
    const panel = modal.querySelector(".sbody");
    check("song meta line", panel.querySelector("p.meta"));
    check("song tier", panel.querySelector(".sgrid .tier") || panel.querySelector(".sgrid .inst"));
    check("song compare button", panel.querySelector(".sgrid .cmp") || panel.querySelector(".sgrid .inst"), true);
    check("song cell D", panel.querySelector(".sgrid .cell b"), true);
    check("song cell percentile", panel.querySelector(".sgrid .cell small") || panel.querySelector(".sgrid .cell b"));
    check("song blank cell", panel.querySelector(".sgrid .cell.none") || panel.querySelector(".sgrid .cell b"));
    for (const h of panel.querySelectorAll(".sgrid .lvlh")) check("level heading " + h.textContent, h);
    // compare mode: the pressed instrument button and the cells' legend letters
    // (a disabled cell is an inactive control, which AA exempts, and is not measured)
    const cmp = panel.querySelector(".sgrid .cmp");
    if (cmp) {
      click(cmp);
      await wait(800);
      check("song compare button pressed", modal.querySelector('.sgrid .cmp[aria-pressed="true"]') || cmp, true);
      check("song cell legend letter", modal.querySelector(".sgrid .cell.on .sl") || modal.querySelector(".sgrid .cell b"));
      check("song on-graph cell D", modal.querySelector(".sgrid .cell.on b") || modal.querySelector(".sgrid .cell b"), true);
      check("row legend letter", document.querySelector("#body tr.on .sl") || modal.querySelector(".sgrid .cell b"));
    }
    key("Escape");
    await wait(200);
  }

  // every level badge, not only the one on screen
  let worst = null;
  for (const b of document.querySelectorAll("#body .lvl")) {
    const bg = bgOf(b);
    const r = ratio(over(parse(getComputedStyle(b).color), bg), bg);
    if (!worst || r < worst.r) worst = { r, text: b.textContent, fg: hex(over(parse(getComputedStyle(b).color), bg)) };
  }
  if (worst) { measured++; if (worst.r < 4.5) failures++;
    const line = (theme() + " worst level badge " + worst.text).padEnd(34) + (worst.r.toFixed(2) + ":1").padStart(8) + "  " + worst.fg;
    if (worst.r >= 4.5) note(line); else say("contrast worst badge", false, line); }
}

await wait(200);
const first = theme();
await audit();
click(document.getElementById("theme"));
await wait(200);
say("the toggle switched the theme for the second pass", theme() !== first && (theme() === "light" || theme() === "dark"), first + " -> " + theme());
await audit();
say("both themes were audited", new Set([first, theme()]).size === 2, first + ", " + theme());
say("every measured pair meets AA in both themes", failures === 0, measured + " pairs, " + failures + " below");
done();
