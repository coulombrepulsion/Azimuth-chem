"""azimuth/tasks.py: the background tasks of the window (0.91.66 — the audit of 2026-11-04, R2)."""

import threading
import time

import pytest

pytest.importorskip('PySide6')


@pytest.fixture
def app():
    # a QApplication, as the other tests make: a QCoreApplication made first stays for the whole run (it
    # cannot become a QApplication), and every later test of a window would fail
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_workers_are_limited_and_one_key_is_coalesced(app):
    from azimuth.tasks import Tasks

    tasks = Tasks(limit=2)
    gate = threading.Event()
    started, shown = [], []

    def work(name):
        def body():
            started.append(name)
            gate.wait(10)
            return name
        return body

    for k in range(12):  # twelve requests of one file: one worker, the newest waits
        tasks.run('same', work(f'same-{k}'), shown.append)
    tasks.run('other', work('other'), shown.append)
    tasks.run('third', work('third'), shown.append)
    time.sleep(0.2)
    assert tasks.working() == 2 and sorted(started) == ['other', 'same-0']  # the limit; «third» waits
    gate.set()
    assert tasks.wait(10, app)
    assert sorted(started) == ['other', 'same-0', 'same-11', 'third']
    assert sorted(shown) == ['other', 'same-11', 'third']  # only the newest answer of «same»
    assert tasks.working() == 0 and not tasks.busy()


def test_cancel_drops_waiting_and_running(app):
    from azimuth.tasks import Tasks

    tasks = Tasks(limit=1)
    gate = threading.Event()
    started, shown = [], []

    def work(name):
        def body():
            started.append(name)
            gate.wait(10)
            return name
        return body

    tasks.run('a', work('a'), shown.append)
    tasks.run('b', work('b'), shown.append)
    time.sleep(0.1)
    tasks.cancel('b')  # not started: never starts
    tasks.cancel('a')  # running: finishes unseen
    assert not tasks.busy() and tasks.working() == 1  # «busy» is about answers, «working» about threads
    gate.set()
    assert tasks.wait(10, app)
    assert started == ['a'] and shown == []


def test_a_failure_goes_to_failed(app):
    from azimuth.tasks import Tasks

    tasks = Tasks()
    errors = []

    def broken():
        raise ValueError('bad file')

    tasks.run('x', broken, lambda r: None, errors.append)
    assert tasks.wait(10, app)
    assert [str(e) for e in errors] == ['bad file']


def test_a_work_with_a_spinner_is_named_by_its_title(app):
    # the name of the work,
    # not the tooltip of its spinner
    from azimuth import tasks
    from azimuth.controls import Spinner

    spinner = Spinner(16)
    spinner.setToolTip('Считается…')
    assert tasks.run_spinning(lambda step: tasks.busy(), spinner, 'Расчёт IGMH…') == 'Расчёт IGMH…'
    assert tasks.run_spinning(lambda step: tasks.busy()) and not tasks.busy()


def test_closing_the_program_under_a_work_asks_and_stops_it(app, monkeypatch):
    import threading

    from PySide6.QtGui import QCloseEvent
    from PySide6.QtWidgets import QMainWindow, QMessageBox

    from azimuth import tasks

    window = QMainWindow()
    asked = []
    answers = iter([QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Yes])
    monkeypatch.setattr(QMessageBox, 'question', lambda *a, **k: asked.append(a[2]) or next(answers))
    cancelled = threading.Event()
    blocker = tasks._Blocker(cancelled, [window], 'Бассейны AIM…')
    for expected in (False, True):
        event = QCloseEvent()
        assert blocker.eventFilter(window, event) and not event.isAccepted()  # not closed at once
        app.processEvents()
        assert cancelled.is_set() == expected
    assert len(asked) == 2 and 'Бассейны AIM' in asked[0]
    assert blocker.quit_after is window  # closed when the work has stopped
    # the close of the button of the title comes first to the window of the system (QWindow): asked about too
    window.show()
    app.processEvents()
    blocker = tasks._Blocker(threading.Event(), [window, window.windowHandle()], 'Бассейны AIM…')
    answers = iter([QMessageBox.StandardButton.Yes])
    event = QCloseEvent()
    assert blocker.eventFilter(window.windowHandle(), event) and not event.isAccepted()
    app.processEvents()
    assert blocker.quit_after is window and len(asked) == 3
    window.close()
    window.deleteLater()


def test_esc_stops_a_work_also_where_it_is_a_shortcut(app):
    # on the model Esc is the shortcut «Снять выделение» — Qt asks
    # the shortcut first (ShortcutOverride); the work is stopped there
    import threading

    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtWidgets import QMainWindow

    from azimuth import tasks

    window = QMainWindow()
    cancelled = threading.Event()
    blocker = tasks._Blocker(cancelled, [window], 'Бассейны AIM…')
    event = QKeyEvent(QEvent.Type.ShortcutOverride, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
    assert blocker.eventFilter(window, event) and cancelled.is_set() and event.isAccepted()
    window.deleteLater()
