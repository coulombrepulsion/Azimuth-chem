"""The UV-Vis, ECD and emission of a result in Spectrum: the plots (UVPlot, EmissionPlot) and the panel UVVisPanel —
the states, their NTO on the model, the analyses of Multiwfn (D, Sr, H, t, HDI, EDI), the charge transfer, the fit,
the reference result.

Split off modules/spectrum/views/spectra_view.py (0.222.30); the NMR stays there.
"""

from azimuth.ui import rounded
from pathlib import Path
from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from modules.spectrum.readers.orca_spectra import DEFAULT_FWHM, cd_curve, rotatory_is_zero, uv_curve
from azimuth.i18n import tr
from modules.spectrum.views.spectrum_extras import ExtrasMixin, num
from modules.spectrum.views.spectrum_common import _export_widget, read_reference, reference_path, show_error


ENSEMBLE_INK, EXPERIMENT_INK = '#9b6fd6', '#2f9e66'  # as on the plot of IR (ir_plot.IRSpectrum)


class UVPlot(QWidget):
    selected = Signal(int)
    LEFT, RIGHT, TOP, BOTTOM = 64, 54, 28, 34

    def __init__(self):
        super().__init__()
        self.excitations = ()
        self.reference = None  # (excitations, name) of a second result drawn for comparison
        self.fwhm = DEFAULT_FWHM
        self.current = -1
        self.mode = 'uv'  # 'uv' — absorption, 'cd' — electronic circular dichroism
        # a measured spectrum (x nm, y with max |y| 1, name), the average of
        # conformers (excitations, name) and the shift of the computed energies, eV (this result and the average)
        self.experiment = None
        self.ensemble = None
        self.shift_ev = 0.0
        self.setMinimumHeight(220)
        self.set_mode('uv')

    def set_mode(self, mode):
        self.mode = mode
        self.setToolTip(
            tr('Гауссовы полосы заданной ширины — модель; палочки — вращательные силы R со знаком. Щелчок выбирает переход.')
            if mode == 'cd' else
            tr('Гауссовы полосы заданной ширины — модель; палочки — силы осцилляторов. Щелчок выбирает переход.')
        )
        self.update()

    def curve(self, excitations):
        return cd_curve(excitations, self.fwhm) if self.mode == 'cd' else uv_curve(excitations, self.fwhm)

    def shown(self, excitations):
        """The excitations as drawn — moved by the shift of the energies."""
        from modules.spectrum.analysis.experiment import shifted_excitations

        return shifted_excitations(excitations, self.shift_ev)

    def ensemble_curve(self):
        if not self.ensemble:
            return None
        try:
            return self.curve(self.shown(self.ensemble[0]))
        except ValueError:
            return None

    def score(self):
        """How alike the computed spectrum (the average of conformers when there is one) and the measured one are."""
        if not self.experiment:
            return None
        from modules.spectrum.analysis.experiment import similarity

        try:
            curve = self.ensemble_curve() if self.ensemble else self.curve(self.shown(self.excitations))
            return None if curve is None else similarity(curve, self.experiment[:2], signed=self.mode == 'cd')
        except ValueError:
            return None

    def stick(self, e):
        """The height of the stick of an excitation: f, or R (10^-40 cgs) for ECD; None — no stick."""
        if self.mode == 'cd':
            return e.rotatory if e.rotatory else None
        return e.fosc if e.fosc > 0 else None

    def data(self):
        moved = self.shown(self.excitations)
        x, y = self.curve(moved)
        # the index k is that of the table (the excitations as read); a band shifted below zero is not drawn
        pairs = [(k, m[0]) for k, e in enumerate(self.excitations) if (m := self.shown((e,)))]
        shown = [(k, e) for k, e in pairs if self.stick(e) is not None and x[0] <= e.wavelength <= x[-1]]
        return x, y, shown

    def frame(self, x):
        lo, hi = float(x[0]), float(x[-1])
        for other in (self.reference_curve(), self.ensemble_curve()):
            if other is not None:
                lo, hi = min(lo, float(other[0][0])), max(hi, float(other[0][-1]))
        return lo, hi

    def reference_curve(self):
        if not self.reference:
            return None
        try:
            return self.curve(self.reference[0])
        except ValueError:
            return None

    def point(self, lam, value, lo, hi, top):
        """top > 0: value 0..top; for ECD the axis is symmetric, -top..top."""
        w = max(1, self.width() - self.LEFT - self.RIGHT)
        h = max(1, self.height() - self.TOP - self.BOTTOM)
        bottom = -top if self.mode == 'cd' else 0.0
        return QPointF(self.LEFT + (lam - lo) / (hi - lo) * w, self.TOP + h - (value - bottom) / (top - bottom) * h)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), self.palette().base())
        from azimuth.ui import frame_plot  # the border of the plot (light theme)

        frame_plot(p, self)
        text = self.palette().text().color()
        p.setPen(text)
        cd = self.mode == 'cd'
        try:
            x, y, shown = self.data()
        except ValueError:
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                       tr('Нет вращательных сил') if cd else tr('Нет разрешённых переходов'))
            return
        lo, hi = self.frame(x)
        other = self.reference_curve()
        average = self.ensemble_curve()
        size = (lambda v: float(abs(v).max())) if cd else (lambda v: float(v.max()))
        top = max(1e-9, max(size(y), size(other[1]) if other is not None else 0.0,
                            size(average[1]) if average is not None else 0.0) * 1.08)
        ftop = max(1e-9, max(abs(self.stick(e)) for _, e in shown) * 1.08) if shown else 1.0
        p.drawText(6, 18, tr('Δε, л·моль⁻¹·см⁻¹') if cd else tr('ε, л·моль⁻¹·см⁻¹'))
        p.drawText(self.width() - self.RIGHT - (60 if cd else 2), 18, tr('R, 10⁻⁴⁰ СГС') if cd else 'f')
        p.drawText(6, self.TOP + 12, f'{top:.3g}')
        p.drawText(self.width() - self.RIGHT + 6, self.TOP + 12, f'{ftop:.2g}')
        if cd:
            p.drawText(6, self.height() - self.BOTTOM - 2, f'{-top:.3g}')
        p.drawText(self.LEFT, self.height() - 10, f'{lo:.0f}')
        p.drawText(self.width() - self.RIGHT - 30, self.height() - 10, f'{hi:.0f}')
        p.drawText(self.width() // 2 - 40, self.height() - 10, tr(f'λ, нм · FWHM {self.fwhm:g} эВ'))
        if self.shift_ev:  # the spectrum is not the one of the output — said on it
            p.drawText(self.LEFT + 60, self.height() - 10,
                       tr('сдвиг {} эВ').format(num(self.shift_ev, '+.2f')))
        p.setPen(QPen(self.palette().mid().color(), 1))
        base = self.height() - self.BOTTOM
        p.drawLine(self.LEFT, self.TOP, self.LEFT, base)
        p.drawLine(self.LEFT, base, self.width() - self.RIGHT, base)
        p.drawLine(self.width() - self.RIGHT, self.TOP, self.width() - self.RIGHT, base)
        if cd:  # the zero line of the signed spectrum
            p.drawLine(self.point(lo, 0, lo, hi, 1), self.point(hi, 0, lo, hi, 1))
        for k, e in shown:
            ink = QColor('#ffb454' if k == self.current else '#9aa8b8')
            p.setPen(QPen(ink, 3 if k == self.current else 1.5))
            p.drawLine(self.point(e.wavelength, 0, lo, hi, 1), self.point(e.wavelength, self.stick(e), lo, hi, ftop))
        if other is not None:  # the second result, dashed, with a legend
            ox, oy = other
            path = QPainterPath()
            path.moveTo(self.point(ox[0], oy[0], lo, hi, top))
            for a, b in zip(ox[1:], oy[1:]):
                path.lineTo(self.point(a, b, lo, hi, top))
            p.setPen(QPen(QColor('#e0709a'), 1.6, Qt.PenStyle.DashLine))
            p.drawPath(path)
        if self.experiment:  # the measured spectrum, green, its largest |band| at the top
            ex, ey = self.experiment[0], self.experiment[1]
            keep = [(a, b) for a, b in zip(ex, ey) if lo <= a <= hi]
            if len(keep) > 1:
                path = QPainterPath()
                path.moveTo(self.point(keep[0][0], keep[0][1] * top * 0.92, lo, hi, top))
                for a, b in keep[1:]:
                    path.lineTo(self.point(a, b * top * 0.92, lo, hi, top))
                p.setPen(QPen(QColor(EXPERIMENT_INK), 1.5))
                p.drawPath(path)
        if average is not None:  # the average of conformers, violet
            path = QPainterPath()
            path.moveTo(self.point(average[0][0], average[1][0], lo, hi, top))
            for a, b in zip(average[0][1:], average[1][1:]):
                path.lineTo(self.point(a, b, lo, hi, top))
            p.setPen(QPen(QColor(ENSEMBLE_INK), 1.8))
            p.drawPath(path)
        entries = []
        if other is not None:
            entries.append(('#e0709a', '- - ' + self.reference[1][:34]))
        if average is not None:
            entries.append((ENSEMBLE_INK, '— ' + self.ensemble[1][:40]))
        if self.experiment:
            score = self.score()
            alike = '' if score is None else ' · ' + tr('сходство {}').format(num(score, '.2f'))
            entries.append((EXPERIMENT_INK, '— ' + tr('эксперимент: ') + self.experiment[2][:28] + alike))
        if entries:
            entries.insert(0, ('#6ea2f0', '— ' + tr('этот результат')))
            widest = max(p.fontMetrics().horizontalAdvance(t) for _, t in entries)
            left = max(self.LEFT + 4, self.width() - self.RIGHT - widest - 8)
            for k, (ink, text) in enumerate(entries):
                p.setPen(QColor(ink))
                p.drawText(left, self.TOP + 14 + 16 * k, text)
        path = QPainterPath()
        path.moveTo(self.point(x[0], y[0], lo, hi, top))
        for a, b in zip(x[1:], y[1:]):
            path.lineTo(self.point(a, b, lo, hi, top))
        p.setPen(QPen(QColor('#6ea2f0'), 2))
        p.drawPath(path)

    def mousePressEvent(self, event):
        try:
            x, _, shown = self.data()
        except ValueError:
            return
        if not shown:
            return
        lo, hi = self.frame(x)
        k, _ = min(shown, key=lambda v: abs(self.point(v[1].wavelength, 0, lo, hi, 1).x() - event.position().x()))
        self.selected.emit(k)


class EmissionPlot(QWidget):
    """The emission of an optimization of an excited state — the absorption at the first geometry (dashed,
    as the spectrum UV-Vis: Gaussian bands of the FWHM in eV) and the band of the light given at the relaxed geometry
    (orange), each scaled to its own top; the two vertical energies of the root followed and the Stokes shift between
    them. emission — emission.Emission or None; curves() -> (λ, absorption, emission) on one grid."""

    LEFT, RIGHT, TOP, BOTTOM = 24, 24, 34, 34
    EMISSION_INK = '#e8913a'

    def __init__(self):
        super().__init__()
        self.emission = None
        self.fwhm = DEFAULT_FWHM
        self.setMinimumHeight(220)
        self.setToolTip(tr('Пунктир — поглощение в начальной геометрии; оранжевая полоса — излучение из '
                           'релаксированной геометрии возбуждённого состояния; обе по своей высоте. Без колебательной '
                           'структуры полос.'))

    def _band(self, energy, grid):
        from math import log, sqrt

        import numpy as np

        sigma = self.fwhm * EV_CM_PLOT / (2 * sqrt(log(2)))
        nu = 1e7 / grid
        return np.exp(-(((nu - energy * EV_CM_PLOT) / sigma) ** 2))

    def curves(self):
        import numpy as np

        found = self.emission
        if found is None:
            return (), (), ()
        lows = [found.end.wavelength, found.start.wavelength]
        highs = list(lows)
        allowed = [e for e in found.absorption if e.fosc > 0]
        if allowed:
            lows += [min(e.wavelength for e in allowed)]
        span = max(highs) - min(lows)
        lo = max(80.0, min(lows) - 0.25 * span - 40)
        hi = max(highs) + 0.35 * span + 60
        grid = np.linspace(lo, hi, 900)
        absorbed = np.zeros_like(grid)
        for e in allowed:
            absorbed += e.fosc * self._band(e.energy_ev, grid)
        if not allowed or absorbed.max() <= 0:  # a dark root alone: its position, as a band of height 1
            absorbed = self._band(found.start.energy_ev, grid)
        emitted = self._band(found.end.energy_ev, grid)
        return grid, absorbed / absorbed.max(), emitted / max(emitted.max(), 1e-12)

    def x_of(self, lam, lo, hi):
        return self.LEFT + (lam - lo) / (hi - lo) * max(1, self.width() - self.LEFT - self.RIGHT)

    def y_of(self, value):
        h = max(1, self.height() - self.TOP - self.BOTTOM)
        return self.TOP + h - value * h * 0.92

    def paintEvent(self, event):
        from azimuth.ui import frame_plot
        from modules.spectrum.views.spectrum_extras import num

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), self.palette().base())
        frame_plot(p, self)
        text = self.palette().text().color()
        found = self.emission
        if found is None:
            p.setPen(text)
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, tr('Нет оптимизации возбуждённого состояния'))
            return
        x, absorbed, emitted = self.curves()
        lo, hi = float(x[0]), float(x[-1])
        base = self.height() - self.BOTTOM
        p.setPen(QPen(self.palette().mid().color(), 1))
        p.drawLine(self.LEFT, base, self.width() - self.RIGHT, base)
        for values, pen in ((absorbed, QPen(QColor('#6ea2f0'), 1.6, Qt.PenStyle.DashLine)),
                            (emitted, QPen(QColor(self.EMISSION_INK), 2.2))):
            path = QPainterPath()
            path.moveTo(self.x_of(x[0], lo, hi), self.y_of(values[0]))
            for a, b in zip(x[1:], values[1:]):
                path.lineTo(self.x_of(a, lo, hi), self.y_of(b))
            p.setPen(pen)
            p.drawPath(path)
        start, end = found.start, found.end
        for point, ink in ((start, '#6ea2f0'), (end, self.EMISSION_INK)):
            px = self.x_of(point.wavelength, lo, hi)
            p.setPen(QPen(QColor(ink), 1, Qt.PenStyle.DotLine))
            p.drawLine(QPointF(px, self.TOP), QPointF(px, base))
            p.setPen(QColor(ink))
            p.drawText(QPointF(px + 4, self.TOP + 12), f'{num(point.wavelength, ".0f")} нм')
        a, b = self.x_of(start.wavelength, lo, hi), self.x_of(end.wavelength, lo, hi)
        middle = self.TOP + 30
        p.setPen(QPen(text, 1))
        p.drawLine(QPointF(a, middle), QPointF(b, middle))
        p.drawLine(QPointF(b, middle), QPointF(b - 6 if b > a else b + 6, middle - 4))
        p.drawLine(QPointF(b, middle), QPointF(b - 6 if b > a else b + 6, middle + 4))
        said = tr('стоксов сдвиг {} см⁻¹').format(num(found.stokes_cm, '.0f'))
        width = p.fontMetrics().horizontalAdvance(said)
        p.drawText(QPointF(max(self.LEFT, min((a + b) / 2 - width / 2, self.width() - self.RIGHT - width)),
                           middle - 6), said)
        p.drawText(self.LEFT, self.height() - 10, f'{lo:.0f}')
        p.drawText(self.width() - self.RIGHT - 30, self.height() - 10, f'{hi:.0f}')
        p.drawText(self.width() // 2 - 60, self.height() - 10, tr('λ, нм · FWHM {} эВ').format(num(self.fwhm, 'g')))
        letter = 'T' if found.multiplicity == 3 else 'S'
        legend = [('#6ea2f0', '- - ' + tr('поглощение (начальная геометрия)')),
                  (self.EMISSION_INK, '— ' + (tr('фосфоресценция') if found.kind == 'phosphorescence'
                                              else tr('флуоресценция')) + f' {letter}{end.root}')]
        widest = max(p.fontMetrics().horizontalAdvance(t) for _, t in legend)
        for k, (ink, line) in enumerate(legend):
            p.setPen(QColor(ink))
            p.drawText(self.width() - self.RIGHT - widest, self.TOP + 50 + 16 * k, line)


EV_CM_PLOT = 8065.543937


ANALYSIS_SCOPES = (('all', 'Все состояния'), ('chosen', 'Выбранные в таблице'), ('bright', 'Яркие: f ≥ 0,01'))


BRIGHT = 0.01


INDEX_COLUMNS = (  # the indices of the hole and the electron (Multiwfn, Lu et al., Carbon 165, 461 (2020))
    ('d', 'D, Å'), ('sr', 'Sr'), ('h', 'H, Å'), ('t', 't, Å'), ('delta_r', 'Δr, Å'), ('hdi', 'HDI'), ('edi', 'EDI'),
    ('character', 'Характер'),
)


def character(values):
    """«перенос заряда» when the hole and the electron are apart (t > 0 or Δr > 2 Å), else «локальное»."""
    if 't' not in values and 'delta_r' not in values:
        return ''
    if values.get('t', -1.0) > 0 or values.get('delta_r', 0.0) > 2.0:
        return tr('перенос заряда')
    return tr('локальное')


class UVVisPanel(ExtrasMixin, QWidget):
    def __init__(self):
        super().__init__()
        self.excitations = ()
        self.has_rotatory = False
        column = QVBoxLayout(self)
        column.setContentsMargins(0, 8, 0, 0)
        controls = QHBoxLayout()
        self.summary = QLabel()
        self.summary.setObjectName('subtitle')
        self.summary.setWordWrap(True)
        controls.addWidget(self.summary, 1)
        self.kind = QComboBox()  # absorption or ECD (shown when the output has rotatory strengths)
        self.kind.addItem(tr('Поглощение (UV-Vis)'), 'uv')
        self.kind.addItem(tr('Круговой дихроизм (ЭКД)'), 'cd')
        self.kind.addItem(tr('Излучение'), 'em')  # fluorescence / phosphorescence of an excited-state opt
        self.emission = None
        self.kind.setToolTip(tr('ЭКД — разность поглощения света, поляризованного по кругу влево и вправо; '
                                'есть только у хиральных молекул, у зеркального изомера — с обратным знаком'))
        self.kind.currentIndexChanged.connect(lambda *_: self.set_kind(self.kind.currentData()))
        self.kind.hide()
        controls.addWidget(self.kind)
        controls.addWidget(QLabel(tr('FWHM, эВ:')))
        self.fwhm = QDoubleSpinBox()
        self.fwhm.setRange(0.05, 2.0)
        self.fwhm.setSingleStep(0.05)
        self.fwhm.setDecimals(2)
        from azimuth import defaults

        self.fwhm.setValue(defaults.get('uv_fwhm'))  # «Настройки → Спектры» (DEFAULT_FWHM is its default)
        self.fwhm.valueChanged.connect(self.set_width)
        controls.addWidget(self.fwhm)
        self.compare_button = QPushButton(tr('Сравнить с…'))
        self.compare_button.setToolTip(tr('Наложить спектр UV-Vis другого результата (ORCA, Gaussian, Psi4)'))
        self.compare_button.clicked.connect(self.choose_reference)
        controls.addWidget(self.compare_button)
        self.clear_button = QPushButton(tr('Убрать сравнение'))
        self.clear_button.clicked.connect(lambda: self.set_reference(None))
        self.clear_button.hide()
        controls.addWidget(self.clear_button)
        controls.addWidget(self.make_extras_button(controls))  # the experiment and the conformers
        self.export_button = QPushButton(tr('Экспорт…'))
        self.export_button.clicked.connect(self.export)
        controls.addWidget(self.export_button)
        column.addLayout(controls)
        # the analysis of the excited states — the hole and the electron, Δr (set_analysis gives the source)
        analysis = QHBoxLayout()
        self.analysis_button = QPushButton(tr('Анализ возбуждений'))
        self.analysis_button.setToolTip(tr('Дырка и электрон каждого состояния: D, Sr, H, t, Δr, HDI, EDI — '
                                           'локальное возбуждение или перенос заряда'))
        self.analysis_button.clicked.connect(self.analyse)
        # an icon — the way to Compass
        from azimuth.icons import iconify

        self.hole_button = iconify(QPushButton(), 'compass', tr('Перейти в Компас · дырка (синее) и электрон (зелёное) '
                                                               'выбранного состояния на модели'))
        self.hole_button.clicked.connect(self.hole_on_model)
        # which states — one run of Multiwfn each (runs made once are taken from its cache)
        self.analysis_scope = QComboBox()
        for key, title in ANALYSIS_SCOPES:
            self.analysis_scope.addItem(tr(title), key)
        self.analysis_scope.setToolTip(tr('Какие состояния анализировать: на каждое — отдельный запуск Multiwfn'))
        analysis.addWidget(self.analysis_scope)
        analysis.addWidget(self.analysis_button)
        analysis.addWidget(self.hole_button)
        # the charge transfer of the state chosen between fragments (IFCT) and its transition matrix
        self.transfer_button = QPushButton(tr('Перенос заряда…'))
        self.transfer_button.setToolTip(tr('Сколько электрона выбранного состояния переходит между фрагментами молекулы '
                                           '(IFCT) и матрица перехода по атомам — тепловой картой'))
        self.transfer_button.clicked.connect(self.charge_transfer)
        analysis.addWidget(self.transfer_button)
        self.transfer_context = None
        analysis.addStretch(1)
        from azimuth.ui import StatusEcho

        self.analysis_status = StatusEcho()  # the messages in the status line, not a line here
        analysis.addWidget(self.analysis_status, 3)
        column.addLayout(analysis)
        # the natural transition orbitals of the state chosen (ORCA DoNTO) — its pairs and the way to Compass
        nto_row = QHBoxLayout()
        self.nto_note = QLabel()
        self.nto_note.setObjectName('subtitle')
        self.nto_note.setWordWrap(True)
        self.nto_button = iconify(QPushButton(), 'compass', tr('Перейти в Компас · NTO выбранного состояния: орбиталь '
                                                              '«откуда» (дырка) или «куда» (частица)'))
        self.nto_button.clicked.connect(self.nto_menu)
        nto_row.addWidget(self.nto_note, 1)
        nto_row.addWidget(self.nto_button)
        column.addLayout(nto_row)
        self.ntos, self.nto_show = {}, None
        self.nto_note.hide()
        self.nto_button.hide()
        self.analysis_source = self.analysis_show = None
        self.indices = {}
        for b in (self.analysis_scope, self.analysis_button, self.hole_button, self.transfer_button):
            b.setVisible(False)
        self.plot = UVPlot()
        self.plot.fwhm = self.fwhm.value()
        column.addWidget(self.plot, 2)
        self.emission_plot = EmissionPlot()
        self.emission_plot.fwhm = self.fwhm.value()
        self.emission_plot.hide()
        column.addWidget(self.emission_plot, 2)
        # + the indices of the analysis (hidden until done); + R (hidden without rotatory strengths)
        self.table = QTableWidget(0, 6 + len(INDEX_COLUMNS))
        self.table.setHorizontalHeaderLabels(
            [tr('Состояние'), tr('E, эВ'), tr('λ, нм'), tr('f'), tr('Мультиплетность')] + [tr(t) for _, t in INDEX_COLUMNS]
            + [tr('R, 10⁻⁴⁰ СГС')]
        )
        self.R_COLUMN = 5 + len(INDEX_COLUMNS)
        for k in range(len(INDEX_COLUMNS)):
            self.table.setColumnHidden(5 + k, True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)  # several states to analyse
        self.table.verticalHeader().hide()
        column.addWidget(self.table, 1)
        self.plot.selected.connect(self.table.selectRow)
        self.table.currentCellChanged.connect(lambda row, *_: self.highlight(row))
        self.table.currentCellChanged.connect(lambda row, *_: self.update_nto_note(row))

    def load(self, excitations):
        self.excitations = tuple(excitations)
        self.plot.shift_ev = 0.0  # the shift found for another result is not this one's
        self.indices = {}
        for k in range(len(INDEX_COLUMNS)):
            self.table.setColumnHidden(5 + k, True)
        self.analysis_status.setText('')
        self.plot.excitations = self.excitations
        self.plot.current = -1
        self.table.setRowCount(len(self.excitations))
        for i, e in enumerate(self.excitations):
            values = (
                e.label,
                f'{e.energy_ev:.3f}',
                f'{e.wavelength:.1f}',
                f'{e.fosc:.4f}',
                '' if e.multiplicity is None else str(e.multiplicity),
            )
            for j, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(i, j, item)
            item = QTableWidgetItem('' if e.rotatory is None else f'{e.rotatory:.4f}')
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, self.R_COLUMN, item)
        self.has_rotatory = any(e.rotatory is not None for e in self.excitations)
        self.table.setColumnHidden(self.R_COLUMN, not self.has_rotatory)
        self.emission = None  # set_emission after load gives it (an optimization of an excited state)
        self._kinds_shown()
        # the view chosen stays for the next result with rotatory strengths (a result without them, or the empty
        # load between two results, only draws absorption — it used to reset the choice to UV-Vis)
        self.set_kind(self.kind.currentData())

    def _kinds_shown(self):
        """The views the result has — absorption always, ECD with rotatory strengths, emission after an
        optimization of an excited state; the list shown when there is more than one."""
        kinds = ['uv'] + (['cd'] if self.has_rotatory else []) + (['em'] if self.emission is not None else [])
        for row in range(self.kind.count()):
            self.kind.view().setRowHidden(row, self.kind.itemData(row) not in kinds)
        # the view chosen is kept for the next result that has it; only a list shown with a view the result has
        # not is put back to absorption
        if len(kinds) > 1 and self.kind.currentData() not in kinds:
            self.kind.blockSignals(True)
            self.kind.setCurrentIndex(0)
            self.kind.blockSignals(False)
        self.kind.setVisible(len(kinds) > 1)
        return kinds

    def set_emission(self, found):
        """The emission of an optimization of an excited state
        (modules/spectrum/analysis/emission.py), or None; shown as the view «Излучение»."""
        self.emission = found
        self.emission_plot.emission = found
        self._kinds_shown()
        self.set_kind(self.kind.currentData())
        return found is not None

    def set_kind(self, kind):
        """The plot and the summary of absorption ('uv') or of ECD ('cd'); of emission ('em')."""
        emitted = kind == 'em' and self.emission is not None
        self.plot.setVisible(not emitted)
        self.emission_plot.setVisible(emitted)
        if emitted:
            from modules.spectrum.analysis import emission

            self.summary.setText(emission.summary(self.emission))
            self.export_button.setEnabled(True)
            self.emission_plot.update()
            return
        self.plot.set_mode(kind if self.has_rotatory and kind == 'cd' else 'uv')
        if self.plot.mode == 'cd':
            given = [e for e in self.excitations if e.rotatory is not None]
            gauge = tr('калибровка скоростей') if any(e.r_velocity is not None for e in given) else tr('калибровка длины')
            if rotatory_is_zero(given):
                self.summary.setText(tr('Вращательные силы практически нулевые (все |R| < 0,1·10⁻⁴⁰): молекула ахиральна, '
                                        'спектра ЭКД у неё нет'))
            else:
                strong = max(given, key=lambda e: abs(e.rotatory))
                self.summary.setText(tr(f'ЭКД, {gauge} · самая сильная полоса: {strong.wavelength:.1f} нм, '
                                        f'R = {strong.rotatory:+.2f}·10⁻⁴⁰ · у зеркального изомера знаки обратные'))
            self.export_button.setEnabled(bool(given))
        else:
            allowed = [e for e in self.excitations if e.fosc > 0]
            if allowed:
                bright = max(allowed, key=lambda e: e.fosc)
                self.summary.setText(
                    tr(
                        f'Переходов: {len(self.excitations)} · самый интенсивный: {bright.wavelength:.1f} нм, f = {bright.fosc:.3f}'
                    )
                )
            else:
                self.summary.setText(tr('Разрешённых переходов нет'))
            self.export_button.setEnabled(bool(allowed))
        if self.experiment_raw is not None:  # ECD is signed, absorption is not
            self.show_experiment()
        self.plot.update()

    # -- the natural transition orbitals ---------------------------------------------------------------------
    def set_ntos(self, ntos, show=None):
        """ntos: {state (1-based): nto.NtoState}; show(entry, 'hole' | 'particle') -> bool puts the NTO on the model."""
        self.ntos = dict(ntos or {})
        if show is not None:
            self.nto_show = show
        self.nto_note.setVisible(bool(self.ntos))
        self.nto_button.setVisible(bool(self.ntos) and self.nto_show is not None)
        self.update_nto_note(self.table.currentRow())
        return bool(self.ntos)

    def nto_entry(self, row=None):
        row = self.table.currentRow() if row is None else row
        return self.ntos.get(row + 1) if row is not None and row >= 0 else None

    def update_nto_note(self, row):
        from modules.spectrum.analysis import nto

        if not self.ntos:
            return ''
        entry = self.nto_entry(row)
        label = self.excitations[row].label if 0 <= row < len(self.excitations) else ''
        text = (tr(f'NTO {label}: ') + nto.describe(entry, 3)) if entry is not None and entry.pairs else \
            tr('NTO: выберите состояние в таблице — пары орбиталей «откуда → куда» и их вес.')
        self.nto_note.setText(text)
        self.nto_button.setEnabled(entry is not None and bool(entry.pairs))
        return text

    def nto_menu(self, *args):
        from PySide6.QtWidgets import QMenu

        entry = self.nto_entry()
        if entry is None or not entry.pairs or self.nto_show is None:
            return None
        pair = entry.pairs[0]
        hole, particle = f'{pair.hole}{pair.spin}', f'{pair.particle}{pair.spin}'
        menu = rounded(QMenu(self))  # rounded corners
        menu.addAction(tr(f'Откуда — дырка {hole}')).triggered.connect(lambda: self.nto_on_model('hole'))
        menu.addAction(tr(f'Куда — частица {particle}')).triggered.connect(lambda: self.nto_on_model('particle'))
        menu.popup(self.nto_button.mapToGlobal(self.nto_button.rect().bottomLeft()))
        return menu

    def nto_on_model(self, which='hole'):
        """The hole (or particle) NTO of the heaviest pair of the state chosen on the model of Compass."""
        entry = self.nto_entry()
        if entry is None or not entry.pairs or self.nto_show is None:
            self.nto_note.setText(tr('Выберите состояние в таблице.'))
            return False
        try:
            return bool(self.nto_show(entry, which))
        except ValueError as exc:
            self.nto_note.setText(str(exc))
            return False

    # -- the analysis of the excited states ------------------------------------------------------------------
    def set_analysis(self, source, show):
        """source() -> (program, wavefunction, output, cores) | None; show(hole, electron, title) -> bool."""
        self.analysis_source, self.analysis_show = source, show
        for b in (self.analysis_scope, self.analysis_button, self.hole_button):
            b.setVisible(source is not None)
        self.transfer_button.setVisible(source is not None and self.transfer_context is not None)

    def set_transfer(self, context):
        """Context() -> (symbols of the atoms, selection() -> [atoms 0-based]) | None."""
        self.transfer_context = context
        self.transfer_button.setVisible(self.analysis_source is not None and context is not None)

    def charge_transfer(self):
        """The window «Перенос заряда» of the state chosen in the table; the dialog or None."""
        from modules.spectrum.views.transfer_view import ChargeTransferDialog

        given = self._given()
        row = self.table.currentRow()
        if not given or self.transfer_context is None:
            return None
        if not 0 <= row < len(self.excitations):
            self.analysis_status.setText(tr('Выберите состояние в таблице.'))
            return None
        context = self.transfer_context()
        if not context or not context[0]:
            self.analysis_status.setText(tr('Нет атомов результата.'))
            return None
        symbols, selection = context
        self.transfer_dialog = ChargeTransferDialog(self, given, row + 1, self.excitations[row].label, symbols, selection)
        self.transfer_dialog.show()
        return self.transfer_dialog

    def chosen_states(self):
        """The states (1-based) of the scope chosen: all, those chosen in the table (else the current one),
        the bright ones (f ≥ BRIGHT)."""
        scope = self.analysis_scope.currentData()
        count = len(self.excitations)
        if scope == 'chosen':
            rows = sorted({i.row() for i in self.table.selectionModel().selectedRows()}) if self.table.selectionModel() else []
            if not rows and 0 <= self.table.currentRow() < count:
                rows = [self.table.currentRow()]
            return [r + 1 for r in rows if r < count]
        if scope == 'bright':
            return [k for k, e in enumerate(self.excitations, 1) if e.fosc >= BRIGHT]
        return list(range(1, count + 1))

    def mixed_kinds(self):
        """Singlets and triplets in one output (ORCA %tddft triplets true): Multiwfn asks which kind."""
        found = {e.multiplicity for e in self.excitations}
        return 1 in found and 3 in found

    def multiwfn_state(self, k):
        """(the number of the state for Multiwfn, the kind '1' / '3' or None) of the row k (1-based). The rows are
        ordered by the energy, singlets and triplets mixed, and
        ORCA numbers the states within their kind — the row was taken for the number, Multiwfn got another state (and
        its question of the kind took the number for an answer, the analysis failed)."""
        e = self.excitations[k - 1]
        return e.state, (('3' if e.multiplicity == 3 else '1') if self.mixed_kinds() else None)

    def _given(self):
        given = self.analysis_source() if self.analysis_source is not None else None
        if not given:
            self.analysis_status.setText(tr('Нужны файл орбиталей и вывод TD-DFT (ORCA или Gaussian) и Multiwfn.'))
        return given

    def _wait(self, title, work):
        from azimuth.tasks import run_waiting

        try:
            return run_waiting(self, title, work)
        except InterruptedError:
            return None
        except (OSError, ValueError, MemoryError) as exc:
            self.analysis_status.setText(str(exc))
            return None

    def analyse(self):
        """D, Sr, H, t, HDI, EDI of every state (one Multiwfn run each, the coarse grid) and Δr of all; the table gets
        the columns, the folder of the calculation the CSV «<name>_excitations.csv»."""
        from modules.spectrum.wavefunction import field_tables, multiwfn

        given = self._given()
        if not given or not self.excitations:
            return None
        program, path, output, cores = given
        count = len(self.excitations)
        states = self.chosen_states()
        if not states:
            self.analysis_status.setText(tr('Нет состояний для анализа: выберите строки в таблице или другой набор.'))
            return None

        def work(step):
            found = {}
            for n, k in enumerate(states):
                if step(n, len(states) + 1) is False:
                    raise InterruptedError()
                number, kind = self.multiwfn_state(k)
                found[k] = multiwfn.run_hole_electron(program, path, output, number, 'low', cores, step, kind=kind)[0]
            # Δr of all the states, of each kind by itself when there are two; back to the rows by (kind, number)
            rows = {self.multiwfn_state(k): k for k in range(1, count + 1)}
            kinds = ('1', '3') if self.mixed_kinds() else (None,)
            for kind in kinds:
                size = sum(1 for (_, each) in rows if each == kind)
                try:
                    delta, _ = multiwfn.run_delta_r(program, path, output, cores, step, states=size, kind=kind)
                except ValueError:
                    delta = {}
                for number, value in delta.items():
                    k = rows.get((number, kind))
                    if k in found:
                        found[k]['delta_r'] = value
            return found

        found = self._wait(tr('Анализ возбуждений…'), work)
        if found is None:
            return None
        for k, values in found.items():  # the states analysed before stay
            self.indices.setdefault(k, {}).update(values)
        self.fill_indices()
        header = [tr('Состояние'), tr('E, эВ'), tr('λ, нм'), tr('f')] + [tr(t) for _, t in INDEX_COLUMNS]
        rows = []
        for k, e in enumerate(self.excitations, 1):
            values = self.indices.get(k, {})
            rows.append([e.label, f'{e.energy_ev:.4f}', f'{e.wavelength:.2f}', f'{e.fosc:.6f}']
                        + [self.cell(values, key) for key, _ in INDEX_COLUMNS])
        base = Path(path)
        try:
            field_tables.write_tables(base.parent, base.name.split('.')[0], {'excitations': (header, rows)})
            self.analysis_status.setText(tr('Таблицы — в папке «Анализ» расчёта.'))
        except OSError as exc:
            self.analysis_status.setText(tr('Таблица не записана: ') + str(exc))
        return found

    @staticmethod
    def cell(values, key):
        if key == 'character':
            return character(values)
        value = values.get(key)
        return '' if value is None else (f'{value:.3f}' if key in ('d', 'h', 't', 'delta_r', 'sr') else f'{value:.2f}')

    def fill_indices(self):
        for k in range(len(INDEX_COLUMNS)):
            self.table.setColumnHidden(5 + k, False)
        for row in range(len(self.excitations)):
            values = self.indices.get(row + 1, {})
            for k, (key, _) in enumerate(INDEX_COLUMNS):
                item = QTableWidgetItem(self.cell(values, key))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 5 + k, item)

    def hole_on_model(self):
        from modules.spectrum.wavefunction import multiwfn

        given = self._given()
        row = self.table.currentRow()
        if not given or self.analysis_show is None:
            return False
        if not 0 <= row < len(self.excitations):
            self.analysis_status.setText(tr('Выберите состояние в таблице.'))
            return False
        program, path, output, cores = given
        number, kind = self.multiwfn_state(row + 1)
        found = self._wait(tr('Дырка и электрон…'),
                           lambda step: multiwfn.run_hole_electron_cubes(program, path, output, number, 'medium', cores, step,
                                                                         kind=kind))
        if found is None:
            return False
        hole, electron, values = found
        self.indices.setdefault(row + 1, {}).update(values)
        label = self.excitations[row].label
        return bool(self.analysis_show(hole, electron, tr(f'Состояние {label}: дырка (синее) и электрон (зелёное)')))

    def set_width(self, value):
        self.plot.fwhm = value
        self.plot.update()
        self.emission_plot.fwhm = value
        self.emission_plot.update()

    # -- the experiment and the conformers (spectrum_extras.ExtrasMixin) ----------------------------------
    EXPERIMENT_AXIS = 'nm'
    NIST_KIND = 'UVVis'

    def signed(self):
        return self.plot.mode == 'cd'

    @property
    def fit_values(self):
        from modules.spectrum.analysis.experiment import SHIFTS

        return SHIFTS

    def fit_hint(self):
        return tr('Сдвиг энергий переходов от −1 до +1 эВ, с которым расчётный спектр больше всего похож на измеренный')

    def fit_curve(self, shift):
        from modules.spectrum.analysis.experiment import shifted_excitations

        base = self.plot.ensemble[0] if self.plot.ensemble else self.excitations
        return self.plot.curve(shifted_excitations(base, shift))

    def apply_fit(self, shift):
        self.plot.shift_ev = float(shift)
        self.plot.update()
        return tr('сдвиг энергий {} эВ').format(num(shift, '+.2f'))

    def extra_actions(self, menu):
        if self.plot.shift_ev:
            menu.addSeparator()
            menu.addAction(tr('Убрать сдвиг ({} эВ)').format(num(self.plot.shift_ev, '+.2f')),
                           lambda: self.clear_shift())

    def clear_shift(self):
        self.plot.shift_ev = 0.0
        self.plot.update()

    def ensemble_lists(self, outputs):
        return [tuple(o.absorption) for o in outputs]

    def lacking_text(self):
        return tr('Нет возбуждённых состояний (UV-Vis) у конформеров: ')

    def set_ensemble_lines(self, lines, name):
        self.plot.ensemble = (tuple(lines), name) if lines else None
        self.plot.update()

    def set_reference(self, excitations, name=''):
        """Draw the excitations of another result too (None: remove it)."""
        allowed = [e for e in excitations or () if e.fosc > 0]
        self.plot.reference = (tuple(excitations), name) if allowed else None
        self.clear_button.setVisible(self.plot.reference is not None)
        self.plot.update()
        return self.plot.reference is not None

    def choose_reference(self):
        path = reference_path(self, tr('Сравнить спектр UV-Vis'))
        if path:
            output = read_reference(self, path)
            if output is not None and not self.set_reference(output.absorption, Path(path).name):
                show_error(self, tr('В этом файле нет разрешённых переходов UV-Vis.'))

    def highlight(self, row):
        self.plot.current = row
        self.plot.update()

    def export(self):
        if self.emission_plot.isVisibleTo(self) and self.emission is not None:  # emission
            path, _ = QFileDialog.getSaveFileName(self, tr('Экспорт излучения'), str(Path.home() / 'emission.png'),
                                                  tr('PNG (*.png);;SVG (*.svg);;CSV (*.csv)'))
            if path:
                x, absorbed, emitted = self.emission_plot.curves()
                _export_widget(self.emission_plot, Path(path), 'Azimuth · emission', zip(x, absorbed, emitted),
                               ['wavelength_nm', 'absorption_relative', 'emission_relative'])
            return path
        cd = self.plot.mode == 'cd'
        path, _ = QFileDialog.getSaveFileName(
            self, tr('Экспорт ЭКД') if cd else tr('Экспорт UV-Vis'), str(Path.home() / ('ecd.png' if cd else 'uv-vis.png')),
            tr('PNG (*.png);;SVG (*.svg);;CSV (*.csv)')
        )
        if not path:
            return
        x, y = self.plot.curve(self.plot.shown(self.excitations))  # with the shift of the energies
        _export_widget(self.plot, Path(path), 'Azimuth · ' + ('ECD' if cd else 'UV-Vis'), zip(x, y),
                       ['wavelength_nm', 'delta_epsilon_L_mol-1_cm-1' if cd else 'epsilon_L_mol-1_cm-1'])
