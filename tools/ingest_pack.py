#!/usr/bin/env python3
"""
INGEST_PACK - Put a song pack into the library, record it, rebuild, and say what changed.

One command takes a pack from wherever it is (a .zip, .rar or .7z on disk, a
folder, or a direct download URL), puts a chart-only copy under
<library>/<name>/, records it in packs.toml through functions/packs.py, runs
build.py and analyze.py for the header, and prints the change against the
previous cache. It stops at analyze: publish and deploy are the two commands it
prints at the end.

    python tools/ingest_pack.py SOURCE --name NAME [--source URL] [--header Local]
                                [--library songs] [--packs packs.toml] [--notes TEXT]
                                [--replace] [--no-build] [--dry-run] [--max-bytes N]

--no-build places and records the pack and stops before build.py, for several
packs in a row: run build and analyze once after the last (the two commands it
prints), since a build of the whole library per pack is the slow part.

Every refusal that can be decided without touching anything is decided first,
and the run stops with one line starting "refused:". Extraction and sanitising
happen under caches/ingest/<name>/; the rename into the library is the single
commit point, so a crash never leaves audio or a half-extracted pack under it.
Run it from the directory where caches/ and metrics/ should land (the repo root).
"""

import argparse
import datetime
import errno
import os
import pathlib
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / 'tools'))

import tqdm                                   # noqa: E402

import config                                 # noqa: E402
import sanitize_songs                         # noqa: E402
from functions import cache as cache_mod      # noqa: E402
from functions import instruments, packs, timestamp   # noqa: E402

ARCHIVES = ('.zip', '.rar', '.7z')
NOT_DIRECT = ('drive.google.com', 'docs.google.com', 'mega.nz', 'mega.co.nz',
              'discord.com', 'discordapp.com', 'cdn.discordapp.com')
DEFAULT_MAX_BYTES = 10 * 1024 ** 3
CHUNK = 1024 * 1024
UA = 'fretwork-ingest'


class Refusal(Exception):
    pass


class Plan:
    """What pre-flight decided: the source kind, the registry, and what --replace means here."""

    def __init__(self, kind, registry, append_entry, remove_folder):
        self.kind = kind                    # 'zip' | 'rar' | '7z' | 'dir' | 'url'
        self.registry = registry
        self.append_entry = append_entry    # write a [[pack]] after the rename
        self.remove_folder = remove_folder  # delete <library>/<name>/ before placing


# --- pre-flight -------------------------------------------------------------------

def source_kind(source):
    if source.startswith(('http://', 'https://')):
        return 'url'
    path = pathlib.Path(source)
    if path.is_dir():
        return 'dir'
    if path.suffix.lower() in ARCHIVES and path.is_file():
        return path.suffix.lower()[1:]
    raise Refusal(f'{source}: not a .zip, .rar or .7z file, a directory, or an http(s) URL to one')


def url_suffix(url):
    name = pathlib.PurePosixPath(urllib.parse.urlparse(url).path).name
    suffix = pathlib.PurePosixPath(name).suffix.lower()
    return suffix if suffix in ARCHIVES else None


def extractor_for(kind):
    """The external tool a .rar or .7z needs, or a refusal naming the package."""
    if kind == 'zip':
        return None
    seven = shutil.which('7z') or shutil.which('7zz')
    if kind == 'rar':
        if shutil.which('unrar'):
            return ['unrar']
        if seven:
            return [seven]
        raise Refusal('.rar needs unrar (apt install unrar) or 7z (apt install p7zip-full p7zip-rar); '
                      'neither is on PATH')
    if seven:
        return [seven]
    raise Refusal(".7z needs 7z on PATH (apt install 7zip, or p7zip-full; 7-Zip's 7z.exe on Windows)")


def preflight(args):
    name = args.name
    if not name or name in ('.', '..') or '/' in name or '\\' in name or name.startswith('.'):
        raise Refusal(f'--name {name!r} must be a single folder name')
    if config.DIFF_WRITE_MODE is not None:
        raise Refusal(f'config.DIFF_WRITE_MODE is {config.DIFF_WRITE_MODE!r}; set it back to None '
                      f'(ingest never writes song.ini, and analyze would)')
    source = args.source if args.source is not None else (args.SOURCE if args.SOURCE.startswith(('http://', 'https://')) else '')
    if source and not source.startswith(('http://', 'https://')):
        raise Refusal(f'--source {source!r} must be an http(s) URL or empty')
    args.source = source
    kind = source_kind(args.SOURCE)
    if kind == 'url':
        host = urllib.parse.urlparse(args.SOURCE).hostname or ''
        if host in NOT_DIRECT or any(host.endswith('.' + h) for h in NOT_DIRECT):
            raise Refusal(f'{host} serves pages or expiring links, not a direct download; '
                          f'download the pack in a browser and pass the file')
        if url_suffix(args.SOURCE) is None:
            raise Refusal(f'{args.SOURCE}: the URL must end in .zip, .rar or .7z')
        extractor_for(url_suffix(args.SOURCE)[1:])
    elif kind in ('rar', '7z'):
        extractor_for(kind)
    packs_path = pathlib.Path(args.packs)
    if not packs_path.is_file():
        if pathlib.Path(args.packs).resolve() == packs.PACKS_FILE.resolve():
            raise Refusal(f'{packs_path} is missing; every pack must be listed there')
        packs_path.write_text('', encoding='utf-8')     # a test registry starts empty
    try:
        registry = packs.load(packs_path)
    except packs.PacksError as exc:
        raise Refusal(f'{packs_path}: {exc}') from exc
    registered = name in registry.by_folder
    for pack in registry.packs:
        if pack.name == name and pack.folder != name:
            raise Refusal(f'{name!r} is already a pack name in {packs_path.name} for folder {pack.folder!r}')
    exists = (pathlib.Path(args.library) / name).is_dir()
    if not args.replace:
        if registered:
            raise Refusal(f'{name} is already in {packs_path.name} (pass --replace to re-download it)')
        if exists:
            raise Refusal(f'{pathlib.Path(args.library) / name}/ exists (pass --replace to replace it)')
    return Plan(kind, registry, append_entry=not registered, remove_folder=exists)


# --- fetching and extracting -------------------------------------------------------

def download(url, dest, max_bytes):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    try:
        return _download(req, url, dest, max_bytes)
    except urllib.error.HTTPError as exc:
        raise Refusal(f'{url}: HTTP {exc.code} {exc.reason}') from exc
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        raise Refusal(f'{url}: {getattr(exc, "reason", exc)}') from exc


def _download(req, url, dest, max_bytes):
    with urllib.request.urlopen(req, timeout=60) as r:
        final = r.geturl()
        if url.startswith('https://') and final.startswith('http://'):
            raise Refusal(f'{url} redirected to plain http ({final}); refusing')
        ctype = r.headers.get('Content-Type', '')
        if ctype.startswith('text/html'):
            raise Refusal(f'{url} answered with a web page ({ctype}), not an archive; '
                          f'download it in a browser and pass the file')
        length = r.headers.get('Content-Length')
        if length and int(length) > max_bytes:
            raise Refusal(f'{url} is {int(length):,} bytes, over --max-bytes {max_bytes:,}')
        total = int(length) if length else None
        got = 0
        with open(dest, 'wb') as f, tqdm.tqdm(total=total, unit='B', unit_scale=True, desc='Downloading') as bar:
            while True:
                chunk = r.read(CHUNK)
                if not chunk:
                    break
                got += len(chunk)
                if got > max_bytes:
                    f.close()
                    dest.unlink(missing_ok=True)
                    raise Refusal(f'{url} passed --max-bytes {max_bytes:,} with no Content-Length; partial file removed')
                f.write(chunk)
                bar.update(len(chunk))
    return got


# A member without the UTF-8 flag (bit 11) was decoded as cp437 by zipfile;
# Windows-made archives arrive with "Mötley Crüe" as "M├╢tley Cr├╝e".
def fix_member_name(name, flag_bits):
    if flag_bits & 0x800:
        return name
    try:
        return name.encode('cp437').decode('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        return name


def safe_target(root, name):
    """The path a member lands on, or None when it would escape the extraction root."""
    if name.startswith('/') or name.startswith('\\'):
        return None
    parts = [p for p in name.replace('\\', '/').split('/') if p not in ('', '.')]
    if not parts or any(p == '..' for p in parts):
        return None
    target = (root / pathlib.Path(*parts)).resolve()
    if root.resolve() not in target.parents:
        return None
    return target


def extract_zip(archive, dest, max_bytes):
    skipped = 0
    with zipfile.ZipFile(archive) as zf:
        members = zf.infolist()
        inflated = sum(m.file_size for m in members)
        if inflated > max_bytes:
            raise Refusal(f'{archive.name} inflates to {inflated:,} bytes, over --max-bytes {max_bytes:,}')
        for m in tqdm.tqdm(members, desc='Extracting', unit='file'):
            if m.is_dir():
                continue
            target = safe_target(dest, fix_member_name(m.filename, m.flag_bits))
            if target is None:
                skipped += 1
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(m) as src, open(target, 'wb') as out:
                shutil.copyfileobj(src, out, CHUNK)
    if skipped:
        print(f'  {skipped} members outside the archive root skipped')
    return skipped


def extract_external(kind, archive, dest):
    tool = extractor_for(kind)
    dest.mkdir(parents=True, exist_ok=True)
    if tool[0].endswith('unrar'):
        cmd = ['unrar', 'x', '-o+', str(archive), str(dest) + os.sep]
    else:
        cmd = [tool[0], 'x', '-y', f'-o{dest}', str(archive)]
    print('  ' + ' '.join(cmd))
    proc = subprocess.run(cmd)
    if proc.returncode != 0:
        raise Refusal(f'{cmd[0]} exited {proc.returncode} on {archive.name}; the extraction directory '
                      f'{dest} is left for inspection (no inflated-size check is possible for this format)')


def copy_dir(source, dest):
    """A folder source is copied without its audio, art or video: the original is never touched."""
    def ignore(directory, names):
        lowered = {n.lower() for n in names}
        in_song = bool(lowered & sanitize_songs.KEEP)
        return {n for n in names if sanitize_songs.classify(pathlib.Path(directory, n), in_song)
                and not pathlib.Path(directory, n).is_dir()}
    shutil.copytree(source, dest, ignore=ignore)


# --- finding the songs --------------------------------------------------------------

def normalise_names(root):
    """Song.ini -> song.ini and so on; the parsers' rglob is case-sensitive on Linux."""
    for dirpath, _dirs, files in os.walk(root):
        lowered = {}
        for f in files:
            low = f.lower()
            if low in sanitize_songs.KEEP:
                if low in lowered:
                    raise Refusal(f'{pathlib.Path(dirpath).relative_to(root)} holds both {lowered[low]} and {f}')
                lowered[low] = f
        for low, f in lowered.items():
            if f != low:
                os.replace(pathlib.Path(dirpath, f), pathlib.Path(dirpath, low))


def strip_wrapper(root):
    """An archive whose root holds one directory unpacks as that directory, unless
    that directory is itself a song folder: a one-song pack keeps its song folder,
    or the pack would land in the library as a loose song."""
    entries = list(root.iterdir())
    if len(entries) == 1 and entries[0].is_dir() and not (entries[0] / 'song.ini').is_file():
        wrapper = entries[0]
        inner = root / ('.unwrap-' + wrapper.name)
        wrapper.rename(inner)
        for child in inner.iterdir():
            child.rename(root / child.name)
        inner.rmdir()
        return wrapper.name
    return None


def song_folders(root):
    return sorted(p.parent for p in root.rglob('song.ini'))


def sng_count(root):
    return sum(1 for _ in root.rglob('*.sng'))


# --- the run -------------------------------------------------------------------------

def stage(args, plan, work):
    """Fetch, extract or copy into work/<name>/, normalise names, strip a wrapper; returns (dest, timings)."""
    dest = work / args.name
    if dest.exists():
        print(f'  removing leftover staging folder {dest}')
        shutil.rmtree(dest)
    timings = {}
    kind = plan.kind
    source = args.SOURCE
    t = time.monotonic()
    if kind == 'url':
        suffix = url_suffix(source)
        archive = work / f'{args.name}{suffix}'
        print(f'Fetching {source}\n  -> {archive}')
        download(source, archive, args.max_bytes)
        timings['fetch'] = time.monotonic() - t
        t = time.monotonic()
        source, kind = str(archive), suffix[1:]
    else:
        timings['fetch'] = 0.0
    dest.mkdir(parents=True)
    if kind == 'dir':
        print(f'Copying {source} (chart files only)')
        shutil.rmtree(dest)
        copy_dir(pathlib.Path(source), dest)
    elif kind == 'zip':
        print(f'Extracting {source}')
        extract_zip(pathlib.Path(source), dest, args.max_bytes)
    else:
        print(f'Extracting {source} with an external tool')
        extract_external(kind, pathlib.Path(source), dest)
    timings['extract'] = time.monotonic() - t
    normalise_names(dest)
    wrapper = strip_wrapper(dest)
    if wrapper:
        print(f'  unwrapped the single top-level folder {wrapper!r}')
    folders = song_folders(dest)
    if not folders:
        raise Refusal(f'found 0 song folders and {sng_count(dest)} .sng files under {source}; '
                      f'.sng is not readable by the parsers, get the pack as song folders')
    print(f'  {len(folders)} song folders found')
    return dest, timings


def place(staged, library, name, remove_first):
    target = library / name
    if remove_first and target.exists():
        n = len(song_folders(target))
        print(f'  removing {target}/ ({n} song folders) before placing the new copy')
        shutil.rmtree(target)
    library.mkdir(parents=True, exist_ok=True)
    try:
        os.replace(staged, target)
    except OSError as exc:
        if exc.errno != errno.EXDEV:
            raise
        print(f'  {library} is on a different filesystem from {staged.parent}; copying the pack instead of renaming it')
        shutil.copytree(staged, target)
        shutil.rmtree(staged)
    return target


def run_step(script, *argv):
    cmd = [sys.executable, str(REPO / script), *argv]
    print('\n$ ' + ' '.join(cmd) + '\n')
    subprocess.run(cmd, check=True)


def expert_counts(cache):
    counts = {key: 0 for key in instruments.INSTRUMENT_KEYS}
    for song in cache['songs'].values():
        for inst, levels in song['codes'].items():
            if 'expert' in levels:
                counts[inst] += 1
    return counts


def scored(cache):
    return packs.scored_codes(cache)


def drums_codes(cache):
    suffix = instruments.CODE_SUFFIX['drums']
    return [c for c in cache['codes'] if c.endswith(suffix)]


def newest_after(kind, header, ext, since):
    try:
        path = timestamp.latest_output(kind, header, ext=ext)
    except FileNotFoundError:
        return None
    return path if path.stat().st_mtime >= since else None


def errors_in(errors_csv, folder):
    import csv
    if errors_csv is None:
        return 0, 0
    total = inside = 0
    prefix = str(folder.resolve()) + os.sep
    with open(errors_csv, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            total += 1
            if str(pathlib.Path(row['path']).resolve()).startswith(prefix):
                inside += 1
    return total, inside


def fmt(n):
    return f'{n:,}'


def summary(args, plan, header, before, after, before_stamp, after_stamp, folder, found, sanitizer, errors_csv,
            xlsx, timings, entry_line):
    codes_after = scored(after)
    resolved = packs.resolve(after, packs.load(args.packs))
    songs_in, charts_in = packs.tally(resolved, codes_after).get(args.name, (0, 0))
    total_err, pack_err = errors_in(errors_csv, folder)
    b_songs = len(before['songs']) if before else None
    b_scored = len(scored(before)) if before else None
    b_drums = len(drums_codes(before)) if before else None
    a_songs, a_scored, a_drums = len(after['songs']), len(codes_after), len(drums_codes(after))
    delta = lambda a, b: f'{a - b:+,}' if b is not None else ''
    show = lambda b: fmt(b) if b is not None else 'none'
    print(f'\nSummary  {header}  {before_stamp or "none"} -> {after_stamp}')
    print(f'  songs                {show(b_songs):>10} -> {fmt(a_songs):>8}  {delta(a_songs, b_songs):>8}')
    print(f'  charts scored        {show(b_scored):>10} -> {fmt(a_scored):>8}  {delta(a_scored, b_scored):>8}')
    print(f'  drums cached (not scored) {show(b_drums):>5} -> {fmt(a_drums):>8}  {delta(a_drums, b_drums):>8}')
    print(f'  build errors         {fmt(total_err):>10}   ' + (f'({errors_csv.name})' if errors_csv else f'(no caches/{header}_errors_*.csv from this run)'))
    eb, ea = (expert_counts(before) if before else None), expert_counts(after)
    print(f'\n  Expert charts        before    after    delta')
    for key in instruments.INSTRUMENT_KEYS:
        b = eb[key] if eb else None
        note = '   (not scored)' if key not in instruments.SCORED_INSTRUMENTS else ''
        print(f'    {instruments.DISPLAY_NAMES[key]:<18} {show(b):>8} {fmt(ea[key]):>8} {delta(ea[key], b):>8}{note}')
    print(f'\n  this pack  {folder}/')
    print(f'    song.ini found          {fmt(found):>6}')
    print(f'    cached                  {fmt(songs_in):>6}')
    print(f'    charts scored           {fmt(charts_in):>6}')
    print(f'    no usable chart or mid  {fmt(found - songs_in):>6}')
    print(f'    build errors in pack    {fmt(pack_err):>6}')
    print(f'    .sng (not readable)     {fmt(sng_count(folder)):>6}')
    if sanitizer:
        print(f'    sanitizer removed     {sanitize_songs.human(sanitizer.removed_bytes)} in {sanitizer.removed_files} files'
              + (f', log {args.log}' if args.log else ''))
    print(f'    packs.toml            {entry_line}')
    print(f'\n  spreadsheet  {xlsx}')
    print('  elapsed  ' + '  '.join(f'{k} {v:.0f}s' for k, v in timings.items()))
    print(f'\nNext:\n  python publish.py --header {header}\n  python deploy.py --dry-run\n  python deploy.py\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[1])
    ap.add_argument('SOURCE', help='.zip / .rar / .7z, a directory, or an http(s) URL to an archive')
    ap.add_argument('--name', required=True, help='folder under the library; also name and folder in packs.toml')
    ap.add_argument('--source', default=None, help='URL recorded in packs.toml (default: SOURCE when it is a URL)')
    ap.add_argument('--header', default='Local')
    ap.add_argument('--library', default='songs')
    ap.add_argument('--packs', default=str(packs.PACKS_FILE))
    ap.add_argument('--notes', default='')
    ap.add_argument('--replace', action='store_true', help='replace an existing <library>/<name>/')
    ap.add_argument('--no-build', action='store_true', help='place and record the pack, then stop: build and analyze once after several')
    ap.add_argument('--dry-run', action='store_true', help='fetch, extract, find and report; change nothing')
    ap.add_argument('--max-bytes', type=int, default=DEFAULT_MAX_BYTES)
    args = ap.parse_args()
    args.library = str(pathlib.Path(args.library).resolve())
    args.log = None
    try:
        sys.exit(ingest(args))
    except Refusal as exc:
        sys.exit(f'refused: {exc}')
    except subprocess.CalledProcessError as exc:
        sys.exit(f'{pathlib.Path(exc.cmd[1]).name} exited {exc.returncode}')


def ingest(args):
    started = time.time()
    plan = preflight(args)
    library = pathlib.Path(args.library)
    work = pathlib.Path(config.OUTPUT_DIRS['cache']) / 'ingest'
    work.mkdir(parents=True, exist_ok=True)
    staged, timings = stage(args, plan, work)

    t = time.monotonic()
    args.log = work / f'{args.name}_removed.csv'
    report = sanitize_songs.sanitize(staged, apply=not args.dry_run, log=None if args.dry_run else args.log)
    timings['sanitize'] = time.monotonic() - t
    found = report.song_folders
    if args.dry_run:
        shutil.rmtree(staged)
        print(f'Dry run: {found} song folders would go to {library / args.name}/; nothing changed')
        return 0

    header = args.header
    before_path = None
    try:
        before_path = timestamp.latest_output('cache', header, ext='pkl')
        before = cache_mod.load(before_path)
        before_stamp = timestamp.ext_ts(before_path, 'cache', header)
    except FileNotFoundError:
        before, before_stamp = None, None
        print(f'no previous cache for {header}')

    folder = place(staged, library, args.name, plan.remove_folder)
    if plan.append_entry:
        packs.append_pack(args.packs, packs.Pack(args.name, args.name, args.source, datetime.date.today(), args.notes))
        entry_line = 'appended'
    else:
        entry_line = 'entry kept (already registered)'
    if args.no_build:
        print(f'\n{found} song folders placed at {folder}/, packs.toml entry {entry_line}; not built (--no-build).\n'
              f'After the last pack:\n'
              f'  python build.py --search-path {library} --header {header}\n'
              f'  python analyze.py --header {header}')
        return 0

    t = time.monotonic()
    run_step('build.py', '--search-path', str(library), '--header', header)
    timings['build'] = time.monotonic() - t
    t = time.monotonic()
    run_step('analyze.py', '--header', header)
    timings['analyze'] = time.monotonic() - t

    after_path = newest_after('cache', header, 'pkl', started)
    if after_path is None:
        raise Refusal('build wrote no new cache')
    after = cache_mod.load(after_path)
    xlsx = newest_after('metrics', header, 'xlsx', started)
    errors_csv = newest_after('errors', header, 'csv', started)
    summary(args, plan, header, before, after, before_stamp, timestamp.ext_ts(after_path, 'cache', header),
            folder, found, report, errors_csv, xlsx, timings, entry_line)
    return 0


if __name__ == '__main__':
    main()
