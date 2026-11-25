"""The folder of the file windows (azimuth/file_dialogs.py): the last folder a file was opened from."""

from pathlib import Path

import pytest

from azimuth import file_dialogs


class Settings(dict):
    def value(self, key, default=None):
        return self.get(key, default)

    def setValue(self, key, value):
        self[key] = value


def test_the_last_folder_is_kept_and_used(tmp_path, monkeypatch):
    monkeypatch.setitem(file_dialogs._state, 'root', None)  # no folder of the projects here
    settings = Settings()
    calls = []

    def dialog(parent, caption, dir, *args, **kwargs):
        calls.append(dir)
        return (str(tmp_path / 'calc' / 'water.out'), 'filter')

    (tmp_path / 'calc').mkdir()
    opened = file_dialogs.wrap(dialog, settings, 'open').__func__
    assert opened(None, 'Открыть', str(Path.home())) == (str(tmp_path / 'calc' / 'water.out'), 'filter')
    assert calls[-1] == str(Path.home())  # nothing kept yet: as given
    assert settings[file_dialogs.KEY] == str(tmp_path / 'calc')
    opened(None, 'Открыть', str(Path.home()))
    assert calls[-1] == str(tmp_path / 'calc')  # the next window starts there
    given = str(tmp_path / 'given')  # an absolute folder on every system («/opt/homebrew/bin» has no drive on Windows)
    opened(None, 'Открыть', given)
    assert calls[-1] == given  # a folder given on purpose stays
    assert file_dialogs.start(str(Path.home() / 'picture.png'), settings) == str(tmp_path / 'calc' / 'picture.png')
    settings[file_dialogs.KEY] = str(tmp_path / 'gone')
    assert file_dialogs.start(str(Path.home()), settings) == str(Path.home())  # the folder is gone: as before


def test_cancel_keeps_the_folder(tmp_path, monkeypatch):
    monkeypatch.setitem(file_dialogs._state, 'root', None)
    settings = Settings({file_dialogs.KEY: str(tmp_path)})
    many = file_dialogs.wrap(lambda *a, **k: ([], ''), settings, 'open-many').__func__
    many(None, 'Открыть', '')
    assert settings[file_dialogs.KEY] == str(tmp_path)
    folder = file_dialogs.wrap(lambda parent, caption, dir, *a, **k: str(tmp_path / 'x'), settings, 'folder').__func__
    (tmp_path / 'x').mkdir()
    folder(None, 'Папка', '')
    assert settings[file_dialogs.KEY] == str(tmp_path / 'x')


def test_install_wraps_the_dialogs_once(monkeypatch, tmp_path):
    pytest.importorskip('PySide6')
    from PySide6.QtWidgets import QFileDialog

    seen = []
    for name in ('getOpenFileName', 'getOpenFileNames', 'getExistingDirectory', 'getSaveFileName'):
        monkeypatch.setattr(QFileDialog, name, staticmethod(lambda parent, caption, dir, *a, **k: seen.append(dir) or ('', '')))
    monkeypatch.setitem(file_dialogs._state, 'installed', False)
    monkeypatch.setitem(file_dialogs._state, 'settings', None)
    monkeypatch.setitem(file_dialogs._state, 'root', None)
    file_dialogs.install(Settings({file_dialogs.KEY: str(tmp_path)}))
    file_dialogs.install(Settings({file_dialogs.KEY: str(tmp_path)}))  # again: not wrapped twice
    QFileDialog.getOpenFileName(None, 'Открыть', str(Path.home()))
    assert seen == [str(tmp_path)]
    assert getattr(QFileDialog.getOpenFileName, '__wrapped__', None) is not None
    assert getattr(QFileDialog.getOpenFileName.__wrapped__, '__wrapped__', None) is None


def test_first_the_projects_then_the_folder_opened_from(tmp_path, monkeypatch):
    projects = tmp_path / 'Azimuth' / 'Проекты'
    projects.mkdir(parents=True)
    other = tmp_path / 'Downloads'
    other.mkdir()
    monkeypatch.setitem(file_dialogs._state, 'root', lambda: projects)
    settings = Settings()
    calls = []

    def dialog(parent, caption, dir, *args, **kwargs):
        calls.append(dir)
        return (str(other / 'report.zip'), '')

    saved = file_dialogs.wrap(dialog, settings, 'save').__func__
    saved(None, 'Сохранить', 'report.zip')
    assert calls[-1] == str(projects / 'report.zip')  # a bare name: into the projects, not the working folder
    assert file_dialogs.KEY not in settings  # a file saved elsewhere does not move where «Открыть…» starts
    opened = file_dialogs.wrap(lambda parent, caption, dir, *a, **k: calls.append(dir) or (str(other / 'w.xyz'), ''),
                               settings, 'open').__func__
    opened(None, 'Открыть', str(Path.home()))
    assert calls[-1] == str(projects)  # first: the projects of Azimuth
    opened(None, 'Открыть', str(Path.home()))
    assert calls[-1] == str(other)  # then the folder the user opened from
