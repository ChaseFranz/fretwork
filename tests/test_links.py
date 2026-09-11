"""The offline link registry (section 13): its published form, the matcher, the pacer and the Enchor lookup, all offline."""

import json
import pathlib
import tempfile
import unittest

import numpy as np

from functions import instruments
from web import links
from tools import links_common as lc
from tools import enchor_lookup

MD5_A = '0123456789abcdef0123456789abcdef'
MD5_B = 'fedcba9876543210fedcba9876543210'
HASH_A = 'A' * 43
HASH_B = 'B' * 43


def registry():
    return {'v': 1,
            'enchor': {'k1': {'md5': MD5_A, 'chartId': 5, 'via': 'meta'}, 'k2': {'md5': None}, 'k3': {'md5': 'ZZ' * 16},
                       'k5': {'md5': MD5_B}},
            'leaderboard': {'k1': {'songHash': HASH_A, 'sure': True, 'twins': 1}, 'k4': {'songHash': HASH_B, 'sure': False, 'twins': 1},
                            'k5': {'songHash': HASH_B, 'sure': False, 'twins': 2}, 'k6': {'songHash': 'bad hash', 'sure': True},
                            'k7': {'songHash': None}}}


class PublishedTest(unittest.TestCase):

    def test_shape_and_filtering(self):
        data = links.published(registry())
        doc = json.loads(data)
        self.assertEqual(doc['v'], 1)
        self.assertEqual(doc['songs'], {'k1': {'enchor': MD5_A, 'lb': HASH_A}, 'k5': {'enchor': MD5_B, 'lb': HASH_B}})
        self.assertNotIn(' ', data.decode())
        self.assertTrue(links.file_name(data).startswith('data/links.') and links.file_name(data).endswith('.json'))
        import hashlib
        self.assertEqual(links.file_name(data), f'data/links.{hashlib.sha1(data).hexdigest()[:8]}.json')

    def test_nothing_known_means_no_file(self):
        self.assertIsNone(links.published(None))
        self.assertIsNone(links.published({'v': 1, 'enchor': {'k': {'md5': None}}, 'leaderboard': {}}))

    def test_a_sheet_named_links_is_refused(self):
        from web import frames
        self.assertEqual(frames.slug('Links'), links.SLUG)   # the collision page.build() raises on


class MatcherTest(unittest.TestCase):
    row = {'title': 'Through the Fire and Flames', 'artist': 'DragonForce', 'charter': 'Neversoft', 'note_count': 3722}

    def test_single_charter_match_is_sure(self):
        c = [{'songHash': HASH_A, 'name': 'Through The Fire And Flames', 'artist': 'Dragonforce', 'charter': 'neversoft'}]
        self.assertEqual(lc.pick(self.row, c), (HASH_A, True, 1))

    def test_lone_charter_miss_is_unsure_until_confirmed(self):
        c = [{'songHash': HASH_A, 'name': 'Through the Fire and Flames', 'artist': 'DragonForce', 'charter': 'Harmonix'}]
        self.assertEqual(lc.pick(self.row, c), (HASH_A, False, 1))
        self.assertTrue(lc.confirm_lone(self.row, c[0], 3722))
        self.assertFalse(lc.confirm_lone(self.row, c[0], 3700))
        self.assertFalse(lc.confirm_lone(self.row, c[0], None))

    def test_note_count_decides_among_several(self):
        c = [{'songHash': HASH_A, 'name': 'Through the Fire and Flames', 'artist': 'DragonForce', 'charter': 'x'},
             {'songHash': HASH_B, 'name': 'Through the Fire and Flames', 'artist': 'DragonForce', 'charter': 'y'}]
        self.assertEqual(lc.pick(self.row, c, {HASH_A: 3000, HASH_B: 3722}), (HASH_B, True, 1))
        self.assertEqual(lc.pick(self.row, c, {HASH_A: 3722, HASH_B: 3722}), (HASH_A, True, 2))   # twins

    def test_other_songs_are_not_in_the_pool(self):
        c = [{'songHash': HASH_A, 'name': 'Other', 'artist': 'DragonForce', 'charter': 'Neversoft'}]
        self.assertEqual(lc.pick(self.row, c), (None, False, 0))

    def test_norm(self):
        self.assertEqual(lc.norm('  Café (Live) [2x]  '), 'cafe')
        self.assertEqual(lc.song_key('A B', 'C'), 'a b|c')


class PacerTest(unittest.TestCase):

    def test_spacing_and_reset(self):
        now = [1.7e9]
        slept = []
        p = lc.Pacer(48, clock=lambda: now[0], sleep=lambda s: (slept.append(s), now.__setitem__(0, now[0] + s)))
        for _ in range(50):
            p.wait()
        self.assertGreaterEqual(sum(slept), 61.25 - 1.25)      # 49 gaps of 1.25 s
        p.after({'x-ratelimit-remaining': '0', 'x-ratelimit-reset': str(now[0] + 10)})
        self.assertAlmostEqual(slept[-1], 11.0)
        p.limited({'x-ratelimit-reset': str(now[0] + 5)})
        self.assertAlmostEqual(slept[-1], 6.0)
        p.limited({})
        self.assertEqual(slept[-1], 60.0)
        with self.assertRaises(lc.RateLimited):
            p.limited({})


class EnchorLookupTest(unittest.TestCase):

    def cache(self):
        notes = lambda n: {'time_ms': np.arange(n, dtype=np.float64), 'lanes': np.ones(n, dtype=np.uint8)}   # noqa: E731
        return {'search_path': '/srv/lib', 'songs': {
            '/srv/lib/Pack A/one': {'song_path': '/srv/lib/Pack A/one', 'song_key': 'k1', 'chart_md5': MD5_A,
                                'meta': {'Name': 'One', 'Artist': 'Band', 'Charter': 'Chezy', 'Release': 'Custom'},
                                'instruments': {'guitar': {'expert': {'notes': notes(100)}}}},
            '/srv/lib/Pack A/two': {'song_path': '/srv/lib/Pack A/two', 'song_key': 'k2', 'chart_md5': MD5_B,
                                'meta': {'Name': 'Two', 'Artist': 'Band', 'Charter': 'Chezy', 'Release': 'Custom'},
                                'instruments': {'guitar': {'expert': {'notes': notes(200)}}}},
            '/srv/lib/Pack A/three': {'song_path': '/srv/lib/Pack A/three', 'song_key': 'k3', 'chart_md5': None,
                                  'meta': {'Name': 'Three', 'Artist': 'Band', 'Charter': 'Nobody', 'Release': 'Custom'},
                                  'instruments': {'bass': {'expert': {'notes': notes(50)}}}},
        }}

    def hit(self, md5, chart_id, charter, count):
        return {'md5': md5, 'chartId': chart_id, 'charter': charter,
                'notesData': {'noteCounts': [{'instrument': 'guitar', 'difficulty': 'expert', 'count': count}]}}

    def test_choose(self):
        hits = [self.hit(MD5_A, 1, 'Chezy', 100), self.hit(MD5_B, 2, 'Other', 100), self.hit('c' * 32, 3, 'Chezy', 999)]
        chosen, n = enchor_lookup.choose(hits, 'Chezy', 100)
        self.assertEqual((chosen['md5'], n), (MD5_A, 2))                       # count then charter
        chosen, n = enchor_lookup.choose(hits, 'Nobody', 100)
        self.assertEqual((chosen['md5'], n), (MD5_B, 2))                       # newest of the count matches
        self.assertEqual(enchor_lookup.choose(hits, 'Chezy', 5), (None, 0))    # no count match: no link
        chosen, n = enchor_lookup.choose(hits, 'Other', None)
        self.assertEqual((chosen['md5'], n), (MD5_B, 1))                       # no count: a lone charter match
        self.assertEqual(enchor_lookup.choose(hits, 'Chezy', None)[0], None)   # two charter matches: ambiguous

    def test_run_records_and_a_second_pass_asks_nothing(self):
        answers = {'One': [self.hit(MD5_A, 1, 'Chezy', 100)], 'Two': [self.hit(MD5_B, 7, 'x', 200), self.hit(MD5_B[::-1], 9, 'y', 200)],
                   'Three': []}
        calls = []

        def post(url, body):
            calls.append(body)
            name = body['name']['value']
            return 201, {'x-ratelimit-remaining': '40'}, {'found': len(answers[name]), 'data': answers[name]}

        pacer = lc.Pacer(6000, clock=lambda: 0.0, sleep=lambda s: None)
        reg = lc.load_registry('/nonexistent/links.json')
        stats, by_folder, by_release = enchor_lookup.run(self.cache(), reg, pacer, post=post, today='2026-09-11')
        self.assertEqual((stats['asked'], stats['found'], stats['missed']), (3, 2, 1))
        self.assertEqual(reg['enchor']['k1']['md5'], MD5_A)
        self.assertEqual(reg['enchor']['k2']['chartId'], 9)          # the newest upload of the two count matches
        self.assertEqual(reg['enchor']['k2']['hits'], 2)
        self.assertIsNone(reg['enchor']['k3']['md5'])
        self.assertEqual(reg['enchor']['k1']['via'], 'meta')
        self.assertEqual(by_folder['Pack A'], [2, 3])
        self.assertEqual(len(calls), 3)
        stats, _, _ = enchor_lookup.run(self.cache(), reg, pacer, post=post)
        self.assertEqual((stats['asked'], stats['known']), (0, 3))
        stats, _, _ = enchor_lookup.run(self.cache(), reg, pacer, post=post, recheck=True)
        self.assertEqual(stats['asked'], 1)                           # only the null is re-asked
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / 'r.json'
            lc.save_registry(path, reg)
            self.assertEqual(lc.load_registry(path)['enchor']['k1']['md5'], MD5_A)


class InstrumentsTest(unittest.TestCase):

    def test_leaderboard_instrument_covers_the_song_key_instruments(self):
        self.assertTrue(set(instruments.SONG_KEY_INSTRUMENTS) <= set(instruments.LEADERBOARD_INSTRUMENT))
        self.assertEqual(lc.type_to_instrument(instruments.TYPE_LABELS['guitar']), 'guitar')


if __name__ == '__main__':
    unittest.main()
