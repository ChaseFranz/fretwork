"""
METHODOLOGY - Methodology.md, parsed and checked against the three formula modules

The engine's Methodology.md mirrors the calibration tables by hand: the
RemapDiff bin edges per group (five tables, each headed by the name of its
constant, which lives in fret_formula.py, drum_formula.py or
vocal_formula.py) and the CalcTier constants (one table, a row per family
naming its module in the Home column). Nothing upstream enforces that, and
the bins have been refit in commits that touched only the code. load()
parses the file through web.markdown and runs check_tables(), which compares
the tables to the code with exact equality (the markdown prints the decimals
the code holds) and returns the drifts it finds, each a sentence naming the
table, the row and both values; a table that cannot be read at all (a
missing table, an unexpected header) raises MethodologyDrift.

This fork never edits Methodology.md, so a drift is reported, not fixed:
page.render_methodology() prints each on every serve start and every publish
and puts a note on the page, since the document is upstream's word and the
code is what scored the charts. KNOWN_DRIFT is the drift upstream has been
told about; the __main__ (for CI and for a maintainer merging upstream) exits
non-zero on any other, and tests/test_methodology.py pins the set, so a new
one is noticed at the merge and an old one's fix is noticed too.

    python -m web.methodology

The Official and Remap percentage columns are measurements of the reference
library at calibration time, which the repo does not hold; they are checked
only for shape (a percentage each, summing to about 100) and printed as written.
"""

import math
import pathlib
import re
import sys

from functions import drum_formula, fret_formula, vocal_formula
from web import markdown

MD_PATH = pathlib.Path(__file__).resolve().parent.parent / 'Methodology.md'
MODULES = {'fret_formula.py': fret_formula, 'drum_formula.py': drum_formula, 'vocal_formula.py': vocal_formula}
REMAP_HEADER = ['Tier', 'D range', 'Official', 'Remap']
TIER_HEADER = ['Group', 'BASE_D', 'LN_INC', 'D step per tier', 'Home']
D_RANGE = re.compile(r'\((\d+(?:\.\d+)?), (\d+(?:\.\d+)?|inf)[\])]')
PERCENT = re.compile(r'\d+\.\d%')
STEP = re.compile(r'~(\d+)%')
BINS_NAME = re.compile(r'<code>([A-Z]+_REMAP_BINS)</code>')
HOME = re.compile(r'<code>([a-z_]+\.py)</code>')

# Upstream's Methodology.md against upstream's code at the 2026-09-19 merge
# (commits ef0f1f8 and fa7bc59 refit the constants without the tables). Each
# entry is the sentence check_tables returns, less the "line N: " prefix.
KNOWN_DRIFT = (
    'GUITAR_REMAP_BINS tier 0 ends at 9.1 in Methodology.md but at 11.3 in fret_formula.py',
    'GUITAR_REMAP_BINS tier 1 ends at 13.6 in Methodology.md but at 16.6 in fret_formula.py',
    'GUITAR_REMAP_BINS tier 2 ends at 20.3 in Methodology.md but at 24.5 in fret_formula.py',
    'GUITAR_REMAP_BINS tier 3 ends at 28.0 in Methodology.md but at 33.5 in fret_formula.py',
    'GUITAR_REMAP_BINS tier 4 ends at 36.9 in Methodology.md but at 44.5 in fret_formula.py',
    'GUITAR_REMAP_BINS tier 5 ends at 53.5 in Methodology.md but at 65.6 in fret_formula.py',
    'CalcTier Drums is 9.0 / 0.2 in Methodology.md but drum_formula.py holds BASE_D 9 / LN_INC 0.196',
)


class MethodologyDrift(ValueError):
    pass


def _number(text):
    return math.inf if text == 'inf' else float(text)


# The module holding a named bins constant, or None.
def _home_of(name):
    for file, module in MODULES.items():
        bins = getattr(module, name, None)
        if isinstance(bins, list):
            return file, bins
    return None, None


def _check_remap(name, table):
    header, rows, line = table[1], table[3], table[4]
    if header != REMAP_HEADER:
        raise MethodologyDrift(f'line {line}: the {name} table header is {header}, expected {REMAP_HEADER}')
    home, bins = _home_of(name)
    if bins is None:
        raise MethodologyDrift(f'line {line}: no formula module has a calibration group named {name}')
    module = MODULES[home]
    tiers = [int(r[0]) for r in rows]
    if tiers != module.DIFF_LABELS:
        raise MethodologyDrift(f'line {line}: {name} tiers are {tiers}, {home} DIFF_LABELS is {module.DIFF_LABELS}')
    drifts, edges = [], [0.0]
    for k, row in enumerate(rows):
        m = D_RANGE.fullmatch(row[1])
        if not m:
            raise MethodologyDrift(f'line {line + 2 + k}: {name} tier {tiers[k]} has a D range of {row[1]!r}, not "(lower, upper]"')
        lower, upper = _number(m.group(1)), _number(m.group(2))
        if lower != edges[-1]:
            raise MethodologyDrift(f'line {line + 2 + k}: {name} tier {tiers[k]} starts at {lower}, the row above ends at {edges[-1]}')
        edges.append(upper)
        if upper != bins[k + 1]:
            drifts.append(f'line {line + 2 + k}: {name} tier {tiers[k]} ends at {upper} in Methodology.md '
                          f'but at {bins[k + 1]} in {home}')
    if edges[-1] != math.inf:
        raise MethodologyDrift(f'line {line}: {name} last tier must end at inf')
    for col, label in ((2, 'Official'), (3, 'Remap')):
        cells = [r[col] for r in rows]
        if not all(PERCENT.fullmatch(c) for c in cells):
            raise MethodologyDrift(f'line {line}: {name} {label} column is not all percentages: {cells}')
        total = sum(float(c[:-1]) for c in cells)
        if abs(total - 100) > 0.5:
            raise MethodologyDrift(f'line {line}: {name} {label} column sums to {total:.1f}, not 100')
    return drifts


# The CalcTier table: a row per family, its module named in the Home column,
# BASE_D and LN_INC against that module, and the step column against LN_INC.
def _check_tiers(table):
    header, rows, line = table[1], table[3], table[4]
    if header != TIER_HEADER:
        raise MethodologyDrift(f'line {line}: the CalcTier table header is {header}, expected {TIER_HEADER}')
    homes = [HOME.search(markdown._inline(r[4], 0)) for r in rows]
    if any(h is None for h in homes) or sorted(h.group(1) for h in homes) != sorted(MODULES):
        raise MethodologyDrift(f'line {line}: the CalcTier rows name {[r[4] for r in rows]}, expected one row per {sorted(MODULES)}')
    drifts = []
    for k, (row, home) in enumerate(zip(rows, homes)):
        module = MODULES[home.group(1)]
        base, inc = float(row[1]), float(row[2])
        if base != module.BASE_D or inc != module.LN_INC:
            drifts.append(f'line {line + 2 + k}: CalcTier {row[0]} is {base} / {inc} in Methodology.md '
                          f'but {home.group(1)} holds BASE_D {module.BASE_D} / LN_INC {module.LN_INC}')
        m = STEP.fullmatch(row[3].strip())
        if not m or int(m.group(1)) != round((math.exp(module.LN_INC) - 1) * 100):
            drifts.append(f'line {line + 2 + k}: CalcTier {row[0]} step per tier reads {row[3]!r} in Methodology.md, '
                          f'{home.group(1)} gives ~{round((math.exp(module.LN_INC) - 1) * 100)}%')
    return drifts


def check_tables(blocks):
    """Every RemapDiff table against its named bins and the CalcTier table against the
    constants: the list of drifts (empty when every number matches)."""
    found, tiers, drifts = set(), None, []
    for i, block in enumerate(blocks):
        if block[0] == 'heading' and block[1] == 4:
            m = BINS_NAME.search(markdown.render([block]))
            if not m:
                continue
            name = m.group(1)
            nxt = blocks[i + 1] if i + 1 < len(blocks) else None
            if nxt is None or nxt[0] != 'table':
                raise MethodologyDrift(f'line {block[-1]}: the {name} heading is not followed by its table')
            drifts += _check_remap(name, nxt)
            found.add(name)
        elif block[0] == 'table' and block[1] == TIER_HEADER:
            tiers = block
    want = {n for module in MODULES.values() for n in dir(module) if n.endswith('_REMAP_BINS')}
    if found != want:
        raise MethodologyDrift(f'the tables cover {sorted(found)}; the formula modules have {sorted(want)}')
    if tiers is None:
        raise MethodologyDrift(f'no CalcTier table (header {TIER_HEADER})')
    return drifts + _check_tiers(tiers)


def plain(drift):
    return re.sub(r'^line \d+: ', '', drift)


# The blocks and the drifts; MarkdownError or MethodologyDrift, prefixed with
# the file name, when the file cannot be rendered or a table cannot be read.
def load(path=MD_PATH):
    path = pathlib.Path(path)
    try:
        blocks = markdown.parse(path.read_text(encoding='utf-8'))
    except markdown.MarkdownError as err:
        raise markdown.MarkdownError(f'{path.name}: {err}') from None
    try:
        drifts = check_tables(blocks)
    except MethodologyDrift as err:
        raise MethodologyDrift(f'{path.name}: {err}') from None
    return blocks, drifts


def main():
    try:
        _blocks, drifts = load()
    except (markdown.MarkdownError, MethodologyDrift) as err:
        print(err, file=sys.stderr)
        sys.exit(1)
    new = [d for d in drifts if plain(d) not in KNOWN_DRIFT]
    gone = [k for k in KNOWN_DRIFT if k not in {plain(d) for d in drifts}]
    for d in drifts:
        print(f'{MD_PATH.name}: {d}' + ('' if plain(d) in KNOWN_DRIFT else '  (new)'))
    for k in gone:
        print(f'{MD_PATH.name}: no longer drifts, drop it from KNOWN_DRIFT: {k}')
    groups = sum(1 for m in MODULES.values() for n in dir(m) if n.endswith('_REMAP_BINS'))
    if new or gone:
        sys.exit(1)
    print(f'{MD_PATH.name}: {groups} remap tables and the CalcTier table checked against '
          f'{", ".join(MODULES)}; {len(drifts)} known drift{"s" if len(drifts) != 1 else ""}')


if __name__ == '__main__':
    main()
