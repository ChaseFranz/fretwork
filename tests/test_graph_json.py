"""The client-side graph (section 06): the palette and words the page carries mirror plot.py, and the smoothing is pinned."""

import pathlib
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

    def test_boot_profile_equals_plot_resolve_profile(self):
        from functions import plot
        got = boot.render_profile()
        want = plot.resolve_profile()
        self.assertEqual(set(got), set(boot.WEB_RENDER_KEYS))
        for key in boot.WEB_RENDER_KEYS:
            self.assertEqual(got[key], want[key], key)

    def test_the_page_is_dark(self):
        self.assertEqual(boot.render_profile()['mode'], 'dark')

    def test_graph_words_are_plot_literals(self):
        src = (REPO / 'functions' / 'plot.py').read_text(encoding='utf-8')
        for key in ('graph_d', 'graph_nps', 'graph_vps', 'graph_y', 'graph_x'):
            literal = labels.UI[key]
            self.assertTrue(f"'{literal}'" in src or f'"{literal}"' in src, f'{key}: {literal!r} is not a literal in plot.py')


class SmoothingTest(unittest.TestCase):

    def test_pinned_vector(self):
        windows = {'time_ms': np.arange(6) * 250.0,
                   'raw_nps_samples': np.array(PINNED_WIN, dtype=np.float64),
                   'raw_vps_samples': np.array(PINNED_VAR, dtype=np.float64)}
        out = curves.smooth_curves(windows, 1000, 250, 2000)
        for name, got, want in (('nps', out['nps'], PINNED_NPS), ('vps', out['vps'], PINNED_VPS), ('d', out['d_raw'], PINNED_D)):
            self.assertEqual([round(float(v), 12) for v in got], want, name)


if __name__ == '__main__':
    unittest.main()
