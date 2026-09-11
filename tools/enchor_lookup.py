"""
ENCHOR_LOOKUP - resolve each song's Chorus Encore chart page, offline, into the link registry

Walks the newest cache for a header, asks api.enchor.us once per song not yet
answered, and records the answer in caches/<header>_links.json under
"enchor", keyed by SongKey: the Enchor folder md5 (the key of
https://enchor.us/chart/<md5>), the chartId, how many hits qualified, and the
date. A null md5 means asked and not found, and is skipped next time unless
--recheck; --recheck-all re-asks everything.

The join is metadata (via "meta"), because the probe (tools/enchor_probe.py)
showed Enchor's chartHash filter is not the notes file's MD5: an exact name
and artist search, then the hits whose guitar/expert note count equals the
cache's Expert Lead timestamp count (the probe showed the two counts agree),
then the charter; among several qualifying hits the largest chartId (the
newest upload) is recorded, so two runs give the same link. A song without an
Expert guitar chart matches on the charter alone, and only when that is
unambiguous: a wrong link sends someone to a different chart.

    python tools/enchor_lookup.py [--header NAME] [--cache FILE.pkl] [--links FILE.json]
                                  [--per-minute 48] [--recheck | --recheck-all] [--limit N] [--dry-run]

48 requests a minute (the service allows 50), the registry saved every 25
songs, so an interruption loses under a minute. Stdlib only.
"""

import argparse
import collections
import datetime
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import config  # noqa: E402
from functions import cache as cache_mod, timestamp  # noqa: E402
from tools import links_common as lc  # noqa: E402

SEARCH = lc.ENCHOR_API + '/search/advanced'
SAVE_EVERY = 25


def request_body(name, artist):
    return {'name': {'value': name, 'exact': True, 'exclude': False},
            'artist': {'value': artist, 'exact': True, 'exclude': False},
            'instrument': None, 'difficulty': None, 'page': 1, 'per_page': 50}


def expert_count(hit):
    for nc in ((hit.get('notesData') or {}).get('noteCounts') or []):
        if nc.get('instrument') == 'guitar' and nc.get('difficulty') == 'expert':
            return nc.get('count')
    return None


def choose(hits, charter, count):
    """The hit to record from an exact name-and-artist pool, and how many qualified.

    With a count (the song has an Expert guitar chart) a hit must carry that
    count; among those the charter decides when it can, else the newest
    upload. Without a count the charter alone must single one hit out.
    """
    pool = [h for h in hits if lc.MD5.match(str(h.get('md5') or ''))]
    if count is not None:
        pool = [h for h in pool if expert_count(h) == count]
        if not pool:
            return None, 0
        same = [h for h in pool if lc.norm(h.get('charter')) == lc.norm(charter)]
        chosen = same or pool
        return max(chosen, key=lambda h: h.get('chartId') or 0), len(pool)
    same = [h for h in pool if lc.norm(h.get('charter')) == lc.norm(charter)]
    if len(same) == 1:
        return same[0], 1
    return None, len(same)


def song_rows(cache):
    """(song_key, song) for each song with a key, first path per key first."""
    seen = set()
    for path in sorted(cache['songs']):
        song = cache['songs'][path]
        key = song.get('song_key')
        if not key or key in seen:
            continue
        seen.add(key)
        yield key, song


def top_folder(cache, song):
    try:
        return pathlib.Path(song['song_path']).relative_to(pathlib.Path(cache['search_path']).resolve()).parts[0]
    except (ValueError, KeyError, IndexError):
        return '?'


def run(cache, registry, pacer, post=lc.post_json, recheck=False, recheck_all=False, limit=None, dry_run=False,
        today=None, save=lambda: None, log=print):
    today = today or datetime.date.today().isoformat()
    known = registry['enchor']
    stats = collections.Counter()
    by_folder, by_release = collections.defaultdict(lambda: [0, 0]), collections.defaultdict(lambda: [0, 0])
    asked = 0
    for key, song in song_rows(cache):
        stats['seen'] += 1
        had = known.get(key)
        if had is not None and not recheck_all and not (recheck and had.get('md5') is None):
            stats['known'] += 1
            continue
        if limit is not None and asked >= limit:
            stats['left'] += 1
            continue
        meta = song['meta']
        guitar = song['instruments'].get('guitar', {}).get('expert')
        count = len(guitar['notes']['time_ms']) if guitar else None
        body = request_body(meta.get('Name') or '', meta.get('Artist') or '')
        if dry_run:
            log(f'would ask: {meta.get("Name")!r} by {meta.get("Artist")!r} (count {count}, charter {meta.get("Charter")!r})')
            asked += 1
            continue
        asked += 1
        stats['asked'] += 1
        try:
            status, headers, data = lc.call(pacer, post, SEARCH, body)
        except lc.RateLimited as err:
            log(f'stopping: {err}')
            break
        if status >= 300 or not isinstance(data, dict):
            stats['errors'] += 1
            log(f'  {meta.get("Name")!r}: status {status}')
            continue
        hit, hits = choose(data.get('data') or [], meta.get('Charter'), count)
        entry = {'chart_md5': song.get('chart_md5'), 'md5': hit['md5'] if hit else None, 'via': 'meta', 'checked': today,
                 'candidates': int(data.get('found') or 0), 'hits': hits}
        if hit:
            entry['chartId'] = hit.get('chartId')
            stats['found'] += 1
        else:
            stats['missed'] += 1
        known[key] = entry
        folder, release = top_folder(cache, song), meta.get('Release') or '?'
        by_folder[folder][0] += bool(hit); by_folder[folder][1] += 1
        by_release[release][0] += bool(hit); by_release[release][1] += 1
        if stats['asked'] % SAVE_EVERY == 0:
            save()
    save()
    return stats, by_folder, by_release


def summary(stats, by_folder, by_release, pacer, path, log=print):
    log(f"\nEnchor lookup: {stats['seen']} songs, {stats['known']} already known, {stats['asked']} asked, "
        f"{stats['found']} found, {stats['missed']} not found, {stats['errors']} errors, {stats['left']} left by --limit")
    log(f"requests {pacer.requests}, 429s {pacer.rate_limited}, waited {pacer.waited:.0f} s")
    for title, table in (('by top-level folder', by_folder), ('by Release', by_release)):
        if table:
            log(f'hit rate {title}:')
            for name, (hits, n) in sorted(table.items(), key=lambda kv: -kv[1][1]):
                log(f'    {name[:50]:50} {hits:5}/{n:<5} {100 * hits / n:5.1f}%')
    log(f'registry: {path}')


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[1])
    ap.add_argument('--header', default=None)
    ap.add_argument('--cache', default=None)
    ap.add_argument('--links', default=None, help='registry file (default caches/<header>_links.json)')
    ap.add_argument('--per-minute', type=int, default=48)
    g = ap.add_mutually_exclusive_group()
    g.add_argument('--recheck', action='store_true', help='re-ask the songs recorded as not found')
    g.add_argument('--recheck-all', action='store_true', help='re-ask every song')
    ap.add_argument('--limit', type=int, default=None, help='ask at most this many songs this run')
    ap.add_argument('--dry-run', action='store_true', help='print the requests that would be made and make none')
    args = ap.parse_args()

    header = args.header or config.HEADER
    cache_path = args.cache or timestamp.latest_output('cache', header, ext='pkl')
    cache = cache_mod.load(cache_path)
    path = pathlib.Path(args.links) if args.links else lc.registry_path(header)
    registry = lc.load_registry(path)
    pacer = lc.Pacer(args.per_minute)
    print(f'cache {cache_path}\nregistry {path} ({len(registry["enchor"])} enchor entries)')
    stats, by_folder, by_release = run(cache, registry, pacer, recheck=args.recheck, recheck_all=args.recheck_all,
                                       limit=args.limit, dry_run=args.dry_run,
                                       save=lambda: None if args.dry_run else lc.save_registry(path, registry))
    summary(stats, by_folder, by_release, pacer, path)


if __name__ == '__main__':
    main()
