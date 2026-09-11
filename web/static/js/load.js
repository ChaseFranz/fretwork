// The rows arrive by fetch, one hashed JSON file per sheet, so the page and its
// scripts stay small and cacheable and a sheet is paid for only when it is
// looked at. One in-flight promise per sheet; a failure rejects and is the
// caller's to show. The other sheets are prefetched when the browser is idle,
// so a later click, and a later deploy that removes the old file, both hit the
// browser cache; not under Save-Data, where a viewer asked for less.
import { SHEETS } from "./boot.js";
import { state } from "./state.js";

const inflight = {};

export function loadSheet(name) {
  if (state.data[name]) return Promise.resolve(state.data[name]);
  if (!inflight[name]) {
    inflight[name] = fetch(SHEETS[name].file)
      .then(r => { if (!r.ok) throw new Error(r.status + " " + SHEETS[name].file); return r.json(); })
      .then(sheet => {
        state.data[name] = sheet;
        document.dispatchEvent(new CustomEvent("fw:sheet", { detail: { sheet: name } }));
        return sheet;
      })
      .catch(err => { delete inflight[name]; throw err; });
  }
  return inflight[name];
}

export function prefetchIdle() {
  if (navigator.connection && navigator.connection.saveData) return;
  const others = Object.keys(SHEETS).filter(s => !state.data[s]);
  const go = () => others.forEach(s => loadSheet(s).catch(() => {}));
  if (typeof requestIdleCallback === "function") requestIdleCallback(go);
  else setTimeout(go, 2000);
}
