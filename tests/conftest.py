"""Shared test guard: no test may wait on a modal window.

Contract: the Qt tests run offscreen (QT_QPA_PLATFORM=offscreen), where a modal QMessageBox,
QInputDialog, QFileDialog, QColorDialog or a QMenu.exec popup is invisible and is never closed,
so the whole run hangs (test_rotation_about_a_bond_window stopped the run for
30 minutes on a QMessageBox.warning). Each test therefore starts with these static calls replaced
by stubs that return the "cancelled" answer at once and record the call (also QDialog.exec of any
dialog, QMessageBox objects included); a test that opened such a
window without replacing it itself fails at teardown with the window title. A test that expects a
dialog replaces it with monkeypatch as before (its own setattr comes later and wins).
The guard is inactive when PySide6 is not installed (pure tests run without Qt).
"""

import os
import shutil
import tempfile
import time

import pytest

# the settings of the run are an INI file of its own (azimuth/settings.py) — never the registry or the
# plist of the user (on Windows the registry could not be written there, and saved values changed the inputs)
os.environ.setdefault('AZIMUTH_SETTINGS_FILE', os.path.join(tempfile.mkdtemp(prefix='azimuth-test-settings-'),
                                                            'settings.ini'))
# the logs of errors of the run go to a folder of its own, not to ~/Library/Logs/Azimuth of the user
os.environ.setdefault('AZIMUTH_LOG_DIR', tempfile.mkdtemp(prefix='azimuth-test-logs-'))
# the projects made by the tests (drafts of opened files) go to a folder of their own, not to
# ~/Documents/Azimuth/Проекты of the user
os.environ.setdefault('AZIMUTH_PROJECTS_DIR', tempfile.mkdtemp(prefix='azimuth-test-projects-'))


def pytest_configure(config):
    """On Windows the folder of pytest «%TEMP%\\pytest-of-<user>» may be closed to the user who runs the
    tests (it was made by another run — as an administrator, or by another user — and Python 3.13 gives mkdir(0o700)
    an owner-only ACL there): then every test with tmp_path fails in its setup with «WinError 5» (175 of them on the
    first run on Windows). Then the tests take a folder of their own in the temporary folder."""
    if os.name != 'nt' or getattr(config.option, 'basetemp', None):
        return
    from pathlib import Path

    try:
        import getpass

        user = getpass.getuser()
    except Exception:  # noqa: BLE001 — pytest itself falls back to «unknown»
        user = 'unknown'
    root = Path(tempfile.gettempdir()) / f'pytest-of-{user}'
    try:
        if root.exists():
            next(os.scandir(root), None)
    except PermissionError:
        # a folder of its own for each pytest process: tools/test.py runs several at once, and pytest empties its
        # basetemp at the start — one shared folder let the parts delete each other's files (FileExistsError in the
        # setup, FileNotFoundError in the middle of a test: 54 failures of the run of 2026-11-25 on Windows)
        base = Path(tempfile.gettempdir())
        for old in base.glob('azimuth-pytest-*'):  # the folders of earlier runs, older than a day
            try:
                if time.time() - old.stat().st_mtime > 86400:
                    shutil.rmtree(old, ignore_errors=True)
            except OSError:
                pass
        config.option.basetemp = str(base / f'azimuth-pytest-{os.getpid()}')


try:
    from PySide6.QtGui import QColor
    from PySide6.QtWidgets import QColorDialog, QDialog, QFileDialog, QInputDialog, QMenu, QMessageBox
except ImportError:  # pure modules tested without Qt
    QMessageBox = None


def _title(args):
    texts = [a for a in args if isinstance(a, str)]
    return texts[0] if texts else '(без заголовка)'


@pytest.fixture(autouse=True)
def no_modal_windows(monkeypatch):
    if QMessageBox is None:
        yield
        return
    opened = []

    def stub(kind, answer):
        def call(*args, **kwargs):
            opened.append(f'{kind}: {_title(args)}')
            return answer() if callable(answer) else answer

        return staticmethod(call)

    ok, no = QMessageBox.StandardButton.Ok, QMessageBox.StandardButton.No
    for name in ('warning', 'information', 'critical'):
        monkeypatch.setattr(QMessageBox, name, stub('QMessageBox.' + name, ok))
    monkeypatch.setattr(QMessageBox, 'question', stub('QMessageBox.question', no))
    for name in ('getText', 'getItem', 'getMultiLineText'):
        monkeypatch.setattr(QInputDialog, name, stub('QInputDialog.' + name, ('', False)))
    for name in ('getInt', 'getDouble'):
        monkeypatch.setattr(QInputDialog, name, stub('QInputDialog.' + name, (0, False)))
    for name in ('getOpenFileName', 'getSaveFileName'):
        monkeypatch.setattr(QFileDialog, name, stub('QFileDialog.' + name, ('', '')))
    monkeypatch.setattr(QFileDialog, 'getOpenFileNames', stub('QFileDialog.getOpenFileNames', ([], '')))
    monkeypatch.setattr(QFileDialog, 'getExistingDirectory', stub('QFileDialog.getExistingDirectory', ''))
    monkeypatch.setattr(QColorDialog, 'getColor', stub('QColorDialog.getColor', QColor))

    def menu_exec(self, *args, **kwargs):
        opened.append('QMenu.exec: ' + (self.title() or '(меню)'))
        return None

    monkeypatch.setattr(QMenu, 'exec', menu_exec)

    def dialog_exec(self, *args, **kwargs):  # any modal window (ServerDialog hung the Windows run)
        opened.append('QDialog.exec: ' + (self.windowTitle() or type(self).__name__))
        return QDialog.DialogCode.Rejected

    monkeypatch.setattr(QDialog, 'exec', dialog_exec)
    yield
    if opened:
        pytest.fail('Тест открыл модальное окно, не подменив его (offscreen оно повесило бы прогон): '
                    + '; '.join(opened), pytrace=False)


@pytest.fixture(autouse=True)
def no_real_keychain(monkeypatch):
    """No test reads or writes the Keychain of the computer: a dict stands for it, and the passwords of the session
    start empty: a test window must never show a password kept on the computer."""
    try:
        from modules.sextant import keychain
    except ImportError:
        yield
        return
    monkeypatch.setattr(keychain, 'STORE', {})
    monkeypatch.setattr(keychain, 'SESSION', {})
    yield


_LEFT = {}  # module: the number of windows its tests left


@pytest.fixture(autouse=True)
def windows_of_the_test(request):
    """The windows a test made and left (dialogs, tool windows, whole Studio windows whose fixture did not
    delete them) are deleted when the test ends; a window of a fixture of the module was made before and stays. They
    stayed alive for the rest of the run (3994 by test_gui alone), and every later app.setStyleSheet (a theme switch)
    restyled them all: 7 s per switch in the full run instead of 0.5 s, 7 s for a test of recovery. Only the windows
    made by Python and not there before the test are deleted (never Qt's own: the tooltip, popups of combo boxes); their
    number per module is shown at the end of the run."""
    if QMessageBox is None:
        yield
        return
    import shiboken6
    from PySide6.QtCore import QCoreApplication, QEvent
    from PySide6.QtWidgets import QApplication

    def tops():
        # a group run alone may have made a QCoreApplication (test_tasks) —
        # it has no windows; QApplication.instance() returns it all the same
        app = QApplication.instance()
        if not isinstance(app, QApplication):
            return {}
        return {shiboken6.getCppPointer(w)[0]: w for w in app.topLevelWidgets()}

    before = set(tops())
    yield
    left = [w for key, w in tops().items() if key not in before and shiboken6.isValid(w) and shiboken6.createdByPython(w)]
    for w in left:
        try:
            for d in getattr(w, 'all_documents', lambda: [])():
                d.dirty = False
            if hasattr(w, 'dirty'):
                w.dirty = False
            w.hide()
            w.deleteLater()
        except RuntimeError:  # its C++ part is already gone
            pass
    if left:
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        name = request.module.__name__
        _LEFT[name] = _LEFT.get(name, 0) + len(left)


def pytest_terminal_summary(terminalreporter):
    if _LEFT:
        terminalreporter.write_line('Окна, оставленные тестами (удалены после теста): '
                                    + ', '.join(f'{name} {count}' for name, count in sorted(_LEFT.items(), key=lambda x: -x[1])))
