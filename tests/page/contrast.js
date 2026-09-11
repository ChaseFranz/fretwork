// Every text pair on the page at AA: 4.5:1 for text, 3:1 for large text and
// clickable chrome, measured from computed styles with alpha and opacity
// flattened over the nearest opaque ancestor. Prints the ratio table as ok lines.
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

let failures = 0, measured = 0;
function check(name, el, clickable) {
  if (!el) { note(("MISSING " + name).padEnd(30)); failures++; return; }
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
  const line = name.padEnd(24) + (r.toFixed(2) + ":1").padStart(8) + "  " + (hex(fg) + " on " + hex(bg)).padEnd(22) + Math.round(px) + "px";
  if (r >= need) note(line); else say("contrast " + name, false, line + " needs " + need);
}

await wait(200);
click(document.getElementById("cols"));
click(document.querySelector('#head th[data-c="D"] [data-flt]'));
await wait(100);
const cd = document.getElementById("cd");

check("brand", document.getElementById("brand"));
check("beta badge", document.querySelector("#brand .beta"), true);
check("strapline", document.getElementById("src"));
check("how it works link", document.getElementById("how"), true);
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

// the graph card (section 06): text on the figure background, and the picker
document.body.click();
await wait(50);
const firstRow = document.querySelector("#body tr[data-code]");
if (firstRow) {
  click(firstRow);
  await wait(600);
  const modal = document.getElementById("modal");
  check("graph readout", modal.querySelector(".readout"));
  check("graph legend", modal.querySelector(".legend li"));
  check("graph meta line", modal.querySelector(".mmeta"));
  check("graph meta value", modal.querySelector(".mmeta b"));
  check("graph heading dim text", modal.querySelector(".mhead .text-secondary"));
  check("graph close button", modal.querySelector(".x"), true);
  check("graph tool button", modal.querySelector(".gtools button"), true);
  click(modal.querySelector('[data-act="compare"]'));
  await wait(400);
  check("picker box text", document.getElementById("cmpq"));
  check("picker result", modal.querySelector("#cmpr [data-add] .tt") || modal.querySelector("#cmpr .note"));
  check("picker note", modal.querySelector("#cmpr .note") || modal.querySelector("#cmpr [data-add] .tt"));
  // the three series swatches against the card: 3:1, the floor for non-text
  const cardBg = bgOf(modal.querySelector(".legend"));
  for (const [name, colour] of [["~D", BOOT.render.color_d], ["Notes", BOOT.render.color_nps], ["Variability", BOOT.render.color_vps]]) {
    const s = document.createElement("span"); s.style.color = colour; document.body.appendChild(s);
    const fg = parse(getComputedStyle(s).color).slice(0, 3); s.remove();
    const r = ratio(fg, cardBg);
    measured++; if (r < 3) failures++;
    const line = ("series " + name).padEnd(24) + (r.toFixed(2) + ":1").padStart(8) + "  " + hex(fg) + " on " + hex(cardBg);
    if (r >= 3) note(line); else say("contrast series " + name, false, line + " needs 3");
  }
  click(modal.querySelector('[data-act="pick"]'));
  await wait(100);
  check("pick bar text", document.getElementById("pick"));
  check("pick bar button", document.querySelector("#pick button"), true);
  key("Escape");
  await wait(300);
  key("Escape");
  await wait(100);
}

// every level badge, not only the one on screen
let worst = null;
for (const b of document.querySelectorAll("#body .lvl")) {
  const bg = bgOf(b);
  const r = ratio(over(parse(getComputedStyle(b).color), bg), bg);
  if (!worst || r < worst.r) worst = { r, text: b.textContent, fg: hex(over(parse(getComputedStyle(b).color), bg)) };
}
if (worst) { measured++; if (worst.r < 4.5) failures++;
  const line = ("worst level badge " + worst.text).padEnd(24) + (worst.r.toFixed(2) + ":1").padStart(8) + "  " + worst.fg;
  if (worst.r >= 4.5) note(line); else say("contrast worst badge", false, line); }

say("every measured pair meets AA", failures === 0, measured + " pairs, " + failures + " below");
done();
