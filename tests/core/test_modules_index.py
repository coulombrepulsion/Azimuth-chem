"""docs/MODULES_INDEX.md names every module of the program (made by tools/modules_index.py)."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_the_index_is_up_to_date():
    spec = importlib.util.spec_from_file_location('modules_index', ROOT / 'tools' / 'modules_index.py')
    index = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(index)
    written = (ROOT / 'docs' / 'MODULES_INDEX.md').read_text(encoding='utf-8')
    assert written == index.text(), 'run: .venv/bin/python tools/modules_index.py'


def test_every_module_tells_what_it_is():
    spec = importlib.util.spec_from_file_location('modules_index', ROOT / 'tools' / 'modules_index.py')
    index = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(index)
    silent = [str(p.relative_to(ROOT)) for p in index.modules() if not index.summary(p)]
    assert not silent, silent
