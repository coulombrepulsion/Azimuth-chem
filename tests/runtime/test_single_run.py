"""One calculation start to result without the window (azimuth/runtime/single_run.py, 0.108.32; the review of
2026-11-09, step B and §7 «Приёмка»).

A fake job that ends when told (its poll, text, code — what runner.Job and RemoteJob show), a real project in a
temporary folder, the history in a dict standing for QSettings, a converter of orbitals that records its calls. No Qt,
no Studio. Oracles: the attempt read back from the project, the history row, the files in the folder, the calls made.
"""

from pathlib import Path
from types import SimpleNamespace

from azimuth import projects
from azimuth.core import Calculation, read_xyz
from azimuth.runtime import lifecycle
from azimuth.runtime.single_run import SingleRun
from modules.sextant import history

WATER = read_xyz('3\nwater\nO 0 0 0.117\nH 0.757 0 -0.469\nH -0.757 0 -0.469')
NORMAL = 'FINAL SINGLE POINT ENERGY -76.4\n****ORCA TERMINATED NORMALLY****\n'


class Settings(dict):
    def value(self, key, default=None):
        return self.get(key, default)

    def setValue(self, key, value):
        self[key] = value


class FakeJob:
    def __init__(self, folder, output, command=('/opt/orca/orca',), place=''):
        self.spec = SimpleNamespace(folder=folder, output=output, kind='orca', command=command)
        self.code = None
        self.stopped = False
        self.state = 'running'
        self.message = ''
        self._text = ''

    def end(self, text, code=0, state=''):
        self._text, self.code = text, code
        Path(self.spec.output).write_text(text)
        self.state = state or ('finished' if code == 0 else 'failed')

    def poll(self):
        return self.code

    def text(self):
        return self._text

    def stdout_text(self):
        return ''


def project_run(tmp_path, converted=None):
    made = projects.Project.create(tmp_path / 'p')
    entry = made.add(WATER, Calculation(), name='вода')
    made.save()
    folder = made.root / 'calculations' / 'H2O_1'
    folder.mkdir(parents=True)
    output = folder / 'H2O.out'
    snapshot = projects.Project.view(made.path).structure(WATER, Calculation(task='Оптимизация'))
    attempt = lifecycle.Attempt(folder, output, 'orca', '', made.path, entry['id'], 'att-1', snapshot)
    calls = [] if converted is None else converted

    def convert(gbw, program):
        calls.append((Path(gbw).name, program))
        made_file = Path(gbw).with_suffix('.molden.input')
        made_file.write_text('[Molden Format]\n')
        return made_file

    settings = Settings()
    run = SingleRun(settings, convert_orbitals=convert)
    job = FakeJob(folder, output)
    assert run.start(attempt, job, Calculation(task='Оптимизация'), 'H₂O · ORCA') == ''
    return made, entry, attempt, job, run, settings, calls


def attempt_of(made, entry):
    (rec,) = projects.Project.load(made.path).entry(entry['id'])['attempts']
    return rec


def test_the_whole_chain_of_a_calculation_of_a_project(tmp_path):
    made, entry, attempt, job, run, settings, calls = project_run(tmp_path)
    assert run.observe(job) == 'running' and attempt_of(made, entry)['state'] == 'running'
    job.end(NORMAL)
    assert run.observe(job) == 'ended'
    outcome = run.conclude(attempt, job, 'Оптимизация')
    assert outcome.state == 'finished' and outcome.actions == ('open_result',)
    assert outcome.result == str(job.spec.output) and outcome.artifacts == ('output', 'orbitals')
    assert calls == [('H2O.gbw', '/opt/orca/orca')] and outcome.warnings == ()
    assert attempt_of(made, entry)['state'] == 'done'
    (row,) = history.load(settings)
    assert row['state'] == 'finished' and row['folder'] == str(attempt.folder)


def test_the_end_is_concluded_once(tmp_path):
    # §7: «Повторное завершение не создаёт дубликатов истории и повторных побочных действий»
    made, entry, attempt, job, run, settings, calls = project_run(tmp_path)
    job.end(NORMAL)
    first = run.conclude(attempt, job)
    history.save(settings, history.finish(history.load(settings), attempt.folder, 'changed by hand'))
    assert run.conclude(attempt, job) is first
    assert len(calls) == 1 and len(history.load(settings)) == 1 and history.load(settings)[0]['state'] == 'changed by hand'
    assert len(projects.Project.load(made.path).entry(entry['id'])['attempts']) == 1


def test_the_input_of_the_attempt_is_its_own_snapshot(tmp_path):
    # §7: «Изменение молекулы после запуска не меняет вход попытки»
    made, entry, attempt, job, run, settings, calls = project_run(tmp_path)
    source = {'atoms': [['O', 0, 0, 0]], 'calculation': {'task': 'Энергия'}}
    other = lifecycle.Attempt(attempt.folder, attempt.output, input=source, extra={'k': [1]})
    source['atoms'][0][0] = 'S'
    source['calculation']['task'] = 'Оптимизация'
    assert other.input == {'atoms': [['O', 0, 0, 0]], 'calculation': {'task': 'Энергия'}} and other.extra == {'k': [1]}
    before = dict(attempt.input)
    job.end(NORMAL)
    run.conclude(attempt, job)
    assert attempt_of(made, entry)['input'] == before


def test_a_failed_calculation_offers_its_steps_and_problems(tmp_path):
    made, entry, attempt, job, run, settings, calls = project_run(tmp_path)
    job.end('SCF NOT CONVERGED AFTER 125 CYCLES\n', code=1)
    outcome = run.conclude(attempt, job)
    assert outcome.state == 'failed' and outcome.result == '' and calls == []
    assert outcome.actions == ('open_steps', 'show_problems') and outcome.problems
    assert attempt_of(made, entry)['state'] == 'failed'


def test_an_unknown_sending_is_checked_never_sent_again(tmp_path):
    made, entry, attempt, job, run, settings, calls = project_run(tmp_path)
    job.message = 'the answer of the server was lost'
    job.end('', code=1, state='uncertain')
    outcome = run.conclude(attempt, job)
    assert outcome.state == 'uncertain' and outcome.actions == ('check_server',)
    rec = attempt_of(made, entry)
    assert rec['state'] == 'uncertain' and rec['note'] == 'the answer of the server was lost'


def test_a_record_that_fails_is_a_warning_not_a_failure(tmp_path):
    made, entry, attempt, job, run, settings, calls = project_run(tmp_path)
    gone = lifecycle.Attempt(attempt.folder, attempt.output, 'orca', '', tmp_path / 'missing' / 'project.json',
                             entry['id'], 'att-1', attempt.input)
    job.end(NORMAL)
    outcome = run.conclude(gone, job)
    assert outcome.state == 'finished' and 'project_not_updated' in outcome.warnings
    assert outcome.notes['project_not_updated'] and outcome.actions == ('open_result',)


def test_orbitals_not_made_are_said_and_a_server_run_makes_none(tmp_path):
    def refuse(gbw, program):
        raise ValueError('Нет файла орбиталей ORCA: H2O.gbw')

    made, entry, attempt, job, run, settings, calls = project_run(tmp_path)
    run.convert = refuse
    job.end(NORMAL)
    outcome = run.conclude(attempt, job)
    assert 'orbitals_not_made' in outcome.warnings and 'H2O.gbw' in outcome.notes['orbitals_not_made']
    server = FakeJob(attempt.folder, attempt.output, command=('server',))
    server.end(NORMAL)
    assert 'orbitals' not in run.conclude(lifecycle.Attempt(attempt.folder, attempt.output), server).artifacts
