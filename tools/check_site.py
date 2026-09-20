#!/usr/bin/env python3
"""
CHECK_SITE - The live-site checks from README step 7, as one command.

Fifteen GET requests against a published fretladder bundle, wherever it is served:
the page and its strapline, compression, the about page, robots.txt, the social
preview image, the module script and stylesheets by their real names (read out
of the page, so a renamed asset needs no edit here), the 404 mapping, and the
shared-link form, the sheet files and the script's cache class, a song page, the
front page's guide as a crawler reads it, and the IndexNow key file when the bundle
holds one. One line per check, then a summary; the exit code is the number of
failures. Skips are not failures.

    python tools/check_site.py                                # https://fretladder.com
    python tools/check_site.py --site site/Local              # and the live strapline must match that bundle's
    python tools/check_site.py http://127.0.0.1:8000          # a local static server: some checks skip

Local mode is a BASE_URL starting http://. A plain file server neither
compresses, nor maps an unknown path to our 404 page, nor holds the fixture's
social-preview chart, so those checks print skip there instead of FAIL.

Stdlib only and no repo import, so it runs anywhere and a test can load it.
"""

import argparse
import json
import os
import re
import secrets
import sys
import time
import urllib.error
import urllib.request

DEFAULT_URL = 'https://fretladder.com'
TIMEOUT = 15
STRAPLINE = re.compile(r'Updated [0-9]+ [A-Z][a-z]+ [0-9]{4}  -  [0-9,]+ charts')
NOT_FOUND_MARK = 'class="code">404<'       # the marker in web/static/404.html


def fetch(url, headers=None):
    """(status, headers, body); an HTTP error is a status, a network error is (None, {}, b'')."""
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, {k.lower(): v for k, v in r.headers.items()}, r.read()
    except urllib.error.HTTPError as e:
        return e.code, {k.lower(): v for k, v in e.headers.items()}, e.read()
    except (urllib.error.URLError, OSError, TimeoutError):
        return None, {}, b''


# --- what the script reads out of the fetched page ---------------------------

def og_image(page):
    """The og:image path relative to the origin, or None."""
    m = re.search(r'<meta property="og:image" content="([^"]+)"', page)
    if not m:
        return None
    return re.sub(r'^https?://[^/]+/', '', m.group(1))


def assets(page):
    """(module script src, [stylesheet hrefs]) as written in the page."""
    script = re.search(r'<script type="module" src="([^"]+)"', page)
    styles = re.findall(r'<link rel="stylesheet" href="([^"]+)"', page)
    return (script.group(1) if script else None), styles


def strapline(page):
    m = STRAPLINE.search(page)
    return m.group(0) if m else None


# --- the run --------------------------------------------------------------------

class Report:
    def __init__(self):
        self.ok = self.skip = self.failed = 0

    def say(self, n, name, passed, detail='', skipped=False):
        if skipped:
            self.skip += 1
            print(f'skip #{n} {name} ({detail})')
        elif passed:
            self.ok += 1
            print(f'ok   #{n} {name}')
        else:
            self.failed += 1
            print(f'FAIL #{n} {name}: {detail}')


def run(base, site_strapline=None, want_strapline=None, key_file=None):
    base = base.rstrip('/')
    local = base.startswith('http://')
    rep = Report()

    # 1. the page and its strapline, uncompressed so the body is plain text
    status, headers, body = fetch(base + '/')
    page = body.decode('utf-8', 'replace')
    found = strapline(page)
    ctype = headers.get('content-type', '')
    detail = f'status {status}, type {ctype!r}, strapline {found!r}'
    passed = status == 200 and ctype.startswith('text/html') and found is not None
    for want in (want_strapline, site_strapline):
        if want and want not in page:
            passed, detail = False, f'strapline is {found!r}, wanted {want!r}'
    rep.say(1, 'page and strapline', passed, detail)

    # 2. compression; CloudFront may answer the first request after an invalidation plain
    if local:
        rep.say(2, 'compressed page', True, 'plain file server', skipped=True)
    else:
        enc = ''
        for attempt in range(2):
            s, h, _ = fetch(base + '/', {'Accept-Encoding': 'br, gzip'})
            enc = h.get('content-encoding', '')
            if enc in ('br', 'gzip'):
                break
            time.sleep(2)
        rep.say(2, 'compressed page', enc in ('br', 'gzip'), f'content-encoding {enc!r}')

    # 3. the page names its data island, its social preview and its assets
    og = og_image(page)
    script, styles = assets(page)
    rep.say(3, 'boot island, og:image and asset names',
            'id="fw-boot"' in page and og is not None and script is not None and styles,
            f'fw-boot {"present" if "fw-boot" in page else "absent"}, og:image {og!r}, '
            f'script {script!r}, stylesheets {styles!r}')

    # 4. about page: one script (the theme's, in the head), at least one heading, canonical under https
    status, headers, body = fetch(base + '/about.html')
    about = body.decode('utf-8', 'replace')
    ctype = headers.get('content-type', '')
    passed = (status == 200 and ctype.startswith('text/html') and about.count('<script') == 1
              and 'localStorage.getItem("fw.theme")' in about and '<h2' in about)
    detail = f'status {status}, type {ctype!r}, {about.count("<script")} scripts, h2 {"present" if "<h2" in about else "absent"}'
    if not local and passed:
        canonical = f'<link rel="canonical" href="{base}/about.html">'
        passed = canonical in about
        if not passed:
            detail = f'no {canonical!r}'
    rep.say(4, 'about page', passed, detail)

    # 5. robots.txt keeps crawlers out of graph/ but lets the preview through
    status, _, body = fetch(base + '/robots.txt')
    robots = body.decode('utf-8', 'replace')
    rep.say(5, 'robots.txt', status == 200 and 'Disallow: /graph/' in robots
            and og is not None and f'Allow: /{og}' in robots,
            f'status {status}, og path {og!r}, body {robots.strip()!r}' if og else 'no og:image path')

    # 6. the social preview image
    if og is None:
        rep.say(6, 'og:image', False, 'no og:image path')
    else:
        status, headers, _ = fetch(f'{base}/{og}')
        ctype = headers.get('content-type', '')
        if local and status == 404:
            rep.say(6, 'og:image', True, 'not in this bundle', skipped=True)
        else:
            rep.say(6, 'og:image', status == 200 and ctype == 'image/png',
                    f'status {status}, type {ctype!r}')

    # 7. the module script must be served as JavaScript or the page is blank
    if script is None:
        rep.say(7, 'module script', False, 'no module script in the page')
    else:
        status, headers, _ = fetch(f'{base}/{script}')
        ctype = headers.get('content-type', '')
        rep.say(7, 'module script', status == 200
                and ctype.startswith(('text/javascript', 'application/javascript')),
                f'{script}: status {status}, type {ctype!r}')

    # 8. every stylesheet
    bad = None
    for href in styles:
        status, headers, _ = fetch(f'{base}/{href}')
        ctype = headers.get('content-type', '')
        if status != 200 or not ctype.startswith('text/css'):
            bad = f'{href}: status {status}, type {ctype!r}'
            break
    rep.say(8, 'stylesheets', bool(styles) and bad is None, bad or 'no stylesheet links in the page')

    # 9. an unknown path gets our 404 page
    status, _, body = fetch(f'{base}/no-such-page-{secrets.token_hex(4)}')
    if local:
        rep.say(9, 'unknown path is 404 (status only)', status == 404, f'status {status}')
    else:
        marked = NOT_FOUND_MARK in body.decode('utf-8', 'replace')
        rep.say(9, 'unknown path is our 404 page', status == 404 and marked,
                f'status {status}, 404 page marker {"present" if marked else "absent"}')

    # 10. the shared-link form of the page
    if og is None:
        rep.say(10, 'shared link', False, 'no og:image path')
    else:
        code = re.sub(r'^.*/|\.png$', '', og)
        status, _, _ = fetch(f'{base}/?code={code}')
        rep.say(10, 'shared link', status == 200, f'?code={code}: status {status}')

    # 11. every sheet file the manifest names is served as JSON, compressed under https
    island = re.search(r'<script type="application/json" id="fw-boot">(.*?)</script>', page, re.S)
    try:
        sheets = json.loads(island.group(1))['data'] if island else {}
        files = [v['file'] for v in sheets.values() if isinstance(v, dict) and 'file' in v]
    except (ValueError, AttributeError, TypeError):
        files = []
    if not files:
        rep.say(11, 'sheet files', True, 'rows are inline in this page', skipped=True)
    else:
        bad = None
        for f in files:
            s, h, _ = fetch(f'{base}/{f}', {} if local else {'Accept-Encoding': 'br, gzip'})
            ctype = h.get('content-type', '')
            enc = h.get('content-encoding', '')
            if s != 200 or not ctype.startswith('application/json') or (not local and enc not in ('br', 'gzip')):
                bad = f'{f}: status {s}, type {ctype!r}, content-encoding {enc!r}'
                break
        rep.say(11, 'sheet files', bad is None, bad or f'{len(files)} files')

    # 12. the module script is cached as immutable
    if script is None or local:
        rep.say(12, 'immutable script', True, 'no module script' if script is None else 'plain file server', skipped=True)
    else:
        _, h, _ = fetch(f'{base}/{script}')
        cc = h.get('cache-control', '')
        rep.say(12, 'immutable script', 'immutable' in cc, f'cache-control {cc!r}')

    # 13. a song page (sections 16 and 21): the first one the sitemap names is a page with the preview tags
    status, _, body = fetch(base + '/sitemap.xml')
    songs = re.findall(r'<loc>[^<]*/(song/[0-9a-f]{12}\.html)</loc>', body.decode('utf-8', 'replace')) if status == 200 else []
    if not songs:
        rep.say(13, 'song page', False, f'sitemap status {status}, no song page in it')
    else:
        status, headers, body = fetch(f'{base}/{songs[0]}')
        text = body.decode('utf-8', 'replace')
        ctype = headers.get('content-type', '')
        # since section 25 a song page links its neighbours, so a page with no song/ link is a ladder that rendered empty
        rep.say(13, 'song page', status == 200 and ctype.startswith('text/html') and 'og:title' in text and 'http-equiv="refresh"' not in text
                and 'href="song/' in text,
                f'{songs[0]}: status {status}, type {ctype!r}, og:title {"present" if "og:title" in text else "absent"}, '
                f'song links {text.count(chr(104) + "ref=" + chr(34) + "song/")}')

    # 14. the front page as a crawler reads it (section 24): the guide in the raw HTML with its one
    # h1 and links to the song, game and list pages, the WebSite block, and no query variant of the page linked
    guide = re.search(r'<details id="static" open>(.*?)</details>', page, re.S)
    words = guide.group(1) if guide else ''
    rep.say(14, 'front page guide for crawlers',
            guide is not None and page.count('<h1') == 1 and '<h1>' in words and 'href="song/' in words
            and 'href="game/' in words and 'href="list/' in words and '"@type": "WebSite"' in page and 'href="./?' not in page,
            f'guide {"present" if guide else "absent"}, h1 {page.count("<h1")}, song links {words.count(chr(104) + "ref=" + chr(34) + "song/")}, '
            f'WebSite block {"present" if chr(34) + "WebSite" + chr(34) in page else "absent"}')

    # 15. the IndexNow key file, when the bundle names one: served as text at the root, holding the key
    if key_file is None:
        rep.say(15, 'IndexNow key file', True, 'no key file in the bundle' if site_strapline else 'no --site given', skipped=True)
    else:
        status, headers, body = fetch(f'{base}/{key_file}')
        ctype = headers.get('content-type', '')
        rep.say(15, 'IndexNow key file', status == 200 and ctype.startswith('text/plain') and body.decode('ascii', 'replace').strip() == key_file[:-4],
                f'{key_file}: status {status}, type {ctype!r}, body {body[:40]!r}')

    print(f'{rep.ok + rep.skip + rep.failed} checks: {rep.ok} ok, {rep.skip} skip, {rep.failed} failed')
    return rep.failed


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[1])
    ap.add_argument('base_url', nargs='?', default=DEFAULT_URL, help=f'site to check (default {DEFAULT_URL})')
    group = ap.add_mutually_exclusive_group()
    group.add_argument('--site', help='a published bundle folder; the live strapline must match its index.html')
    group.add_argument('--strapline', help='text the page must contain')
    args = ap.parse_args()

    site_strapline = key_file = None
    if args.site:
        with open(f'{args.site.rstrip("/")}/index.html', encoding='utf-8') as f:
            site_strapline = strapline(f.read())
        if site_strapline is None:
            sys.exit(f'no strapline found in {args.site}/index.html')
        # the IndexNow key file publish wrote, if any: a 32-hex .txt at the bundle's root
        keys = [n for n in os.listdir(args.site) if re.fullmatch(r'[0-9a-f]{32}\.txt', n)]
        key_file = keys[0] if keys else None
    sys.exit(run(args.base_url, site_strapline, args.strapline, key_file))


if __name__ == '__main__':
    main()
