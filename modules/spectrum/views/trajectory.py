"""Selectable, theme-aware energy plot of optimization cycles (used by the Compass drawer)."""

from PySide6.QtCore import Qt, Signal, QPointF
from PySide6.QtGui import QPainter, QPen, QColor
from PySide6.QtWidgets import QWidget
from azimuth.i18n import tr


class EnergyPlot(QWidget):
    """Compact plot for the Compass drawer: energy of each cycle relative to the first,
    the lowest point at the bottom; the chosen cycle is orange. No axis captions: the numbers are
    in the table next to it."""

    selected = Signal(int)
    LEFT, RIGHT, TOP, BOTTOM = 12, 12, 22, 14

    def __init__(self):
        super().__init__()
        self.steps = ()
        self.current = -1
        self.setMinimumSize(160, 90)
        self.setToolTip(
            tr(
                'Энергия относительно первого доступного шага. Щёлкните по точке, чтобы выбрать шаг. Пропуски не соединяются.'
            )
        )

    def points(self):
        values = [(i, s.energy) for i, s in enumerate(self.steps) if s.energy is not None]
        if not values:
            return []
        ref = values[0][1]
        low = min(v - ref for _, v in values)
        high = max(v - ref for _, v in values)
        span = max(high - low, 1e-8)
        width = max(1, self.width() - self.LEFT - self.RIGHT)
        height = max(1, self.height() - self.TOP - self.BOTTOM)
        return [
            (
                i,
                QPointF(
                    self.LEFT + i * width / max(1, len(self.steps) - 1), self.TOP + (high - (v - ref)) / span * height
                ),
            )
            for i, v in values
        ]

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        text = self.palette().text().color()
        muted = QColor(text)
        muted.setAlpha(140)
        points = self.points()
        if not points:
            p.setPen(muted)
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, tr('Нет энергий шагов'))
            return
        grid = QColor(text)
        grid.setAlpha(40)
        p.setPen(QPen(grid, 1))
        p.drawLine(
            self.LEFT, self.height() - self.BOTTOM + 6, self.width() - self.RIGHT, self.height() - self.BOTTOM + 6
        )
        for (a, pa), (b, pb) in zip(points, points[1:]):
            if b == a + 1:
                p.setPen(QPen(QColor('#6ea2f0'), 2))
                p.drawLine(pa, pb)
        for i, point in points:
            p.setPen(QPen(QColor('#2a62b8'), 1.5))
            p.setBrush(QColor('#ffb454' if i == self.current else '#6ea2f0'))
            r = 5 if i == self.current else 3.5
            p.drawEllipse(point, r, r)
        if 0 <= self.current < len(self.steps):
            font = p.font()
            font.setPixelSize(11)
            p.setFont(font)
            p.setPen(muted)
            p.drawText(
                self.rect().adjusted(0, 2, -self.RIGHT, 0),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop,
                tr(f'Цикл {self.steps[self.current].cycle}'),
            )

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        points = self.points()
        if points:
            i, pt = min(points, key=lambda pair: (pair[1] - event.position()).manhattanLength())
            if (pt - event.position()).manhattanLength() < 24:
                self.selected.emit(i)


# the optimization browser moved to Compass (modules/compass/panels/trajectory_drawer.py);
# EnergyPlot stays here and is used by the drawer.
