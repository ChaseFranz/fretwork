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
        'Code': ['00000001XG', '00000002XG', '00000001HG', '00000003XG'], 'Song Title': ['Alpha', 'Beta', 'Alpha', 'Gamma'],
        'Artist': ['a', 'b', 'a', 'c'], 'Type': ['Lead', 'Lead', 'Lead', 'Rhythm'],
        'Level': ['Expert', 'Expert', 'Hard', 'Expert'], 'D': [10.0, 20.5, 5.0, 20.5],
        'CalcTier': [3, 5, 3, None], 'Official': [True, False, True, True],
        'SongKey': ['0000000000a1', '0000000000a2', '0000000000a1', '0000000000a3'], 'NotesHash': ['h1', 'h1', 'h3', 'h4'],
    })
    bass = pd.DataFrame({
        'Code': ['00000001XB'], 'Song Title': ['Alpha'], 'Artist': ['a'], 'Type': ['Bass'], 'Level': ['Expert'],
        'D': [4.0], 'CalcTier': [1], 'Official': [True], 'SongKey': ['0000000000a1'], 'NotesHash': ['h9'],
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
        self.assertEqual([r['code'] for r in g['hardest']], ['00000002XG', '00000003XG', '00000001XG'])
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
        return packs.Resolved(reg, pathlib.Path('/lib'), {}, {'00000001XG': 'one', '00000002XG': 'one', '00000001HG': 'one', '00000003XG': 'two', '00000001XB': 'one'},
                              {'one': 2, 'two': 1}, (), (), ())

    def test_render_library(self):
        names = {'favicon': 'static/favicon.x.svg'}
        out = page.render_library(self.resolved(), small_frames(), names).decode('utf-8')
        self.assertEqual(out.count('<h2>'), 5)
        self.assertIn('2 packs, 3 songs, 5 charts', out)
        self.assertIn('<a href="./?code=00000002XG">Beta</a>', out)
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


class SongPagesTest(unittest.TestCase):
    """A page per song (section 16): the facts, the tags, the forward, the sitemap, the robots line."""

    def test_song_facts(self):
        f = small_frames()
        f['Guitar']['Pct'] = [50, 100, 80, 100]
        facts = page.song_facts(f)
        self.assertEqual(sorted(facts), ['0000000000a1', '0000000000a2', '0000000000a3'])
        a1 = facts['0000000000a1']
        self.assertEqual((a1['title'], a1['artist']), ('Alpha', 'a'))
        # the folder's parts in VALUE_ORDER order, each at Expert when it has one
        self.assertEqual([(l['type'], l['level'], l['d'], l['tier'], l['pct']) for l in a1['lines']],
                         [('Lead', 'Expert', 10.0, 3, 50), ('Bass', 'Expert', 4.0, 1, None)])
        self.assertEqual(page.share_line(a1['lines'][0]), 'Expert Lead: D 10.00, Calc Tier 3, at or above 50%')
        self.assertEqual(page.share_line(facts['0000000000a3']['lines'][0]), 'Expert Rhythm: D 20.50, at or above 100%')

    def test_a_song_without_expert_uses_its_highest_level(self):
        f = small_frames()
        f['Guitar'] = f['Guitar'][f['Guitar']['Code'] != '00000001XG']
        line = page.song_facts(f)['0000000000a1']['lines'][0]
        self.assertEqual((line['type'], line['level'], line['d']), ('Lead', 'Hard', 5.0))

    def test_official_folder_leads(self):
        f = small_frames()
        g = f['Guitar']
        # a custom copy of Alpha in another folder, alphabetically first: the official one still names the page
        copy = g.iloc[[0]].copy()
        copy['Code'] = '00000000XG'; copy['Song Title'] = 'AAlpha (custom)'; copy['Official'] = False
        f['Guitar'] = pd.concat([copy, g], ignore_index=True)
        self.assertEqual(page.song_facts(f)['0000000000a1']['title'], 'Alpha')

    def test_render_song_page(self):
        names = {'favicon': 'static/favicon.x.svg'}
        facts = page.song_facts(small_frames())
        out = page.render_song_page('0000000000a1', facts['0000000000a1'], names).decode('utf-8')
        self.assertIn('<title>Alpha - a - Fretladder</title>', out)
        self.assertIn('<meta property="og:title" content="Alpha - a">', out)
        self.assertIn('<meta property="og:description" content="Expert Lead: D 10.00, Calc Tier 3; Expert Bass: D 4.00, Calc Tier 1">', out)
        self.assertIn('<link rel="canonical" href="https://fretladder.com/song/0000000000a1.html">', out)
        self.assertNotIn('og:image', out)
        self.assertIn('location.replace("../"+(location.search||"?song=0000000000a1"))', out)
        self.assertIn('content="0; url=../?song=0000000000a1"', out)
        self.assertIn('href="../static/favicon.x.svg"', out)
        self.assertEqual(out.count('<script'), 2)                             # the forward and the theme
        self.assertNotRegex(out, r'__[A-Z][A-Z_]*__')
        pages = page.render_song_pages(small_frames(), names)
        self.assertEqual(sorted(pages), ['song/0000000000a1.html', 'song/0000000000a2.html', 'song/0000000000a3.html'])
        self.assertTrue(all(len(b) < 2200 for b in pages.values()), [len(b) for b in pages.values()])

    def test_sitemap_and_robots(self):
        files = {'index.html': b'', 'about.html': b'', 'changelog.html': b'', 'song/0000000000a2.html': b'', 'song/0000000000a1.html': b''}
        out = page.render_sitemap(files, datetime.date(2026, 9, 11)).decode('utf-8')
        self.assertEqual(out.count('<url>'), 5)
        self.assertLess(out.index('fretladder.com/</loc>'), out.index('about.html'))
        self.assertLess(out.index('0000000000a1'), out.index('0000000000a2'))
        self.assertIn('<lastmod>2026-09-11</lastmod>', out)
        self.assertTrue(page.robots_txt().startswith(page.ROBOTS))
        self.assertIn('Sitemap: https://fretladder.com/sitemap.xml', page.robots_txt())


if __name__ == '__main__':
    unittest.main()
