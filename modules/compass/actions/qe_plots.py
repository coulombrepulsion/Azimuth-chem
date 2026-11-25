"""The plots of a band structure and of a density of states of Quantum ESPRESSO.

§1 PURPOSE
    After the steps «Зонная структура» or «Плотность состояний» of the panel of Quantum ESPRESSO (qe_window.QePanel):
    the bands E_n(k) − E0 along the path of qe_paths with the letters of its points, or the density of states against
    E − E0; E0 — the highest occupied level of the scf run for an insulator (the top of the valence band, 0 eV), the
    Fermi level for a metal. The data can be saved as a table (CSV) for another program.
§4 SPECIFICATION
    BandsPlot(): x, energies [[eV − E0] per k], ticks [(x, label)], breaks [index], span (lo, hi eV);
    DosPlot(): energies [eV − E0], dos [states/eV]; QePlotWindow(parent, title, plot, rows, header, name):
    plot, save_button; save(path=None) -> path (CSV: header and rows).
§7 TESTS
    tests/gui/test_gui_files.py::test_crystal_quantum_espresso_bands (the real bands and DOS of silicon).
"""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QDialog, QFileDialog, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from azimuth.i18n import tr
from azimuth.ui import action_button

LINE = '#2a62b8'
ZERO = '#c0504d'


class _Plot(QWidget):
    LEFT, RIGHT, TOP, BOTTOM = 48, 14, 12, 34

    def __init__(self):
        super().__init__()
        self.setMinimumSize(520, 380)

    def frame(self):
        return self.LEFT, self.width() - self.RIGHT, self.TOP, self.height() - self.BOTTOM

    @staticmethod
    def steps(lo, hi):
        """The step of the ticks: 1, 2 or 5 × 10ⁿ, about 5 to 12 of them — eV of the bands as before (1, 2, 5),
        and hundreds of cm⁻¹ of the phonons (5 for 280 cm⁻¹ made 56 labels run together)."""
        from math import floor, log10

        span = hi - lo
        if span <= 0:
            return 1.0
        if span <= 50:
            return 1.0 if span <= 10 else 2.0 if span <= 25 else 5.0
        raw = span / 8
        power = 10 ** floor(log10(raw))
        return next(m * power for m in (1, 2, 5, 10) if m * power >= raw)


class BandsPlot(_Plot):
    """Branches along the path of the zone: the electron bands (E − E₀, eV) or the phonon branches (axis set to
    «ν, см⁻¹», no line of the zero)."""

    def __init__(self):
        super().__init__()
        self.x, self.energies, self.ticks, self.breaks = [], [], [], []
        self.span = (-12.0, 8.0)
        self.axis = 'E − E₀, эВ'
        self.zero_line = True

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        ink = self.palette().text().color()
        left, right, top, bottom = self.frame()
        lo, hi = self.span
        xmax = self.x[-1] if self.x else 1.0

        def X(v):
            return left + (right - left) * v / (xmax or 1.0)

        def Y(e):
            return bottom - (bottom - top) * (e - lo) / (hi - lo)

        font = QFont(self.font())
        font.setPixelSize(11)
        p.setFont(font)
        p.setPen(QPen(ink, 1))
        p.drawRect(QRectF(left, top, right - left, bottom - top))
        step = self.steps(lo, hi)
        e = int(lo // step + 1) * step
        while e < hi:
            p.drawLine(QPointF(left - 4, Y(e)), QPointF(left, Y(e)))
            p.drawText(QRectF(0, Y(e) - 7, left - 6, 14), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, f'{e:g}')
            e += step
        p.save()
        p.translate(12, (top + bottom) / 2)
        p.rotate(-90)
        p.drawText(QRectF(-80, -10, 160, 14), Qt.AlignmentFlag.AlignCenter, tr(self.axis))
        p.restore()
        grey = QColor(ink)
        grey.setAlpha(90)
        for x, label in self.ticks:
            p.setPen(QPen(grey, 1))
            p.drawLine(QPointF(X(x), top), QPointF(X(x), bottom))
            p.setPen(QPen(ink, 1))
            p.drawText(QRectF(X(x) - 30, bottom + 6, 60, 16), Qt.AlignmentFlag.AlignCenter, label)
        p.setPen(QPen(QColor(ZERO), 1, Qt.PenStyle.DashLine))
        if self.zero_line and lo < 0 < hi:
            p.drawLine(QPointF(left, Y(0)), QPointF(right, Y(0)))
        p.setClipRect(QRectF(left, top, right - left, bottom - top))
        p.setPen(QPen(QColor(LINE), 1.4))
        count = min((len(e) for e in self.energies), default=0)
        starts = set(self.breaks)
        for n in range(count):
            path = QPainterPath()
            for k, (x, e) in enumerate(zip(self.x, self.energies)):
                point = QPointF(X(x), Y(e[n]))
                if k == 0 or k in starts:
                    path.moveTo(point)
                else:
                    path.lineTo(point)
            p.drawPath(path)
        p.end()


# the colours of the PDOS of the elements and of their s, p, d, f (Tableau 10, as crystal_packing.PALETTE)
PARTS = ('#e15759', '#59a14f', '#f28e2b', '#b07aa1', '#76b7b2', '#edc948', '#9c755f', '#ff9da7', '#4e79a7', '#bab0ac')


class DosPlot(_Plot):
    def __init__(self):
        super().__init__()
        self.energies, self.dos = [], []
        self.parts = []  # the PDOS — [(name, values on self.energies)], drawn in PARTS with a legend
        self.span = (-12.0, 8.0)
        self.label = 'DOS, состояний/эВ'
        self.axis = 'E − E₀, эВ'  # «ν, см⁻¹» for the phonons

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        ink = self.palette().text().color()
        left, right, top, bottom = self.frame()
        lo, hi = self.span
        shown = [d for e, d in zip(self.energies, self.dos) if lo <= e <= hi]
        for _, values in self.parts:
            shown += [d for e, d in zip(self.energies, values) if lo <= e <= hi]
        top_value = max(shown, default=1.0) * 1.08 or 1.0

        def X(e):
            return left + (right - left) * (e - lo) / (hi - lo)

        def Y(v):
            return bottom - (bottom - top) * v / top_value

        font = QFont(self.font())
        font.setPixelSize(11)
        p.setFont(font)
        p.setPen(QPen(ink, 1))
        p.drawRect(QRectF(left, top, right - left, bottom - top))
        step = self.steps(lo, hi)
        e = int(lo // step + 1) * step
        while e < hi:
            p.drawLine(QPointF(X(e), bottom), QPointF(X(e), bottom + 4))
            p.drawText(QRectF(X(e) - 20, bottom + 6, 40, 14), Qt.AlignmentFlag.AlignCenter, f'{e:g}')
            e += step
        p.drawText(QRectF(right - 120, bottom + 18, 120, 14), Qt.AlignmentFlag.AlignRight, tr(self.axis))
        p.save()
        p.translate(12, (top + bottom) / 2)
        p.rotate(-90)
        p.drawText(QRectF(-110, -10, 220, 14), Qt.AlignmentFlag.AlignCenter, tr(self.label))
        p.restore()
        p.setPen(QPen(QColor(ZERO), 1, Qt.PenStyle.DashLine))
        if lo < 0 < hi:
            p.drawLine(QPointF(X(0), top), QPointF(X(0), bottom))
        p.setClipRect(QRectF(left, top, right - left, bottom - top))
        path = QPainterPath()
        for k, (e, d) in enumerate(zip(self.energies, self.dos)):
            point = QPointF(X(e), Y(d))
            if k:
                path.lineTo(point)
            else:
                path.moveTo(point)
        p.setPen(QPen(QColor(LINE), 1.4))
        p.drawPath(path)
        for k, (name, values) in enumerate(self.parts):
            part = QPainterPath()
            for n, (e, d) in enumerate(zip(self.energies, values)):
                point = QPointF(X(e), Y(d))
                if n:
                    part.lineTo(point)
                else:
                    part.moveTo(point)
            p.setPen(QPen(QColor(PARTS[k % len(PARTS)]), 1.2))
            p.drawPath(part)
        if self.parts:
            p.setClipping(False)
            rows = [(tr('всего'), LINE)] + [(name, PARTS[k % len(PARTS)]) for k, (name, _) in enumerate(self.parts)]
            for k, (name, colour) in enumerate(rows):
                y = top + 10 + 16 * k
                p.setPen(QPen(QColor(colour), 2))
                p.drawLine(QPointF(right - 96, y), QPointF(right - 76, y))
                p.setPen(QPen(ink, 1))
                p.drawText(QRectF(right - 72, y - 7, 70, 14), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                           name)
        p.end()


class QePlotWindow(QDialog):
    def __init__(self, parent, title, plot, rows, header, name):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.plot, self.rows, self.header, self.name = plot, rows, header, name
        layout = QVBoxLayout(self)
        layout.addWidget(plot, 1)
        self.note = QLabel('')
        self.note.setWordWrap(True)
        self.note.setObjectName('subtitle')
        layout.addWidget(self.note)
        buttons = QHBoxLayout()
        self.save_button = action_button(tr('Сохранить данные…'), self.save, 'save')
        buttons.addWidget(self.save_button)
        buttons.addStretch(1)
        buttons.addWidget(action_button(tr('Закрыть'), self.reject, 'close'))
        layout.addLayout(buttons)
        self.resize(760, 560)

    def save(self, path=None):
        if not path:
            path, _ = QFileDialog.getSaveFileName(self, tr('Сохранить данные'), self.name, 'CSV (*.csv)')
        if not path:
            return None
        from azimuth.files import atomic_write

        lines = [','.join(self.header)] + [','.join(f'{v:.6g}' if isinstance(v, float) else str(v) for v in r) for r in self.rows]
        atomic_write(path, '\n'.join(lines) + '\n')
        return path
