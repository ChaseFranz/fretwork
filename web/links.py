"""
LINKS - the published form of the offline link registry

The offline lookups (tools/enchor_lookup.py, tools/leaderboards_lookup.py)
write caches/<header>_links.json, keyed by SongKey, one section per host
(labels.CHART_HOSTS: "enchor" today) plus "leaderboard", with everything they
learned. Page-build turns it into one small immutable file,
data/links.<hash8>.json, holding only what the page shows: per song, each
host's chart id and, when the match was sure, the leaderboard songHash. A
value outside its host's character class is dropped here, so a registry
edited by hand costs a link and never a different host. No registry means no
file and a null boot key.

The same links are two page-built columns: `Chart`, the key of the first host
in CHART_HOSTS order that has the song (null when none), so the table shows
where a chart is published and filters by host, and `Leaderboard`, a bit. The
rows carry the host, never the id; the page draws each arrow from the file. A
column exists only when some song has that kind of link.
"""

import hashlib
import json
import pathlib
import re

import config
from functions import labels

VERSION = 1
SLUG = 'links'                      # reserved under data/; a sheet that slugs to it fails publish
SONG_HASH = re.compile(r'[A-Za-z0-9_-]{40,50}')
HOST_ID = {key: re.compile(host['id']) for key, host in labels.CHART_HOSTS}
CHART_COL, LB_COL = 'Chart', 'Leaderboard'


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
    """{song_key: {<host>: id, 'lb': songHash}} with only the keys that are known and sure.

    A host's registry entry carries the id under 'id', or under 'md5' for
    Enchor, whose id is its folder md5 (the key of enchor.us/chart/<md5>).
    """
    out = {}
    for host, pattern in HOST_ID.items():
        for key, entry in (registry.get(host) or {}).items():
            value = (entry or {}).get('id', (entry or {}).get('md5'))
            if isinstance(value, str) and pattern.fullmatch(value):
                out.setdefault(key, {})[host] = value
    for key, entry in (registry.get('leaderboard') or {}).items():
        entry = entry or {}
        song_hash = entry.get('songHash')
        sure = entry.get('sure') is True or (entry.get('twins') or 0) > 1
        if sure and isinstance(song_hash, str) and SONG_HASH.fullmatch(song_hash):
            out.setdefault(key, {})['lb'] = song_hash
    return dict(sorted(out.items()))


def link_columns(songs):
    """The page-built link columns, for the kinds any song has.

    {'Chart': {song_key: host}} with each song's first host in CHART_HOSTS
    order, and {'Leaderboard': {song_key}}; a kind no song has is absent.
    """
    out = {}
    hosts = [key for key, _ in labels.CHART_HOSTS]
    chart = {k: next(h for h in hosts if h in v) for k, v in songs.items() if any(h in v for h in hosts)}
    if chart:
        out[CHART_COL] = chart
    lb = {k for k, v in songs.items() if 'lb' in v}
    if lb:
        out[LB_COL] = lb
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
