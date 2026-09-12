"""
SERVER - the HTTP server, carrying the handler's dependencies
"""

import http.server

from web.handler import MetricsHandler

BIND_HOST = '127.0.0.1'


class MetricsServer(http.server.ThreadingHTTPServer):
    """Threading server whose attributes are what MetricsHandler reads."""

    def __init__(self, port, files, graphs):
        self.files = files          # {'/index.html': bytes, ...}: every file the site is, graphs excepted
        self.graphs = graphs
        super().__init__((BIND_HOST, port), MetricsHandler)
