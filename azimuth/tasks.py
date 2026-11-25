"""Background tasks of the program: long work off the window's thread.

§1 PURPOSE
    Reading and parsing a big output (tens of MB) took seconds on the thread of the window, which stopped
    answering meanwhile. A task runs a pure function (no widgets) in a worker thread and hands its result back to
    the window's thread through a queued Qt signal; the window stays responsive.
§2 ALGORITHM
    run(key, work, done, failed=None): a new generation number for the key; a daemon thread calls work(); the
    answer (key, generation, result | exception) is emitted from the worker and delivered in the window's thread
    (the relay QObject lives there). An answer whose generation is not the newest for its key is dropped — a newer
    request (the same file opened again, another result for the same tab) has superseded it; cancel(key) drops the
    running one too. done(result) or failed(exception) run in the window's thread; nothing of the task touches a
    widget in the worker. Python threads share the GIL: the parsers are pure Python, so the window gets the
    interpreter between their bytecodes (switch interval 5 ms) — responsive, not faster.
    run_waiting(parent, title, work, total=0): for work whose result the caller needs at once (an orbital,
    the density, −∇²ρ, Δρ, the critical points, a slice): work(step) runs in a worker thread while the window
    thread waits in a local event loop — the window keeps painting; no progress dialog — the busy cursor,
    the title, the share of step(done, total) and «Esc — отменить» in the status bar, the input of the windows held
    back meanwhile (so nothing changes under the work) — nothing is held back any more; what would change the document
    under the work asks held() and is
    refused (the tabs, the projects, Компас · Молекула ↔ Кристалл), as is a second local work (busy()); in another
    section the work is the sign of its section in the left panel (studio.activities, key WAITING), a click on it
    goes back; Esc sets a flag that step returns as False (the work raises
    InterruptedError). The progress is read by a timer in
    the window thread; the worker touches no widget (the work ran in the window thread and called
    QApplication.processEvents() from its progress callback).
§3 APPLICATIONS
    modules/spectrum/workspace.py (open_output_path: big outputs are read in the background); run_waiting:
    modules/spectrum/views/orbitals_view.py, density_view.py, modules/compass/panels/density_drawer.py.
§4 SPECIFICATION
    Tasks(parent, limit=2): run(key, work, done, failed=None) -> generation; cancel(key); busy(key=None) -> bool (an
    answer is awaited); working() -> the number of worker threads alive; wait(timeout=10.0, app=None) -> bool (tests:
    processes events until nothing runs).
    0.91.66 (the audit of 2026-11-04, R2: «12 requests of one key started 12 workers»): at most limit workers at once;
    one worker per key — a request while its key works waits, and a newer request replaces the waiting one (only the
    newest is computed after the running one); cancel drops the waiting work too. A running work is not interrupted
    (Python threads cannot be stopped): its answer is dropped.
    busy() -> the title of the local work going on (run_waiting, run_spinning) or '';
    held(widget=None) -> bool: busy, and then it is said (a notice of the window); WAITING — the key of the board.
    run_waiting(parent, title, work, total=0, alone=True) -> the result of work(step); its exception is raised again
    (alone — refused, InterruptedError, while another work goes on; False for a reading or a sending)
    (InterruptedError after Esc — no dialog, «Отмена» was its button). run_quietly(work); run_spinning(work,
    spinner=None) (no window — the busy
    cursor and a Spinner of azimuth/controls.py; the fields of the drawer of Compass).
§6 NOTES
    Daemon threads: quitting the program does not wait for a parse; its answer is never delivered (the relay is
    gone with the window).
§7 TESTS
    tests/core/test_tasks.py, tests/test_gui.py::test_big_output_is_read_in_the_background."""

from collections import OrderedDict
import threading
import time

from PySide6.QtCore import QObject, Signal


class _Relay(QObject):
    answer = Signal(object)


class Tasks(QObject):
    def __init__(self, parent=None, limit=2):
        super().__init__(parent)
        self._relay = _Relay(self)
        self._relay.answer.connect(self._deliver)
        self._generation = {}
        self._handlers = {}
        self._running = {}  # key: the generation whose answer is awaited
        self.limit = max(1, int(limit))
        self._lock = threading.Lock()
        self._active = set()  # keys with a worker thread alive
        self._waiting = OrderedDict()  # key: (generation, work) — to start when a worker is free

    def run(self, key, work, done, failed=None):
        generation = self._generation.get(key, 0) + 1
        self._generation[key] = generation
        self._handlers[(key, generation)] = (done, failed)
        self._running[key] = generation
        with self._lock:
            older = self._waiting.pop(key, None)
            if older is not None:  # replaced before it started: its handlers will never be called
                self._handlers.pop((key, older[0]), None)
            self._waiting[key] = (generation, work)
            self._start_free()
        return generation

    def _start_free(self):
        """Start waiting works while workers are free (under the lock); a key never has two workers."""
        for key in list(self._waiting):
            if len(self._active) >= self.limit:
                return
            if key in self._active:
                continue
            generation, work = self._waiting.pop(key)
            self._active.add(key)
            threading.Thread(target=self._body, args=(key, generation, work), name=f'azimuth-task-{key}',
                             daemon=True).start()

    def _body(self, key, generation, work):
        try:
            result, error = work(), None
        except Exception as exc:  # noqa: BLE001 — every failure goes back to the window
            result, error = None, exc
        with self._lock:
            self._active.discard(key)
            self._start_free()
        try:
            self._relay.answer.emit((key, generation, result, error))
        except RuntimeError:  # the window (and the relay) are gone
            pass

    def cancel(self, key):
        """Drop the answer of the task of key; a work not started yet is not started (a running one finishes unseen)."""
        with self._lock:
            waiting = self._waiting.pop(key, None)
        if waiting is not None:
            self._handlers.pop((key, waiting[0]), None)
        if key in self._running:
            self._generation[key] = self._generation.get(key, 0) + 1
            self._running.pop(key, None)

    def busy(self, key=None):
        return bool(self._running) if key is None else key in self._running

    def working(self):
        """The worker threads alive — also those whose answer is no longer awaited."""
        with self._lock:
            return len(self._active)

    def _deliver(self, answer):
        key, generation, result, error = answer
        done, failed = self._handlers.pop((key, generation), (None, None))
        if self._generation.get(key) != generation:
            return  # superseded or cancelled
        self._running.pop(key, None)
        if error is not None:
            if failed is not None:
                failed(error)
            return
        if done is not None:
            done(result)

    def wait(self, timeout=10.0, app=None):
        """Process events until no task runs (for tests); False on timeout."""
        from PySide6.QtCore import QCoreApplication

        app = app or QCoreApplication.instance()
        end = time.monotonic() + timeout
        while (self._running or self.working()) and time.monotonic() < end:
            app.processEvents()
            time.sleep(0.005)
        app.processEvents()
        return not self._running and not self.working()


WAITING = 'waiting'  # the key of the work of run_waiting on the board of the Studio (azimuth/activities.py)
_WORK = {'title': ''}  # the local work going on in the window thread (run_waiting, run_spinning)
# one action is often several works one after another (the points,
# then their paths); the next one begun right after the last ended keeps its page — not the page shown then
_LAST = {'page': None, 'section': '', 'ended': 0.0, 'away': False}
CHAIN_S = 1.5
SECTIONS = {0: 'compass', 1: 'sextant', 2: 'spectrum'}  # the pages of the Studio


def _studio():
    from PySide6.QtWidgets import QApplication, QMainWindow

    app = QApplication.instance()
    for widget in app.topLevelWidgets() if app is not None else ():
        if isinstance(widget, QMainWindow) and hasattr(widget, 'notify') and hasattr(widget, 'stack'):
            return widget
        studio = getattr(widget, 'studio', None)
        if isinstance(studio, QMainWindow) and hasattr(studio, 'notify'):
            return studio
    return None


def busy():
    """The title of the local work going on (run_waiting, run_spinning), or ''. A calculation of Sextant
    is not one here: results are read and looked at while it runs; Sextant does not start a second work meanwhile."""
    return _WORK['title']


def held(widget=None):
    """True (and it is said) while a local work goes on — what would change the document under it, or
    start another work, waits."""
    title = busy()
    if not title:
        return False
    from azimuth.i18n import tr

    studio = _studio()
    if studio is not None:
        # the work itself is on a pill of its own (busy_status) — the message stands above it
        studio.notify(tr('Идёт расчёт: «{}». Дождитесь конца или нажмите Esc, чтобы отменить.').format(
            title.rstrip('…')), 6000)
    return True


def _refuse_second(title):
    """A work asked while another one goes on: said, InterruptedError (the callers end quietly on it)."""
    if held():
        raise InterruptedError(title)


def pill_busy(host, text, on=True):
    """Text on the pill over the model of Compass with the turning compass at its left (as the wait of
    run_waiting puts it there) — on=False takes the compass away. For a work that is not run_waiting (the quick xtb)."""
    from azimuth.ui import Spinner

    if hasattr(host, 'busy_status'):  # the pill of the work itself
        spinner = getattr(host, '_quick_spinner', None)
        if not on or not text:
            if spinner is not None:
                try:
                    spinner.timer.stop()
                    spinner.deleteLater()
                except RuntimeError:
                    pass
                host._quick_spinner = None
            host.busy_status('')
            return None
        pill = host.busy_status(text, 'compass')
        if spinner is None or spinner.parentWidget() is not pill:
            spinner = host._quick_spinner = Spinner(pill)
        spinner.move(14, (pill.height() - spinner.height()) // 2)
        spinner.show()
        spinner.raise_()
        return pill
    notice = getattr(host, 'notice', None)
    if notice is None:
        return None
    spinner = getattr(notice, '_busy_spinner', None)
    if not on:
        if spinner is not None:
            spinner.timer.stop()
            spinner.hide()
            spinner.deleteLater()
            notice._busy_spinner = None
        if notice.property('busy'):
            notice.setProperty('busy', False)
            notice.style().unpolish(notice)
            notice.style().polish(notice)
        return None
    host.notify(text, 3_600_000)
    if spinner is None:
        spinner = notice._busy_spinner = Spinner(notice)
        notice.setProperty('busy', True)
        notice.style().unpolish(notice)
        notice.style().polish(notice)
        if hasattr(host, 'place_notice'):
            host.place_notice()
    spinner.move(14, (notice.height() - spinner.height()) // 2)
    spinner.show()
    spinner.raise_()
    return spinner


def run_quietly(work):
    """Work(step) in a worker thread with no window (the caller shows a small spinner); the window keeps painting
    in a local event loop; returns the result or raises. step() always answers «go on»."""
    from PySide6.QtCore import QEventLoop

    state = {'result': None, 'error': None, 'finished': False}
    loop = QEventLoop()
    relay = _Relay()
    relay.answer.connect(lambda _: loop.quit())

    def body():
        try:
            state['result'] = work(lambda *args: True)
        except BaseException as exc:  # noqa: BLE001 — raised again in the window thread
            state['error'] = exc
        state['finished'] = True
        try:
            relay.answer.emit(None)
        except RuntimeError:
            pass

    threading.Thread(target=body, name='azimuth-quiet', daemon=True).start()
    if not state['finished']:
        loop.exec()
    if state['error'] is not None:
        raise state['error']
    return state['result']


def run_spinning(work, spinner=None, title=''):
    """Work(step) in a worker thread with no window — the busy cursor (the turning ring instead of the arrow) and
    the spinner next to what is being computed while it runs; returns the result or raises."""
    _refuse_second('')  # one local work at a time
    if spinner is not None:
        spinner.start()
    # the name of the work
    # itself (title), not the tooltip of its spinner («Считается…»)
    if not title:
        from azimuth.i18n import tr

        title = tr('Расчёт')
    _WORK['title'] = title
    try:
        return run_quietly(work)
    finally:
        _WORK['title'] = ''
        if spinner is not None:
            try:
                spinner.stop()
            except RuntimeError:  # the panel is gone
                pass


class _Blocker(QObject):
    """While run_waiting works — no clicks, keys, wheel or closing in the windows that were open when it began
    (nothing may change under the work, as the application-modal dialog of 0.64.5 kept it); Esc asks to stop. A window
    opened meanwhile (a message of a calculation that ended) is answered as usual. Only Esc (when no menu
    and no dialog is open — there it closes them) and the closing of the windows; the rest goes through (held())."""

    def __init__(self, cancelled, windows, title=''):
        super().__init__()
        self.cancelled, self.windows, self.title = cancelled, windows, title
        self.quit_after = None  # the main window to close when the work has stopped
        self.asking = False

    def ask_to_quit(self, top):
        """Yes — the work is stopped (as Esc) and the
        window closes when it has ended."""
        from PySide6.QtWidgets import QMessageBox

        from azimuth import quill
        from azimuth.i18n import tr

        if self.asking:
            return
        self.asking = True
        try:
            yes = QMessageBox.StandardButton.Yes
            answer = quill.question(
                top, tr('Идёт расчёт'),
                tr('Сейчас идёт расчёт «{}». Выйти из программы? Расчёт будет остановлен.').format(
                    self.title.rstrip('…')),
                yes | QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Cancel, 'nothing-found',
                {yes: tr('Остановить и выйти')})
        finally:
            self.asking = False
        if answer == yes:
            if getattr(self, 'done', False):  # the work ended while the question was open
                top.close()
                return
            self.quit_after = top
            self.cancelled.set()

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent, Qt
        from PySide6.QtWidgets import QWidget

        kind = event.type()
        # Esc is a shortcut of the model («Снять выделение») — with
        # the focus there Qt asked the shortcut first (ShortcutOverride) and the key never came as a key press
        if kind not in (QEvent.Type.KeyPress, QEvent.Type.ShortcutOverride, QEvent.Type.Close):
            return False
        widget = obj if isinstance(obj, QWidget) else None
        if widget is None:
            from PySide6.QtGui import QWindow

            if not isinstance(obj, QWindow):
                return False
            top = obj
        else:
            top = widget.window()
        if not any(top is w for w in self.windows):
            return False  # a window opened meanwhile
        if kind in (QEvent.Type.KeyPress, QEvent.Type.ShortcutOverride):
            from PySide6.QtWidgets import QApplication

            if event.key() != Qt.Key.Key_Escape or QApplication.activePopupWidget() is not None \
                    or QApplication.activeModalWidget() is not None:
                return False
            self.cancelled.set()
            event.accept()  # taken here: neither the shortcut nor the widget gets it
            return True
        if kind == QEvent.Type.Close and obj is top:
            event.ignore()
            from PySide6.QtCore import QTimer
            from PySide6.QtWidgets import QApplication, QMainWindow

            # the close comes first to the window of the system (a QWindow, its widget gets it after) — that one is
            # asked about
            main = top if isinstance(top, QMainWindow) else next(
                (w for w in QApplication.topLevelWidgets() if isinstance(w, QMainWindow) and w.windowHandle() == top),
                None)
            if main is not None and self.quit_after is None:  # the program itself: asked, not refused
                QTimer.singleShot(0, lambda: self.ask_to_quit(main))
            return True
        return False


def run_waiting(parent, title, work, total=0, alone=True):
    """work(step) in a worker thread, the window painting meanwhile (see §2); returns its result or raises.

    No progress dialog — the busy cursor (the turning ring) over the program, the title and «Esc — отменить» (with the
    share done when it is known) in the status bar of the window, the input of the windows open at the start held back
    (_Blocker) until the work ends; Esc is the former «Отмена» (InterruptedError). The line goes to notify() of the
    window (the pill over the model of Compass — its status bar is hidden) with a turning sign ◐◓◑◒ and the time spent,
    the widget under the mouse gets the busy cursor too."""
    from PySide6.QtCore import QEventLoop, QTimer
    from PySide6.QtWidgets import QApplication, QMainWindow, QWidget

    from azimuth.i18n import tr

    # one local work at a time — the window is not held back any more; alone=False — a reading or a sending
    # (a result read, a queue sent to a server) that may come while a work goes on (the end of a calculation)
    outer = _WORK['title']
    if alone:
        _refuse_second(title)
    state = {'done': 0, 'total': max(0, int(total)), 'result': None, 'error': None, 'finished': False}
    cancelled = threading.Event()

    def step(done, all_):
        state['done'], state['total'] = int(done), int(all_)
        return not cancelled.is_set()

    loop = QEventLoop()
    relay = _Relay()
    relay.answer.connect(lambda _: loop.quit())

    def body():
        try:
            state['result'] = work(step)
        except BaseException as exc:  # noqa: BLE001 — raised again in the window thread
            state['error'] = exc
        state['finished'] = True
        try:
            relay.answer.emit(None)
        except RuntimeError:
            pass

    app = QApplication.instance()
    windows = list(app.topLevelWidgets()) + list(app.topLevelWindows()) if app is not None else []
    blocker = _Blocker(cancelled, windows, outer or title)
    # where the line goes — the window with notify() (the pill over the model of Compass: its status bar is
    # hidden there, 0.99.0 wrote into it and nothing was seen), else the status bar of the main window
    host, bar = None, None
    widget = parent if isinstance(parent, QWidget) else None
    # up to the window itself — a
    # panel deep in the tabs of Spectrum (the cards of «Делокализация») was more than 6 parents from it: no window
    # with notify() was found, the line and the ring went to the hidden status bar
    for _ in range(40):
        if widget is None:
            break
        if hasattr(widget, 'notify') and callable(widget.notify) and isinstance(widget, QMainWindow):
            host = widget
            break
        if isinstance(widget, QMainWindow) and bar is None:
            bar = widget.statusBar()
        owner = getattr(widget, 'owner', None)
        widget = owner if isinstance(owner, QWidget) else widget.parentWidget()
    hint = tr('Esc — отменить')
    started = time.monotonic()
    shown = {'text': '', 'tick': 0}
    # a turning ring in the style of the program (azimuth.ui.Spinner) instead of the glyphs ◐◓◑◒ —
    # at the left of the pill of Compass (its padding grows, property busy), or at the right of the status bar
    from azimuth.ui import Spinner

    notice = getattr(host, 'notice', None) if host is not None else None
    spinner = None
    # the section the work began in; in another one the work is the sign of its section in the left panel
    stack = getattr(host, 'stack', None) if host is not None else None
    page = stack.currentIndex() if stack is not None else None
    section = SECTIONS.get(page, '')
    if section == 'compass' and getattr(host, 'compass_mode', 'molecule') == 'crystal':
        section = 'crystal'
    # only when the last one ended away from its section (the user had left it): a work begun right after one that ended
    # in its own section, in another section now, is a new action of that section (the tests of the signs of sections)
    if not outer and _LAST['away'] and _LAST['page'] is not None and time.monotonic() - _LAST['ended'] < CHAIN_S:
        page, section = _LAST['page'], _LAST['section']  # the next step of the same action
    board = getattr(host, 'activities', None) if host is not None else None

    def away(*_):
        if board is not None and not outer and board.get(WAITING) is not None:
            board.park(WAITING, stack is not None and stack.currentIndex() != page)

    def update():
        elapsed = int(time.monotonic() - started)
        share = f' · {100 * state["done"] // state["total"]} %' if state['total'] else ''
        shown['tick'] += 1
        text = f'{title}{share} · {elapsed // 60}:{elapsed % 60:02d} · {hint}'
        shown['text'] = text
        try:
            if board is not None and not outer and board.get(WAITING) is not None:
                board.progress(WAITING, state['done'] if state['total'] else None, state['total'] or None)
            if stack is not None and stack.currentIndex() != page:
                return  # in another section: the sign in the left panel tells it (away)
            if host is not None and hasattr(host, 'busy_status'):
                # a calculation gets a pill of its own, apart from other messages
                place_spinner(host.busy_status(text))
            elif host is not None:
                host.notify(text, 3_600_000)
                place_spinner()
            elif bar is not None:
                bar.showMessage(text)
                place_spinner()
        except RuntimeError:
            pass

    def page_toast():
        toast = getattr(host, '_page_toast', None) if host is not None else None
        return toast if toast is not None and not toast.isHidden() and toast.text() == shown['text'] else None

    def place_spinner(pill=None):
        nonlocal spinner
        if pill is not None:  # the pill of the work itself
            if spinner is not None and spinner.parentWidget() is not pill:
                try:
                    spinner.timer.stop()
                    spinner.deleteLater()
                except RuntimeError:
                    pass
                spinner = None
            if spinner is None:
                index = host.stack.currentIndex() if hasattr(host, 'stack') else 0
                spinner = Spinner(pill, kind={1: 'sextant', 2: 'spectrum'}.get(index, 'compass'))
            spinner.move(14, (pill.height() - spinner.height()) // 2)
            spinner.show()
            spinner.raise_()
            return
        if notice is not None and notice.isVisible():
            if spinner is not None and spinner.parentWidget() is not notice:
                return  # it went to the status bar first (another page of the window): it stays there
            if spinner is None:
                spinner = Spinner(notice)
                notice.setProperty('busy', True)
                notice.style().unpolish(notice)
                notice.style().polish(notice)
                if hasattr(host, 'place_notice'):
                    host.place_notice()
            spinner.move(14, (notice.height() - spinner.height()) // 2)
            spinner.show()
            spinner.raise_()
        elif page_toast() is not None:  # the pill of Sextant or Spectrum, the sign of its section
            toast = page_toast()
            if spinner is None:
                index = host.stack.currentIndex() if hasattr(host, 'stack') else 0
                kind = {1: 'sextant', 2: 'spectrum'}.get(index, 'compass')
                spinner = Spinner(toast, kind=kind)
                toast.setProperty('busy', 'wide' if kind == 'spectrum' else True)
                toast.style().unpolish(toast)
                toast.style().polish(toast)
                host.notify(shown['text'], 3_600_000)  # laid out again with the wider padding
            if spinner.parentWidget() is toast:
                spinner.move(14, (toast.height() - spinner.height()) // 2)
                spinner.show()
                spinner.raise_()
        elif spinner is None:
            target = bar if bar is not None else (host.statusBar() if host is not None else None)
            if target is not None:
                spinner = Spinner(target)
                target.insertPermanentWidget(0, spinner)
                spinner.show()

    timer = QTimer()
    timer.setInterval(250)
    timer.timeout.connect(update)
    if app is not None:
        app.installEventFilter(blocker)
    _WORK['title'] = outer or title
    if board is not None and not outer:
        board.start(WAITING, title, None, parked=stack is not None and stack.currentIndex() != page)
        item = board.get(WAITING)
        if item is not None:
            item.section = section
    if stack is not None:
        stack.currentChanged.connect(away)
    try:
        threading.Thread(target=body, name='azimuth-field', daemon=True).start()
        update()
        timer.start()
        if not state['finished']:
            loop.exec()
    finally:
        timer.stop()
        if app is not None:
            app.removeEventFilter(blocker)
        blocker.done = True
        if blocker.quit_after is not None:  # «Остановить и выйти» — the window closes after the work
            from PySide6.QtCore import QTimer

            closing = blocker.quit_after
            QTimer.singleShot(0, lambda: closing.close())
        _WORK['title'] = outer
        if not outer:
            _LAST.update(page=page, section=section, ended=time.monotonic(),
                         away=stack is not None and stack.currentIndex() != page)
        try:
            if stack is not None:
                stack.currentChanged.disconnect(away)
            if board is not None and not outer and board.get(WAITING) is not None:
                # ended in another section — the sign stays with its end (the gold ring and the tick when it is done)
                # until it is opened; ended in its own — it goes, the end is seen there
                error = state['error']
                end = 'done' if error is None else ('stopped' if isinstance(error, InterruptedError) else 'failed')
                if stack is not None and stack.currentIndex() != page:
                    board.park(WAITING, True)
                    board.finish(WAITING, end)
                else:
                    board.remove(WAITING)
        except (RuntimeError, TypeError):
            pass
        try:
            if spinner is not None:
                spinner.timer.stop()
                spinner.hide()
                parent_bar = spinner.parentWidget()
                if hasattr(parent_bar, 'removeWidget'):
                    parent_bar.removeWidget(spinner)
                spinner.deleteLater()
            for pill in (notice, getattr(host, '_page_toast', None) if host is not None else None):
                if pill is not None and pill.property('busy'):
                    pill.setProperty('busy', False)
                    pill.style().unpolish(pill)
                    pill.style().polish(pill)
            if host is not None and hasattr(host, 'busy_status'):
                host.busy_status('')
            page_toast = getattr(host, '_page_toast', None) if host is not None else None
            if notice is not None and notice.text() == shown['text'] and hasattr(host, 'hide_notice'):
                host.hide_notice()
            elif page_toast is not None and page_toast.text() == shown['text']:  # the pill of a page
                page_toast.clear()
                page_toast.hide()
            elif host is not None and host.statusBar().currentMessage() == shown['text']:
                host.statusBar().clearMessage()
            elif bar is not None and bar.currentMessage() == shown['text']:
                bar.clearMessage()
        except RuntimeError:
            pass
    if state['error'] is not None:
        raise state['error']
    return state['result']
