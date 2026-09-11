// The column show/hide panel, whose rows can be dragged into a new order.
import { UI } from "./boot.js";
import { el, esc, placeUnder } from "./dom.js";
import { lab } from "./format.js";
import { state, allCols, saveHidden, saveOrder, resetColumns } from "./state.js";
import { draw } from "./table.js";

let dragging = null;

function renderCD() {
  const items = allCols().map(c =>
    '<div class="cc" draggable="true" data-col="' + esc(c) + '">' +
    '<span class="grip" title="' + esc(UI.reorder_tip) + '">&#10303;</span>' +
    '<div class="form-check"><input class="form-check-input" type="checkbox" id="cc' +
    esc(c) + '" data-col="' + esc(c) + '"' + (state.hidden.has(c) ? "" : " checked") + '>' +
    '<label class="form-check-label" for="cc' + esc(c) + '">' + esc(lab(c)) +
    "</label></div></div>").join("");
  el("cd").innerHTML = items +
    '<button class="btn btn-sm btn-outline-secondary w-100 mt-2" data-act="showall" title="' +
    esc(UI.columns_reset_tip) + '">' + esc(UI.columns_reset) + "</button>";
}

export function toggleCD(anchor) {
  const cd = el("cd");
  if (cd.classList.contains("show")) { closeCD(); return; }
  renderCD();
  cd.classList.add("show");
  el("cols").setAttribute("aria-expanded", "true");
  placeUnder(cd, anchor);
}

export function closeCD() {
  el("cd").classList.remove("show");
  el("cols").setAttribute("aria-expanded", "false");
}

// The panel's own DOM order is the column order: move the row, then read it back.
function initDrag(cd) {
  cd.addEventListener("dragstart", e => {
    dragging = e.target.closest(".cc");
    if (dragging) dragging.classList.add("dragging");
  });
  cd.addEventListener("dragover", e => {
    e.preventDefault();
    const over = e.target.closest(".cc");
    if (!dragging || !over || over === dragging) return;
    const box = over.getBoundingClientRect();
    const after = e.clientY > box.top + box.height / 2;
    over.parentNode.insertBefore(dragging, after ? over.nextSibling : over);
  });
  cd.addEventListener("dragend", () => {
    if (!dragging) return;
    dragging.classList.remove("dragging");
    dragging = null;
    state.order = [...cd.querySelectorAll(".cc")].map(row => row.dataset.col);
    saveOrder();
    draw();
  });
}

export function initChooser() {
  const cd = el("cd");
  initDrag(cd);
  cd.addEventListener("change", e => {
    if (e.target.type !== "checkbox") return;
    const col = e.target.dataset.col;
    if (e.target.checked) state.hidden.delete(col); else state.hidden.add(col);
    saveHidden();
    draw();
  });
  cd.addEventListener("click", e => {
    if (e.target.dataset.act !== "showall") return;
    resetColumns();
    draw();
    renderCD();
  });
}
