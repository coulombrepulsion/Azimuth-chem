"""A spectrum being recorded by the status line of Spectrum while the calculation runs."""

import pytest

from tests.gui_support import *  # noqa: F401,F403 — the fixtures app, window and the helpers


def test_the_recording_goes_and_fades():
    from modules.spectrum.views.spectrum_pulse import CYCLE, SCAN, recorded, trace

    assert recorded(0) == (0.0, 0.0)
    assert recorded(CYCLE * SCAN / 2) == pytest.approx((0.5, 0.0))
    scan, fade = recorded(CYCLE * (SCAN + (1 - SCAN) / 2))
    assert scan == 1.0 and fade == pytest.approx(0.5)
    assert recorded(CYCLE) == recorded(0)  # again
    values = [trace(k / 200) for k in range(201)]
    assert all(0.0 <= v <= 1.0 for v in values) and max(values) > 0.9 and min(values) < 0.1


def test_it_shows_while_the_calculation_runs(window, app):
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtCore import QRectF

    pulse, board = window.calc_pulse, window.activities
    assert pulse.isHidden() and not pulse.timer.isActive()
    opened = []
    board.start('calculation', 'H2O · B3LYP', lambda: opened.append(1))
    assert not pulse.isHidden() and pulse.timer.isActive() and 'H2O · B3LYP' in pulse.toolTip()
    pulse.mousePressEvent(None)
    assert opened == [1]
    frames = []
    for seconds in (0.3, 1.2, 2.0):  # the trace grows behind the scan line
        image = QImage(96, 30, QImage.Format.Format_ARGB32)
        image.fill(0)
        painter = QPainter(image)
        pulse.paint_frame(painter, QRectF(2, 3, 92, 24), seconds)
        painter.end()
        frames.append(sum(image.pixelColor(x, y).alpha() > 0 for x in range(96) for y in range(30)))
    assert frames[0] < frames[1] < frames[2]
    board.finish('calculation', 'done', '1 мин')
    assert pulse.isHidden() and not pulse.timer.isActive()
    board.remove('calculation')
    board.start('conformers', 'Поиск конформеров')  # other work: not this sign (the compass of the panel shows it)
    assert pulse.isHidden()
    board.remove('conformers')
