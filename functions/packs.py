"""
PACKS - the registry of every pack in the song library, and what changed on the site

packs.toml at the repo root names each pack (its top-level folder under the
search path, a display name, where it is published, the date it was added) and
carries a hand-written list of site changes. The site joins it to the cache at
page-build time: an Added column on every row and a changelog page. Counts are
computed from the cache and never stored, so the file cannot go stale.

Stdlib only (tomllib reads; the one writer here is append_pack, which builds
the block by hand and proves it with a re-read before renaming it into place),
no pandas and no web/ import, so the pipeline side stays importable without the
viewer. Folder is the key: the first path component of a song's path under the
library root. A library whose songs sit directly under the root has no pack
level; those songs are reported as loose rather than registered.

    python -m functions.packs [--header NAME] [--cache FILE] [--packs FILE]
"""

import argparse
import dataclasses
import datetime
import os
import pathlib
import unicodedata

from functions import cache as cache_mod
from functions import instruments, timestamp

PACKS_FILE = pathlib.Path(__file__).resolve().parent.parent / 'packs.toml'
PACK_KEYS = ('name', 'folder', 'source', 'added', 'notes')
CHANGE_KEYS = ('date', 'text')
DATE = '%Y-%m-%d'


class PacksError(ValueError):
    pass


@dataclasses.dataclass(frozen=True)
class Pack:
    name: str
    folder: str
    source: str
    added: datetime.date
    notes: str


@dataclasses.dataclass(frozen=True)
class Change:
    date: datetime.date
    text: str


@dataclasses.dataclass(frozen=True)
class Registry:
    packs: tuple
    changes: tuple
    path: pathlib.Path

    @property
    def by_folder(self):
        return {p.folder: p for p in self.packs}


@dataclasses.dataclass(frozen=True)
class Resolved:
    registry: Registry
    library_root: pathlib.Path
    added_by_code: dict        # code -> 'YYYY-MM-DD', registered folders only
    folder_by_code: dict       # code -> folder, every cached code
    songs_by_folder: dict      # folder -> songs in the cache
    unregistered: tuple        # folders with songs beneath them that no [[pack]] names
    missing: tuple             # registered folders with no songs in the cache
    loose: tuple               # top-level folders that are themselves a song folder

    @property
    def clean(self):
        return not (self.unregistered or self.missing or self.loose)


# --- reading -----------------------------------------------------------------

def _control(text):
    return any(unicodedata.category(ch) == 'Cc' for ch in text)


def _string(entry, key, where, default=None):
    if key not in entry:
        if default is None:
            raise PacksError(f'{where}: missing {key}')
        return default
    value = entry[key]
    if not isinstance(value, str):
        raise PacksError(f'{where}: {key} must be a string')
    if _control(value):
        raise PacksError(f'{where}: {key} contains a control character')
    return value


def _date(entry, key, where):
    if key not in entry:
        raise PacksError(f'{where}: missing {key}')
    value = entry[key]
    # a bare TOML date only: a quoted string or a local date-time is an error,
    # since the changelog groups by day and tomllib reads the latter as datetime
    if type(value) is not datetime.date:
        raise PacksError(f'{where}: {key} must be a bare date such as 2026-09-07, got {value!r}')
    return value


def load(path=PACKS_FILE):
    import tomllib
    path = pathlib.Path(path)
    with open(path, 'rb') as f:
        try:
            data = tomllib.load(f)
        except tomllib.TOMLDecodeError as exc:
            raise PacksError(f'{path}: {exc}') from exc
    packs, seen_folder, seen_name = [], set(), set()
    for i, entry in enumerate(data.get('pack', [])):
        where = f'[[pack]] {i + 1} ({entry.get("name", "?")})'
        unknown = set(entry) - set(PACK_KEYS)
        if unknown:
            raise PacksError(f'{where}: unknown key(s) {sorted(unknown)}')
        name = _string(entry, 'name', where)
        folder = _string(entry, 'folder', where)
        if not folder or folder in ('.', '..') or '/' in folder or '\\' in folder:
            raise PacksError(f'{where}: folder must be a single path component, got {folder!r}')
        if folder in seen_folder:
            raise PacksError(f'{where}: folder {folder!r} is listed twice')
        if name in seen_name:
            raise PacksError(f'{where}: name {name!r} is listed twice')
        seen_folder.add(folder)
        seen_name.add(name)
        source = _string(entry, 'source', where, default='')
        if source and not source.startswith(('http://', 'https://')):
            raise PacksError(f'{where}: source must be an http(s) URL or empty')
        packs.append(Pack(name, folder, source, _date(entry, 'added', where),
                          _string(entry, 'notes', where, default='')))
    changes = []
    for i, entry in enumerate(data.get('change', [])):
        where = f'[[change]] {i + 1}'
        unknown = set(entry) - set(CHANGE_KEYS)
        if unknown:
            raise PacksError(f'{where}: unknown key(s) {sorted(unknown)}')
        changes.append(Change(_date(entry, 'date', where), _string(entry, 'text', where)))
    return Registry(tuple(packs), tuple(changes), path)


# --- the join -----------------------------------------------------------------

# The library root the cache was built from. An absolute search_path is used
# as stored; a relative one (the usual case) is recovered from the songs: the
# common ancestor of every song_path, walked up until its name is the last
# component of the stored path, so publish from any directory finds the same
# root. A stored '.' has no usable name and is used as the commonpath, which
# misreads a one-pack library; build with a named path instead.
def library_root(cache):
    stored = str(cache.get('search_path') or '')
    if os.path.isabs(stored):
        return pathlib.Path(stored)
    paths = list(cache['songs'])
    if not paths:
        raise PacksError('the cache holds no songs')
    common = pathlib.Path(os.path.commonpath(paths))
    if all(pathlib.Path(p) == common for p in paths):
        common = common.parent          # a single song: commonpath is the song itself
    name = pathlib.Path(os.path.normpath(stored)).name
    if not name:
        print(f'  [warn] packs: search_path {stored!r} has no folder name; using {common}')
        return common
    for candidate in (common, *common.parents):
        if candidate.name == name:
            return candidate
    raise PacksError(f'no directory named {name!r} (the stored search_path) above {common}')


def folder_of_songs(cache, root):
    out = {}
    for song_path in cache['songs']:
        try:
            parts = pathlib.Path(song_path).relative_to(root).parts
        except ValueError as exc:
            raise PacksError(f'{song_path} is not under {root}') from exc
        out[song_path] = parts[0]
    return out


def scored_codes(cache):
    return [code for song in cache['songs'].values()
            for inst, levels in song['codes'].items() if inst in instruments.SCORED_INSTRUMENTS
            for code in levels.values()]


def resolve(cache, registry):
    root = library_root(cache)
    folders = folder_of_songs(cache, root)
    by_folder = registry.by_folder
    songs_by_folder, loose, unregistered = {}, set(), set()
    added_by_code, folder_by_code = {}, {}
    for song_path, song in cache['songs'].items():
        folder = folders[song_path]
        depth = len(pathlib.Path(song_path).relative_to(root).parts)
        if depth == 1:
            loose.add(folder)
        else:
            songs_by_folder[folder] = songs_by_folder.get(folder, 0) + 1
            if folder not in by_folder:
                unregistered.add(folder)
        added = by_folder[folder].added.strftime(DATE) if folder in by_folder and depth > 1 else None
        for levels in song['codes'].values():
            for code in levels.values():
                folder_by_code[code] = folder
                if added:
                    added_by_code[code] = added
    missing = [p.folder for p in registry.packs if songs_by_folder.get(p.folder, 0) == 0]
    return Resolved(registry, root, added_by_code, folder_by_code, songs_by_folder,
                    tuple(sorted(unregistered)), tuple(sorted(missing)), tuple(sorted(loose)))


def report(resolved):
    lines = []
    if resolved.missing:
        lines.append(f'packs: {len(resolved.missing)} registered folder(s) with no songs in this cache: '
                     + ', '.join(resolved.missing))
    if resolved.loose:
        lines.append(f'packs: {len(resolved.loose)} loose song folder(s) directly under the library root '
                     f'(move these into a pack folder): ' + ', '.join(resolved.loose[:5])
                     + (' ...' if len(resolved.loose) > 5 else ''))
    if resolved.unregistered:
        lines.append(f'packs: {len(resolved.unregistered)} folder(s) not registered in {resolved.registry.path.name}: '
                     + ', '.join(resolved.unregistered))
    return '\n'.join(lines)


# {folder: (songs, charts)} for every registered folder; charts counts the codes given.
def tally(resolved, codes):
    charts = {}
    for code in codes:
        folder = resolved.folder_by_code.get(code)
        if folder is not None:
            charts[folder] = charts.get(folder, 0) + 1
    return {p.folder: (resolved.songs_by_folder.get(p.folder, 0), charts.get(p.folder, 0))
            for p in resolved.registry.packs}


# --- writing -----------------------------------------------------------------

# A complete TOML basic string: with control characters refused, the only
# characters TOML requires escaped are the backslash and the quotation mark, and
# the file is UTF-8, so accents and emoji go in raw (json.dumps would write
# astral characters as surrogate pairs, which tomllib refuses).
def format_string(value):
    if _control(value):
        raise PacksError(f'{value!r} contains a control character')
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'


# Appends one [[pack]] block, proving the result with load() on a temporary
# copy before renaming it over the file; packs.toml is never left broken.
def append_pack(path, pack):
    path = pathlib.Path(path)
    block = '\n[[pack]]\n' + ''.join(
        f'{key} = {value}\n' for key, value in (
            ('name', format_string(pack.name)), ('folder', format_string(pack.folder)),
            ('source', format_string(pack.source)), ('added', pack.added.strftime(DATE)),
            ('notes', format_string(pack.notes))))
    text = path.read_text(encoding='utf-8')
    if text and not text.endswith('\n'):
        text += '\n'
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(text + block, encoding='utf-8')
    try:
        load(tmp)
    except PacksError as exc:
        tmp.unlink(missing_ok=True)
        raise PacksError(f'refusing to append {pack.name!r}: {exc}') from exc
    os.replace(tmp, path)


# --- the terminal table -----------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description='Every registered pack with its songs and charts from the cache.')
    ap.add_argument('--header', default=None)
    ap.add_argument('--cache', default=None)
    ap.add_argument('--packs', default=str(PACKS_FILE))
    args = ap.parse_args()
    import config
    header = args.header or config.HEADER
    cache_path = args.cache or timestamp.latest_output('cache', header, ext='pkl')
    cache = cache_mod.load(cache_path)
    registry = load(args.packs)
    resolved = resolve(cache, registry)
    counts = tally(resolved, scored_codes(cache))
    width = max(len(p.folder) for p in registry.packs) if registry.packs else 6
    print(f'\n{registry.path} against {cache_path}\n')
    print(f'    {"folder":<{width}}  {"songs":>6}  {"charts":>7}  added')
    for p in registry.packs:
        songs, charts = counts[p.folder]
        print(f'    {p.folder:<{width}}  {songs:>6}  {charts:>7}  {p.added.strftime(DATE)}')
    print(f'\n    {len(registry.packs)} packs, {sum(s for s, _ in counts.values())} songs, '
          f'{sum(c for _, c in counts.values())} charts (cache, 5-fret)')
    print(report(resolved) or 'unregistered: none')
    print()


if __name__ == '__main__':
    main()
