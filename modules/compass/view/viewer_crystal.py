"""What the model of a crystal has drawn over it: the edges of the cell, the lattice points and planes, the
symmetry elements, the displacement ellipsoids, the rings and π–π stacks, the energy framework, the polyhedra.
Methods of ViewerDrawing (self is the view), kept here to make viewer_drawing.py shorter.

Split off modules/compass/view/viewer_drawing.py (0.222.30).
"""

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QFont, QPen


def draw_cell(self, p):
    """The edges of the crystal block: a, b, c from the origin in red, green, blue, the rest grey."""
    center, scale = self.camera()

    def at(r):
        x, y, z = self.to_view(tuple(r[k] - center[k] for k in range(3)))
        f = self.depth_factor(z)
        return QPointF(self.width() / 2 + self.pan.x() + x * scale * f, self.height() / 2 + self.pan.y() - y * scale * f)

    grey = QColor('#7d8b9b' if self.dark else '#8a97a6')
    axes = ('#d65454', '#2ca77a', '#528edf')
    font = QFont(self.font())
    font.setPixelSize(13)
    font.setBold(True)
    p.setFont(font)
    for k, (start, end) in enumerate(self.cell_lines):
        ink = QColor(axes[k]) if k < 3 else grey
        p.setPen(QPen(ink, 2.0 if k < 3 else 1.3))
        a, b = at(start), at(end)
        p.drawLine(a, b)
        if k < 3:
            p.drawText(b + QPointF(5, -5), 'abc'[k])


def draw_lattice_points(self, p):
    """The nodes of the Bravais lattice in the block — small filled diamonds in the ink of the cell; the
    nodes of the centring (not at a corner of a cell) a little larger, to be told apart."""
    from PySide6.QtGui import QPolygonF

    center, scale = self.camera()
    ink = QColor('#c7d0db' if self.dark else '#2f3a48')
    p.setPen(QPen(ink, 1.0))
    p.setBrush(ink)
    for point, centred in self.lattice_points:
        x, y, z = self.to_view(tuple(point[k] - center[k] for k in range(3)))
        f = self.depth_factor(z)
        c = QPointF(self.width() / 2 + self.pan.x() + x * scale * f, self.height() / 2 + self.pan.y() - y * scale * f)
        r = 5.0 if centred else 3.5
        p.drawPolygon(QPolygonF([c + QPointF(0, -r), c + QPointF(r, 0), c + QPointF(0, r), c + QPointF(-r, 0)]))
    p.setBrush(Qt.BrushStyle.NoBrush)


def draw_lattice_planes(self, p):
    """The planes (hkl) of the block (lattice_planes): translucent amber sheets, the label at the first."""
    from PySide6.QtGui import QPolygonF

    center, scale = self.camera()

    def at(r):
        x, y, z = self.to_view(tuple(r[k] - center[k] for k in range(3)))
        f = self.depth_factor(z)
        return QPointF(self.width() / 2 + self.pan.x() + x * scale * f, self.height() / 2 + self.pan.y() - y * scale * f)

    label, polygons = self.lattice_planes
    ink = QColor('#d6a95c' if self.dark else '#b8893f')
    fill = QColor(ink)
    fill.setAlpha(52)
    p.setBrush(fill)
    p.setPen(QPen(ink, 1.3))
    for polygon in polygons:
        p.drawPolygon(QPolygonF([at(c) for c in polygon]))
    p.setBrush(Qt.BrushStyle.NoBrush)
    if polygons:
        font = QFont(self.font())
        font.setPixelSize(13)
        font.setBold(True)
        p.setFont(font)
        p.setPen(ink)
        last = polygons[-1]  # at the centre of the last sheet: away from the labels a, b, c at the origin
        centre = tuple(sum(c[k] for c in last) / len(last) for k in range(3))
        p.drawText(at(centre) + QPointF(-20, 5), label)


def draw_symmetry(self, p):
    """The symmetry elements of the crystal inside the cell (crystal_symmetry.elements): rotation axes
    solid and screw axes dashed (green), mirror planes filled faintly and glide planes dashed (blue), inversion
    centres and rotoinversion points as rings (brown); each with its symbol."""
    center, scale = self.camera()

    def at(r):
        x, y, z = self.to_view(tuple(r[k] - center[k] for k in range(3)))
        f = self.depth_factor(z)
        return QPointF(self.width() / 2 + self.pan.x() + x * scale * f, self.height() / 2 + self.pan.y() - y * scale * f)

    font = QFont(self.font())
    font.setPixelSize(12)
    p.setFont(font)
    theme = 1 if self.dark else 0
    for symbol, kind, geometry in self.symmetry_items:
        if kind in ('-1', '-3', '-4', '-6'):
            ink = QColor(self.SYMMETRY_INK['point'][theme])
            point = at(geometry)
            p.setPen(QPen(ink, 1.6))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(point, 4.0, 4.0)
            if kind != '-1':
                p.drawText(point + QPointF(6, -6), symbol.replace('-', '−'))
        elif kind == 'm':
            glide = symbol != 'm'
            ink = QColor(self.SYMMETRY_INK['glide' if glide else 'mirror'][theme])
            corners = [at(r) for r in geometry]
            fill = QColor(ink)
            fill.setAlpha(0 if glide else 28)
            p.setBrush(fill)
            p.setPen(QPen(ink, 1.2, Qt.PenStyle.DashLine if glide else Qt.PenStyle.SolidLine))
            from PySide6.QtGui import QPolygonF

            p.drawPolygon(QPolygonF(corners))
            p.drawText(corners[0] + QPointF(4, -4), symbol)
        else:
            screw = len(symbol) > 1 and not symbol.startswith('-')
            ink = QColor(self.SYMMETRY_INK['screw' if screw else 'axis'][theme])
            a, b = at(geometry[0]), at(geometry[1])
            p.setPen(QPen(ink, 1.8, Qt.PenStyle.DashLine if screw else Qt.PenStyle.SolidLine))
            p.drawLine(a, b)
            p.drawText(b + QPointF(4, -4), symbol)
    p.setBrush(Qt.BrushStyle.NoBrush)


def draw_ellipsoids(self, p):
    """The displacement ellipsoids (50 %) of the atoms of a crystal as the ellipses of their parallel
    projection (crystal_adp.ellipse), under the atoms; atoms without a tensor are left as they are."""
    import numpy as np

    from modules.compass.chemistry import crystal_adp

    molecule, tensors = self.ellipsoids
    if molecule is not self.molecule or len(tensors) != len(self.molecule.atoms):
        return
    center, scale = self.camera()
    basis = np.array([self.to_view(e) for e in ((1, 0, 0), (0, 1, 0), (0, 0, 1))], dtype=float).T
    ink = QColor('#c9d2dd' if self.dark else '#3b4656')
    fill = QColor(ink)
    fill.setAlpha(40)
    p.setPen(QPen(ink, 1.1))
    p.setBrush(fill)
    for atom, u in zip(self.molecule.atoms, tensors):
        if u is None:
            continue
        x, y, z = self.to_view(tuple(atom.position[k] - center[k] for k in range(3)))
        f = self.depth_factor(z)
        a, b, angle = crystal_adp.ellipse(u, basis)
        p.save()
        p.translate(self.width() / 2 + self.pan.x() + x * scale * f, self.height() / 2 + self.pan.y() - y * scale * f)
        p.rotate(-angle)
        p.drawEllipse(QPointF(0, 0), a * scale * f, b * scale * f)
        p.restore()
    p.setBrush(Qt.BrushStyle.NoBrush)


def draw_ring_marks(self, p):
    """The planes of the rings (translucent), their centroids (dots), the π–π stacks (dashed Cg···Cg) and
    C–H···π (dotted H···Cg) of crystal_rings.model_marks."""
    from PySide6.QtGui import QPolygonF

    molecule, marks = self.ring_marks
    if molecule is not self.molecule:
        return
    center, scale = self.camera()

    def spot(r):
        x, y, z = self.to_view(tuple(r[k] - center[k] for k in range(3)))
        f = self.depth_factor(z)
        return QPointF(self.width() / 2 + self.pan.x() + x * scale * f, self.height() / 2 + self.pan.y() - y * scale * f)

    ink = QColor(self.RING_INK)
    fill = QColor(ink)
    fill.setAlpha(55)
    p.setPen(QPen(QColor(ink.red(), ink.green(), ink.blue(), 150), 1.0))
    p.setBrush(fill)
    for _, corners in marks['rings']:
        p.drawPolygon(QPolygonF([spot(c) for c in corners]))
    for style, key in ((Qt.PenStyle.DashLine, 'stacks'), (Qt.PenStyle.DotLine, 'ch_pi')):
        p.setPen(QPen(ink, 1.6, style))
        for a, b in marks[key]:
            p.drawLine(spot(a), spot(b))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(ink)
    for centroid, _ in marks['rings']:
        p.drawEllipse(spot(centroid), 3.0, 3.0)
    p.setBrush(Qt.BrushStyle.NoBrush)


def draw_energy_frame(self, p):
    """The energy framework (crystal_pairs.frame): a thick line between the centroids of the molecule and
    each neighbour, the thickness by |E_int| (up to 14 px at the strongest), blue — attraction, red — repulsion;
    a dot at each centroid."""
    molecule, cylinders = self.energy_frame
    if molecule is not self.molecule:
        return
    center, scale = self.camera()

    def spot(r):
        x, y, z = self.to_view(tuple(r[k] - center[k] for k in range(3)))
        f = self.depth_factor(z)
        return QPointF(self.width() / 2 + self.pan.x() + x * scale * f, self.height() / 2 + self.pan.y() - y * scale * f)

    for a, b, width, attractive in sorted(cylinders, key=lambda c: c[2]):
        ink = QColor(self.FRAME_ATTRACTIVE if attractive else self.FRAME_REPULSIVE)
        ink.setAlpha(190)
        pen = QPen(ink, max(1.5, 14.0 * width))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawLine(spot(a), spot(b))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor('#4a5563'))
    for a, b, _, _ in cylinders:
        p.drawEllipse(spot(b), 3.0, 3.0)
    if cylinders:
        p.drawEllipse(spot(cylinders[0][0]), 4.0, 4.0)
    p.setBrush(Qt.BrushStyle.NoBrush)


def draw_polyhedra(self, p):
    """The coordination polyhedra (crystal_symmetry.polyhedra) as faces in the colour of the centre atom,
    translucent, the far faces first; under the atoms."""
    from PySide6.QtGui import QPolygonF

    molecule, found = self.polyhedra
    if molecule is not self.molecule:
        return
    center, scale = self.camera()
    faces = []
    for symbol, polygons in found:
        for face in polygons:
            spots, depth = [], 0.0
            for r in face:
                x, y, z = self.to_view(tuple(r[k] - center[k] for k in range(3)))
                f = self.depth_factor(z)
                spots.append(QPointF(self.width() / 2 + self.pan.x() + x * scale * f,
                                     self.height() / 2 + self.pan.y() - y * scale * f))
                depth += z
            faces.append((depth / len(face), symbol, spots))
    faces.sort(key=lambda item: item[0])  # the far faces first (z towards the viewer)
    for _, symbol, spots in faces:
        colour = QColor(self.palette.get(symbol, '#9c80b7') if isinstance(self.palette, dict) else '#9c80b7')
        fill = QColor(colour)
        fill.setAlpha(70)
        edge = QColor(colour).darker(140)
        edge.setAlpha(200)
        p.setBrush(fill)
        p.setPen(QPen(edge, 1.0))
        p.drawPolygon(QPolygonF(spots))
    p.setBrush(Qt.BrushStyle.NoBrush)
