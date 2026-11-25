"""Errors of the program written down and handed to the author.

§1 PURPOSE
    When something breaks on another computer, it must not vanish. Azimuth.app has no terminal, and startup.log
    (gui_launcher.py) is overwritten at the next start. So
      — every exception not caught (the main thread, other threads, the slots of Qt) is appended to errors.log with the
        time and the version, and the window says so once (Quill, «Что-то пошло не так»: the program goes on);
      — a crash of Qt itself (a segmentation fault) leaves its stack in crash.log (faulthandler); at the next start
        the program asks to save a report;
      — the warnings of Qt go to errors.log too;
      — «Файл → Отчёт об ошибке…» and «Настройки → Ошибки» put errors.log, crash.log, startup.log, the versions of
        the program, Python, Qt, NumPy and VTK, the system and the settings (without passwords) into one .zip for
        the author;
      — «Отправить автору…» in the window about an error, in the question after a crash and in «Настройки → Ошибки»
        makes the .zip on the Desktop without asking, opens a letter to AUTHOR in the mail program of the system
        (mailto: the subject with the version, the body with the system, the last error and where the .zip is — a link
        mailto cannot attach a file) and shows the .zip in its folder, to be dragged into the letter. No mail program —
        a window with the address (copied) and the path.
§2 ALGORITHM
    The folder: AZIMUTH_LOG_DIR (or QUAIL_LOG_DIR of gui_launcher), else ~/Library/Logs/Azimuth (macOS),
    %LOCALAPPDATA%\\Azimuth\\Logs (Windows), ~/.local/state/Azimuth. errors.log is cut to its last LOG_LIMIT bytes when
    it grows past twice that. The settings in the report: every key whose name has «pass», «secret», «token» or
    «private» is left out (the server profiles keep their address and login, which tell where it failed);
    only the program's own keys (not those of macOS's global domain), the home folder written «~».
§4 SPECIFICATION
    log_dir() -> Path; ERRORS, CRASH, STARTUP; record(kind, text) -> Path (append, with the time and the version);
    format_exception(exc_type, value, tb) -> str; system_text() -> str; safe_settings(settings) -> [(key, value)];
    make_report(target (Path of the .zip), settings=None) -> Path; crashed_before(settings) -> bool;
    AUTHOR; last_error(limit=MAIL_ERROR) -> str (the end of the last entry of errors.log or of crash.log, '' none);
    mail_url(report, error='') -> str (mailto:AUTHOR?subject=…&body=…, at most MAIL_LIMIT characters);
    send_report(parent=None, settings=None) -> Path | None;
    install(app, parent=None) — the hooks (sys.excepthook, threading.excepthook, qInstallMessageHandler,
    faulthandler); Reporter.notify(text) — the window, at most once per QUIET seconds.
§7 TESTS tests/core/test_crash_report.py (no Qt), tests/test_gui.py::test_error_report_window.
"""

import datetime
import faulthandler
import os
import platform
import re
import sys
import threading
import traceback
import zipfile
from pathlib import Path

ERRORS, CRASH, STARTUP = 'errors.log', 'crash.log', 'startup.log'
LOG_LIMIT = 1_000_000  # bytes of errors.log kept
QUIET = 20.0  # s: at most one window about errors in this time
SECRET = re.compile(r'pass|secret|token|private', re.I)
SEEN_KEY = 'crash_log_seen'  # the size of crash.log the user was told about
AUTHOR = 'contact@azimuth-chem.com'  # where the reports go (hub/about.py EMAIL — the same address)
MAIL_ERROR = 900  # characters of the last error in the letter
MAIL_LIMIT = 1900  # characters of the whole mailto link (the mail programs of Windows cut longer ones)


def log_dir():
    given = os.environ.get('AZIMUTH_LOG_DIR') or os.environ.get('QUAIL_LOG_DIR')
    if given:
        base = Path(given)
    elif sys.platform == 'darwin':
        base = Path.home() / 'Library' / 'Logs' / 'Azimuth'
    elif sys.platform == 'win32':
        base = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'Azimuth' / 'Logs'
    else:
        base = Path.home() / '.local' / 'state' / 'Azimuth'
    base.mkdir(parents=True, exist_ok=True)
    return base


def _version():
    try:
        from azimuth import __version__

        return __version__
    except Exception:  # noqa: BLE001 — a report never fails for this
        return '?'


def record(kind, text):
    """Append an entry to errors.log: «=== 2026-11-03 12:00:01 · 0.91.44 · <kind>» and the text; → the path."""
    path = log_dir() / ERRORS
    stamp = datetime.datetime.now().isoformat(sep=' ', timespec='seconds')
    with open(path, 'a', encoding='utf-8') as out:
        out.write(f'=== {stamp} · {_version()} · {kind}\n{text.rstrip()}\n\n')
    try:
        if path.stat().st_size > 2 * LOG_LIMIT:
            data = path.read_bytes()[-LOG_LIMIT:]
            cut = data.find(b'\n=== ')
            path.write_bytes(b'[... earlier entries cut ...]\n' + (data[cut + 1:] if cut >= 0 else data))
    except OSError:
        pass
    return path


def format_exception(exc_type, value, tb):
    return ''.join(traceback.format_exception(exc_type, value, tb))


def _module_version(name):
    try:
        module = __import__(name)
        return getattr(module, '__version__', None) or getattr(module, 'VTK_VERSION', None) or '?'
    except Exception:  # noqa: BLE001
        return 'нет'


def system_text():
    lines = [f'Azimuth {_version()}', f'Python {sys.version.split()[0]} ({sys.executable})',
             f'System {platform.platform()} · {platform.machine()}']
    for name in ('PySide6', 'numpy', 'vtkmodules', 'scipy'):
        lines.append(f'{name} {_module_version(name)}')
    try:
        from PySide6.QtCore import qVersion

        lines.append(f'Qt {qVersion()}')
    except Exception:  # noqa: BLE001
        pass
    return '\n'.join(lines) + '\n'


SYSTEM_KEY = re.compile(r'^(com/apple/|NS|Apple|AK|PK|WebKit|KB_|csTime$|shouldShow)')


def safe_settings(settings):
    """(key, value) of the settings without the secret ones; values as text, long ones shortened. Only the program's own
    keys — on macOS QSettings also reads the system's global domain
    (text replacements, the city of the time zone, the gestures of the trackpad), so its fallbacks are turned off
    while listing and the keys of the system (SYSTEM_KEY) left out; the home folder in a value is written «~»."""
    from pathlib import Path

    rows = []
    if settings is None:
        return rows
    fallbacks = getattr(settings, 'fallbacksEnabled', None)
    before = fallbacks() if callable(fallbacks) else None
    if before:
        settings.setFallbacksEnabled(False)
    try:
        keys = sorted(settings.allKeys())
    finally:
        if before:
            settings.setFallbacksEnabled(True)
    home = str(Path.home())
    for key in keys:
        if SECRET.search(key) or SYSTEM_KEY.search(key):
            continue
        value = str(settings.value(key))
        if home and len(home) > 1:
            value = value.replace(home, '~')
        rows.append((key, value if len(value) <= 300 else value[:300] + '…'))
    return rows


def make_report(target, settings=None):
    """One .zip for the author: the three logs (those there are), system.txt and settings.txt."""
    target = Path(target)
    folder = log_dir()
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as box:
        for name in (ERRORS, CRASH, STARTUP, 'startup.previous.log'):
            if (folder / name).is_file():
                box.write(folder / name, name)
        box.writestr('system.txt', system_text())
        box.writestr('settings.txt', ''.join(f'{k} = {v}\n' for k, v in safe_settings(settings)))
    return target


def crashed_before(settings):
    """crash.log grew since the user was last told (a fatal error of Qt or of Python at an earlier run)."""
    path = log_dir() / CRASH
    size = path.stat().st_size if path.is_file() else 0
    seen = int(settings.value(SEEN_KEY, 0) or 0) if settings is not None else 0
    return size > seen


def mark_crash_seen(settings):
    path = log_dir() / CRASH
    if settings is not None:
        settings.setValue(SEEN_KEY, path.stat().st_size if path.is_file() else 0)


_crash_file = None


def enable_faulthandler():
    """A crash of the process (Qt, VTK) writes the stacks of every thread to crash.log."""
    global _crash_file
    if _crash_file is None:
        try:
            # nothing is written at the start: crash.log grows only by a crash (crashed_before compares its size)
            _crash_file = open(log_dir() / CRASH, 'a', encoding='utf-8')
            faulthandler.enable(_crash_file, all_threads=True)
        except OSError:
            _crash_file = None
    return _crash_file


class Reporter:
    """The hooks and the window about errors (one per application)."""

    def __init__(self, app, parent=None):
        self.app = app
        self.parent = parent
        self.last = -1e9
        self.showing = False
        self.count = 0
        self.qt_seen = set()

    def window(self):
        if self.parent is not None:
            return self.parent() if callable(self.parent) else self.parent
        return self.app.activeWindow() if self.app is not None else None

    def excepthook(self, exc_type, value, tb):
        if issubclass(exc_type, KeyboardInterrupt):
            return sys.__excepthook__(exc_type, value, tb)
        text = format_exception(exc_type, value, tb)
        record('exception', text)
        sys.__stderr__.write(text) if sys.__stderr__ else None
        self.count += 1
        if 'paintEvent' in text:  # an error in painting is written, never answered by a window — a modal
            return                # window opened from the painting of Windows fell with an access violation
        self.notify(f'{exc_type.__name__}: {value}')

    def thread_hook(self, args):
        text = format_exception(args.exc_type, args.exc_value, args.exc_traceback)
        record(f'exception in thread {getattr(args.thread, "name", "?")}', text)

    def qt_message(self, mode, context, message):
        from PySide6.QtCore import QtMsgType

        if mode in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg, QtMsgType.QtFatalMsg):
            if message in self.qt_seen:  # a warning repeated at every frame is written once per run
                return
            self.qt_seen.add(message)
            where = f'{context.file}:{context.line}' if context is not None and context.file else ''
            record('qt ' + mode.name.replace('Qt', '').replace('Msg', '').lower(), f'{message}  {where}'.rstrip())

    def notify(self, short):
        """The window «Что-то пошло не так» — not while another is open, not more often than every QUIET s."""
        import time

        from PySide6.QtCore import QTimer

        now = time.monotonic()
        if self.showing or now - self.last < QUIET or self.app is None:
            return False
        self.last = now
        QTimer.singleShot(0, lambda: self._show(short))
        return True

    def _show(self, short):
        from PySide6.QtWidgets import QMessageBox

        from azimuth import quill
        from azimuth.i18n import tr

        self.showing = True
        try:
            box = QMessageBox(self.window())
            box.setWindowTitle(tr('Азимут: ошибка'))
            quill._fill(box, tr('Что-то пошло не так — программа продолжает работать. Подробности записаны в журнал '
                                'ошибок; чтобы автор мог разобраться, сохраните отчёт и пришлите ему.') + '\n\n' + short)
            quill.set_icon(box, 'error', QMessageBox.Icon.Warning)
            send = box.addButton(tr('Отправить автору…'), QMessageBox.ButtonRole.AcceptRole)
            save = box.addButton(tr('Сохранить отчёт…'), QMessageBox.ButtonRole.ActionRole)
            box.addButton(QMessageBox.StandardButton.Close)
            box.setDefaultButton(send)
            self.box = box
            box.exec()
            if box.clickedButton() is send:
                send_report(self.window())
            elif box.clickedButton() is save:
                save_report_dialog(self.window())
        finally:
            self.showing = False
            self.box = None


_reporter = None


def install(app, parent=None):
    """The hooks of this application (once)."""
    global _reporter
    if _reporter is not None:
        return _reporter
    enable_faulthandler()
    _reporter = Reporter(app, parent)
    sys.excepthook = _reporter.excepthook
    threading.excepthook = _reporter.thread_hook
    try:
        from PySide6.QtCore import qInstallMessageHandler

        qInstallMessageHandler(_reporter.qt_message)
    except ImportError:
        pass
    return _reporter


def ask_after_crash(parent=None, settings=None):
    """At the start: the last run ended by a crash (crash.log grew) — offer to save a report; told once."""
    from PySide6.QtWidgets import QMessageBox

    from azimuth import quill
    from azimuth.i18n import tr

    if settings is None:
        from azimuth.settings import open_settings

        settings = open_settings()
    if not crashed_before(settings):
        return False
    box = QMessageBox(parent)
    box.setWindowTitle(tr('Азимут закрылся аварийно'))
    quill._fill(box, tr('В прошлый раз программа закрылась аварийно. Отправить автору отчёт об ошибке? '
                        'В нём журналы, версии программ и настройки без паролей.'))
    quill.set_icon(box, 'error', QMessageBox.Icon.Question)
    send = box.addButton(tr('Отправить автору…'), QMessageBox.ButtonRole.AcceptRole)
    save = box.addButton(tr('Сохранить отчёт…'), QMessageBox.ButtonRole.ActionRole)
    box.addButton(tr('Не сейчас'), QMessageBox.ButtonRole.RejectRole)
    box.setDefaultButton(send)
    mark_crash_seen(settings)
    ask_after_crash.box = box
    box.exec()
    if box.clickedButton() is send:
        send_report(parent, settings)
    elif box.clickedButton() is save:
        save_report_dialog(parent, settings)
    return True


def save_report_dialog(parent=None, settings=None):
    """Ask where to save the .zip (the Desktop by default), make it and show it in its folder; → the path or None."""
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtWidgets import QFileDialog

    from azimuth.i18n import tr

    if settings is None:
        from azimuth.settings import open_settings

        settings = open_settings()
    stamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')
    start = Path.home() / 'Desktop'
    start = start if start.is_dir() else Path.home()
    path, _ = QFileDialog.getSaveFileName(parent, tr('Отчёт об ошибке'), str(start / f'azimuth-report_{stamp}.zip'),
                                          tr('Архив ZIP (*.zip)'))
    if not path:
        return None
    report = make_report(path, settings)
    mark_crash_seen(settings)
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(report.parent)))
    return report


# -- the report sent to the author -------------------------------------------------------------------------

def last_error(limit=MAIL_ERROR):
    """The last entry of errors.log (or the end of crash.log, if it is newer), its last limit characters."""
    folder = log_dir()
    found = []
    for name in (ERRORS, CRASH):
        path = folder / name
        if path.is_file():
            try:
                text = path.read_text(encoding='utf-8', errors='replace').strip()
            except OSError:
                continue
            if name == ERRORS and text.rfind('=== ') >= 0:
                text = text[text.rfind('=== '):]  # the last entry
            if text:
                found.append((path.stat().st_mtime, text))
    if not found:
        return ''
    text = max(found)[1]
    return text if len(text) <= limit else '…' + text[-limit:]


def mail_url(report, error=''):
    """mailto:AUTHOR with the subject and the body of the letter; the error shortened so that the link fits."""
    from urllib.parse import quote

    from azimuth.i18n import tr

    subject = tr('Азимут {}: отчёт об ошибке').format(_version())

    def body(err):
        parts = [tr('Что я делал, когда это случилось:'), '', '', '— — —', system_text().strip()]
        if err:
            parts += ['', tr('Последняя ошибка:'), err]
        parts += ['', tr('Отчёт (журналы и настройки без паролей) — приложите этот файл к письму:'), str(report)]
        return '\n'.join(parts)

    def link(err):
        return f'mailto:{AUTHOR}?subject={quote(subject)}&body={quote(body(err))}'

    error = error.strip()
    url = link(error)
    while len(url) > MAIL_LIMIT and error:
        error = '…' + error[max(1, len(error) // 4):]  # keep the end: the line of the exception is the last one
        url = link(error if len(error) > 1 else '')
        if len(error) <= 1:
            break
    return url


def send_report(parent=None, settings=None):
    """The .zip on the Desktop, a letter to the author in the mail program, the .zip shown in its folder; → the path
    (None — the report could not be written)."""
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QDesktopServices, QGuiApplication

    from azimuth import quill
    from azimuth.i18n import tr

    if settings is None:
        from azimuth.settings import open_settings

        settings = open_settings()
    stamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')
    folder = Path.home() / 'Desktop'
    folder = folder if folder.is_dir() else Path.home()
    try:
        report = make_report(folder / f'azimuth-report_{stamp}.zip', settings)
    except OSError as exc:
        quill.warning(parent, tr('Отчёт об ошибке'), tr('Не удалось записать отчёт: {}').format(exc))
        return None
    mark_crash_seen(settings)
    sent = QDesktopServices.openUrl(QUrl(mail_url(report, last_error())))
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(report.parent)))
    if not sent:
        clipboard = QGuiApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(AUTHOR)
        quill.warning(parent, tr('Отчёт об ошибке'),
                      tr('Почтовая программа не открылась. Напишите на {} (адрес скопирован) и приложите файл:\n{}')
                      .format(AUTHOR, report))
    return report
