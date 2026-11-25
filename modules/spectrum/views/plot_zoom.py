"""Spectrum: moving and zooming a picture of «Карты и профили» — the map and the profile.

HEADER
    Arrows and zoom buttons over a map or a plot: move the picture left, right, up and down, zoom in and out (often
    the interesting part of a plot is at small values). Wilkinson convention, sections 1-8.

§2 ALGORITHM
    A picture shows the window (x0, x1, y0, y1) of its whole extent, in shares 0…1 of it (y from the top for the map,
    from the bottom for the profile — Y_UP). zoom(factor, fx, fy) narrows (widens) the window around the point (fx, fy)
    of it, which stays in place; pan(dx, dy) shifts it by shares of its width and height (as a camera: «←» shows what
    is to the left). The window never leaves 0…1 and is never wider than 1 nor narrower than MIN. Mouse: the wheel
    zooms at the pointer (Shift — the values only, Ctrl/⌘ — the positions only, on the profile), a drag moves, a double
    click shows everything. The pad (ZoomPad) in the lower right corner: «−», «+», four arrows and «Всё».
§4 SPECIFICATION
    Zoomable (mixed into a QWidget with plot_rect() -> QRectF and Y_UP): window, reset_view(), zoom(factor, fx=0.5,
    fy=0.5, axes='xy'), pan(dx, dy), step(direction), zoomed() -> bool, picture() -> QPixmap (without the pad).
    ZoomPad(view).
§7 TESTS
    tests/gui/test_spectrum_polish.py::test_the_map_and_the_profile_zoom_and_move.
"""

from PySide6.QtCore import QPointF, Qt
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from azimuth.i18n import tr

ZOOM = 1.25  # one step of the buttons and of the wheel
PAN = 0.15  # one step of an arrow: a share of the window
MIN = 0.01  # the narrowest window: a hundredth of the whole


def _clamp(low, high):
    width = min(1.0, max(MIN, high - low))
    if width > 1.0 - 1e-9:  # 1.15 − 0.15 is 0.9999999999999999 — the whole stayed off by 1e-16
        return 0.0, 1.0
    low = max(0.0, min(low, 1.0 - width))
    return low, low + width


class Zoomable:
    Y_UP = False

    def _zoom_init(self):
        self.window = [0.0, 1.0, 0.0, 1.0]
        self._drag = None
        self.pad = ZoomPad(self)

    # -- the window -----------------------------------------------------------------------------------------------
    def zoomed(self):
        return any(abs(a - b) > 1e-9 for a, b in zip(self.window, (0.0, 1.0, 0.0, 1.0)))

    def reset_view(self):
        self.window = [0.0, 1.0, 0.0, 1.0]
        self.update()

    def zoom(self, factor, fx=0.5, fy=0.5, axes='xy'):
        x0, x1, y0, y1 = self.window
        if 'x' in axes:
            centre, width = x0 + fx * (x1 - x0), (x1 - x0) / factor
            x0, x1 = _clamp(centre - fx * width, centre - fx * width + width)
        if 'y' in axes:
            centre, height = y0 + fy * (y1 - y0), (y1 - y0) / factor
            y0, y1 = _clamp(centre - fy * height, centre - fy * height + height)
        self.window = [x0, x1, y0, y1]
        self.update()

    def pan(self, dx, dy):
        x0, x1, y0, y1 = self.window
        x0, x1 = _clamp(x0 + dx * (x1 - x0), x1 + dx * (x1 - x0))
        y0, y1 = _clamp(y0 + dy * (y1 - y0), y1 + dy * (y1 - y0))
        self.window = [x0, x1, y0, y1]
        self.update()

    def step(self, direction):
        """«left», «right», «up», «down», «in», «out», «all» — the buttons of the pad."""
        up = 1 if self.Y_UP else -1
        moves = {'left': (-PAN, 0), 'right': (PAN, 0), 'up': (0, up * PAN), 'down': (0, -up * PAN)}
        if direction in moves:
            self.pan(*moves[direction])
        elif direction == 'in':
            self.zoom(ZOOM)
        elif direction == 'out':
            self.zoom(1 / ZOOM)
        else:
            self.reset_view()

    def _share(self, pos):
        rect = self.plot_rect()
        if rect is None or rect.width() <= 0 or rect.height() <= 0:
            return None
        fx = (pos.x() - rect.left()) / rect.width()
        fy = (pos.y() - rect.top()) / rect.height()
        if self.Y_UP:
            fy = 1 - fy
        return min(1.0, max(0.0, fx)), min(1.0, max(0.0, fy))

    # -- the mouse ------------------------------------------------------------------------------------------------
    def wheelEvent(self, event):
        share = self._share(event.position()) if self.data is not None else None
        if share is None:
            return super().wheelEvent(event)
        delta = event.angleDelta().y() or event.angleDelta().x()
        if not delta:
            return None
        modifiers = event.modifiers()
        axes = 'xy'
        if self.Y_UP and modifiers & Qt.KeyboardModifier.ShiftModifier:
            axes = 'y'
        elif self.Y_UP and modifiers & Qt.KeyboardModifier.ControlModifier:
            axes = 'x'
        self.zoom(ZOOM ** (delta / 120.0), share[0], share[1], axes)
        event.accept()
        return None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.data is not None and self.plot_rect() is not None:
            self._drag = (QPointF(event.position()), list(self.window))
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return None
        return super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag is None:
            return super().mouseMoveEvent(event)
        start, (x0, x1, y0, y1) = self._drag
        rect = self.plot_rect()
        moved = QPointF(event.position()) - start
        dx = -moved.x() / max(rect.width(), 1.0) * (x1 - x0)
        dy = moved.y() / max(rect.height(), 1.0) * (y1 - y0)
        if not self.Y_UP:
            dy = -dy
        nx0, nx1 = _clamp(x0 + dx, x1 + dx)
        ny0, ny1 = _clamp(y0 + dy, y1 + dy)
        self.window = [nx0, nx1, ny0, ny1]
        self.update()
        event.accept()
        return None

    def mouseReleaseEvent(self, event):
        if self._drag is not None:
            self._drag = None
            self.unsetCursor()
            event.accept()
            return None
        return super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if self.data is not None:
            self.reset_view()
            event.accept()
            return None
        return super().mouseDoubleClickEvent(event)

    # -- the pad --------------------------------------------------------------------------------------------------
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.pad.place()

    def picture(self):
        """The picture as it is drawn, without the pad (the floppy disk of the panel)."""
        if self.pad.docked:
            return self.grab()
        shown = not self.pad.isHidden()  # isVisible is False in a window not shown — the pad stayed hidden
        self.pad.hide()
        try:
            return self.grab()
        finally:
            self.pad.setVisible(shown)

    def follow_data(self):
        """A new map or profile: the whole of it, the pad with it."""
        self.window = [0.0, 1.0, 0.0, 1.0]
        self.pad.setVisible(self.data is not None)
        self.pad.place()


class ZoomPad(QWidget):
    """The buttons over the lower right corner of a picture; or in a row of the panel — dock(row, index)."""

    SIZE = 26

    def __init__(self, view):
        super().__init__(view)
        from azimuth.icons import iconify
        from PySide6.QtCore import QSize

        self.view = view
        self.docked = False
        self.setObjectName('zoomPad')
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._dark = None
        row = QHBoxLayout(self)
        row.setContentsMargins(3, 3, 3, 3)
        row.setSpacing(1)
        self.buttons = {}
        for key, glyph, title in (('out', 'zoom-out', tr('Отдалить · колесо мыши')),
                                  ('in', 'zoom-in', tr('Приблизить · колесо мыши')),
                                  ('left', 'pan-left', tr('Сдвинуть влево · перетаскивание мышью')),
                                  ('up', 'pan-up', tr('Сдвинуть вверх')),
                                  ('down', 'pan-down', tr('Сдвинуть вниз')),
                                  ('right', 'pan-right', tr('Сдвинуть вправо')),
                                  ('all', 'center', tr('Показать всё · двойной щелчок'))):
            item = iconify(QPushButton(), glyph, title)
            item.setFixedSize(self.SIZE, self.SIZE)
            item.setIconSize(QSize(16, 16))
            item.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            item.clicked.connect(lambda checked=False, key=key: view.step(key))
            row.addWidget(item)
            self.buttons[key] = item
        self.adjustSize()
        self.hide()

    def dock(self, row, index):
        """In the row (a layout) at index, not over the picture: no ground of its own."""
        self.docked = True
        self.setStyleSheet('QWidget#zoomPad {background: transparent; border: none;}')
        self.layout().setContentsMargins(0, 0, 0, 0)
        row.insertWidget(index, self)
        self.setVisible(self.view.data is not None)

    def place(self):
        if self.docked:
            return
        view = self.view
        dark = view.palette().base().color().lightness() < 128
        if dark != self._dark:  # the light or the dark theme: the ground of the pad as the plot's
            self._dark = dark
            self.setStyleSheet('QWidget#zoomPad {background: %s; border: 1px solid %s; border-radius: 8px;}'
                               % (('rgba(25, 31, 40, 215)', '#3a4452') if dark else ('rgba(255, 255, 255, 215)',
                                                                                      '#d8dce3')))
        self.adjustSize()
        self.move(view.width() - self.width() - 8, view.height() - self.height() - 8)
        self.raise_()
