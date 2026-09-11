"""
DIFFICULTY - the per-entry difficulty block shared by render and the web viewer

D/N/V/COV come from the entry's own level, while RemapDiff and CalcTier anchor
to the song's Expert chart - see Methodology.md.
"""

from functions import density, formula

SCORED_KEYS = ('time_ms', 'lanes')


# True for the five-fret stream shape every metric understands; a drums entry
# carries {'hand_mask', 'kick_mask'} and is not scored yet.
def scorable(notes):
    return isinstance(notes, dict) and all(k in notes for k in SCORED_KEYS)


# None when the entry has no usable notes or is not scored yet; RemapDiff/CalcTier
# are None when the instrument has no Expert chart to anchor against.
def entry_difficulty(entry):
    if not scorable(entry['notes']):
        return None
    metrics = density.calc_metrics(entry['notes'])
    if metrics is None:
        return None

    expert_notes = entry.get('expert_notes')
    expert_metrics = density.calc_metrics(expert_notes) if expert_notes is not None else None
    anchor_remap, anchor_tier = formula.anchor_remap_tier(expert_metrics, entry['instrument'])

    return {
        **formula.calc_nvcov(metrics),
        'RemapDiff': anchor_remap,
        'CalcTier': anchor_tier,
    }
