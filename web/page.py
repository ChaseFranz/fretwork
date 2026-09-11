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

_PLACEHOLDER = re.compile(r'__([A-Z][A-Z_]*)__')

# a chart whose graph reads well as a link preview
OG_IMAGE = 'graph/10145439XG.png'

# Crawlers are welcome on the page and not in the graph folder: it is ~12,000
# PNGs and a couple of gigabytes, none of it meaningful out of context, and all
# of it counted against the CDN's request and transfer allowance. The one graph
# used as the social preview stays fetchable.
ROBOTS = ('User-agent: *\n'
          'Allow: /\n'
          f'Allow: /{OG_IMAGE}\n'
          'Disallow: /graph/\n')

BOOTSTRAP_LINK = '<link rel="stylesheet" href="bootstrap.css">'


# Checks the template against the values before substituting: every placeholder
# must have a value (a typo or a missing value) and every value must be named by
# the template (a placeholder the regex cannot see, which is how __LICENSE_URL__
# once shipped as text). Substitution is one pass, so a value is inserted verbatim
# and never re-scanned; with both checks passing no placeholder can survive, and
# the output, which carries the whole data island, is never scanned at all.
def fill(template, values):
    names = set(_PLACEHOLDER.findall(template))
    missing, unused = sorted(names - values.keys()), sorted(values.keys() - names)
    if missing or unused:
        raise KeyError(f"placeholders and values disagree: missing {missing}, unused {unused}")
    return _PLACEHOLDER.sub(lambda m: values[m.group(1)], template).encode('utf-8')


def bootstrap_head(bootstrap_css):
    return BOOTSTRAP_LINK if bootstrap_css else bootstrap.FALLBACK_CSS


# Description always; the social-preview tags need an absolute URL, so they are
# emitted only for a published site with config.SITE_URL set.
def meta_head(public, canonical=''):
    description = labels.UI['description']
    tags = [f'<meta name="description" content="{html.escape(description)}">']
    if public and config.SITE_URL:
        url = config.SITE_URL.rstrip('/')
        tags.append(f'<link rel="canonical" href="{html.escape(url)}/{html.escape(canonical)}">')
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
    return fill(assets.read_text('index.html'), values)


# The same [text](url) markup labels.py uses, rendered for the static pages.
# Mirrors rich() in static/js/dom.js: everything is escaped, and the only markup
# emitted is an anchor built here.
_LINK = re.compile(r'\[([^\]]+)\]\(([^()]*(?:\([^()]*\)[^()]*)*)\)')


def rich_text(text):
    out, at = [], 0
    for found in _LINK.finditer(text):
        out.append(html.escape(text[at:found.start()]))
        href, label = found.group(2), html.escape(found.group(1))
        out.append(f'<a href="{html.escape(href)}" rel="noopener">{label}</a>'
                   if href.startswith(('http://', 'https://')) else label)
        at = found.end()
    out.append(html.escape(text[at:]))
    return ''.join(out)


# The 404 body. Static text, no data and no scripts, so it stays valid however
# old the bundle around it gets.
def render_404():
    values = {
        'TITLE': html.escape(f"{labels.UI['not_found_title']} - {config.SITE_NAME}"),
        'BRAND': html.escape(config.SITE_NAME),
        'MESSAGE': html.escape(labels.UI['not_found']),
        'LINK': html.escape(labels.UI['not_found_link']),
    }
    return fill(assets.read_text('404.html'), values)


# The about page: who runs this, what it does and does not hold, and who owns
# what. Static text and no scripts, like the 404, so it keeps working when the
# app around it does not.
def render_about():
    body = '\n'.join(
        f'  <h2>{html.escape(heading)}</h2>\n  <p>{rich_text(text)}</p>'
        for heading, text in labels.ABOUT)
    links = '\n'.join(
        f'    <li><a href="{html.escape(href)}" rel="noopener">{html.escape(text)}</a></li>'
        for text, href in labels.FOOTER_LINKS)
    values = {
        'TITLE': html.escape(f"{labels.UI['about']} - {config.SITE_NAME}"),
        'META': meta_head(public=True, canonical='about.html'),
        'BRAND': html.escape(f"{config.SITE_NAME} \u2013 {labels.UI['about']}"),
        'BACK': html.escape(labels.UI['about_back']),
        'BODY': body,
        'LINKS': links,
        'COPYRIGHT': rich_text(labels.UI['copyright']),
        'LICENSE_LABEL': html.escape(labels.UI['license_label']),
        'LICENSE_URL': html.escape(labels.UI['license_url']),
    }
    return fill(assets.read_text('about.html'), values)


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
