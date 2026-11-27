"""ViewerDrawing: what the model view of Compass draws over and around the molecule with QPainter — labels, axes, the
aim of a point, surfaces with their veil and legend, hydrogen bonds, measurements, overlays, bond labels, van der Waals
spheres, guides, constraints, the ghost of a placement, the cell, the comparison, the empty field. A mixin of
MoleculeView (modules/compass/view/viewer.py), split from it on 2026-11-08 without changes of the code."""

from math import cos, dist, hypot, radians, sqrt

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPen

from modules.compass.chemistry.builder import connections
from modules.compass.chemistry.geometry_tools import dot, sub
from azimuth.i18n import tr
from modules.compass.chemistry.molecular_size import BONDI as VDW_ALL
from modules.compass.view import viewer_surface as _surface
from modules.compass.view import viewer_crystal as _crystal

# Bondi values for common organic atoms, Å; other elements use an illustrative fallback.
# https://pmc.ncbi.nlm.nih.gov/articles/PMC7079509/
VDW_RADII = {'H': 1.20, 'C': 1.70, 'N': 1.55, 'O': 1.52}
BOND_LEGENDS = {  # the legend of the bond orders on the model (the titles of property_actions.BOND_TITLES)
    'Mayer': 'Порядки связей Майера',
    'Wiberg': 'Порядки связей Виберга (xtb)',
    'Wiberg-Löwdin': 'Порядки связей Виберга–Лёвдина',
    'Fuzzy': 'Нечёткие порядки связей (FBO)',
    'Laplacian': 'Лапласиановы порядки связей (LBO)',
}


class ViewerDrawing:
    """Mixin of MoleculeView (modules/compass/view/viewer.py)."""

    def draw_dummies(self, p, points, radii):
        """A dashed ring around every dummy atom X, so that the point is seen as «not an atom»."""
        if self.molecule is None:
            return
        ink = QColor('#9aa6b4' if self.dark else '#6f7d8c')
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(ink, 1.2, Qt.PenStyle.DashLine))
        for i, a in enumerate(self.molecule.atoms):
            if a.symbol == 'X' and i < len(points):
                r = radii[i] * 2.2 + 3
                p.drawEllipse(points[i][0], r, r)

    def draw_custom_labels(self, p, points, radii):
        """Own labels beside their atoms (up and to the right), in a readable size on a light pill."""
        if not self.show_custom or not self.custom_labels:
            return
        font = QFont('Arial')
        font.setBold(True)
        font.setPixelSize(11)
        p.setFont(font)
        metrics = p.fontMetrics()
        ink = QColor('#e7eaf0' if self.dark else '#1b2230')
        pill = QColor(25, 31, 40, 200) if self.dark else QColor(255, 255, 255, 210)
        hidden = self.hidden_atoms()
        for i, text in sorted(self.custom_labels.items(), key=lambda kv: points[kv[0]][1] if kv[0] < len(points) else 0):
            if not (0 <= i < len(points)) or not text or i in hidden:
                continue
            point, r = points[i][0], radii[i]
            width, height = metrics.horizontalAdvance(text) + 8, metrics.height() + 2
            box = QRectF(point.x() + r * 0.7, point.y() - r * 0.7 - height, width, height)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(pill)
            p.drawRoundedRect(box, height / 2, height / 2)
            p.setPen(ink)
            p.drawText(box, Qt.AlignmentFlag.AlignCenter, text)

    AXES_CORNER = (52, 52)  # top right — the steps drawer covers the left edge

    def axes_origin(self):
        """The origin of the corner axes — axes_offset (from the right edge, from the top) when they were
        moved, else AXES_CORNER; always inside the field."""
        right, top = getattr(self, 'axes_offset', None) or self.AXES_CORNER
        margin = 40
        x = min(max(self.width() - right, margin), max(margin, self.width() - margin))
        y = min(max(top, margin), max(margin, self.height() - margin))
        return QPointF(x, y)

    def axes_ring(self):
        """The circle around the axes as they
        are drawn now — the middle of the box of their origin, ends and letters, wide enough for all of them (it was
        round the origin, which is a corner of the axes) -> (centre, radius); the axes are taken inside it."""
        origin = self.axes_origin()
        points = [origin]
        for vector in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
            x, y, _ = self.to_view(vector)
            end = origin + QPointF(x * 32, -y * 32)
            points += [end, end + QPointF(12, -14)]  # the letter beside the end
        left, right = min(q.x() for q in points), max(q.x() for q in points)
        top, bottom = min(q.y() for q in points), max(q.y() for q in points)
        centre = QPointF((left + right) / 2, (top + bottom) / 2)
        radius = max(((q.x() - centre.x()) ** 2 + (q.y() - centre.y()) ** 2) ** 0.5 for q in points) + 8
        return centre, max(22.0, radius)

    def draw_axes(self, p):
        if self.axes_place != 'corner':
            return  # drawn on the model (draw_model_axes)
        origin = self.axes_origin()
        if getattr(self, 'axes_movable', False):  # a faint ring — they can be taken and carried
            ring = QColor('#8fa3bd')
            ring.setAlpha(110)
            p.setPen(QPen(ring, 1, Qt.PenStyle.DashLine))
            p.setBrush(Qt.BrushStyle.NoBrush)
            centre, radius = self.axes_ring()
            p.drawEllipse(centre, radius, radius)
        for name, vector, color in [
            ('X', (1, 0, 0), '#d65454'),
            ('Y', (0, 1, 0), '#2ca77a'),
            ('Z', (0, 0, 1), '#528edf'),
        ]:
            x, y, z = self.to_view(vector)
            end = origin + QPointF(x * 32, -y * 32)
            p.setPen(QPen(QColor(color), 2))
            p.drawLine(origin, end)
            p.setFont(QFont('Arial', 10, QFont.Weight.Bold))
            p.drawText(end + QPointF(4, -3), name)

    def draw_aim(self, p):
        """The bond paths (thin lines from nucleus to nucleus through the bond critical point) and the critical points
        (bond — green, ring — orange, cage — violet) of modules/spectrum/analysis/density.py, while the structure is the one
        they were found for."""
        a = self.aim
        if not a or not self.molecule or self.molecule.atoms != a['atoms']:
            return
        from PySide6.QtGui import QPolygonF

        ink = QColor('#d8dee8' if self.dark else '#33404d')
        ink.setAlpha(190)
        p.save()
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(ink, 1.6))
        for path in a['paths']:
            xy = self.project_vertices(path)[:, :2]
            p.drawPolyline(QPolygonF([QPointF(float(x), float(y)) for x, y in xy]))
        edge = QColor('#10151c' if self.dark else '#ffffff')
        spots = []  # (x, y, kind) on the screen
        for kind, position in a['points']:
            x, y, _ = self.project_vertices(position[None])[0]
            spots.append((float(x), float(y), kind))
            if kind == 'nucleus':
                # a filled dot on a nucleus covered the element of the atom («H»
                # looked like «Ю») — a thin ring around the centre instead, the letter stays readable
                p.setPen(QPen(QColor(self.AIM_COLOURS['nucleus']), 1.4))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawEllipse(QPointF(float(x), float(y)), 9.5, 9.5)
                continue
            p.setPen(QPen(edge, 1.2))
            p.setBrush(QColor(self.AIM_COLOURS.get(kind, '#888888')))
            p.drawEllipse(QPointF(float(x), float(y)), 4.5, 4.5)
        labels = a.get('labels') or []
        if labels:  # the numbers of the table (n1, b1 …) next to the points, with a halo
            from PySide6.QtGui import QPainterPath

            font = QFont(self.font())
            font.setPixelSize(11)
            font.setBold(True)
            text_ink = QColor('#e6ebf2' if self.dark else '#1f2a36')
            # every label where it covers no other label and no other point («n3» sat on «b2», «b1» on «n2»):
            # the first free place of eight around its point, the upper right first; the nearest one when none is free
            boxes = []
            for label in labels:
                probe = QPainterPath()
                probe.addText(QPointF(0.0, 0.0), font, label or '')
                boxes.append(probe.boundingRect())
            from modules.compass.view.label_places import aim_label_places

            places = aim_label_places(spots, [(b.width(), b.height()) if label else None
                                              for b, label in zip(boxes, labels)])
            for place, box, label in zip(places, boxes, labels):
                if place is None:
                    continue
                chosen = QRectF(place[0], place[1], box.width(), box.height())
                path = QPainterPath()
                path.addText(QPointF(chosen.left() - box.left(), chosen.top() - box.top()), font, label)
                p.setPen(QPen(edge, 3.0))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawPath(path)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(text_ink)
                p.drawPath(path)
        if a.get('selected') is not None:  # the row chosen in the table of the points; it pulses
            x, y, _ = self.project_vertices(a['selected'][None])[0]
            centre = QPointF(float(x), float(y))
            blue = QColor('#6ea2f0' if self.dark else '#2a62b8')
            p.setBrush(Qt.BrushStyle.NoBrush)
            if self.capture:  # a picture: one still ring
                p.setPen(QPen(blue, 2.4))
                p.drawEllipse(centre, 9.0, 9.0)
            else:
                radius, opacity = self.pulse_radius()
                ring = QColor(blue)
                ring.setAlphaF(opacity)
                p.setPen(QPen(ring, 2.6))
                p.drawEllipse(centre, radius, radius)
                p.setPen(QPen(blue, 1.6))
                p.drawEllipse(centre, 6.0, 6.0)
                if not self._pulse.isActive():
                    self._pulse.start()
        p.restore()

    draw_surface_markers = _surface.draw_surface_markers
    surface_meshes = _surface.surface_meshes
    project_vertices = _surface.project_vertices

    def label_clip(self, i, points=None, radii=None, covers=None):
        """Where the label of atom i may be drawn: its circle minus the discs of the atoms nearer to
        the viewer that overlap it; None when nothing covers it (draw freely), an empty region when the nearer
        atoms cover the whole circle. Covers — label_covers of the whole frame, found once with numpy
        (view/occlusion.py); without it, found for this atom alone."""
        from PySide6.QtGui import QRegion

        points = points if points is not None else self.projected()
        radii = radii if radii is not None else [self.atom_radius(k) for k in range(len(points))]
        if covers is None:
            covers = self.label_covers(points, radii, rows=(i,))
        found = covers.get(i)
        if found is None:
            return None
        if found == 'full':
            return QRegion()
        pi, ri = points[i][0], radii[i]
        cover = None
        for j in found:
            pj, rj = points[j][0], radii[j]
            disc = QRegion(round(pj.x() - rj), round(pj.y() - rj), round(2 * rj), round(2 * rj), QRegion.RegionType.Ellipse)
            cover = disc if cover is None else cover.united(disc)
        own = QRegion(int(pi.x() - ri) - 1, int(pi.y() - ri) - 1, int(2 * ri) + 3, int(2 * ri) + 3)
        return own.subtracted(cover)

    def label_covers(self, points, radii, rows=None):
        """View/occlusion.label_covers for the atoms drawn now."""
        from modules.compass.view.occlusion import label_covers

        hidden = self.hidden_atoms()
        drawn = [k for k in range(len(points)) if k not in hidden]
        return label_covers([(q.x(), q.y()) for q, _ in points], [zz for _, zz in points], radii, drawn, rows)

    def draw_empty(self, p):
        """The hint of the empty field, pale: «Постройте свою молекулу ✎ или откройте готовую 📁» with the
        glyphs of «Изменение структуры» and «Файл → Открыть…» (two lines when the field is narrow); in the crystals
        their own text (empty_text), as pale."""
        from PySide6.QtCore import QByteArray
        from PySide6.QtGui import QFontMetricsF
        from PySide6.QtSvg import QSvgRenderer

        from azimuth.icons import GLYPHS

        ink = QColor('#5d6b78' if self.dark else '#a3afba')
        font = QFont('Arial', 14)
        p.setFont(font)
        p.setPen(ink)
        if hasattr(self, 'empty_text'):
            p.drawText(QRectF(self.rect()), Qt.AlignmentFlag.AlignCenter, self.empty_text)
            return
        metrics = QFontMetricsF(font)
        size = metrics.height() * 1.05
        from modules.compass.view.viewer import EMPTY_PARTS

        parts = [(tr(text), glyph) for text, glyph in getattr(self, 'empty_parts', None) or EMPTY_PARTS]

        def width(text):
            return metrics.horizontalAdvance(text) + 6 + size

        one = sum(width(text) for text, _ in parts) + 10
        lines = [parts] if one <= self.width() - 40 else [[part] for part in parts]
        top = self.height() / 2 - len(lines) * size * 1.25 / 2
        for line in lines:
            x = (self.width() - sum(width(text) for text, _ in line) - 10 * (len(line) - 1)) / 2
            for text, glyph in line:
                p.drawText(QPointF(x, top + size * 0.82), text)
                x += metrics.horizontalAdvance(text) + 6
                svg = (
                    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g fill="none" stroke="'
                    + ink.name()
                    + '" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">'
                    + GLYPHS[glyph]
                    + '</g></svg>'
                )
                QSvgRenderer(QByteArray(svg.encode())).render(p, QRectF(x, top, size, size))
                x += size + 10
            top += size * 1.25

    def ornament_cover(self, within=None):
        """The pixels of the model (atoms and bonds) as a QRegion of this widget: the hub's faint
        scales are not drawn there, so the molecule hides the picture behind it instead of showing it through.
        within: a QRect of this widget; atoms and bonds wholly outside it are skipped (only the corners with
        scales are asked for, so a large crystal stays cheap)."""
        from PySide6.QtCore import QPoint
        from PySide6.QtGui import QPolygon, QRegion

        region = QRegion()
        if not self.molecule or not self.molecule.atoms:
            return region
        points = self.projected()
        radii = [self.atom_radius(k) for k in range(len(points))]
        def outside(x0, y0, x1, y1):
            return within is not None and (x1 < within.left() or x0 > within.right() or y1 < within.top() or y0 > within.bottom())

        hidden = self.hidden_atoms()
        for k, ((pt, _), r) in enumerate(zip(points, radii)):
            if k in hidden or outside(pt.x() - r, pt.y() - r, pt.x() + r, pt.y() + r):
                continue
            region = region.united(QRegion(round(pt.x() - r), round(pt.y() - r), round(2 * r), round(2 * r), QRegion.RegionType.Ellipse))
        if self.display_mode != 'spacefill' and self.show_bonds:
            half = max(1.0, self.bond_width * self.camera()[1] * 0.08) / 2 + 1
            for i, j, _ in self.drawn_bonds(hidden):
                a, b = points[i][0], points[j][0]
                if outside(min(a.x(), b.x()) - half, min(a.y(), b.y()) - half, max(a.x(), b.x()) + half, max(a.y(), b.y()) + half):
                    continue
                dx, dy = b.x() - a.x(), b.y() - a.y()
                length = hypot(dx, dy)
                if length < 1:
                    continue
                ox, oy = -dy / length * half, dx / length * half
                corners = [(a.x() + ox, a.y() + oy), (b.x() + ox, b.y() + oy), (b.x() - ox, b.y() - oy), (a.x() - ox, a.y() - oy)]
                region = region.united(QRegion(QPolygon([QPoint(round(x), round(y)) for x, y in corners])))
        return region

    surface_triangles = _surface.surface_triangles
    draw_surface_veil = _surface.draw_surface_veil
    erase_under_surface = _surface.erase_under_surface
    draw_surface = _surface.draw_surface
    draw_surface_legend = _surface.draw_surface_legend

    def hydrogen_bonds(self):
        """(H, acceptor) pairs: H on N, O or F; acceptor N, O or F not bonded to it; H···A 1.5–2.5 Å,
        angle D–H···A above 120°. Kept for the last structure (it was searched again every frame)."""
        if self._hbonds[0] is self.molecule:
            return self._hbonds[1]
        found = self._hydrogen_bonds()
        self._hbonds = (self.molecule, found)
        return found

    def _hydrogen_bonds(self):
        atoms = self.molecule.atoms
        bonds = connections(self.molecule)
        donor = {}
        for i, j, _ in bonds:
            for h, d in ((i, j), (j, i)):
                if atoms[h].symbol == 'H' and atoms[d].symbol in ('N', 'O', 'F'):
                    donor[h] = d
        bonded = {(min(i, j), max(i, j)) for i, j, _ in bonds}
        found = []
        for h, d in donor.items():
            for a, atom in enumerate(atoms):
                if a in (h, d) or atom.symbol not in ('N', 'O', 'F') or (min(a, h), max(a, h)) in bonded:
                    continue
                r = dist(atoms[h].position, atom.position)
                if 1.5 <= r <= 2.5:
                    u = sub(atoms[d].position, atoms[h].position)
                    v = sub(atom.position, atoms[h].position)
                    c = dot(u, v) / sqrt(dot(u, u) * dot(v, v))
                    if c < cos(radians(120)):
                        found.append((h, a))
        return found

    def draw_hbonds(self, p):
        from azimuth import defaults

        points = self.projected()
        # «Стиль связей…» — the colour, the width and the line of the hydrogen bonds
        ink = QColor(defaults.get('hbond_color') or ('#7fb2ff' if self.dark else '#3d7dd8'))
        ink.setAlpha(200)
        line = {'dotted': Qt.PenStyle.DotLine, 'dashed': Qt.PenStyle.DashLine,
                'solid': Qt.PenStyle.SolidLine}.get(defaults.get('hbond_style'), Qt.PenStyle.DotLine)
        p.setPen(QPen(ink, defaults.get('hbond_width'), line, Qt.PenCapStyle.RoundCap))
        hidden = self.hidden_atoms()
        for h, a in self.hydrogen_bonds():
            if h not in hidden:  # no hydrogen bond from a hidden H
                p.drawLine(points[h][0], points[a][0])

    # the lines of the weak interactions named after a QTAIM search (aim['contacts']); the hydrogen bonds
    # in the style of the hydrogen bonds («Стиль связей…»), the σ-hole bonds dashed in their colour, van der Waals thin
    CONTACT_COLOURS = {'halogen': '#2fa58a', 'chalcogen': '#c9a227', 'pnictogen': '#d0702c', 'tetrel': '#8e6bd0'}

    def aim_contacts(self):
        """(i, j, kind) of the weak interactions found by the last QTAIM search put on the model (found_contacts),
        while the structure is theirs — also after the points are taken away."""
        a = getattr(self, 'found_contacts', None)
        if not a or not self.molecule or self.molecule.atoms != a.get('atoms'):
            return []
        n = len(self.molecule.atoms)
        return [(i, j, kind) for i, j, kind in a.get('contacts') or () if 0 <= i < n and 0 <= j < n]

    def draw_aim_contacts(self, p):
        from azimuth import defaults

        points = self.projected()
        hidden = self.hidden_atoms()
        drawn = {frozenset(pair) for pair in self.hydrogen_bonds()} if self.show_hbonds else set()
        lines = {'dotted': Qt.PenStyle.DotLine, 'dashed': Qt.PenStyle.DashLine, 'solid': Qt.PenStyle.SolidLine}
        width = defaults.get('hbond_width')
        p.save()
        for i, j, kind in self.aim_contacts():
            if i in hidden or j in hidden or frozenset((i, j)) in drawn:
                continue
            if kind == 'hydrogen':
                ink = QColor(defaults.get('hbond_color') or ('#7fb2ff' if self.dark else '#3d7dd8'))
                ink.setAlpha(200)
                pen = QPen(ink, width, lines.get(defaults.get('hbond_style'), Qt.PenStyle.DotLine),
                           Qt.PenCapStyle.RoundCap)
            elif kind in self.CONTACT_COLOURS:
                ink = QColor(self.CONTACT_COLOURS[kind])
                ink.setAlpha(210)
                pen = QPen(ink, width, Qt.PenStyle.DashLine, Qt.PenCapStyle.RoundCap)
            else:  # van der Waals
                ink = QColor('#9aa6b4' if self.dark else '#7d8896')
                ink.setAlpha(170)
                pen = QPen(ink, max(1.0, width * 0.7), Qt.PenStyle.DotLine, Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.drawLine(points[i][0], points[j][0])
        p.restore()

    def _tag(self, p, point, text, size=11, measured=False):
        """A number on a plate. measured («Стиль измерений…»): of a measurement — its font, bold, italic,
        colour and plate (or none) from azimuth.defaults."""
        font = QFont(self.font())
        ink = QColor('#e7eaf0' if self.dark else '#1b2230')
        plate = True
        if measured:
            from azimuth import defaults

            if defaults.get('measure_font'):
                font = QFont(defaults.get('measure_font'))
            font.setItalic(defaults.get('measure_italic'))
            if defaults.get('measure_color'):
                ink = QColor(defaults.get('measure_color'))
            plate = defaults.get('measure_plate')
        font.setPixelSize(size)
        font.setBold(bool(measured) and defaults.get('measure_bold'))
        p.setFont(font)
        w = p.fontMetrics().horizontalAdvance(text) + 10
        h = max(18, p.fontMetrics().height() + 4)
        rect = QRectF(point.x() - w / 2, point.y() - h / 2, w, h)
        if plate:
            back = QColor('#1d2430' if self.dark else '#ffffff')
            back.setAlpha(225)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(back)
            p.drawRoundedRect(rect, 5, 5)
        p.setPen(ink)
        p.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

    def draw_measurements(self, p, points):
        """Bond lengths on the model (option) and the length / angle / dihedral of the selection."""
        from azimuth import defaults

        atoms = self.molecule.atoms
        size, digits = defaults.get('measure_size'), defaults.get('measure_decimals')  # «Стиль измерений…»
        if self.show_lengths:
            hidden = self.hidden_atoms()
            for i, j, _ in connections(self.molecule):
                if i in hidden or j in hidden:
                    continue
                self._tag(p, (points[i][0] + points[j][0]) / 2,
                          f'{dist(atoms[i].position, atoms[j].position):.{digits}f}', size, True)
        from modules.compass.chemistry.geometry_tools import measurement

        ink = QColor('#6ea2f0' if self.dark else '#2a62b8')
        scanned = tuple(getattr(self, 'scan_pin', None) or ())  # the coordinate of a scan being browsed
        for sel in list(self.pinned) + ([scanned] if scanned and scanned not in self.pinned else []):
            if any(i >= len(atoms) for i in sel):
                continue
            ink = QColor(('#f0a24a' if self.dark else '#d97a16') if sel == scanned else
                         (defaults.get('measure_line_color') or ('#6ea2f0' if self.dark else '#2a62b8')))
            try:
                value = measurement([atoms[i].position for i in sel])
            except (ValueError, ZeroDivisionError):
                continue
            number = value[1] if isinstance(value, tuple) else value
            if number is None:
                continue
            p.setPen(QPen(ink, 1.2, Qt.PenStyle.DashLine))
            for a, b in zip(sel, sel[1:]):
                p.drawLine(points[a][0], points[b][0])
            angle = max(0, digits - 1)  # angles one decimal less than lengths (3 → 0.001 Å and 0.01°, as before)
            if len(sel) == 2:
                self._tag(p, (points[sel[0]][0] + points[sel[1]][0]) / 2 + QPointF(0, -14), f'{number:.{digits}f} Å',
                          size, True)
            elif len(sel) == 3:
                self._tag(p, points[sel[1]][0] + QPointF(0, -self.atom_radius(sel[1]) - 14), f'{number:.{angle}f}°',
                          size, True)
            else:
                self._tag(p, (points[sel[1]][0] + points[sel[2]][0]) / 2 + QPointF(0, -14),
                          f'φ {number:.{max(0, digits - 2)}f}°', size, True)

    def _arrow(self, p, start, end, ink, width=2.4):
        """A straight arrow on the screen from start to end (QPointF), head at end."""
        dx, dy = end.x() - start.x(), end.y() - start.y()
        length = hypot(dx, dy)
        if length < 2:
            return
        ux, uy = dx / length, dy / length
        head = min(12.0, 0.35 * length)
        p.setPen(QPen(ink, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(start, end - QPointF(ux * head * 0.6, uy * head * 0.6))
        from PySide6.QtGui import QPolygonF

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(ink)
        p.drawPolygon(
            QPolygonF(
                [
                    end,
                    end - QPointF(ux * head - uy * head * 0.45, uy * head + ux * head * 0.45),
                    end - QPointF(ux * head + uy * head * 0.45, uy * head - ux * head * 0.45),
                ]
            )
        )

    def draw_overlay(self, p, points):
        """Properties of a calculation result: values under the atoms, Mayer orders on the
        bonds (a dotted line where no bond is drawn), the dipole from the centre of the nuclei, forces."""
        shown = self.overlay_source(self.molecule)
        if not shown:
            return
        atoms = self.molecule.atoms
        legend = []
        if shown['bonds']:
            drawn = {(min(i, j), max(i, j)) for i, j, _ in connections(self.molecule)}
            ink = QColor('#9aa8b8' if self.dark else '#6f7d8c')
            for i, j, order in shown['bonds']:
                if (min(i, j), max(i, j)) not in drawn:
                    p.setPen(QPen(ink, 1.2, Qt.PenStyle.DotLine))
                    p.drawLine(points[i][0], points[j][0])
                self._tag(p, (points[i][0] + points[j][0]) / 2, f'{order:.2f}')
            kind = shown.get('bond_kind', 'Mayer')
            legend.append(tr(BOND_LEGENDS.get(kind, BOND_LEGENDS['Mayer'])))  # every kind by its name
        if shown['atom']:
            key, values = shown['atom']
            for i, value in enumerate(values):
                if value is None:  # an atom of a crystal with no atom of the calculation near it
                    continue
                if isinstance(value, str):  # the labels of a crystal (oxidation states, sites …)
                    text = value
                else:
                    text = f'{value:.2f}' if key in ('mayer-valence', 'bvs') else f'{value:+.3f}'.replace('-', '−')
                self._tag(p, points[i][0] + QPointF(0, self.atom_radius(i) + 11), text)
            from modules.compass.view.result_overlay import ATOM_VALUES, CRYSTAL_LABELS

            if key in CRYSTAL_LABELS:
                legend.append(tr(CRYSTAL_LABELS[key]))
            else:
                legend.append(tr(ATOM_VALUES[key][2]) + ('' if key == 'mayer-valence' else tr(', e')))
        if shown['dipole']:
            vector, debye = shown['dipole']
            size = sqrt(sum(c * c for c in vector))
            if size > 1e-6 and debye:
                centre = tuple(sum(a.position[k] for a in atoms) / len(atoms) for k in range(3))
                length = self.DIPOLE_LENGTH * debye
                tip = tuple(centre[k] + vector[k] / size * length for k in range(3))
                ink = QColor('#c08cff' if self.dark else '#7a3fd0')
                start, end = self.screen(centre), self.screen(tip)
                self._arrow(p, start, end, ink, 3.0)
                d = end - start
                n = max(1e-9, hypot(d.x(), d.y()))
                self._tag(p, end + QPointF(d.x() / n * 22, d.y() / n * 16), f'μ = {debye:.2f} D')  # beyond the tip
            legend.append(tr('Диполь: от − к +, длина ∝ |μ|') if debye else tr('Диполь: 0 D'))
        if shown['forces']:
            sizes = [sqrt(sum(c * c for c in f)) for f in shown['forces']]
            largest = max(sizes) if sizes else 0.0
            if largest > 0:
                ink = QColor('#ff8a5c' if self.dark else '#d0491b')
                for i, (force, size) in enumerate(zip(shown['forces'], sizes)):
                    if size < 0.02 * largest:
                        continue
                    start = atoms[i].position
                    end = tuple(start[k] + force[k] / largest * self.FORCE_LENGTH for k in range(3))
                    self._arrow(p, self.screen(start), self.screen(end), ink, 2.0)
            legend.append(tr(f'Силы: наибольшая {largest:.2e} Eh/бор'))
        if legend:
            font = QFont(self.font())
            font.setPixelSize(11)
            p.setFont(font)
            p.setPen(QColor('#b2c3cf' if self.dark else '#55667a'))
            y = self.height() - 12 - 15 * (len(legend) - 1)
            for line in legend:
                p.drawText(QPointF(14, y), line)
                y += 15

    # -- «Вид» ---------------------------------------------------------------------------------------------
    def draw_bond_labels(self, p, points):
        """The number of every bond (as in builder.connections, from 1) or its order (perceived from the valences:
        1, 2, 3, 1.5 aromatic) at its middle."""
        hidden = self.hidden_atoms()
        if self.bond_labels == 'order':
            from modules.compass.chemistry.editing import perceived_orders

            bonds = perceived_orders(self.molecule)
        else:
            bonds = connections(self.molecule)
        for k, (i, j, order) in enumerate(bonds, start=1):
            if i in hidden or j in hidden or i >= len(points) or j >= len(points):
                continue
            text = str(k) if self.bond_labels == 'number' else f'{order:g}'
            self._tag(p, (points[i][0] + points[j][0]) / 2, text, 10)

    def draw_vdw(self, p, points):
        """Translucent spheres of the van der Waals radii (Bondi 1964; 1.8 Å for the elements without one), shaded
        like a ball: a disc with a radial gradient, the nearer over the farther."""
        from PySide6.QtGui import QRadialGradient

        center, scale = self.camera()
        hidden = self.hidden_atoms()
        atoms = self.molecule.atoms
        for i in sorted(range(len(atoms)), key=lambda i: points[i][1]):
            if i in hidden or atoms[i].symbol == 'X':
                continue
            point, z = points[i]
            r = VDW_ALL.get(atoms[i].symbol, 1.8) * scale * self.depth_factor(z)
            base = QColor(self.palette.get(atoms[i].symbol, '#b0b8c4') if isinstance(self.palette, dict) else '#b0b8c4')
            glow = QRadialGradient(point - QPointF(r * 0.35, r * 0.35), r * 1.3)
            light, dark = QColor(base).lighter(140), QColor(base).darker(115)
            light.setAlpha(70)
            dark.setAlpha(40)
            glow.setColorAt(0, light)
            glow.setColorAt(1, dark)
            p.setBrush(glow)
            edge = QColor(base).darker(130)
            edge.setAlpha(90)
            p.setPen(QPen(edge, 1))
            p.drawEllipse(point, r, r)
        p.setBrush(Qt.BrushStyle.NoBrush)

    def draw_model_axes(self, p):
        """The axes X, Y, Z on the model: from the centre of the molecule or from the origin (0, 0, 0), as long as
        the molecule is wide (at least 2 Å)."""
        atoms = self.molecule.atoms
        if not atoms:
            return
        centre = tuple(sum(a.position[k] for a in atoms) / len(atoms) for k in range(3))
        start = (0.0, 0.0, 0.0) if self.axes_place == 'origin' else centre
        length = max(2.0, max(dist(a.position, centre) for a in atoms) + 0.8)
        for name, vector, color in (('X', (1, 0, 0), '#d65454'), ('Y', (0, 1, 0), '#2ca77a'),
                                    ('Z', (0, 0, 1), '#528edf')):
            end = tuple(start[k] + vector[k] * length for k in range(3))
            a, b = self.screen(start), self.screen(end)
            self._arrow(p, a, b, QColor(color), 1.8)
            p.setPen(QColor(color))
            p.setFont(QFont('Arial', 10, QFont.Weight.Bold))
            p.drawText(b + QPointF(5, -4), name)

    def draw_guides(self, p):
        """The vectors (arrows), normals (arrows from the centre) and planes (translucent sheets) of «Правка →
        Векторы и плоскости», each with its number — the number of the list of «Углы между…» and of the text."""
        from PySide6.QtGui import QPolygonF

        from azimuth import defaults
        from modules.compass.chemistry import guides as made

        # «Стиль векторов и плоскостей…» — the colour of each kind (else that of the theme), whether it is
        # shown, the width of the lines, the fill of a plane and its edge, the numbers
        width = defaults.get('guide_width')
        for number, guide in enumerate(self.guides, start=1):
            kind = guide['kind']
            if not defaults.get(f'guide_{kind}_show'):
                continue
            try:
                shape = made.geometry(guide, self.molecule)
            except ValueError:
                shape = None
            if shape is None:
                continue
            ink = QColor(defaults.get(f'guide_{kind}_color') or self.GUIDE_INKS[kind][1 if self.dark else 0])
            if shape['kind'] == 'plane':
                fill = QColor(ink)
                fill.setAlpha(round(255 * defaults.get('guide_plane_opacity') / 100))
                p.setBrush(fill)
                p.setPen(QPen(ink, max(0.5, width * 0.6)) if defaults.get('guide_plane_edge') else Qt.PenStyle.NoPen)
                p.drawPolygon(QPolygonF([self.screen(c) for c in shape['corners']]))
                p.setBrush(Qt.BrushStyle.NoBrush)
                at = self.screen(shape['corners'][2])
            else:
                start, end = self.screen(shape['start']), self.screen(shape['end'])
                self._arrow(p, start, end, ink, width)
                at = end
            if defaults.get('guide_numbers'):
                self._tag(p, at + QPointF(10, -8), str(number))

    def draw_constraints(self, p, points):
        """Frozen atoms: an orange dashed ring; a fixed length / angle / dihedral: an orange dashed path."""
        ink = QColor('#f0a24a' if self.dark else '#d97a16')
        for kind, atoms in self.constraints:
            if any(i >= len(points) for i in atoms):
                continue
            if kind == 'C':
                i = atoms[0]
                r = self.atom_radius(i) + 9
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(QPen(ink, 2, Qt.PenStyle.DashLine))
                p.drawEllipse(points[i][0], r, r)
            else:
                p.setPen(QPen(ink, 2.4, Qt.PenStyle.DashLine, Qt.PenCapStyle.RoundCap))
                for a, b in zip(atoms, atoms[1:]):
                    p.drawLine(points[a][0], points[b][0])
                for i in atoms:
                    p.setBrush(ink)
                    p.setPen(Qt.PenStyle.NoPen)
                    p.drawEllipse(points[i][0], 3, 3)

    def draw_ghost(self, p):
        """The starting positions of the nuclei: pale atoms, dashed bonds, thin lines to where they went."""
        center, scale = self.camera()
        points = []
        for atom in self.ghost.atoms:
            x, y, z = self.to_view(tuple(atom.position[k] - center[k] for k in range(3)))
            f = self.depth_factor(z)
            points.append(
                (
                    QPointF(
                        self.width() / 2 + self.pan.x() + x * scale * f,
                        self.height() / 2 + self.pan.y() - y * scale * f,
                    ),
                    f,
                )
            )
        ink = QColor('#9aa8b8' if self.dark else '#7d8b9b')
        pen = QPen(ink, 1.6, Qt.PenStyle.DashLine, Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        for i, j, _ in connections(self.ghost):
            p.drawLine(points[i][0], points[j][0])
        now = self.projected()
        if len(now) == len(points):
            trail = QColor(ink)
            trail.setAlpha(110)
            p.setPen(QPen(trail, 1, Qt.PenStyle.DotLine))
            for (a, _), (b, _) in zip(points, now):
                p.drawLine(a, b)
        for (point, f), atom in zip(points, self.ghost.atoms):
            radius = (
                VDW_RADII.get(atom.symbol, 1.8)
                if self.display_mode == 'spacefill'
                else (0.09 if self.display_mode == 'sticks' else (0.17 if atom.symbol == 'H' else 0.24))
            )
            r = max(2, scale * radius * f) * 0.85
            fill = QColor(self.palette.get(atom.symbol, '#9c80b7'))
            fill.setAlpha(55)
            edge = QColor(self.palette.get(atom.symbol, '#9c80b7'))
            edge.setAlpha(170)
            p.setBrush(fill)
            p.setPen(QPen(edge, 1.2, Qt.PenStyle.DashLine))
            p.drawEllipse(point, r, r)

    draw_cell = _crystal.draw_cell
    draw_lattice_points = _crystal.draw_lattice_points
    draw_lattice_planes = _crystal.draw_lattice_planes

    SYMMETRY_INK = {'axis': ('#2e8b57', '#5fd39a'), 'screw': ('#2e8b57', '#5fd39a'), 'mirror': ('#2a62b8', '#6ea2f0'),
                    'glide': ('#2a62b8', '#6ea2f0'), 'point': ('#b8893f', '#d6a95c')}

    draw_symmetry = _crystal.draw_symmetry
    draw_ellipsoids = _crystal.draw_ellipsoids

    RING_INK = '#c46ad6'  # the rings, their centroids and the π contacts

    draw_ring_marks = _crystal.draw_ring_marks

    FRAME_ATTRACTIVE, FRAME_REPULSIVE = '#2f7fd0', '#d0503f'  # the energy framework

    draw_energy_frame = _crystal.draw_energy_frame
    draw_polyhedra = _crystal.draw_polyhedra

    def draw_compare(self, p, points):
        """The compared structure over the model: rings and dashed bonds in one colour, dotted lines from
        each atom of the model to its partner; the caption at the top right (also in snapshots)."""
        ghost, caption = self.compare_source(self.molecule)
        ink = QColor(self.COMPARE_INK[1 if self.dark else 0])
        if ghost is not None and len(ghost.atoms) == len(points):
            center, scale = self.camera()
            spots = []
            for atom in ghost.atoms:
                x, y, z = self.to_view(tuple(atom.position[k] - center[k] for k in range(3)))
                f = self.depth_factor(z)
                spots.append(
                    (QPointF(self.width() / 2 + self.pan.x() + x * scale * f, self.height() / 2 + self.pan.y() - y * scale * f), f)
                )
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(ink, 1.8, Qt.PenStyle.DashLine, Qt.PenCapStyle.RoundCap))
            for i, j, _ in connections(ghost):
                p.drawLine(spots[i][0], spots[j][0])
            trail = QColor(ink)
            trail.setAlpha(150)
            p.setPen(QPen(trail, 1.1, Qt.PenStyle.DotLine))
            for (a, _), (b, _) in zip(spots, points):
                p.drawLine(a, b)
            p.setPen(QPen(ink, 1.4))
            for (point, f), atom in zip(spots, ghost.atoms):
                radius = 0.09 if self.display_mode == 'sticks' else (0.17 if atom.symbol == 'H' else 0.24)
                r = max(3, scale * radius * f) * 0.8
                p.drawEllipse(point, r, r)
        if caption:
            font = QFont(self.font())
            font.setPixelSize(12)
            p.setFont(font)
            p.setPen(ink)
            y = 104 if self.show_axes else 8  # under the axes, which are top right now
            for line in caption:
                p.drawText(QRectF(0, y, self.width() - 14, 16), Qt.AlignmentFlag.AlignRight, line)
                y += 16
