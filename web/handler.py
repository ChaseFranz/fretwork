"""
HANDLER - routes GET requests and writes responses

Dependencies arrive on self.server, the stdlib's own injection point, so this
class stays module-level and constructor-free.
"""

import http.server
import pathlib
import urllib.parse

HTML_TYPE = 'text/html; charset=utf-8'
TEXT_TYPE = 'text/plain; charset=utf-8'
CSS_TYPE = 'text/css; charset=utf-8'

GRAPH_PREFIX = '/graph/'
PAGE_PATHS = ('/', '/index.html')
PAGE_TYPES = {'.html': HTML_TYPE, '.txt': TEXT_TYPE}
NOT_FOUND = '/404.html'


class MetricsHandler(http.server.BaseHTTPRequestHandler):

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        pages = self.server.pages

        if path in PAGE_PATHS:
            return self._send(200, HTML_TYPE, pages['/index.html'])
        if path in pages:
            return self._send(200, PAGE_TYPES[pathlib.PurePosixPath(path).suffix], pages[path])
        if path == '/bootstrap.css':
            return self._send_bootstrap()
        if path in self.server.static:
            data, content_type = self.server.static[path]
            return self._send(200, content_type, data)
        if path.startswith(GRAPH_PREFIX):
            return self._send_graph(path)
        # the same 404 page S3 serves for an unknown key; a direct GET /404.html is 200 there too
        return self._send(404, HTML_TYPE, pages[NOT_FOUND])

    def _send_bootstrap(self):
        css = self.server.bootstrap_css
        if css is None:
            return self._send(404, TEXT_TYPE, b'bootstrap not cached')
        return self._send(200, CSS_TYPE, css, cache_seconds=86400)

    # isalnum() is the only guard the code needs: it rejects dots and slashes,
    # so a traversal attempt can never reach the renderer.
    def _send_graph(self, path):
        code = pathlib.PurePosixPath(path).stem
        if not code.isalnum():
            return self._send(400, TEXT_TYPE, b'bad code')
        try:
            data = self.server.graphs.png(code)
        except FileNotFoundError as exc:
            return self._send(503, TEXT_TYPE, str(exc).encode())
        if data is None:
            return self._send(404, TEXT_TYPE, b'no graph for that code')
        return self._send(200, 'image/png', data)

    # A viewer that navigates away mid-response is normal, not an error.
    def _send(self, status, content_type, data, cache_seconds=None):
        try:
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(data)))
            if cache_seconds:
                self.send_header('Cache-Control', f'max-age={cache_seconds}')
            self.end_headers()
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    # Keep the terminal quiet during browsing; only graph requests are worth a line.
    def log_message(self, fmt, *args):
        first = str(args[0]) if args else ''
        if GRAPH_PREFIX in first:
            super().log_message(fmt, *args)
