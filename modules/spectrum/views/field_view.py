"""Spectrum: «Карты и профили» — a function of the wavefunction in the plane of three atoms (a colour map with contours)
and along the line through two atoms (a profile), computed by Multiwfn.

§1 PURPOSE
    The two-dimensional pictures of the density analysis: ρ with Bader's contours, ∇²ρ, ELF, ESP… in the plane of a
    molecule; ρ along a bond with its minimum — the bond critical point. Everything a map or a profile shows is also
    written into the folder of the calculation: the data and the extrema as CSV
    (modules/spectrum/wavefunction/field_tables.py).
§2 ALGORITHM
    multiwfn.run_plane / run_line; MapView paints the values as a QImage (ρ, |∇ρ|, G — on a log scale; signed functions
    — blue/white/red around 0, clipped at the 2nd and 98th percentiles; the rest — a sequential scale) with contour
    lines (density.contours: Bader's levels for ρ and ∇²ρ, otherwise 12 levels over the colour range), the atoms within
    NEAR Å of the plane with their labels. LineView: value against the position (log scale for the positive ones on
    request), the atoms near the line as vertical marks, the extrema as dots. Extrema: of the map — a point not below
    (not above) its eight neighbours; of the profile — a point not below (not above) both neighbours.
§4 SPECIFICATION
    FieldPanel(source, geometry, parent, topology=None): source() -> (program, wavefunction path, cores) | None;
    topology() -> Topology | None (its critical points and bond paths near the plane are drawn on the map);
    geometry() -> Molecule
    | None; build_map() -> dict | None; build_line() -> dict | None; map_view, line_view; written (the last CSV paths).
    map_extrema(values, points) / line_extrema(x, values, points) -> [dict].
§7 TESTS
    tests/spectrum/test_field_tables.py (extrema of the recorded map and profile),
    tests/test_gui.py::test_maps_and_profiles.
"""

from pathlib import Path

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from modules.spectrum.views.plot_zoom import Zoomable
from modules.spectrum.wavefunction.field_tables import line_extrema, map_extrema
from azimuth.i18n import tr

CP_COLOURS = {'bond': '#2e9e5b', 'ring': '#e0882c', 'cage': '#8e5bd0'}  # as on the model of Compass
class AtomBox(QSpinBox):
    """An atom number shown with its element («H1»); typed as «H1» or «1» (an element that is not that atom's is
    refused)."""

    def __init__(self, *args):
        super().__init__(*args)
        self.symbols = None
        # «H1» in the middle of its field, as the other number fields of the program
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def set_symbols(self, symbols):
        self.symbols = list(symbols) if symbols else None
        self.lineEdit().setText(self.textFromValue(self.value()))
        self.updateGeometry()

    def textFromValue(self, value):
        symbols = getattr(self, 'symbols', None)
        return f'{symbols[value - 1]}{value}' if symbols and 1 <= value <= len(symbols) else str(value)

    def valueFromText(self, text):
        import re

        found = re.search(r'\d+', text)
        return int(found.group()) if found else self.value()

    def validate(self, text, pos):
        import re

        from PySide6.QtGui import QValidator

        found = re.fullmatch(r'\s*([A-Z][a-z]?)?\s*(\d*)\s*', text)
        if not found:
            return QValidator.State.Invalid, text, pos
        if not found.group(2):
            return QValidator.State.Intermediate, text, pos
        value = int(found.group(2))
        if not self.minimum() <= value <= self.maximum():
            return QValidator.State.Intermediate, text, pos
        symbols = getattr(self, 'symbols', None)
        if found.group(1) and symbols and symbols[value - 1] != found.group(1):
            return QValidator.State.Intermediate, text, pos
        return QValidator.State.Acceptable, text, pos


NEAR = 0.6  # Å: atoms nearer than this to the plane (or the line) are drawn on the map (the profile)
CHOICES = (
    ('rho', 'Электронная плотность ρ'), ('laplacian', 'Лапласиан ∇²ρ'), ('gradient', 'Градиент |∇ρ|'),
    ('elf', 'ELF'), ('lol', 'LOL'), ('esp', 'Электростатический потенциал'), ('alie', 'ALIE'),
    ('rdg', 'RDG'), ('sign', 'sign(λ₂)ρ'), ('entropy', 'Информационная энтропия'), ('g', 'G(r)'), ('k', 'K(r)'),
    ('spin', 'Спиновая плотность'),
)
SIGNED = {'laplacian', 'esp', 'sign', 'k', 'spin'}
LOGARITHMIC = {'rho', 'gradient', 'g'}


def _colour(t, signed):
    """t in 0…1 → (r, g, b) 0…255: signed — blue, white, red; else a dark-blue → teal → yellow scale."""
    t = np.clip(t, 0.0, 1.0)
    if signed:
        blue, white, red = np.array((44, 100, 200)), np.array((255, 255, 255)), np.array((215, 48, 47))
        out = np.where(t[..., None] < 0.5, blue + (white - blue) * (2 * t[..., None]), white + (red - white) * (2 * t[..., None] - 1))
    else:
        stops = np.array([(32, 33, 92), (35, 98, 160), (32, 160, 150), (150, 205, 80), (250, 230, 60)], float)
        s = t * (len(stops) - 1)
        k = np.minimum(np.floor(s).astype(int), len(stops) - 2)
        f = (s - k)[..., None]
        out = stops[k] + (stops[k + 1] - stops[k]) * f
    return out.astype(np.uint8)


def scaled(values, name):
    """(scaled values for the colours and contours, low, high, logarithmic?)."""
    v = np.asarray(values, float)
    if name in LOGARITHMIC:
        w = np.log10(np.maximum(v, 1e-6))
        return w, float(np.percentile(w, 1)), float(np.percentile(w, 99.5)), True
    if name in SIGNED:
        top = float(np.percentile(np.abs(v), 98)) or 1.0
        return v, -top, top, False
    return v, float(np.percentile(v, 1)), float(np.percentile(v, 99)), False


class MapView(Zoomable, QWidget):
    """Moved and zoomed (plot_zoom.Zoomable) — the arrows and the scale of its pad, the wheel, a drag."""

    def __init__(self):
        super().__init__()
        self.data = None  # (plane dict, name, atoms [(u, v, label)], extrema)
        self.setMinimumSize(420, 420)
        self._zoom_init()

    TOP, BOTTOM, SIDE = 26, 8, 10  # px: the scale and the size of the map over it; the margins

    def map_rect(self):
        """The rectangle of the map — as large as the
        field lets it be, its own proportions kept (the region of Multiwfn is the projection of the molecule and 4.5
        Bohr round it: seldom a square), in the middle of the field; it was drawn in a square at its top left."""
        width = max(1.0, self.width() - 2 * self.SIDE)
        height = max(1.0, self.height() - self.TOP - self.BOTTOM)
        if self.data is None:
            side = min(width, height)
            return QRectF((self.width() - side) / 2, self.TOP, side, side)
        u, v = self.data[0]['u'], self.data[0]['v']
        span_u, span_v = max(float(u[-1] - u[0]), 1e-9), max(float(v[-1] - v[0]), 1e-9)
        scale = min(width / span_u, height / span_v)  # px per Å
        w, h = span_u * scale, span_v * scale
        return QRectF((self.width() - w) / 2, self.TOP + (height - h) / 2, w, h)

    def plot_rect(self):
        if self.data is None:
            return None
        return self.map_rect()

    def set(self, plane, name, atoms, extrema, points=(), paths=()):
        """Points [(u, v, kind)] — the critical points near the plane, paths [(n, 2) (u, v)] — their bond paths."""
        self.data = (plane, name, atoms, extrema)
        self.points, self.paths = list(points), list(paths)
        self.follow_data()
        self.update()

    def paintEvent(self, event):
        from modules.spectrum.analysis import density

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pal = self.palette()
        base, ink = pal.base().color(), pal.text().color()
        p.fillRect(self.rect(), base)
        from azimuth.ui import frame_plot  # the border of the plot (light theme)

        frame_plot(p, self)
        if self.data is None:
            p.setPen(ink)
            p.drawText(self.rect().adjusted(16, 0, -16, 0), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                       tr('Выберите функцию и три атома, затем «Построить карту»'))  # wrapped in a narrow column
            return
        plane, name, atoms, extrema = self.data
        u, v, values = plane['u'], plane['v'], plane['values']
        w, low, high, log = scaled(values, name)
        # the scale and the size of the map over it, not under it
        # (a panel lower than the map cut them away)
        rect = self.map_rect()
        x0, y0, mw, mh = rect.x(), rect.y(), rect.width(), rect.height()
        span_u, span_v = u[-1] - u[0], v[-1] - v[0]
        span = span_u
        # the part shown (plot_zoom); shares of the map along each of its axes (v from the top)
        wx0, wx1, wy0, wy1 = self.window

        def at(a, b):
            return QPointF(x0 + ((a - u[0]) / span_u - wx0) / (wx1 - wx0) * mw,
                           y0 + ((v[-1] - b) / span_v - wy0) / (wy1 - wy0) * mh)

        if self.zoomed():  # the whole map lets the labels of the atoms near its edge out; a part of it is cut by it
            p.save()
            p.setClipRect(rect)

        t = (w - low) / max(high - low, 1e-12)
        rgb = _colour(t.T[::-1], name in SIGNED)  # rows: v from the top
        image = QImage(np.ascontiguousarray(rgb).data, rgb.shape[1], rgb.shape[0], 3 * rgb.shape[1],
                       QImage.Format.Format_RGB888).copy()
        p.drawImage(QRectF(at(u[0], v[-1]), at(u[-1], v[0])), image)
        if name == 'rho':
            levels = [(level, QPen(QColor(20, 20, 20, 150), 0.8)) for level in density.BADER]
            field = values
        elif name == 'laplacian':
            levels = [(lv, QPen(QColor(20, 20, 20, 150), 0.8)) for lv in density.BADER]
            levels += [(-lv, QPen(QColor(20, 20, 20, 150), 0.8, Qt.PenStyle.DashLine)) for lv in density.BADER]
            field = values
        else:
            levels = [(low + (high - low) * k / 13, QPen(QColor(20, 20, 20, 120), 0.7)) for k in range(1, 13)]
            field = w
        for level, pen in levels:
            segments = density.contours(np.asarray(field).T, u, v, level)  # values[row = v, column = u]
            if len(segments):
                p.setPen(pen)
                for (ax, ay), (bx, by) in segments:
                    p.drawLine(at(ax, ay), at(bx, by))
        p.setPen(QPen(QColor(20, 20, 20, 170), 1.3))  # the bond paths and the critical points of QTAIM
        for path in getattr(self, 'paths', ()):
            for (ax, ay), (bx, by) in zip(path[:-1], path[1:]):
                p.drawLine(at(ax, ay), at(bx, by))
        for a, b, kind in getattr(self, 'points', ()):
            c = at(a, b)
            p.setPen(QPen(QColor('#ffffff'), 1.2))
            p.setBrush(QColor(CP_COLOURS.get(kind, '#888888')))
            p.drawPolygon([QPointF(c.x(), c.y() - 5), QPointF(c.x() + 5, c.y()), QPointF(c.x(), c.y() + 5),
                           QPointF(c.x() - 5, c.y())])
        for e in extrema:
            i, j = e['ij']
            c = at(u[i], v[j])
            p.setPen(QPen(QColor('#ffffff'), 1.2))
            p.setBrush(QColor('#d7302f' if e['kind'] == 'max' else '#2c64c8'))
            p.drawRect(QRectF(c.x() - 3, c.y() - 3, 6, 6))
        font = QFont(self.font())
        font.setPixelSize(12)
        font.setBold(True)
        p.setFont(font)
        from PySide6.QtGui import QPainterPath

        for a, b, label in atoms:
            c = at(a, b)
            p.setPen(QPen(QColor('#ffffff'), 1.5))
            p.setBrush(QColor('#1f2a36'))
            p.drawEllipse(c, 4.0, 4.0)
            # the label on a light halo — read over the dark and the light parts of the map alike
            path = QPainterPath()
            path.addText(QPointF(c.x() + 6, c.y() - 6), font, label)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.strokePath(path, QPen(QColor(255, 255, 255, 215), 3.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                                    Qt.PenJoinStyle.RoundJoin))
            p.fillPath(path, QColor('#1f2a36'))
        if self.zoomed():
            p.restore()
        p.setPen(ink)
        small = QFont(self.font())
        small.setPixelSize(11)
        p.setFont(small)
        scale = (tr('lg ') if log else '') + f'{low:.3g} … {high:.3g}'
        p.drawText(QRectF(x0, y0 - 22, mw, 18), Qt.AlignmentFlag.AlignLeft, scale)
        shown = span * (wx1 - wx0)  # the width of the part shown
        p.drawText(QRectF(x0, y0 - 22, mw, 18), Qt.AlignmentFlag.AlignRight,
                   f'{shown:.2f} Å' if shown < 2 else f'{shown:.1f} Å')
        p.end()


class LineView(Zoomable, QWidget):
    """Moved and zoomed (plot_zoom.Zoomable); Shift with the wheel — the values only, Ctrl/⌘ — the positions only."""

    LEFT, RIGHT, TOP, BOTTOM = 64, 18, 14, 44
    Y_UP = True

    def __init__(self):
        super().__init__()
        self.data = None  # (line dict, name, atoms [(x, label)], extrema, log)
        self.setMinimumSize(420, 320)
        self._zoom_init()

    def plot_rect(self):
        if self.data is None:
            return None
        return QRectF(self.LEFT, self.TOP, self.width() - self.LEFT - self.RIGHT,
                      self.height() - self.TOP - self.BOTTOM)

    def set(self, line, name, atoms, extrema, log):
        self.data = (line, name, atoms, extrema, log)
        self.follow_data()
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pal = self.palette()
        base, ink = pal.base().color(), pal.text().color()
        p.fillRect(self.rect(), base)
        from azimuth.ui import frame_plot  # the border of the plot (light theme)

        frame_plot(p, self)
        if self.data is None:
            p.setPen(ink)
            p.drawText(self.rect().adjusted(16, 0, -16, 0), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                       tr('Выберите функцию и два атома, затем «Построить профиль»'))  # wrapped in a narrow column
            return
        line, name, atoms, extrema, log = self.data
        x, y = line['x'], np.asarray(line['values'], float)
        if log:
            y = np.log10(np.maximum(y, 1e-6))
        low, high = float(np.min(y)), float(np.max(y))
        if high - low < 1e-12:
            high = low + 1.0
        w, h = self.width() - self.LEFT - self.RIGHT, self.height() - self.TOP - self.BOTTOM
        # the part shown (plot_zoom) — the positions xa…xb, the values low…high
        wx0, wx1, wy0, wy1 = self.window
        whole_x, whole_y = x[-1] - x[0], high - low
        xa, xb = x[0] + wx0 * whole_x, x[0] + wx1 * whole_x
        low, high = low + wy0 * whole_y, low + wy1 * whole_y

        def at(a, b):
            return QPointF(self.LEFT + (a - xa) / (xb - xa) * w, self.TOP + (1 - (b - low) / (high - low)) * h)

        # round values on both axes, a mark and a faint line of
        # the grid at each (about one per 50 px of the values and per 80 px of the positions)
        from modules.spectrum.views.convergence_view import nice_ticks

        y_ticks = [t for t in nice_ticks(low, high, max(3, int(h // 50))) if low <= t <= high]
        x_ticks = [t for t in nice_ticks(xa, xb, max(3, int(w // 80))) if xa <= t <= xb]
        grid = QColor(ink)
        grid.setAlpha(28)
        p.setPen(QPen(grid, 1))
        for t in y_ticks:
            y_at = at(xa, t).y()
            p.drawLine(QPointF(self.LEFT, y_at), QPointF(self.LEFT + w, y_at))
        for t in x_ticks:
            x_at = at(t, low).x()
            p.drawLine(QPointF(x_at, self.TOP), QPointF(x_at, self.TOP + h))
        p.setPen(QPen(ink, 1))
        p.drawRect(QRectF(self.LEFT, self.TOP, w, h))
        for t in y_ticks:
            y_at = at(xa, t).y()
            p.drawLine(QPointF(self.LEFT - 4, y_at), QPointF(self.LEFT, y_at))
        for t in x_ticks:
            x_at = at(t, low).x()
            p.drawLine(QPointF(x_at, self.TOP + h), QPointF(x_at, self.TOP + h + 4))
        p.save()
        p.setClipRect(QRectF(self.LEFT, self.TOP, w, h))
        faint = QColor(ink)
        faint.setAlpha(90)
        for a, label in atoms:
            top, bottom = at(a, high), at(a, low)
            p.setPen(QPen(faint, 1, Qt.PenStyle.DashLine))
            p.drawLine(top, bottom)
            p.setPen(ink)
            p.drawText(QPointF(top.x() + 3, self.TOP + 12), label)
        p.setPen(QPen(QColor('#2a62b8'), 2))
        step = max(1, len(x) // 1500)
        points = [at(a, b) for a, b in zip(x[::step], y[::step])]
        for a, b in zip(points[:-1], points[1:]):
            p.drawLine(a, b)
        for e in extrema:
            value = np.log10(max(e['value'], 1e-6)) if log else e['value']
            c = at(e['x'], value)
            p.setPen(QPen(QColor('#ffffff'), 1))
            p.setBrush(QColor('#d7302f' if e['kind'] == 'max' else '#2c64c8'))
            p.drawEllipse(c, 4, 4)
        p.restore()
        small = QFont(self.font())
        small.setPixelSize(11)
        p.setFont(small)
        p.setPen(ink)
        for t in y_ticks:
            y_at = at(xa, t).y()
            p.drawText(QRectF(0, y_at - 7, self.LEFT - 8, 14), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                       f'{t:.4g}')
        for t in x_ticks:
            x_at = at(t, low).x()
            p.drawText(QRectF(x_at - 30, self.TOP + h + 5, 60, 14), Qt.AlignmentFlag.AlignHCenter, f'{t:.4g}')
        p.drawText(QRectF(self.LEFT, self.height() - 22, w, 16), Qt.AlignmentFlag.AlignHCenter,
                   tr('расстояние вдоль линии, Å') + ('   ·   ' + tr('значение — lg') if log else ''))
        p.end()


class SideBySide(QSplitter):
    """The map and the profile side by
    side, a splitter between them; the one built last is «current» — «Сохранить картинку…» saves it."""

    def __init__(self):
        super().__init__(Qt.Orientation.Horizontal)
        self.setChildrenCollapsible(False)
        self.setHandleWidth(17)
        self._current = None

    def createHandle(self):
        """The handle between the map and the profile is a thin line from top to bottom."""
        from PySide6.QtGui import QPainter, QPen
        from PySide6.QtWidgets import QSplitterHandle

        class Line(QSplitterHandle):
            def paintEvent(self, event):
                from PySide6.QtGui import QColor

                p = QPainter(self)
                line = QColor(self.palette().mid().color())  # grey and quiet, not bright
                line.setAlpha(70)
                p.setPen(QPen(line, 1))
                x = self.width() // 2
                p.drawLine(x, 4, x, self.height() - 4)
                p.end()

        return Line(self.orientation(), self)

    _sized = False

    def showEvent(self, event):
        """Shown the first time, the map gets the width its rows of buttons need, the profile the
        rest; the line between them moves as before."""
        super().showEvent(event)
        if not self._sized and self.count() == 2 and self.width() > 0:
            first = self.widget(0).minimumSizeHint().width()
            rest = self.width() - first - self.handleWidth()
            if rest > self.widget(1).minimumSizeHint().width():
                self.setSizes([first, rest])
                self._sized = True

    def addWidget(self, widget):
        super().addWidget(widget)
        self.setStretchFactor(self.count() - 1, 1)
        if self._current is None:
            self._current = widget

    def setCurrentWidget(self, widget):
        self._current = widget

    def currentWidget(self):
        return self._current


class FieldPanel(QWidget):
    def __init__(self, source=None, geometry=None, parent=None, topology=None):
        super().__init__(parent)
        self.topology = topology  # () -> Topology | None — the critical points of these orbitals, for the maps
        self.source, self.geometry = source, geometry
        self.written = []
        layout = QVBoxLayout(self)
        from azimuth.icons import iconify
        from azimuth.ui import help_button

        # the explanation in «?» (it was a line over the page); the plane over the map and the
        # line over the profile, a vertical rule between them; a floppy disk in the row of each picture saves it
        row = QHBoxLayout()
        self.function = QComboBox()
        for key, title in CHOICES:
            self.function.addItem(tr(title), key)
        row.addWidget(QLabel(tr('Функция:')))
        row.addWidget(self.function, 1)
        self.field_help = help_button(tr('Функция волновой функции в плоскости трёх атомов (карта) и вдоль линии через '
                                         'два атома (профиль). Данные и экстремумы записываются в папку расчёта.'),
                                      tr('Карты и профили'))
        row.addWidget(self.field_help)
        layout.addLayout(row)

        def column(atoms, actions, view):
            """Two lines over the picture — its atoms, then its button and its floppy disk (one line was squeezed
            in the window: «роить к»), nothing shrinks below the width of its text."""
            from PySide6.QtWidgets import QSizePolicy

            holder = QWidget()
            stack = QVBoxLayout(holder)
            stack.setContentsMargins(0, 0, 0, 0)
            stack.setSpacing(8)
            for line in (atoms, actions):
                for k in range(line.count()):
                    item = line.itemAt(k).widget()
                    if isinstance(item, (QLabel, QPushButton)):
                        item.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
                stack.addLayout(line)
            stack.addWidget(view, 1)
            return holder

        row = QHBoxLayout()
        row.addWidget(QLabel(tr('Плоскость через атомы')))
        self.plane_atoms = [self._atom(k) for k in (1, 2, 3)]
        for box in self.plane_atoms:
            row.addWidget(box)
        self.map_size = QComboBox()
        for n in (100, 200, 300):
            self.map_size.addItem(f'{n} × {n}', n)
        row.addWidget(self.map_size)
        row.addStretch(1)
        plane_atoms = row
        row = QHBoxLayout()
        self.map_button = QPushButton(tr('Построить карту'))
        self.map_button.setObjectName('primary')
        self.map_button.clicked.connect(self.build_map)
        row.addWidget(self.map_button)
        row.addStretch(1)
        self.map_save = iconify(QPushButton(), 'save', tr('Сохранить карту как картинку…'))
        self.map_save.clicked.connect(lambda: self.save_picture(view=self.map_view))
        row.addWidget(self.map_save)
        plane_row = row
        row = QHBoxLayout()
        row.addWidget(QLabel(tr('Линия через атомы')))
        self.line_atoms = [self._atom(k) for k in (1, 2)]
        for box in self.line_atoms:
            row.addWidget(box)
        self.log = iconify(QPushButton(), 'log-scale', tr('Логарифмическая шкала'))  # an icon
        self.log.setCheckable(True)
        self.log.setChecked(True)
        row.addWidget(self.log)
        row.addStretch(1)
        line_atoms = row
        row = QHBoxLayout()
        self.line_button = QPushButton(tr('Построить профиль'))
        self.line_button.setObjectName('primary')  # as «Построить карту» — the main action of its picture
        self.line_button.clicked.connect(self.build_line)
        row.addWidget(self.line_button)
        row.addStretch(1)
        self.line_save = iconify(QPushButton(), 'save', tr('Сохранить профиль как картинку…'))
        self.line_save.clicked.connect(lambda: self.save_picture(view=self.line_view))
        row.addWidget(self.line_save)
        self.views = SideBySide()
        self.map_view, self.line_view = MapView(), LineView()
        self.views.addWidget(column(plane_atoms, plane_row, self.map_view))
        self.views.addWidget(column(line_atoms, row, self.line_view))
        self.views.setCurrentWidget(self.map_view)
        # the arrows and the scale right of «Построить …» — over the picture they hid its labels
        plane_row.insertSpacing(1, 10)
        self.map_view.pad.dock(plane_row, 2)
        row.insertSpacing(1, 10)
        self.line_view.pad.dock(row, 2)
        layout.addWidget(self.views, 1)
        from azimuth.ui import StatusEcho

        self.status = StatusEcho()  # «Таблицы в папке расчёта…» — in the status line, not a line here
        layout.addWidget(self.status)

    @staticmethod
    def _atom(value):
        box = AtomBox()
        box.setRange(1, 999)
        box.setValue(value)
        return box

    def set_atoms(self, count, symbols=None):
        """The atoms of the result: the number of them and their elements — the boxes show «O1», «H2»."""
        for box in self.plane_atoms + self.line_atoms:
            box.set_symbols(symbols if symbols is not None and len(symbols) == count else None)
            box.setMaximum(max(1, count))

    def _source(self):
        given = self.source() if self.source is not None else None
        if not given:
            self.status.setText(tr('Нужен файл орбиталей результата (Molden, fchk или .gbw ORCA) и Multiwfn.'))
        return given

    def _run(self, work, title):
        from azimuth.tasks import run_waiting

        try:
            return run_waiting(self, title, work)
        except InterruptedError:
            return None
        except (OSError, ValueError, MemoryError) as exc:
            self.status.setText(str(exc))
            return None

    def _symbols(self):
        molecule = self.geometry() if self.geometry is not None else None
        return molecule, [a.symbol for a in molecule.atoms] if molecule is not None else []

    def build_map(self):
        from modules.spectrum.wavefunction import multiwfn

        given = self._source()
        if not given:
            return None
        program, path, cores = given
        name = self.function.currentData()
        atoms = tuple(box.value() - 1 for box in self.plane_atoms)
        if len(set(atoms)) != 3:
            self.status.setText(tr('Выберите три разных атома.'))
            return None
        size = self.map_size.currentData()
        plane = self._run(lambda step: multiwfn.run_plane(program, path, name, atoms, size, cores, step), tr('Карта…'))
        if plane is None:
            return None
        from modules.spectrum.wavefunction import field_tables

        field_tables.save_field(path, 'map', plane, name, atoms)  # shown again when the result is opened
        extrema, molecule, symbols = self.show_map(plane, name)
        tag = f'{name}_plane_' + '-'.join(str(a + 1) for a in atoms)
        n1, n2 = plane['values'].shape
        data = [[*(f'{c:.5f}' for c in plane['points'][i, j]), f"{plane['u'][i]:.5f}", f"{plane['v'][j]:.5f}",
                 f"{plane['values'][i, j]:.8g}"] for i in range(n1) for j in range(n2)]
        header = ['x, Å', 'y, Å', 'z, Å', 'u, Å', 'v, Å', tr('Значение')]
        self._write(path, {tag: (header, data), tag + '_extrema': self._extrema_rows(extrema, molecule, symbols)})
        return plane

    def show_map(self, plane, name):
        """The map of a plane on the picture: the atoms near the plane, the extrema, the points and paths of QTAIM in
        it. → (extrema, molecule, symbols)."""
        molecule, symbols = self._symbols()
        shown = []
        if molecule is not None:
            points = plane['points']
            e1 = points[1, 0] - points[0, 0]
            e2 = points[0, 1] - points[0, 0]
            e1, e2 = e1 / np.linalg.norm(e1), e2 / np.linalg.norm(e2)
            normal = np.cross(e1, e2)
            for k, a in enumerate(molecule.atoms):
                d = np.asarray(a.position, float) - points[0, 0]
                if abs(d @ normal) < NEAR:
                    shown.append((plane['u'][0] + d @ e1, plane['v'][0] + d @ e2, f'{a.symbol}{k + 1}'))
        extrema = map_extrema(plane['values'], plane['points'])
        marks, lines = [], []
        found = self.topology() if self.topology is not None else None
        if found is not None and molecule is not None:  # the points and bond paths that lie in the plane
            origin = points[0, 0]
            for cp in found.points:
                d = np.asarray(cp.position, float) - origin
                if abs(d @ normal) < NEAR:
                    marks.append((plane['u'][0] + d @ e1, plane['v'][0] + d @ e2, cp.kind))
            for path_ in found.paths:
                d = np.asarray(path_, float) - origin
                if len(d) and np.max(np.abs(d @ normal)) < NEAR:
                    lines.append(np.column_stack((plane['u'][0] + d @ e1, plane['v'][0] + d @ e2)))
        self.map_view.set(plane, name, shown, extrema, marks, lines)
        self.views.setCurrentWidget(self.map_view)
        return extrema, molecule, symbols

    def build_line(self):
        from modules.spectrum.wavefunction import multiwfn

        given = self._source()
        if not given:
            return None
        program, path, cores = given
        name = self.function.currentData()
        atoms = tuple(box.value() - 1 for box in self.line_atoms)
        if atoms[0] == atoms[1]:
            self.status.setText(tr('Выберите два разных атома.'))
            return None
        line = self._run(lambda step: multiwfn.run_line(program, path, name, atoms, cores, step), tr('Профиль…'))
        if line is None:
            return None
        from modules.spectrum.wavefunction import field_tables

        field_tables.save_field(path, 'line', line, name, atoms)  # shown again when the result is opened
        extrema, molecule, symbols = self.show_line(line, name)
        tag = f'{name}_line_' + '-'.join(str(a + 1) for a in atoms)
        header = ['x, Å', 'y, Å', 'z, Å', tr('Расстояние, Å'), tr('Значение')]
        data = [[*(f'{c:.5f}' for c in pt), f'{s:.5f}', f'{val:.8g}']
                for pt, s, val in zip(line['points'], line['x'], line['values'])]
        rows = self._extrema_rows(extrema, molecule, symbols, along=True)
        self._write(path, {tag: (header, data), tag + '_extrema': rows})
        return line

    def show_line(self, line, name):
        """The profile along a line on the picture, its atoms and extrema. → (extrema, molecule, symbols)."""
        molecule, symbols = self._symbols()
        marks = []
        if molecule is not None:
            start, direction = line['points'][0], line['points'][-1] - line['points'][0]
            length = np.linalg.norm(direction)
            direction = direction / length
            for k, a in enumerate(molecule.atoms):
                d = np.asarray(a.position, float) - start
                along = d @ direction
                if 0 <= along <= length and np.linalg.norm(d - along * direction) < NEAR:
                    marks.append((line['x'][0] + along, f'{a.symbol}{k + 1}'))
        extrema = line_extrema(line['x'], line['values'], line['points'])
        log = self.log.isChecked() and bool(np.all(np.asarray(line['values']) > 0))
        self.line_view.set(line, name, marks, extrema, log)
        self.views.setCurrentWidget(self.line_view)
        return extrema, molecule, symbols

    orbitals = None  # () -> the file of orbitals of the result (its .gbw or Molden), not converted

    def load_saved(self):
        """When the tab is opened, once per result — the last map and the last profile built for these orbitals
        (field_tables.load_field), their function and atoms in the fields. True when something was shown."""
        if getattr(self, '_saved_tried', False) or self.orbitals is None:
            return False
        self._saved_tried = True
        from modules.spectrum.wavefunction import field_tables

        try:
            orbitals = self.orbitals()
        except (AttributeError, OSError):
            orbitals = None
        if orbitals is None:
            return False
        shown = []
        for kind, boxes, show in (('map', self.plane_atoms, self.show_map), ('line', self.line_atoms, self.show_line)):
            kept = field_tables.load_field(orbitals, kind)
            if kept is None:
                continue
            data, name, atoms = kept
            index = self.function.findData(name)
            if index >= 0:
                self.function.setCurrentIndex(index)
            for box, atom in zip(boxes, atoms):
                box.setValue(int(atom) + 1)
            try:
                show(data, name)
            except (ValueError, IndexError, KeyError):
                continue
            shown.append(kind)
        if shown:
            self.status.setText(tr('Последняя карта и профиль — построенные раньше по этому же файлу орбиталей.'))
        return bool(shown)

    def forget_saved(self):
        """A new result: what was kept is looked for again when the tab is opened."""
        self._saved_tried = False

    @staticmethod
    def _extrema_rows(extrema, molecule, symbols, along=False):
        from modules.spectrum.wavefunction.field_tables import _nearest

        header = [tr('№'), tr('Экстремум'), tr('Значение'), 'x, Å', 'y, Å', 'z, Å'] + (
            [tr('Расстояние вдоль линии, Å')] if along else []) + [tr('Ближайший атом'), tr('Расстояние, Å')]
        rows = []
        for n, e in enumerate(extrema, 1):
            atom, distance = _nearest(e['position'], molecule.atoms if molecule is not None else ())
            rows.append([n, tr('максимум') if e['kind'] == 'max' else tr('минимум'), f"{e['value']:.8g}",
                         *(f'{c:.4f}' for c in e['position'])] + ([f"{e['x']:.4f}"] if along else [])
                        + ['' if atom is None else f'{symbols[atom]}{atom + 1}', '' if distance is None else f'{distance:.3f}'])
        return header, rows

    def _write(self, path, tables):
        from modules.spectrum.wavefunction import field_tables

        base = Path(path)
        try:
            self.written = field_tables.write_tables(base.parent, base.name.split('.')[0], tables)
        except OSError as exc:
            self.status.setText(tr('Таблица не записана: ') + str(exc))
            return
        self.status.setText(tr('Таблицы — в папке «Анализ» расчёта.'))

    def save_picture(self, path=None, view=None):
        """The picture as PNG — view (the floppy disk of the map or of the profile), else the one built
        last. The button gives «clicked» its False — no path either (the button did nothing)."""
        view = view or self.views.currentWidget()
        if not path:
            name = 'profile.png' if view is self.line_view else 'map.png'
            path, _ = QFileDialog.getSaveFileName(self, tr('Сохранить картинку…'), name, tr('PNG (*.png)'))
        if path:
            view.picture().save(str(path), 'PNG')  # without the pad of the arrows and the scale
        return path or None
