// The 404 page: what CloudFront serves for an unknown key. The bundle under
// http.server answers an unknown path with its own 404 (status only); the page
// itself is fetched by name and parsed.
import { BOOT, say, done } from "./lib.js";

const miss = await fetch("no-such-page-" + Math.random().toString(16).slice(2));
say("an unknown path is 404", miss.status === 404, miss.status);
const res = await fetch("404.html");
say("404.html is published", res.status === 200, res.status);
const doc = new DOMParser().parseFromString(await res.text(), "text/html");
say("it names the status", doc.querySelector("p.code") && doc.querySelector("p.code").textContent.trim() === "404");
const home = doc.querySelector('a[href="/"]');
say("a root-absolute way home, worded from the payload", home && home.textContent === BOOT.ui.not_found_link, home && home.textContent);
say("crawlers are told not to index it", doc.querySelector('meta[name="robots"]') && /noindex/.test(doc.querySelector('meta[name="robots"]').content));
say("no scripts, no placeholders", doc.querySelectorAll("script").length === 0 && !/__[A-Z][A-Z_]*__/.test(doc.body.textContent));
done();
