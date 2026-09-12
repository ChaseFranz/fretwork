#!/usr/bin/env python3
"""
SANITIZE_SONGS - Strip a song library down to what fretwork reads.

Fretwork parses only song.ini, notes.chart and notes.mid. Everything else in a
song folder - audio stems, album art, backgrounds, highways, videos, editor
scratch files, Windows Zone.Identifier streams - is dead weight for a metrics
archive. This script removes those, and nothing else.

Every instrument's notes live inside notes.chart / notes.mid, so no chart data
is ever touched. Files the script does not recognise are listed and left alone.

Usage:
    python tools/sanitize_songs.py LIBRARY_DIR            # dry run: report only
    python tools/sanitize_songs.py LIBRARY_DIR --apply    # delete
    python tools/sanitize_songs.py LIBRARY_DIR --apply --log removed.csv

Runs only inside a folder that actually looks like a song library (has at
least one song.ini). Deletes only from folders that contain a song.ini or a
notes file, except Zone.Identifier / desktop.ini / Thumbs.db, which are junk
anywhere.
"""

import argparse
import csv
import os
import sys
from collections import Counter, defaultdict, namedtuple
from pathlib import Path

# The only files fretwork's parsers open (build.py / parsers/*.py rglob these).
KEEP = {'song.ini', 'notes.chart', 'notes.mid'}

# Extensions removed from a song folder, grouped for the report.
REMOVE = {
    'audio': {'.ogg', '.opus', '.mp3', '.wav', '.flac', '.m4a', '.aac', '.wma', '.aiff', '.aif'},
    'image': {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.tif', '.tiff'},
    'video': {'.mp4', '.webm', '.avi', '.mkv', '.mov', '.wmv', '.m4v', '.flv'},
    'scratch': {'.sfk',      # Sound Forge peak cache
                '.reapeaks', # REAPER peak cache
                '.bak', '.tmp'},
}
EXT_CATEGORY = {ext: cat for cat, exts in REMOVE.items() for ext in exts}

# Junk that is safe to drop anywhere under the library, song folder or not.
JUNK_NAMES = {'desktop.ini', 'thumbs.db', '.ds_store'}
JUNK_SUFFIX = ':zone.identifier'   # NTFS alternate stream copied out as a file


def classify(path: Path, in_song_folder: bool):
    """Return a removal category for path, or None to keep it."""
    name = path.name.lower()
    if name in KEEP:
        return None
    if name.endswith(JUNK_SUFFIX) or name in JUNK_NAMES:
        return 'junk'
    if not in_song_folder:
        return None          # pack-level readmes etc.: not ours to judge
    return EXT_CATEGORY.get(path.suffix.lower())


def scan(root: Path):
    """Walk root once. Yields (path, size, category-or-None, in_song_folder)."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        lowered = {f.lower() for f in filenames}
        in_song = bool(lowered & KEEP)
        for f in sorted(filenames):
            p = Path(dirpath, f)
            try:
                size = p.stat().st_size
            except OSError:
                continue
            yield p, size, classify(p, in_song), in_song


def human(n: int) -> str:
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if n < 1024 or unit == 'TB':
            return f'{n:,.1f} {unit}' if unit != 'B' else f'{n} B'
        n /= 1024


Report = namedtuple('Report', 'song_folders total_bytes removed_bytes removed_files failed unknown')


# The whole job as a call: report, and delete when apply is set. Raises
# ValueError where the command line would exit, so a caller decides what a
# refusal means for it. Prints the report exactly as the command does.
def sanitize(root, apply=False, log=None, show_unknown=False):
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError(f'not a directory: {root}')

    remove, unknown = [], []
    bytes_by_cat = Counter()
    count_by_cat = Counter()
    bytes_by_pack = defaultdict(int)
    song_folders = set()
    total_bytes = 0

    for p, size, cat, in_song in scan(root):
        total_bytes += size
        if in_song:
            song_folders.add(p.parent)
        if cat:
            remove.append((p, size, cat))
            bytes_by_cat[cat] += size
            count_by_cat[cat] += 1
            rel = p.relative_to(root)
            bytes_by_pack[rel.parts[0] if len(rel.parts) > 1 else '.'] += size
        elif in_song and p.name.lower() not in KEEP:
            unknown.append((p, size))

    if not song_folders:
        raise ValueError(f'no song.ini / notes files under {root} - refusing to run on something that is not a song library')

    mode = 'APPLY' if apply else 'DRY RUN'
    print(f'\n{mode}: {root}')
    print(f'  song folders      {len(song_folders):>8,}')
    print(f'  library size      {human(total_bytes):>12}')
    print(f'  to remove         {human(sum(bytes_by_cat.values())):>12}  ({len(remove):,} files)')
    print(f'  after             {human(total_bytes - sum(bytes_by_cat.values())):>12}\n')

    print('  by category')
    for cat in sorted(count_by_cat, key=lambda c: -bytes_by_cat[c]):
        print(f'    {cat:<8} {count_by_cat[cat]:>7,} files  {human(bytes_by_cat[cat]):>12}')

    print('\n  by top-level folder')
    for pack, b in sorted(bytes_by_pack.items(), key=lambda kv: -kv[1]):
        print(f'    {human(b):>12}  {pack}')

    if unknown:
        exts = Counter(p.suffix.lower() or '(none)' for p, _ in unknown)
        print(f'\n  left alone in song folders (unrecognised): {len(unknown):,} files, '
              f'{human(sum(s for _, s in unknown))}')
        for ext, n in exts.most_common():
            print(f'    {n:>6,}  {ext}')
        if show_unknown:
            for p, s in unknown:
                print(f'      {human(s):>10}  {p.relative_to(root)}')

    if not apply:
        print('\n  Dry run - nothing deleted. Re-run with --apply to remove the files above.\n')
        return Report(len(song_folders), total_bytes, sum(bytes_by_cat.values()), len(remove), 0, unknown)

    writer = None
    if log:
        log_file = open(log, 'w', newline='', encoding='utf-8')
        writer = csv.writer(log_file)
        writer.writerow(['path', 'bytes', 'category'])

    freed = 0
    failed = 0
    for p, size, cat in remove:
        try:
            p.unlink()
            freed += size
            if writer:
                writer.writerow([str(p), size, cat])
        except OSError as e:
            failed += 1
            print(f'  could not delete {p}: {e}')
    if writer:
        log_file.close()

    print(f'\n  Deleted {len(remove) - failed:,} files, freed {human(freed)}'
          + (f', {failed} failed' if failed else '')
          + (f', log at {log}' if log else '') + '\n')
    return Report(len(song_folders), total_bytes, freed, len(remove) - failed, failed, unknown)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[1])
    ap.add_argument('library', type=Path, help='song library root (e.g. songs/)')
    ap.add_argument('--apply', action='store_true', help='actually delete; default is a dry run')
    ap.add_argument('--log', type=Path, help='CSV of removed files (path, bytes, category)')
    ap.add_argument('--show-unknown', action='store_true',
                    help='list every unrecognised file left in song folders, not just a summary')
    args = ap.parse_args()
    try:
        sanitize(args.library, apply=args.apply, log=args.log, show_unknown=args.show_unknown)
    except ValueError as e:
        sys.exit(str(e))


if __name__ == '__main__':
    main()
