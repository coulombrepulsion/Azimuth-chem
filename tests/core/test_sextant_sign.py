"""The sign of a calculation of Sextant in the left panel — a sextant whose index arm
sweeps its scale there and back (hub/job_indicator.sight, SIGHT s) and whose star flashes when the arm comes to it."""

import pytest
from PySide6.QtGui import QColor, QImage, QPainter

from hub.job_indicator import SIGHT, draw_sextant, sight


def test_the_arm_goes_there_and_back_and_the_star_flashes_at_the_far_end():
    assert sight(0) == pytest.approx((0.0, 0.0))
    share, flash = sight(SIGHT / 2)
    assert share == pytest.approx(1.0) and flash == pytest.approx(1.0)  # at the star: brightest
    assert sight(SIGHT) == pytest.approx(sight(0))  # a cycle
    assert sight(SIGHT / 4)[0] == pytest.approx(0.5) and sight(SIGHT / 4)[1] == 0.0
    shares = [sight(SIGHT * k / 40)[0] for k in range(41)]
    assert all(0.0 <= x <= 1.0 for x in shares) and max(shares) == pytest.approx(1.0)


def _drawn(seconds, dark=False, running=True):
    image = QImage(96, 96, QImage.Format.Format_ARGB32)
    image.fill(QColor(0, 0, 0, 0))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    draw_sextant(painter, 96, seconds, dark, running)
    painter.end()
    return image


def test_the_sextant_is_drawn_and_moves():
    from PySide6.QtWidgets import QApplication

    QApplication.instance() or QApplication([])
    start, middle = _drawn(0.0), _drawn(SIGHT / 2)
    painted = sum(start.pixelColor(x, y).alpha() > 0 for x in range(0, 96, 2) for y in range(0, 96, 2))
    assert painted > 150  # the frame, the scale, the arm, the star
    assert start != middle  # the arm has moved, the star is brighter
    assert _drawn(0.3, running=False) == _drawn(1.7, running=False)  # stopped: still
    assert _drawn(0.0, dark=True) != start  # the colours of the dark theme


def test_the_sign_is_large_and_its_ring_is_not_cut():
    # 40 px (was 28), the
    # sextant or the compass 0.68 of it; the ring of the share done and the comet inside the picture
    import time

    from PySide6.QtWidgets import QApplication

    from hub.job_indicator import CALCULATION, INNER, SIZE, JobIndicator

    QApplication.instance() or QApplication([])
    assert SIZE == 40 and INNER * SIZE > 0.64 * 28 * 1.4

    class Studio:
        activities = None

    for key, total in ((CALCULATION, None), ('conformers', 8)):
        studio = Studio()
        sign = JobIndicator(lambda: studio)
        assert sign.iconSize().width() == SIZE
        board = sign.board()
        board.start(key, 'работа', total=total)
        board.park(key)
        if total:
            board.progress(key, done=7)  # the ring almost whole
        for item in sign.shown():
            item.started = time.monotonic() - 0.5
        image = sign.paint_icon(SIZE, 2.0).toImage()
        assert sign.sextant_drawn == (key == CALCULATION)
        side = image.width()
        edge = [image.pixelColor(x, y).alpha() for x in range(side) for y in (0, side - 1)]
        edge += [image.pixelColor(x, y).alpha() for y in range(side) for x in (0, side - 1)]
        assert max(edge) < 40, key  # nothing drawn up to the edge: no ring cut by it
