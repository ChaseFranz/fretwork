"""
FIXTURE - a small synthetic song library, generated the same way every time.

Sixteen song folders across three packs, nothing real in any of them: every
title, artist and charter is invented and every note stream comes from a seeded
random generator. Fourteen carry a chart the parsers accept (ten notes.chart
written as text, four notes.mid written with mido), one has only a song.ini,
and one has a song.ini beside a truncated notes.mid so the errors path runs.
Two songs carry drums (one per format) and two of the .mid songs carry vocals
(a sung line with slides, talkies and percussion taps), so every family the
site scores (instruments.FAMILY) is in the fixture.
Three of the charts repeat notes on purpose, for the Copies column: B5 is A1's
Expert guitar in another pack under another title (a cross-pack pair), A2's
Hard equals its Expert, and C4's Rhythm equals its Lead (neither is a copy).
The table in SONGS is the interface: test_fixture.py pins its totals and
pipeline_test.py derives every expected count from it.

    python tests/fixture.py DEST        # write the library and print the totals

Nothing here is committed except this generator: the library is written into a
temporary directory by the tests. The same seed writes byte-identical files.
"""

import dataclasses
import pathlib
import random
import sys

import mido

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from functions import instruments  # noqa: E402

SEED = 20260911
RESOLUTION = 192          # ticks per beat, both formats
GRID = 48                 # a 16th note at that resolution
NOTE_OFF_TICKS = 24
LEVEL_OF = {'E': 'easy', 'M': 'medium', 'H': 'hard', 'X': 'expert'}
STRIDE = {'expert': 1, 'hard': 2, 'medium': 3, 'easy': 4}   # lower levels are strided subsets of Expert
BROKEN = 'broken'         # a song whose notes.mid is truncated inside its guitar track


@dataclasses.dataclass(frozen=True)
class Song:
    pack: str
    folder: str
    fmt: str                     # 'chart' | 'mid' | 'both' (chart wins) | 'none' | BROKEN
    parts: dict                  # instrument key -> level letters, e.g. {'guitar': 'EMHX', 'bass': 'X'}
    official: bool
    release: str
    ini: dict                    # extra song.ini keys beyond the generated ones
    bpm: int
    notes: int                   # Expert note count target
    seconds: int
    encoding: str = 'utf-8'      # 'utf-8' | 'utf-8-sig-crlf' | 'cp1252'
    enhanced_opens: bool = False
    copy_of: str = None          # folder whose Expert guitar this song repeats note for note
    flat_levels: bool = False    # every level is the Expert stream (Hard = Expert)
    mirror_lead: tuple = ()      # instruments whose streams are the guitar's (Lead = Rhythm)

    @property
    def charted(self):
        return self.fmt in ('chart', 'mid', 'both')

    @property
    def source_format(self):
        return 'chart' if self.fmt in ('chart', 'both') else ('mid' if self.fmt == 'mid' else None)

    def levels(self, instrument):
        return [LEVEL_OF[c] for c in self.parts.get(instrument, '')]


PACKS = {
    'Fixture Pack A': ('gh3', 'Guitar Hero III: Legends Of Rock', True),
    'Fixture Pack B': ('rb2', 'Rock Band 2', True),
    'Fixture Pack C': ('fixturepack', 'Custom', False),
}

# Values for a fake link registry (section 13): an Enchor md5 and a leaderboard
# songHash, each made distinct per song by its last characters.
LINKS_FAKE = {'md5': '0123456789abcdef0123456789abcdef', 'songHash': 'A' * 43}


def fake_links(index):
    tail = f'{index:02d}'
    return {'md5': LINKS_FAKE['md5'][:-2] + tail, 'songHash': LINKS_FAKE['songHash'][:-2] + tail}


# The table. Rows on the site = every level of every instrument.
SONGS = [
    Song('Fixture Pack A', 'A1 - Grid Runner', 'chart', {'guitar': 'EMHX', 'bass': 'X'}, True, PACKS['Fixture Pack A'][1],
         {'name': 'Grid Runner', 'artist': 'The Tessellates', 'charter': 'Fixture', 'diff_guitar': '4', 'diff_bass': '3'},
         bpm=140, notes=600, seconds=120),
    Song('Fixture Pack A', 'A2 - Two Tier', 'chart', {'guitar': 'HX'}, True, PACKS['Fixture Pack A'][1],
         {'name': '__SHOUT__ Two Tier', 'artist': 'Placeholder Pattern', 'charter': 'Fixture', 'year': 'Unknown Year'},
         bpm=120, notes=300, seconds=90, flat_levels=True),
    Song('Fixture Pack A', 'A3 - Midi Mirror', 'mid', {'guitar': 'EMHX', 'bass': 'HX', 'vocals': 'X'}, True, PACKS['Fixture Pack A'][1],
         {'name': 'Midi Mirror', 'artist': 'Reflected Signal', 'charter': 'Fixture', 'diff_guitar': '6', 'year': '2007 (re-issue)'},
         bpm=160, notes=800, seconds=140, encoding='utf-8-sig-crlf'),
    Song('Fixture Pack A', 'A4 - Keys Only Once', 'chart', {'guitar': 'X', 'keys': 'X'}, True, PACKS['Fixture Pack A'][1],
         {'name': 'Keys Only Once', 'artist': 'Ivory Latch', 'charter': 'Fixture', 'year': 'Vol. 2 (2001)', 'album': 'Latch, Vol. 2'},
         bpm=100, notes=200, seconds=75),
    Song('Fixture Pack B', 'B1 - Half Medium', 'chart', {'guitar': 'MX', 'bass': 'X'}, True, PACKS['Fixture Pack B'][1],
         {'name': 'Half Medium', 'artist': 'Quarter Rest', 'charter': 'Fixture Two', 'diff_guitar': '-1', 'genre': '<color=#ff0000>Rock</color>'},
         bpm=130, notes=450, seconds=100),
    Song('Fixture Pack B', 'B2 - Drum Mid', 'mid', {'guitar': 'EMHX', 'drums': 'X', 'vocals': 'X'}, True, PACKS['Fixture Pack B'][1],
         {'name': 'Drum Mid', 'artist': 'Kick Pattern', 'charter': 'Fixture Two'},
         bpm=150, notes=500, seconds=110),
    Song('Fixture Pack B', 'B3 - Co-op Lead', 'chart', {'guitar': 'EX', 'coop': 'X'}, True, PACKS['Fixture Pack B'][1],
         {'name': 'Co-op Lead', 'artist': 'Two Necks', 'charter': 'Fixture Two'},
         bpm=110, notes=350, seconds=95),
    Song('Fixture Pack B', 'B4 - Ini Only', 'none', {}, True, PACKS['Fixture Pack B'][1],
         {'name': 'Ini Only', 'artist': 'No Notes', 'charter': 'Fixture Two'},
         bpm=120, notes=0, seconds=60),
    # A1's Expert guitar again: same bpm, length and target, no bass, another title
    Song('Fixture Pack B', 'B5 - Grid Runner (Live)', 'chart', {'guitar': 'X'}, True, PACKS['Fixture Pack B'][1],
         {'name': 'Grid Runner (Live)', 'artist': 'The Tessellates', 'charter': 'Fixture Two'},
         bpm=140, notes=600, seconds=120, copy_of='A1 - Grid Runner'),
    Song('Fixture Pack C', 'C1 - Legacy Bass', 'chart', {'guitar': 'MHX', 'bass': 'X', 'drums': 'X'}, False, 'Custom',
         {'name': 'Legacy Bass', 'artist': 'Old Section', 'charter': 'Custom Charter'},
         bpm=170, notes=700, seconds=130),
    Song('Fixture Pack C', 'C2 - Mid Pair', 'both', {'guitar': 'X', 'bass': 'X'}, False, 'Custom',
         {'name': 'Mid Pair', 'artist': 'Two Files', 'charter': 'Custom Charter'},
         bpm=125, notes=400, seconds=105),
    Song('Fixture Pack C', 'C3 - Hard Without Expert', 'chart', {'guitar': 'H'}, False, 'Custom',
         {'name': 'Hard Without Expert', 'artist': 'No Anchor', 'charter': 'Custom Charter'},
         bpm=115, notes=250, seconds=80),
    Song('Fixture Pack C', 'C4 - Less Than More', 'chart', {'guitar': 'X', 'rhythm': 'X', 'bass': 'X'}, False, 'Custom',
         {'name': '<b>Less</b> < More', 'artist': 'René Escapé', 'charter': 'Custom Charter',
          'loading_phrase': '100% = one hundred percent'},
         bpm=135, notes=550, seconds=115, encoding='cp1252', mirror_lead=('rhythm',)),
    Song('Fixture Pack C', 'C5 - Every Level', 'chart', {'guitar': 'EMHX', 'bass': 'EMHX'}, False, 'Custom',
         {'name': 'Every Level', 'artist': 'Full Ladder', 'charter': 'Custom Charter', 'diff_guitar': '2'},
         bpm=180, notes=900, seconds=150),
    Song('Fixture Pack C', 'C6 - Enhanced Opens', 'mid', {'guitar': 'EMHX'}, False, 'Custom',
         {'name': 'Enhanced Opens', 'artist': 'Low String', 'charter': 'Custom Charter'},
         bpm=105, notes=320, seconds=85, enhanced_opens=True),
    Song('Fixture Pack C', 'C7 - Broken Mid', BROKEN, {'guitar': 'X'}, False, 'Custom',
         {'name': 'Broken Mid', 'artist': 'Cut Short', 'charter': 'Custom Charter'},
         bpm=120, notes=300, seconds=90),
]


# --- what the table implies ------------------------------------------------------------

@dataclasses.dataclass
class Library:
    root: pathlib.Path
    songs: list

    @property
    def ini_count(self):
        return len(self.songs)

    @property
    def charted(self):
        return [s for s in self.songs if s.charted]

    @property
    def unusable(self):
        return [s for s in self.songs if not s.charted]

    @property
    def errors(self):
        return [s for s in self.songs if s.fmt == BROKEN]

    # every (song, instrument, level) the cache holds, drums included
    @property
    def codes(self):
        return sum(len(s.levels(i)) for s in self.charted for i in s.parts)

    @property
    def rows_by_sheet(self):
        out = {}
        for sheet, keys in instruments.SHEET_GROUPS.items():
            n = sum(len(s.levels(i)) for s in self.charted for i in s.parts if i in keys)
            if n:
                out[sheet] = n
        return out

    @property
    def official_rows(self):
        return sum(len(s.levels(i)) for s in self.charted if s.official for i in s.parts)

    # the diff_* cell backup_data writes per song and tag: the ini value ('-1' when
    # the tag is absent) for an instrument the song has a stream for, '' otherwise
    @property
    def backup_rows(self):
        rows = {}
        for s in self.charted:
            row = {}
            for key, tag in instruments.DIFF_TAGS.items():
                row[tag] = s.ini.get(tag, '-1') if key in s.parts else ''
            rows[str(self.root / s.pack / s.folder)] = row
        return rows


# --- note streams ----------------------------------------------------------------------

# Expert as a random walk over a 16th-note grid: singles mostly, some two- and
# three-note chords, no two notes on one tick. Lower levels take every Nth note.
def expert_ticks(rng, song):
    beats = song.seconds * song.bpm / 60
    slots = int(beats * RESOLUTION / GRID)
    count = min(song.notes, slots)
    picked = sorted(rng.sample(range(slots), count))
    out = []
    for slot in picked:
        r = rng.random()
        lanes = [rng.randrange(5)]
        if r > 0.75:
            lanes.append((lanes[0] + rng.choice([1, 2])) % 5)
        if r > 0.95:
            lanes.append((lanes[0] + 3) % 5)
        out.append((slot * GRID, sorted(set(lanes))))
    return out


def level_ticks(expert, level, flat=False):
    return expert[::1 if flat else STRIDE[level]]


def part_streams(rng, song, instrument, expert=None):
    if expert is None:
        expert = expert_ticks(rng, song)
        if instrument != 'guitar':
            # another part of the same song plays a different line
            expert = [(t, [(lane + 1 + i) % 5 for i, lane in enumerate(lanes)]) for t, lanes in expert[::2]]
    return {level: level_ticks(expert, level, song.flat_levels) for level in song.levels(instrument)}


# A song's streams: its own from its own generator, or, for a copy, the guitar
# stream its source drew, so the two charts parse to the same notes and hash
# the same. A mirrored instrument is given the guitar's Expert and draws nothing.
def song_streams(song, seed):
    if song.copy_of:
        source = next(s for s in SONGS if s.folder == song.copy_of)
        expert = expert_ticks(random.Random(f'{seed}:{source.folder}'), source)
        return {'guitar': part_streams(None, song, 'guitar', expert)}
    rng = random.Random(f'{seed}:{song.folder}')
    streams = {}
    for instrument in song.parts:
        mirrored = instrument in song.mirror_lead
        streams[instrument] = part_streams(rng, song, instrument, streams['guitar']['expert'] if mirrored else None)
    return streams


# --- writers ----------------------------------------------------------------------------

def write_ini(song, folder):
    lines = ['[song]']
    keys = {'genre': 'Fixture Rock', 'year': '2026', 'album': f'{song.pack} Album',
            'song_length': str(song.seconds * 1000), **song.ini, 'icon': PACKS[song.pack][0]}
    for key in sorted(keys):
        lines.append(f'{key} = {keys[key]}')
    text = '\n'.join(lines) + '\n'
    if song.encoding == 'utf-8-sig-crlf':
        (folder / 'song.ini').write_bytes(text.replace('\n', '\r\n').encode('utf-8-sig'))
    elif song.encoding == 'cp1252':
        (folder / 'song.ini').write_bytes(text.encode('cp1252'))
    else:
        (folder / 'song.ini').write_bytes(text.encode('utf-8'))


def chart_section(name, ticks, drums=False, extras=()):
    lines = [f'[{name}]', '{']
    for tick, lanes in ticks:
        for lane in lanes:
            lines.append(f'  {tick} = N {lane} 0')
    for line in extras:
        lines.append(f'  {line}')
    lines.append('}')
    return lines


def write_chart(rng, song, folder, streams):
    lines = ['[Song]', '{', f'  Name = "{song.ini["name"]}"', f'  Resolution = {RESOLUTION}', '}',
             '[SyncTrack]', '{', '  0 = TS 4', f'  0 = B {song.bpm * 1000}', '}',
             '[Events]', '{', '}']
    for instrument, levels in streams.items():
        for level, ticks in levels.items():
            prefix = instruments.CHART_LEVEL_PREFIX[level]
            if instrument == 'drums':
                # kick on the beat, hands 1-4 elsewhere
                drum_ticks = [(t, [0] if i % 3 == 0 else [1 + (i % 4)]) for i, (t, _) in enumerate(ticks)]
                lines += chart_section(f'{prefix}Drums', drum_ticks)
                continue
            # C1's bass uses the legacy section name the parser falls back to
            base = 'SingleBass' if (instrument == 'bass' and song.folder.startswith('C1')) \
                else instruments.CHART_BASE_SECTIONS[instrument][0]
            extras = []
            if (song.folder.startswith('A1') or song.copy_of == 'A1 - Grid Runner') and level == 'expert':
                # an open note, a tap/force modifier pair on a real note, a star-power
                # phrase and a solo marker: the parser folds the first and ignores the rest
                first = ticks[0][0]
                extras = [f'{first} = N 5 0', f'{first} = N 6 0', f'{first + GRID * 8} = N 7 0',
                          f'{first} = S 2 768', f'{first} = E solo']
            lines += chart_section(f'{prefix}{base}', ticks, extras=extras)
    (folder / 'notes.chart').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def write_mid(rng, song, folder, streams, name='notes.mid', truncate=False):
    mid = mido.MidiFile(type=1, ticks_per_beat=RESOLUTION)
    tempo = mido.MidiTrack()
    tempo.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(song.bpm), time=0))
    tempo.append(mido.MetaMessage('end_of_track', time=0))
    mid.tracks.append(tempo)
    for instrument, levels in streams.items():
        track = mido.MidiTrack()
        track.append(mido.MetaMessage('track_name', name=instruments.MID_TRACK_NAMES[instrument][0], time=0))
        if song.enhanced_opens and instrument == 'guitar':
            track.append(mido.MetaMessage('text', text='[ENHANCED_OPENS]', time=0))
        events = []   # (abs tick, order, message without time)
        for level, ticks in levels.items():
            base = instruments.MID_PITCH_BASE[level]
            if instrument == 'vocals':
                # a sung line walking the lanes over an octave, a slide every
                # fifth note, a talkie every seventh, a percussion tap every
                # eleventh; the lyric rides on the note's tick
                for i, (tick, lanes) in enumerate(ticks):
                    if i % 11 == 0:
                        events.append((tick, 0, mido.Message('note_on', note=96, velocity=100)))
                        events.append((tick + NOTE_OFF_TICKS, 1, mido.Message('note_off', note=96, velocity=0)))
                        continue
                    pitch = 55 + lanes[0] * 3 + (i % 3)
                    lyric = 'la' if i % 5 else '+'
                    if i % 7 == 0:
                        lyric = 'talk#'
                    events.append((tick, 0, mido.Message('note_on', note=pitch, velocity=100)))
                    events.append((tick, 0, mido.MetaMessage('lyrics', text=lyric)))
                    events.append((tick + GRID * 2, 1, mido.Message('note_off', note=pitch, velocity=0)))
                continue
            for i, (tick, lanes) in enumerate(ticks):
                if instrument == 'drums':
                    pitches = [base] if i % 3 == 0 else [base + 1 + (i % 4)]
                elif song.enhanced_opens and level == 'expert' and i % 7 == 0:
                    pitches = [base - 1]            # open note, honoured only with the marker
                else:
                    pitches = [base + lane for lane in lanes]
                for pitch in pitches:
                    events.append((tick, 0, mido.Message('note_on', note=pitch, velocity=100)))
                    events.append((tick + NOTE_OFF_TICKS, 1, mido.Message('note_off', note=pitch, velocity=0)))
        events.sort(key=lambda e: (e[0], e[1], getattr(e[2], 'note', -1)))
        at = 0
        for tick, _, msg in events:
            msg.time = tick - at
            at = tick
            track.append(msg)
        track.append(mido.MetaMessage('end_of_track', time=0))
        mid.tracks.append(track)
    path = folder / name
    mid.save(str(path))
    if truncate:
        data = path.read_bytes()
        path.write_bytes(data[:len(data) * 2 // 3])   # cut inside the last track's notes


# The registry publish needs for this library: the three packs, dated a day
# apart so the changelog groups them, and one site change. Written beside the
# library, not inside it (it is not a song folder).
def write_registry(path, lib):
    lines = ['# fixture registry']
    for i, (name, (icon, release, official)) in enumerate(PACKS.items()):
        lines += ['', '[[pack]]', f'name = "{name}"', f'folder = "{name}"',
                  f'source = "{"https://example.com/" + icon if official else ""}"',
                  f'added = 2026-09-0{7 + i}', 'notes = "Fixture pack, invented."']
    lines += ['', '[[change]]', 'date = 2026-09-07', 'text = "First fixture publish."', '']
    pathlib.Path(path).write_text('\n'.join(lines), encoding='utf-8')
    return pathlib.Path(path)


def write(dest, seed=SEED):
    root = pathlib.Path(dest)
    for song in SONGS:
        rng = random.Random(f'{seed}:{song.folder}')
        folder = root / song.pack / song.folder
        folder.mkdir(parents=True, exist_ok=True)
        write_ini(song, folder)
        if song.fmt == 'none':
            continue
        streams = song_streams(song, seed)
        if song.fmt == BROKEN:
            write_mid(rng, song, folder, streams, truncate=True)
        elif song.fmt == 'chart':
            write_chart(rng, song, folder, streams)
        elif song.fmt == 'mid':
            write_mid(rng, song, folder, streams)
        else:   # both: the mid carries different notes, and the chart must win
            write_mid(rng, song, folder, {i: part_streams(random.Random(f'{seed}:{song.folder}:mid'), song, i)
                                          for i in song.parts})
            write_chart(rng, song, folder, streams)
    return Library(root.resolve(), list(SONGS))


def main():
    if len(sys.argv) != 2:
        sys.exit('usage: python tests/fixture.py DEST')
    lib = write(sys.argv[1])
    rows = ' '.join(f'{k} {v}' for k, v in lib.rows_by_sheet.items())
    print(f'{lib.ini_count} song.ini, {len(lib.charted)} charted, {lib.codes} codes, rows {rows}')


if __name__ == '__main__':
    main()
