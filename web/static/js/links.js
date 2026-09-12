// The outbound links a song can carry: its page on each host it is published
// on (HOSTS, labels.CHART_HOSTS: Chorus Encore today) and its Clone Hero
// leaderboard, from data/links.<hash>.json (state.links), resolved offline by
// the lookup tools. A link is built only from a host's own URL template, and
// only when the value matches that host's character class, so a registry
// edited by hand cannot point at another host. The same links are two
// page-built columns: Chart carries the host key (the first in HOSTS order the
// song is on; null when none), Leaderboard a bit; the row says where, the file
// says the id, so the table shows and filters before the file has arrived.
import { UI, HOSTS } from "./boot.js";
import { esc } from "./dom.js";
import { t } from "./format.js";
import { state } from "./state.js";

export const CHART_COL = "Chart";
export const LB_COL = "Leaderboard";
const LB = "lb";

// kind -> {ok, url(value), label, tip}: every host, then the leaderboard
const RULES = Object.fromEntries(HOSTS.map(([key, host]) =>
  [key, { ok: new RegExp(host.id), url: v => host.url.replace("{id}", v), label: host.label, tip: host.tip }]));
RULES[LB] = { ok: /^[A-Za-z0-9_-]{40,50}$/, url: v => t("leaderboard_url", { hash: v }), label: UI.leaderboard, tip: UI.leaderboard_tip };
const KINDS = [...HOSTS.map(([key]) => key), LB];
const ARROW = '<span aria-hidden="true">&#8599;</span>';

// {href, label, tip} for one kind, or null while the file has not arrived or
// the song is not on it.
export function linkFor(songKey, kind) {
  const song = state.links && typeof songKey === "string" ? state.links[songKey] : null;
  const rule = RULES[kind];
  if (!song || !rule) return null;
  const value = song[kind];
  if (typeof value !== "string" || !rule.ok.test(value)) return null;
  return { href: rule.url(encodeURIComponent(value)), label: rule.label, tip: rule.tip };
}

const anchor = (link, cls, text) => '<a class="' + cls + '" target="_blank" rel="noopener" title="' +
  esc(link.tip) + '" href="' + esc(link.href) + '">' + text + "</a>";

// The anchors a song has, named, every host then the leaderboard, for the
// pane's tool row; "" while the file has not arrived or the song has none.
export function linkAnchors(songKey, cls = "ext") {
  return KINDS.map(kind => {
    const link = linkFor(songKey, kind);
    return link ? anchor(link, cls, esc(link.label) + " " + ARROW) : "";
  }).join("");
}

// A link column's cell: the arrow as an anchor once the file is here, a dim
// arrow until then (filled in by fillLinkCells), nothing for a row without
// the link. The Chart cell's value is its host key; the Leaderboard cell's is
// a boolean.
export function linkCell(col, v, songKey) {
  const kind = col === CHART_COL ? (typeof v === "string" && v in RULES ? v : null) : (v === true ? LB : null);
  if (!kind) return '<td class="lnkc"></td>';
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
