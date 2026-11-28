"""«Порошковая дифрактограмма» of the «Кристалл» window.

§1 PURPOSE
    The powder pattern of the crystal with intensities
    (modules/compass/chemistry/powder.py) — the curve, the lines with hkl, d and the multiplicity, a measured pattern
    (.xy) laid over it, the curve saved as .xy.
§4 SPECIFICATION
    PowderWindow(crystal_window, crystal): source (wavelength combo), start, stop, fwhm (spin boxes), plot
    (PowderPlot: curve, lines, measured), table; compute() -> lines; load_xy(path=None) -> path; save_xy(path=None)
    -> path; save_lines(path=None) -> path. Ka2 (check box: the Kα₂ doublets), widths (combo:
    'fixed' | 'caglioti') with u, v, w, eta (the Lorentzian share), step; texture (check box), texture_hkl (line),
    texture_r — March–Dollase; second — the lines of Kα₂ drawn; shape() -> the shape of the curve.
§7 TESTS
    tests/gui/test_gui_files.py::test_crystal_powder_pattern.
"""

from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
                               QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from azimuth.i18n import tr
from azimuth.ui import action_button, help_button
from modules.compass.chemistry import powder

CURVE = '#2a62b8'
MEASURED = '#c0504d'


class PowderPlot(QWidget):
    """The calculated curve (blue), the line positions as ticks under the axis, a measured pattern (red), 2θ in degrees."""

    def __init__(self):
        super().__init__()
        self.curve = ([], [])
        self.lines = ()
        self.measured = None
        self.span = (5.0, 90.0)
        self.setMinimumHeight(240)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        ink = self.palette().text().color()
        left, right, top = 40, self.width() - 12, 12
        bottom = self.height() - 34
        lo, hi = self.span
        width = max(1, right - left)

        def x_of(t):
            return left + (t - lo) / (hi - lo) * width

        def y_of(v):
            return bottom - (bottom - top) * v / 100

        p.setPen(QPen(ink, 1))
        p.drawLine(QPointF(left, bottom), QPointF(right, bottom))
        p.drawLine(QPointF(left, bottom), QPointF(left, top))
        font = QFont(self.font())
        font.setPixelSize(10)
        p.setFont(font)
        step = 10 if hi - lo > 40 else 5 if hi - lo > 15 else 1
        t = int(lo // step + 1) * step
        while t <= hi:
            x = x_of(t)
            p.drawLine(QPointF(x, bottom), QPointF(x, bottom + 4))
            p.drawText(QRectF(x - 20, bottom + 14, 40, 14), Qt.AlignmentFlag.AlignCenter, f'{t:g}')
            t += step
        p.drawText(QRectF(right - 60, bottom + 14, 60, 14), Qt.AlignmentFlag.AlignRight, '2θ, °')
        p.drawText(QRectF(2, top - 6, left - 6, 14), Qt.AlignmentFlag.AlignRight, '100')
        if self.measured:
            self._draw(p, self.measured, QColor(MEASURED), x_of, y_of)
        xs, ys = self.curve
        if xs:
            self._draw(p, (xs, ys), QColor(CURVE), x_of, y_of)
        p.setPen(QPen(QColor(CURVE), 1))
        for line in self.lines:
            x = x_of(line.two_theta)
            p.drawLine(QPointF(x, bottom + 4), QPointF(x, bottom + 10))
        p.end()

    @staticmethod
    def _draw(p, data, colour, x_of, y_of):
        xs, ys = data
        path = QPainterPath()
        for k, (x, y) in enumerate(zip(xs, ys)):
            point = QPointF(x_of(x), y_of(y))
            if k:
                path.lineTo(point)
            else:
                path.moveTo(point)
        p.setPen(QPen(colour, 1.2))
        p.drawPath(path)


class PowderWindow(QDialog):
    def __init__(self, crystal_window, crystal):
        super().__init__(crystal_window)
        self.crystal_window, self.crystal = crystal_window, crystal
        self.lines = ()
        self.second = ()  # the lines of Kα₂
        self.measured_path = None
        self.measured_raw = None  # (2θ, I) of the file; self.match — powder_match.Match
        self.match = None
        self.setWindowTitle(tr('Порошковая дифрактограмма · ') + (crystal.title or 'CIF'))
        layout = QVBoxLayout(self)
        # the explanation behind «?» (help_button), not on the page
        note = tr('Рассчитана по атомам ячейки: атомные факторы рассеяния нейтральных атомов, тепловые '
                  'параметры файла, фактор Лоренца — поляризации; без поглощения, текстура — по желанию '
                  '(March–Dollase). Высота — в % от самой сильной линии.')
        row = QHBoxLayout()
        self.source = QComboBox()
        for name, value in powder.WAVELENGTHS.items():
            self.source.addItem(f'{name} · {value:.5f} Å', value)
        row.addWidget(QLabel(tr('Излучение')))
        row.addWidget(self.source)
        self.start, self.stop, self.fwhm = (self._spin(v, a, b, s, d) for v, a, b, s, d in
                                            ((5.0, 1.0, 170.0, 1.0, 1), (90.0, 2.0, 175.0, 1.0, 1), (0.10, 0.01, 2.0, 0.02, 2)))
        row.addWidget(QLabel('2θ, °'))
        row.addWidget(self.start)
        row.addWidget(QLabel('—'))
        row.addWidget(self.stop)
        row.addWidget(QLabel(tr('Ширина линии, °')))
        row.addWidget(self.fwhm)
        row.addStretch(1)
        row.addWidget(help_button(note))
        layout.addLayout(row)
        # the Kα₂ line, the widths of Caglioti, the Lorentzian share, the step, the texture
        shape = QHBoxLayout()
        self.ka2 = QCheckBox('Kα₂')
        self.ka2.setToolTip(tr('Вторая линия трубки: каждая линия ещё раз при λ(Kα₂) с половинной интенсивностью — '
                               'как в опыте без монохроматора Kα₁'))
        shape.addWidget(self.ka2)
        self.anomalous = QCheckBox(tr('Аномальное рассеяние'))
        self.anomalous.setToolTip(tr('f′ и f″ атомов на линии трубки (Henke и др., 1993): заметно для тяжёлых атомов '
                                     'и вблизи края поглощения — Fe с Co Kα, Cu с Cu Kα'))
        shape.addWidget(self.anomalous)
        self.widths = QComboBox()
        self.widths.addItem(tr('ширина постоянная'), 'fixed')
        self.widths.addItem(tr('ширина по Кальоти'), 'caglioti')
        self.widths.setToolTip(tr('По Кальоти: FWHM² = U tan²θ + V tanθ + W — линии шире к большим углам, как на '
                                  'приборе; U, V, W — в градусах²'))
        shape.addWidget(self.widths)
        self.u, self.v, self.w = (self._spin(value, -1.0, 1.0, 0.001, 4) for value in (0.01, -0.005, 0.003))
        for box, name in ((self.u, 'U'), (self.v, 'V'), (self.w, 'W')):
            box.setPrefix(name + ' ')
            shape.addWidget(box)
        self.eta = self._spin(0.5, 0.0, 1.0, 0.1, 2)
        self.eta.setPrefix('η ')
        self.eta.setToolTip(tr('Доля лоренциана в форме линии (псевдо-Фойгт): 0 — гауссиана, 1 — лоренциан'))
        shape.addWidget(self.eta)
        self.step = self._spin(0.02, 0.002, 0.2, 0.01, 3)
        self.step.setPrefix(tr('шаг '))
        self.step.setSuffix('°')
        self.step.setToolTip(tr('Шаг 2θ рассчитанной кривой — он же в сохранённом файле .xy'))
        shape.addWidget(self.step)
        shape.addStretch(1)
        layout.addLayout(shape)
        texture = QHBoxLayout()
        self.texture = QCheckBox(tr('Преимущественная ориентация вдоль'))
        self.texture.setToolTip(tr('March–Dollase: пластинки или иголки ложатся в кювете не как попало; линии с '
                                   'вектором вдоль оси (hkl) усилены при r < 1 (пластинки) или ослаблены при r > 1 '
                                   '(иголки); r = 1 — без текстуры'))
        texture.addWidget(self.texture)
        self.texture_hkl = QLineEdit('0 0 1')
        self.texture_hkl.setMaximumWidth(80)
        self.texture_hkl.setToolTip(tr('Индексы плоскости hkl через пробел'))
        texture.addWidget(self.texture_hkl)
        self.texture_r = self._spin(0.8, 0.1, 5.0, 0.05, 2)
        self.texture_r.setPrefix('r ')
        texture.addWidget(self.texture_r)
        texture.addStretch(1)
        layout.addLayout(texture)
        self.status = QLabel('')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.plot = PowderPlot()
        layout.addWidget(self.plot, 1)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(['h k l', '2θ, °', 'd, Å', tr('Повторяемость'), 'I, %'])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setToolTip(tr('Двойной щелчок — плоскости этой линии в ячейке на модели'))
        self.table.cellDoubleClicked.connect(lambda row, _column: self.planes_of(row))
        layout.addWidget(self.table, 1)
        buttons = QHBoxLayout()
        buttons.addWidget(action_button(tr('Наложить опытную дифрактограмму…'), lambda: self.load_xy(), 'import'))
        # the background off, the zero and the cell fitted
        self.fitted = QCheckBox(tr('Вычесть фон, подогнать ноль и ячейку'))
        self.fitted.setChecked(True)
        self.fitted.setEnabled(False)
        self.fitted.toggled.connect(lambda _: self.compare())
        buttons.addWidget(self.fitted)
        self.compare_button = action_button(tr('Таблица сравнения…'), lambda: self.comparison_table(), 'table')
        self.compare_button.setEnabled(False)
        buttons.addWidget(self.compare_button)
        buttons.addWidget(action_button(tr('Сохранить дифрактограмму .xy…'), lambda: self.save_xy(), 'export'))
        buttons.addWidget(action_button(tr('Сохранить список линий…'), lambda: self.save_lines(), 'table'))
        buttons.addStretch(1)
        buttons.addWidget(action_button(tr('Закрыть'), self.reject, 'close'))
        layout.addLayout(buttons)
        self.source.currentIndexChanged.connect(lambda _: self.compute())
        for box in (self.start, self.stop, self.fwhm, self.u, self.v, self.w, self.eta, self.step, self.texture_r):
            box.editingFinished.connect(self.compute)
        for box in (self.ka2, self.texture, self.anomalous):
            box.toggled.connect(lambda _: self.compute())
        self.widths.currentIndexChanged.connect(lambda _: self.compute())
        self.texture_hkl.editingFinished.connect(self.compute)
        self.resize(760, 680)
        self.compute()

    @staticmethod
    def _spin(value, low, high, step, decimals):
        box = QDoubleSpinBox()
        box.setRange(low, high)
        box.setDecimals(decimals)
        box.setSingleStep(step)
        box.setValue(value)
        return box

    def alpha2(self):
        """(λ(Kα₂), ratio) of the tube chosen when «Kα₂» is on, else None."""
        names = list(powder.WAVELENGTHS)
        name = names[self.source.currentIndex()] if 0 <= self.source.currentIndex() < len(names) else None
        if not self.ka2.isChecked() or name not in powder.KA2:
            return None
        return powder.KA2[name], powder.KA2_RATIO

    def shape(self):
        """The shape of the curve — {'step', 'fwhm', 'eta', 'uvw' (or None)}."""
        caglioti = self.widths.currentData() == 'caglioti'
        for box in (self.u, self.v, self.w):
            box.setEnabled(caglioti)
        self.fwhm.setEnabled(not caglioti)
        return {'step': self.step.value(), 'fwhm': self.fwhm.value(), 'eta': self.eta.value(),
                'uvw': (self.u.value(), self.v.value(), self.w.value()) if caglioti else None}

    def texture_axis(self):
        """((h, k, l), r) of March–Dollase when the box is on; ValueError for a line that is not three integers."""
        if not self.texture.isChecked():
            return None
        try:
            hkl = tuple(int(x) for x in self.texture_hkl.text().replace(',', ' ').split())
        except ValueError:
            hkl = ()
        if len(hkl) != 3 or hkl == (0, 0, 0):
            raise ValueError(tr('Преимущественная ориентация: напишите три целых индекса плоскости, например 0 0 1.'))
        return hkl, self.texture_r.value()

    def curve(self, start, stop):
        shape = self.shape()
        every = tuple(self.lines) + tuple(self.second)
        if not every:
            return [], []
        return powder.profile(every, start, stop, shape['step'], shape['fwhm'], shape['eta'], shape['uvw'])

    def compute(self):
        start, stop = self.start.value(), self.stop.value()
        try:
            self.lines = powder.pattern(self.crystal, self.source.currentData(), start, stop,
                                        texture=self.texture_axis(), anomalous=self.anomalous.isChecked())
        except ValueError as exc:
            self.status.setText(str(exc))
            self.lines = ()
            failed = True
        else:
            self.status.setText(tr('Линий: {}').format(len(self.lines)))
            failed = False
        second = self.alpha2()
        self.second = powder.alpha2(self.lines, self.source.currentData(), second[0], second[1], start, stop) if second else ()
        self.plot.span = (start, stop) if start < stop else (5.0, 90.0)
        self.plot.lines = self.lines
        self.plot.curve = self.curve(start, stop)
        rows = [(' '.join(str(x) for x in line.hkl), f'{line.two_theta:.3f}', f'{line.d:.4f}', str(line.multiplicity),
                 f'{line.intensity:.1f}') for line in self.lines]
        self.table.setRowCount(len(rows))
        for r, values in enumerate(rows):
            for c, text in enumerate(values):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(r, c, item)
        # compared again with the new lines; not over the message of a wrong entry (its text stays)
        if getattr(self, 'measured_raw', None) is not None and not failed:
            self.compare()
        self.plot.update()
        return self.lines

    def planes_of(self, row):
        """The planes (hkl) of the line of the row on the model of the crystal (lattice_planes)."""
        if not 0 <= row < len(self.lines):
            return None
        owner = getattr(self.crystal_window, 'owner', None)
        tool = getattr(owner, 'crystal_tool', None)
        return tool.show_lattice_planes(self.lines[row].hkl) if tool is not None else None

    def load_xy(self, path=None):
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, tr('Опытная дифрактограмма'), str(Path.home()),
                                                  tr('Дифрактограмма (*.xy *.xye *.dat *.txt *.csv)'))
            if not path:
                return None
        try:
            xs, ys = powder.read_xy(Path(path).read_text(encoding='utf-8', errors='replace'))
        except (OSError, ValueError) as exc:
            self.status.setText(str(exc))
            return None
        self.measured_raw = (xs, ys)
        self.measured_path = path
        self.fitted.setEnabled(True)
        self.compare_button.setEnabled(True)
        self.compare()
        return path

    def compare(self):
        """The measured pattern against the calculated one (powder_match) — with «Вычесть фон…» the curves
        after the background and the fit of the zero and the cell, else both as they are (each to 100)."""
        from modules.compass.chemistry import powder_match

        if self.measured_raw is None:
            return None
        xs, ys = self.measured_raw
        name = Path(self.measured_path).name if self.measured_path else ''
        self.match = None
        try:
            shape = self.shape()
            self.match = powder_match.match(self.lines, xs, ys, self.source.currentData(), shape['fwhm'], shape['eta'],
                                            shape['uvw'], self.alpha2())
        except ValueError:
            self.match = None
        m = self.match
        if m is not None and self.fitted.isChecked():
            self.plot.measured = m.measured
            self.plot.curve = m.calculated
        else:
            top = max(ys) or 1.0
            self.plot.measured = (xs, [100 * y / top for y in ys])
            self.plot.curve = self.curve(self.start.value(), self.stop.value())
        text = tr('Линий: {}').format(len(self.lines)) + ' · ' + tr('опытная: ') + name
        if m is not None:
            parts = [tr('сдвиг нуля {}°').format(f'{m.shift:+.3f}'.replace('-', '−'))]
            if m.cell_change is not None:
                parts.append(tr('ячейка в опыте {} на {} % по d').format(
                    tr('больше') if m.cell_change >= 0 else tr('меньше'), f'{100 * abs(m.cell_change):.2f}'))
            parts.append(tr('расхождение профилей R = {} %, корреляция r = {}').format(
                f'{100 * m.r_profile:.0f}', f'{m.correlation:.3f}'))
            parts.append(tr('линий найдено {} из {}').format(len(m.pairs), len(m.pairs) + len(m.missing)))
            if m.extra:
                parts.append(tr('лишние пики (другая фаза?): {}').format(
                    ', '.join(f'{t:.2f}°' for t, _ in m.extra[:5])))
            text += ' · ' + '; '.join(parts)
        self.status.setText(text)
        self.plot.update()
        return m

    def comparison_table(self):
        from modules.compass.actions.qe_results import TableWindow

        m = self.match
        if m is None:
            return None
        rows = [(' '.join(str(x) for x in line.hkl), f'{line.two_theta:.3f}', f'{obs:.3f}',
                 f'{delta:+.3f}'.replace('-', '−'), f'{line.intensity:.1f}', tr('найдена'))
                for line, obs, delta in m.pairs]
        rows += [(' '.join(str(x) for x in line.hkl), f'{line.two_theta:.3f}', '—', '—', f'{line.intensity:.1f}',
                  tr('нет в опыте')) for line in m.missing]
        rows += [('—', '—', f'{t:.3f}', '—', f'{h:.0f}', tr('лишний пик')) for t, h in m.extra]
        lines = [tr('Δ — от места линии после подгонки нуля и ячейки. «Нет в опыте» — сильная линия не найдена: '
                    'текстура образца, наложение пиков или другая фаза; «лишний пик» — пик опыта без линии этой фазы: '
                    'примесь или другая модификация.'),
                 tr('Фон — среднее в окне 3° с отрезанными пиками; R — профильное расхождение без уточнения '
                    'структуры: около 10 % — та же фаза (шум опыта), десятки % — другие интенсивности, текстура или '
                    'другая фаза.')]
        self.comparison = TableWindow(self, tr('Сравнение с опытом · ') + (self.crystal.title or 'CIF'),
                                      ['h k l', tr('2θ расчёт, °'), tr('2θ опыт, °'), 'Δ, °', 'I, %', ''], rows, lines)
        self.comparison.show()
        return self.comparison

    def _target(self, path, title, pattern, suffix):
        if path is None:
            name = (self.crystal.title or 'crystal') + suffix
            path, _ = QFileDialog.getSaveFileName(self, title, str(Path.home() / name), pattern)
        return path or None

    def save_xy(self, path=None):
        path = self._target(path, tr('Сохранить дифрактограмму'), 'XY (*.xy)', '.xy')
        if path:
            from azimuth.files import atomic_write

            xs, ys = self.plot.curve
            atomic_write(path, '# 2theta intensity, ' + self.source.currentText() + '\n' + powder.write_xy(xs, ys))
        return path

    def save_lines(self, path=None):
        path = self._target(path, tr('Сохранить список линий'), 'CSV (*.csv)', '-lines.csv')
        if path:
            from azimuth.files import atomic_write

            text = 'h,k,l,2theta,d,multiplicity,I\n' + ''.join(
                f'{h},{k},{l},{line.two_theta:.4f},{line.d:.5f},{line.multiplicity},{line.intensity:.2f}\n'
                for line in self.lines for h, k, l in [line.hkl])
            atomic_write(path, text)
        return path
