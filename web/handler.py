"""
HANDLER - routes GET requests and writes responses

Dependencies arrive on self.server, the stdlib's own injection point, so this
class stays module-level and constructor-free.
"""

import http.server
import pathlib
import urllib.parse

from web import assets

HTML_TYPE = assets.CONTENT_TYPES['.html']
TEXT_TYPE = assets.CONTENT_TYPES['.txt']

GRAPH_PREFIX = '/graph/'
PAGE_PATHS = ('/', '/index.html')
NOT_FOUND = '/404.html'
GRAPH_SUFFIXES = ('.png', '.json')


class MetricsHandler(http.server.BaseHTTPRequestHandler):

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        files = self.server.files

        if path in PAGE_PATHS:
            return self._send(200, HTML_TYPE, files['/index.html'], assets.CACHE_PAGE)
        if path in files:
            # the same bytes publish writes, with the cache class deploy gives them
            return self._send(200, assets.content_type(path), files[path], assets.cache_class(path))
        if path.startswith(GRAPH_PREFIX):
            return self._send_graph(path)
        # the same 404 page S3 serves for an unknown key; a direct GET /404.html is 200 there too
        return self._send(404, HTML_TYPE, files[NOT_FOUND], assets.CACHE_PAGE)

    # isalnum() is the only guard the code needs: it rejects dots and slashes,
    # so a traversal attempt can never reach the renderer. Two products per
    # code: the PNG, and the curve JSON the page draws from.
    def _send_graph(self, path):
        p = pathlib.PurePosixPath(path)
        code, suffix = p.stem, p.suffix
        if not code.isalnum() or suffix not in GRAPH_SUFFIXES:
            return self._send(400 if not code.isalnum() else 404, TEXT_TYPE, b'bad code' if not code.isalnum() else b'not found')
        try:
            data = self.server.graphs.png(code) if suffix == '.png' else self.server.graphs.curves(code)
        except FileNotFoundError as exc:
            return self._send(503, TEXT_TYPE, str(exc).encode())
        if data is None:
            return self._send(404, TEXT_TYPE, b'no graph for that code')
        return self._send(200, assets.content_type(path), data, assets.CACHE_WEEK)

    # A viewer that navigates away mid-response is normal, not an error.
    def _send(self, status, content_type, data, cache=None):
        try:
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(data)))
            if cache:
                self.send_header('Cache-Control', cache)
            self.end_headers()
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    # Keep the terminal quiet during browsing; only graph requests are worth a line.
    def log_message(self, fmt, *args):
        first = str(args[0]) if args else ''
        if GRAPH_PREFIX in first:
            super().log_message(fmt, *args)
