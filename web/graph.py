"""
GRAPH - renders one chart's PNG, or its curve JSON, on demand, caching within the process

Owns the note cache and the memos, so two renderers cannot split them. The
curve JSON is what the page draws from: the raw window counts of each line
under ~D, named, the constants the smoothing needs, the recipe that makes ~D
of the smoothed lines, and the numbers the PNG header prints; the browser does
the smoothing itself, so a smoothing change never re-renders a PNG. One shape
for the three families (instruments.FAMILY), so the page has one drawing path:

    {v: 2, family, step, window, tau, n, head,
     series: {nps: [...], vps: [...]},          the lines, n counts each, in
                                                labels.CURVE_FAMILIES' order
     d: {geo: ['nps', 'vps']}                   ~D is their geometric mean (fret)
        | {sum: {hps: 1, tps: 1, kps: 1}}       or a weighted sum (drums, vocals)}

The recipes are functions/curves.py's d_raw lines: sqrt(nps * vps) for the
fret family, hps + tps + kps at the 1x reading for drums (the site ranks drums
by D_1x, so the graph shows the 1x picture; the 2x reading is the D_2x column),
and R * A * pps + S_WEIGHT * sps for vocals, whose R and A are the chart's own
register and articulation factors, so they ride in the file. Counts are
integers where the density module keeps them so (the fret family), else
rounded to four places.
"""

import json
import pathlib
import threading

import config
from functions import cache as cache_mod
from functions import curves as curves_mod
from functions import difficulty, drum_density, fret_density, timestamp, vocal_density, vocal_formula

CURVES_VERSION = 2


def _num(v):
    f = float(v)
    return int(f) if f.is_integer() else round(f, 4)


def _fret_series(entry):
    windows = fret_density.window_arrays(entry['notes'])
    if windows is None:
        return None
    return ({'nps': windows['raw_nps_samples'], 'vps': windows['raw_vps_samples']}, {'geo': ['nps', 'vps']})


# The hand and 1x kick streams on one grid, the longer of the two, as
# curves.calc_drum_curves pads them (without the 2x reading, which the site
# does not draw). A chart with no hand hits has no picture, as upstream's.
def _drum_series(entry):
    notes = entry['notes']
    hand = drum_density.window_arrays(notes['hand_mask'], entry.get('roll_spans'))
    if hand is None:
        return None
    kicks = drum_density.kick_arrays(notes['kick_mask'], 0b01)
    n = max(hand['time_ms'].size, kicks['time_ms'].size if kicks is not None else 0)
    pad = lambda arr: curves_mod._pad_to_length(arr, n)
    series = {'hps': pad(hand['raw_hps_samples']), 'tps': pad(hand['raw_tps_samples']),
              'kps': pad(kicks['raw_kps_samples']) if kicks is not None else [0] * n}
    return series, {'sum': {'hps': 1, 'tps': 1, 'kps': 1}}


def _vocal_series(entry):
    talkie, percussion = entry.get('talkie'), entry.get('percussion')
    windows = vocal_density.window_arrays(entry['notes'], talkie, percussion)
    if windows is None:
        return None
    metrics = vocal_density.calc_vocal_metrics(entry['notes'], talkie, percussion)
    diff = vocal_formula.calc_vocal_d(metrics)
    series = {'pps': windows['raw_pps_samples'], 'sps': windows['raw_sps_samples']}
    if windows['has_percussion']:
        series['perc'] = windows['raw_perc_samples']
    return series, {'sum': {'pps': _num(diff['R'] * diff['A']), 'sps': _num(vocal_formula.S_WEIGHT)}}


FAMILY_SERIES = {'fret': _fret_series, 'drums': _drum_series, 'vocals': _vocal_series}


# The curve JSON for one entry, compact, or None when the chart has no notes.
def curves_bytes(entry):
    if not difficulty.scorable(entry):
        return None
    family = difficulty.family(entry)
    made = FAMILY_SERIES[family](entry)
    if made is None:
        return None
    series, recipe = made
    diff = difficulty.entry_difficulty(entry) or {}
    head = {k: (None if v is None else int(v) if k in ('RemapDiff', 'CalcTier') else round(float(v), 4))
            for k, v in diff.items()}
    head['source'] = entry.get('source_format')
    n = len(next(iter(series.values())))
    doc = {'v': CURVES_VERSION, 'family': family, 'step': int(fret_density.STEP_MS), 'window': int(fret_density.WINDOW_MS),
           'tau': int(curves_mod.TAU_MS), 'n': n, 'head': head,
           'series': {k: [_num(v) for v in vals] for k, vals in series.items()}, 'd': recipe}
    return json.dumps(doc, separators=(',', ':')).encode('utf-8')


class GraphRenderer:
    """Renders retrieval codes to PNG bytes, loading the cache once, lazily."""

    def __init__(self, header, cache_path=None, out_dir=None):
        self.header = header
        self.cache_path = cache_path
        self.out_dir = out_dir or config.RENDER_DIR
        self._cache = None
        self._diffs = None
        self._png = {}
        self._curves = {}
        self._lock = threading.Lock()

    # None when the code is unknown or has no curve data.
    def png(self, code):
        if code in self._png:
            return self._png[code]
        with self._lock:
            if code in self._png:
                return self._png[code]
            entry = self.lookup(code)
            data = self.render(entry) if entry else None
            if data is not None:
                self._png[code] = data
            return data

    # The curve JSON bytes for a code, memoised; None for an unknown code.
    def curves(self, code):
        if code in self._curves:
            return self._curves[code]
        with self._lock:
            if code in self._curves:
                return self._curves[code]
            entry = self.lookup(code)
            data = curves_bytes(entry) if entry else None
            if data is not None:
                self._curves[code] = data
            return data

    # The cache entry behind a code, or None: unknown, or a stream shape its
    # family's metrics cannot read (a cache from before the family was scored).
    def lookup(self, code):
        entries, _missing = cache_mod.entries_by_code(self.cache(), [code])
        if not entries or not difficulty.scorable(entries[0]):
            return None
        return entries[0]

    # PNG bytes for one entry, never memoized: publish walks thousands of these.
    # The same per-family calls render.py makes, which is upstream's file.
    def render(self, entry, out_dir=None):
        # plot pulls matplotlib, so it stays off the startup path
        from functions import plot

        family = difficulty.family(entry)
        diff = difficulty.entry_difficulty(entry)
        original_diff = self.original_diff(entry)
        out_dir = out_dir or self.out_dir
        if family == 'drums':
            song_curves = curves_mod.calc_drum_curves(entry['notes'], roll_spans=entry.get('roll_spans'))
            if song_curves is None:
                return None
            if diff is not None:
                diff = {**diff, 'D_1x': diff['D']}    # plot's drum header reads the 1x reading by that name
            png_path = plot.render_drum_song(entry, song_curves, diff, original_diff=original_diff, out_dir=out_dir)
        elif family == 'vocals':
            song_curves = curves_mod.calc_vocal_curves(entry['notes'], entry.get('talkie'), percussion=entry.get('percussion'))
            if song_curves is None:
                return None
            png_path = plot.render_vocal_song(entry, song_curves, diff, original_diff=original_diff, out_dir=out_dir)
        else:
            song_curves = curves_mod.calc_curves(entry['notes'])
            if song_curves is None:
                return None
            png_path = plot.render_song(entry, song_curves, diff, original_diff=original_diff, out_dir=out_dir)
        return pathlib.Path(png_path).read_bytes()

    def cache(self):
        if self._cache is None:
            self.cache_path = self.cache_path or timestamp.latest_output(
                'cache', self.header, ext='pkl')
            self._cache = cache_mod.load(self.cache_path)
        return self._cache

    # The backed-up song.ini tier shown in the render header.
    def original_diff(self, entry):
        from functions import ini_updater

        if self._diffs is None:
            self._diffs = ini_updater.load_backup_diffs(self.header)
        return self._diffs.get(entry['song_path'], {}).get(entry['instrument'])
