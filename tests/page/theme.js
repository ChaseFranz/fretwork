// The theme (section 15): decided before the first paint by page.THEME_SCRIPT
// (a stored choice, else the OS), switched by the header's toggle, remembered
// in fw.theme, and reaching Bootstrap's ground, the graph, the compare marks
// and the document pages. run.py seeds fw.theme=light, so the page opened
// light whatever the OS prefers.
import { BOOT, say, done, wait, click, ready } from "./lib.js";
await ready();

const { ui: UI } = BOOT;
const root = document.documentElement;
const theme = () => root.getAttribute("data-bs-theme");
const stored = () => { try { return localStorage.getItem("fw.theme"); } catch (e) { return null; } };
const token = name => {
  const s = document.createElement("span"); s.style.color = "var(" + name + ")"; document.body.appendChild(s);
  const c = getComputedStyle(s).color; s.remove(); return c;
};
const lum = rgb => { const [r, g, b] = (rgb.match(/[\d.]+/g) || []).map(Number); return (r + g + b) / 765; };
const btn = document.getElementById("theme");

say("a stored choice decides the theme before the first paint", stored() === "light" && theme() === "light", stored() + " / " + theme());
say("the light ground is light", lum(token("--fw-bg")) > 0.9, token("--fw-bg"));
say("the header carries the toggle, labelled with the action it offers", btn && btn.title === UI.theme_to_dark &&
    btn.getAttribute("aria-label") === UI.theme_to_dark && !btn.hasAttribute("aria-pressed"), btn && btn.title);
say("Bootstrap's ground is the page's", getComputedStyle(document.body).backgroundColor === token("--fw-bg"),
    getComputedStyle(document.body).backgroundColor + " vs " + token("--fw-bg"));
say("the header stands on the same ground", getComputedStyle(document.querySelector(".fw-head")).backgroundColor === token("--fw-bg"));

// --- the graph follows a switch -----------------------------------------------------------
const row = document.querySelector("#body tr[data-code]");
click(row);
await wait(800);
const canvas = () => document.querySelector("#pane canvas");
const corner = () => { const d = canvas().getContext("2d").getImageData(1, 1, 1, 1).data; return "rgb(" + d[0] + ", " + d[1] + ", " + d[2] + ")"; };
const lightBg = token("--fw-bg");
say("the canvas is painted on the light ground", canvas() && corner() === lightBg, canvas() && corner());
let fired = null;
document.addEventListener("fw:theme", e => { fired = e.detail; }, { once: true });
click(btn);
await wait(300);
say("the toggle switches to dark and remembers it", theme() === "dark" && stored() === "dark", theme() + " / " + stored());
say("and announces it", fired === "dark", fired);
say("the button now offers the light theme", btn.title === UI.theme_to_light && btn.getAttribute("aria-label") === UI.theme_to_light, btn.title);
say("the tokens changed with the theme", token("--fw-bg") !== lightBg && lum(token("--fw-bg")) < 0.2, token("--fw-bg"));
say("the graph repainted on the dark ground", corner() === token("--fw-bg"), corner() + " vs " + token("--fw-bg"));
say("the browser's theme-color follows", document.querySelector('meta[name="theme-color"]').content === "#1a1920",
    document.querySelector('meta[name="theme-color"]').content);
say("the open row's edge is the brand", getComputedStyle(row.firstElementChild).boxShadow.includes(token("--fw-brand-text")),
    getComputedStyle(row.firstElementChild).boxShadow);

// --- the compare marks are tokens, so they switched too --------------------------------------
const cmp = document.querySelector("#pane .sgrid .cmp");
if (cmp) {
  click(cmp);
  await wait(800);
  const on = [...document.querySelectorAll("#pane .sgrid .cell.on")];
  const a = token("--fw-series-a");
  say("a marked cell's bar is series A's dark value", on.length && getComputedStyle(on[0]).borderTopColor === a, on.length && getComputedStyle(on[0]).borderTopColor + " vs " + a);
  click(btn);
  await wait(300);
  say("switched back to light, the same mark is series A's light value", theme() === "light" && getComputedStyle(on[0]).borderTopColor === token("--fw-series-a") && token("--fw-series-a") !== a,
      getComputedStyle(on[0]).borderTopColor + " vs " + token("--fw-series-a"));
  say("and the graph repainted again", corner() === token("--fw-bg"));
}

// --- the head script, in fresh documents -----------------------------------------------------
const load = url => new Promise(resolve => {
  const f = document.createElement("iframe");
  f.style.cssText = "width:400px;height:300px;position:absolute;left:-1000px";
  f.onload = () => resolve(f);
  f.src = url;
  document.body.appendChild(f);
});
const themeOf = f => f.contentDocument.documentElement.getAttribute("data-bs-theme");
const groundOf = f => f.contentWindow.getComputedStyle(f.contentDocument.body).backgroundColor;
// plain.html carries run.py's storage script, which clears the store as it
// loads, so it can only show the no-choice path; the document pages carry no
// such script and show the stored one
try { localStorage.removeItem("fw.theme"); } catch (e) {}
const os = matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
const fresh = await load("plain.html");
say("with no choice stored a fresh page follows the OS", themeOf(fresh) === os, themeOf(fresh) + " vs " + os);
try { localStorage.setItem("fw.theme", "dark"); } catch (e) {}
const about = await load("about.html");
say("a stored dark opens about.html dark, on the dark palette", themeOf(about) === "dark" && groundOf(about) === "rgb(26, 25, 32)", themeOf(about) + " " + groundOf(about));
try { localStorage.setItem("fw.theme", "light"); } catch (e) {}
const aboutLight = await load("about.html");
say("a stored light opens it light", themeOf(aboutLight) === "light" && groundOf(aboutLight) === "rgb(251, 250, 253)", themeOf(aboutLight) + " " + groundOf(aboutLight));
const missing = await load("404.html");
say("the 404 page too", themeOf(missing) === "light" && groundOf(missing) === "rgb(251, 250, 253)", themeOf(missing) + " " + groundOf(missing));
say("the document pages' script is the app's", about.contentDocument.head.innerHTML.includes('localStorage.getItem("fw.theme")') &&
    document.head.innerHTML.includes('localStorage.getItem("fw.theme")'));
done();
