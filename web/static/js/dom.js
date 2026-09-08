// The two DOM primitives every other module builds on.

export const el = id => document.getElementById(id);

export const esc = v => String(v)
  .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;");

// Our own strings carry a minimal [text](url) markup so that a mention of
// fretwork or its author can be a link without putting HTML in labels.py. Every
// character still goes through esc(); the only markup produced is an anchor this
// function builds itself, so text that came from data could not inject any.
const LINK = /\[([^\]]+)\]\(([^()]*(?:\([^()]*\)[^()]*)*)\)/g;

export function rich(text) {
  let out = "", at = 0;
  for (const found of String(text).matchAll(LINK)) {
    const safe = /^https?:\/\//.test(found[2]);
    out += esc(text.slice(at, found.index)) + (safe
      ? '<a href="' + esc(found[2]) + '" target="_blank" rel="noopener">' +
        esc(found[1]) + "</a>"
      : esc(found[1]));
    at = found.index + found[0].length;
  }
  return out + esc(text.slice(at));
}

// Drop a panel just under its anchor, kept inside the viewport.
export function placeUnder(panel, anchor) {
  const box = anchor.getBoundingClientRect();
  panel.style.left = Math.min(box.left, window.innerWidth - panel.offsetWidth - 10) + "px";
  panel.style.top = (box.bottom + 4) + "px";
}
