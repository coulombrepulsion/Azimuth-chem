"""Sort the projects made into «Проекты/Молекулы» and «Проекты/Кристаллы» (azimuth/project_kinds.py).

Run with Azimuth closed (an open project must not move under it), from the folder of the program:
    .venv/bin/python tools/sort_projects.py — only shows what would move
    .venv/bin/python tools/sort_projects.py --move — moves
The folder of projects is the one of the settings of Azimuth (or «Документы/Azimuth/Проекты»); --root DIR names another.
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def settings_root():
    from azimuth.project_folders import projects_root

    try:
        from azimuth.settings import open_settings

        chosen = open_settings().value('projects_folder', '') or ''
    except Exception:  # no Qt here: the folder by default
        chosen = ''
    return projects_root(chosen)


def main(argv=None):
    from azimuth import project_kinds

    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--move', action='store_true', help='move (without it — only show)')
    parser.add_argument('--root', help='the folder of projects')
    args = parser.parse_args(argv)
    root = Path(args.root).expanduser() if args.root else settings_root()
    moves = project_kinds.plan(root)
    print(f'Папка проектов: {root}')
    if not moves:
        print('Нечего переносить: в самой папке проектов проектов нет.')
        return 0
    for folder, target in moves:
        print(f'  {folder.name}  →  {target.parent.name}/{target.name}')
    if not args.move:
        print(f'\nПроектов: {len(moves)}. Закройте Азимут и запустите с --move, чтобы перенести.')
        return 0
    moved, failed = project_kinds.sort(root)
    print(f'\nПеренесено: {len(moved)}.')
    for folder, message in failed:
        print(f'  не перенесён {folder.name}: {message}')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
