"""
PIPELINE_TEST - build, analyze, publish and deploy the synthetic library, end to end.

Runs the real entry points as subprocesses from a temporary working directory,
so caches/, metrics/ and site/ land there and the repo is never written to, with
a stub `aws` on PATH so deploy runs its whole non-dry path without credentials.
Every expected number comes from tests/fixture.py's table; every stage prints
one summary line, and the first failed assertion prints that stage's output and
exits 1.

    python tests/pipeline_test.py --bootstrap-css caches/bootstrap-5.3.8.min.css
    python tests/pipeline_test.py --keep /tmp/fw-ci        # keep the working directory

Linux and WSL only: the stub is a shebang script with no extension.
"""

import argparse
import csv
import html
import html.parser
import json
import os
import pathlib
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import analyze                                   # noqa: E402
import config                                    # noqa: E402
import deploy                                    # noqa: E402
from functions import cache as cache_mod         # noqa: E402
from functions import ini_updater, instruments, labels  # noqa: E402
from web import assets, bootstrap, frames, page  # noqa: E402
from web.graph import GraphRenderer              # noqa: E402
from web.server import MetricsServer             # noqa: E402
from tests import fixture                        # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[1]
PLACEHOLDER = re.compile(r'__[A-Z][A-Z_]*__')
STRAPLINE = re.compile(r'Updated \d{1,2} [A-Z][a-z]+ \d{4}  -  ([\d,]+) charts')


class Failed(Exception):
    pass


class Stage:
    """One entry-point run: its captured output, and assertions that print it on failure."""

    def __init__(self, name, work, env, python):
        self.name, self.work, self.env, self.python = name, work, env, python
        self.out = ''

    def run(self, script, *args, expect=0):
        cmd = [self.python, str(REPO / script), *args]
        proc = subprocess.run(cmd, cwd=self.work, env=self.env, capture_output=True, text=True)
        self.out = proc.stdout + proc.stderr
        if expect is not None and proc.returncode != expect:
            self.fail(f'{script} exited {proc.returncode}, expected {expect}')
        return proc

    def check(self, ok, what):
        if not ok:
            self.fail(what)

    def fail(self, what):
        print(f'\nFAIL [{self.name}] {what}\n--- output ---\n{self.out}', file=sys.stderr)
        raise Failed(what)

    def done(self, summary):
        print(f'ok   {self.name}: {summary}')


def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def boot_island(text):
    m = re.search(r'<script type="application/json" id="fw-boot">(.*?)</script>', text, re.S)
    return json.loads(m.group(1))


class Anchors(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs, self.scripts, self.h2 = [], 0, 0

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.hrefs.append(dict(attrs).get('href', ''))
        elif tag == 'script':
            self.scripts += 1
        elif tag == 'h2':
            self.h2 += 1


def main():
    ap = argparse.ArgumentParser(description='Build, analyze, publish and deploy the fixture library.')
    ap.add_argument('--keep', help='use and keep this working directory')
    ap.add_argument('--bootstrap-css', help='a Bootstrap file for the second publish; skipped when absent')
    ap.add_argument('--header', default='Fixture')
    ap.add_argument('--python', default=sys.executable)
    args = ap.parse_args()

    if config.DIFF_WRITE_MODE is not None:
        sys.exit(f'config.DIFF_WRITE_MODE is {config.DIFF_WRITE_MODE!r}; set it to None in config.py '
                 f'before running this test (Restore writes no spreadsheet, the others write song.ini)')

    if args.keep:
        work = pathlib.Path(args.keep).resolve()
        for sub in ('caches', 'metrics'):
            if (work / sub).exists() and any((work / sub).iterdir()):
                sys.exit(f'{work / sub} is not empty; timestamps are minute-resolution, so start clean')
        work.mkdir(parents=True, exist_ok=True)
        tmp = None
    else:
        tmp = tempfile.TemporaryDirectory(prefix='fretwork-pipeline-')
        work = pathlib.Path(tmp.name)
    header = args.header
    try:
        run_all(work, header, args)
    except Failed:
        sys.exit(1)
    finally:
        if tmp:
            tmp.cleanup()
        else:
            print(f'working directory kept at {work}')


def run_all(work, header, args):
    lib = fixture.write(work / 'library')
    registry = fixture.write_registry(work / 'packs.toml', lib)
    for ini in (work / 'library').rglob('song.ini'):          # audio beside every chart: ingest must drop it, build must not care
        (ini.parent / 'song.ogg').write_bytes(b'\x00' * 64)
    (work / 'bin').mkdir(exist_ok=True)
    stub = (REPO / 'tests' / 'bin' / 'aws').read_text(encoding='utf-8').splitlines()
    stub[0] = '#!' + args.python
    (work / 'bin' / 'aws').write_text('\n'.join(stub) + '\n', encoding='utf-8')
    (work / 'bin' / 'aws').chmod(0o755)
    (work / 'deploy.env').write_text(
        f'FRETWORK_BUCKET=fixture-bucket\nFRETWORK_DISTRIBUTION=E1FIXTURE0000\n'
        f'FRETWORK_HEADER={header}\nFRETWORK_SITE_DIR=site/{header}\n', encoding='utf-8')
    log = work / 'aws.log'
    env = {**os.environ, 'PATH': f"{work / 'bin'}{os.pathsep}{os.environ.get('PATH', '')}",
           'AWS_STUB_LOG': str(log), 'PYTHONUNBUFFERED': '1'}
    site = work / 'site' / header

    # A backup CSV from before drums and vocals joined DIFF_TAGS: build must migrate its header (section 00).
    (work / 'caches').mkdir(exist_ok=True)
    old_cols = [c for c in ini_updater.BACKUP_COLUMNS if c not in ('diff_drums', 'diff_vocals')]
    (work / 'caches' / f'{header}_BackupData.csv').write_text(','.join(old_cols) + '\n', encoding='utf-8')

    # ---- ingest (section 09): the three packs one at a time, in its own working directory ----
    ingest = work / 'ingest'
    ingest.mkdir()
    st = Stage('ingest', ingest, env, args.python)
    charted_so_far = 0
    for i, pack in enumerate(fixture.PACKS):
        songs_in_pack = [s for s in lib.songs if s.pack == pack]
        charted_in_pack = [s for s in songs_in_pack if s.charted]
        st.run('tools/ingest_pack.py', str(work / 'library' / pack), '--name', pack, '--library', 'library',
               '--header', header, '--packs', 'packs.toml', '--source', '')
        before = 'none' if i == 0 else f'{charted_so_far:,}'
        st.check(re.search(rf'songs\s+{re.escape(before)} ->\s+{charted_so_far + len(charted_in_pack):,}\b', st.out),
                 f'{pack}: summary songs line')
        st.check(re.search(rf'song\.ini found\s+{len(songs_in_pack)}\b', st.out) and
                 re.search(rf'cached\s+{len(charted_in_pack)}\b', st.out) and
                 re.search(rf'no usable chart or mid\s+{len(songs_in_pack) - len(charted_in_pack)}\b', st.out),
                 f'{pack}: this-pack block')
        st.check('packs.toml            appended' in st.out, f'{pack}: entry not appended')
        charted_so_far += len(charted_in_pack)
    from functions import packs as packs_mod
    reg = packs_mod.load(ingest / 'packs.toml')
    st.check([p.folder for p in reg.packs] == list(fixture.PACKS) and
             all(p.added == __import__('datetime').date.today() for p in reg.packs), 'ingest registry')
    with (ingest / 'caches' / f'{header}_BackupData.csv').open(newline='', encoding='utf-8') as f:
        rows = list(csv.reader(f))
    st.check(rows[0] == ini_updater.BACKUP_COLUMNS and len(rows) - 1 == len(lib.charted) and all(len(r) == len(rows[0]) for r in rows),
             f'backup CSV after three appends: {len(rows) - 1} rows, header {rows[0]}')
    st.check(not list((ingest / 'library').rglob('*.ogg')), 'audio reached the ingest library')
    st.done(f'three packs ingested one at a time, {charted_so_far} songs, registry and backup CSV consistent')

    # ---- build -----------------------------------------------------------------------
    st = Stage('build', work, env, args.python)
    st.run('build.py', '--search-path', 'library', '--header', header)
    for line, want in (('Song.ini count', lib.ini_count), ('No usable chart/mid', len(lib.unusable)),
                       ('Errors', len(lib.errors)), ('Cached songs', len(lib.charted))):
        st.check(re.search(rf'{re.escape(line)}\s+{want}\b', st.out), f'summary line {line!r} is not {want}')
    st.check('Backup CSV header updated' in st.out, 'the old backup header was not migrated')
    errors = list((work / 'caches').glob(f'{header}_errors_*.csv'))
    st.check(len(errors) == 1, f'expected one errors CSV, found {errors}')
    err_rows = list(csv.reader(errors[0].open(encoding='utf-8')))
    st.check(len(err_rows) == 2 and 'C7 - Broken Mid' in err_rows[1][0], f'errors CSV rows: {err_rows}')
    caches = list((work / 'caches').glob(f'{header}_cache_*.pkl'))
    st.check(len(caches) == 1, f'expected one cache, found {caches}')
    cache = cache_mod.load(caches[0])
    st.check(len(cache['songs']) == len(lib.charted), f"{len(cache['songs'])} songs cached")
    st.check(len(cache['codes']) == lib.codes, f"{len(cache['codes'])} codes")
    st.check(all(re.fullmatch(r'\d{8}[EMHX][GCRBKDV]', c) for c in cache['codes']), 'a code has the wrong shape')
    by_folder = {pathlib.Path(p).name: s for p, s in cache['songs'].items()}
    for song in lib.charted:
        s = by_folder[song.folder]
        st.check(s['source_format'] == song.source_format, f'{song.folder}: source_format {s["source_format"]}')
        st.check(s['meta']['Official'] == song.official and s['meta']['Release'] == song.release,
                 f'{song.folder}: {s["meta"]}')
        for key, levels in s['instruments'].items():
            for level, stream in levels.items():
                if key in ('drums', 'vocals'):
                    st.check(re.fullmatch('[0-9a-f]{12}', stream.get('notes_hash', '')), f'{song.folder} {key}: notes_hash')
                    continue
                notes = stream['notes']
                st.check(str(notes['time_ms'].dtype) == 'float64' and str(notes['lanes'].dtype) == 'uint8'
                         and (notes['time_ms'][1:] >= notes['time_ms'][:-1]).all(),
                         f'{song.folder} {key} {level}: stream shape')
    st.check(by_folder['C4 - Less Than More']['meta']['Name'] == 'Less < More', 'C4 name not detagged')
    st.check(by_folder['C2 - Mid Pair']['source_format'] == 'chart', 'chart did not win over mid for C2')
    with (work / 'caches' / f'{header}_BackupData.csv').open(newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
        f.seek(0)
        head = next(csv.reader(f))
    st.check(head == ini_updater.BACKUP_COLUMNS, f'backup header {head}')
    want = lib.backup_rows
    st.check(len(rows) == len(want), f'{len(rows)} backup rows, expected {len(want)}')
    for row in rows:
        exp = want[row['song_path']]
        got = {k: row[k] for k in exp}
        st.check(got == exp, f'backup row for {pathlib.Path(row["song_path"]).name}: {got} != {exp}')
    st.done(f'{len(lib.charted)} songs, {lib.codes} codes, {len(lib.errors)} error, backup header migrated')

    # ---- analyze ----------------------------------------------------------------------
    import pandas as pd
    st = Stage('analyze', work, env, args.python)
    st.run('analyze.py', '--header', header, '--xlsx-levels', 'ALL')
    xlsxs = list((work / 'metrics').glob(f'{header}_metrics_*.xlsx'))
    st.check(len(xlsxs) == 1, f'expected one xlsx, found {xlsxs}')
    st.check(xlsxs[0].stem.split('_')[-1] == caches[0].stem.split('_')[-1], 'xlsx timestamp differs from the cache')
    sheets = pd.read_excel(xlsxs[0], sheet_name=None)
    st.check(list(sheets) == list(lib.rows_by_sheet), f'sheets {list(sheets)}')
    for name, df in sheets.items():
        st.check(list(df.columns) == analyze._column_order_for(name), f'{name} columns {list(df.columns)}')
        st.check(len(df) == lib.rows_by_sheet[name], f'{name} has {len(df)} rows, expected {lib.rows_by_sheet[name]}')
        d_col = instruments.SHEET_PROFILES[name].sort_col
        st.check((df[d_col] > 0).all(), f'{name}: a {d_col} is not positive')
    # the site's one shape over the profiles (section 23): frames.unify reads drums at 1x and vocals at Expert
    _, unified = frames.load_frames(header, xlsxs[0])
    st.check(all({'D', 'Level', 'NoteCount'} <= set(df.columns) for df in unified.values()), 'a sheet lacks D, Level or NoteCount after unify')
    st.check((unified['Drums']['D'] == sheets['Drums']['D_1x']).all() and 'D_2x' in unified['Drums'].columns, 'the Drums sheet is not read at 1x')
    st.check((unified['Vocals']['Level'] == 'Expert').all() and 'Level' not in sheets['Vocals'].columns, 'the Vocals sheet is not read as Expert')
    total = pd.concat(unified.values())
    st.check(int(total['Official'].sum()) == lib.official_rows, f"{int(total['Official'].sum())} official rows")
    c3 = total[total['Song Title'] == 'Hard Without Expert']
    st.check(len(c3) == 1 and c3['RemapDiff'].isna().all() and c3['CalcTier'].isna().all(), 'C3 should have no anchor')
    others = total[total['Song Title'] != 'Hard Without Expert']
    st.check(others['RemapDiff'].notna().all() and others['CalcTier'].notna().all(), 'a row lost its anchor')
    st.check(set(total['Code']) <= set(cache['codes']), 'an xlsx code is not in the cache')
    st.check(sum(c.endswith('D') for c in total['Code']) == 2 and sum(c.endswith('V') for c in total['Code']) == 2, 'the drums and vocals rows')
    # section 08: the three song.ini columns, and the year rule
    for name, df in sheets.items():
        at = list(df.columns).index('Release')
        st.check(list(df.columns)[at:at + 4] == ['Release', 'Album', 'Year', 'Genre'] and str(df['Year'].dtype) == 'int64', f'{name}: {list(df.columns)[at:at + 4]} {df["Year"].dtype}')
    by_title = total.drop_duplicates('Song Title').set_index('Song Title')
    st.check(by_title.loc['__SHOUT__ Two Tier', 'Year'] == -1 and by_title.loc['Midi Mirror', 'Year'] == 2007
             and by_title.loc['Keys Only Once', 'Year'] == 2001 and by_title.loc['Grid Runner', 'Year'] == 2026, 'the year rule')
    st.check(by_title.loc['Keys Only Once', 'Album'] == 'Latch, Vol. 2' and by_title.loc['Half Medium', 'Genre'] == 'Rock', 'album with a comma, genre markup stripped')
    # section 10: NotesHash hidden in Excel, read back as text even on the one-row Keys sheet
    import openpyxl
    wb = openpyxl.load_workbook(xlsxs[0], read_only=False)
    for name, df in sheets.items():
        letter = openpyxl.utils.get_column_letter(list(df.columns).index('NotesHash') + 1)
        st.check(wb[name].column_dimensions[letter].hidden, f'{name}: NotesHash column {letter} is not hidden')
    st.check(total['NotesHash'].str.fullmatch('[0-9a-f]{12}').all(), 'a NotesHash is not 12 hex digits')
    _, loaded = frames.load_frames(header, xlsxs[0])
    st.check(all(pd.api.types.is_string_dtype(df['NotesHash']) and pd.api.types.is_string_dtype(df['SongKey']) for df in loaded.values()),
             'a hash column did not load as text')
    a1 = total[(total['Song Title'] == 'Grid Runner') & (total['Level'] == 'Expert') & (total['Type'] == 'Lead')]['NotesHash'].item()
    b5 = total[total['Song Title'] == 'Grid Runner (Live)']['NotesHash'].item()
    st.check(a1 == b5, f'B5 should hash as A1: {a1} vs {b5}')
    # only the cross-pack pair collapses: Hard = Expert differ in Level, Lead = Rhythm in Type
    st.check(re.search(rf'Distinct charts\s+{len(total) - 1:,} of {len(total):,}', st.out), 'the distinct-charts summary line')
    st.done(f"{len(total)} rows on {len(sheets)} sheets, columns as COLUMN_ORDER")

    # ---- a fake link registry (section 13): the first four keyed songs ------------------
    keyed = sorted({s['song_key'] for s in cache['songs'].values() if s.get('song_key')})[:4]
    fake = [fixture.fake_links(i) for i in range(4)]
    links_registry = {'v': 1,
                      'enchor': {keyed[0]: {'md5': fake[0]['md5'], 'chartId': 1, 'via': 'meta'},
                                 keyed[1]: {'md5': fake[1]['md5'], 'chartId': 2, 'via': 'meta'}},
                      'leaderboard': {keyed[0]: {'songHash': fake[0]['songHash'], 'sure': True, 'twins': 1},
                                      keyed[2]: {'songHash': fake[2]['songHash'], 'sure': True, 'twins': 1},
                                      keyed[3]: {'songHash': fake[3]['songHash'], 'sure': False, 'twins': 1}}}
    (work / 'caches' / f'{header}_links.json').write_text(json.dumps(links_registry), encoding='utf-8')

    # ---- publish without bootstrap -------------------------------------------------
    st = Stage('publish (fallback css)', work, env, args.python)
    proc = st.run('publish.py', '--header', header, '--no-bootstrap', expect=None)
    st.check(proc.returncode != 0 and 'not registered' in st.out and not site.exists(),
             'publish should refuse the fixture without its registry, before writing anything')
    st.run('publish.py', '--header', header, '--no-bootstrap', '--packs', str(registry))
    st.check('spreadsheet is from' not in st.out, 'publish complained about the pair')
    st.check(sorted(os.listdir(site)) == sorted(deploy.BUNDLE_TOP), f'site holds {sorted(os.listdir(site))}')
    changelog = (site / 'changelog.html').read_text(encoding='utf-8')
    st.check(changelog.count('<h2') == 3 and f'{len(lib.charted)} songs' in changelog
             and f'{sum(lib.rows_by_sheet.values())} charts' in changelog and not PLACEHOLDER.search(changelog),
             f'changelog: {changelog.count("<h2")} dates')
    # section 20: the library page, its totals the sheets' own, five blocks, the hardest linked into the table
    library = (site / 'library.html').read_text(encoding='utf-8')
    st.check(library.count('<h2>') == 5 and f'{len(lib.charted)} songs' in library
             and f'{sum(lib.rows_by_sheet.values())} charts' in library and library.count('<a href="./?code=') >= 3
             and '<span class="bar" style="width:100.0%">' in library and library.count('<script') == 1
             and not PLACEHOLDER.search(library),
             f'library.html: {library.count("<h2>")} blocks, {library.count(chr(60) + "a href=" + chr(34) + "./?code=")} chart links')
    index = (site / 'index.html').read_text(encoding='utf-8')
    st.check('<a href="changelog.html"' in index, 'strapline is not linked to the changelog')
    st.check('["library.html", "library"]' in index and '["changelog.html", "changelog"]' in index, 'the footer lists the library page and the changelog')
    # A2's title is __SHOUT__ Two Tier on purpose (section 00): placeholder-shaped data
    # must survive in the island while no placeholder survives in the page around it.
    outside = re.sub(r'<script type="application/json" id="fw-boot">.*?</script>', '', index, flags=re.S)
    st.check('id="fw-boot"' in index and not PLACEHOLDER.search(outside), 'index.html island or placeholder')
    st.check(b'__SHOUT__ Two Tier' in (site / boot_island(index)['data']['Guitar']['file']).read_bytes(), 'the placeholder-shaped title did not survive publish')
    st.check('<style>' in index and 'static/bootstrap.' not in index, 'fallback CSS not inlined')
    # five sheets' manifests, the explainer and the words for every column shown: about 29 KB with the fallback CSS
    st.check(len(index) < 31000, f'index.html is {len(index)} bytes with the fallback CSS inlined; the rows should be in data/')
    st.check(f'<title>{html.escape(page.site_title())}</title>' in index and 'Clone Hero' in page.site_title()
             and '<h1 class="h6 mb-0 fw-semibold" id="brand">Fretladder</h1>' in index, 'title and brand')
    m = STRAPLINE.search(index)
    st.check(m and int(m.group(1).replace(',', '')) == len(total), f'strapline {m and m.group(0)}')
    st.check('Less < More' not in index, 'row text reached the island')
    boot = boot_island(index)
    manifest_sheets = boot['data']
    st.check(all(set(v) == {'file', 'rows', 'columns'} and (site / v['file']).is_file() for v in manifest_sheets.values()),
             f'sheet manifest {manifest_sheets}')
    data_files = sorted(p.name for p in (site / 'data').iterdir())
    links_files = [n for n in data_files if n.startswith('links.')]
    st.check(len(links_files) == 1 and boot['links'] == f'data/{links_files[0]}', f'links file {links_files}, boot {boot.get("links")}')
    published_links = json.loads((site / 'data' / links_files[0]).read_bytes())
    st.check(published_links == {'v': 1, 'songs': {keyed[0]: {'enchor': fake[0]['md5'], 'lb': fake[0]['songHash']},
                                                    keyed[1]: {'enchor': fake[1]['md5']}, keyed[2]: {'lb': fake[2]['songHash']}}},
             f'published links {published_links}')
    st.check(sorted(n for n in data_files if not n.startswith('links.')) == sorted(pathlib.PurePosixPath(v['file']).name for v in manifest_sheets.values())
             and all(re.fullmatch(r'[a-z0-9-]+\.[0-9a-f]{8}\.json', n) for n in data_files), f'data/ holds {data_files}')
    for name, entry in manifest_sheets.items():
        blob = (site / entry['file']).read_bytes()
        st.check(entry['file'].split('.')[-2] == __import__('hashlib').sha1(blob).hexdigest()[:8], f'{entry["file"]} is not named by its hash')
        sheet_json = json.loads(blob)
        st.check(sheet_json['columns'] == entry['columns'] and len(sheet_json['rows']) == entry['rows'], f'{name}: manifest and file disagree')
    st.check(boot['sheetOfCode'] == page.sheet_of_code(sheets) and boot['sheetOfCode']['B'] == 'Bass', f"sheetOfCode {boot['sheetOfCode']}")
    guitar = json.loads((site / manifest_sheets['Guitar']['file']).read_bytes())
    gcols = guitar['columns']
    c4 = [r for r in guitar['rows'] if r[gcols.index('Song Title')] == 'Less < More']
    st.check(len(c4) >= 1, 'C4 row missing from the sheet file')
    st.check(b'Less < More' in (site / manifest_sheets['Guitar']['file']).read_bytes(), 'the sheet file is not escaped (it need not be)')
    st.check('Added' in gcols and c4[0][gcols.index('Added')] == '2026-09-09', f"C4 Added {c4[0][gcols.index('Added')] if 'Added' in gcols else None}")
    st.check(gcols[-5:] == ['Added', 'Copies', 'Pct', 'Chart', 'Leaderboard'], f'page-build column order {gcols[-5:]}')
    # section 14: Chart names the host the registry found the song on, Leaderboard is a bit, per song
    by_key = {}
    for r in guitar['rows']:
        by_key.setdefault(r[gcols.index('SongKey')], set()).add((r[gcols.index('Chart')], r[gcols.index('Leaderboard')]))
    st.check(all(len(v) == 1 for v in by_key.values()), 'a song has two answers in the link columns')
    want = {keyed[0]: {('enchor', True)}, keyed[1]: {('enchor', False)}, keyed[2]: {(None, True)}, keyed[3]: {(None, False)}}
    st.check({k: v for k, v in by_key.items() if k in want} == {k: v for k, v in want.items() if k in by_key},
             f'link columns for the four keyed songs: {[(k[:4], by_key.get(k)) for k in keyed]}')
    st.check(all(v == {(None, False)} for k, v in by_key.items() if k not in keyed), 'an unkeyed song has a link')
    # section 10: the planted pair counts as one chart; the within-song repeats are not copies
    def rows_titled(title):
        return [r for r in guitar['rows'] if r[gcols.index('Song Title')] == title]
    pair = rows_titled('Grid Runner (Live)') + [r for r in rows_titled('Grid Runner')
                                                if r[gcols.index('Level')] == 'Expert' and r[gcols.index('Type')] == 'Lead']
    st.check(len(pair) == 2 and all(r[gcols.index('Copies')] == 2 for r in pair) and len({r[gcols.index('Pct')] for r in pair}) == 1,
             f'the B5/A1 pair: {[(r[gcols.index("Copies")], r[gcols.index("Pct")]) for r in pair]}')
    singles = rows_titled('__SHOUT__ Two Tier') + rows_titled('Less < More')
    st.check(singles and all(r[gcols.index('Copies')] == 1 for r in singles), 'Hard = Expert or Lead = Rhythm counted as a copy')
    st.check(all(isinstance(r[gcols.index('Copies')], int) and r[gcols.index('Copies')] >= 1 for r in guitar['rows']), 'a Copies value is not a positive integer')
    st.check({k: v['rows'] for k, v in boot['data'].items()} == lib.rows_by_sheet, 'manifest row counts')
    # section 06: the page draws from the curve JSON; the PNGs publish makes are the social
    # preview, which this library lacks, and each song page's picture (section 22): one per
    # charted song, its first part's Expert graph
    manifest = json.loads((site / 'graph' / 'manifest.json').read_text())
    codes = frames.codes_in(sheets)
    pngs = sorted(p.stem for p in (site / 'graph').glob('*.png'))
    st.check(len(pngs) == len(lib.charted) and sorted(manifest) == pngs and sum(c[-2] == 'X' for c in pngs) >= len(pngs) - 1,   # one fixture song has no Expert: its picture is its Hard chart
             f'{len(pngs)} PNGs for {len(lib.charted)} songs, manifest {len(manifest)}: {pngs[:3]}')
    st.check(f'social preview chart {page.OG_CODE} is not in this spreadsheet' in st.out, 'the social-preview warning')
    st.check(f'social preview {page.OG_CODE}: not in this spreadsheet' in st.out, 'the social-preview banner line')
    curves_manifest = json.loads((site / 'graph' / 'curves-manifest.json').read_text())
    st.check(sorted(curves_manifest) == sorted(codes) and all((site / 'graph' / f'{c}.json').is_file() for c in codes),
             f'curves manifest has {len(curves_manifest)} entries, expected {len(codes)}')
    st.check(re.search(rf'curves: {len(codes)} rendered, 0 unchanged', st.out), 'curves banner')
    about = (site / 'about.html').read_text(encoding='utf-8')
    a = Anchors(); a.feed(about)
    # one script, the theme's (page.THEME_SCRIPT), on every page; nothing else runs on the document pages
    st.check(a.scripts == 1 and page.THEME_SCRIPT in about and a.h2 == len(labels.ABOUT), f'about.html: {a.scripts} scripts, {a.h2} h2')
    same_site = {'./'} | {name for name in deploy.BUNDLE_TOP if name.endswith('.html')}
    st.check(all(h in same_site or urllib.parse.urlparse(h).netloc in ('github.com', 'www.youtube.com', 'youtu.be')
                 for h in a.hrefs), f'about.html anchors {a.hrefs}')
    st.check('methodology.html' in a.hrefs, 'about.html does not link the methodology page')
    # section 12: Methodology.md rendered, its tables checked, no scripts and nothing left unrendered
    method = (site / 'methodology.html').read_text(encoding='utf-8')
    st.check(not PLACEHOLDER.search(method) and method.count('<table') == 6 and method.count('<math display="block"') == 29
             and method.count('<script') == 1 and page.THEME_SCRIPT in method and method.count('<h1') == 1 and '$$' not in method and '**' not in method,
             f'methodology.html: {method.count("<table")} tables, {method.count(chr(36) * 2)} $$')
    st.check(method.count('<ul class="drift">') == 1 and 'in Methodology.md but at' in method, 'the known drift is on the methodology page')
    st.check(not PLACEHOLDER.search(about) and not PLACEHOLDER.search((site / '404.html').read_text()), 'placeholders')
    st.check((site / 'robots.txt').read_text() == page.robots_txt() and 'Sitemap: ' in page.robots_txt(), 'robots.txt')
    # section 16: a page per song under song/, the week class; the sitemap names every page
    song_keys = set()
    for entry in manifest_sheets.values():
        sheet_json = json.loads((site / entry['file']).read_bytes())
        at = sheet_json['columns'].index('SongKey')
        song_keys |= {r[at] for r in sheet_json['rows'] if r[at]}
    song_pages = sorted(p.name for p in (site / 'song').iterdir())
    st.check(song_pages == sorted(f'{k}.html' for k in song_keys) and len(song_pages) == len(lib.charted),
             f'song/ holds {len(song_pages)} pages for {len(song_keys)} keys, {len(lib.charted)} charted songs')
    one = (site / 'song' / song_pages[0]).read_text(encoding='utf-8')
    # section 21: a page, not a redirect: the forward only with a query, the table of every level, the JSON-LD
    st.check(one.count('<script') == 3 and 'og:title' in one and f'?song={song_pages[0][:-5]}' in one
             and 'if(location.search)location.replace(location.search)' in one and 'http-equiv="refresh"' not in one
             and '"@type": "MusicRecording"' in one and one.count('href="./?code=') >= 1 and '<base href="../">' in one
             and len(one) < 6000 and not re.search(r'__(TITLE|FAVICON|META|THEME|KEY|SONG|ARTIST|FACTS|SENTENCES|PICTURE|TABLE|GAME|NOTE|OPEN|LD|BRAND)__', one)   # A2's title is __SHOUT__ on purpose
             and assets.cache_class(f'song/{song_pages[0]}') == assets.CACHE_WEEK,
             f'song page: {len(one)} bytes, {one.count("<script")} scripts')
    # section 22: a page per pack under game/, the lists under list/, the song page's picture and words
    games = sorted(p.name for p in (site / 'game').iterdir())
    lists = sorted(p.name for p in (site / 'list').iterdir())
    st.check(len(games) == 3 and all(re.fullmatch(r'[a-z0-9-]+\.html', g) for g in games), f'game/ holds {games}')
    st.check(len(lists) >= 3 and 'hardest-guitar.html' in lists and 'easiest-guitar.html' in lists, f'list/ holds {lists}')
    st.check('hardest-drums.html' in lists and 'hardest-vocals.html' in lists, f'the drums and vocals lists: {lists}')
    game_page = (site / 'game' / games[0]).read_text(encoding='utf-8')
    st.check('setlist by difficulty' in game_page and '<base href="../">' in game_page and 'href="song/' in game_page
             and game_page.count('<script') == 1 and not PLACEHOLDER.search(game_page.replace('__SHOUT__', '')), f'game page {games[0]}')
    st.check(all(f'<th class="r">{part}</th>' in game_page for part in ('Bass', 'Keys', 'Drums', 'Vocals')), 'the game page has a column per other part')
    # the vocals song page reads Expert on its one level, and the drum chart's picture names its lines
    b2_key = by_folder['B2 - Drum Mid']['song_key']
    b2 = (site / 'song' / f'{b2_key}.html').read_text(encoding='utf-8')
    st.check('On Expert Vocals it scores D' in b2 and 'On Expert Drums it scores D' in b2, 'the song page reads the drums and vocals parts')
    hardest = (site / 'list' / 'hardest-guitar.html').read_text(encoding='utf-8')
    st.check('href="game/' in hardest and 'href="song/' in hardest and 'hardest Guitar Hero and Rock Band songs' in hardest, 'the hardest list')
    st.check('<img src="graph/' in one and 'og:image' in one and 'it scores D' in one and 'href="game/' in one, 'the song page carries its picture, its words and its game')
    songs_index = (site / 'songs.html').read_text(encoding='utf-8')
    st.check(songs_index.count('href="song/') == len(song_pages) and songs_index.count('<script') == 1 and '<h2 id="' in songs_index,
             f'songs.html: {songs_index.count(chr(104) + "ref=" + chr(34) + "song/")} links for {len(song_pages)} pages')
    sitemap = (site / 'sitemap.xml').read_text(encoding='utf-8')
    folders = sum(1 for d in ('song', 'game', 'list') for _ in (site / d).iterdir())
    st.check(sitemap.count('<url>') == 1 + sum(1 for n, _ in labels.DOC_PAGES if (site / n).is_file()) + folders
             and sitemap.count('<lastmod>') == sitemap.count('<url>'), f'sitemap: {sitemap.count("<url>")} urls for {folders} folder pages')
    static = sorted(str(p.relative_to(site / 'static')) for p in (site / 'static').rglob('*') if p.is_file())
    want_static = sorted(k[len('static/'):] for k in assets.load_assets(None)[0])
    st.check(static == want_static, f'static files {static} vs {want_static}')
    st.check(all(re.fullmatch(r'[a-z]+\.[0-9a-f]{8}\.(js|css|svg)', n) for n in static), 'a static file is not hashed')
    st.check(re.search(r'<script type="module" src="static/app\.[0-9a-f]{8}\.js"></script>', index) is not None
             and index.count('<script') == 3 and index.index(page.THEME_SCRIPT) < index.index('<link rel="stylesheet"'), 'the module tag and the theme script before the styles')
    st.check(page.THEME_SCRIPT in (site / '404.html').read_text(encoding='utf-8'), 'the 404 page carries the theme script')
    st.done(f'{len(codes)} graphs, {len(static)} hashed static files, {len(data_files)} sheet files, fallback styles inlined')

    # ---- publish with bootstrap ------------------------------------------------------
    if args.bootstrap_css:
        st = Stage('publish (bootstrap)', work, env, args.python)
        css = pathlib.Path(args.bootstrap_css)
        shutil.copy(css, work / 'caches' / f'bootstrap-{bootstrap.BOOTSTRAP_VERSION}.min.css')
        st.run('publish.py', '--header', header, '--packs', str(registry))
        boot_files = list((site / 'static').glob('bootstrap.*.css'))
        st.check(len(boot_files) == 1 and boot_files[0].read_bytes() == css.read_bytes(), 'hashed bootstrap.css differs from the source')
        index = (site / 'index.html').read_text(encoding='utf-8')
        st.check(f'href="static/{boot_files[0].name}"' in index and '<style>' not in index, 'index.html should link bootstrap')
        st.check(not (site / 'bootstrap.css').exists(), 'a top-level bootstrap.css survived')
        st.check(len(index) < 29000, f'index.html is {len(index)} bytes; the rows should be in data/')
        st.check(re.search(rf'curves: 0 rendered, {len(codes)} unchanged', st.out), 'curves re-rendered on a no-op')
        st.check(len(list((site / 'graph').glob('*.png'))) == len(lib.charted) and re.search(r'pictures: 0 rendered, \d+ unchanged', st.out), 'the song pictures were re-rendered or lost on the second publish')
        st.check(sorted(os.listdir(site)) == sorted(deploy.BUNDLE_TOP), f'site holds {sorted(os.listdir(site))}')
        st.done('bootstrap linked, 0 graphs re-rendered')
    else:
        print('skip publish (bootstrap): no --bootstrap-css given')

    # ---- deploy, dry run -----------------------------------------------------------------
    st = Stage('deploy --dry-run', work, env, args.python)
    log.write_text('')
    st.run('deploy.py', '--env', 'deploy.env', '--dry-run')
    lines = log.read_text().splitlines()
    st.check(len(lines) == 9 and all(l.startswith('s3 sync') and l.endswith('--dryrun') for l in lines), f'aws.log {lines}')
    st.check(f"site/{header}/graph/ s3://fixture-bucket/graph/ --delete --cache-control 'public, max-age=604800'" in lines[0], lines[0])
    st.check(f"site/{header}/song/ s3://fixture-bucket/song/ --delete --cache-control 'public, max-age=604800'" in lines[1], lines[1])
    st.check(f"site/{header}/game/ s3://fixture-bucket/game/ --delete" in lines[2] and f"site/{header}/list/ s3://fixture-bucket/list/ --delete" in lines[3], f'{lines[2]} | {lines[3]}')
    st.check("--exclude 'graph/*' --exclude 'song/*' --exclude 'game/*' --exclude 'list/*' --exclude 'static/*' --exclude 'data/*' --cache-control no-cache" in lines[6], lines[6])
    st.check('--delete' not in lines[4] and '--delete' in lines[7] and 'immutable' in lines[4] and 'immutable' in lines[8], f'{lines[4]} | {lines[7]}')
    st.check('cloudfront' in st.out and 'create-invalidation' not in ''.join(lines), 'invalidation planned but not run')
    st.done('nine dry syncs recorded in order, no invalidation')

    # ---- deploy, wet, against the stub -----------------------------------------------
    st = Stage('deploy --no-publish', work, env, args.python)
    log.write_text('')
    st.run('deploy.py', '--env', 'deploy.env', '--no-publish')
    lines = log.read_text().splitlines()
    samples = deploy.samples(site)
    st.check(len(lines) == 11 + len(samples), f'{len(lines)} aws calls: {lines}')
    st.check(all(l.startswith('s3 sync') and '--dryrun' not in l for l in lines[:7] + lines[9:11]), lines[:11])
    st.check(lines[7] == "cloudfront create-invalidation --distribution-id E1FIXTURE0000 --paths '/*' --output json", lines[7])
    st.check(lines[8] == 'cloudfront wait invalidation-completed --distribution-id E1FIXTURE0000 --id I1FIXTURE0000', lines[8])
    heads = [re.search(r'--key (\S+)', l).group(1) for l in lines[11:]]
    st.check(heads == list(samples), f'head-object keys {heads} vs {list(samples)}')
    # twelve kinds: every folder and type publish writes, the song pictures' PNG among them (section 22)
    st.check(len(samples) == 12 and any(k.endswith('.png') for k in samples)
             and st.out.count('ok  ') >= len(samples) and 'Done' in st.out, f'verify: {len(samples)} samples')
    st.done(f'seven syncs, invalidation and wait, two deletes, {len(samples)} head-objects all ok')

    # ---- deploy guards ---------------------------------------------------------------------
    st = Stage('deploy guards', work, env, args.python)
    (site / 'stray.txt').write_text('x')
    proc = st.run('deploy.py', '--env', 'deploy.env', '--no-publish', expect=None)
    (site / 'stray.txt').unlink()
    st.check(proc.returncode != 0 and 'holds files publish did not write' in st.out, 'stray file accepted')
    (work / 'leak.env').write_text('FRETWORK_BUCKET=b\nAWS_SECRET_ACCESS_KEY=x\n')
    proc = st.run('deploy.py', '--env', 'leak.env', '--dry-run', expect=None)
    st.check(proc.returncode != 0 and 'contains AWS credentials' in st.out, 'credential in .env accepted')
    st.done('a stray file and a credential are both refused')

    # ---- check_site against the served bundle (section 01) ---------------------------------
    st = Stage('check_site', work, env, args.python)
    port = free_port()
    server = subprocess.Popen([args.python, '-m', 'http.server', str(port), '--bind', '127.0.0.1',
                               '--directory', str(site)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            try:
                urllib.request.urlopen(f'http://127.0.0.1:{port}/robots.txt', timeout=1).read(1)
                break
            except Exception:
                time.sleep(0.1)
        proc = st.run('tools/check_site.py', f'http://127.0.0.1:{port}', expect=None)
    finally:
        server.terminate()
        server.wait(timeout=10)
    st.check(proc.returncode == 0, f'check_site exited {proc.returncode}')
    st.check(st.out.count('\nok  ') + st.out.startswith('ok  ') == 10 and st.out.count('skip ') == 3, 'expected 10 ok and 3 skip')
    st.done('9 ok, 3 skip against the fixture bundle')

    # ---- section 00: the in-process assertions that need outputs ---------------------------
    st = Stage('section 00', work, env, args.python)
    renderer = GraphRenderer(header, caches[0])
    drums_code = next(c for c in cache['codes'] if c.endswith('D'))
    vocals_code = next(c for c in cache['codes'] if c.endswith('V'))
    guitar_code = next(c for c in cache['codes'] if c.endswith('XG'))
    for code in (drums_code, vocals_code, guitar_code):
        st.check(renderer.lookup(code) is not None, f'lookup({code}) should resolve')
    from functions import packs as packs_mod
    resolved = packs_mod.resolve(cache, packs_mod.load(registry))
    built = page.build(header, xlsxs[0], None, public=True, resolved=resolved, links_path=work / 'caches' / f'{header}_links.json')
    httpd = MetricsServer(0, {'/' + n: d for n, d in built.files.items()}, renderer)
    port = httpd.server_address[1]
    import threading
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        def get(path):
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{port}{path}') as r:
                    return r.status, r.read()
            except urllib.error.HTTPError as e:
                return e.code, e.read()
        for path, want in (('/about.html', 200), ('/changelog.html', 200), ('/library.html', 200), ('/robots.txt', 200),
                           (f'/song/{song_pages[0]}', 200), ('/songs.html', 200), ('/sitemap.xml', 200), ('/nope', 404)):
            status, body_bytes = get(path)
            st.check(status == want, f'serve {path} -> {status}')
            if want == 200:
                st.check(body_bytes == (site / path.lstrip('/')).read_bytes(), f'serve {path} differs from publish')
        # every family renders a PNG on demand and answers the published curve file (section 23)
        for code, family, lines in ((drums_code, 'drums', ['hps', 'tps', 'kps']), (vocals_code, 'vocals', ['pps', 'sps', 'perc']),
                                    (guitar_code, 'fret', ['nps', 'vps'])):
            status, body_bytes = get(f'/graph/{code}.png')
            st.check(status == 200 and body_bytes.startswith(b'\x89PNG'), f'serve {family} graph -> {status}')
            status, body_bytes = get(f'/graph/{code}.json')
            doc = json.loads(body_bytes) if status == 200 else {}
            st.check(status == 200 and doc.get('v') == 2 and doc.get('family') == family and list(doc.get('series', {})) == lines
                     and (site / 'graph' / f'{code}.json').read_bytes() == body_bytes,
                     f'serve {family} curve json -> {status} {doc.get("family")} {list(doc.get("series", {}))}, equal to the published file')
        for name, data in built.files.items():
            if name.startswith(('static/', 'data/')):
                st.check((site / name).read_bytes() == data, f'{name} differs between serve and publish')
    finally:
        httpd.shutdown()
        httpd.server_close()
    st.done('every family resolves, serve answers the same bytes publish wrote')

    print(f'\nall stages passed ({work})')


if __name__ == '__main__':
    main()
