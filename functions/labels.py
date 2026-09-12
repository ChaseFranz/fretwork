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

from functions import formula, instruments

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
    'Album':      'Album',
    'Year':       'Year',
    'Genre':      'Genre',
    'Added':      'Added',
    'SongKey':    'Song key',
    'NotesHash':  'Notes hash',
    'Copies':     'Copies',
    'Official':   'Official',
    # the link columns, page-built from the offline registry (web/links.py)
    'Chart':      'Chart page',
    'Leaderboard': 'Scores',

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
    'Album':      'Album from song.ini, as the charter wrote it. Empty when the file has none.',
    'Year':       'Release year from song.ini. A dash means the file has no four-digit year.',
    'Genre':      'Genre from song.ini, as the charter wrote it. Spellings vary between charters; empty when the file has none.',
    'Added':      'When the pack this chart came in was added to the site, from packs.toml.',
    'SongKey':    'A hash of every chart in the song: the same charts give the same key, whatever folder they came from, so it survives a re-download.',
    'NotesHash':  'Fingerprint of the notes. Two charts with the same hash play identically, whatever they are called.',
    'Copies':     'How many charts on this sheet have exactly these notes at this level and part, this one included. 1 is unique; 2 means the same chart is in another folder, usually another pack.',
    'Official':   'True when the source pack is an official Guitar Hero or Rock Band release.',
    'Chart':      'Where this chart is published: the arrow opens its page there. '
                  'A dash means no host was found for it.',
    'Leaderboard': 'Has a Clone Hero leaderboard: the arrow opens the scores page.',

    'NoteCount':  'Total notes in this chart. Frets played together count as one note, same as the games score it.',
    'DurationS':  'Time from t=0 to the last note.',

    'Difficulty': 'The diff_* tier already in song.ini. -1 means the tag is missing.',
    'D':          'Calculated difficulty, D = N x V x CoV. The main output. Higher is harder, uncapped.',
    'RemapDiff':  'D binned to 0-6, calibrated per instrument so the spread matches official tiers. From the Expert chart only.',
    'CalcTier':   f'Log-scaled tier, one step per {formula.LN_INC} increase in ln(D) above {formula.BASE_D}. Uncapped, so hard customs reach 10+. From the Expert chart only.',
    'Pct':        'Sits at or above N% of the charts on this sheet at the same level, officials and customs together. Each distinct chart counts once, however many packs carry it. Ties share a value and the top chart reads 100. The Guitar sheet pools Lead, Rhythm and Co-op, which share one calibration group.',

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
    'Year': (-1,),
}

MISSING_TEXT = '\u2014'  # em dash

MISSING_HELP = {
    'Difficulty': 'No difficulty rating in song.ini (diff_* is -1 or absent)',
    'RemapDiff':  'No Expert chart for this instrument to anchor the tier to',
    'CalcTier':   'No Expert chart for this instrument to anchor the tier to',
    'Added':      'Not registered in packs.toml',
    'Year':       'No four-digit year in song.ini',
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
    'Leaderboard': {'true': 'Yes', 'false': 'No'},
}


# The four places this site points at, named once. Every mention of fretwork or
# its author in the prose below links to one of them.
ENGINE_REPO = 'https://github.com/Staycation44/fretwork'
CHANNEL = 'https://www.youtube.com/@StaycationGH'
FORK_REPO = 'https://github.com/ChaseFranz/fretwork'
VIDEO = 'https://youtu.be/emoWMpDJ4ls'
# Where a chart can be published, in the order the Chart column prefers when a
# chart is on more than one: each host's label, tip, URL template and the
# character class its id must match. The page builds a link only from these
# (`static/js/links.js` reads them from boot), so a registry value can cost a
# link and never point at another host; the offline lookup that fills the
# registry for a host is its own tool (tools/enchor_lookup.py for Enchor).
# Adding a host is one entry here and that tool. The Chart column's value is
# the host's key and its filter list shows the label.
ENCHOR = 'https://enchor.us'
CHART_HOSTS = (
    ('enchor', {'label': 'Chorus Encore',
                'tip': 'This chart\u2019s page on Chorus Encore, where it is published',
                'url': f'{ENCHOR}/chart/{{id}}',
                'id': '^[a-f0-9]{32}$'}),
)
# The scores are a different kind of link (where the chart is played, not where
# it is), so the leaderboard is its own column and its own registry section.
LEADERBOARDS = 'https://leaderboards.clonehero.net'
VALUE_LABELS['Chart'] = {key: host['label'] for key, host in CHART_HOSTS}

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
DOC_PAGES = (('about.html', 'about'), ('changelog.html', 'changelog'), ('library.html', 'library'),
             ('methodology.html', 'methodology'))

# The line above the rendered Methodology.md, naming the upstream file as the
# source of truth. A module constant rather than a UI key: every UI key rides
# in the charts page's boot island, and nothing there reads this sentence.
METHODOLOGY_SOURCE = (
    f'Rendered at publish from [Methodology.md]({ENGINE_REPO}/blob/main/Methodology.md) in the '
    f'fretwork engine repository, which is the reference for the formula and its calibration '
    f'tables. The tables on this page are checked against the code that scored every chart here.')

# Left-to-right order on the page, which is not the spreadsheet's order: D is what
# the site is for, so it sits beside the song instead of past the right edge.
# Anything missing from this list keeps its spreadsheet position, at the end.
DISPLAY_ORDER = (
    'Song Title', 'Artist', 'Chart', 'Leaderboard', 'D', 'Pct', 'CalcTier', 'Level', 'Type',
    'DurationS', 'NoteCount', 'Charter', 'Release', 'Album', 'Year', 'Genre', 'Added', 'Copies',
    'Difficulty', 'RemapDiff', 'Official', 'Code', 'SongKey', 'NotesHash',
)

# Off by default, so a first visit is the ten columns worth reading rather than
# every column the spreadsheet has. Each is still one click away in the chooser,
# and search still looks inside Charter and Release while they are hidden:
#   Difficulty  the tag already in song.ini, not what this site calculates
#   RemapDiff   CalcTier says the same thing without a 0-6 ceiling
#   Official    the header has a chip for it, which is the useful form
#   Code        only means something to render.py
#   Added       the changelog page tells the same story with names and dates
#   Album       wraps, and the first view is already full at 390 px
#   Year        a filter on it works while hidden, which is how it is used
#   Genre       likewise; 212 spellings make it a filter, not a column to read
# Charter is deliberately NOT in this list: the people most likely to read this
# site are the ones who charted what is in it.
DEFAULT_HIDDEN = ('Album', 'Year', 'Genre', 'Difficulty', 'RemapDiff', 'Official', 'Code', 'Added', 'Copies',
                  'SongKey', 'NotesHash')

# Bump when DEFAULT_HIDDEN changes: a returning visitor's saved column set is
# replaced by the new default once, and their order and widths are kept.
PREFS_VERSION = 3


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
     f'Calc Tier is D on a log scale: one step for every {formula.LN_INC} rise in ln(D) above {formula.BASE_D}, '
     'so it keeps climbing past 10 for the hardest customs. Remap Tier is the same '
     'value binned into the 0\u20136 range the games use, calibrated per instrument. Both '
     'are computed from the Expert chart and then shown on every difficulty of that '
     'song, because song.ini carries only one rating per instrument. Percentile is '
     'where a chart\u2019s D sits among the charts on its sheet at the same level, so it '
     'moves as the library grows, counting a chart once however many packs carry it. '
     'How the library spreads over the tiers is on [the library page](library.html).'),
    ('What it does not know',
     'Strum, HOPO and tap state are discarded, so how a chart flows does not change '
     'its score. There is no pattern recognition \u2013 trills, anchoring and chord '
     'shapes all count simply as movement. Long quiet stretches pull the averages '
     'down. Drums and vocals are not scored at all.'),
    ('Where the numbers come from',
     f'Every chart here was parsed and scored by [fretwork]({ENGINE_REPO}), an '
     f'open-source project by [Staycation44]({CHANNEL}). This site runs that engine '
     f'unchanged and only displays the result. The full method, including the '
     f'calibration tables, is on the [methodology page](methodology.html).'),
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
     '\u201cHow it works\u201d on the charts page, and in full on the '
     '[methodology page](methodology.html).'),
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
     'names those charts already carry, and one graph per chart, drawn from its note density. Where a '
     'chart is published on Chorus Encore, or has a Clone Hero leaderboard, its graph links there; nothing '
     'is hosted here. It is not a place to get songs.'),
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
    'search':           'Search song, artist, album, charter or source...',
    'clear_one':        'Clear 1 filter',
    'clear_many':       'Clear {n} filters',
    'count':            '{shown} of {total} charts',
    'filter_tip':       'Filter this column',
    'sort_tip':         'Sort by this column',
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
    'methodology':      'Methodology',
    'changelog_tip':    'Every pack on the site, and when it was added',
    'changelog_intro':  'Every pack on the site, newest first, with the date it was added and where it is '
                        'published, and what changed on the site itself. The date in the charts page '
                        'header is when the numbers were last computed. Percentiles are relative to the '
                        'whole library on that day, so they shift a little with every update.',
    'changelog_totals': '{packs} packs, {songs} songs, {charts} charts',
    'pack_counts':      '{songs} songs, {charts} charts',
    'changelog_date_tip': 'Show the Expert charts added on this date',
    # the library page (section 20): what the library is, in numbers
    'library':          'The library',
    'library_tip':      'What the site covers: charts by instrument, level and tier, and the packs',
    'library_intro':    'What is on the site, in numbers: every count below comes from the same '
                        'table the charts page shows, so the two always agree. A chart is one '
                        'instrument at one level; a song has up to four levels of each instrument '
                        'it is charted for.',
    'library_charts':   'Charts',
    'library_charts_note': 'Charts as the table lists them; the smaller number under a count is the '
                        'distinct charts, counting a chart once however many packs carry it, which '
                        'is how the percentiles count.',
    'library_sheet':    'Sheet',
    'library_all':      'All levels',
    'library_songs':    'Songs',
    'library_tiers':    'Expert charts by tier',
    'library_tiers_note': 'Calc Tier is D on a log scale, anchored to the Expert chart; the bins and the '
                        'constants are in [the methodology](methodology.html#calctier-calibration).',
    'library_no_tier':  'No tier',
    'library_official': 'Official and custom',
    'library_official_note': 'At Expert. Official is a chart matched to a released game or DLC; the '
                        'rest are customs.',
    'library_hardest':  'The hardest',
    'library_hardest_note': 'The ten highest D at Expert on each sheet, as the table ranks them; the top '
                        'of the Guitar sheet is exercise charts, which is what the number says.',
    'library_packs':    'Packs',
    'library_packs_note': 'In the order of the registry; a name opens the table on the Expert charts '
                        'added with the pack, and a source is where the pack is published.',
    'library_pack':     'Pack',
    'library_source':   'Source',
    'library_mixed':    'Mixed',
    'library_share':    'Share',
    # a page per song (section 16): what a shared link previews with, and the button that copies one
    'share':            'Copy link',
    'share_tip':        'Copy a link to this chart that previews as the song when pasted',
    'share_copied':     'Link copied',
    'share_failed':     'Could not copy; the address bar has the link',
    'share_line':       '{level} {type}: {facts}',
    'share_d':          'D {d}',
    'share_tier':       'Calc Tier {tier}',
    'share_pct':        'at or above {pct}%',
    'share_open':       'Open on {site}',
    # The video is the origin of all of this, so it leads the explainer. Served
    # from the no-cookie host, and only requested if someone opens the panel -
    # the iframe is not in the page until then.
    'video_embed':      'https://www.youtube-nocookie.com/embed/emoWMpDJ4ls'
                        '?start=470&rel=0&enablejsapi=1',   # 7:50, where the method starts
    'video_title':      'Solving Guitar Hero\u2019s Difficulty Problem \u2013 Staycation44',
    'video_caption':    f'Solving Guitar Hero\u2019s Difficulty Problem \u2013 '
                        f'[Staycation44]({CHANNEL})',
    'explainer_more':   'Watch it on YouTube',
    'explainer_method': 'The full method',
    'method_url':       'methodology.html',

    # reporting a rating that looks wrong, from the chart's own graph
    'report':           'Report this rating',
    'report_url':       f'{FORK_REPO}/issues/new?template=rating.yml',

    # the graph heading's list of other folders carrying the same notes
    'copies_label':     'Same chart in:',
    'copies_tip':       'The same notes in another folder. Opens that copy\u2019s graph.',

    # the graph itself, drawn on a canvas from graph/<code>.json; the first
    # five mirror literals in functions/plot.py, which is upstream's
    'graph_d':          '~D',
    'graph_nps':        'Notes',
    'graph_vps':        'Variability',
    'graph_y':          'per second',
    'graph_x':          'Time (m:ss)',
    'graph_source':     '.{source} file',
    'graph_readout':    '{t}  ~D {d}  notes/s {nps}  changes/s {vps}',
    'graph_readout_part': '{letter} {d}',
    'graph_readout_many': '{t}  {parts}',
    'graph_legend':     '{title} - {artist}, {level} {type}',
    'graph_legend_part': '{level} {type}',    # compared charts of one song
    'graph_legend_level': '{level}',          # ... and one part
    'graph_hint':       'Hover or use the arrow keys to read values',
    'graph_alt':        'Difficulty graph of {song}: notes per second, fret changes per second and their geometric mean over time',
    # compare is pick-from-the-table alone: the table's search and filters are
    # the picker, and the song grid lists the song's other charts
    'compare_pick':     'Compare with a row',
    'compare_pick_tip': 'Overlay another chart\u2019s curve: click its row in the table (three charts at most)',
    'compare_picking':  'Choosing a chart to compare with {song}. Click a row, or press Esc to cancel.',
    'compare_cancel':   'Cancel',
    'compare_full':     'Three charts is the most the graph will hold',
    'compare_dup':      'That chart is already on the graph',
    'compare_remove':   'Remove {code} from the graph',
    'compare_missing':  'No graph for {code}',
    'song_compare':     'Compare all levels',
    'song_compare_tip': 'Overlay this instrument\u2019s levels on one graph: {levels}',
    'song_compare_off': 'Back to one chart',
    'song_on_graph':    'On the graph as {letter}: click to take it off',
    'song_add':         'Click to add this chart to the graph',
    'song_open':        'Click to open this chart',

    # the details pane under the table: the graph and every chart of the song
    'pane_label':       'Chart details',
    'pane_resize_tip':  'Drag to resize',
    'pane_collapse':    'Collapse the details',
    'pane_expand':      'Expand the details',
    'song_grid_label':  'Charts by instrument and level',
    'song_loading':     'Loading every sheet...',
    'song_not_found':   'No song has that key.',
    'song_tier':        'Tier {n}',
    'song_also_in':     'Also in',
    'song_no_level':    'No {level} chart',
    'save_png':         'Save as PNG',

    # where a chart's scores are, resolved offline; the chart hosts are CHART_HOSTS
    'links_pending':    'Loading links...',
    'leaderboard':      'Leaderboard',
    'leaderboard_tip':  'Scores for this song on the Clone Hero leaderboards',
    'leaderboard_url':  f'{LEADERBOARDS}/scores/{{hash}}',

    # the page CloudFront serves for a path that is not in the bucket
    'not_found_title':  'Page not found',
    'not_found':        'There is nothing at that address. Every chart is on one page.',
    'not_found_link':   'Go to the charts',

    # how someone asks for a pack to be scored
    'request':          'Request a song pack',
    'request_url':      f'{FORK_REPO}/issues/new?template=song-pack.yml',

    # row / graph interaction
    'row_tip':          'Click for the graph and every chart of this song',
    'pct_of':           'At or above {pct}% of {level} {sheet} charts',
    'loading':          'Loading {n} charts...',
    'load_failed':      'The chart data did not load.',
    'reload':           'Reload',
    'grid_label':       'Charts, sortable and filterable by column',
    'copy_code_tip':    'Copy this code',
    'close_tip':        'Close (Esc)',

    # column chooser
    'columns':          'Columns',
    'columns_tip':      'Choose which columns to show',
    'columns_reset':    'Reset columns',

    # the theme toggle: its label is the action it offers
    'theme_to_light':   'Switch to the light theme',
    'theme_to_dark':    'Switch to the dark theme',
}
