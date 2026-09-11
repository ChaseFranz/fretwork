"""The markdown subset, the typesetter, the drift check and the rendered methodology page (section 12)."""

import html.parser
import pathlib
import unittest

from functions import formula, labels
from web import markdown, methodology, page

REPO = pathlib.Path(__file__).resolve().parents[1]
MD = (REPO / 'Methodology.md').read_text(encoding='utf-8')


class MarkdownTest(unittest.TestCase):

    def test_the_real_file_renders_as_counted(self):
        out = markdown.to_html(MD)
        self.assertEqual(out.count('<table'), 4)
        self.assertEqual(out.count('<math display="block"'), 7)
        self.assertEqual(sum(out.count(f'<h{n} id=') for n in range(1, 5)), 17)
        self.assertEqual(out.count('<code>'), 16)
        self.assertEqual(out.count('<strong>'), 3)
        self.assertEqual(out.count('<em>'), 3)
        self.assertEqual(out.count('<math><mi>'), 3)
        self.assertEqual(out.count('N * V'), 1)
        self.assertNotIn('$$', out)
        self.assertNotIn('**', out)
        self.assertNotIn('`', out)
        ids = [b[3] for b in markdown.parse(MD) if b[0] == 'heading']
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(ids))
        self.assertIn('calctier-calibration', ids)

    def test_shift_moves_every_heading(self):
        out = markdown.to_html(MD, shift=1)
        self.assertEqual(out.count('<h1'), 0)
        self.assertEqual(sum(out.count(f'<h{n} id=') for n in range(2, 6)), 17)

    def test_refusals_name_the_line(self):
        cases = [
            ('ok\n\n- item', 3), ('```\nx\n```', 1), ('ok\n\n    code', 3), ('see [a](b)', 1), ('![i](x.png)', 1),
            ('<div>', 1), ('##### deep', 1), ('> > nested', 1), ('$$\n\\foo\n$$', 1), ('*x never closes', 1),
            ('a `code', 1), ('a $x y$', 1), ('| a | b |\n| c | d |', 1), ('$$\nx =\n', 1),
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

    def test_the_real_file_matches(self):
        self.assertEqual(methodology.check_tables(markdown.parse(MD)), 3)

    def test_mutations_are_caught(self):
        cases = {
            'an edge': MD.replace('| 2    | (13.7, 21.2]', '| 2    | (13.7, 21.3]'),
            'a tier': MD.replace('| 3    | (21.2, 29.0]', '| 4    | (21.2, 29.0]'),
            'a BASE_D': MD.replace('| Bass   |    7.6 |', '| Bass   |    7.7 |'),
            'a removed group': MD.replace('#### Keys (`KEYS_REMAP_BINS`)', '#### Keys'),
        }
        for name, text in cases.items():
            with self.subTest(name=name):
                with self.assertRaises(methodology.MethodologyDrift):
                    methodology.check_tables(markdown.parse(text))

    def test_labels_print_the_constants(self):
        self.assertIn(str(formula.LN_INC), labels.COLUMN_HELP['CalcTier'])
        self.assertIn(str(formula.BASE_D), labels.COLUMN_HELP['CalcTier'])


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
        self.assertEqual(sum(count(f'h{n}') for n in range(2, 6)), 17)
        self.assertEqual(len(c.ids), len(set(c.ids)))
        self.assertTrue(all(c.ids))
        self.assertEqual(c.first_h2, 'The Difficulty Formula')
        self.assertEqual(count('math'), 10)
        self.assertEqual(c.math_in_eq, 7)
        self.assertEqual(count('table'), 4)
        self.assertEqual(c.table_in_tbl, 4)
        self.assertEqual(count('script'), 0)
        self.assertFalse(any('$$' in t or '**' in t or '|---' in t for t in c.text))
        self.assertIn('href="https://github.com/Staycation44/fretwork/blob/main/Methodology.md"', out)


if __name__ == '__main__':
    unittest.main()
