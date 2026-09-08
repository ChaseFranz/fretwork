// The button-group renderer shared by the sheet, level and official rows.
// Pass a Set as `active` for a group where more than one can be lit at once.
import { el, esc } from "./dom.js";

export function chips(hostId, items, active, onPick) {
  const isOn = active instanceof Set ? v => active.has(v) : v => v === active;
  el(hostId).innerHTML = items.map(v =>
    '<button type="button" class="btn btn-fw btn-outline-secondary' +
    (isOn(v) ? " active" : "") + '" data-v="' + esc(v) + '">' +
    esc(v) + "</button>").join("");
  el(hostId).querySelectorAll("button")
    .forEach(b => b.onclick = () => onPick(b.dataset.v));
}
