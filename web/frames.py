"""
FRAMES - reads a metrics .xlsx into JSON-safe rows

The only module here that imports pandas.
"""

import hashlib
import json
import pathlib
import re

import pandas as pd

from functions import timestamp

PCT_COL = 'Pct'        # the column added to every sheet
PCT_OF = 'D'           # what is ranked
PCT_WITHIN = 'Level'   # the pool a row is ranked within, per sheet
COPY_KEY = ['Type', 'NotesHash']   # a chart's identity within a level
COPIES_COL = 'Copies'

# The two hash columns are read as text: read_excel infers per column, and a
# one-row sheet whose hash happens to be all digits would come back as an
# integer with its leading zeros gone. A name the sheet lacks is ignored.
HASH_COLS = {'SongKey': str, 'NotesHash': str}


def load_frames(header, xlsx_path=None):
    if xlsx_path is None:
        xlsx_path = timestamp.latest_output('metrics', header, ext='xlsx')
    xlsx_path = pathlib.Path(xlsx_path)
    return xlsx_path, pd.read_excel(xlsx_path, sheet_name=None, dtype=HASH_COLS)


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


# The Copies column: how many rows on this sheet carry exactly these notes at
# this level and part, this one included. Within one song, Hard often equals
# Expert byte for byte and a Lead chart its own Rhythm; neither is a copy a
# reader means, which is why the key holds Type and Level. groupby's default
# dropna=True is load-bearing: a row with no hash gets NaN, then 1, rather
# than the count of every hashless row. An older spreadsheet without the hash
# is left alone: no copies known, no column.
def add_copies(df):
    if 'NotesHash' not in df.columns or not all(c in df.columns for c in [*COPY_KEY, PCT_WITHIN, 'Code']):
        return df
    df = df.copy()
    size = df.groupby([*COPY_KEY, PCT_WITHIN])['Code'].transform('size')
    df[COPIES_COL] = size.fillna(1).astype(int)
    return df


# The Added column: each row's pack date, joined by Code at page-build time.
# Appended after the xlsx columns; the page-build columns of sections 10 and 02
# follow it. A code outside the registry maps to NaN, which to_json makes null.
def with_added(frames, added_by_code):
    return {name: df.assign(Added=df['Code'].astype(str).map(added_by_code)) if 'Code' in df.columns else df
            for name, df in frames.items()}


# The rows leave the page: one hashed JSON file per sheet under data/, holding
# exactly what frames_payload emits, and a manifest the page reads in their
# place. The '<' escape the island needs is not applied here: a file parsed by
# response.json() never enters an HTML or script context.
def slug(name):
    out = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    if not out:
        raise ValueError(f'sheet name {name!r} gives an empty file name')
    return out


# The link columns (section 14): True where the song has that link, joined by
# SongKey at page-build time, after Pct. `link_columns` is links.link_columns()'s
# answer, {column: set of keys}; a sheet without SongKey gets none.
def with_links(frames, link_columns):
    if not link_columns:
        return frames
    out = {}
    for name, df in frames.items():
        if 'SongKey' in df.columns:
            df = df.copy()
            for col, keys in link_columns.items():
                df[col] = df['SongKey'].isin(keys).astype(bool)
        out[name] = df
    return out


def sheet_files(frames):
    payload = frames_payload(frames)
    files, manifest, seen = {}, {}, {}
    for name, sheet in payload.items():
        s = slug(name)
        if s in seen:
            raise ValueError(f'sheets {seen[s]!r} and {name!r} both slug to {s!r}')
        seen[s] = name
        data = json.dumps(sheet, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
        file = f'data/{s}.{hashlib.sha1(data).hexdigest()[:8]}.json'
        files[file] = data
        manifest[name] = {'file': file, 'rows': len(sheet['rows']), 'columns': sheet['columns']}
    return files, manifest


def frames_payload(frames):
    return {
        name: {
            'columns': list(df.columns),
            'rows': json.loads(df.to_json(orient='values')),
        }
        for name, df in frames.items()
    }
