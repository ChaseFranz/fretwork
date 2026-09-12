// The theme: dark or light, stamped on <html> as data-bs-theme, which Bootstrap
// and every token in app.css key on. page.THEME_SCRIPT decides it before the
// first paint (a stored choice, else the OS); this module is the header's
// toggle and the follow-up: the choice is remembered (fw.theme), a visitor who
// has not chosen follows the OS live, and a switch tells the graph to repaint
// (fw:theme), since the canvas reads its colours at each paint rather than
// from a stylesheet. The button's label is the action it offers, so it is a
// plain button, not a pressed toggle.
import { UI } from "./boot.js";
import { el } from "./dom.js";

const THEME_KEY = "fw.theme";
const ROOT = document.documentElement;
const LIGHT = matchMedia("(prefers-color-scheme: light)");
// the browser chrome's colour on a phone, kept with the ground
const THEME_COLOR = { dark: "#1a1920", light: "#fbfafd" };

export const currentTheme = () => ROOT.getAttribute("data-bs-theme") === "light" ? "light" : "dark";

function labelButton() {
  const b = el("theme");
  if (!b) return;
  const toLight = currentTheme() === "dark";
  b.innerHTML = '<span aria-hidden="true">' + (toLight ? "&#9728;&#xFE0E;" : "&#9790;&#xFE0E;") + "</span>";
  b.title = toLight ? UI.theme_to_light : UI.theme_to_dark;
  b.setAttribute("aria-label", b.title);
}

// Bootstrap's buttons and controls each fade their colours over 150 ms, which
// on a theme switch is a page changing piecemeal; the switch is made with
// transitions off and they come back on the frame after.
function apply(theme) {
  ROOT.classList.add("theming");
  ROOT.setAttribute("data-bs-theme", theme);
  requestAnimationFrame(() => requestAnimationFrame(() => ROOT.classList.remove("theming")));
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.content = THEME_COLOR[theme];
  labelButton();
  document.dispatchEvent(new CustomEvent("fw:theme", { detail: theme }));
}

export function setTheme(theme, remember = true) {
  if (remember) { try { localStorage.setItem(THEME_KEY, theme); } catch (e) {} }
  apply(theme);
}

export function initTheme() {
  labelButton();
  const b = el("theme");
  if (b) b.addEventListener("click", () => setTheme(currentTheme() === "dark" ? "light" : "dark"));
  // no choice stored: the OS's setting is followed as it changes
  LIGHT.addEventListener("change", e => {
    let stored = null;
    try { stored = localStorage.getItem(THEME_KEY); } catch (err) {}
    if (stored !== "light" && stored !== "dark") apply(e.matches ? "light" : "dark");
  });
}
