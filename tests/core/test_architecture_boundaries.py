"""The boundaries of the architecture, checked by the imports.

Rules:
  1. The scientific and the runtime layers — chemistry, analysis, readers, wave functions, the runtime of projects
     and calculations, the storage, the server and the runner of Sextant — import no Qt and no VTK, not even inside a
     function, and no module of the interface of the program (a module that imports Qt at its top).
  2. They can be imported with Qt and VTK absent (a fresh interpreter with them blocked): no hidden dependency through
     another module either.
  3. SQLite is opened only by the storage of projects (azimuth/project_store.py); the database is written only
     through it.
Exceptions are listed here with their reason; a new one is a decision, not a silent change.
Oracle: the syntax tree of every file (ast), and a subprocess importing the modules with a finder that refuses Qt.
"""

import ast
import subprocess
import sys
from pathlib import Path

from tests.program_files import moved_methods, python_files

ROOT = Path(__file__).resolve().parents[2]
GUI = ('PySide6', 'shiboken6', 'vtk', 'vtkmodules')
PROTECTED = (
    'modules/compass/chemistry',
    'modules/spectrum/analysis',
    'modules/spectrum/readers',
    'modules/spectrum/wavefunction',
    'azimuth/runtime',
)
PROTECTED_FILES = (
    'azimuth/core.py', 'azimuth/core_bases.py', 'azimuth/core_isotopes.py', 'azimuth/projects.py', 'azimuth/project_store.py', 'azimuth/project_folders.py',
    'modules/sextant/runner.py', 'modules/sextant/remote_job.py', 'modules/sextant/cluster.py',
    'modules/sextant/ssh.py', 'modules/sextant/inputs.py', 'modules/sextant/batch.py', 'modules/sextant/history.py',
    'modules/sextant/remote.py', 'modules/compass/constraints.py', 'azimuth/headless.py', 'azimuth/headless_server.py', 'azimuth/files.py',
    'azimuth/handbook.py',
)
EXCEPTIONS = {
    # file: reason
}
SQLITE_ALLOWED = {'azimuth/project_store.py'}


def files():
    found = [ROOT / f for f in PROTECTED_FILES]
    for folder in PROTECTED:
        found.extend(sorted((ROOT / folder).rglob('*.py')))
    return [p for p in found if '__pycache__' not in p.parts and p.relative_to(ROOT).as_posix() not in EXCEPTIONS]


def module_of(path):
    parts = list(path.relative_to(ROOT).with_suffix('').parts)
    return '.'.join(parts[:-1] if parts[-1] == '__init__' else parts)


def imports(path):
    """(module, line) of every import of the file, at any depth (a function too); relative ones resolved."""
    tree = ast.parse(path.read_text(encoding='utf-8'))
    package = module_of(path).rsplit('.', 1)[0] if path.name != '__init__.py' else module_of(path)
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += [(a.name, node.lineno) for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package.split('.')[: len(package.split('.')) - node.level + 1]
                name = '.'.join(base + ([node.module] if node.module else []))
            else:
                name = node.module or ''
            found.append((name, node.lineno))
            found += [(f'{name}.{a.name}', node.lineno) for a in node.names]
    return found


def interface_modules():
    """The modules of the program that import Qt or VTK at their top: the interface."""
    found = set()
    for path in python_files():
        rel = path.relative_to(ROOT).as_posix()
        if rel.startswith(('tests/', '.venv/', 'tools/')) or '__pycache__' in rel:
            continue
        try:
            tree = ast.parse(path.read_text(encoding='utf-8'))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in tree.body:
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else (
                [node.module or ''] if isinstance(node, ast.ImportFrom) else [])
            if any(n.split('.')[0] in GUI for n in names):
                found.add(module_of(path))
                break
    return found


def test_the_scientific_and_runtime_layers_import_no_interface():
    gui = interface_modules()
    broken = []
    for path in files():
        for name, line in imports(path):
            if name.split('.')[0] in GUI or name in gui:
                broken.append(f'{path.relative_to(ROOT).as_posix()}:{line} imports {name}')
    assert not broken, 'An interface dependency in a protected layer:\n' + '\n'.join(broken)


def test_they_import_with_qt_and_vtk_absent():
    names = sorted({module_of(p) for p in files()})
    script = (
        'import importlib, importlib.abc, sys\n'
        f'GUI = {GUI!r}\n'
        'class Refuse(importlib.abc.MetaPathFinder):\n'
        '    def find_spec(self, name, path, target=None):\n'
        '        if name.split(".")[0] in GUI:\n'
        '            raise ImportError("blocked: " + name)\n'
        'sys.meta_path.insert(0, Refuse())\n'
        f'sys.path.insert(0, {str(ROOT)!r})\n'
        'bad = []\n'
        f'for name in {names!r}:\n'
        '    try:\n'
        '        importlib.import_module(name)\n'
        '    except Exception as exc:\n'
        '        if "blocked: " in str(exc):  # another missing package (rdkit here) is not this rule\n'
        '            bad.append(f"{name}: {exc}")\n'
        'print("\\n".join(bad))\n'
    )
    done = subprocess.run([sys.executable, '-c', script], capture_output=True, text=True, timeout=300, cwd=ROOT)
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == '', 'Not importable without Qt and VTK:\n' + done.stdout


def test_only_the_storage_opens_sqlite():
    broken = []
    for path in python_files():
        rel = path.relative_to(ROOT).as_posix()
        if rel.startswith(('tests/', '.venv/', 'tools/')) or '__pycache__' in rel or rel in SQLITE_ALLOWED:
            continue
        try:
            found = imports(path)
        except (SyntaxError, UnicodeDecodeError):
            continue
        broken += [f'{rel}:{line}' for name, line in found if name.split('.')[0] == 'sqlite3']
    assert not broken, 'sqlite3 outside azimuth/project_store.py:\n' + '\n'.join(broken)


def test_the_rules_find_what_they_forbid(tmp_path):
    # the oracle of the oracle: a file with a lazy Qt import and one with a relative import are read right
    lazy = tmp_path / 'lazy.py'
    lazy.write_text('def f():\n    from PySide6.QtWidgets import QWidget\n    return QWidget\n', encoding='utf-8')
    tree = ast.parse(lazy.read_text(encoding='utf-8'))
    names = [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
    assert names == ['PySide6.QtWidgets']
    found = dict(imports(ROOT / 'modules/spectrum/analysis/ir_spectrum.py'))
    assert 'azimuth.i18n' in found and not any(n.split('.')[0] in GUI for n in found)
    assert 'modules.sextant.workspace' in interface_modules() and 'azimuth.app' in interface_modules()


# the mixins of the window only ever get fewer (the roadmap of 2026-11-09, stage 5). The ceiling is lowered
# with each part taken out; a new mixin needs a reason here.
MIXIN_CEILING = {
    ('azimuth/app.py', 'Studio'): 5,
    ('modules/compass/workspace.py', 'CompassWorkspace'): 2,
    ('modules/sextant/workspace.py', 'SextantWorkspace'): 0,
    ('modules/spectrum/workspace.py', 'SpectrumWorkspace'): 0,
}


def test_the_window_gets_no_new_mixins():
    found = {}
    for (rel, name), ceiling in MIXIN_CEILING.items():
        tree = ast.parse((ROOT / rel).read_text(encoding='utf-8'))
        (cls,) = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == name]
        found[(rel, name)] = len(cls.bases)
    assert all(found[k] <= v for k, v in MIXIN_CEILING.items()), found
    assert found[('modules/compass/workspace.py', 'CompassWorkspace')] == MIXIN_CEILING[
        ('modules/compass/workspace.py', 'CompassWorkspace')], 'lower the ceiling to what is left'


def test_a_class_kept_in_several_files_finds_its_methods():
    # the oracle of moved_methods: BatchTool takes batch_complete from modules/sextant/batch_results.py
    tree = ast.parse((ROOT / 'modules/sextant/batch_actions.py').read_text(encoding='utf-8'))
    (cls,) = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'BatchTool']
    assert 'batch_complete' in {f.name for f in moved_methods(tree, cls)}


def test_a_tool_reaches_the_window_only_through_its_port():
    # a class with PORT (azimuth/window_port.WindowPort) uses self.w.<name> only for the names of PORT, and
    # gives the window to Qt only as self.w.widget — never itself (a tool is not a QWidget); its methods kept in
    # other files (moved_methods) too
    broken = []
    for path in sorted((ROOT / 'modules').rglob('*.py')):
        tree = ast.parse(path.read_text(encoding='utf-8'))
        for cls in [n for n in tree.body if isinstance(n, ast.ClassDef)]:
            port = next((n for n in cls.body if isinstance(n, ast.Assign)
                         and any(isinstance(t, ast.Name) and t.id == 'PORT' for t in n.targets)), None)
            if port is None:
                continue
            names = set(ast.literal_eval(port.value))
            for node in [n for body in [cls, *moved_methods(tree, cls)] for n in ast.walk(body)]:
                if (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Attribute)
                        and isinstance(node.value.value, ast.Name) and node.value.value.id == 'self'
                        and node.value.attr == 'w' and node.attr not in names | {'widget', 'has'}):
                    broken.append(f'{path.relative_to(ROOT)}:{node.lineno} self.w.{node.attr} not in PORT')
                if isinstance(node, ast.Call):
                    for arg in node.args:
                        if isinstance(arg, ast.Name) and arg.id == 'self' and not (
                                isinstance(node.func, ast.Name) and node.func.id in ('getattr', 'hasattr', 'setattr',
                                                                                    'isinstance', 'super', 'id')):
                            broken.append(f'{path.relative_to(ROOT)}:{node.lineno} the tool itself given to a call')
    assert not broken, '\n'.join(broken)


def test_the_view_of_a_tab_is_never_data():
    # 0.108.65 (RUNTIME_CONTRACTS.md §1: «Камера, раскрытые панели, прокрутка — WorkspaceState: только представление, не
    # источник научных данных»): the storage, the runtime of projects and calculations, the recovery copies and the
    # inputs of Sextant name no field of azimuth/runtime/workspace_state.WorkspaceState and no .view of a document
    # (a call like Project.view(path) is another thing: a method). 'current' is left out: queue.current(),
    # project.current(entry) are the data's own words.
    from azimuth.runtime.workspace_state import VIEW_FIELDS

    names = set(VIEW_FIELDS) - {'current'}
    files = [p for p in (ROOT / 'azimuth' / 'runtime').glob('*.py') if p.name != 'workspace_state.py']
    files += [ROOT / f for f in PROTECTED_FILES] + [ROOT / 'azimuth' / 'recovery.py']
    called = set()
    found = []
    for path in files:
        tree = ast.parse(path.read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                called.add(id(node.func))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and (node.attr in names or (node.attr == 'view' and id(node) not in called)):
                found.append(f'{path.relative_to(ROOT)}:{node.lineno} .{node.attr}')
    assert not found, '\n'.join(found)


def port_of(path, name):
    tree = ast.parse((ROOT / path).read_text(encoding='utf-8'))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == name)
    port = next(n for n in cls.body if isinstance(n, ast.Assign) and any(getattr(t, 'id', '') == 'PORT' for t in n.targets))
    return set(ast.literal_eval(port.value))


def test_the_watching_of_the_server_is_a_part_of_its_own():
    # the mark of the server, «Проверить подключение»
    # and «Файлы на сервере» live in ServerWatchTool with the few names they need; RunTool no longer reaches them
    watching = port_of('modules/sextant/server_watch_actions.py', 'ServerWatchTool')
    running = port_of('modules/sextant/run_actions.py', 'RunTool')
    assert len(watching) <= 10 and not watching & {'job', 'job_window', 'batch_tool', 'input_tool'}
    assert not running & {'SERVER_PING_S', 'server_spinner', 'server_watch_timer', 'server_browser'}


def test_the_program_shown_is_a_part_of_its_own():
    # the mark of the program, «Указать…», «Искать самой» and the line «… не нашлась» live in ProgramTool
    showing = port_of('modules/sextant/program_actions.py', 'ProgramTool')
    running = port_of('modules/sextant/run_actions.py', 'RunTool')
    assert len(showing) <= 20 and not showing & {'job', 'job_window', 'batch_tool', 'input_tool'}
    assert not running & {'program_badge', 'program_found', 'program_path', 'program_missing', 'program_missing_text',
                          'install_missing_button', 'found_program', 'server_mark'}
    assert len(running) <= 74


def test_the_installation_of_the_programs_is_a_part_of_its_own():
    # «Установить программы для расчёта» lives in InstallTool
    installing = port_of('modules/sextant/install_actions.py', 'InstallTool')
    running = port_of('modules/sextant/run_actions.py', 'RunTool')
    assert len(installing) <= 15 and not installing & {'job', 'batch_tool', 'program_kind'}
    assert not running & {'install_timer', 'mpi_button', 'job_window_button'} and len(running) <= 73  # + doctor_tool


def test_the_history_of_the_calculations_is_a_part_of_its_own():
    # «История расчётов» lives in HistoryTool with five names of the window
    keeping = port_of('modules/sextant/history_actions.py', 'HistoryTool')
    assert len(keeping) <= 6 and not keeping & {'job', 'job_window', 'batch_tool', 'at_place'}
    assert 'running_jobs' not in port_of('modules/sextant/run_actions.py', 'RunTool')
