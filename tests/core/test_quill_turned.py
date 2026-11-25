"""The Quill with the magnifier
(Spectrum without a result) and the animation of the running calculation are shown mirrored, the files are not
changed. A picture of two colours stands in for the WebP here (the full pictures: tests/gui/test_gui_settings.py)."""

import pytest
from PySide6.QtGui import QColor, QImage, QPixmap
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope='module')
def app():
    # QApplication, not QGuiApplication: the one application of the process — the tests of the window that run after
    # this file in the same part need setStyleSheet and widgets
    return QApplication.instance() or QApplication([])


def _halves(tmp_path):
    image = QImage(40, 20, QImage.Format.Format_ARGB32)
    for x in range(40):
        for y in range(20):
            image.setPixelColor(x, y, QColor('#d03030') if x < 20 else QColor('#3050d0'))
    path = tmp_path / 'halves.png'
    image.save(str(path))
    return path


def test_the_two_pictures_are_turned_to_the_left(app, tmp_path, monkeypatch):
    from azimuth import quill

    picture = _halves(tmp_path)
    monkeypatch.setattr(quill, 'path', lambda name: picture)
    for name, left in (('empty-result', '#3050d0'), ('calc-running', '#3050d0'), ('calc-done', '#d03030'), ('save', '#d03030')):
        shown = quill.pixmap(name, 40, 1.0).toImage()
        assert shown.pixelColor(2, 5).name() == left and shown.pixelColor(37, 5).name() != left, name
    frame = QPixmap(str(picture))
    frame.setDevicePixelRatio(2.0)
    turned = quill.turned('calc-running', frame)
    assert turned.devicePixelRatio() == 2.0 and turned.toImage().pixelColor(2, 5).name() == '#3050d0'
    assert quill.turned('calc-done', frame) is frame and quill.turned('empty-result', QPixmap()).isNull()


def test_the_window_of_the_calculation_turns_each_frame():
    from pathlib import Path

    source = (Path(__file__).resolve().parents[2] / 'modules' / 'sextant' / 'job_window.py').read_text(encoding='utf-8')
    start = source.index('    def show_animation(')
    body = source[start:source.index('\n    def ', start + 10)]
    assert 'self.picture.setPixmap(quill.turned(name, pixmap))' in body
