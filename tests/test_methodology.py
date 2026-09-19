"""The markdown subset, the typesetter, the drift check and the rendered methodology page (section 12)."""

import html.parser
import pathlib
import unittest

from functions import drum_formula, fret_formula as formula, labels, vocal_formula
from web import markdown, methodology, page

REPO = pathlib.Path(__file__).resolve().parents[1]
MD = (REPO / 'Methodology.md').read_text(encoding='utf-8')


class MarkdownTest(unittest.TestCase):

    # The counts pin what the 2026-09-19 upstream file holds (five remap tables and
    # the CalcTier table, 29 display formulas, 15 inline ones, three bullet lists,
    # three rules, seven links, every "omit in toc" comment stripped): an upstream
    # edit that adds a construct the renderer refuses fails in to_html, one that
    # adds more of these moves a number here.
    def test_the_real_file_renders_as_counted(self):
        out = markdown.to_html(MD)
        self.assertEqual(out.count('<table'), 6)
        self.assertEqual(out.count('<math display="block"'), 29)
        self.assertEqual(sum(out.count(f'<h{n} id=') for n in range(1, 5)), 44)
        self.assertEqual(out.count('<code>'), 29)
        self.assertEqual(out.count('<strong>'), 13)
        self.assertEqual(out.count('<em>'), 2)
        self.assertEqual(out.count('<math>'), 15)
        self.assertEqual(out.count('<ul>'), 3)
        self.assertEqual(out.count('<hr>'), 3)
        self.assertEqual(out.count('<a '), 7)
        self.assertNotIn('$$', out)
        self.assertNotIn('**', out)
        self.assertNotIn('`', out)
        self.assertNotIn('omit in toc', out)
        self.assertNotIn('<!--', out)
        ids = [b[3] for b in markdown.parse(MD) if b[0] == 'heading']
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(ids))
        self.assertIn('calctier-calibration', ids)

    def test_shift_moves_every_heading(self):
        out = markdown.to_html(MD, shift=1)
        self.assertEqual(out.count('<h1'), 0)
        self.assertEqual(sum(out.count(f'<h{n} id=') for n in range(2, 6)), 44)

    def test_refusals_name_the_line(self):
        cases = [
            ('ok\n\n1. item', 3), ('- a\n  - b', 2), ('```\nx\n```', 1), ('ok\n\n    code', 3), ('see [a](b)', 1), ('![i](x.png)', 1),
            ('<div>', 1), ('##### deep', 1), ('> > nested', 1), ('$$\n\\foo\n$$', 1), ('*x never closes', 1),
            ('a `code', 1), ('a $\\foo$', 1), ('| a | b |\n| c | d |', 1), ('$$\nx =\n', 1), ('a\n===', 2),
        ]
        for text, line in cases:
            with self.subTest(text=text):
                with self.assertRaises(markdown.MarkdownError) as ctx:
                    markdown.to_html(text)
                self.assertTrue(str(ctx.exception).startswith(f'line {line}:'), str(ctx.exception))

    def test_must_pass_cases(self):
        self.assertIn('raw N * V', markdown.to_html('raw N * V'))
        self.assertIn('<msub>', markdown.to_html('$$\n  - x_1\n$$'))    # a formula line is never a list
        self.assertEqual(markdown.to_html('a *b* and **c**'), '<p>a <em>b</em> and <strong>c</strong></p>')
        self.assertEqual(markdown.to_html('`<b>`'), '<p><code>&lt;b&gt;</code></p>')
        self.assertEqual(markdown.to_html('| a | b |\n|---|---:|\n| 1 | 2 |'),
                         '<div class="tbl"><table><thead><tr><th>a</th><th class="r">b</th></tr></thead>'
                         '<tbody><tr><td>1</td><td class="r">2</td></tr></tbody></table></div>')

    def test_typesetter(self):
        self.assertEqual(markdown.to_html('$$\n\\frac{a}{b}\n$$'),
                         '<div class="eq"><math display="block"><mrow><mfrac><mi>a</mi><mi>b</mi></mfrac></mrow></math></div>')
        out = markdown.to_html('$$\nN = \\Big[(\\mathrm{med}_N + \\varepsilon_N)\\cdot a_N\\Big]^{1/3}\n$$')
        self.assertIn('<mo stretchy="true">[</mo>', out)
        self.assertIn('<mi mathvariant="normal">med</mi>', out)
        self.assertIn('<mi>ε</mi>', out)
        self.assertIn('<msup>', out)
        self.assertIn('<mo>⋅</mo>', out)


class DriftTest(unittest.TestCase):

    # The file's drift against the three modules is exactly the known set: a new
    # one (an upstream refit without its table) or a fixed one moves KNOWN_DRIFT.
    def test_the_real_file_drifts_as_known(self):
        drifts = methodology.check_tables(markdown.parse(MD))
        self.assertEqual([methodology.plain(d) for d in drifts], list(methodology.KNOWN_DRIFT))
        self.assertTrue(all(d.startswith('line ') for d in drifts))
        blocks, again = methodology.load()
        self.assertEqual(again, drifts)
        self.assertTrue(blocks)

    def test_a_number_that_moves_is_a_drift(self):
        cases = {
            'a keys edge': (('(7.8, 13.7]', '(7.8, 13.8]'), ('(13.7, 21.5]', '(13.8, 21.5]'), 'KEYS_REMAP_BINS tier 2 ends at 13.8'),
            'a drum edge': (('(14.0, 16.2]', '(14.0, 16.3]'), ('(16.2, 19.2]', '(16.3, 19.2]'), 'DRUM_REMAP_BINS tier 3 ends at 16.3'),
            'a vocal BASE_D': (('| Vocals |   4.4 |', '| Vocals |   4.5 |'), None, 'CalcTier Vocals is 4.5 / 0.32'),
            'a step': (('|  0.32 |           ~38% |', '|  0.32 |           ~39% |'), None, "step per tier reads '~39%'"),
        }
        for name, (first, second, want) in cases.items():
            with self.subTest(name=name):
                text = MD
                for old, new in (first, second) if second else (first,):
                    self.assertEqual(text.count(old), 1, old)
                    text = text.replace(old, new)
                drifts = [methodology.plain(d) for d in methodology.check_tables(markdown.parse(text))]
                self.assertEqual(len(drifts), len(methodology.KNOWN_DRIFT) + 1, drifts)
                self.assertTrue(any(want in d for d in drifts), drifts)

    def test_a_table_that_cannot_be_read_raises(self):
        cases = {
            'a tier': MD.replace('| 3    | (14.0, 16.2]', '| 4    | (14.0, 16.2]'),
            'a gap': MD.replace('| 3    | (14.0, 16.2]', '| 3    | (14.1, 16.2]'),
            'a removed group': MD.replace('#### Keys (`KEYS_REMAP_BINS`)', '#### Keys'),
            'a tier row without its module': MD.replace('| `vocal_formula.py` |', '| vocals |'),
        }
        for name, text in cases.items():
            with self.subTest(name=name):
                with self.assertRaises(methodology.MethodologyDrift):
                    methodology.check_tables(markdown.parse(text))

    def test_labels_print_the_constants(self):
        for module in (formula, drum_formula, vocal_formula):
            self.assertIn(str(module.LN_INC), labels.COLUMN_HELP['CalcTier'])
            self.assertIn(str(module.BASE_D), labels.COLUMN_HELP['CalcTier'])


class Counter(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags, self.ids, self.first_h2, self.text, self.stack = [], [], None, [], []
        self.in_eq = self.in_tbl = 0
        self.math_in_eq = self.table_in_tbl = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.tags.append((tag, a))
        if tag in ('h2', 'h3', 'h4', 'h5', 'h6'):
            self.ids.append(a.get('id'))
        if tag == 'div' and a.get('class') == 'eq':
            self.in_eq += 1
        if tag == 'div' and a.get('class') == 'tbl':
            self.in_tbl += 1
        if tag == 'math' and a.get('display') == 'block' and self.in_eq:
            self.math_in_eq += 1
        if tag == 'table' and self.in_tbl:
            self.table_in_tbl += 1
        self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag == 'div':
            if self.in_eq:
                self.in_eq -= 1
            elif self.in_tbl:
                self.in_tbl -= 1

    def handle_data(self, data):
        if self.stack and self.stack[-1] == 'h2' and self.first_h2 is None:
            self.first_h2 = data
        self.text.append(data)


class PageTest(unittest.TestCase):

    def test_render_methodology(self):
        names = {'favicon': 'static/favicon.00000000.svg'}
        out = page.render_methodology(names).decode('utf-8') if isinstance(page.render_methodology(names), bytes) \
            else page.render_methodology(names)
        c = Counter()
        c.feed(out)
        count = lambda t: sum(1 for tag, _ in c.tags if tag == t)   # noqa: E731
        self.assertEqual(count('h1'), 1)
        self.assertEqual(sum(count(f'h{n}') for n in range(2, 6)), 44)
        self.assertEqual(len(c.ids), len(set(c.ids)))
        self.assertTrue(all(c.ids))
        self.assertEqual(c.first_h2, 'The Difficulty Formulas')
        self.assertEqual(count('math'), 44)
        self.assertEqual(c.math_in_eq, 29)
        self.assertEqual(count('table'), 6)
        self.assertEqual(c.table_in_tbl, 6)
        self.assertEqual(count('script'), 1)     # the theme's, page.THEME_SCRIPT, and nothing else
        self.assertFalse(any('$$' in t or '**' in t or '|---' in t for t in c.text))
        self.assertIn('href="https://github.com/Staycation44/fretwork/blob/main/Methodology.md"', out)
        # the known drift is on the page, one sentence each, under the source line
        self.assertEqual(out.count('<ul class="drift">'), 1)
        for drift in methodology.KNOWN_DRIFT:
            self.assertIn(f'<li>{drift}.</li>', out)


if __name__ == '__main__':
    unittest.main()
