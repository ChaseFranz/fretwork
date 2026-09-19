"""Copies and the distinct percentile (section 10): the frame helpers on synthetic sheets, and the hash primitive."""

import hashlib
import unittest

import numpy as np
import pandas as pd

from functions import cache
from web import frames


def frame(hashes, types=None, levels=None, d=None):
    n = len(hashes)
    return pd.DataFrame({
        'Code': [f'{i:08d}XG' for i in range(n)],
        'Type': types or ['Lead'] * n,
        'Level': levels or ['Expert'] * n,
        'D': d if d is not None else list(range(n, 0, -1)),
        'NotesHash': hashes,
    })


class CopiesTest(unittest.TestCase):

    def test_a_pair_counts_two_and_within_song_repeats_count_one(self):
        # a cross-pack pair (a, a), Hard = Expert (b at two levels), Lead = Rhythm (c on two parts), a null hash
        df = frame(['a', 'a', 'b', 'b', 'c', 'c', None],
                   types=['Lead', 'Lead', 'Lead', 'Lead', 'Lead', 'Rhythm', 'Lead'],
                   levels=['Expert', 'Expert', 'Expert', 'Hard', 'Expert', 'Expert', 'Expert'])
        out = frames.add_copies(df)
        self.assertEqual(out['Copies'].tolist(), [2, 2, 1, 1, 1, 1, 1])
        self.assertEqual(str(out['Copies'].dtype), 'int64')
        self.assertNotIn('Copies', df.columns)          # a copy was returned, the input untouched

    def test_without_the_hash_column_the_frame_passes_through(self):
        df = frame(['a', 'a']).drop(columns=['NotesHash'])
        self.assertIs(frames.add_copies(df), df)

    def test_null_hashes_are_each_their_own_chart(self):
        df = frame([None, None, None])
        self.assertEqual(frames.add_copies(df)['Copies'].tolist(), [1, 1, 1])

    def test_distinct_percentile_over_all_null_hashes_is_the_plain_rank(self):
        df = frame([None] * 5, d=[10, 10, 20, 5, 1])
        plain = frames.percentile(df).tolist()
        sheets = {'x': df.copy()}
        frames.add_percentiles(sheets, distinct=frames.COPY_KEY)
        self.assertEqual(sheets['x']['Pct'].tolist(), plain)

    def test_the_synthetic_table_from_section_02(self):
        df = pd.DataFrame({
            'Code': [f'{i}' for i in range(7)],
            'Level': ['Expert'] * 4 + ['Easy'] * 2 + ['Expert'],
            'D': [10, 10, 20, 5, 1, 2, np.nan],
            'Type': ['Lead'] * 7,
            'NotesHash': list('aabcdef'),
        })
        got = frames.percentile(df, distinct=frames.COPY_KEY).tolist()
        self.assertEqual([None if pd.isna(v) else int(v) for v in got], [66, 66, 100, 33, 50, 100, None])
        copies = frames.add_copies(df)['Copies'].tolist()
        self.assertEqual(copies, [2, 2, 1, 1, 1, 1, 1])
        # the page-build order: Copies before Pct
        sheets = {'x': frames.add_copies(df)}
        frames.add_percentiles(sheets, distinct=frames.COPY_KEY)
        self.assertEqual(list(sheets['x'].columns)[-2:], ['Copies', 'Pct'])


class NotesHashTest(unittest.TestCase):

    def test_flat_stream_is_the_two_arrays_back_to_back(self):
        notes = {'time_ms': np.array([0.0, 250.5, 1000.0]), 'lanes': np.array([1, 2, 4], dtype=np.uint8)}
        want = hashlib.sha1(notes['time_ms'].tobytes() + notes['lanes'].tobytes()).hexdigest()[:12]
        self.assertEqual(cache.notes_hash(notes), want)
        self.assertRegex(cache.notes_hash(notes), r'^[0-9a-f]{12}$')

    def test_drums_pair_is_labelled(self):
        hand = {'time_ms': np.array([0.0]), 'lanes': np.array([2], dtype=np.uint8)}
        kick = {'time_ms': np.array([500.0]), 'lanes': np.array([1], dtype=np.uint8)}
        got = cache.stream_bytes({'hand_mask': hand, 'kick_mask': kick})
        self.assertEqual(got, b'hand' + cache.stream_bytes(hand) + b'kick' + cache.stream_bytes(kick))
        swapped = cache.stream_bytes({'hand_mask': kick, 'kick_mask': hand})
        self.assertNotEqual(got, swapped)

    # A vocals chart is its sung arrays plus the talkie and percussion streams
    # beside them, so two talkie-only charts with different lyrics differ.
    def test_vocals_hash_covers_the_side_streams(self):
        sung = {'time_ms': np.array([], dtype=np.float64), 'end_ms': np.array([], dtype=np.float64),
                'pitch': np.array([], dtype=np.uint8), 'is_placeholder': np.array([], dtype=bool), 'is_slide': np.array([], dtype=bool)}
        talk_a = {'time_ms': np.array([0.0, 400.0]), 'end_ms': np.array([np.nan, np.nan])}
        talk_b = {'time_ms': np.array([0.0, 800.0]), 'end_ms': np.array([np.nan, np.nan])}
        none = {'time_ms': np.array([], dtype=np.float64), 'end_ms': np.array([], dtype=np.float64)}
        self.assertNotEqual(cache.notes_hash(sung, talk_a, none), cache.notes_hash(sung, talk_b, none))
        self.assertEqual(cache.notes_hash(sung, talk_a, none), cache.notes_hash(sung, dict(talk_a), dict(none)))
        self.assertTrue(cache.stream_bytes(sung, talk_a, none).startswith(b'vox'))

    def test_same_notes_same_hash_and_a_lane_change_moves_it(self):
        a = {'time_ms': np.array([0.0, 1.0]), 'lanes': np.array([1, 1], dtype=np.uint8)}
        b = {'time_ms': a['time_ms'].copy(), 'lanes': a['lanes'].copy()}
        c = {'time_ms': a['time_ms'].copy(), 'lanes': np.array([1, 2], dtype=np.uint8)}
        self.assertEqual(cache.notes_hash(a), cache.notes_hash(b))
        self.assertNotEqual(cache.notes_hash(a), cache.notes_hash(c))


if __name__ == '__main__':
    unittest.main()
