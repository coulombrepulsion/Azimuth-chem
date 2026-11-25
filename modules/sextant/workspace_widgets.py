"""The small widgets of the page of Sextant: fill_grouped (a list of methods or basis sets by family), GuessPicker
(the file of the starting orbitals) and WrappedNote (a wrapped note of an exact height).

Split off modules/sextant/workspace.py (0.222.29).
"""

import re
from pathlib import Path
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import QLabel, QLineEdit, QFileDialog, QHBoxLayout, QWidget
from azimuth.ui import icon_button
from azimuth.i18n import tr


def fill_grouped(combo, keys, table, current, default):
    """Items of keys under bold, unselectable family headers (table[key][0]); keeps current when possible."""
    combo.blockSignals(True)
    combo.clear()
    family = None
    for key in keys:
        if table[key][0] != family:
            family = table[key][0]
            combo.addItem(tr(family))
            model = combo.model()
            if isinstance(model, QStandardItemModel):
                item = model.item(combo.count() - 1)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable & ~Qt.ItemFlag.ItemIsEnabled)
                font = item.font()
                font.setBold(True)
                item.setFont(font)
        combo.addItem(key, key)
    choice = current if current in keys else default if default in keys else (keys[0] if keys else None)
    if choice is not None:
        combo.setCurrentIndex(combo.findData(choice))
    combo.blockSignals(False)


class GuessPicker(QWidget):
    """«Начальные орбитали» — the .gbw of an earlier calculation of ORCA to start from (MORead): the name of the
    file, a folder button to choose it (it opens next to the result of the tab, its .gbw chosen), a cross to go back to
    the program's own guess. changed() when the path changes."""

    changed = Signal()

    def __init__(self, owner):
        super().__init__()
        self.owner = owner
        self._path = ''
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)
        self.name = QLineEdit()
        self.name.setReadOnly(True)
        self.name.setPlaceholderText(tr('Своё начальное приближение программы'))
        self.name.setToolTip(tr('Старт с орбиталей прошлого расчёта ORCA (MORead): SCF сходится быстрее и к тому же '
                                'состоянию — после оборванного расчёта, для близкой геометрии или другого метода'))
        row.addWidget(self.name, 1)
        self.choose_button = icon_button(tr('Выбрать файл .gbw прошлого расчёта…'), self.choose, 'folder')
        self.clear_button = icon_button(tr('Без начальных орбиталей'), lambda: self.set_path(''), 'close')
        for item in (self.choose_button, self.clear_button):
            item.setFixedSize(28, 28)
            row.addWidget(item)
        self.clear_button.setEnabled(False)

    def path(self):
        return self._path

    def set_path(self, path, quiet=False):
        path = str(path or '')
        if path == self._path:
            return path
        self._path = path
        self.name.setText(Path(path).name if path else '')
        self.name.setToolTip(path or self.name.toolTip())
        self.clear_button.setEnabled(bool(path))
        if not quiet:
            self.changed.emit()
        return path

    def suggested(self):
        """The .gbw next to the output of the result of the tab, else the folder of the calculations."""
        output = getattr(self.owner, 'output_path', None)
        if output:
            gbw = Path(output).with_suffix('.gbw')
            return str(gbw if gbw.is_file() else Path(output).parent)
        root = getattr(getattr(self.owner, 'run_tool', None), 'jobs_root', None)
        return str(root()) if root is not None else str(Path.home())

    def choose(self, *args):

        path, _ = QFileDialog.getOpenFileName(self, tr('Начальные орбитали'), self.suggested(),
                                              tr('Орбитали ORCA (*.gbw)'))
        if path:
            self.set_path(path)
        return path


class WrappedNote(QLabel):
    """A note of several lines under the task — QFormLayout gave a word-wrapped label one line, and the note of
    «Частоты и термохимия» was cut off; the label asks for the height of its text at its width."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('subtitle')
        self.setWordWrap(True)

    def _fit(self):
        width = self.width() if self.width() > 50 else 360
        text = self.text()
        if text and self.textFormat() != Qt.TextFormat.RichText and not re.search(r'<[A-Za-z/][^>]*>', text):
            # the height of the lines measured by the font itself: heightForWidth of the label counted 7 lines for the
            # 4 of the card of the molecule at 370 px, and the card showed a gap of 50 px over «Примерное время
            # расчёта» (the owner, 2026-11-23: «опять много места над временем расчёта»). Fixed, so that the layout
            # does not give it the height of heightForWidth either
            from PySide6.QtCore import QRect

            flags = int(Qt.TextFlag.TextWordWrap) | int(self.alignment().value)
            need = self.fontMetrics().boundingRect(QRect(0, 0, width, 100000), flags, text).height() + 2
            if need != self.minimumHeight() or need != self.maximumHeight():
                self.setFixedHeight(need)
            return
        need = self.heightForWidth(width) if text else 0
        if self.maximumHeight() != 16777215:
            self.setMaximumHeight(16777215)
        if need > 0 and need != self.minimumHeight():
            self.setMinimumHeight(need)

    def setText(self, text):
        super().setText(text)
        self._fit()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit()
