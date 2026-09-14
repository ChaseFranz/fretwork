"""
PLOT - Renders selected song's curves to a PNG.

y-axis scales per song

Guitar/Bass/Keys: NPS/VPS/D share an axis by using D = sqrt(NPS * VPS)
Drums: Hands/Travel/Kicks/D share an axis, D = Hands + Travel + Kicks
    - Hands reuses the NPS color, Kicks reuses the VPS color, Travel has a new color
    - a chart with 2x stacks a second chart underneath the 1x

Light/dark themes can be set in config
"""

import pathlib
import re

import matplotlib
matplotlib.use('Agg')  # no display in a batch render
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator, FuncFormatter

import config
from functions import instruments

# fixed header truncation limits - keeps PNG width consistent song to song
TITLE_LIMIT = 44      # applied to song title and artist separately
CHARTER_LIMIT = 28
RELEASE_LIMIT = 34

# small in-axes label distinguishing the two drum subplots
KICK_MODE_LABELS = {
    '1x': '1x (single pedal)',
    '2x': '2x (double pedal)',
}

#-------------
# Filename
#-------------
_UNSAFE = re.compile(r'[^A-Za-z0-9 _.-]')

# strips non-ASCII for display
def _safe(text, limit=60):
    cleaned = _UNSAFE.sub('', str(text)).strip()
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned[:limit] or 'unknown'

# code + artist + song title
def output_filename(entry):
    meta = entry.get('meta', {})
    return f"{entry['code']}_{_safe(meta.get('Artist'))} - {_safe(meta.get('Name'))}.png"

# combined EMHX level + instrument label
def level_instrument_label(entry):
    level_label = instruments.LEVEL_DISPLAY_NAMES.get(entry.get('level'), '')
    instrument_label = instruments.DISPLAY_NAMES.get(entry.get('instrument'), '')
    return f"{level_label} {instrument_label}".strip()

# RENDER_DEFAULT + the selected theme
def resolve_profile(profile=None):
    if profile is not None:
        return dict(profile)
    mode = config.RENDER_DEFAULT.get('mode', 'light')
    theme = config.RENDER_THEMES.get(mode, config.RENDER_THEMES['light'])
    return {**config.RENDER_DEFAULT, **theme}

# Header text
def _ellipsize(text, limit):
    text = str(text)
    if len(text) <= limit:
        return text
    return text[:limit - 3].rstrip() + '...'

# sets Release (Official tag)
def release_label(meta):
    release = str(meta.get('Release') or '').strip() or 'Custom'
    if release.lower() == 'custom':
        return 'Custom'
    tag = 'official' if meta.get('Official') else 'custom'
    return f"{_ellipsize(release, RELEASE_LIMIT)} ({tag})"

# D display - 5 Fret is just "D" / drums is "D_1x" or "D_1x / D_2x"
def _d_display(difficulty):
    if 'D_1x' in difficulty:
        d_1x = difficulty['D_1x']
        d_2x = difficulty.get('D_2x')
        if d_2x is not None:
            return f"D {d_1x:.2f} / {d_2x:.2f}"
        return f"D {d_1x:.2f}"
    return f"D {difficulty['D']:.2f}"

# metadata line - level+instrument / charter / release (tag) / file type / D / calc tier / remap bin
def meta_header(entry, difficulty, original_diff=None):
    meta = entry.get('meta', {})
    instrument_key = entry.get('instrument')

    bits = [
        level_instrument_label(entry),
        f"charter {_ellipsize(meta.get('Charter', 'unk'), CHARTER_LIMIT)}",
        release_label(meta),
        str(entry.get('source_format', '?')),
    ]

    # meta.Difficulty is a per-instrument dict set from song.ini at last Build (Expert-referenced)
    if difficulty is not None:
        remap = difficulty.get('RemapDiff')
        calc_tier = difficulty.get('CalcTier')
        ini_diff = (meta.get('Difficulty') or {}).get(instrument_key, '-')
        diff_value = original_diff if original_diff is not None else ini_diff
        bits.append(_d_display(difficulty))
        bits.append(f"diff {diff_value}")
        bits.append(f"remap bin {remap if remap is not None else '-'}")
        bits.append(f"calc tier {calc_tier if calc_tier is not None else '-'}")

    return '  |  '.join(bits)

# seconds to m:ss output for time axis
def _format_time(value, pos=None):
    total = max(int(round(value)), 0)
    minutes, seconds = divmod(total, 60)
    return f"{minutes}:{seconds:02d}"

#------------
# Rendering
#------------

# render each song
#    entry: cache_mod.entries_by_code() result - a flattened song+instrument+level entry
#    curves: output of functions.curves.calc_curves
#    difficulty: optional dict (D/N/V/COV + Expert-anchored RemapDiff/CalcTier), for header
#    original_diff: optional backed-up original diff_* value for this instrument, for header
#    profile: style dict, defaults to RENDER_DEFAULT merged with the selected theme
#    Returns the written path.
def render_song(entry, curves, difficulty=None, original_diff=None, profile=None, out_dir=None):
    profile = resolve_profile(profile)
    out_dir = pathlib.Path(out_dir or config.RENDER_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)

    time_s = [ms / 1000.0 for ms in curves['time_ms']]
    meta = entry.get('meta', {})

    fig, ax_nv = plt.subplots(
        figsize=tuple(profile['figsize']),
        dpi=profile['dpi'],
    )

    fig.patch.set_facecolor(profile['figure_bg'])
    ax_nv.set_facecolor(profile['axes_bg'])

    #D: filled backdrop
    ax_nv.plot(time_s, curves['d_raw'], color=profile['color_d'],
               linewidth=profile['linewidth'], zorder=3, label='~D')
    if profile.get('fill_curves'):
        ax_nv.fill_between(time_s, curves['d_raw'], color=profile['color_d'],
                           alpha=profile['fill_alpha'], linewidth=0, zorder=2)

    #NPS / VPS: dotted lines
    ax_nv.plot(time_s, curves['nps'], color=profile['color_nps'],
               linewidth=profile['linewidth'], linestyle=':',
               zorder=3, label='Notes')
    ax_nv.plot(time_s, curves['vps'], color=profile['color_vps'],
               linewidth=profile['linewidth'], linestyle=':',
               zorder=3, label='Variability')

    ax_nv.set_ylabel('per second', fontsize=profile['label_size'],
                     color=profile['text_color'])
    ax_nv.tick_params(labelsize=profile['tick_size'], colors=profile['text_color'])
    ax_nv.set_ylim(bottom=0)
    ax_nv.grid(True, alpha=profile['grid_alpha'], linewidth=0.6,
               color=profile['grid_color'])
    ax_nv.margins(x=0)
    for spine in ax_nv.spines.values():
        spine.set_color(profile['spine_color'])

    # x-axis: M:SS time scale
    ax_nv.xaxis.set_major_formatter(FuncFormatter(_format_time))
    ax_nv.xaxis.set_major_locator(MaxNLocator(nbins=10, integer=True))
    ax_nv.set_xlabel('Time (m:ss)', fontsize=profile['label_size'],
                     color=profile['text_color'])

    # Legend - horizontal below the axes
    ax_nv.legend(loc='upper center', bbox_to_anchor=(0.5, -0.08),
                 ncol=3, frameon=False,
                 fontsize=profile['tick_size'], labelcolor=profile['text_color'])

    # Header - title row, metadata row under
    title = (f"{_ellipsize(meta.get('Name', 'unk'), TITLE_LIMIT)}"
             f" - {_ellipsize(meta.get('Artist', 'unk'), TITLE_LIMIT)}")
    ax_nv.set_title(title, fontsize=profile['title_size'], loc='left',
                    color=profile['text_color'], pad=profile['title_pad'])
    ax_nv.text(0.0, 1.01, meta_header(entry, difficulty, original_diff),
               transform=ax_nv.transAxes, ha='left', va='bottom',
               fontsize=profile['tick_size'], color=profile['muted_text_color'])

    fig.tight_layout(rect=(0, 0.06, 1, 1))

    out_path = out_dir / output_filename(entry)
    fig.savefig(out_path, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close(fig)

    return out_path

# style one drum graph (1x or stacked 1x/2x)
def _style_drum_axes(ax, time_s, curves, mode, profile, show_xlabel):
    ax.set_facecolor(profile['axes_bg'])

    d_curve = curves['d_raw'][mode]
    kps_curve = curves['kps'][mode]

    # D: filled backdrop (H + T + K)
    ax.plot(time_s, d_curve, color=profile['color_d'],
            linewidth=profile['linewidth'], zorder=3, label='~D')
    if profile.get('fill_curves'):
        ax.fill_between(time_s, d_curve, color=profile['color_d'],
                        alpha=profile['fill_alpha'], linewidth=0, zorder=2)

    # Hands / Travel / Kicks: dotted lines
    ax.plot(time_s, curves['hps'], color=profile['color_nps'],
            linewidth=profile['linewidth'], linestyle=':', zorder=3, label='Hands')
    ax.plot(time_s, curves['tps'], color=profile['color_tps'],
            linewidth=profile['linewidth'], linestyle=':', zorder=3, label='Travel')
    ax.plot(time_s, kps_curve, color=profile['color_vps'],
            linewidth=profile['linewidth'], linestyle=':', zorder=3, label='Kicks')

    ax.set_ylabel('per second', fontsize=profile['label_size'], color=profile['text_color'])
    ax.tick_params(labelsize=profile['tick_size'], colors=profile['text_color'])
    ax.set_ylim(bottom=0)
    ax.grid(True, alpha=profile['grid_alpha'], linewidth=0.6, color=profile['grid_color'])
    ax.margins(x=0)
    for spine in ax.spines.values():
        spine.set_color(profile['spine_color'])

    # x-axis
    ax.xaxis.set_major_formatter(FuncFormatter(_format_time))
    ax.xaxis.set_major_locator(MaxNLocator(nbins=10, integer=True))
    if show_xlabel:
        ax.set_xlabel('Time (m:ss)', fontsize=profile['label_size'], color=profile['text_color'])

    # tag to id 1x/2x
    if curves.get('has_2x'):
        ax.text(0.995, 0.96, KICK_MODE_LABELS[mode], transform=ax.transAxes,
                ha='right', va='top', fontsize=profile['tick_size'],
                color=profile['muted_text_color'])

# render one drums song
#    entry: cache_mod.entries_by_code() result
#    curves: output of functions.curves.calc_drum_curves
#    difficulty: optional dict (D_1x, optional D_2x, Expert-anchored RemapDiff/CalcTier), for header
#    original_diff: optional backed-up original diff_drums value for this instrument, for header
#    profile: style dict, defaults to RENDER_DEFAULT merged with the selected theme
#    Returns the written path.
def render_drum_song(entry, curves, difficulty=None, original_diff=None, profile=None, out_dir=None):
    profile = resolve_profile(profile)
    out_dir = pathlib.Path(out_dir or config.RENDER_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)

    time_s = [ms / 1000.0 for ms in curves['time_ms']]
    meta = entry.get('meta', {})
    has_2x = curves.get('has_2x', False)

    figsize = tuple(profile['figsize'])
    # stacked layout gets close to double height
    fig_height = figsize[1] * 1.9 if has_2x else figsize[1]

    n_rows = 2 if has_2x else 1
    fig, axes = plt.subplots(n_rows, 1, figsize=(figsize[0], fig_height), dpi=profile['dpi'])
    axes = [axes] if n_rows == 1 else list(axes)

    fig.patch.set_facecolor(profile['figure_bg'])

    modes = ['1x', '2x'] if has_2x else ['1x']
    for mode, ax in zip(modes, axes):
        _style_drum_axes(ax, time_s, curves, mode, profile, show_xlabel=True)

    # Legend - one shared legend below the bottom axes
    handles, labels = axes[0].get_legend_handles_labels()
    axes[-1].legend(handles, labels, loc='upper center', bbox_to_anchor=(0.5, -0.08),
                     ncol=4, frameon=False,
                     fontsize=profile['tick_size'], labelcolor=profile['text_color'])

    # Header - title + metadata line above the top axes
    title = (f"{_ellipsize(meta.get('Name', 'unk'), TITLE_LIMIT)}"
             f" - {_ellipsize(meta.get('Artist', 'unk'), TITLE_LIMIT)}")
    axes[0].set_title(title, fontsize=profile['title_size'], loc='left',
                      color=profile['text_color'], pad=profile['title_pad'])
    axes[0].text(0.0, 1.01, meta_header(entry, difficulty, original_diff),
                 transform=axes[0].transAxes, ha='left', va='bottom',
                 fontsize=profile['tick_size'], color=profile['muted_text_color'])

    base_height = figsize[1]
    bottom_margin = 0.06 * (base_height / fig_height)
    fig.tight_layout(rect=(0, bottom_margin, 1, 1))

    out_path = out_dir / output_filename(entry)
    fig.savefig(out_path, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close(fig)

    return out_path