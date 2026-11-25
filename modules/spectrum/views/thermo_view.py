"""Spectrum: the «Термохимия» tab. Numbers: modules/spectrum/analysis/thermo.py.

The frequencies and the geometry of the result, the temperature, the pressure, the rotational symmetry number
(from the point group found by Compass, editable) and the multiplicity (printed by the program, editable);
Grimme's quasi-RRHO for the entropy of low modes on request. A table: ZPE, E, H, T·S, G as corrections to the
electronic energy and as totals, in hartree, kcal/mol and kJ/mol; the entropy by parts in cal/(mol·K) and
J/(mol·K); notes (imaginary frequencies left out, an unexpected number of modes, average masses). «Копировать»
puts the table as tab-separated text on the clipboard.
0.91.6, MOPAC: no total energy — the row ΔHf(T) = ΔHf(298 K) + H(T) − H(298 K) instead (MOPAC's own formula: its
heat of formation is for 298 K; H without ZPE cancels it in the difference), and the THERMO table of MOPAC at the
chosen temperature, when it has one, as a check (ΔHf, S printed by MOPAC next to ours).
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from modules.spectrum.analysis import thermo
from azimuth.i18n import tr
from azimuth.ui import card

ATM = 101325.0
CAL = 4.184
MOPAC_REFERENCE = 298.0  # K: the temperature of the MOPAC heat of formation (its THERMO starts there)


class ThermoPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.geometry = None
        self.frequencies = ()
        self.energy = None
        self.heat_of_formation = None
        self.mopac_thermo = ()
        self.result = None
        column = QVBoxLayout(self)
        column.setContentsMargins(0, 8, 0, 0)
        controls = QHBoxLayout()
        self.temperature = QDoubleSpinBox()
        self.temperature.setRange(1.0, 5000.0)
        self.temperature.setDecimals(2)
        self.temperature.setValue(298.15)
        self.temperature.setSuffix(' K')
        self.pressure = QDoubleSpinBox()
        self.pressure.setRange(0.001, 1000.0)
        self.pressure.setDecimals(3)
        self.pressure.setValue(1.0)
        self.pressure.setSuffix(tr(' атм'))
        self.sigma = QSpinBox()
        self.sigma.setRange(1, 60)
        self.sigma.setToolTip(tr('Число симметрии вращения: сколько поворотов группы переводят молекулу в себя'))
        self.multiplicity = QSpinBox()
        self.multiplicity.setRange(1, 30)
        self.qrrho = QCheckBox(tr('Квази-RRHO (Гримме) для мод ниже 100 см⁻¹'))
        self.qrrho.setToolTip(
            tr('Энтропия низких мод смешивается с энтропией свободного ротатора (как в ORCA); энергия остаётся гармонической')
        )
        for title, widget in (
            (tr('T:'), self.temperature),
            (tr('P:'), self.pressure),
            (tr('σ:'), self.sigma),
            (tr('2S + 1:'), self.multiplicity),
        ):
            controls.addWidget(QLabel(title))
            controls.addWidget(widget)
            signal = widget.valueChanged
            signal.connect(self.refresh)
        controls.addWidget(self.qrrho)
        self.qrrho.toggled.connect(self.refresh)
        controls.addStretch()
        self.copy_button = QPushButton(tr('Копировать'))
        self.copy_button.clicked.connect(self.copy)
        controls.addWidget(self.copy_button)
        column.addLayout(controls)
        self.group = QLabel()
        self.group.setObjectName('subtitle')
        self.group.setWordWrap(True)
        column.addWidget(self.group)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels([tr('Величина'), tr('хартри'), tr('ккал/моль'), tr('кДж/моль')])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # the names
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().hide()
        tables = QHBoxLayout()  # side by side — both short, neither scrolls (one under the other they did)
        tables.setSpacing(12)
        # the two tables in cards with their titles, as «Энергии и частоты»
        energy_card, energy_box = card(tr('Энергии и поправки'))
        energy_box.setContentsMargins(14, 12, 14, 14)
        energy_box.addWidget(self.table)
        energy_box.addStretch(1)
        tables.addWidget(energy_card, 3, Qt.AlignmentFlag.AlignTop)
        self.entropy = QTableWidget(0, 3)
        self.entropy.setHorizontalHeaderLabels([tr('Энтропия'), tr('кал/(моль·К)'), tr('Дж/(моль·К)')])
        self.entropy.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.entropy.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # the names
        self.entropy.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.entropy.verticalHeader().hide()
        entropy_card, entropy_box = card(tr('Энтропия'))
        entropy_box.setContentsMargins(14, 12, 14, 14)
        entropy_box.addWidget(self.entropy)
        entropy_box.addStretch(1)
        tables.addWidget(entropy_card, 2, Qt.AlignmentFlag.AlignTop)
        column.addLayout(tables, 1)
        self.notes = QLabel()
        self.notes.setObjectName('notice')
        self.notes.setWordWrap(True)
        column.addWidget(self.notes)

    def load(self, output, text=''):
        """Take the result; returns True when there are frequencies to work with."""
        geometry = getattr(output, 'vibration_geometry', None) or getattr(output, 'geometry', None)
        frequencies = tuple(getattr(output, 'frequencies', ()) or ())
        self.geometry, self.frequencies = geometry, frequencies
        self.energy = output.energies[-1] if getattr(output, 'energies', None) else None
        self.heat_of_formation = getattr(output, 'heat_of_formation', None)  # MOPAC, kcal/mol
        self.mopac_thermo = tuple(getattr(output, 'mopac_thermo', ()) or ())
        if not frequencies or geometry is None:
            self.result = None
            return False
        name = ''
        try:
            from modules.compass.chemistry.symmetry import analyze

            found = analyze(geometry)
            name = found.get('name', '') if 'err' not in found else ''
        except Exception:  # the point group only proposes σ; the user can set it
            name = ''
        found = thermo.find_multiplicity(text)  # not printed — 1, and said so
        self.multiplicity_missing = found is None
        for widget, value in ((self.sigma, thermo.symmetry_number(name)), (self.multiplicity, found or 1)):
            widget.blockSignals(True)
            widget.setValue(value)
            widget.blockSignals(False)
        self.group.setText(
            (tr(f'Точечная группа {name}: σ = {thermo.symmetry_number(name)}. ') if name else '')
            + tr('Идеальный газ, жёсткий ротатор и гармонический осциллятор (RRHO).')
            + (tr(' Мультиплетность в выводе не найдена — взята 1; проверьте поле 2S + 1.') if self.multiplicity_missing else '')
        )
        self.refresh()
        return True

    def refresh(self, *args):
        if self.geometry is None or not self.frequencies:
            return None
        try:
            self.result = thermo.thermochemistry(
                self.geometry,
                self.frequencies,
                self.energy,
                self.temperature.value(),
                self.pressure.value() * ATM,
                self.multiplicity.value(),
                self.sigma.value(),
                self.qrrho.isChecked(),
            )
        except ValueError as exc:
            self.result = None
            self.notes.setText(str(exc))
            return None
        r = self.result
        T = r.temperature
        rows = [
            (tr('Нулевые колебания (ZPE)'), r.zpe),
            (tr('Поправка к энергии E (с ZPE)'), r.thermal_energy),
            (tr('Поправка к энтальпии H'), r.enthalpy),
            (tr('T·S'), T * r.entropy),
            (tr('Поправка к энергии Гиббса G'), r.gibbs),
        ]
        if r.energy is not None:
            rows += [
                (tr('Электронная энергия E₀'), r.energy),
                (tr('E₀ + ZPE'), r.energy + r.zpe),
                (tr('H = E₀ + поправка'), r.energy + r.enthalpy),
                (tr('G = E₀ + поправка'), r.energy + r.gibbs),
            ]
        mopac = self.mopac_rows(r)
        rows += mopac[0]
        self._fill(self.table, [(n, f'{v:.8f}', f'{v * thermo.KCAL:.3f}', f'{v * thermo.KJ:.3f}') for n, v in rows])
        per = thermo.HARTREE * thermo.NA  # J/mol per hartree
        names = {
            'translational': tr('Поступательная'),
            'rotational': tr('Вращательная'),
            'vibrational': tr('Колебательная'),
            'electronic': tr('Электронная'),
        }
        parts = [(names[k], v[1] * per) for k, v in r.parts.items()] + [(tr('Всего'), r.entropy * per)]
        self._fill(self.entropy, [(n, f'{s / CAL:.3f}', f'{s:.3f}') for n, s in parts])
        notes = list(r.notes) + mopac[1]
        notes.append(
            tr(f'Мод учтено: {r.modes}') + (tr(' · молекула линейная') if r.linear else '') + f' · P = {r.pressure:.0f} ' + tr('Па')
        )
        self.notes.setText('\n'.join(notes))
        return r

    def mopac_rows(self, r):
        """([(name, hartree)], [notes]) for a MOPAC result: ΔHf(T) and the check against its THERMO table."""
        if self.heat_of_formation is None:
            return [], []
        reference = thermo.thermochemistry(self.geometry, self.frequencies, None, MOPAC_REFERENCE,
                                           self.pressure.value() * ATM, self.multiplicity.value(), self.sigma.value(),
                                           self.qrrho.isChecked())
        hof = self.heat_of_formation / thermo.KCAL + (r.enthalpy - reference.enthalpy)
        rows = [(tr('ΔHf(T) = ΔHf(298 К) + H(T) − H(298 К) (MOPAC)'), hof)]
        notes = []
        printed = [row for row in self.mopac_thermo if abs(row[0] - r.temperature) < 0.01]
        per = thermo.HARTREE * thermo.NA / CAL  # cal/mol per hartree
        if printed:
            t, h, _, _, s = printed[0]
            notes.append(tr(f'MOPAC при {t:.2f} К: ΔHf = {h:.3f} ккал/моль, S = {s:.3f} кал/(моль·К); '
                            f'здесь: {hof * thermo.KCAL:.3f} и {r.entropy * per:.3f}.'))
        elif self.mopac_thermo:
            temperatures = ', '.join(f'{row[0]:g}' for row in self.mopac_thermo[:6])
            notes.append(tr(f'Таблица THERMO MOPAC посчитана при {temperatures} К — поставьте одну из этих T для сверки.'))
        return rows, notes

    @staticmethod
    def _fill(table, rows):
        table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, value in enumerate(row):
                item = QTableWidgetItem(value)
                if j:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                table.setItem(i, j, item)
        # the card as tall as its rows (they were cards with an empty half under a short table)
        from PySide6.QtWidgets import QAbstractScrollArea

        table.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        table.updateGeometry()

    def text(self):
        lines = []
        for table in (self.table, self.entropy):
            lines.append('\t'.join(table.horizontalHeaderItem(j).text() for j in range(table.columnCount())))
            for i in range(table.rowCount()):
                lines.append('\t'.join(table.item(i, j).text() for j in range(table.columnCount())))
            lines.append('')
        return '\n'.join(lines + [self.notes.text()])

    def copy(self):
        from azimuth.ui import copied

        QApplication.clipboard().setText(self.text())
        copied(self, tr('таблица термохимии'), self.copy_button)
