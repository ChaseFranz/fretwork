"""
PUBLISH - write the viewer as a static site, ready for S3 or any file host

The same page serve.py serves, written to SITE_DIR/<header>/: index.html with
the data baked in, the static assets, Bootstrap, and every chart's graph
pre-rendered under graph/<code>.png. Nothing server-side is needed to host the
result, and its URLs are relative, so it works at a domain root or a sub-path.

    python publish.py
    python publish.py --header Main --out-dir /srv/www/fretwork
    python publish.py --force            # re-render every graph

Re-publishing is incremental. Unchanged files are left alone, so an
`aws s3 sync` uploads only what moved. A chart whose notes, header numbers,
metadata, curve settings and render theme are unchanged skips its render, and
a chart that cannot be rendered keeps the graph an earlier publish made. Only
graphs a previous publish recorded are ever pruned. --force re-renders
everything, which a change to functions/plot.py or a matplotlib upgrade needs.

Reads the spreadsheet for the table and the cache for the graphs, so run
analyze.py first. Measured at about 0.12 s per chart: a 4,600-chart library
takes around ten minutes the first time and seconds after that.
"""

import argparse
import pathlib

import config
from functions import timestamp
from web import assets, banner, bootstrap, bundle, frames, page
from web.graph import GraphRenderer


# analyze pairs each spreadsheet with its cache by timestamp; say so if they differ
def check_pair(header, xlsx_path, cache_path):
    try:
        xlsx_ts = timestamp.ext_ts(xlsx_path, 'metrics', header)
        cache_ts = timestamp.ext_ts(cache_path, 'cache', header)
    except ValueError:
        return
    if xlsx_ts != cache_ts:
        print(f"Note: spreadsheet is from {xlsx_ts} but the cache is from {cache_ts}; "
              f"run analyze.py so the table and graphs come from the same build.")


def publish(header=None, xlsx_path=None, cache_path=None, out_dir=None,
            use_bootstrap=True, force=False):
    header = header or config.HEADER
    out_dir = pathlib.Path(out_dir).expanduser() if out_dir else pathlib.Path(config.SITE_DIR) / header

    renderer = GraphRenderer(header, cache_path)
    renderer.cache()   # a missing cache fails here, before anything is written
    bootstrap_css = bootstrap.ensure_bootstrap(use_bootstrap)
    xlsx_path, sheets, _total, body = page.build(header, xlsx_path, bootstrap_css, public=True)
    check_pair(header, xlsx_path, renderer.cache_path)

    print(f"\nPublishing {xlsx_path}")
    pages = {'index.html': body, '404.html': page.render_404(),
             'robots.txt': page.ROBOTS.encode('utf-8')}
    page_files, written = bundle.write_page(out_dir, pages, assets.load_static(), bootstrap_css)
    counts, graph_files = bundle.render_graphs(out_dir, frames.codes_in(sheets), renderer, force)
    banner.print_published(out_dir, page_files, written, counts, graph_files)


def main():
    parser = argparse.ArgumentParser(description="Write the metrics viewer as a static site.")
    parser.add_argument('--header', default=None, help="run identifier to look up (default: config.HEADER)")
    parser.add_argument('--xlsx', default=None, help="explicit metrics .xlsx (overrides header lookup)")
    parser.add_argument('--cache', default=None, help="explicit cache path, used for the graphs")
    parser.add_argument('--out-dir', default=None,
                        help=f"folder to write the site into (default: {config.SITE_DIR}/<header>/)")
    parser.add_argument('--no-bootstrap', action='store_true',
                        help="skip the Bootstrap fetch and use the built-in styles")
    parser.add_argument('--force', action='store_true', help="re-render every graph")
    args = parser.parse_args()

    publish(header=args.header, xlsx_path=args.xlsx, cache_path=args.cache,
            out_dir=args.out_dir, use_bootstrap=not args.no_bootstrap, force=args.force)


if __name__ == '__main__':
    main()
