"""The look of popups and marks on Windows (the owner's Windows, 2026-11-28): every menu rounded by the program, not
square behind its border nor rounded a second time by the system; the ticks of «Ход расчёта» drawn, not the glyph of
the font."""

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMenu

from tests.gui_support import *  # noqa: F401,F403 — the fixtures app, window and the helpers


def test_every_menu_is_rounded_when_it_is_polished(app, monkeypatch):
    from azimuth import ui

    monkeypatch.setattr(ui._MenuRounding, 'filter', None)
    monkeypatch.setattr(sys, 'platform', 'darwin')  # the Mac too (0.249.32)
    assert ui.round_menus(app) and not ui.round_menus(app)  # once
    try:
        menu = QMenu()  # as a context menu of a text field: not passed to rounded()
        menu.addAction('один')
        menu.ensurePolished()
        assert menu.property('quail_round') and menu.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        assert menu.windowFlags() & Qt.WindowType.FramelessWindowHint
        assert not ui.system_corners_off(menu)  # not Windows: nothing asked of the system
        menu.deleteLater()
    finally:
        app.removeEventFilter(ui._MenuRounding.filter)


def test_the_corners_of_windows_are_asked_only_of_popups_of_the_program(app, monkeypatch):
    from azimuth import ui

    plain = QMenu()
    monkeypatch.setattr(sys, 'platform', 'win32')
    assert not ui.system_corners_off(plain)  # not drawn by the program with its own corners
    assert not ui.system_corners_off(None)
    assert (ui.DWMWA_WINDOW_CORNER_PREFERENCE, ui.DWMWCP_DONOTROUND) == (33, 1)
    plain.deleteLater()


def test_the_tick_of_a_stage_is_a_picture_of_two_scales(app, tmp_path, monkeypatch):
    from modules.sextant import job_window

    monkeypatch.setattr(job_window, 'MARKS_FOLDER', tmp_path)
    html = job_window.mark_image('check', '#3a9a5b')
    assert html.startswith('<img ') and '✓' not in html
    one, two = tmp_path / 'check-3a9a5b-13.png', tmp_path / 'check-3a9a5b-13@2x.png'
    assert one.is_file() and two.is_file() and Path(one).as_posix() in html
    from PySide6.QtGui import QImage

    assert QImage(str(two)).width() == 2 * QImage(str(one)).width() == 26
    monkeypatch.setattr(job_window, 'MARKS_FOLDER', tmp_path / 'file' / 'below')
    (tmp_path / 'file').write_text('', encoding='utf-8')  # not a folder: the glyph of the font then
    assert job_window.mark_image('check', '#3a9a5b') == '<span style="color: #3a9a5b;">✓</span>'
