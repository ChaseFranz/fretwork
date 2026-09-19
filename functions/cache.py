"""
CACHE - The cache save/load pieces and retrieval code generation
BUILD writes a cache of all the song data needed from the search_path in config.py
ANALYZE and RENDER can read from caches to generate metrics/visuals

Shape:
    {
        'generated_at': str,
        'search_path':  str,
        'codes':        {code: song_path},   # code = 8-digit song hash + level letter + instrument letter
        'songs': {
            song_path: {
                'song_path':     str,
                'song_key':      str | None,   # 12 hex digits over every 5-fret stream; same charts, same key, whatever folder
                'meta':          {...},   # Name, Artist, Charter, Release, Official, Genre, Year (int, -1 sentinel),
                                          # Album, and the per-instrument Difficulty dict (Expert-referenced)
                'source_format': 'chart' | 'mid',
                'chart_md5':     str,   # MD5 of the raw notes file that produced source_format; never in meta
                'codes':         {instrument_key: {level_key: code, ...}, ...},
                'instruments': {
                    instrument_key: {
                        level_key: {
                            'notes': {
                                'time_ms': ndarray,   # sorted
                                'lanes':   ndarray uint8,  # bitmask, bit N = lane N
                            },
                            'notes_hash': str,   # 12 hex digits: sha1(stream_bytes(notes))[:12]; same notes, same hash
                        },
                        ...  # only levels actually charted for this instrument
                    },
                    ...  # only instruments actually present for this song
                    # 'drums' entries have two different streams (hands and kick)
                    #     'notes': {
                    #         'hand_mask': {'time_ms': ndarray, 'lanes': ndarray uint8},
                    #         'kick_mask': {'time_ms': ndarray, 'lanes': ndarray uint8},
                    #     }
                    # 'vocals' entries are Expert only, with three streams side by side at the level
                    #     'notes': {                           # sung, pitched, non-talkie
                    #         'time_ms':        ndarray,       # sorted
                    #         'end_ms':         ndarray,
                    #         'pitch':          ndarray uint8, # midi note 36-84
                    #         'is_placeholder': ndarray bool,  # '+$' hold filler, not a new syllable
                    #         'is_slide':       ndarray bool,  # '+' pitch glide, not a new syllable
                    #     },
                    #     'talkie': { # rap/spoken
                    #         'time_ms': ndarray,
                    #         'end_ms':  ndarray, # NaN when no length is authored (GH lyric-only)
                    #     },
                    #     'percussion': {'time_ms': ndarray, 'end_ms': ndarray},   # note 96 taps, render only
                },
                'roll_spans': {'drums': {level_key: [(start_ms, end_ms, 'single'|'double'), ...], ...}},
                # roll lanes available per level
            },
            ...
        },
    }

Every level charted for an instrument is cached (whatever combination of E/M/H/X)

Caches should be managed based on timestamp / generation time & date

When generated with errors, a CSV is produced alongside the cache with details

Retrieval codes are per the 8-digit song hash + a level (E/M/H/X) + instrument (G/C/R/B/K/D/V)
'04821993' + Expert + Bass -> '04821993XB' 
Render uses the code to define the instrument/level

Drums requires roll spans to calculate correctly so those are paired to the code as well

Vocals only exist at Expert, talkie/percussion streams are carried with the code for render
"""

import hashlib
import pickle

from functions import instruments

# Hash-derived retrieval codes digit length (pre level/instrument suffix)
CODE_LEN = 8
SUFFIX_LEN = 2  # level letter + instrument letter

# Retrieval codes
def _hash_code(song_path, digits):
    digest = hashlib.sha1(song_path.encode('utf-8')).hexdigest()
    return int(digest, 16) % (10 ** digits)

# assigns the numeric 8-digit code per song
# A song's identity that survives a re-download: SHA-1 over every 5-fret
# stream, sorted by (instrument, level), as the bytes of the note arrays. Two
# folders holding the same charts share a key; a pack moved to a new folder
# keeps its keys while every path-hashed code changes. None when the song has
# no stream in SONG_KEY_INSTRUMENTS. A parser change moves every key.
# The bytes a chart's notes hash over: the two arrays back to back for a flat
# stream (equal length and fixed widths, so no separator is needed), and the
# two labelled streams for a drums pair. bundle.fingerprint keeps its own
# two-element form of the same bytes; routing it through here would change
# every stored fingerprint and re-render every graph.
# A vocals chart is three streams side by side (sung, talkie, percussion); the
# sung stream's arrays, in this order, then the other two, so two talkie-only
# charts with different lyrics do not hash the same.
VOCAL_KEYS = ('time_ms', 'end_ms', 'pitch', 'is_placeholder', 'is_slide')
SIDE_KEYS = ('time_ms', 'end_ms')


def stream_bytes(notes, *sides):
    if 'lanes' in notes:
        return notes['time_ms'].tobytes() + notes['lanes'].tobytes()
    if 'hand_mask' in notes:
        return b'hand' + stream_bytes(notes['hand_mask']) + b'kick' + stream_bytes(notes['kick_mask'])
    out = b'vox' + b''.join(notes[k].tobytes() for k in VOCAL_KEYS)
    for side in sides:
        out += (b'side' + b''.join(side[k].tobytes() for k in SIDE_KEYS)) if side else b'none'
    return out


# A chart's identity: the same notes in another folder hash the same, whatever
# the song is called. Per (song, instrument, level), where song_key is per song.
# A vocals chart passes its talkie and percussion streams as `sides`.
def notes_hash(notes, *sides):
    return hashlib.sha1(stream_bytes(notes, *sides)).hexdigest()[:12]


def song_key(song_instruments):
    parts = sorted(
        (inst, level, notes['notes']['time_ms'].tobytes(), notes['notes']['lanes'].tobytes())
        for inst in instruments.SONG_KEY_INSTRUMENTS
        for level, notes in song_instruments.get(inst, {}).items())
    if not parts:
        return None
    h = hashlib.sha1()
    for inst, level, times, lanes in parts:
        h.update(inst.encode()); h.update(b'\0'); h.update(level.encode()); h.update(b'\0')
        h.update(times); h.update(lanes)
    return h.hexdigest()[:12]


def assign_song_codes(song_paths, digits=None):
    digits = digits or CODE_LEN
    span = 10 ** digits

    song_paths = list(song_paths)
    if len(song_paths) > span // 2:
        raise ValueError(
            f"{len(song_paths)} songs is too many for {digits}-digit codes; "
            f"raise cache.CODE_LEN"
        )

    taken = {}
    for song_path in sorted(song_paths):
        code_int = _hash_code(song_path, digits)
        while code_int in taken:
            code_int = (code_int + 1) % span
        taken[code_int] = song_path

    codes = {path: str(code).zfill(digits) for code, path in taken.items()}

    assert len(set(codes.values())) == len(codes), "code collision survived probing"
    return codes


# Builds the full song+instrument+level -> code map for every
# (song_path, instrument_key, level_key) triple present
def assign_codes(song_instrument_level_triples, digits=None):
    triples = list(song_instrument_level_triples)
    song_paths = sorted({song_path for song_path, _, _ in triples})
    song_codes = assign_song_codes(song_paths, digits)

    codes = {}
    for song_path, instrument_key, level_key in triples:
        suffix = (
            instruments.LEVEL_CODE_SUFFIX[level_key]
            + instruments.CODE_SUFFIX[instrument_key]
        )
        codes[(song_path, instrument_key, level_key)] = song_codes[song_path] + suffix

    assert len(set(codes.values())) == len(codes), "song+instrument+level code collision"
    return codes

# Persistence
def save(cache, cache_path):
    with open(cache_path, 'wb') as f:
        pickle.dump(cache, f, protocol=pickle.HIGHEST_PROTOCOL)
    return cache_path

def load(cache_path):
    with open(cache_path, 'rb') as f:
        return pickle.load(f)

# Lookup retrieval codes - str or int w/ zero padding
# '421XB' and '00000421XB' both work, Last 2 chars are level & instrument
def entries_by_code(cache, codes):
    entries = []
    missing = []

    for raw in codes:
        raw = str(raw).strip()

        if len(raw) < SUFFIX_LEN + 1 or not raw[-1].isalpha() or not raw[-2].isalpha():
            missing.append(raw)
            continue

        instrument_letter = raw[-1].upper()
        level_letter = raw[-2].upper()

        if (instrument_letter not in instruments.SUFFIX_TO_INSTRUMENT
                or level_letter not in instruments.SUFFIX_TO_LEVEL):
            missing.append(raw)
            continue

        digits_part = raw[:-SUFFIX_LEN].zfill(CODE_LEN)
        full_code = digits_part + level_letter + instrument_letter

        song_path = cache['codes'].get(full_code)
        if song_path is None:
            missing.append(raw)
            continue

        song = cache['songs'].get(song_path)
        instrument_key = instruments.SUFFIX_TO_INSTRUMENT[instrument_letter]
        level_key = instruments.SUFFIX_TO_LEVEL[level_letter]

        instrument_levels = (song or {}).get('instruments', {}).get(instrument_key, {})
        inst_entry = instrument_levels.get(level_key)
        if inst_entry is None:
            missing.append(raw)
            continue

        # Expert's notes, alongside the requested level 
        # RemapDiff/CalcTier are anchored to Expert row's data
        expert_notes = instrument_levels.get('expert', {}).get('notes')

        # Roll spans - drums only to calc metrics correctly
        instrument_roll_spans = song.get('roll_spans', {}).get(instrument_key, {})
        roll_spans = instrument_roll_spans.get(level_key)
        expert_roll_spans = instrument_roll_spans.get('expert')

        entries.append({
            **inst_entry,
            'code': full_code,
            'song_path': song_path,
            'instrument': instrument_key,
            'level': level_key,
            'meta': song['meta'],
            'source_format': song['source_format'],
            'expert_notes': expert_notes,
            'roll_spans': roll_spans,
            'expert_roll_spans': expert_roll_spans,
        })

    return entries, missing
