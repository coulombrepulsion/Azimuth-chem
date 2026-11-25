"""The files of the server: what the two-pane file manager of Sextant asks the server and how it reads it.

§1 PURPOSE
    «Файлы на сервере» (the icon between «Сервер…» and «Проверить подключение»): the folders of the server and of this
    computer side by side, as in Total Commander — to go through them, copy both ways, open a result in Azimuth, edit a
    text file, rename, make a folder, delete.
§2 COMMANDS (through the open ssh connection of Sextant)
    listing: `cd <dir> && pwd && LC_ALL=C ls -lAL` — the first line is the real path (~ resolved), then the long listing
    of POSIX ls (the same on Linux and on macOS; -L shows what a link points to, -A without . and ..). The name is
    everything after the eighth field (names with spaces stay whole); the type is the first letter of the mode; the date
    is kept as ls prints it. remove / make / rename: rm -rf, mkdir -p, mv -- with every path quoted (ssh.shell_path).
§3 INTERFACE
    Entry(name, kind 'dir' | 'file' | 'link', size, when); list_command(path) -> str; parse_listing(text) -> (path,
    [Entry]) — folders first, then by name (case ignored); child(path, name) -> str; parent(path) -> str;
    remove_command(path, names), make_command(path, name), rename_command(path, old, new) -> str; human(size) -> str;
    find_command(path, mask, limit) -> str (POSIX find -iname, 8 levels, the first
    limit), parse_found(text) -> [path relative to the folder]; when_key(text, now=None) -> tuple (Ctrl+F5).
    ValueError for a name with «/» or an empty one.
§4 TESTS
    tests/sextant/test_server_files.py — listings of GNU and BSD ls, names with spaces, links; the commands against the
    fake server of tests/fake_server.py.
"""

import re
from dataclasses import dataclass
from datetime import datetime

from azimuth.i18n import tr
from modules.sextant.ssh import shell_path

MONTHS = {m: k for k, m in enumerate(('jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'), 1)}
_MODE = re.compile(r'^[dlbcps-][rwxsStT-]{9}[.+@]?$')


@dataclass(frozen=True)
class Entry:
    name: str
    kind: str
    size: int
    when: str


def list_command(path):
    return f'cd {shell_path(path)} && pwd && LC_ALL=C ls -lAL'


def parse_listing(text):
    lines = [line for line in (text or '').splitlines() if line.strip()]
    if not lines:
        return '', []
    path = lines[0].strip()
    found = []
    for line in lines[1:]:
        if line.startswith('total '):
            continue
        parts = line.split(None, 8)
        if len(parts) < 9 or not _MODE.match(parts[0]):
            continue
        mode, size, name = parts[0], parts[4], parts[8]
        if name in ('.', '..'):
            continue
        kind = 'dir' if mode[0] == 'd' else 'link' if mode[0] == 'l' else 'file'
        found.append(Entry(name, kind, int(size) if size.isdigit() else 0, ' '.join(parts[5:8])))
    found.sort(key=lambda e: (e.kind != 'dir', e.name.lower()))
    return path, found


def _check(name):
    if not name or '/' in name or name in ('.', '..'):
        raise ValueError(f'name: {name!r}')
    return name


def child(path, name):
    return path.rstrip('/') + '/' + _check(name) if path != '/' else '/' + _check(name)


def parent(path):
    path = path.rstrip('/')
    if not path or path == '~':
        return '/'
    head = path.rsplit('/', 1)[0]
    return head or '/'


def remove_command(path, names):
    return 'rm -rf -- ' + ' '.join(shell_path(child(path, n)) for n in names)


def make_command(path, name):
    return 'mkdir -p -- ' + shell_path(child(path, name))


def rename_command(path, old, new):
    return f'mv -- {shell_path(child(path, old))} {shell_path(child(path, new))}'


def find_command(path, mask, limit=500):
    """The files and folders under path whose name fits mask (case ignored), relative to it."""
    import shlex

    return (f'cd {shell_path(path)} && find . -mindepth 1 -maxdepth 8 -iname {shlex.quote(mask)} 2>/dev/null '
            f'| head -n {int(limit)}')


def parse_found(text):
    return [line[2:] if line.startswith('./') else line for line in (text or '').splitlines()
            if line.strip() and line.strip() != '.']


def when_key(text, now=None):
    """A date of a listing as a sortable tuple — «2026-11-08 10:01» of this computer, «Nov 8 10:01» (this
    year, or the last one when it would be in the future) and «Oct 27 2026» of ls on the server; if unread."""
    text = (text or '').strip()
    try:
        moment = datetime.strptime(text, '%Y-%m-%d %H:%M')
        return (moment.year, moment.month, moment.day, moment.hour, moment.minute)
    except ValueError:
        pass
    parts = text.split()
    if len(parts) != 3 or parts[0][:3].lower() not in MONTHS or not parts[1].isdigit():
        return ()
    month, day = MONTHS[parts[0][:3].lower()], int(parts[1])
    if ':' in parts[2]:
        hour, minute = (int(x) for x in parts[2].split(':', 1))
        now = now or datetime.now()
        year = now.year if (month, day) <= (now.month, now.day + 1) else now.year - 1
        return (year, month, day, hour, minute)
    return (int(parts[2]), month, day, 0, 0) if parts[2].isdigit() else ()


def human(size):
    value = float(size)
    for unit in ('Б', 'КБ', 'МБ', 'ГБ'):
        if value < 1024 or unit == 'ГБ':
            return f'{value:.0f} {tr(unit)}' if unit == 'Б' else f'{value:.1f} {tr(unit)}'
        value /= 1024
    return f'{size} Б'
