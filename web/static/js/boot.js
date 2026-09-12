// Server-injected data, parsed once from the JSON island in index.html.
// Re-exported under the names the rest of the page uses.
const BOOT = JSON.parse(document.getElementById("fw-boot").textContent);

// The sheet manifest: {sheet: {file, rows, columns}}. The rows themselves are
// fetched on demand from `file` (load.js) into state.data.
export const SHEETS = BOOT.data;
export const SHEET_OF_CODE = BOOT.sheetOfCode || {};   // instrument letter -> sheet
export const PREFS_VERSION = BOOT.prefsVersion || 0;
export const RENDER = BOOT.render;      // the graph palette, plot.resolve_profile()'s canvas keys
export const LINKS_FILE = BOOT.links || null;   // data/links.<hash8>.json, or null when no song has a link
export const HOSTS = BOOT.hosts || [];          // [[key, {label, tip, url, id}]], where a chart can be published
export const LABELS = BOOT.labels;
export const ORDER = BOOT.order;
export const HIDDEN_DEFAULT = BOOT.hiddenDefault;
export const VALUE_ORDER = BOOT.valueOrder;
export const VALUE_LABELS = BOOT.valueLabels;
export const FOOTER = BOOT.footer;
export const DOC_PAGES = BOOT.docPages || [];   // [[file, ui key], ...] the footer lists
export const HELP = BOOT.help;
export const EXPLAINER = BOOT.explainer;
export const UI = BOOT.ui;
export const TIMECOLS = new Set(BOOT.timecols);
export const MISSING = BOOT.missing;
export const MISS_TEXT = BOOT.missText;
export const MISS_HELP = BOOT.missHelp;

export const LEVELS = ["Expert", "Hard", "Medium", "Easy"];

// Numeric columns with more distinct values than this get a min/max box
// instead of a checkbox list.
export const RANGE_MIN_DISTINCT = 25;
