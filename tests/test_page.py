"""The library page (section 20): frames.counts from a small frame, and the page it renders."""

import datetime
import pathlib
import tempfile
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


class UnifyTest(unittest.TestCase):
    """frames.unify (section 23): one D, Level and NoteCount per sheet, whatever the profile calls them."""

    def test_drums_read_at_1x_and_vocals_at_expert(self):
        drums = pd.DataFrame({'Code': ['00000001XD'], 'Song Title': ['Alpha'], 'Artist': ['a'], 'Level': ['Expert'], 'Type': ['Drums'],
                              'NoteCount_1x': [100], 'NoteCount_2x': [120], 'D_1x': [9.5], 'D_2x': [11.0]})
        vocals = pd.DataFrame({'Code': ['00000001XV'], 'Song Title': ['Alpha'], 'Artist': ['a'], 'Type': ['Vocals'], 'D': [4.0]})
        out = frames.unify({'Drums': drums, 'Vocals': vocals, 'Guitar': small_frames()['Guitar']})
        self.assertEqual(list(out['Drums'].columns), ['Code', 'Song Title', 'Artist', 'Level', 'Type', 'NoteCount', 'NoteCount_2x', 'D', 'D_2x'])
        self.assertEqual(out['Drums']['D'][0], 9.5)
        self.assertEqual(list(out['Vocals'].columns), ['Code', 'Song Title', 'Artist', 'Level', 'Type', 'D'])
        self.assertEqual(out['Vocals']['Level'][0], 'Expert')
        self.assertEqual(list(out['Guitar'].columns), list(small_frames()['Guitar'].columns))
        # the counts and the percentile read the unified names
        frames.add_percentiles(out)
        self.assertEqual(int(out['Drums']['Pct'][0]), 100)
        self.assertEqual(frames.counts(out)['sheets']['Vocals']['levels'], {'Expert': (1, 1)})


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
        self.assertIn('href="./#f.Added=2026-09-07&amp;f.Level=Expert"', out)
        self.assertIn('<a href="https://example.com/one" rel="noopener">', out)
        self.assertIn('<td>Mixed</td>', out)                                  # pack one: 1XG official, 2XG custom
        self.assertIn('<td>Official</td>', out)                               # pack two: 4XG alone
        self.assertIn(page.THEME_SCRIPT, out)
        self.assertEqual(out.count('<script'), 1)                             # the theme's, from render_library alone
        # through library_pages the Dataset block rides along (section 24), and it is data, not a script that runs
        with_ld = page.library_pages(self.resolved(), small_frames(), {'favicon': 'static/favicon.x.svg'},
                                     {'Guitar': {'file': 'data/guitar.1.json'}}, datetime.date(2026, 9, 19))['library.html'].decode('utf-8')
        self.assertEqual(with_ld.count('<script>'), 1)
        self.assertEqual(with_ld.count('<script type="application/ld+json">'), 1)
        self.assertIn('"@type": "Dataset"', with_ld)
        self.assertIn('"dateModified": "2026-09-19"', with_ld)
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
        self.assertEqual(a1['parts'][0]['levels']['Hard'], {'code': '00000001HG', 'd': 5.0, 'pct': 80, 'sheet': 'Guitar', 'notes': None, 'secs': None})
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
        self.assertIn('<title>Alpha by a: Clone Hero chart difficulty</title>', out)
        self.assertIn('<base href="../">', out)
        self.assertIn('<meta property="og:title" content="Alpha by a">', out)
        self.assertIn('<meta property="og:description" content="How hard is Alpha by a in Clone Hero? Expert Lead: D 10.00, Calc Tier 3, at or above 50%; Expert Bass: D 4.00, Calc Tier 1">', out)
        self.assertIn('<link rel="canonical" href="https://fretladder.com/song/0000000000a1.html">', out)
        # the picture (section 22): the first part's Expert graph, as og:image, in the JSON-LD and on the page
        self.assertIn('<meta property="og:image" content="https://fretladder.com/graph/00000001XG.png">', out)
        self.assertIn('<meta name="twitter:card" content="summary_large_image">', out)
        self.assertIn('<img src="graph/00000001XG.png" width="1908" height="774" loading="lazy" alt="Difficulty graph of Alpha by a', out)
        self.assertIn('"image": "https://fretladder.com/graph/00000001XG.png"', out)
        # the song in words
        self.assertIn('On Expert Lead it scores D 10.00, Calc Tier 3, at or above 50% of the site\u2019s Expert Guitar charts. On Expert Bass it scores D 4.00, Calc Tier 1.', out)
        # a page, not a redirect: the forward only with a query, no meta refresh
        self.assertIn('<script>if(location.search)location.replace(location.search)</script>', out)
        self.assertNotIn('http-equiv="refresh"', out)
        self.assertEqual(out.count('<script'), 3)                             # the forward, the theme, the JSON-LD
        self.assertIn('"@type": "MusicRecording"', out)
        self.assertIn('"byArtist": {"@type": "MusicGroup", "name": "a"}', out)
        # section 24: the game in the title, the question in the description, the artist in the h1,
        # the breadcrumb beside the recording, and every app link by fragment
        self.assertIn('<title>Alpha by a: Clone Hero chart difficulty</title>', out)
        self.assertIn('content="How hard is Alpha by a in Clone Hero? Expert Lead: D 10.00', out)
        self.assertIn('<h1>Alpha by a</h1>', out)
        self.assertIn('<p class="by">A Clone Hero custom chart.</p>', out)     # rendered without its game here; with one, FindabilityTest below
        self.assertIn('"@type": "BreadcrumbList"', out)
        self.assertIn('{"@type": "ListItem", "position": 2, "name": "Alpha", "item": "https://fretladder.com/song/0000000000a1.html"}', out)
        # every level of every part, each a link into the table on that chart
        self.assertIn('<a href="./#code=00000001XG">10.00</a><small>50%</small>', out)
        self.assertIn('<a href="./#code=00000001HG">5.00</a><small>80%</small>', out)
        self.assertIn('<a href="./#code=00000001XB">4.00</a>', out)
        self.assertEqual(out.count('href="./#code='), 4)                     # three cells and the picture
        self.assertNotIn('href="./?', out)
        self.assertIn('Lead <span class="tier">Tier 3</span>', out)
        self.assertIn('<a href="methodology.html">', out)
        self.assertIn('href="./#song=0000000000a1"', out)
        self.assertIn('href="static/favicon.x.svg"', out)
        self.assertNotRegex(out, r'__[A-Z][A-Z_]*__')
        pages = page.render_song_pages(f, names, facts, LibraryPageTest().resolved())
        self.assertEqual(sorted(pages), ['song/0000000000a1.html', 'song/0000000000a2.html', 'song/0000000000a3.html'])
        self.assertTrue(all(len(b) < 7000 for b in pages.values()), [len(b) for b in pages.values()])     # about 6.5 KB with the ladder (section 25)
        # the game it came in, linked (section 22)
        self.assertIn('From <a href="game/pack-one.html">Pack One</a>, whose every song is ranked by difficulty on its page.', pages['song/0000000000a1.html'].decode('utf-8'))
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
        self.assertIn('<title>Pack One song list ranked by difficulty - Fretladder</title>', one)
        self.assertIn('<h1>Pack One song list ranked by difficulty</h1>', one)
        self.assertIn('<p class="site"><a href="./">Fretladder</a></p>', one)
        self.assertIn('<base href="../">', one)
        self.assertIn('<meta property="og:url" content="https://fretladder.com/game/pack-one.html">', one)
        self.assertIn('2 songs, 4 charts, mixed, on the site since 7 September 2026', one)
        # ranked by Expert guitar D: Beta (20.50) before Alpha (10.00), each linking its page and its chart
        self.assertLess(one.index('song/0000000000a2.html'), one.index('song/0000000000a1.html'))
        self.assertIn('<a href="./#code=00000002XG">20.50</a><small>100%</small>', one)
        self.assertIn('<a href="./#code=00000001XB">4.00</a>', one)
        self.assertEqual(one.count('<script>'), 1)                            # the theme's; the JSON-LD block is data
        self.assertEqual(one.count('<script type="application/ld+json">'), 1)
        self.assertIn('"@type": "ItemList"', one)
        self.assertIn('{"@type": "ListItem", "position": 1, "name": "Beta", "url": "https://fretladder.com/song/0000000000a2.html"}', one)
        self.assertNotRegex(one, r'__[A-Z][A-Z_]*__')

    def test_list_pages(self):
        # one song is not a list (LIST_LEAST, section 24): the bass lists and the customs list need a second song
        self.assertEqual(sorted(page.render_list_pages(self.f, self.r, self.names)), ['list/easiest-guitar.html', 'list/hardest-guitar.html'])
        # Delta, official, on both sheets (a song's kind is the song's, so its bass chart counts as official too); Epsilon, a second custom
        rows = [('Guitar', '00000005XG', 'Delta', 'd', 'Lead', 15.0, 4, True, '0000000000a5', 'h5'), ('Bass', '00000005XB', 'Delta', 'd', 'Bass', 3.0, 1, True, '0000000000a5', 'h6'),
                ('Guitar', '00000006XG', 'Epsilon', 'e', 'Lead', 12.0, 3, False, '0000000000a6', 'h7')]
        for sheet, code, title, artist, part, d, tier, official, key, h in rows:
            self.f[sheet] = pd.concat([self.f[sheet], pd.DataFrame([{'Code': code, 'Song Title': title, 'Artist': artist, 'Type': part, 'Level': 'Expert',
                                                                     'D': d, 'CalcTier': tier, 'Official': official, 'SongKey': key, 'NotesHash': h}])], ignore_index=True)
            self.r.folder_by_code[code] = 'one'
        pages = page.render_list_pages(self.f, self.r, self.names)
        self.assertEqual(sorted(pages), ['list/easiest-bass.html', 'list/easiest-guitar.html', 'list/hardest-bass.html',
                                         'list/hardest-customs-guitar.html', 'list/hardest-guitar.html'])
        hardest = pages['list/hardest-guitar.html'].decode('utf-8')
        self.assertIn('<title>The 3 hardest Guitar Hero and Rock Band songs on Expert guitar - Fretladder</title>', hardest)
        # official only, one entry per song at its hardest part, the game linked
        self.assertNotIn('0000000000a2', hardest)                                    # Beta is custom
        self.assertLess(hardest.index('song/0000000000a3.html'), hardest.index('song/0000000000a1.html'))
        self.assertIn('<a href="game/pack-two.html">Pack Two</a>', hardest)
        customs = pages['list/hardest-customs-guitar.html'].decode('utf-8')
        self.assertIn('song/0000000000a2.html', customs)
        self.assertNotIn('song/0000000000a1.html', customs)
        easiest = pages['list/easiest-guitar.html'].decode('utf-8')
        self.assertLess(easiest.index('song/0000000000a1.html'), easiest.index('song/0000000000a3.html'))
        # section 24: the method paragraph, the ItemList, the breadcrumb through the library, the More block,
        # and the top entries' pictures once the facts are given (none without them)
        self.assertIn('not a poll', hardest)
        self.assertIn('"@type": "ItemList"', hardest)
        self.assertIn('"name": "The library", "item": "https://fretladder.com/library.html"', hardest)
        self.assertIn('<div class="more"><h2>Every source on the site: the games, their DLC and the custom packs</h2><ul><li><a href="game/pack-one.html">Pack One</a></li>', hardest)
        self.assertIn('<a href="list/easiest-bass.html">Easiest bass</a>', hardest)
        self.assertNotIn('<p class="pics">', hardest)
        facts = page.song_facts(self.f)
        with_pics = page.render_list_pages(self.f, self.r, self.names, facts)['list/hardest-guitar.html'].decode('utf-8')
        self.assertEqual(with_pics.count('<p class="pics">'), 1)
        self.assertIn('<a href="song/0000000000a3.html"><img src="graph/00000003XG.png" width="1908" height="774" loading="lazy" alt="Difficulty graph of Gamma by c:', with_pics)
        self.assertIn('<b>1. Gamma</b> c, D 20.50</a>', with_pics)
        self.assertNotIn('href="./?', with_pics)


if __name__ == '__main__':
    unittest.main()


class FindabilityTest(unittest.TestCase):
    """Section 24: the front page's guide, the titles, the description, the dates, the JSON-LD, the key file."""

    def setUp(self):
        self.f = small_frames()
        self.r = LibraryPageTest().resolved()
        self.facts = page.song_facts(self.f)
        self.names = {'favicon': 'static/f.svg', 'script': 'static/app.x.js', 'style': 'static/app.x.css', 'bootstrap': 'static/b.css'}

    def test_static_section_is_a_details_block_closed_before_the_first_paint(self):
        stats = frames.counts(self.f)
        pools = page.list_pools(self.f, self.r)
        out = page.static_section(self.f, self.r, stats, list(pools), self.facts, True)
        self.assertTrue(out.startswith('<details id="static" open>\n<summary>'))
        self.assertTrue(out.endswith('</details>\n<script>document.getElementById("static").open=false</script>'))
        self.assertEqual(out.count('<h1>'), 1)
        self.assertIn('<h1>Difficulty ratings for Guitar Hero, Rock Band and Clone Hero charts</h1>', out)
        self.assertNotIn('every Guitar Hero', out)
        self.assertIn('5 charts of 3 songs from 2 sources, the games, their DLC and the custom packs', out)
        self.assertIn('<a href="https://github.com/Staycation44/fretwork" rel="noopener">fretwork</a>', out)
        # the hardest per sheet link their song pages, the games and lists their pages, the document pages theirs
        self.assertIn('<h2>The hardest Expert Guitar charts</h2>', out)
        self.assertIn('<td class="r">1</td><td><a href="song/0000000000a2.html">Beta</a></td>', out)
        self.assertIn('<li><a href="game/pack-one.html">Pack One</a></li>', out)
        self.assertIn('<li><a href="list/hardest-guitar.html">Hardest guitar</a></li>', out)
        self.assertIn('<li><a href="library.html">The library</a></li>', out)
        self.assertNotIn('href="./?', out)
        # without a songs index the Songs page is not linked; without a pack join, no games
        self.assertNotIn('songs.html', page.static_section(self.f, self.r, stats, list(pools), self.facts, False))
        self.assertNotIn('game/', page.static_section(self.f, None, stats, [], self.facts, True))

    def test_render_page_carries_the_guide_above_the_footer_and_the_website_block(self):
        out = page.render_page('t', 's', self.names, '{}', public=True, linked=True, static_html='<details id="static" open><summary>s</summary><h1>x</h1></details>')
        out = out.decode('utf-8') if isinstance(out, bytes) else out
        self.assertIn('<p class="h6 mb-0 fw-semibold" id="brand">Fretladder</p>', out)
        self.assertLess(out.index('id="body"'), out.index('<details id="static"'))
        self.assertLess(out.index('<details id="static"'), out.index('<footer'))
        self.assertEqual(out.count('<h1'), 1)
        self.assertIn('"@type": "WebSite"', out)
        self.assertIn('"urlTemplate": "https://fretladder.com/?q={search_term_string}"', out)
        self.assertIn('<meta property="og:site_name" content="Fretladder">', out)
        serve = page.render_page('t', 's', self.names, '{}', public=False)
        serve = serve.decode('utf-8') if isinstance(serve, bytes) else serve
        self.assertNotIn('id="static"', serve)
        self.assertNotIn('ld+json', serve)

    def test_song_titles_name_the_game_and_tell_customs_apart(self):
        official = dict(self.facts['0000000000a1'], official=True, release='Guitar Hero III')
        out = page.render_song_page('0000000000a1', official, self.names, {'name': 'Guitar Hero III', 'slug': 'gh3'}).decode('utf-8')
        self.assertIn('<title>Alpha by a: Guitar Hero III chart difficulty</title>', out)
        self.assertIn('<p class="by">A Guitar Hero III chart.</p>', out)
        self.assertIn('content="How hard is Alpha by a in Guitar Hero III? Expert Lead: D 10.00', out)
        self.assertIn('{"@type": "ListItem", "position": 2, "name": "Guitar Hero III", "item": "https://fretladder.com/game/gh3.html"}', out)
        dlc = page.render_song_page('0000000000a1', official, self.names, {'name': 'GH3 DLC', 'slug': 'gh3-dlc'}).decode('utf-8')
        self.assertIn('<p class="by">A Guitar Hero III chart, from the GH3 DLC pack.</p>', dlc)
        custom = page.render_song_page('0000000000a1', self.facts['0000000000a1'], self.names, {'name': 'Pack One', 'slug': 'pack-one'}, disambiguate=True).decode('utf-8')
        self.assertIn('<title>Alpha by a: Clone Hero (Pack One) chart difficulty</title>', custom)
        self.assertIn('<p class="by">A Clone Hero custom chart, from the Pack One pack.</p>', custom)
        alone = page.render_song_page('0000000000a1', self.facts['0000000000a1'], self.names).decode('utf-8')
        self.assertIn('<p class="by">A Clone Hero custom chart.</p>', alone)
        # the same custom in two packs: both titles carry their pack, and no two pages share a title
        f = small_frames()
        f['Guitar'].loc[3, 'Song Title'] = 'Alpha'
        f['Guitar'].loc[3, 'Artist'] = 'a'
        pages = page.render_song_pages(f, self.names, page.song_facts(f), self.r)
        titles = [re.search(r'<title>(.*?)</title>', p.decode('utf-8')).group(1) for p in pages.values()]
        self.assertEqual(sum(1 for t in titles if t.startswith('Alpha by a: Clone Hero (Pack')), 2, titles)
        self.assertEqual(len(set(titles)), len(titles), titles)

    def test_song_description_keeps_whole_parts_within_a_result(self):
        lead = 'How hard is X by Y in Z?'
        parts = ['Expert Lead: D 100.00, Calc Tier 7, at or above 90%', 'Expert Bass: D 50.00, Calc Tier 5, at or above 80%',
                 'Expert Keys: D 20.00, Calc Tier 3, at or above 70%', 'Expert Drums: D 10.00, Calc Tier 2, at or above 60%']
        out = page.song_description(lead, parts)
        self.assertTrue(out.startswith(lead + ' ' + parts[0]))
        self.assertLessEqual(len(out), page.DESCRIPTION_MOST)
        self.assertTrue(out.endswith(parts[1]), out)                      # two whole parts fit, the third does not
        self.assertEqual(page.song_description(lead, [parts[0] * 3]), lead + ' ' + parts[0] * 3)    # the first part always
        self.assertEqual(page.song_description(lead, []), lead)

    def test_lists_need_two_songs(self):
        pools = page.list_pools(self.f, self.r)
        self.assertNotIn(('hardest', 'Bass'), pools)                     # one bass song is not a list
        self.assertNotIn(('hardest-customs', 'Guitar'), pools)           # nor one custom
        self.assertIn(('hardest', 'Guitar'), pools)
        self.assertNotIn('list/hardest-bass.html', page.render_list_pages(self.f, self.r, self.names, self.facts, pools))

    def test_page_dates_keep_a_date_while_the_bytes_stay(self):
        files = {'index.html': b'a', 'about.html': b'b', 'song/k.html': b'c', 'static/x.js': b'js', 'sitemap.xml': b'x'}
        first = page.PageDates().stamp(files, today=datetime.date(2026, 9, 1))
        self.assertEqual(set(first), {'index.html', 'about.html', 'song/k.html'})       # pages only, never the assets or the sitemap
        self.assertEqual(first['song/k.html'][1], '2026-09-01')
        later = page.PageDates(first).stamp({**files, 'about.html': b'changed'}, today=datetime.date(2026, 9, 19))
        self.assertEqual(later['song/k.html'], first['song/k.html'])
        self.assertEqual(later['about.html'][1], '2026-09-19')
        self.assertEqual(later['index.html'][1], '2026-09-01')
        gone = page.PageDates(later).stamp({'index.html': b'a'}, today=datetime.date(2026, 9, 20))
        self.assertEqual(list(gone), ['index.html'])
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / 'sub' / 'dates.json'
            page.PageDates.save(path, later)
            self.assertEqual(page.PageDates.load(path).previous, later)
            self.assertEqual(page.PageDates.load(pathlib.Path(tmp) / 'missing.json').previous, {})
        sitemap = page.render_sitemap({'index.html': b'', 'about.html': b'', 'song/k.html': b''}, datetime.date(2026, 9, 19), page.dates_of(later)).decode('utf-8')
        self.assertIn('<url><loc>https://fretladder.com/</loc><lastmod>2026-09-01</lastmod></url>', sitemap)
        self.assertIn('<url><loc>https://fretladder.com/about.html</loc><lastmod>2026-09-19</lastmod></url>', sitemap)
        self.assertIn('<url><loc>https://fretladder.com/song/k.html</loc><lastmod>2026-09-01</lastmod></url>', sitemap)
        plain = page.render_sitemap({'index.html': b'', 'about.html': b''}, datetime.date(2026, 9, 19)).decode('utf-8')
        self.assertEqual(plain.count('<lastmod>2026-09-19</lastmod>'), 2)

    def test_build_stamps_dates_and_writes_the_key_file(self):
        import unittest.mock
        with unittest.mock.patch.object(page.frames, 'load_frames', return_value=(pathlib.Path('Fixture_metrics_09192026-1755.xlsx'), small_frames())), \
             unittest.mock.patch.object(page.assets, 'load_assets', return_value=({}, self.names)):
            built = page.build('Fixture', None, None, public=True, resolved=self.r, page_dates=page.PageDates(), indexnow_key='a' * 32)
        self.assertEqual(built.files['a' * 32 + '.txt'], b'a' * 32)
        self.assertEqual(set(built.page_dates), set(n or 'index.html' for n in page.sitemap_urls(built.files)))
        self.assertNotIn('sitemap.xml', built.page_dates)
        sitemap = built.files['sitemap.xml'].decode('utf-8')
        self.assertEqual(sitemap.count('<lastmod>'), sitemap.count('<url>'))
        self.assertNotIn('a' * 32, sitemap)
        index = built.files['index.html'].decode('utf-8')
        self.assertIn('<details id="static" open>', index)
        self.assertIn('<li><a href="game/pack-one.html">Pack One</a></li>', index)
        self.assertEqual(index.count('<script'), 5)                       # the theme, the WebSite block, the island, the module, the guide's closer

    def test_ld_blocks(self):
        crumbs = page.breadcrumb_ld([('Charts', ''), ('Pack', 'game/p.html')])
        self.assertEqual(crumbs['itemListElement'][0]['item'], 'https://fretladder.com/')
        self.assertEqual(crumbs['itemListElement'][1], {'@type': 'ListItem', 'position': 2, 'name': 'Pack', 'item': 'https://fretladder.com/game/p.html'})
        items = page.itemlist_ld('L', [('A', 'song/a.html'), ('B', 'song/b.html')])
        self.assertEqual(items['numberOfItems'], 2)
        self.assertEqual(items['itemListElement'][1]['url'], 'https://fretladder.com/song/b.html')
        data = page.dataset_ld({'rows': 5, 'songs': 3, 'packs': 2}, datetime.date(2026, 9, 19))
        self.assertEqual(data['dateModified'], '2026-09-19')
        self.assertEqual(data['isBasedOn'], 'https://github.com/Staycation44/fretwork')
        self.assertNotIn('distribution', data)                            # the sheet files are hashed and the next deploy deletes them
        self.assertNotIn('license', data)                                 # the engine's MIT is the code's, not the charts'
        self.assertEqual(page.ld_script(None), '')
        one = page.ld_script({'a': '</script>'})
        self.assertNotIn('</script>"', one)
        self.assertTrue(one.startswith('<script type="application/ld+json">{'))
        self.assertIn('[{"a": 1}, {"b": 2}]', page.ld_script({'a': 1}, {'b': 2}))


class LadderTest(unittest.TestCase):
    """Section 25: every song page stands on a ladder of its neighbours, from the data alone."""

    def setUp(self):
        self.f = small_frames()
        self.r = LibraryPageTest().resolved()
        self.names = {'favicon': 'static/f.svg', 'script': 'static/app.x.js', 'style': 'static/app.x.css', 'bootstrap': 'static/b.css'}
        # a fourth song by Alpha's artist in Pack One, so the source group reaches three and the artist has two
        self.f['Guitar'] = pd.concat([self.f['Guitar'], pd.DataFrame([{'Code': '00000005XG', 'Song Title': 'Delta', 'Artist': 'a', 'Type': 'Lead', 'Level': 'Expert',
                                                                       'D': 15.0, 'CalcTier': 4, 'Official': True, 'SongKey': '0000000000a5', 'NotesHash': 'h5',
                                                                       'NoteCount': 900, 'DurationS': 120.0}])], ignore_index=True)
        self.r.folder_by_code['00000005XG'] = 'one'
        self.facts = page.song_facts(self.f)

    def test_primary_expert_and_ladders(self):
        p = page.primary_expert(self.facts['0000000000a1'])
        self.assertEqual((p['sheet'], p['d'], p['tier'], p['part'], p['code']), ('Guitar', 10.0, 3, 'Lead', '00000001XG'))
        self.assertEqual((p['notes'], p['secs']), (None, None))
        self.assertEqual(page.primary_expert(self.facts['0000000000a5'])['notes'], 900)
        ladders = page.song_ladders(self.facts, self.r)
        # the site: Gamma 20.50 and Beta 20.50 (ties by title), Delta 15, Alpha 10
        a1 = ladders['0000000000a1']
        self.assertEqual((a1['site']['rank'], a1['site']['n']), (4, 4))
        self.assertEqual(a1['site']['harder'], ['0000000000a3', '0000000000a5'])          # the two above, nearest last
        self.assertEqual(a1['site']['easier'], [])
        # the source: Pack One holds Alpha, Beta and Delta on Guitar, three songs, so it has a ladder; Pack Two (Gamma alone) has none
        self.assertEqual((a1['source']['rank'], a1['source']['n'], a1['source']['harder'], a1['source']['easier']), (3, 3, ['0000000000a2', '0000000000a5'], []))
        self.assertIsNone(ladders['0000000000a3']['source'])
        # the artist: Delta is by a too
        self.assertEqual(a1['artist'], ['0000000000a5'])
        self.assertEqual(ladders['0000000000a5']['artist'], ['0000000000a1'])
        self.assertEqual(ladders['0000000000a2']['artist'], [])
        # no pack join: no source ladder, the site ladder stands
        self.assertIsNone(page.song_ladders(self.facts, None)['0000000000a1']['source'])

    def test_ladder_html(self):
        ladders = page.song_ladders(self.facts, self.r)
        out = page.song_ladder_html('0000000000a5', ladders['0000000000a5'], self.facts, {'name': 'Pack One', 'slug': 'pack-one'})
        self.assertIn('<p class="rank">Ranked #2 of 3 songs in Pack One on Expert guitar, and #3 of the 4 songs on the site with an Expert guitar chart. 900 notes over 2:00, 7.5 a second on average.</p>', out)
        self.assertIn('<b>Nearby on Expert guitar</b>: harder: <a href="song/0000000000a3.html">Gamma by c (D 20.50)</a>, <a href="song/0000000000a2.html">Beta by b (D 20.50, tier 5)</a>; easier: <a href="song/0000000000a1.html">Alpha by a (D 10.00, tier 3)</a>', out)
        self.assertIn('<b>In Pack One</b>: harder: <a href="song/0000000000a2.html">Beta by b (D 20.50, tier 5)</a>; easier: <a href="song/0000000000a1.html">Alpha by a (D 10.00, tier 3)</a>', out)
        self.assertIn('<b>More by a</b>: <a href="song/0000000000a1.html">Alpha by a (D 10.00, tier 3)</a>', out)
        # without a source, the site sentence alone; without a ladder, nothing
        alone = page.song_ladder_html('0000000000a3', ladders['0000000000a3'], self.facts, None)
        self.assertIn('<p class="rank">Ranked #2 of the 4 songs on the site with an Expert guitar chart.</p>', alone)   # Beta ties at 20.50 and sorts first by title
        self.assertNotIn('<b>In ', alone)
        self.assertEqual(page.song_ladder_html('x', None, self.facts, None), '')

    def test_song_pages_carry_the_ladder_and_the_picture_s_real_size(self):
        pages = page.render_song_pages(self.f, self.names, self.facts, self.r, png_size=(1908, 774))
        one = pages['song/0000000000a1.html'].decode('utf-8')
        self.assertIn('<p class="rank">Ranked #3 of 3 songs in Pack One', one)
        self.assertGreaterEqual(one.count('href="song/'), 3)
        self.assertIn('width="1908" height="774"', one)
        self.assertLess(one.index('</table>'), one.index('<p class="rank">'))
        self.assertLess(one.index('<div class="ladder">'), one.index('<p class="game">'))
        self.assertIn('0000000000a5', one)                                            # the artist's other song
        self.assertNotRegex(one, r'__[A-Z][A-Z_]*__')

    def test_png_size_reads_a_picture_and_falls_back(self):
        from web import bundle
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(bundle.png_size(tmp))
            graph = pathlib.Path(tmp) / 'graph'
            graph.mkdir()
            (graph / 'A.png').write_bytes(b'\x89PNG\r\n\x1a\n' + b'\x00\x00\x00\x0dIHDR' + (1908).to_bytes(4, 'big') + (774).to_bytes(4, 'big') + b'\x08')
            self.assertEqual(bundle.png_size(tmp), (1908, 774))
            (graph / '0.png').write_bytes(b'not a png')
            self.assertEqual(bundle.png_size(tmp), (1908, 774))                     # the bad file is skipped
