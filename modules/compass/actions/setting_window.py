"""«Кристалл → Установка ячейки…»: the cell of the crystal in another setting of its group or as the
reduced cell (crystal_setting) — the crystal shown again in the cell chosen.

§1 PURPOSE
    The transformation of the cell, as in Mercury: one structure
    is printed as P 21/c in one paper and as P 21/n in another; the reduced cell compares two files of one crystal.
§4 SPECIFICATION
    show(studio) -> SettingWindow | None; SettingWindow(parent, crystal, studio): rows — [(title, M)], the reduced cell
    last; apply(row) -> the crystal built in that cell.
§7 TESTS tests/gui/test_gui_files.py::test_another_setting_of_the_cell.
"""

from PySide6.QtWidgets import (QDialog, QHBoxLayout, QHeaderView, QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout,
                               QWidget)

from azimuth.i18n import tr
from azimuth.ui import action_button
from modules.compass.chemistry import crystal_setting as cs


def _cell_text(cell):
    return (f'{cell.a:.4f}, {cell.b:.4f}, {cell.c:.4f} Å · '
            f'{cell.alpha:.2f}°, {cell.beta:.2f}°, {cell.gamma:.2f}°')


class SettingWindow(QDialog):
    def __init__(self, parent, crystal, studio=None, title=''):
        super().__init__(parent)
        self.crystal, self.studio = crystal, studio
        self.setWindowTitle(tr('Установка ячейки · ') + (title or crystal.title or 'CIF'))
        layout = QVBoxLayout(self)
        own = cs.identify(crystal.operations)
        self.summary = QLabel(tr('Сейчас: {}, ячейка {}.').format(
            cs.entry_name(own) or tr('группа без названия в таблице установок'), _cell_text(crystal.cell)))
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        self.rows = []
        for entry, m, cell in cs.settings(crystal):
            self.rows.append((cs.entry_name(entry) + (tr(' (файл)') if entry is own and m == cs._matrix(
                [[1, 0, 0], [0, 1, 0], [0, 0, 1]]) else ''), m, cell))
        try:
            reduced = cs.reduced_matrix(crystal)
            new = cs.transform(crystal, reduced)
            self.rows.append((tr('Приведённая ячейка') + (f' · {new.space_group}' if new.space_group else ''),
                              reduced, new.cell))
        except ValueError:
            pass
        self.table = QTableWidget(len(self.rows), 3)
        self.table.setHorizontalHeaderLabels([tr('Установка'), tr('Новые оси'), tr('Ячейка')])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        for r, (name, m, cell) in enumerate(self.rows):
            for c, text in enumerate((name, cs.matrix_text(m), _cell_text(cell))):
                self.table.setItem(r, c, QTableWidgetItem(text))
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(True)
        if self.rows:
            self.table.selectRow(0)
        self.table.doubleClicked.connect(lambda index: self.apply(index.row()))
        layout.addWidget(self.table, 1)
        note = QLabel(tr('Один кристалл описывают разные ячейки: оси можно переименовать, а у моноклинной группы есть '
                         'три выбора ячейки (P 21/c, P 21/n, P 21/a — одна группа № 14). Приведённая ячейка (Бюргер, '
                         'Нигли) — три кратчайших вектора примитивной решётки, углы все острые или все не острые: у '
                         'двух файлов одного кристалла она одна. Атомы остаются на своих местах — меняются только '
                         'оси и дробные координаты; тепловые эллипсоиды файла в новых осях не показываются.'))
        note.setWordWrap(True)
        note.setObjectName('subtitle')
        layout.addWidget(note)
        bottom = QHBoxLayout()
        bottom.addWidget(action_button(tr('Открыть в выбранной установке'), lambda: self.apply(), 'cell'))
        bottom.addStretch(1)
        bottom.addWidget(action_button(tr('Закрыть'), self.accept, 'close'))
        layout.addLayout(bottom)
        self.resize(820, 420)

    def apply(self, row=None):
        if row is None:
            chosen = self.table.selectionModel().selectedRows()
            row = chosen[0].row() if chosen else 0
        if not 0 <= row < len(self.rows):
            return None
        _, m, _ = self.rows[row]
        try:
            new = cs.transform(self.crystal, m)
        except ValueError as exc:
            self.summary.setText(str(exc))
            return None
        if self.studio is not None:
            shown = getattr(self.studio, 'crystal', None)
            whole = bool(shown[3]) if shown and len(shown) > 3 else False
            self.studio.crystal_tool.build_crystal(new, (1, 1, 1), True, whole)
            self.studio.notify(tr('Кристалл в установке {}: {}.').format(new.space_group or tr('без названия'),
                                                                         cs.matrix_text(m)), 10000)
        return new


def show(studio):
    shown = getattr(studio, 'crystal', None)
    crystal = shown[0] if isinstance(shown, tuple) and shown else shown
    if crystal is None:
        studio.notify(tr('Откройте файл CIF: «Файл → Открыть…».'), 6000)
        return None
    window = SettingWindow(studio if isinstance(studio, QWidget) else None, crystal, studio)
    studio._setting_window = window
    window.show()
    return window
