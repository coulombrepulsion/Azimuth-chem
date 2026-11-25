"""The extras of «Файлы на сервере»: the favourite folders (Ctrl+D), the search by a mask, the keys (F1), dragging
files between the panes and from the window. Methods of ServerBrowser (self is the window), kept here to make
server_browser.py shorter.

Split off modules/sextant/server_browser.py (0.222.30).
"""

import fnmatch
import os
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QMenu,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)
from azimuth.i18n import tr
from azimuth.icons import icon
from azimuth.ui import button, label
from modules.sextant import server_files as sf
from modules.sextant.server_panes import MIME


FOUND_LIMIT = 500  # Alt+F7: the files found at most


# the keys of Total Commander (F1 lists them); the bar under the panes has the function keys
KEYS = (
    ('Enter', 'Открыть папку или файл в Азимуте'),
    ('F3', 'Просмотр файла'),
    ('F4', 'Правка текстового файла'),
    ('Shift+F4', 'Новый текстовый файл'),
    ('F5', 'Копировать в другую панель'),
    ('F6', 'Переместить в другую панель'),
    ('Shift+F6', 'Переименовать'),
    ('F7', 'Новая папка'),
    ('F8 / Delete', 'Удалить (здесь — в Корзину)'),
    ('Alt+F7', 'Найти файлы по маске'),
    ('Ctrl+D', 'Избранные папки'),
    ('Insert / Пробел', 'Отметить файл и перейти ниже'),
    ('+ / −', 'Отметить / снять отметку по маске'),
    ('*', 'Обратить отметку'),
    ('Ctrl+A', 'Отметить всё'),
    ('Ctrl+F3 … Ctrl+F6', 'Сортировать по имени, типу, дате, размеру'),
    ('Ctrl+R / F2', 'Перечитать обе панели'),
    ('Backspace / Ctrl+PgUp', 'На уровень выше'),
    ('Ctrl+\\', 'В корень'),
    ('Tab', 'Другая панель'),
    ('Ctrl+Shift+C', 'Скопировать полные пути'),
    ('F1', 'Горячие клавиши'),
    ('F10 / Esc', 'Закрыть окно'),
)


def favourites(self, pane=None):
    return list(self._stored().get(self._side(pane or self.active), []))


def add_favourite(self, pane=None):
    pane = pane or self.active
    data = self._stored()
    paths = [p for p in data.get(self._side(pane), []) if p != pane.path]
    data[self._side(pane)] = [pane.path] + paths[:19]
    self._store(data)
    self.say(tr('В избранном: {}').format(pane.path))
    return data[self._side(pane)]


def remove_favourite(self, path, pane=None):
    pane = pane or self.active
    data = self._stored()
    data[self._side(pane)] = [p for p in data.get(self._side(pane), []) if p != path]
    self._store(data)
    return data[self._side(pane)]


def go_favourite(self, path, pane=None):
    pane = pane or self.active
    self._focus(pane)
    return self.go(pane, path)


def favourites_menu(self, pane=None, show=True):
    """Ctrl+D (as the «Directory hotlist» of Total Commander): the folders of this side, «Добавить текущую», «Убрать
    текущую». Returns the menu."""
    from azimuth.ui import rounded

    pane = pane or self.active
    menu = QMenu(self)
    for path in self.favourites(pane):
        item = menu.addAction(icon('folder'), path)
        item.triggered.connect(lambda checked=False, p=path: self.go_favourite(p, pane))
    if self.favourites(pane):
        menu.addSeparator()
    add = menu.addAction(icon('hotlist'), tr('Добавить текущую папку'))
    add.triggered.connect(lambda: self.add_favourite(pane))
    if pane.path in self.favourites(pane):
        remove = menu.addAction(icon('delete'), tr('Убрать текущую папку'))
        remove.triggered.connect(lambda: self.remove_favourite(pane.path, pane))
    rounded(menu)
    if show:
        menu.popup(pane.favourite_button.mapToGlobal(pane.favourite_button.rect().bottomLeft()))
    return menu


# -- Alt+F7: the files by a mask -------------------------------------------------------------------------------------
def search(self, mask=None, show=True):
    """The files (and folders) whose name fits the mask, in the folder of the active pane and below it (8 levels,
    FOUND_LIMIT at most): [relative path]; show — a window with them (a double click goes to the file)."""
    pane = self.active
    if mask is None:
        mask, ok = QInputDialog.getText(self, tr('Найти файлы'), tr('Маска имени (например *.out или *opt*):'),
                                        text='*')
        if not ok or not mask.strip():
            return []
    mask = mask.strip()
    if pane is self.local:
        found = []
        base = Path(pane.path)
        for folder, dirs, files in os.walk(base):
            depth = len(Path(folder).relative_to(base).parts)
            if depth >= 8:
                dirs[:] = []
            for name in dirs + files:
                if fnmatch.fnmatch(name.lower(), mask.lower()):
                    found.append(str((Path(folder) / name).relative_to(base)))
            if len(found) >= FOUND_LIMIT:
                break
        found = found[:FOUND_LIMIT]
    else:
        text = self._remote(tr('Ищу на сервере…'), lambda: self.connection.text(
            sf.find_command(pane.path, mask, FOUND_LIMIT), timeout=120))
        if text is None:
            return []
        found = sf.parse_found(text)
    self.say(tr('Найдено: {}').format(len(found)) + (tr(' (показаны первые {})').format(FOUND_LIMIT)
                                                     if len(found) >= FOUND_LIMIT else ''))
    if show:
        self.found_window(pane, mask, found)
    return found


def found_window(self, pane, mask, found):
    box = QDialog(self)
    box.setWindowTitle(tr('Найдено: {}').format(mask))
    column = QVBoxLayout(box)
    column.setContentsMargins(18, 16, 18, 16)
    column.addWidget(label(tr('«{}» в {}').format(mask, pane.path), 'subtitle'))
    tree = QTreeWidget()
    tree.setHeaderLabels([tr('Файл')])
    tree.setRootIsDecorated(False)
    for path in found:
        item = QTreeWidgetItem([path])
        item.setIcon(0, icon('file'))
        tree.addTopLevelItem(item)
    column.addWidget(tree, 1)
    if not found:
        column.addWidget(label(tr('Ничего не найдено.'), 'subtitle'))

    def go(item, _column=0):
        parts = item.text(0).replace('\\', '/').rsplit('/', 1)
        folder, name = (parts[0], parts[1]) if len(parts) == 2 else ('', parts[0])
        if pane is self.local:
            target = str(Path(pane_path) / folder) if folder else pane_path
        else:
            target = pane_path.rstrip('/') + '/' + folder if folder else pane_path
        if self.go(pane, target):
            pane.select([name])
            box.accept()

    pane_path = pane.path
    tree.itemActivated.connect(go)
    row = QHBoxLayout()
    row.addWidget(label(tr('Двойной щелчок — перейти к файлу'), 'subtitle'), 1)
    row.addWidget(button(tr('Закрыть'), box.reject))
    column.addLayout(row)
    box.resize(640, 480)
    box.show()
    self.found_box = box
    return box


def show_keys(self):
    """F1: the keys of the window in a small window of the program."""
    from PySide6.QtWidgets import QTableWidget, QTableWidgetItem

    box = QDialog(self)
    box.setWindowTitle(tr('Горячие клавиши'))
    column = QVBoxLayout(box)
    column.setContentsMargins(18, 16, 18, 16)
    table = QTableWidget(len(KEYS), 2)
    table.setHorizontalHeaderLabels([tr('Клавиши'), tr('Действие')])
    table.verticalHeader().hide()
    table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
    table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    for i, (keys, title) in enumerate(KEYS):
        table.setItem(i, 0, QTableWidgetItem(tr(keys)))
        table.setItem(i, 1, QTableWidgetItem(tr(title)))
    column.addWidget(table, 1)
    row = QHBoxLayout()
    row.addStretch(1)
    row.addWidget(button(tr('Закрыть'), box.accept))
    column.addLayout(row)
    box.resize(520, 640)
    box.show()
    self.keys_box = box
    return box


def drag_data(self, pane, items):
    """The QMimeData of the files of the pane dragged: their names for the other pane, the files themselves for
    Finder and the other programs (a server file downloaded first into the cache, when they are small enough)."""
    from PySide6.QtCore import QMimeData, QUrl

    entries = [i.data(0, Qt.ItemDataRole.UserRole) for i in items]
    entries = [e for e in entries if e is not None]
    if not entries:
        return None
    data = QMimeData()
    side = 'local' if pane is self.local else 'remote'
    data.setData(MIME, '\n'.join([side, pane.path] + [e.name for e in entries]).encode('utf-8'))
    if pane is self.local:
        data.setUrls([QUrl.fromLocalFile(str(Path(pane.path) / e.name)) for e in entries])
    elif all(e.kind != 'dir' for e in entries) and sum(e.size for e in entries) <= self.DRAG_DOWNLOAD:
        target = self.cache()
        names = [e.name for e in entries]
        if self._remote(tr('Скачиваю для переноса ({})…').format(len(names)),
                        lambda: self.connection.get(names, pane.path, target)) is not None:
            data.setUrls([QUrl.fromLocalFile(str(target / n)) for n in names])
    return data


def dropped_on(self, pane, data):
    """Files dropped on a pane: from the other pane — copied there as by F5; from Finder (or the other programs) —
    copied into the folder of the pane (uploaded to the server). Returns the number of the files taken."""
    import shutil

    own = self.dragged(data)
    side = 'local' if pane is self.local else 'remote'
    if own is not None and own[0] == side:
        return 0  # dropped where they came from
    cached = [Path(u.toLocalFile()) for u in data.urls() if u.isLocalFile() and Path(u.toLocalFile()).is_file()]
    if own is not None and own[0] == 'remote' and pane is self.local and not cached:  # the server → here
        names = own[2]
        if self._remote(tr('Скачиваю с сервера ({})…').format(len(names)),
                        lambda: self.connection.get(names, own[1], self.local.path)) is None:
            return 0
        self.go_local(self.local.path)
        self.local.select(names)
        self._focus(self.local)
        self.say(tr('Скопировано: {}').format(len(names)))
        return len(names)
    # the files of Finder, of the other pane, or those of the server downloaded already for the drag (cached)
    paths = [Path(u.toLocalFile()) for u in data.urls() if u.isLocalFile() and u.toLocalFile()]
    paths = [p for p in paths if p.exists()]
    if not paths:
        return 0
    if pane is self.remote:
        if self._remote(tr('Загружаю на сервер ({})…').format(len(paths)),
                        lambda: self.connection.put(paths, self.remote.path)) is None:
            return 0
        self.go_remote(self.remote.path)
        self.remote.select([p.name for p in paths])
        self._focus(self.remote)
    else:
        folder = Path(self.local.path)
        copied = []
        for path in paths:
            if path.parent.resolve() == folder.resolve():
                continue  # already here
            try:
                if path.is_dir():
                    shutil.copytree(path, folder / path.name, dirs_exist_ok=True)
                else:
                    shutil.copy2(path, folder / path.name)
                copied.append(path.name)
            except OSError as exc:
                self.say(str(exc), error=True)
        self.go_local(self.local.path)
        self.local.select(copied)
        self._focus(self.local)
        paths = copied
    self.say(tr('Скопировано: {}').format(len(paths)))
    return len(paths)
