"""Sextant: «Файлы на сервере» — a two-pane file manager, this computer and the server, as Total Commander.

Files on the server, opened by the icon between the server settings and the connection check: two panes, as Total
Commander, to move between folders and open, edit or delete files.

Left — the folders of this computer, right — of the server (through the ssh connection of Sextant; the commands and
the reading of the listing: server_files.py). Double click or Enter — into a folder, or a file opened in Azimuth (a
server file is downloaded first into «<папка расчётов>/from-server/»). Every network call runs in a worker
(azimuth.tasks.run_waiting: the busy cursor, Esc cancels).
The panes are white cards (QFrame#filePane) with
their glyph (computer / server), title and count of folders and files, «up» and «home» as the icon buttons of the
program; the chosen pane framed in blue; folders and files with the glyphs of the program (no emoji).
The keys and the bar of the function keys of Total
Commander under the panes —
    F3 view (the editor of the program, read only, with its search) · F4 edit · Shift+F4 a new text file · F5 copy ·
    F6 move · Shift+F6 rename · F7 new folder · F8 / Delete delete · Alt+F7 find files by a mask · Ctrl+D the
    favourite folders · Enter open in Azimuth · Insert / Space mark the file and go down · + / - mark / unmark by a mask
    · * invert the marks · Ctrl+A mark all · Ctrl+F3 / F4 / F5 / F6 sort by name / type / date / size (the header
    too) · Ctrl+R / F2 read again · Backspace / Ctrl+PgUp up · Ctrl+\\ the root · Tab the other pane · Ctrl+Shift+C
    the full paths copied · F1 the keys · F10 / Esc close;
the line under each pane says what is marked (as Total Commander: «Выделено 2 из 15 · 1,2 МБ из 3,4 МБ»); the editor of
F3 / F4 is azimuth/text_editor.py (the keys of AkelPad). ServerBrowser(owner, profile, connection, local='',
remote='').{go_local(path), go_remote(path), copy(), move(confirm=None), open_in_azimuth(), view(), edit(save=None),
new_file(name=None, save=None), rename(new=None), make_folder(name=None), delete(confirm=None), mark(),
select_mask(mask=None, on=True), invert(), sort_by(key), search(mask=None, show=True), add_favourite(), favourites(),
go_favourite(path)} — the arguments without a window are for the tests; .local, .remote
— the two panes (Pane: .path, .entries, .selected() -> [Entry], .tree, .marked_line)."""

import json
import os
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QDialog, QHBoxLayout, QInputDialog, QLabel, QPushButton, QVBoxLayout

from azimuth.i18n import tr
from azimuth.icons import icon, iconify
from azimuth.ui import button
from modules.sextant import server_files as sf
from modules.sextant.server_panes import FileTree, Pane, TextEditor, MIME  # noqa: F401 — also named from here
from modules.sextant import server_browser_files as _files
from modules.sextant import server_browser_extras as _extras

FAVOURITES_KEY = 'server_browser_favourites'  # {"local": [paths], "remote:<server>": [paths]}
# the panes are the white cards of the program
# (the colours of azimuth/app.py STYLE, so the dark theme comes from its replacements), the chosen one framed in blue
STYLE = """
QFrame#filePane {background: white; border: 1px solid #d8dce3; border-radius: 12px;}
QFrame#filePane[active="true"] {border: 1px solid #2a62b8;}
QFrame#filePane QTreeWidget {background: transparent; border: none; alternate-background-color: #f8fafc;
    selection-background-color: #dbe8fb; selection-color: #1b2230;}
QFrame#filePane QHeaderView::section {background: transparent; border: none; border-bottom: 1px solid #e1e6ed;
    padding: 4px 6px; color: #5b6474; font-weight: 600;}
QLabel#paneCount {color: #5b6474;}
QLabel#paneMarked {color: #5b6474; font-size: 11px;}
QPushButton#functionKey {padding: 5px 10px;}
QLabel#keysLine {color: #5b6474; font-size: 11px;}
"""
# the panes of the dark theme, its colours as DARK_STYLE of azimuth/app.py; both sheets in one
# (azimuth/theme_sheet.both, the window marked dark by the program)
DARK = (STYLE.replace('background: white', 'background: #191f28').replace('#d8dce3', '#2b333f')
        .replace('#2a62b8', '#6ea2f0').replace('#f8fafc', '#1e2530').replace('#dbe8fb', '#26364f')
        .replace('#1b2230', '#e7eaf0').replace('#e1e6ed', '#2b333f').replace('#5b6474', '#9aa3b2')
        + 'QFrame#filePane QTreeWidget {color: #e7eaf0;}\n')


def style_sheet():
    from azimuth import theme_sheet

    return theme_sheet.both(STYLE, DARK)


def local_listing(path):
    """(the real path, [Entry]) of a folder of this computer, folders first."""
    folder = Path(path).expanduser().resolve()
    found = []
    with os.scandir(folder) as items:
        for item in items:
            try:
                kind = 'dir' if item.is_dir() else 'file'
                stat = item.stat()
                size = 0 if kind == 'dir' else stat.st_size
                when = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')
            except OSError:
                kind, size, when = 'file', 0, ''
            found.append(sf.Entry(item.name, kind, size, when))
    found.sort(key=lambda e: (e.kind != 'dir', e.name.lower()))
    return str(folder), found


class ServerBrowser(QDialog):
    def __init__(self, owner, profile, connection, local='', remote=''):
        super().__init__(owner)
        self.owner = owner
        self.profile = profile
        self.connection = connection
        self._favourites = {}  # without the settings of the window (the tests)
        where = f'{profile.user.strip()}@{profile.host.strip()}' if getattr(profile, 'host', '') else ''
        # the title is in the title bar only, not repeated inside the window
        self.setWindowTitle(' · '.join(t for t in (tr('Файлы на сервере'), profile.title(), where) if t))
        self.setStyleSheet(style_sheet())
        column = QVBoxLayout(self)
        column.setContentsMargins(20, 18, 20, 14)
        column.setSpacing(12)
        head = QHBoxLayout()
        head.setSpacing(10)
        head.addStretch(1)
        self.search_button = iconify(QPushButton(), 'search', tr('Найти файлы по маске · Alt+F7'))
        self.search_button.clicked.connect(lambda: self.search())
        head.addWidget(self.search_button)
        self.keys_button = iconify(QPushButton(), 'keyboard', tr('Горячие клавиши · F1'))
        self.keys_button.clicked.connect(self.show_keys)
        head.addWidget(self.keys_button)
        self.refresh_button = iconify(QPushButton(), 'refresh', tr('Обновить обе панели · Ctrl+R'))
        self.refresh_button.clicked.connect(self.refresh)
        head.addWidget(self.refresh_button)
        column.addLayout(head)
        panes = QHBoxLayout()
        panes.setSpacing(14)
        self.local = Pane(tr('Этот компьютер'), 'computer')
        self.remote = Pane(profile.title(), 'server')
        for pane in (self.local, self.remote):
            panes.addWidget(pane, 1)
            pane.focused.connect(lambda p=pane: self._focus(p))
            pane.favourite_button.clicked.connect(lambda checked=False, p=pane: self.favourites_menu(p))
        for pane in (self.local, self.remote):  # the files dragged out of a pane and dropped on it
            pane.tree.make_drag = lambda items, p=pane: self.drag_data(p, items)
            pane.tree.dropped.connect(lambda data, p=pane: self.dropped_on(p, data))
        self.local.activated.connect(lambda e: self._activated(self.local, e))
        self.remote.activated.connect(lambda e: self._activated(self.remote, e))
        self.local.up_button.clicked.connect(lambda: self.go_local(str(Path(self.local.path).parent)))
        self.remote.up_button.clicked.connect(lambda: self.go_remote(sf.parent(self.remote.path)))
        self.local.home_button.clicked.connect(lambda: self.go_local(str(Path.home())))
        self.remote.home_button.clicked.connect(lambda: self.go_remote(profile.folder or '~'))
        self.remote.home_button.setToolTip(tr('Папка расчётов на сервере'))
        self.local.path_edit.returnPressed.connect(lambda: self.go_local(self.local.path_edit.text()))
        self.remote.path_edit.returnPressed.connect(lambda: self.go_remote(self.remote.path_edit.text()))
        column.addLayout(panes, 1)
        # the bar of the function keys of Total Commander — «F3 Просмотр», «F4 Правка», … each a button
        bar = QHBoxLayout()
        bar.setSpacing(6)
        self.buttons = {}
        for key, title, glyph, slot in (
            ('F3', 'Просмотр', 'eye', lambda: self.view()),
            ('F4', 'Правка', 'edit', lambda: self.edit()),
            ('F5', 'Копировать', 'copy', lambda: self.copy()),
            ('F6', 'Переместить', 'move', lambda: self.move()),
            ('F7', 'Каталог', 'folder', lambda: self.make_folder()),
            ('F8', 'Удалить', 'delete', lambda: self.delete()),
        ):
            item = button(f'{key}  {tr(title)}', slot)
            item.setObjectName('functionKey')
            item.setIcon(icon(glyph))
            item.setToolTip(f'{tr(title)} · {key}')
            bar.addWidget(item, 1)
            self.buttons[key] = item
        # the main action of the window is the blue one
        self.open_button = button(tr('Открыть в Азимуте'), lambda: self.open_in_azimuth(), True)
        self.open_button.setIcon(icon('file-open', 'white'))
        self.open_button.setToolTip(tr('Открыть в Азимуте · Enter'))
        bar.addWidget(self.open_button, 1)
        self.buttons['Enter'] = self.open_button
        column.addLayout(bar)
        for keys, slot in (
            ('F3', lambda: self.view()), ('F4', lambda: self.edit()), ('Shift+F4', lambda: self.new_file()),
            ('F5', lambda: self.copy()), ('F6', lambda: self.move()), ('Shift+F6', lambda: self.rename()),
            ('F7', lambda: self.make_folder()), ('F8', lambda: self.delete()), ('Alt+F7', lambda: self.search()),
            ('Ctrl+D', lambda: self.favourites_menu(self.active)), ('Ctrl+R', self.refresh), ('F2', self.refresh),
            ('Ctrl+F3', lambda: self.sort_by('name')), ('Ctrl+F4', lambda: self.sort_by('type')),
            ('Ctrl+F5', lambda: self.sort_by('date')), ('Ctrl+F6', lambda: self.sort_by('size')),
            ('Ctrl+\\', self.root), ('Ctrl+PgUp', self.up), ('Ctrl+Shift+C', lambda: self.copy_paths()),
            ('F1', self.show_keys), ('F10', self.close),
        ):
            QShortcut(QKeySequence(keys), self).activated.connect(slot)
        for pane in (self.local, self.remote):  # in the lists only: the path field keeps its own keys
            for key, slot in (('Delete', lambda: self.delete()), ('Backspace', self.up), ('Insert', self.mark),
                              ('Space', self.mark), ('+', lambda: self.select_mask(None, True)),
                              ('-', lambda: self.select_mask(None, False)), ('*', self.invert),
                              ('Tab', self.other_pane)):
                shortcut = QShortcut(QKeySequence(key), pane.tree)
                shortcut.setContext(Qt.ShortcutContext.WidgetShortcut)
                shortcut.activated.connect(slot)
        foot = QHBoxLayout()
        self.status = QLabel()
        self.status.setObjectName('subtitle')
        foot.addWidget(self.status, 1)
        keys = QLabel(tr('Shift+F6 переименовать · Shift+F4 новый файл · Alt+F7 поиск · Ctrl+D избранное · '
                         'Insert отметить · F1 все клавиши'))
        keys.setObjectName('keysLine')
        foot.addWidget(keys)
        column.addLayout(foot)
        self.active = self.remote
        self._focus(self.remote)
        self.resize(1180, 720)
        self.go_local(local or str(Path.home()))
        self.go_remote(remote or profile.folder or '~')

    # -- the network, in a worker --------------------------------------------------------------------------------
    def _remote(self, title, work):
        from azimuth.tasks import run_waiting

        def done(step):
            result = work()
            return True if result is None else result

        try:
            return run_waiting(self, title, done, alone=False)
        except InterruptedError:
            return None
        except Exception as exc:  # noqa: BLE001 — ssh.SshError and the rest: said, the window stays
            self.say(str(exc), error=True)
            return None

    def say(self, text, error=False):
        self.status.setText(text)
        self.status.setObjectName('error' if error else 'subtitle')  # the colours of the program, both themes
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)

    def _focus(self, pane):
        self.active = pane
        other = self.remote if pane is self.local else self.local
        pane.set_active(True)
        other.set_active(False)
        # the direction in the words — «на сервер» / «сюда» (an arrow alone was easy to misread)
        self.buttons['F5'].setText('F5  ' + (tr('Копировать на сервер →') if pane is self.local else tr('← Копировать сюда')))
        self.buttons['F6'].setText('F6  ' + (tr('Переместить на сервер →') if pane is self.local else
                                             tr('← Переместить сюда')))
        # the marks of the
        # other pane stay; F5, F6, F8 act on the pane chosen only

    def other_pane(self):
        """Tab: the other pane chosen, its list in focus."""
        pane = self.remote if self.active is self.local else self.local
        pane.tree.setFocus()
        self._focus(pane)
        return pane

    # -- the panes -----------------------------------------------------------------------------------------------
    def go_local(self, path):
        try:
            real, entries = local_listing(path)
        except OSError as exc:
            self.say(str(exc), error=True)
            return False
        self.local.show_entries(real, entries)
        return True

    def go_remote(self, path):
        text = self._remote(tr('Читаю папку на сервере…'), lambda: self.connection.text(sf.list_command(path), timeout=60))
        if text is None:
            return False
        real, entries = sf.parse_listing(text)
        self.remote.show_entries(real or path, entries)
        self.say(tr('Папок и файлов: {}.').format(len(entries)))
        return True

    def go(self, pane, path):
        return self.go_local(path) if pane is self.local else self.go_remote(path)

    def refresh(self):
        self.go_local(self.local.path)
        self.go_remote(self.remote.path)

    def up(self):
        if self.active is self.local:
            self.go_local(str(Path(self.local.path).parent))
        else:
            self.go_remote(sf.parent(self.remote.path))

    def root(self):
        """Ctrl+\\: the root of the disc of the folder (here) or «/» (the server)."""
        if self.active is self.local:
            return self.go_local(Path(self.local.path).anchor or '/')
        return self.go_remote('/')

    def _activated(self, pane, entry):
        if entry is None:
            return
        self.active = pane
        if entry.kind == 'dir':
            if pane is self.local:
                self.go_local(str(Path(pane.path) / entry.name))
            else:
                self.go_remote(sf.child(pane.path, entry.name))
        else:
            self.open_in_azimuth([entry])

    # -- the marks and the order (Total Commander) ---------------------------------------------------------------------
    def mark(self):
        return self.active.mark()

    def select_mask(self, mask=None, on=True):
        if mask is None:
            mask, ok = QInputDialog.getText(self, tr('Отметить по маске') if on else tr('Снять отметку по маске'),
                                            tr('Маска (например *.out; несколько — через ;):'), text='*.*' if on else '*')
            if not ok:
                return 0
        count = self.active.select_mask('*' if mask.strip() == '*.*' else mask, on)
        self.say((tr('Отмечено по маске: {}') if on else tr('Снята отметка: {}')).format(count))
        return count

    def invert(self):
        return self.active.invert()

    def sort_by(self, key):
        return self.active.sort_by(key)

    def copy_paths(self):
        """Ctrl+Shift+C: the full paths of the marked items to the clipboard (a server path as user@host:path)."""
        pane = self.active
        chosen = pane.selected()
        if not chosen:
            return ''
        if pane is self.local:
            paths = [str(Path(pane.path) / e.name) for e in chosen]
        else:
            host = f'{self.profile.user.strip()}@{self.profile.host.strip()}:' if getattr(self.profile, 'host', '') else ''
            paths = [host + sf.child(pane.path, e.name) for e in chosen]
        text = '\n'.join(paths)
        QApplication.clipboard().setText(text)
        self.say(tr('Пути скопированы: {}').format(len(paths)))
        return text

    # -- the favourite folders (Ctrl+D) --------------------------------------------------------------------------------
    def _side(self, pane):
        return 'local' if pane is self.local else 'remote:' + self.profile.title()

    def _stored(self):
        preferences = getattr(self.owner, 'preferences', None)
        if preferences is None or not hasattr(preferences, 'value'):
            return self._favourites
        try:
            data = json.loads(preferences.value(FAVOURITES_KEY, '{}') or '{}')
        except (TypeError, ValueError):
            data = {}
        return data if isinstance(data, dict) else {}

    def _store(self, data):
        preferences = getattr(self.owner, 'preferences', None)
        if preferences is None or not hasattr(preferences, 'setValue'):
            self._favourites = data
            return
        preferences.setValue(FAVOURITES_KEY, json.dumps(data, ensure_ascii=False))

    favourites = _extras.favourites
    add_favourite = _extras.add_favourite
    remove_favourite = _extras.remove_favourite
    go_favourite = _extras.go_favourite
    favourites_menu = _extras.favourites_menu
    search = _extras.search
    found_window = _extras.found_window
    show_keys = _extras.show_keys

    # -- the drag and the drop -------------------------------------------------------------------------
    DRAG_DOWNLOAD = 50_000_000  # bytes: server files up to this size are downloaded for a drop outside the window

    drag_data = _extras.drag_data

    @staticmethod
    def dragged(data):
        """(side, folder, names) of files dragged from a pane of this window, or None."""
        if not data.hasFormat(MIME):
            return None
        lines = bytes(data.data(MIME)).decode('utf-8').split('\n')
        return (lines[0], lines[1], [n for n in lines[2:] if n]) if len(lines) >= 3 else None

    dropped_on = _extras.dropped_on
    cache = _files.cache
    _fetched = _files._fetched
    open_in_azimuth = _files.open_in_azimuth
    _text_of = _files._text_of
    view = _files.view
    edit = _files.edit
    _written = _files._written
    new_file = _files.new_file
    copy = _files.copy
    move = _files.move
    rename = _files.rename
    make_folder = _files.make_folder
    delete = _files.delete
