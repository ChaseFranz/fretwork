"""The synthetic library: deterministic, parseable in-process, and its totals as the table says."""

import hashlib
import pathlib
import tempfile
import unittest

from functions import fret_density as density, fret_formula as formula, instruments
from parsers import chart_parser, ini_parser, mid_parser
from tests import fixture


def digest(root):
    out = {}
    for path in sorted(pathlib.Path(root).rglob('*')):
        if path.is_file():
            out[str(path.relative_to(root))] = hashlib.sha1(path.read_bytes()).hexdigest()
    return out


class FixtureTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.lib = fixture.write(cls.tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_deterministic(self):
        with tempfile.TemporaryDirectory() as again:
            fixture.write(again)
            self.assertEqual(digest(self.tmp.name), digest(again))

    def test_totals_from_the_table(self):
        lib = self.lib
        self.assertEqual(lib.ini_count, 16)
        self.assertEqual(len(lib.charted), 14)
        self.assertEqual(len(lib.unusable), 2)          # the ini-only song and the broken mid
        self.assertEqual(len(lib.errors), 1)
        self.assertEqual(lib.codes, 52)                  # 48 five-fret + 2 drums + 2 vocals
        self.assertEqual(lib.rows_by_sheet, {'Guitar': 36, 'Bass': 11, 'Keys': 1, 'Drums': 2, 'Vocals': 2})
        self.assertEqual(lib.official_rows, 29)
        self.assertEqual(sum(lib.rows_by_sheet.values()) - lib.official_rows, 23)
        landing = sum(1 for s in lib.charted if s.official
                      for i in ('guitar', 'coop', 'rhythm') if 'X' in s.parts.get(i, ''))
        self.assertEqual(landing, 9)

    def test_files_are_only_the_three_the_parsers_read(self):
        names = {p.name for p in pathlib.Path(self.tmp.name).rglob('*') if p.is_file()}
        self.assertEqual(names, {'song.ini', 'notes.chart', 'notes.mid'})
        self.assertEqual(len(list(pathlib.Path(self.tmp.name).rglob('song.ini'))), 16)
        both = [s for s in self.lib.songs if s.fmt == 'both']
        self.assertEqual(len(both), 1)
        folder = pathlib.Path(self.tmp.name) / both[0].pack / both[0].folder
        self.assertTrue((folder / 'notes.chart').is_file() and (folder / 'notes.mid').is_file())

    # In-process, no pools: every generated file parses to the parts and levels the
    # table names; the truncated mid raises the parser's own EOFError.
    def test_parsers_accept_every_file(self):
        for song in self.lib.songs:
            folder = pathlib.Path(self.tmp.name) / song.pack / song.folder
            with self.subTest(song=song.folder):
                meta = ini_parser.ini_metadata(folder / 'song.ini')
                self.assertEqual(meta['Release'], song.release)
                self.assertEqual(meta['Official'], song.official)
                if song.fmt == fixture.BROKEN:
                    with self.assertRaises((EOFError, OSError)):
                        mid_parser.mid_notes(folder / 'notes.mid')
                    continue
                if not song.charted:
                    continue
                parsed = (chart_parser.chart_notes(folder / 'notes.chart') if song.source_format == 'chart'
                          else mid_parser.mid_notes(folder / 'notes.mid'))
                got = {k: sorted(v) for k, v in parsed['instruments'].items()}
                want = {k: sorted(song.levels(k)) for k in song.parts}
                self.assertEqual(got, want)
                for key, levels in parsed['instruments'].items():
                    for stream in levels.values():
                        notes = stream['notes']
                        if key == 'drums':
                            self.assertIn('hand_mask', notes)
                            continue
                        if key == 'vocals':
                            # a sung line with slides, and the talkie and percussion streams beside it
                            self.assertEqual(sorted(levels), ['expert'])
                            self.assertTrue(notes['is_slide'].any() and not notes['is_slide'].all())
                            self.assertGreater(len(stream['talkie']['time_ms']), 0)
                            self.assertGreater(len(stream['percussion']['time_ms']), 0)
                            continue
                        self.assertEqual(str(notes['time_ms'].dtype), 'float64')
                        self.assertEqual(str(notes['lanes'].dtype), 'uint8')
                        self.assertTrue((notes['time_ms'][1:] >= notes['time_ms'][:-1]).all())

    def test_detag_and_encodings(self):
        c4 = pathlib.Path(self.tmp.name) / 'Fixture Pack C' / 'C4 - Less Than More'
        meta = ini_parser.ini_metadata(c4 / 'song.ini')
        self.assertEqual(meta['Name'], 'Less < More')
        self.assertEqual(meta['Artist'], 'René Escapé')
        a3 = pathlib.Path(self.tmp.name) / 'Fixture Pack A' / 'A3 - Midi Mirror'
        raw = (a3 / 'song.ini').read_bytes()
        self.assertTrue(raw.startswith(b'\xef\xbb\xbf') and b'\r\n' in raw)
        self.assertEqual(ini_parser.ini_metadata(a3 / 'song.ini')['Name'], 'Midi Mirror')

    def test_enhanced_opens_and_a_folded_open_note(self):
        c6 = pathlib.Path(self.tmp.name) / 'Fixture Pack C' / 'C6 - Enhanced Opens'
        lanes = mid_parser.mid_notes(c6 / 'notes.mid')['instruments']['guitar']['expert']['notes']['lanes']
        self.assertTrue(any(int(v) & 0x80 for v in lanes))
        a1 = pathlib.Path(self.tmp.name) / 'Fixture Pack A' / 'A1 - Grid Runner'
        lanes = chart_parser.chart_notes(a1 / 'notes.chart')['instruments']['guitar']['expert']['notes']['lanes']
        self.assertTrue(any(int(v) & 0x80 for v in lanes))
        self.assertFalse(any(int(v) & 0x60 for v in lanes))     # bits 5-6 never set

    # 36 Guitar-sheet rows, three of them repeats by design, must give more than
    # RANGE_MIN_DISTINCT (25) distinct D values after the 2-place rounding analyze
    # applies, so the page's range box appears; the test wants 30 so a small
    # drift cannot land on the threshold.
    def test_guitar_d_values_distinct(self):
        seen = set()
        for song in self.lib.charted:
            folder = pathlib.Path(self.tmp.name) / song.pack / song.folder
            parsed = (chart_parser.chart_notes(folder / 'notes.chart') if song.source_format == 'chart'
                      else mid_parser.mid_notes(folder / 'notes.mid'))
            for key in instruments.SHEET_GROUPS['Guitar']:
                for stream in parsed['instruments'].get(key, {}).values():
                    metrics = density.calc_metrics(stream['notes'])
                    seen.add(round(formula.calc_nvcov(metrics)['D'], 2))
        self.assertGreaterEqual(len(seen), 30, sorted(seen))


if __name__ == '__main__':
    unittest.main()
