"""
LINKS_COMMON - what the offline link lookups share

The two lookup tools (enchor_lookup.py, leaderboards_lookup.py) and the
one-off probe resolve, away from the page, where each rated chart is
published (Chorus Encore) and where its Clone Hero leaderboard is. This module
holds the pieces they share: a pacer that keeps under the services' 50
requests a minute and honours their rate-limit headers, the HTTP calls (both
injectable, so tests never touch the network), the registry file's load and
atomic save, the matcher ported from the leaderboards userscript, and the
instrument vocabulary bridge.

Stdlib plus the repo's own modules, nothing added to requirements.txt. The
sys.path line makes `import functions` work when a tool is run as
`python tools/x.py` from any directory (tools/ is then sys.path[0], not the
repo root).
"""

import json
import os
import pathlib
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from functions import instruments  # noqa: E402

USER_AGENT = 'fretladder-links/1 (+https://fretladder.com)'
TIMEOUT = 30
REGISTRY_VERSION = 1

ENCHOR_API = 'https://api.enchor.us'
LEADERBOARDS_API = 'https://api.clonehero.net'

MD5 = re.compile(r'^[a-f0-9]{32}$')
SONG_HASH = re.compile(r'^[A-Za-z0-9_-]{40,50}$')


class RateLimited(Exception):
    """Three 429s in a row: the caller saves what it has and stops."""


class Pacer:
    """Spaces requests to per_minute and sleeps through a rate-limit reset.

    clock and sleep are injectable for tests. reset headers are epoch seconds
    (Enchor sends them that way); a value under 1e9 is taken as a delta.
    """

    def __init__(self, per_minute=48, clock=time.time, sleep=time.sleep):
        self.gap = 60.0 / per_minute
        self.clock, self.sleep = clock, sleep
        self.last = None
        self.waited = 0.0
        self.requests = 0
        self.rate_limited = 0

    def wait(self):
        if self.last is not None:
            due = self.last + self.gap
            now = self.clock()
            if now < due:
                self.sleep(due - now)
                self.waited += due - now
        self.last = self.clock()
        self.requests += 1

    def _until(self, reset):
        try:
            value = float(reset)
        except (TypeError, ValueError):
            return 60.0
        now = self.clock()
        return max(1.0, (value - now if value > 1e9 else value) + 1)

    def after(self, headers):
        """Honour x-ratelimit-remaining: 0 by sleeping to the reset."""
        h = {k.lower(): v for k, v in dict(headers).items()}
        if h.get('x-ratelimit-remaining') == '0':
            delay = self._until(h.get('x-ratelimit-reset'))
            self.sleep(delay)
            self.waited += delay

    def limited(self, headers):
        """A 429: sleep 60 s or to the reset; the third in a row aborts."""
        self.rate_limited += 1
        if self.rate_limited >= 3:
            raise RateLimited('three 429 responses in a row')
        h = {k.lower(): v for k, v in dict(headers).items()}
        delay = self._until(h.get('x-ratelimit-reset')) if 'x-ratelimit-reset' in h else 60.0
        self.sleep(delay)
        self.waited += delay


def _request(url, body=None):
    data = json.dumps(body).encode('utf-8') if body is not None else None
    req = urllib.request.Request(url, data=data, headers={
        'User-Agent': USER_AGENT, 'Accept': 'application/json',
        **({'Content-Type': 'application/json'} if body is not None else {})})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, dict(r.headers.items()), json.loads(r.read().decode('utf-8') or 'null')
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            payload = json.loads(raw.decode('utf-8')) if raw else None
        except ValueError:
            payload = raw.decode('utf-8', 'replace')
        return e.code, dict(e.headers.items()), payload


def get_json(url):
    """(status, headers, json) for a GET."""
    return _request(url)


def post_json(url, body):
    """(status, headers, json) for a JSON POST."""
    return _request(url, body)


def call(pacer, fn, *args):
    """One paced request through fn, retrying on 429 as the pacer allows."""
    while True:
        pacer.wait()
        status, headers, payload = fn(*args)
        if status == 429:
            pacer.limited(headers)
            continue
        pacer.rate_limited = 0
        pacer.after(headers)
        return status, headers, payload


# --- the registry -----------------------------------------------------------------

def registry_path(header):
    import config
    return pathlib.Path(config.OUTPUT_DIRS['cache']) / f'{header}_links.json'


def load_registry(path):
    path = pathlib.Path(path)
    if not path.is_file():
        return {'v': REGISTRY_VERSION, 'enchor': {}, 'leaderboard': {}}
    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('v') != REGISTRY_VERSION:
        raise ValueError(f'{path}: registry version {data.get("v")!r}, expected {REGISTRY_VERSION}')
    data.setdefault('enchor', {})
    data.setdefault('leaderboard', {})
    return data


def save_registry(path, data):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(data, indent=1, sort_keys=True), encoding='utf-8')
    os.replace(tmp, path)


# --- the matcher, ported from the leaderboards userscript -----------------------------

def norm(text):
    """Lower-case, accents stripped, punctuation out, spaces collapsed."""
    s = unicodedata.normalize('NFKD', str(text or ''))
    s = ''.join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r'\(.*?\)|\[.*?\]', ' ', s)          # a bracketed tag is not part of the name
    s = re.sub(r'[^a-z0-9]+', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def song_key(title, artist):
    return norm(title) + '|' + norm(artist)


def pick(row, candidates, counts=None):
    """The userscript's choice among the boards sharing a title and artist.

    row: {'title', 'artist', 'charter', 'note_count'}; candidates: [{'songHash',
    'name', 'artist', 'charter'}]; counts: {songHash: board Expert note count}
    for the candidates a /scores call was made for. Returns (songHash | None,
    sure, twins): a lone candidate whose charter matches is sure; among
    several, the ones whose board count equals the row's are the twins and the
    first is taken; a lone charter-miss is unsure here (confirm_lone decides it).
    """
    pool = [c for c in candidates if song_key(c.get('name'), c.get('artist')) == song_key(row['title'], row['artist'])]
    if not pool:
        return None, False, 0
    charter = norm(row.get('charter'))
    same_charter = [c for c in pool if norm(c.get('charter')) == charter]
    if len(pool) == 1:
        return pool[0]['songHash'], bool(same_charter), 1
    counts = counts or {}
    by_count = [c for c in pool if counts.get(c['songHash']) == row.get('note_count')]
    if by_count:
        return by_count[0]['songHash'], True, len(by_count)
    if len(same_charter) == 1:
        return same_charter[0]['songHash'], False, 1
    return None, False, 0


def confirm_lone(row, candidate, board_count):
    """A lone candidate whose charter text differs: sure when the board's Expert note count equals the row's."""
    return board_count is not None and board_count == row.get('note_count')


# --- instruments ---------------------------------------------------------------------

TYPE_TO_INSTRUMENT = {label: key for key, label in instruments.TYPE_LABELS.items()}


def type_to_instrument(type_label):
    return TYPE_TO_INSTRUMENT.get(type_label)
