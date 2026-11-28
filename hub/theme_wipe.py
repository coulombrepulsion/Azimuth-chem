"""The change of theme as a circle from the theme button.

HEADER
    Pressing the theme button of the hub: to the dark theme the darkness spreads from the button over the whole window;
    back to the light theme it gathers into the button again. The program is restyled once, under a still picture of
    the window as it was; the picture is then cut by a closed wavy line round the icon of the button — like ink
    spreading on paper, not a circle: outside the growing shape (to dark) or inside the shrinking one (to light). A thin
    rim of the accent colour marks the edge.
    Wilkinson convention, sections 1-8.

§2 ALGORITHM
    still = window.grab(); the overlay shows it whole and is painted at once; the theme is applied (slow: every widget
    is restyled, which the still picture hides); then a QVariantAnimation t: 0 → 1 over WIPE_MS with an ease in and
    out; the mean radius ρ = R·t (to dark) or R·(1 − t) (to light); the edge r(θ) = ρ·(1 + Σ aₖ sin(kθ + φₖ + ωₖ t))
    with the waves k = 3, 5, 8, 13 (amplitudes 0.07 … 0.012, each drifting at its own speed); R = (distance to the
    farthest corner) / (1 − Σ aₖ), so that the shape covers the window at the end.
    The centre is the icon of the theme button (left in the button), not the middle of the wide button.
    0.249.21: the new look is a still picture too (set_after — the window grabbed once after the restyling, the
    overlay hidden for it): the overlay is then opaque and paints the two pictures, and nothing under it is painted
    while the ink moves. Before, the part already in the new theme was the window itself, painted anew at every frame
    under the clip — on Windows the change of theme went in jerks (the owner, 2026-11-28: «тема очень дерганно
    переключилась»).
    WIPE_MS is 950 ms with an ease out: the ink moves from the first frame, so the answer to the click looks quicker.
    To the dark theme an ease in (InCubic), the reverse of the way back: the darkness grows out of the button point
    instead of jumping out at once. The restyling stays under the still picture: done before the wipe or under ink
    covering the window, its pause would be seen.
§4 SPECIFICATION
    ThemeWipe(parent, still: QPixmap, centre: QPointF, spreading: bool); set_after(picture: QPixmap); start(done=None);
    radius() -> float (mean); edge() -> QPainterPath; edge_radius(theta) -> float. centre is in the coordinates of
    parent.
    wipe_enabled() -> bool: not on the offscreen and minimal platforms (tests) and not with WIPE_MS = 0.
§7 TEST CASES tests/hub/test_hub.py::test_theme_wipe_circle.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QEasingCurve, QPointF, QRectF, Qt, QVariantAnimation
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

WIPE_MS = 950
WAVES = ((3, 0.07, 0.4, 1.3), (5, 0.045, 2.1, -1.9), (8, 0.025, 4.0, 2.7), (13, 0.012, 1.0, -3.6))  # k, a, φ, ω
POINTS = 240


def wipe_enabled():
    return WIPE_MS > 0 and QGuiApplication.platformName() not in ('offscreen', 'minimal')


class ThemeWipe(QWidget):
    def __init__(self, parent, still, centre, spreading):
        super().__init__(parent)
        self.still = still
        self.centre = QPointF(centre)
        self.spreading = bool(spreading)  # True: to the dark theme, the circle grows
        self.progress = 0.0
        self.after = None  # the window in the new theme (set_after); None — the window itself shows through
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)
        self.setGeometry(parent.rect())
        self.animation = QVariantAnimation(self)
        self.animation.setDuration(WIPE_MS)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        # the two ways are each other's reverse — back to the light theme the ink gathers fast from the corners
        # and slows down into the button (OutCubic), to the dark theme it starts slowly from the button and speeds up
        # towards the corners (InCubic); OutCubic both ways made the darkness jump out at once (by the user's remark)
        self.animation.setEasingCurve(QEasingCurve.Type.InCubic if self.spreading else QEasingCurve.Type.OutCubic)
        self.animation.valueChanged.connect(self._step)

    def far(self):
        """The mean radius at which even the deepest trough of the edge is past the farthest corner."""
        c, w, h = self.centre, self.width(), self.height()
        corner = max(math.hypot(x - c.x(), y - c.y()) for x in (0, w) for y in (0, h)) + 4
        return corner / (1.0 - sum(a for _, a, _, _ in WAVES))

    def edge_radius(self, theta):
        t = self.progress
        return self.radius() * (1.0 + sum(a * math.sin(k * theta + phase + speed * t) for k, a, phase, speed in WAVES))

    def edge(self):
        path = QPainterPath()
        for i in range(POINTS):
            theta = 2 * math.pi * i / POINTS
            r = self.edge_radius(theta)
            point = QPointF(self.centre.x() + r * math.cos(theta), self.centre.y() + r * math.sin(theta))
            path.moveTo(point) if i == 0 else path.lineTo(point)
        path.closeSubpath()
        return path

    def radius(self):
        r = self.far()
        return r * self.progress if self.spreading else r * (1.0 - self.progress)

    def set_after(self, picture):
        """The window in the new theme as a still picture: the overlay becomes opaque, the window under it is not
        painted while the ink moves."""
        self.after = picture if picture is not None and not picture.isNull() else None
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, self.after is not None)
        self.update()

    def start(self, done=None):
        def finished():
            if done is not None:
                done()
            self.hide()
            self.deleteLater()

        self.animation.finished.connect(finished)
        self.animation.start()

    def _step(self, value):
        self.progress = float(value)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.radius()
        blot = self.edge() if r > 0.5 else QPainterPath()
        whole = QPainterPath()
        whole.addRect(QRectF(self.rect()))
        if self.after is not None:
            p.drawPixmap(self.rect(), self.after)
        p.setClipPath(whole.subtracted(blot) if self.spreading else blot)
        p.drawPixmap(self.rect(), self.still)
        p.setClipping(False)
        if r > 1.0 and 0.0 < self.progress < 1.0:  # the edge, fading out in the last quarter of the way
            fade = min(1.0, (1.0 - self.progress) * 4.0) if self.progress > 0.75 else 1.0
            p.setPen(QPen(QColor(110, 162, 240, round(150 * fade)), 2.0))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(blot)
        p.end()
