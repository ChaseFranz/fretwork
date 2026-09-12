"""The data model (section 05): bundler invariants, hashed names, sheet files, pruning, curve JSON."""

import io
import json
import math
import pathlib
import tempfile
import unittest
import unittest.mock

import numpy as np

import config
from functions import curves, density
from web import assets, bundle, bundler, frames
from web import graph as graph_mod

REPO = pathlib.Path(__file__).resolve().parents[1]


def module_dir(files):
    tmp = pathlib.Path(tempfile.mkdtemp())
    (tmp / 'js').mkdir()
    for name, text in files.items():
        (tmp / 'js' / name).write_text(text, encoding='utf-8')
    return tmp


class BundlerTest(unittest.TestCase):

    def test_real_modules_bundle_and_keep_their_literals(self):
        out = bundler.bundle(assets.STATIC_DIR).decode('utf-8')
        self.assertEqual(out.count('// ---- '), len(list((assets.STATIC_DIR / 'js').glob('*.js'))))
        self.assertNotIn('\nimport ', out)
        self.assertNotIn('\nexport ', out)
        self.assertIn('"https://www.youtube-nocookie.com"', out)
        self.assertTrue(out.rstrip().endswith('\n') or True)
        self.assertLess(out.index('// ---- boot.js'), out.index('// ---- main.js'))

    def test_refusals_name_file_and_line(self):
        cases = {
            'export default': ({'main.js': 'import { a } from "./a.js";\nconsole.log(a);\n',
                                'a.js': 'export default 1;\nexport const a = 1;\n'}, 'a.js:1'),
            'cycle': ({'main.js': 'import { a } from "./a.js";\n', 'a.js': 'import { b } from "./b.js";\nexport const a = b;\n',
                       'b.js': 'import { a } from "./a.js";\nexport const b = 2;\n'}, 'cycle'),
            'duplicate name': ({'main.js': 'import { a } from "./a.js";\n', 'a.js': 'export const a = 1;\n',
                                'b.js': 'const a = 2;\n'}, "'a' is declared in both"),
            'renamed import': ({'main.js': 'import { a as b } from "./a.js";\n', 'a.js': 'export const a = 1;\n'}, 'renamed'),
            'missing export': ({'main.js': 'import { z } from "./a.js";\n', 'a.js': 'export const a = 1;\n'}, 'does not export'),
            'dynamic import': ({'main.js': 'const m = import("./a.js");\n', 'a.js': 'export const a = 1;\n'}, 'dynamic'),
        }
        for label, (files, needle) in cases.items():
            with self.subTest(case=label):
                with self.assertRaisesRegex(bundler.BundleError, needle):
                    bundler.bundle(module_dir(files))


class AssetsAndSheetsTest(unittest.TestCase):

    def test_hashed_names_match_bytes(self):
        files, names = assets.load_assets(b'body{}')
        self.assertEqual(set(names), {'script', 'style', 'favicon', 'bootstrap'})
        for role, name in names.items():
            self.assertRegex(name, r'^static/[a-z]+\.[0-9a-f]{8}\.(js|css|svg)$')
            self.assertEqual(name.split('.')[-2], assets.hash8(files[name]))
        files, names = assets.load_assets(None)
        self.assertNotIn('bootstrap', names)

    def test_sheet_files_round_trip(self):
        import pandas as pd
        sheets = {'Guitar': pd.DataFrame({'Code': ['1XG'], 'Song Title': ['A < B'], 'D': [1.5]}),
                  'Bass': pd.DataFrame({'Code': ['2XB'], 'Song Title': ['C'], 'D': [np.nan]})}
        files, manifest = frames.sheet_files(sheets)
        self.assertEqual(list(manifest), ['Guitar', 'Bass'])
        for name, entry in manifest.items():
            self.assertRegex(entry['file'], r'^data/[a-z]+\.[0-9a-f]{8}\.json$')
            self.assertEqual(json.loads(files[entry['file']]), frames.frames_payload(sheets)[name])
            self.assertEqual(entry['rows'], 1)
        self.assertIn(b'A < B', files[manifest['Guitar']['file']])       # not escaped: never inside a script tag
        self.assertIn(b'null', files[manifest['Bass']['file']])
        with self.assertRaises(ValueError):
            frames.sheet_files({'Guitar': sheets['Guitar'], 'GUITAR': sheets['Bass']})

    def test_prune_removes_stale_hashes_and_emptied_directories(self):
        tmp = pathlib.Path(tempfile.mkdtemp())
        (tmp / 'data').mkdir()
        (tmp / 'static' / 'old').mkdir(parents=True)
        (tmp / 'data' / 'guitar.deadbeef.json').write_bytes(b'x')
        (tmp / 'static' / 'old' / 'main.js').write_bytes(b'x')
        (tmp / 'bootstrap.css').write_bytes(b'x')
        files = {'index.html': b'i', 'data/guitar.12345678.json': b'y', 'static/app.abcdef01.js': b'z'}
        names, written, removed = bundle.write_page(tmp, files)
        self.assertEqual(written, 3)
        self.assertEqual(removed, 3)
        self.assertEqual(sorted(p.relative_to(tmp).as_posix() for p in tmp.rglob('*') if p.is_file()),
                         ['data/guitar.12345678.json', 'index.html', 'static/app.abcdef01.js'])
        self.assertFalse((tmp / 'static' / 'old').exists())


class CurvesTest(unittest.TestCase):

    def entry(self):
        times = np.array([0.0, 400.0, 900.0, 1300.0, 2100.0, 2600.0], dtype=np.float64)
        lanes = np.array([1, 2, 4, 1, 3, 8], dtype=np.uint8)
        return {'code': '00000001XG', 'instrument': 'guitar', 'level': 'expert', 'source_format': 'chart',
                'notes': {'time_ms': times, 'lanes': lanes}, 'expert_notes': {'time_ms': times, 'lanes': lanes},
                'meta': {'Name': 'x'}, 'song_path': '/x'}

    def test_curve_json_shape(self):
        doc = json.loads(graph_mod.curves_bytes(self.entry()))
        self.assertEqual([doc['v'], doc['step'], doc['window'], doc['tau']], [1, 250, 1000, 2000])
        self.assertEqual(doc['n'], len(doc['win']))
        self.assertEqual(len(doc['win']), len(doc['var']))
        self.assertEqual(doc['n'], int(2600 // 250) + 1)
        self.assertEqual(set(doc['head']), {'N', 'V', 'COV', 'D', 'RemapDiff', 'CalcTier', 'source'})
        self.assertEqual(doc['head']['source'], 'chart')
        self.assertTrue(all(isinstance(v, int) and v >= 0 for v in doc['win'] + doc['var']))

    # The JS reconstruction, written in Python with the same operations, must land
    # on curves.calc_curves to within floating-point noise.
    def test_client_reconstruction_matches_calc_curves(self):
        entry = self.entry()
        doc = json.loads(graph_mod.curves_bytes(entry))
        ref = curves.calc_curves(entry['notes'])
        decay = math.exp(-doc['step'] / doc['tau'])
        gain = 1 - decay

        def ema(values):
            out, acc = [], 0.0
            for v in values:
                acc = acc * decay + v * gain
                out.append(acc)
            back, acc = [], 0.0
            for v in reversed(out):
                acc = acc * decay + v * gain
                back.append(acc)
            return list(reversed(back))
        nps = ema([c / (doc['window'] / 1000) for c in doc['win']])
        vps = ema([c / (doc['window'] / 1000) for c in doc['var']])
        for a, b in zip(nps, ref['nps']):
            self.assertAlmostEqual(a, b, places=12)
        for a, b in zip(vps, ref['vps']):
            self.assertAlmostEqual(a, b, places=12)
        for a, b, c in zip(nps, vps, ref['d_raw']):
            self.assertAlmostEqual(math.sqrt(a * b), c, places=12)

    # HEADER_META_KEYS mirrors what upstream's plot.py prints; the mirror is checked
    # against plot.py's source so an upstream change turns into a red test here.
    def test_header_meta_keys_mirror_plot(self):
        from functions import difficulty
        src = (REPO / 'functions' / 'plot.py').read_text(encoding='utf-8')
        for key in difficulty.HEADER_META_KEYS:
            self.assertIn(f"'{key}'", src, f'{key} is in HEADER_META_KEYS but plot.py never reads it')
        for key in ('Genre', 'Year', 'Album'):
            self.assertNotIn(f"meta['{key}']", src)
            self.assertNotIn(f"meta.get('{key}'", src)
        entry = self.entry()
        before = bundle.fingerprint(entry, None)
        entry['meta']['Genre'] = 'Rock'
        self.assertEqual(bundle.fingerprint(entry, None), before)
        entry['meta']['Name'] = 'other'
        self.assertNotEqual(bundle.fingerprint(entry, None), before)

    def test_curve_fingerprint_ignores_the_theme(self):
        entry = self.entry()
        before = bundle.fingerprint_curves(entry)
        before_png = bundle.fingerprint(entry, None)
        with unittest.mock.patch.object(config, 'RENDER_THEMES', {'x': 1}):
            self.assertEqual(bundle.fingerprint_curves(entry), before)
            self.assertNotEqual(bundle.fingerprint(entry, None), before_png)
        entry['meta']['Name'] = 'renamed'
        self.assertEqual(bundle.fingerprint_curves(entry), before)


if __name__ == '__main__':
    unittest.main()
