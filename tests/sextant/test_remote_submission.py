"""A sending to the server that is never doubled (stage C; guide §7, scenarios T06, T07, T08) — against the fake
SLURM server of tests/fake_server.py.

Oracles, independent of the code under test: what the fake sbatch recorded (how many jobs reached the queue and with
which name), the receipt the helper left in the folder on the server, the files of the job folder here, and the
expected results of §13 of the guide: T06 — prepared restored, sending needs a command, no duplicate; T07 — uncertain,
the check restores the only link or stops for clarification (zero and several candidates too); T08 — no automatic
sending again, the accepted job can be found.
"""

import json
import os
import time

import pytest

from azimuth.core import Calculation, read_xyz
from azimuth.runtime import runs
from modules.sextant import cluster, history
from modules.sextant.remote import ServerProfile
from modules.sextant.remote_job import RemoteJob, prepare_remote
from modules.sextant.ssh import Connection
from tests import fake_server

WATER = read_xyz('3\nwater\nO 0 0 0.117\nH 0.757 0 -0.469\nH -0.757 0 -0.469')
PLAN = cluster.Plan(processes=6, maxcore=1500, mem_request=None, physical=48, physical_free=40, queued=False)
PROFILE = ServerProfile('serv3', '192.0.2.103', 22, 'user', '~/azimuth/calculations')


@pytest.fixture
def server(tmp_path, monkeypatch):
    if os.name == 'nt':
        pytest.skip('the fake server is a set of POSIX scripts')
    (tmp_path / 'ctl').mkdir()
    return fake_server.install(tmp_path, monkeypatch)


def connection(tmp_path):
    return Connection(PROFILE, control_dir=tmp_path / 'ctl')


def prepared(tmp_path):
    return prepare_remote(WATER, Calculation(task='Оптимизация', cores=2), (), tmp_path / 'local', PLAN)


def wait(j, timeout=20):
    end = time.monotonic() + timeout
    while j.poll() is None and time.monotonic() < end:
        time.sleep(0.05)
    return j.poll()


def queued(server):
    """The jobs that reached the fake queue: [(number, name)]."""
    folder = server / 'home' / '.queue'
    return sorted((p.stem, p.read_text()) for p in folder.glob('*.name')) if folder.is_dir() else []


def there(server, spec):
    return server / 'home' / 'azimuth' / 'calculations' / spec.folder.name


def history_record(spec):
    return {'folder': str(spec.folder), 'output': str(spec.output), 'kind': 'orca', 'place': 'serv3', 'state': 'running'}


def test_t07_the_answer_lost_after_the_server_accepted(server, tmp_path):
    (server / 'drop_answer').write_text('')  # the helper runs, its answer never comes back
    spec = prepared(tmp_path)
    j = RemoteJob(spec, PROFILE, connection(tmp_path), interval=0.1).start()
    assert wait(j) == 0, j.message
    sent = runs.read(spec.folder)
    assert queued(server) == [('101', sent.name)]  # one job in the queue — the check did not send it again
    assert sent.state == 'accepted' and sent.job_id == j.job_id == '101'
    assert any('found on the server' in line for line in sent.journal)
    assert json.loads((spec.folder / 'job.json').read_text())['job'] == '101'
    assert (there(server, spec) / runs.RECEIPT).read_text().splitlines()[1] == 'job=101'


def test_t06_closed_after_the_intent_before_the_sending(server, tmp_path):
    spec = prepared(tmp_path)  # the intent is on disk; the program «closes» here
    sent = runs.read(spec.folder)
    assert sent.state == 'prepared' and (spec.folder / runs.HELPER).is_file()
    rec = history_record(spec)
    assert history.state_of(rec) == 'prepared' and history.remote_info(rec) is None  # no «Проверить на сервере»
    assert 'prepared' not in history.RESUMABLE
    assert queued(server) == [] and not (server / 'home' / 'azimuth').exists()  # nothing reached the server
    # the explicit command sends the prepared attempt once, with its token
    j = RemoteJob(spec, PROFILE, connection(tmp_path), interval=0.1).start()
    assert wait(j) == 0, j.message
    assert queued(server) == [('101', sent.name)] and runs.read(spec.folder).attempt_id == sent.attempt_id


def lock_without_receipt(server, tmp_path, spec, jobs=1):
    """The window of §7: sbatch accepted (jobs times), the helper was cut before its receipt."""
    c = connection(tmp_path)
    c.upload(spec.folder, PROFILE.folder)
    sub = runs.moved(runs.read(spec.folder), 'submitting', server='serv3', folder=f'{PROFILE.folder}/{spec.folder.name}')
    runs.write(spec.folder, sub)
    folder = there(server, spec)
    (folder / runs.LOCK).mkdir()
    for _ in range(jobs):
        c.run(f'cd ~/azimuth/calculations/{spec.folder.name} && sbatch -J {sub.name} job.sh', timeout=30)
    return sub


def resumed(spec, tmp_path):
    info = history.remote_info(history_record(spec))
    assert info is not None and info['job'] is None and info['folder'].endswith(spec.folder.name)
    return RemoteJob.resume(spec.folder, spec.output, PROFILE, connection(tmp_path), info, interval=0.1).start()


def test_t07_one_job_of_the_token_restores_the_link(server, tmp_path):
    spec = prepared(tmp_path)
    sub = lock_without_receipt(server, tmp_path, spec)
    (server / 'no_sacct').write_text('')  # only squeue knows it
    assert history.state_of(history_record(spec)) == 'uncertain'
    j = resumed(spec, tmp_path)
    assert wait(j) == 0, j.message
    assert queued(server) == [('101', sub.name)] and j.job_id == '101'
    assert runs.read(spec.folder).state == 'accepted'


def test_t07_several_jobs_of_the_token_stop_for_clarification(server, tmp_path):
    spec = prepared(tmp_path)
    lock_without_receipt(server, tmp_path, spec, jobs=2)
    j = resumed(spec, tmp_path)
    assert wait(j) == 1 and j.state == 'uncertain'
    assert '101' in j.message and '102' in j.message and 'ничего не отправлено' in j.message
    assert len(queued(server)) == 2  # nothing more
    record = runs.read(spec.folder)
    assert record.state == 'uncertain' and record.job_id == '' and any('101, 102' in n for n in record.journal)
    assert history.state_of(dict(history_record(spec), state='uncertain')) == 'uncertain'


def test_t07_no_job_found_proves_nothing(server, tmp_path, monkeypatch):
    monkeypatch.setenv('FAKE_ORCA_STEPS', '1')
    spec = prepared(tmp_path)
    sub = lock_without_receipt(server, tmp_path, spec)
    for pid in (server / 'home' / '.queue').glob('*.pid'):
        pid.unlink()  # gone from squeue
    (server / 'no_sacct').write_text('')  # and no accounting to ask
    j = resumed(spec, tmp_path)
    assert wait(j) == 1 and j.state == 'uncertain' and 'Повторно он не отправлен' in j.message
    assert queued(server) == [('101', sub.name)] and runs.read(spec.folder).state == 'uncertain'
    (server / 'no_sacct').unlink()  # the accounting answers later: the same check settles it
    j = resumed(spec, tmp_path)
    wait(j)
    record = runs.read(spec.folder)
    assert record.state == 'accepted' and record.job_id == '101' and 'settled' in record.journal[-1]
    assert queued(server) == [('101', sub.name)]


def test_no_lock_means_the_helper_never_ran(server, tmp_path):
    spec = prepared(tmp_path)
    c = connection(tmp_path)
    c.upload(spec.folder, PROFILE.folder)
    runs.write(spec.folder, runs.moved(runs.read(spec.folder), 'submitting', server='serv3',
                                       folder=f'{PROFILE.folder}/{spec.folder.name}'))
    j = resumed(spec, tmp_path)
    assert wait(j) == 1 and j.state == 'failed' and 'не получал' in j.message
    assert runs.read(spec.folder).state == 'rejected' and queued(server) == []


def test_t08_a_full_disk_after_the_acceptance(server, tmp_path, monkeypatch):
    (server / 'drop_answer').write_text('')
    write, job_json = runs.write, RemoteJob._write_json

    def full_after_acceptance(folder, sub):
        if sub.state == 'accepted':
            raise OSError(28, 'No space left on device')
        return write(folder, sub)

    def no_job_json(self):
        raise OSError(28, 'No space left on device')

    monkeypatch.setattr(runs, 'write', full_after_acceptance)
    monkeypatch.setattr(RemoteJob, '_write_json', no_job_json)
    spec = prepared(tmp_path)
    j = RemoteJob(spec, PROFILE, connection(tmp_path), interval=0.1).start()
    assert wait(j) == 0, j.message  # watched to its end all the same
    assert j.job_id == '101' and '101' in j.local_warning
    assert len(queued(server)) == 1
    monkeypatch.setattr(runs, 'write', write)  # the disk has room again (not undo(): the fake server stays)
    monkeypatch.setattr(RemoteJob, '_write_json', job_json)
    # «restart»: the record here stayed «submitting», job.json is missing — the receipt on the server gives the number
    assert runs.read(spec.folder).state == 'submitting' and not (spec.folder / 'job.json').exists()
    j = resumed(spec, tmp_path)
    wait(j)
    assert runs.read(spec.folder).state == 'accepted' and runs.read(spec.folder).job_id == '101'
    assert json.loads((spec.folder / 'job.json').read_text())['job'] == '101'
    assert len(queued(server)) == 1


def test_an_accepted_sending_is_not_sent_again(server, tmp_path):
    spec = prepared(tmp_path)
    j = RemoteJob(spec, PROFILE, connection(tmp_path), interval=0.1).start()
    assert wait(j) == 0
    again = RemoteJob(spec, PROFILE, connection(tmp_path), interval=0.1).start()  # the same folder started once more
    wait(again)
    assert len(queued(server)) == 1 and again.job_id == '101'


# -- a queue sent as one job — an ExecutionGroup ------------------------------------------------
AMMONIA = read_xyz('4\nammonia\nN 0 0 0.1\nH 0.94 0 -0.27\nH -0.47 0.81 -0.27\nH -0.47 -0.81 -0.27')


def queue_specs(tmp_path, molecules=(WATER, AMMONIA)):
    root = tmp_path / 'local' / 'queue'
    return [prepare_remote(m, Calculation(task='Оптимизация', cores=2), (), root, PLAN) for m in molecules]


def test_the_group_has_a_manifest_and_markers_name_their_attempts(server, tmp_path, monkeypatch):
    import hashlib

    from modules.sextant.remote_job import send_batch

    monkeypatch.setenv('AZ_POLL', '0.1')
    specs = queue_specs(tmp_path)
    job_id = send_batch(specs, PROFILE, connection(tmp_path), PLAN, '', 'az-queue')
    group_dir = specs[0].folder.parent / 'queue-batch'
    manifest = runs.read_group(group_dir)
    attempts = [runs.read(s.folder).attempt_id for s in specs]
    assert [m['attempt'] for m in manifest['members']] == attempts and len(set(attempts)) == 2
    for member, spec in zip(manifest['members'], specs):
        assert member['folder'] == spec.folder.name
        assert member['sha256'] == hashlib.sha256((spec.folder / f'{member["base"]}.inp').read_bytes()).hexdigest()
    group = runs.read(group_dir)
    assert group.state == 'accepted' and group.job_id == job_id and group.attempt_id == manifest['group_id']
    assert len(queued(server)) == 1
    jobs = [RemoteJob.resume(s.folder, s.output, PROFILE, connection(tmp_path),
                             json.loads((s.folder / 'job.json').read_text()), interval=0.1).start() for s in specs]
    assert [wait(j, 40) for j in jobs] == [0, 0]
    for spec, attempt in zip(specs, attempts):
        code, mine = (there(server, spec) / cluster.FINISHED).read_text().split()
        assert code == '0' and mine == attempt
        assert (there(server, spec) / cluster.STARTED).read_text().split()[1] == attempt
    with pytest.raises(FileExistsError):  # the composition of a sent group is not rewritten
        runs.write_group(group_dir, 'x', [])


def test_t12_a_marker_of_another_attempt_is_not_this_one(server, tmp_path, monkeypatch):
    from modules.sextant.remote_job import send_batch

    monkeypatch.setenv('AZ_POLL', '0.1')
    monkeypatch.setenv('FAKE_ORCA_DELAY', '1.0')
    specs = queue_specs(tmp_path)
    c = connection(tmp_path)
    job_id = send_batch(specs, PROFILE, c, PLAN, '', 'az-queue')
    c.run(f'scancel {job_id}', timeout=30)  # the shared job ended before the second calculation
    (there(server, specs[1]) / cluster.FINISHED).write_text('0 ' + '0' * 32 + '\n')  # left by another attempt
    info = json.loads((specs[1].folder / 'job.json').read_text())
    late = RemoteJob.resume(specs[1].folder, specs[1].output, PROFILE, c, info, interval=0.1).start()
    assert wait(late, 20) == 1 and late.state == 'failed' and 'раньше' in late.message  # not «finished»


def test_t07_the_answer_to_a_queue_lost_and_the_server_gone(server, tmp_path, monkeypatch):
    from modules.sextant.remote_job import SubmissionUncertain, send_batch

    monkeypatch.setenv('AZ_POLL', '0.1')
    (server / 'drop_answer').write_text('offline')  # accepted, the answer lost, then no server at all
    specs = queue_specs(tmp_path)
    with pytest.raises(SubmissionUncertain, match='Повторно она не'):
        send_batch(specs, PROFILE, connection(tmp_path), PLAN, '', 'az-queue')
    assert len(queued(server)) == 1  # it is there; nothing was sent again
    group_dir = specs[0].folder.parent / 'queue-batch'
    assert runs.read(group_dir).state == 'uncertain'
    infos = [json.loads((s.folder / 'job.json').read_text()) for s in specs]
    assert all(i['job'] is None and i['batch'] and i['group'] == str(group_dir) for i in infos)
    (server / 'offline').unlink()  # the connection is back: the watching settles the group, once
    first = RemoteJob.resume(specs[0].folder, specs[0].output, PROFILE, connection(tmp_path), infos[0], interval=0.1)
    first.start()
    assert wait(first, 40) == 0, first.message
    settled = runs.read(group_dir)
    assert settled.state == 'accepted' and settled.job_id == first.job_id and 'settled' in settled.journal[-1]
    log = (server / 'ssh.log').read_text().count('az-receipt')
    second = RemoteJob.resume(specs[1].folder, specs[1].output, PROFILE, connection(tmp_path), infos[1], interval=0.1)
    second.start()
    assert wait(second, 40) == 0 and second.job_id == first.job_id
    assert (server / 'ssh.log').read_text().count('az-receipt') == log  # the record of the group here was enough
    assert len(queued(server)) == 1


def test_a_queue_whose_answer_was_lost_is_found_by_its_receipt(server, tmp_path):
    from modules.sextant.remote_job import send_batch

    (server / 'drop_answer').write_text('')
    specs = queue_specs(tmp_path)
    job_id = send_batch(specs, PROFILE, connection(tmp_path), PLAN, '', 'az-queue')
    assert job_id == '101' and len(queued(server)) == 1
    assert all(json.loads((s.folder / 'job.json').read_text())['job'] == '101' for s in specs)
    again = send_batch(specs, PROFILE, connection(tmp_path), PLAN, '', 'az-queue')  # sent «again» from that folder
    assert again == '101' and len(queued(server)) == 1


def test_the_end_by_an_exception_keeps_its_category(server, tmp_path):
    # what kind of failure it was (azimuth/runtime/errors.py) — the login refused: an outside action may be
    # tried again (nothing ran there)
    (server / 'password').write_text('secret')
    j = RemoteJob(prepared(tmp_path), PROFILE, connection(tmp_path), interval=0.1).start()
    assert wait(j) == 1 and j.state == 'failed'
    assert j.failure is not None and j.failure.name == 'refused' and j.failure.action == 'ask'
    assert queued(server) == []


def test_the_message_of_a_failure_says_what_to_do(server, tmp_path):
    (server / 'password').write_text('secret')
    j = RemoteJob(prepared(tmp_path), PROFILE, connection(tmp_path), interval=0.1).start()
    assert wait(j) == 1 and 'проверьте логин, пароль или ключ сервера' in j.message


def test_the_files_for_the_server_have_unix_line_ends():
    # Windows of the owner (2026-11-24): job.sh, the inputs and batch.sh were written with \r\n — sbatch refused «DOS
    # line breaks», bash read «cd …\r». Every file of a job folder for the server is written with newline='\n' (the
    # oracle: the source, since \r\n is written only by a Windows Python)
    import ast
    from pathlib import Path

    for rel in ('modules/sextant/remote_job.py', 'modules/compass/actions/qe_run.py',
                'modules/sextant/server_browser_files.py'):
        tree = ast.parse((Path(__file__).parents[2] / rel).read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, 'attr', '') == 'write_text':
                newline = [k for k in node.keywords if k.arg == 'newline']
                assert newline and newline[0].value.value == '\n', f'{rel}:{node.lineno}'


def test_stop_ends_an_upload_at_once(tmp_path):
    # «Остановить» during «Отправка на сервер…» (the owner, 2026-11-24): the upload went on and the job was queued.
    # ssh.abort_on — a call of this thread ends when the event is set: the program is killed, SshError 'stopped'
    import sys
    import threading
    import time

    from modules.sextant import ssh
    from modules.sextant.remote import ServerProfile

    connection = ssh.Connection(ServerProfile('lab', 'host.invalid', 22, 'me'))
    stop = threading.Event()
    threading.Timer(0.3, stop.set).start()
    ssh.abort_on(stop)
    started = time.monotonic()
    try:
        with pytest.raises(ssh.SshError) as caught:
            connection._call([sys.executable, '-c', 'import time; time.sleep(30)'], 60)
    finally:
        ssh.abort_on(None)
    assert caught.value.kind == 'stopped' and time.monotonic() - started < 5
    done = connection._call([sys.executable, '-c', 'print("ok")'], 30)  # without the event — as before
    assert done.code == 0 and b'ok' in done.out
