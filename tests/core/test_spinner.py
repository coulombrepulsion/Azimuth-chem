"""The waiting sign of the program — the compass of its icon with a turning needle (azimuth/controls.py Spinner,
2026-11-13).

Oracle: the colors of assets/app-icon/glyph.svg — the point of the needle #2a62b8 (dark theme #6ea2f0), the arc of
the azimuth #b8893f; the needle swings (its steps differ) and turns on (a full turn in about 50 steps)."""

from PySide6.QtGui import QColor, QImage, QPalette
from PySide6.QtWidgets import QApplication

from azimuth.controls import Spinner


def app():
    return QApplication.instance() or QApplication([])


def colors(spinner):
    image = spinner.grab().toImage().convertToFormat(QImage.Format.Format_RGB32)
    return {QColor(image.pixel(x, y)).name() for x in range(image.width()) for y in range(image.height())}


def near(seen, color, tolerance=24):
    """A pixel of about this color (the edges are smoothed: at 16 px few pixels keep the exact one)."""
    target = QColor(color)
    return any(abs(QColor(c).red() - target.red()) + abs(QColor(c).green() - target.green())
               + abs(QColor(c).blue() - target.blue()) <= tolerance for c in seen)


def themed(size, dark):
    spinner = Spinner(size)
    palette = spinner.palette()
    palette.setColor(QPalette.ColorRole.Window, QColor('#1e2430' if dark else '#f4f5f7'))
    spinner.setPalette(palette)
    return spinner


def test_the_needle_swings_and_turns():
    # the needle of Spinner follows swing (with inertia) from the moment the wait began, at the north
    from time import monotonic

    from azimuth.controls import PAUSE, TURN, swing

    app()
    spinner = Spinner(24)
    spinner.start()
    assert spinner.angle == 0 and spinner.running()
    for t in (0.2, TURN / 2, TURN + PAUSE / 2, TURN + PAUSE + TURN / 2, 2 * (TURN + PAUSE) - 0.01):
        spinner.since = monotonic() - t
        spinner._turn()
        assert abs(spinner.angle - swing(t)) < 3  # the few ms of the call
    spinner.stop()


def test_it_is_the_compass_of_the_icon():
    app()
    for dark, point in ((False, '#2a62b8'), (True, '#6ea2f0')):
        spinner = themed(48, dark)
        spinner.angle = 120  # the arc of the azimuth is drawn from the north to here
        seen = colors(spinner)
        assert near(seen, point, 6) and near(seen, Spinner.COLORS[dark]['arc'], 6)
    seen = colors(themed(16, False))
    assert near(seen, '#2a62b8')  # 16 px: the small glyph, its needle


def test_the_sign_of_the_pill_is_the_compass_too():
    # the sign of waiting of run_waiting (azimuth.ui.Spinner, by the pill of Compass) — the same compass, not the ring
    # of 0.100.2
    from azimuth.controls import swing
    from azimuth.ui import Spinner as PillSpinner

    app()
    for text, point in (('#202020', '#2a62b8'), ('#f0f0f0', '#6ea2f0')):  # dark text on a light pill, and the reverse
        sign = PillSpinner(colour=text)
        assert sign.width() == 20
        assert near(colors(sign), point, 30)
        sign.timer.stop()
    # a turn starts slowly, is fast in the middle, slows to a
    # stop at the north and rests there; the second turn the same (the arc taken back, azimuth_arc)
    from azimuth.controls import PAUSE, TURN

    cycle = TURN + PAUSE
    assert swing(0) == 0 and abs(swing(TURN) - 360) < 1e-6 and swing(TURN + PAUSE / 2) == 360
    assert abs(swing(cycle + TURN) - 720) < 1e-6 and swing(2 * cycle) == 0
    speed = lambda t: (swing(t + 0.005) - swing(t)) / 0.005
    start, middle, end = speed(0.02), speed(TURN * 0.5), speed(TURN - 0.03)
    assert start < middle / 6 and end < middle / 4 and middle > 360 / TURN  # slow, fast, slowing to a stop
    assert speed(TURN + PAUSE / 2) == 0  # resting at the north
    angles = [swing(k / 100) for k in range(int(2 * cycle * 100))]
    assert all(b >= a for a, b in zip(angles, angles[1:]))  # never back
    assert speed(cycle + TURN * 0.5) == speed(TURN * 0.5)  # the second turn moves as the first


def test_the_arc_fills_and_empties_without_a_jump():
    # the length of the golden arc goes 0 → 360° on the first turn and 360° → 0 on the second, its ends move with the
    # needle
    from azimuth.controls import azimuth_arc

    lengths = [-azimuth_arc(a)[1] for a in range(0, 721, 1)]
    assert lengths[0] == 0 and lengths[360] == 360 and lengths[720] == 0
    assert max(abs(x - y) for x, y in zip(lengths, lengths[1:])) <= 1.0  # no jump anywhere, the wrap at 720 included
    start, span = azimuth_arc(450)  # the second turn: from the needle (at 90°, 3 o'clock) clockwise back to the north
    assert (start, span) == (0.0, -270.0)
    assert azimuth_arc(90) == (90.0, -90.0)  # the first turn: from the north clockwise to the needle


def test_it_is_drawn_as_the_icon():
    """The compass of waiting drawn over the icon itself —
    assets/app-icon/glyph.svg from 40 px, glyph-small.svg below, light and dark — without its star, the arrowhead and
    the arc (their angle is the icon's own), centred: the same pixels away from the band of the arc."""
    import math
    import re
    from pathlib import Path

    from PySide6.QtCore import QByteArray, QRectF
    from PySide6.QtGui import QPainter
    from PySide6.QtSvg import QSvgRenderer

    from azimuth.controls import draw_compass

    app()
    folder = Path(__file__).resolve().parents[2] / 'assets' / 'app-icon'
    for side in (16, 20, 48, 96):
        for dark in (False, True):
            text = (folder / ('dark' if dark else '') / ('glyph-small.svg' if side < 40 else 'glyph.svg')).read_text()
            filled = re.findall(r'<path d="[^"]+" fill="[^"]+"/>', text)
            for piece in (filled[0], filled[-1]):  # the arrowhead of the arc, the star
                text = text.replace(piece, '')
            text = re.sub(r'<path d="M[\d.]+ [\d.]+ A[^"]+"[^>]*/>', '', text)  # the arc
            text = text.replace('viewBox="160 160 760 760"', 'viewBox="132 132 760 760"')  # the compass in the middle
            ground = QColor('#1e2430' if dark else '#ffffff')
            icon, drawn = (QImage(side, side, QImage.Format.Format_ARGB32) for _ in range(2))
            for image in (icon, drawn):
                image.fill(ground)
            p = QPainter(icon)
            QSvgRenderer(QByteArray(text.encode())).render(p, QRectF(0, 0, side, side))
            p.end()
            p = QPainter(drawn)
            draw_compass(p, side, side, 360 + 52, dark)  # the needle of the icon points to its star, at 52°
            p.end()
            k, (radius, width) = side / 760, ((215, 22) if side >= 40 else (200, 44))
            away = [(x, y) for x in range(side) for y in range(side)
                    if abs(math.hypot(x + 0.5 - side / 2, y + 0.5 - side / 2) - radius * k) > width * k / 2 + 1]
            gaps = [sum(abs(a - b) for a, b in zip(icon.pixelColor(x, y).getRgb()[:3], drawn.pixelColor(x, y).getRgb()[:3]))
                    for x, y in away]
            assert max(gaps) <= 24 and sum(gaps) / len(gaps) < 2, (side, dark, max(gaps))
