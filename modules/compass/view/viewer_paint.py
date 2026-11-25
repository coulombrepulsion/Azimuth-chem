"""The painting of the Compass view (MoleculeView): the labels of the atoms, the layers under and over the model,
the silhouette, what is painted over the native (VTK) picture. Methods of MoleculeView (self is the view), kept here
to make viewer.py shorter; the model itself is drawn by viewer_drawing.py and bond_depth.py.

Split off modules/compass/view/viewer.py (0.222.29).
"""

from math import hypot
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QPainter, QPen, QFont
from modules.compass.view.bond_depth import draw_model


def shown_symbol(self, index):
    """The element of an atom as its label shows it — an isotope by its name (D, T, ¹³C …)."""
    symbol = self.molecule.atoms[index].symbol
    source = self.isotope_source
    if source is None:
        return symbol
    text = source() or ''
    if not text:
        return symbol
    from azimuth.core import isotope_masses, isotope_name

    key = (text, id(self.molecule))
    if getattr(self, '_isotope_cache', (None,))[0] != key:
        self._isotope_cache = (key, isotope_masses(text, self.molecule))
    mass = self._isotope_cache[1].get(index)
    return isotope_name(symbol, mass) if mass else symbol


def atom_label(self, index):
    if self.label_mode == 'none':
        return ''
    symbol = self.shown_symbol(index)
    if self.label_mode == 'number':
        return str(index + 1)
    if self.label_mode == 'both':
        return f'{symbol}{index + 1}'
    if self.label_mode == 'group':  # the number within the element — C1, C2, H1, H2
        return f'{symbol}{sum(1 for a in self.molecule.atoms[:index + 1] if a.symbol == symbol)}'
    return symbol


def paintEvent(self, event):
    if self.gliding() and not self.capture:  # the picture of the field lies over it
        return
    if self.native_active() and not self.capture:
        # the VTK widget and the overlay cover the field; still the colour of the field under them,
        # so that a widget that has not drawn yet never shows an old picture of another page
        p = QPainter(self)
        p.fillRect(self.rect(), self.field_color())
        p.end()
        return
    self._paint_camera = None
    self._paint_camera = self.camera()
    # a white or black background of the scheme: everything drawn uses the matching inks
    theme_dark = self.dark
    if self.background != 'theme':
        self.dark = self.background == 'black'
    try:
        self._paint(event)
    finally:
        self.dark = theme_dark
        self._paint_camera = None


def field_color(self):
    """The colour of the empty field (theme or the scheme's white / black background)."""
    fill = {'white': '#ffffff', 'black': '#000000'}.get(self.background)
    return QColor(fill or ('#11151c' if self.dark else '#f5f6f8'))


def _paint(self, event):
    p = QPainter(self)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    if self.capture and self.transparent:
        p.fillRect(self.rect(), Qt.GlobalColor.transparent)
    else:
        p.fillRect(self.rect(), self.field_color())
    under = self._paint_under(p)
    if under is None:
        return
    points, shown = under
    draw_model(self, p, points, self.palette)  # spheres and bonds, per-pixel depth
    self._paint_over(p, points, shown)


def _paint_under(self, p):
    """What lies under the model: the grid, axes, cell, start structure, hydrogen bonds and
    the far half of a surface. None (and the hint) for an empty field, else (points, surface triangles)."""
    # dot grid: a little stronger than before in both themes
    p.setPen(QPen(QColor('#3a4757' if self.dark else '#c3c9d3'), 1))
    if not self.capture and self.grid:  # the dot grid is for the screen only
        for x in range(24, self.width(), 30):
            for y in range(24, self.height(), 30):
                p.drawPoint(x, y)
    if self.show_axes:
        self.draw_axes(p)
    if self.cell_lines:
        self.draw_cell(p)
    if self.lattice_planes:
        self.draw_lattice_planes(p)
    if self.symmetry_items:
        self.draw_symmetry(p)
    if self.lattice_points:
        self.draw_lattice_points(p)
    if self.polyhedra and self.molecule and self.molecule.atoms:
        self.draw_polyhedra(p)
    if self.ring_marks and self.molecule and self.molecule.atoms:
        self.draw_ring_marks(p)
    if self.energy_frame and self.molecule and self.molecule.atoms:
        self.draw_energy_frame(p)
    if self.ellipsoids and self.molecule and self.molecule.atoms:
        self.draw_ellipsoids(p)
    if self.ghost is not None and self.molecule and self.molecule.atoms:
        self.draw_ghost(p)
    if self.show_hbonds and self.molecule and self.molecule.atoms:
        self.draw_hbonds(p)
    if self.found_contacts and self.molecule and self.molecule.atoms:
        self.draw_aim_contacts(p)
    if not self.molecule or not self.molecule.atoms:
        self.draw_empty(p)  # a short hint with the pencil and the folder; Quill moved to the right panel
        return None
    points = self.projected()
    # the far half of a surface under the model, the near half over it; none when VTK draws
    # the surface in the window together with the model (vtk_view.py), only its legend is painted
    shown = None if getattr(self, '_vtk_surfaces', False) else self.surface_triangles()
    if shown:
        # the dots of the field do not shine through the surface; not while the view moves (one
        # more pass over every triangle a frame)
        if not self.capture and self.grid and not self.interactive():
            self.draw_surface_veil(p, shown)
        self.draw_surface(p, shown, front=False)
    return points, shown


def _paint_over(self, p, points, shown):
    """What lies over the model: the near half of a surface, selection rings, labels, overlays, measurements,
    the band."""
    atoms = self.molecule.atoms
    if shown:
        self.draw_surface(p, shown, front=True)
    elif getattr(self, '_vtk_surfaces', False) and self.surface_meshes()[0]:
        self.draw_surface_legend(p)
    if self.show_vdw:
        self.draw_vdw(p, points)
    # Selection rings over the model: the ring of an atom behind others is cut by the disks of the atoms in
    # front of it, so it does not lie over them (ring_clip).
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(QColor('#6ea2f0' if self.dark else '#2a62b8'), 3))
    ring_radii = [self.atom_radius(k) for k in range(len(atoms))] if self.selected else []
    for i in self.selected:
        if 0 <= i < len(atoms):
            r = ring_radii[i]
            clip = self.ring_clip(i, points, ring_radii, r + 7)
            if clip is not None:
                p.save()
                p.setClipRegion(clip)
            p.drawEllipse(points[i][0], r + 5, r + 5)
            if clip is not None:
                p.restore()
    self.draw_aim(p)
    self.draw_surface_markers(p)
    # Labels remain centred and readable over front-facing bonds. A label is cut by the atoms
    # in front of its own (label_clip), so an atom hidden behind another no longer shows its label through.
    radii = [self.atom_radius(i) for i in range(len(atoms))]
    hidden = self.hidden_atoms()
    from azimuth import defaults

    grow = defaults.get('label_scale')  # «Стиль подписей…»
    chosen = set(self.selected)
    labelled = [i for i in range(len(atoms)) if i not in hidden and (not self.labels_selected_only or i in chosen)]
    covers = self.label_covers(points, radii, labelled) if labelled else {}  # once per frame
    for i in sorted(labelled, key=lambda i: points[i][1]):
        atom = atoms[i]
        point = points[i][0]
        r = radii[i]
        clip = self.label_clip(i, points, radii, covers)
        if clip is not None and clip.isEmpty():
            continue  # entirely behind nearer atoms
        p.save()
        if clip is not None:
            p.setClipRegion(clip)
        text = self.atom_label(i)
        self.draw_atom_label(p, point, r, text, atom.symbol, grow)
        p.restore()
    self.draw_dummies(p, points, radii)
    self.draw_custom_labels(p, points, radii)
    if self.bond_labels:
        self.draw_bond_labels(p, points)
    if self.axes_place != 'corner' and self.show_axes:
        self.draw_model_axes(p)
    if self.overlay_source is not None:
        self.draw_overlay(p, points)
    if self.compare_source is not None:
        self.draw_compare(p, points)
    if self.constraints:
        self.draw_constraints(p, points)
    self.draw_measurements(p, points)
    if self.guides:
        self.draw_guides(p)
    if self.band is not None:
        ink = QColor('#6ea2f0' if self.dark else '#2a62b8')
        fill = QColor(ink)
        fill.setAlpha(28)
        p.setBrush(fill)
        p.setPen(QPen(ink, 1, Qt.PenStyle.DashLine))
        p.drawRect(self.band)


def draw_atom_label(self, p, point, r, text, symbol, grow):
    """The label of an atom in the style of «Стиль подписей…»: its font (Arial by default), bold,
    italic, colour (by default white on a coloured atom, dark on hydrogen; beside the atom — the ink of the
    theme), an outline of the other colour, on the atom (shrunk to fit it) or beside it (up to the right)."""
    from PySide6.QtGui import QPainterPath, QPen

    from azimuth import defaults

    family = defaults.get('label_font') or 'Arial'
    beside = defaults.get('label_place') == 'beside'
    chosen = defaults.get('label_color')
    if chosen:
        ink = QColor(chosen)
    elif beside:
        ink = QColor('#e7eaf0' if self.dark else '#1b2230')
    else:
        ink = QColor('#344354') if symbol == 'H' else QColor('white')
    font = QFont(family)
    font.setBold(defaults.get('label_bold'))
    font.setItalic(defaults.get('label_italic'))
    font.setPixelSize(max(8, int(r * 0.9 * grow)))
    p.setFont(font)
    if beside:
        font.setPixelSize(max(9, int(min(r, 16) * 0.95 * grow)))
        p.setFont(font)
        metrics = p.fontMetrics()
        box = QRectF(point.x() + r * 0.72, point.y() - r * 0.72 - metrics.height() * 0.8,
                     metrics.horizontalAdvance(text) + 4, metrics.height())
    else:
        # the size that fits the atom is kept for the label, the font and the size asked — it was measured
        # anew (a QFontMetrics a pixel) for every atom of every frame, also while the view or a panel moves
        limit = r * 1.65 * max(1.0, grow)
        key = (family, font.bold(), font.italic(), text, font.pixelSize(), int(limit))
        sizes = self.__dict__.setdefault('_label_sizes', {})
        fitted = sizes.get(key)
        if fitted is None:
            while p.fontMetrics().horizontalAdvance(text) > limit and font.pixelSize() > 5:
                font.setPixelSize(font.pixelSize() - 1)
                p.setFont(font)
            if len(sizes) > 4000:
                sizes.clear()
            sizes[key] = font.pixelSize()
        elif fitted != font.pixelSize():
            font.setPixelSize(fitted)
            p.setFont(font)
        box = QRectF(point.x() - r, point.y() - r, 2 * r, 2 * r)
    if defaults.get('label_outline'):
        metrics = p.fontMetrics()
        x = box.center().x() - metrics.horizontalAdvance(text) / 2
        y = box.center().y() + (metrics.ascent() - metrics.descent()) / 2
        path = QPainterPath()
        path.addText(x, y, font, text)
        halo = QColor('#000000' if ink.lightness() > 140 else '#ffffff')
        halo.setAlpha(200)
        p.setRenderHint(p.RenderHint.Antialiasing)
        p.strokePath(path, QPen(halo, max(2.0, font.pixelSize() / 6.0)))
        p.fillPath(path, ink)
        return
    p.setPen(ink)
    p.drawText(box, Qt.AlignmentFlag.AlignCenter, text)


def paint_silhouette(self, p, points, radii=None):
    """Fill the discs of the atoms and the quads of the bonds (the pixels of the model) with the painter's
    brush — the geometry of ornament_cover."""
    from PySide6.QtCore import QPointF as _P
    from PySide6.QtGui import QPolygonF

    radii = radii if radii is not None else [self.atom_radius(k) for k in range(len(points))]
    hidden = self.hidden_atoms()
    for k, ((pt, _), r) in enumerate(zip(points, radii)):
        if k not in hidden:
            p.drawEllipse(pt, r + 0.5, r + 0.5)
    if self.display_mode != 'spacefill' and self.show_bonds:
        half = max(1.0, self.bond_width * self.camera()[1] * 0.08) / 2 + 0.5
        for i, j, order in self.drawn_bonds(hidden):
            a, b = points[i][0], points[j][0]
            dx, dy = b.x() - a.x(), b.y() - a.y()
            length = hypot(dx, dy)
            if length < 1:
                continue
            count = order if self.multiple_bonds else 1
            span = half + (count - 1) / 2 * 2 * (half - 0.5) * 1.5  # out to the outer rods of a multiple bond (build_scene)
            ox, oy = -dy / length * span, dx / length * span
            p.drawPolygon(QPolygonF([_P(a.x() + ox, a.y() + oy), _P(b.x() + ox, b.y() + oy), _P(b.x() - ox, b.y() - oy), _P(a.x() - ox, a.y() - oy)]))


def paint_over_native(self, device):
    """VTK draws the background and the model in a child widget; this paints the rest on the transparent
    overlay above it. What the built-in renderer draws under the model is painted into an image whose model
    pixels are cleared, so on screen it still lies under the model."""
    from PySide6.QtGui import QImage

    self._paint_camera = self.camera()
    theme_dark = self.dark
    if self.background != 'theme':
        self.dark = self.background == 'black'
    self._vtk_surfaces = True  # VTK draws the surface (vtk_view.NativeModel)
    try:
        ratio = device.devicePixelRatioF()
        image = QImage(max(1, round(self.width() * ratio)), max(1, round(self.height() * ratio)), QImage.Format.Format_ARGB32_Premultiplied)
        image.setDevicePixelRatio(ratio)
        image.fill(0)
        q = QPainter(image)
        q.setRenderHint(QPainter.RenderHint.Antialiasing)
        under = self._paint_under(q)
        if under is not None:
            points, shown = under
            q.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            q.setPen(Qt.PenStyle.NoPen)
            q.setBrush(QColor('black'))
            self.paint_silhouette(q, points)
            if self.grid:  # the dots over the surface of VTK are mostly erased — they shone through it
                self.erase_under_surface(q)
        q.end()
        p = QPainter(device)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.drawImage(0, 0, image)
        if under is not None:
            self._paint_over(p, points, shown)
        p.end()
    finally:
        self.dark = theme_dark
        self._paint_camera = None
        self._vtk_surfaces = False
