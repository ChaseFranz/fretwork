"""
DIFFICULTY - the per-entry difficulty block shared by render and the web viewer

One function per family (instruments.FAMILY): the five 5-fret keys through
fret_density and fret_formula, drums through drum_density and drum_formula,
vocals through vocal_density and vocal_formula, the same calls render.py and
analyze.py make, so the graph header and the spreadsheet agree. Every block
carries 'D' (for drums the 1x reading, which is what the site ranks by, with
'D_2x' beside it when the chart has a double-pedal reading), 'RemapDiff' and
'CalcTier', anchored to the song's Expert chart for the fret and drum
families and straight from D for vocals, which are Expert only - see
Methodology.md.
"""

from functions import drum_density, drum_formula, fret_density, fret_formula, instruments
from functions import vocal_density, vocal_formula

# The stream shape each family's entry carries under 'notes' (functions/cache.py).
FAMILY_KEYS = {
    'fret': ('time_ms', 'lanes'),
    'drums': ('hand_mask', 'kick_mask'),
    'vocals': ('time_ms', 'end_ms', 'pitch', 'is_placeholder', 'is_slide'),
}

# The meta keys the graph header prints: the title row (Name, Artist),
# plot.meta_header (Charter, Release, Official, the instrument's Difficulty) and
# plot.output_filename (Artist, Name). bundle.fingerprint hashes only these, so
# a meta key the PNG never shows (Genre, Year, Album) re-renders nothing. It
# mirrors upstream's functions/plot.py from here because that file is not the
# fork's to edit; tests/test_bundle.py checks the mirror against plot.py's
# source, and adding a printed key here means a full re-render.
HEADER_META_KEYS = ('Name', 'Artist', 'Charter', 'Release', 'Official', 'Difficulty')


def family(entry):
    return instruments.FAMILY[entry['instrument']]


# True when the entry's notes are the shape its family's metrics read; a
# stream of another shape (a cache built before the family was scored) is not.
def scorable(entry):
    notes = entry.get('notes')
    return isinstance(notes, dict) and all(k in notes for k in FAMILY_KEYS[family(entry)])


def _fret(entry):
    metrics = fret_density.calc_metrics(entry['notes'])
    if metrics is None:
        return None
    expert_notes = entry.get('expert_notes')
    expert_metrics = fret_density.calc_metrics(expert_notes) if expert_notes is not None else None
    anchor_remap, anchor_tier = fret_formula.anchor_remap_tier(expert_metrics, entry['instrument'])
    return {**fret_formula.calc_nvcov(metrics), 'RemapDiff': anchor_remap, 'CalcTier': anchor_tier}


def _drums(entry):
    metrics = drum_density.calc_drum_metrics(entry['notes'], roll_spans=entry.get('roll_spans'))
    if metrics is None or metrics.get('hand') is None or metrics.get('1x') is None:
        return None
    expert_notes = entry.get('expert_notes')
    expert_metrics = (drum_density.calc_drum_metrics(expert_notes, roll_spans=entry.get('expert_roll_spans'))
                      if expert_notes is not None else None)
    anchor_remap, anchor_tier = drum_formula.anchor_remap_tier(expert_metrics)
    one = drum_formula.calc_drum_d(metrics, '1x')
    out = {'H': one['H'], 'T': one['T'], 'K': one['K'], 'CoV': one['CoV'], 'STAM': one['STAM'], 'D': one['D'],
           'RemapDiff': anchor_remap, 'CalcTier': anchor_tier}
    if metrics.get('2x') is not None:
        out['D_2x'] = drum_formula.calc_drum_d(metrics, '2x')['D']
    return out


def _vocals(entry):
    metrics = vocal_density.calc_vocal_metrics(entry['notes'], entry.get('talkie'), percussion=entry.get('percussion'))
    if metrics is None:
        return None
    return vocal_formula.calc_vocal_d(metrics)


FAMILY_DIFFICULTY = {'fret': _fret, 'drums': _drums, 'vocals': _vocals}


# None when the entry has no usable notes; RemapDiff/CalcTier are None when the
# instrument has no Expert chart to anchor against.
def entry_difficulty(entry):
    if not scorable(entry):
        return None
    return FAMILY_DIFFICULTY[family(entry)](entry)
