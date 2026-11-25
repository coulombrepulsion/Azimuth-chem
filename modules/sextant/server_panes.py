"""The panes of «Файлы на сервере»: the list of files of a folder (FileTree), a pane — here or the server — with its
path and its list (Pane), and the editor of a text file (TextEditor).

Split off modules/sextant/server_browser.py (0.222.30).
"""

import fnmatch
import re
from pathlib import Path
from PySide6.QtCore import QItemSelectionModel, QSize, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)
from azimuth.i18n import tr
from azimuth.icons import icon, iconify
from azimuth.ui import button, label
from modules.sextant import server_files as sf


def _extension(name):
    return Path(name).suffix.lower().lstrip('.')


SORTS = {
    'name': lambda e: e.name.lower(),
    'type': lambda e: (_extension(e.name), e.name.lower()),
    'date': lambda e: sf.when_key(e.when),
    'size': lambda e: e.size,
}


MIME = 'application/x-azimuth-pane'  # the files dragged from a pane: «local» or «remote», then the names


class FileTree(QTreeWidget):
    """The list of a pane that
    gives its marked files to a drag (make_drag(items) -> QMimeData of the window) and takes the files dropped on it
    (dropped: the QMimeData — from the other pane, Finder or Explorer); a drop on itself is nothing."""

    dropped = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.make_drag = None
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.CopyAction)

    def mimeTypes(self):
        return ['text/uri-list', MIME]

    def mimeData(self, items):
        from PySide6.QtCore import QMimeData

        made = self.make_drag(items) if self.make_drag is not None else None
        return made if made is not None else QMimeData()

    def supportedDropActions(self):
        return Qt.DropAction.CopyAction

    def _wanted(self, event):
        data = event.mimeData()
        return event.source() is not self and (data.hasUrls() or data.hasFormat(MIME))

    def dragEnterEvent(self, event):
        if self._wanted(event):
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        self.dragEnterEvent(event)

    def dropEvent(self, event):
        if not self._wanted(event):
            event.ignore()
            return
        event.setDropAction(Qt.DropAction.CopyAction)
        event.accept()
        self.dropped.emit(event.mimeData())


class Pane(QFrame):
    """One side: a card with its icon, title and count, the path with «up» and «home», the list (folders first) and
    the line of what is marked."""

    activated = Signal(object)  # the Entry double-clicked (or Enter)
    focused = Signal()

    def __init__(self, title, glyph='computer', parent=None):
        super().__init__(parent)
        self.setObjectName('filePane')
        self.setProperty('active', False)
        self.path = ''
        self.entries = []
        self.sort = ('name', False)  # (key of SORTS, descending)
        column = QVBoxLayout(self)
        column.setContentsMargins(16, 14, 16, 10)
        column.setSpacing(8)
        head = QHBoxLayout()
        head.setSpacing(8)
        mark = QLabel()
        mark.setPixmap(icon(glyph).pixmap(22, 22))
        head.addWidget(mark)
        self.title = label(title, 'cardtitle')
        self.title.setWordWrap(False)
        head.addWidget(self.title)
        head.addStretch(1)
        self.count = QLabel()
        self.count.setObjectName('paneCount')
        head.addWidget(self.count)
        column.addLayout(head)
        row = QHBoxLayout()
        row.setSpacing(6)
        self.up_button = iconify(QPushButton(), 'pan-up', tr('На уровень выше · Backspace'))
        self.home_button = iconify(QPushButton(), 'home', tr('Домашняя папка'))
        self.favourite_button = iconify(QPushButton(), 'hotlist', tr('Избранные папки · Ctrl+D'))
        row.addWidget(self.up_button)
        row.addWidget(self.home_button)
        row.addWidget(self.favourite_button)
        self.path_edit = QLineEdit()
        self.path_edit.setToolTip(tr('Путь: впишите и нажмите Enter'))
        row.addWidget(self.path_edit, 1)
        column.addLayout(row)
        self.tree = FileTree()
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels([tr('Имя'), tr('Размер'), tr('Изменён')])
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(True)
        self.tree.setIconSize(QSize(18, 18))
        self.tree.setUniformRowHeights(True)
        self.tree.setFrameShape(QFrame.Shape.NoFrame)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        header = self.tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        header.setSectionsClickable(True)
        header.sectionClicked.connect(lambda k: self.sort_by(('name', 'size', 'date')[k] if k < 3 else 'name'))
        self.tree.itemActivated.connect(lambda item, _c: self.activated.emit(item.data(0, Qt.ItemDataRole.UserRole)))
        self.tree.itemSelectionChanged.connect(self.show_marked)
        self.tree.installEventFilter(self)
        column.addWidget(self.tree, 1)
        self.marked_line = QLabel('')
        self.marked_line.setObjectName('paneMarked')
        column.addWidget(self.marked_line)

    def set_active(self, on):
        if self.property('active') != bool(on):
            self.setProperty('active', bool(on))
            self.style().unpolish(self)
            self.style().polish(self)

    def eventFilter(self, watched, event):
        from PySide6.QtCore import QEvent

        if watched is self.tree and event.type() == QEvent.Type.FocusIn:
            self.focused.emit()
        return False

    def sorted_entries(self, entries):
        key, back = self.sort
        rule = SORTS.get(key, SORTS['name'])
        folders = sorted((e for e in entries if e.kind == 'dir'), key=SORTS['name'] if key in ('size', 'type') else rule,
                         reverse=back and key not in ('size', 'type'))
        files = sorted((e for e in entries if e.kind != 'dir'), key=rule, reverse=back)
        return folders + files

    def sort_by(self, key):
        """The same key again — the other way round."""
        old_key, back = self.sort
        self.sort = (key, not back if key == old_key else key in ('date', 'size'))
        chosen = [e.name for e in self.selected()]
        self.show_entries(self.path, self.entries)
        if chosen:
            self.select(chosen)
        return self.sort

    def show_entries(self, path, entries):
        self.path, self.entries = path, self.sorted_entries(entries)
        self.path_edit.setText(path)
        self.tree.clear()
        folder, file = icon('folder', '#2a62b8'), icon('file')
        for e in self.entries:
            item = QTreeWidgetItem([e.name, '' if e.kind == 'dir' else sf.human(e.size), e.when])
            item.setIcon(0, folder if e.kind == 'dir' else file)
            item.setData(0, Qt.ItemDataRole.UserRole, e)
            item.setTextAlignment(1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.tree.addTopLevelItem(item)
        folders = sum(e.kind == 'dir' for e in self.entries)
        self.count.setText(tr('папок {}, файлов {}').format(folders, len(self.entries) - folders))
        if self.entries:  # the cursor on the first line, nothing marked (as Total Commander: + and Insert add to it)
            self.tree.setCurrentItem(self.tree.topLevelItem(0), 0, QItemSelectionModel.SelectionFlag.NoUpdate)
        self.show_marked()

    def marked(self):
        """The entries marked (the selection itself, not the line of the cursor alone)."""
        return [e for e in (i.data(0, Qt.ItemDataRole.UserRole) for i in self.tree.selectedItems()) if e is not None]

    def show_marked(self):
        """«Выделено 2 из 15 · 1,2 МБ из 3,4 МБ» — as the line under a panel of Total Commander."""
        marked = self.marked()
        files = [e for e in self.entries if e.kind != 'dir']
        total = sum(e.size for e in files)
        size = sum(e.size for e in marked if e.kind != 'dir')
        self.marked_line.setText(tr('Выделено {} из {} · {} из {}').format(
            len(marked), len(self.entries), sf.human(size), sf.human(total)))

    def selected(self):
        chosen = self.marked()
        if not chosen and self.tree.currentItem() is not None:
            chosen = [self.tree.currentItem().data(0, Qt.ItemDataRole.UserRole)]
        return [e for e in chosen if e is not None]

    def current(self):
        item = self.tree.currentItem()
        return item.data(0, Qt.ItemDataRole.UserRole) if item is not None else None

    def select(self, names):
        """The items of these names selected (all of them: setCurrentItem alone would leave only the last one)."""
        names = set(names)
        self.tree.clearSelection()
        first = True
        for k in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(k)
            if item.data(0, Qt.ItemDataRole.UserRole).name in names:
                if first:
                    self.tree.setCurrentItem(item, 0, QItemSelectionModel.SelectionFlag.NoUpdate)
                    first = False
                item.setSelected(True)

    def mark(self):
        """Insert / Space: the mark of the item of the cursor turned over, the cursor one line down."""
        item = self.tree.currentItem()
        if item is None:
            return None
        item.setSelected(not item.isSelected())
        below = self.tree.itemBelow(item)
        if below is not None:
            self.tree.setCurrentItem(below, 0, QItemSelectionModel.SelectionFlag.NoUpdate)
        return item.isSelected()

    def select_mask(self, mask, on=True):
        """+ / -: the files whose name fits the mask (*.out; several by «;») marked or unmarked; their number."""
        masks = [m.strip() for m in re.split(r'[;,]', mask or '') if m.strip()] or ['*']
        count = 0
        for k in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(k)
            entry = item.data(0, Qt.ItemDataRole.UserRole)
            if entry.kind != 'dir' and any(fnmatch.fnmatch(entry.name.lower(), m.lower()) for m in masks):
                item.setSelected(on)
                count += 1
        return count

    def invert(self):
        """*: the marks of the files turned over (as Total Commander, the folders stay as they are)."""
        for k in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(k)
            if item.data(0, Qt.ItemDataRole.UserRole).kind != 'dir':
                item.setSelected(not item.isSelected())
        return len(self.marked())


class TextEditor(QDialog):
    """F3 / F4: a text file in the editor of the program (azimuth/text_editor.py: the keys of AkelPad); read only for
    F3. Ctrl+S saves (F4), Esc closes."""

    def __init__(self, title, text, parent=None, read_only=False):
        super().__init__(parent)
        from azimuth.text_editor import CodeEdit, EditorPane

        self.setWindowTitle(title)
        column = QVBoxLayout(self)
        column.setContentsMargins(18, 16, 18, 16)
        column.setSpacing(12)
        # the comment of Ctrl+/: «!» for Gaussian (.gjf, .com) and pw.x (&control …), «#» for the rest (ORCA, CP2K…)
        name = title.split(' · ')[0].lower()
        gaussian = name.endswith(('.gjf', '.com'))
        pw = text.lstrip().lower().startswith('&control')
        self.edit = CodeEdit(text, comment='!' if gaussian or pw else '#')
        if len(text) < 1_000_000:  # the colours of an input it recognises (not of a long output)
            from azimuth.text_editor import guess_language

            self.edit.set_language(guess_language(name, text))
        self.edit.setReadOnly(read_only)
        self.pane = EditorPane(self.edit, save=None if read_only else self.accept)
        column.addWidget(self.pane, 1)
        row = QHBoxLayout()
        row.addStretch(1)
        # no default button: Enter in the fields of the find bar finds, it does not close the window
        if read_only:
            row.addWidget(button(tr('Закрыть'), self.reject, True))
        else:
            row.addWidget(button(tr('Отмена'), self.reject))
            save = button(tr('Сохранить'), self.accept, True)
            save.setToolTip(tr('Сохранить · Ctrl+S'))
            row.addWidget(save)
        for item in self.findChildren(QPushButton):
            item.setAutoDefault(False)
            item.setDefault(False)
        column.addLayout(row)
        self.resize(900, 680)
