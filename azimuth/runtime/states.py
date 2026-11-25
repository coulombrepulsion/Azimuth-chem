"""The states of an attempt in six dimensions and their transitions (PROJECT_RUNTIME_GUIDE.md §6).

§1 PURPOSE
    One field «status» mixed things that are not the same: no network is not a failed calculation, a process that ended
    well is not a wave function on this computer. An attempt is described by six independent dimensions; the interface
    builds a short caption from them («Выполнялся; связь потеряна»).
§2 RULES TRANSITIONS[dimension][state] — the states it may go to; transition(dimension, old, new) -> new or
    TransitionError. A terminal state of execution (succeeded, failed, cancelled) is changed only by reconcile() with a
    reason written in the result — never by a late observation. Submission 'uncertain' (the answer of the server was
    lost) goes to 'accepted' or 'rejected' only by reconcile(): it never allows to send again by itself (§7 of the
    guide). Observations of a watcher (Observation) carry its generation and a sequence: accept(watch, observation)
    drops one of an older generation (a watcher replaced after reconnecting), one not newer than the last of its
    generation (delivered twice), and a non-terminal one after a terminal state (a late «running»); a different terminal
    state after a terminal one is a conflict — dropped and told, to be reconciled.
§3 INTERFACE DIMENSIONS, TRANSITIONS, TERMINAL_EXECUTION; TransitionError; transition(dimension, old, new); AttemptState
    (frozen: submission, execution, connectivity, artifacts, outcome, cancellation, seen — the time of the last
    confirmed observation, UTC ISO or ''); Observation(attempt_id, group_id, source, generation, sequence, execution);
    Watch(generation=0, sequence=-1, state=AttemptState()); accept(watch, observation) -> (Watch, verdict) with verdict
    'applied' | 'stale' | 'duplicate' | 'late' | 'conflict'; reconcile(state, execution, reason) -> (AttemptState,
    note); caption(state) -> str (translated pieces joined by «; »).
§4 TESTS
    tests/runtime/test_runtime_states.py.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from azimuth.i18n import tr

DIMENSIONS = ('submission', 'execution', 'connectivity', 'artifacts', 'outcome', 'cancellation')

TRANSITIONS = {
    'submission': {
        'prepared': {'submitting'},
        'submitting': {'accepted', 'rejected', 'uncertain'},
        'uncertain': set(),  # only reconcile(): never a new sending by itself
        'accepted': set(),
        'rejected': set(),
    },
    'execution': {
        'not_started': {'queued', 'running', 'succeeded', 'failed', 'cancelled', 'unknown'},
        'queued': {'running', 'succeeded', 'failed', 'cancelled', 'unknown'},
        'running': {'queued', 'succeeded', 'failed', 'cancelled', 'unknown'},  # queued again: a requeue of SLURM
        'unknown': {'queued', 'running', 'succeeded', 'failed', 'cancelled'},
        'succeeded': set(),
        'failed': set(),
        'cancelled': set(),
    },
    'connectivity': {
        'online': {'offline', 'auth_required'},
        'offline': {'online', 'auth_required'},
        'auth_required': {'online', 'offline'},
    },
    'artifacts': {
        'not_requested': {'transferring'},
        'transferring': {'partial', 'ready', 'transfer_error'},
        'partial': {'transferring', 'ready', 'transfer_error'},
        'transfer_error': {'transferring'},
        'ready': {'transferring'},  # another set of files asked for (the orbitals after the energy)
    },
    'outcome': {
        'unparsed': {'valid', 'unconverged', 'invalid', 'parse_error'},
        'parse_error': {'unparsed'},  # read again by a newer parser
        'valid': {'unparsed'},
        'unconverged': {'unparsed'},
        'invalid': {'unparsed'},
    },
    'cancellation': {
        'none': {'requested'},
        'requested': {'confirmed', 'failed'},
        'failed': {'requested'},
        'confirmed': set(),
    },
}
TERMINAL_EXECUTION = frozenset({'succeeded', 'failed', 'cancelled'})


class TransitionError(ValueError):
    pass


def transition(dimension, old, new):
    table = TRANSITIONS[dimension]
    if old not in table or new not in table:
        raise TransitionError(f'{dimension}: unknown state {old!r} → {new!r}')
    if new != old and new not in table[old]:
        raise TransitionError(f'{dimension}: {old} → {new} is not allowed')
    return new


@dataclass(frozen=True)
class AttemptState:
    submission: str = 'prepared'
    execution: str = 'not_started'
    connectivity: str = 'online'
    artifacts: str = 'not_requested'
    outcome: str = 'unparsed'
    cancellation: str = 'none'
    seen: str = ''  # UTC ISO of the last confirmed observation; '' — never observed

    def moved(self, **changes):
        """A new state with the given dimensions changed through transition() (TransitionError when not allowed)."""
        values = {k: transition(k, getattr(self, k), v) for k, v in changes.items() if k in DIMENSIONS}
        extra = {k: v for k, v in changes.items() if k not in DIMENSIONS}
        return replace(self, **values, **extra)


@dataclass(frozen=True)
class Observation:
    attempt_id: str
    group_id: str
    source: str  # 'squeue', 'sacct', 'marker', 'process', …
    generation: int
    sequence: int
    execution: str
    when: str = ''


@dataclass(frozen=True)
class Watch:
    generation: int = 0
    sequence: int = -1
    state: AttemptState = AttemptState()


def accept(watch, observation):
    """(Watch, verdict) — see §2."""
    if observation.generation < watch.generation:
        return watch, 'stale'
    if observation.generation == watch.generation and observation.sequence <= watch.sequence:
        return watch, 'duplicate'
    current = watch.state.execution
    position = Watch(observation.generation, observation.sequence, watch.state)
    if current in TERMINAL_EXECUTION:
        if observation.execution == current:
            return position, 'duplicate'
        verdict = 'conflict' if observation.execution in TERMINAL_EXECUTION else 'late'
        return position, verdict
    state = watch.state
    if observation.execution != current:
        state = state.moved(execution=observation.execution)
    if observation.when:
        state = replace(state, seen=observation.when)
    return Watch(observation.generation, observation.sequence, state), 'applied'


def reconcile(state, execution, reason):
    """An explicit correction of a contradiction (a terminal state replaced, an uncertain submission settled): the new
    state and the note to keep in the journal of the attempt. reason is required."""
    if not reason or not str(reason).strip():
        raise TransitionError('reconcile: the reason is required')
    if execution not in TRANSITIONS['execution']:
        raise TransitionError(f'execution: unknown state {execution!r}')
    submission = state.submission
    if submission == 'uncertain':
        submission = 'accepted' if execution != 'not_started' else 'rejected'
    note = f'{state.submission}/{state.execution} → {submission}/{execution}: {reason}'
    return replace(state, submission=submission, execution=execution), note


def caption(state):
    """The short caption of the interface (the guide, §6): what is known of the run, then of the link, of the files and
    of the result — only what is not the ordinary course."""
    parts = []
    run = {
        'prepared': tr('Подготовлен'), 'submitting': tr('Отправляется'), 'rejected': tr('Сервер не принял'),
        'uncertain': tr('Неизвестно, принят ли сервером'),
    }
    if state.submission in run:
        parts.append(run[state.submission])
    elif state.cancellation == 'requested':
        parts.append(tr('Остановка запрошена'))
    else:
        parts.append({
            'not_started': tr('Ждёт начала'), 'queued': tr('В очереди'), 'running': tr('Выполняется'),
            'succeeded': tr('Расчёт завершён'), 'failed': tr('Расчёт завершился с ошибкой'),
            'cancelled': tr('Остановлен'), 'unknown': tr('Состояние неизвестно'),
        }[state.execution])
    if state.execution in ('queued', 'running', 'unknown') and state.connectivity != 'online':
        if parts[-1] == tr('Выполняется'):
            parts[-1] = tr('Выполнялся')
        parts.append(tr('связь потеряна') if state.connectivity == 'offline' else tr('нужен вход на сервер'))
    if state.execution == 'succeeded':
        files = {'transferring': tr('загружаются файлы'), 'partial': tr('загружена часть файлов'),
                 'transfer_error': tr('файлы не загрузились')}.get(state.artifacts)
        if files:
            parts.append(files)
    result = {'unconverged': tr('без сходимости; последняя геометрия доступна'), 'invalid': tr('результат непригоден'),
              'parse_error': tr('вывод не прочитан')}.get(state.outcome)
    if result:
        parts.append(result)
    return '; '.join(parts)
