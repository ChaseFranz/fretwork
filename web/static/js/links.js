// The two outbound anchors a chart can carry: its page on Chorus Encore and
// its Clone Hero leaderboard, from data/links.<hash>.json (state.links),
// resolved offline by tools/enchor_lookup.py and tools/leaderboards_lookup.py.
// Each value is accepted only in its own character class before it goes into
// a URL template, so a registry edited by hand cannot point at another host.
import { UI } from "./boot.js";
import { esc } from "./dom.js";
import { t } from "./format.js";
import { state } from "./state.js";

const LINK_RULES = [
  ["enchor", /^[a-f0-9]{32}$/, "enchor_url", "md5", "enchor", "enchor_tip"],
  ["lb", /^[A-Za-z0-9_-]{40,50}$/, "leaderboard_url", "hash", "leaderboard", "leaderboard_tip"],
];

// Markup for the anchors a song has, or "" while the file has not arrived or
// the song is not in it.
export function linkAnchors(songKey) {
  const song = state.links && typeof songKey === "string" ? state.links[songKey] : null;
  if (!song) return "";
  return LINK_RULES.map(([key, ok, template, name, label, tip]) => {
    const value = song[key];
    if (typeof value !== "string" || !ok.test(value)) return "";
    return '<a class="ext" target="_blank" rel="noopener" title="' + esc(UI[tip]) + '" href="' +
      esc(t(template, { [name]: encodeURIComponent(value) })) + '">' + esc(UI[label]) + "</a>";
  }).join("");
}
