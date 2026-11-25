"""The life of one calculation apart from the window: its attempt, its start, its end (the roadmap of
2026-11-09, stages 1 and 3 — «Жизненный цикл расчёта тестируется с поддельным исполнителем без создания Studio»).

§1 PURPOSE
    What happened at the start and at the end of a calculation lived in the handlers of the window (run_actions,
    project_actions): the final state from the output, the history of calculations, the attempt in the project. It
    could be checked only with the whole window. Here those steps are one object of their own; the window calls it
    and shows what it returns.
§2 RULES
    1. Attempt — the explicit context of an attempt: the folder and the output of the calculation, its kind, the
       place, and for a calculation of a project the manifest, the molecule id, the attempt id and the snapshot of
       its input (a structure of the project). No widget, no tab: the addressee is the ids (delivery.result_tab).
    2. final_state(job, text) — 'stopped' (the user stopped it), 'finished' (the program ended normally,
       modules/sextant/runner.finished_normally), 'uncertain' (the answer of the server was lost, runs.py), else
       'failed'.
    3. Lifecycle(history) — started = remember (the history) + record_start (the project); — history: an object with
    value(key, default) and setValue(key, value) (QSettings, a dict
       wrapper in the tests).
       started(attempt, job, calc, title): the history of calculations gets its row; a calculation of a project gets
       its attempt 'running' (with the snapshot of the input, its place); the window keeps the attempt on the job.
       ended(attempt, job, text) -> Ended(state, project_error, history_error): the state of §2.2; the attempt of the
       project recorded by its ids — 'done' when finished, else the state — with the message of the job; the
       history row finished. A failure of one record never stops the other, and is returned, not swallowed: the
       window says it (a result saved but the project not updated).
    4. The input of an attempt stays as recorded at its start: a molecule edited after the start does not change it
       (the roadmap, invariant 3). Attempt copies input and extra when made (a frozen dataclass does not
       freeze a dict inside it).
§3 INTERFACE Attempt; final_state(job, text); Lifecycle(history).started(...), .ended(...) -> Ended.
    Row_state(job, text); row_ended(queue, item, job, text, history_settings) -> RowEnded — the end of a
    row of a queue (its state, its numbers, why it failed, the queue and its project, the history); once
    per job; row_of(queue, job) — the row of that job, by its folder (None for a folder no row has);
    inside(root, folder).
    «Once» means once per job object in this run of the program: the end remembered on the job (_outcome,
    _row_ended) after its records are made. A job taken up again after a restart is a new object; then the records
    themselves guard: the attempt and the row are written by their ids (the same state written again changes
    nothing), a row already 'done' is not started again. An interruption between the records of one end (the
    project written, the history not) is not one transaction: what was not written is said (project_warning,
    errors.log), not repeated.
§4 TESTS tests/runtime/test_runtime_lifecycle.py (a fake job, a real project, no Qt).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Attempt:
    folder: Path
    output: Path
    kind: str = 'orca'
    place: str = ''
    project: Path | None = None  # the manifest
    molecule_id: str | None = None
    attempt_id: str | None = None
    input: dict | None = None  # the snapshot of the input (Project.structure)
    extra: dict = field(default_factory=dict)

    def __post_init__(self):
        # the snapshot is the attempt's own — a copy, so the caller's dict edited later changes nothing
        import copy

        object.__setattr__(self, 'input', copy.deepcopy(self.input))
        object.__setattr__(self, 'extra', copy.deepcopy(self.extra))

    @property
    def in_project(self):
        return self.project is not None and bool(self.molecule_id) and bool(self.attempt_id)


@dataclass(frozen=True)
class Ended:
    state: str
    project_error: str = ''
    history_error: str = ''


def final_state(job, text):
    from modules.sextant import runner

    if getattr(job, 'stopped', False):
        return 'stopped'
    if runner.finished_normally(job.spec.kind, text or '', getattr(job, 'code', None)):
        return 'finished'
    if getattr(job, 'state', '') == 'uncertain':
        return 'uncertain'
    return 'failed'


class Lifecycle:
    def __init__(self, history):
        self.history = history

    def started(self, attempt, job, calc, title):
        """§2.3: remember() and record_start(); returns the error of the project record ('' when none)."""
        self.remember(attempt, job, calc, title)
        return self.record_start(attempt, calc)

    def remember(self, attempt, job, calc, title):
        """The row of the history of calculations — a help, never a failure of the calculation."""
        from modules.sextant import history

        try:
            rec = history.record(job.spec, attempt.kind, calc, title, attempt.place)
            history.save(self.history, history.add(history.load(self.history), rec))
        except Exception as exc:  # noqa: BLE001 — the history is a help: kept in errors.log (the review, §15)
            from azimuth.runtime.provenance import note

            note('history', f'{attempt.folder}: the row of the history was not written ({exc})')

    def record_start(self, attempt, calc):
        """The attempt 'running' in its project ('' — done, or not a calculation of a project; else the error)."""
        if not attempt.in_project:
            return ''
        from azimuth import projects

        try:
            with projects.edit(attempt.project) as project:
                entry = project.entry(attempt.molecule_id)
                molecule, saved = project.read_structure(attempt.input or entry['structure'])
                if saved.guess and not getattr(calc, 'guess', None):
                    from dataclasses import replace

                    calc = replace(calc, guess=saved.guess)
                record = project.record(entry['id'], attempt.attempt_id, molecule, calc, attempt.kind, 'running',
                                        attempt.folder, attempt.output)
                record['place'] = attempt.place
                if attempt.input:
                    record['input'] = attempt.input
        except (OSError, ValueError, KeyError, StopIteration) as exc:
            return str(exc)
        return ''

    def ended(self, attempt, job, text='', state=None, with_history=True):
        """§2.3; state — when the caller knows it (a row of a queue), else final_state(job, text); with_history=False —
        the project record alone (the window finishes the history itself)."""
        from modules.sextant import history

        keep = with_history
        state = state or final_state(job, text)
        project_error = history_error = ''
        if attempt is not None and attempt.in_project:
            from azimuth import projects

            try:
                with projects.edit(attempt.project) as project:
                    entry = project.entry(attempt.molecule_id)
                    recorded = next((a for a in entry['attempts'] if a['id'] == attempt.attempt_id), None)
                    molecule, calc = project.read_structure(recorded['input'] if recorded and recorded.get('input')
                                                            else attempt.input or entry['structure'])
                    project.record(entry['id'], attempt.attempt_id, molecule, calc, attempt.kind,
                                   'done' if state == 'finished' else state, attempt.folder, attempt.output,
                                   note=getattr(job, 'message', '') or '')
            except (OSError, ValueError, KeyError, StopIteration) as exc:
                project_error = str(exc)
        if not keep:
            return Ended(state, project_error, history_error)
        try:
            history.save(self.history, history.finish(history.load(self.history), job.spec.folder, state))
        except Exception as exc:  # noqa: BLE001
            history_error = str(exc)
        return Ended(state, project_error, history_error)


# -- the end of a row of a queue -----------------------------------------------------------------------
@dataclass(frozen=True)
class RowEnded:
    state: str  # of the row of the queue: 'done' | 'failed' | 'stopped' | 'uncertain'
    energy: float | None = None
    gibbs: float | None = None
    heat: float | None = None
    note: str = ''
    project_warning: str = ''
    history_error: str = ''
    repeated: bool = False  # T11: the row had ended already — nothing recorded or started again


def row_state(job, text):
    """final_state for a row of a queue: 'finished' is the 'done' of a row. An
    unknown outcome of the sending stays 'uncertain' — it was 'failed', and a failed row may be prepared again, so a job
    the server had accepted could be sent a second time; now the row waits for the server to be asked."""
    state = final_state(job, text)
    return {'finished': 'done'}.get(state, state)


def _same_folder(a, b):
    try:
        return Path(a).resolve() == Path(b).resolve()
    except (OSError, RuntimeError, ValueError):
        return str(a) == str(b)


def row_of(queue, job):
    """The row whose calculation this
    job is — by its folder. The running row of the queue may be another one by then (a queue taken up again, a row
    skipped meanwhile).
    A job whose folder no row has is nobody's — None, not
    the running row. The running row is taken only when it knows no folder itself (a record older than 0.91.7, where
    a row got its folder only at the end): then nothing can contradict it. A row is given its folder before its job
    starts (batch_actions), so a running row of the current code always has one."""
    folder = getattr(getattr(job, 'spec', None), 'folder', None)
    if folder:
        mine = next((item for item in queue.items if item.folder and _same_folder(item.folder, folder)), None)
        if mine is not None:
            return mine
    running = queue.current()
    if running is not None and not running.folder:
        return running
    return None


def inside(root, folder):
    """Whether folder lies in root (the folder of a queue) — a calculation of that queue by where it is."""
    if not root or not folder:
        return False
    try:
        return Path(root).resolve() in Path(folder).resolve().parents
    except (OSError, RuntimeError, ValueError):
        return False


ROW_ENDED = ('done', 'failed', 'stopped', 'skipped')  # the states of a row whose end is recorded


def row_ended(queue, item, job, text, history_settings=None):
    """The bookkeeping of the end of a row (was batch_actions.batch_job_finished): its state, its energy, G, ΔHf and
    geometry read from the output, why it failed, the row recorded in the queue (and so in its project — Batch.save,
    projects.sync), the follow-ups of a calculation of binding energy, the row of the history finished. No widget.
    Once per job — a second end (a timer firing twice) returns the same RowEnded and records nothing again."""
    done = getattr(job, '_row_ended', None)
    if done is not None:
        return done
    if item is not None and item.state in ROW_ENDED:
        # T11 (PROJECT_RUNTIME_GUIDE.md §13): an end delivered twice gives one record and no second analysis. The end of
        # a row already recorded, delivered again by another
        # watcher of the same calculation (taken up twice, after a restart) — what was recorded is returned; nothing
        # written again, no orbitals made again, no follow-up calculations (BSSE) added again
        ended = RowEnded(item.state, item.energy, item.gibbs, item.heat, item.note, '', '', True)
    else:
        ended = _row_ended(queue, item, job, text, history_settings)
    try:
        job._row_ended = ended
    except AttributeError:  # a job that takes no attribute: recorded, only not remembered
        pass
    return ended


def _row_ended(queue, item, job, text, history_settings):
    from modules.sextant import batch as batches
    from modules.sextant import history, runner

    state = row_state(job, text)
    history_error = ''
    if history_settings is not None:
        try:
            history.save(history_settings, history.finish(history.load(history_settings), job.spec.folder,
                                                          final_state(job, text)))
        except Exception as exc:  # noqa: BLE001 — the history is a help
            history_error = str(exc)
    energy = geometry = gibbs = heat = None
    if state == 'done':
        energy, geometry, gibbs, heat = batches.result_of(job.spec.kind, text)
        if job.spec.kind == 'orca' and job.spec.command and job.spec.command[0] != 'server':
            try:  # the orbitals of every conformer, as after a single calculation
                runner.molden_from_gbw(job.spec.output.with_suffix('.gbw'), job.spec.command[0])
            except ValueError:
                pass
    note = ''
    warning = ''
    if item is not None:
        # why it failed, kept (the message of the job: «MOPAC завершилась с ошибкой», a lost download …)
        note = '' if state == 'done' else (getattr(job, 'message', '') or
                                           '; '.join(what for what, _ in runner.diagnose(job.spec.kind, text, job.code)))
        item.note = note
        queue.finished(item, state, energy, gibbs, geometry, heat)
        if queue.purpose == 'binding':  # the single points of BSSE after a complex
            from modules.sextant import binding

            if binding.follow_ups(queue, item):
                if queue.extra.get('project'):
                    from azimuth.projects import extend_queue

                    try:  # the queue goes on even when the project is not updated
                        extend_queue(queue)
                    except (OSError, ValueError, KeyError, StopIteration) as exc:
                        queue.project_warning = str(exc)
                queue.save()
        warning = getattr(queue, 'project_warning', '') or ''
    return RowEnded(state, energy, gibbs, heat, note, warning, history_error)
