// Builds the table's HTML. Everything it needs is passed in.
import { SHEETS, TIMECOLS, HELP, UI, MISS_TEXT, MISS_HELP } from "./boot.js";
import { esc } from "./dom.js";
import { lab, t, mmss, isMissing, decimals } from "./format.js";
import { LINK_COLS, linkCell } from "./links.js";
import { RANK_COL, state } from "./state.js";

// Rank is a position in the current view, so there is nothing to sort or
// filter it by; it gets a bare header instead of the usual controls.
function rankHeaderCell() {
  return '<th scope="col" data-c="' + esc(RANK_COL) + '" class="rank"><div class="thw">' +
    '<span title="' + esc(HELP[RANK_COL] || "") + '">' + esc(lab(RANK_COL)) +
    "</span></div></th>";
}

// The label and the caret are real buttons so a keyboard reaches them, and the
// th carries aria-sort so the sort is announced rather than only drawn as an
// arrow. The resize grip is deliberately not focusable: it changes how wide a
// column is drawn and nothing else, and the value it might clip is in the cell's
// title, so there is no content behind it for a keyboard to be locked out of.
export function headerCell(col, { sorted, ascending, filtered, expanded }) {
  if (col === RANK_COL) return rankHeaderCell();
  const cls = [sorted ? "sorted" : "", filtered ? "filtered" : ""].join(" ").trim();
  const tip = (HELP[col] ? HELP[col] + "\n\n" : "") + "Column: " + col + "\n" + UI.sort_tip;
  const arrow = sorted ? (ascending ? " &#9650;" : " &#9660;") : "";
  const order = sorted ? (ascending ? "ascending" : "descending") : "none";
  return '<th scope="col" aria-sort="' + order + '" data-c="' + esc(col) + '"' +
    (cls ? ' class="' + cls + '"' : '') + '><div class="thw">' +
    '<button type="button" class="lbl" data-sort="' + esc(col) + '" title="' + esc(tip) + '">' +
    esc(lab(col)) + arrow + '</button>' +
    '<button type="button" class="btn btn-sm btn-link p-0 px-1 flt text-secondary" data-flt="' +
    esc(col) + '" title="' + esc(UI.filter_tip) + '" aria-label="' +
    esc(UI.filter_tip + ": " + lab(col)) + '" aria-expanded="' + (expanded ? "true" : "false") +
    '">&#9662;</button>' +
    '<span class="rz" aria-hidden="true" data-rz="' + esc(col) + '" title="' +
    esc(UI.resize_tip) + '"></span></div></th>';
}

// The wrapping text columns. Each gets its own class as well, because how much
// room they may take differs per column and differs again on a phone.
const TEXT_CLASS = {
  "Song Title": "title song",
  "Artist": "title artist",
  "Charter": "title",
  "Release": "title",
  "Album": "title album",
  "Genre": "genre",
};

// No conditional-formatting fill. The table is nearly always sorted by D, so a
// colour ramp was decorating a ranking the row order already states; weight on
// the one headline number does the same job without the spreadsheet look.
function numberCell(col, v) {
  const text = v.toFixed(decimals(col));
  return '<td class="num' + (col === "D" ? " headline" : "") + '">' + text + "</td>";
}

// A link column's arrow is the one anchor inside a row: the router lets the
// browser follow it rather than opening the row.
function bodyCell(col, v, songKey) {
  if (col in LINK_COLS) return linkCell(col, v, songKey);
  if (col === "Code")
    return '<td class="code" title="' + esc(UI.copy_code_tip) + '">' + esc(v) +
      '<span class="cp" data-copy="' + esc(v) + '">&#128203;</span></td>';
  if (col === "Official")
    return '<td class="num">' + (v === true ? "&#10003;" : "") + "</td>";
  if (col === "Level")
    return '<td><span class="badge rounded-pill lvl ' + esc(v) + '">' + esc(v) + "</span></td>";
  if (TEXT_CLASS[col])
    return '<td class="' + TEXT_CLASS[col] + '" title="' + esc(v ?? "") + '">' +
      esc(v ?? "") + "</td>";
  if (isMissing(col, v)) {
    const tip = MISS_HELP[col] || "";
    return '<td class="num blank"' + (tip ? ' title="' + esc(tip) + '"' : '') +
      ">" + MISS_TEXT + "</td>";
  }
  if (TIMECOLS.has(col) && typeof v === "number")
    return '<td class="num">' + mmss(v) + "</td>";
  if (typeof v === "number") return numberCell(col, v);
  return "<td>" + esc(v === null ? "" : v) + "</td>";
}

// The row open in the details pane is marked as it is drawn, so the mark
// survives a sort or a filter; data-key carries the SongKey for the link
// cells filled in later.
export function bodyRow(row, visibleCols, code, rank, tip, songKey) {
  const cells = visibleCols
    .map(([col, i]) => col === RANK_COL
      ? '<td class="num rank">' + rank + "</td>"
      : bodyCell(col, row[i], songKey))
    .join("");
  const sel = code === state.graph ? ' class="sel" aria-current="true"' : "";
  return '<tr tabindex="-1"' + sel + ' title="' + esc(tip) + '" data-code="' + esc(code) + '"' +
    (typeof songKey === "string" ? ' data-key="' + esc(songKey) + '"' : "") + ">" + cells + "</tr>";
}

export function emptyRow(span) {
  return '<tr class="empty"><td colspan="' + span + '" class="text-secondary p-3">' +
    esc(UI.no_data) + "</td></tr>";
}

// While a sheet's rows are in flight, or when they failed to arrive. The same
// shape as emptyRow, and the .empty class, so the widths stylesheet skips it.
export function loadingRow(span, failed) {
  const body = failed
    ? esc(UI.load_failed) + ' <a href="">' + esc(UI.reload) + "</a>"
    : esc(t("loading", { n: SHEETS[state.sheet].rows }));
  return '<tr class="empty loading"><td colspan="' + span + '" class="text-secondary p-3">' +
    body + "</td></tr>";
}
