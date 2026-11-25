"""Where the projects live: «Документы/Azimuth/Проекты», a folder per project (stage B of
docs/architecture/PROJECT_RUNTIME_GUIDE.md, §1).

§1 PURPOSE
    A project made by opening molecules (a draft — its name not confirmed yet) lived in a folder of the recovery data
    of the system, named by a random hex, and «Сохранить» copied it elsewhere: two folders with the same project id.
    The guide: «Автоматический проект сразу получает постоянную папку, а не каталог ОС для временных файлов»; the
    default root is ~/Documents/Azimuth/Проекты, another one is chosen in the settings; a project has a subfolder with
    a readable name, a clash gets « (2)», « (3)»; the id inside the project, not the name or the path, is its identity.
§2 RULES
    The root: AZIMUTH_PROJECTS_DIR (tests, a deployment), else the folder chosen (setting «projects_folder»), else the
    default. Windows: the calculations of a project are made in its folder, and ORCA, xtb, Gaussian there do not open
    files on a path with letters outside Latin (modules/sextant/runner.latin_path) — the default is
    «Documents\\Azimuth\\Projects», or «%PUBLIC%\\Documents\\Azimuth\\Projects» / «C:\\Azimuth\\Projects» when the home
    folder has such letters, and the name of a project folder is transliterated (Russian letters → Latin, others →
    «_»). macOS, Linux: «Documents/Azimuth/Проекты», names as they are. A name: without the characters forbidden on
    Windows or macOS, without spaces and dots at the ends, at most 60 characters, «Project» when nothing is left; never
    a reserved name of Windows (CON, NUL, COM1 …). The folder is made at once (mkdir exclusive: two projects of one
    name at the same moment never share it).
§4 SPECIFICATION
    default_projects_root(home=None, windows=None, environ=None) -> Path; projects_root(chosen='', environ=None,
    windows=None) -> Path; folder_name(name, windows=None) -> str; new_project_folder(root, name, windows=None) -> Path
    (made, empty).
§7 TESTS tests/projects/test_project_folders.py.
"""

import os
import re
from pathlib import Path

ENV = 'AZIMUTH_PROJECTS_DIR'
MAX_NAME = 60
RESERVED = {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{k}' for k in range(1, 10)), *(f'LPT{k}' for k in range(1, 10))}
# GOST 7.79-2000 system B (the usual Latin spelling of Russian), lower case; upper case is derived
_LATIN = dict(zip('абвгдеёжзийклмнопрстуфхцчшщъыьэюя',
                  ['a', 'b', 'v', 'g', 'd', 'e', 'yo', 'zh', 'z', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'r', 's',
                   't', 'u', 'f', 'kh', 'c', 'ch', 'sh', 'shh', '', 'y', '', 'e', 'yu', 'ya']))


def _windows(windows):
    return os.name == 'nt' if windows is None else windows


def default_projects_root(home=None, windows=None, environ=None):
    environ = os.environ if environ is None else environ
    home = Path(home or Path.home())
    if not _windows(windows):
        return home / 'Documents' / 'Azimuth' / 'Проекты'
    first = home / 'Documents' / 'Azimuth' / 'Projects'
    if str(first).isascii():
        return first
    public = environ.get('PUBLIC', '')
    if public and public.isascii():
        return Path(public) / 'Documents' / 'Azimuth' / 'Projects'
    return Path(environ.get('SystemDrive', 'C:') + '\\') / 'Azimuth' / 'Projects'


# the new projects of each kind in a folder
# of their own in the folder of projects; Latin names on Windows (the programs of the calculations there and Cyrillic)
KIND_FOLDERS = {'molecule': ('Молекулы', 'Molecules'), 'crystal': ('Кристаллы', 'Crystals')}


def kind_root(root, kind, windows=None):
    names = KIND_FOLDERS['crystal' if kind == 'crystal' else 'molecule']
    return Path(root) / (names[1] if _windows(windows) else names[0])


def projects_root(chosen='', environ=None, windows=None):
    environ = os.environ if environ is None else environ
    if environ.get(ENV):
        return Path(environ[ENV])
    if chosen and (not _windows(windows) or str(chosen).isascii()):
        return Path(chosen)
    return default_projects_root(windows=windows, environ=environ)


def _latin(text):
    out = []
    for ch in text:
        low = ch.lower()
        if low in _LATIN:
            latin = _LATIN[low]
            out.append(latin.capitalize() if ch != low else latin)
        elif ch.isascii():
            out.append(ch)
        else:
            out.append('_')
    return ''.join(out)


def folder_name(name, windows=None):
    text = _latin(name or '') if _windows(windows) else (name or '')
    text = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', '_', text)
    text = re.sub(r'\s+', ' ', text).strip(' .')[:MAX_NAME].strip(' .')
    if not text or text.split('.')[0].upper() in RESERVED:
        text = 'Project' if not text else text + '_'
    return text


def new_project_folder(root, name, windows=None):
    """A new empty folder for the project in root: «name», else «name (2)», «name (3)» …"""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    base = folder_name(name, windows)
    for k in range(1, 10000):
        folder = root / (base if k == 1 else f'{base} ({k})')
        try:
            folder.mkdir()
        except FileExistsError:
            continue
        return folder
    raise OSError(f'No free folder name for {base!r} in {root}')
