"""The kind of a project on disk — molecules, crystal or empty — and the sorting of the folder of projects into the
folders of the kinds.

§1 PURPOSE «Открыть проект» opens the folder of the projects, molecules and crystals apart. The new projects are made in
    «Проекты/Молекулы» and «Проекты/Кристаллы» (project_folders.kind_root); the projects made before stay in «Проекты»
    until sorted (tools/sort_projects.py).
§2 RULES
    1. kind(manifest) reads without opening the project (no structure parsed, nothing written): the document of the
       project (project_store.peek, read-only; or the JSON of an older project.qcc). A crystal — the key
       crystal_projects.KEY in the document; molecules in it — of molecules; neither — empty (a new draft).
    2. plan(root) — the projects lying directly in the folder of projects (not those already in the folders of the
       kinds) with where each goes: a crystal into «Кристаллы», molecules and empty drafts into «Молекулы»; a name taken
       there gets « (2)», « (3)» … as a new project does.
    3. sort(root) moves the folders whole (os.replace on the same disk: the calculations inside keep their relative
       paths); a project that cannot be moved (open, locked) stays and is reported.
§3 INTERFACE
    kind(manifest) -> 'crystal' | 'molecule' | 'empty' | None; plan(root, windows=None) -> [(folder, target)];
    sort(root, windows=None) -> (moved [(folder, target)], failed [(folder, message)]).
§4 TESTS
    tests/projects/test_project_kinds.py.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

MANIFEST = 'project.qcc'
CRYSTAL_KEY = 'crystal'  # crystal_projects.KEY


def kind(manifest):
    manifest = Path(manifest)
    try:
        data = json.loads(manifest.read_text(encoding='utf-8-sig'))
        if isinstance(data, dict) and data.get('database'):
            from azimuth import project_store

            document, count, _ = project_store.peek(manifest.parent / str(data['database']), names=0)
        elif isinstance(data, dict):
            document, count = data, len(data.get('molecules') or [])
        else:
            return None
    except Exception:  # a broken or foreign project (sqlite3.Error too) is left alone
        return None
    if document.get('format') not in (None, 'azimuth-research-project'):
        return None
    if isinstance(document.get(CRYSTAL_KEY), dict):
        return 'crystal'
    return 'molecule' if count else 'empty'


def plan(root, windows=None):
    from azimuth.project_folders import KIND_FOLDERS, folder_name, kind_root

    root = Path(root)
    if not root.is_dir():
        return []
    own = {name for names in KIND_FOLDERS.values() for name in names}
    taken = {}
    moves = []
    for folder in sorted(root.iterdir()):
        if not folder.is_dir() or folder.name in own or not (folder / MANIFEST).is_file():
            continue
        found = kind(folder / MANIFEST)
        if found is None:
            continue
        target_root = kind_root(root, 'crystal' if found == 'crystal' else 'molecule', windows)
        used = taken.setdefault(target_root, {p.name for p in target_root.iterdir()} if target_root.is_dir() else set())
        base = folder_name(folder.name, windows) if windows else folder.name
        name = next(n for n in (base if k == 1 else f'{base} ({k})' for k in range(1, 10000)) if n not in used)
        used.add(name)
        moves.append((folder, target_root / name))
    return moves


def sort(root, windows=None):
    moved, failed = [], []
    for folder, target in plan(root, windows):
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(folder, target)
            moved.append((folder, target))
        except OSError as exc:
            failed.append((folder, str(exc)))
    return moved, failed
