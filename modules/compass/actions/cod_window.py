"""«Файл → Найти кристалл в COD…»: a search of the Crystallography Open Database and its CIF opened in
«Компас · Кристалл» (cod.py).

§1 PURPOSE
    The roadmap, «Кристаллы: очередь дальше», 4: Mercury opens the structures of the paid CSD; the open COD has half
    a million of them — found here by words, a formula or elements, opened with one click.
§2 ALGORITHM
    The search and the download in a worker thread (threading + a queued signal, as «Молекула по названию…»), the
    answer in the table; the CIF is saved into FOLDER (Documents/Azimuth/COD/<number>.cif — the default projects
    folder's parent) and opened as any CIF (opening_tool.open_path: the crystal gets its project).
§4 SPECIFICATION
    show(studio) -> CodWindow; CodWindow(parent, studio): words, formula, elements (QLineEdit), exact (QCheckBox),
    table, status; find(wait=False) -> started; answer((kind, payload, error)); open_entry(row=None) -> started;
    folder() -> Path. The worker's function: worker (default cod.search / cod.fetch; replaced in the tests).
§7 TESTS tests/gui/test_gui_files.py::test_a_crystal_from_cod (a fake server).
"""

import json
import threading

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from azimuth.i18n import tr
from azimuth.ui import action_button
from modules.compass.chemistry import cod


class CodWindow(QDialog):
    def __init__(self, parent, studio=None):
        super().__init__(parent)
        from modules.compass.actions.naming_actions import _Relay

        self.studio, self.entries, self.count, self.busy = studio, [], 0, False
        self.search_function, self.fetch_function = cod.search, cod.fetch
        self.relay = _Relay(self)
        self.relay.done.connect(self.answer)
        self.setWindowTitle(tr('Кристаллы из COD'))
        layout = QVBoxLayout(self)
        note = QLabel(tr('Crystallography Open Database — открытая база кристаллических структур (около полумиллиона '
                         'CIF): органика, неорганика, минералы. Нужен интернет; отправляются только условия поиска.'))
        note.setWordWrap(True)
        note.setObjectName('subtitle')
        layout.addWidget(note)
        row = QHBoxLayout()
        self.words = QLineEdit()
        self.words.setPlaceholderText(tr('слова: benzoic acid, quartz, автор…'))
        self.formula = QLineEdit()
        self.formula.setPlaceholderText(tr('формула: C7H6O2'))
        self.elements = QLineEdit()
        self.elements.setPlaceholderText(tr('элементы: Cu O'))
        for box in (self.words, self.formula, self.elements):
            box.returnPressed.connect(self.find)
        row.addWidget(self.words, 3)
        row.addWidget(self.formula, 2)
        row.addWidget(self.elements, 2)
        self.exact = QCheckBox(tr('только эти элементы'))
        row.addWidget(self.exact)
        self.find_button = action_button(tr('Найти'), self.find, 'search')
        row.addWidget(self.find_button)
        layout.addLayout(row)
        # the search by the cell (the form «search by cell» of COD)
        cells = QHBoxLayout()
        self.cell = QLineEdit()
        self.cell.setPlaceholderText(tr('ячейка: a b c (Å) или a b c α β γ'))
        self.cell.returnPressed.connect(self.find)
        cells.addWidget(self.cell, 4)
        self.tolerance = QComboBox()
        for value in (0.5, 1.0, 2.0, 5.0):
            self.tolerance.addItem(tr('± {} % длины, ± {}°').format(f'{value:g}'.replace('.', ','), f'{value:g}'.replace('.', ',')),
                                   value)
        self.tolerance.setCurrentIndex(1)
        cells.addWidget(self.tolerance)
        self.any_order = QCheckBox(tr('в любом порядке осей'))
        self.any_order.setToolTip(tr('Та же ячейка в другой установке: длины перебираются во всех порядках (углы тогда '
                                     'не учитываются); шесть запросов вместо одного'))
        cells.addWidget(self.any_order)
        self.from_crystal = action_button(tr('Как у открытого'), self.cell_of_crystal, 'import')
        self.from_crystal.setToolTip(tr('Ячейка кристалла, открытого в Компасе: найти ту же структуру и её полиморфы'))
        cells.addWidget(self.from_crystal)
        layout.addLayout(cells)
        self.status = QLabel('')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([tr('Номер COD'), tr('Формула'), tr('Название'), tr('Группа'),
                                              'a, b, c, Å; α, β, γ, °', tr('Год')])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.cellDoubleClicked.connect(lambda r, _c: self.open_entry(r))
        layout.addWidget(self.table, 1)
        bottom = QHBoxLayout()
        self.open_button = action_button(tr('Открыть в Компасе'), lambda: self.open_entry(), 'import')
        self.open_button.setEnabled(False)
        bottom.addWidget(self.open_button)
        self.page_button = action_button(tr('Страница в COD'), self.open_page, 'link')
        self.page_button.setEnabled(False)
        bottom.addWidget(self.page_button)
        self.table.itemSelectionChanged.connect(self._selected)
        bottom.addStretch(1)
        bottom.addWidget(action_button(tr('Закрыть'), self.accept, 'close'))
        layout.addLayout(bottom)
        self.resize(900, 560)

    def folder(self):
        from azimuth import project_folders

        return project_folders.default_projects_root().parent / 'COD'

    def _row(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()})
        return rows[0] if rows else None

    def _selected(self):
        chosen = self._row() is not None and not self.busy
        self.open_button.setEnabled(chosen)
        self.page_button.setEnabled(self._row() is not None)

    def _run(self, kind, job):
        self.busy = True
        self.find_button.setEnabled(False)
        self.open_button.setEnabled(False)
        relay = self.relay

        def work():
            try:
                relay.done.emit((kind, job(), None))
            except Exception as exc:  # no network, a timeout, an answer that is not JSON: said in the status line
                relay.done.emit((kind, None, exc))

        threading.Thread(target=work, daemon=True).start()
        return True

    def find(self):
        if self.busy:
            return False
        words, formula = self.words.text(), self.formula.text()
        elements = self.elements.text().replace(',', ' ').split()
        try:
            cell = cod.parse_cell(self.cell.text()) if self.cell.text().strip() else None
            value = float(self.tolerance.currentData() or cod.TOLERANCE)
            options = dict(cell=cell, tolerance=value, angle_tolerance=value, any_order=self.any_order.isChecked())
            cod.url(words, formula, elements, self.exact.isChecked(), cell, value, value)
        except ValueError as exc:
            self.status.setText(str(exc))
            return False
        self.status.setText(tr('Ищу в COD…'))
        search = self.search_function
        return self._run('search', lambda: search(words, formula, elements, self.exact.isChecked(), **options))

    def cell_of_crystal(self):
        """The cell of the crystal open in Compass into the field; the text or None."""
        shown = getattr(self.studio, 'crystal', None) if self.studio is not None else None
        crystal = shown[0] if isinstance(shown, tuple) and shown else shown
        if crystal is None:
            self.status.setText(tr('В Компасе не открыт кристалл.'))
            return None
        c = crystal.cell
        text = ' '.join(f'{v:.4f}'.rstrip('0').rstrip('.') for v in (c.a, c.b, c.c, c.alpha, c.beta, c.gamma))
        self.cell.setText(text)
        return text

    def open_entry(self, row=None):
        row = self._row() if row is None else row
        if self.busy or row is None or not 0 <= row < len(self.entries):
            return False
        number = self.entries[row].number
        self.status.setText(tr('Загружаю CIF {} из COD…').format(number))
        fetch = self.fetch_function
        return self._run('cif', lambda: (number, fetch(number)))

    def open_page(self):
        row = self._row()
        if row is None or not 0 <= row < len(self.entries):
            return False
        return QDesktopServices.openUrl(QUrl(cod.PAGE.format(self.entries[row].number)))

    def answer(self, message):
        kind, payload, error = message
        self.busy = False
        self.find_button.setEnabled(True)
        self._selected()
        if error is not None:
            self.status.setText(self.problem(error))
            return None
        if kind == 'search':
            self.entries, self.count = payload
            self.fill()
            return self.entries
        number, text = payload
        folder = self.folder()
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f'{number}.cif'
        path.write_text(text, encoding='utf-8')
        self.status.setText(tr('Открыт COD {} — файл в папке {}.').format(number, str(folder)))
        if self.studio is not None:
            self.studio.opening_tool.open_path(str(path))
        return path

    def fill(self):
        if not self.entries:
            self.status.setText(tr('Ничего не найдено. Проверьте формулу (C7H6O2) или ослабьте условия.'))
        elif self.count > len(self.entries):
            self.status.setText(tr('Найдено {}; показаны первые {} — уточните условия.').format(self.count, len(self.entries)))
        else:
            self.status.setText(tr('Найдено: {}. Двойной щелчок — открыть в Компасе.').format(self.count))
        self.table.setRowCount(len(self.entries))
        for k, e in enumerate(self.entries):
            cell = ('{:.3f} {:.3f} {:.3f}; {:.1f} {:.1f} {:.1f}'.format(*e.cell) if e.cell else '')
            for c, text in enumerate((e.number, e.formula, e.name, e.group, cell, e.year)):
                item = QTableWidgetItem(text)
                if c == 2 and e.journal:
                    item.setToolTip(e.journal + (f' · doi {e.doi}' if e.doi else ''))
                self.table.setItem(k, c, item)
        self._selected()

    @staticmethod
    def problem(error):
        from modules.compass.chemistry import pubchem

        if isinstance(error, json.JSONDecodeError):
            return tr('COD ответил не так, как ожидалось.')
        if isinstance(error, ValueError):
            return str(error)
        why = pubchem.reason(error)
        return {
            'certificate': tr('COD: не удалось проверить сертификат сервера. Python с python.org не знает корневых '
                              'сертификатов — запустите «Install Certificates.command» из папки Python в «Программах».'),
            'timeout': tr('COD не ответил вовремя — попробуйте ещё раз или уточните условия.'),
            'server': tr('COD ответил ошибкой: ') + str(getattr(error, 'code', '')),
        }.get(why, tr('COD недоступен — проверьте подключение к интернету.') + ' (' +
              str(getattr(error, 'reason', error))[:120] + ')')


def show(studio):
    window = CodWindow(studio if isinstance(studio, QWidget) else None, studio)
    studio._cod_window = window
    window.show()
    return window

