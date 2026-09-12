"""tools/ingest_pack.py: pre-flight refusals, staging, name repair, containment, the registry, --replace."""

import argparse
import datetime
import io
import os
import pathlib
import shutil
import sys
import tempfile
import unittest
import unittest.mock
import zipfile

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'tools'))

import config                      # noqa: E402
import ingest_pack                 # noqa: E402
from functions import packs        # noqa: E402
from tests import fixture          # noqa: E402


def args_for(src, name, work, **over):
    ns = argparse.Namespace(SOURCE=str(src), name=name, source=None, header='IngestTest',
                            library=str(work / 'lib'), packs=str(work / 'packs.toml'), notes='',
                            replace=False, dry_run=False, max_bytes=ingest_pack.DEFAULT_MAX_BYTES, log=None)
    for k, v in over.items():
        setattr(ns, k, v)
    return ns


def zip_of(folder, dest, wrap=None):
    with zipfile.ZipFile(dest, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in sorted(pathlib.Path(folder).rglob('*')):
            if p.is_file():
                rel = p.relative_to(folder)
                z.write(p, str(pathlib.PurePosixPath(wrap) / rel.as_posix()) if wrap else rel.as_posix())
    return dest


class IngestTest(unittest.TestCase):

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.work = self.tmp / 'work'
        self.work.mkdir()
        self.lib = fixture.write(self.tmp / 'fixture')
        self.pack_a = self.tmp / 'fixture' / 'Fixture Pack A'
        # an audio file beside every song.ini, which staging must never copy or keep
        for ini in self.pack_a.rglob('song.ini'):
            (ini.parent / 'song.ogg').write_bytes(b'\x00' * 100)
        self.cwd = os.getcwd()
        os.chdir(self.work)                       # caches/ingest lands here, not in the repo

    def tearDown(self):
        os.chdir(self.cwd)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def stage(self, source, name, **over):
        a = args_for(source, name, self.work, **over)
        plan = ingest_pack.preflight(a)
        work = pathlib.Path(config.OUTPUT_DIRS['cache']) / 'ingest'
        work.mkdir(parents=True, exist_ok=True)
        with unittest.mock.patch('sys.stdout', new_callable=io.StringIO):
            dest, _ = ingest_pack.stage(a, plan, work)
        return a, plan, dest

    def test_wrapper_stripped_only_when_single(self):
        wrapped = zip_of(self.pack_a, self.tmp / 'wrapped.zip', wrap='Fixture Pack A')
        _, _, dest = self.stage(wrapped, 'W')
        self.assertTrue((dest / 'A1 - Grid Runner' / 'song.ini').is_file())
        flat = zip_of(self.pack_a, self.tmp / 'flat.zip')
        _, _, dest = self.stage(flat, 'F')
        self.assertTrue((dest / 'A1 - Grid Runner' / 'song.ini').is_file())
        self.assertEqual(len(ingest_pack.song_folders(dest)), 4)

    def test_audio_never_copied_from_a_folder_and_removed_from_an_archive(self):
        _, _, dest = self.stage(self.pack_a, 'Dir')
        self.assertEqual(list(dest.rglob('*.ogg')), [])
        self.assertEqual(len(list(self.pack_a.rglob('*.ogg'))), 4)          # the source is untouched
        archive = zip_of(self.pack_a, self.tmp / 'a.zip')
        _, _, dest = self.stage(archive, 'Zip')
        self.assertEqual(len(list(dest.rglob('*.ogg'))), 4)                 # extracted, and then:
        import sanitize_songs
        with unittest.mock.patch('sys.stdout', new_callable=io.StringIO):
            report = sanitize_songs.sanitize(dest, apply=True, log=self.work / 'removed.csv')
        self.assertEqual(report.removed_files, 4)
        self.assertEqual(list(dest.rglob('*.ogg')), [])
        self.assertIn('song.ogg', (self.work / 'removed.csv').read_text())

    def test_fix_member_name(self):
        self.assertEqual(ingest_pack.fix_member_name('M├╢tley Cr├╝the', 0), 'Mötley Crüthe')
        self.assertEqual(ingest_pack.fix_member_name('M├╢tley', 0x800), 'M├╢tley')
        self.assertEqual(ingest_pack.fix_member_name('plain', 0), 'plain')

    def test_escaping_members_are_skipped(self):
        archive = self.tmp / 'esc.zip'
        with zipfile.ZipFile(archive, 'w') as z:
            z.writestr('../escape.txt', 'x')
            z.writestr('/abs.txt', 'x')
            z.writestr('A/song.ini', '[song]\nname = A\n')
        self.assertIn('../escape.txt', zipfile.ZipFile(archive).namelist())
        dest = self.work / 'x'
        dest.mkdir()
        with unittest.mock.patch('sys.stdout', new_callable=io.StringIO) as out:
            skipped = ingest_pack.extract_zip(archive, dest, 10 ** 9)
        self.assertEqual(skipped, 2)
        self.assertIn('2 members outside the archive root skipped', out.getvalue())
        self.assertFalse((self.work / 'escape.txt').exists())
        self.assertTrue((dest / 'A' / 'song.ini').is_file())

    def test_case_rename_and_collision(self):
        archive = self.tmp / 'case.zip'
        with zipfile.ZipFile(archive, 'w') as z:
            z.writestr('A/Song.ini', '[song]\nname = A\n')
            z.writestr('A/Notes.mid', b'MThd')
        _, _, dest = self.stage(archive, 'Case')
        self.assertEqual(sorted(p.name for p in (dest / 'A').iterdir()), ['notes.mid', 'song.ini'])
        clash = self.tmp / 'clash.zip'
        with zipfile.ZipFile(clash, 'w') as z:
            z.writestr('A/Song.ini', 'x')
            z.writestr('A/song.ini', 'y')
        with self.assertRaises(ingest_pack.Refusal):
            self.stage(clash, 'Clash')

    def test_sng_only_is_refused(self):
        archive = self.tmp / 'sng.zip'
        with zipfile.ZipFile(archive, 'w') as z:
            z.writestr('a.sng', 'x')
            z.writestr('b.sng', 'y')
        with self.assertRaisesRegex(ingest_pack.Refusal, r'0 song folders and 2 \.sng'):
            self.stage(archive, 'Sng')

    def test_inflated_size_cap(self):
        archive = zip_of(self.pack_a, self.tmp / 'big.zip')
        with self.assertRaisesRegex(ingest_pack.Refusal, 'inflates to'):
            self.stage(archive, 'Big', max_bytes=1000)

    def test_replace_states(self):
        reg = self.work / 'packs.toml'
        reg.write_text('')
        (self.work / 'lib').mkdir()
        # not registered, folder absent: goes ahead and will append
        plan = ingest_pack.preflight(args_for(self.pack_a, 'P', self.work))
        self.assertTrue(plan.append_entry and not plan.remove_folder)
        # not registered, folder exists
        (self.work / 'lib' / 'P').mkdir()
        with self.assertRaisesRegex(ingest_pack.Refusal, 'exists'):
            ingest_pack.preflight(args_for(self.pack_a, 'P', self.work))
        plan = ingest_pack.preflight(args_for(self.pack_a, 'P', self.work, replace=True))
        self.assertTrue(plan.append_entry and plan.remove_folder)
        # registered, folder exists: refused without --replace, entry kept with it
        packs.append_pack(reg, packs.Pack('P', 'P', '', datetime.date(2026, 9, 11), ''))
        before = reg.read_bytes()
        with self.assertRaisesRegex(ingest_pack.Refusal, 'already in'):
            ingest_pack.preflight(args_for(self.pack_a, 'P', self.work))
        plan = ingest_pack.preflight(args_for(self.pack_a, 'P', self.work, replace=True))
        self.assertFalse(plan.append_entry)
        self.assertEqual(reg.read_bytes(), before)
        # registered, folder missing
        shutil.rmtree(self.work / 'lib' / 'P')
        with self.assertRaisesRegex(ingest_pack.Refusal, 'already in'):
            ingest_pack.preflight(args_for(self.pack_a, 'P', self.work))
        plan = ingest_pack.preflight(args_for(self.pack_a, 'P', self.work, replace=True))
        self.assertFalse(plan.append_entry or plan.remove_folder)

    def test_not_direct_hosts_never_open_a_socket(self):
        (self.work / 'packs.toml').write_text('')
        with unittest.mock.patch('urllib.request.urlopen', side_effect=AssertionError('socket opened')):
            for host in ingest_pack.NOT_DIRECT:
                with self.assertRaisesRegex(ingest_pack.Refusal, 'not a direct download'):
                    ingest_pack.preflight(args_for(f'https://{host}/x/pack.zip', 'N', self.work))

    def test_diff_write_mode_guard(self):
        (self.work / 'packs.toml').write_text('')
        with unittest.mock.patch.object(config, 'DIFF_WRITE_MODE', 'CalcTier'):
            with self.assertRaisesRegex(ingest_pack.Refusal, 'DIFF_WRITE_MODE'):
                ingest_pack.preflight(args_for(self.pack_a, 'N', self.work))

    def test_source_rule(self):
        (self.work / 'packs.toml').write_text('')
        with self.assertRaisesRegex(ingest_pack.Refusal, '--source'):
            ingest_pack.preflight(args_for(self.pack_a, 'N', self.work, source='ftp://x'))
        plan = ingest_pack.preflight(args_for(self.pack_a, 'N', self.work, source=''))
        self.assertIsNotNone(plan)
        a = args_for('https://example.com/p.zip', 'N', self.work)
        ingest_pack.preflight(a)
        self.assertEqual(a.source, 'https://example.com/p.zip')     # a URL SOURCE is the default --source

    def test_name_shape(self):
        (self.work / 'packs.toml').write_text('')
        for bad in ('', '.', '..', 'a/b', 'a\\b', '.hidden'):
            with self.assertRaisesRegex(ingest_pack.Refusal, '--name'):
                ingest_pack.preflight(args_for(self.pack_a, bad, self.work))


if __name__ == '__main__':
    unittest.main()
