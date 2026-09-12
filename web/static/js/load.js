// The rows arrive by fetch, one hashed JSON file per sheet, so the page and its
// scripts stay small and cacheable and a sheet is paid for only when it is
// looked at. One in-flight promise per sheet; a failure rejects and is the
// caller's to show. The other sheets are prefetched when the browser is idle,
// so a later click, and a later deploy that removes the old file, both hit the
// browser cache; not under Save-Data, where a viewer asked for less.
import { SHEETS, LINKS_FILE } from "./boot.js";
import { state } from "./state.js";

const inflight = {};
let linksInflight = null;

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

// The links file: where each song is published and its leaderboard. One
// in-flight promise; {songs: {}} at once when the site has no file; a failed
// fetch rejects and the caller carries on without the anchors.
export function loadLinks() {
  if (state.links) return Promise.resolve({ songs: state.links });
  if (!LINKS_FILE) { state.links = {}; return Promise.resolve({ songs: {} }); }
  if (!linksInflight) {
    linksInflight = fetch(LINKS_FILE)
      .then(r => { if (!r.ok) throw new Error(r.status + " " + LINKS_FILE); return r.json(); })
      .then(file => { state.links = file.songs || {}; return { songs: state.links }; })
      .catch(err => { linksInflight = null; throw err; });
  }
  return linksInflight;
}

// Every sheet, for a search across the library; a sheet that fails is skipped.
export function loadAll() {
  return Promise.all(Object.keys(SHEETS).map(s => loadSheet(s).catch(() => null))).then(() => undefined);
}

export function prefetchIdle() {
  if (navigator.connection && navigator.connection.saveData) return;
  const others = Object.keys(SHEETS).filter(s => !state.data[s]);
  const go = () => { others.forEach(s => loadSheet(s).catch(() => {})); loadLinks().catch(() => {}); };
  if (typeof requestIdleCallback === "function") requestIdleCallback(go);
  else setTimeout(go, 2000);
}
