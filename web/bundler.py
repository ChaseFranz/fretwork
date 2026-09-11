"""
BUNDLER - concatenates the page's ES modules into one file, and refuses anything it cannot prove safe

The 17 modules under web/static/js use one import form (`import { a, b } from
"./x.js";`) and one export form (`export` on a const, let, function or class
declaration), and no two modules declare the same top-level name. Under those
conditions a bundle is the modules in dependency order with the import lines
deleted and the `export ` prefixes removed: module scope becomes one scope,
every name resolves to the same declaration it did before, and evaluation
order is the post-order ES modules would use. Nothing else is rewritten, so
string literals (the YouTube origin, the rich() markup) survive byte for byte.

Anything outside that whitelist raises BundleError naming the file and line:
the fix is to write the plain form, not to extend this. Stdlib only; no Node.

    python -m web.bundler > app.mjs        # print the bundle
"""

import pathlib
import re
import sys

IMPORT = re.compile(r'^import\s*\{([^}]*)\}\s*from\s*"\./([\w.-]+\.js)"\s*;\s*$', re.M)
IMPORT_ANY = re.compile(r'^import\b', re.M)
EXPORT_DECL = re.compile(r'^export\s+(?:const|let|function|class)\s+([A-Za-z_$][\w$]*)', re.M)
EXPORT_ANY = re.compile(r'^export\b', re.M)
DECL = re.compile(r'^(?:export\s+)?(?:const|let|var|function|class)\s+([A-Za-z_$][\w$]*)', re.M)
DYNAMIC_IMPORT = re.compile(r'\bimport\s*\(')


class BundleError(ValueError):
    pass


def line_of(text, pos):
    return text.count('\n', 0, pos) + 1


def parse(path):
    """(imports: {file: [names]}, exports: {names}, declared: {names}, body without imports)."""
    text = path.read_text(encoding='utf-8')
    imports = {}
    for m in IMPORT.finditer(text):
        names = [n.strip() for n in m.group(1).split(',') if n.strip()]
        for n in names:
            if ' as ' in n:
                raise BundleError(f'{path.name}:{line_of(text, m.start())}: renamed import {n!r} is not supported')
        imports.setdefault(m.group(2), []).extend(names)
    stripped = IMPORT.sub('', text)
    for m in IMPORT_ANY.finditer(stripped):
        raise BundleError(f'{path.name}:{line_of(stripped, m.start())}: only `import {{ a, b }} from "./x.js";` is supported')
    if DYNAMIC_IMPORT.search(text):
        m = DYNAMIC_IMPORT.search(text)
        raise BundleError(f'{path.name}:{line_of(text, m.start())}: dynamic import() is not supported')
    exports = set()
    for m in EXPORT_ANY.finditer(stripped):
        decl = EXPORT_DECL.match(stripped, m.start())
        if not decl:
            raise BundleError(f'{path.name}:{line_of(stripped, m.start())}: only `export const|let|function|class name` is supported')
        exports.add(decl.group(1))
    declared = set(DECL.findall(stripped))
    return imports, exports, declared, stripped


def order(modules, entry):
    """Depth-first post-order from the entry: a module comes after everything it imports."""
    seen, done, out = set(), set(), []

    def visit(name, chain):
        if name in done:
            return
        if name in seen:
            raise BundleError('import cycle: ' + ' -> '.join(chain + [name]))
        seen.add(name)
        for dep in modules[name][0]:
            if dep not in modules:
                raise BundleError(f'{name} imports {dep}, which does not exist')
            visit(dep, chain + [name])
        done.add(name)
        out.append(name)

    visit(entry, [])
    return out


def bundle(static_dir, entry='js/main.js'):
    js_dir = pathlib.Path(static_dir) / pathlib.Path(entry).parent
    modules = {p.name: parse(p) for p in sorted(js_dir.glob('*.js'))}
    entry_name = pathlib.Path(entry).name
    if entry_name not in modules:
        raise BundleError(f'entry {entry} not found under {js_dir}')
    declared_in = {}
    for name, (imports, exports, declared, _) in modules.items():
        for dep, names in imports.items():
            for n in names:
                if dep in modules and n not in modules[dep][1]:
                    raise BundleError(f'{name} imports {n!r} from {dep}, which does not export it')
        for n in declared:
            if n in declared_in:
                raise BundleError(f'top-level name {n!r} is declared in both {declared_in[n]} and {name}')
            declared_in[n] = name
    parts = []
    for name in order(modules, entry_name):
        body = modules[name][3]
        body = re.sub(r'^export\s+', '', body, flags=re.M)
        parts.append(f'// ---- {name}\n{body.strip()}\n')
    return ('\n'.join(parts)).encode('utf-8')


def main():
    static_dir = pathlib.Path(__file__).resolve().parent / 'static'
    try:
        sys.stdout.buffer.write(bundle(static_dir))
    except BundleError as exc:
        sys.exit(f'bundle: {exc}')


if __name__ == '__main__':
    main()
