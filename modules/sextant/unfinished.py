"""Sextant at the start: a queue of calculations and a calculation on a server left unfinished when the program was
closed are offered again.

HEADER
    A calculation on a server goes on after Azimuth is closed; its watching could be taken up from «Расчёт → История
    расчётов…», and a queue from the button «Продолжить очередь», but only by one who remembered them.
    At the start Sextant asks: a queue not finished (the preference batch_actions.OPEN_KEY) — «Открыть очередь?», which
    takes it up and shows its whole progress in the window of the calculation as when it ran (a job of it that was on
    the server is watched again, not sent again: batch_actions._resume_batch_item); else the newest calculation sent
    to a server whose end was not seen (history.state_of == 'server') — «Проверить?», which takes up its watching
    (workspace.resume_history). «Нет» is remembered for that folder (DISMISSED_KEY): it is not asked again, it stays in
    the history and under «Продолжить очередь». A single calculation is not asked about — its project,
    when opened, takes up its watching by itself (azimuth/project_actions.watch_server_attempts_later). Wilkinson
    convention, sections 1-8.

§2 ALGORITHM pending(settings): {'batch': (folder, Batch) | None, 'jobs': [history records]} — the queue of OPEN_KEY
    when it can be read and is not done and not dismissed; the records of the history in state 'server', newest first,
    not dismissed and not of the queue (their folders are inside it). UnfinishedCheck(window): a single-shot timer at
    the start (after the question of the recovery copies), check() asks one question — the queue first, else the newest
    job — and on «Да» goes to Sextant (shown('sextant') for the hub) and takes it up.

§4 SPECIFICATION
    DISMISSED_KEY, LIMIT; dismissed(settings) -> [str]; dismiss(settings, folder); pending(settings) -> dict;
    UnfinishedCheck(window, start=True): .check() -> 'batch' | None; signal shown(str).

§7 TEST CASES tests/sextant/test_unfinished.py (pending and dismiss without a window; the queue resumed by the check).
"""

from __future__ import annotations

import json
from pathlib import Path

from azimuth.i18n import tr

DISMISSED_KEY = 'unfinished_dismissed'
LIMIT = 40


def dismissed(settings):
    try:
        value = json.loads(settings.value(DISMISSED_KEY, '') or '[]')
    except (TypeError, ValueError):
        return []
    return [str(v) for v in value if isinstance(v, str)] if isinstance(value, list) else []


def dismiss(settings, folder):
    kept = [f for f in dismissed(settings) if f != str(folder)]
    settings.setValue(DISMISSED_KEY, json.dumps(([str(folder)] + kept)[:LIMIT], ensure_ascii=False))


def _inside(path, folder):
    try:
        Path(path).resolve().relative_to(Path(folder).resolve())
        return True
    except (ValueError, OSError):
        return False


def pending(settings):
    from modules.sextant import batch as batches, history
    from modules.sextant.batch import OPEN_KEY

    skip = set(dismissed(settings))
    found = {'batch': None, 'jobs': []}
    folder = settings.value(OPEN_KEY, '') or ''
    if folder and folder not in skip:
        try:
            queue = batches.Batch.load(folder)
            if not queue.done():
                found['batch'] = (folder, queue)
        except (OSError, ValueError, KeyError, TypeError):
            pass
    for rec in history.load(settings):
        if rec.get('folder') in skip or (folder and _inside(rec.get('folder', ''), folder)):
            continue
        if history.state_of(rec) == 'server':
            found['jobs'].append(rec)
    return found


try:
    from PySide6.QtCore import QObject, QTimer, Signal
except ImportError:  # the pure part above runs without Qt (the stubs of the tests)
    QObject = object


if QObject is not object:
    class UnfinishedCheck(QObject):
        shown = Signal(str)

        def __init__(self, window, start=True):
            super().__init__(window)
            self.window = window
            self.timer = QTimer(self)
            self.timer.setSingleShot(True)
            self.timer.timeout.connect(self.check)
            if start:
                self.timer.start(0)

        def _ask(self, title, text):
            from PySide6.QtWidgets import QMessageBox

            from azimuth import quill

            return quill.question(self.window, title, text, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                  QMessageBox.StandardButton.Yes, 'calc-stopped') == QMessageBox.StandardButton.Yes

        def check(self):
            window = self.window
            settings = getattr(window, 'preferences', None)
            if settings is None or getattr(window, 'batch', None) is not None:
                return None
            found = pending(settings)
            if found['batch'] is not None:
                folder, queue = found['batch']
                counts = queue.counts()
                where = tr(' на сервере') if queue.place == 'server' else ''
                text = tr(f'Очередь расчётов «{queue.source or Path(folder).name}»{where} не закончена: готово '
                          f'{counts["done"]} из {len(queue.items)}. Открыть её и следить за ней дальше?')
                if queue.place == 'server' and counts.get('sent'):  # sent before the exit, running there
                    text += ' ' + tr(f'Ещё {counts["sent"]} отправлены перед выходом и идут на сервере — Секстант '
                                     'проверит их по одному, заново ничего не отправится.')
                elif queue.place == 'server' and queue.current() is not None:
                    text += ' ' + tr('Расчёт, что шёл на сервере, не отправится заново — Секстант продолжит следить за ним.')
                if not self._ask(tr('Незаконченная очередь'), text):
                    dismiss(settings, folder)
                    return None
                self._go()
                window.batch_tool.resume_batch(folder)
                return 'batch'
            # a single calculation left on a server is not asked about at the start — the
            # project opened takes it up by itself (ProjectActions.watch_server_attempts_later); one of no project
            # stays in «История расчётов» («Проверить на сервере»)
            return None

        def _go(self):
            if hasattr(self.window, 'navigate'):
                self.window.navigate(1)
            self.shown.emit('sextant')
