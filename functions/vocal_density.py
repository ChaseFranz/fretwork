"""
VOCAL DENSITY - Density metrics, computed from the cached vocal streams

SPS = Syllables Per Second
    Every new articulation counts 1: sung notes that aren't slides (+) placeholders (+$) or talkies (*/^/#)
    This logic also defines NoteCount - so aSPS = NoteCount / Duration, similar to NPS

PPS = Pitch-movement Per Second
    Each sung note (including slides and placeholders) is compared to the previous pitch
    Games score pitch in any octave, so the interval is folded (0-6) and compressed by a square root like drum travel
        k = |dp| mod 12,  d = min(k, 12 - k),  m = d ** 0.5
    repeat note 0 / half-step 1 / whole-step ~1.41 / octave 0
    A song's first note has nothing to compare against, so it scores 0

Active windows (median/std gating) = any sung note or talkie overlapping the window

Talkie length
    Authored talkie lengths are ignored so RB and GH talkies are treated the same:
        end = time + min(gap to next onset, TALKIE_FILL_MS)
    TALKIE_FILL_MS is the pooled median authored talkie length across RB officials
    Clipping to the next onset means talkies never overlap anything

Span = highest minus lowest sung pitch (semitones, unfolded), 0 for talkie-only charts
    Even with octave-free scoring most people still try to hit the notes as recorded, adding difficulty

Percussion is render/duration gate only

Charts with zero syllables return None

WINDOW_MS/STEP_MS and the active-window median/std helpers are shared with fret_density
Grid start is t=0 and runs until the latest endpoint across all three streams
"""

import numpy as np

from functions import fret_density

WINDOW_MS = fret_density.WINDOW_MS
STEP_MS = fret_density.STEP_MS

# square-root compression
PITCH_GAMMA = 0.5

# fixed talkie length, clipped to the next onset
TALKIE_FILL_MS = 133.0

# minimum interval length so a zero-length event still marks its window active
MIN_EVENT_MS = 1e-3


def _sorted_stream(stream, keys):
    times = np.asarray(stream['time_ms'], dtype=np.float64)
    arrays = {k: np.asarray(stream[k]) for k in keys}
    if times.size > 1 and not np.all(np.diff(times) >= 0):
        order = np.argsort(times, kind='stable')
        times = times[order]
        arrays = {k: v[order] for k, v in arrays.items()}
    return times, arrays


# PPS source - folded/compressed interval from the previous pitch
def pitch_move(pitches, gamma=PITCH_GAMMA):
    p = np.asarray(pitches, dtype=np.int64)
    out = np.zeros(p.size, dtype=np.float64)
    if p.size > 1:
        k = np.abs(np.diff(p)) % 12
        d = np.minimum(k, 12 - k).astype(np.float64)
        out[1:] = d ** gamma
    return out


# talkie end = onset + min(gap to next onset, fill)
def talkie_ends(talkie_times, sung_times, fill_ms=TALKIE_FILL_MS):
    if talkie_times.size == 0:
        return np.empty(0, dtype=np.float64)
    onsets = np.unique(np.concatenate([sung_times, talkie_times]))
    j = np.searchsorted(onsets, talkie_times, side='right')
    gap = np.full(talkie_times.size, np.inf)
    has_next = j < onsets.size
    gap[has_next] = onsets[j[has_next]] - talkie_times[has_next]
    return talkie_times + np.minimum(gap, fill_ms)


# Per grid window where any start/end overlaps the window
def occupancy_gate(starts, ends, grid, window_ms=WINDOW_MS):
    active = np.zeros(grid.size, dtype=bool)
    if starts.size == 0:
        return active
    order = np.argsort(starts, kind='stable')
    s = starts[order]
    e = np.maximum(ends[order], s + MIN_EVENT_MS)
    run_max_end = np.maximum.accumulate(e)

    # intervals starting before the window closes
    idx = np.searchsorted(s, grid + window_ms, side='left')
    has = idx > 0
    active[has] = run_max_end[idx[has] - 1] > grid[has]
    return active


# Windowing pass across SPS/PPS + the occupancy gate
# zero activity windows are included
#     Returns:
#        {
#            'time_ms':          ndarray,  # uniform grid, starts at 0
#            'raw_sps_samples':  ndarray,  # syllables per window
#            'raw_pps_samples':  ndarray,  # pitch movement per window
#            'active':           ndarray,  # bool, any sung/talkie time in window
#            'syllable_times':   ndarray,  # sorted syllable onsets (sung + talkie)
#            'move':             ndarray,  # per sung note movement (not windowed)
#            'sung_times':       ndarray,  # sorted sung note onsets
#            'talkie_end_ms':    ndarray,  # filled talkie ends
#            'dur_ms':           float,    # latest end across sung/talkie/percussion
#            'span':             float,    # highest - lowest sung pitch, semitones
#        }
def window_arrays(notes, talkie, percussion=None, window_ms=WINDOW_MS, step_ms=STEP_MS):
    sung_t, sung = _sorted_stream(notes, ('end_ms', 'pitch', 'is_placeholder', 'is_slide'))
    talk_t = np.sort(np.asarray(talkie['time_ms'], dtype=np.float64))

    new_syllable = ~(sung['is_slide'].astype(bool) | sung['is_placeholder'].astype(bool))
    syllable_times = np.sort(np.concatenate([sung_t[new_syllable], talk_t]))
    if syllable_times.size == 0:
        return None

    sung_end = sung['end_ms'].astype(np.float64)
    talk_end = talkie_ends(talk_t, sung_t)
    move = pitch_move(sung['pitch'])
    sung['pitch'] = sung['pitch'].astype(np.int64)

    perc_end = np.asarray((percussion or {}).get('end_ms', []), dtype=np.float64)
    dur_ms = float(max(
        (arr.max() for arr in (sung_end, talk_end, perc_end) if arr.size),
        default=0.0,
    ))

    n_samples = int(dur_ms // step_ms) + 1
    grid = np.arange(n_samples, dtype=np.float64) * step_ms

    left = np.searchsorted(syllable_times, grid, side='left')
    right = np.searchsorted(syllable_times, grid + window_ms, side='left')
    raw_sps = (right - left).astype(np.float64)

    prefix = np.concatenate(([0.0], np.cumsum(move)))
    left = np.searchsorted(sung_t, grid, side='left')
    right = np.searchsorted(sung_t, grid + window_ms, side='left')
    raw_pps = prefix[right] - prefix[left]

    active = occupancy_gate(
        np.concatenate([sung_t, talk_t]),
        np.concatenate([sung_end, talk_end]),
        grid, window_ms,
    )

    return {
        'time_ms': grid,
        'raw_sps_samples': raw_sps,
        'raw_pps_samples': raw_pps,
        'active': active,
        'syllable_times': syllable_times,
        'move': move,
        'sung_times': sung_t,
        'talkie_end_ms': talk_end,
        'dur_ms': dur_ms,
        'span': float(sung['pitch'].max() - sung['pitch'].min()) if sung_t.size else 0.0,
    }


# provides SPS & PPS metrics to calculate D
def calc_vocal_metrics(notes, talkie, percussion=None, window_ms=WINDOW_MS, step_ms=STEP_MS):
    windows = window_arrays(notes, talkie, percussion, window_ms, step_ms)
    if windows is None:
        return None

    dur_s = windows['dur_ms'] / 1000.0
    window_s = window_ms / 1000.0
    active = windows['active']   # occupancy gate used for both SPS & PPS

    # SPS
    note_count = int(windows['syllable_times'].size)
    sps_window_values = windows['raw_sps_samples'] / window_s

    # PPS
    pps_window_values = windows['raw_pps_samples'] / window_s

    return {
        'NoteCount': note_count,
        'DurationS': dur_s,
        'Span': windows['span'],
        'aSPS': note_count / dur_s if dur_s > 0 else 0.0,
        'pSPS': float(sps_window_values.max()),
        'stdSPS': fret_density.active_std(sps_window_values, active),   # gated by occupancy
        'medSPS': fret_density.active_median(sps_window_values, active),  # gated by occupancy
        'aPPS': float(windows['move'].sum()) / dur_s if dur_s > 0 else 0.0,
        'pPPS': float(pps_window_values.max()),
        'stdPPS': fret_density.active_std(pps_window_values, active),   # gated by occupancy
        'medPPS': fret_density.active_median(pps_window_values, active),  # gated by occupancy
    }
