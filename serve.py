"""
SERVE - browse a metrics spreadsheet in a browser instead of Excel

Loads the newest metrics .xlsx for a header and serves it as a sortable,
filterable table on localhost. Clicking a row renders that song's graph on
demand - same PNG render.py produces, written to RENDER_DIR and cached in
memory for the life of the process.

    python serve.py
    python serve.py --header FullTest --port 8080
    python serve.py --xlsx metrics/Local_metrics_09072026-1022.xlsx

Stdlib http.server - no web framework, nothing added to requirements.txt.
Binds 127.0.0.1 only. WSL2 forwards localhost, so the URL opens in a Windows
browser as-is.

Bootstrap 5.3 supplies the CSS. It is downloaded once into CACHE_DIR and then
served same-origin from /bootstrap.css, so the page has no CDN dependency at
view time and keeps working offline after the first run. --no-bootstrap skips
it and falls back to the built-in styles.

Reads the spreadsheet, not the cache, for the table - run analyze.py first. The
cache is loaded at startup when there is one, for the pack join (the Added
column and the changelog); a graph click reuses it. Without a cache the page
still serves, without those two.

Serves exactly the four pages publish.py writes (index.html, about.html,
404.html, robots.txt); an unknown path gets the 404 page with status 404.

The page itself lives in web/ - see web/static/ for its markup and scripts.
"""

import argparse

import config
from functions import packs
from web import banner, bootstrap, page
from web.graph import GraphRenderer
from web.server import MetricsServer


# The pack join needs the cache, so serve loads it at startup when there is
# one (0.2 s; a graph click reuses it). Without a cache the page serves with no
# Added column and no changelog. Unlike publish, an unregistered or missing
# folder only warns: serve is for looking at any header's library.
def resolve_packs(renderer, packs_path):
    try:
        cache = renderer.cache()
    except FileNotFoundError:
        return None, f"packs: no cache for {renderer.header}, Added column and changelog off"
    try:
        resolved = packs.resolve(cache, packs.load(packs_path))
    except (FileNotFoundError, packs.PacksError) as exc:
        return None, f"packs: {exc}; Added column and changelog off"
    warning = packs.report(resolved)
    return resolved, (warning or f"packs: {len(resolved.registry.packs)} registered from {resolved.registry.path.name}")


def serve(header=None, xlsx_path=None, cache_path=None, port=8000, out_dir=None,
          use_bootstrap=True, packs_path=None):
    header = header or config.HEADER
    bootstrap_css = bootstrap.ensure_bootstrap(use_bootstrap)
    renderer = GraphRenderer(header, cache_path, out_dir)
    resolved, packs_line = resolve_packs(renderer, packs_path or packs.PACKS_FILE)

    built = page.build(header, xlsx_path, bootstrap_css, resolved=resolved, page_dates=page.PageDates.load(page.page_dates_path(header)))
    httpd = MetricsServer(port, {'/' + name: data for name, data in built.files.items()}, renderer)

    with httpd:
        banner.print_startup(built.xlsx_path, built.sheets, built.total, bootstrap_css, port, packs_line)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            banner.print_stopped()


def main():
    parser = argparse.ArgumentParser(description="Serve a metrics spreadsheet as a local web page.")
    parser.add_argument('--header', default=None, help="run identifier to look up (default: config.HEADER)")
    parser.add_argument('--xlsx', default=None, help="explicit metrics .xlsx (overrides header lookup)")
    parser.add_argument('--cache', default=None, help="explicit cache path, used for on-demand graphs")
    parser.add_argument('--out-dir', default=None, help="PNG output directory for rendered graphs")
    parser.add_argument('--port', type=int, default=8000, help="localhost port (default 8000)")
    parser.add_argument('--no-bootstrap', action='store_true',
                        help="skip the Bootstrap fetch and use the built-in styles")
    parser.add_argument('--packs', default=None,
                        help=f"pack registry to join (default: {packs.PACKS_FILE.name} in the repo root)")
    args = parser.parse_args()

    serve(header=args.header, xlsx_path=args.xlsx, cache_path=args.cache,
          port=args.port, out_dir=args.out_dir, use_bootstrap=not args.no_bootstrap,
          packs_path=args.packs)


if __name__ == '__main__':
    main()
