"""Sextant: the history of calculations — the calculation is not lost when the program is closed.

§1 PURPOSE
    A calculation on a server goes on when Azimuth is closed, and the result of a finished one stays in its folder; but
    the window of the calculation was gone with the program, and the way back was the folder in Finder. The history
    keeps every calculation started from Sextant (the last LIMIT): when, where, what, its folder and output; after a
    restart «Расчёт → История расчётов…» shows its state and opens the result, the folder, or — on a server — takes the
    watching up again (remote_job.RemoteJob.resume: no new sending, the same queue number from job.json).
§2 ALGORITHM
    record(spec, kind, calculation, title, place, now) → a dict of strings and numbers (JSON in the settings, KEY);
    add(items, rec) puts it first (one entry per folder) and keeps LIMIT; finish(items, folder, state) writes the end
    ('finished' | 'failed' | 'stopped'); state_of(rec) — the stored end, else read from the files now: the folder gone →
    'missing'; the output with the normal end of its program → 'finished'; on a server with job.json and no end →
    'server' (may still run there or be done: «Проверить» takes it up); otherwise 'unknown' (closed while running).
    Submission.json 'submitting'/'uncertain' without job.json → 'uncertain' (the answer of the server lost;
    «Проверить» asks the server, never sends again); 'prepared' → 'prepared' (closed before the sending: nothing on
    the server, a new calculation is needed).
§4 SPECIFICATION
    KEY, LIMIT; load(settings) -> [dict]; save(settings, items); record(...); add(items, rec) -> list;
    finish(items, folder, state) -> list; state_of(rec) -> str; describe(state) -> str (for the table);
    remote_info(rec) -> dict of job.json (or of an uncertain submission) or None; RESUMABLE; calculation_of(rec) ->
    azimuth.core.Calculation.
§7 TESTS tests/sextant/test_history.py (no window).
"""

import json
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from azimuth.i18n import tr

KEY = 'jobs_history'
LIMIT = 60
ENDED = ('finished', 'failed', 'stopped')
STATES = {
    'running': 'идёт',
    'finished': 'закончен',
    'failed': 'с ошибкой',
    'stopped': 'остановлен',
    'server': 'на сервере — проверить',
    'missing': 'папки нет',
    'unknown': 'не закончен (программа была закрыта)',
    'uncertain': 'неизвестно, принят ли сервером — проверить',
    'prepared': 'подготовлен, не отправлен',  # the program closed before the sending
    'unreadable': 'база проекта не читается',  # its records cannot be read now — nothing guessed
}
RESUMABLE = ('server', 'uncertain')


def load(settings):
    try:
        text = settings.value(KEY, '') or ''
        items = json.loads(text) if text else []
    except (TypeError, ValueError):
        return []
    return [d for d in items if isinstance(d, dict) and d.get('folder')]


def save(settings, items):
    settings.setValue(KEY, json.dumps(items[:LIMIT], ensure_ascii=False))


def record(spec, kind, calculation, title, place=None, now=None):
    return {
        'when': (now or datetime.now()).isoformat(timespec='seconds'),
        'place': place or '',
        'kind': kind,
        'title': title,
        'task': calculation.task,
        'method': calculation.method,
        'basis': calculation.basis,
        'cores': int(calculation.cores),
        'memory_mb': int(calculation.memory_mb),
        'folder': str(spec.folder),
        'output': str(spec.output),
        'state': 'running',
    }


def add(items, rec):
    return ([rec] + [d for d in items if d.get('folder') != rec['folder']])[:LIMIT]


def finish(items, folder, state):
    folder = str(folder)
    return [dict(d, state=state) if d.get('folder') == folder else d for d in items]


def remote_info(rec):
    """job.json of the folder; without it, a sending whose answer was lost (submission.json 'submitting' or
    'uncertain') — the server and folder, no number (RemoteJob.resume asks the server first)."""
    from modules.sextant.remote_job import JOB_JSON
    from azimuth.runtime import runs

    from azimuth.runtime import records

    info = records.read(rec['folder'], JOB_JSON)  # the database of the project, else the file
    if isinstance(info, dict):
        return info
    sub = runs.read(rec['folder'])
    if sub is not None and sub.state in ('submitting', 'uncertain') and sub.folder:
        return {'server': sub.server, 'folder': sub.folder, 'job': None, 'program': rec.get('kind', 'orca'),
                'submission': sub.state}
    return None


def submission_state(rec):
    from azimuth.runtime import runs

    sub = runs.read(rec.get('folder', '')) if rec.get('place') else None
    return sub.state if sub is not None else ''


def state_of(rec):
    """'unreadable' when the database of its project cannot be read (never a state guessed from a file)."""
    from azimuth.project_store import ProjectDatabaseError

    try:
        return _state_of(rec)
    except ProjectDatabaseError:
        return 'unreadable'


def _state_of(rec):
    from modules.sextant import runner

    folder = Path(rec.get('folder', ''))
    if not folder.is_dir():
        return 'missing'
    sent = submission_state(rec)  # before the stored end — «failed» was the old word for a lost answer
    from azimuth.runtime import records

    if sent in ('submitting', 'uncertain') and not records.exists(folder, 'job.json'):
        return 'uncertain'
    if rec.get('state') in ENDED:
        return rec['state']
    if sent == 'prepared':
        return 'prepared'
    output = Path(rec.get('output', ''))
    try:
        text = output.read_text(encoding='utf-8', errors='replace') if output.is_file() else ''
    except OSError:
        text = ''
    if text and runner.finished_normally(rec.get('kind', 'orca'), text, 0):
        return 'finished'
    if rec.get('place') and remote_info(rec) is not None:
        return 'server'
    return 'unknown'


def describe(state):
    return tr(STATES.get(state, state))


def calculation_of(rec):
    from azimuth.core import Calculation

    base = Calculation()
    try:
        return replace(base, task=rec.get('task', base.task), method=rec.get('method', base.method),
                       basis=rec.get('basis', base.basis), cores=int(rec.get('cores', base.cores)),
                       memory_mb=int(rec.get('memory_mb', base.memory_mb)))
    except (TypeError, ValueError):
        return base
