"""Playback contract of the Compass optimization drawer: one printed step per tick; no
interpolation or skipped gaps."""

import pytest
from PySide6.QtWidgets import QApplication
from modules.compass.panels.trajectory_drawer import TrajectoryDrawer
from modules.spectrum.readers.orca import OptimizationStep


@pytest.fixture
def panel():
    app = QApplication.instance() or QApplication([])
    widget = TrajectoryDrawer()
    widget.load(tuple(OptimizationStep(i, None, None) for i in (1, 2, 3)))
    yield widget
    widget.close()
    widget.deleteLater()
    app.processEvents()


def test_play_pause_end_restart(panel):
    panel.set_playing(True)
    panel.advance()
    assert panel.current == 1 and panel.timer.isActive()
    panel.set_playing(False)
    panel.advance()
    assert panel.current == 1
    panel.set_playing(True)
    panel.advance()
    assert panel.current == 2 and not panel.timer.isActive()
    panel.set_playing(True)
    assert panel.current == 0
    panel.reset_playback()
    assert panel.current == 0 and not panel.timer.isActive()


def test_manual_selection_and_reload_stop(panel):
    panel.set_playing(True)
    panel.select(1)
    assert not panel.timer.isActive()
    panel.set_playing(True)
    panel.load(())
    assert not panel.timer.isActive() and not panel.play.isEnabled()


def test_hide_stops(panel):
    panel.show()
    QApplication.processEvents()
    panel.set_playing(True)
    panel.hide()
    assert not panel.timer.isActive()


def test_single_step(panel):
    panel.load((OptimizationStep(1, None, None),))
    panel.set_playing(True)
    assert not panel.play.isEnabled() and not panel.timer.isActive()


def test_energies_relative_in_kcal(panel):
    panel.load((OptimizationStep(1, -76.0, None), OptimizationStep(2, -76.001, None)))
    assert panel.table.item(0, 1).text() == '+0.00' and panel.table.item(1, 1).text() == '-0.63'
