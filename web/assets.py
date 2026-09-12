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

REQUIRED = ('index.html', '404.html', 'doc.html', 'js/main.js', 'css/app.css', 'favicon.svg')

CONTENT_TYPES = {
    '.html': 'text/html; charset=utf-8',
    '.txt': 'text/plain; charset=utf-8',
    '.js': 'text/javascript; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.svg': 'image/svg+xml',
    '.json': 'application/json',
    '.png': 'image/png',
}
CACHE_PAGE = 'no-cache'                                  # revalidate: rewritten in place
CACHE_IMMUTABLE = 'public, max-age=31536000, immutable'  # a hashed name never changes
CACHE_GRAPHS = 'public, max-age=604800'                  # a week; a chart's files change when it does
IMMUTABLE_DIRS = ('static', 'data')
GRAPH_DIR = 'graph'


def content_type(name):
    return CONTENT_TYPES.get(pathlib.PurePosixPath(name).suffix.lower(), 'application/octet-stream')


def cache_class(name):
    name = str(name).lstrip('/')
    if any(name.startswith(d + '/') for d in IMMUTABLE_DIRS):
        return CACHE_IMMUTABLE
    if name.startswith(GRAPH_DIR + '/'):
        return CACHE_GRAPHS
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
