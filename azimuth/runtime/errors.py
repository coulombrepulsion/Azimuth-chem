"""What kind of failure it is and what to do about it (the roadmap of 2026-11-09, «C. Общие правила ошибок»).

§1 PURPOSE
    The program has its own errors (SshError with its kinds, ProjectDatabaseError, ProjectLocked, SubmissionUncertain,
    CommandError, TransitionError) and the ones of Python (OSError, ValueError). The roadmap: tell apart missing data,
    an unsupported format, damage, an unavailable resource, a lost connection, a failed program and a failed save; for
    each say whether to try again, to recover, to ask the user or to stop; a lost connection never allows a second
    sending whose first outcome is unknown; a failed write never shows as saved.
§2 RULES — the categories (CATEGORIES) and their actions:
    missing — what is needed is not there (no file of orbitals, no energy) → ask (the user supplies it)
    unsupported — a format or a request the program does not handle → stop, say what is handled
    damaged — data unreadable (a broken database, a cut output) → recover (a backup, a new run)
    unavailable — present but not now (another window writes the project, busy) → retry later, reads only
    connection — the server out of reach → retry reads; an outside
                   action with a side effect (a sending) is not repeated — it is reconciled (azimuth/runtime/runs.py)
    uncertain — an outside action whose outcome is unknown (the answer of sbatch lost) → reconcile, never repeat
    refused — the other side said no (a login refused, a host key changed) → ask the user
    execution — a program ran and failed (ORCA ended with an error, a command failed) → stop, show its output
    storage — a write on this computer failed (a full disk) → stop: not saved, say it
    invalid — the input of the user is wrong (a value not finite, a stale revision) → ask (correct it)
    classify(exc) -> Category(name, action, repeat_outside). repeat_outside: whether an outside action with a side
    effect may be repeated after it — False for all but the categories where it provably did not happen (refused,
    invalid, missing, unsupported).
§3 INTERFACE CATEGORIES {name: (action, repeat_outside)}; Category; classify(exc) -> Category; ADVICE; advice(c).
§4 TESTS tests/runtime/test_runtime_errors.py.
"""

from __future__ import annotations

import errno
from dataclasses import dataclass

CATEGORIES = {
    'missing': ('ask', True),
    'unsupported': ('stop', True),
    'damaged': ('recover', False),
    'unavailable': ('retry', False),
    'connection': ('retry', False),
    'uncertain': ('reconcile', False),
    'refused': ('ask', True),
    'execution': ('stop', False),
    'storage': ('stop', False),
    'invalid': ('ask', True),
}


@dataclass(frozen=True)
class Category:
    name: str
    action: str
    repeat_outside: bool
    cause: str = ''


def _make(name, exc):
    action, repeat = CATEGORIES[name]
    return Category(name, action, repeat, f'{type(exc).__name__}: {exc}')


def classify(exc):
    """The category of an exception (§2); an exception the program does not know is 'execution' — stop and show it,
    never a reason to repeat an outside action."""
    from azimuth.project_store import ProjectDatabaseError
    from azimuth.projects import ProjectLocked
    from azimuth.runtime.contracts import CommandError
    from azimuth.runtime.states import TransitionError

    if isinstance(exc, ProjectLocked):
        return _make('unavailable', exc)
    if isinstance(exc, ProjectDatabaseError):
        cause = str(getattr(exc, 'cause', '')).lower()
        return _make('unavailable' if 'locked' in cause or 'busy' in cause else 'damaged', exc)
    try:
        from modules.sextant.remote_job import SubmissionUncertain
        from modules.sextant.ssh import SshError
    except ImportError:  # a part without Sextant
        SubmissionUncertain = SshError = ()
    if SubmissionUncertain and isinstance(exc, SubmissionUncertain):
        return _make('uncertain', exc)
    if SshError and isinstance(exc, SshError):
        return _make({'connection': 'connection', 'timeout': 'connection', 'auth': 'refused', 'hostkey': 'refused',
                      'missing': 'missing', 'command': 'execution'}.get(getattr(exc, 'kind', ''), 'connection'), exc)
    if isinstance(exc, CommandError):
        return _make({'stale_revision': 'invalid', 'invalid': 'invalid', 'not_found': 'missing', 'busy': 'unavailable',
                      'uncertain_submission': 'uncertain', 'backend': 'execution'}.get(exc.code, 'execution'), exc)
    if isinstance(exc, TransitionError):
        return _make('invalid', exc)
    if isinstance(exc, FileNotFoundError):
        return _make('missing', exc)
    if isinstance(exc, PermissionError):
        return _make('unavailable', exc)
    if isinstance(exc, OSError):
        if exc.errno in (errno.ENOSPC, errno.EDQUOT, errno.EROFS, errno.EIO):
            return _make('storage', exc)
        return _make('unavailable', exc)
    if isinstance(exc, (UnicodeDecodeError,)):
        return _make('damaged', exc)
    if isinstance(exc, ValueError):
        return _make('invalid', exc)
    return _make('execution', exc)


ADVICE = {  # what the user reads after the message of the failure
    'missing': 'Не хватает файла или программы — укажите их и запустите снова.',
    'unsupported': 'Такой формат или запрос программа не обрабатывает.',
    'damaged': 'Данные повреждены — восстановите их из резервной копии или запустите расчёт заново.',
    'unavailable': 'Ресурс сейчас занят или недоступен — попробуйте позже.',
    'connection': 'Связи нет — когда она вернётся, расчёт можно проверить в истории («Проверить на сервере»); '
                  'заново он сам не отправляется.',
    'uncertain': 'Неизвестно, принят ли расчёт, — проверьте его в истории («Проверить на сервере»), не запуская снова.',
    'refused': 'Сервер отказал — проверьте логин, пароль или ключ сервера.',
    'execution': '',
    'storage': 'Записать на этом компьютере не удалось — освободите место на диске; сохранённым это не считается.',
    'invalid': 'Исправьте введённые данные.',
}


def advice(category):
    """The sentence of what to do next for a Category ('' — the message of the failure says enough)."""
    from azimuth.i18n import tr

    text = ADVICE.get(getattr(category, 'name', category), '')
    return tr(text) if text else ''
