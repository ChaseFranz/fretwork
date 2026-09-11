// Column widths the viewer drags out. They are applied as one generated
// stylesheet keyed by :nth-child rather than as styles on the cells: the table
// runs to thousands of rows, and nth-child follows the visible order for free,
// so a repaint after a reorder needs no bookkeeping.
import { state, saveWidths, visible } from "./state.js";

const MIN_PX = 48;
const STYLE_ID = "fw-widths";

let drag = null;

function sheet() {
  let node = document.getElementById(STYLE_ID);
  if (!node) {
    node = document.createElement("style");
    node.id = STYLE_ID;
    document.head.appendChild(node);
  }
  return node;
}

// Pin both edges. In an auto-layout table a width on its own is only a hint,
// and a max-width can cap a column but never widen one past its content.
// The empty-state row spans every column, so it is left out.
function rule(width, nth) {
  const at = ":nth-child(" + nth + ")";
  return ".fw-wrap thead th" + at + ",.fw-wrap tbody tr:not(.empty) td" + at +
    "{width:" + width + "px;min-width:" + width + "px;max-width:" + width +
    "px;overflow:hidden;text-overflow:ellipsis}";
}

export function applyWidths() {
  sheet().textContent = visible()
    .map(([col], n) => state.widths[col] ? rule(state.widths[col], n + 1) : "")
    .join("");
}

function onDown(e) {
  const grip = e.target.closest(".rz");
  if (!grip) return;
  e.preventDefault();
  e.stopPropagation();
  const th = grip.closest("th");
  drag = { col: grip.dataset.rz, from: e.clientX, width: th.getBoundingClientRect().width };
  document.body.classList.add("resizing");
}

function onMove(e) {
  if (!drag) return;
  state.widths[drag.col] =
    Math.round(Math.max(MIN_PX, drag.width + e.clientX - drag.from));
  applyWidths();
}

function onUp() {
  if (!drag) return;
  drag = null;
  document.body.classList.remove("resizing");
  saveWidths();
}

// Double-click hands the column back to the browser's own sizing.
function onDouble(e) {
  const grip = e.target.closest(".rz");
  if (!grip) return;
  e.stopPropagation();
  delete state.widths[grip.dataset.rz];
  saveWidths();
  applyWidths();
}

// The header row's listeners live on #head, which draw() refills rather than
// replaces, so they survive every repaint. The move and release listeners sit on
// the document instead of capturing the pointer, so a fast drag that outruns the
// 7px grip still lands.
export function initWidths() {
  const head = document.getElementById("head");
  head.addEventListener("pointerdown", onDown);
  head.addEventListener("dblclick", onDouble);
  document.addEventListener("pointermove", onMove);
  document.addEventListener("pointerup", onUp);
  document.addEventListener("pointercancel", onUp);
}
