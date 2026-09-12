"""
BOOT - assembles the JSON payload the page's JavaScript reads on load

Delivered as one <script type="application/json"> island rather than inlined
into the script, so spreadsheet text can never be parsed as code.
"""

import json
import sys

import config
from functions import labels as labels_mod

# The render profile keys a canvas can use. figsize, dpi and the point sizes
# are matplotlib's and stay out; the page sizes its own text.
WEB_RENDER_KEYS = ('mode', 'color_d', 'color_nps', 'color_vps', 'linewidth', 'grid_alpha',
                   'fill_curves', 'fill_alpha', 'figure_bg', 'axes_bg', 'text_color',
                   'muted_text_color', 'grid_color', 'spine_color')


# The same two-dict merge plot.resolve_profile does, so the page and render.py
# draw from one palette; an unknown mode falls back to light in both. A key the
# merge lacks raises, which is the drift guard for an upstream file this fork
# does not edit. The page's own chrome is dark only, hence the warning.
def render_profile():
    mode = config.RENDER_DEFAULT.get('mode', 'light')
    theme = config.RENDER_THEMES.get(mode, config.RENDER_THEMES['light'])
    merged = {**config.RENDER_DEFAULT, **theme}
    profile = {k: merged[k] for k in WEB_RENDER_KEYS}
    if profile['mode'] != 'dark':
        print(f"warning: config.RENDER_DEFAULT mode is {profile['mode']!r}; the page is dark only", file=sys.stderr)
    return profile


def boot_payload(manifest, sheet_of_code, links=None):
    return {
        'data': manifest,
        'links': links,            # data/links.<hash8>.json, or null when no song has one
        'render': render_profile(),
        'sheetOfCode': sheet_of_code,
        'prefsVersion': labels_mod.PREFS_VERSION,
        'labels': labels_mod.COLUMN_LABELS,
        'order': list(labels_mod.DISPLAY_ORDER),
        'hiddenDefault': list(labels_mod.DEFAULT_HIDDEN),
        'valueOrder': {k: list(v) for k, v in labels_mod.VALUE_ORDER.items()},
        'valueLabels': labels_mod.VALUE_LABELS,
        'footer': [list(pair) for pair in labels_mod.FOOTER_LINKS],
        'docPages': [list(pair) for pair in labels_mod.DOC_PAGES],
        'help': labels_mod.COLUMN_HELP,
        'explainer': [list(pair) for pair in labels_mod.EXPLAINER],
        'ui': {**labels_mod.UI, 'title': config.SITE_NAME},
        'timecols': list(labels_mod.TIME_COLUMNS),
        'missing': {k: list(v) for k, v in labels_mod.MISSING_VALUES.items()},
        'missText': labels_mod.MISSING_TEXT,
        'missHelp': labels_mod.MISSING_HELP,
    }


# Escaping every "<" keeps spreadsheet text from closing the script tag or
# entering its double-escaped state. A valid JSON escape, parsed back unchanged.
def boot_json(manifest, sheet_of_code, links=None):
    return json.dumps(boot_payload(manifest, sheet_of_code, links)).replace('<', '\\u003c')
