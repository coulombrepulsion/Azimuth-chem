"""The plots of a band structure and of a density of states of Quantum ESPRESSO.

§1 PURPOSE
    After the steps «Зонная структура» or «Плотность состояний» of the panel of Quantum ESPRESSO (qe_window.QePanel):
    the bands E_n(k) − E0 along the path of qe_paths with the letters of its points, or the density of states against
    E − E0; E0 — the highest occupied level of the scf run for an insulator (the top of the valence band, 0 eV), the
    Fermi level for a metal. The data can be saved as a table (CSV) for another program.
§4 SPECIFICATION
    BandsPlot(): x, energies [[eV − E0] per k], ticks [(x, label)], breaks [index], span (lo, hi eV), marks [(x, eV −
    E0, 'v' | 'c')] — the edges of the gap as dots, caption — a line at the top of the frame (band_gap.marks, band_gap.text);
    SeriesPlot(): labels, values [meV per atom], tolerance, axis — a convergence series (convergence.py);
    EosPlot(): volumes [Å³], energies [meV from E₀ of the fit], curve [(V, meV)], minimum V₀ — the series of volumes
    and its Birch–Murnaghan fit;
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
        self.marks = []  # the edges of the gap: [(x, E − E₀, 'v' | 'c')] — the top of the valence band, the bottom of
        # the conduction band (band_gap.gap)
        self.caption = ''  # a line inside the frame, at its top (the gap, where the plot has no note under it)
        self.xrange = None  # (x from, x to) of the path shown; None — all of it
        self.model = []  # a model beside the bands, dashed: a row of energies for every point of x

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        ink = self.palette().text().color()
        left, right, top, bottom = self.frame()
        lo, hi = self.span
        xmin, xmax = self.xrange or (0.0, self.x[-1] if self.x else 1.0)

        def X(v):
            return left + (right - left) * (v - xmin) / ((xmax - xmin) or 1.0)

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
            if not xmin - 1e-9 <= x <= xmax + 1e-9:
                continue
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
        if self.model and len(self.model) == len(self.x):
            p.setPen(QPen(QColor('#2e8b57'), 1.3, Qt.PenStyle.DashLine))
            for n in range(len(self.model[0])):
                path = QPainterPath()
                for k, (x, e) in enumerate(zip(self.x, self.model)):
                    point = QPointF(X(x), Y(e[n]))
                    if k == 0 or k in starts:
                        path.moveTo(point)
                    else:
                        path.lineTo(point)
                p.drawPath(path)
        for x, e, edge in self.marks:  # the edges of the gap on the bands
            colour = QColor(ZERO if edge == 'v' else '#2e8b57')
            p.setPen(QPen(colour.darker(130), 1))
            p.setBrush(colour)
            p.drawEllipse(QPointF(X(x), Y(e)), 4.5, 4.5)
        p.setClipping(False)
        if self.caption:
            box = QRectF(left + 6, top + 4, right - left - 12, 34)
            back = QColor(self.palette().base().color())
            back.setAlpha(215)
            p.fillRect(box, back)
            p.setPen(QPen(ink, 1))
            p.drawText(box.adjusted(4, 0, -4, 0), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                       | Qt.TextFlag.TextWordWrap, self.caption)
        p.end()


class SeriesPlot(_Plot):
    """A convergence series: ΔE per atom (meV, from the last point) against the values of the parameter, which stand
    at equal steps under the axis; the band of the tolerance about zero."""

    LEFT = 64

    def __init__(self):
        super().__init__()
        self.labels, self.values = [], []
        self.tolerance = 1.0  # meV per atom
        self.axis = ''
        self.marked = []  # the points drawn green: the grids of a layer that hold the corner K

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        ink = self.palette().text().color()
        left, right, top, bottom = self.frame()
        if not self.values:
            p.end()
            return
        lo, hi = min(self.values + [-self.tolerance]), max(self.values + [self.tolerance])
        pad = 0.08 * (hi - lo or 1.0)
        lo, hi = lo - pad, hi + pad
        count = len(self.values)

        def X(k):
            return left + (right - left) * (k + 0.5) / count

        def Y(v):
            return bottom - (bottom - top) * (v - lo) / (hi - lo)

        font = QFont(self.font())
        font.setPixelSize(11)
        p.setFont(font)
        p.setPen(QPen(ink, 1))
        p.drawRect(QRectF(left, top, right - left, bottom - top))
        from math import floor, log10

        raw = (hi - lo) / 6
        power = 10 ** floor(log10(raw))
        step = next(m * power for m in (1, 2, 5, 10) if m * power >= raw)
        v = int(lo // step + 1) * step
        while v < hi:
            p.drawLine(QPointF(left - 4, Y(v)), QPointF(left, Y(v)))
            p.drawText(QRectF(0, Y(v) - 7, left - 6, 14), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, f'{v:g}')
            v += step
        for k, text in enumerate(self.labels):
            p.drawLine(QPointF(X(k), bottom), QPointF(X(k), bottom + 4))
            p.drawText(QRectF(X(k) - 45, bottom + 6, 90, 14), Qt.AlignmentFlag.AlignCenter, text)
        p.drawText(QRectF(right - 200, bottom + 18, 200, 14), Qt.AlignmentFlag.AlignRight, tr(self.axis))
        p.save()
        p.translate(12, (top + bottom) / 2)
        p.rotate(-90)
        p.drawText(QRectF(-110, -10, 220, 14), Qt.AlignmentFlag.AlignCenter, tr('ΔE, мэВ на атом'))
        p.restore()
        p.setClipRect(QRectF(left, top, right - left, bottom - top))
        band = QColor('#2e8b57')
        band.setAlpha(45)
        p.fillRect(QRectF(left, Y(self.tolerance), right - left, Y(-self.tolerance) - Y(self.tolerance)), band)
        p.setPen(QPen(QColor(ZERO), 1, Qt.PenStyle.DashLine))
        p.drawLine(QPointF(left, Y(0)), QPointF(right, Y(0)))
        path = QPainterPath()
        for k, value in enumerate(self.values):
            point = QPointF(X(k), Y(value))
            if k:
                path.lineTo(point)
            else:
                path.moveTo(point)
        p.setPen(QPen(QColor(LINE), 1.4))
        p.drawPath(path)
        p.setPen(QPen(QColor(LINE).darker(140), 1))
        p.setBrush(QColor(LINE))
        for k, value in enumerate(self.values):
            colour = QColor('#2e8b57' if k < len(self.marked) and self.marked[k] else LINE)
            p.setPen(QPen(colour.darker(140), 1))
            p.setBrush(colour)
            p.drawEllipse(QPointF(X(k), Y(value)), 4.0, 4.0)
        p.end()


class EosPlot(_Plot):
    """E(V) of a series of volumes: the points computed and the curve of the fit (equation_of_state.Fit)."""

    LEFT = 64

    def __init__(self):
        super().__init__()
        self.volumes, self.energies = [], []  # Å³, meV from the minimum of the fit
        self.curve = []  # [(V, meV)] of the fit
        self.minimum = None  # V₀

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        ink = self.palette().text().color()
        left, right, top, bottom = self.frame()
        xs = self.volumes + [v for v, _ in self.curve]
        ys = self.energies + [e for _, e in self.curve]
        if not xs:
            p.end()
            return
        x0, x1 = min(xs), max(xs)
        pad = 0.04 * (x1 - x0 or 1.0)
        x0, x1 = x0 - pad, x1 + pad
        y0, y1 = min(0.0, min(ys)), max(ys) * 1.08 or 1.0

        def X(v):
            return left + (right - left) * (v - x0) / (x1 - x0)

        def Y(e):
            return bottom - (bottom - top) * (e - y0) / (y1 - y0)

        font = QFont(self.font())
        font.setPixelSize(11)
        p.setFont(font)
        p.setPen(QPen(ink, 1))
        p.drawRect(QRectF(left, top, right - left, bottom - top))
        for lo, hi, place in ((x0, x1, 'x'), (y0, y1, 'y')):
            step = self.steps(lo, hi)
            if (hi - lo) / step > 12 or (hi - lo) / step < 3:
                from math import floor, log10

                raw = (hi - lo) / 6
                power = 10 ** floor(log10(raw))
                step = next(m * power for m in (1, 2, 5, 10) if m * power >= raw)
            v = int(lo // step + 1) * step
            while v < hi:
                if place == 'x':
                    p.drawLine(QPointF(X(v), bottom), QPointF(X(v), bottom + 4))
                    p.drawText(QRectF(X(v) - 30, bottom + 6, 60, 14), Qt.AlignmentFlag.AlignCenter, f'{v:g}')
                else:
                    p.drawLine(QPointF(left - 4, Y(v)), QPointF(left, Y(v)))
                    p.drawText(QRectF(0, Y(v) - 7, left - 6, 14), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, f'{v:g}')
                v += step
        p.drawText(QRectF(right - 160, bottom + 18, 160, 14), Qt.AlignmentFlag.AlignRight, tr('V, Å³ на ячейку расчёта'))
        p.save()
        p.translate(12, (top + bottom) / 2)
        p.rotate(-90)
        p.drawText(QRectF(-110, -10, 220, 14), Qt.AlignmentFlag.AlignCenter, tr('E − E₀, мэВ'))
        p.restore()
        p.setClipRect(QRectF(left, top, right - left, bottom - top))
        if self.minimum is not None:
            p.setPen(QPen(QColor(ZERO), 1, Qt.PenStyle.DashLine))
            p.drawLine(QPointF(X(self.minimum), top), QPointF(X(self.minimum), bottom))
        path = QPainterPath()
        for k, (v, e) in enumerate(self.curve):
            point = QPointF(X(v), Y(e))
            if k:
                path.lineTo(point)
            else:
                path.moveTo(point)
        p.setPen(QPen(QColor(LINE), 1.4))
        p.drawPath(path)
        p.setPen(QPen(QColor(LINE).darker(140), 1))
        p.setBrush(QColor(LINE))
        for v, e in zip(self.volumes, self.energies):
            p.drawEllipse(QPointF(X(v), Y(e)), 4.0, 4.0)
        p.end()


class CurvesPlot(_Plot):
    """Several curves with their points on common axes: series [(name, colour, points [(x, y)], line [(x, y)])]."""

    LEFT = 64

    def __init__(self):
        super().__init__()
        self.series = []
        self.x_axis, self.y_axis = '', ''

    def paintEvent(self, event):
        from math import floor, log10

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        ink = self.palette().text().color()
        left, right, top, bottom = self.frame()
        xs = [x for _, _, points, line in self.series for x, _ in points + line]
        ys = [y for _, _, points, line in self.series for _, y in points + line]
        if not xs:
            p.end()
            return
        x0, x1 = min(xs), max(xs)
        y0, y1 = min(ys), max(ys)
        pad_x, pad_y = 0.04 * (x1 - x0 or 1.0), 0.06 * (y1 - y0 or 1.0)
        x0, x1, y0, y1 = x0 - pad_x, x1 + pad_x, y0 - pad_y, y1 + pad_y

        def X(v):
            return left + (right - left) * (v - x0) / (x1 - x0)

        def Y(v):
            return bottom - (bottom - top) * (v - y0) / (y1 - y0)

        font = QFont(self.font())
        font.setPixelSize(11)
        p.setFont(font)
        p.setPen(QPen(ink, 1))
        p.drawRect(QRectF(left, top, right - left, bottom - top))
        for lo, hi, place in ((x0, x1, 'x'), (y0, y1, 'y')):
            raw = (hi - lo) / 6
            power = 10 ** floor(log10(raw))
            step = next(m * power for m in (1, 2, 5, 10) if m * power >= raw)
            v = int(lo // step + 1) * step
            while v < hi:
                if place == 'x':
                    p.drawLine(QPointF(X(v), bottom), QPointF(X(v), bottom + 4))
                    p.drawText(QRectF(X(v) - 30, bottom + 6, 60, 14), Qt.AlignmentFlag.AlignCenter, f'{v:g}')
                else:
                    p.drawLine(QPointF(left - 4, Y(v)), QPointF(left, Y(v)))
                    p.drawText(QRectF(0, Y(v) - 7, left - 6, 14), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, f'{v:g}')
                v += step
        p.drawText(QRectF(right - 200, bottom + 18, 200, 14), Qt.AlignmentFlag.AlignRight, tr(self.x_axis))
        p.save()
        p.translate(12, (top + bottom) / 2)
        p.rotate(-90)
        p.drawText(QRectF(-110, -10, 220, 14), Qt.AlignmentFlag.AlignCenter, tr(self.y_axis))
        p.restore()
        for k, (name, colour, _, _) in enumerate(self.series):  # the legend, inside the frame
            y = top + 14 + 16 * k
            p.setPen(QPen(QColor(colour), 2))
            p.drawLine(QPointF(left + 10, y), QPointF(left + 30, y))
            p.setPen(QPen(ink, 1))
            p.drawText(QRectF(left + 36, y - 7, right - left - 46, 14), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, name)
        p.setClipRect(QRectF(left, top, right - left, bottom - top))
        for _, colour, points, line in self.series:
            path = QPainterPath()
            for k, (x, y) in enumerate(line):
                point = QPointF(X(x), Y(y))
                if k:
                    path.lineTo(point)
                else:
                    path.moveTo(point)
            p.setPen(QPen(QColor(colour), 1.4))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(path)
            p.setPen(QPen(QColor(colour).darker(140), 1))
            p.setBrush(QColor(colour))
            for x, y in points:
                p.drawEllipse(QPointF(X(x), Y(y)), 3.6, 3.6)
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
