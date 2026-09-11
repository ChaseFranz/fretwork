"""functions/packs.py: the registry loader, the cache join, the writer, and the changelog renderer."""

import datetime
import json
import pathlib
import re
import shutil
import tempfile
import unittest

import pandas as pd

from functions import packs
from web import frames

REPO = pathlib.Path(__file__).resolve().parents[1]
SEED = REPO / 'packs.toml'


def registry_text(**edits):
    text = SEED.read_text(encoding='utf-8')
    for old, new in edits.items():
        assert old in text, old
        text = text.replace(old, new, 1)
    return text


def synthetic_cache(root, layout):
    """layout: {folder: [song names]} or {song: None} for loose songs; codes per song, one guitar expert."""
    songs, codes = {}, {}
    n = 0
    for folder, names in layout.items():
        for name in (names or [None]):
            path = str(root / folder / name) if name else str(root / folder)
            code = f'{n:08d}XG'
            n += 1
            songs[path] = {'song_path': path, 'codes': {'guitar': {'expert': code}}}
            codes[code] = path
    return {'search_path': str(root), 'songs': songs, 'codes': codes}


class LoaderTest(unittest.TestCase):

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, text):
        p = self.tmp / 'p.toml'
        p.write_text(text, encoding='utf-8')
        return p

    def test_seed_loads(self):
        r = packs.load(SEED)
        self.assertGreaterEqual(len(r.packs), 1)
        self.assertEqual(len({p.folder for p in r.packs}), len(r.packs))
        self.assertTrue(all(type(p.added) is datetime.date for p in r.packs))

    def test_invalid_registries(self):
        cases = {
            'quoted date': registry_text(**{'added = 2026-09-07': 'added = "2026-09-07"'}),
            'date-time': registry_text(**{'added = 2026-09-07': 'added = 2026-09-07T10:00:00'}),
            'duplicate folder': registry_text() + '\n[[pack]]\nname = "Dup"\nfolder = "S Hero"\nadded = 2026-09-07\n',
            'separator': registry_text(**{'folder = "S Hero"': 'folder = "a/b"'}),
            'control character': registry_text(**{'notes = ""': 'notes = "a\\tb"'}),
            'unknown key': registry_text(**{'notes = ""': 'notes = ""\nextra = 1'}),
            'bad source': registry_text(**{'source = ""': 'source = "ftp://x"'}),
        }
        for label, text in cases.items():
            with self.subTest(case=label):
                with self.assertRaises(packs.PacksError):
                    packs.load(self.write(text))


class JoinTest(unittest.TestCase):

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_library_root_absolute_and_relative(self):
        root = self.tmp / 'songs'
        cache = synthetic_cache(root, {'Pack A': ['s1', 's2'], 'Pack B': ['s3']})
        self.assertEqual(packs.library_root(cache), root)
        cache['search_path'] = 'songs'                  # relative: recovered by name from the song paths
        self.assertEqual(packs.library_root(cache), root)
        one = synthetic_cache(root, {'Only Pack': ['s1', 's2']})
        one['search_path'] = 'songs'
        self.assertEqual(packs.library_root(one), root)  # commonpath is the pack; walk up to 'songs'
        cache['search_path'] = 'elsewhere'
        with self.assertRaises(packs.PacksError):
            packs.library_root(cache)

    def test_resolve_and_tally(self):
        root = self.tmp / 'songs'
        cache = synthetic_cache(root, {'Pack A': ['s1', 's2'], 'Pack B': ['s3'], 'Stray': ['s4']})
        reg = packs.Registry((packs.Pack('A', 'Pack A', '', datetime.date(2026, 9, 7), ''),
                              packs.Pack('B', 'Pack B', '', datetime.date(2026, 9, 8), ''),
                              packs.Pack('Gone', 'Pack C', '', datetime.date(2026, 9, 8), '')), (), self.tmp)
        res = packs.resolve(cache, reg)
        self.assertEqual(res.unregistered, ('Stray',))
        self.assertEqual(res.missing, ('Pack C',))
        self.assertEqual(res.loose, ())
        self.assertEqual(len(res.folder_by_code), 4)
        self.assertEqual(len(res.added_by_code), 3)
        self.assertEqual(sorted(set(res.added_by_code.values())), ['2026-09-07', '2026-09-08'])
        self.assertEqual(packs.tally(res, list(cache['codes'])), {'Pack A': (2, 2), 'Pack B': (1, 1), 'Pack C': (0, 0)})
        self.assertIn('Stray', packs.report(res))
        self.assertFalse(res.clean)

    def test_loose_songs_are_not_unregistered(self):
        root = self.tmp / 'songs'
        cache = synthetic_cache(root, {'Artist - Song': None, 'Other - Song': None})
        res = packs.resolve(cache, packs.Registry((), (), self.tmp))
        self.assertEqual(res.loose, ('Artist - Song', 'Other - Song'))
        self.assertEqual(res.unregistered, ())
        self.assertIn('move these into a pack folder', packs.report(res))


class WriterTest(unittest.TestCase):

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.path = self.tmp / 'packs.toml'
        shutil.copy(SEED, self.path)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_append_round_trips_awkward_names(self):
        before = len(packs.load(self.path).packs)
        name = 'Quote " back \\ é 🎵'
        packs.append_pack(self.path, packs.Pack(name, 'New Folder', 'https://example.com/x',
                                                datetime.date(2026, 9, 11), 'see [here](https://e.com)'))
        r = packs.load(self.path)
        self.assertEqual(len(r.packs), before + 1)
        self.assertEqual(r.packs[-1].name, name)
        self.assertEqual(r.packs[-1].added, datetime.date(2026, 9, 11))

    def test_append_refuses_and_leaves_the_file_alone(self):
        original = self.path.read_bytes()
        for bad in (packs.Pack('a\nb', 'X', '', datetime.date(2026, 9, 11), ''),
                    packs.Pack('Dup', 'S Hero', '', datetime.date(2026, 9, 11), '')):
            with self.assertRaises(packs.PacksError):
                packs.append_pack(self.path, bad)
            self.assertEqual(self.path.read_bytes(), original)
            self.assertEqual(list(self.tmp.glob('*.tmp')), [])

    def test_format_string(self):
        self.assertEqual(packs.format_string('a "b" \\ é'), '"a \\"b\\" \\\\ é"')
        with self.assertRaises(packs.PacksError):
            packs.format_string('tab\there')


class ColumnAndChangelogTest(unittest.TestCase):

    def test_with_added_appends_a_last_column_with_nulls(self):
        df = pd.DataFrame({'Code': ['1XG', '2XG', '3XG'], 'D': [1.0, 2.0, 3.0]})
        out = frames.with_added({'Guitar': df}, {'1XG': '2026-09-07', '3XG': '2026-09-08'})
        self.assertEqual(list(out['Guitar'].columns), ['Code', 'D', 'Added'])
        rows = frames.frames_payload(out)['Guitar']['rows']
        self.assertEqual([r[-1] for r in rows], ['2026-09-07', None, '2026-09-08'])

    def test_render_changelog_groups_by_date_newest_first(self):
        from web import page
        root = pathlib.Path('/lib/songs')
        cache = synthetic_cache(root, {'Pack A': ['s1'], 'Pack B': ['s2']})
        reg = packs.Registry((packs.Pack('Alpha', 'Pack A', 'https://x.test/a', datetime.date(2026, 9, 7), 'first'),
                              packs.Pack('Beta', 'Pack B', '', datetime.date(2026, 9, 9), '')),
                             (packs.Change(datetime.date(2026, 9, 9), 'Site [changed](https://x.test/c).'),), root)
        res = packs.resolve(cache, reg)
        html_out = page.render_changelog(res, list(cache['codes'])).decode('utf-8')
        h2 = re.findall(r'<h2><a href="([^"]+)"[^>]*>([^<]+)</a></h2>', html_out)
        self.assertEqual([t for _, t in h2], ['9 September 2026', '7 September 2026'])
        self.assertTrue(h2[0][0].startswith('./?f.Added=2026-09-09&amp;f.Level=Expert'))
        items = re.findall(r'<p class="item">(.*?)</p>', html_out)
        self.assertTrue(items[0].startswith('Site <a href='))          # a change before that date's packs
        self.assertIn('<strong>Beta</strong>, 1 songs, 1 charts.', items[1])
        self.assertIn('<a href="https://x.test/a" rel="noopener">Alpha</a>', items[2])
        self.assertIn('2 packs, 2 songs, 2 charts', html_out)
        self.assertNotRegex(html_out, r'__[A-Z][A-Z_]*__')


if __name__ == '__main__':
    unittest.main()
