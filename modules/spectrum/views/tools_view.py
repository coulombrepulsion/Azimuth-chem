"""«Инструменты» of Spectrum: the isotope pattern, the energies of several results, the Boltzmann shares.

§1 PURPOSE
    The tools of Chemcraft that belong to results: the windows over modules/spectrum/analysis/isotopes.py and
    boltzmann.py; tables saved as CSV in the style of «Настройки → Таблицы анализа».
§4 SPECIFICATION
    IsotopeDialog(owner, formula='') — formula, peaks (QTableWidget: M+n, m/z, %), plot, masses (label);
    show(formula) -> pattern. EnergiesDialog(owner, paths=None, temperature=298.15) — table, note; fill(paths).
    BoltzmannDialog(owner) — text, unit, temperature, table; compute() -> rows. Each: save_csv(path) -> path.
    SpectrumToolsTool (window.spectrum_tools): show_isotopes(formula=None), energies_of_files(paths=None),
    boltzmann_dialog(), current_formula().
§7 TESTS
    tests/test_gui.py::test_spectrum_tools.
"""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (QComboBox, QDialog, QDoubleSpinBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel,
                               QLineEdit, QPlainTextEdit, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from azimuth.i18n import tr
from azimuth.ui import button, label

UNITS = (('hartree', 'хартри'), ('kcal', 'ккал/моль'), ('kj', 'кДж/моль'), ('ev', 'эВ'))


def _table(headers):
    table = QTableWidget(0, len(headers))
    table.setHorizontalHeaderLabels([tr(h) for h in headers])
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.verticalHeader().hide()
    table.horizontalHeader().setStretchLastSection(True)
    return table


def _fill(table, rows):
    table.setRowCount(len(rows))
    for r, row in enumerate(rows):
        for c, text in enumerate(row):
            item = QTableWidgetItem(text)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(r, c, item)


def _save(owner, table, path, name):
    from modules.spectrum.wavefunction import field_tables

    if path is None:
        path, _ = QFileDialog.getSaveFileName(owner, tr('Сохранить таблицу'), name, 'CSV (*.csv)')
        if not path:
            return None
    header = [table.horizontalHeaderItem(c).text() for c in range(table.columnCount())]
    rows = [[table.item(r, c).text() if table.item(r, c) else '' for c in range(table.columnCount())]
            for r in range(table.rowCount())]
    return field_tables.write_csv(path, header, rows)


class PeakPlot(QWidget):
    """Sticks of the isotope cluster: one per M + n, the height in % of the largest."""

    def __init__(self):
        super().__init__()
        self.peaks = []
        self.setMinimumHeight(150)

    def paintEvent(self, event):
        if not self.peaks:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        ink = self.palette().text().color()
        left, bottom, top = 34, self.height() - 22, 12
        width = self.width() - left - 14
        shifts = [s for s, _, _ in self.peaks]
        low, high = min(shifts) - 0.5, max(shifts) + 0.5
        p.setPen(QPen(ink, 1))
        p.drawLine(QPointF(left, bottom), QPointF(left + width, bottom))
        font = QFont(self.font())
        font.setPixelSize(10)
        p.setFont(font)
        for s, _, share in self.peaks:
            x = left + (s - low) / (high - low) * width
            y = bottom - (bottom - top) * share / 100
            p.setPen(QPen(QColor('#2a62b8'), 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
            p.drawLine(QPointF(x, bottom), QPointF(x, y))
            p.setPen(ink)
            p.drawText(QRectF(x - 20, bottom + 3, 40, 14), Qt.AlignmentFlag.AlignCenter, 'M' if s == 0 else f'M+{s}')
        p.end()


class IsotopeDialog(QDialog):
    def __init__(self, owner, formula=''):
        super().__init__(owner)
        self.setWindowTitle(tr('Изотопный пик молекулярного иона'))
        lay = QVBoxLayout(self)
        note = label(tr('Распределение изотопов в молекулярном ионе: M — все атомы в самых лёгких изотопах, M+1, M+2… '
                        'Высота — в % от самого высокого пика. Формула без скобок, например C6H5Cl.'), 'subtitle')
        note.setWordWrap(True)
        lay.addWidget(note)
        row = QHBoxLayout()
        self.formula = QLineEdit(formula)
        self.formula.returnPressed.connect(lambda: self.show_pattern())
        row.addWidget(QLabel(tr('Формула')))
        row.addWidget(self.formula, 1)
        row.addWidget(button(tr('Посчитать'), lambda: self.show_pattern(), True))
        lay.addLayout(row)
        self.masses = label('', 'subtitle')
        lay.addWidget(self.masses)
        self.plot = PeakPlot()
        lay.addWidget(self.plot)
        self.peaks = _table(('Пик', 'm/z', '%'))
        lay.addWidget(self.peaks)
        bottom = QHBoxLayout()
        bottom.addWidget(button(tr('Сохранить CSV…'), lambda: self.save_csv()))
        bottom.addStretch(1)
        bottom.addWidget(button(tr('Закрыть'), self.accept))
        lay.addLayout(bottom)
        self.resize(460, 560)
        if formula:
            self.show_pattern()

    def show_pattern(self, formula=None):
        from modules.spectrum.analysis import isotopes

        if formula is not None:
            self.formula.setText(formula)
        try:
            counts = isotopes.formula_counts(self.formula.text())
            found = isotopes.pattern(counts, least=0.01)
        except ValueError as exc:
            self.masses.setText(tr(str(exc)))
            self.plot.peaks = []
            self.peaks.setRowCount(0)
            self.plot.update()
            return None
        self.masses.setText(tr('Моноизотопная масса: ') + f'{isotopes.monoisotopic(counts):.5f} · '
                            + tr('средняя: ') + f'{isotopes.average(counts):.3f}')
        self.plot.peaks = [row for row in found if row[2] >= 0.1]
        self.plot.update()
        _fill(self.peaks, [('M' if s == 0 else f'M+{s}', f'{m:.5f}', f'{p:.2f}') for s, m, p in found])
        return found

    def save_csv(self, path=None):
        return _save(self, self.peaks, path, (self.formula.text() or 'isotopes') + '_isotopes.csv')


class EnergiesDialog(QDialog):
    HEADERS = ('Файл', 'Программа', 'Уровень теории', 'E, хартри', 'G, хартри', 'ΔE', 'ΔG', 'Доля, %')

    def __init__(self, owner, paths=None, temperature=298.15):
        super().__init__(owner)
        self.setWindowTitle(tr('Энергии из нескольких файлов'))
        self.paths = list(paths or [])
        lay = QVBoxLayout(self)
        row = QHBoxLayout()
        row.addWidget(button(tr('Выбрать файлы…'), lambda: self.choose()))
        row.addWidget(QLabel(tr('Температура')))
        self.temperature = QDoubleSpinBox()
        self.temperature.setRange(1, 5000)
        self.temperature.setDecimals(2)
        self.temperature.setSuffix(' K')
        self.temperature.setValue(temperature)
        self.temperature.valueChanged.connect(lambda *_: self.fill(self.paths))
        row.addWidget(self.temperature)
        row.addStretch(1)
        lay.addLayout(row)
        self.table = _table(self.HEADERS)
        lay.addWidget(self.table)
        self.note = label('', 'subtitle')
        self.note.setWordWrap(True)
        lay.addWidget(self.note)
        bottom = QHBoxLayout()
        bottom.addWidget(button(tr('Сохранить CSV…'), lambda: self.save_csv()))
        bottom.addStretch(1)
        bottom.addWidget(button(tr('Закрыть'), self.accept))
        lay.addLayout(bottom)
        self.resize(820, 420)
        if self.paths:
            self.fill(self.paths)

    def choose(self):
        from modules.spectrum.views.reaction_view import RESULT_FILTER

        paths, _ = QFileDialog.getOpenFileNames(self, tr('Результаты расчётов'), '', tr(RESULT_FILTER))
        if paths:
            self.fill(paths)
        return paths

    def fill(self, paths, read=None):
        from azimuth import defaults
        from modules.spectrum.analysis import boltzmann

        self.paths = list(paths)
        if not self.paths:
            return None
        unit = tr(defaults.energy_name())
        headers = list(self.HEADERS)
        headers[5], headers[6] = f'ΔE, {unit}', f'ΔG, {unit}'
        self.table.setHorizontalHeaderLabels([tr(h) if k < 5 or k == 7 else h for k, h in enumerate(headers)])
        try:
            found = boltzmann.files_table(self.paths, self.temperature.value(), defaults.energy_factor(), read=read)
        except ValueError as exc:
            self.note.setText(str(exc))
            self.table.setRowCount(0)
            return None
        _fill(self.table, [(name, program, level, f'{e:.8f}', '—' if g is None else f'{g:.8f}', f'{de:.2f}',
                            '—' if dg is None else f'{dg:.2f}', f'{100 * p:.1f}')
                           for name, program, level, e, g, de, dg, p in found['rows']])
        by = tr('Доли — по G при ') if found['by'] == 'G' else tr('Доли — по E (электронной энергии) при ')
        self.note.setText(by + f'{self.temperature.value():g} K.' + ''.join(' ' + tr(w) for w in found['warnings']))
        return found

    def save_csv(self, path=None):
        return _save(self, self.table, path, 'energies.csv')


class BoltzmannDialog(QDialog):
    def __init__(self, owner):
        super().__init__(owner)
        self.setWindowTitle(tr('Доли по Больцману'))
        lay = QVBoxLayout(self)
        note = label(tr('По одной энергии в строке; перед числом можно название (conf-1  -76.4321). Доли считаются от '
                        'самой низкой энергии при выбранной температуре.'), 'subtitle')
        note.setWordWrap(True)
        lay.addWidget(note)
        self.text = QPlainTextEdit()
        self.text.setPlaceholderText('conf-1  -76.43210\nconf-2  -76.42980')
        self.text.setMaximumHeight(140)
        lay.addWidget(self.text)
        form = QFormLayout()
        self.unit = QComboBox()
        for key, title in UNITS:
            self.unit.addItem(tr(title), key)
        form.addRow(tr('Энергии в'), self.unit)
        self.temperature = QDoubleSpinBox()
        self.temperature.setRange(1, 5000)
        self.temperature.setDecimals(2)
        self.temperature.setSuffix(' K')
        self.temperature.setValue(298.15)
        form.addRow(tr('Температура'), self.temperature)
        lay.addLayout(form)
        row = QHBoxLayout()
        row.addWidget(button(tr('Посчитать'), lambda: self.compute(), True))
        row.addStretch(1)
        lay.addLayout(row)
        self.table = _table(('Название', 'Энергия', 'ΔE', 'Доля, %'))
        lay.addWidget(self.table)
        self.note = label('', 'subtitle')
        lay.addWidget(self.note)
        bottom = QHBoxLayout()
        bottom.addWidget(button(tr('Сохранить CSV…'), lambda: self.save_csv()))
        bottom.addStretch(1)
        bottom.addWidget(button(tr('Закрыть'), self.accept))
        lay.addLayout(bottom)
        self.resize(480, 560)

    def compute(self):
        from azimuth import defaults
        from modules.spectrum.analysis import boltzmann

        try:
            rows = boltzmann.typed_table(boltzmann.parse_energies(self.text.toPlainText()), self.unit.currentData(),
                                         self.temperature.value(), defaults.energy_factor())
        except ValueError as exc:
            self.note.setText(tr(str(exc)))
            self.table.setRowCount(0)
            return None
        self.table.setHorizontalHeaderLabels([tr('Название'), tr('Энергия'), 'ΔE, ' + tr(defaults.energy_name()),
                                              tr('Доля, %')])
        _fill(self.table, [(n, f'{v:g}', f'{d:.2f}', f'{100 * p:.1f}') for n, v, d, p in rows])
        self.note.setText('')
        return rows

    def save_csv(self, path=None):
        return _save(self, self.table, path, 'boltzmann.csv')


class SpectrumToolsTool:
    """Was the mixin SpectrumTools of the window; a part of its own — it reaches the window only through
    the names of PORT (azimuth/window_port.WindowPort)."""

    PORT = (
        'molecule',
        'output',
    )

    def __init__(self, window):
        from azimuth.window_port import WindowPort

        self.w = WindowPort(window, self.PORT)


    def current_formula(self):
        """The formula of the result shown, else of the structure of the tab (Hill order: C, H, then A–Z)."""
        output = getattr(self.w, 'output', None)
        geometry = getattr(output, 'final_geometry', None) or getattr(output, 'geometry', None)
        molecule = geometry if getattr(geometry, 'atoms', None) else getattr(self.w, 'molecule', None)
        if molecule is None or not molecule.atoms:
            return ''
        counts = {}
        for a in molecule.atoms:
            if a.symbol != 'X':
                counts[a.symbol] = counts.get(a.symbol, 0) + 1
        order = (['C', 'H'] if 'C' in counts else []) + sorted(s for s in counts if not ('C' in counts and s in 'CH'))
        return ''.join(s + (str(counts[s]) if counts[s] > 1 else '') for s in order if s in counts)

    def show_isotopes(self, formula=None):
        dialog = IsotopeDialog(self.w.widget, self.current_formula() if formula is None else formula)
        self.isotope_dialog = dialog
        dialog.show()
        return dialog

    def energies_of_files(self, paths=None):
        dialog = EnergiesDialog(self.w.widget, paths)
        self.energies_dialog = dialog
        dialog.show()
        if paths is None:
            dialog.choose()
        return dialog

    def boltzmann_dialog(self):
        dialog = BoltzmannDialog(self.w.widget)
        self.boltzmann_window = dialog
        dialog.show()
        return dialog
