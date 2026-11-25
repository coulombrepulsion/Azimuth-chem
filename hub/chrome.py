"""Hub window decorations: faint scales (Ornament), the wordmark widget, the sidebar scrim (moved from window.py)."""

import math

from PySide6.QtCore import (
    QEvent,
    QPoint,
    QPointF,
    QRect,
    QRectF,
    QSize,
    Qt,
)
from PySide6.QtGui import (
    QColor,
    QRegion,
    QPen,
    QPainter,
    QPixmap,
    QPolygonF,
)
from PySide6.QtWidgets import (
    QAbstractButton,
    QAbstractScrollArea,
    QAbstractSpinBox,
    QComboBox,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QStatusBar,
    QTabBar,
    QTabWidget,
    QWidget,
)


class Ornament(QWidget):
    """Very faint scales in every section: the azimuth dial in the upper right corner (an
    arc with marks every 5 deg, longer every 30 deg, two circles and the cardinal lines) and the sextant
    in the lower left corner (marks every 3 deg, longer every 15 deg, an inner arc, the index arm and
    the guide star). Drawn over the page but transparent for the mouse, with low alpha so that they
    never compete with the text.

    The scales lie on the background: wherever they pass under something with a filled surface they keep only THROUGH of
    their strength, as if seen through a not quite opaque layer. Full strength remains on the bare page and over the
    section header. Surfaces (see is_surface): panels and blocks (cards, the optimization steps drawer, Quill's bubble,
    notices), buttons with a background (not the transparent icon buttons unless checked), combo and spin boxes, line
    edits, text and table views, tab bars and tab panes, the status bar, and the custom-drawn fields (the molecule,
    plots, the element tile). Text labels and layout containers are not surfaces. The area is a union of rectangles
    clipped to what is on screen, rebuilt on every paint (cheap: no path arithmetic)."""

    THROUGH = 0.45  # share of the scales seen through a surface (0.2 in 0.35–0.46; the pictures were hidden too much)
    SURFACE_NAMES = {'card', 'trajectoryDrawer', 'projectPane', 'bubble', 'notice', 'error', 'toolRule', 'panelRule', 'code'}
    BACKGROUNDS = {'HomeBackdrop', 'Ornament', 'Scrim', 'BrandMark'}  # custom-drawn, but page or decoration
    DRAWN = {'MoleculeView', 'IRSpectrum', 'EnergyPlot', 'ElementTile'}  # custom-drawn fields

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.ink = QColor('#2a62b8')
        self.section = 'sextant'

    def set_color(self, ink):
        self.ink = QColor(ink)
        self.update()

    def set_section(self, ident):
        """The picture in the lower left corner follows the section (the home page: none)."""
        self.section = ident
        self.update()

    @classmethod
    def is_surface(cls, widget):
        """True when the widget paints a filled surface of its own."""
        name, kind = QWidget.objectName(widget), type(widget).__name__  # see surface_region
        if name in cls.SURFACE_NAMES or kind in cls.DRAWN:
            return True
        if kind in cls.BACKGROUNDS or name in ('nav', 'lang', 'sectionHeader', 'scrim'):
            return False
        if isinstance(widget, QAbstractButton):
            if QWidget.property(widget, 'iconic'):
                return widget.isCheckable() and widget.isChecked()  # transparent unless checked
            return isinstance(widget, QPushButton) and not widget.isFlat()
        if isinstance(widget, (QComboBox, QAbstractSpinBox, QLineEdit, QTabBar, QStatusBar, QTabWidget)):
            return True
        if isinstance(widget, QAbstractScrollArea) and not isinstance(widget, QScrollArea):
            return True  # text edits, tables, lists (a QScrollArea is only a container)
        return False

    # the methods of QWidget called as QWidget.size(w), QWidget.window(w)…, not w.size(): a widget may have an
    # attribute of that name of its own — the list «size» of «Карты и профили», the render window «window» of the VTK
    # view of Compass («'QComboBox' / 'vtkWin32OpenGLRenderWindow' object is not callable» at every paint, the user's
    # reports from Windows)
    def surface_region(self):
        """The visible surfaces under the ornament, in its own coordinates."""
        region = QRegion()
        host = self.parentWidget()
        if host is None:
            return region
        bounds = self.rect()
        for widget in host.findChildren(QWidget):
            through = QWidget.testAttribute(widget, Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            if not QWidget.isVisible(widget) or through:
                continue  # hidden pages, the ornament itself, the fading still of a section change
            if QWidget.window(widget) is not self.window() or not self.is_surface(widget):
                continue
            # Where it is on screen: the widget clipped by every ancestor up to the host; nothing inside
            # the section header (the scales stay at full strength there).
            seen = QRect(self.mapFrom(host, QWidget.mapTo(widget, host, QPoint(0, 0))), QWidget.size(widget))
            if isinstance(widget, QTabWidget):
                seen.setTop(seen.top() + widget.tabBar().height())  # the pane; the bar is a surface itself
            ancestor, header = QWidget.parentWidget(widget), False
            while ancestor is not None and ancestor is not host:
                header = header or QWidget.objectName(ancestor) == 'sectionHeader'
                place = self.mapFrom(host, QWidget.mapTo(ancestor, host, QPoint(0, 0)))
                seen = seen.intersected(QRect(place, QWidget.size(ancestor)))
                ancestor = QWidget.parentWidget(ancestor)
            seen = seen.intersected(bounds)
            if ancestor is not None and not header and not seen.isEmpty():
                region = region.united(seen)
        return region

    ZONE = 430  # px: the corner squares where the scales are drawn (dial R 330 top right, cards about 270 lower left)

    def scale_zone(self):
        """The parts of the ornament where scales are drawn: the top right and the lower left squares."""
        w, h, z = self.width(), self.height(), self.ZONE
        return QRegion(w - z, 0, z, z).united(QRegion(0, h - z, z, z))

    def opaque_region(self):
        """What hides the scales completely — the molecule drawn in Compass (MoleculeView.ornament_cover),
        in the ornament's coordinates, clipped to the visible part of the view. Also Quill — labels with the
        property 'quill' and her picture in the empty field of Compass."""
        region = QRegion()
        host = self.parentWidget()
        if host is None:
            return region
        for widget in host.findChildren(QWidget):
            cover = getattr(widget, 'ornament_cover', None)
            if cover is None and QWidget.property(widget, 'quill'):  # a picture of Quill hides the scales
                cover = lambda within, w=widget: QRegion(QWidget.contentsRect(w))  # noqa: E731
            if cover is None or not QWidget.isVisible(widget) or QWidget.window(widget) is not self.window():
                continue
            origin = self.mapFrom(host, QWidget.mapTo(widget, host, QPoint(0, 0)))
            seen = QRect(origin, QWidget.size(widget))
            ancestor = QWidget.parentWidget(widget)
            while ancestor is not None and ancestor is not host:  # clipped by every ancestor, as in surface_region
                place = self.mapFrom(host, QWidget.mapTo(ancestor, host, QPoint(0, 0)))
                seen = seen.intersected(QRect(place, QWidget.size(ancestor)))
                ancestor = QWidget.parentWidget(ancestor)
            if ancestor is None or seen.isEmpty():
                continue
            zone = QRegion(seen).intersected(self.scale_zone())
            if zone.isEmpty():
                continue
            part = cover(zone.translated(-origin).boundingRect()).translated(origin).intersected(zone)
            if not part.isEmpty():
                region = region.united(part)
        return region

    def freeze_ornament(self):
        """While a panel slides, the scales are a
        picture taken at its start; thaw_ornament draws them anew when it has stopped."""
        if getattr(self, '_frozen', None) is not None or not self.isVisible() or self.width() <= 0:
            return
        from PySide6.QtGui import QPixmap

        ratio = self.devicePixelRatioF() or 1.0
        picture = QPixmap(max(1, round(self.width() * ratio)), max(1, round(self.height() * ratio)))
        picture.setDevicePixelRatio(ratio)
        picture.fill(Qt.GlobalColor.transparent)
        painter = QPainter(picture)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        try:
            self.paint_layers(painter, self.surface_region(), self.opaque_region())
        except Exception:  # noqa: BLE001 — drawn as usual then
            painter.end()
            return
        painter.end()
        self._frozen = (self.size(), picture)

    def thaw_ornament(self):
        if getattr(self, '_frozen', None) is not None:
            self._frozen = None
            self.update()

    def paintEvent(self, event):
        frozen = getattr(self, '_frozen', None)
        if frozen is not None and frozen[0] == self.size():
            painter = QPainter(self)
            painter.drawPixmap(0, 0, frozen[1])
            painter.end()
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        try:
            self.paint_layers(painter, self.surface_region(), self.opaque_region())
        except Exception as exc:  # noqa: BLE001 — 0.91.52: the background ornament never stops the painting
            if not getattr(self, '_paint_error', False):  # written once; no window «Что-то пошло не так» in a paint
                self._paint_error = True
                from azimuth.crash_report import format_exception, record

                record('exception', format_exception(type(exc), exc, exc.__traceback__))
        finally:  # ended even after an error (Qt warned «endPaint() called with active painter»)
            painter.end()

    def paint_layers(self, painter, surfaces, opaque=None):
        """The scales at full strength on the background and at THROUGH under the surfaces; none under `opaque`."""
        if opaque is not None and not opaque.isEmpty():
            painter.setClipRegion(QRegion(self.rect()).subtracted(opaque))
            surfaces = surfaces.subtracted(opaque)
        if surfaces.isEmpty():
            self._scales(painter)
            return
        painter.save()
        base = QRegion(self.rect()) if opaque is None else QRegion(self.rect()).subtracted(opaque)
        painter.setClipRegion(base.subtracted(surfaces))
        self._scales(painter)
        painter.restore()
        painter.save()
        painter.setClipRegion(surfaces)
        painter.setOpacity(self.THROUGH)
        self._scales(painter)
        painter.restore()

    def _scales(self, painter):
        self._azimuth(painter)  # top right, in every section
        corner = {
            'sextant': self._sextant,
            'compass': self._compass,
            'crystal': self._compass,  # both Compasses have the compass card
            'spectrum': self._spectrum,
        }.get(self.section)  # the book of the Atlas went with the Atlas (it is drawn on the site)
        if corner is not None:
            corner(painter)

    def _pen(self, alpha, width=1.0, style=Qt.PenStyle.SolidLine):
        color = QColor(self.ink)
        color.setAlphaF(alpha)
        return QPen(color, width, style)

    def _star(self, painter, sx, sy, r1=7.0, alpha=0.22):
        color = QColor(self.ink)
        color.setAlphaF(alpha)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        r2 = r1 * 0.3
        pts = [
            QPointF(sx + (r1 if k % 2 == 0 else r2) * math.sin(math.radians(k * 45)), sy - (r1 if k % 2 == 0 else r2) * math.cos(math.radians(k * 45)))
            for k in range(8)
        ]
        painter.drawPolygon(QPolygonF(pts))
        painter.setBrush(Qt.BrushStyle.NoBrush)

    def _compass(self, painter):
        """Компас: a quarter of a compass card — marks every 5°, longer every 45°, two rings, the needle to the north-east."""
        h = self.height()
        cx, cy, R = -36.0, h + 36.0, 236.0
        for deg in range(270, 361, 5):
            a = math.radians(deg)
            long = deg % 45 == 0
            painter.setPen(self._pen(0.20 if long else 0.10, 1.4 if long else 0.9))
            r0 = R - (20 if long else 9)
            painter.drawLine(QPointF(cx + R * math.cos(a), cy + R * math.sin(a)), QPointF(cx + r0 * math.cos(a), cy + r0 * math.sin(a)))
        painter.setPen(self._pen(0.11, 1.1))
        for r in (R, R * 0.74, R * 0.3):
            painter.drawArc(QRectF(cx - r, cy - r, 2 * r, 2 * r), 0, 90 * 16)
        a = math.radians(-45)  # the needle: a long thin diamond from the centre to the north-east
        tip = QPointF(cx + R * 0.92 * math.cos(a), cy + R * 0.92 * math.sin(a))
        side = math.radians(-45 + 90)
        w = 9.0
        mid = QPointF(cx + R * 0.38 * math.cos(a), cy + R * 0.38 * math.sin(a))
        left = mid + QPointF(w * math.cos(side), w * math.sin(side))
        right = mid - QPointF(w * math.cos(side), w * math.sin(side))
        painter.setPen(self._pen(0.14, 1.1))
        painter.drawPolygon(QPolygonF([QPointF(cx, cy), left, tip, right]))
        painter.setPen(self._pen(0.08, 1.0, Qt.PenStyle.DashLine))
        painter.drawLine(QPointF(cx, cy), tip)
        self._star(painter, cx + R * 1.12 * math.cos(a), cy + R * 1.12 * math.sin(a))

    def _spectrum(self, painter):
        """Спектр: an axis with marks and a few bands of a spectrum rising from it. Its start outside the corner, as the
        centres of the compass and of the sextant (tools/site_scales.py SPECTRUM_X0, SPECTRUM_DY)."""
        h = self.height()
        x0, y0, width = -100.0, h - 14.0, 380.0
        painter.setPen(self._pen(0.14, 1.2))
        painter.drawLine(QPointF(x0, y0), QPointF(x0 + width, y0))
        painter.drawLine(QPointF(x0, y0), QPointF(x0, y0 - 190))
        for k in range(0, 21):
            long = k % 5 == 0
            painter.setPen(self._pen(0.16 if long else 0.09, 1.0))
            x = x0 + k * width / 20
            painter.drawLine(QPointF(x, y0), QPointF(x, y0 + (9 if long else 5)))
        bands = ((0.18, 120, 9), (0.33, 62, 6), (0.47, 168, 7), (0.6, 40, 5), (0.74, 96, 11), (0.88, 54, 6))
        path = [QPointF(x0, y0)]
        for t in range(0, 381, 2):
            y = sum(hgt * g * g / ((t - c * width) ** 2 + g * g) for c, hgt, g in bands)
            path.append(QPointF(x0 + t, y0 - y))
        painter.setPen(self._pen(0.16, 1.2))
        painter.drawPolyline(QPolygonF(path))
        painter.setPen(self._pen(0.07, 1.0, Qt.PenStyle.DashLine))
        for c, hgt, _ in bands[::2]:
            painter.drawLine(QPointF(x0 + c * width, y0), QPointF(x0 + c * width, y0 - hgt - 12))
        self._star(painter, x0 + 0.47 * width, y0 - 168 - 30)

    def _sextant(self, painter):
        h = self.height()
        cx, cy, R = -36.0, h + 36.0, 236.0  # centre outside the corner: a quarter of the dial shows
        color = QColor(self.ink)
        for deg in range(270, 361, 3):
            a = math.radians(deg)
            long = deg % 15 == 0
            color.setAlphaF(0.20 if long else 0.10)
            painter.setPen(QPen(color, 1.4 if long else 0.9))
            r0 = R - (18 if long else 9)
            painter.drawLine(
                QPointF(cx + R * math.cos(a), cy + R * math.sin(a)),
                QPointF(cx + r0 * math.cos(a), cy + r0 * math.sin(a)),
            )
        color.setAlphaF(0.11)
        painter.setPen(QPen(color, 1.1))
        painter.drawArc(QRectF(cx - R, cy - R, 2 * R, 2 * R), 0, 90 * 16)
        inner = R * 0.70
        painter.drawArc(QRectF(cx - inner, cy - inner, 2 * inner, 2 * inner), 0, 90 * 16)
        color.setAlphaF(0.08)
        painter.setPen(QPen(color, 1.0, Qt.PenStyle.DashLine))
        a = math.radians(-38)  # the index arm of the sextant
        painter.drawLine(QPointF(cx, cy), QPointF(cx + R * 1.06 * math.cos(a), cy + R * 1.06 * math.sin(a)))
        color.setAlphaF(0.22)  # the guide star, as after the name
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        sx, sy, r1 = cx + R * 1.18 * math.cos(a), cy + R * 1.18 * math.sin(a), 7.0
        r2 = r1 * 0.3
        pts = [
            QPointF(
                sx + (r1 if k % 2 == 0 else r2) * math.sin(math.radians(k * 45)),
                sy - (r1 if k % 2 == 0 else r2) * math.cos(math.radians(k * 45)),
            )
            for k in range(8)
        ]
        painter.drawPolygon(QPolygonF(pts))

    def _azimuth(self, painter):
        w = self.width()
        R = 330.0
        cx, cy = w - 70.0, 70.0
        color = QColor(self.ink)
        for deg in range(90, 271, 5):  # the visible part of the dial
            a = math.radians(deg)
            long = deg % 30 == 0
            color.setAlphaF(0.16 if long else 0.08)
            painter.setPen(QPen(color, 1.6 if long else 1.0))
            r0 = R - (22 if long else 11)
            painter.drawLine(
                QPointF(cx + R * math.cos(a), cy + R * math.sin(a)),
                QPointF(cx + r0 * math.cos(a), cy + r0 * math.sin(a)),
            )
        color.setAlphaF(0.09)
        painter.setPen(QPen(color, 1.2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(cx, cy), R, R)
        painter.drawEllipse(QPointF(cx, cy), R * 0.62, R * 0.62)
        color.setAlphaF(0.07)
        painter.setPen(QPen(color, 1.0, Qt.PenStyle.DashLine))
        painter.drawLine(QPointF(cx, cy - R), QPointF(cx, cy + R))
        painter.drawLine(QPointF(cx - R, cy), QPointF(cx + R, cy))


class BrandMark(QWidget):
    """The wordmark in the sidebar. While the panel opens it appears letter by letter (each letter fades
    in and rises 3 px); it never moves sideways, so nothing shakes during the slide."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = QPixmap()
        self._cuts = [0.0, 1.0]
        self.progress = 1.0

    def setPixmap(self, pixmap, cuts=None):
        self._pixmap = pixmap
        self._cuts = cuts or [0.0, 1.0]
        size = pixmap.deviceIndependentSize().toSize() if not pixmap.isNull() else QSize(0, 0)
        self.setFixedSize(size)
        self.update()

    def pixmap(self):
        return self._pixmap

    def set_progress(self, value):
        self.progress = max(0.0, min(1.0, value))
        self.update()

    def paintEvent(self, event):
        if self._pixmap.isNull() or self.progress <= 0:
            return
        painter = QPainter(self)
        ratio = self._pixmap.devicePixelRatio()
        width, height = self._pixmap.width() / ratio, self._pixmap.height() / ratio
        count = len(self._cuts) - 1
        moment = max(0.0, (self.progress - 0.18) / 0.82) * (count + 0.6)  # starts once the panel uncovers it
        for index in range(count):
            level = max(0.0, min(1.0, moment - index * 0.95))
            if level <= 0:
                break
            level = level * level * (3 - 2 * level)  # smoothstep
            left, right = self._cuts[index] * width, self._cuts[index + 1] * width
            painter.setOpacity(level)
            target = QRectF(left, (1 - level) * 3, right - left, height)
            source = QRectF(left * ratio, 0, (right - left) * ratio, height * ratio)
            painter.drawPixmap(target, self._pixmap, source)
        painter.end()


class Scrim(QWidget):
    """Light veil over the page while the panel is open; it darkens with the slide; a click closes."""

    def __init__(self, parent, on_press):
        super().__init__(parent)
        self.level = 0.0
        self.on_press = on_press
        self.setObjectName('scrim')

    def set_level(self, value):
        self.level = value
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(8, 12, 18, round(42 * self.level)))
        painter.end()

    def mousePressEvent(self, event):
        self.on_press()
        event.accept()


class MoleculeArt(QWidget):
    """Molecules drawn in thin lines on the side panel, in the spirit of the scales on the pages.
    The background of the whole panel, under its buttons (a child of the panel
    that follows its size, not an item of its column): two columns — the rail (seen when the panel is narrow)
    and the wide part — from the line under the name to the bottom, scattered about a row every ROW px; twelve molecules
    and three cells of
    crystals, mixed once (ORDER) so that the picture is the same at every start; faint (alpha ART_ALPHA), transparent
    for the mouse."""

    ART_ALPHA = {False: 0.22, True: 0.19}
    # nothing above the line under the name (top() — set by the window, the bottom of that line); a row every ROW px
    # in each column (was 74 — a third fewer drawings), each moved from its place of the grid by up to ±JITTER_Y px
    # down or up and across its column (the rail ±RAIL px, the wide part ±WIDE px), turned by any angle (a cell — by
    # no more than CELL_TURN °, it must stay a cell)
    TOP, ROW, EDGE, REACH = 112, 104, 26, 30  # px: the line under the name, the step, the bottom margin, half a drawing
    JITTER_Y, RAIL, WIDE, CELL_TURN = 22, 9, 30, 28
    COLUMNS = ((34, 0.0, RAIL), (132, 0.5, WIDE))  # (x of the centre px, shift in rows, ± px across)
    # the order of the drawings (indices of drawings()), mixed by hand: no two alike next to each other, about every
    # sixth one a cell of a crystal («пару ячеек»)
    ORDER = ((0, 5, 12, 8, 2, 10, 6, 3, 14, 9, 1, 7, 11, 4, 13), (7, 3, 9, 1, 11, 13, 4, 6, 0, 8, 2, 10, 5, 12, 14))

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setMinimumHeight(0)
        self.ink = QColor('#2a62b8')
        self.dark = False
        self.reserve = lambda: 0  # px taken from the bottom by a widget that comes and goes (none does)
        self.top = lambda: self.TOP  # y of the line under the name — nothing is drawn above it
        if parent is not None:
            parent.installEventFilter(self)
            self.setGeometry(parent.rect())
            self.lower()

    def eventFilter(self, watched, event):
        if watched is self.parent() and event.type() == QEvent.Type.Resize:
            self.setGeometry(watched.rect())
            self.lower()
        return False

    def set_color(self, ink, dark):
        self.ink, self.dark = QColor(ink), bool(dark)
        self.update()

    def drawings(self):
        return (self._benzene, self._water, self._chain, self._methane, self._ammonia, self._carbon_dioxide,
                self._ethene, self._naphthalene, self._pyridine, self._ethanol, self._cyclopentane, self._formaldehyde,
                self._cubic_cell, self._centred_cell, self._hexagonal_cell)

    @staticmethod
    def _scatter(row, column, salt):
        """A number 0 … 1 of that place — a fixed scatter (no random numbers: the picture never changes)."""
        n = (row * 374761393 + column * 668265263 + salt * 2246822519 + 3266489917) & 0xFFFFFFFF
        n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
        return ((n ^ (n >> 16)) & 0xFFFF) / 0xFFFF

    def places(self, height=None):
        """[(drawing index, x, y, turn °, scale)] for a panel of that height — the same for the same height."""
        height = self.height() if height is None else height
        try:
            top = float(self.top())
        except Exception:  # noqa: BLE001 — a background must not stop painting
            top = self.TOP
        cells = len(self.drawings()) - 3
        found = []
        for column, ((x, shift, across), order) in enumerate(zip(self.COLUMNS, self.ORDER)):
            row = 0
            while True:
                base = top + self.REACH + 8 + (row + shift) * self.ROW
                if base > height - self.EDGE:
                    break
                r = [self._scatter(row, column, salt) for salt in range(4)]
                index = order[row % len(order)]
                y = min(max(base + (2 * r[0] - 1) * self.JITTER_Y, top + self.REACH), height - self.EDGE)
                turn = (2 * r[2] - 1) * (self.CELL_TURN if index >= cells else 180)
                found.append((index, x + (2 * r[1] - 1) * across, y, turn, 0.74 + 0.30 * r[3]))
                row += 1
        return found

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        ink = QColor(self.ink)
        ink.setAlphaF(self.ART_ALPHA[self.dark])
        painter.setPen(QPen(ink, 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        drawings = self.drawings()
        try:
            painter.setClipRect(QRectF(0, float(self.top()) + 2, self.width(), self.height()))  # never over the line
        except Exception:  # noqa: BLE001
            pass
        for index, x, y, turn, scale in self.places():
            painter.save()
            painter.translate(x, y)
            painter.rotate(turn)
            painter.scale(scale, scale)
            try:
                drawings[index](painter, QPointF(0, 0))
            except Exception:  # noqa: BLE001 — a background must not stop painting
                pass
            painter.restore()
        painter.end()

    @staticmethod
    def _atom(painter, centre, r):
        painter.drawEllipse(centre, r, r)

    def _benzene(self, painter, c):
        r = 17
        points = [c + QPointF(r * math.cos(math.radians(90 + 60 * k)), -r * math.sin(math.radians(90 + 60 * k))) for k in range(6)]
        painter.drawPolygon(QPolygonF(points))
        painter.drawEllipse(c, r * 0.58, r * 0.58)
        for p in points:  # the C–H bonds, short
            d = (p - c) / r
            painter.drawLine(p, p + d * 7)

    def _water(self, painter, c):
        o = c + QPointF(0, -6)
        self._atom(painter, o, 6)
        for sign in (-1, 1):
            a = math.radians(90 + sign * 52.25)
            d = QPointF(math.cos(a), math.sin(a))
            h = o + d * 21
            painter.drawLine(o + d * 6, h - d * 4)
            self._atom(painter, h, 4)

    def _chain(self, painter, c):
        points = [c + QPointF(-21 + 14 * k, (-6 if k % 2 else 6)) for k in range(4)]
        for p, q in zip(points, points[1:]):
            painter.drawLine(p, q)
        for p in points:
            self._atom(painter, p, 2.2)
        painter.drawLine(points[1] + QPointF(0, -2.2), points[1] + QPointF(0, -14))  # a substituent
        self._atom(painter, points[1] + QPointF(0, -17), 3)

    def _methane(self, painter, c):
        self._atom(painter, c, 5)
        ends = [QPointF(0, -20), QPointF(-18, 9), QPointF(15, 12), QPointF(15, -7)]
        for k, e in enumerate(ends):
            d = e / math.hypot(e.x(), e.y())
            pen = painter.pen()
            if k == 3:  # the bond behind the carbon: dashed
                dashed = QPen(pen)
                dashed.setStyle(Qt.PenStyle.DashLine)
                painter.setPen(dashed)
            painter.drawLine(c + d * 5, c + e)
            painter.setPen(pen)
            self._atom(painter, c + e + d * 3, 3)

    # more molecules and the cells of crystals -------------------------------------------------------
    def _bonded(self, painter, centre, r, ends, small=3):
        """An atom of radius r with bonds to the atoms at centre + e of `ends` (radius `small`)."""
        self._atom(painter, centre, r)
        for e in ends:
            d = e / math.hypot(e.x(), e.y())
            painter.drawLine(centre + d * r, centre + e - d * small)
            self._atom(painter, centre + e, small)

    def _ammonia(self, painter, c):
        self._bonded(painter, c + QPointF(0, -5), 5.5, [QPointF(-17, 13), QPointF(0, 20), QPointF(17, 13)])

    def _carbon_dioxide(self, painter, c):
        self._atom(painter, c, 4)
        for sign in (-1, 1):
            o = c + QPointF(sign * 21, 0)
            self._atom(painter, o, 5.5)
            for dy in (-2, 2):  # the double bonds
                painter.drawLine(c + QPointF(sign * 4.5, dy), o - QPointF(sign * 6, -dy))

    def _ethene(self, painter, c):
        left, right = c + QPointF(-9, 0), c + QPointF(9, 0)
        for dy in (-2, 2):
            painter.drawLine(left + QPointF(0, dy), right + QPointF(0, dy))
        for carbon, sign in ((left, -1), (right, 1)):
            for dy in (-13, 13):
                h = carbon + QPointF(sign * 11, dy)
                painter.drawLine(carbon, h)
                self._atom(painter, h + QPointF(sign * 2, dy / 6.5), 2.6)

    def _ring(self, c, r, n, start=90):
        return [c + QPointF(r * math.cos(math.radians(start + 360 / n * k)), -r * math.sin(math.radians(start + 360 / n * k)))
                for k in range(n)]

    def _naphthalene(self, painter, c):
        r = 13
        half = r * math.cos(math.radians(30))
        for sign in (-1, 1):
            centre = c + QPointF(sign * half, 0)
            painter.drawPolygon(QPolygonF(self._ring(centre, r, 6)))
            painter.drawEllipse(centre, r * 0.55, r * 0.55)

    def _pyridine(self, painter, c):
        r = 16
        points = self._ring(c, r, 6)
        for k in range(6):
            p, q = points[k], points[(k + 1) % 6]
            d = (q - p) / math.hypot((q - p).x(), (q - p).y())
            painter.drawLine(p + d * (5 if k == 0 else 0), q - d * (5 if k == 5 else 0))  # the gap of the nitrogen
        self._atom(painter, points[0], 5)
        painter.drawEllipse(c, r * 0.55, r * 0.55)

    def _ethanol(self, painter, c):
        points = [c + QPointF(-20, 6), c + QPointF(-6, -6), c + QPointF(8, 6)]
        for p, q in zip(points, points[1:]):
            painter.drawLine(p, q)
        for p in points[:2]:
            self._atom(painter, p, 2.2)
        self._atom(painter, points[2] + QPointF(4, 3), 5)  # the oxygen
        painter.drawLine(points[2] + QPointF(8.5, 0.5), points[2] + QPointF(18, -7))
        self._atom(painter, points[2] + QPointF(20.5, -9), 2.8)

    def _cyclopentane(self, painter, c):
        points = self._ring(c, 15, 5)
        painter.drawPolygon(QPolygonF(points))
        for p in points:
            self._atom(painter, p, 2.2)

    def _formaldehyde(self, painter, c):
        carbon, oxygen = c + QPointF(0, 4), c + QPointF(0, -17)
        self._atom(painter, oxygen, 5.5)
        for dx in (-2, 2):
            painter.drawLine(carbon + QPointF(dx, 0), oxygen + QPointF(dx, 5.5))
        for sign in (-1, 1):
            h = carbon + QPointF(sign * 14, 11)
            painter.drawLine(carbon, h)
            self._atom(painter, h + QPointF(sign * 2, 1.6), 2.8)

    def _cell(self, painter, c, a, shift, atoms=True):
        """A cube in projection: the front square of side a, the back one moved by `shift` and dashed where hidden."""
        front = [c + QPointF(-a / 2, -a / 2 + 4), c + QPointF(a / 2, -a / 2 + 4), c + QPointF(a / 2, a / 2 + 4), c + QPointF(-a / 2, a / 2 + 4)]
        back = [p + shift for p in front]
        painter.drawPolygon(QPolygonF(front))
        pen = painter.pen()
        dashed = QPen(pen)
        dashed.setStyle(Qt.PenStyle.DashLine)
        for k in range(4):
            hidden = k == 3  # the lower left corner of the back face is behind the cube
            painter.setPen(dashed if hidden else pen)
            painter.drawLine(front[k], back[k])
            painter.setPen(dashed if hidden or (k + 1) % 4 == 3 else pen)
            painter.drawLine(back[k], back[(k + 1) % 4])
        painter.setPen(pen)
        if atoms:
            for p in front + back:
                self._atom(painter, p, 2.4)
        return front, back

    def _cubic_cell(self, painter, c):
        """Rock salt in a line: the cube with atoms at the corners and the other ion on the middles of the front edges."""
        front, _back = self._cell(painter, c, 26, QPointF(11, -9))
        for k in range(4):
            self._atom(painter, (front[k] + front[(k + 1) % 4]) / 2, 1.5)

    def _centred_cell(self, painter, c):
        """A body-centred cube (CsCl, α-Fe): the atom in the middle, its dashed lines to two corners."""
        front, back = self._cell(painter, c, 26, QPointF(11, -9))
        centre = (front[0] + back[2]) / 2
        self._atom(painter, centre, 4)
        pen = painter.pen()
        dashed = QPen(pen)
        dashed.setStyle(Qt.PenStyle.DotLine)
        painter.setPen(dashed)
        painter.drawLine(centre, front[3])
        painter.drawLine(centre, back[1])
        painter.setPen(pen)

    def _hexagonal_cell(self, painter, c):
        """A hexagonal prism (graphite, hcp): two flattened hexagons and the vertical edges."""
        def hexagon(centre):
            return [centre + QPointF(17 * math.cos(math.radians(60 * k)), -7 * math.sin(math.radians(60 * k))) for k in range(6)]

        top, bottom = hexagon(c + QPointF(0, -11)), hexagon(c + QPointF(0, 13))
        painter.drawPolygon(QPolygonF(top))
        pen = painter.pen()
        dashed = QPen(pen)
        dashed.setStyle(Qt.PenStyle.DashLine)
        for k in range(6):
            behind = k in (1, 2)  # the far edges of the bottom and the far vertical ones
            painter.setPen(dashed if k in (0, 1, 2) else pen)
            painter.drawLine(bottom[k], bottom[(k + 1) % 6])
            painter.setPen(dashed if behind else pen)
            painter.drawLine(top[k], bottom[k])
        painter.setPen(pen)
        for p in top + bottom:
            self._atom(painter, p, 2.2)



class SiteArrow(QWidget):
    """«↗» over the button of a section that opens outside the window — the Atlas of the site. At the right of
    the button in the open panel, in the top right corner of the icon on the narrow rail; transparent for the mouse.
    Drawn as two lines (not a character of the font: the typeface of the panel may have no arrows)."""

    def __init__(self, button):
        super().__init__(button)
        self.setObjectName('siteArrow')
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.color = QColor('#2a62b8')  # the accent of the panel (set_color follows the theme, as NavGroup)
        self.visible = None  # how much of the button is seen (place)
        button.installEventFilter(self)
        self.place()

    def set_color(self, ink):
        self.color = QColor(ink)
        self.update()

    def eventFilter(self, watched, event):
        if watched is self.parentWidget() and event.type() in (QEvent.Type.Resize, QEvent.Type.Show):
            self.place()
        return False

    def narrow(self):
        """The rail: the panel shows less of the button than its width (the buttons keep the width of the open panel
        and the panel is cut to the rail — the arrow at the right of the button would be out of sight there)."""
        return self.visible is not None and self.visible < self.parentWidget().width()

    def place(self, visible=None):
        """visible: how much of the button the panel shows now (HubWindow._apply_progress, also while it slides)."""
        if visible is not None:
            self.visible = visible
        button = self.parentWidget()
        if self.narrow():  # in the top right corner of the icon (QPushButton#nav: padding 12 px, icon 22 px)
            self.setGeometry(35, 4, 11, 11)
        else:
            self.setGeometry(button.width() - 26, (button.height() - 14) // 2, 14, 14)
        self.raise_()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(self.color, 1.6 if self.narrow() else 1.8)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        m, w = 1.5, self.width() - 1.5
        painter.drawLine(QPointF(m, w), QPointF(w, m))  # the shaft, bottom left to top right
        head = w * 0.55
        painter.drawLine(QPointF(w - head, m), QPointF(w, m))  # the head: along the top
        painter.drawLine(QPointF(w, m), QPointF(w, m + head))  # and down the right side
        painter.end()


class NavGroup(QWidget):
    """Section buttons that belong together (Компас · Молекула and Компас · Кристалл), joined by a
    thin vertical line along their left edge (over the buttons, transparent for the mouse)."""

    def __init__(self, spacing=6, parent=None):
        from PySide6.QtWidgets import QFrame, QVBoxLayout

        super().__init__(parent)
        self.column = QVBoxLayout(self)
        self.column.setContentsMargins(0, 0, 0, 0)
        self.column.setSpacing(spacing)
        self.line = QFrame(self)
        self.line.setObjectName('navGroupLine')
        self.line.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.set_color('#2a62b8')

    def add(self, button):
        self.column.addWidget(button)
        self.line.raise_()

    def set_color(self, ink, alpha=0.45):
        color = QColor(ink)
        self.line.setStyleSheet(
            f'QFrame#navGroupLine {{background: rgba({color.red()}, {color.green()}, {color.blue()}, {alpha}); border: none;}}'
        )

    def resizeEvent(self, event):
        self.line.setGeometry(1, 10, 1, max(0, self.height() - 20))
        self.line.raise_()
        super().resizeEvent(event)
