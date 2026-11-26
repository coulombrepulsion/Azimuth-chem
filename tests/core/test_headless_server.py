"""A calculation sent to a server without the window (azimuth/headless_server.py, Jobs.start_server) against the fake
SLURM server of tests/fake_server.py.

Oracles, independent of the code under test: what the fake ssh, sbatch and scancel recorded (the options of every
login, the job script that reached the queue, the cancelled number), the output of the fake ORCA, the journal file
read as text, and the rules of §2 of the module — the key only, the limits from what the server says is free (the
resources are made here by hand: a node of 48 cores), a time limit always, three at once, only its own calculations.
"""

import json
from pathlib import Path
import os
import time

import pytest

from azimuth import headless, headless_server
from modules.sextant import cluster, remote
from modules.sextant.remote import ServerProfile
from modules.sextant.ssh import Connection
from tests import fake_server


class Store(dict):
    def value(self, key, default=None):
        return self.get(key, default)


def store(**changes):
    profile = ServerProfile('serv3', '192.0.2.103', 22, 'user', '~/azimuth/calculations', **changes)
    return Store({remote.PROFILES_KEY: json.dumps([profile.to_dict()]), remote.CURRENT_KEY: profile.title()})


def node(idle, cpus=48, memory=256_000, available=200_000):
    one = cluster.Node('n1', cpus, memory, memory, cpus - idle, idle, 0, cpus, 'mix')
    return cluster.Resources(cpus, cpus, 1, memory, (one,), 500_000, True, '/opt/orca/orca', available)


@pytest.fixture
def server(tmp_path, monkeypatch):
    if os.name == 'nt':
        pytest.skip('the fake server is a set of POSIX scripts')
    return fake_server.install(tmp_path, monkeypatch)


def opener(tmp_path):
    (tmp_path / 'ctl').mkdir(exist_ok=True)
    return lambda profile: Connection(profile, batch=True, control_dir=tmp_path / 'ctl', key=tmp_path / 'no-key')


def wait(jobs, ident, timeout=30):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        status = jobs.status(ident)
        if status['exit_code'] is not None:
            return status
        time.sleep(0.05)
    return jobs.status(ident)


def test_the_cores_and_the_memory_stay_within_what_is_free():
    # a node of 48 cores: with the new calculation at most 80 % of it is busy (38 cores), those busy now counted —
    # 8 busy leave 30, 28 busy leave 10, 43 busy leave nothing though 5 are free
    assert headless_server.ceiling(node(40)) == (30, 48, 40)
    assert headless_server.ceiling(node(20)) == (10, 48, 20)
    assert headless_server.ceiling(node(5)) == (0, 48, 5)
    assert headless_server.choose(node(40)).processes == headless_server.DEFAULT_CORES == 8
    assert headless_server.choose(node(15)).processes == 5 and headless_server.choose(node(40), cores=24).processes == 24
    plan = headless_server.choose(node(40), cores=4, memory_mb=3000)
    assert (plan.processes, plan.maxcore, plan.mem_request) == (4, 3000, 15000)
    with pytest.raises(ValueError, match='31 asked, at most 30'):
        headless_server.choose(node(40), cores=31)  # refused with the ceiling, not cut silently
    for idle in (0, 5):
        with pytest.raises(ValueError, match='no cores to take'):
            headless_server.choose(node(idle))
    # the request (processes × memory × 1.25) is at most half of the free memory: 8 × 12000 × 1.25 = 120 GB of 200 free
    with pytest.raises(ValueError, match='at most 10000 MB per process'):
        headless_server.choose(node(40), cores=8, memory_mb=12000)
    assert headless_server.choose(node(40), cores=8, memory_mb=10000).mem_request == 100_000


def test_a_time_limit_is_always_written():
    plain, own = ServerProfile('s', 'h', 22, 'u'), ServerProfile('s', 'h', 22, 'u', time_limit='2-00:00:00')
    assert headless_server.time_directive(plain) == ['#SBATCH -t 04:00:00']
    assert headless_server.time_directive(plain, 24) == ['#SBATCH -t 24:00:00']
    assert headless_server.time_directive(own) == [] and '#SBATCH -t 2-00:00:00' in own.directives()
    for hours in (0, 25):
        with pytest.raises(ValueError, match='from 1 to 24'):
            headless_server.time_directive(plain, hours)
    with pytest.raises(ValueError, match='its own time limit'):
        headless_server.time_directive(own, 2)


def test_a_calculation_sent_watched_and_read(server, tmp_path):
    jobs = headless.Jobs()
    sent = jobs.start_server('orca', {'smiles': 'O'}, {'task': 'Оптимизация'}, store(), cores=2, root=tmp_path / 'calc',
                             opener=opener(tmp_path), interval=0.1)
    assert sent['server'] == 'serv3' and sent['cores'] == 2 and sent['memory_mb_per_process'] == 2000
    done = wait(jobs, sent['job'])
    assert done['state'] == 'finished' and done['exit_code'] == 0 and done['slurm_job'] == '101', done
    assert done['result']['normal_exit'] and done['cycles'] == 4
    # what reached the queue: the plan of the call (not the 2 processes and 1000 MB of the settings), a time limit
    there = server / 'home' / 'azimuth' / 'calculations' / os.path.basename(sent['folder'])
    script = (there / 'job.sh').read_text()
    assert '#SBATCH -n 2' in script and '#SBATCH -t 04:00:00' in script
    assert '%maxcore 2000' in next(there.glob('*.inp')).read_text()
    # every login was by the key only: BatchMode, and no program to ask a password
    logins = (server / 'ssh.log').read_text().splitlines()
    assert logins and all('BatchMode=yes' in line for line in logins)
    # the journal: one line of the sending, one of the end
    rows = [json.loads(line) for line in (tmp_path / 'calc' / headless_server.JOURNAL).read_text().splitlines()]
    assert [r['event'] for r in rows] == ['sent', 'ended'] and rows[0]['folder'] == rows[1]['folder'] == sent['folder']
    assert (rows[0]['server'], rows[0]['program'], rows[0]['cores'], rows[0]['time_limit']) == ('serv3', 'orca', 2, '04:00:00')
    assert headless_server.active(tmp_path / 'calc') == [] and jobs.listing()[0]['kind'] == 'server'


def test_a_server_that_wants_a_password_is_refused_and_told_why(server, tmp_path):
    (server / 'password').write_text('secret')  # no key of the program there
    jobs = headless.Jobs()
    with pytest.raises(ValueError, match='did not accept the login by the key') as refused:
        jobs.start_server('orca', {'smiles': 'O'}, None, store(), root=tmp_path / 'calc', opener=opener(tmp_path))
    assert 'Вход без пароля' in str(refused.value)
    assert not (server / 'home' / '.queue' / 'args').exists()  # nothing reached sbatch
    assert not (tmp_path / 'calc' / headless_server.JOURNAL).exists() and jobs.listing() == []
    (server / 'password').unlink()
    (server / 'offline').write_text('')
    with pytest.raises(ValueError, match='does not answer, and its profile has no VPN chosen'):
        headless_server.state(store(), root=tmp_path / 'calc', opener=opener(tmp_path))


def test_a_server_behind_a_vpn_gets_the_vpn_of_its_profile(server, tmp_path):
    # the server does not answer and its profile names a VPN: OpenVPN Connect (a fake one that records its arguments)
    # is asked to connect that profile — and no other —, and the server is asked again. The oracle of «the VPN came up»
    # is the fake server itself: the wait removes its «offline» mark
    import sys

    from tests.fake_programs import program_script

    calls = tmp_path / 'vpn-calls.txt'
    app = program_script(tmp_path / 'OpenVPN Connect',
                         f'#!{sys.executable}\nimport sys\nopen({str(calls)!r}, "a").write(" ".join(sys.argv[1:]) + "\\n")\n')
    chosen = headless_server.profile(store(vpn_id='17', vpn_name='lab'))
    connection = opener(tmp_path)(chosen)
    (server / 'offline').write_text('')
    waited = []

    def up(exe, host, port, seconds):
        waited.append((str(exe), host, port, seconds))
        (server / 'offline').unlink()
        return True

    resources = headless_server.look(chosen, connection, vpn_app=app, vpn_wait=up)
    assert resources.slurm and waited == [(str(app), '192.0.2.103', 22, 60.0)]
    end = time.monotonic() + 5
    while not calls.exists() and time.monotonic() < end:
        time.sleep(0.05)
    assert calls.read_text().split() == ['--connect-shortcut=17']  # asked once, that profile, nothing switched off
    # the VPN did not come up: said so, with what to look at
    (server / 'offline').write_text('')
    with pytest.raises(ValueError, match='was asked to connect «lab» and the server still did not answer'):
        headless_server.look(chosen, connection, vpn_app=app, vpn_wait=lambda *a: False)
    # a profile without a VPN: nothing is asked of OpenVPN Connect
    before = calls.read_text()
    assert headless_server.switch_vpn_on(headless_server.profile(store()), app=app, wait=lambda *a: True) is False
    assert calls.read_text() == before


def test_what_a_server_is_not_asked(server, tmp_path):
    jobs = headless.Jobs()
    with pytest.raises(ValueError, match='a server runs orca, mopac, not xtb'):
        jobs.start_server('xtb', {'smiles': 'O'}, None, store(), root=tmp_path / 'calc', opener=opener(tmp_path))
    with pytest.raises(ValueError, match='no server profile'):
        headless_server.profile(Store())
    with pytest.raises(ValueError, match="no server profile 'other'"):
        headless_server.profile(store(), 'other')
    broken = Store({remote.PROFILES_KEY: json.dumps([ServerProfile('s', '', 22, '').to_dict()])})
    with pytest.raises(ValueError, match='is not complete'):
        headless_server.profile(broken)
    # three calculations of the journal not known to have ended — a fourth is not sent
    root = tmp_path / 'calc'
    for k in range(headless_server.ACTIVE):
        headless_server._note(root, event='sent', folder=str(root / f'job{k}'))
    with pytest.raises(ValueError, match='at most 3 at\\s+once'):
        jobs.start_server('orca', {'smiles': 'O'}, None, store(), root=root, opener=opener(tmp_path))
    assert not (server / 'ssh.log').exists()  # refused before the server was asked anything
    # only a calculation of the journal is taken up again
    with pytest.raises(ValueError, match='is not a calculation sent to a server from here'):
        jobs.resume_server(tmp_path / 'somewhere', store(), root=root, opener=opener(tmp_path))


def test_stop_cancels_its_own_job_and_a_restart_takes_the_watching_up(server, tmp_path, monkeypatch):
    monkeypatch.setenv('FAKE_ORCA_STEPS', '200')
    monkeypatch.setenv('FAKE_ORCA_DELAY', '0.2')
    root = tmp_path / 'calc'
    jobs = headless.Jobs()
    sent = jobs.start_server('orca', {'smiles': 'O'}, {'task': 'Оптимизация'}, store(), cores=1, root=root,
                             opener=opener(tmp_path), interval=0.1)
    end = time.monotonic() + 20
    while jobs.status(sent['job'])['state'] != 'running' and time.monotonic() < end:
        time.sleep(0.05)
    assert jobs.status(sent['job'])['state'] == 'running' and headless_server.active(root) == [sent['folder']]
    # the process of the tools was restarted: other Jobs take the watching up from the journal and job.json
    again = headless.Jobs()
    taken = again.resume_server(sent['folder'], store(), root=root, opener=opener(tmp_path), interval=0.1)
    assert again.resume_server(sent['folder'], store(), root=root, opener=opener(tmp_path))['job'] == taken['job']
    sbatch = (server / 'home' / '.queue' / 'args').read_text().splitlines()
    assert len(sbatch) == 1  # nothing was sent again
    again.stop(taken['job'])
    stopped = wait(again, taken['job'])
    assert stopped['state'] == 'stopped' and stopped['exit_code'] == -15, stopped
    assert (server / 'scancel.log').read_text().split() == ['101']  # scancel of its own number
    assert headless_server.active(root) == []


def test_the_state_of_the_server(server, tmp_path):
    found = headless_server.state(store(time_limit='1-00:00:00', partition='long'), root=tmp_path / 'calc',
                                  opener=opener(tmp_path))
    assert found['server'] == 'serv3' and found['slurm'] and found['programs']['orca'] and found['programs']['mopac']
    cores = found['cores']
    assert 1 <= cores['most_for_one_calculation'] <= max(1, int(0.8 * cores['physical'])) and cores['default'] <= 8
    assert found['time_limit'] == '1-00:00:00' and found['partition'] == 'long' and found['calculations_open'] == []
    assert found['calculations_at_once'] == 3


def bare(load, cores=20):
    """A server without SLURM (serv1): no node of sinfo, the busy cores are its load average."""
    return cluster.Resources(cores, cores, 1, 128_000, (), 500_000, False, '/opt/orca/orca', 114_000, load=load)


def test_a_server_without_slurm_gives_only_the_cores_its_load_leaves():
    # 20 cores, at most 16 busy (80 %): an idle server gives 16, a load of 9.6 (10 cores) gives 6, of 17 — nothing
    assert headless_server.ceiling(bare(0.1)) == (16, 20, 16)
    assert headless_server.ceiling(bare(9.6)) == (6, 20, 6)
    assert headless_server.ceiling(bare(17.0))[0] == 0
    # a calculation sent a moment ago is not in the load yet: its cores are taken off
    assert headless_server.ceiling(bare(0.1), reserved=8)[0] == 8
    with pytest.raises(ValueError, match='7 asked, at most 6'):
        headless_server.choose(bare(9.6), cores=7)


def test_a_calculation_on_a_server_without_slurm_goes_by_nohup(tmp_path, monkeypatch):
    if os.name == 'nt':
        pytest.skip('the fake server is a set of POSIX scripts')
    server = fake_server.install(tmp_path, monkeypatch, slurm=False)
    jobs = headless.Jobs()
    sent = jobs.start_server('orca', {'smiles': 'O'}, {'task': 'Оптимизация'}, store(), cores=2, root=tmp_path / 'calc',
                             opener=opener(tmp_path), interval=0.1)
    done = wait(jobs, sent['job'])
    assert done['state'] == 'finished' and done['exit_code'] == 0 and done['result']['normal_exit'], done
    there = server / 'home' / 'azimuth' / 'calculations' / os.path.basename(sent['folder'])
    # the helper started the script itself: its receipt names the process, what the script printed is kept
    receipt = (there / '.az-receipt').read_text() if (there / '.az-receipt').is_file() else ''
    assert done['slurm_job'].isdigit() and (there / 'az-nohup.out').is_file(), receipt
    # the next one, sent while the journal still counts the first as just sent, has its cores taken off
    assert headless_server.just_sent(tmp_path / 'calc', 'serv3') == 0  # the first has ended


def test_stop_on_a_server_without_slurm_ends_its_own_process(tmp_path, monkeypatch):
    if os.name == 'nt':
        pytest.skip('the fake server is a set of POSIX scripts')
    fake_server.install(tmp_path, monkeypatch, slurm=False)
    monkeypatch.setenv('FAKE_ORCA_STEPS', '400')
    jobs = headless.Jobs()
    sent = jobs.start_server('orca', {'smiles': 'O'}, {'task': 'Оптимизация'}, store(), cores=2, root=tmp_path / 'calc',
                             opener=opener(tmp_path), interval=0.1)
    end = time.monotonic() + 20
    while time.monotonic() < end and jobs.status(sent['job'])['state'] != 'running':
        time.sleep(0.05)
    assert headless_server.just_sent(tmp_path / 'calc', 'serv3') == 2
    pid = int(jobs.status(sent['job'])['slurm_job'])
    os.kill(pid, 0)  # the process of the script is alive
    jobs.stop(sent['job'])
    done = wait(jobs, sent['job'])
    assert done['state'] == 'stopped', done
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)


def test_a_calculation_sent_long_ago_is_not_open(tmp_path):
    # Windows of the owner (2026-11-24): yesterday's water listed as open on both servers — its watcher ended before it
    # and wrote no «ended». Older than the longest time limit it cannot still run
    import json
    from datetime import datetime, timedelta

    from azimuth import headless_server

    root = tmp_path / 'calc'
    path = headless_server.jobs_root(root) / headless_server.JOURNAL
    path.parent.mkdir(parents=True)
    now = datetime(2026, 11, 24, 12, 0, 0)
    def accepted(name):  # a folder the queue accepted: its job.json is there
        folder = tmp_path / name
        folder.mkdir(exist_ok=True)
        (folder / 'job.json').write_text('{}', encoding='utf-8')
        return str(folder)

    old, new, a, b = (accepted(name) for name in ('old', 'new', 'a', 'b'))
    rows = [{'time': (now - timedelta(hours=26)).isoformat(timespec='seconds'), 'event': 'sent', 'folder': old},
            {'time': (now - timedelta(hours=1)).isoformat(timespec='seconds'), 'event': 'sent', 'folder': new}]
    path.write_text(''.join(json.dumps(r) + '\n' for r in rows), encoding='utf-8')
    assert headless_server.active(root, now=now) == [new]
    # the calculations of one server (Windows check 2026-11-24: those of .101 were listed for .103)
    rows = [{'time': (now - timedelta(hours=1)).isoformat(timespec='seconds'), 'event': 'sent', 'folder': name,
             'server': server} for name, server in ((a, 'serv1'), (b, 'serv3'))]
    path.write_text(''.join(json.dumps(r) + '\n' for r in rows), encoding='utf-8')
    assert headless_server.active(root, now=now, server='serv3') == [b] and headless_server.active(root, now=now) == [a, b]


def test_a_sending_that_never_reached_the_server_takes_no_place(tmp_path):
    # the queue writes job.json into the folder when it accepts the job: a «sent» of the journal without it, whose
    # process is gone or which is older than UNSENT_S, was cut during the upload — it held a place of ACTIVE for a day
    from datetime import datetime, timedelta

    from azimuth import headless_server

    root = tmp_path / 'calc'
    path = headless_server.jobs_root(root) / headless_server.JOURNAL
    path.parent.mkdir(parents=True)
    now = datetime(2026, 11, 26, 12, 0, 0)

    def row(name, minutes, pid=None, accepted=False):
        folder = tmp_path / name
        folder.mkdir()
        if accepted:
            (folder / 'job.json').write_text('{}', encoding='utf-8')
        found = {'time': (now - timedelta(minutes=minutes)).isoformat(timespec='seconds'), 'event': 'sent', 'folder': str(folder)}
        return {**found, 'pid': pid} if pid is not None else found

    rows = [row('lost_long_ago', 11), row('just_sent', 1), row('sender_gone', 1, pid=111), row('sender_alive', 1, pid=222),
            row('in_the_queue', 300, pid=111, accepted=True)]
    path.write_text(''.join(json.dumps(r) + '\n' for r in rows), encoding='utf-8')
    alive = {111: False, 222: True}.get
    names = lambda folders: [Path(f).name for f in folders]  # noqa: E731
    assert names(headless_server.active(root, now=now, alive=alive)) == ['just_sent', 'sender_alive', 'in_the_queue']
    assert names(headless_server.close_unsent(root, now=now, alive=alive)) == ['lost_long_ago', 'sender_gone']
    ends = [r for r in headless_server.journal(root) if r.get('event') == 'ended']
    assert [(Path(r['folder']).name, r['state'], r['code']) for r in ends] == [('lost_long_ago', 'not sent', None),
                                                                              ('sender_gone', 'not sent', None)]
    assert headless_server.close_unsent(root, now=now, alive=alive) == []  # written once
    # the process of this test is alive, one that cannot exist is not
    import os

    assert headless_server._alive(os.getpid()) is True and headless_server._alive('x') is None
    assert headless_server._alive(2 ** 22 + 12345) in (False, None)
