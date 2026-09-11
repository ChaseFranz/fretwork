// "There is more this way."
//
// Two things on this page scroll sideways - the control strip on a phone, and
// the table whenever it is wider than the window - and in both cases the edge
// gives nothing away when the last item happens to end flush with it. A fade
// that appears only while there is something past the edge says so, and clears
// itself once you reach the end. An overlay scrollbar cannot do this job: iOS
// hides it until you are already scrolling, which is too late to be a hint.
const SLACK = 4;              // px of sub-pixel rounding to ignore

const updaters = [];

export function edgeFade(scroller, host = scroller) {
  const update = () => host.classList.toggle("more",
    scroller.scrollWidth - scroller.scrollLeft - scroller.clientWidth > SLACK);
  scroller.addEventListener("scroll", update, { passive: true });
  window.addEventListener("resize", update);
  updaters.push(update);
  update();
  return update;
}

// A repaint can change how wide the table is - a column shown, hidden, resized
// or reordered - so draw() asks the fades to look again.
export const refreshFades = () => updaters.forEach(update => update());
