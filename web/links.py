"""
LINKS - the published form of the offline link registry

tools/enchor_lookup.py and tools/leaderboards_lookup.py write
caches/<header>_links.json, keyed by SongKey, with everything they learned.
Page-build turns it into one small immutable file, data/links.<hash8>.json,
holding only what the page shows: per song, the Enchor folder md5 and, when
the match was sure, the leaderboard songHash. Values outside their character
class are dropped here, so a registry edited by hand costs a link and never a
different host. No registry means no file and a null boot key.

The same two links are page-built boolean columns (LINK_COLS: Enchor,
Leaderboard), one bit per row rather than the hash, so the table can show and
filter on whether a chart is published while the rows stay small; the page
draws each arrow from the file. A column exists only when some song has that
link, so a library with no leaderboard answers has no Scores column.
"""

import hashlib
import json
import pathlib
import re

import config

VERSION = 1
SLUG = 'links'                      # reserved under data/; a sheet that slugs to it fails publish
MD5 = re.compile(r'[a-f0-9]{32}')
SONG_HASH = re.compile(r'[A-Za-z0-9_-]{40,50}')
LINK_COLS = (('Enchor', 'enchor'), ('Leaderboard', 'lb'))   # (page column, key in the file)


def registry_path(header):
    return pathlib.Path(config.OUTPUT_DIRS['cache']) / f'{header}_links.json'


def load_registry(header, path=None):
    """The registry dict, or None when there is none for this header."""
    path = pathlib.Path(path) if path else registry_path(header)
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('v') != VERSION:
        raise ValueError(f'{path}: registry version {data.get("v")!r}, expected {VERSION}')
    return data


def songs_with_links(registry):
    """{song_key: {'enchor': md5, 'lb': songHash}} with only the keys that are known and sure."""
    out = {}
    for key, entry in (registry.get('enchor') or {}).items():
        md5 = (entry or {}).get('md5')
        if isinstance(md5, str) and MD5.fullmatch(md5):
            out.setdefault(key, {})['enchor'] = md5
    for key, entry in (registry.get('leaderboard') or {}).items():
        entry = entry or {}
        song_hash = entry.get('songHash')
        sure = entry.get('sure') is True or (entry.get('twins') or 0) > 1
        if sure and isinstance(song_hash, str) and SONG_HASH.fullmatch(song_hash):
            out.setdefault(key, {})['lb'] = song_hash
    return dict(sorted(out.items()))


def link_columns(songs):
    """{column: set of song keys that have it}, for the LINK_COLS any song has."""
    out = {}
    for col, key in LINK_COLS:
        keys = {k for k, v in songs.items() if key in v}
        if keys:
            out[col] = keys
    return out


def publish_songs(songs):
    """The file's bytes for songs_with_links()'s answer, or None when no song has a link."""
    if not songs:
        return None
    return json.dumps({'v': VERSION, 'songs': songs}, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


def published(registry):
    """The file's bytes, or None when no song has a link."""
    return publish_songs(songs_with_links(registry) if registry else {})


def file_name(data):
    return f'data/{SLUG}.{hashlib.sha1(data).hexdigest()[:8]}.json'
