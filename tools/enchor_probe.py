"""
ENCHOR_PROBE - does Chorus Encore's chartHash filter take the MD5 of the notes file?

A one-off experiment behind tools/enchor_lookup.py. The advanced search
(POST https://api.enchor.us/search/advanced) takes a `chartHash` filter of
comma-separated MD5s, but the response's `chartHash` field is a blake3 of the
chart and nothing in the client sources says which bytes the filter's MD5 is
over. The only reading that makes it useful offline (a chart-only library has
no audio, so Enchor's folder `md5` can never be recomputed here) is "MD5 of
the raw notes.chart or notes.mid", and that is what this asks: one request per
folder with that hash, one with every hash comma-joined, one batch of --batch
hashes (the real ones padded with the last, repeated) to see what length is
accepted, and one echo of a hit's blake3 chartHash to see whether that filters
too. Every request, its headers and its response go to --out.

    python tools/enchor_probe.py FOLDER [FOLDER ...] [--batch 100] [--out caches/enchor_probe_<date>.json]

RESULT (2026-09-11, caches/enchor_probe_2026-09-11.json): NO. Five folders
(two .chart and one .mid from CSC Quarterly Pack 4Q2025, one S Hero .chart,
one Guitar Hero III .mid as the control) each returned found 0 for the
notes-file MD5, singly and in the comma-joined batch; a 100-hash batch was
accepted (status 201, found 0), so the length is not the problem. No hit was
returned, so the blake3 echo could not be sent. Headers: x-ratelimit-limit 50,
reset an epoch timestamp about 60 s on. A follow-up by name and artist (the
filters take {"value", "exact", "exclude"} objects, not bare strings, which
return 400) found all three songs tried, including the official Guitar Hero
III rip (charter Neversoft), and Enchor's notesData.noteCounts guitar/expert
count equalled the cache's Expert Lead timestamp count on every hit (1929,
739, 395), so the count is a chord-once count like fretwork's NoteCount.
enchor_lookup.py therefore joins on metadata (via "meta"): exact name and
artist, then the Expert Lead note count, then the charter.
"""

import argparse
import datetime
import hashlib
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import config  # noqa: E402
from tools import links_common as lc  # noqa: E402

SEARCH = lc.ENCHOR_API + '/search/advanced'


def notes_file(folder):
    folder = pathlib.Path(folder)
    for name in ('notes.chart', 'notes.mid'):
        for f in folder.iterdir():
            if f.name.lower() == name:
                return f
    return None


def body(hashes):
    return {'chartHash': ','.join(hashes), 'instrument': None, 'difficulty': None, 'page': 1, 'per_page': 250}


def expert_count(song):
    """Enchor's guitar/expert count from a hit, or None."""
    for nc in ((song.get('notesData') or {}).get('noteCounts') or []):
        if nc.get('instrument') == 'guitar' and nc.get('difficulty') == 'expert':
            return nc.get('count')
    return None


def cache_count(folder):
    """The cache's Expert Lead timestamp count for the folder, from the newest cache of --header, or None."""
    try:
        from functions import cache as cache_mod, timestamp
        path = timestamp.latest_output('cache', config.HEADER, ext='pkl')
        c = cache_mod.load(path)
        song = c['songs'].get(str(pathlib.Path(folder).resolve()))
        if not song:
            return None
        return len(song['instruments']['guitar']['expert']['notes']['time_ms'])
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[1])
    ap.add_argument('folders', nargs='+')
    ap.add_argument('--batch', type=int, default=100)
    ap.add_argument('--header', default=None, help='cache header for the note-count column (default config.HEADER)')
    ap.add_argument('--out', default=None)
    args = ap.parse_args()
    if args.header:
        config.HEADER = args.header
    today = datetime.date.today().isoformat()
    out = pathlib.Path(args.out or pathlib.Path(config.OUTPUT_DIRS['cache']) / f'enchor_probe_{today}.json')
    pacer = lc.Pacer(48)
    log = []

    def ask(label, payload):
        status, headers, data = lc.call(pacer, lc.post_json, SEARCH, payload)
        log.append({'label': label, 'request': payload, 'status': status, 'headers': headers, 'response': data})
        return status, headers, data

    rows = []
    for folder in args.folders:
        f = notes_file(folder)
        if f is None:
            print(f'{folder}: no notes file', file=sys.stderr)
            continue
        md5 = hashlib.md5(f.read_bytes()).hexdigest()
        rows.append({'folder': folder, 'format': f.suffix[1:], 'chart_md5': md5, 'cache_count': cache_count(folder)})

    first_headers = None
    for row in rows:
        status, headers, data = ask(f'single {row["folder"]}', body([row['chart_md5']]))
        first_headers = first_headers or headers
        hits = (data or {}).get('data', []) if status < 300 else []
        row['status'] = status
        row['found'] = (data or {}).get('found') if status < 300 else None
        row['hits'] = [{'md5': h.get('md5'), 'chartId': h.get('chartId'), 'name': h.get('name'), 'charter': h.get('charter'),
                        'chartHash': h.get('chartHash'), 'enchor_count': expert_count(h)} for h in hits]

    print(f'{"folder":60} {"fmt":5} {"chart_md5":32} {"found":>5}  hits')
    for row in rows:
        print(f'{pathlib.Path(row["folder"]).name[:60]:60} {row["format"]:5} {row["chart_md5"]} {str(row["found"]):>5}  '
              + '; '.join(f'md5 {h["md5"]} chartId {h["chartId"]} {h["name"]!r} by {h["charter"]!r} '
                          f'enchor guitar/expert {h["enchor_count"]} cache {row["cache_count"]}' for h in row['hits']))

    all_hashes = [r['chart_md5'] for r in rows]
    status, headers, data = ask('batch of all', body(all_hashes))
    got = {h.get('md5') for h in (data or {}).get('data', [])} if status < 300 else set()
    singles = {h['md5'] for r in rows for h in r['hits']}
    print(f'\nbatch of {len(all_hashes)}: status {status}, found {(data or {}).get("found") if status < 300 else None}, '
          f'same hits as the singles: {got == singles}')

    padded = (all_hashes + [all_hashes[-1]] * args.batch)[:args.batch]
    status, headers, data = ask(f'batch of {args.batch}', body(padded))
    print(f'batch of {args.batch} hashes: status {status}' +
          (f', found {(data or {}).get("found")}' if status < 300 else f', refused: {str(data)[:200]}'))

    echo = next((h['chartHash'] for r in rows for h in r['hits'] if h.get('chartHash')), None)
    if echo:
        status, headers, data = ask('blake3 echo', body([echo]))
        n = (data or {}).get('found') if status < 300 else None
        print(f'blake3 chartHash echo: status {status}, found {n} ({"filters" if n else "does not filter"})')

    if first_headers:
        h = {k.lower(): v for k, v in first_headers.items()}
        print(f'\nheaders: x-ratelimit-limit {h.get("x-ratelimit-limit")}, remaining {h.get("x-ratelimit-remaining")}, '
              f'reset {h.get("x-ratelimit-reset")}, date {h.get("date")}')
    print(f'requests made: {pacer.requests}, waited {pacer.waited:.1f} s')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({'date': today, 'rows': rows, 'requests': log}, indent=1), encoding='utf-8')
    print(f'recorded in {out}')


if __name__ == '__main__':
    main()
