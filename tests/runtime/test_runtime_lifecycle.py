"""The life of one calculation without the window (azimuth/runtime/lifecycle.py; the roadmap of
2026-11-09, stages 1 and 3).

A fake job (its spec, code, state, message — what RemoteJob and runner.Job show), a real project, the history of
calculations in a dict standing for QSettings. Oracles: the attempt read back from the project, the row of the
history, the rules of §2 of the module (final states; the input of the attempt as at its start)."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from azimuth import projects
from azimuth.core import Calculation, read_xyz
from azimuth.runtime import lifecycle
from modules.sextant import history

WATER = read_xyz('3\nwater\nO 0 0 0.117\nH 0.757 0 -0.469\nH -0.757 0 -0.469')
NORMAL = '****ORCA TERMINATED NORMALLY****\n'


class Settings(dict):
    def value(self, key, default=None):
        return self.get(key, default)

    def setValue(self, key, value):
        self[key] = value


def started(tmp_path, place='serv3'):
    made = projects.Project.create(tmp_path / 'p')
    entry = made.add(WATER, Calculation(), name='вода')
    made.save()
    folder = made.root / 'calculations' / 'H2O_1'
    folder.mkdir(parents=True)
    output = folder / 'H2O.out'
    output.write_text('')
    snapshot = projects.Project.view(made.path).structure(WATER, Calculation(task='Оптимизация'))
    attempt = lifecycle.Attempt(folder, output, 'orca', place, made.path, entry['id'], 'att-1', snapshot)
    job = SimpleNamespace(spec=SimpleNamespace(folder=folder, output=output, kind='orca'), code=None, stopped=False,
                          state='running', message='')
    settings = Settings()
    life = lifecycle.Lifecycle(settings)
    assert life.started(attempt, job, Calculation(task='Оптимизация'), 'H₂O · ORCA') == ''
    return made, attempt, job, settings, life


def attempts(made, attempt):
    return projects.Project.load(made.path).entry(attempt.molecule_id)['attempts']


def test_the_start_records_the_attempt_and_the_history(tmp_path):
    made, attempt, job, settings, _ = started(tmp_path)
    (rec,) = attempts(made, attempt)
    assert rec['id'] == 'att-1' and rec['state'] == 'running' and rec['place'] == 'serv3' and rec['input'] == attempt.input
    (row,) = history.load(settings)
    assert row['folder'] == str(attempt.folder) and row['place'] == 'serv3' and row['title'] == 'H₂O · ORCA'


@pytest.mark.parametrize('text, code, stopped, state, expected, recorded', [
    (NORMAL, 0, False, 'finished', 'finished', 'done'),
    ('cut', 1, False, 'failed', 'failed', 'failed'),
    ('cut', -15, True, 'stopped', 'stopped', 'stopped'),
    ('', 1, False, 'uncertain', 'uncertain', 'uncertain'),
])
def test_the_end_is_recorded_by_the_ids_of_the_attempt(tmp_path, text, code, stopped, state, expected, recorded):
    made, attempt, job, settings, life = started(tmp_path)
    job.code, job.stopped, job.state, job.message = code, stopped, state, 'the message of the job'
    ended = life.ended(attempt, job, text)
    assert ended == lifecycle.Ended(expected)
    (rec,) = attempts(made, attempt)
    assert rec['state'] == recorded and rec.get('note') == 'the message of the job'
    assert history.load(settings)[0]['state'] == expected


def test_the_molecule_edited_after_the_start_does_not_change_the_input_of_the_attempt(tmp_path):
    made, attempt, job, settings, life = started(tmp_path)
    with projects.edit(made.path) as project:  # the user moves an atom of the molecule meanwhile
        moved = read_xyz('3\nwater\nO 0 0 0.5\nH 0.757 0 -0.469\nH -0.757 0 -0.469')
        project.entry(attempt.molecule_id)['structure'] = project.structure(moved, Calculation())
    job.code = 0
    life.ended(attempt, job, NORMAL)
    (rec,) = attempts(made, attempt)
    assert rec['input'] == attempt.input  # the snapshot of the start
    molecule, calc = projects.Project.load(made.path).read_structure(rec['input'])
    assert molecule.atoms[0].z == pytest.approx(0.117) and calc.task == 'Оптимизация'


def test_a_failed_project_record_is_returned_not_swallowed(tmp_path):
    made, attempt, job, settings, life = started(tmp_path)
    made.database.write_bytes(b'broken' * 50)
    job.code = 0
    ended = life.ended(attempt, job, NORMAL)
    assert ended.state == 'finished' and 'повреждена' in ended.project_error  # said by the window
    assert history.load(settings)[0]['state'] == 'finished'  # the history finished all the same


def test_a_calculation_outside_a_project(tmp_path):
    folder = tmp_path / 'calc'
    folder.mkdir()
    attempt = lifecycle.Attempt(folder, folder / 'x.out', 'xtb')
    job = SimpleNamespace(spec=SimpleNamespace(folder=folder, output=folder / 'x.out', kind='xtb'), code=0,
                          stopped=False, state='finished', message='')
    settings = Settings()
    life = lifecycle.Lifecycle(settings)
    assert not attempt.in_project and life.started(attempt, job, Calculation(), 'x') == ''
    assert life.ended(attempt, job, 'normal termination of xtb').state == 'finished'
    assert json.loads(settings[history.KEY])[0]['state'] == 'finished' and Path(folder).is_dir()


# -- the end of a row of a queue, without the window ---------------------------------------------------
DATA = Path(__file__).resolve().parents[1] / 'data'


def queue_of(tmp_path, n=2):
    from modules.sextant import batch

    items = [batch.BatchItem(f'w{k}', WATER) for k in range(n)]
    q = batch.Batch('orca', Calculation(task='Оптимизация'), items, tmp_path / 'queue')
    q.folder.mkdir(parents=True)
    q.save()
    return q


def row_job(tmp_path, code=0, stopped=False, message='', kind='orca'):
    folder = tmp_path / 'queue' / 'w0'
    folder.mkdir(parents=True, exist_ok=True)
    return SimpleNamespace(spec=SimpleNamespace(folder=folder, output=folder / 'w0.out', kind=kind, command=('server',)),
                           code=code, stopped=stopped, state='finished', message=message)


def test_a_row_that_ended_normally_gets_its_numbers(tmp_path):
    import re

    from modules.sextant import batch

    text = (DATA / 'orca601' / 'h2o_optfreq.out').read_text(encoding='utf-8', errors='replace')
    q = queue_of(tmp_path)
    item = q.items[0]
    settings = Settings()
    ended = lifecycle.row_ended(q, item, row_job(tmp_path), text, settings)
    last = float(re.findall(r'FINAL SINGLE POINT ENERGY\s+(-?\d+\.\d+)', text)[-1])
    assert ended.state == 'done' and ended.energy == pytest.approx(last, abs=1e-10) and ended.note == ''
    again = batch.Batch.load(q.folder)  # the row is in the queue on disk (and so in its project)
    assert again.items[0].state == 'done' and again.items[0].energy == pytest.approx(last, abs=1e-10)
    assert again.items[1].state == 'waiting'


@pytest.mark.parametrize('code, stopped, message, state', [
    (1, False, 'ORCA завершилась с ошибкой', 'failed'),
    (-15, True, '', 'stopped'),
])
def test_a_row_that_did_not_end_normally_keeps_why(tmp_path, code, stopped, message, state):
    q = queue_of(tmp_path)
    ended = lifecycle.row_ended(q, q.items[0], row_job(tmp_path, code, stopped, message), 'cut output', None)
    assert ended.state == state and ended.energy is None
    assert q.items[0].state == state and (message in ended.note if message else True)


def test_an_unknown_outcome_of_a_row_stays_unknown_and_is_never_repeated(tmp_path):
    # it was 'failed' — and a failed row may be prepared again, so a job the
    # server had accepted could be sent twice. Now 'uncertain', kept in batch.json, not a row to repeat
    from modules.sextant import batch, batch_retry

    q = queue_of(tmp_path)
    job = row_job(tmp_path, 1, False, 'Неизвестно, принял ли сервер очередь')
    job.state = 'uncertain'
    assert lifecycle.row_state(job, '') == 'uncertain'
    ended = lifecycle.row_ended(q, q.items[0], job, '', None)
    assert ended.state == 'uncertain' and 'Неизвестно' in ended.note
    again = batch.Batch.load(q.folder)
    assert again.items[0].state == 'uncertain' and 'Неизвестно' in again.items[0].note
    for other in again.items[1:]:
        other.state = 'done'
    assert 'uncertain' in batch.NOT_REPEATABLE and again.done()  # the queue does not wait for it forever
    item = again.items[0]
    with pytest.raises(ValueError, match='повтор не готовится'):
        batch_retry.prepare(again, [(0, item.molecule, item.charge, item.multiplicity, 'output')], again.calc,
                            again.kind, again.place, tmp_path / 'retry')
    assert not (tmp_path / 'retry').exists()


# -- the row of a job, and its end once -------------------------------
def test_the_row_of_a_job_is_found_by_its_folder_not_by_the_running_row(tmp_path):
    q = queue_of(tmp_path, n=3)
    job = row_job(tmp_path)  # the folder of w0
    q.items[0].folder = str(job.spec.folder)
    q.items[2].state = 'running'  # another row runs meanwhile
    assert lifecycle.row_of(q, job) is q.items[0]
    stranger = SimpleNamespace(spec=SimpleNamespace(folder=tmp_path / 'elsewhere'))
    assert lifecycle.row_of(q, stranger) is q.items[2]  # an older record: the running row knows no folder
    q.items[2].state = 'done'
    assert lifecycle.row_of(q, stranger) is None


def test_a_job_of_a_folder_no_row_has_is_nobodys(tmp_path):
    """The running row has a folder of its own, and the job
    another one — the end of that job is not given to the running row."""
    current = SimpleNamespace(folder='/queue/new', name='new', state='running')
    queue = SimpleNamespace(items=[current], current=lambda: current)
    job = SimpleNamespace(spec=SimpleNamespace(folder='/queue/old'))
    assert lifecycle.row_of(queue, job) is None
    same = SimpleNamespace(spec=SimpleNamespace(folder='/queue/new/'))  # the same folder written otherwise
    assert lifecycle.row_of(queue, same) is current
    assert lifecycle.inside('/queue', '/queue/old') and not lifecycle.inside('/queue', '/elsewhere/old')
    assert not lifecycle.inside('', '/queue/old')


def test_the_end_of_a_row_is_recorded_once(tmp_path):
    from modules.sextant import batch

    q = queue_of(tmp_path)
    job = row_job(tmp_path, code=1, message='SCF')
    settings = Settings()
    history.save(settings, [{'folder': str(job.spec.folder), 'state': ''}])
    first = lifecycle.row_ended(q, q.items[0], job, 'cut', settings)
    q.items[0].state = 'changed by hand'
    history.save(settings, [{'folder': str(job.spec.folder), 'state': 'changed by hand'}])
    assert lifecycle.row_ended(q, q.items[0], job, 'cut', settings) is first
    assert q.items[0].state == 'changed by hand' and history.load(settings)[0]['state'] == 'changed by hand'
    assert batch.Batch.load(q.folder).items[0].state == 'failed'
