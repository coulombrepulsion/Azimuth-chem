"""azimuth/state_icons.py: the pictures of states in thin lines that took the place of Quill in the program (0.247.0)."""

import pytest
from PySide6.QtWidgets import QApplication

from azimuth import state_icons


@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


def test_every_name_of_quill_has_a_picture(app):
    from azimuth import quill

    for name in quill.NAMES:
        text = state_icons.svg(name)
        assert text.startswith('<svg') and 'viewBox="0 0 48 48"' in text and 'currentColor' not in text, name
        assert not state_icons.pixmap(name, 48).isNull(), name
    assert state_icons.svg('missing') == '' and state_icons.pixmap('missing', 48).isNull()
    assert state_icons.svg('empty-model-mirrored') == state_icons.svg('empty-model')


def test_the_pictures_are_thin_lines_in_one_blue(app):
    for name in state_icons.PICTURES:
        image = state_icons.pixmap(name, 48, 1.0).toImage()
        drawn = [(x, y) for x in range(48) for y in range(48) if image.pixelColor(x, y).alpha() > 40]
        assert 20 < len(drawn) < 48 * 48 * 0.35, name  # lines, not filled shapes
        assert image.pixelColor(0, 0).alpha() == 0 and image.pixelColor(47, 0).alpha() == 0, name  # clear corners
    text = state_icons.svg('calc-done', '#123456')
    assert '#123456' in text and state_icons.INK not in text
    picture = state_icons.pixmap('calc-done', 48, 2.0)
    assert picture.width() == 96 and picture.devicePixelRatio() == 2.0
