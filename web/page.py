"""
PAGE - composes a header's page: its newest spreadsheet, rendered into index.html

One regex pass rather than chained replaces, so a value that happens to
contain __TOKEN__ text is never rewritten by a later substitution. URLs in the
page are relative, so it works at a domain root or under any sub-path.
"""

import collections
import datetime
import html
import re

import config
from functions import instruments, labels, packs, timestamp
from web import assets, boot, bootstrap, frames

_PLACEHOLDER = re.compile(r'__([A-Z][A-Z_]*)__')

# a chart whose graph reads well as a link preview
OG_IMAGE = 'graph/10145439XG.png'
OG_CODE = OG_IMAGE.rsplit('/', 1)[-1].rsplit('.', 1)[0]   # the one chart publish still renders as a PNG

# Crawlers are welcome on the page and not in the graph folder: it is ~12,000
# PNGs and a couple of gigabytes, none of it meaningful out of context, and all
# of it counted against the CDN's request and transfer allowance. The one graph
# used as the social preview stays fetchable.
ROBOTS = ('User-agent: *\n'
          'Allow: /\n'
          f'Allow: /{OG_IMAGE}\n'
          'Disallow: /graph/\n'
          'Disallow: /data/\n')

# What serve and publish both need: the spreadsheet path, the sheets, the row
# count, and every file the site is, {relative name: bytes}, graphs excepted.
Built = collections.namedtuple('Built', 'xlsx_path sheets total files')


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


# The stylesheet links: Bootstrap by its hashed name, or the inline fallback,
# then the page's own sheet.
def styles_head(names):
    first = (f'<link rel="stylesheet" href="{names["bootstrap"]}">' if 'bootstrap' in names
             else bootstrap.FALLBACK_CSS)
    return f'{first}\n<link rel="stylesheet" href="{names["style"]}">'


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


# "7 September 2026": the strapline's date shape, shared with the changelog.
def fmt_date(d):
    return f"{d.day} {d:%B %Y}"


# "Updated 7 September 2026  -  4,634 charts", from the spreadsheet's own timestamp.
def public_source(header, xlsx_path, total):
    try:
        stamp = timestamp.ext_ts(xlsx_path, 'metrics', header)
        when = datetime.datetime.strptime(stamp, timestamp.TS_FORMAT)
    except (ValueError, TypeError):
        return labels.t_count(total)
    return f"{labels.UI['updated'].format(date=fmt_date(when))}  -  {labels.t_count(total)}"


# The strapline links to the changelog when there is one; a serve with no cache
# has no changelog, so its text stays plain rather than pointing at the 404 page.
def strapline(source, linked):
    text = html.escape(source)
    if not linked:
        return text
    return f'<a href="changelog.html" title="{html.escape(labels.UI["changelog_tip"])}">{text}</a>'


def render_page(title, source, names, boot_json, public=False, linked=False):
    values = {
        'TITLE': html.escape(title),
        'SOURCE': strapline(source, linked),
        'META': meta_head(public),
        'FAVICON': names['favicon'],
        'STYLES': styles_head(names),
        'SCRIPT': names['script'],
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
def render_404(names):
    values = {
        'FAVICON': names['favicon'],
        'TITLE': html.escape(f"{labels.UI['not_found_title']} - {config.SITE_NAME}"),
        'BRAND': html.escape(config.SITE_NAME),
        'MESSAGE': html.escape(labels.UI['not_found']),
        'LINK': html.escape(labels.UI['not_found_link']),
    }
    return fill(assets.read_text('404.html'), values)


# The document pages: about and the changelog. One template, static text and
# no scripts, like the 404, so they keep working when the app around them does
# not. The link list leads with the site's other document pages.
def render_doc(name, title, body, names):
    others = [(labels.UI[key], page) for page, key in labels.DOC_PAGES if page != name]
    links = '\n'.join(
        [f'    <li><a href="{html.escape(href)}">{html.escape(text)}</a></li>' for text, href in others] +
        [f'    <li><a href="{html.escape(href)}" rel="noopener">{html.escape(text)}</a></li>'
         for text, href in labels.FOOTER_LINKS])
    values = {
        'FAVICON': names['favicon'],
        'TITLE': html.escape(f"{title} - {config.SITE_NAME}"),
        'META': meta_head(public=True, canonical=name),
        'BRAND': html.escape(f"{config.SITE_NAME} \u2013 {title}"),
        'BACK': html.escape(labels.UI['about_back']),
        'BODY': body,
        'LINKS': links,
        'COPYRIGHT': rich_text(labels.UI['copyright']),
        'LICENSE_LABEL': html.escape(labels.UI['license_label']),
        'LICENSE_URL': html.escape(labels.UI['license_url']),
    }
    return fill(assets.read_text('doc.html'), values)


# Who runs this, what it does and does not hold, and who owns what.
def render_about(names):
    body = '\n'.join(
        f'  <h2>{html.escape(heading)}</h2>\n  <p>{rich_text(text)}</p>'
        for heading, text in labels.ABOUT)
    return render_doc('about.html', labels.UI['about'], body, names)


# Every pack newest first, grouped by date with the site's own changes, each
# date heading a link to the table filtered to that update (Expert only,
# official and custom, since a custom pack's update would otherwise show
# nothing). Counts come from the cache and the sheets, never from the file.
def render_changelog(resolved, codes, names):
    counts = packs.tally(resolved, codes)
    registry = resolved.registry
    by_date = {}
    for change in registry.changes:
        by_date.setdefault(change.date, [[], []])[0].append(change)
    for pack in registry.packs:
        by_date.setdefault(pack.added, [[], []])[1].append(pack)
    parts = [f'  <p class="intro">{rich_text(labels.UI["changelog_intro"])}</p>',
             '  <p class="totals">' + html.escape(labels.UI['changelog_totals'].format(
                 packs=f'{len(registry.packs):,}', songs=f'{sum(s for s, _ in counts.values()):,}',
                 charts=f'{sum(c for _, c in counts.values()):,}')) + '</p>']
    for date in sorted(by_date, reverse=True):
        changes, date_packs = by_date[date]
        href = f'./?f.Added={date.strftime(packs.DATE)}&amp;f.Level=Expert'
        parts.append(f'  <h2><a href="{href}" title="{html.escape(labels.UI["changelog_date_tip"])}">'
                     f'{html.escape(fmt_date(date))}</a></h2>')
        for change in changes:
            parts.append(f'  <p class="item">{rich_text(change.text)}</p>')
        for pack in sorted(date_packs, key=lambda p: p.name.lower()):
            songs, charts = counts[pack.folder]
            name = html.escape(pack.name)
            if pack.source:
                name = f'<a href="{html.escape(pack.source)}" rel="noopener">{name}</a>'
            item = f'<strong>{name}</strong>, ' + html.escape(
                labels.UI['pack_counts'].format(songs=f'{songs:,}', charts=f'{charts:,}')) + '.'
            if pack.notes:
                item += ' ' + rich_text(pack.notes)
            parts.append(f'  <p class="item">{item}</p>')
    return render_doc('changelog.html', labels.UI['changelog'], '\n'.join(parts), names)


# The changelog exists exactly when the page has a pack join to build it from.
def changelog_pages(resolved, sheets, names):
    if resolved is None:
        return {}
    return {'changelog.html': render_changelog(resolved, frames.codes_in(sheets), names)}


# Which sheet a code's instrument letter lands on, derived from the instrument
# tables and restricted to the sheets the workbook has, so ?code=...XB opens
# Bass with a filled heading rather than the default sheet with a blank one.
def sheet_of_code(sheets):
    out = {}
    for sheet, keys in instruments.SHEET_GROUPS.items():
        if sheet in sheets:
            for key in keys:
                out[instruments.CODE_SUFFIX[key]] = sheet
    return out


# What serve and publish both need: (xlsx_path, sheets, total rows, page body).
# A published page names no internal file: the title is just the site and the
# strapline is when the data was built. Serving locally keeps both, which is
# what tells you which library and which run you are looking at.
# `resolved` is packs.resolve()'s answer, or None when there is no cache to
# join: then the Added column is absent and the strapline is plain text. The
# page-build columns are appended in a fixed order: Added, Copies, then Pct.
def build(header, xlsx_path, bootstrap_css, public=False, resolved=None):
    xlsx_path, sheets = frames.load_frames(header, xlsx_path)
    if resolved is not None:
        sheets = frames.with_added(sheets, resolved.added_by_code)
    # the page-build columns, in this order: Added, Copies, Pct
    sheets = {name: frames.add_copies(df) for name, df in sheets.items()}
    frames.add_percentiles(sheets, distinct=frames.COPY_KEY)
    total = sum(len(df) for df in sheets.values())
    if public:
        title, source = config.SITE_NAME, public_source(header, xlsx_path, total)
    else:
        title = f"{config.SITE_NAME} - {header}"
        source = f"{xlsx_path.name}  -  {total} rows  -  {', '.join(sheets)}"
    files, names = assets.load_assets(bootstrap_css)
    data_files, manifest = frames.sheet_files(sheets)
    files.update(data_files)
    files['index.html'] = render_page(title, source, names, boot.boot_json(manifest, sheet_of_code(sheets)),
                                      public, linked=resolved is not None)
    files['404.html'] = render_404(names)
    files['about.html'] = render_about(names)
    files['robots.txt'] = ROBOTS.encode('utf-8')
    files.update(changelog_pages(resolved, sheets, names))
    return Built(xlsx_path, sheets, total, files)
