"""
BOOT - assembles the JSON payload the page's JavaScript reads on load

Delivered as one <script type="application/json"> island rather than inlined
into the script, so spreadsheet text can never be parsed as code.
"""

import json

import config
from functions import labels as labels_mod

def boot_payload(frames_data):
    return {
        'data': frames_data,
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
def boot_json(frames_data):
    return json.dumps(boot_payload(frames_data)).replace('<', '\\u003c')
