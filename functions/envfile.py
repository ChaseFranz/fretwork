"""
ENVFILE - reads a .env file into a dict, nothing more

KEY=VALUE per line, # comments (whole-line or after an unquoted value),
optional single or double quotes around the value. No variable expansion,
no export keyword, no dependency. A UTF-8 BOM is tolerated.
"""

import pathlib


def load(path):
    path = pathlib.Path(path)
    if not path.is_file():
        return {}
    values = {}
    for raw in path.read_text(encoding='utf-8-sig').splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in '"\'':
            value = value[1:-1]
        else:
            value = value.split(' #', 1)[0].rstrip()
        values[key.strip()] = value
    return values
