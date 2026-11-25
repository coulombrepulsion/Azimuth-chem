"""The Compass view while the window around it moves: the model keeping its place while rows above it change, a panel
sliding beside the field (a picture of the field glides instead). Methods of MoleculeView (self is the view), kept
here to make viewer.py shorter.

Split off modules/compass/view/viewer.py (0.222.30).
"""

from time import monotonic
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget


class _GlideCover(QWidget):
    """The picture of the field while a panel slides (MoleculeView.begin_glide): the colour of the field, and
    the picture moved and scaled so that its model stands where the model of the field now stands."""

    def __init__(self, view):
        super().__init__(view)
        self.view = view
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)

    def paintEvent(self, event):
        glide = getattr(self.view, '_glide', None) or getattr(self, 'kept', None)
        p = QPainter(self)
        view = self.view
        field = view.field_color()
        p.fillRect(self.rect(), field)
        dark = field.lightness() < 128
        # what stands by the edges of
        # the field — the dot grid (from the left edge) and the axes (top right) — is drawn here at its place now; the
        # picture (taken without them) lies over the grid darkening (light field) or lightening (dark field) it, so
        # the dots show through its empty field and its model covers them
        if view.grid and not view.capture:
            p.setPen(QPen(QColor('#3a4757' if dark else '#c3c9d3'), 1))
            for x in range(24, view.width(), 30):
                for y in range(24, view.height(), 30):
                    p.drawPoint(x, y)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Lighten if dark
                             else QPainter.CompositionMode.CompositionMode_Darken)
        if glide is not None:
            picture, centre, scale = glide
            try:
                now = self.view.camera()[1]
            except (ValueError, ZeroDivisionError):
                now = scale
            factor = now / scale if scale > 0 else 1.0
            dx = self.view.width() / 2 + self.view.pan.x() - centre.x()
            dy = self.view.height() / 2 + self.view.pan.y() - centre.y()
            if abs(factor - 1.0) < 1e-3:
                # the size of the model unchanged (the height of the field decides it) — the picture is only
                # moved, by whole device pixels: no resampling of the whole field every step (it took the time of a
                # frame now and then, and the tabs and the buttons beside it shook)
                ratio = picture.devicePixelRatioF() or 1.0
                p.drawPixmap(QPointF(round(dx * ratio) / ratio, round(dy * ratio) / ratio), picture)
            else:
                # the size changes — a
                # picture of half the pixels is scaled (made once), not the whole picture of the screen every frame
                fast = getattr(self, '_fast', None)
                if fast is None or fast[0] is not picture:
                    ratio = picture.devicePixelRatioF() or 1.0
                    small = picture.scaled(max(1, picture.width() // 2), max(1, picture.height() // 2),
                                           Qt.AspectRatioMode.IgnoreAspectRatio,
                                           Qt.TransformationMode.SmoothTransformation)
                    small.setDevicePixelRatio(ratio / 2)
                    fast = self._fast = (picture, small)
                p.translate(centre.x() + dx, centre.y() + dy)
                p.scale(factor, factor)
                p.translate(-centre.x(), -centre.y())
                p.drawPixmap(0, 0, fast[1])  # no smoothing while it moves — the model is drawn sharp at the end
        p.resetTransform()
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        if view.show_axes and view.axes_place == 'corner':
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            view.draw_axes(p)
        p.end()


def hold_place(self, ms=400):
    """The model keeps its size and its place in the window while the rows above the field change (the
    tools of «Изменение структуры» and «Перемещение» appear or go): the field changes its height, and the fitted
    scale and the middle of the field moved the model — a jerk. For ms after the call every resize is
    compensated by the camera and the shift."""
    from PySide6.QtCore import QPoint, QTimer

    if not self.molecule or not self.molecule.atoms or self.width() <= 0:
        return
    if getattr(self, '_held', None) is None:
        self.keep_camera()
        self._held = (self.mapTo(self.window(), QPoint(0, 0)), self.width(), self.height(), QPointF(self.pan))
    token = object()
    self._held_token = token
    QTimer.singleShot(ms, self, lambda: self._release_place(token))


def _release_place(self, token):
    if getattr(self, '_held_token', None) is token:
        self._held = None


def _settle_place(self):
    from PySide6.QtCore import QPoint

    held = getattr(self, '_held', None)
    if held is None:
        return
    corner, width, height, pan = held
    now = self.mapTo(self.window(), QPoint(0, 0))
    self.pan = QPointF(pan.x() + corner.x() - now.x() + (width - self.width()) / 2,
                       pan.y() + corner.y() - now.y() + (height - self.height()) / 2)


def layout_motion(self):
    """A panel beside the field is sliding — every step
    changes the size of the field. The VTK picture is drawn at once at each step (drawn on the next turn of the
    loop, the old picture stood for a frame at the new place of the field — the model jumped there and back at
    every step), and the frames are the fast ones of a movement (the built-in drawing is lighter)."""
    self._layout_motion_until = monotonic() + self.LAYOUT_MOTION
    self.moving()


def in_layout_motion(self):
    return monotonic() < getattr(self, '_layout_motion_until', 0.0)


def begin_glide(self):
    """While a panel slides beside the field, the field shows a picture
    of itself taken at the start — the model, its labels and all, in one piece — moved and scaled as the model
    would be; the model is drawn anew once, when the panel has stopped (end_glide). Every step drew the whole
    scene again (VTK built it anew) and painted the labels over it on their own, and they fell behind."""
    # an empty field too
    if getattr(self, '_glide', None) is not None or not self.isVisible() or self.width() <= 0:
        return
    kept = self.grid, self.show_axes
    corner = self.axes_place == 'corner'
    try:  # without the grid and the corner axes — the cover draws them at their places (_GlideCover)
        self.grid = False
        if corner:
            self.show_axes = False
        picture = self.grab()
    except RuntimeError:
        return
    finally:
        self.grid, self.show_axes = kept
    self._glide = (picture, QPointF(self.width() / 2 + self.pan.x(), self.height() / 2 + self.pan.y()),
                   self.camera()[1])
    cover = _GlideCover(self)
    cover.setGeometry(self.rect())
    cover.show()
    cover.raise_()
    self._glide_cover = cover


def end_glide(self):
    cover = getattr(self, '_glide_cover', None)
    cover_glide = getattr(self, '_glide', None)
    self._glide = None
    self._glide_cover = None
    if cover is None:
        return
    cover.kept = cover_glide  # it still shows the picture at the end of the slide
    self._follow_now()  # the model at its place now, drawn before the picture goes
    self.update()

    def gone():
        try:
            cover.hide()
            cover.deleteLater()
        except RuntimeError:
            pass

    # the labels (painted over VTK) were on the
    # screen at their new places a frame before VTK had shown its new frame — the picture goes only when VTK has
    # shown it (frameSwapped), or after FRAME_WAIT at most; the built-in drawing paints both at once
    n = getattr(self, '_native', None)
    gl = getattr(n, 'gl', None) if n is not None and getattr(n, 'active', False) else None
    if gl is None or not hasattr(gl, 'frameSwapped'):
        gone()
        return
    from PySide6.QtCore import QTimer

    done = [False]
    swaps = [0]

    def swapped():
        # the first frame of VTK
        # after its field became narrower can still be the old one — the picture goes after the second
        swaps[0] += 1
        if swaps[0] >= 2:
            once()
        else:
            gl.update()  # the second frame

    def once():
        if done[0]:
            return
        done[0] = True
        try:
            gl.frameSwapped.disconnect(swapped)
        except (RuntimeError, TypeError):
            pass
        gone()

    gl.frameSwapped.connect(swapped)
    QTimer.singleShot(self.FRAME_WAIT, once)


def gliding(self):
    return getattr(self, '_glide', None) is not None


def _follow_now(self):
    """While the place is held (the rows above the field change) the VTK picture is drawn at once — it
    was drawn on the next turn of the loop, and for a frame the old picture moved with the field: the jerk the user
    saw on leaving «Изменение структуры» and «Перемещение»."""
    if self.gliding():  # see update
        return
    n = getattr(self, '_native', None)
    if n is not None and n.active:
        n.refresh()


def _without_native(self):
    """A context in which the children of the native view are hidden (pictures are drawn by the view)."""
    from contextlib import contextmanager

    @contextmanager
    def hidden():
        n = getattr(self, '_native', None)
        if n is None or not n.active:
            yield
            return
        n.set_visible(False)
        try:
            yield
        finally:
            n.set_visible(True)
            n.schedule()

    return hidden()
