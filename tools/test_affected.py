"""Which tests a change touches (internal; tools/test.py affected): from the files changed to the test files that depend
on them, by the imports of the code.

§1 PURPOSE
    After a small change the whole set takes 20 minutes, most of it the scenarios of the window. A change of one reader
    or one window should run its own tests in a minute: the tests that import it — directly or through other modules —
    and the scenarios of the window of its section. This is a first signal, never «the tests passed»: the full set stays
    before a push and a release (AGENTS.md).
§2 RULES
    1. Changed files: those of `git diff` against a base (by default: the uncommitted changes, staged or not, and the new
       files; with nothing uncommitted — the last commit), as paths of the repository.
    2. A module of the program changed (azimuth/, hub/, modules/, tools/): every test file of the plain tests (not
       tests/gui) whose imports reach it, directly or through other modules of the program, the conftest of the tests
       included — but not through the main window (WINDOW_MODULES): it imports every section, so a dialog that borrows
       its styles would tie its tests to the whole program; those tests are the window's (rule 3).
    3. The scenarios of the window (tests/gui and tests/hub build the whole window, which imports nearly every module)
       are chosen otherwise: the file of the window of the section of the module (WINDOW), and every file of the window
       that imports the module itself. A module shared by all the sections (SHARED) runs every scenario of the window.
    4. A test file changed — itself; tests/conftest.py, tests/gui_support.py — all the tests (they are under every
       test); a file of tests/data/<set>/ — the test files that name that set; azimuth/locale/*.json — the tests of the
       translations and of the window settings; documents (*.md), pictures and the rest — nothing, said so.
    5. What is chosen and why is printed; tools/test.py runs it as one pytest run.
§3 INTERFACE
    changed(base=None) -> [path]; graph() -> {module: {modules it imports}}; select(paths) -> (files, reasons, notes).
§7 TESTS tests/core/test_test_affected.py.
"""

import ast
from functools import lru_cache
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parent.parent
CODE = ('azimuth', 'hub', 'modules', 'tools', 'tests')
WINDOW_DIRS = ('tests/gui/', 'tests/hub/')
# the scenarios of the window of each section: a module under the key runs these files
WINDOW = {
    'modules/compass/': ('tests/gui/test_gui_compass.py', 'tests/gui/test_model_styles.py',
                         'tests/gui/test_aimed_placement.py'),
    'modules/sextant/': ('tests/gui/test_gui_sextant.py',),
    'modules/spectrum/': ('tests/gui/test_gui_spectrum.py', 'tests/gui/test_gui_multiwfn.py',
                          'tests/gui/test_spectrum_polish.py', 'tests/gui/test_spectrum_layout.py'),
    'azimuth/project': ('tests/gui/test_gui_files.py',),
    'azimuth/runtime/': ('tests/gui/test_gui_files.py',),
    'hub/': ('tests/hub/test_hub.py',),
    'modules/atlas/': (),
}
# modules every section draws through: a change of one of them can break any scenario of the window
SHARED = ('azimuth/app.py', 'azimuth/ui.py', 'azimuth/polish.py', 'azimuth/i18n.py', 'azimuth/theme_sheet.py',
          'azimuth/window_port.py', 'azimuth/controls.py', 'hub/window.py', 'hub/menus.py')
EVERYTHING = ('tests/conftest.py', 'tests/gui_support.py', 'pytest.ini', 'requirements.txt', 'requirements-dev.txt')
TRANSLATIONS = ('tests/core/test_i18n_patterns.py', 'tests/gui/test_gui_settings.py')


def changed(base=None):
    """Paths changed against base; base None — the uncommitted changes, else the last commit."""
    def run(*args):
        done = subprocess.run(['git', *args], cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
        return [line.strip() for line in done.stdout.splitlines() if line.strip()] if done.returncode == 0 else []

    if base:
        return sorted(set(run('diff', '--name-only', base)) | set(run('ls-files', '--others', '--exclude-standard')))
    found = set(run('diff', '--name-only', 'HEAD')) | set(run('ls-files', '--others', '--exclude-standard'))
    return sorted(found) or sorted(run('diff', '--name-only', 'HEAD~1', 'HEAD'))


def module_name(path):
    path = Path(path)
    parts = list(path.with_suffix('').parts)
    if parts[-1] == '__init__':
        parts = parts[:-1]
    return '.'.join(parts)


@lru_cache(maxsize=1)
def _files():
    found = {}
    for top in CODE:
        for path in (ROOT / top).rglob('*.py'):
            relative = path.relative_to(ROOT).as_posix()
            if '__pycache__' in relative or '/atlas_v2/quas_atlas/web/' in relative:
                continue
            found[module_name(relative)] = relative
    return found


def _imports(path, name):
    """The modules of the program a file imports (anywhere in it, functions included)."""
    files = _files()
    try:
        tree = ast.parse((ROOT / path).read_text(encoding='utf-8'))
    except (SyntaxError, UnicodeDecodeError):
        return set()
    package = name if path.endswith('__init__.py') else name.rpartition('.')[0]
    out = set()
    for node in ast.walk(tree):
        targets = []
        if isinstance(node, ast.Import):
            targets = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ''
            if node.level:
                parent = package.split('.') if package else []
                parent = parent[:len(parent) - node.level + 1] if node.level > 1 else parent
                base = '.'.join(parent + ([base] if base else []))
            targets = [base] + [f'{base}.{alias.name}' for alias in node.names]
        for target in targets:
            while target:  # the module itself, else its package
                if target in files:
                    out.add(target)
                    break
                target = target.rpartition('.')[0]
    out.discard(name)
    return out


@lru_cache(maxsize=1)
def graph():
    return {name: _imports(path, name) for name, path in _files().items()}


# the main window imports every section: a test that builds it (Studio) would depend on the whole program; such
# dependencies are those of the window — rule 3 — and the walk does not go through these modules. No module of the
# program imports the window any more (atomic_write lives in azimuth/files.py), only the hub and the tools.
WINDOW_MODULES = ('azimuth.app', 'hub.window')


def _reach(start):
    """Every module start imports, directly or through others (not through the main window: WINDOW_MODULES)."""
    links, seen, stack = graph(), set(), [start]
    while stack:
        for nxt in links.get(stack.pop(), ()):
            if nxt not in seen:
                seen.add(nxt)
                if nxt not in WINDOW_MODULES:
                    stack.append(nxt)
    return seen


def _tests():
    return sorted(p for n, p in _files().items() if p.startswith('tests/') and Path(p).name.startswith('test_'))


def select(paths):
    """(test files, {file: reason}, notes) for the changed paths."""
    files, links = _files(), graph()
    by_path = {p: n for n, p in files.items()}
    tests = _tests()
    conftest = _reach(module_name('tests/conftest.py')) if 'tests.conftest' in files else set()
    reach = {t: _reach(by_path[t]) | conftest for t in tests}
    chosen, notes = {}, []

    def take(test, why):
        if test in reach or (ROOT / test).is_file():
            chosen.setdefault(test, why)

    for path in paths:
        if path in EVERYTHING:
            for t in tests:
                take(t, f'{path} — под всеми тестами')
            continue
        if path.startswith('tests/data/'):
            name = path.split('/')[2]
            hits = [t for t in tests if re.search(r"['\"/]" + re.escape(name) + r"['\"/]",
                                                  (ROOT / t).read_text(encoding='utf-8'))]
            for t in hits:
                take(t, f'данные {name}')
            if not hits:
                notes.append(f'{path}: ни один тест не называет набор {name}')
            continue
        if path.startswith('tests/') and path.endswith('.py'):
            if Path(path).name.startswith('test_'):
                take(path, 'изменён сам тест')
            else:  # a helper of the tests: the tests that import it
                helper = by_path.get(path)
                for t in tests:
                    if helper in reach[t]:
                        take(t, f'импортирует {path}')
            continue
        if path.startswith('azimuth/locale/') and path.endswith('.json'):
            for t in TRANSLATIONS:
                take(t, 'переводы')
            continue
        if not path.endswith('.py') or path not in by_path:
            notes.append(f'{path}: не код программы — тесты не выбраны')
            continue
        name = by_path[path]
        for t in tests:
            window = t.startswith(WINDOW_DIRS)
            if not window and name in reach[t]:
                take(t, f'зависит от {path}')
            elif window and name in links.get(by_path[t], set()):
                take(t, f'импортирует {path}')
        if path in SHARED:
            for t in tests:
                if t.startswith(WINDOW_DIRS):
                    take(t, f'{path} — общий для всех окон')
        for prefix, scenarios in WINDOW.items():
            if path.startswith(prefix):
                for t in scenarios:
                    take(t, f'окно раздела {prefix.rstrip("/")}')
    return sorted(chosen), chosen, notes
