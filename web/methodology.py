"""
METHODOLOGY - Methodology.md, parsed and checked against functions/formula.py

The engine's Methodology.md mirrors formula.py's calibration tables by hand:
the RemapDiff bin edges per group and the CalcTier constants. Nothing used to
enforce that, and the bins have been refit in commits that touched only
formula.py. load() parses the file through web.markdown and runs
check_tables(), which compares the tables to the code with exact equality
(the markdown prints the decimals the code holds) and raises
MethodologyDrift naming the table, the row and both values. page.render_
methodology() calls it, so the check runs on every serve start and every
publish; the __main__ runs it alone, for CI and for a maintainer merging
upstream.

    python -m web.methodology

The Official and Remap percentage columns are measurements of the reference
library at calibration time, which the repo does not hold; they are checked
only for shape (a percentage each, summing to about 100) and printed as written.
"""

import math
import pathlib
import re
import sys

from functions import formula
from web import markdown

MD_PATH = pathlib.Path(__file__).resolve().parent.parent / 'Methodology.md'
REMAP_HEADER = ['Tier', 'D range', 'Official', 'Remap']
TIER_HEADER = ['Group', 'BASE_D', 'LN_INC']
D_RANGE = re.compile(r'\((\d+(?:\.\d+)?), (\d+(?:\.\d+)?|inf)[\])]')
PERCENT = re.compile(r'\d+\.\d%')
BINS_NAME = re.compile(r'<code>([A-Z]+_REMAP_BINS)</code>')


class MethodologyDrift(ValueError):
    pass


def _number(text):
    return math.inf if text == 'inf' else float(text)


def _check_remap(name, table):
    header, rows, line = table[1], table[3], table[4]
    if header != REMAP_HEADER:
        raise MethodologyDrift(f'line {line}: the {name} table header is {header}, expected {REMAP_HEADER}')
    bins = getattr(formula, name, None)
    if bins is None or bins not in formula.REMAP_BINS.values():
        raise MethodologyDrift(f'line {line}: formula.py has no calibration group named {name}')
    tiers = [int(r[0]) for r in rows]
    if tiers != formula.DIFF_LABELS:
        raise MethodologyDrift(f'line {line}: {name} tiers are {tiers}, formula.DIFF_LABELS is {formula.DIFF_LABELS}')
    edges = [0.0]
    for k, row in enumerate(rows):
        m = D_RANGE.fullmatch(row[1])
        if not m:
            raise MethodologyDrift(f'line {line + 2 + k}: {name} tier {tiers[k]} has a D range of {row[1]!r}, not "(lower, upper]"')
        lower, upper = _number(m.group(1)), _number(m.group(2))
        if lower != edges[-1]:
            raise MethodologyDrift(f'line {line + 2 + k}: {name} tier {tiers[k]} starts at {lower}, the row above ends at {edges[-1]}')
        edges.append(upper)
        if upper != bins[k + 1]:
            raise MethodologyDrift(f'line {line + 2 + k}: {name} tier {tiers[k]} ends at {upper} in Methodology.md '
                                   f'but at {bins[k + 1]} in formula.py')
    if edges[-1] != math.inf:
        raise MethodologyDrift(f'line {line}: {name} last tier must end at inf')
    if edges != [float(b) for b in bins]:
        raise MethodologyDrift(f'line {line}: {name} edges {edges} differ from formula.py {bins}')
    for col, label in ((2, 'Official'), (3, 'Remap')):
        cells = [r[col] for r in rows]
        if not all(PERCENT.fullmatch(c) for c in cells):
            raise MethodologyDrift(f'line {line}: {name} {label} column is not all percentages: {cells}')
        total = sum(float(c[:-1]) for c in cells)
        if abs(total - 100) > 0.5:
            raise MethodologyDrift(f'line {line}: {name} {label} column sums to {total:.1f}, not 100')


def _check_tiers(table):
    header, rows, line = table[1], table[3], table[4]
    if header != TIER_HEADER:
        raise MethodologyDrift(f'line {line}: the CalcTier table header is {header}, expected {TIER_HEADER}')
    groups = {r[0].lower() for r in rows}
    if groups != set(formula.REMAP_BINS):
        raise MethodologyDrift(f'line {line}: CalcTier groups {sorted(groups)} differ from formula.REMAP_BINS {sorted(formula.REMAP_BINS)}')
    for k, row in enumerate(rows):
        base, inc = float(row[1]), float(row[2])
        if base != formula.BASE_D or inc != formula.LN_INC:
            raise MethodologyDrift(f'line {line + 2 + k}: CalcTier {row[0]} is {base} / {inc} in Methodology.md '
                                   f'but formula.py holds BASE_D {formula.BASE_D} / LN_INC {formula.LN_INC}')


def check_tables(blocks):
    """Every RemapDiff table against its named bins, and the CalcTier table against the constants."""
    found, tiers = set(), None
    for i, block in enumerate(blocks):
        if block[0] == 'heading' and block[1] == 4:
            m = BINS_NAME.search(markdown.render([block]))
            if not m:
                continue
            name = m.group(1)
            nxt = blocks[i + 1] if i + 1 < len(blocks) else None
            if nxt is None or nxt[0] != 'table':
                raise MethodologyDrift(f'line {block[-1]}: the {name} heading is not followed by its table')
            _check_remap(name, nxt)
            found.add(name)
        elif block[0] == 'table' and block[1] == TIER_HEADER:
            tiers = block
    want = {n for n in dir(formula) if n.endswith('_REMAP_BINS') and getattr(formula, n) in formula.REMAP_BINS.values()}
    if found != want:
        raise MethodologyDrift(f'the tables cover {sorted(found)}; formula.py has {sorted(want)}')
    if tiers is None:
        raise MethodologyDrift('no CalcTier table (header Group, BASE_D, LN_INC)')
    _check_tiers(tiers)
    return len(found)


def load(path=MD_PATH):
    path = pathlib.Path(path)
    try:
        blocks = markdown.parse(path.read_text(encoding='utf-8'))
    except markdown.MarkdownError as err:
        raise markdown.MarkdownError(f'{path.name}: {err}') from None
    try:
        check_tables(blocks)
    except MethodologyDrift as err:
        raise MethodologyDrift(f'{path.name}: {err}') from None
    return blocks


def main():
    try:
        blocks = load()
    except (markdown.MarkdownError, MethodologyDrift) as err:
        print(err, file=sys.stderr)
        sys.exit(1)
    groups = len(formula.REMAP_BINS)
    print(f'{MD_PATH.name}: tables match formula.py ({groups} remap groups, CalcTier {formula.BASE_D} / {formula.LN_INC})')
    return blocks


if __name__ == '__main__':
    main()
