"""deploy.plan() and deploy.samples(): the aws commands, read without an aws on PATH."""

import pathlib
import tempfile
import unittest

import deploy
from web import assets

BOTH = {'static', 'data'}
WITH_SONGS = {'static', 'data', 'song'}


class PlanTest(unittest.TestCase):

    def test_eight_commands_with_a_distribution(self):
        cmds = deploy.plan('b', 'E1X', 'site/X', present=BOTH)
        self.assertEqual([c[1:3] if c[1] == 'cloudfront' else c[:3] for c in cmds], [
            ['aws', 's3', 'sync'], ['aws', 's3', 'sync'], ['aws', 's3', 'sync'], ['aws', 's3', 'sync'],
            ['cloudfront', 'create-invalidation'], ['cloudfront', 'wait'],
            ['aws', 's3', 'sync'], ['aws', 's3', 'sync']])
        graphs, static1, data1, pages, create, wait, static2, data2 = cmds
        self.assertEqual(graphs[3:5], ['site/X/graph/', 's3://b/graph/'])
        self.assertIn('--delete', graphs)
        self.assertEqual(graphs[graphs.index('--cache-control') + 1], assets.CACHE_GRAPHS)
        for cmd in (static1, data1):
            self.assertNotIn('--delete', cmd)
            self.assertEqual(cmd[cmd.index('--cache-control') + 1], assets.CACHE_IMMUTABLE)
        self.assertEqual(pages[3:5], ['site/X/', 's3://b/'])
        self.assertIn('--delete', pages)
        excludes = [pages[i + 1] for i, a in enumerate(pages) if a == '--exclude']
        self.assertEqual(excludes, ['graph/*', 'song/*', 'static/*', 'data/*'])
        self.assertEqual(pages[pages.index('--cache-control') + 1], assets.CACHE_PAGE)
        self.assertEqual(create[3:], ['--distribution-id', 'E1X', '--paths', '/*', '--output', 'json'])
        self.assertEqual(wait[3:], ['invalidation-completed', '--distribution-id', 'E1X', '--id', '<pending>'])
        for cmd in (static2, data2):
            self.assertIn('--delete', cmd)
            self.assertEqual(cmd[cmd.index('--cache-control') + 1], assets.CACHE_IMMUTABLE)
        self.assertEqual(static2[3:5], ['site/X/static/', 's3://b/static/'])

    def test_nine_with_the_song_pages(self):
        # section 16: song/ is the week class, synced with --delete right after graph/, before the hashed folders
        cmds = deploy.plan('b', 'E1X', 'site/X', present=WITH_SONGS)
        self.assertEqual(len(cmds), 9)
        graphs, songs = cmds[0], cmds[1]
        self.assertEqual(songs[3:5], ['site/X/song/', 's3://b/song/'])
        self.assertIn('--delete', songs)
        self.assertEqual(songs[songs.index('--cache-control') + 1], assets.CACHE_WEEK)
        self.assertEqual(graphs[graphs.index('--cache-control') + 1], assets.CACHE_WEEK)
        self.assertEqual(cmds[2][3:5], ['site/X/static/', 's3://b/static/'])
        pages = cmds[4]
        self.assertEqual(pages[3:5], ['site/X/', 's3://b/'])
        self.assertIn('song/*', [pages[i + 1] for i, a in enumerate(pages) if a == '--exclude'])
        with tempfile.TemporaryDirectory() as tmp:
            site = pathlib.Path(tmp)
            for d in ('static', 'data', 'song'):
                (site / d).mkdir()
            self.assertEqual(len(deploy.plan('b', None, site, dry_run=True)), 7)
            self.assertEqual(deploy.skipped_dirs(site), [])

    def test_six_without_a_distribution(self):
        cmds = deploy.plan('b', None, 'site/X', present=BOTH)
        self.assertEqual(len(cmds), 6)
        self.assertTrue(all(c[1] == 's3' for c in cmds))
        self.assertEqual(len(deploy.plan('b', '', 'site/X', present=BOTH)), 6)

    def test_absent_directories_are_skipped(self):
        cmds = deploy.plan('b', 'E1X', 'site/X', present=set())
        self.assertEqual(len(cmds), 4)
        self.assertTrue(all('static' not in ' '.join(c) and 'data/' not in ' '.join(c) or c[1] == 's3' and 'exclude' in ' '.join(c) for c in cmds))
        with tempfile.TemporaryDirectory() as tmp:
            site = pathlib.Path(tmp)
            (site / 'static').mkdir()
            self.assertEqual(deploy.skipped_dirs(site), ['data'])
            self.assertEqual(len(deploy.plan('b', None, site, dry_run=True)), 4)

    def test_dry_run_appends_to_syncs_only(self):
        cmds = deploy.plan('b', 'E1X', 'site/X', dry_run=True, present=BOTH)
        for c in cmds:
            if c[1] == 's3':
                self.assertEqual(c[-1], '--dryrun')
            else:
                self.assertNotIn('--dryrun', c)
        wet = deploy.plan('b', 'E1X', 'site/X', dry_run=False, present=BOTH)
        self.assertTrue(all('--dryrun' not in c for c in wet))

    def test_samples_by_glob(self):
        with tempfile.TemporaryDirectory() as tmp:
            site = pathlib.Path(tmp)
            (site / 'graph').mkdir()
            (site / 'index.html').write_bytes(b'x')
            self.assertEqual(deploy.samples(site), {'index.html': ('text/html', assets.CACHE_PAGE)})
            (site / 'static').mkdir()
            (site / 'static' / 'app.abcd1234.js').write_bytes(b'x')
            (site / 'data').mkdir()
            (site / 'data' / 'guitar.abcd1234.json').write_bytes(b'x')
            (site / 'graph' / '0002.png').write_bytes(b'x')
            (site / 'graph' / '0001.png').write_bytes(b'x')
            found = deploy.samples(site)
            self.assertEqual(found['static/app.abcd1234.js'], ('text/javascript', assets.CACHE_IMMUTABLE))
            self.assertEqual(found['data/guitar.abcd1234.json'], ('application/json', assets.CACHE_IMMUTABLE))
            self.assertEqual(found['graph/0001.png'], ('image/png', assets.CACHE_GRAPHS))
            self.assertNotIn('robots.txt', found)
            (site / 'song').mkdir()
            (site / 'song' / '0000000000a1.html').write_bytes(b'x')
            (site / 'sitemap.xml').write_bytes(b'x')
            found = deploy.samples(site)
            self.assertEqual(found['song/0000000000a1.html'], ('text/html', assets.CACHE_WEEK))
            self.assertEqual(found['sitemap.xml'], ('application/xml', assets.CACHE_PAGE))


class CacheClassTest(unittest.TestCase):

    def test_classes(self):
        self.assertEqual(assets.cache_class('/index.html'), assets.CACHE_PAGE)
        self.assertEqual(assets.cache_class('about.html'), assets.CACHE_PAGE)
        self.assertEqual(assets.cache_class('/static/app.1234abcd.js'), assets.CACHE_IMMUTABLE)
        self.assertEqual(assets.cache_class('data/guitar.1234abcd.json'), assets.CACHE_IMMUTABLE)
        self.assertEqual(assets.cache_class('graph/0001XG.png'), assets.CACHE_GRAPHS)
        self.assertEqual(assets.cache_class('graph/manifest.json'), assets.CACHE_GRAPHS)
        self.assertEqual(assets.cache_class('song/0000000000a1.html'), assets.CACHE_WEEK)
        self.assertEqual(assets.cache_class('sitemap.xml'), assets.CACHE_PAGE)


if __name__ == '__main__':
    unittest.main()
