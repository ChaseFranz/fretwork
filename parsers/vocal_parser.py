"""
VOCAL_PARSER - Extracts PART VOCALS into note/talkie/percussion pieces for the cache

_extract_vocal_track(track, to_ms_array) returns
    {'expert': {'notes': {...}, 'talkie': {...}, 'percussion': {...}, 'phrase_marks': {...}}}
    or None if the track has no pitch, talkie, or percussion content

All other instruments use EMHX levels, so vocals is treated as Expert for downstream handling

THREE SEPARATE STREAMS:
    'notes' - sung, pitched, non-talkie (keeps duration for holds/breath calcs)
    'talkie' - every rap/talkie/spoken hit, 2 flavors:
                - has_note=True:  '#'/'^'/'*' suffix on a normally-pitched note
                  RB style rap/scream
                - has_note=False: a lyric event with no note 
                  GH-style rap/scream
    'percussion' - standardized taps, onset only

phrase_marks (note 105) for calibration data only (may be dropped later)
kept for comparing against the computed rest-gap-based BREATH_WINDOW_MS derivation once real data exists
"""

import numpy as np

PITCH_LOW, PITCH_HIGH = 36, 84
PERC_PLAYABLE = 96
PHRASE_MARK = 105  # diagnostic/calibration only

# Structural notes discarded: 0/1 range-shift, 106 versus tag, 116 sp, 97 non-playable perc
DISCARD_NOTES = frozenset({0, 1, 97, 106, 116})

TALKIE_SUFFIXES = ('#', '^', '*')
PLACEHOLDER_LYRIC = '+$'
CONT_LYRIC = '+'

# Used to cut off notes that are left on at track end (defensive)
TRACK_END_CLOSE_MS = 500.0


def _extract_vocal_track(track, to_ms_array):
    # Scan mido messages
    note_on_events = []
    note_off_events = []
    lyric_events = []
    end_tick = 0

    abs_tick = 0
    for msg in track:
        abs_tick += msg.time
        end_tick = abs_tick

        if msg.type == 'note_on' and msg.velocity > 0:
            note_on_events.append((abs_tick, msg.note))
        elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
            note_off_events.append((abs_tick, msg.note))
        elif msg.type == 'lyrics':
            lyric_events.append((abs_tick, msg.text))
        # text/animation events ([idle]/[intense]/etc.) ignored

    # note/phrase on/off pairs
    open_by_note = {}
    for tick, note in note_on_events:
        if note in DISCARD_NOTES:
            continue
        open_by_note.setdefault(note, []).append(tick)

    pitched_pairs = []
    perc_pairs = []
    phrase_pairs = []

    for tick, note in sorted(note_off_events, key=lambda e: e[0]):
        if note in DISCARD_NOTES:
            continue
        starts = open_by_note.get(note)
        if not starts:
            continue
        start_tick = starts.pop(0)

        if PITCH_LOW <= note <= PITCH_HIGH:
            pitched_pairs.append([start_tick, tick, note])
        elif note == PERC_PLAYABLE:
            perc_pairs.append([start_tick, tick])
        elif note == PHRASE_MARK:
            phrase_pairs.append([start_tick, tick])
        # note values with no category ignored

    # resolving end danglers (defensive)
    dangling = [
        (note, start_tick)
        for note, starts in open_by_note.items()
        for start_tick in starts
    ]
    if dangling:
        start_ms_all = to_ms_array([start_tick for _note, start_tick in dangling])
        end_tick_ms = to_ms_array([end_tick])[0]
        for (note, start_tick), start_ms in zip(dangling, start_ms_all):
            if not (PITCH_LOW <= note <= PITCH_HIGH
                    or note == PERC_PLAYABLE
                    or note == PHRASE_MARK):
                continue

            gap_ms = end_tick_ms - start_ms
            close_it = gap_ms <= TRACK_END_CLOSE_MS
            if not close_it:
                continue
            if PITCH_LOW <= note <= PITCH_HIGH:
                pitched_pairs.append([start_tick, end_tick, note])
            elif note == PERC_PLAYABLE:
                perc_pairs.append([start_tick, end_tick])
            elif note == PHRASE_MARK:  # PHRASE_MARKS block
                phrase_pairs.append([start_tick, end_tick])

    pitched_pairs.sort(key=lambda p: p[0])
    perc_pairs.sort(key=lambda p: p[0])
    phrase_pairs.sort(key=lambda p: p[0])  # PHRASE_MARKS block

    if not pitched_pairs and not perc_pairs:
        return None

    # Lyric resolution
    # - split pitched_pairs into sung vs. talkie, 
    # - tag placeholders
    # - create talkie hits from lyric events w/o notes
    lyric_by_tick = {}
    for tick, text in sorted(lyric_events, key=lambda e: e[0]):
        lyric_by_tick.setdefault(tick, text)

    sung_pairs = []
    talkie_from_notes = []
    for start_tick, end_tick_pair, note in pitched_pairs:
        text = lyric_by_tick.get(start_tick)
        if text is None:
            sung_pairs.append([start_tick, end_tick_pair, note, False])
            continue
        if text.endswith(TALKIE_SUFFIXES):
            talkie_from_notes.append(start_tick)
        else:
            sung_pairs.append([start_tick, end_tick_pair, note, text == PLACEHOLDER_LYRIC])

    # GH-style talkies
    consumed_ticks = {start_tick for start_tick, _e, _n in pitched_pairs}
    talkie_lyric_only = [
        tick for tick, text in lyric_by_tick.items()
        if tick not in consumed_ticks and text not in (CONT_LYRIC, PLACEHOLDER_LYRIC)
    ]

    sung_pairs.sort(key=lambda p: p[0])

    # Final arrays
    time_ms = to_ms_array([p[0] for p in sung_pairs])
    end_ms = to_ms_array([p[1] for p in sung_pairs])
    pitch = np.array([p[2] for p in sung_pairs], dtype=np.uint8)
    is_placeholder = np.array([p[3] for p in sung_pairs], dtype=bool)

    talkie_ticks = sorted(
        [(t, True) for t in talkie_from_notes] + [(t, False) for t in talkie_lyric_only]
    )
    talkie_time_ms = to_ms_array([t for t, _has_note in talkie_ticks])
    talkie_has_note = np.array([h for _t, h in talkie_ticks], dtype=bool)

    perc_time_ms = to_ms_array([p[0] for p in perc_pairs])
    perc_end_ms = to_ms_array([p[1] for p in perc_pairs])

    # PHRASE_MARKS block
    phrase_time_ms = to_ms_array([p[0] for p in phrase_pairs])
    phrase_end_ms = to_ms_array([p[1] for p in phrase_pairs])

    return {
        'expert': {
            'notes': {
                'time_ms': time_ms,
                'end_ms': end_ms,
                'pitch': pitch,
                'is_placeholder': is_placeholder,
            },
            'talkie': {
                'time_ms': talkie_time_ms,
                'has_note': talkie_has_note,
            },
            'percussion': {
                'time_ms': perc_time_ms,
                'end_ms': perc_end_ms,
            },
            # Diagnostic/calibration only
            'phrase_marks': {
                'time_ms': phrase_time_ms,
                'end_ms': phrase_end_ms,
            },
        }
    }
