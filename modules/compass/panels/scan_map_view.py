"""Compass: the map of a two-dimensional scan — ΔE in colour with isolines, the points, the valley.

A click on a point selects it in the panel of steps (☰): the model shows its geometry. The numbers come from
modules/spectrum/analysis/scan_map.py; the energy unit is that of «Настройки → Единицы».
"""

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPen
from PySide6.QtWidgets import QCheckBox, QDialog, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from azimuth.i18n import tr
from modules.spectrum.analysis import scan_map as sm

# low energy dark blue, through teal and green, to yellow (perceptually ordered, readable in both themes)
STOPS = ((0.0, (38, 52, 120)), (0.25, (40, 110, 160)), (0.5, (45, 160, 140)), (0.75, (150, 200, 80)),
         (1.0, (250, 225, 70)))
ACCENT = '#d97a16'


def colour(t):
    t = min(1.0, max(0.0, float(t)))
    for (a, ca), (b, cb) in zip(STOPS, STOPS[1:]):
        if t <= b:
            s = (t - a) / (b - a)
            return tuple(int(round(ca[k] + s * (cb[k] - ca[k]))) for k in range(3))
    return STOPS[-1][1]


class ScanMapView(QWidget):
    chosen = Signal(int)  # the index of the point in the scan

    LEFT, RIGHT, TOP, BOTTOM = 62, 86, 16, 46

    def __init__(self, parent=None):
        super().__init__(parent)
        self.grid = None
        self.factor = 627.509474
        self.unit = ''
        self.current = -1
        self.show_valley = True
        self.setMinimumSize(420, 340)
        self._image = None

    def set_scan(self, scan, factor, unit):
        self.grid = sm.grid(scan)
        self.factor, self.unit = factor, unit
        self._image = None
        self.update()

    def plot_rect(self):
        return QRectF(self.LEFT, self.TOP, max(10, self.width() - self.LEFT - self.RIGHT),
                      max(10, self.height() - self.TOP - self.BOTTOM))

    def to_screen(self, x, y):
        g, r = self.grid, self.plot_rect()
        sx = r.left() + (x - g.xs[0]) / (g.xs[-1] - g.xs[0]) * r.width()
        sy = r.bottom() - (y - g.ys[0]) / (g.ys[-1] - g.ys[0]) * r.height()
        return QPointF(sx, sy)

    def relative(self):
        g = self.grid
        return (g.energy - np.nanmin(g.energy)) * self.factor

    def image(self):
        if self._image is None:
            fx, fy, fz = sm.fine(self.grid.xs, self.grid.ys, self.relative(), 12)
            top = np.nanmax(fz) or 1.0
            img = QImage(len(fx), len(fy), QImage.Format.Format_RGB32)
            for i in range(len(fy)):
                for j in range(len(fx)):
                    v = fz[len(fy) - 1 - i, j]
                    r, gg, b = (128, 128, 128) if np.isnan(v) else colour(v / top)
                    img.setPixelColor(j, i, QColor(r, gg, b))
            self._image = (img, fx, fy, fz, top)
        return self._image

    def paintEvent(self, event):
        from azimuth.ui import frame_plot

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), self.palette().base())
        frame_plot(p, self)
        text = self.palette().text().color()
        if self.grid is None:
            p.setPen(text)
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, tr('Это не двумерный скан.'))
            return
        g, r = self.grid, self.plot_rect()
        img, fx, fy, fz, top = self.image()
        p.drawImage(r, img)
        p.setPen(QPen(QColor(255, 255, 255, 150), 0.8))
        for level in sm.levels(0.0, top, 10):
            for (x1, y1), (x2, y2) in sm.isolines(fx, fy, fz, level):
                p.drawLine(self.to_screen(x1, y1), self.to_screen(x2, y2))
        if self.show_valley:
            pen = QPen(QColor(255, 255, 255, 230), 1.6, Qt.PenStyle.DashLine)
            p.setPen(pen)
            path = [self.to_screen(x, y) for x, y, _ in sm.valley(g)]
            for a, b in zip(path, path[1:]):
                p.drawLine(a, b)
        low = sm.minimum(g)[2]
        for i, yv in enumerate(g.ys):
            for j, xv in enumerate(g.xs):
                k = int(g.index[i, j])
                if k < 0:
                    continue
                c = self.to_screen(xv, yv)
                p.setPen(QPen(QColor(20, 20, 20, 200), 1))
                p.setBrush(QColor(255, 255, 255, 220) if k != low else QColor(ACCENT))
                p.drawEllipse(c, 3.2, 3.2)
                if k == self.current:
                    p.setBrush(Qt.BrushStyle.NoBrush)
                    p.setPen(QPen(QColor(ACCENT), 2.4))
                    p.drawEllipse(c, 8, 8)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(text)
        metrics = p.fontMetrics()
        for xv in g.xs:  # ticks at the scanned values
            c = self.to_screen(xv, g.ys[0])
            label = f'{xv:.2f}' if g.labels[0].endswith('Å') else f'{xv:.0f}'
            p.drawText(QPointF(c.x() - metrics.horizontalAdvance(label) / 2, r.bottom() + 15), label)
        for yv in g.ys:
            c = self.to_screen(g.xs[0], yv)
            label = f'{yv:.2f}' if g.labels[1].endswith('Å') else f'{yv:.0f}'
            p.drawText(QPointF(r.left() - 6 - metrics.horizontalAdvance(label), c.y() + 4), label)
        p.drawText(QPointF(r.center().x() - metrics.horizontalAdvance(g.labels[0]) / 2, self.height() - 8), g.labels[0])
        p.save()
        p.translate(14, r.center().y() + metrics.horizontalAdvance(g.labels[1]) / 2)
        p.rotate(-90)
        p.drawText(QPointF(0, 0), g.labels[1])
        p.restore()
        bar = QRectF(r.right() + 18, r.top(), 14, r.height())  # the colour bar, ΔE
        for k in range(int(bar.height())):
            rr, gg, bb = colour(1.0 - k / bar.height())
            p.setPen(QColor(rr, gg, bb))
            p.drawLine(QPointF(bar.left(), bar.top() + k), QPointF(bar.right(), bar.top() + k))
        p.setPen(text)
        for value, y in ((top, bar.top() + 4), (0.0, bar.bottom())):
            p.drawText(QPointF(bar.right() + 4, y), f'{value:.1f}')
        p.drawText(QPointF(bar.left() - 4, bar.bottom() + 18), 'ΔE, ' + self.unit)

    def mousePressEvent(self, event):
        if self.grid is None or not self.plot_rect().contains(event.position()):
            return
        g, r = self.grid, self.plot_rect()
        x = g.xs[0] + (event.position().x() - r.left()) / r.width() * (g.xs[-1] - g.xs[0])
        y = g.ys[0] + (r.bottom() - event.position().y()) / r.height() * (g.ys[-1] - g.ys[0])
        k = sm.nearest(g, x, y, g.xs[-1] - g.xs[0], g.ys[-1] - g.ys[0])
        if k >= 0:
            self.current = k
            self.update()
            self.chosen.emit(k)


class ScanMapDialog(QDialog):
    """The map in a window of its own beside Compass; follows the step chosen in the panel."""

    chosen = Signal(int)

    def __init__(self, scan, factor, unit, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr('Карта скана'))
        column = QVBoxLayout(self)
        self.view = ScanMapView(self)
        self.view.set_scan(scan, factor, unit)
        column.addWidget(self.view, 1)
        row = QHBoxLayout()
        self.valley = QCheckBox(tr('Долина'))
        self.valley.setToolTip(tr('Для каждого значения первой координаты — точка с наименьшей энергией по второй'))
        self.valley.setChecked(True)
        self.valley.toggled.connect(self._valley)
        row.addWidget(self.valley)
        self.note = QLabel(tr('Щелчок по точке — её геометрия на модели; оранжевая точка — минимум, изолинии — равные ΔE.'))
        self.note.setWordWrap(True)
        row.addWidget(self.note, 1)
        column.addLayout(row)
        self.view.chosen.connect(self.chosen)
        self.resize(620, 520)

    def _valley(self, on):
        self.view.show_valley = bool(on)
        self.view.update()

    def show_point(self, index):
        self.view.current = index
        self.view.update()
