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

GRAPH_DIR = 'graph'
MANIFEST = 'manifest.json'
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


# The pages, the static assets and Bootstrap. Returns (names, count rewritten).
def write_page(out_dir, pages, static, bootstrap_css):
    out = pathlib.Path(out_dir)
    files = dict(pages)
    files.update({url.lstrip('/'): data for url, (data, _type) in static.items()})
    if bootstrap_css:
        files['bootstrap.css'] = bootstrap_css
    written = sum(write_if_changed(out / name, data) for name, data in files.items())
    return list(files), written


# Everything the PNG depends on: the chart, its Expert anchor, the numbers the
# header prints, the metadata, and the curve and render settings.
def fingerprint(entry, original_diff):
    expert = entry.get('expert_notes')
    parts = (
        entry['code'], entry['instrument'], entry['level'], entry.get('source_format'),
        entry['notes']['time_ms'].tobytes(), entry['notes']['lanes'].tobytes(),
        repr(sorted(entry['spans'].items())),
        expert['time_ms'].tobytes() if expert is not None else b'',
        expert['lanes'].tobytes() if expert is not None else b'',
        repr(sorted(entry['meta'].items())), repr(original_diff),
        repr(difficulty.entry_difficulty(entry)),
        curves.TAU_MS, density.WINDOW_MS, density.STEP_MS,
        repr(config.RENDER_DEFAULT), repr(config.RENDER_THEMES),
    )
    return hashlib.sha1(pickle.dumps(parts, protocol=4)).hexdigest()


def _load_manifest(graph_dir):
    try:
        return json.loads((graph_dir / MANIFEST).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def _save_manifest(graph_dir, entries):
    write_if_changed(graph_dir / MANIFEST,
                     json.dumps(entries, indent=0, sort_keys=True).encode('utf-8'))


def _clear(directory):
    for path in pathlib.Path(directory).iterdir():
        if path.is_file():
            path.unlink()


class GraphRun:
    """One pass over the codes: what the last publish recorded, what this one did."""

    def __init__(self, graph_dir, renderer, scratch, force):
        self.graph_dir = graph_dir
        self.renderer = renderer
        self.scratch = scratch
        self.prior = _load_manifest(graph_dir)      # what is on disk from last time
        self.skip = {} if force else self.prior      # what may be reused as-is
        self.fresh = {}                              # what this publish stands behind
        self.resolved = 0
        self.counts = dict(rendered=0, unchanged=0, kept=0, no_graph=0, failed=0, pruned=0)

    def one(self, code):
        png = self.graph_dir / f"{code}.png"
        entry = self.renderer.lookup(code)
        if entry is None:
            self.counts['no_graph'] += 1
            return self.keep(code, png)
        self.resolved += 1
        key = fingerprint(entry, self.renderer.original_diff(entry))
        if self.skip.get(code) == key and png.is_file():
            self.fresh[code] = key
            self.counts['unchanged'] += 1
            return
        try:
            data = self.renderer.render(entry, out_dir=self.scratch)
        except Exception as exc:   # one bad chart never stops a publish
            self.counts['failed'] += 1
            tqdm.write(f"  {code}: render failed ({exc})")
            return self.keep(code, png)
        finally:
            _clear(self.scratch)
        if data is None:
            self.counts['no_graph'] += 1
            return self.keep(code, png)
        write_if_changed(png, data)
        self.fresh[code] = key
        self.counts['rendered'] += 1

    # A chart that cannot be rendered now keeps the PNG an earlier publish made.
    def keep(self, code, png):
        if code in self.prior and png.is_file():
            self.fresh[code] = self.prior[code]
            self.counts['kept'] += 1

    # Only after a completed pass, and only files a previous publish recorded.
    def prune(self):
        if not self.resolved:
            tqdm.write("  no spreadsheet code was found in the cache - are the xlsx and "
                       "cache from the same build? Nothing pruned.")
            self.fresh = {**self.prior, **self.fresh}
            return
        for code in set(self.prior) - set(self.fresh):
            (self.graph_dir / f"{code}.png").unlink(missing_ok=True)
            self.counts['pruned'] += 1


# Renders graph/<code>.png for every code. Returns (counts, relative file names).
def render_graphs(out_dir, codes, renderer, force=False):
    graph_dir = pathlib.Path(out_dir) / GRAPH_DIR
    graph_dir.mkdir(parents=True, exist_ok=True)

    # plot.render_song writes its own file: render into scratch, keep the bytes
    with tempfile.TemporaryDirectory(prefix=TMP_PREFIX) as scratch:
        run = GraphRun(graph_dir, renderer, scratch, force)
        try:
            for i, code in enumerate(tqdm(codes, desc="Rendering graphs", unit="chart"), 1):
                run.one(code)
                if i % FLUSH_EVERY == 0:
                    _save_manifest(graph_dir, {**run.prior, **run.fresh})
        finally:
            _save_manifest(graph_dir, {**run.prior, **run.fresh})

    run.prune()
    _save_manifest(graph_dir, run.fresh)
    files = [f"{GRAPH_DIR}/{code}.png" for code in sorted(run.fresh)] + [f"{GRAPH_DIR}/{MANIFEST}"]
    return run.counts, files
