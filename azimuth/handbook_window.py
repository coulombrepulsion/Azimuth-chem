"""«Справка → Справочник»: units and constants, solvents, scaling factors of frequencies and where to find measured
data (azimuth/handbook.py — the data and their sources).

§1 PURPOSE
    A window to look a fact up during the preparation of a calculation or the reading of its result, each table with
    its source. It opens on a tab: from the menu, from «?» at the solvent of Sextant (the solvents), from the scaling of
    the IR spectrum of Spectrum (the factors — a double click or «Применить» puts the factor into the spectrum), from
    «Опытные данные…» of Spectrum (the databases, with the formula of the molecule).
§2 RULES
    1. The field «Найти» hides the rows of the table of the tab shown that do not contain its text.
    2. Numbers are written with the decimal comma in Russian; a number typed is read with either.
    3. Links open in the browser of the system; nothing is fetched by the program.
§3 INTERFACE
    HandbookDialog(parent=None, tab='units', formula='', apply_factor=None, level=None); show_tab(key); TABS;
    open_handbook(owner, tab='units', **options) — the window of owner (a new one each time it is asked, the last kept
    as owner.handbook_dialog).
§7 TESTS tests/gui/test_handbook_window.py; tests/core/test_handbook.py.
"""

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QGroupBox, QHBoxLayout, QHeaderView, QLabel,
                               QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget)

from azimuth import handbook
from azimuth.i18n import tr

TABS = ('units', 'solvents', 'factors', 'experiment')
TITLES = {'units': 'Единицы и константы', 'solvents': 'Растворители', 'factors': 'Множители частот',
          'experiment': 'Опытные данные'}
QUANTITIES = {'energy': 'Энергия', 'length': 'Длина', 'dipole': 'Дипольный момент'}


def num(value, digits=10):
    """A number of `digits` significant digits, with the decimal comma in Russian."""
    from azimuth import i18n

    if value is None:
        return '—'
    text = f'{value:.{digits}g}'
    return text.replace('.', ',') if i18n.LANG == 'ru' else text


def fixed(value, decimals=3):
    """A number with its decimals kept (0,940, not 0,94), the decimal comma in Russian."""
    from azimuth import i18n

    if value is None:
        return '—'
    text = f'{value:.{decimals}f}'
    return text.replace('.', ',') if i18n.LANG == 'ru' else text


def read_number(text):
    return float(text.strip().replace(' ', '').replace(' ', '').replace(',', '.'))


def source(text, url):
    label = QLabel(f'{tr("Источник")}: <a href="{url}">{text}</a>')
    label.setOpenExternalLinks(True)
    label.setWordWrap(True)
    label.setStyleSheet('color: #5b6474;')
    return label


def table(headers):
    found = QTableWidget(0, len(headers))
    found.setHorizontalHeaderLabels([tr(h) for h in headers])
    found.verticalHeader().hide()
    found.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    found.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    found.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    found.setAlternatingRowColors(True)
    found.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    found.horizontalHeader().setStretchLastSection(True)
    return found


def fill(found, rows):
    found.setRowCount(len(rows))
    for r, row in enumerate(rows):
        for c, value in enumerate(row):
            item = QTableWidgetItem('—' if value in (None, '') else str(value))
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            found.setItem(r, c, item)


class HandbookDialog(QDialog):
    """The tabs of the handbook with a search field above them; apply_factor(factor) — the scaling of Spectrum (the
    tab of the factors gets «Применить»); level — (method, basis) of the result shown, its row chosen."""

    def __init__(self, parent=None, tab='units', formula='', apply_factor=None, level=None):
        super().__init__(parent)
        self.setWindowTitle(tr('Справочник'))
        self.resize(1000, 660)
        self.apply_factor = apply_factor
        outer = QVBoxLayout(self)
        top = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText(tr('Найти в таблице…'))
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.filter_rows)
        top.addWidget(self.search, 1)
        outer.addLayout(top)
        self.tabs = QTabWidget()
        self.tables = {}
        builders = {'units': self._units, 'solvents': self._solvents, 'factors': self._factors,
                    'experiment': self._experiment}
        for key in TABS:
            self.tabs.addTab(builders[key](), tr(TITLES[key]))
        self.tabs.currentChanged.connect(lambda *_: self.filter_rows(self.search.text()))
        outer.addWidget(self.tabs, 1)
        if formula:
            self.formula.setText(formula)
        if level:
            self.choose_level(*level)
        self.show_tab(tab)

    def show_tab(self, key):
        self.tabs.setCurrentIndex(TABS.index(key) if key in TABS else 0)

    def current_table(self):
        return self.tables.get(TABS[self.tabs.currentIndex()])

    def filter_rows(self, text):
        found = self.current_table()
        if found is None:
            return
        text = (text or '').strip().lower()
        for r in range(found.rowCount()):
            cells = ' '.join(found.item(r, c).text() for c in range(found.columnCount()) if found.item(r, c))
            found.setRowHidden(r, bool(text) and text not in cells.lower())

    # -- the units and the constants ------------------------------------------------------------------------------
    def _units(self):
        page = QWidget()
        layout = QHBoxLayout(page)  # the converter and the constants side by side: one over the other cut the note
        box = QGroupBox(tr('Пересчёт единиц'))
        inner = QVBoxLayout(box)
        row = QHBoxLayout()
        self.quantity = QComboBox()
        for key, title in QUANTITIES.items():
            self.quantity.addItem(tr(title), key)
        self.value = QLineEdit(num(1.0))
        self.value.setMinimumWidth(90)
        self.value.setMaximumWidth(140)
        self.unit = QComboBox()
        row.addWidget(self.quantity)
        row.addWidget(self.value)
        row.addWidget(self.unit)
        inner.addLayout(row)
        self.converted = table(('Единица', 'Значение'))
        inner.addWidget(self.converted, 1)
        self.unit_note = QLabel()
        self.unit_note.setWordWrap(True)
        self.unit_note.setStyleSheet('color: #5b6474;')
        inner.addWidget(self.unit_note)
        box.setMaximumWidth(380)
        layout.addWidget(box)
        self.quantity.currentIndexChanged.connect(self._units_of_quantity)
        self.unit.currentIndexChanged.connect(self.convert)
        self.value.textChanged.connect(self.convert)
        self._units_of_quantity()
        constants = QGroupBox(tr('Фундаментальные постоянные'))
        inner = QVBoxLayout(constants)
        self.constants = table(('Величина', 'Обозначение', 'Значение', 'Единица'))
        self.constants.horizontalHeader().setStretchLastSection(False)
        self.constants.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        fill(self.constants, [(tr(name) + (' ' + tr('(точно)') if exact else ''), symbol, num(value, 11), tr(unit))
                              for name, symbol, value, unit, exact in handbook.CONSTANTS])
        inner.addWidget(self.constants)
        inner.addWidget(source(handbook.CODATA, handbook.CODATA_URL))
        layout.addWidget(constants, 1)
        self.tables['units'] = self.constants
        return page

    def _units_of_quantity(self):
        kind = self.quantity.currentData()
        self.unit.blockSignals(True)
        self.unit.clear()
        for name in handbook.units(kind):
            self.unit.addItem(tr(name), name)
        self.unit.blockSignals(False)
        notes = {'energy': 'ккал/моль — термохимическая калория (4,184 Дж); К — температура, при которой kT равно этой '
                           'энергии; нм — длина волны фотона этой энергии.',
                 'length': '1 бор — атомная единица длины, a₀.',
                 'dipole': '1 Д = 10⁻²¹/c Кл·м; программы печатают диполь в дебаях или в атомных единицах (e·бор).'}
        self.unit_note.setText(tr(notes[kind]))
        self.convert()

    def convert(self, *args):
        kind, unit = self.quantity.currentData(), self.unit.currentData()
        try:
            found = handbook.convert(kind, read_number(self.value.text()), unit)
        except (ValueError, TypeError):
            fill(self.converted, [])
            return None
        fill(self.converted, [(tr(name), num(found[name])) for name in handbook.units(kind)])
        return found

    # -- the solvents ---------------------------------------------------------------------------------------------
    def _solvents(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        intro = QLabel(tr('Диэлектрическая проницаемость ε при 20–25 °C и имя, под которым растворитель знает каждая '
                          'программа; «—» — у программы (её модели) такого растворителя нет. Для GAMESS и NWChem '
                          'Секстант растворитель пока не пишет.'))
        intro.setWordWrap(True)
        layout.addWidget(intro)
        headers = ('Растворитель', 'ε') + tuple(title for title, _ in handbook.PROGRAM_COLUMNS)
        self.solvents = table(headers)
        fill(self.solvents, [(tr(r['name']), num(r['epsilon'], 4)) + tuple(r[kind] for _, kind in
                                                                            handbook.PROGRAM_COLUMNS)
                             for r in handbook.solvent_rows()])
        layout.addWidget(self.solvents, 1)
        layout.addWidget(source('CRC Handbook of Chemistry and Physics (ε); руководства ORCA, Gaussian, xtb, Psi4, MOPAC',
                                'https://openmopac.github.io/keywords.html'))
        self.tables['solvents'] = self.solvents
        return page

    # -- the scaling factors --------------------------------------------------------------------------------------
    def _factors(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        intro = QLabel(tr('Гармонические частоты метода выше наблюдаемых: ν(опыт) ≈ c·ω(расчёт). Множитель подобран '
                          'по сотням молекул; ± — стандартное отклонение, насколько может отличаться отдельная полоса.'))
        intro.setWordWrap(True)
        layout.addWidget(intro)
        row = QHBoxLayout()
        self.factor_method = QComboBox()
        self.factor_method.addItem(tr('Все методы'), None)
        for method in dict.fromkeys(r['method'] for r in handbook.factor_rows()):
            self.factor_method.addItem(method, method)
        self.factor_method.currentIndexChanged.connect(self._fill_factors)
        row.addWidget(QLabel(tr('Метод:')))
        row.addWidget(self.factor_method)
        row.addStretch()
        self.apply_button = QPushButton(tr('Применить к спектру'))
        self.apply_button.setVisible(self.apply_factor is not None)
        self.apply_button.clicked.connect(self.apply_chosen)
        row.addWidget(self.apply_button)
        layout.addLayout(row)
        self.factors = table(('Метод', 'Базис', 'Множитель', '±'))
        self.factors.itemDoubleClicked.connect(lambda *_: self.apply_chosen())
        layout.addWidget(self.factors, 1)
        layout.addWidget(source(handbook.FACTOR_SOURCE, handbook.FACTOR_URL))
        self.tables['factors'] = self.factors
        self._fill_factors()
        return page

    def _fill_factors(self, *args):
        self.factor_list = handbook.factor_rows(self.factor_method.currentData())
        fill(self.factors, [(r['method'], r['basis'], fixed(r['factor']), fixed(r['uncertainty']))
                            for r in self.factor_list])
        self.filter_rows(self.search.text() if hasattr(self, 'search') else '')

    def choose_level(self, method, basis):
        """The row of a method and basis (as Spectrum names them), if the table has it."""
        for r, entry in enumerate(self.factor_list):
            if entry['method'].lower() == (method or '').lower() and entry['basis'].lower() == (basis or '').lower():
                self.factors.selectRow(r)
                return r
        return None

    def apply_chosen(self):
        rows = self.factors.selectionModel().selectedRows()
        if self.apply_factor is None or not rows:
            return None
        factor = self.factor_list[rows[0].row()]['factor']
        self.apply_factor(factor)
        return factor

    # -- the measured data ----------------------------------------------------------------------------------------
    def _experiment(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        intro = QLabel(tr('С чем сравнить расчёт: опытные спектры, геометрии, частоты и термохимия. Ссылки открываются в '
                          'браузере.'))
        intro.setWordWrap(True)
        layout.addWidget(intro)
        row = QHBoxLayout()
        row.addWidget(QLabel(tr('Формула:')))
        self.formula = QLineEdit()
        self.formula.setPlaceholderText('CH2O')
        self.formula.setMaximumWidth(200)
        row.addWidget(self.formula)
        self.formula_buttons = []
        for title, _ in handbook.formula_links('X'):
            button = QPushButton(title)
            button.clicked.connect(lambda checked=False, t=title: self.open_formula(t))
            row.addWidget(button)
            self.formula_buttons.append(button)
        row.addStretch()
        layout.addLayout(row)
        self.databases = table(('База данных', 'Что там есть'))
        fill(self.databases, [(d['name'], tr(d['what'])) for d in handbook.DATABASES])
        self.databases.setWordWrap(True)
        self.databases.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.databases.resizeRowsToContents()
        self.databases.itemDoubleClicked.connect(lambda item: self.open_url(handbook.DATABASES[item.row()]['url']))
        layout.addWidget(self.databases, 1)
        hint = QLabel(tr('Двойной щелчок по строке открывает сайт базы.'))
        hint.setStyleSheet('color: #5b6474;')
        layout.addWidget(hint)
        self.tables['experiment'] = self.databases
        return page

    def formula_url(self, title):
        return dict(handbook.formula_links(self.formula.text())).get(title)

    def open_formula(self, title):
        url = self.formula_url(title)
        if url:
            self.open_url(url)
        return url

    @staticmethod
    def open_url(url):
        QDesktopServices.openUrl(QUrl(url))


def open_handbook(owner, tab='units', **options):
    """The handbook on a tab, over owner; the last window is kept (owner.handbook_dialog) and replaced by the next."""
    old = getattr(owner, 'handbook_dialog', None)
    if old is not None:
        try:
            old.close()
        except RuntimeError:  # its C++ part is gone
            pass
    dialog = HandbookDialog(owner, tab, **options)
    owner.handbook_dialog = dialog
    dialog.show()
    return dialog
