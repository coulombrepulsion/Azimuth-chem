"""The .py files of the program for the tests that read its sources (the architecture, the encodings).

python_files(*folders, skip=()) — sorted, under the folders of the program (all of it when none given); hidden folders
(.venv, .venv.nosync, .tools, .tools.nosync, .git), __pycache__ and the folders named in skip are never entered, nor
artifacts/ at the top (not in git: reports of the runs, calculations, a working copy — none of it the program).
The tests walked ROOT.rglob('*.py') and dropped what lay under '.venv/' afterwards — the walk itself
went through every package of the environment, and once the environment became .venv.nosync (out of iCloud Drive)
the prefix no longer matched and its files were read as the program's (test_architecture_boundaries 25 → 52 s).
moved_methods(tree, cls) — the functions of other files a class takes as its methods (0.222.29)."""

import ast
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOT_THE_PROGRAM = ('artifacts',)


def python_files(*folders, skip=(), root=ROOT):
    found = []
    for folder in folders or ('',):
        top = Path(root) / folder
        for here, dirs, names in os.walk(top):
            dirs[:] = sorted(d for d in dirs if not d.startswith('.') and d != '__pycache__' and d not in skip
                             and not (Path(here) == Path(root) and d in NOT_THE_PROGRAM))
            found += [Path(here) / n for n in names if n.endswith('.py')]
    return sorted(found)


def moved_methods(tree, cls):
    """The functions of other modules a class takes as its methods (`name = _part.name` in its body, the module
    imported as `from package import module as _part`; 0.222.29 — a long class kept in several files)."""
    modules = {}
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module and not node.level:
            for alias in node.names:
                modules[alias.asname or alias.name] = f'{node.module}.{alias.name}'
    found = []
    for node in cls.body:
        if (isinstance(node, ast.Assign) and isinstance(node.value, ast.Attribute)
                and isinstance(node.value.value, ast.Name) and node.value.value.id in modules):
            path = ROOT / (modules[node.value.value.id].replace('.', '/') + '.py')
            if path.exists():
                other = ast.parse(path.read_text(encoding='utf-8'))
                found += [f for f in other.body if isinstance(f, ast.FunctionDef) and f.name == node.value.attr]
    return found

