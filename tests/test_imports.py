"""Every module imports, and serve's startup path stays clear of matplotlib and openpyxl."""

import importlib
import pathlib
import subprocess
import sys
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ['build', 'analyze', 'render', 'serve', 'publish', 'deploy', 'config']
PACKAGES = ['web', 'functions', 'parsers']


def modules():
    names = list(SCRIPTS)
    for pkg in PACKAGES:
        for path in sorted((REPO / pkg).glob('*.py')):
            if path.name != '__init__.py':
                names.append(f'{pkg}.{path.stem}')
    return names


class ImportTest(unittest.TestCase):

    def test_every_module_imports(self):
        names = modules()
        self.assertGreaterEqual(len(names), 30, names)
        for name in names:
            with self.subTest(module=name):
                importlib.import_module(name)

    # CLAUDE.md: matplotlib (functions/plot.py) and openpyxl (functions/xlsx_format.py)
    # must stay off the server's startup import path. A fresh interpreter, so this
    # test's own imports cannot pollute the answer.
    def test_serve_startup_path_is_clean(self):
        code = ('import sys; import serve, web.server, web.handler, web.page, web.graph; '
                'print(sorted(m for m in ("matplotlib", "openpyxl") if m in sys.modules))')
        out = subprocess.run([sys.executable, '-c', code], cwd=REPO, capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(), '[]')


if __name__ == '__main__':
    unittest.main()
