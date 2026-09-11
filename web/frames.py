"""
FRAMES - reads a metrics .xlsx into JSON-safe rows

The only module here that imports pandas.
"""

import json
import pathlib

import pandas as pd

from functions import timestamp

PCT_COL = 'Pct'        # the column added to every sheet
PCT_OF = 'D'           # what is ranked
PCT_WITHIN = 'Level'   # the pool a row is ranked within, per sheet


def load_frames(header, xlsx_path=None):
    if xlsx_path is None:
        xlsx_path = timestamp.latest_output('metrics', header, ext='xlsx')
    xlsx_path = pathlib.Path(xlsx_path)
    return xlsx_path, pd.read_excel(xlsx_path, sheet_name=None)


# to_json is the round trip that turns NaN into null and numpy scalars into
# plain numbers; df.values.tolist() would emit bare NaN and invalid JSON.
# Every code the table can click, in sheet order, without duplicates.
def codes_in(frames):
    codes = [str(c) for df in frames.values() if 'Code' in df.columns
             for c in df['Code'].dropna()]
    return list(dict.fromkeys(codes))


# Share of the sheet's charts at the same level whose D is at or below this
# row's, as a whole number 0-100. Ties take the top rank of their group, so
# equal D means equal percentile, and the division floors, so a value never
# overstates. rank() is float64; the values are whole numbers, so the floor
# division is exact.
# distinct: identity columns; when given, each distinct (identity, level)
# counts once, so copies of one chart share a value and are not counted twice.
# A row with a null anywhere in its identity ranks as its own chart. Section 10
# passes ['Type', 'NotesHash']; a per-song key would merge a song's Lead,
# Rhythm and Co-op rows. Needs a unique index (read_excel gives one).
def percentile(df, distinct=None):
    if distinct is None:
        pool, has = df, None
    else:
        keys = [*distinct, PCT_WITHIN]
        has = df[distinct].notna().all(axis=1)
        pool = pd.concat([df[~has], df[has].drop_duplicates(subset=keys)])
    grouped = pool.groupby(PCT_WITHIN)[PCT_OF]
    pct = (grouped.rank(method='max') * 100 // grouped.transform('count')).astype('Int64')
    if distinct is None:
        return pct
    kept = pool[has.reindex(pool.index)]
    lookup = kept[keys].assign(**{PCT_COL: pct[kept.index]})
    merged = df[keys].merge(lookup, on=keys, how='left')[PCT_COL].set_axis(df.index)
    return merged.where(has, pct.reindex(df.index))


# A sheet without D or Level is left alone. A sheet missing any identity column
# gets the plain pool: a partial key would collapse charts, and an older
# spreadsheet is still worth the percentile it had before section 10.
def add_percentiles(frames, distinct=None):
    for df in frames.values():
        if PCT_OF not in df.columns or PCT_WITHIN not in df.columns:
            continue
        use = distinct if distinct and all(c in df.columns for c in distinct) else None
        df[PCT_COL] = percentile(df, use)
    return frames


def frames_payload(frames):
    return {
        name: {
            'columns': list(df.columns),
            'rows': json.loads(df.to_json(orient='values')),
        }
        for name, df in frames.items()
    }
