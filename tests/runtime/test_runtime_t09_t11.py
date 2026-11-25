"""The scenarios T09–T11 of docs/architecture/PROJECT_RUNTIME_GUIDE.md §13 checked whole.

T09: an unreachable server does not stop a project from opening; the last state and its age are shown.
T10: a job gone from squeue while its output is late is not a success until the evidence is enough.
T11: an end delivered twice gives one record and no second analysis.

A scripted server (Server below): the answers of squeue in order, an output on «the server» that grows when told,
offline when told — the commands of RemoteJob answered from a folder here; the fake SLURM server of
tests/fake_server.py for opening a server that does not answer. Oracles: the mark of the end of ORCA in the output
(the only evidence of success), the states and messages of the job, observed.json, the records of the project and
of the history read back, the calls of the converter of orbitals counted.
"""

import os
import shutil
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from modules.sextant import cluster, keychain, remote_job, runner, server_access
from modules.sextant.remote import ServerProfile
from modules.sextant.ssh import Result, SshError

NORMAL = '****ORCA TERMINATED NORMALLY****\n'


class Server:
    """squeue answers (the last one repeats), the output on the server, offline; hooks by the number of squeue calls."""

    def __init__(self, root, answers, hooks=None):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.out = self.root / 'H2O.out'
        self.out.write_text('ORCA started\n', encoding='utf-8')
        self.answers = list(answers)
        self.hooks = dict(hooks or {})
        self.offline = False
        self.asked = 0

    def text(self, command, timeout=None):
        if self.offline:
            raise SshError('ssh: connect to host: Connection timed out', 'connection')
        if 'squeue -h -j' in command:  # cluster.queue_command (0.222.19: it also serves a server without SLURM)
            self.asked += 1
            hook = self.hooks.pop(self.asked, None)
            if hook:
                hook(self)
            return self.answers.pop(0) if len(self.answers) > 1 else self.answers[0]
        if command.startswith('wc -c'):
            return f'{self.out.stat().st_size}\n'
        if command.startswith('ls -1'):
            return '\n'.join(p.name for p in self.root.iterdir()) + '\n'
        if command.startswith('cat ') and cluster.EXIT_MARK in command:  # the end the job wrote itself
            mark = self.root / cluster.EXIT_MARK
            return mark.read_text(encoding='utf-8') if mark.is_file() else ''
        return ''

    def run(self, command, timeout=None):
        if self.offline:
            raise SshError('ssh: connect to host: Connection timed out', 'connection')
        if command.startswith('tail -c +'):
            start = int(command.split()[2][1:])
            return Result(0, self.out.read_bytes()[start - 1:], '')
        return Result(0, b'', '')

    def download(self, names, remote_dir, local_folder, timeout=None):
        for name in names:
            shutil.copy2(self.root / name, Path(local_folder) / name)

    def finish(self, server=None):
        with open(self.out, 'a', encoding='utf-8') as f:
            f.write(NORMAL)


def watched(tmp_path, server, observed=None):
    folder = tmp_path / 'local' / 'H2O_1'
    folder.mkdir(parents=True)
    output = folder / 'H2O.out'
    if observed:
        (folder / remote_job.OBSERVED).write_text(observed, encoding='utf-8')
    profile = ServerProfile('serv3', '192.0.2.103', 22, 'user', str(tmp_path / 'remote'))
    info = {'job': '4127', 'folder': str(server.root), 'program': 'orca', 'server': 'serv3'}
    return remote_job.RemoteJob.resume(folder, output, profile, server, info, interval=0.01,
                                       sleep=lambda s: time.sleep(min(s, 0.002)))


def ended(job, seconds=10):
    end = time.monotonic() + seconds
    seen = set()
    while job.poll() is None and time.monotonic() < end:
        seen.add(job.state)
        time.sleep(0.005)
    seen.add(job.state)
    return job.poll(), seen


# -- T10 -----------------------------------------------------------------------------------------------------------
def test_t10_an_output_that_comes_after_the_job_left_the_queue_is_a_success(tmp_path):
    # gone from squeue with the output not finished yet (a slow file system): the end is waited for, not «failed»
    server = Server(tmp_path / 'remote' / 'H2O_1', ['RUNNING|0:10|node', ''], hooks={3: Server.finish})
    code, seen = ended(watched(tmp_path, server).start())
    assert code == 0 and 'finished' in seen and 'failed' not in seen
    assert server.asked >= 3


def test_t10_a_job_gone_without_the_mark_fails_only_after_enough_evidence_never_succeeds(tmp_path):
    for answers in (['RUNNING|0:10|node', ''], ['RUNNING|0:10|node', 'COMPLETED|0:12|node']):
        server = Server(tmp_path / answers[-1][:4] / 'H2O_1', answers)
        job = watched(tmp_path / answers[-1][:4], server)
        code, seen = ended(job.start())
        assert code == 1 and job.state == 'failed' and 'finished' not in seen, answers
        # 1 answer «running», then GONE_CHECKS answers «not in the queue» with the output not growing
        assert server.asked >= 1 + remote_job.GONE_CHECKS, answers


def test_t10_a_job_that_wrote_its_end_is_known_to_have_ended_at_once(tmp_path):
    # the job broke at its start (Windows check 2026-11-24: about four minutes of «жду вывод» before the error): the
    # exit code it wrote ends the watching at the first answer «not in the queue»
    server = Server(tmp_path / 'remote' / 'H2O_1', ['RUNNING|0:10|node', ''])
    (server.root / cluster.EXIT_MARK).write_text('2\n', encoding='utf-8')
    code, seen = ended(watched(tmp_path, server).start())
    assert code == 1 and 'finished' not in seen and server.asked == 2


def test_t10_a_job_back_in_the_queue_is_watched_again(tmp_path):
    # squeue said nothing once (between its answers), then the job again: the count starts anew
    server = Server(tmp_path / 'remote' / 'H2O_1', ['RUNNING|0:10|node', '', 'RUNNING|0:11|node', 'RUNNING|0:12|node',
                                                    ''], hooks={5: Server.finish})
    code, seen = ended(watched(tmp_path, server).start())
    assert code == 0 and 'failed' not in seen


def test_t10_ended_states_of_slurm_are_not_running():
    assert cluster.queue_state('COMPLETED|1:02|node') is None
    assert cluster.queue_state('CANCELLED by 1001|0:05|node') is None
    assert cluster.queue_state('TIMEOUT|9:59|node') is None
    assert cluster.queue_state('RUNNING|1:02|node') == 'RUNNING' and cluster.queue_state('COMPLETING|1:02|n') == 'COMPLETING'


# -- T09 -----------------------------------------------------------------------------------------------------------
def test_t09_a_server_out_of_reach_at_the_start_says_what_was_known_and_when(tmp_path, monkeypatch):
    monkeypatch.setattr(remote_job, 'RETRY', (0.05, 0.05))
    server = Server(tmp_path / 'remote' / 'H2O_1', ['RUNNING|0:10|node'])
    server.offline = True
    job = watched(tmp_path, server, observed='{"state": "running", "at": "2026-11-10T14:02:00"}').start()
    end = time.monotonic() + 5
    while job.state != 'offline' and time.monotonic() < end:
        time.sleep(0.005)
    # not a failure: the calculation goes on there; what was seen last and when is said
    assert job.state == 'offline' and job.poll() is None
    assert 'Нет связи' in job.message and '14:02 10.11' in job.message and 'шёл' in job.message
    # what ssh said is in the message (Windows check 2026-11-24: «why it cannot connect is not said»)
    assert 'Ответ ssh: ssh: connect to host: Connection timed out' in job.message
    server.offline = False
    end = time.monotonic() + 5
    while job.state == 'offline' and time.monotonic() < end:
        time.sleep(0.005)
    assert job.state == 'running' and job.poll() is None
    seen = remote_job.read_observed(job.spec.folder)  # the new answer kept for the next start
    assert seen[0] == 'running' and seen[1] != '2026-11-10T14:02:00'
    server.finish()
    server.answers = ['']
    code, _ = ended(job)
    assert code == 0 and remote_job.read_observed(job.spec.folder)[0] == 'gone'


@pytest.fixture
def fake(tmp_path, monkeypatch):
    if os.name == 'nt':
        pytest.skip('the fake server is a set of POSIX scripts')
    from tests import fake_server

    root = fake_server.install(tmp_path, monkeypatch)
    monkeypatch.setattr(keychain, 'SESSION', {})
    monkeypatch.setattr(keychain, '_lib', lambda: None)
    return root


def test_t09_a_server_that_does_not_answer_is_opened_for_watching(fake):
    profile = ServerProfile('serv3', '192.0.2.103', 22, 'user', '~/azimuth/calculations')
    now = lambda work: work(lambda *a: True)  # noqa: E731
    (fake / 'offline').write_text('')
    with pytest.raises(SshError):  # to send, the server is needed
        server_access.open_server(None, profile, ask=lambda p, w: None, waiting=now)
    connection, resources, why = server_access.open_for_watching(None, profile, ask=lambda p, w: None, waiting=now)
    assert resources is None and 'timed out' in why and connection.profile is profile
    (fake / 'offline').unlink()
    connection, resources, why = server_access.open_for_watching(None, profile, ask=lambda p, w: None, waiting=now)
    assert resources is not None and resources.slurm and why == ''


# -- T11 -----------------------------------------------------------------------------------------------------------
def test_t11_the_end_of_a_calculation_delivered_twice_is_one_record_and_no_analysis_again(tmp_path):
    from azimuth.runtime import lifecycle
    from modules.sextant import history
    from tests.runtime.test_single_run import NORMAL as ORCA_NORMAL, FakeJob, attempt_of, project_run

    made, entry, attempt, job, run, settings, calls = project_run(tmp_path)
    job.end(ORCA_NORMAL)
    first = run.conclude(attempt, job, 'Оптимизация')
    assert first.state == 'finished' and not first.repeated and len(calls) == 1
    recorded = attempt_of(made, entry)
    rows = history.load(settings)
    # Act: the same end delivered by another watcher of the same calculation (taken up again)
    again = FakeJob(job.spec.folder, job.spec.output)
    again._text, again.code, again.state = ORCA_NORMAL, 0, 'finished'
    second = run.conclude(attempt, again, 'Оптимизация')
    # Assert: one record, the orbitals not made again; the result is still there to open
    assert second.repeated and second.state == 'finished' and 'open_result' in second.actions
    assert len(calls) == 1 and 'orbitals' in second.artifacts
    assert attempt_of(made, entry) == recorded and history.load(settings) == rows
    # a different end (the output changed: computed again into the same folder) is recorded, not taken for a repeat
    third = FakeJob(job.spec.folder, job.spec.output)
    time.sleep(0.01)
    third.end(ORCA_NORMAL + '\n')
    assert not run.conclude(attempt, third, 'Оптимизация').repeated
    assert lifecycle.ROW_ENDED == ('done', 'failed', 'stopped', 'skipped')


def test_t11_the_end_of_a_row_delivered_twice_records_and_follows_nothing_again(tmp_path, monkeypatch):
    from azimuth.runtime import lifecycle
    from modules.sextant import binding, history
    from tests.runtime.test_runtime_lifecycle import queue_of, row_job
    from tests.runtime.test_single_run import Settings

    q = queue_of(tmp_path)
    settings = Settings()
    job = row_job(tmp_path)
    q.items[0].folder, q.items[0].state = str(job.spec.folder), 'running'
    text = (Path(__file__).resolve().parents[1] / 'data' / 'orca_cclib' / 'dvb_gopt_orca6.0.out').read_text(
        encoding='utf-8', errors='replace')
    first = lifecycle.row_ended(q, q.items[0], job, text, settings)
    assert first.state == 'done' and not first.repeated and q.items[0].state == 'done'
    energy = q.items[0].energy
    follow = []
    monkeypatch.setattr(binding, 'follow_ups', lambda queue, item: follow.append(item) or False)
    monkeypatch.setattr(runner, 'molden_from_gbw', lambda *a: follow.append(a))
    q.purpose = 'binding'
    # Act: another object for the same row (the watching taken up again) ends it again
    again = row_job(tmp_path)
    second = lifecycle.row_ended(q, q.items[0], again, 'cut output', settings)
    # Assert: what was recorded, nothing written, read or followed again
    assert second.repeated and second.state == 'done' and second.energy == energy
    assert q.items[0].state == 'done' and q.items[0].energy == energy and follow == []
    assert history.load(settings) == []  # this row had no history row; the repeat made none


def test_the_watching_asks_once_for_the_state_the_size_and_the_end(tmp_path):
    """One login per check (on Windows every login is a new connection): the queue, the size of the output and the end
    the job wrote come in one answer."""
    asked = []

    class Combined(Server):
        def text(self, command, timeout=None):
            asked.append(command)
            if 'squeue -h -j' in command:
                self.asked += 1
                state = self.answers.pop(0) if len(self.answers) > 1 else self.answers[0]
                mark = self.root / cluster.EXIT_MARK
                end = mark.read_text(encoding='utf-8').strip() if mark.is_file() else ''
                return f'{state}\n@size {self.out.stat().st_size}\n@exit {end}\n'
            return super().text(command, timeout)

    server = Combined(tmp_path / 'remote' / 'H2O_1', ['RUNNING|0:10|node', 'RUNNING|0:11|node', ''],
                      hooks={2: lambda s: (s.root / cluster.EXIT_MARK).write_text('0\n', encoding='utf-8')})
    server.finish()
    code, seen = ended(watched(tmp_path, server).start())
    assert code == 0 and 'finished' in seen
    # nothing asked apart while it was watched (the end reads the size once more, before the download)
    assert not [c for c in asked if c.startswith('cat ')] and len([c for c in asked if c.startswith('wc -c')]) <= 1
    assert server.asked == 3
    assert remote_job._ssh_detail(SshError('Нет связи с сервером. (kex_exchange_identification: Connection closed)',
                                           'connection')) == 'kex_exchange_identification: Connection closed'


def test_the_watching_on_windows_asks_less_often():
    windows = SimpleNamespace(windows=True)
    spec = SimpleNamespace(folder=Path('.'), output=Path('x.out'), kind='orca')
    profile = SimpleNamespace(folder='~/azimuth')
    assert remote_job.RemoteJob(spec, profile, windows).interval == remote_job.WINDOWS_INTERVAL_S
    assert remote_job.RemoteJob(spec, profile, SimpleNamespace(windows=False)).interval == 10.0
    assert remote_job.RemoteJob(spec, profile, object(), interval=0.01).interval == 0.01
