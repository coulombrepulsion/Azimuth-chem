"""The surface on the model of Compass: its meshes in the pixels of the view, the triangles shaded, the veil of its
silhouette, the legend and the extrema of the ESP. Methods of ViewerDrawing (self is the view), kept here to make
viewer_drawing.py shorter.

Split off modules/compass/view/viewer_drawing.py (0.222.30).
"""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from azimuth.i18n import tr


FINE_TRIANGLES = 400_000  # a surface drawn by VTK keeps up to this many triangles (QPainter: surfaces.TARGET)


SURFACE_MOVING = 2500  # the triangles of a surface drawn while the view moves (the rest when it stops)


def draw_surface_markers(self, p):
    """The extrema of the ESP of Multiwfn on its surface (surface['markers']: (xyz Å, colour, label,
    global)) — dots with the value in kcal/mol, while the surface belongs to the structure shown."""
    import numpy as np

    s = self.surface
    if not s or not s.get('markers') or not self.molecule or self.molecule.atoms != s['atoms']:
        return
    font = QFont(self.font())
    font.setPixelSize(11)
    p.save()
    p.setFont(font)
    edge = QColor('#10151c' if self.dark else '#ffffff')
    ink = QColor('#e6ebf2' if self.dark else '#1f2a36')
    for position, colour, label, top in s['markers']:
        x, y, _ = self.project_vertices(np.asarray(position, float)[None])[0]
        r = 5.5 if top else 3.8
        p.setPen(QPen(edge, 1.2))
        p.setBrush(QColor(colour))
        p.drawEllipse(QPointF(float(x), float(y)), r, r)
        if top or len(s['markers']) <= 8:
            p.setPen(ink)
            p.drawText(QPointF(float(x) + r + 3, float(y) + 4), label)
    p.restore()


# -- the surface for VTK -------------------------------------------------------------------------------
def surface_meshes(self, fine=True):
    """(meshes, opacity) of the surface while it belongs to the structure shown, else ([], None). fine: the
    meshes without decimation (built once on demand by surface_actions, 'build'), for drawing on the graphics
    card; the decimated ones (surfaces.TARGET) stay for QPainter."""
    s = self.surface
    if not s or not self.molecule or self.molecule.atoms != s['atoms']:
        return [], None
    meshes = s['meshes']
    if fine and s.get('build') is not None:
        if s.get('fine') is None:
            try:
                s['fine'] = s['build'](FINE_TRIANGLES) or meshes
            except Exception:  # noqa: BLE001 — the decimated surface is good enough
                s['fine'] = meshes
        meshes = s['fine']
    return meshes, s.get('opacity', 0.55)


def project_vertices(self, vertices, ratio=1.0):
    """(n, 3) points of the structure (Å) in output pixels as model_scene puts the atoms: x right, y down,
    z towards the viewer (z · scale · depth factor), all times ratio."""
    import numpy as np

    center, scale = self.camera()
    v = (np.asarray(vertices, float) - np.asarray(center, float)) @ self.view_matrix()
    if self.perspective:
        distance = max(8.0, min(self.width(), self.height()) / (scale / self.zoom) * 1.5)
        factor = distance / np.maximum(distance * 0.15, distance - v[:, 2])
    else:
        factor = np.ones(len(v))
    x = self.width() / 2 + self.pan.x() + v[:, 0] * scale * factor
    y = self.height() / 2 + self.pan.y() - v[:, 1] * scale * factor
    return np.column_stack((x, y, v[:, 2] * scale * factor)) * ratio


def surface_triangles(self):
    """[(screen polygon (3, 2), depth, shade, (r, g, b))] of the surface for this frame, or None.
    The surface belongs to one structure: drawn only while the atoms are those it was built for."""
    import numpy as np

    s = self.surface
    if not s or not self.molecule or self.molecule.atoms != s['atoms']:
        return None
    center, scale = self.camera()
    T = self.view_matrix()
    out = []
    for mesh in s['meshes']:
        v = (mesh.vertices - np.asarray(center, float)) @ T
        if self.perspective:
            factor = np.array([self.depth_factor(z) for z in v[:, 2]])
        else:
            factor = np.ones(len(v))
        sx = self.width() / 2 + self.pan.x() + v[:, 0] * scale * factor
        sy = self.height() / 2 + self.pan.y() - v[:, 1] * scale * factor
        tri = mesh.triangles
        a, b, c = v[tri[:, 0]], v[tri[:, 1]], v[tri[:, 2]]
        n = np.cross(b - a, c - a)
        length = np.linalg.norm(n, axis=1)
        nz = np.abs(n[:, 2]) / np.maximum(length, 1e-12)
        shade = 0.45 + 0.55 * nz
        depth = (a[:, 2] + b[:, 2] + c[:, 2]) / 3
        if mesh.colors is not None:
            rgb = (mesh.colors[tri[:, 0]] + mesh.colors[tri[:, 1]] + mesh.colors[tri[:, 2]]) / 3
        else:
            base = QColor(mesh.color)
            rgb = np.tile((base.redF(), base.greenF(), base.blueF()), (len(tri), 1))
        xs = np.stack((sx[tri], sy[tri]), axis=2)  # (m, 3, 2)
        out.append((xs, depth, shade, rgb))
    if not out:
        return None
    polygons = np.concatenate([o[0] for o in out])
    depth = np.concatenate([o[1] for o in out])
    shade = np.concatenate([o[2] for o in out])
    rgb = np.concatenate([o[3] for o in out])
    order = np.argsort(depth)  # far (small z) first
    return polygons[order], depth[order], shade[order], rgb[order]


def draw_surface_veil(self, p, shown):
    """The silhouette of the surface in the colour of the field over the dot grid, once (a layer of its own:
    the triangles lying over each other do not darken it more), SURFACE_VEIL of it — the dots stay faintly seen."""
    from PySide6.QtGui import QImage, QPolygonF

    polygons = shown[0]
    if not len(polygons):
        return
    ratio = self.devicePixelRatioF()
    layer = QImage(max(1, round(self.width() * ratio)), max(1, round(self.height() * ratio)),
                   QImage.Format.Format_ARGB32_Premultiplied)
    layer.setDevicePixelRatio(ratio)
    layer.fill(Qt.GlobalColor.transparent)
    q = QPainter(layer)
    q.setPen(Qt.PenStyle.NoPen)
    q.setBrush(self.field_color())
    for poly in polygons:
        q.drawPolygon(QPolygonF([QPointF(poly[0][0], poly[0][1]), QPointF(poly[1][0], poly[1][1]),
                                 QPointF(poly[2][0], poly[2][1])]))
    q.end()
    p.save()
    p.setOpacity(self.SURFACE_VEIL)
    p.drawImage(QPointF(0, 0), layer)
    p.restore()


def erase_under_surface(self, q):
    """SURFACE_VEIL of what the overlay image has under the silhouette of the surface is taken away."""
    from PySide6.QtGui import QImage, QPolygonF

    if self.interactive():  # not while the view moves
        return
    shown = self.surface_triangles()
    if not shown or not len(shown[0]):
        return
    device = q.device()
    ratio = device.devicePixelRatioF() if hasattr(device, 'devicePixelRatioF') else 1.0
    layer = QImage(max(1, round(self.width() * ratio)), max(1, round(self.height() * ratio)),
                   QImage.Format.Format_ARGB32_Premultiplied)
    layer.setDevicePixelRatio(ratio)
    layer.fill(Qt.GlobalColor.transparent)
    m = QPainter(layer)
    m.setPen(Qt.PenStyle.NoPen)
    m.setBrush(QColor('black'))
    for poly in shown[0]:
        m.drawPolygon(QPolygonF([QPointF(poly[0][0], poly[0][1]), QPointF(poly[1][0], poly[1][1]),
                                 QPointF(poly[2][0], poly[2][1])]))
    m.end()
    q.save()
    q.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationOut)
    q.setOpacity(self.SURFACE_VEIL)
    q.drawImage(QPointF(0, 0), layer)
    q.restore()


def draw_surface(self, p, shown, front):
    from PySide6.QtGui import QPolygonF

    polygons, depth, shade, rgb = shown
    alpha = int(255 * self.surface.get('opacity', 0.55))
    p.save()
    p.setPen(Qt.PenStyle.NoPen)
    picked = range(len(depth))
    # while the view moves, an even share of them, each grown about its centre to close the gaps; the whole surface
    # when it stops
    if len(depth) > SURFACE_MOVING and self.interactive():
        import numpy as np

        picked = np.linspace(0, len(depth) - 1, SURFACE_MOVING).astype(int)
        grow = min(3.0, (len(depth) / SURFACE_MOVING) ** 0.5)
        centres = polygons[picked].mean(axis=1, keepdims=True)
        polygons = polygons.copy()
        polygons[picked] = centres + (polygons[picked] - centres) * grow
    for k in picked:
        if (depth[k] >= 0) != front:
            continue
        r, g, b = (min(1.0, c * shade[k]) for c in rgb[k])
        p.setBrush(QColor.fromRgbF(r, g, b, alpha / 255))
        poly = polygons[k]
        p.drawPolygon(QPolygonF([QPointF(poly[0][0], poly[0][1]), QPointF(poly[1][0], poly[1][1]), QPointF(poly[2][0], poly[2][1])]))
    p.restore()
    if front:
        self.draw_surface_legend(p)


def draw_surface_legend(self, p):
    s = self.surface
    text = s.get('legend', '')
    limit = s.get('limit')
    font = QFont(self.font())
    font.setPixelSize(11)
    p.setFont(font)
    ink = QColor('#b2c3cf' if self.dark else '#55667a')
    x = self.width() - 210
    y = self.height() - 54
    if limit is not None:  # the ESP scale: red − … white … blue +
        from PySide6.QtGui import QLinearGradient

        gradient = QLinearGradient(x, 0, x + 180, 0)
        gradient.setColorAt(0.0, QColor('#d7302f'))
        gradient.setColorAt(0.5, QColor('#ffffff'))
        gradient.setColorAt(1.0, QColor('#2c64c8'))
        p.setPen(QPen(ink, 1))
        p.setBrush(gradient)
        p.drawRect(QRectF(x, y, 180, 10))
        kcal = limit * 627.5094740631
        p.drawText(QRectF(x - 20, y + 12, 80, 16), Qt.AlignmentFlag.AlignLeft, f'−{kcal:.0f}')
        p.drawText(QRectF(x + 120, y + 12, 80, 16), Qt.AlignmentFlag.AlignRight, f'+{kcal:.0f}')
        p.drawText(QRectF(x, y + 12, 180, 16), Qt.AlignmentFlag.AlignHCenter, tr('ккал/моль'))
    if s.get('scale') == 'range' and s.get('range'):  # ALIE, LEA… — low blue, high red
        from PySide6.QtGui import QLinearGradient

        low, high, unit = s['range']
        gradient = QLinearGradient(x, 0, x + 180, 0)
        gradient.setColorAt(0.0, QColor('#2c64c8'))
        gradient.setColorAt(0.5, QColor('#ffffff'))
        gradient.setColorAt(1.0, QColor('#d7302f'))
        p.setPen(QPen(ink, 1))
        p.setBrush(gradient)
        p.drawRect(QRectF(x, y, 180, 10))
        p.drawText(QRectF(x - 20, y + 12, 80, 16), Qt.AlignmentFlag.AlignLeft, f'{low:.2f}')
        p.drawText(QRectF(x + 120, y + 12, 80, 16), Qt.AlignmentFlag.AlignRight, f'{high:.2f}')
        p.drawText(QRectF(x, y + 12, 180, 16), Qt.AlignmentFlag.AlignHCenter, unit)
    if s.get('scale') == 'nci':  # sign(λ₂)ρ, blue — green — red (surfaces.NCI_LOW … NCI_HIGH)
        from PySide6.QtGui import QLinearGradient

        from modules.compass.view import surfaces

        gradient = QLinearGradient(x, 0, x + 180, 0)
        for t, rgb in ((0.0, surfaces.NCI_BLUE), (0.5, surfaces.NCI_GREEN), (1.0, surfaces.NCI_RED)):
            gradient.setColorAt(t, QColor.fromRgbF(*rgb))
        p.setPen(QPen(ink, 1))
        p.setBrush(gradient)
        p.drawRect(QRectF(x, y, 180, 10))
        p.drawText(QRectF(x - 20, y + 12, 80, 16), Qt.AlignmentFlag.AlignLeft, f'{surfaces.NCI_LOW:g}'.replace('-', '−'))
        p.drawText(QRectF(x + 120, y + 12, 80, 16), Qt.AlignmentFlag.AlignRight, f'+{surfaces.NCI_HIGH:g}')
        p.drawText(QRectF(x, y + 12, 180, 16), Qt.AlignmentFlag.AlignHCenter, tr('sign(λ₂)ρ, а. е.'))
        p.drawText(QRectF(x - 40, y - 18, 260, 16), Qt.AlignmentFlag.AlignHCenter,
                   tr('Н-связь · ван-дер-Ваальс · отталкивание'))
    if text:
        p.setPen(ink)
        p.drawText(QRectF(10, 8, self.width() - 20, 18), Qt.AlignmentFlag.AlignRight, text)
