"""Spectrum: the «Сходимость» tab. Data: modules/spectrum/analysis/convergence.py.

Upper plot: the energy of every optimization step relative to the last one, kcal/mol. Lower plot: log10 of
each convergence criterion per step (gradients, steps, forces, displacements, xtb gradient norm), each in its
own colour, with its threshold as a dashed line of the same colour when the program printed it. A table under
the plots: the last value of each criterion, the threshold and whether it is met. PNG / SVG / CSV export.
"""

from math import log10
from pathlib import Path

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
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

from modules.spectrum.analysis.convergence import TITLES, relative_kcal
from azimuth.i18n import tr

COLORS = ('#6ea2f0', '#ffb454', '#5cc28a', '#e0709a', '#b28cff', '#59c3c3')


def nice_ticks(lo, hi, count=5):
    """Round values between lo and hi, about count of them (1, 2, 2.5 or 5 × a power of ten apart)."""
    from math import ceil, floor

    span = hi - lo
    if span <= 0:
        return [lo]
    raw = span / max(1, count)
    power = 10 ** floor(log10(raw))
    step = next(m * power for m in (1, 2, 2.5, 5, 10) if m * power >= raw)
    first = ceil(lo / step - 1e-9) * step
    ticks = []
    value = first
    while value <= hi + 1e-9 * step:
        ticks.append(round(value, 10))
        value += step
    return ticks


def step_ticks(steps, room):
    """The steps marked on the axis: every one when they fit (room px for each), else round ones."""
    if steps <= max(2, room):
        return list(range(1, steps + 1))
    every = next(m for m in (2, 5, 10, 20, 25, 50, 100, 200, 500, 1000) if steps / m <= room)
    return [1] + [k for k in range(every, steps + 1, every)]


class ConvergencePlot(QWidget):
    """Ticks with values on both axes and faint grid lines, the titles of the
    axes along them (turned upright at the left), the names of the criteria in a row of their own over the lower plot —
    never over the curves."""

    LEFT, RIGHT, TOP, GAP, BOTTOM = 84, 18, 14, 18, 40

    def __init__(self):
        super().__init__()
        self.history = None
        self.setMinimumHeight(320)

    def series(self):
        """[(name, [(step, log10 value)])] of the criteria with positive values."""
        out = []
        for name, values in self.history.criteria.items():
            points = [(k + 1, log10(v)) for k, v in enumerate(values) if v is not None and v > 0]
            if points:
                out.append((name, points))
        return out

    def _axis_title(self, p, text, top, height, labels=0.0):
        """The title of a y axis turned upright, at the left of its plot, centred on it — right by the values of the
        axis (labels — the widest of them)."""
        p.save()
        x = max(p.fontMetrics().height() / 2 + 2, self.LEFT - 7 - labels - 8 - p.fontMetrics().height() / 2)
        p.translate(x, top + height / 2)
        p.rotate(-90)
        width = p.fontMetrics().horizontalAdvance(text)
        p.drawText(QPointF(-width / 2, p.fontMetrics().ascent() / 2), text)
        p.restore()

    def _y_ticks(self, p, ticks, y, left, width, fmt):
        grid = QColor(self.palette().mid().color())
        grid.setAlpha(45)
        text = self.palette().text().color()
        metrics = p.fontMetrics()
        widest = 0.0
        for value in ticks:
            yy = y(value)
            p.setPen(QPen(grid, 1))
            p.drawLine(QPointF(left, yy), QPointF(left + width, yy))
            p.setPen(QPen(self.palette().mid().color(), 1))
            p.drawLine(QPointF(left - 4, yy), QPointF(left, yy))
            label = fmt(value)
            p.setPen(text)
            p.drawText(QPointF(left - 7 - metrics.horizontalAdvance(label), yy + metrics.ascent() / 2 - 1), label)
            widest = max(widest, metrics.horizontalAdvance(label))
        return widest

    def _legend(self, p, names, left, width):
        """The names of the criteria with a sample of their line, in rows over the lower plot; its height."""
        metrics = p.fontMetrics()
        x, rows = left, 1
        places = []
        for k, name in enumerate(names):
            label = tr(TITLES.get(name, name))
            room = 22 + metrics.horizontalAdvance(label) + 18
            if x + room > left + width and x > left:
                x, rows = left, rows + 1
            places.append((k, label, x, rows - 1))
            x += room
        return places, rows * (metrics.height() + 4)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), self.palette().base())
        from azimuth.ui import frame_plot  # the border of the plot (light theme)

        frame_plot(p, self)
        text = self.palette().text().color()
        p.setPen(text)
        h = self.history
        if h is None:
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, tr('Нет шагов оптимизации'))
            return
        steps = max(2, h.steps)
        width = max(1, self.width() - self.LEFT - self.RIGHT)
        series = self.series()
        places, legend_height = self._legend(p, [name for name, _ in series], self.LEFT, width)
        free = self.height() - self.TOP - self.GAP - legend_height - self.BOTTOM
        pane = max(40, free // 2)
        frame = QPen(self.palette().mid().color(), 1)

        def x(step):
            return self.LEFT + (step - 1) / (steps - 1) * width

        marks = step_ticks(steps, max(2, width // 34))

        def step_marks(bottom, labels):
            metrics = p.fontMetrics()
            for step in marks:
                xx = x(step)
                p.setPen(frame)
                p.drawLine(QPointF(xx, bottom), QPointF(xx, bottom + 4))
                if labels:
                    p.setPen(text)
                    label = str(step)
                    p.drawText(QPointF(xx - metrics.horizontalAdvance(label) / 2, bottom + 6 + metrics.ascent()), label)

        energy = relative_kcal(h)
        top_y = self.TOP
        p.setPen(text)
        energy_labels = 0.0
        if len(energy) >= 2:
            values = [v for _, v in energy]
            lo, hi = min(values + [0.0]), max(values + [0.0])
            span = (hi - lo) or 1.0
            y = lambda v: top_y + pane - (v - lo) / span * pane  # noqa: E731
            ticks = [t for t in nice_ticks(lo, hi, max(3, pane // 34)) if lo - 1e-12 <= t <= hi + 1e-12]
            energy_labels = self._y_ticks(p, ticks, y, self.LEFT, width, lambda v: f'{v:g}')
            path = QPainterPath()
            for k, (_, v) in enumerate(energy):
                point = QPointF(x(k + 1), y(v))
                if k:
                    path.lineTo(point)
                else:
                    path.moveTo(point)
            p.setPen(QPen(QColor(COLORS[0]), 2))
            p.drawPath(path)
            for k, (_, v) in enumerate(energy):
                p.drawEllipse(QPointF(x(k + 1), y(v)), 2.5, 2.5)
        else:
            p.setPen(text)
            p.drawText(self.LEFT + 8, top_y + 20, tr('Энергии шагов нет в файле'))
        p.setPen(frame)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(self.LEFT, top_y, width, pane)
        step_marks(top_y + pane, False)

        legend_top = top_y + pane + self.GAP
        low_y = legend_top + legend_height
        metrics = p.fontMetrics()
        for k, label, lx, row in places:
            ink = QColor(COLORS[k % len(COLORS)])
            ly = legend_top + row * (metrics.height() + 4) + metrics.height() / 2
            p.setPen(QPen(ink, 2))
            p.drawLine(QPointF(lx, ly), QPointF(lx + 16, ly))
            p.setPen(text)
            p.drawText(QPointF(lx + 22, ly + metrics.ascent() / 2 - 1), label)
        p.setPen(text)
        criteria_labels = 0.0
        if series:
            values = [v for _, pts in series for _, v in pts]
            values += [log10(t) for t in h.thresholds.values() if t and t > 0]
            lo, hi = min(values), max(values)
            span = (hi - lo) or 1.0
            y = lambda v: low_y + pane - (v - lo) / span * pane  # noqa: E731
            ticks = [t for t in nice_ticks(lo, hi, max(3, pane // 34)) if lo - 1e-12 <= t <= hi + 1e-12]
            criteria_labels = self._y_ticks(p, ticks, y, self.LEFT, width, lambda v: f'{v:g}'.replace('-', '−'))
            for k, (name, pts) in enumerate(series):
                ink = QColor(COLORS[k % len(COLORS)])
                path = QPainterPath()
                path.moveTo(QPointF(x(pts[0][0]), y(pts[0][1])))
                for step, v in pts[1:]:
                    path.lineTo(QPointF(x(step), y(v)))
                p.setPen(QPen(ink, 2))
                p.drawPath(path)
                threshold = h.thresholds.get(name)
                if threshold and threshold > 0:
                    p.setPen(QPen(ink, 1, Qt.PenStyle.DashLine))
                    p.drawLine(QPointF(self.LEFT, y(log10(threshold))), QPointF(self.LEFT + width, y(log10(threshold))))
        else:
            p.drawText(self.LEFT + 8, low_y + 20, tr('Критериев сходимости нет в файле'))
        p.setPen(frame)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(self.LEFT, low_y, width, pane)
        step_marks(low_y + pane, True)
        p.setPen(text)
        title = tr('шаг')
        p.drawText(QPointF(self.LEFT + width / 2 - metrics.horizontalAdvance(title) / 2, self.height() - 6), title)
        self._axis_title(p, tr('ΔE, ккал/моль'), top_y, pane, energy_labels)  # by the values of their axes
        self._axis_title(p, tr('log₁₀ критерия'), low_y, pane, criteria_labels)


class ConvergencePanel(QWidget):
    def __init__(self):
        super().__init__()
        self.history = None
        column = QVBoxLayout(self)
        column.setContentsMargins(0, 8, 0, 0)
        controls = QHBoxLayout()
        self.summary = QLabel()  # not over the plots — the steps are in the status of the result
        self.summary.setObjectName('subtitle')
        self.summary.setWordWrap(True)
        self.summary.hide()
        controls.addStretch(1)
        self.export_button = QPushButton(tr('Экспорт…'))
        self.export_button.clicked.connect(self.export)
        controls.addWidget(self.export_button)
        column.addLayout(controls)
        self.plot = ConvergencePlot()
        column.addWidget(self.plot, 3)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels([tr('Критерий'), tr('Последнее значение'), tr('Порог'), tr('Выполнен')])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().hide()
        column.addWidget(self.table, 1)

    def load(self, history):
        self.history = history
        self.plot.history = history
        rows = []
        if history is not None:
            for name, values in history.criteria.items():
                last = next((v for v in reversed(values) if v is not None), None)
                threshold = history.thresholds.get(name)
                met = history.converged.get(name)
                rows.append((
                    tr(TITLES.get(name, name)),
                    '' if last is None else f'{last:.2e}',
                    '' if threshold is None else f'{threshold:.2e}',
                    '' if met is None else (tr('да') if met else tr('нет')),
                ))
            self.summary.setText(
                tr(f'{history.program}: шагов {history.steps}') + (
                    tr(f' · изменение энергии от первого шага {relative_kcal(history)[0][1]:.2f} ккал/моль')
                    if len(history.energies) >= 2 else ''
                )
            )
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, value in enumerate(row):
                self.table.setItem(i, j, QTableWidgetItem(value))
        self.export_button.setEnabled(history is not None)
        self.plot.update()
        return history is not None

    def csv_rows(self):
        h = self.history
        names = list(h.criteria)
        energy = dict(enumerate([v for _, v in relative_kcal(h)], 1))
        rows = []
        for step in range(1, h.steps + 1):
            row = [step, energy.get(step, '')]
            for name in names:
                values = h.criteria[name]
                row.append('' if step > len(values) or values[step - 1] is None else values[step - 1])
            rows.append(row)
        return rows, ['step', 'dE_kcal_mol', *names]

    def export(self):
        from modules.spectrum.views.spectrum_common import _export_widget

        if self.history is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, tr('Экспорт сходимости'), str(Path.home() / 'convergence.png'), tr('PNG (*.png);;SVG (*.svg);;CSV (*.csv)')
        )
        if not path:
            return
        rows, header = self.csv_rows()
        _export_widget(self.plot, Path(path), 'Azimuth · convergence', rows, header)
