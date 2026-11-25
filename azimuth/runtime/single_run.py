"""One calculation from its start to its result, without the window.
§1 PURPOSE
    RunTool._finish_job decided everything at the end of a calculation and showed it at once: the final state, the
    orbitals made from the .gbw, the warnings, what to open, the records of the history and of the project. It could
    be checked only with the whole window, and a second end (a timer firing twice) repeated the side effects. Here the
    decisions are made apart; the window shows what conclude() returns and does what its actions allow.
§2 RULES
    1. The input of an attempt is its snapshot (lifecycle.Attempt makes a deep copy of input and extra): a molecule
       edited after the start never changes it.
    2. observe(job) — 'running' while job.poll() is None, else 'ended'. The timer that asks stays in the window.
    3. conclude(attempt, job, task) -> Outcome, once per job: a second call returns the same Outcome and repeats no side
       effect (the history row, the project record, the orbitals).
       state — lifecycle.final_state (finished | failed | stopped | uncertain);
       artifacts — the files there are: 'output' (not empty), 'orbitals' (the Molden file made from the .gbw of ORCA
       on this computer), 'path' (the minimum-energy path of NEB);
       result — the file to open as the result: the path of NEB, else the output; '' when not finished;
       warnings — codes: 'optimization_unconverged' (ORCA ended normally, the optimization did not converge),
       'orbitals_not_made' (with its message in notes), 'project_not_updated', 'history_not_updated';
       problems — runner.diagnose of a failed calculation;
       actions — what the window may offer: 'open_result' (finished), 'open_steps' (stopped or failed with an output
       that may hold steps), 'show_problems' (failed), 'check_server' (uncertain: never sent again).
       A failure of a record is a warning with its message, never a failure of the calculation.
§3 INTERFACE SingleRun(history, convert_orbitals=runner.molden_from_gbw); .start(attempt, job, calc, title) -> str;
    SingleRun.observe(job) -> str; .conclude(attempt, job, task='') -> Outcome.
§4 TESTS tests/runtime/test_single_run.py — a fake job, a real project, no Qt, no Studio."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from azimuth.runtime import lifecycle


@dataclass(frozen=True)
class Outcome:
    state: str
    artifacts: tuple = ()
    result: str = ''
    warnings: tuple = ()
    notes: dict = field(default_factory=dict)
    problems: tuple = ()
    actions: tuple = ()
    repeated: bool = False  # T11: this end was recorded already (another watcher of the same calculation)


def _orbitals(job, convert):
    """The Molden file of an ORCA calculation run here ('' and the message when it could not be made)."""
    if job.spec.kind != 'orca' or not job.spec.command or job.spec.command[0] == 'server':
        return None, ''
    try:
        made = convert(Path(job.spec.output).with_suffix('.gbw'), job.spec.command[0])
    except ValueError as exc:
        return None, str(exc)
    return made, ''


class SingleRun:
    def __init__(self, history, convert_orbitals=None):
        from modules.sextant import runner

        self.history = history
        self.convert = convert_orbitals or runner.molden_from_gbw
        self.life = lifecycle.Lifecycle(history)

    def start(self, attempt, job, calc, title):
        """lifecycle.Lifecycle.started: the history row and the attempt 'running' in its project ('' or the error)."""
        job._attempt = attempt
        return self.life.started(attempt, job, calc, title)

    @staticmethod
    def observe(job):
        return 'running' if job.poll() is None else 'ended'

    def conclude(self, attempt, job, task=''):
        done = getattr(job, '_outcome', None)
        if done is not None:  # §2.3: once
            return done
        from modules.sextant import runner

        text = job.text() if hasattr(job, 'text') else ''
        state = lifecycle.final_state(job, text)
        repeated = self.recorded(attempt, job, state)
        warnings, notes, artifacts = [], {}, []
        output = Path(job.spec.output)
        if output.is_file() and output.stat().st_size > 0:
            artifacts.append('output')
        result, problems, actions = '', (), []
        if state == 'finished':
            unconverged = runner.diagnose(job.spec.kind, text)
            from azimuth.i18n import tr

            if any(what == tr('Оптимизация геометрии не сошлась за отведённые циклы.') for what, _ in unconverged):
                warnings.append('optimization_unconverged')
            made, why = (None, '') if repeated else _orbitals(job, self.convert)  # not made again
            if made or (repeated and Path(job.spec.output).with_suffix('.molden.input').is_file()):
                artifacts.append('orbitals')
            elif why:
                warnings.append('orbitals_not_made')
                notes['orbitals_not_made'] = why
            from azimuth.core import NEB_TASK

            path = runner.path_file(job.spec) if task == NEB_TASK else None
            if path is not None:
                artifacts.append('path')
            result = str(path or output)
            actions.append('open_result')
        elif state == 'uncertain':
            actions.append('check_server')
        else:
            if 'output' in artifacts:
                actions.append('open_steps')
            if state == 'failed':
                problems = tuple(runner.diagnose(job.spec.kind, text or _stdout(job), getattr(job, 'code', None)))
                actions.append('show_problems')
        ended = lifecycle.Ended(state, '', '') if repeated else self.life.ended(attempt, job, text, state=state)
        if ended.project_error:
            warnings.append('project_not_updated')
            notes['project_not_updated'] = ended.project_error
        if ended.history_error:
            warnings.append('history_not_updated')
            notes['history_not_updated'] = ended.history_error
        outcome = Outcome(state, tuple(artifacts), result, tuple(warnings), notes, problems, tuple(actions), repeated)
        job._outcome = outcome
        return outcome


def _stamp(path):
    try:
        stat = Path(path).stat()
    except OSError:
        return None
    return [stat.st_size, stat.st_mtime_ns]


def _recorded(self, attempt, job, state):
    """T11 (PROJECT_RUNTIME_GUIDE.md §13: an end delivered twice gives one record, no second analysis): this end was
    recorded already — by another object watching the same
    calculation (taken up twice, after a restart; once per object is §2.3). For a calculation of a project: its
    attempt has this state ('done' for finished) and, when done, the same output (size and time). Otherwise: the row
    of the history of its folder has this state. Then conclude() writes nothing and makes no orbitals again."""
    from modules.sextant import history

    if attempt is not None and attempt.in_project:
        from azimuth import projects

        try:
            project = projects.Project.load(attempt.project)
            entry = project.entry(attempt.molecule_id)
        except (OSError, ValueError, KeyError):
            return False
        kept = next((a for a in entry['attempts'] if a['id'] == attempt.attempt_id), None)
        wanted = 'done' if state == 'finished' else state
        if kept is None or kept.get('state') != wanted:
            return False
        return wanted != 'done' or kept.get('stamp') == _stamp(job.spec.output)
    try:
        rows = history.load(self.history)
    except Exception:  # noqa: BLE001 — the history is a help: when it cannot be read, the end is recorded
        return False
    folder = str(job.spec.folder)
    return any(r.get('folder') == folder and r.get('state') == state for r in rows)


SingleRun.recorded = _recorded


def _stdout(job):
    try:
        return job.stdout_text()
    except (AttributeError, OSError):
        return ''
