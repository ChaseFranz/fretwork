// The outbound links a song can carry: its page on Chorus Encore and its
// Clone Hero leaderboard, from data/links.<hash>.json (state.links), resolved
// offline by tools/enchor_lookup.py and tools/leaderboards_lookup.py. Each
// value is accepted only in its own character class before it goes into a URL
// template, so a registry edited by hand cannot point at another host. The
// same two are page-built boolean columns (LINK_COLS): the row says whether
// the link exists, so the table can show and filter on it before the file has
// arrived, and the file says where it goes.
import { UI } from "./boot.js";
import { esc } from "./dom.js";
import { t } from "./format.js";
import { state } from "./state.js";

const LINK_RULES = {
  enchor: [/^[a-f0-9]{32}$/, "enchor_url", "md5", "enchor", "enchor_tip"],
  lb: [/^[A-Za-z0-9_-]{40,50}$/, "leaderboard_url", "hash", "leaderboard", "leaderboard_tip"],
};
export const LINK_COLS = { Enchor: "enchor", Leaderboard: "lb" };   // column -> key in the file
const ARROW = '<span aria-hidden="true">&#8599;</span>';

// {href, label, tip} for one kind, or null while the file has not arrived or
// the song is not in it.
export function linkFor(songKey, kind) {
  const song = state.links && typeof songKey === "string" ? state.links[songKey] : null;
  const rule = LINK_RULES[kind];
  if (!song || !rule) return null;
  const [ok, template, name, label, tip] = rule;
  const value = song[kind];
  if (typeof value !== "string" || !ok.test(value)) return null;
  return { href: t(template, { [name]: encodeURIComponent(value) }), label: UI[label], tip: UI[tip] };
}

const anchor = (link, cls, text) => '<a class="' + cls + '" target="_blank" rel="noopener" title="' +
  esc(link.tip) + '" href="' + esc(link.href) + '">' + text + "</a>";

// The anchors a song has, named, for the pane's tool row; "" while the file
// has not arrived or the song is not in it.
export function linkAnchors(songKey, cls = "ext") {
  return Object.keys(LINK_RULES).map(kind => {
    const link = linkFor(songKey, kind);
    return link ? anchor(link, cls, esc(link.label) + " " + ARROW) : "";
  }).join("");
}

// A link column's cell: the arrow as an anchor once the file is here, a dim
// arrow until then (filled in by fillLinkCells), nothing for a row without it.
export function linkCell(col, has, songKey) {
  const kind = LINK_COLS[col];
  if (has !== true) return '<td class="lnkc"></td>';
  const link = linkFor(songKey, kind);
  if (link) return '<td class="lnkc">' + anchor(link, "ext", ARROW) + "</td>";
  return '<td class="lnkc" data-k="' + esc(kind) + '"><span class="wait" title="' + esc(UI.links_pending) + '">' + ARROW + "</span></td>";
}

// When the file lands after the rows were drawn: each waiting arrow becomes
// its anchor in place, so focus and scroll are not disturbed by a redraw.
export function fillLinkCells(tbody) {
  for (const td of tbody.querySelectorAll("td.lnkc[data-k]")) {
    const link = linkFor(td.closest("tr").dataset.key, td.dataset.k);
    td.innerHTML = link ? anchor(link, "ext", ARROW) : "";
    td.removeAttribute("data-k");
  }
}
