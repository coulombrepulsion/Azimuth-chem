"""The camera of the Compass view (MoleculeView): centring, the best view, looking along a direction, zoom and pan,
the turns, the inset of a drawer, and the field as SVG, PDF or a picture. Methods of MoleculeView (self is the view),
kept here to make viewer.py shorter.

Split off modules/compass/view/viewer.py (0.222.30).
"""

from math import sin, cos, dist, sqrt
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QPainter
from modules.compass.chemistry.geometry_tools import cross, dot, unit, sub
from azimuth.i18n import tr


def center_view(self):
    self.zoom = 1.0
    self.pan = QPointF(self.inset / 2, 0)  # the middle of the part of the field the drawer leaves free
    self.locked_camera = None
    self.update()


def best_view(self):
    if not self.molecule or len(self.molecule.atoms) < 2:
        return
    positions = [a.position for a in self.molecule.atoms]
    a = max(positions, key=lambda p: dist(p, positions[0]))
    b = max(positions, key=lambda p: dist(p, a))
    if dist(a, b) < 1e-10:
        return
    x = unit(sub(b, a))
    vectors = [sub(p, a) for p in positions]
    v = max(vectors, key=lambda v: dot(cross(x, v), cross(x, v)))
    normal = cross(x, v)
    if dot(normal, normal) < 1e-12:
        helper = min([(1, 0, 0), (0, 1, 0), (0, 0, 1)], key=lambda v: abs(dot(x, v)))
        normal = cross(x, helper)
    z = unit(normal)
    y = cross(z, x)
    self.basis = (x, y, z)
    self.yaw = self.pitch = self.roll = 0.0
    self.center_view()


def look_along(self, direction, right=None):
    """Standard view: the line of sight along direction (it points to the viewer), right — a
    vector shown to the right (its part across the line of sight), else the cell axis most across it."""
    n = sqrt(dot(direction, direction))
    if n < 1e-10:
        return False
    z = tuple(c / n for c in direction)
    if right is not None:
        r = tuple(right[k] - dot(right, z) * z[k] for k in range(3))
    else:
        r = (0.0, 0.0, 0.0)
    if dot(r, r) < 1e-12:
        helper = min([(1, 0, 0), (0, 1, 0), (0, 0, 1)], key=lambda v: abs(dot(z, v)))
        r = tuple(helper[k] - dot(helper, z) * z[k] for k in range(3))
    x = unit(r)
    y = cross(z, x)
    self.basis = (x, y, z)
    self.yaw = self.pitch = self.roll = 0.0
    self.center_view()
    return True


def export_document(self, path, scale=4):
    """The field as SVG or PDF: labels, measurements and lines as vectors, the shaded model as
    an image of scale × the field resolution; no grid. Returns the path."""
    from pathlib import Path as _Path

    from PySide6.QtCore import QMarginsF, QSize, QSizeF
    from PySide6.QtGui import QPageLayout, QPageSize, QPdfWriter
    from PySide6.QtSvg import QSvgGenerator

    path = _Path(path)
    suffix = path.suffix.lower()
    if suffix == '.svg':
        device = QSvgGenerator()
        device.setFileName(str(path))
        device.setSize(QSize(self.width(), self.height()))
        device.setViewBox(self.rect())
        device.setTitle('Azimuth · Compass')
    elif suffix == '.pdf':
        device = QPdfWriter(str(path))
        device.setResolution(72)  # one point per pixel of the field
        device.setPageLayout(
            QPageLayout(
                QPageSize(QSizeF(self.width(), self.height()), QPageSize.Unit.Point),
                QPageLayout.Orientation.Portrait,
                QMarginsF(0, 0, 0, 0),
            )
        )
        device.setTitle('Azimuth · Compass')
    else:
        raise ValueError(tr('Поддерживаются SVG и PDF.'))
    self.capture = True
    self.export_ratio = scale
    painter = QPainter(device)
    try:
        if not painter.isActive():
            raise OSError(tr('Не удалось создать файл: ') + str(path))
        with self._without_native():
            self.render(painter, QPointF(0, 0).toPoint())  # PySide6 wants the offset with a painter
    finally:
        if painter.isActive():
            painter.end()
        self.capture = False
        self.export_ratio = None
        self._model_image = None
        self.update()
    return path


def zoom_view(self, factor):
    self.zoom = min(6.0, max(0.15, self.zoom * factor))
    self.moving()
    self.update()


def pan_view(self, dx, dy):
    self.pan += QPointF(dx, dy)
    # the model never leaves the field — its centre stays within the field (and a little past its edge)
    reach_x, reach_y = max(200.0, self.width() * 0.6), max(200.0, self.height() * 0.6)
    self.pan = QPointF(min(reach_x + self.inset, max(-reach_x, self.pan.x())), min(reach_y, max(-reach_y, self.pan.y())))
    self.moving()
    self.update()


def screenshot(self, path):
    pixmap = self.render_image(self.scale_capture, self.transparent)
    from azimuth import defaults

    if self.molecule and self.molecule.atoms and defaults.get('picture_crop'):  # or the whole field
        bounds = None
        for i, (point, z) in enumerate(self.projected()):
            r = self.atom_radius(i) + 24
            rect = QRectF(point.x() - r, point.y() - r, 2 * r, 2 * r)
            bounds = rect if bounds is None else bounds.united(rect)
        if self.show_axes:
            bounds = bounds.united(QRectF(8, 8, 100, 100))
        bounds = bounds.intersected(QRectF(self.rect()))
        if not bounds.isEmpty():
            ratio = pixmap.devicePixelRatio()
            pixmap = pixmap.copy(
                int(bounds.x() * ratio),
                int(bounds.y() * ratio),
                int(bounds.width() * ratio),
                int(bounds.height() * ratio),
            )
    if not pixmap.save(str(path), 'PNG'):
        raise OSError(tr('Не удалось сохранить изображение: ') + str(path))


def render_image(self, scale=1, transparent=False):
    """The field as a pixmap at scale × the screen resolution (no grid; optionally transparent)."""
    from PySide6.QtGui import QPixmap

    ratio = self.devicePixelRatioF() * scale
    pixmap = QPixmap(int(self.width() * ratio), int(self.height() * ratio))
    pixmap.setDevicePixelRatio(ratio)
    pixmap.fill(Qt.GlobalColor.transparent)
    self.capture = True
    old = self.transparent
    self.transparent = transparent
    try:
        with self._without_native():
            self.render(pixmap)
    finally:
        self.capture = False
        self.transparent = old
        self.update()
    return pixmap


def rotate_screen(self, a, b):
    """Turn about the vertical (a) and horizontal (b) axes of the screen: the near side of the
    molecule moves with the mouse. The turn is kept in basis; yaw, pitch, roll restart at 0."""
    cols = [self.to_view(e) for e in ((1, 0, 0), (0, 1, 0), (0, 0, 1))]

    def turn(v):
        x, y, z = v
        x, z = cos(a) * x + sin(a) * z, -sin(a) * x + cos(a) * z
        y, z = cos(b) * y - sin(b) * z, sin(b) * y + cos(b) * z
        return x, y, z

    cols = [turn(c) for c in cols]
    self.basis = tuple(tuple(cols[k][i] for k in range(3)) for i in range(3))
    self.yaw = self.pitch = self.roll = 0.0
    self.moving()
    self.update()


def rotate_view(self, axis, angle):
    if axis == 'x':
        self.pitch += angle
    elif axis == 'y':
        self.yaw += angle
    else:
        self.roll += angle
    self.moving()
    self.update()


def reset_view(self):
    self.yaw, self.pitch, self.zoom = 0.25, -1.0, 1.0
    self.roll = 0.0
    self.pan = QPointF(self.inset / 2, 0)
    self.basis = None
    self.locked_camera = None
    self.update()


def set_inset(self, width, animate=True):
    """The drawer of the result covers width px of the left edge of the field: the model moves right by
    half of the change (smoothly, INSET_MS), so that it stays in sight; 0 — back when the drawer closes."""
    from PySide6.QtCore import QVariantAnimation

    width = max(0.0, float(width))
    delta = (width - self.inset) / 2
    self.inset = width
    # a movement still under way is not
    # lost when it is stopped — what it had left to go is added to this one (closed and opened again at once: none)
    rest = getattr(self, '_inset_rest', None)
    if self._inset_motion is not None:
        self._inset_motion.stop()
        self._inset_motion = None
        if rest is not None:
            delta += rest()
    self._inset_rest = None
    if abs(delta) < 0.5:
        return
    if not animate or not self.isVisible():
        self.pan += QPointF(delta, 0)
        self.update()
        return
    from PySide6.QtCore import QEasingCurve

    motion = QVariantAnimation(self)
    motion.setDuration(self.INSET_MS)
    # the curve of the drawer (it was linear: the drawer braked, the model did not — it looked uneven)
    motion.setEasingCurve(QEasingCurve.Type.OutCubic if delta > 0 else QEasingCurve.Type.InOutCubic)
    motion.setStartValue(0.0)
    motion.setEndValue(1.0)
    done = [0.0]

    def step(t):
        t = float(t)
        self.pan += QPointF(delta * (t - done[0]), 0)
        done[0] = t
        self.moving()  # the fast frames of a movement while it slides
        self.update()
        self._follow_now()  # VTK in step with the drawer that slides beside it (it lagged a frame)

    motion.valueChanged.connect(step)
    motion.finished.connect(lambda: step(1.0))
    self._inset_motion = motion
    self._inset_rest = lambda: delta * (1.0 - done[0])  # the part not gone yet
    motion.start()
