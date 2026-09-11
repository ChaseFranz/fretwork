"""
LABELS - human-facing display strings for the abbreviated column/metric keys

The short keys ('pNPS', 'medVPS', 'COV', 'DurationS') stay exactly as they are
everywhere in the data path - density.calc_metrics output, formula.calc_nvcov
output, the dataframes in analyze.py, and the xlsx headers. Nothing keyed off a
column name has to change. This module is the single place that maps one of
those keys to something a person can read, applied only at display time.

    COLUMN_LABELS  short label for a column header
    VALUE_ORDER    the order a column's values are listed and sorted in
    COLUMN_HELP    one-line explanation, for tooltips / hover text
    DISPLAY_ORDER  left-to-right column order on the page
    DEFAULT_HIDDEN columns a first visit does not show
    FOOTER_LINKS   attribution links along the bottom of the page
    UI             interface strings for the page

Anything not in COLUMN_LABELS falls back to the raw key, so a new metric column
shows up readable-ish instead of blowing up - see label().

Formula terms are spelled out in Methodology.md; the help text here is the short
version of the same thing.
"""

from functions import instruments

# NPS/VPS get spelled out - "notes/sec" and "fret changes/sec" are what they
# actually measure, and that reads better than the acronym in a column header
COLUMN_LABELS = {
    # view-only, added by the page rather than the data pipeline
    'Rank':       'Rank',

    # identity / metadata
    'Code':       'Code',
    'Song Title': 'Song',
    'Artist':     'Artist',
    'Level':      'Level',
    'Type':       'Part',
    'Charter':    'Charter',
    'Release':    'Source',
    'Added':      'Added',
    'Official':   'Official',

    # shape of the chart
    'NoteCount':  'Notes',
    'DurationS':  'Length',

    # difficulty
    'Difficulty': 'Original Tier',
    'D':          'Difficulty (D)',
    'RemapDiff':  'Remap Tier',
    'CalcTier':   'Calc Tier',
    'Pct':        'Percentile',

    # note density
    'pNPS':       'Peak notes/sec',
    'aNPS':       'Avg notes/sec',
    'medNPS':     'Median notes/sec',
    'stdNPS':     'Std dev notes/sec',

    # fret variability
    'pVPS':       'Peak changes/sec',
    'aVPS':       'Avg changes/sec',
    'medVPS':     'Median changes/sec',
    'stdVPS':     'Std dev changes/sec',

    # formula components
    'N':          'Note factor (N)',
    'V':          'Variability factor (V)',
    'COV':        'Consistency (CoV)',
}

COLUMN_HELP = {
    'Rank':       'Position in the list as currently sorted and filtered, so it renumbers as you narrow the view.',
    'Code':       'Retrieval code: 8-digit song hash, then level (E/M/H/X) and instrument (G/C/R/B/K). Pass it to render.py.',
    'Song Title': 'Song name from song.ini.',
    'Artist':     'Artist from song.ini.',
    'Level':      'Charted difficulty level: Easy, Medium, Hard or Expert.',
    'Type':       'Which part this row is: Lead, Co-op, Rhythm, Bass or Keys.',
    'Charter':    'Who charted the song, from song.ini.',
    'Release':    'Release or source pack. Officials are matched against the tables in sources/.',
    'Added':      'When the pack this chart came in was added to the site, from packs.toml.',
    'Official':   'True when the source pack is an official Guitar Hero or Rock Band release.',

    'NoteCount':  'Total notes in this chart. Frets played together count as one note, same as the games score it.',
    'DurationS':  'Time from t=0 to the last note.',

    'Difficulty': 'The diff_* tier already in song.ini. -1 means the tag is missing.',
    'D':          'Calculated difficulty, D = N x V x CoV. The main output. Higher is harder, uncapped.',
    'RemapDiff':  'D binned to 0-6, calibrated per instrument so the spread matches official tiers. From the Expert chart only.',
    'CalcTier':   'Log-scaled tier, one step per 0.44 increase in ln(D) above 7.6. Uncapped, so hard customs reach 10+. From the Expert chart only.',
    'Pct':        'Sits at or above N% of the charts on this sheet at the same level, officials and customs together. Ties share a value and the top chart reads 100. The Guitar sheet pools Lead, Rhythm and Co-op, which share one calibration group.',

    'pNPS':       'Busiest one-second window, in notes per second.',
    'aNPS':       'Notes per second across the whole chart, including rests.',
    'medNPS':     'Median one-second window. Resistant to a single spike.',
    'stdNPS':     'Spread of note density across the chart.',

    'pVPS':       'Busiest one-second window of fret movement.',
    'aVPS':       'Fret changes per second across the whole chart.',
    'medVPS':     'Median one-second window of fret movement.',
    'stdVPS':     'Spread of fret movement across the chart.',

    'N':          'Note-density term: cube root of median x average x peak notes/sec.',
    'V':          'Variability term: cube root of median x average x peak changes/sec.',
    'COV':        'Interaction term, 1 or higher. Rewards charts whose difficulty is uneven.',
}

# ---------------------------------------------------------------------
# "no data" sentinels
# ---------------------------------------------------------------------
# Difficulty's -1 has two origins that mean the same thing to a reader:
#   - the diff_* tag is absent, and ini_parser falls back to '-1'
#   - the tag is present but set to -1, which is the unrated convention
#     (the GH3 pack does this: every diff_* is -1 while diff_band is set)
# xlsx_format already treats -1 as blank for fill/color-scale purposes; this is
# the same idea for any human-facing surface.
MISSING_VALUES = {
    'Difficulty': (-1,),
}

MISSING_TEXT = '\u2014'  # em dash

MISSING_HELP = {
    'Difficulty': 'No difficulty rating in song.ini (diff_* is -1 or absent)',
    'RemapDiff':  'No Expert chart for this instrument to anchor the tier to',
    'CalcTier':   'No Expert chart for this instrument to anchor the tier to',
    'Added':      'Not registered in packs.toml',
}


# True for None/NaN or a column's own "unrated" sentinel
def is_missing(column, value):
    if value is None:
        return True
    return value in MISSING_VALUES.get(column, ())


# columns holding a duration in seconds - shown as m:ss, still sorted as a number
TIME_COLUMNS = ('DurationS',)


# The columns whose values have an order of their own. Sorting them as text puts
# Expert between Easy and Hard, and Co-op before Lead. Both orders come from
# instruments.py rather than being spelled out again here, and both read as
# ascending: the filter list runs top to bottom in this order, and so does a sort
# on the column. Official is deliberately absent - as plain text its two values
# already sort Custom before Official, which is what puts the ticks on top when
# the column is first clicked, since the first click sorts descending.
VALUE_ORDER = {
    'Level': tuple(instruments.LEVEL_DISPLAY_NAMES[k] for k in instruments.LEVEL_KEYS),
    'Type': tuple(instruments.TYPE_LABELS[k] for k in instruments.INSTRUMENT_KEYS),
}

# A column whose stored values are not what a reader should see. Display only:
# the filter still matches on the stored key underneath.
VALUE_LABELS = {
    'Official': {'true': 'Official', 'false': 'Custom'},
}


# The four places this site points at, named once. Every mention of fretwork or
# its author in the prose below links to one of them.
ENGINE_REPO = 'https://github.com/Staycation44/fretwork'
CHANNEL = 'https://www.youtube.com/@StaycationGH'
FORK_REPO = 'https://github.com/ChaseFranz/fretwork'
VIDEO = 'https://youtu.be/emoWMpDJ4ls'

# The author is "Staycation44" everywhere in the prose, matching the GitHub
# account and the video credit - except in the two copyright notices below, which
# quote LICENSE verbatim ("Copyright (c) 2026 Staycation", no 44). MIT requires
# that notice to travel unaltered, so the inconsistency is deliberate: do not
# tidy it up without changing LICENSE upstream first.
# Prose that names fretwork or Staycation44 carries a minimal [text](url) markup
# rather than HTML. The renderers - rich() in dom.js, rich_text() in page.py -
# escape every character and build the anchors themselves, so a string that ever
# came from data could not smuggle markup through the same path.
FOOTER_LINKS = (
    ('How difficulty is scored', VIDEO),
    ('fretwork engine', ENGINE_REPO),
    ('@StaycationGH', CHANNEL),
    ('Site source', FORK_REPO),
)

# The site's document pages, in footer order: the published file name and the UI
# key of its title. page.render_doc links each to the others; the footer lists them
# after the request link; the boot payload carries the names so a test can count.
DOC_PAGES = (('about.html', 'about'), ('changelog.html', 'changelog'))

# Left-to-right order on the page, which is not the spreadsheet's order: D is what
# the site is for, so it sits beside the song instead of past the right edge.
# Anything missing from this list keeps its spreadsheet position, at the end.
DISPLAY_ORDER = (
    'Song Title', 'Artist', 'D', 'Pct', 'CalcTier', 'Level', 'Type',
    'DurationS', 'NoteCount', 'Charter', 'Release', 'Added',
    'Difficulty', 'RemapDiff', 'Official', 'Code',
)

# Off by default, so a first visit is the ten columns worth reading rather than
# every column the spreadsheet has. Each is still one click away in the chooser,
# and search still looks inside Charter and Release while they are hidden:
#   Difficulty  the tag already in song.ini, not what this site calculates
#   RemapDiff   CalcTier says the same thing without a 0-6 ceiling
#   Official    the header has a chip for it, which is the useful form
#   Code        only means something to render.py
#   Added       the changelog page tells the same story with names and dates
# Charter is deliberately NOT in this list: the people most likely to read this
# site are the ones who charted what is in it.
DEFAULT_HIDDEN = ('Difficulty', 'RemapDiff', 'Official', 'Code', 'Added')


# The in-page answer to "what is this number?", which until now lived only in a
# 20-minute video linked from the footer. Kept as (heading, body) pairs so the
# panel that renders it needs no markup of its own.
EXPLAINER = (
    ('What D measures',
     'D is a single number for how hard a chart is to play, read out of the chart '
     'file itself rather than from anyone\u2019s opinion. It multiplies three things: '
     'how busy the chart is (N, from the peak, average and median notes per second), '
     'how much the fretting hand has to move (V, the same three figures for fret '
     'changes), and how unevenly that work is spread across the song (CoV). Higher '
     'is harder, and the scale has no ceiling \u2013 the hardest charts here run past 1000.'),
    ('Reading the tiers',
     'Calc Tier is D on a log scale: one step for every 0.44 rise in ln(D) above 7.6, '
     'so it keeps climbing past 10 for the hardest customs. Remap Tier is the same '
     'value binned into the 0\u20136 range the games use, calibrated per instrument. Both '
     'are computed from the Expert chart and then shown on every difficulty of that '
     'song, because song.ini carries only one rating per instrument. Percentile is '
     'where a chart\u2019s D sits among the charts on its sheet at the same level, so it '
     'moves as the library grows.'),
    ('What it does not know',
     'Strum, HOPO and tap state are discarded, so how a chart flows does not change '
     'its score. There is no pattern recognition \u2013 trills, anchoring and chord '
     'shapes all count simply as movement. Long quiet stretches pull the averages '
     'down. Drums and vocals are not scored at all.'),
    ('Where the numbers come from',
     f'Every chart here was parsed and scored by [fretwork]({ENGINE_REPO}), an '
     f'open-source project by [Staycation44]({CHANNEL}). This site runs that engine '
     f'unchanged and only displays the result. The full method, including the '
     f'calibration tables, is in [Methodology.md]({ENGINE_REPO}/blob/main/Methodology.md).'),
)


# The about page. Its own page rather than another heading in the explainer,
# because the people who need it are not the people asking what D means - they
# are asking whether this is the official site, whether songs can be downloaded
# here, and who to complain to. All three answers deserve a URL.
ABOUT = (
    ('What this site is',
     'Fretladder publishes calculated difficulty ratings for 5-fret rhythm-game charts '
     '\u2013 Guitar Hero, Rock Band, Clone Hero, and the custom charts made for them. '
     'Every rating is computed from the chart file itself. None of it is hand-assigned, '
     'voted on, or edited afterwards. How the calculation works is explained under '
     '\u201cHow it works\u201d on the charts page.'),
    ('An independent project',
     f'Fretladder is not affiliated with, endorsed by, or run by '
     f'[Staycation44]({CHANNEL}), and it is not the [fretwork]({ENGINE_REPO}) project '
     f'itself. It is a separate fork that uses fretwork\u2019s engine under its MIT '
     f'licence, hosted and maintained independently. Anything about this site \u2013 a '
     f'wrong rating, a missing pack, a bug \u2013 belongs here rather than with the '
     f'engine\u2019s author or their YouTube channel.'),
    ('What is stored here, and what is not',
     'The site hosts no audio and no chart files, and nothing can be downloaded from it. '
     'What it holds is numbers calculated from charts, the song, artist, charter and pack '
     'names those charts already carry, and one rendered graph per chart. It is not a '
     'place to get songs.'),
    ('Ownership',
     'Guitar Hero, Rock Band and Clone Hero, and the names and marks that go with them, '
     'belong to their respective owners. The songs belong to their rights holders, and '
     'the charts to the people who made them. Fretladder claims none of it, and is '
     'endorsed by none of them.'),
    ('Licence',
     f'The code behind this site is a fork of [fretwork]({ENGINE_REPO}), published under '
     f'the [MIT licence]({ENGINE_REPO}/blob/main/LICENSE), which requires the original '
     f'copyright notice to travel with it, unaltered: \u201cCopyright (c) 2026 '
     f'[Staycation]({CHANNEL})\u201d. '
     f'The fork\u2019s own source is [on GitHub]({FORK_REPO}).'),
)


# "4,634 charts", grouped for readability
def t_count(n):
    return UI['chart_count'].format(n=f"{n:,}")


def label(column):
    return COLUMN_LABELS.get(column, column)


def help_text(column):
    return COLUMN_HELP.get(column, '')


# interface strings for serve.py's page, kept here so the wording lives in one file
UI = {
    'title':            'Fretwork',            # overridden by config.SITE_NAME at serve time
    'description':      'Difficulty ratings for Clone Hero and Guitar Hero charts, '
                        'scored from note density and fret movement.',
    'updated':          'Updated {date}',
    'chart_count':      '{n} charts',
    # what "beta" actually means here, rather than a bare badge
    'beta':             'beta',
    'beta_tip':         'Coverage and calibration are both still changing',
    # the badge already says "beta", so the note carries the substance instead of
    # repeating it - and stays one line on a desktop, three on a phone
    'beta_note':        'The library is partial and the scoring is still being calibrated, '
                        'so a chart\u2019s numbers can move between updates. '
                        'Guitar, bass and keys for now.',

    'copyright':        f'An independent fork of [fretwork]({ENGINE_REPO}), not '
                        f'affiliated with its author. Engine copyright (c) 2026 '
                        f'[Staycation]({CHANNEL}).',
    'license_label':    'MIT License',
    'license_url':      f'{ENGINE_REPO}/blob/main/LICENSE',
    'reorder_tip':      'Drag to reorder',
    'resize_tip':       'Drag to resize, double-click to fit',
    'columns_reset_tip':'Back to the default columns, order and widths',
    'search':           'Search song, artist, charter or source...',
    'clear_one':        'Clear 1 filter',
    'clear_many':       'Clear {n} filters',
    'count':            '{shown} of {total} charts',
    'filter_tip':       'Filter this column',
    'sort_tip':         'Sort by this column',
    'code_tip':         'Click to see the difficulty graph, shift-click to copy the code',
    'select_all':       'Select all',
    'select_none':      'Clear',
    'value_search':     'Search values',
    'range_apply':      'Apply',
    'range_clear':      'Clear',
    'range_hint':       '{label} between min and max',
    'range_min':        'min {v}',
    'range_max':        'max {v}',
    'rendering':        'Rendering graph...',
    'render_failed':    'No graph available for this chart.',
    'copied':           'Copied {code}',
    'no_data':          'No charts match these filters.',

    # quick filters in the header, a shortcut into the Official column
    'official_chip':    'Official',
    'custom_chip':      'Custom',

    # the explainer panel
    'explainer':        'How it works',
    'explainer_tip':    'What D means, and what it does not measure',
    'explainer_title':  'How difficulty is scored',
    'about':            'About this site',
    'about_back':       'Back to the charts',
    'changelog':        'What\u2019s new',
    'changelog_tip':    'Every pack on the site, and when it was added',
    'changelog_intro':  'Every pack on the site, newest first, with the date it was added and where it is '
                        'published, and what changed on the site itself. The date in the charts page '
                        'header is when the numbers were last computed. Percentiles are relative to the '
                        'whole library on that day, so they shift a little with every update.',
    'changelog_totals': '{packs} packs, {songs} songs, {charts} charts',
    'pack_counts':      '{songs} songs, {charts} charts',
    'changelog_date_tip': 'Show the Expert charts added on this date',
    # The video is the origin of all of this, so it leads the explainer. Served
    # from the no-cookie host, and only requested if someone opens the panel -
    # the iframe is not in the page until then.
    'video_embed':      'https://www.youtube-nocookie.com/embed/emoWMpDJ4ls'
                        '?start=470&rel=0&enablejsapi=1',   # 7:50, where the method starts
    'video_title':      'Solving Guitar Hero\u2019s Difficulty Problem \u2013 Staycation44',
    'video_caption':    f'Solving Guitar Hero\u2019s Difficulty Problem \u2013 '
                        f'[Staycation44]({CHANNEL})',
    'explainer_more':   'Watch it on YouTube',
    'explainer_method': 'The full method (Methodology.md)',
    'method_url':       f'{ENGINE_REPO}/blob/main/Methodology.md',

    # reporting a rating that looks wrong, from the chart's own graph
    'report':           'Report this rating',
    'report_url':       f'{FORK_REPO}/issues/new?template=rating.yml',

    # the page CloudFront serves for a path that is not in the bucket
    'not_found_title':  'Page not found',
    'not_found':        'There is nothing at that address. Every chart is on one page.',
    'not_found_link':   'Go to the charts',

    # how someone asks for a pack to be scored
    'request':          'Request a song pack',
    'request_url':      f'{FORK_REPO}/issues/new?template=song-pack.yml',

    # row / graph interaction
    'row_tip':          'Click for the difficulty graph',
    'pct_of':           'At or above {pct}% of {level} {sheet} charts',
    'graph_label':      'Difficulty graph',
    'grid_label':       'Charts, sortable and filterable by column',
    'copy_code_tip':    'Copy this code',
    'close_tip':        'Close (Esc)',

    # column chooser
    'columns':          'Columns',
    'columns_tip':      'Choose which columns to show',
    'columns_reset':    'Reset columns',
}
