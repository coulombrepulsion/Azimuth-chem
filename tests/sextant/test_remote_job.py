"""A calculation on a SLURM server (modules/sextant/remote_job.py) against a fake server on this computer.

Oracles, independent of the code under test: the files the fake sbatch and scancel record (what reached the
server), the output the fake ORCA writes compared with the local copy byte for byte, the interface of runner.Job
(the window uses only it), and the rule of the module header: the end is the job leaving the queue, success is
«ORCA TERMINATED NORMALLY» in the output.
"""

import json
import os
from pathlib import Path
import re
import time

import pytest

from modules.sextant import cluster, runner
from modules.sextant.remote import ServerProfile
from modules.sextant.remote_job import RemoteJob, prepare_remote, submit, wanted
from modules.sextant.ssh import Connection
from azimuth.core import Calculation, read_xyz
from tests import fake_server

WATER = read_xyz('3\nwater\nO 0 0 0.117\nH 0.757 0 -0.469\nH -0.757 0 -0.469')
PLAN = cluster.Plan(processes=6, maxcore=1500, mem_request=None, physical=48, physical_free=40, queued=False)


@pytest.fixture
def server(tmp_path, monkeypatch):
    if os.name == 'nt':  # the Windows run of 2026-10-29 — no sh to run them
        pytest.skip('the fake server is a set of POSIX scripts')
    return fake_server.install(tmp_path, monkeypatch)


def job(tmp_path, interval=0.1, text=None):
    (tmp_path / 'ctl').mkdir(exist_ok=True)
    spec = prepare_remote(WATER, Calculation(task='Оптимизация', cores=2), (), tmp_path / 'local', PLAN, text=text)
    profile = ServerProfile('serv3', '192.0.2.103', 22, 'user', '~/azimuth/calculations')
    return RemoteJob(spec, profile, Connection(profile, control_dir=tmp_path / 'ctl'), interval=interval)


def sbatch_calls(server):
    """What sbatch was asked, without the options of the helper of 0.107.4 (--parsable, -J <name of the token>)."""
    path = server / 'home' / '.queue' / 'args'
    return [re.sub(r'^--parsable -J az-\S+ ', '', line) for line in path.read_text().splitlines()]


def wait(j, timeout=20):
    end = time.monotonic() + timeout
    while j.poll() is None and time.monotonic() < end:
        time.sleep(0.05)
    return j.poll()


def test_the_input_carries_the_plan(tmp_path):
    spec = prepare_remote(WATER, Calculation(cores=2, memory_mb=4000), (), tmp_path, PLAN, 'module add orca-6.1.1')
    text = (spec.folder / 'H2O_B3LYP_def2-SVP.inp').read_text()
    assert '%pal nprocs 6 end' in text and '%maxcore 1500' in text
    script = (spec.folder / 'job.sh').read_text()
    assert '#SBATCH -n 6' in script and 'module add orca-6.1.1' in script
    assert spec.output == spec.folder / 'H2O_B3LYP_def2-SVP.out' and spec.output.read_bytes() == b''
    edited = prepare_remote(WATER, Calculation(), (), tmp_path, PLAN, text='! HF STO-3G\n%pal nprocs 2 end\n* xyz 0 1\nHe 0 0 0\n*')
    assert '%pal nprocs 6 end' in (edited.folder / 'H2O_B3LYP_def2-SVP.inp').read_text()  # the hand-edited file follows the plan
    with pytest.raises(ValueError):
        prepare_remote(WATER, Calculation(), (), tmp_path, PLAN, text='   ')


def test_a_calculation_from_sending_to_the_result(server, tmp_path):
    j = job(tmp_path).start()
    assert j.running and j.poll() is None and j.state in ('new', 'sending', 'queued', 'running')
    assert wait(j) == 0, j.message
    assert j.state == 'finished' and not j.running and j.elapsed() > 0
    there = server / 'home' / 'azimuth' / 'calculations' / j.spec.folder.name
    assert (there / 'H2O_B3LYP_def2-SVP.out').read_bytes() == j.spec.output.read_bytes()  # the local copy is the output
    text = j.text()
    assert runner.finished_normally('orca', text, j.code)
    assert 'PAL: %pal nprocs 6 end' in text  # what ORCA read on the server
    cycles, energy = runner.progress('orca', text, j.spec.folder)
    assert cycles == 4 and energy == pytest.approx(-76.04)
    got = {p.name for p in j.spec.folder.iterdir()}
    assert {'H2O_B3LYP_def2-SVP.gbw', 'H2O_B3LYP_def2-SVP_trj.xyz', 'H2O_B3LYP_def2-SVP.molden.input', 'job.json'} <= got
    assert 'H2O_B3LYP_def2-SVP.tmp.0' not in got  # scratch files are not downloaded
    assert not (there / 'H2O_B3LYP_def2-SVP.tmp.0').exists()  # and removed on the server at the end
    assert (there / 'H2O_B3LYP_def2-SVP.gbw').exists()
    record = json.loads((j.spec.folder / 'job.json').read_text())
    assert record['job'] == j.job_id == '101' and record['folder'] == f'~/azimuth/calculations/{j.spec.folder.name}'
    # one sbatch, through the helper of the token: machine-readable answer, the job named by the token
    sent = json.loads((j.spec.folder / 'submission.json').read_text())
    assert (server / 'home' / '.queue' / 'args').read_text().splitlines() == [f'--parsable -J {sent["name"]} job.sh']
    assert sent['state'] == 'accepted' and sent['job_id'] == '101' and sent['token'][:12] in sent['name']
    assert (there / '.az-receipt').read_text().splitlines()[:2] == [f'token={sent["token"]}', 'job=101']


def test_output_grows_while_it_runs(server, tmp_path, monkeypatch):
    monkeypatch.setenv('FAKE_ORCA_STEPS', '12')
    monkeypatch.setenv('FAKE_ORCA_DELAY', '0.25')
    j = job(tmp_path).start()
    seen = []
    end = time.monotonic() + 20
    while j.poll() is None and time.monotonic() < end:
        seen.append(runner.progress('orca', j.text(), j.spec.folder)[0])
        time.sleep(0.1)
    assert j.code == 0
    middle = [c for c in seen if c and 0 < c < 12]
    assert middle and middle == sorted(middle)  # the window saw the cycles come one after another


def test_refused_by_sbatch(server, tmp_path):
    (server / 'sbatch_fail').write_text('')
    j = job(tmp_path).start()
    assert wait(j) == 1 and j.state == 'failed'
    assert 'не поставил расчёт в очередь' in j.message and 'Requested node configuration' in j.message
    assert j.job_id is None


def test_orca_error(server, tmp_path):
    (server / 'orca_fail').write_text('')
    j = job(tmp_path).start()
    assert wait(j) == 1 and j.state == 'failed' and not runner.finished_normally('orca', j.text(), j.code)


def test_stop_cancels_the_job(server, tmp_path, monkeypatch):
    monkeypatch.setenv('FAKE_ORCA_STEPS', '200')
    j = job(tmp_path).start()
    end = time.monotonic() + 10
    while j.job_id is None and time.monotonic() < end:
        time.sleep(0.05)
    j.stop()
    assert wait(j) == -15 and j.state == 'stopped' and j.stopped
    assert (server / 'scancel.log').read_text().split() == [j.job_id]
    j.stop()  # a finished job: nothing more


def test_a_lost_connection_does_not_end_the_job(server, tmp_path, monkeypatch):
    monkeypatch.setenv('FAKE_ORCA_STEPS', '10')
    monkeypatch.setenv('FAKE_ORCA_DELAY', '0.2')
    monkeypatch.setattr('modules.sextant.remote_job.RETRY', (0.3, 0.3))
    j = job(tmp_path).start()
    end = time.monotonic() + 10
    while j.state != 'running' and time.monotonic() < end:
        time.sleep(0.05)
    (server / 'offline').write_text('')
    end = time.monotonic() + 5
    while j.state != 'offline' and time.monotonic() < end:
        time.sleep(0.05)
    assert j.state == 'offline' and j.poll() is None and 'Нет связи' in j.message  # it goes on there
    (server / 'offline').unlink()
    assert wait(j) == 0 and j.state == 'finished'
    there = server / 'home' / 'azimuth' / 'calculations' / j.spec.folder.name
    assert (there / 'H2O_B3LYP_def2-SVP.out').read_bytes() == j.spec.output.read_bytes()


def test_queued_state(server, tmp_path, monkeypatch):
    monkeypatch.setenv('FAKE_ORCA_STEPS', '30')
    queue = server / 'home' / '.queue'
    queue.mkdir(parents=True, exist_ok=True)
    (queue / '101.pending').write_text('')
    j = job(tmp_path).start()
    end = time.monotonic() + 10
    while j.state != 'queued' and time.monotonic() < end:
        time.sleep(0.05)
    assert j.state == 'queued' and 'В очереди' in j.message
    (queue / '101.pending').unlink()
    j.stop()
    wait(j)


def test_what_is_downloaded():
    names = ['H2O_B3LYP_def2-SVP.out', 'input.gbw', 'input.tmp', 'input.tmp.0', 'input_trj.xyz', 'input.hess', 'slurm-101.out',
             'job.sh', 'H2O_B3LYP_def2-SVP.inp', 'input.densities', 'core.1234', 'input.molden.input', 'input.engrad']
    assert wanted(names) == ['H2O_B3LYP_def2-SVP.out', 'input.gbw', 'input_trj.xyz', 'input.hess', 'slurm-101.out',
                             'input.molden.input', 'input.engrad']
    # the phonons of Quantum ESPRESSO: the modes of dynmat.x, the branches and the DOS of matdyn.x come back; the
    # force constants and the dynamical matrices (large, read by nothing here) stay
    phonons = ['pw.out', 'azimuth.mold', 'azimuth.freq', 'azimuth.freq.gp', 'azimuth.phdos', 'azimuth.fc', 'azimuth.dyn1',
               'azimuth.dos', 'scf.in']
    assert wanted(phonons) == ['pw.out', 'azimuth.mold', 'azimuth.freq', 'azimuth.phdos', 'azimuth.dos']


def test_resumed_after_the_program_was_closed(server, tmp_path):
    # «История расчётов → Проверить»: the watching of a calculation sent before is taken up from job.json —
    # nothing is sent again; the calculation already left the queue, so the output and the results come down
    j = job(tmp_path).start()
    assert wait(j) == 0
    folder, output = j.spec.folder, j.spec.output
    for item in folder.iterdir():  # as if the program had been closed while it ran: only what was there at sending
        if item.name not in ('job.json', output.name) and item.suffix != '.inp' and item.name != 'job.sh':
            item.unlink()
    output.write_bytes(b'')
    sent = (server / 'home' / '.queue' / 'args').stat().st_mtime
    info = json.loads((folder / 'job.json').read_text())
    profile = ServerProfile('serv3', '192.0.2.103', 22, 'user', '~/azimuth/calculations')
    again = RemoteJob.resume(folder, output, profile, Connection(profile, control_dir=tmp_path / 'ctl'), info,
                             interval=0.1).start()
    assert again.job_id == '101' and wait(again) == 0 and again.state == 'finished'
    assert runner.finished_normally('orca', again.text(), again.code)
    assert (folder / 'H2O_B3LYP_def2-SVP.gbw').exists()
    assert (server / 'home' / '.queue' / 'args').stat().st_mtime == sent  # no new sbatch


def test_a_mopac_calculation_on_the_server(server, tmp_path, monkeypatch):
    """Job.sh of MOPAC — one task with
    the threads (-n 1 -c N, OMP_NUM_THREADS), «mopac <base>.mop»; THREADS=N in the input; success is «JOB ENDED
    NORMALLY» of the output MOPAC wrote (a recorded MOPAC 23.2.5 output), the .aux comes back with it."""
    from pathlib import Path

    data = Path(__file__).parents[1] / 'data' / 'mopac'
    monkeypatch.setenv('FAKE_MOPAC_OUTPUT', str(data / 'ch2o_am1_1scf.out'))
    (tmp_path / 'ctl').mkdir(exist_ok=True)
    calc = Calculation(task='Энергия', method='AM1', cores=2)
    spec = prepare_remote(WATER, calc, (), tmp_path / 'local', PLAN, kind='mopac')
    main = next(spec.folder.glob('*.mop'))
    assert main.read_text().split('\n')[0].split()[-1] == 'THREADS=6' and spec.kind == 'mopac'
    script = (spec.folder / 'job.sh').read_text()
    assert '#SBATCH -n 1' in script and '#SBATCH -c 6' in script and 'export OMP_NUM_THREADS=6' in script
    assert f'"$MOPAC" {main.name} > {main.stem}.stdout' in script and 'orca' not in script.lower()
    assert spec.output == spec.folder / (main.stem + '.out')
    profile = ServerProfile('serv3', '192.0.2.103', 22, 'user', '~/azimuth/calculations')
    j = RemoteJob(spec, profile, Connection(profile, control_dir=tmp_path / 'ctl'), interval=0.1).start()
    assert wait(j) == 0, j.message
    assert j.state == 'finished' and runner.finished_normally('mopac', j.text(), 0)
    assert j.text() == (data / 'ch2o_am1_1scf.out').read_text()
    assert (spec.folder / (main.stem + '.aux')).is_file()  # what Spectrum reads
    log = (server / 'mopac.log').read_text()
    assert 'THREADS=6' in log and 'OMP_NUM_THREADS=6' in log
    assert json.loads((spec.folder / 'job.json').read_text())['program'] == 'mopac'
    (server / 'mopac_fail').write_text('')
    failed = prepare_remote(WATER, calc, (), tmp_path / 'local2', PLAN, kind='mopac')
    j = RemoteJob(failed, profile, Connection(profile, control_dir=tmp_path / 'ctl'), interval=0.1).start()
    wait(j)
    assert j.state == 'failed' and 'MOPAC' in j.message
    with pytest.raises(ValueError):
        prepare_remote(WATER, calc, (), tmp_path / 'local3', PLAN, kind='gaussian')


def test_a_failed_local_note_does_not_stop_the_watching(server, tmp_path, monkeypatch):
    # sbatch answered, writing job.json failed (a full disk) — the job was «failed» with code 1 and no longer watched,
    # though the server ran it. Now: the number is said, the job is watched to its end, it is not sent twice
    def full_disk(self):
        raise OSError(28, 'No space left on device')

    monkeypatch.setattr(RemoteJob, '_write_json', full_disk)
    j = job(tmp_path).start()
    seen = set()
    end = time.monotonic() + 20
    while j.poll() is None and time.monotonic() < end:
        seen.add(j.message)
        time.sleep(0.05)
    assert j.poll() == 0 and j.state == 'finished', j.message
    assert j.job_id == '101' and '101' in j.local_warning and 'job.json' in j.local_warning
    assert j.local_warning in j.message  # stays with every later message
    assert sbatch_calls(server) == ['job.sh']  # one sbatch
    assert runner.finished_normally('orca', j.text(), j.code)
    assert not (j.spec.folder / 'job.json').exists() and not (j.spec.folder / 'job.json.tmp').exists()


def test_job_json_is_replaced_whole(tmp_path):
    # a temporary file moved over job.json
    j = job(tmp_path)
    j.job_id = '7'
    j._write_json()
    assert json.loads((j.spec.folder / 'job.json').read_text())['job'] == '7'
    assert not (j.spec.folder / 'job.json.tmp').exists()


def test_the_rest_of_a_queue_sent_before_the_exit(server, tmp_path):
    # sent and queued without watching, each after the one before (afterany); the watching taken up later from
    # job.json, as after a restart
    (tmp_path / 'ctl').mkdir()
    profile = ServerProfile('serv3', '192.0.2.103', 22, 'user', '~/azimuth/calculations')
    connection = Connection(profile, control_dir=tmp_path / 'ctl')
    specs = [prepare_remote(WATER, Calculation(title=f'{k:02d}'), (), tmp_path / 'queue', PLAN) for k in (1, 2)]
    first = submit(specs[0], profile, connection)
    second = submit(specs[1], profile, connection, after=first)
    assert (first, second) == ('101', '102')
    assert sbatch_calls(server) == ['job.sh', '--dependency=afterany:101 job.sh']
    for spec, number in zip(specs, (first, second)):
        info = json.loads((spec.folder / 'job.json').read_text())
        assert info['job'] == number and info['program'] == 'orca'
        j = RemoteJob.resume(spec.folder, spec.output, profile, connection, info, interval=0.1).start()
        assert wait(j) == 0, j.message
        assert runner.finished_normally('orca', j.text(), j.code)
    (server / 'sbatch_dependency_fail').write_text('')  # SLURM no longer knows the job waited for: queued without it
    third = prepare_remote(WATER, Calculation(title='03'), (), tmp_path / 'queue', PLAN)
    assert submit(third, profile, connection, after='99') == '103'
    assert sbatch_calls(server)[-1] == 'job.sh'
    (server / 'sbatch_fail').write_text('')
    with pytest.raises(ValueError, match='не поставил'):
        submit(prepare_remote(WATER, Calculation(title='04'), (), tmp_path / 'queue', PLAN), profile, connection)


class Flaky:
    """A connection that loses the server for the first calls of a kind (the user's queue: jobs 3 and 26 were
    «failed» after MOPAC ended normally, the download at the end met a lost moment of the connection)."""

    def __init__(self, fail_downloads=0, fail_uploads=0, kind='connection'):
        from modules.sextant.ssh import SshError

        self.error, self.kind = SshError, kind
        self.downloads, self.uploads, self.calls = fail_downloads, fail_uploads, []

    def text(self, command, timeout=30):
        self.calls.append(command)
        return '0' if command.startswith('wc') else 'water.out water.aux'

    def run(self, command, timeout=60):
        from modules.sextant.ssh import Result

        self.calls.append(command)
        return Result(0, b'Submitted batch job 7\n', '')

    def download(self, names, remote, local):
        self.calls.append(('download', tuple(names)))
        if self.downloads:
            self.downloads -= 1
            raise self.error('ssh: connect to host 192.0.2.103 port 22: Connection timed out', self.kind)
        for name in names:  # a download that succeeded leaves its files (verified, then moved): «the
            # server's» copy is the one the job made while it ran (the folder above the transfer folder), else empty
            here = Path(local).parent / name
            (Path(local) / name).write_bytes(here.read_bytes() if here.is_file() else b'')

    def upload(self, folder, parent):
        self.calls.append(('upload', parent))
        if self.uploads:
            self.uploads -= 1
            raise self.error('ssh: connect to host 192.0.2.103 port 22: Connection timed out', self.kind)


def flaky_job(tmp_path, connection, text):
    spec = prepare_remote(WATER, Calculation(), (), tmp_path / 'local', PLAN)
    spec.output.write_text(text, encoding='utf-8')
    profile = ServerProfile('serv3', '192.0.2.103', 22, 'user', '~/azimuth/calculations')
    said = []
    j = RemoteJob(spec, profile, connection)
    j.job_id = '7'
    original = j._set
    j._set = lambda state, message='': (said.append(message), original(state, message))
    return j, said


@pytest.fixture
def quick_retries(monkeypatch):
    from modules.sextant import remote_job

    monkeypatch.setattr(remote_job, 'RETRY', (0.01, 0.02, 0.03))


def retries(said):
    return [m for m in said if m.startswith('Нет связи с сервером · повтор')]


def test_a_lost_moment_at_the_download_does_not_fail_a_finished_job(tmp_path, quick_retries):
    connection = Flaky(fail_downloads=2)
    j, slept = flaky_job(tmp_path, connection, '... ****ORCA TERMINATED NORMALLY****')
    j._finish()
    assert j.code == 0 and j.state == 'finished' and 'Не все файлы' not in j.message
    downloads = [c for c in connection.calls if isinstance(c, tuple)]
    assert len(downloads) == 4 and downloads[0] == downloads[2] and downloads[3][1] == (j.spec.output.name,)
    assert len(retries(slept)) == 2  # the third try took them
    # the server away for good: the output copied while it ran ended normally — finished, the rest said
    j, _ = flaky_job(tmp_path, Flaky(fail_downloads=100), '... ****ORCA TERMINATED NORMALLY****')
    j._finish()
    assert j.code == 0 and 'Не все файлы скачались' in j.message and '~/azimuth/calculations/' in j.message
    # an output without its end and no download: still a failure (from the error of the connection)
    j, _ = flaky_job(tmp_path, Flaky(fail_downloads=100), 'cut off')
    with pytest.raises(Exception):
        j._finish()
    # an error that is not the connection (a file not found) is not tried again
    connection = Flaky(fail_downloads=1, kind='command')
    j, slept = flaky_job(tmp_path, connection, '... ****ORCA TERMINATED NORMALLY****')
    j._finish()
    assert not retries(slept) and 'Не все файлы скачались' in j.message


def test_a_lost_moment_while_sending_is_tried_again(tmp_path, quick_retries):
    connection = Flaky(fail_uploads=1)
    j, slept = flaky_job(tmp_path, connection, '')
    j.job_id = None
    j._send()
    assert j.job_id == '7' and j.state == 'queued' and len(retries(slept)) == 1
    assert [c for c in connection.calls if isinstance(c, tuple)] == [('upload', '~/azimuth/calculations')] * 2


def test_a_queue_sent_at_once_runs_in_one_job(server, tmp_path, monkeypatch):
    """The calculations of a queue uploaded together and run one after
    another by one sbatch of batch.sh; each is watched from its job.json (resume → BatchItemJob) — the markers of its
    folder tell when it starts and ends; «Пропустить» (stop) leaves .az-skip and the script goes to the next."""
    from modules.sextant.remote_job import BatchItemJob, send_batch

    monkeypatch.setenv('AZ_POLL', '0.1')
    monkeypatch.setenv('FAKE_ORCA_STEPS', '6')
    monkeypatch.setenv('FAKE_ORCA_DELAY', '0.3')
    (tmp_path / 'ctl').mkdir(exist_ok=True)
    ammonia = read_xyz('4\nammonia\nN 0 0 0.1\nH 0.94 0 -0.27\nH -0.47 0.81 -0.27\nH -0.47 -0.81 -0.27')
    methane = read_xyz('5\nmethane\nC 0 0 0\nH 0.63 0.63 0.63\nH -0.63 -0.63 0.63\nH -0.63 0.63 -0.63\nH 0.63 -0.63 -0.63')
    root = tmp_path / 'local' / 'queue'
    specs = [prepare_remote(m, Calculation(task='Оптимизация', cores=2), (), root, PLAN) for m in (WATER, ammonia, methane)]
    profile = ServerProfile('serv3', '192.0.2.103', 22, 'user', '~/azimuth/calculations')
    connection = Connection(profile, control_dir=tmp_path / 'ctl')
    log = server / 'ssh.log'
    before = len(log.read_text().splitlines()) if log.exists() else 0
    job_id = send_batch(specs, profile, connection, PLAN, 'module add orca-6.1.1', 'az-queue')
    # one archive (one scp) and one ssh that unpacks it and runs sbatch — not two calls for every calculation
    assert len(log.read_text().splitlines()) - before == 1
    assert not list((server / 'home').glob('.az-upload-*'))  # the archive removed after unpacking
    assert sbatch_calls(server) == ['batch.sh']  # one sbatch for the three
    script = (root / 'queue-batch' / 'batch.sh').read_text()
    assert script.count('run_one ') == 3 and '#SBATCH -n 6' in script and 'module add orca-6.1.1' in script
    jobs = []
    for spec in specs:
        info = json.loads((spec.folder / 'job.json').read_text())
        assert info['batch'] is True and info['job'] == job_id
        jobs.append(RemoteJob.resume(spec.folder, spec.output, profile, connection, info, interval=0.1))
    assert all(isinstance(j, BatchItemJob) for j in jobs)
    first = jobs[0].start()
    assert wait(first, 40) == 0 and first.state == 'finished', first.message
    assert runner.finished_normally('orca', first.text(), 0)
    assert (specs[0].folder / 'H2O_B3LYP_def2-SVP.gbw').exists()
    second = jobs[1].start()  # «Пропустить» while it runs
    end = time.monotonic() + 20
    while second.state != 'running' and time.monotonic() < end:
        time.sleep(0.05)
    second.stop()
    assert wait(second, 30) == -15 and second.state == 'stopped'
    third = jobs[2].start()
    assert wait(third, 40) == 0 and runner.finished_normally('orca', third.text(), 0)
    there = server / 'home' / 'azimuth' / 'calculations'
    assert (there / specs[1].folder.name / '.az-finished').exists()
    assert not list(there.glob('*/*.tmp.0'))  # the scratch files removed after each


def test_a_queue_ended_before_its_calculation(server, tmp_path, monkeypatch):
    # the shared job cancelled («Остановить» of the queue) — a calculation that had not started is not «running»
    # for ever: it ends as failed with the reason
    from modules.sextant.remote_job import send_batch

    monkeypatch.setenv('AZ_POLL', '0.1')
    monkeypatch.setenv('FAKE_ORCA_DELAY', '1.0')
    (tmp_path / 'ctl').mkdir(exist_ok=True)
    root = tmp_path / 'local' / 'queue'
    ammonia = read_xyz('4\nammonia\nN 0 0 0.1\nH 0.94 0 -0.27\nH -0.47 0.81 -0.27\nH -0.47 -0.81 -0.27')
    specs = [prepare_remote(m, Calculation(task='Оптимизация', cores=2), (), root, PLAN) for m in (WATER, ammonia)]
    profile = ServerProfile('serv3', '192.0.2.103', 22, 'user', '~/azimuth/calculations')
    connection = Connection(profile, control_dir=tmp_path / 'ctl')
    job_id = send_batch(specs, profile, connection, PLAN, '', 'az-queue')
    connection.run(f'scancel {job_id}', timeout=30)
    info = json.loads((specs[1].folder / 'job.json').read_text())
    late = RemoteJob.resume(specs[1].folder, specs[1].output, profile, connection, info, interval=0.1).start()
    assert wait(late, 20) == 1 and 'раньше' in late.message


def test_a_queue_whose_program_is_not_found_says_why(server, tmp_path, monkeypatch):
    # the job of the queue ends at once with «orca not found in PATH» in its
    # slurm-<номер>.out — that line is now in the message of the calculation, not only «закончилась раньше»
    from modules.sextant.remote_job import send_batch

    monkeypatch.setenv('AZ_POLL', '0.1')
    (tmp_path / 'ctl').mkdir(exist_ok=True)
    root = tmp_path / 'local' / 'queue'
    specs = [prepare_remote(WATER, Calculation(task='Оптимизация', cores=2), (), root, PLAN)]
    profile = ServerProfile('serv3', '192.0.2.103', 22, 'user', '~/azimuth/calculations')
    connection = Connection(profile, control_dir=tmp_path / 'ctl')
    job_id = send_batch(specs, profile, connection, PLAN, 'export PATH=/usr/bin:/bin', 'az-queue')
    info = json.loads((specs[0].folder / 'job.json').read_text())
    job = RemoteJob.resume(specs[0].folder, specs[0].output, profile, connection, info, interval=0.1).start()
    assert wait(job, 20) == 1 and job.state == 'failed'
    assert 'раньше' in job.message and 'orca not found in PATH' in job.message and str(job_id) in job.message


def test_the_watchers_of_a_queue_share_one_look_at_the_group(server, tmp_path, monkeypatch):
    # one command tells squeue and the markers of every calculation of the group; the next calculation, taken up when
    # the one before has ended (here all three ended while the program was «closed»), uses that answer — not three looks
    from modules.sextant import remote_job
    from modules.sextant.remote_job import send_batch

    monkeypatch.setenv('AZ_POLL', '0.1')
    (tmp_path / 'ctl').mkdir(exist_ok=True)
    ammonia = read_xyz('4\nammonia\nN 0 0 0.1\nH 0.94 0 -0.27\nH -0.47 0.81 -0.27\nH -0.47 -0.81 -0.27')
    root = tmp_path / 'local' / 'queue'
    specs = [prepare_remote(m, Calculation(task='Оптимизация', cores=2), (), root, PLAN) for m in (WATER, ammonia, WATER)]
    profile = ServerProfile('serv3', '192.0.2.103', 22, 'user', '~/azimuth/calculations')
    connection = Connection(profile, control_dir=tmp_path / 'ctl')
    send_batch(specs, profile, connection, PLAN, '', 'az-queue')
    there = server / 'home' / 'azimuth' / 'calculations'
    end = time.monotonic() + 30
    while time.monotonic() < end and not all((there / s.folder.name / '.az-finished').exists() for s in specs):
        time.sleep(0.05)
    log = server / 'ssh.log'
    before = len(log.read_text().splitlines())
    for spec in specs:  # one after another, as the queue takes them up
        info = json.loads((spec.folder / 'job.json').read_text())
        job = RemoteJob.resume(spec.folder, spec.output, profile, connection, info, interval=30.0).start()
        assert wait(job, 30) == 0 and job.state == 'finished', job.message
    looks = [line for line in log.read_text().splitlines()[before:] if 'squeue' in line]
    assert len(looks) == 1 and remote_job._GROUP_MARK in looks[0]  # one look for the three
    head, markers = remote_job.parse_group('RUNNING|0:01|n\n' + remote_job._GROUP_MARK + '\na|0 x|17 x|\nb||17 y|1\n')
    assert remote_job.cluster.queue_state(head) == 'RUNNING' and markers == {'a': ('0 x', '17 x', ''), 'b': ('', '17 y', '1')}


def test_quantum_espresso_on_the_server(server, tmp_path):
    # the steps of the density of states of silicon sent as one SLURM job (remote_job.prepare_qe): the fake
    # pw.x and dos.x on the «server» print the real outputs of pw.x 7.6 (tests/data/qe) by the input they get; the
    # pseudopotentials go with the folder, pw.out grows here, azimuth.dos comes back, the wave functions stay out
    import shutil
    import stat
    import sys

    from modules.sextant.remote_job import prepare_qe

    data = Path(__file__).resolve().parents[1] / 'data' / 'qe'
    runs = (data / 'si_dos_pw76.out').read_text(encoding='utf-8').split('Program PWSCF')
    texts = {'scf.in': 'Program PWSCF' + runs[1], 'nscf.in': 'Program PWSCF' + runs[2].split('Program DOS')[0],
             'dos.in': 'Program DOS' + runs[2].split('Program DOS')[1]}
    for name, text in texts.items():
        (tmp_path / (name + '.txt')).write_text(text, encoding='utf-8')
    bin_dir = server / 'bin'
    for tool, extra in (('pw.x', "import os; os.makedirs('out', exist_ok=True)\n"),
                        ('dos.x', f"import shutil; shutil.copy({str(data / 'si_dos_pw76.dos')!r}, 'azimuth.dos')\n")):
        path = bin_dir / tool
        path.write_text(f'#!{sys.executable}\nimport sys\n{extra}'
                        f"name = sys.argv[sys.argv.index('-in') + 1]\n"
                        f"assert open('pseudo/Si.upf').read() == 'upf'\n"
                        f"sys.stdout.write(open({str(tmp_path)!r} + '/' + name + '.txt').read())\n", encoding='utf-8')
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
    folder = tmp_path / 'local' / 'qe-Si-20261111'
    (folder / 'pseudo').mkdir(parents=True)
    (folder / 'pseudo' / 'Si.upf').write_text('upf', encoding='utf-8')
    for name in texts:
        (folder / name).write_text(f'input {name}\n', encoding='utf-8')
    steps = [('scf.in', 'pw.x'), ('nscf.in', 'pw.x'), ('dos.in', 'dos.x')]
    spec = prepare_qe(folder, steps, PLAN, 'module load qe/7.6', 'Si')
    script = (folder / 'job.sh').read_text()
    assert '#SBATCH -n 6' in script and 'module load qe/7.6' in script and 'mpirun -np 6' in script
    assert script.index('-in scf.in') < script.index('-in nscf.in') < script.index('-in dos.in') and 'rm -rf out' in script
    (tmp_path / 'ctl').mkdir()
    profile = ServerProfile('serv3', '192.0.2.103', 22, 'user', '~/azimuth/calculations')
    j = RemoteJob(spec, profile, Connection(profile, control_dir=tmp_path / 'ctl'), interval=0.1).start()
    assert wait(j) == 0, j.message
    text = j.text()
    assert text.count('JOB DONE.') == 3 and runner.finished_normally('qe', text, 0)
    assert (folder / 'azimuth.dos').read_bytes() == (data / 'si_dos_pw76.dos').read_bytes()
    there = server / 'home' / 'azimuth' / 'calculations' / folder.name
    assert not (there / 'out').exists() and (there / 'pseudo' / 'Si.upf').exists()
    shutil.rmtree(folder / 'pseudo')


def test_the_server_finds_quantum_espresso():
    resources = cluster.parse_probe('@progmodule qe/7.2\n@progmodule quantum-espresso/7.4.1\n')
    assert cluster.find_on_server(resources, 'qe') is not None
    assert cluster.suggested_setup(resources, 'qe') == 'module load quantum-espresso/7.4.1'
    assert cluster.find_on_server(cluster.parse_probe('@prog pw.x /opt/qe/bin/pw.x\n'), 'qe') == '/opt/qe/bin/pw.x'
