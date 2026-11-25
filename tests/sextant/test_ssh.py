"""ssh and scp to a calculation server (modules/sextant/ssh.py); a fake server on this computer.

Oracles: the OpenSSH options named in its manual (ssh_config(5): ControlMaster, ControlPath, ControlPersist,
StrictHostKeyChecking=accept-new; ssh(1): SSH_ASKPASS, SSH_ASKPASS_REQUIRE=force, exit status 255 for its own
errors); the files copied are compared byte for byte; the error texts are those printed by OpenSSH.
"""

import os
from pathlib import Path

import pytest

from modules.sextant import ssh
from modules.sextant.remote import ServerProfile
from tests import fake_server


def profile():
    return ServerProfile('serv3', '192.0.2.103', 22, 'user', '~/azimuth/calculations')


@pytest.fixture
def server(tmp_path, monkeypatch):
    if os.name == 'nt':  # the Windows run of 2026-10-29 — no sh to run them
        pytest.skip('the fake server is a set of POSIX scripts')
    return fake_server.install(tmp_path, monkeypatch)


def test_options_keep_one_connection_and_no_password_on_the_command_line(tmp_path):
    c = ssh.Connection(profile(), password='секрет 1', control_dir=tmp_path)
    options = c.options()
    assert options[:2] == ['-p', '22']
    assert 'StrictHostKeyChecking=accept-new' in options
    # the OpenSSH of Windows has no ControlMaster — every command logs in anew there (the test
    # expected the options of macOS on Windows too)
    control = ('ControlMaster=auto', 'ControlPersist=600', f'ControlPath={tmp_path / "%C"}')
    for wanted in control:
        assert (wanted in options) == (os.name != 'nt')
    assert not any('секрет' in o for o in options)
    env = c.environment()
    assert env['SSH_ASKPASS_REQUIRE'] == 'force' and env['AZIMUTH_SSH_SECRET'] == 'секрет 1'
    helper = tmp_path / ('askpass.cmd' if os.name == 'nt' else 'askpass.sh')
    assert 'секрет' not in helper.read_text()  # the helper reads the variable, holds nothing
    # on Windows no path in the .cmd (cmd.exe reads it in the OEM code page: a Python under a Cyrillic folder
    # would not start) — the Python comes from the environment
    (tmp_path / 'w').mkdir()
    windows = ssh.Connection(profile(), password='секрет 2', control_dir=tmp_path / 'w', windows=True)
    assert not any(o.startswith('ControlMaster') for o in windows.options())
    env = windows.environment()
    text = (tmp_path / 'w' / 'askpass.cmd').read_text(encoding='ascii')
    assert '%AZIMUTH_SSH_PYTHON%' in text and 'секрет' not in text and Path(env['AZIMUTH_SSH_PYTHON']).is_file()
    # written once, not before every login (the watchers of two calculations wrote it while another ssh ran it)
    helper = tmp_path / 'w' / 'askpass.cmd'
    assert helper.read_bytes().endswith(b'"\r\n') and helper.read_bytes().count(b'\r') == 1
    before = helper.stat().st_mtime_ns
    import time as _time
    _time.sleep(0.02)
    windows.environment()
    assert helper.stat().st_mtime_ns == before and not list((tmp_path / 'w').glob('*.tmp'))
    assert '-J' in ssh.Connection(ServerProfile(host='h', user='u', jump='me@gate:2222'), control_dir=tmp_path).options()
    assert 'AZIMUTH_SSH_SECRET' not in ssh.Connection(profile(), control_dir=tmp_path).environment()  # keys: no helper


def test_paths_for_the_shell_and_for_scp():
    assert ssh.shell_path('~/azimuth/my calcs') == '"$HOME"/\'azimuth/my calcs\''
    assert ssh.shell_path('~') == '"$HOME"' and ssh.shell_path('/data/a') == '/data/a'
    assert ssh.scp_path('~/azimuth') == 'azimuth' and ssh.scp_path('/data/a') == '/data/a' and ssh.scp_path('~') == '.'


def test_errors_are_named_for_the_user():
    assert ssh.classify('ssh: connect to host x port 22: Connection timed out') == 'connection'
    assert ssh.classify('ssh: Could not resolve hostname serv3: nodename nor servname provided') == 'connection'
    assert ssh.classify('user@x: Permission denied (publickey,password).') == 'auth'
    assert ssh.classify('@@@ WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED! @@@') == 'hostkey'
    assert ssh.classify('Host key verification failed.') == 'hostkey'


def test_run_upload_download_through_the_fake_server(server, tmp_path):
    c = ssh.Connection(profile(), control_dir=tmp_path / 'ctl')
    (tmp_path / 'ctl').mkdir()
    assert c.text('echo "$HOME"').strip() == str(server / 'home')
    assert c.run('exit 3').code == 3  # the code of the remote command, not an ssh failure
    with pytest.raises(ssh.SshError) as failed:
        c.text('ls /nowhere')
    assert failed.value.kind == 'command'
    job = tmp_path / 'job-1'
    job.mkdir()
    (job / 'input.inp').write_bytes(b'! HF\n* xyz 0 1\nHe 0 0 0\n*\n')
    c.upload(job, '~/azimuth/calculations')
    there = server / 'home' / 'azimuth' / 'calculations' / 'job-1'
    assert (there / 'input.inp').read_bytes() == (job / 'input.inp').read_bytes()
    (there / 'input.out').write_text('ORCA TERMINATED NORMALLY\n')
    back = tmp_path / 'back'
    back.mkdir()
    c.download(['input.out', '../escape', 'a/b'], '~/azimuth/calculations/job-1', back)  # only plain names
    assert (back / 'input.out').read_text() == 'ORCA TERMINATED NORMALLY\n' and len(list(back.iterdir())) == 1


def test_password_through_askpass_and_refusals(server, tmp_path):
    (server / 'password').write_text('s3cret')
    (tmp_path / 'ctl').mkdir()
    assert ssh.Connection(profile(), password='s3cret', control_dir=tmp_path / 'ctl').text('echo ok').strip() == 'ok'
    with pytest.raises(ssh.SshError) as refused:
        ssh.Connection(profile(), password='wrong', control_dir=tmp_path / 'ctl').text('echo ok')
    assert refused.value.kind == 'auth' and 'логин или пароль' in str(refused.value)
    assert 's3cret' not in (server / 'ssh.log').read_text()  # never on a command line
    (server / 'offline').write_text('')
    with pytest.raises(ssh.SshError) as lost:
        ssh.Connection(profile(), password='s3cret', control_dir=tmp_path / 'ctl').text('echo ok')
    assert lost.value.kind == 'connection' and 'VPN' in str(lost.value)


@pytest.mark.skipif(os.name == 'nt', reason='the slow fake ssh is a POSIX script')
def test_missing_ssh_and_timeout(tmp_path):
    (tmp_path / 'ctl').mkdir()
    with pytest.raises(ssh.SshError) as missing:
        ssh.Connection(profile(), ssh='/nowhere/ssh', control_dir=tmp_path / 'ctl').run('true')
    assert missing.value.kind == 'missing'
    slow = tmp_path / 'slow-ssh'
    slow.write_text('#!/bin/sh\nsleep 5\n')
    slow.chmod(0o755)
    with pytest.raises(ssh.SshError) as late:
        ssh.Connection(profile(), ssh=str(slow), control_dir=tmp_path / 'ctl', timeout=0.5).run('true')
    assert late.value.kind == 'timeout'
