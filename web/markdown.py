"""
MARKDOWN - a subset renderer for Methodology.md that refuses what it does not know

Exactly the constructs the engine's Methodology.md uses: ATX headings h1-h4,
paragraphs, one level of blockquote, pipe tables with an alignment row, $$
display math, and the inline forms `code`, **bold**, *italic* and $X$. Every
character of prose goes through html.escape; the only markup emitted is what
this module builds. Anything else (a list, a link, fenced or indented code, a
rule, HTML, a deeper heading, an unknown LaTeX command) raises MarkdownError
naming the line, so an upstream edit fails publish loudly instead of rendering
as literal asterisks on the live site. Extend the allow-list deliberately; do
not loosen the refusals into "render as text".

Display math is typeset to MathML Core (every current engine draws it) by a
recursive descent over an allow-list of tokens; no CDN, no image, no library.

    python -m web.markdown Methodology.md [--shift N] > out.html

Stdlib only: html and re. Nothing here imports pandas, matplotlib or openpyxl.
"""

import argparse
import html
import re
import sys


class MarkdownError(ValueError):
    """Raised with a message of the form 'line <n>: <what>'."""


# --- refusals: the constructs the file does not use, and must not start using silently

REFUSE = (
    (re.compile(r'^\s*(\d+\.)\s'), 'an ordered list is not supported'),
    (re.compile(r'^\s+[-*+]\s'), 'a nested list is not supported'),
    (re.compile(r'^```'), 'a fenced code block is not supported'),
    (re.compile(r'^(    |\t)'), 'an indented code block is not supported'),
    (re.compile(r'^===+\s*$'), 'a setext heading is not supported'),
    (re.compile(r'^<'), 'an HTML block is not supported'),
)
HEADING = re.compile(r'^(#{1,6})\s+(.*)$')
ALIGN_CELL = re.compile(r'^:?-+:?$')
BULLET = re.compile(r'^[-*+]\s+(.*)$')     # a flat unordered list, one line per item (upstream's 2026-09 edit)
RULE = re.compile(r'^---+\s*$')              # a thematic break between the instrument families


def _cells(line):
    inner = line.strip()
    if inner.startswith('|'):
        inner = inner[1:]
    if inner.endswith('|'):
        inner = inner[:-1]
    return [c.strip() for c in inner.split('|')]


def _slug(text, taken):
    plain = re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')
    slug, n = plain, 1
    while slug in taken:
        n += 1
        slug = f'{plain}-{n}'
    taken.add(slug)
    return slug


COMMENT = re.compile(r'<!--.*?-->')    # a toc generator's "omit in toc" marks on the headings: not content


def parse(text):
    """The file as block tuples, each ending with the 1-based line it starts on."""
    lines = [COMMENT.sub('', line).rstrip() for line in text.split('\n')]
    blocks, taken = [], set()
    i, n = 0, len(lines)
    para = []

    def flush():
        if para:
            blocks.append(('paragraph', ' '.join(s.strip() for s in para), para_line[0]))
            para.clear()
    para_line = [0]

    while i < n:
        line = lines[i]
        at = i + 1
        stripped = line.strip()
        if stripped == '$$':
            flush()
            j = i + 1
            while j < n and lines[j].strip() != '$$':
                j += 1
            if j >= n:
                raise MarkdownError(f'line {at}: unclosed $$ block')
            blocks.append(('math', '\n'.join(lines[i + 1:j]), at))
            i = j + 1
            continue
        for pattern, what in REFUSE:
            if pattern.search(line):
                raise MarkdownError(f'line {at}: {what}')
        if not stripped:
            flush()
            i += 1
            continue
        m = HEADING.match(line)
        if m:
            flush()
            level = len(m.group(1))
            if level > 4:
                raise MarkdownError(f'line {at}: a heading deeper than h4 is not supported')
            heading = m.group(2).rstrip()
            blocks.append(('heading', level, heading, _slug(heading, taken), at))
            i += 1
            continue
        if RULE.match(line):
            flush()
            blocks.append(('rule', at))
            i += 1
            continue
        if BULLET.match(line):
            flush()
            items = []
            while i < n and BULLET.match(lines[i]):
                items.append(BULLET.match(lines[i]).group(1).rstrip())
                i += 1
            blocks.append(('list', items, at))
            continue
        if stripped.startswith('>'):
            flush()
            paras, cur = [], []
            while i < n and lines[i].strip().startswith('>'):
                body = lines[i].strip()[1:]
                if body.lstrip().startswith('>'):
                    raise MarkdownError(f'line {i + 1}: a nested blockquote is not supported')
                if not body.strip():
                    if cur:
                        paras.append(' '.join(cur))
                        cur = []
                else:
                    cur.append(body.strip())
                i += 1
            if cur:
                paras.append(' '.join(cur))
            blocks.append(('quote', paras, at))
            continue
        if stripped.startswith('|'):
            flush()
            rows = []
            while i < n and lines[i].strip().startswith('|'):
                rows.append(_cells(lines[i]))
                i += 1
            if len(rows) < 2 or not all(ALIGN_CELL.match(c) for c in rows[1]):
                raise MarkdownError(f'line {at}: a table needs an alignment row after its header')
            header = rows[0]
            if len(rows[1]) != len(header):
                raise MarkdownError(f'line {at + 1}: the alignment row has {len(rows[1])} cells, the header {len(header)}')
            align = ['r' if c.endswith(':') and not c.startswith(':') else 'c' if c.startswith(':') and c.endswith(':') else 'l'
                     for c in rows[1]]
            for k, row in enumerate(rows[2:], start=at + 2):
                if len(row) != len(header):
                    raise MarkdownError(f'line {k}: a table row has {len(row)} cells, the header {len(header)}')
            blocks.append(('table', header, align, rows[2:], at))
            continue
        if not para:
            para_line[0] = at
        para.append(line)
        i += 1
    flush()
    return blocks


# --- inline rules, applied on placeholders so they cannot nest wrongly ----------------

CODE = re.compile(r'`([^`]+)`')
# a link to a heading on the same page, the only link form the file uses:
# [text](#slug), where the slug is a heading's own (checked at render)
ANCHOR = re.compile(r'\[([^\]]+)\]\(#([a-z0-9-]+)\)')
INLINE_MATH = re.compile(r'\$([^$]*)\$')
BOLD = re.compile(r'\*\*(.+?)\*\*')
ITALIC = re.compile(r'\*(?=\S)(.+?)(?<=\S)\*')
LEFTOVER = (
    (re.compile(r'\[[^\]]*\]\([^)]*\)'), 'a link is not supported'),
    (re.compile(r'!\['), 'an image is not supported'),
    (re.compile(r'<[a-zA-Z/]'), 'inline HTML is not supported'),
    (re.compile(r'`'), 'an unclosed code span'),
    (re.compile(r'\*\*'), 'an unclosed bold span'),
    (re.compile(r'\$'), 'an unclosed inline math span'),
    (re.compile(r'\*(?=\S)'), 'an emphasis opener that never closes'),
)


def _inline(text, line):
    held = []

    def hold(markup):
        held.append(markup)
        return f'\x00{len(held) - 1}\x00'

    def code(m):
        return hold('<code>' + html.escape(m.group(1)) + '</code>')

    def imath(m):
        # an identifier, or a short expression in the same subset the display formulas use
        return hold('<math>' + _math(m.group(1), line) + '</math>')

    out = CODE.sub(code, text)
    out = ANCHOR.sub(lambda m: hold(f'<a href="#{html.escape(m.group(2))}">' + html.escape(m.group(1)) + '</a>'), out)
    out = INLINE_MATH.sub(imath, out)
    out = BOLD.sub(lambda m: hold('<strong>' + html.escape(m.group(1)) + '</strong>'), out)
    out = ITALIC.sub(lambda m: hold('<em>' + html.escape(m.group(1)) + '</em>'), out)
    for pattern, what in LEFTOVER:
        if pattern.search(out):
            raise MarkdownError(f'line {line}: {what}')
    out = html.escape(out)
    return re.sub(r'\x00(\d+)\x00', lambda m: held[int(m.group(1))], out)


# --- the typesetter: a LaTeX subset to MathML Core -----------------------------------

MATH_TOKEN = re.compile(r'\\[A-Za-z]+|\\[,;]|[A-Za-z]+|\d+(?:\.\d+)?|\s+|.')
SYMBOLS = {'\\varepsilon': 'ε', '\\sigma': 'σ'}
SPACES = {'\\,': '0.17em', '\\;': '0.28em', '\\qquad': '2em'}
OPERATORS = {'=': '=', '+': '+', '-': '−', ',': ',', '/': '/', '\\cdot': '⋅', '\\approx': '≈', '<': '&lt;', '>': '&gt;'}


class _Math:
    def __init__(self, latex, line):
        self.tokens = [t for t in MATH_TOKEN.findall(latex) if not t.isspace()]
        self.pos = 0
        self.line = line

    def fail(self, what):
        raise MarkdownError(f'line {self.line}: {what}')

    def peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def take(self):
        tok = self.peek()
        if tok is None:
            self.fail('formula ends early')
        self.pos += 1
        return tok

    def expect(self, tok):
        if self.take() != tok:
            self.fail(f'expected {tok!r}')

    def group(self):
        """A {...} group as one node, or a single atom."""
        if self.peek() == '{':
            self.take()
            nodes = self.row(until='}')
            self.expect('}')
            return self.wrap(nodes)
        return self.atom()

    def wrap(self, nodes):
        return nodes[0] if len(nodes) == 1 else '<mrow>' + ''.join(nodes) + '</mrow>'

    def atom(self):
        tok = self.take()
        if tok in SYMBOLS:
            return f'<mi>{SYMBOLS[tok]}</mi>'
        if tok in SPACES:
            return f'<mspace width="{SPACES[tok]}"/>'
        if tok in OPERATORS:
            return f'<mo>{OPERATORS[tok]}</mo>'
        if tok == '\\mathrm':
            self.expect('{')
            name = self.take()
            if not re.fullmatch(r'[A-Za-z]+', name):
                self.fail('\\mathrm needs letters')
            self.expect('}')
            return f'<mi mathvariant="normal">{name}</mi>'
        if tok == '\\frac':
            return '<mfrac>' + self.group() + self.group() + '</mfrac>'
        if tok == '\\sqrt':
            return '<msqrt>' + self.group() + '</msqrt>'
        if tok == '(':
            nodes = self.row(until=')')
            self.expect(')')
            return '<mrow><mo>(</mo>' + ''.join(nodes) + '<mo>)</mo></mrow>'
        if tok == '\\Big':
            fence = self.take()
            if fence != '[':
                self.fail('\\Big is only supported around [ ... ]')
            nodes = self.row(until='\\Big]')
            self.expect('\\Big')
            self.expect(']')
            return '<mrow><mo stretchy="true">[</mo>' + ''.join(nodes) + '<mo stretchy="true">]</mo></mrow>'
        if tok == '\\left':
            fence = self.take()
            if fence != '(':
                self.fail('\\left is only supported around ( ... )')
            nodes = self.row(until='\\right')
            self.expect('\\right')
            self.expect(')')
            return '<mrow><mo stretchy="true">(</mo>' + ''.join(nodes) + '<mo stretchy="true">)</mo></mrow>'
        if re.fullmatch(r'[A-Za-z]+', tok):
            return f'<mi>{tok}</mi>'
        if re.fullmatch(r'\d+(?:\.\d+)?', tok):
            return f'<mn>{tok}</mn>'
        self.fail(f'unsupported token {tok!r} in a formula')

    def row(self, until):
        nodes = []
        while True:
            tok = self.peek()
            if tok is None:
                if until is None:
                    return nodes
                self.fail(f'missing {until!r}')
            if until == '\\Big]' and tok == '\\Big' and self.pos + 1 < len(self.tokens) and self.tokens[self.pos + 1] == ']':
                return nodes
            if tok == until:
                return nodes
            if tok in ('}', ')', ']'):
                self.fail(f'unbalanced {tok!r}')
            if tok in ('_', '^'):
                if not nodes:
                    self.fail('a script with nothing before it')
                self.take()
                base = nodes.pop()
                script = self.group()
                nodes.append(('<msub>' if tok == '_' else '<msup>') + base + script + ('</msub>' if tok == '_' else '</msup>'))
                continue
            nodes.append(self.atom())

    def render(self):
        nodes = self.row(until=None)
        if not nodes:
            self.fail('an empty formula')
        return '<mrow>' + ''.join(nodes) + '</mrow>'


def _math(latex, line):
    return _Math(latex, line).render()


# --- rendering ------------------------------------------------------------------------

def render(blocks, shift=0):
    out = []
    for block in blocks:
        kind, line = block[0], block[-1]
        if kind == 'heading':
            level = block[1] + shift
            if level > 6:
                raise MarkdownError(f'line {line}: heading level {level} after the shift')
            out.append(f'<h{level} id="{html.escape(block[3])}">{_inline(block[2], line)}</h{level}>')
        elif kind == 'paragraph':
            out.append('<p>' + _inline(block[1], line) + '</p>')
        elif kind == 'quote':
            out.append('<blockquote>' + ''.join('<p>' + _inline(p, line) + '</p>' for p in block[1]) + '</blockquote>')
        elif kind == 'list':
            out.append('<ul>' + ''.join('<li>' + _inline(item, line) + '</li>' for item in block[1]) + '</ul>')
        elif kind == 'rule':
            out.append('<hr>')
        elif kind == 'math':
            out.append('<div class="eq"><math display="block">' + _math(block[1], line) + '</math></div>')
        elif kind == 'table':
            header, align, rows = block[1], block[2], block[3]
            cls = lambda a: '' if a == 'l' else f' class="{a}"'   # noqa: E731
            head = ''.join(f'<th{cls(a)}>{_inline(c, line)}</th>' for c, a in zip(header, align))
            body = ''.join('<tr>' + ''.join(f'<td{cls(a)}>{_inline(c, line)}</td>' for c, a in zip(row, align)) + '</tr>'
                           for row in rows)
            out.append(f'<div class="tbl"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>')
        else:
            raise MarkdownError(f'line {line}: unknown block {kind!r}')
    return '\n'.join(out)


def to_html(text, shift=0):
    return render(parse(text), shift)


def main():
    ap = argparse.ArgumentParser(description='Render a markdown file through the subset renderer.')
    ap.add_argument('file')
    ap.add_argument('--shift', type=int, default=0, help='move every heading down this many levels')
    args = ap.parse_args()
    try:
        with open(args.file, encoding='utf-8') as f:
            body = to_html(f.read(), args.shift)
    except MarkdownError as err:
        print(f'{args.file}: {err}', file=sys.stderr)
        sys.exit(1)
    print('<meta charset="utf-8">')
    print(body)


if __name__ == '__main__':
    main()
