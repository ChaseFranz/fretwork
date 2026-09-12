"""The strings CLAUDE.md pins: the copyright notice, and the two rich-text renderers."""

import pathlib
import re
import unittest

from functions import labels
from web import page

REPO = pathlib.Path(__file__).resolve().parents[1]
STRIP = re.compile(r'<[^>]+>|\[([^\]]+)\]\([^)]*\)')


def plain(text):
    return STRIP.sub(lambda m: m.group(1) or '', text)


class CopyrightTest(unittest.TestCase):

    # The fork's LICENSE is byte-identical to upstream's, so the notice must name
    # Staycation exactly as line 3 of LICENSE does; "Staycation44" must not pass.
    def test_notice_matches_license(self):
        line = REPO.joinpath('LICENSE').read_text(encoding='utf-8').splitlines()[2].strip()
        self.assertRegex(line.lower(), r'^copyright \(c\) \d{4} staycation$')
        surfaces = [plain(labels.UI['copyright'])] + [plain(body) for _, body in labels.ABOUT]
        hits = [s for s in surfaces if re.search(re.escape(line) + r'(?![A-Za-z0-9])', s, re.I)]
        self.assertGreaterEqual(len(hits), 2, surfaces)


class RichTextTest(unittest.TestCase):

    def test_https_link_becomes_an_anchor(self):
        out = page.rich_text('see [the repo](https://example.com/x) now')
        self.assertEqual(out, 'see <a href="https://example.com/x" rel="noopener">the repo</a> now')

    def test_everything_is_escaped(self):
        self.assertEqual(page.rich_text('a <b> & "c"'), 'a &lt;b&gt; &amp; &quot;c&quot;')
        self.assertEqual(page.rich_text('[<x>](https://e.com/?a=1&b=2)'),
                         '<a href="https://e.com/?a=1&amp;b=2" rel="noopener">&lt;x&gt;</a>')

    def test_non_http_target_gives_text_only(self):
        self.assertEqual(page.rich_text('[x](javascript:alert(1))'), 'x')
        self.assertEqual(page.rich_text('[x](../y.html)'), 'x')

    def test_balanced_parentheses_stay_in_the_url(self):
        out = page.rich_text('[w](https://en.wikipedia.org/wiki/Foo_(bar)) end')
        self.assertEqual(out, '<a href="https://en.wikipedia.org/wiki/Foo_(bar)" rel="noopener">w</a> end')


if __name__ == '__main__':
    unittest.main()
