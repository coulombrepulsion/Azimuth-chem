"""«Инструменты» of Spectrum: the isotope pattern, the energies of several results, the Boltzmann shares, the equilibrium of two forms, the hindered rotor.

§1 PURPOSE
    The tools of Chemcraft that belong to results: the windows over modules/spectrum/analysis/isotopes.py and
    boltzmann.py; tables saved as CSV in the style of «Настройки → Таблицы анализа».
§4 SPECIFICATION
    IsotopeDialog(owner, formula='') — formula, peaks (QTableWidget: M+n, m/z, %), plot, masses (label);
    show(formula) -> pattern. EnergiesDialog(owner, paths=None, temperature=298.15) — table, note; fill(paths).
    BoltzmannDialog(owner) — text, unit, temperature, table; compute() -> rows. Each: save_csv(path) -> path.
    SpectrumToolsTool (window.spectrum_tools): show_isotopes(formula=None), energies_of_files(paths=None),
    boltzmann_dialog(), equilibrium_dialog(paths=None), current_formula().
    EquilibriumDialog(owner, read=None) — set_form(k, path), sigmas, mirrors, temperature, qrrho, table (K(T) at
    200–600 K and the chosen T), factors (what K is made of at the chosen T), compute(), copy(), save_csv(path).
    HinderedRotorDialog(owner) — set_scan(path), cover, sigma, wavenumber (0 — from the curvature of the scan),
    temperature, table (q of the harmonic oscillator, the hindered and the free rotor, ΔG and the factor of K at
    200–600 K and the chosen T), compute(), copy(), save_csv(path); hindered_rotor_dialog(path=None) of the tool.
    methods_dialog(folder=None) of the tool — «Методика расчёта…» (modules/spectrum/views/methods_view.py).
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


class EquilibriumDialog(QDialog):
    """«Равновесие двух форм…»: K(T), the shares and the factors of K (modules/spectrum/analysis/equilibrium.py)."""

    HEADERS = ('T, K', 'ΔG°', 'K', 'Доля A, %', 'Доля B, %')
    FACTOR_NAMES = (('energy', 'exp(−ΔE₀/RT): разность энергий с нулевыми колебаниями'),
                    ('translational', 'Поступательная сумма по состояниям'),
                    ('rotational', 'Вращательная сумма (с числом симметрии σ)'),
                    ('vibrational', 'Колебательная сумма'),
                    ('electronic', 'Электронная (мультиплетность)'),
                    ('mirror', 'Зеркальные формы'))

    def __init__(self, owner, read=None):
        from PySide6.QtWidgets import QCheckBox, QSpinBox

        super().__init__(owner)
        self.setWindowTitle(tr('Равновесие двух форм'))
        self.read = read
        self.species = [None, None]
        self.rows = []
        lay = QVBoxLayout(self)
        hint = label(tr('A ⇌ B: два результата «Оптимизация + частоты» одной молекулы (конформеры, таутомеры, '
                        'изомеры), посчитанные одним методом. K = [B]/[A].'), 'subtitle')
        hint.setWordWrap(True)
        lay.addWidget(hint)
        form = QFormLayout()
        self.names, self.sigmas, self.mirrors = [], [], []
        for k, letter in enumerate('AB'):
            row = QHBoxLayout()
            row.addWidget(button(tr('Выбрать файл…'), lambda *_, k=k: self.choose(k)))
            name = QLabel('—')
            self.names.append(name)
            row.addWidget(name, 1)
            row.addWidget(QLabel('σ'))
            sigma = QSpinBox()
            sigma.setRange(1, 60)
            sigma.setToolTip(tr('Вращательное число симметрии: число поворотов, совмещающих молекулу с собой. '
                                'Предложено по точечной группе геометрии — проверьте.'))
            sigma.valueChanged.connect(lambda *_: self.compute())
            self.sigmas.append(sigma)
            row.addWidget(sigma)
            row.addWidget(QLabel(tr('зеркальных форм')))
            mirror = QSpinBox()
            mirror.setRange(1, 2)
            mirror.setToolTip(tr('2 — форма хиральна и в образце есть оба зеркальных изомера (они одной энергии и '
                                 'считаются одной формой удвоенного веса); 1 — форма не хиральна. Предложено по '
                                 'точечной группе.'))
            mirror.valueChanged.connect(lambda *_: self.compute())
            self.mirrors.append(mirror)
            row.addWidget(mirror)
            form.addRow(tr('Форма') + f' {letter}', row)
        options = QHBoxLayout()
        self.temperature = QDoubleSpinBox()
        self.temperature.setRange(1, 5000)
        self.temperature.setDecimals(2)
        self.temperature.setSuffix(' K')
        self.temperature.setValue(298.15)
        self.temperature.valueChanged.connect(lambda *_: self.compute())
        options.addWidget(self.temperature)
        self.qrrho = QCheckBox(tr('Квази-RRHO для низких частот'))
        self.qrrho.setToolTip(tr('Энтропия мод ниже ~100 см⁻¹ — по Гримме (как в ORCA); без неё мягкие торсионные '
                                 'колебания завышают колебательную сумму'))
        self.qrrho.toggled.connect(lambda *_: self.compute())
        options.addWidget(self.qrrho)
        options.addStretch(1)
        form.addRow(tr('Температура'), options)
        lay.addLayout(form)
        self.table = _table(self.HEADERS)
        lay.addWidget(self.table, 2)
        self.factors = _table(('Множитель в K', 'Значение'))
        lay.addWidget(self.factors, 2)
        self.note = label('', 'subtitle')
        self.note.setWordWrap(True)
        lay.addWidget(self.note)
        bottom = QHBoxLayout()
        self.copy_button = button(tr('Копировать таблицу'), lambda: self.copy())
        bottom.addWidget(self.copy_button)
        bottom.addWidget(button(tr('Сохранить CSV…'), lambda: self.save_csv()))
        bottom.addStretch(1)
        bottom.addWidget(button(tr('Закрыть'), self.accept))
        lay.addLayout(bottom)
        self.resize(760, 640)

    def choose(self, k):
        from modules.spectrum.views.reaction_view import RESULT_FILTER

        path, _ = QFileDialog.getOpenFileName(self, tr('Результат расчёта'), '', tr(RESULT_FILTER))
        if path:
            self.set_form(k, path)
        return path

    def set_form(self, k, path):
        """The result of form k (0 — A, 1 — B): σ and the mirror forms proposed from its geometry."""
        from pathlib import Path

        from modules.spectrum.analysis import equilibrium, reaction

        read = self.read or reaction.read_species
        try:
            species = read(str(path), Path(path).stem)
        except (ValueError, OSError) as exc:
            self.note.setText(str(exc))
            return None
        self.species[k] = species
        self.names[k].setText(species.label + (f' ({species.formula})' if species.formula else ''))
        for box, value in ((self.sigmas[k], species.sigma or 1), (self.mirrors[k], equilibrium.mirror_forms(species.geometry))):
            box.blockSignals(True)
            box.setValue(value)
            box.blockSignals(False)
        self.compute()
        return species

    def compute(self):
        from azimuth import defaults
        from modules.spectrum.analysis import equilibrium

        a, b = self.species
        if a is None or b is None:
            return None
        sigma = (self.sigmas[0].value(), self.sigmas[1].value())
        mirror = (self.mirrors[0].value(), self.mirrors[1].value())
        chosen = round(self.temperature.value(), 2)
        temperatures = sorted(set(equilibrium.TEMPERATURES) | {chosen})
        try:
            self.rows = equilibrium.table(a, b, temperatures, qrrho=self.qrrho.isChecked(), sigma=sigma, mirror=mirror)
        except ValueError as exc:
            self.rows = []
            self.table.setRowCount(0)
            self.factors.setRowCount(0)
            self.note.setText(str(exc))
            return None
        unit, factor = tr(defaults.energy_name()), defaults.energy_factor()
        headers = list(self.HEADERS)
        headers[1] = f'ΔG°, {unit}'
        self.table.setHorizontalHeaderLabels([tr(h) if k != 1 else h for k, h in enumerate(headers)])
        _fill(self.table, [(f'{p.temperature:g}', f'{p.delta_g * factor:.2f}', f'{p.constant:.4g}',
                            f'{100 * p.share_a:.1f}', f'{100 * p.share_b:.1f}') for p in self.rows])
        at = next(p for p in self.rows if p.temperature == chosen)
        _fill(self.factors, [(tr(title), f'{at.factors[key]:.4g}') for key, title in self.FACTOR_NAMES]
              + [(tr('K — произведение множителей') + f' ({chosen:g} K)', f'{at.constant:.4g}')])
        text = tr('ΔE₀ = {:.2f} {} (B − A, с нулевыми колебаниями). Множители — при {} K.').format(
            at.delta_e0 * factor, unit, f'{chosen:g}')
        self.note.setText(text + ''.join(' ⚠ ' + tr(w) for w in equilibrium.warnings(a, b)))
        return self.rows

    def copy(self):
        from PySide6.QtWidgets import QApplication

        from azimuth.ui import copied

        lines = []
        for table in (self.table, self.factors):
            lines.append('\t'.join(table.horizontalHeaderItem(c).text() for c in range(table.columnCount())))
            lines += ['\t'.join(table.item(r, c).text() for c in range(table.columnCount()))
                      for r in range(table.rowCount())]
            lines.append('')
        QApplication.clipboard().setText('\n'.join(lines).rstrip())
        copied(self, tr('таблица равновесия'), self.copy_button)

    def save_csv(self, path=None):
        return _save(self, self.table, path, 'equilibrium.csv')


class HinderedRotorDialog(QDialog):
    """«Заторможенный ротатор…»: a torsion from its relaxed scan (modules/spectrum/analysis/hindered_rotor.py)."""

    HEADERS = ('T, K', 'q гарм.', 'q заторм.', 'q своб.', 'ΔG', 'Множитель к K')
    COVERS = (('full', 'Полный оборот (0–360°)'), ('mirror', 'Половина оборота, вторая — зеркальная (0–180°)'),
              ('period2', 'Потенциал повторяется через 180°'), ('period3', 'Потенциал повторяется через 120°'))

    def __init__(self, owner):
        from PySide6.QtWidgets import QSpinBox

        super().__init__(owner)
        self.setWindowTitle(tr('Заторможенный ротатор'))
        self.points, self.moment, self.potential, self.rows = None, None, None, []
        lay = QVBoxLayout(self)
        hint = label(tr('Торсионное колебание с низким барьером — плохой гармонический осциллятор. Откройте скан '
                        'двугранного угла с релаксацией: по его потенциалу считаются уровни вращения волчка и поправка '
                        'ΔG к свободной энергии, посчитанной с гармонической частотой этой моды.'), 'subtitle')
        hint.setWordWrap(True)
        lay.addWidget(hint)
        form = QFormLayout()
        row = QHBoxLayout()
        row.addWidget(button(tr('Выбрать файл…'), lambda: self.choose()))
        self.name = QLabel('—')
        row.addWidget(self.name, 1)
        form.addRow(tr('Скан'), row)
        self.cover = QComboBox()
        for key, title in self.COVERS:
            self.cover.addItem(tr(title), key)
        self.cover.currentIndexChanged.connect(lambda *_: self.compute())
        form.addRow(tr('Скан покрывает'), self.cover)
        options = QHBoxLayout()
        self.sigma = QSpinBox()
        self.sigma.setRange(1, 6)
        self.sigma.setToolTip(tr('Число симметрии волчка: 3 у метильной группы, 2 у фенила, 1 у волчка без симметрии. '
                                 'Если две ямы — зеркальные формы и они уже учтены числом зеркальных форм в «Равновесии '
                                 'двух форм», поставьте 2, чтобы не посчитать их дважды.'))
        self.sigma.valueChanged.connect(lambda *_: self.compute())
        options.addWidget(QLabel('σ'))
        options.addWidget(self.sigma)
        self.wavenumber = QDoubleSpinBox()
        self.wavenumber.setRange(0.0, 2000.0)
        self.wavenumber.setDecimals(1)
        self.wavenumber.setSuffix(' ' + tr('см⁻¹'))
        self.wavenumber.setSpecialValueText(tr('по кривизне скана'))
        self.wavenumber.setToolTip(tr('Частота торсионной моды из расчёта частот — её вклад заменяется. 0 — взять '
                                      'частоту по кривизне потенциала в минимуме.'))
        self.wavenumber.valueChanged.connect(lambda *_: self.compute())
        options.addWidget(QLabel(tr('Гармоническая частота')))
        options.addWidget(self.wavenumber)
        self.temperature = QDoubleSpinBox()
        self.temperature.setRange(1, 5000)
        self.temperature.setDecimals(2)
        self.temperature.setSuffix(' K')
        self.temperature.setValue(298.15)
        self.temperature.valueChanged.connect(lambda *_: self.compute())
        options.addWidget(self.temperature)
        options.addStretch(1)
        form.addRow(tr('Волчок'), options)
        lay.addLayout(form)
        self.table = _table(self.HEADERS)
        lay.addWidget(self.table, 1)
        self.note = label('', 'subtitle')
        self.note.setWordWrap(True)
        lay.addWidget(self.note)
        bottom = QHBoxLayout()
        self.copy_button = button(tr('Копировать таблицу'), lambda: self.copy())
        bottom.addWidget(self.copy_button)
        bottom.addWidget(button(tr('Сохранить CSV…'), lambda: self.save_csv()))
        bottom.addStretch(1)
        bottom.addWidget(button(tr('Закрыть'), self.accept))
        lay.addLayout(bottom)
        self.resize(780, 560)

    def choose(self):
        from modules.spectrum.views.reaction_view import RESULT_FILTER

        path, _ = QFileDialog.getOpenFileName(self, tr('Скан двугранного угла'), '', tr(RESULT_FILTER))
        if path:
            self.set_scan(path)
        return path

    def set_scan(self, path):
        """The scan of the output: its points, the reduced moment of the two tops at the lowest point."""
        from pathlib import Path

        from modules.spectrum.analysis import hindered_rotor
        from modules.spectrum.readers.outputs import read_any

        self.points, self.moment, self.potential, self.rows = None, None, None, []
        self.table.setRowCount(0)
        try:
            output = read_any(Path(path).read_text(encoding='utf-8', errors='replace'))
            scan = getattr(output, 'scan', None)
            self.points = hindered_rotor.points_of(scan)
            geometry = scan.points[scan.reference].geometry
            if geometry is None:
                raise ValueError(tr('В скане нет геометрий — приведённый момент инерции не посчитать.'))
            atoms = scan.coordinates[0].atoms
            self.moment = hindered_rotor.reduced_moment(geometry, atoms[1], atoms[2])
        except (ValueError, OSError) as exc:
            self.points = None
            self.name.setText('—')
            self.note.setText(str(exc))
            return None
        self.name.setText(Path(path).name + ' · ' + scan.coordinates[0].label)
        cover = hindered_rotor.cover_of(self.points)
        self.cover.blockSignals(True)
        self.cover.setCurrentIndex(max(0, self.cover.findData(cover or 'full')))
        self.cover.blockSignals(False)
        return self.compute()

    def compute(self):
        from azimuth import defaults
        from modules.spectrum.analysis import hindered_rotor, thermo

        if self.points is None:
            return None
        chosen = round(self.temperature.value(), 2)
        temperatures = sorted(set(hindered_rotor.TEMPERATURES) | {chosen})
        try:
            self.potential = hindered_rotor.fit(self.points, self.cover.currentData())
            own = hindered_rotor.harmonic_wavenumber(self.potential, self.moment)
            nu = self.wavenumber.value() or None
            self.rows = hindered_rotor.table(self.potential, self.moment, self.sigma.value(), nu, temperatures)
        except ValueError as exc:
            self.rows = []
            self.table.setRowCount(0)
            self.note.setText(str(exc))
            return None
        unit, factor = tr(defaults.energy_name()), defaults.energy_factor()
        headers = list(self.HEADERS)
        headers[4] = f'ΔG, {unit}'
        self.table.setHorizontalHeaderLabels([tr(h) if k != 4 else h for k, h in enumerate(headers)])
        _fill(self.table, [(f'{r.temperature:g}', f'{r.q_ho:.3f}', f'{r.q_hr:.3f}', f'{r.q_free:.3f}',
                            f'{r.correction * factor:+.3f}', f'{r.factor:.3f}') for r in self.rows])
        p = self.potential
        amu = self.moment / thermo.AMU * 1e20
        constant = hindered_rotor.rotational_constant(self.moment) * thermo.HARTREE / hindered_rotor.CM
        self.note.setText(tr('Барьер {:.2f} {}, минимум при {:.0f}°. Приведённый момент инерции {:.3f} а.е.м.·Å², '
                             'B = {:.2f} см⁻¹. Частота по кривизне скана {:.0f} см⁻¹. ΔG = G(заторм.) − G(гарм.): '
                             'прибавьте её к G; K или k умножается на множитель.').format(
            p.barrier * factor, unit, p.minimum_angle, amu, constant, own))
        return self.rows

    def copy(self):
        from PySide6.QtWidgets import QApplication

        from azimuth.ui import copied

        lines = ['\t'.join(self.table.horizontalHeaderItem(c).text() for c in range(self.table.columnCount()))]
        lines += ['\t'.join(self.table.item(r, c).text() for c in range(self.table.columnCount()))
                  for r in range(self.table.rowCount())]
        QApplication.clipboard().setText('\n'.join(lines))
        copied(self, tr('таблица ротатора'), self.copy_button)

    def save_csv(self, path=None):
        return _save(self, self.table, path, 'hindered_rotor.csv')


class SpectrumToolsTool:
    """Was the mixin SpectrumTools of the window; a part of its own — it reaches the window only through
    the names of PORT (azimuth/window_port.WindowPort)."""

    PORT = (
        'molecule',
        'output',
        'output_path',
        'output_text',
        'crystal_mode_tool',
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

    def equilibrium_dialog(self, paths=None):
        dialog = EquilibriumDialog(self.w.widget)
        self.equilibrium_window = dialog
        dialog.show()
        for k, path in enumerate(paths or ()):
            dialog.set_form(k, path)
        return dialog

    def hindered_rotor_dialog(self, path=None):
        dialog = HinderedRotorDialog(self.w.widget)
        self.hindered_rotor_window = dialog
        dialog.show()
        if path:
            dialog.set_scan(path)
        return dialog

    def methods_dialog(self, folder=None):
        """«Методика расчёта…»: of the folder given, else of the crystal calculation shown in Sextant, else of the
        result open in Spectrum (its own text — a folder may hold several results)."""
        from pathlib import Path

        from modules.spectrum.analysis import methods_text
        from modules.spectrum.views.methods_view import MethodsDialog

        details = None
        if folder is None:
            crystal = getattr(self.w, 'crystal_mode_tool', None) if self.w.has('crystal_mode_tool') else None
            panel = getattr(crystal, 'panel', None) if getattr(crystal, 'active', False) else None
            if panel is not None and getattr(panel, 'folder', None):
                folder = panel.folder
            elif getattr(self.w, 'output_path', None):
                folder = Path(str(self.w.output_path)).parent
                try:
                    details = methods_text.orca(getattr(self.w, 'output_text', '') or '')
                except ValueError:
                    details = None
        dialog = MethodsDialog(self.w.widget, folder, details)
        self.methods_window = dialog
        dialog.show()
        return dialog

    def boltzmann_dialog(self):
        dialog = BoltzmannDialog(self.w.widget)
        self.boltzmann_window = dialog
        dialog.show()
        return dialog
