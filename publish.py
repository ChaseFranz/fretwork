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
analyze.py first: a spreadsheet and cache from different builds stop the run
unless --allow-mismatch is passed. Measured at about 0.12 s per chart: a
4,600-chart library takes around ten minutes the first time and seconds after
that.
"""

import argparse
import pathlib
import sys

import config
from functions import packs, timestamp
from web import banner, bootstrap, bundle, frames, page
from web.graph import GraphRenderer


# latest_output picks the newest file by mtime while the pairing below compares
# filename stamps; when the two orders disagree (a copied or touched old file),
# name both files rather than leave it to be inferred from the pairing message.
def warn_mtime_order(kind, header, ext):
    try:
        by_mtime = timestamp.latest_output(kind, header, ext=ext)
    except FileNotFoundError:
        return
    stamped = []
    for path in by_mtime.parent.glob(f"{header}_{kind}_*.{ext}"):
        try:
            stamped.append((timestamp.ext_ts(path, kind, header), path))
        except ValueError:
            continue
    if stamped:
        _stamp, by_name = max(stamped)
        if by_name != by_mtime:
            print(f"Warning: {kind} newest by mtime is {by_mtime.name} but newest by name is {by_name.name}")


# analyze pairs each spreadsheet with its cache by timestamp; a table computed
# from one build beside graphs rendered from another is refused unless asked for
def check_pair(header, xlsx_path, cache_path, allow_mismatch=False):
    for kind, ext in (('metrics', 'xlsx'), ('cache', 'pkl')):
        warn_mtime_order(kind, header, ext)
    try:
        xlsx_ts = timestamp.ext_ts(xlsx_path, 'metrics', header)
        cache_ts = timestamp.ext_ts(cache_path, 'cache', header)
    except ValueError:
        print("Note: the spreadsheet or cache name does not carry a build timestamp; "
              "not checking that they are from the same build.")
        return
    if xlsx_ts == cache_ts:
        return
    first = f"spreadsheet is from {xlsx_ts} but the cache is from {cache_ts}."
    if allow_mismatch:
        print(f"Note: {first[:-1]}; publishing anyway (--allow-mismatch)")
        return
    raise SystemExit(f"{first}\nRun `python analyze.py --header {header}` so the table and "
                     f"graphs come from the same build, or pass --allow-mismatch.")


# The pack registry against the cache: publish is for the one library the site
# is built from, so a folder the registry does not name, or a registered folder
# the cache does not have, stops the run before anything is written.
def resolve_packs(cache, packs_path):
    try:
        registry = packs.load(packs_path)
    except FileNotFoundError:
        sys.exit(f"no pack registry at {packs_path}; every pack in the library must be listed there")
    except packs.PacksError as exc:
        sys.exit(str(exc))
    try:
        resolved = packs.resolve(cache, registry)
    except packs.PacksError as exc:
        sys.exit(str(exc))
    if not resolved.clean:
        sys.exit(packs.report(resolved))
    return resolved


def publish(header=None, xlsx_path=None, cache_path=None, out_dir=None,
            use_bootstrap=True, force=False, allow_mismatch=False, packs_path=None):
    header = header or config.HEADER
    out_dir = pathlib.Path(out_dir).expanduser() if out_dir else pathlib.Path(config.SITE_DIR) / header

    renderer = GraphRenderer(header, cache_path)
    cache = renderer.cache()   # a missing cache fails here, before anything is written
    resolved = resolve_packs(cache, packs_path or packs.PACKS_FILE)
    bootstrap_css = bootstrap.ensure_bootstrap(use_bootstrap)
    built = page.build(header, xlsx_path, bootstrap_css, public=True, resolved=resolved)
    check_pair(header, built.xlsx_path, renderer.cache_path, allow_mismatch)

    print(f"\nPublishing {built.xlsx_path}")
    page_files, written, removed = bundle.write_page(out_dir, built.files)
    codes = frames.codes_in(built.sheets)
    # the PNGs: the social preview and each song page's picture (Built.png_codes,
    # section 22); every other graph is the curve JSON the page draws
    have = set(codes)
    png_codes = [c for c in built.png_codes if c in have]
    if page.OG_CODE not in have:
        print(f"  social preview chart {page.OG_CODE} is not in this spreadsheet; no preview PNG published")
    counts, graph_files = bundle.render_graphs(out_dir, codes, renderer, force, png_codes=png_codes)
    banner.print_published(out_dir, page_files, written, removed, counts, graph_files,
                           packs_line=f"packs: {len(resolved.registry.packs)} registered from {resolved.registry.path.name}",
                           preview=(page.OG_CODE, page.OG_CODE in have))


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
    parser.add_argument('--allow-mismatch', action='store_true',
                        help="publish even if the spreadsheet and cache are from different builds")
    parser.add_argument('--packs', default=None,
                        help=f"pack registry to join and list (default: {packs.PACKS_FILE.name} in the repo root)")
    args = parser.parse_args()

    publish(header=args.header, xlsx_path=args.xlsx, cache_path=args.cache,
            out_dir=args.out_dir, use_bootstrap=not args.no_bootstrap, force=args.force,
            allow_mismatch=args.allow_mismatch, packs_path=args.packs)


if __name__ == '__main__':
    main()
