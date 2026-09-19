// The graph, drawn on a canvas from graph/<code>.json: the same curves
// functions/plot.py draws, re-smoothed here so a smoothing change never
// republishes a file, plus what a picture cannot do - a readout of the values
// under the cursor (pointer or arrow keys), up to three charts on one axis, and
// a PNG export named the way render.py names its files. The file names its
// lines (nps and vps for a fret chart, hps, tps and kps for drums, pps, sps
// and perc for vocals) and carries the recipe that makes ~D of them; CURVES,
// labels.CURVE_FAMILIES, gives each family's lines their order, words and
// colour tokens, so one drawing path serves the three. The picture's shape
// (line width, grid alpha, the fill) comes from RENDER, plot.resolve_profile()'s
// numbers, so the page and render.py draw the same lines; its colours are the
// page's own, read from the stylesheet's tokens at every paint (gPalette), so
// the graph follows the theme and is painted on the page's ground. Every
// helper is prefixed g- or lives inside mountGraph's closure: the bundle is one
// scope, and draw, render, heading, opener and toast are already top-level
// names elsewhere.
import { RENDER, CURVES, UI, MISS_TEXT } from "./boot.js";
import { esc } from "./dom.js";
import { t, mmss } from "./format.js";

// Fixed CSS-pixel margins around the plot area; the y label and ticks sit in
// the left one, the m:ss ticks and the x label in the bottom one.
const G_MARGIN = { left: 44, right: 10, top: 8, bottom: 28 };
// x tick steps in seconds: the smallest giving at most ten ticks, else the last
const G_TICK_STEPS = [5, 10, 15, 30, 60, 120, 300, 600];
const G_Y_STEPS = [0.1, 0.2, 0.25, 0.5, 1, 2, 2.5, 5, 10, 20, 25, 50, 100];
const G_HEADROOM = 1.05;          // matplotlib's default 5% above the tallest point
const G_DASH = [1.5, 3];          // the ':' linestyle, near enough
const G_CACHE_MAX = 100;
const G_EXPORT = { width: 1920, height: 840 };   // figsize * dpi, before the tight crop

// --- the curve --------------------------------------------------------------------

// curves.smooth_series in the browser: counts to rates, then a single-pole EMA
// run forward and backward so peaks do not lag. Doubles throughout, so it
// reproduces the Python loop exactly (measured: a maximum difference of 0).
// Then ~D by the file's recipe, as curves.py's d_raw lines: the geometric
// mean of the named lines (sqrt(nps * vps) for a fret chart) or their
// weighted sum (hps + tps + kps for drums, R * A * pps + S_WEIGHT * sps for
// vocals). Returns {lines: {key: Float64Array}, keys, d}.
export function smooth(json) {
  const windowS = json.window / 1000;
  const decay = Math.exp(-json.step / json.tau), gain = 1 - decay;
  const both = xs => {
    const out = new Float64Array(xs.length);
    let acc = 0;
    for (let i = 0; i < xs.length; i++) out[i] = acc = acc * decay + (xs[i] / windowS) * gain;
    acc = 0;
    for (let i = xs.length - 1; i >= 0; i--) out[i] = acc = acc * decay + out[i] * gain;
    return out;
  };
  const keys = Object.keys(json.series);
  const lines = {};
  for (const k of keys) lines[k] = both(json.series[k]);
  const d = new Float64Array(json.n);
  if (json.d.geo) {
    const geo = json.d.geo.map(k => lines[k]), root = 1 / geo.length;
    for (let i = 0; i < d.length; i++) {
      let p = 1;
      for (const s of geo) p *= s[i];
      d[i] = geo.length === 2 ? Math.sqrt(p) : Math.pow(p, root);
    }
  } else {
    const terms = Object.entries(json.d.sum).map(([k, w]) => [lines[k], w]);
    for (let i = 0; i < d.length; i++) {
      let v = 0;
      for (const [s, w] of terms) v += w * s[i];
      d[i] = v;
    }
  }
  return { lines, keys, d };
}

// The lines a chart's graph draws under ~D, in the family's order, only the
// ones its file has: [{key, legend, readout, token}]. A family the page does
// not know (a newer file) draws what the file names, in the file's order.
export function gLines(curves) {
  const spec = (CURVES[curves.family] || {}).lines || [];
  const known = spec.filter(([key]) => key in curves.lines).map(([key, legend, readout, token]) => ({ key, legend, readout, token }));
  const extra = curves.keys.filter(k => !spec.some(([key]) => key === k)).map(key => ({ key, legend: key, readout: key, token: "--fw-curve-kps" }));
  return known.concat(extra);
}

const gCurves = new Map();    // code -> promise of the smoothed curves, oldest evicted

// graph/<code>.json, relative like every other URL, so the bundle works under a
// sub-path. A file of the wrong shape rejects, and the caller shows render_failed.
export function loadCurves(code) {
  if (gCurves.has(code)) return gCurves.get(code);
  const p = fetch("graph/" + encodeURIComponent(code) + ".json")
    .then(r => { if (!r.ok) throw new Error(r.status + " " + code); return r.json(); })
    .then(json => {
      const series = json.series && typeof json.series === "object" ? Object.values(json.series) : [];
      const recipe = json.d && typeof json.d === "object" ? (json.d.geo || (json.d.sum && Object.keys(json.d.sum))) : null;
      if (json.v !== 2 || !series.length || !(json.n > 0) || !Array.isArray(recipe) || !recipe.length ||
          series.some(s => !Array.isArray(s) || s.length !== json.n) || recipe.some(k => !(k in json.series)))
        throw new Error("bad curve file " + code);
      return { ...smooth(json), n: json.n, step: json.step, family: json.family, head: json.head || {} };
    })
    .catch(err => { gCurves.delete(code); throw err; });
  gCurves.set(code, p);
  while (gCurves.size > G_CACHE_MAX) gCurves.delete(gCurves.keys().next().value);
  return p;
}

// --- the picture ------------------------------------------------------------------

function gPickStep(steps, span, most) {
  return steps.find(s => Math.floor(span / s) <= most) ?? steps[steps.length - 1];
}

// How the charts share the axes: x runs to the longest chart, y to the tallest
// series with head-room. In compare mode only ~D is drawn per chart.
function gExtent(charts) {
  const compare = charts.length > 1;
  let xMax = 0, yMax = 0;
  for (const c of charts) {
    xMax = Math.max(xMax, (c.curves.n - 1) * c.curves.step);
    const series = compare ? [c.curves.d] : [c.curves.d, ...gLines(c.curves).map(l => c.curves.lines[l.key])];
    for (const s of series) for (let i = 0; i < s.length; i++) if (s[i] > yMax) yMax = s[i];
  }
  return { xMax: Math.max(xMax, 1), yMax: (yMax || 1) * G_HEADROOM, compare };
}

function gPolyline(ctx, ys, Xi, Y) {
  ctx.beginPath();
  ctx.moveTo(Xi(0), Y(ys[0]));
  for (let i = 1; i < ys.length; i++) ctx.lineTo(Xi(i), Y(ys[i]));
}

// A compare's three series, in order: the letter the readout and legend use
// and the token of its colour. The pane colours the charts from this and the
// song grid marks its cells from it, so the three agree; the tokens are the
// stylesheet's, so a mark is written as var(--fw-series-a) and follows the
// theme by itself, and only the canvas needs the value (gPalette).
export const G_LETTERS = ["A", "B", "C"];
export const G_SERIES = ["--fw-series-a", "--fw-series-b", "--fw-series-c"];
export const G_MOST = G_LETTERS.length;      // charts on one graph
export const seriesVar = k => "var(" + G_SERIES[k] + ")";

// The page's colours for the canvas, read from the tokens app.css defines per
// theme: the ground (the canvas is painted on it, so it is not a box), the
// text, the dim for the spines and the cursor, ~D, the three line tokens the
// families share (line(token) reads one) and the three series. Read at each
// paint, which is how a theme switch reaches the graph.
export function gPalette() {
  const cs = getComputedStyle(document.documentElement);
  const tok = name => cs.getPropertyValue(name).trim();
  return { bg: tok("--fw-bg"), text: tok("--fw-text"), dim: tok("--fw-dim"),
    d: tok("--fw-curve-d"), nps: tok("--fw-curve-nps"), vps: tok("--fw-curve-vps"), kps: tok("--fw-curve-kps"),
    line: tok, series: G_SERIES.map(tok) };
}

// The plot into a 2d context sized W by H CSS px; fonts are {label, tick} px.
// Returns the plot rectangle so the cursor code can map x to time.
function gPaint(ctx, W, H, charts, fonts, margin, pal) {
  const { xMax, yMax, compare } = gExtent(charts);
  const left = margin.left, top = margin.top;
  const pw = Math.max(1, W - margin.left - margin.right), ph = Math.max(1, H - margin.top - margin.bottom);
  const X = ms => left + (ms / xMax) * pw;
  const Y = v => top + ph - (v / yMax) * ph;

  ctx.fillStyle = pal.bg;
  ctx.fillRect(0, 0, W, H);

  // grid, matplotlib's 0.6 width at grid_alpha, in the text colour
  const xStep = gPickStep(G_TICK_STEPS, xMax / 1000, 10);
  const yStep = gPickStep(G_Y_STEPS, yMax, 6);
  ctx.save();
  ctx.globalAlpha = RENDER.grid_alpha;
  ctx.strokeStyle = pal.text;
  ctx.lineWidth = 0.6;
  for (let s = 0; s * 1000 <= xMax; s += xStep) {
    ctx.beginPath(); ctx.moveTo(X(s * 1000), top); ctx.lineTo(X(s * 1000), top + ph); ctx.stroke();
  }
  for (let v = 0; v <= yMax; v += yStep) {
    ctx.beginPath(); ctx.moveTo(left, Y(v)); ctx.lineTo(left + pw, Y(v)); ctx.stroke();
  }
  ctx.restore();

  // the curves, clipped to the axes: fill at z 2, lines at z 3 in plot order
  ctx.save();
  ctx.beginPath(); ctx.rect(left, top, pw, ph); ctx.clip();
  ctx.lineWidth = RENDER.linewidth;
  ctx.lineJoin = "round";
  charts.forEach((c, k) => {
    const colour = compare ? pal.series[k] : pal.d;
    const Xi = i => X(i * c.curves.step);
    if (RENDER.fill_curves) {
      gPolyline(ctx, c.curves.d, Xi, Y);
      ctx.lineTo(Xi(c.curves.d.length - 1), Y(0)); ctx.lineTo(Xi(0), Y(0)); ctx.closePath();
      ctx.globalAlpha = RENDER.fill_alpha; ctx.fillStyle = colour; ctx.fill(); ctx.globalAlpha = 1;
    }
    ctx.setLineDash([]); ctx.strokeStyle = colour;
    gPolyline(ctx, c.curves.d, Xi, Y); ctx.stroke();
    if (!compare) {
      ctx.setLineDash(G_DASH);
      for (const l of gLines(c.curves)) {
        ctx.strokeStyle = pal.line(l.token); gPolyline(ctx, c.curves.lines[l.key], Xi, Y); ctx.stroke();
      }
      ctx.setLineDash([]);
    }
  });
  ctx.restore();

  // spines
  ctx.strokeStyle = pal.dim;
  ctx.lineWidth = 1;
  ctx.strokeRect(left + 0.5, top + 0.5, pw - 1, ph - 1);

  // ticks and labels
  ctx.fillStyle = pal.text;
  ctx.font = fonts.tick + "px system-ui, sans-serif";
  ctx.textAlign = "center"; ctx.textBaseline = "top";
  for (let s = 0; s * 1000 <= xMax; s += xStep) ctx.fillText(mmss(s), X(s * 1000), top + ph + 3);
  ctx.textAlign = "right"; ctx.textBaseline = "middle";
  const places = yStep < 1 ? (yStep < 0.25 ? 2 : 1) : 0;
  for (let v = 0; v <= yMax; v += yStep) ctx.fillText(v.toFixed(places), left - 4, Y(v));
  ctx.font = fonts.label + "px system-ui, sans-serif";
  ctx.textAlign = "center"; ctx.textBaseline = "bottom";
  ctx.fillText(UI.graph_x, left + pw / 2, H - 1);
  ctx.save();
  ctx.translate(fonts.label, top + ph / 2); ctx.rotate(-Math.PI / 2);
  ctx.textBaseline = "middle";
  ctx.fillText(UI.graph_y, 0, 0);
  ctx.restore();

  return { left, top, pw, ph, xMax, yMax, X, Y, compare };
}

// One row's words for the legend and the alt text: title, artist, level, part.
const gField = (chart, n) => {
  const i = chart.columns ? chart.columns.indexOf(n) : -1;
  return i < 0 || !chart.row ? "" : chart.row[i];
};
function gName(chart) {
  if (!chart.row) return chart.code;
  return t("graph_legend", { title: gField(chart, "Song Title"), artist: gField(chart, "Artist"),
    level: gField(chart, "Level"), type: gField(chart, "Type") });
}

// The compared charts' legend entries, with only what tells them apart:
// the levels of one song and part read "Expert" and "Hard", not the title
// and artist three times over; two parts of one song keep the part; two
// songs keep everything.
function gNames(charts) {
  const rows = charts.filter(c => c.row);
  const same = n => rows.every(c => gField(c, n) === gField(rows[0], n));
  if (rows.length < 2 || !same("Song Title") || !same("Artist")) return charts.map(gName);
  const key = same("Type") ? "graph_legend_level" : "graph_legend_part";
  return charts.map(c => c.row ? t(key, { level: gField(c, "Level"), type: gField(c, "Type") }) : c.code);
}

const gLetters = G_LETTERS;
const gFix = v => v === null || v === undefined || Number.isNaN(v) ? MISS_TEXT : v.toFixed(2);
// The family's words for its lines in the alt text, else the legend words joined.
const gAltWords = curves => (CURVES[curves.family] || {}).alt || gLines(curves).map(l => l.legend).join(", ");

// --- the mounted graph --------------------------------------------------------------

// host: the .gbody element. charts: [{code, row, columns, curves}], whose
// order is the series order: charts[k] is drawn in series k's colour.
// opts.onRemove(code) wires the legend's remove buttons in compare mode;
// opts.fill() true means the host's height is fixed by its layout and the
// canvas takes what is left of it under the readout and legend, rather than
// the 16:7 aspect it draws at when the host grows to fit it.
// Returns a controller; host.fw is the same thing for the page suites, which
// cannot import from the bundle.
export function mountGraph(host, charts, opts = {}) {
  host.innerHTML = "";
  const canvas = document.createElement("canvas");
  const readout = document.createElement("p");
  const legend = document.createElement("ul");
  const id = "readout-" + Math.random().toString(36).slice(2, 8);
  readout.className = "readout"; readout.id = id; readout.setAttribute("aria-live", "polite");
  legend.className = "legend";
  canvas.tabIndex = 0;
  canvas.setAttribute("role", "application");
  canvas.setAttribute("aria-roledescription", "difficulty graph");
  canvas.setAttribute("aria-describedby", id);
  host.append(canvas, readout, legend);

  const buffer = document.createElement("canvas");   // the plot, painted once per size
  let W = 0, H = 0, hostH = 0, dpr = 1, geom = null, cursor = 0, raf = 0, pal = gPalette();
  const filling = () => !!(opts.fill && opts.fill());
  const ctx = canvas.getContext("2d");

  // The width is the host's, read with the canvas out of the way: at its
  // default 300 by 150 a canvas styled width:100% is half as tall as it is
  // wide, enough to give the card a scrollbar and steal 15px from the width.
  // Read again once sized, since the real height can do the same.
  const measure = () => {
    canvas.style.height = "1px";
    return Math.max(1, Math.round(host.clientWidth || host.getBoundingClientRect().width || 300));
  };
  const size = () => {
    W = measure();
    hostH = Math.round(host.clientHeight);
    for (let pass = 0; pass < 2; pass++) {
      H = filling()
        ? Math.max(120, hostH - readout.offsetHeight - legend.offsetHeight - 4)
        : Math.round(Math.min(Math.max(W * 7 / 16, 220), window.innerHeight * 0.55));
      dpr = window.devicePixelRatio || 1;
      canvas.style.width = W + "px"; canvas.style.height = H + "px";
      const again = Math.max(1, Math.round(host.clientWidth || W));
      if (again === W) break;
      W = again;
    }
    for (const c of [canvas, buffer]) {
      c.width = Math.round(W * dpr); c.height = Math.round(H * dpr);
    }
    const bctx = buffer.getContext("2d");
    bctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    pal = gPalette();
    geom = gPaint(bctx, W, H, charts, { label: 11, tick: 10 }, G_MARGIN, pal);
  };

  // the buffer, then only the hairline and the dots: cost independent of n
  const paintCursor = () => {
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.drawImage(buffer, 0, 0);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const x = geom.X(cursor);
    ctx.strokeStyle = pal.dim; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(x, geom.top); ctx.lineTo(x, geom.top + geom.ph); ctx.stroke();
    charts.forEach((c, k) => {
      const i = Math.round(cursor / c.curves.step);
      if (i >= c.curves.n) return;
      const dots = geom.compare ? [[c.curves.d[i], pal.series[k]]]
        : [[c.curves.d[i], pal.d], ...gLines(c.curves).map(l => [c.curves.lines[l.key][i], pal.line(l.token)])];
      for (const [v, colour] of dots) {
        ctx.fillStyle = colour;
        ctx.beginPath(); ctx.arc(x, geom.Y(v), 3, 0, Math.PI * 2); ctx.fill();
      }
    });
  };

  const writeReadout = () => {
    const at = mmss(cursor / 1000);
    if (!geom.compare) {
      const c = charts[0], i = Math.round(cursor / c.curves.step);
      const v = xs => i < c.curves.n ? gFix(xs[i]) : MISS_TEXT;
      const lines = gLines(c.curves).map(l => t("graph_readout_line", { label: l.readout, v: v(c.curves.lines[l.key]) }));
      readout.textContent = t("graph_readout", { t: at, d: v(c.curves.d), lines: lines.join("  ") });
    } else {
      const parts = charts.map((c, k) => {
        const i = Math.round(cursor / c.curves.step);
        return t("graph_readout_part", { letter: gLetters[k], d: i < c.curves.n ? gFix(c.curves.d[i]) : MISS_TEXT });
      });
      readout.textContent = t("graph_readout_many", { t: at, parts: parts.join("  ") });
    }
  };

  const setCursor = ms => {
    cursor = Math.max(0, Math.min(geom.xMax, Math.round(ms / charts[0].curves.step) * charts[0].curves.step));
    paintCursor();
    writeReadout();
  };

  // The series legend for one chart; one entry per chart, with a remove
  // button, for a comparison. The swatches are written as the tokens, so they
  // follow the theme with the rest of the page; the buttons are --fw-dim,
  // never a series colour.
  const writeLegend = () => {
    const swatch = (colour, dotted) => '<span class="sw' + (dotted ? " dot" : "") + '" style="border-color:' + esc(colour) + '"></span>';
    if (charts.length < 2) {
      legend.innerHTML = [[UI.graph_d, "var(--fw-curve-d)", false], ...gLines(charts[0].curves).map(l => [l.legend, "var(" + l.token + ")", true])]
        .map(([text, colour, dotted]) => "<li>" + swatch(colour, dotted) + esc(text) + "</li>").join("");
      return;
    }
    const names = gNames(charts);
    legend.innerHTML = charts.map((c, k) => "<li>" + swatch(seriesVar(k), false) +
      '<span class="lt">' + esc(gLetters[k]) + " " + esc(names[k]) + "</span>" +
      '<button type="button" class="rm" data-rm="' + esc(c.code) + '" aria-label="' +
      esc(t("compare_remove", { code: c.code })) + '" title="' + esc(t("compare_remove", { code: c.code })) +
      '">&times;</button></li>').join("");
  };

  // the legend first: in fill mode the canvas takes what the legend leaves;
  // the palette is read again inside size(), so a theme switch redraws here
  const redraw = () => {
    writeLegend();
    size();
    setCursor(cursor);
    const song = charts[0].row ? gName(charts[0]) : charts[0].code;
    canvas.setAttribute("aria-label", t("graph_alt", { song, lines: gAltWords(charts[0].curves) }));
  };

  // pointer: a time under the cursor; the readout stops narrating while it moves
  const onPointer = e => {
    const box = canvas.getBoundingClientRect();
    const frac = Math.max(0, Math.min(1, (e.clientX - box.left - geom.left) / geom.pw));
    readout.setAttribute("aria-live", "off");
    setCursor(frac * geom.xMax);
  };
  const onLeave = () => readout.setAttribute("aria-live", "polite");
  const onKey = e => {
    const step = charts[0].curves.step, big = 40 * step;
    const moves = { ArrowLeft: -(e.shiftKey ? big : step), ArrowRight: e.shiftKey ? big : step };
    if (e.key in moves) { e.preventDefault(); e.stopPropagation(); setCursor(cursor + moves[e.key]); }
    else if (e.key === "Home") { e.preventDefault(); e.stopPropagation(); setCursor(0); }
    else if (e.key === "End") { e.preventDefault(); e.stopPropagation(); setCursor(geom.xMax); }
  };
  const onResize = () => { cancelAnimationFrame(raf); raf = requestAnimationFrame(redraw); };
  const onLegend = e => {
    const rm = e.target.closest("[data-rm]");
    if (rm && opts.onRemove) { e.stopPropagation(); opts.onRemove(rm.dataset.rm); }
  };
  canvas.addEventListener("pointermove", onPointer);
  canvas.addEventListener("pointerdown", onPointer);
  canvas.addEventListener("pointerleave", onLeave);
  canvas.addEventListener("keydown", onKey);
  legend.addEventListener("click", onLegend);
  window.addEventListener("resize", onResize);
  // the host's own width moves too: a scrollbar the card grows, a legend that wraps
  const watcher = typeof ResizeObserver === "function"
    ? new ResizeObserver(() => {
      if (Math.round(host.clientWidth) !== W || (filling() && Math.round(host.clientHeight) !== hostH)) onResize();
    }) : null;
  if (watcher) watcher.observe(host);

  redraw();
  const api = {
    charts, smooth, redraw, setCursor, exportPng, outputFilename,
    destroy() {
      cancelAnimationFrame(raf);
      if (watcher) watcher.disconnect();
      window.removeEventListener("resize", onResize);
      canvas.removeEventListener("pointermove", onPointer);
      canvas.removeEventListener("pointerdown", onPointer);
      canvas.removeEventListener("pointerleave", onLeave);
      canvas.removeEventListener("keydown", onKey);
      legend.removeEventListener("click", onLegend);
      host.fw = null;
    },
  };
  host.fw = api;
  return api;
}

// --- export -------------------------------------------------------------------------

// A twin of plot._safe / plot.output_filename: strip to ASCII, collapse spaces,
// 60 characters, "unknown" when nothing is left. Compare inserts _vs_<B>[_<C>].
const gSafe = s => (String(s ?? "").replace(/[^A-Za-z0-9 _.-]/g, "").trim().replace(/\s+/g, " ").slice(0, 60)) || "unknown";

export function outputFilename(codes, row, columns) {
  const get = n => { const i = columns ? columns.indexOf(n) : -1; return i < 0 || !row ? "" : row[i]; };
  const vs = codes.length > 1 ? "_vs_" + codes.slice(1).join("_") : "";
  return codes[0] + "_" + gSafe(get("Artist")) + " - " + gSafe(get("Song Title")) + vs + ".png";
}

// The same charts at the figure's own size, dpr 1, with the two header lines
// drawn in, so a share from a phone and from a desktop look the same; in the
// theme the page is in, since that is the picture the visitor is looking at.
export function exportPng(charts, heading) {
  const c = document.createElement("canvas");
  c.width = G_EXPORT.width; c.height = G_EXPORT.height;
  const ctx = c.getContext("2d");
  const pal = gPalette();
  const headTop = 16, title = 17, meta = 12, gap = 8;
  const headH = headTop + title + gap + meta + 14;
  ctx.fillStyle = pal.bg;
  ctx.fillRect(0, 0, c.width, c.height);
  ctx.textBaseline = "top"; ctx.textAlign = "left";
  ctx.fillStyle = pal.text;
  ctx.font = "bold " + title + "px system-ui, sans-serif";
  ctx.fillText(heading.title || "", G_MARGIN.left, headTop, c.width - G_MARGIN.left - G_MARGIN.right);
  ctx.fillStyle = pal.dim;
  ctx.font = meta + "px system-ui, sans-serif";
  ctx.fillText(heading.meta || "", G_MARGIN.left, headTop + title + gap, c.width - G_MARGIN.left - G_MARGIN.right);
  const legendH = 26;
  ctx.save();
  ctx.translate(0, headH);
  const geom = gPaint(ctx, c.width, c.height - headH - legendH, charts, { label: 11, tick: 10 }, G_MARGIN, pal);
  ctx.restore();
  // legend centred under the axes, as the PNG has it
  const names = gNames(charts);
  const entries = geom.compare
    ? charts.map((ch, k) => [gLetters[k] + " " + names[k], pal.series[k], false])
    : [[UI.graph_d, pal.d, false], ...gLines(charts[0].curves).map(l => [l.legend, pal.line(l.token), true])];
  ctx.font = "11px system-ui, sans-serif"; ctx.textBaseline = "middle"; ctx.textAlign = "left";
  const widths = entries.map(([text]) => ctx.measureText(text).width + 34);
  let x = (c.width - widths.reduce((a, b) => a + b, 0)) / 2;
  const y = c.height - legendH / 2;
  entries.forEach(([text, colour, dotted], k) => {
    ctx.strokeStyle = colour; ctx.lineWidth = 2; ctx.setLineDash(dotted ? G_DASH : []);
    ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + 22, y); ctx.stroke(); ctx.setLineDash([]);
    ctx.fillStyle = pal.text;
    ctx.fillText(text, x + 28, y);
    x += widths[k];
  });
  return new Promise((resolve, reject) => c.toBlob(b => b ? resolve(b) : reject(new Error("toBlob")), "image/png"));
}
