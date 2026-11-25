"""The molecule to be calculated, small, in Sextant.

§1 PURPOSE
    The right column of Sextant shows what is going to be calculated: a small model of the structure of the tab
    (turned with the mouse) and its formula, electrons, charge and multiplicity; the input file is below it.
§2 ALGORITHM MoleculeThumb: the atoms turned by yaw and pitch (a drag turns them), scaled to fit the widget with a
    margin; bonds (modules/compass/chemistry/builder.connections) as lines in two halves of the atoms' colours, then the
    atoms as shaded discs from the back to the front (painter's order); the colours are those of the model in Compass
    (palette, schemes.AZIMUTH by default; neutral grey for the rest), radii ~ covalent (H smaller).
§4 SPECIFICATION
    MoleculeThumb(); set_molecule(molecule), set_dark(dark), set_palette(dict).
§7 TESTS
    tests/test_gui.py::test_sextant_molecule_card.
"""

from math import cos, sin

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import QWidget

RADIUS = {'H': 0.55}  # Å, the rest 0.8 (a small model, only the shape matters)


class MoleculeThumb(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.molecule = None
        self.dark = False
        self.palette_colors = {}
        self.yaw, self.pitch = 0.6, -0.5
        self._last = None
        self.setMinimumSize(120, 110)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setToolTip('')

    def set_molecule(self, molecule):
        self.molecule = molecule
        self.update()

    def set_dark(self, dark):
        self.dark = bool(dark)
        self.update()

    def set_palette(self, colors):
        self.palette_colors = dict(colors or {})
        self.update()

    def mousePressEvent(self, event):
        self._last = event.position()
        self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        if self._last is None:
            return
        d = event.position() - self._last
        self._last = event.position()
        self.yaw += d.x() * 0.012
        self.pitch += d.y() * 0.012
        self.update()

    def mouseReleaseEvent(self, event):
        self._last = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def turned(self):
        atoms = [a for a in (self.molecule.atoms if self.molecule else ()) if a.symbol != 'X']
        if not atoms:
            return [], []
        cx = sum(a.x for a in atoms) / len(atoms)
        cy = sum(a.y for a in atoms) / len(atoms)
        cz = sum(a.z for a in atoms) / len(atoms)
        cyaw, syaw, cp, sp = cos(self.yaw), sin(self.yaw), cos(self.pitch), sin(self.pitch)
        points = []
        for a in atoms:
            x, y, z = a.x - cx, a.y - cy, a.z - cz
            x, z = cyaw * x + syaw * z, -syaw * x + cyaw * z
            y, z = cp * y - sp * z, sp * y + cp * z
            points.append((x, y, z))
        return atoms, points

    def color(self, symbol):
        return QColor(self.palette_colors.get(symbol, '#9aa6b8'))

    def paintEvent(self, event):
        from modules.compass.chemistry.builder import connections

        atoms, points = self.turned()
        if not atoms:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        span = max(max(max(abs(x), abs(y)) + RADIUS.get(a.symbol, 0.8) for a, (x, y, _) in zip(atoms, points)), 0.8)
        scale = (min(self.width(), self.height()) / 2 - 6) / span
        mid = QPointF(self.width() / 2, self.height() / 2)

        def at(k):
            x, y, _ = points[k]
            return QPointF(mid.x() + x * scale, mid.y() - y * scale)

        source = self.molecule
        keep = [k for k, a in enumerate(source.atoms) if a.symbol != 'X']
        renumber = {old: new for new, old in enumerate(keep)}
        width = max(1.5, 0.18 * scale)
        for i, j, _ in connections(source):
            if i not in renumber or j not in renumber:
                continue
            a, b = renumber[i], renumber[j]
            pa, pb = at(a), at(b)
            half = (pa + pb) / 2
            for k, start, end in ((a, pa, half), (b, half, pb)):
                p.setPen(QPen(self.color(atoms[k].symbol).darker(115), width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                p.drawLine(start, end)
        edge = QColor('#0d1420' if self.dark else '#1b2230')
        edge.setAlphaF(0.35)
        for k in sorted(range(len(atoms)), key=lambda k: points[k][2]):
            r = RADIUS.get(atoms[k].symbol, 0.8) * scale * 0.55
            c = at(k)
            base = self.color(atoms[k].symbol)
            g = QRadialGradient(c + QPointF(-r * 0.35, -r * 0.35), r * 1.3)
            g.setColorAt(0, base.lighter(140))
            g.setColorAt(1, base.darker(110))
            p.setPen(QPen(edge, 0.8))
            p.setBrush(g)
            p.drawEllipse(c, r, r)
        p.end()

