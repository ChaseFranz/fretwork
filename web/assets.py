"""
ASSETS - the page's static files, bundled and content-hashed, and the tables every server needs

Paths resolve from this file, not the working directory, so serve.py works
from anywhere. Required files are read at startup so a partial checkout fails
before the socket binds.

Everything under static/ and data/ is immutable: its name carries the first
eight hex digits of the SHA-1 of its bytes, so it is cached for a year and a
change is a new name. The entry pages (index.html and the document pages) are
no-cache, and graph/ keeps a week. cache_class() is the one place that rule
lives; deploy.py and the handler both read it from here.
"""

import hashlib
import pathlib

from web import bundler

STATIC_DIR = pathlib.Path(__file__).resolve().parent / 'static'

REQUIRED = ('index.html', '404.html', 'doc.html', 'song.html', 'js/main.js', 'css/app.css', 'favicon.svg')

CONTENT_TYPES = {
    '.html': 'text/html; charset=utf-8',
    '.txt': 'text/plain; charset=utf-8',
    '.js': 'text/javascript; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.svg': 'image/svg+xml',
    '.json': 'application/json',
    '.png': 'image/png',
    '.xml': 'application/xml',
}
CACHE_PAGE = 'no-cache'                                  # revalidate: rewritten in place
CACHE_IMMUTABLE = 'public, max-age=31536000, immutable'  # a hashed name never changes
CACHE_WEEK = 'public, max-age=604800'                    # a week: derived per chart or per song, changes with the library
CACHE_GRAPHS = CACHE_WEEK
IMMUTABLE_DIRS = ('static', 'data')
GRAPH_DIR = 'graph'
SONG_DIR = 'song'                                        # a page per song (section 16), the week class like graph/
GAME_DIR = 'game'                                        # a page per pack (section 22)
LIST_DIR = 'list'                                        # the ranked lists (section 22)
WEEK_DIRS = (GRAPH_DIR, SONG_DIR, GAME_DIR, LIST_DIR)


def content_type(name):
    return CONTENT_TYPES.get(pathlib.PurePosixPath(name).suffix.lower(), 'application/octet-stream')


def cache_class(name):
    name = str(name).lstrip('/')
    if any(name.startswith(d + '/') for d in IMMUTABLE_DIRS):
        return CACHE_IMMUTABLE
    if any(name.startswith(d + '/') for d in WEEK_DIRS):
        return CACHE_WEEK
    return CACHE_PAGE


def hash8(data):
    return hashlib.sha1(data).hexdigest()[:8]


def hashed(stem, suffix, data):
    return f'static/{stem}.{hash8(data)}{suffix}'


def read_text(name):
    return (STATIC_DIR / name).read_text(encoding='utf-8')


def check_present():
    missing = [n for n in REQUIRED if not (STATIC_DIR / n).is_file()]
    if missing:
        raise FileNotFoundError(
            f"missing static file(s) under {STATIC_DIR}: {', '.join(missing)}")


# {relative name: bytes} for everything under static/: the one JS bundle, the
# stylesheet, the favicon, and Bootstrap when it is available (None means the
# page inlines FALLBACK_CSS instead). Names never come from a request, so path
# traversal is impossible by construction. `names` maps each asset's role to
# its hashed name, for the templates.
def load_assets(bootstrap_css=None):
    check_present()
    files, names = {}, {}
    script = bundler.bundle(STATIC_DIR)
    names['script'] = hashed('app', '.js', script)
    files[names['script']] = script
    css = (STATIC_DIR / 'css' / 'app.css').read_bytes()
    names['style'] = hashed('app', '.css', css)
    files[names['style']] = css
    icon = (STATIC_DIR / 'favicon.svg').read_bytes()
    names['favicon'] = hashed('favicon', '.svg', icon)
    files[names['favicon']] = icon
    if bootstrap_css:
        names['bootstrap'] = hashed('bootstrap', '.css', bootstrap_css)
        files[names['bootstrap']] = bootstrap_css
    return files, names
