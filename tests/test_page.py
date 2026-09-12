"""The library page (section 20): frames.counts from a small frame, and the page it renders."""

import datetime
import pathlib
import re
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
    """A page per song (sections 16 and 21): the facts, the tags, the page, the forward, the index, the sitemap, the robots line."""

    def test_song_facts(self):
        f = small_frames()
        f['Guitar']['Pct'] = [50, 100, 80, 100]
        facts = page.song_facts(f)
        self.assertEqual(sorted(facts), ['0000000000a1', '0000000000a2', '0000000000a3'])
        a1 = facts['0000000000a1']
        self.assertEqual((a1['title'], a1['artist'], a1['official']), ('Alpha', 'a', True))
        # the folder's parts in VALUE_ORDER order, every level each has, the tier once per part
        self.assertEqual([(p['type'], p['tier'], sorted(p['levels'])) for p in a1['parts']],
                         [('Lead', 3, ['Expert', 'Hard']), ('Bass', 1, ['Expert'])])
        self.assertEqual(a1['parts'][0]['levels']['Hard'], {'code': '00000001HG', 'd': 5.0, 'pct': 80, 'sheet': 'Guitar'})
        self.assertEqual(a1['code'], '00000001XG')
        self.assertEqual(page.song_image_code(a1), '00000001XG')
        self.assertEqual(page.share_lines(a1), ['Expert Lead: D 10.00, Calc Tier 3, at or above 50%', 'Expert Bass: D 4.00, Calc Tier 1'])
        self.assertEqual(page.share_lines(facts['0000000000a3']), ['Expert Rhythm: D 20.50, at or above 100%'])

    def test_a_song_without_expert_previews_its_highest_level(self):
        f = small_frames()
        f['Guitar'] = f['Guitar'][f['Guitar']['Code'] != '00000001XG']
        self.assertEqual(page.share_lines(page.song_facts(f)['0000000000a1'])[0], 'Hard Lead: D 5.00, Calc Tier 3')

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
        f = small_frames()
        f['Guitar']['Pct'] = [50, 100, 80, 100]
        facts = page.song_facts(f)
        out = page.render_song_page('0000000000a1', facts['0000000000a1'], names).decode('utf-8')
        self.assertIn('<title>Alpha by a: chart difficulty - Fretladder</title>', out)
        self.assertIn('<base href="../">', out)
        self.assertIn('<meta property="og:title" content="Alpha by a">', out)
        self.assertIn('<meta property="og:description" content="Expert Lead: D 10.00, Calc Tier 3, at or above 50%; Expert Bass: D 4.00, Calc Tier 1">', out)
        self.assertIn('<link rel="canonical" href="https://fretladder.com/song/0000000000a1.html">', out)
        # the picture (section 22): the first part's Expert graph, as og:image, in the JSON-LD and on the page
        self.assertIn('<meta property="og:image" content="https://fretladder.com/graph/00000001XG.png">', out)
        self.assertIn('<meta name="twitter:card" content="summary_large_image">', out)
        self.assertIn('<img src="graph/00000001XG.png" width="1920" height="840" loading="lazy" alt="Difficulty graph of Alpha by a', out)
        self.assertIn('"image": "https://fretladder.com/graph/00000001XG.png"', out)
        # the song in words
        self.assertIn('On Expert Lead it scores D 10.00, Calc Tier 3, at or above 50% of the site\u2019s Expert Guitar charts. On Expert Bass it scores D 4.00, Calc Tier 1.', out)
        # a page, not a redirect: the forward only with a query, no meta refresh
        self.assertIn('<script>if(location.search)location.replace(location.search)</script>', out)
        self.assertNotIn('http-equiv="refresh"', out)
        self.assertEqual(out.count('<script'), 3)                             # the forward, the theme, the JSON-LD
        self.assertIn('"@type": "MusicRecording"', out)
        self.assertIn('"byArtist": {"@type": "MusicGroup", "name": "a"}', out)
        # every level of every part, each a link into the table on that chart
        self.assertIn('<h1>Alpha</h1>', out)
        self.assertIn('<a href="./?code=00000001XG">10.00</a><small>50%</small>', out)
        self.assertIn('<a href="./?code=00000001HG">5.00</a><small>80%</small>', out)
        self.assertIn('<a href="./?code=00000001XB">4.00</a>', out)
        self.assertEqual(out.count('href="./?code='), 4)                     # three cells and the picture
        self.assertIn('Lead <span class="tier">Tier 3</span>', out)
        self.assertIn('<a href="methodology.html">', out)
        self.assertIn('href="./?song=0000000000a1"', out)
        self.assertIn('href="static/favicon.x.svg"', out)
        self.assertNotRegex(out, r'__[A-Z][A-Z_]*__')
        pages = page.render_song_pages(f, names, facts, LibraryPageTest().resolved())
        self.assertEqual(sorted(pages), ['song/0000000000a1.html', 'song/0000000000a2.html', 'song/0000000000a3.html'])
        self.assertTrue(all(len(b) < 5600 for b in pages.values()), [len(b) for b in pages.values()])
        # the game it came in, linked (section 22)
        self.assertIn('From <a href="game/pack-one.html">Pack One</a>, with every song of that setlist ranked by difficulty.', pages['song/0000000000a1.html'].decode('utf-8'))
        self.assertIn('href="game/pack-two.html"', pages['song/0000000000a3.html'].decode('utf-8'))

    def test_songs_index(self):
        facts = page.song_facts(small_frames())
        facts['0000000000a4'] = dict(facts['0000000000a1'], title='10 Years Gone', artist='z')
        facts['0000000000a5'] = dict(facts['0000000000a1'], title='(untitled)', artist='')
        out = page.render_songs_index(facts, {'favicon': 'static/f.svg'}).decode('utf-8')
        heads = re.findall(r'<h2 id="([^"]+)">', out)
        self.assertEqual(heads, ['0-9', 'A', 'B', 'G', 'other'])
        self.assertEqual(out.count('href="song/'), 5)
        self.assertIn('<a href="song/0000000000a4.html">10 Years Gone</a> <span class="by">z</span>', out)
        self.assertLess(out.index('song/0000000000a1.html'), out.index('song/0000000000a2.html'))
        self.assertIn('5 of them', out)
        self.assertEqual(out.count('<script'), 1)

    def test_sitemap_and_robots(self):
        files = {'index.html': b'', 'about.html': b'', 'changelog.html': b'', 'songs.html': b'', 'song/0000000000a2.html': b'', 'song/0000000000a1.html': b'',
                 'game/pack-one.html': b'', 'list/hardest-guitar.html': b''}
        out = page.render_sitemap(files, datetime.date(2026, 9, 11)).decode('utf-8')
        self.assertEqual(out.count('<url>'), 8)
        self.assertLess(out.index('fretladder.com/</loc>'), out.index('about.html'))
        self.assertLess(out.index('songs.html'), out.index('game/pack-one'))
        self.assertLess(out.index('game/pack-one'), out.index('list/hardest'))
        self.assertLess(out.index('list/hardest'), out.index('song/0000000000a1'))
        self.assertLess(out.index('0000000000a1'), out.index('0000000000a2'))
        self.assertIn('<lastmod>2026-09-11</lastmod>', out)
        self.assertTrue(page.robots_txt().startswith(page.ROBOTS))
        self.assertIn('Sitemap: https://fretladder.com/sitemap.xml', page.robots_txt())
        self.assertIn('Disallow: /graph/', page.ROBOTS)
        self.assertIn('Allow: /graph/*.png', page.ROBOTS)                     # the song pages' pictures (section 22)
        self.assertNotIn('data/', page.ROBOTS)                                # crawlers render the rows (section 21)

    def test_front_page_title(self):
        self.assertTrue(page.site_title().startswith('Fretladder: ') and 'Clone Hero' in page.site_title())

    def test_library_links_the_hardest_to_the_song_pages(self):
        out = page.render_library(LibraryPageTest().resolved(), small_frames(), {'favicon': 'static/f.svg'}).decode('utf-8')
        self.assertIn('<a href="song/0000000000a2.html">Beta</a>', out)
        # and the packs to their pages, the hardest blocks to the lists (section 22)
        self.assertIn('<a href="game/pack-one.html">Pack One</a>', out)
        self.assertIn('href="list/hardest-guitar.html"', out)
        self.assertIn('href="list/easiest-bass.html"', out)


class GameAndListPagesTest(unittest.TestCase):
    """A page per pack and the ranked lists (section 22)."""

    def setUp(self):
        self.f = small_frames()
        self.f['Guitar']['Pct'] = [50, 100, 80, 100]
        self.r = LibraryPageTest().resolved()
        self.names = {'favicon': 'static/f.svg'}

    def test_slugs(self):
        self.assertEqual(page.slug('Guitar Hero III: Legends of Rock'), 'guitar-hero-iii-legends-of-rock')
        self.assertEqual(page.slug('  ***  '), 'pack')
        self.assertEqual(page.pack_slugs(self.r), {'one': 'pack-one', 'two': 'pack-two'})

    def test_charts_by_folder(self):
        by = page.charts_by_folder(self.f, self.r)
        self.assertEqual(sorted(by), ['one', 'two'])
        self.assertEqual(sorted(by['one']), ['0000000000a1', '0000000000a2'])
        self.assertEqual(by['one']['0000000000a1']['parts']['Bass'], {'code': '00000001XB', 'd': 4.0, 'pct': None, 'tier': 1, 'sheet': 'Bass'})
        self.assertEqual(by['two']['0000000000a3']['parts']['Rhythm']['tier'], None)

    def test_game_pages(self):
        pages = page.render_game_pages(self.f, self.r, self.names)
        self.assertEqual(sorted(pages), ['game/pack-one.html', 'game/pack-two.html'])
        one = pages['game/pack-one.html'].decode('utf-8')
        self.assertIn('<title>Pack One setlist by difficulty - Fretladder</title>', one)
        self.assertIn('<base href="../">', one)
        self.assertIn('<meta property="og:url" content="https://fretladder.com/game/pack-one.html">', one)
        self.assertIn('2 songs, 4 charts, mixed, on the site since 7 September 2026', one)
        # ranked by Expert guitar D: Beta (20.50) before Alpha (10.00), each linking its page and its chart
        self.assertLess(one.index('song/0000000000a2.html'), one.index('song/0000000000a1.html'))
        self.assertIn('<a href="./?code=00000002XG">20.50</a><small>100%</small>', one)
        self.assertIn('<a href="./?code=00000001XB">4.00</a>', one)
        self.assertEqual(one.count('<script'), 1)
        self.assertNotRegex(one, r'__[A-Z][A-Z_]*__')

    def test_list_pages(self):
        pages = page.render_list_pages(self.f, self.r, self.names)
        self.assertEqual(sorted(pages), ['list/easiest-bass.html', 'list/easiest-guitar.html', 'list/hardest-bass.html',
                                         'list/hardest-customs-guitar.html', 'list/hardest-guitar.html'])
        hardest = pages['list/hardest-guitar.html'].decode('utf-8')
        self.assertIn('<title>The 2 hardest Guitar Hero and Rock Band songs on Expert guitar - Fretladder</title>', hardest)
        # official only, one entry per song at its hardest part, the game linked
        self.assertNotIn('0000000000a2', hardest)                                    # Beta is custom
        self.assertLess(hardest.index('song/0000000000a3.html'), hardest.index('song/0000000000a1.html'))
        self.assertIn('<a href="game/pack-two.html">Pack Two</a>', hardest)
        customs = pages['list/hardest-customs-guitar.html'].decode('utf-8')
        self.assertIn('song/0000000000a2.html', customs)
        self.assertNotIn('song/0000000000a1.html', customs)
        easiest = pages['list/easiest-guitar.html'].decode('utf-8')
        self.assertLess(easiest.index('song/0000000000a1.html'), easiest.index('song/0000000000a3.html'))


if __name__ == '__main__':
    unittest.main()
