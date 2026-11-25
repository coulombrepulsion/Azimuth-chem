"""Press for a discrete step; hold for smaller timed increments.

ExpandingButton — an icon that unfolds smoothly into «icon + text» while the pointer is over it (or it
has the keyboard focus) and folds back after; the text stays the button's text (tooltip, accessible name,
retranslation), only the painting shows it when there is room.
"""

from PySide6.QtCore import QEasingCurve, QRect, QSize, Qt, QTimer, QVariantAnimation
from PySide6.QtGui import QIcon, QPalette
from PySide6.QtWidgets import QPushButton, QStyle, QStyleOptionButton, QStylePainter, QWidget

COLLAPSED = 34  # the size of the icon buttons of the program (azimuth.icons.iconify)
UNFOLD_MS = 170


class HoldButton(QPushButton):
    def __init__(self, step, tick, begin, end):
        super().__init__()
        self.step = step
        self.tick = tick
        self.begin = begin
        self.end = end
        self.running = False
        self.repeated = False
        self.delay = QTimer(self)
        self.delay.setSingleShot(True)
        self.delay.setInterval(200)
        self.timer = QTimer(self)
        self.timer.setInterval(25)
        self.delay.timeout.connect(self.start_repeat)
        self.timer.timeout.connect(self.repeat)
        self.pressed.connect(self.start)
        self.released.connect(self.finish)

    def start(self):
        self.running = True
        self.repeated = False
        self.begin()
        self.delay.start()

    def start_repeat(self):
        if self.running and self.isDown():
            self.repeat()
            if self.running:
                self.timer.start()

    def repeat(self):
        if not self.isDown() or not self.isEnabled():
            self.finish(False)
            return
        self.repeated = True
        self.tick()

    def finish(self, step=True):
        self.delay.stop()
        self.timer.stop()
        if not self.running:
            return
        self.running = False
        try:
            if step and not self.repeated:
                self.step()
        finally:
            self.end()

    def hideEvent(self, event):
        self.finish(False)
        super().hideEvent(event)


class ExpandingButton(QPushButton):
    """An icon button that unfolds into icon + text."""

    def __init__(self, text, callback=None, name='', parent=None):
        from azimuth.icons import icon

        super().__init__(text, parent)
        self.setProperty('iconic', True)
        self.setProperty('expanding', True)
        self.setProperty('quail_icon', name)
        self.setIcon(icon(name))
        self.setIconSize(QSize(21, 21))
        self.setToolTip(text)
        self.setAccessibleName(text)
        self.setFixedSize(COLLAPSED, COLLAPSED)
        self.unfolded = False
        self.foldable = True  # False — only the icon and the tooltip (Sextant)
        self.animation = QVariantAnimation(self)
        self.animation.setDuration(UNFOLD_MS)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.valueChanged.connect(lambda value: self.setFixedWidth(int(value)))
        if callback is not None:
            self.clicked.connect(callback)

    def setText(self, text):  # retranslation and callers keep the tooltip and the width right
        super().setText(text)
        self.setToolTip(text)
        self.setAccessibleName(text)
        if self.unfolded and self.animation.state() != QVariantAnimation.State.Running:
            self.setFixedWidth(self.full_width())

    def full_width(self):
        return COLLAPSED + self.fontMetrics().horizontalAdvance(self.text()) + 12

    def unfold(self, on):
        on = bool(on) and self.foldable and self.isEnabled() and bool(self.text())
        if on == self.unfolded:
            return
        self.unfolded = on
        self.animation.stop()
        self.animation.setStartValue(self.width())
        self.animation.setEndValue(self.full_width() if on else COLLAPSED)
        self.animation.start()

    def enterEvent(self, event):
        self.unfold(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self.hasFocus():
            self.unfold(False)
        super().leaveEvent(event)

    def focusInEvent(self, event):
        if event.reason() in (Qt.FocusReason.TabFocusReason, Qt.FocusReason.BacktabFocusReason):
            self.unfold(True)
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        if not self.underMouse():
            self.unfold(False)
        super().focusOutEvent(event)

    def changeEvent(self, event):
        from PySide6.QtCore import QEvent

        if event.type() == QEvent.Type.EnabledChange and not self.isEnabled():
            self.unfold(False)
        super().changeEvent(event)

    def paintEvent(self, event):
        painter = QStylePainter(self)
        option = QStyleOptionButton()
        self.initStyleOption(option)
        option.text = ''
        option.icon = QIcon()
        painter.drawControl(QStyle.ControlElement.CE_PushButton, option)
        h = self.height()
        mode = QIcon.Mode.Normal if self.isEnabled() else QIcon.Mode.Disabled
        state = QIcon.State.On if self.isChecked() else QIcon.State.Off
        side = (COLLAPSED - 21) // 2
        self.icon().paint(painter, QRect(side, (h - 21) // 2, 21, 21), Qt.AlignmentFlag.AlignCenter, mode, state)
        if self.width() > COLLAPSED + 2 and self.text():
            group = QPalette.ColorGroup.Active if self.isEnabled() else QPalette.ColorGroup.Disabled
            painter.setPen(self.palette().color(group, QPalette.ColorRole.ButtonText))
            painter.setClipRect(QRect(COLLAPSED - 4, 0, self.width() - COLLAPSED, h))
            painter.drawText(
                QRect(COLLAPSED - 2, 0, self.full_width(), h),
                int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
                self.text(),
            )


class Spinner(QWidget):
    """«something is going on» without a window (the check of a server, a calculation, a long task).

    The compass of the icon of the program (assets/app-icon/glyph.svg) — its ring, its needle (the blue point, the grey
    tail), its axis — with the needle turning as a real one swings: fast, slower, overshooting a little; the golden arc
    of the azimuth runs from the north to the needle (on the icon it marks the angle; here it follows the turn)."""

    STEP_MS = 30
    from azimuth.compass_glyph import COLOURS as COLORS  # the colours of the icon (glyph.svg, dark/glyph.svg)

    def __init__(self, size=16, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.angle = 0.0  # the needle, degrees clockwise from the north
        self.since = 0.0  # when the wait began (time.monotonic)
        self.timer = QTimer(self)
        self.timer.setInterval(self.STEP_MS)
        self.timer.timeout.connect(self._turn)
        self.hide()

    def _turn(self):
        # with inertia (swing): a turn eased from a rest at the north to a rest at the north
        from time import monotonic

        self.angle = swing(monotonic() - self.since)
        self.update()

    def start(self):
        from time import monotonic

        if not self.timer.isActive():
            self.since = monotonic()  # each wait begins at the north, with the arc empty
            self.angle = 0.0
        self.show()
        self.timer.start()

    def stop(self):
        self.timer.stop()
        self.hide()

    def running(self):
        return self.timer.isActive()

    def paintEvent(self, event):
        from PySide6.QtGui import QPainter

        painter = QPainter(self)
        draw_compass(painter, self.width(), self.height(), self.angle,
                     self.palette().window().color().lightness() < 128)
        painter.end()


def draw_compass(painter, width, height, angle, dark):
    """The compass of the icon of the program in a box width × height, its needle at angle (degrees
    clockwise from the north) and the golden arc of the azimuth from the north to the needle (azimuth_arc). Both signs
    of waiting draw it: Spinner here and azimuth.ui.Spinner (the pill of Compass with «Esc — отменить»).
    Drawn from the lines of the icon itself (azimuth.compass_glyph: glyph.svg, below 40 px
    glyph-small.svg) — the same ring, divisions, meridian, arc, needle and axis, scaled to the box; no star."""
    from PySide6.QtCore import QPointF, QRectF
    from PySide6.QtGui import QBrush, QColor, QPainter, QPen, QPolygonF

    from azimuth import compass_glyph as glyph

    colors = glyph.COLOURS[bool(dark)]
    shape = glyph.VARIANTS[glyph.variant(min(width, height))]
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.translate(width / 2, height / 2)
    k = min(width, height) / glyph.BOX
    painter.scale(k, k)  # the units of the icon from here

    def pen(name, width, opacity=1.0):
        colour = QColor(colors[name])
        colour.setAlphaF(opacity)
        line = QPen(colour, width)
        line.setCapStyle(Qt.PenCapStyle.RoundCap)
        return line

    import math

    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(pen('ring', shape['ring'], glyph.RING_OPACITY))
    painter.drawEllipse(QPointF(0, 0), glyph.RING_RADIUS, glyph.RING_RADIUS)
    for degrees, r0, r1, line, opacity in glyph.divisions(glyph.variant(min(width, height))):
        a = math.radians(degrees)
        painter.setPen(pen('ink', line, opacity))
        painter.drawLine(QPointF(math.sin(a) * r0, -math.cos(a) * r0), QPointF(math.sin(a) * r1, -math.cos(a) * r1))
    if shape['meridian']:
        length, line, opacity, dash, gap = shape['meridian']
        dotted = pen('ink', line, opacity)
        dotted.setDashPattern([dash / line, gap / line])  # in widths of the pen, as stroke-dasharray of the icon
        painter.setPen(dotted)
        painter.drawLine(QPointF(0, 0), QPointF(0, -length))
    radius, line = shape['arc']
    start, span = azimuth_arc(angle)
    if span:
        painter.setPen(pen('arc', line))
        painter.drawArc(QRectF(-radius, -radius, 2 * radius, 2 * radius), int(start * 16), int(span * 16))
    painter.rotate(angle % 360.0)
    point, half, tail = shape['needle']
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(QColor(colors['point'])))
    painter.drawPolygon(QPolygonF([QPointF(0, -point), QPointF(half, 0), QPointF(-half, 0)]))
    painter.setBrush(QBrush(QColor(colors['tail'])))
    painter.drawPolygon(QPolygonF([QPointF(0, tail), QPointF(half, 0), QPointF(-half, 0)]))
    axis, eye = shape['axis']
    painter.setBrush(QBrush(QColor(colors['axis'])))
    painter.drawEllipse(QPointF(0, 0), axis, axis)
    painter.setBrush(QBrush(QColor(colors['eye'])))
    painter.drawEllipse(QPointF(0, 0), eye, eye)
    painter.restore()


def azimuth_arc(angle):
    """The golden arc over two turns of the needle (angle 0–720°,
    clockwise from the north) — on the first turn it grows from the north behind the needle, on the second its start
    follows the needle and it shrinks back to the north; at 360° and at 720° (= 0) it is whole and empty, no jump.
    → (start, span) in the degrees of QPainter.drawArc (counterclockwise from 3 o'clock; the span negative —
    clockwise)."""
    a = angle % 720.0
    if a < 360.0:
        return 90.0, -a
    return 90.0 - (a - 360.0), -(720.0 - a)


# a turn is TURN s eased by EASE (slow to start, fast in the middle, slowing to a stop at the north), then the
# needle rests PAUSE s at the north; two turns a cycle — the arc grows on the first and is taken back on the second.
# The compass of the site moves the same way (tools/build_atlas_site.py, COMPASS_*: the same numbers).
TURN, PAUSE = 1.3, 0.3  # s
EASE = (0.6, 0.0, 0.3, 1.0)  # the cubic Bézier of CSS cubic-bezier(.6,0,.3,1)


def ease(u, curve=EASE):
    """y of the cubic Bézier (0,0)-(x1,y1)-(x2,y2)-(1,1) at x = u (0…1), as CSS computes a timing function."""
    x1, y1, x2, y2 = curve
    if u <= 0.0 or u >= 1.0:
        return 0.0 if u <= 0.0 else 1.0
    bez = lambda t, a, b: 3 * (1 - t) ** 2 * t * a + 3 * (1 - t) * t * t * b + t ** 3
    lo, hi = 0.0, 1.0
    for _ in range(40):  # x(t) grows with t: bisection
        mid = (lo + hi) / 2
        if bez(mid, x1, x2) < u:
            lo = mid
        else:
            hi = mid
    return bez((lo + hi) / 2, y1, y2)


def swing(seconds):
    """The angle of the needle (degrees clockwise from the north, 0–720) at that moment: two turns a cycle of
    2 × (TURN + PAUSE) s, each turn eased (EASE) and ended by a rest at the north (azimuth_arc: the arc fills on the
    first, empties on the second)."""
    cycle = TURN + PAUSE
    t = seconds % (2 * cycle)
    turn, within = divmod(t, cycle)
    return 360.0 * turn + (360.0 * ease(within / TURN) if within < TURN else 360.0)