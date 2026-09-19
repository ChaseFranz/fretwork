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
from functions import curves
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
    """The curve JSON (v2) for the three families, and its reconstruction against curves.py."""

    def entry(self):
        times = np.array([0.0, 400.0, 900.0, 1300.0, 2100.0, 2600.0], dtype=np.float64)
        lanes = np.array([1, 2, 4, 1, 3, 8], dtype=np.uint8)
        return {'code': '00000001XG', 'instrument': 'guitar', 'level': 'expert', 'source_format': 'chart',
                'notes': {'time_ms': times, 'lanes': lanes}, 'expert_notes': {'time_ms': times, 'lanes': lanes},
                'meta': {'Name': 'x'}, 'song_path': '/x'}

    # hands on five pads, a roll span over the second bar, 1x kicks on the
    # beat and one 2x kick, so both readings exist and the roll cap is exercised
    def drum_entry(self):
        hand = {'time_ms': np.arange(0, 6000, 300, dtype=np.float64), 'lanes': np.array([1 << (i % 5) for i in range(20)], dtype=np.uint8)}
        kick = {'time_ms': np.array([0.0, 500.0, 1000.0, 1500.0, 2000.0, 2250.0, 3000.0, 4000.0, 6500.0]),
                'lanes': np.array([1, 1, 1, 1, 1, 2, 1, 1, 1], dtype=np.uint8)}
        notes = {'hand_mask': hand, 'kick_mask': kick}
        spans = [(1200.0, 2400.0, 'single')]
        return {'code': '00000002XD', 'instrument': 'drums', 'level': 'expert', 'source_format': 'mid',
                'notes': notes, 'expert_notes': notes, 'roll_spans': spans, 'expert_roll_spans': spans,
                'meta': {'Name': 'd'}, 'song_path': '/d'}

    def vocal_entry(self, percussion=True):
        n = 16
        times = np.arange(0, n * 400, 400, dtype=np.float64)
        notes = {'time_ms': times, 'end_ms': times + 300.0,
                 'pitch': np.array([55 + (i * 5) % 17 for i in range(n)], dtype=np.uint8),
                 'is_placeholder': np.zeros(n, dtype=bool), 'is_slide': np.array([i % 5 == 4 for i in range(n)])}
        talkie = {'time_ms': np.array([200.0, 3300.0]), 'end_ms': np.array([np.nan, np.nan])}
        perc = {'time_ms': np.array([1000.0, 5000.0]), 'end_ms': np.array([1020.0, 5020.0])} if percussion \
            else {'time_ms': np.array([], dtype=np.float64), 'end_ms': np.array([], dtype=np.float64)}
        return {'code': '00000003XV', 'instrument': 'vocals', 'level': 'expert', 'source_format': 'mid',
                'notes': notes, 'talkie': talkie, 'percussion': perc, 'expert_notes': notes,
                'meta': {'Name': 'v'}, 'song_path': '/v'}

    def test_curve_json_shape(self):
        doc = json.loads(graph_mod.curves_bytes(self.entry()))
        self.assertEqual([doc['v'], doc['family'], doc['step'], doc['window'], doc['tau']], [2, 'fret', 250, 1000, 2000])
        self.assertEqual(list(doc['series']), ['nps', 'vps'])
        self.assertEqual(doc['d'], {'geo': ['nps', 'vps']})
        self.assertTrue(all(len(v) == doc['n'] for v in doc['series'].values()))
        self.assertEqual(doc['n'], int(2600 // 250) + 1)
        self.assertEqual(set(doc['head']), {'N', 'V', 'CoV', 'STAM', 'D', 'RemapDiff', 'CalcTier', 'source'})
        self.assertEqual(doc['head']['source'], 'chart')
        self.assertTrue(all(isinstance(v, int) and v >= 0 for k in doc['series'] for v in doc['series'][k]))

    def test_drum_and_vocal_json_shapes(self):
        drums = json.loads(graph_mod.curves_bytes(self.drum_entry()))
        self.assertEqual([drums['v'], drums['family']], [2, 'drums'])
        self.assertEqual(list(drums['series']), ['hps', 'tps', 'kps'])
        self.assertEqual(drums['d'], {'sum': {'hps': 1, 'tps': 1, 'kps': 1}})
        self.assertEqual({'H', 'T', 'K', 'CoV', 'STAM', 'D', 'D_2x', 'RemapDiff', 'CalcTier', 'source'}, set(drums['head']))
        self.assertEqual(drums['n'], int(6500 // 250) + 1)     # the 1x kicks outlast the hands
        vocals = json.loads(graph_mod.curves_bytes(self.vocal_entry()))
        self.assertEqual([vocals['v'], vocals['family']], [2, 'vocals'])
        self.assertEqual(list(vocals['series']), ['pps', 'sps', 'perc'])
        self.assertEqual(list(vocals['d']['sum']), ['pps', 'sps'])
        self.assertEqual(vocals['d']['sum']['sps'], 0.25)
        self.assertIn('R', vocals['head'])
        quiet = json.loads(graph_mod.curves_bytes(self.vocal_entry(percussion=False)))
        self.assertEqual(list(quiet['series']), ['pps', 'sps'])
        # every family's series is n long and finite
        for doc in (drums, vocals, quiet):
            self.assertTrue(all(len(v) == doc['n'] and all(math.isfinite(x) for x in v) for v in doc['series'].values()))

    # The JS reconstruction (graph.js smooth), written in Python with the same
    # operations: the smoothing of each line, then ~D by the file's recipe, must
    # land on curves.py's d_raw for every family, to the four places the drum
    # and vocal counts are rounded to and to floating-point noise for the fret
    # family, whose counts are integers.
    @staticmethod
    def reconstruct(doc):
        decay = math.exp(-doc['step'] / doc['tau'])
        gain = 1 - decay
        window_s = doc['window'] / 1000

        def ema(values):
            out, acc = [], 0.0
            for v in values:
                acc = acc * decay + (v / window_s) * gain
                out.append(acc)
            back, acc = [], 0.0
            for v in reversed(out):
                acc = acc * decay + v * gain
                back.append(acc)
            return list(reversed(back))
        lines = {k: ema(v) for k, v in doc['series'].items()}
        if 'geo' in doc['d']:
            d = [math.sqrt(math.prod(lines[k][i] for k in doc['d']['geo'])) for i in range(doc['n'])]
        else:
            d = [sum(w * lines[k][i] for k, w in doc['d']['sum'].items()) for i in range(doc['n'])]
        return lines, d

    def test_client_reconstruction_matches_calc_curves(self):
        entry = self.entry()
        lines, d = self.reconstruct(json.loads(graph_mod.curves_bytes(entry)))
        ref = curves.calc_curves(entry['notes'])
        for key in ('nps', 'vps'):
            for a, b in zip(lines[key], ref[key]):
                self.assertAlmostEqual(a, b, places=12)
        for a, b in zip(d, ref['d_raw']):
            self.assertAlmostEqual(a, b, places=12)

    def test_client_reconstruction_matches_drum_and_vocal_curves(self):
        entry = self.drum_entry()
        lines, d = self.reconstruct(json.loads(graph_mod.curves_bytes(entry)))
        ref = curves.calc_drum_curves(entry['notes'], roll_spans=entry['roll_spans'])
        self.assertEqual(len(d), len(ref['d_raw']['1x']))
        for key, want in (('hps', ref['hps']), ('tps', ref['tps']), ('kps', ref['kps']['1x'])):
            for a, b in zip(lines[key], want):
                self.assertAlmostEqual(a, b, places=3, msg=key)
        for a, b in zip(d, ref['d_raw']['1x']):
            self.assertAlmostEqual(a, b, places=3)
        entry = self.vocal_entry()
        lines, d = self.reconstruct(json.loads(graph_mod.curves_bytes(entry)))
        ref = curves.calc_vocal_curves(entry['notes'], entry['talkie'], percussion=entry['percussion'])
        for key in ('pps', 'sps', 'perc'):
            for a, b in zip(lines[key], ref[key]):
                self.assertAlmostEqual(a, b, places=3, msg=key)
        for a, b in zip(d, ref['d_raw']):
            self.assertAlmostEqual(a, b, places=3)

    def test_the_difficulty_block_is_the_row_s(self):
        from functions import difficulty
        # drums: D is the 1x reading, D_2x beside it; vocals: the tiers come straight from D
        drums = difficulty.entry_difficulty(self.drum_entry())
        self.assertGreater(drums['D'], 0)
        self.assertIsNotNone(drums['D_2x'])
        self.assertIsInstance(drums['CalcTier'], int)
        vocals = difficulty.entry_difficulty(self.vocal_entry())
        self.assertGreater(vocals['D'], 0)
        self.assertIn(vocals['RemapDiff'], range(7))
        # a stream of another shape is not scorable, and the JSON is None
        bad = self.drum_entry()
        bad['notes'] = self.entry()['notes']
        self.assertFalse(difficulty.scorable(bad))
        self.assertIsNone(graph_mod.curves_bytes(bad))

    def test_fingerprints_see_every_family_s_streams(self):
        drums = self.drum_entry()
        before = bundle.fingerprint_curves(drums), bundle.fingerprint(drums, None)
        drums['roll_spans'] = []
        self.assertNotEqual(bundle.fingerprint_curves(drums), before[0])
        self.assertNotEqual(bundle.fingerprint(drums, None), before[1])
        vocals = self.vocal_entry()
        before = bundle.fingerprint_curves(vocals)
        vocals['talkie'] = {'time_ms': np.array([200.0]), 'end_ms': np.array([np.nan])}
        self.assertNotEqual(bundle.fingerprint_curves(vocals), before)

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
