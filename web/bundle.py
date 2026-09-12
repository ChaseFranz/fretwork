"""
BUNDLE - writes the viewer as a static site: one folder S3 can serve as-is

Same page, assets and graphs serve.py hands out, written to disk instead.
Files are rewritten only when their bytes change, so an `aws s3 sync` after a
re-publish uploads just what moved. Graphs are the slow part, so a manifest of
render-input fingerprints lets an unchanged chart skip its render entirely.
Nothing here deletes a file that an earlier publish did not record writing.
"""

import hashlib
import json
import pathlib
import pickle
import tempfile

from tqdm import tqdm

import config
from functions import curves, density, difficulty
from web import assets
from web import graph as graph_mod

GRAPH_DIR = 'graph'
MANIFEST = 'manifest.json'
CURVES_MANIFEST = 'curves-manifest.json'
TMP_PREFIX = 'fretwork-publish-'
FLUSH_EVERY = 200   # charts between manifest saves, so an interrupted run keeps its work


# Rewrites only on change, so untouched files keep their mtime for s3 sync.
def write_if_changed(path, data):
    path = pathlib.Path(path)
    if path.is_file() and path.read_bytes() == data:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return True


# A page file this publish no longer produces - the previous generation of a
# hashed asset or sheet, bootstrap.css from before it moved under static/ -
# would otherwise sit in the folder forever and go on being uploaded. Only the
# page's own territory is swept: the top-level files it writes and everything
# under static/ and data/, plus a directory that sweep has emptied. graph/ has
# its own pruning, with its own rules, and is never touched from here.
PAGE_TOP = ('index.html', '404.html', 'about.html', 'changelog.html', 'library.html', 'methodology.html', 'robots.txt', 'bootstrap.css')


def prune_page(out, files):
    keep = {(out / name).resolve() for name in files}
    stale = [path for d in assets.IMMUTABLE_DIRS for path in (out / d).rglob('*')
             if path.is_file() and path.resolve() not in keep]
    stale += [out / name for name in PAGE_TOP
              if (out / name).is_file() and (out / name).resolve() not in keep]
    for path in stale:
        path.unlink()
    for d in assets.IMMUTABLE_DIRS:
        for sub in sorted((p for p in (out / d).rglob('*') if p.is_dir()), reverse=True):
            if not any(sub.iterdir()):
                sub.rmdir()
    return len(stale)


# Every file the site is, graphs excepted: {relative name: bytes}.
# Returns (names, count rewritten, count removed).
def write_page(out_dir, files):
    out = pathlib.Path(out_dir)
    written = sum(write_if_changed(out / name, data) for name, data in files.items())
    return list(files), written, prune_page(out, files)


# Everything the PNG depends on: the chart, its Expert anchor, the numbers the
# header prints, the metadata the header prints (difficulty.HEADER_META_KEYS,
# never the rest of meta), and the curve and render settings.
def fingerprint(entry, original_diff):
    expert = entry.get('expert_notes')
    parts = (
        entry['code'], entry['instrument'], entry['level'], entry.get('source_format'),
        entry['notes']['time_ms'].tobytes(), entry['notes']['lanes'].tobytes(),
        expert['time_ms'].tobytes() if expert is not None else b'',
        expert['lanes'].tobytes() if expert is not None else b'',
        repr(sorted((k, v) for k, v in entry['meta'].items() if k in difficulty.HEADER_META_KEYS)),
        repr(original_diff),
        repr(difficulty.entry_difficulty(entry)),
        curves.TAU_MS, density.WINDOW_MS, density.STEP_MS,
        repr(config.RENDER_DEFAULT), repr(config.RENDER_THEMES),
    )
    return hashlib.sha1(pickle.dumps(parts, protocol=4)).hexdigest()


# The curve JSON depends on less: the chart, its Expert anchor, the source
# format, the difficulty block its head carries, and the window and smoothing
# constants. Never the theme or the metadata, so a theme edit or a retitle
# rewrites no JSON.
def fingerprint_curves(entry):
    expert = entry.get('expert_notes')
    parts = (
        1, entry['notes']['time_ms'].tobytes(), entry['notes']['lanes'].tobytes(),
        expert['time_ms'].tobytes() if expert is not None else b'',
        expert['lanes'].tobytes() if expert is not None else b'',
        entry.get('source_format'), repr(difficulty.entry_difficulty(entry)),
        density.WINDOW_MS, density.STEP_MS, curves.TAU_MS,
    )
    return hashlib.sha1(pickle.dumps(parts, protocol=4)).hexdigest()


# The two products a chart has, each with its own manifest, fingerprint and
# maker, so a rollback to a commit that knows only PNGs re-renders nothing.
class Product:
    def __init__(self, suffix, manifest, fingerprint_of, make):
        self.suffix = suffix
        self.manifest = manifest
        self.fingerprint_of = fingerprint_of     # (renderer, entry) -> str
        self.make = make                         # (renderer, entry, scratch) -> bytes | None


PNG = Product('.png', MANIFEST,
              lambda renderer, entry: fingerprint(entry, renderer.original_diff(entry)),
              lambda renderer, entry, scratch: renderer.render(entry, out_dir=scratch))
CURVES = Product('.json', CURVES_MANIFEST,
                 lambda renderer, entry: fingerprint_curves(entry),
                 lambda renderer, entry, scratch: graph_mod.curves_bytes(entry))


def _load_manifest(graph_dir, name=MANIFEST):
    try:
        return json.loads((graph_dir / name).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def _save_manifest(graph_dir, entries, name=MANIFEST):
    write_if_changed(graph_dir / name,
                     json.dumps(entries, indent=0, sort_keys=True).encode('utf-8'))


def _clear(directory):
    for path in pathlib.Path(directory).iterdir():
        if path.is_file():
            path.unlink()


class GraphRun:
    """One pass over the codes for one product: what the last publish recorded, what this one did."""

    def __init__(self, graph_dir, renderer, scratch, force, product=PNG):
        self.graph_dir = graph_dir
        self.renderer = renderer
        self.scratch = scratch
        self.product = product
        self.prior = _load_manifest(graph_dir, product.manifest)   # what is on disk from last time
        self.skip = {} if force else self.prior      # what may be reused as-is
        self.fresh = {}                              # what this publish stands behind
        self.resolved = 0
        self.counts = dict(rendered=0, unchanged=0, kept=0, no_graph=0, failed=0, pruned=0)

    def path(self, code):
        return self.graph_dir / f"{code}{self.product.suffix}"

    def one(self, code):
        out = self.path(code)
        entry = self.renderer.lookup(code)
        if entry is None:
            self.counts['no_graph'] += 1
            return self.keep(code, out)
        self.resolved += 1
        key = self.product.fingerprint_of(self.renderer, entry)
        if self.skip.get(code) == key and out.is_file():
            self.fresh[code] = key
            self.counts['unchanged'] += 1
            return
        try:
            data = self.product.make(self.renderer, entry, self.scratch)
        except Exception as exc:   # one bad chart never stops a publish
            self.counts['failed'] += 1
            tqdm.write(f"  {code}: {self.product.suffix} failed ({exc})")
            return self.keep(code, out)
        finally:
            _clear(self.scratch)
        if data is None:
            self.counts['no_graph'] += 1
            return self.keep(code, out)
        write_if_changed(out, data)
        self.fresh[code] = key
        self.counts['rendered'] += 1

    # A chart that cannot be made now keeps the file an earlier publish made.
    def keep(self, code, out):
        if code in self.prior and out.is_file():
            self.fresh[code] = self.prior[code]
            self.counts['kept'] += 1

    # Only after a completed pass, and only files a previous publish recorded.
    # A pass that resolved nothing keeps everything: a cache/xlsx mismatch, or
    # a PNG list that was empty on purpose (the caller has already said so).
    def prune(self, expected_empty=False):
        if not self.resolved:
            if not expected_empty:
                tqdm.write("  no spreadsheet code was found in the cache - are the xlsx and "
                           "cache from the same build? Nothing pruned.")
            self.fresh = {**self.prior, **self.fresh}
            return
        for code in set(self.prior) - set(self.fresh):
            self.path(code).unlink(missing_ok=True)
            self.counts['pruned'] += 1


def _run_product(graph_dir, codes, renderer, force, product, label, expected_empty=False):
    with tempfile.TemporaryDirectory(prefix=TMP_PREFIX) as scratch:
        run = GraphRun(graph_dir, renderer, scratch, force, product)
        try:
            for i, code in enumerate(tqdm(codes, desc=label, unit="chart", disable=not codes), 1):
                run.one(code)
                if i % FLUSH_EVERY == 0:
                    _save_manifest(graph_dir, {**run.prior, **run.fresh}, product.manifest)
        finally:
            _save_manifest(graph_dir, {**run.prior, **run.fresh}, product.manifest)
    run.prune(expected_empty)
    _save_manifest(graph_dir, run.fresh, product.manifest)
    files = [f"{GRAPH_DIR}/{code}{product.suffix}" for code in sorted(run.fresh)] + [f"{GRAPH_DIR}/{product.manifest}"]
    return run.counts, files


# Writes graph/<code>.json for every code, and graph/<code>.png for png_codes
# only: the page draws from the JSON, so the one PNG left is the social
# preview. None means every code, which render-only callers may still want.
# With an empty png_codes the PNG pass resolves nothing, so the zero-resolved
# rule keeps every PNG an earlier publish recorded (the warning is the
# caller's to print). Returns ({'png': counts, 'curves': counts}, file names).
def render_graphs(out_dir, codes, renderer, force=False, png_codes=None):
    graph_dir = pathlib.Path(out_dir) / GRAPH_DIR
    graph_dir.mkdir(parents=True, exist_ok=True)
    png_codes = list(codes) if png_codes is None else list(png_codes)
    png_counts, png_files = _run_product(graph_dir, png_codes, renderer, force, PNG, "Rendering graphs",
                                         expected_empty=not png_codes)
    curve_counts, curve_files = _run_product(graph_dir, codes, renderer, force, CURVES, "Writing curves")
    return {'png': png_counts, 'curves': curve_counts}, png_files + curve_files
