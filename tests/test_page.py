"""The library page (section 20): frames.counts from a small frame, and the page it renders."""

import datetime
import pathlib
import unittest

import pandas as pd

from functions import labels, packs
from web import boot, frames, page

REPO = pathlib.Path(__file__).resolve().parents[1]


def small_frames():
    guitar = pd.DataFrame({
        'Code': ['1XG', '2XG', '3HG', '4XG'], 'Song Title': ['Alpha', 'Beta', 'Alpha', 'Gamma'],
        'Artist': ['a', 'b', 'a', 'c'], 'Type': ['Lead', 'Lead', 'Lead', 'Rhythm'],
        'Level': ['Expert', 'Expert', 'Hard', 'Expert'], 'D': [10.0, 20.5, 5.0, 20.5],
        'CalcTier': [3, 5, 3, None], 'Official': [True, False, True, True],
        'SongKey': ['k1', 'k2', 'k1', 'k3'], 'NotesHash': ['h1', 'h1', 'h3', 'h4'],
    })
    bass = pd.DataFrame({
        'Code': ['1XB'], 'Song Title': ['Alpha'], 'Artist': ['a'], 'Type': ['Bass'], 'Level': ['Expert'],
        'D': [4.0], 'CalcTier': [1], 'Official': [True], 'SongKey': ['k1'], 'NotesHash': ['h9'],
    })
    return {'Guitar': guitar, 'Bass': bass}


class CountsTest(unittest.TestCase):

    def test_counts(self):
        out = frames.counts(small_frames())
        g = out['sheets']['Guitar']
        self.assertEqual(g['levels'], {'Expert': (3, 2), 'Hard': (1, 1)})   # 1XG and 2XG share a hash and a part; 4XG is Rhythm
        self.assertEqual(g['rows'], 4)
        self.assertEqual(g['songs'], 3)
        self.assertEqual(g['tiers'], {3: 1, 5: 1})                            # the tierless row is not a tier
        self.assertEqual(g['official'], (2, 1))
        self.assertEqual([r['code'] for r in g['hardest']], ['2XG', '4XG', '1XG'])
        self.assertEqual(g['hardest'][1]['tier'], None)
        self.assertEqual(out['sheets']['Bass']['levels'], {'Expert': (1, 1)})
        self.assertEqual(out['songs'], 3)                                     # k1 is on both sheets, once
        self.assertEqual(out['rows'], 5)

    def test_distinct_is_within_type_and_level(self):
        f = small_frames()
        f['Guitar'].loc[3, 'Type'] = 'Lead'                                   # now 4XG shares 2XG's part, not its hash
        f['Guitar'].loc[3, 'NotesHash'] = 'h1'
        self.assertEqual(frames.counts(f)['sheets']['Guitar']['levels']['Expert'], (3, 1))

    def test_without_hashes_distinct_is_rows(self):
        f = small_frames()
        f['Guitar'] = f['Guitar'].drop(columns=['NotesHash'])
        self.assertEqual(frames.counts(f)['sheets']['Guitar']['levels']['Expert'], (3, 3))


class LibraryPageTest(unittest.TestCase):

    def resolved(self):
        reg = packs.Registry(path=pathlib.Path('packs.toml'), packs=(
            packs.Pack(name='Pack One', folder='one', source='https://example.com/one', added=datetime.date(2026, 9, 7), notes=''),
            packs.Pack(name='Pack Two', folder='two', source='', added=datetime.date(2026, 9, 8), notes=''),
        ), changes=())
        return packs.Resolved(reg, pathlib.Path('/lib'), {}, {'1XG': 'one', '2XG': 'one', '3HG': 'one', '4XG': 'two', '1XB': 'one'},
                              {'one': 2, 'two': 1}, (), (), ())

    def test_render_library(self):
        names = {'favicon': 'static/favicon.x.svg'}
        out = page.render_library(self.resolved(), small_frames(), names).decode('utf-8')
        self.assertEqual(out.count('<h2>'), 5)
        self.assertIn('2 packs, 3 songs, 5 charts', out)
        self.assertIn('<a href="./?code=2XG">Beta</a>', out)
        self.assertIn('<span class="bar" style="width:100.0%"></span>', out)
        self.assertIn('href="./?f.Added=2026-09-07&amp;f.Level=Expert"', out)
        self.assertIn('<a href="https://example.com/one" rel="noopener">', out)
        self.assertIn('<td>Mixed</td>', out)                                  # pack one: 1XG official, 2XG custom
        self.assertIn('<td>Official</td>', out)                               # pack two: 4XG alone
        self.assertIn(page.THEME_SCRIPT, out)
        self.assertEqual(out.count('<script'), 1)
        self.assertNotRegex(out, r'__[A-Z][A-Z_]*__')

    def test_library_pages_need_the_pack_join(self):
        self.assertEqual(page.library_pages(None, small_frames(), {}), {})

    def test_footer_lists_only_the_pages_the_site_has(self):
        payload = boot.boot_payload({}, {}, None, [p for p in labels.DOC_PAGES if p[0] != 'library.html'])
        self.assertNotIn(['library.html', 'library'], payload['docPages'])
        self.assertIn(['about.html', 'about'], payload['docPages'])
        self.assertIn(['library.html', 'library'], boot.boot_payload({}, {})['docPages'])


if __name__ == '__main__':
    unittest.main()
