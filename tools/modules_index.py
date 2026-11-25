"""The index of the modules of the program: docs/MODULES_INDEX.md — every module with the first line of its docstring
(the audit: docs/MODULES.md named about a third of the 184 modules).

Run from the folder of the program after adding a module: .venv/bin/python tools/modules_index.py
tests/core/test_modules_index.py fails while the index lacks a module or names one that is gone.
"""

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDERS = ('azimuth', 'azimuth/runtime', 'hub', 'modules/compass', 'modules/compass/actions',
           'modules/compass/chemistry', 'modules/compass/view', 'modules/compass/panels', 'modules/sextant',
           'modules/spectrum', 'modules/spectrum/readers', 'modules/spectrum/wavefunction', 'modules/spectrum/analysis',
           'modules/spectrum/views', 'modules/atlas', 'tools')  # the sections in folders
SKIP = ('atlas_v2', 'Отдельные_страницы', 'QuAS_Атлас_сайт', '__pycache__')
INDEX = ROOT / 'docs' / 'MODULES_INDEX.md'


def modules():
    found = []
    for folder in FOLDERS:
        for path in sorted((ROOT / folder).glob('*.py')):
            if path.name == '__init__.py' or any(s in path.parts for s in SKIP):
                continue
            found.append(path)
    return found


def summary(path):
    try:
        doc = ast.get_docstring(ast.parse(path.read_text(encoding='utf-8'))) or ''
    except SyntaxError:
        doc = ''
    first = doc.strip().split('\n\n')[0].replace('\n', ' ').strip()
    return first if len(first) <= 240 else first[:237] + '…'


def text():
    lines = ['# Модули «Азимута» — указатель', '',
             'Составлен `tools/modules_index.py` по первым строкам описаний модулей (docstring); подробности — в самих',
             'модулях (раздел §4 SPECIFICATION) и в docs/MODULES.md, docs/ARCHITECTURE.md. Не правится вручную.', '']
    folder = None
    for path in modules():
        rel = path.relative_to(ROOT)
        if rel.parent.as_posix() != folder:  # «modules/compass» on Windows too (str gave «modules\\compass»)
            folder = rel.parent.as_posix()
            lines += ['', f'## {folder}', '']
        lines.append(f'- `{rel.as_posix()}` — {summary(path) or "(нет описания)"}')
    return '\n'.join(lines) + '\n'


def main():
    INDEX.write_text(text(), encoding='utf-8')
    print(f'{INDEX.relative_to(ROOT)}: {len(modules())} модулей')


if __name__ == '__main__':
    sys.exit(main())
