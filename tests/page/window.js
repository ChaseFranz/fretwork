// The windowed table (section 17): the DOM holds the rows on screen and a
// margin either side, two spacer rows stand for the rest, the ranks are the
// view's, a scroll paints the rows around it, the arrow keys and End reach rows
// that are not painted, and a shared code deep in the view opens with its row
// on screen. On the fixture the view is small enough to paint whole, which is
// the degenerate case; the real case is the Local run.
import { BOOT, rows as sheetRows, say, note, done, wait, click, key, ready, params } from "./lib.js";
await ready();
await wait(300);

const body = document.getElementById("body"), wrap = document.querySelector(".fw-wrap");
const painted = () => [...body.querySelectorAll("tr[data-code]")];
const pads = () => [...body.querySelectorAll("tr.pad")];
const rank = tr => parseInt(tr.querySelector("td.rank").textContent, 10);
const shown = () => parseInt((document.getElementById("count").textContent.match(/[\d,]+/) || ["0"])[0].replace(/,/g, ""), 10);
const inView = tr => { const b = tr.getBoundingClientRect(), e = wrap.getBoundingClientRect(); return b.top >= e.top && b.bottom <= e.bottom + 1; };
const continuous = rows => rows.every((tr, i) => i === 0 || rank(tr) === rank(rows[i - 1]) + 1);
// headless Chrome under the virtual clock delivers no scroll event for a programmatic scroll (fade.js), so it is dispatched
const scrollTo = y => { wrap.scrollTop = y; wrap.dispatchEvent(new Event("scroll")); };

if (params().get("code")) {
  // a shared code deep in the view (run.py picks the lowest official Expert D): painted and on screen
  const code = params().get("code");
  const pane = document.getElementById("pane");
  await wait(600);
  const row = body.querySelector('tr[data-code="' + code + '"]');
  say("the pane opened on the shared code", pane.classList.contains("on") && (pane.getAttribute("aria-label") || "").endsWith(": " + code), pane.getAttribute("aria-label"));
  say("its row is painted, marked and on screen", row && row.classList.contains("sel") && inView(row), row ? rank(row) + " of " + shown() : "not painted");
  // on the fixture the view is a few rows and painted whole; the Local run is the deep case
  if (shown() > 120) say("and deep in the view, with a spacer above it", row && rank(row) > 50 && pads().length >= 1 && parseInt(pads()[0].dataset.n, 10) > 0,
                         row && rank(row) + " / " + pads().map(p => p.dataset.n).join(","));
  else say("the small view is painted whole", pads().length === 0 && painted().length === shown(), painted().length + " of " + shown());
  say("it holds the tab stop", row && row.tabIndex === 0);
  done();
} else {
  click(document.getElementById("clear"));
  await wait(300);
  const total = shown();
  const sheet = document.querySelector("#sheets .active").textContent;
  const all = await sheetRows(sheet);
  say("with the filters cleared the count is the sheet", total === all.length, total + " vs " + all.length);
  if (total <= 120) {
    say("a small view is painted whole, with no spacer", painted().length === total && pads().length === 0, painted().length + " rows, " + pads().length + " spacers");
    say("ranks run from 1 without a gap", rank(painted()[0]) === 1 && continuous(painted()));
  } else {
    say("the DOM holds a window of the view", painted().length < total && painted().length >= 40, painted().length + " of " + total);
    say("one spacer stands for the rest", pads().length === 1 && parseInt(pads()[0].dataset.n, 10) === total - painted().length,
        pads().map(p => p.dataset.n).join(",") + " for " + (total - painted().length));
    say("ranks run from 1 without a gap", rank(painted()[0]) === 1 && continuous(painted()));
    const avg = painted().reduce((h, tr) => h + tr.getBoundingClientRect().height, 0) / painted().length;
    // the spacer stands at the average the previous paint measured, so the
    // scroll height is the view's order of magnitude, not an exact product
    say("the scroll height stands for the whole view", wrap.scrollHeight > total * 20 && wrap.scrollHeight < total * 120,
        wrap.scrollHeight + " for " + total + " rows at about " + Math.round(avg) + "px");

    // a scroll to the middle paints the rows around it
    scrollTo(wrap.scrollHeight / 2);
    await wait(400);
    const mid = painted();
    say("a scroll to the middle paints rows around it, between two spacers", pads().length === 2 && mid.length >= 40 && rank(mid[0]) > 1 && rank(mid[mid.length - 1]) < total,
        rank(mid[0]) + ".." + rank(mid[mid.length - 1]) + " of " + total);
    say("their ranks are continuous and start after the spacer", continuous(mid) && rank(mid[0]) === parseInt(pads()[0].dataset.n, 10) + 1,
        rank(mid[0]) + " after " + pads()[0].dataset.n);
    const onScreen = mid.filter(inView);
    say("the rows on screen are painted", onScreen.length >= 5, onScreen.length + " on screen");
    const perRow = (wrap.scrollHeight - document.getElementById("head").offsetHeight) / total;
    // the spacers stand at an estimate and the painted rows at their real heights, so the
    // row under the screen's top is within the overscan of the arithmetic, not exactly on it
    say("and the row under the screen's top is near where the scroll says", Math.abs((rank(onScreen[0]) - 1) - (wrap.scrollTop - document.getElementById("head").offsetHeight) / perRow) < 20,
        rank(onScreen[0]) + " at " + Math.round(wrap.scrollTop) + ", " + perRow.toFixed(1) + "px a row");

    // the arrow keys and End reach rows that are not painted
    const last = mid[mid.length - 1];
    last.focus();
    const lastRank = rank(last);
    key("ArrowDown", last);
    await wait(100);
    const next = document.activeElement.closest && document.activeElement.closest("tr[data-code]");
    say("ArrowDown from the last painted row focuses the next row of the view", next && rank(next) === lastRank + 1 && inView(next),
        (next && rank(next)) + " after " + lastRank + ", pads " + pads().map(p => p.dataset.n).join(","));
    key("End", document.activeElement);
    await wait(100);
    const end = document.activeElement.closest("tr[data-code]");
    say("End focuses the last row of the view", end && rank(end) === total && inView(end) && pads().length === 1, end && rank(end));
    key("Home", document.activeElement);
    await wait(100);
    const home = document.activeElement.closest("tr[data-code]");
    say("Home focuses the first", home && rank(home) === 1 && inView(home), home && rank(home));
    key("PageDown", document.activeElement);
    await wait(100);
    say("PageDown moves twelve", rank(document.activeElement.closest("tr[data-code]")) === 13);

    // a scroll with a row focused keeps the focus while the row is painted
    const held = document.activeElement.closest("tr[data-code]");
    scrollTo(wrap.scrollTop + 200);
    await wait(300);
    say("a small scroll keeps the focused row", document.activeElement.closest && document.activeElement.closest("tr[data-code]") &&
        rank(document.activeElement.closest("tr[data-code]")) === rank(held), document.activeElement.tagName);

    // a fast scroll down and back: the window must return to the first row (the
    // bug: a painted window starting a few rows down never looked stale against
    // the wanted window, clamped at 0, so rows 1 to 5 stayed a blank spacer)
    scrollTo(wrap.scrollHeight / 2);
    await wait(200);
    // the screen's first row about 60 at the estimate the spacers now stand at: the window
    // then starts between rows 1 and 39 whatever the next paint's estimate does (within 20%)
    const perRow2 = (wrap.scrollHeight - document.getElementById("head").offsetHeight) / total;
    scrollTo(document.getElementById("head").offsetHeight + 60 * perRow2);
    await wait(200);
    const topPad = () => body.firstElementChild && body.firstElementChild.classList.contains("pad") ? parseInt(body.firstElementChild.dataset.n, 10) : 0;
    const nearTop = topPad();
    say("a scroll near the top leaves a short spacer above the window", nearTop > 0 && nearTop < 40, nearTop + " rows above, pads " + pads().map(p => p.dataset.n).join(","));
    scrollTo(0);
    await wait(200);
    say("scrolling back to the top paints the first row, with no spacer above it", rank(painted()[0]) === 1 && topPad() === 0,
        rank(painted()[0]) + " first, " + topPad() + " above");
    say("and the scroller is still at the top", wrap.scrollTop === 0, wrap.scrollTop);
    const bottomPad = () => body.lastElementChild && body.lastElementChild.classList.contains("pad") ? parseInt(body.lastElementChild.dataset.n, 10) : 0;
    scrollTo(wrap.scrollHeight);
    await wait(200);
    say("scrolling to the bottom paints the last row, with no spacer below it", rank(painted()[painted().length - 1]) === total && bottomPad() === 0,
        rank(painted()[painted().length - 1]) + " of " + total + ", pad below " + bottomPad());

    // sorting keeps the scroll position and repaints the window there
    scrollTo(wrap.scrollHeight / 3);
    await wait(300);
    const before = wrap.scrollTop;
    click(document.querySelector('#head th[data-c="Song Title"] .lbl'));
    await wait(300);
    say("a sort keeps the scroll position and paints the window there", Math.abs(wrap.scrollTop - before) < 5 && pads().length === 2 && continuous(painted()),
        before + " -> " + wrap.scrollTop);
    say("the count is unchanged", shown() === total);
  }
  done();
}
