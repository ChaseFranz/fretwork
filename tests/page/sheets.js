// Switching sheets keeps what the visitor set: the level chips, the other
// filters, the search and the sort carry over to the new instrument, and only
// a filter that could match nothing there (a Part the sheet lacks) is dropped.
// Launched with ?f.Level=Hard,Medium&f.Type=<the first sheet's first Part>&r.NoteCount=1:&sort=NoteCount&q=<a letter>.
import { BOOT, say, done, wait, click, ready, params, levels } from "./lib.js";
await ready();

const sheets = Object.keys(BOOT.data);
const p = params();
const lit = () => [...document.querySelectorAll("#levels button.active")].map(b => b.textContent).join(",");
const filtered = c => document.querySelector('#head th[data-c="' + c + '"]').classList.contains("filtered");
const active = () => document.querySelector("#sheets .active").textContent;
const sorted = () => document.querySelector("#head th.sorted").dataset.c;
const q = document.getElementById("q");

say("the link set two levels, a Part, a range and a sort on the first sheet", active() === sheets[0] && lit() === "Hard,Medium" && filtered("Type") &&
    filtered("NoteCount") && sorted() === "NoteCount" && q.value === p.get("q"), lit() + " " + sorted() + " " + JSON.stringify(q.value));
say("the fixture has a second sheet", sheets.length > 1);

click([...document.querySelectorAll("#sheets button")].find(b => b.textContent === sheets[1]));
await wait(800);
say("on the second sheet the two levels are still the ones lit", active() === sheets[1] && lit() === "Hard,Medium", active() + " " + lit());
say("the range filter carried", filtered("NoteCount"));
say("the Part filter, which no row here could match, was dropped", !filtered("Type"));
say("the search carried", q.value === p.get("q"), JSON.stringify(q.value));
say("the sort carried", sorted() === "NoteCount", sorted());
say("the address bar says the same", params().get("f.Level") === "Hard,Medium" && params().get("f.Type") === null && params().get("r.NoteCount") !== null,
    location.search);
const shown = document.querySelectorAll("#body tr[data-code]").length;
const empty = document.querySelector("#body tr.empty");
say("rows are on screen, not an empty table", shown > 0 && !empty, shown + " rows");
say("every row is Hard or Medium", [...document.querySelectorAll("#body tr[data-code] .lvl")].every(b => ["Hard", "Medium"].includes(b.textContent)));

click([...document.querySelectorAll("#sheets button")].find(b => b.textContent === sheets[0]));
await wait(800);
say("back on the first sheet the levels are still the two", active() === sheets[0] && lit() === "Hard,Medium", lit());
say("and the Part filter stays gone", !filtered("Type"));

// the level chips are a multi-select into the same filter; a change made
// after the switch is what carries next time
click([...document.querySelectorAll("#levels button")].find(b => b.textContent === "Expert"));
await wait(100);
click([...document.querySelectorAll("#sheets button")].find(b => b.textContent === sheets[1]));
await wait(800);
say("a chip lit after the switch carries too", lit() === "Expert,Hard,Medium", lit());
for (const l of levels()) if (!lit().split(",").includes(l)) click([...document.querySelectorAll("#levels button")].find(b => b.textContent === l));
await wait(400);                       // the address bar is written 250 ms after a draw
say("all levels lit means no Level filter, in the address bar too", lit().split(",").length === levels().length && params().get("f.Level") === null,
    lit() + " " + location.search);
click([...document.querySelectorAll("#sheets button")].find(b => b.textContent === sheets[0]));
await wait(800);
say("and no filter carries as no filter", lit().split(",").length === levels().length && params().get("f.Level") === null, lit());
done();
