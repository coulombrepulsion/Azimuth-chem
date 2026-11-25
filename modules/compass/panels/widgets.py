"""Small Compass widgets: the element tile and the expanding arrow button (moved from workspace.py)."""

from PySide6.QtCore import QEasingCurve, QRectF, Qt, QVariantAnimation
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter
from PySide6.QtWidgets import (
    QFrame,
    QPushButton,
    QSizePolicy,
)
from azimuth.core import SYMBOLS

from azimuth.i18n import tr


class ElementTile(QFrame):
    """The chosen element as a cell of the periodic table: atomic number above, symbol below."""

    def __init__(self, callback):
        super().__init__()
        self.callback = callback
        self.symbol = 'C'
        self.setFixedSize(34, 34)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(tr('Элемент для добавления · щелчок — таблица Менделеева'))

    def set_symbol(self, symbol):
        self.symbol = symbol
        self.setAccessibleName(symbol)
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.callback()

    def paintEvent(self, event):
        from PySide6.QtGui import QPainter, QPen, QFont, QColor

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pal = self.palette()
        ink = pal.color(pal.ColorRole.Text)
        dark = pal.color(pal.ColorRole.Window).lightness() < 128
        frame = QColor('#46505e' if dark else '#c3cbd6')
        side = min(self.width(), self.height())
        box = QRectF((self.width() - side) / 2 + 0.5, (self.height() - side) / 2 + 0.5, side - 1, side - 1)
        p.setPen(QPen(frame, 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(box, 7, 7)
        number = str(SYMBOLS.index(self.symbol) + 1) if self.symbol in SYMBOLS else ''
        f = QFont(self.font())
        f.setPixelSize(9)
        p.setFont(f)
        muted = QColor(ink)
        muted.setAlpha(170)
        p.setPen(muted)
        p.drawText(box.adjusted(4, 2, -3, 0), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, number)
        f.setPixelSize(14)
        f.setBold(True)
        p.setFont(f)
        p.setPen(ink)
        p.drawText(box.adjusted(0, 7, 0, 0), Qt.AlignmentFlag.AlignCenter, self.symbol)


class ExpandButton(QPushButton):
    """A small arrow button that widens to show its text while the mouse is over it; drawn by hand so that the text
    fades in and out with the width. Always wide — its text and the arrow; a new text (full = …) or font widens or
    narrows it at once."""

    def __init__(self, text, callback):
        super().__init__('')
        self._full = text
        self.setObjectName('primary')
        self.clicked.connect(callback)
        self.setToolTip(text)
        self.setAccessibleName(text)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.small = 40
        self.progress = 0.0
        self.dark = None  # set by the theme of the program
        self.setFixedSize(self.small, 34)
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(220)
        self.anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.anim.valueChanged.connect(self._step)
        self._step(1.0)

    @property
    def full(self):
        return self._full

    @full.setter
    def full(self, text):
        self._full = text
        self._step(self.progress)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == event.Type.FontChange:
            self._step(self.progress)

    def text(self):
        return self.full + '  →' if self.progress > 0.5 else '→'

    def wide(self):
        f = QFont(self.font())
        f.setWeight(QFont.Weight.DemiBold)
        return QFontMetrics(f).horizontalAdvance(self.full) + self.small + 16

    def _step(self, value):
        self.progress = float(value)
        self.setFixedWidth(round(self.small + (self.wide() - self.small) * self.progress))
        self.update()

    def _go(self, target):
        self.anim.stop()
        self.anim.setStartValue(self.progress)
        self.anim.setEndValue(target)
        self.anim.setDuration(int(220 * abs(target - self.progress)) + 1)
        self.anim.start()

    def enterEvent(self, event):
        self.update()  # the shade under the mouse; it stays wide
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        # the theme is told by the program (Studio.apply_theme sets .dark): the palette of the button could come from
        # the system and say «dark» in the light theme — the button was then light blue the colour of the other filled
        # buttons (the language, «Запустить расчёт»): #2a62b8 — in the dark theme too, as #primary of DARK_STYLE (it was
        # the pale #6ea2f0 there)
        base = QColor('#2a62b8')
        if self.isDown():
            base = base.darker(115)
        elif self.underMouse():
            base = base.darker(108)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(base)
        p.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 8, 8)
        if self.underMouse() and self.isEnabled():
            # drawn by hand, so the gold frame of a blue button under the mouse (QPushButton#primary:hover) is drawn
            # here too
            from PySide6.QtGui import QPen as _Pen

            from hub.branding import NEXT_GOLD

            p.setPen(_Pen(QColor(NEXT_GOLD['dark' if self.dark else 'light']), 1.6))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(QRectF(self.rect()).adjusted(1.0, 1.0, -1.0, -1.0), 7.5, 7.5)
        f = QFont(self.font())
        f.setWeight(QFont.Weight.DemiBold)
        p.setFont(f)
        ink = QColor('#ffffff')
        p.setPen(ink)
        # the arrow drawn like the icons of the program (a 1.8 px line with round ends), not the «→» of the font
        from PySide6.QtGui import QPainterPath, QPen

        cx, cy = self.width() - self.small / 2, self.height() / 2
        arrow = QPainterPath()
        arrow.moveTo(cx - 6.5, cy)
        arrow.lineTo(cx + 6.5, cy)
        arrow.moveTo(cx + 1.5, cy - 5)
        arrow.lineTo(cx + 6.5, cy)
        arrow.lineTo(cx + 1.5, cy + 5)
        p.setPen(QPen(ink, 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(arrow)
        if self.progress > 0:
            ink.setAlphaF(max(0.0, min(1.0, (self.progress - 0.25) / 0.75)))
            p.setPen(ink)
            p.setClipRect(QRectF(0, 0, self.width() - self.small + 6, self.height()))
            p.drawText(
                QRectF(14, 0, self.wide(), self.height()),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                self.full,
            )
