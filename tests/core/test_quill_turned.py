"""0.247.0: the pictures of states (azimuth/state_icons.py) are drawn as they are — nothing is mirrored any more (until
0.246.0 Quill with the magnifier and the animation of the running calculation were turned to the left)."""

import pytest
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


def test_nothing_is_turned(app):
    from azimuth import quill

    assert quill.TURNED_LEFT == frozenset()
    frame = QPixmap(10, 10)
    assert quill.turned('calc-running', frame) is frame and quill.turned('empty-result', frame) is frame


def test_the_window_of_the_calculation_plays_no_animation():
    from pathlib import Path

    source = (Path(__file__).resolve().parents[2] / 'modules' / 'sextant' / 'job_window.py').read_text(encoding='utf-8')
    start = source.index('    def show_animation(')
    body = source[start:source.index('\n    def ', start + 10)]
    assert 'QMovie(' not in body and 'self.show_picture(name, size)' in body
