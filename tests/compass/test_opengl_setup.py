"""modules/compass/view/opengl_setup.py: the switch to OpenGL composition is made only before QApplication."""

import pytest

pytest.importorskip('PySide6')

from modules.compass.view import opengl_setup  # noqa: E402


def test_prepare_refuses_once_the_application_exists():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    assert app is not None
    assert opengl_setup.prepare() is False
    assert not opengl_setup.ready() and 'already' in opengl_setup.reason()


def test_environment_overrides_the_preference(monkeypatch):
    monkeypatch.setenv('AZIMUTH_OPENGL', '1')
    assert opengl_setup.wanted() is True
    monkeypatch.setenv('AZIMUTH_OPENGL', '0')
    assert opengl_setup.wanted() is False
