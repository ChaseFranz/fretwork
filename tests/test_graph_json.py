"""The client-side graph (section 06): the palette and words the page carries mirror plot.py, and the smoothing is pinned."""

import pathlib
import re
import unittest

import numpy as np

from functions import curves, labels
from web import boot

REPO = pathlib.Path(__file__).resolve().parents[1]

# The vector tests/page/graph.js smooths in the browser; both sides must give these.
PINNED_WIN = [0, 1, 3, 2, 0, 4]
PINNED_VAR = [0, 1, 2, 2, 0, 3]
PINNED_NPS = [0.206319956884, 0.233791139980, 0.249274712958, 0.221722210520, 0.166347919619, 0.113576201083]
PINNED_VPS = [0.168201115681, 0.190596834038, 0.200329151998, 0.181904979485, 0.135036063769, 0.090279835296]
PINNED_D = [0.186288075129, 0.211092044157, 0.223465862854, 0.200829216391, 0.149876510106, 0.101260262331]


class RenderProfileTest(unittest.TestCase):

    def test_boot_profile_is_plot_resolve_profile_s_numbers(self):
        from functions import plot
        got = boot.render_profile()
        want = plot.resolve_profile()
        self.assertEqual(set(got), set(boot.WEB_RENDER_KEYS))
        for key in boot.WEB_RENDER_KEYS:
            self.assertEqual(got[key], want[key], key)

    def test_no_colour_reaches_the_page(self):
        # the page's colours are app.css's tokens, per theme; the profile carries only how the lines are drawn
        for key in boot.WEB_RENDER_KEYS:
            self.assertNotRegex(key, r'color|bg|mode', key)

    def test_the_stylesheet_defines_every_token_the_canvas_reads_in_both_themes(self):
        css = (REPO / 'web' / 'static' / 'css' / 'app.css').read_text(encoding='utf-8')
        js = (REPO / 'web' / 'static' / 'js' / 'graph.js').read_text(encoding='utf-8')
        read = set(re.findall(r'"(--fw-[a-z-]+)"', js))
        self.assertTrue({'--fw-bg', '--fw-series-a', '--fw-series-c', '--fw-curve-d', '--fw-curve-kps'} <= read, read)
        # and the token each family's lines name (labels.CURVE_FAMILIES) is one the canvas can read
        for fam in labels.CURVE_FAMILIES.values():
            for line in fam['lines']:
                read.add(line[3])
        blocks = {name: css[css.index(name):] for name in (':root, [data-bs-theme="light"] {', '[data-bs-theme="dark"] {')}
        for name, text in blocks.items():
            block = text[:text.index('}')]
            for token in sorted(read):
                self.assertIn(token + ':', block, f'{token} is not defined in {name}')

    def test_graph_words_are_plot_literals(self):
        src = (REPO / 'functions' / 'plot.py').read_text(encoding='utf-8')
        for key in ('graph_d', 'graph_y', 'graph_x'):
            literal = labels.UI[key]
            self.assertTrue(f"'{literal}'" in src or f'"{literal}"' in src, f'{key}: {literal!r} is not a literal in plot.py')
        # each family's legend words, and its colour tokens in plot.py's own assignment (config.RENDER_DEFAULT)
        colour_of = {'--fw-curve-nps': 'color_nps', '--fw-curve-vps': 'color_vps', '--fw-curve-kps': 'color_kps'}
        for fam, spec in labels.CURVE_FAMILIES.items():
            for key, legend, readout, token in spec['lines']:
                self.assertIn(f"label='{legend}'", src, f'{fam} {key}: {legend!r} is not a plot.py label')
                self.assertIn(token, colour_of, token)
        self.assertEqual({t for spec in labels.CURVE_FAMILIES.values() for *_, t in spec['lines']}, set(colour_of))
        self.assertEqual(set(boot.boot_payload({}, {})['curves']), set(labels.CURVE_FAMILIES))


class SmoothingTest(unittest.TestCase):

    def test_pinned_vector(self):
        windows = {'time_ms': np.arange(6) * 250.0,
                   'raw_nps_samples': np.array(PINNED_WIN, dtype=np.float64),
                   'raw_vps_samples': np.array(PINNED_VAR, dtype=np.float64)}
        out = curves._calc_fret_curves(windows, 1000, 250, 2000)
        for name, got, want in (('nps', out['nps'], PINNED_NPS), ('vps', out['vps'], PINNED_VPS), ('d', out['d_raw'], PINNED_D)):
            self.assertEqual([round(float(v), 12) for v in got], want, name)


if __name__ == '__main__':
    unittest.main()


class StubRenderer:
    """Resolves every code it is given; renders a tiny PNG; the curve product is stubbed too."""

    def __init__(self, codes):
        self.codes = set(codes)

    def lookup(self, code):
        return {'code': code} if code in self.codes else None

    def original_diff(self, entry):
        return None

    def render(self, entry, out_dir=None):
        return b'\x89PNG' + entry['code'].encode()


class RenderGraphsTest(unittest.TestCase):
    """The PNG product walks png_codes only; the prune rules are per product."""

    def setUp(self):
        import tempfile
        from web import bundle
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.bundle = bundle
        # the fingerprints and the curve bytes, stubbed so no cache is needed
        self._fp, self._fpc, self._cb = bundle.PNG.fingerprint_of, bundle.CURVES.fingerprint_of, bundle.CURVES.make
        bundle.PNG.fingerprint_of = lambda renderer, entry: 'fp-' + entry['code']
        bundle.CURVES.fingerprint_of = lambda renderer, entry: 'cfp-' + entry['code']
        bundle.CURVES.make = lambda renderer, entry, scratch: b'{"v":2}'

    def tearDown(self):
        import shutil
        self.bundle.PNG.fingerprint_of, self.bundle.CURVES.fingerprint_of, self.bundle.CURVES.make = self._fp, self._fpc, self._cb
        shutil.rmtree(self.tmp, ignore_errors=True)

    def pngs(self):
        return sorted(p.name for p in (self.tmp / 'graph').glob('*.png'))

    def test_only_png_codes_get_a_png_and_recorded_stale_ones_go(self):
        import json
        graph = self.tmp / 'graph'
        graph.mkdir()
        (graph / 'B.png').write_bytes(b'old')            # recorded by an earlier publish: pruned
        (graph / 'Z.png').write_bytes(b'stray')          # never recorded: left alone
        (graph / 'manifest.json').write_text(json.dumps({'B': 'fp-B'}))
        codes = ['A', 'B', 'C']
        counts, files = self.bundle.render_graphs(self.tmp, codes, StubRenderer(codes), png_codes=['A'])
        self.assertEqual(self.pngs(), ['A.png', 'Z.png'])
        self.assertEqual(counts['png']['rendered'], 1)
        self.assertEqual(counts['png']['pruned'], 1)
        self.assertEqual(json.loads((graph / 'manifest.json').read_text()), {'A': 'fp-A'})
        self.assertEqual(sorted(p.name for p in graph.glob('*.json')), ['A.json', 'B.json', 'C.json', 'curves-manifest.json', 'manifest.json'])
        self.assertEqual(counts['curves']['rendered'], 3)
        self.assertIn('graph/A.png', files)
        self.assertNotIn('graph/B.png', files)

    def test_an_empty_png_list_prunes_nothing_and_writes_an_empty_manifest(self):
        import json
        codes = ['A', 'B']
        counts, files = self.bundle.render_graphs(self.tmp, codes, StubRenderer(codes), png_codes=[])
        graph = self.tmp / 'graph'
        self.assertEqual(self.pngs(), [])
        self.assertEqual(json.loads((graph / 'manifest.json').read_text()), {})
        self.assertEqual(counts['png'], dict(rendered=0, unchanged=0, kept=0, no_graph=0, failed=0, pruned=0))
        # a recorded PNG from before survives an empty list: the zero-resolved rule
        (graph / 'B.png').write_bytes(b'old')
        (graph / 'manifest.json').write_text(json.dumps({'B': 'fp-B'}))
        counts, files = self.bundle.render_graphs(self.tmp, codes, StubRenderer(codes), png_codes=[])
        self.assertEqual(self.pngs(), ['B.png'])
        self.assertEqual(json.loads((graph / 'manifest.json').read_text()), {'B': 'fp-B'})
        self.assertIn('graph/B.png', files)

    def test_none_means_every_code(self):
        codes = ['A', 'B']
        counts, _ = self.bundle.render_graphs(self.tmp, codes, StubRenderer(codes))
        self.assertEqual(self.pngs(), ['A.png', 'B.png'])
        self.assertEqual(counts['png']['rendered'], 2)
