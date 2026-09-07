"""
PAGE - composes a header's page: its newest spreadsheet, rendered into index.html

One regex pass rather than chained replaces, so a value that happens to
contain __TOKEN__ text is never rewritten by a later substitution. URLs in the
page are relative, so it works at a domain root or under any sub-path.
"""

import datetime
import html
import re

import config
from functions import labels, timestamp
from web import assets, boot, bootstrap, frames

_PLACEHOLDER = re.compile(r'__([A-Z]+)__')

# a chart whose graph reads well as a link preview
OG_IMAGE = 'graph/10145439XG.png'

BOOTSTRAP_LINK = '<link rel="stylesheet" href="bootstrap.css">'


def bootstrap_head(bootstrap_css):
    return BOOTSTRAP_LINK if bootstrap_css else bootstrap.FALLBACK_CSS


# Description always; the social-preview tags need an absolute URL, so they are
# emitted only for a published site with config.SITE_URL set.
def meta_head(public):
    description = labels.UI['description']
    tags = [f'<meta name="description" content="{html.escape(description)}">']
    if public and config.SITE_URL:
        url = config.SITE_URL.rstrip('/')
        for prop, content in (('og:type', 'website'), ('og:url', url),
                              ('og:title', config.SITE_NAME), ('og:description', description),
                              ('og:image', f'{url}/{OG_IMAGE}')):
            tags.append(f'<meta property="{prop}" content="{html.escape(content)}">')
        tags.append('<meta name="twitter:card" content="summary_large_image">')
    return '\n'.join(tags)


# "Updated 7 September 2026  -  4,634 charts", from the spreadsheet's own timestamp.
def public_source(header, xlsx_path, total):
    try:
        stamp = timestamp.ext_ts(xlsx_path, 'metrics', header)
        when = datetime.datetime.strptime(stamp, timestamp.TS_FORMAT)
        date = f"{when.day} {when:%B %Y}"
    except (ValueError, TypeError):
        return labels.t_count(total)
    return f"{labels.UI['updated'].format(date=date)}  -  {labels.t_count(total)}"


def render_page(title, source, bootstrap_css, boot_json, public=False):
    values = {
        'TITLE': html.escape(title),
        'SOURCE': html.escape(source),
        'META': meta_head(public),
        'BOOTSTRAP': bootstrap_head(bootstrap_css),
        'BOOT': boot_json,
    }
    template = assets.read_text('index.html')
    body = _PLACEHOLDER.sub(lambda m: values[m.group(1)], template)
    return body.encode('utf-8')


# What serve and publish both need: (xlsx_path, sheets, total rows, page body).
# A published page names no internal file: the title is just the site and the
# strapline is when the data was built. Serving locally keeps both, which is
# what tells you which library and which run you are looking at.
def build(header, xlsx_path, bootstrap_css, public=False):
    xlsx_path, sheets = frames.load_frames(header, xlsx_path)
    total = sum(len(df) for df in sheets.values())
    if public:
        title, source = config.SITE_NAME, public_source(header, xlsx_path, total)
    else:
        title = f"{config.SITE_NAME} - {header}"
        source = f"{xlsx_path.name}  -  {total} rows  -  {', '.join(sheets)}"
    body = render_page(title, source, bootstrap_css,
                       boot.boot_json(frames.frames_payload(sheets)), public)
    return xlsx_path, sheets, total, body
