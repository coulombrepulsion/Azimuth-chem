"""The sign of a running calculation in Spectrum: a small spectrum being recorded by the status line.

HEADER
    A sign of life in Spectrum during a calculation. While the calculation of the program
    runs (the activity «calculation» of the board, azimuth/activities.py — the one the sign of the left panel follows)
    a little spectrum is recorded at the right of the status line: a scan line goes from left to right, the bands
    rise behind it and stay; at the end the trace fades and the recording starts again. Its tooltip is the title of the
    calculation, a click opens its window. Wilkinson convention, sections 1-8.

§2 ALGORITHM
    recorded(t) -> (scan, fade): the place of the scan line (0…1) and how faded the trace is, at t s of a cycle of
    CYCLE s (the scan for SCAN of it, then the fade). trace(x): the bands BANDS (Lorentz curves) at x (0…1), 0…1.
§4 SPECIFICATION
    SpectrumPulse(board=None): follow(board) — shown while the calculation of board runs, the timer with it;
    paint_frame(painter, rect, t) draws the frame of the moment t.
§7 TEST CASES tests/gui/test_spectrum_pulse.py.
"""

import time

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from azimuth.i18n import tr

CALCULATION = 'calculation'  # the key of the calculation of Sextant on the board (hub/job_indicator.CALCULATION)
CYCLE = 3.2  # s: one recording
SCAN = 0.78  # the share of the cycle the scan takes; the rest — the fade
BANDS = ((0.14, 0.55, 0.035), (0.30, 0.9, 0.025), (0.43, 0.35, 0.03), (0.58, 1.0, 0.02), (0.71, 0.5, 0.04),
         (0.86, 0.7, 0.025))  # (place, height, half width) of the bands, in shares of the field
FRAME_MS = 40


def recorded(seconds):
    """(the place of the scan line 0…1, the fade 0…1 of the trace) at that moment of the cycle."""
    t = (seconds % CYCLE) / CYCLE
    if t < SCAN:
        return t / SCAN, 0.0
    return 1.0, (t - SCAN) / (1 - SCAN)


def trace(x):
    return min(1.0, sum(h * w * w / ((x - c) ** 2 + w * w) for c, h, w in BANDS))


class SpectrumPulse(QWidget):
    def __init__(self, board=None, parent=None):
        super().__init__(parent)
        self.setFixedSize(QSize(96, 30))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.started = time.monotonic()
        self.item = None
        self.timer = QTimer(self)
        self.timer.setInterval(FRAME_MS)
        self.timer.timeout.connect(self.update)
        self.hide()
        if board is not None:
            board.listen(self.follow)
            self.follow(board)

    def follow(self, board):
        """Shown, and moving, while the calculation of board runs."""
        item = board.get(CALCULATION)
        running = item is not None and item.state == 'running'
        self.item = item if running else None
        if running and not self.timer.isActive():
            self.started = time.monotonic()
            self.timer.start()
        elif not running:
            self.timer.stop()
        self.setToolTip(tr('Идёт расчёт · {} — щелчок открывает его окно').format(item.title) if running else '')
        self.setVisible(running)

    def mousePressEvent(self, event):
        if self.item is not None and self.item.open is not None:
            self.item.open()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.paint_frame(p, QRectF(self.rect()).adjusted(2, 3, -2, -3), time.monotonic() - self.started)
        p.end()

    def paint_frame(self, p, rect, seconds):
        dark = self.palette().window().color().lightness() < 128
        draw_pulse(p, rect, seconds, dark, QColor(self.palette().mid().color()))


def draw_pulse(p, rect, seconds, dark, axis):
    """The frame of the moment seconds in rect (also the sign of waiting on the pill of Spectrum, azimuth.ui.Spinner
    kind 'spectrum'): the axis in axis, the trace and the scan line in the accent of dark or light."""
    accent = QColor('#6ea2f0' if dark else '#2a62b8')
    scan, fade = recorded(seconds)
    base = rect.bottom()
    p.setPen(QPen(axis, 1))
    p.drawLine(QPointF(rect.left(), base), QPointF(rect.right(), base))
    ink = QColor(accent)
    ink.setAlphaF(1.0 - 0.85 * fade)
    path = QPainterPath(QPointF(rect.left(), base))
    steps = 60
    for k in range(steps + 1):
        x = k / steps
        if x > scan:
            break
        path.lineTo(QPointF(rect.left() + x * rect.width(), base - trace(x) * rect.height()))
    p.setPen(QPen(ink, 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.drawPath(path)
    if fade == 0.0:  # the scan line and its spot
        x = rect.left() + scan * rect.width()
        line = QColor(accent)
        line.setAlpha(110)
        p.setPen(QPen(line, 1, Qt.PenStyle.DashLine))
        p.drawLine(QPointF(x, rect.top()), QPointF(x, base))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(accent)
        p.drawEllipse(QPointF(x, base - trace(scan) * rect.height()), 2.2, 2.2)
