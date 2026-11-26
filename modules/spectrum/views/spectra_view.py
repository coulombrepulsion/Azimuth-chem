"""Spectrum: the «UV-Vis» and «ЯМР» tabs. The numbers come from orca_spectra.py.

UV-Vis: the excitations of the output (energy, wavelength, oscillator strength, multiplicity) in a table
and a plot of epsilon(lambda) — Gaussian bands of a chosen FWHM in eV — with the excitations as sticks
(height f, right axis). When the output has rotatory strengths, «Вид» switches the plot to the ECD
spectrum delta_epsilon(lambda) — the same band shape, signed, with the rotatory strengths as sticks (R, right
axis), and the table gets a column R; for an achiral molecule (all |R| tiny) the panel says there is no ECD. NMR:
isotropic shieldings; with a reference shielding per element (typed in, or
read from an ORCA output of the reference molecule, TMS, computed at the same level) the chemical shifts
delta = sigma_ref - sigma; equivalent atoms (symmetry, rotating CH3) averaged into one signal; a stick
spectrum of the shifts, high delta on the left as usual. PNG, SVG and CSV export as for IR.
"""

from pathlib import Path

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
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

from modules.spectrum.readers.orca_spectra import equivalent_groups, read_shieldings, shifts
from azimuth.i18n import tr
from modules.spectrum.analysis import nmr_multiplets as nm
from modules.spectrum.views.spectrum_common import show_error, _export_widget


class NMRPlot(QWidget):
    LEFT, RIGHT, TOP, BOTTOM = 20, 20, 24, 34

    def __init__(self):
        super().__init__()
        self.rows = []
        self.lines = {}  # atoms tuple -> [(ppm, share)] of its multiplet (empty: one stick)
        self.setMinimumHeight(150)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), self.palette().base())
        from azimuth.ui import frame_plot  # the border of the plot (light theme)

        frame_plot(p, self)
        p.setPen(self.palette().text().color())
        known = [(atoms, d) for atoms, _, d, _ in self.rows if d is not None]
        if not known:
            p.drawText(
                self.rect(), Qt.AlignmentFlag.AlignCenter, tr('Задайте опорное экранирование, чтобы увидеть сдвиги δ')
            )
            return
        values = [d for _, d in known]
        hi, lo = max(values), min(values)
        pad = max(0.5, (hi - lo) * 0.08)
        hi, lo = hi + pad, lo - pad
        w = max(1, self.width() - self.LEFT - self.RIGHT)
        base = self.height() - self.BOTTOM
        tallest = max(len(a) for a, _ in known)
        p.setPen(QPen(self.palette().mid().color(), 1))
        p.drawLine(self.LEFT, base, self.width() - self.RIGHT, base)
        p.setPen(self.palette().text().color())
        p.drawText(self.LEFT, self.height() - 10, f'{hi:.1f}')
        p.drawText(self.width() - self.RIGHT - 30, self.height() - 10, f'{lo:.1f}')
        p.drawText(self.width() // 2 - 20, self.height() - 10, tr('δ, м.д.'))
        for atoms, d in known:
            height = (base - self.TOP) * len(atoms) / tallest
            sticks = list(self.lines.get(atoms, ())) or [(d, 1.0)]
            tallest_share = max(share for _, share in sticks)
            p.setPen(QPen(QColor('#6ea2f0'), 2 if len(sticks) == 1 else 1))
            for ppm, share in sticks:
                xpos = self.LEFT + (hi - ppm) / (hi - lo) * w  # high delta on the left
                p.drawLine(QPointF(xpos, base), QPointF(xpos, base - height * share / tallest_share))


class MultipletPlot(QWidget):
    """One signal at the scale of hertz — its lines as a Lorentzian curve with the sticks under it, the
    name of the multiplet and its J above."""

    LEFT, RIGHT, TOP, BOTTOM = 20, 20, 26, 30

    def __init__(self):
        super().__init__()
        self.lines = []  # (Hz from the centre, share)
        self.title = ''
        self.setMinimumHeight(130)

    def paintEvent(self, event):
        from azimuth.ui import frame_plot

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), self.palette().base())
        frame_plot(p, self)
        p.setPen(self.palette().text().color())
        if not self.lines:
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, tr('Выберите сигнал в таблице — здесь его мультиплет'))
            return
        span = max(8.0, max(abs(hz) for hz, _ in self.lines) * 1.25 + 3.0)
        w = max(1, self.width() - self.LEFT - self.RIGHT)
        base = self.height() - self.BOTTOM
        top = self.TOP

        def x_of(hz):
            return self.LEFT + (span - hz) / (2 * span) * w  # high frequency on the left, as δ

        gamma = 0.4  # Hz: half the drawn line width
        points = [(-span + 2 * span * k / 400) for k in range(401)]
        values = [sum(share * gamma ** 2 / ((x - hz) ** 2 + gamma ** 2) for hz, share in self.lines) for x in points]
        peak = max(values) or 1.0
        path = QPainterPath()
        for k, (x, v) in enumerate(zip(points, values)):
            point = QPointF(x_of(x), base - (base - top) * v / peak)
            path.moveTo(point) if k == 0 else path.lineTo(point)
        p.setPen(QPen(QColor('#6ea2f0'), 1.5))
        p.drawPath(path)
        p.setPen(QPen(self.palette().mid().color(), 1))
        p.drawLine(self.LEFT, base, self.width() - self.RIGHT, base)
        p.setPen(self.palette().text().color())
        p.drawText(self.LEFT, self.height() - 10, f'{span:+.0f}')
        p.drawText(self.width() - self.RIGHT - 30, self.height() - 10, f'{-span:+.0f}')
        p.drawText(self.width() // 2 - 30, self.height() - 10, tr('Δν, Гц'))
        p.drawText(self.LEFT + 6, top - 8, self.title)


class NMRPanel(QWidget):
    """Shieldings, reference per element, shifts and averaging of equivalent atoms. The reference is kept
    per level of theory (TMS of another method or basis is wrong by ppm); a TMS result opened in Spectrum is
    remembered for its level by itself; «Рассчитать TMS этим уровнем» builds the TMS input from the input of the
    result (modules/spectrum/analysis/nmr_reference) and hands it to Sextant (tmsRequested)."""

    tmsRequested = Signal(str, str, str)  # kind ('orca' | 'gaussian'), input text, level of theory

    def __init__(self, preferences=None):
        super().__init__()
        self.preferences = preferences
        self.shieldings = ()
        self.geometry = None
        self.level = ''
        self.source_text = ''
        self.program = ''
        self._said = ''
        column = QVBoxLayout(self)
        column.setContentsMargins(0, 8, 0, 0)
        controls = QHBoxLayout()
        controls.addWidget(QLabel(tr('Элемент:')))
        self.element = QComboBox()
        self.element.currentIndexChanged.connect(self.element_changed)
        controls.addWidget(self.element)
        controls.addWidget(QLabel(tr('σ опоры, м.д.:')))
        self.reference = QDoubleSpinBox()
        self.reference.setRange(0.0, 5000.0)
        self.reference.setDecimals(3)
        self.reference.setSpecialValueText(tr('не задано'))
        self.reference.valueChanged.connect(self.reference_changed)
        controls.addWidget(self.reference)
        self.tms_button = QPushButton(tr('Рассчитать TMS этим уровнем'))
        self.tms_button.setToolTip(
            tr('Входной файл TMS с методом, базисом и растворителем этого расчёта — в Секстант; '
               'откройте результат TMS в Спектре, и опора запомнится для этого уровня')
        )
        self.tms_button.clicked.connect(self.request_tms)
        self.from_file = QPushButton(tr('Опора из расчёта TMS…'))
        self.from_file.setToolTip(
            tr('Вывод ORCA для эталона (TMS для ¹H и ¹³C) тем же методом и базисом: средние σ по элементам')
        )
        self.from_file.clicked.connect(self.reference_from_file)
        self.average = QCheckBox(tr('Усреднять эквивалентные атомы'))
        self.average.setChecked(True)
        self.average.setToolTip(
            tr('Атомы, связанные симметрией геометрии, и три H вращающейся группы CH₃ дают один сигнал')
        )
        self.average.toggled.connect(self.refresh)
        controls.addWidget(self.average)
        controls.addStretch(1)
        self.export_button = QPushButton(tr('Экспорт…'))
        self.export_button.clicked.connect(self.export)
        controls.addWidget(self.export_button)
        column.addLayout(controls)
        reference_row = QHBoxLayout()  # where the reference comes from, and the two ways to get one
        self.note = QLabel()
        self.note.setWordWrap(True)
        reference_row.addWidget(self.note, 1)
        reference_row.addWidget(self.tms_button)
        reference_row.addWidget(self.from_file)
        column.addLayout(reference_row)
        # the splitting by the computed couplings (nmr_multiplets), first order
        split_row = QHBoxLayout()
        self.split = QCheckBox(tr('Мультиплеты (КССВ)'))
        self.split.setToolTip(tr('Расщепление сигналов по рассчитанным КССВ в первом порядке: n соседних эквивалентных '
                                 'ядер дают n + 1 линию'))
        self.split.setChecked(True)
        self.split.toggled.connect(self.refresh)
        split_row.addWidget(self.split)
        split_row.addWidget(QLabel(tr('Прибор (¹H):')))
        self.mhz = QSpinBox()
        self.mhz.setRange(40, 1200)
        self.mhz.setSingleStep(100)
        self.mhz.setValue(400)
        self.mhz.setSuffix(tr(' МГц'))
        self.mhz.valueChanged.connect(self.refresh)
        split_row.addWidget(self.mhz)
        self.decoupled = QCheckBox(tr('Развязка от ¹H'))
        self.decoupled.setToolTip(tr('Обычный спектр ¹³C{¹H}: водороды не расщепляют сигналы'))
        self.decoupled.setChecked(True)
        self.decoupled.toggled.connect(self.refresh)
        split_row.addWidget(self.decoupled)
        split_row.addStretch(1)
        self.compare_button = QPushButton(tr('Сравнить с экспериментом…'))
        self.compare_button.setToolTip(tr('Расчётные сдвиги этого ядра рядом с экспериментальными: средняя ошибка, '
                                          'наибольшее отклонение, линейная поправка и график'))
        self.compare_button.clicked.connect(lambda: self.compare())
        split_row.addWidget(self.compare_button)
        self.conformers_button = QPushButton(tr('Среднее по конформерам…'))
        self.conformers_button.setToolTip(tr('Экранирования гибкой молекулы, усреднённые по расчётам ЯМР её конформеров '
                                             'с долями по Больцману'))
        self.conformers_button.clicked.connect(lambda: self.open_conformers())
        split_row.addWidget(self.conformers_button)
        column.addLayout(split_row)
        self.plot = NMRPlot()
        column.addWidget(self.plot, 1)
        self.multiplet = MultipletPlot()
        column.addWidget(self.multiplet, 1)
        self.multiplet_note = QLabel()
        self.multiplet_note.setWordWrap(True)
        column.addWidget(self.multiplet_note)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([tr('Атомы'), tr('Элемент'), tr('σ, м.д.'), tr('δ, м.д.'), tr('Мультиплет')])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.itemSelectionChanged.connect(self.show_multiplet)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().hide()
        column.addWidget(self.table, 2)
        self.rows = []
        self.couplings = ()
        self.splittings = {}  # atoms tuple -> [(n, J)]
        self.measured = {}  # element -> the text of the measured shifts typed into «Сравнить с экспериментом…»

    def open_conformers(self, show=True):
        """The window that averages the shieldings over the NMR results of conformers (nmr_conformers_view)."""
        from modules.spectrum.views.nmr_conformers_view import NMRConformersDialog

        dialog = NMRConformersDialog(self)
        dialog.built.connect(self.show_conformers)
        self.conformers_dialog = dialog
        if show:
            dialog.show()
        return dialog

    def show_conformers(self, made):
        """The averaged shieldings in the panel: the geometry, the level and the input of the most populated
        conformer (the reference of the level applies as to any result)."""
        from modules.spectrum.analysis.reaction import level_of_theory

        shieldings, outputs, shares = made
        main = max(range(len(shares)), key=shares.__getitem__)
        dialog = getattr(self, 'conformers_dialog', None)
        text = dialog.texts[main] if dialog is not None and len(dialog.texts) == len(outputs) else ''
        self.load(shieldings, outputs[main].geometry, level_of_theory(text) or self.level, text,
                  getattr(outputs[main], 'program', ''))
        self._said = tr('Среднее по {} конформерам, доли: {}.').format(
            len(shares), ', '.join(f'{100 * p:.0f} %' for p in shares)) + ' ' + tr(
            'Чтобы вернуться к одному расчёту, откройте его снова.')
        self.update_note()
        return shieldings

    def compare(self, show=True):
        """The window of the comparison with the measured shifts for the element shown (nmr_compare_view)."""
        from modules.spectrum.views.nmr_compare_view import NMRCompareDialog

        element = self.element.currentText()
        if not element or not self.rows:
            return None
        dialog = NMRCompareDialog(self, self.rows, element, self.measured.get(element, ''))
        dialog.text.textChanged.connect(lambda: self.measured.__setitem__(element, dialog.text.toPlainText()))
        self.compare_dialog = dialog
        if show:
            dialog.show()
        return dialog

    # -- the stored references: «nmr_reference_C@B3LYP DEF2-SVP» per level, «nmr_reference_C» without one --------
    @staticmethod
    def _name(element, level=''):
        from modules.spectrum.analysis.nmr_reference import key

        return f'nmr_reference_{element}' + (f'@{key(level)}' if level else '')

    def _get(self, name):
        if self.preferences is None:
            return getattr(self, '_references', {}).get(name)
        value = self.preferences.value(name, None)
        return None if value in (None, '') else float(value)

    def _put(self, name, value):
        if self.preferences is None:
            self._references = {**getattr(self, '_references', {}), name: value}
            if value is None:
                self._references.pop(name)
        else:
            self.preferences.setValue(name, '' if value is None else value)

    def sources(self):
        """{element: (sigma_ref, 'level' | 'other')}: the reference of this level, or one stored without a level."""
        found = {}
        for element in {s.element for s in self.shieldings}:
            value = self._get(self._name(element, self.level)) if self.level else None
            if value is not None:
                found[element] = (value, 'level')
                continue
            value = self._get(self._name(element))
            if value is not None:
                found[element] = (value, 'other')
        return found

    def references(self):
        return {element: value for element, (value, _) in self.sources().items()}

    def set_reference(self, element, value, level=None):
        self._put(self._name(element, self.level if level is None else level), value)

    def load(self, shieldings, geometry, level='', text='', program='', couplings=()):
        from modules.spectrum.analysis.nmr_reference import averaged, is_tms

        self.couplings = tuple(couplings)
        self.shieldings = tuple(shieldings)
        self.geometry = geometry
        self.level, self.source_text, self.program = level or '', text or '', program or ''
        self._said = ''
        if self.shieldings and self.level and is_tms(geometry):  # TMS of a level is the reference of it
            for element, value in averaged(self.shieldings).items():
                self.set_reference(element, value)
            self._said = tr(f'Это TMS: опора запомнена для уровня {self.level}. '
                            'Откройте свои результаты этого уровня — сдвиги δ появятся сами.')
        self.tms_button.setEnabled(bool(self.source_text) and not is_tms(geometry))
        self.element.blockSignals(True)
        self.element.clear()
        for element in sorted({s.element for s in self.shieldings}, key=lambda e: (e != 'H', e != 'C', e)):
            self.element.addItem(element)
        self.element.blockSignals(False)
        self.element_changed()

    def element_changed(self, *args):
        element = self.element.currentText()
        self.reference.blockSignals(True)
        self.reference.setValue(self.references().get(element, 0.0))
        self.reference.blockSignals(False)
        self.refresh()

    def reference_changed(self, value):
        element = self.element.currentText()
        if element:
            self.set_reference(element, value if value > 0 else None)
            self._said = ''
        self.refresh()

    def request_tms(self):
        from modules.spectrum.analysis.nmr_reference import tms_input

        try:
            kind, text = tms_input(self.source_text, self.program)
        except ValueError as exc:
            show_error(self, str(exc))
            return
        self.tmsRequested.emit(kind, text, self.level)

    def reference_from_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, tr('Вывод ORCA для опоры (TMS)'), str(Path.home()), tr('ORCA, Gaussian (*.out *.log);;Все файлы (*)')
        )
        if path:
            try:
                self.reference_from_text(Path(path).read_text(encoding='utf-8', errors='replace'))
            except (OSError, ValueError) as exc:
                show_error(self, str(exc))

    def reference_from_text(self, text):
        from modules.spectrum.analysis.nmr_reference import averaged
        from modules.spectrum.analysis.reaction import level_of_theory

        found = read_shieldings(text)
        if not found:
            from modules.spectrum.readers.outputs import read_any

            try:
                found = read_any(text).shieldings
            except ValueError:
                found = ()
        if not found:
            raise ValueError(tr('В файле нет таблицы CHEMICAL SHIELDING SUMMARY.'))
        level = level_of_theory(text) or self.level  # the level of the reference file, if it says one
        for element, value in averaged(found).items():
            self.set_reference(element, value, level)
        self._said = ''
        if self.level and level != self.level:
            self._said = tr(f'Опора посчитана уровнем {level}, а результат — {self.level}: она запомнена для своего '
                            'уровня и к этому результату не применяется.')
        self.element_changed()

    def update_note(self):
        element = self.element.currentText()
        source = self.sources().get(element)
        if self._said:
            text = self._said
        elif not element:
            text = ''
        elif source is None:
            text = (tr(f'Нет опоры для {element} на уровне {self.level}: «Рассчитать TMS этим уровнем» или '
                       '«Опора из расчёта TMS…».') if self.level else
                    tr('Задайте σ опоры или откройте расчёт TMS тем же методом и базисом.'))
        elif source[1] == 'level':
            text = tr(f'Опора — TMS уровня {self.level}.')
        else:
            text = tr('Опора задана без уровня расчёта: проверьте, что TMS считали тем же методом и базисом.')
        self.note.setText(text)

    def refresh(self, *args):
        self.update_note()
        groups = None
        if (
            self.average.isChecked()
            and self.geometry is not None
            and len(self.geometry.atoms) >= max((s.atom + 1 for s in self.shieldings), default=0)
        ):
            groups = equivalent_groups(self.geometry)
        element = self.element.currentText()
        every = shifts(self.shieldings, self.references(), groups)
        rows = [r for r in every if not element or r[1] == element]
        self.rows = rows
        self.update_splittings(every)
        self.table.setRowCount(len(rows))
        for i, (atoms, symbol, delta, sigma) in enumerate(rows):
            values = (
                ', '.join(f'{symbol}{a + 1}' for a in atoms),
                symbol,
                f'{sigma:.3f}',
                '—' if delta is None else f'{delta:.2f}',
                self.multiplet_text(atoms),
            )
            for j, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(i, j, item)
        self.plot.rows = rows
        mhz = self.nucleus_mhz()
        self.plot.lines = {atoms: nm.lines(delta, self.splittings.get(atoms, []), mhz)
                           for atoms, _, delta, _ in rows if delta is not None and self.splittings.get(atoms)}
        self.plot.update()
        self.export_button.setEnabled(bool(rows))
        self.compare_button.setEnabled(bool(rows))
        if rows and not self.table.selectedItems():
            self.table.selectRow(0)
        self.show_multiplet()

    # -- multiplets --------------------------------------------------------------------------------------
    def nucleus_mhz(self):
        return nm.frequency(self.element.currentText() or 'H', self.mhz.value())

    def update_splittings(self, every):
        """[(n, J)] of every signal (its atoms tuple) from the couplings, when «Мультиплеты» is on."""
        self.splittings = {}
        has = bool(self.couplings)
        self.split.setEnabled(has)
        self.mhz.setEnabled(has)
        self.decoupled.setVisible(has and self.element.currentText() not in ('', 'H'))
        self.multiplet.setVisible(has)
        self.multiplet_note.setVisible(has)
        if not has or not self.split.isChecked():
            return
        groups = [atoms for atoms, *_ in every]
        elements = [symbol for _, symbol, *_ in every]
        covered = {a for g in groups for a in g}
        if self.geometry is not None:  # nuclei whose shielding was not computed may still couple (F, P)
            for i, atom in enumerate(self.geometry.atoms):
                if i not in covered:
                    groups.append((i,))
                    elements.append(atom.symbol)
        for k, atoms in enumerate(groups[:len(every)]):
            self.splittings[atoms] = nm.partners(k, groups, elements, self.couplings, self.decoupled.isChecked())

    def multiplet_text(self, atoms):
        if not self.couplings or not self.split.isChecked():
            return ''
        split = self.splittings.get(atoms, [])
        if not split:
            return nm.name(split)
        return nm.name(split) + ', J = ' + ', '.join(f'{abs(j):.1f}' for _, j in split) + ' ' + tr('Гц')

    def show_multiplet(self):
        rows = sorted({i.row() for i in self.table.selectedItems()})
        if not rows or rows[0] >= len(self.rows) or not self.couplings:
            self.multiplet.lines, self.multiplet.title = [], ''
            self.multiplet_note.setText('')
            self.multiplet.update()
            return
        atoms, symbol, delta, _ = self.rows[rows[0]]
        split = self.splittings.get(atoms, []) if self.split.isChecked() else []
        mhz = self.nucleus_mhz()
        self.multiplet.lines = [(ppm * mhz, share) for ppm, share in nm.lines(0.0, split, mhz)]
        label = ', '.join(f'{symbol}{a + 1}' for a in atoms)
        self.multiplet.title = f'{label}: {self.multiplet_text(atoms) or nm.name(split)}'
        note = tr('Первый порядок: линии на расстоянии J, интенсивности — по треугольнику Паскаля.')
        strong = self.strongly_coupled(atoms, delta, mhz)
        if strong:
            note += ' ' + tr('Сильная связь с {} (Δν/J = {:.1f}): настоящий мультиплет кособокий («крыша»), '
                             'с лишними линиями.').format(strong[0], strong[1])
        self.multiplet_note.setText(note)
        self.multiplet.update()

    def strongly_coupled(self, atoms, delta, mhz):
        """(label, Δν/J) of the partner with the smallest ratio below 5, or None (first order needs Δν ≫ J)."""
        if delta is None:
            return None
        rows = [r for r in self.rows if r[0] != atoms and r[2] is not None]
        found = None
        for other, symbol, d, _ in rows:
            couples = [v for i, j, v in self.couplings if (i in atoms and j in other) or (j in atoms and i in other)]
            if not couples:
                continue
            j = abs(sum(couples) / len(couples))
            if j < nm.MIN_J:
                continue
            ratio = abs(delta - d) * mhz / j
            if ratio < 5 and (found is None or ratio < found[1]):
                found = (', '.join(f'{symbol}{a + 1}' for a in other), ratio)
        return found

    def export(self):
        path, _ = QFileDialog.getSaveFileName(
            self, tr('Экспорт ЯМР'), str(Path.home() / 'nmr.csv'), tr('CSV (*.csv);;PNG (*.png);;SVG (*.svg)')
        )
        if not path:
            return
        rows = [
            (' '.join(str(a + 1) for a in atoms), symbol, sigma, '' if delta is None else delta,
             self.multiplet_text(atoms))
            for atoms, symbol, delta, sigma in self.rows
        ]
        _export_widget(self.plot, Path(path), 'Azimuth · NMR', rows,
                       ['atoms', 'element', 'sigma_ppm', 'delta_ppm', 'multiplet'])
