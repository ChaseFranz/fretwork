"""deploy.plan() and deploy.samples(): the aws commands, read without an aws on PATH."""

import pathlib
import tempfile
import unittest

import deploy


class PlanTest(unittest.TestCase):

    def test_two_syncs_then_invalidation(self):
        cmds = deploy.plan('b', 'E1X', 'site/X')
        self.assertEqual([c[:3] for c in cmds],
                         [['aws', 's3', 'sync'], ['aws', 's3', 'sync'], ['aws', 'cloudfront', 'create-invalidation']])
        graphs, pages, inval = cmds
        self.assertEqual(graphs[3:5], ['site/X/graph/', 's3://b/graph/'])
        self.assertEqual(pages[3:5], ['site/X/', 's3://b/'])
        self.assertEqual(inval[3:], ['--distribution-id', 'E1X', '--paths', '/*'])

    def test_flags(self):
        graphs, pages = deploy.plan('b', None, 'site/X')
        self.assertIn('--delete', graphs)
        self.assertIn('--delete', pages)
        self.assertEqual(pages[pages.index('--exclude') + 1], 'graph/*')
        self.assertNotIn('--exclude', graphs)
        self.assertEqual(graphs[graphs.index('--cache-control') + 1], 'public, max-age=604800')
        self.assertEqual(pages[pages.index('--cache-control') + 1], 'no-cache')

    def test_no_invalidation_without_distribution(self):
        self.assertEqual(len(deploy.plan('b', None, 'site/X')), 2)
        self.assertEqual(len(deploy.plan('b', '', 'site/X')), 2)

    def test_dry_run_appends_to_syncs_only(self):
        cmds = deploy.plan('b', 'E1X', 'site/X', dry_run=True)
        self.assertEqual([c[-1] for c in cmds[:2]], ['--dryrun', '--dryrun'])
        self.assertNotIn('--dryrun', cmds[2])
        wet = deploy.plan('b', 'E1X', 'site/X', dry_run=False)
        self.assertTrue(all('--dryrun' not in c for c in wet))

    def test_samples_with_and_without_a_png(self):
        with tempfile.TemporaryDirectory() as tmp:
            site = pathlib.Path(tmp)
            (site / 'graph').mkdir()
            self.assertEqual(list(deploy.samples(site)),
                             ['index.html', 'static/js/main.js', 'static/css/app.css', 'static/favicon.svg'])
            (site / 'graph' / '0002.png').write_bytes(b'x')
            (site / 'graph' / '0001.png').write_bytes(b'x')
            found = deploy.samples(site)
            self.assertEqual(list(found)[-1], 'graph/0001.png')
            self.assertEqual(found['graph/0001.png'], 'image/png')
            self.assertEqual(found['static/js/main.js'], 'text/javascript')


if __name__ == '__main__':
    unittest.main()
