"""
PAGE - composes a header's page: its newest spreadsheet, rendered into index.html

One regex pass rather than chained replaces, so a value that happens to
contain __TOKEN__ text is never rewritten by a later substitution. URLs in the
page are relative, so it works at a domain root or under any sub-path.
"""

import collections
import datetime
import hashlib
import html
import json
import pathlib
import re

import config
from functions import instruments, labels, packs, timestamp
from web import assets, boot, bootstrap, frames, links as links_mod, markdown, methodology

_PLACEHOLDER = re.compile(r'__([A-Z][A-Z_]*)__')

# a chart whose graph reads well as a link preview
OG_IMAGE = 'graph/10145439XG.png'
OG_CODE = OG_IMAGE.rsplit('/', 1)[-1].rsplit('.', 1)[0]   # the one chart publish still renders as a PNG

# Crawlers are welcome on the page and not in the graph folder: it is 11,904
# curve files, none of them meaningful out of context, and all of them counted
# against the CDN's request allowance. The one graph used as the social preview
# stays fetchable. data/ is crawlable on purpose (section 21): the rows are
# there, and a crawler that renders the page needs them or it indexes an empty
# table; it is three files, fetched now and then.
ROBOTS = ('User-agent: *\n'
          'Allow: /\n'
          f'Allow: /{OG_IMAGE}\n'
          'Allow: /graph/*.png\n'        # the song pages' pictures (section 22); the curve files stay out
          'Disallow: /graph/\n')
SITEMAP = 'sitemap.xml'


# The robots file names the sitemap when the site has an address for it.
def robots_txt():
    if not config.SITE_URL:
        return ROBOTS
    return ROBOTS + f'Sitemap: {config.SITE_URL.rstrip("/")}/{SITEMAP}\n'

# What serve and publish both need: the spreadsheet path, the sheets, the row
# count, and every file the site is, {relative name: bytes}, graphs excepted.
# png_codes: the graphs publish draws as PNGs (section 22); page_dates: the
# per-page dates manifest this build stamped, for publish to save (section 24)
Built = collections.namedtuple('Built', 'xlsx_path sheets total files png_codes page_dates')

# The theme, decided before the first paint so a light-theme visitor never sees
# a dark flash: the header toggle's stored choice (fw.theme, static/js/theme.js)
# or the OS's, stamped on <html> as the attribute Bootstrap and app.css key on.
# In the head of every page, the document pages and the 404 included, since
# each carries its own two palettes; the template's data-bs-theme="dark" is
# what a visitor with no script gets.
THEME_SCRIPT = ('<script>(function(){var t=null;try{t=localStorage.getItem("fw.theme")}catch(e){}'
                'if(t!=="light"&&t!=="dark")t=matchMedia("(prefers-color-scheme: light)").matches?"light":"dark";'
                'document.documentElement.setAttribute("data-bs-theme",t)})()</script>')


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


# What the site is, in a title: the name, then the one line that carries the
# words someone searches for (section 21).
def site_title():
    return f"{config.SITE_NAME}: {labels.UI['site_title']}"


# A link from a document page into the app (section 24): by fragment, so a
# crawler sees one front page and not a query variant per chart; url.js reads
# the fragment as the query. Every page-side link into the app goes through here.
def app_link(param, value):
    return f'./#{param}={html.escape(str(value))}'


# The JSON-LD blocks a search feature reads (section 24). One <script> per page,
# holding a list when a page has more than one; '<' is escaped as boot.py does.
def ld_script(*blocks):
    blocks = [b for b in blocks if b]
    if not blocks:
        return ''
    doc = blocks[0] if len(blocks) == 1 else blocks
    return '<script type="application/ld+json">' + json.dumps(doc, ensure_ascii=False).replace('<', '\\u003c') + '</script>'


def _abs(name):
    base = config.SITE_URL.rstrip('/') if config.SITE_URL else ''
    return f'{base}/{name}' if base else name


def breadcrumb_ld(items):
    """items: [(name, page name or '' for the front page), ...], the page itself last."""
    return {'@context': 'https://schema.org', '@type': 'BreadcrumbList',
            'itemListElement': [{'@type': 'ListItem', 'position': i, 'name': name, 'item': _abs(page)}
                                for i, (name, page) in enumerate(items, 1)]}


def itemlist_ld(name, entries):
    """entries: [(name, page name), ...] in rank order."""
    return {'@context': 'https://schema.org', '@type': 'ItemList', 'name': name, 'numberOfItems': len(entries),
            'itemListOrder': 'https://schema.org/ItemListOrderDescending',
            'itemListElement': [{'@type': 'ListItem', 'position': i, 'name': n, 'url': _abs(page)}
                                for i, (n, page) in enumerate(entries, 1)]}


# The front page's WebSite block with its search: the app reads ?q= (url.js).
def website_ld():
    if not config.SITE_URL:
        return None
    base = config.SITE_URL.rstrip('/')
    return {'@context': 'https://schema.org', '@type': 'WebSite', 'name': config.SITE_NAME, 'url': base + '/',
            'description': labels.UI['description'],
            'potentialAction': {'@type': 'SearchAction', 'target': {'@type': 'EntryPoint', 'urlTemplate': base + '/?q={search_term_string}'},
                                'query-input': 'required name=search_term_string'}}


# The library as a dataset, which Google Dataset Search indexes: the counts,
# the engine it is based on and what it measures. No distribution: the sheet
# files are hashed and the next deploy deletes them; and no licence, since the
# engine's MIT covers its code and the charts are their charters'.
def dataset_ld(stats, when=None):
    if not config.SITE_URL:
        return None
    base = config.SITE_URL.rstrip('/')
    ld = {'@context': 'https://schema.org', '@type': 'Dataset',
          'name': f'{config.SITE_NAME}: {labels.UI["site_title"]}',
          'description': labels.UI['library_desc'].format(charts=f'{stats["rows"]:,}', songs=f'{stats["songs"]:,}', packs=stats.get('packs', 0)),
          'url': f'{base}/{LIBRARY_PAGE}', 'isAccessibleForFree': True,
          'isBasedOn': labels.ENGINE_REPO, 'creator': {'@type': 'Organization', 'name': config.SITE_NAME, 'url': base + '/'},
          'keywords': ['Guitar Hero', 'Rock Band', 'Clone Hero', 'chart difficulty', 'rhythm game'],
          'variableMeasured': [labels.label('D'), labels.label('CalcTier'), labels.label('RemapDiff'), labels.label('Pct')]}
    if when:
        ld['dateModified'] = f'{when:%Y-%m-%d}'
    return ld


# Description always; the social-preview tags need an absolute URL, so they are
# emitted only for a published site with config.SITE_URL set. A document page
# passes its own title and description (section 22), so each result and each
# preview says what that page is.
def meta_head(public, canonical='', title=None, description=None):
    description = description or labels.UI['description']
    tags = [f'<meta name="description" content="{html.escape(description)}">']
    if public and config.SITE_URL:
        url = config.SITE_URL.rstrip('/')
        tags.append(f'<link rel="canonical" href="{html.escape(url)}/{html.escape(canonical)}">')
        for prop, content in (('og:type', 'website'), ('og:url', f'{url}/{canonical}' if canonical else url),
                              ('og:site_name', config.SITE_NAME),
                              ('og:title', title or site_title()), ('og:description', description),
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


def render_page(title, source, names, boot_json, public=False, linked=False, static_html=''):
    values = {
        'TITLE': html.escape(title),
        'BRAND': html.escape(config.SITE_NAME),
        'SOURCE': strapline(source, linked),
        'META': meta_head(public) + ('\n' + ld_script(website_ld()) if public else ''),
        'STATIC': static_html,
        'THEME': THEME_SCRIPT,
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


# A same-site document page (about.html, methodology.html#calctier-calibration)
# gets a plain same-tab anchor; the pattern is a bare page name so a string
# that ever came from data could not smuggle javascript: or a path.
_PAGE = re.compile(r'[a-z0-9-]+\.html(#[a-z0-9-]+)?')


def rich_text(text):
    out, at = [], 0
    for found in _LINK.finditer(text):
        out.append(html.escape(text[at:found.start()]))
        href, label = found.group(2), html.escape(found.group(1))
        if href.startswith(('http://', 'https://')):
            out.append(f'<a href="{html.escape(href)}" rel="noopener">{label}</a>')
        elif _PAGE.fullmatch(href):
            out.append(f'<a href="{html.escape(href)}">{label}</a>')
        else:
            out.append(label)
        at = found.end()
    out.append(html.escape(text[at:]))
    return ''.join(out)


# The 404 body. Static text, no data and no script but the theme's, so it stays
# valid however old the bundle around it gets.
def render_404(names):
    values = {
        'FAVICON': names['favicon'],
        'TITLE': html.escape(f"{labels.UI['not_found_title']} - {config.SITE_NAME}"),
        'THEME': THEME_SCRIPT,
        'BRAND': html.escape(config.SITE_NAME),
        'MESSAGE': html.escape(labels.UI['not_found']),
        'LINK': html.escape(labels.UI['not_found_link']),
    }
    return fill(assets.read_text('404.html'), values)


# The document pages: about and the changelog. One template, static text and
# no script but the theme's, like the 404, so they keep working when the app
# around them does not. The link list leads with the site's other document
# pages. page_title is the <title> and og:title when the heading is not the
# words a search carries; description the page's own; a page under a folder
# (game/, list/) gets <base href="../"> so its relative links resolve from the
# root, and must then carry no fragment links (a base breaks them).
def render_doc(name, title, body, names, page_title=None, description=None, ld=None, more=''):
    others = [(labels.UI[key], page) for page, key in labels.DOC_PAGES if page != name]
    links = '\n'.join(
        [f'    <li><a href="{html.escape(href)}">{html.escape(text)}</a></li>' for text, href in others] +
        [f'    <li><a href="{html.escape(href)}" rel="noopener">{html.escape(text)}</a></li>'
         for text, href in labels.FOOTER_LINKS])
    full = f"{page_title or title} - {config.SITE_NAME}"
    values = {
        'FAVICON': names['favicon'],
        'BASE': '<base href="../">' if '/' in name else '',
        'TITLE': html.escape(full),
        'META': meta_head(public=True, canonical=name, title=page_title or title, description=description) + ('\n' + ld if ld else ''),
        'THEME': THEME_SCRIPT,
        'SITE': html.escape(config.SITE_NAME),
        'HEADING': html.escape(page_title or title),
        'BACK': html.escape(labels.UI['about_back']),
        'BODY': body,
        'MORE': more,
        'LINKS': links,
        'COPYRIGHT': rich_text(labels.UI['copyright']),
        'LICENSE_LABEL': html.escape(labels.UI['license_label']),
        'LICENSE_URL': html.escape(labels.UI['license_url']),
    }
    return fill(assets.read_text('doc.html'), values)


# The engine's Methodology.md, rendered through the subset renderer with every
# heading one level down (the brand is the page's h1), after its tables have
# been checked against the formula modules. A table that cannot be read stops
# publish and serve here; a number that differs from the code is upstream's
# document lagging upstream's code (this fork edits neither), so it is printed
# and put on the page as a note under the source line, one sentence per
# drift, since the code is what scored the charts.
def render_methodology(names):
    blocks, drifts = methodology.load()
    for drift in drifts:
        print(f'  Methodology.md: {drift}')
    note = ''
    if drifts:
        items = ''.join(f'<li>{html.escape(methodology.plain(d))}.</li>' for d in drifts)
        note = f'<p class="drift">{rich_text(labels.METHODOLOGY_DRIFT)}</p>\n<ul class="drift">{items}</ul>\n'
    body = (f'<p class="source">{rich_text(labels.METHODOLOGY_SOURCE)}</p>\n{note}'
            f'<div class="md">\n{markdown.render(blocks, shift=1)}\n</div>')
    return render_doc('methodology.html', labels.UI['methodology'], body, names,
                      page_title=labels.UI['methodology_title'], description=labels.UI['methodology_desc'])


# Who runs this, what it does and does not hold, and who owns what.
def render_about(names):
    body = '\n'.join(
        f'  <h2>{html.escape(heading)}</h2>\n  <p>{rich_text(text)}</p>'
        for heading, text in labels.ABOUT)
    return render_doc('about.html', labels.UI['about'], body, names, description=labels.UI['about_desc'])


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
        href = f'./#f.Added={date.strftime(packs.DATE)}&amp;f.Level=Expert'
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
    return render_doc('changelog.html', labels.UI['changelog'], '\n'.join(parts), names,
                      page_title=labels.UI['changelog_title'], description=labels.UI['changelog_desc'])


# The changelog exists exactly when the page has a pack join to build it from.
def changelog_pages(resolved, sheets, names):
    if resolved is None:
        return {}
    return {'changelog.html': render_changelog(resolved, frames.codes_in(sheets), names)}


# --- a page per song (section 16) -----------------------------------------------------

SONG_DIR = assets.SONG_DIR
_KEY = re.compile(r'^[0-9a-f]{12}$')


def _text(v):
    return '' if v is None or (isinstance(v, float) and v != v) else str(v)


def _isnum(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v == v


# What a song's page and a shared link say, per song: the primary folder's
# title, artist and facts (the same folder song.folders picks on the page:
# official first, then Release, then title, then the code prefix), and every
# level of every part of that folder with D, the percentile and the code, the
# tier once per part. Keyed by SongKey.
def song_facts(sheets):
    levels = list(reversed(labels.VALUE_ORDER['Level']))
    types = list(labels.VALUE_ORDER.get('Type', ()))
    by_key = {}
    for sheet, df in sheets.items():
        if 'SongKey' not in df.columns or 'Code' not in df.columns:
            continue
        for r in df.to_dict('records'):
            key = r.get('SongKey')
            if isinstance(key, str) and _KEY.match(key):
                r['_sheet'] = sheet
                by_key.setdefault(key, []).append(r)
    facts = {}
    for key, rows in by_key.items():
        folders = {}
        for r in rows:
            folders.setdefault(str(r['Code'])[:8], []).append(r)

        def rank(item):
            prefix, rs = item
            first = rs[0]
            return (0 if str(first.get('Official')).lower() == 'true' else 1,
                    _text(first.get('Release')), _text(first.get('Song Title')), prefix)
        own = sorted(folders.items(), key=rank)[0][1]
        by_part = {}
        for r in own:
            by_part.setdefault(_text(r.get('Type')), []).append(r)
        parts = []
        for part in sorted(by_part, key=lambda t: (types.index(t) if t in types else len(types), t)):
            rs = by_part[part]
            tier = next((int(r['CalcTier']) for r in rs if _isnum(r.get('CalcTier'))), None)
            have = {}
            for r in rs:
                level = _text(r.get('Level'))
                if level in levels and level not in have:
                    have[level] = {'code': str(r['Code']), 'd': r['D'] if _isnum(r.get('D')) else None,
                                   'pct': int(r['Pct']) if _isnum(r.get('Pct')) else None, 'sheet': r['_sheet']}
            parts.append({'type': part, 'tier': tier, 'levels': have})
        main = own[0]
        year = main.get('Year')
        facts[key] = {'title': _text(main.get('Song Title')), 'artist': _text(main.get('Artist')),
                      'charter': _text(main.get('Charter')), 'release': _text(main.get('Release')),
                      'official': str(main.get('Official')).lower() == 'true',
                      'album': _text(main.get('Album')), 'genre': _text(main.get('Genre')),
                      'year': int(year) if _isnum(year) and int(year) > 0 else None,
                      'code': str(main['Code']), 'parts': parts}
    return facts


# The chart whose graph is the song's picture: the preview line's chart, the
# first part's Expert (else its highest level). None for a song with no chart.
def song_image_code(fact):
    levels = list(reversed(labels.VALUE_ORDER['Level']))
    for part in fact['parts']:
        for level in levels:
            if level in part['levels']:
                return part['levels'][level]['code']
    return None


# The packs as pages (section 22): a slug per registered pack from its name,
# made unique in registry order, and the folder each song's primary chart is
# in, so a song page can name its source and a source page can list its songs.
def slug(name):
    out = re.sub(r'[^a-z0-9]+', '-', str(name).casefold()).strip('-')
    return out or 'pack'


def pack_slugs(resolved):
    slugs, seen = {}, set()
    for pack in resolved.registry.packs:
        base = slug(pack.name)
        candidate, n = base, 2
        while candidate in seen:
            candidate, n = f'{base}-{n}', n + 1
        seen.add(candidate)
        slugs[pack.folder] = candidate
    return slugs


# Every Expert chart by the folder it is in, by song, by part: what a source page
# lists. A song shipped in two packs appears on both pages with each pack's own
# numbers (they are the same chart when the notes are).
def charts_by_folder(sheets, resolved):
    out = {}
    for df in sheets.values():
        need = ('Code', 'SongKey', 'Level', 'Type', 'D')
        if not all(c in df.columns for c in need):
            continue
        expert = df[df['Level'] == 'Expert']
        for r in expert.to_dict('records'):
            key = r.get('SongKey')
            folder = resolved.folder_by_code.get(str(r['Code']))
            if folder is None or not (isinstance(key, str) and _KEY.match(key)):
                continue
            song = out.setdefault(folder, {}).setdefault(key, {
                'title': _text(r.get('Song Title')), 'artist': _text(r.get('Artist')),
                'official': str(r.get('Official')).lower() == 'true', 'parts': {}})
            part = _text(r.get('Type'))
            if part in song['parts']:
                continue
            song['parts'][part] = {'code': str(r['Code']), 'd': r['D'] if _isnum(r.get('D')) else None,
                                   'pct': int(r['Pct']) if _isnum(r.get('Pct')) else None,
                                   'tier': int(r['CalcTier']) if _isnum(r.get('CalcTier')) else None,
                                   'sheet': next((n for n, f in sheets.items() if f is df), '')}
    return out


# One line per part for the preview: its Expert chart, else its highest level.
def share_lines(fact):
    levels = list(reversed(labels.VALUE_ORDER['Level']))
    lines = []
    for part in fact['parts']:
        level = next((l for l in levels if l in part['levels']), None)
        if level is None:
            continue
        chart = part['levels'][level]
        lines.append(share_line({'level': level, 'type': part['type'], 'd': chart['d'], 'tier': part['tier'], 'pct': chart['pct']}))
    return lines


def share_line(line):
    ui = labels.UI
    bits = [] if line['d'] is None else [ui['share_d'].format(d=f'{line["d"]:.2f}')]
    if line['tier'] is not None:
        bits.append(ui['share_tier'].format(tier=line['tier']))
    if line['pct'] is not None:
        bits.append(ui['share_pct'].format(pct=line['pct']))
    return ui['share_line'].format(level=line['level'], type=line['type'], facts=', '.join(bits) or labels.MISSING_TEXT)


# The tags a preview reads: the song as the title, the parts' lines as the
# description, the page's own address as canonical and og:url. No image: the
# site's one PNG is another song's graph.
def song_meta(key, title, description, image=None):
    tags = [f'<meta name="description" content="{html.escape(description)}">']
    if config.SITE_URL:
        base = config.SITE_URL.rstrip('/')
        url = f'{base}/{SONG_DIR}/{key}.html'
        tags.append(f'<link rel="canonical" href="{html.escape(url)}">')
        props = [('og:type', 'website'), ('og:url', url), ('og:site_name', config.SITE_NAME),
                 ('og:title', title), ('og:description', description)]
        if image:
            props.append(('og:image', f'{base}/{assets.GRAPH_DIR}/{image}.png'))
        for prop, content in props:
            tags.append(f'<meta property="{prop}" content="{html.escape(content)}">')
        tags.append('<meta name="twitter:card" content="summary_large_image">' if image else '<meta name="twitter:card" content="summary">')
    return '\n'.join(tags)


# One page per song (sections 16 and 21): the tags a shared link previews
# with (song_meta), the song as a page a search engine can read (every level
# of every part in a table, the facts, a note on what the numbers are, a
# MusicRecording block), and a forward to the app only when the URL carries a
# query, which is what Copy link produces (song/<key>.html?code=A&vs=B opens
# that comparison); a bare URL, the sitemap's and the songs index's, renders.
# <base href="../"> makes every relative URL the site root's, so the favicon,
# the note's page links and the forward resolve as they do on the other
# document pages. Self-contained like those (its own two palettes, the theme
# script). The template carries no comment of its own, since it goes out
# 1,748 times.
def song_table(fact):
    ui = labels.UI
    levels = list(reversed(labels.VALUE_ORDER['Level']))
    head = ''.join(f'<th>{html.escape(l)}</th>' for l in levels)
    rows = []
    for part in fact['parts']:
        tier = '' if part['tier'] is None else f' <span class="tier">{html.escape(ui["song_tier"].format(n=part["tier"]))}</span>'
        cells = []
        for level in levels:
            chart = part['levels'].get(level)
            if chart is None or chart['d'] is None:
                cells.append(f'<td class="none">{labels.MISSING_TEXT}</td>')
                continue
            pct = '' if chart['pct'] is None else f'<small>{chart["pct"]}%</small>'
            cells.append(f'<td><a href="{app_link("code", chart["code"])}">{chart["d"]:.2f}</a>{pct}</td>')
        rows.append(f'    <tr><td>{html.escape(part["type"])}{tier}</td>{"".join(cells)}</tr>')
    return ('  <div class="tbl"><table>\n    <thead><tr><th>' + html.escape(labels.label('Type')) + '</th>' + head + '</tr></thead>\n'
            '    <tbody>\n' + '\n'.join(rows) + '\n    </tbody>\n  </table></div>')


def song_ld(key, fact, image=None, game=None):
    base = config.SITE_URL.rstrip('/') if config.SITE_URL else ''
    ld = {'@context': 'https://schema.org', '@type': 'MusicRecording', 'name': fact['title'],
          'url': f'{base}/{SONG_DIR}/{key}.html' if base else f'{SONG_DIR}/{key}.html',
          'description': '; '.join(share_lines(fact))}
    if image:
        ld['image'] = f'{base}/{assets.GRAPH_DIR}/{image}.png' if base else f'{assets.GRAPH_DIR}/{image}.png'
    if fact['artist']:
        ld['byArtist'] = {'@type': 'MusicGroup', 'name': fact['artist']}
    if fact['album']:
        ld['inAlbum'] = {'@type': 'MusicAlbum', 'name': fact['album']}
    crumbs = [(labels.UI['breadcrumb_home'], '')]
    if game:
        crumbs.append((game['name'], f'{GAME_DIR}/{game["slug"]}.html'))
    crumbs.append((fact['title'], f'{SONG_DIR}/{key}.html'))
    return json.dumps([ld, breadcrumb_ld(crumbs)], ensure_ascii=False).replace('<', '\\u003c')


# The source a song page names in its title (section 24): the release it was
# matched to (a game or a game's DLC), or Clone Hero for a custom, which is
# the word people type.
def song_source_name(fact):
    return fact['release'] if fact['official'] and fact['release'] else labels.UI['song_custom_source']


# The description a result shows (section 24): the question, then whole parts
# while they fit DESCRIPTION_MOST characters, the first part always, so the
# text a search engine cuts is never cut mid-list.
DESCRIPTION_MOST = 155


def song_description(lead, lines):
    out = lead
    for k, line in enumerate(lines):
        more = ('; ' if k else ' ') + line
        if k and len(out + more) > DESCRIPTION_MOST:
            break
        out += more
    return out.strip()


# The line under a song page's heading: the source, and the pack when the
# pack is not the source itself (a DLC pack under a game's release name).
def song_where(fact, game):
    ui = labels.UI
    pack = game['name'] if game else ''
    if fact['official'] and fact['release']:
        if pack and pack != fact['release']:
            return ui['song_where'].format(source=fact['release'], pack=pack)
        return ui['song_where_source'].format(source=fact['release'])
    return ui['song_where_custom'].format(pack=pack) if pack else ui['song_where_custom_only']


# The song in words (section 22): one sentence per part, the numbers the
# table shows read out, so the page says something a search can match.
def song_sentences(fact):
    ui = labels.UI
    levels = list(reversed(labels.VALUE_ORDER['Level']))
    out = []
    for part in fact['parts']:
        level = next((l for l in levels if l in part['levels']), None)
        if level is None:
            continue
        chart = part['levels'][level]
        if chart['d'] is None:
            continue
        sheet = chart.get('sheet') or ''
        if part['tier'] is not None and chart['pct'] is not None:
            out.append(ui['song_sentence'].format(level=level, type=part['type'], d=f'{chart["d"]:.2f}', tier=part['tier'], pct=chart['pct'], sheet=sheet))
        elif chart['pct'] is not None:
            out.append(ui['song_sentence_pct'].format(level=level, type=part['type'], d=f'{chart["d"]:.2f}', pct=chart['pct'], sheet=sheet))
        elif part['tier'] is not None:
            out.append(ui['song_sentence_tier'].format(level=level, type=part['type'], d=f'{chart["d"]:.2f}', tier=part['tier']))
        else:
            out.append(ui['song_sentence_d'].format(level=level, type=part['type'], d=f'{chart["d"]:.2f}'))
    return out


# `disambiguate` adds the pack to a custom's title when another song page
# carries the same song and artist (the same custom in two packs).
def render_song_page(key, fact, names, game=None, disambiguate=False):
    ui = labels.UI
    by = f'{fact["title"]} by {fact["artist"]}' if fact['artist'] else fact['title']
    game_name = song_source_name(fact)
    if disambiguate and game and game['name'] != game_name:
        game_name = f'{game_name} ({game["name"]})'
    lines = share_lines(fact)
    lead = ui['song_desc_lead'].format(song=fact['title'], artist=fact['artist'] or labels.MISSING_TEXT, source=song_source_name(fact))
    kind = labels.VALUE_LABELS.get('Official', {}).get('true' if fact['official'] else 'false', '')
    facts = [v for v in (fact['charter'], fact['release'], kind, fact['album'],
                         str(fact['year']) if fact['year'] else '', fact['genre']) if v]
    image = song_image_code(fact)
    # the picture: the first part's Expert graph, drawn by publish as a PNG (Built.png_codes);
    # its alt names the lines of the chart's family, read from the code's instrument letter
    picture = ('' if image is None else
               f'<p class="pic"><a href="{app_link("code", image)}"><img src="graph/{html.escape(image)}.png" width="1920" height="840" loading="lazy" '
               f'alt="{html.escape(labels.t_graph_alt(by, image))}"></a></p>')
    # the source it came in, when the registry names one
    where = ''
    if game:
        # the anchor is built here: rich_text admits bare page names only, and this one is under game/
        before, _, after = ui['song_source'].partition('{source}')
        where = ('<p class="game">' + html.escape(before) +
                 f'<a href="{GAME_DIR}/{html.escape(game["slug"])}.html">{html.escape(game["name"])}</a>' + html.escape(after) + '</p>')
    values = {
        'TITLE': html.escape(ui['song_page_title'].format(song=by, source=game_name, site=config.SITE_NAME)),
        'FAVICON': names['favicon'],
        'META': song_meta(key, by, song_description(lead, lines), image),
        'THEME': THEME_SCRIPT,
        'LD': song_ld(key, fact, image, game),
        'BRAND': html.escape(config.SITE_NAME),
        'KEY': key,
        'HEADING': html.escape(by),
        'WHERE': html.escape(song_where(fact, game)),
        'FACTS': html.escape(' / '.join(facts)),
        'SENTENCES': ' '.join(html.escape(t) for t in song_sentences(fact)),
        'PICTURE': picture,
        'TABLE': song_table(fact),
        'GAME': where,
        'NOTE': rich_text(ui['song_note']),
        'OPEN': html.escape(ui['share_open'].format(site=config.SITE_NAME)),
    }
    return fill(assets.read_text('song.html'), values)


def render_song_pages(sheets, names, facts=None, resolved=None):
    if facts is None:
        facts = song_facts(sheets)
    games = {}
    if resolved is not None:
        slugs = pack_slugs(resolved)
        by_folder = resolved.registry.by_folder
        for key, fact in facts.items():
            folder = resolved.folder_by_code.get(fact['code'])
            if folder in slugs:
                games[key] = {'name': by_folder[folder].name, 'slug': slugs[folder]}
    # a custom in two packs shares a title with itself: the pack tells them apart
    seen = collections.Counter((f['title'].casefold(), f['artist'].casefold()) for f in facts.values())
    return {f'{SONG_DIR}/{key}.html': render_song_page(key, fact, names, games.get(key),
                                                       disambiguate=seen[(fact['title'].casefold(), fact['artist'].casefold())] > 1)
            for key, fact in facts.items()}


# Every song, A to Z by title, each a link to its page: the crawl path to the
# song pages and their internal links (section 21). Digits under "0-9", the
# rest under "#"; a title's leading "The " does not move it.
SONGS_PAGE = 'songs.html'


def _index_letter(title):
    t = title.casefold()
    for ch in t:
        if ch.isalpha():
            return ch.upper()
        if ch.isdigit():
            return '0-9'
        if not ch.isspace():
            return '#'
    return '#'


def render_songs_index(facts, names):
    ui = labels.UI
    entries = sorted(((fact['title'], fact['artist'], key) for key, fact in facts.items()),
                     key=lambda e: (e[0].casefold(), e[1].casefold()))
    groups = {}
    for title, artist, key in entries:
        groups.setdefault(_index_letter(title), []).append((title, artist, key))
    order = sorted(groups, key=lambda g: (g == '#', g != '0-9', g))
    parts = [f'  <p class="intro">{html.escape(ui["songs_intro"].format(n=f"{len(entries):,}"))}</p>',
             '  <p class="totals">' + ' '.join(f'<a href="#{html.escape(g if g != "#" else "other")}">{html.escape(g)}</a>' for g in order) + '</p>']
    for g in order:
        parts.append(f'  <h2 id="{html.escape(g if g != "#" else "other")}">{html.escape(g)}</h2>')
        items = ''.join(f'<li><a href="{SONG_DIR}/{key}.html">{html.escape(title)}</a>'
                        + (f' <span class="by">{html.escape(artist)}</span>' if artist else '') + '</li>'
                        for title, artist, key in groups[g])
        parts.append(f'  <ul class="songs">{items}</ul>')
    body = '<div class="lib">\n' + '\n'.join(parts) + '\n</div>'
    return render_doc(SONGS_PAGE, ui['songs'], body, names, page_title=ui['songs_title'], description=ui['songs_desc'].format(n=f'{len(entries):,}'))


# Every page a crawler may index: the charts page, the document pages, the
# song pages; lastmod is the spreadsheet's date when it has one.
# `dates` is {page name: 'YYYY-MM-DD'}, the day each page's bytes last moved
# (PageDates, section 24), so lastmod is selective; without it every page
# carries the spreadsheet's date, as serve does.
def sitemap_urls(files):
    urls = ['']
    urls += [name for name, _ in labels.DOC_PAGES if name in files]
    for folder in (GAME_DIR, LIST_DIR, SONG_DIR):
        urls += sorted(name for name in files if name.startswith(folder + '/'))
    return urls


def render_sitemap(files, lastmod=None, dates=None):
    base = config.SITE_URL.rstrip('/')
    fallback = f'{lastmod:%Y-%m-%d}' if lastmod else ''
    urls = sitemap_urls(files)

    def when(name):
        day = (dates or {}).get(name or 'index.html', fallback)
        return f'<lastmod>{day}</lastmod>' if day else ''
    body = ''.join(f'<url><loc>{html.escape(base + "/" + name)}</loc>{when(name)}</url>\n' for name in urls)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + body + '</urlset>\n').encode('utf-8')


def sheet_date(header, xlsx_path):
    try:
        return datetime.datetime.strptime(timestamp.ext_ts(xlsx_path, 'metrics', header), timestamp.TS_FORMAT).date()
    except (ValueError, TypeError):
        return None


# --- a page per source (the registry's packs: a game, a game's DLC or a custom pack;
# the folder is game/, named before the distinction) and the ranked lists (section 22) ---

GAME_DIR = assets.GAME_DIR
LIST_DIR = assets.LIST_DIR
LIST_MOST = 100


# A chart in a cell: D linking its graph, the percentile beneath; the dash for none.
def _chart_html(chart):
    if chart is None or chart['d'] is None:
        return labels.MISSING_TEXT
    pct = '' if chart['pct'] is None else f'<small>{chart["pct"]}%</small>'
    return f'<a href="{app_link("code", chart["code"])}">{chart["d"]:.2f}</a>{pct}'


# The block under a source or list page's table (section 24): every source page
# and every list, so a crawler that lands on one reaches all of them.
def more_html(resolved, list_keys):
    ui = labels.UI
    slugs = pack_slugs(resolved)
    games = ''.join(f'<li><a href="{GAME_DIR}/{slugs[p.folder]}.html">{html.escape(p.name)}</a></li>'
                    for p in resolved.registry.packs if p.folder in slugs)
    lists = ''.join(f'<li><a href="{LIST_DIR}/{list_slug(kind, sheet)}.html">{html.escape(list_short_title(kind, sheet))}</a></li>'
                    for kind, sheet in list_keys)
    return (f'<div class="more"><h2>{html.escape(ui["more_sources"])}</h2><ul>{games}</ul>'
            f'<h2>{html.escape(ui["more_lists"])}</h2><ul>{lists}</ul></div>')


def list_short_title(kind, sheet):
    key = {'hardest': 'list_short_hardest', 'hardest-customs': 'list_short_custom', 'easiest': 'list_short_easiest'}[kind]
    return labels.UI[key].format(sheet=sheet.lower())


def _kind_of(songs):
    official = sum(1 for s in songs.values() if s['official'])
    return _kind_label(official, len(songs) - official)


# The pack's songs ranked by their Expert guitar D (the parts of the Guitar
# sheet, Lead first in VALUE_ORDER), the other sheets' parts beside, one column
# each in sheet order (Bass, Keys, Drums, Vocals); songs with no guitar Expert
# follow, by their best other part. Each song links its page, each number the
# chart's graph.
GUITAR_SHEET = next(iter(instruments.SHEET_GROUPS))
OTHER_PARTS = [instruments.TYPE_LABELS[k] for sheet, keys in instruments.SHEET_GROUPS.items() if sheet != GUITAR_SHEET for k in keys]


def render_game_page(pack, slug_, songs, names, tally, more=''):
    ui = labels.UI
    types = list(labels.VALUE_ORDER.get('Type', ()))
    guitar_parts = [t for t in types if t not in OTHER_PARTS]

    def best(song, parts):
        charts = [song['parts'][t] for t in parts if t in song['parts'] and song['parts'][t]['d'] is not None]
        return max(charts, key=lambda c: c['d']) if charts else None
    ranked = []
    for key, song in songs.items():
        g = best(song, guitar_parts)
        other = best(song, OTHER_PARTS)
        ranked.append((0 if g else 1, -(g['d'] if g else (other['d'] if other else 0)), song['title'].casefold(), key, song, g))
    ranked.sort()
    head = [('#', 'r'), (labels.label('Song Title'), ''), (labels.label('Artist'), ''), (labels.label('D'), 'r'),
            (labels.label('CalcTier'), 'r'), *((part, 'r') for part in OTHER_PARTS)]
    rows = []
    for n, (_, _, _, key, song, g) in enumerate(ranked, 1):
        tier = labels.MISSING_TEXT if g is None or g['tier'] is None else str(g['tier'])
        rows.append([str(n), f'<a href="{SONG_DIR}/{key}.html">{html.escape(song["title"])}</a>', html.escape(song['artist']),
                     _chart_html(g), tier, *(_chart_html(song['parts'].get(part)) for part in OTHER_PARTS)])
    n_songs, n_charts = tally.get(pack.folder, (len(songs), 0))
    facts = ui['source_facts'].format(songs=_n(n_songs), charts=_n(n_charts), kind=_kind_of(songs).lower(), date=fmt_date(pack.added))
    parts = [f'  <p class="intro">{html.escape(ui["source_intro"].format(source=pack.name))}</p>',
             '  <p class="totals">' + html.escape(facts) + (f' <a href="{html.escape(pack.source)}" rel="noopener">{html.escape(ui["library_source"])}</a>' if pack.source else '') + '</p>',
             _table(head, rows)]
    if any(g is None for *_, g in ranked):
        parts.append(f'  <p class="note">{html.escape(ui["source_no_guitar"])}</p>')
    body = '<div class="lib">\n' + '\n'.join(parts) + '\n</div>'
    title = ui['source_title'].format(source=pack.name)
    name = f'{GAME_DIR}/{slug_}.html'
    ld = ld_script(itemlist_ld(title, [(song['title'], f'{SONG_DIR}/{key}.html') for _, _, _, key, song, _ in ranked]),
                   breadcrumb_ld([(ui['breadcrumb_home'], ''), (pack.name, name)]))
    return render_doc(name, pack.name, body, names, page_title=title, description=f'{title}: {facts}.', ld=ld, more=more)


def render_game_pages(sheets, resolved, names, list_keys=()):
    slugs = pack_slugs(resolved)
    by_folder = charts_by_folder(sheets, resolved)
    tally = packs.tally(resolved, frames.codes_in(sheets))
    more = more_html(resolved, list_keys)
    out = {}
    for pack in resolved.registry.packs:
        songs = by_folder.get(pack.folder)
        if not songs:
            continue
        out[f'{GAME_DIR}/{slugs[pack.folder]}.html'] = render_game_page(pack, slugs[pack.folder], songs, names, tally, more)
    return out


# The lists: per sheet, the hardest official songs, the hardest customs and
# the easiest official songs on Expert, one entry per song at its hardest (or
# easiest) part, LIST_MOST at most. The source column links the pack's page.
LISTS = (('hardest', True, False), ('hardest-customs', False, False), ('easiest', True, True))


def list_slug(kind, sheet):
    return f'{kind}-{slug(sheet)}'


# Every list's entries, keyed (kind, sheet), in rank order: [(key, (chart, song, folder))].
# The keys are the lists the site has, which the More blocks and the front page name.
def list_pools(sheets, resolved):
    by_folder = charts_by_folder(sheets, resolved)
    pools = {}
    for sheet in sheets:
        # every Expert chart on this sheet, by song, keeping each song's extreme
        entries = {}
        for folder, songs in by_folder.items():
            for key, song in songs.items():
                for chart in song['parts'].values():
                    if chart['sheet'] != sheet or chart['d'] is None:
                        continue
                    entries.setdefault(key, []).append((chart, song, folder))
        for kind, official, easiest in LISTS:
            pool = []
            for key, charts in entries.items():
                charts = [c for c in charts if c[1]['official'] == official]
                if not charts:
                    continue
                pool.append((key, (min if easiest else max)(charts, key=lambda c: c[0]['d'])))
            pool.sort(key=lambda e: (e[1][0]['d'], e[1][1]['title'].casefold()), reverse=not easiest)
            pool = pool[:LIST_MOST]
            if len(pool) >= LIST_LEAST:
                pools[(kind, sheet)] = pool
    return pools


LIST_PICTURES = 3
LIST_LEAST = 2      # "The 1 hardest ..." is not a list; a sheet with one song has no page (section 24)


def render_list_pages(sheets, resolved, names, facts=None, pools=None):
    ui = labels.UI
    slugs = pack_slugs(resolved)
    by_name = resolved.registry.by_folder
    pools = list_pools(sheets, resolved) if pools is None else pools
    more = more_html(resolved, list(pools))
    out = {}
    for (kind, sheet), pool in pools.items():
        official, easiest = next((o, e) for k, o, e in LISTS if k == kind)
        if True:
            title_key = 'list_easiest' if easiest else ('list_hardest' if official else 'list_hardest_custom')
            title = ui[title_key].format(n=len(pool), sheet=sheet.lower())
            intro = ui['list_intro_official' if official else 'list_intro_custom'].format(sheet=sheet.lower())
            head = [('#', 'r'), (labels.label('Song Title'), ''), (labels.label('Artist'), ''), (ui['list_source'], ''),
                    (labels.label('Type'), ''), (labels.label('D'), 'r'), (labels.label('CalcTier'), 'r')]
            rows = []
            for n, (key, (chart, song, folder)) in enumerate(pool, 1):
                game = (f'<a href="{GAME_DIR}/{slugs[folder]}.html">{html.escape(by_name[folder].name)}</a>'
                        if folder in slugs else html.escape(_text(by_name[folder].name) if folder in by_name else ''))
                part = next((t for t, c in song['parts'].items() if c is chart), '')
                tier = labels.MISSING_TEXT if chart['tier'] is None else str(chart['tier'])
                rows.append([str(n), f'<a href="{SONG_DIR}/{key}.html">{html.escape(song["title"])}</a>', html.escape(song['artist']),
                             game, html.escape(part), _chart_html(chart), tier])
            # the top entries' pictures (section 24): the song's own graph, the one publish draws
            pics = []
            for n, (key, (chart, song, folder)) in enumerate(pool[:LIST_PICTURES], 1):
                code = song_image_code(facts[key]) if facts and key in facts else None
                if code is None:
                    continue
                by = f'{song["title"]} by {song["artist"]}' if song['artist'] else song['title']
                pics.append(f'<a href="{SONG_DIR}/{key}.html"><img src="graph/{html.escape(code)}.png" width="1920" height="840" loading="lazy" '
                            f'alt="{html.escape(labels.t_graph_alt(by, code))}"><b>{n}. {html.escape(song["title"])}</b> {html.escape(song["artist"])}, D {chart["d"]:.2f}</a>')
            pictures = f'  <p class="pics">{"".join(pics)}</p>\n' if pics else ''
            body = ('<div class="lib">\n' + f'  <p class="intro">{html.escape(intro)}</p>\n' + f'  <p class="intro">{html.escape(ui["list_method"])}</p>\n'
                    + pictures + _table(head, rows) + '\n</div>')
            name = f'{LIST_DIR}/{list_slug(kind, sheet)}.html'
            ld = ld_script(itemlist_ld(title, [(song['title'], f'{SONG_DIR}/{key}.html') for key, (chart, song, folder) in pool]),
                           breadcrumb_ld([(ui['breadcrumb_home'], ''), (ui['library'], LIBRARY_PAGE), (title, name)]))
            out[name] = render_doc(name, title, body, names, description=f'{title}, by fretwork\u2019s difficulty D.', ld=ld, more=more)
    return out


# --- the library page (section 20) --------------------------------------------------

LIBRARY_PAGE = 'library.html'


def _n(v):
    return f'{v:,}'


def _table(head, rows):
    """One table: head is [(label, classes)], classes among 'r' (right) and 'nw' (no wrap); rows are cell HTML in that order."""
    attr = lambda cls: f' class="{cls}"' if cls else ''   # noqa: E731
    ths = ''.join(f'<th{attr(cls)}>{html.escape(label)}</th>' for label, cls in head)
    trs = '\n'.join('    <tr>' + ''.join(f'<td{attr(cls)}>{cell}</td>' for (_, cls), cell in zip(head, row)) + '</tr>'
                     for row in rows)
    return f'  <div class="tbl"><table>\n    <thead><tr>{ths}</tr></thead>\n    <tbody>\n{trs}\n    </tbody>\n  </table></div>'


# Official against custom per registered folder, at Expert, from the sheets'
# own Official column joined by code, so the packs block says what the rows say.
def pack_kinds(resolved, sheets):
    kinds = {}
    for df in sheets.values():
        if not all(c in df.columns for c in ('Code', 'Official', frames.PCT_WITHIN)):
            continue
        expert = df[df[frames.PCT_WITHIN] == 'Expert']
        for code, official in zip(expert['Code'], expert['Official']):
            folder = resolved.folder_by_code.get(str(code))
            if folder is None:
                continue
            have = kinds.setdefault(folder, [0, 0])
            have[0 if str(official).lower() == 'true' else 1] += 1
    return kinds


def _kind_label(official, custom):
    kinds = labels.VALUE_LABELS.get('Official', {})
    if official and not custom:
        return kinds.get('true', 'Official')
    if custom and not official:
        return kinds.get('false', 'Custom')
    return labels.UI['library_mixed'] if official or custom else labels.MISSING_TEXT


# What the library is, in numbers: charts per sheet and level (rows and
# distinct), the Expert charts per tier as bar tables, official against
# custom, the ten hardest per sheet, the packs. Every number comes from
# frames.counts over the sheets the page serves, and from the pack join, so
# the page and the table agree. Rendered into doc.html like the changelog:
# static text, no script but the theme's.
def render_library(resolved, sheets, names, ld=None):
    ui = labels.UI
    stats = frames.counts(sheets)
    levels = list(reversed(labels.VALUE_ORDER['Level']))
    registry = resolved.registry
    tally = packs.tally(resolved, frames.codes_in(sheets))
    parts = [f'  <p class="intro">{rich_text(ui["library_intro"])}</p>',
             '  <p class="totals">' + html.escape(ui['changelog_totals'].format(
                 packs=_n(len(registry.packs)), songs=_n(stats['songs']), charts=_n(stats['rows']))) + '</p>']

    # charts: rows and distinct per level, per sheet, with totals
    parts += [f'  <h2>{html.escape(ui["library_charts"])}</h2>',
              f'  <p class="note">{rich_text(ui["library_charts_note"])}</p>']
    head = [(ui['library_sheet'], 'nw')] + [(l, 'r') for l in levels] + [(ui['library_all'], 'r'), (ui['library_songs'], 'r')]
    rows, totals = [], {l: [0, 0] for l in levels}

    # the smaller number under a count is the distinct charts, which the note says
    def cell(n, distinct):
        if not n:
            return labels.MISSING_TEXT
        return _n(n) + ('' if distinct == n else '<br><small>' + _n(distinct) + '</small>')

    for sheet, st in stats['sheets'].items():
        row = [html.escape(sheet)]
        all_rows = all_distinct = 0
        for level in levels:
            n, distinct = st['levels'].get(level, (0, 0))
            totals[level][0] += n
            totals[level][1] += distinct
            all_rows += n
            all_distinct += distinct
            row.append(cell(n, distinct))
        row += [cell(all_rows, all_distinct), _n(st['songs'])]
        rows.append(row)
    if len(stats['sheets']) > 1:
        rows.append(['<strong>' + html.escape(ui['library_all']) + '</strong>']
                    + [cell(*totals[l]) for l in levels]
                    + [cell(sum(t[0] for t in totals.values()), sum(t[1] for t in totals.values())), _n(stats['songs'])])
    parts.append(_table(head, rows))

    # tiers: Expert charts per CalcTier, a bar per tier, per sheet
    parts += [f'  <h2>{html.escape(ui["library_tiers"])}</h2>',
              f'  <p class="note">{rich_text(ui["library_tiers_note"])}</p>']
    for sheet, st in stats['sheets'].items():
        if not st['tiers']:
            continue
        top = max(st['tiers'].values())
        parts.append(f'  <h3>{html.escape(sheet)}</h3>')
        parts.append(_table([(labels.label('CalcTier'), 'r'), ('', ''), (ui['library_charts'], 'r')],
                            [[_n(tier), f'<span class="bar" style="width:{max(0.5, 100 * n / top):.1f}%"></span>', _n(n)]
                             for tier, n in sorted(st['tiers'].items())]))

    # official against custom, at Expert
    parts += [f'  <h2>{html.escape(ui["library_official"])}</h2>',
              f'  <p class="note">{rich_text(ui["library_official_note"])}</p>']
    kinds = labels.VALUE_LABELS.get('Official', {})
    rows = []
    for sheet, st in stats['sheets'].items():
        official, custom = st['official']
        share = f'{100 * official // (official + custom)}%' if official + custom else labels.MISSING_TEXT
        rows.append([html.escape(sheet), _n(official), _n(custom), share])
    parts.append(_table([(ui['library_sheet'], 'nw'), (kinds.get('true', 'Official'), 'r'),
                         (kinds.get('false', 'Custom'), 'r'), (ui['library_share'], 'r')], rows))

    # the hardest: the ten highest D at Expert per sheet, each a link into the table
    parts += [f'  <h2>{html.escape(ui["library_hardest"])}</h2>',
              f'  <p class="note">{rich_text(ui["library_hardest_note"])}</p>']
    for sheet, st in stats['sheets'].items():
        if not st['hardest']:
            continue
        parts.append(f'  <h3>{html.escape(sheet)}</h3>')
        rows = []
        for rank, r in enumerate(st['hardest'], 1):
            # the title to the song's page (section 21), the number into the table on the chart
            title = (f'<a href="{SONG_DIR}/{html.escape(r["key"])}.html">{html.escape(r["title"])}</a>'
                     if r.get('key') and _KEY.match(r['key']) else html.escape(r['title']))
            d = f'<a href="{app_link("code", r["code"])}">{r["d"]:,.2f}</a>'
            tier = labels.MISSING_TEXT if r['tier'] is None else _n(r['tier'])
            rows.append([_n(rank), title, html.escape(r['artist']), html.escape(r['type']), d, tier])
        parts.append(_table([('#', 'r'), (labels.label('Song Title'), ''), (labels.label('Artist'), ''),
                             (labels.label('Type'), ''), (labels.label('D'), 'r'), (labels.label('CalcTier'), 'r')], rows))
        # the full lists (section 22)
        links = [f'<a href="{LIST_DIR}/{list_slug(kind, sheet)}.html">{html.escape(list_short_title(kind, sheet))}</a>'
                 for kind, key in (('hardest', 'list_hardest'), ('hardest-customs', 'list_hardest_custom'), ('easiest', 'list_easiest'))]
        parts.append('  <p class="note">' + ' <span class="sep">/</span> '.join(links) + '</p>')

    # the packs, in the registry's order
    parts += [f'  <h2>{html.escape(ui["library_packs"])}</h2>',
              f'  <p class="note">{rich_text(ui["library_packs_note"])}</p>']
    by_folder = pack_kinds(resolved, sheets)
    slugs = pack_slugs(resolved)
    rows = []
    for pack in registry.packs:
        songs, charts = tally[pack.folder]
        # the name to the pack's page (section 22), the date to the table on the Expert charts added with it
        name = f'<a href="{GAME_DIR}/{slugs[pack.folder]}.html">{html.escape(pack.name)}</a>'
        href = f'./#f.Added={pack.added.strftime(packs.DATE)}&amp;f.Level=Expert'
        date = f'<a href="{href}" title="{html.escape(ui["changelog_date_tip"])}">{html.escape(pack.added.strftime(packs.DATE))}</a>'
        source = (f'<a href="{html.escape(pack.source)}" rel="noopener">{html.escape(ui["library_source"])}</a>'
                  if pack.source else '')
        rows.append([name, date, _n(songs), _n(charts),
                     html.escape(_kind_label(*by_folder.get(pack.folder, (0, 0)))), source])
    parts.append(_table([(ui['library_pack'], ''), (labels.label('Added'), 'nw'), (ui['library_songs'], 'r'),
                         (ui['library_charts'], 'r'), (labels.label('Official'), ''), (ui['library_source'], '')], rows))
    body = '<div class="lib">\n' + '\n'.join(parts) + '\n</div>'
    return render_doc(LIBRARY_PAGE, ui['library'], body, names, page_title=ui['library_title'],
                      description=ui['library_desc'].format(charts=_n(stats['rows']), songs=_n(stats['songs']), packs=_n(len(registry.packs))), ld=ld)


# The library page exists exactly when the changelog does: both need the pack join.
def library_pages(resolved, sheets, names, manifest=None, when=None, stats=None):
    if resolved is None:
        return {}
    ld = ld_script(dataset_ld({**(stats or frames.counts(sheets)), 'packs': len(resolved.registry.packs)}, when))
    return {LIBRARY_PAGE: render_library(resolved, sheets, names, ld=ld)}


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


# The front page's guide (section 24): what the site is in the words people
# type, the hardest Expert charts per instrument linking their song pages,
# every game page, every list and the document pages, as a <details> block
# above the footer. Open in the HTML, so a crawler that does not run scripts,
# a reader mode and a visitor without scripts get a page; closed by the inline
# script right after it, before the first paint, so a visitor with scripts
# sees the app with one summary line under the table and can open it. The
# same content for everyone, and in the DOM Google renders: nothing is removed
# or hidden from one and shown to the other. Empty on serve without a pack
# join, where there are no such pages.
def static_section(sheets, resolved, stats, list_keys, facts, has_songs_index):
    ui = labels.UI
    parts = [f'<summary>{html.escape(ui["home_summary"])}</summary>', f'<h1>{html.escape(ui["home_h1"])}</h1>']
    intro = ui['home_intro'].format(charts=_n(stats['rows']), songs=_n(stats['songs']),
                                    packs=_n(len(resolved.registry.packs)) if resolved else '0', engine=labels.ENGINE_REPO)
    parts.append(f'<p>{rich_text(intro)}</p>')
    key_of_code = {}
    for key, fact in (facts or {}).items():
        for part in fact['parts']:
            for chart in part['levels'].values():
                key_of_code[chart['code']] = key
    for sheet, block in stats['sheets'].items():
        if not block['hardest']:
            continue
        rows = []
        for n, r in enumerate(block['hardest'], 1):
            key = key_of_code.get(r['code'])
            song = (f'<a href="{SONG_DIR}/{key}.html">{html.escape(r["title"])}</a>' if key else html.escape(r['title']))
            tier = labels.MISSING_TEXT if r['tier'] is None else str(r['tier'])
            rows.append(f'<tr><td class="r">{n}</td><td>{song}</td><td>{html.escape(r["artist"])}</td><td>{html.escape(r["type"])}</td>'
                        f'<td class="r">{r["d"]:,.2f}</td><td class="r">{tier}</td></tr>')
        parts.append(f'<h2>{html.escape(ui["home_hardest"].format(sheet=sheet))}</h2>'
                     f'<table><thead><tr><th class="r">#</th><th>{html.escape(labels.label("Song Title"))}</th><th>{html.escape(labels.label("Artist"))}</th>'
                     f'<th>{html.escape(labels.label("Type"))}</th><th class="r">{html.escape(labels.label("D"))}</th><th class="r">{html.escape(labels.label("CalcTier"))}</th></tr></thead>'
                     f'<tbody>{"".join(rows)}</tbody></table>')
    if resolved is not None:
        slugs = pack_slugs(resolved)
        games = ''.join(f'<li><a href="{GAME_DIR}/{slugs[p.folder]}.html">{html.escape(p.name)}</a></li>'
                        for p in resolved.registry.packs if p.folder in slugs)
        if games:
            parts.append(f'<h2>{html.escape(ui["home_sources"])}</h2><ul>{games}</ul>')
    lists = ''.join(f'<li><a href="{LIST_DIR}/{list_slug(kind, sheet)}.html">{html.escape(list_short_title(kind, sheet))}</a></li>'
                    for kind, sheet in list_keys)
    if lists:
        parts.append(f'<h2>{html.escape(ui["home_lists"])}</h2><ul>{lists}</ul>')
    docs = ''.join(f'<li><a href="{page}">{html.escape(ui[key])}</a></li>' for page, key in labels.DOC_PAGES
                   if page != SONGS_PAGE or has_songs_index)
    parts.append(f'<h2>{html.escape(ui["home_more"])}</h2><ul class="one">{docs}</ul>')
    return ('<details id="static" open>\n' + '\n'.join(parts) + '\n</details>\n'
            '<script>document.getElementById("static").open=false</script>')


# The day each page's bytes last moved (section 24), so the sitemap's lastmod
# is selective: publish keeps caches/<header>_pagedates.json, {name: [hash8,
# date]}, and a page keeps its date while its bytes are the same. A page that
# leaves the site leaves the manifest.
class PageDates:
    def __init__(self, previous=None):
        self.previous = dict(previous or {})

    @classmethod
    def load(cls, path):
        try:
            return cls(json.loads(pathlib.Path(path).read_text(encoding='utf-8')))
        except (OSError, ValueError):
            return cls()

    def stamp(self, files, today=None):
        today = f'{today or datetime.date.today():%Y-%m-%d}'
        out = {}
        for name in sitemap_urls(files):
            name = name or 'index.html'
            digest = hashlib.sha1(files[name]).hexdigest()[:8]
            before = self.previous.get(name)
            out[name] = [digest, before[1] if before and before[0] == digest else today]
        return out

    @staticmethod
    def save(path, stamped):
        path = pathlib.Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(stamped, sort_keys=True), encoding='utf-8')


def dates_of(stamped):
    return {name: day for name, (_, day) in stamped.items()}


# Where publish keeps the manifest between runs; serve reads it too, so the
# sitemap it serves is the one publish wrote, and never writes it.
def page_dates_path(header):
    return timestamp.output_dir('cache') / f'{header}_pagedates.json'


# What serve and publish both need: (xlsx_path, sheets, total rows, page body).
# A published page names no internal file: the title is just the site and the
# strapline is when the data was built. Serving locally keeps both, which is
# what tells you which library and which run you are looking at.
# `resolved` is packs.resolve()'s answer, or None when there is no cache to
# join: then the Added column is absent and the strapline is plain text. The
# page-build columns are appended in a fixed order: Added, Copies, Pct, then the
# link columns (Enchor, Leaderboard) for the links the registry knows.
def build(header, xlsx_path, bootstrap_css, public=False, resolved=None, links_path=None, page_dates=None, indexnow_key=None):
    xlsx_path, sheets = frames.load_frames(header, xlsx_path)
    if any(frames.slug(name) == links_mod.SLUG for name in sheets):
        raise ValueError(f'a sheet slugs to {links_mod.SLUG!r}, the name of the links file under data/')
    if resolved is not None:
        sheets = frames.with_added(sheets, resolved.added_by_code)
    # the page-build columns, in this order: Added, Copies, Pct, the link columns
    sheets = {name: frames.add_copies(df) for name, df in sheets.items()}
    frames.add_percentiles(sheets, distinct=frames.COPY_KEY)
    # where each song is published and its leaderboard, from the offline registry, when there is one
    registry = links_mod.load_registry(header, links_path)
    linked = links_mod.songs_with_links(registry) if registry else {}
    sheets = frames.with_links(sheets, links_mod.link_columns(linked))
    total = sum(len(df) for df in sheets.values())
    if public:
        title, source = site_title(), public_source(header, xlsx_path, total)
    else:
        title = f"{config.SITE_NAME} - {header}"
        source = f"{xlsx_path.name}  -  {total} rows  -  {', '.join(sheets)}"
    files, names = assets.load_assets(bootstrap_css)
    data_files, manifest = frames.sheet_files(sheets)
    files.update(data_files)
    links_file = None
    published = links_mod.publish_songs(linked)
    if published is not None:
        links_file = links_mod.file_name(published)
        files[links_file] = published
    when = sheet_date(header, xlsx_path)
    files['404.html'] = render_404(names)
    files['about.html'] = render_about(names)
    files['methodology.html'] = render_methodology(names)
    files.update(changelog_pages(resolved, sheets, names))
    stats = frames.counts(sheets)
    files.update(library_pages(resolved, sheets, names, manifest, when, stats))
    facts = song_facts(sheets)
    files.update(render_song_pages(sheets, names, facts, resolved))
    if facts:
        files[SONGS_PAGE] = render_songs_index(facts, names)
    pools = list_pools(sheets, resolved) if resolved is not None else {}
    if resolved is not None:
        files.update(render_game_pages(sheets, resolved, names, list(pools)))
        files.update(render_list_pages(sheets, resolved, names, facts, pools))
    # the graphs publish draws as PNGs: the social preview and each song page's picture (section 22)
    png_codes = list(dict.fromkeys([OG_CODE] + [c for c in (song_image_code(f) for f in facts.values()) if c]))
    files['robots.txt'] = robots_txt().encode('utf-8')
    if indexnow_key:
        files[f'{indexnow_key}.txt'] = indexnow_key.encode('ascii')
    # the document pages first, so the footer lists only the ones this site has
    # (a serve with no cache has no changelog and no library page)
    doc_pages = [pair for pair in labels.DOC_PAGES if pair[0] in files]
    files['index.html'] = render_page(title, source, names,
                                      boot.boot_json(manifest, sheet_of_code(sheets), links_file, doc_pages,
                                                     site_url=config.SITE_URL if public else None),
                                      public, linked=resolved is not None,
                                      static_html=static_section(sheets, resolved, stats, list(pools), facts, SONGS_PAGE in files) if public else '')
    # the dates a page's bytes last moved, then the sitemap that carries them; the
    # sitemap and the key file are not pages, so they are stamped by neither
    stamped = page_dates.stamp(files) if page_dates is not None else None
    if config.SITE_URL:
        files[SITEMAP] = render_sitemap(files, when, dates_of(stamped) if stamped else None)
    return Built(xlsx_path, sheets, total, files, png_codes, stamped)
