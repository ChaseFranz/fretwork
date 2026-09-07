"""
PAGE - composes a header's page: its newest spreadsheet, rendered into index.html

One regex pass rather than chained replaces, so a value that happens to
contain __TOKEN__ text is never rewritten by a later substitution. URLs in the
page are relative, so it works at a domain root or under any sub-path.
"""

import html
import re

import config
from web import assets, boot, bootstrap, frames

_PLACEHOLDER = re.compile(r'__([A-Z]+)__')

BOOTSTRAP_LINK = '<link rel="stylesheet" href="bootstrap.css">'


def bootstrap_head(bootstrap_css):
    return BOOTSTRAP_LINK if bootstrap_css else bootstrap.FALLBACK_CSS


def render_page(title, source, bootstrap_css, boot_json):
    values = {
        'TITLE': html.escape(title),
        'SOURCE': html.escape(source),
        'BOOTSTRAP': bootstrap_head(bootstrap_css),
        'BOOT': boot_json,
    }
    template = assets.read_text('index.html')
    body = _PLACEHOLDER.sub(lambda m: values[m.group(1)], template)
    return body.encode('utf-8')


# What serve and publish both need: (xlsx_path, sheets, total rows, page body).
def build(header, xlsx_path, bootstrap_css):
    xlsx_path, sheets = frames.load_frames(header, xlsx_path)
    total = sum(len(df) for df in sheets.values())
    source = f"{xlsx_path.name}  -  {total} rows  -  {', '.join(sheets)}"
    body = render_page(f"{config.SITE_NAME} - {header}", source, bootstrap_css,
                       boot.boot_json(frames.frames_payload(sheets)))
    return xlsx_path, sheets, total, body
