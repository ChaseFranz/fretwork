// Shared by every suite: results go into <pre id="results">, which run.py reads
// out of --dump-dom. Anything that throws lands as an ERROR line rather than as
// silence, which is the failure mode that costs the most time to diagnose.
// Nothing here imports a page module: the island is parsed again, so the suites
// keep working when section 05 bundles the modules away.
export const BOOT = JSON.parse(document.getElementById("fw-boot").textContent);

// Async from day one: section 05 turns this into a fetch of BOOT.data[sheet].file.
export async function rows(sheet) {
  return BOOT.data[sheet].rows;
}
export const levels = () =>
  [...document.querySelectorAll("#levels button")].map(b => b.textContent);

const out = [];
let reported = false;

export function say(name, ok, detail) {
  out.push((ok ? "PASS " : "FAIL ") + name + (detail === undefined ? "" : "  " + String(detail)));
}
export const note = line => out.push("ok   " + line);
export const skip = (name, reason) => out.push("SKIP " + name + "  " + reason);

export function done() {
  if (reported) return;
  reported = true;
  const pre = document.createElement("pre");
  pre.id = "results";
  pre.textContent = out.join("\n");
  document.body.appendChild(pre);
}

window.addEventListener("error", e => { out.push("ERROR " + e.message); done(); });
window.addEventListener("unhandledrejection", e => {
  out.push("ERROR " + ((e.reason && e.reason.message) || e.reason)); done();
});

export const wait = ms => new Promise(resolve => setTimeout(resolve, ms));

// Returns dispatchEvent's result: false when the page called preventDefault.
export const key = (k, target) => (target || document.activeElement).dispatchEvent(
  new KeyboardEvent("keydown", { key: k, bubbles: true, cancelable: true }));
export const pt = (type, clientX, target) => target.dispatchEvent(
  new PointerEvent(type, { clientX, bubbles: true, cancelable: true, pointerId: 1 }));
// A synthetic click does not move focus; suites that assert focus return call
// el.focus() first (overlay.js records document.activeElement as the opener).
export const click = el => el.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));

export const chip = (hostId, text) =>
  [...document.querySelectorAll("#" + hostId + " button")].find(b => b.textContent === text);
export const lit = hostId =>
  [...document.querySelectorAll("#" + hostId + " button.active")].map(b => b.textContent);
export const shown = () => document.querySelectorAll("#body tr[data-code]").length;
export const params = () => new URLSearchParams(location.search);
