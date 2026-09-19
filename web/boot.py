"""
BOOT - assembles the JSON payload the page's JavaScript reads on load

Delivered as one <script type="application/json"> island rather than inlined
into the script, so spreadsheet text can never be parsed as code.
"""

import json

import config
from functions import labels as labels_mod

# The render profile keys the canvas uses: how the picture is drawn, not what
# colour it is. figsize, dpi and the point sizes are matplotlib's and stay out;
# the page sizes its own text. The colours stay out too: the page's are the
# role tokens in static/css/app.css, one set per theme, which the canvas reads
# at each paint (graph.js gPalette), so the graph follows the theme; the PNG
# render.py and the social preview draw keep config.RENDER_THEMES.
WEB_RENDER_KEYS = ('linewidth', 'grid_alpha', 'fill_curves', 'fill_alpha')


# The same two-dict merge plot.resolve_profile does, so the page and render.py
# draw the same lines. A key the merge lacks raises, which is the drift guard
# for an upstream file this fork does not edit.
def render_profile():
    mode = config.RENDER_DEFAULT.get('mode', 'light')
    theme = config.RENDER_THEMES.get(mode, config.RENDER_THEMES['light'])
    merged = {**config.RENDER_DEFAULT, **theme}
    return {k: merged[k] for k in WEB_RENDER_KEYS}


# The columns the page can show: the sheets' own (the manifest's columns, the
# page-built ones included) and the synthetic Rank. The labels and help are
# sent for these alone, so the diagnostic columns analyze drops from the
# spreadsheet (config.EXTRA_METRICS) cost the island nothing; with no
# manifest (a test), every word goes.
def columns_present(manifest):
    if not manifest:
        return None
    return {'Rank'} | {c for sheet in manifest.values() for c in sheet.get('columns', ())}


def boot_payload(manifest, sheet_of_code, links=None, doc_pages=None, site_url=None):
    if doc_pages is None:
        doc_pages = labels_mod.DOC_PAGES
    present = columns_present(manifest)
    words = lambda table: table if present is None else {k: v for k, v in table.items() if k in present}   # noqa: E731
    return {
        'siteUrl': site_url or None,   # the published address, for Copy link; None on serve, which copies its own
        'data': manifest,
        'links': links,            # data/links.<hash8>.json, or null when no song has one
        'hosts': [[key, host] for key, host in labels_mod.CHART_HOSTS],   # where a chart can be published
        'render': render_profile(),
        # the lines under ~D per family, for the legend, the readout and the alt text
        'curves': {fam: {'lines': [list(line) for line in spec['lines']], 'alt': spec['alt']}
                   for fam, spec in labels_mod.CURVE_FAMILIES.items()},
        'sheetOfCode': sheet_of_code,
        'prefsVersion': labels_mod.PREFS_VERSION,
        'labels': words(labels_mod.COLUMN_LABELS),
        'order': list(labels_mod.DISPLAY_ORDER),
        'hiddenDefault': list(labels_mod.DEFAULT_HIDDEN),
        'valueOrder': {k: list(v) for k, v in labels_mod.VALUE_ORDER.items()},
        'valueLabels': labels_mod.VALUE_LABELS,
        'footer': [list(pair) for pair in labels_mod.FOOTER_LINKS],
        'docPages': [list(pair) for pair in doc_pages],   # the document pages the site has, for the footer
        'help': words(labels_mod.COLUMN_HELP),
        'explainer': [list(pair) for pair in labels_mod.EXPLAINER],
        'ui': {**labels_mod.UI, 'title': config.SITE_NAME},
        'timecols': list(labels_mod.TIME_COLUMNS),
        'missing': {k: list(v) for k, v in labels_mod.MISSING_VALUES.items()},
        'missText': labels_mod.MISSING_TEXT,
        'missHelp': labels_mod.MISSING_HELP,
    }


# Escaping every "<" keeps spreadsheet text from closing the script tag or
# entering its double-escaped state. A valid JSON escape, parsed back unchanged.
def boot_json(manifest, sheet_of_code, links=None, doc_pages=None, site_url=None):
    return json.dumps(boot_payload(manifest, sheet_of_code, links, doc_pages, site_url)).replace('<', '\\u003c')
