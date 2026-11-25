"""Opening a server before a calculation (modules/sextant/server_access.py); the fake server, no window.

Oracles: the calls the user would see — how many times the password is asked and with which note — counted here;
the fake ssh accepts only the password written in its file; the session store of keychain.py after success;
the fake OpenVPN Connect records --connect-shortcut=<id>.
"""

import os

import pytest

from modules.sextant import keychain, server_access
from modules.sextant.remote import ServerProfile
from modules.sextant.ssh import SshError
from tests import fake_server


def now(work):
    return work(lambda *a: True)


@pytest.fixture
def server(tmp_path, monkeypatch):
    if os.name == 'nt':  # the Windows run of 2026-10-29 — no sh to run them
        pytest.skip('the fake server is a set of POSIX scripts')
    root = fake_server.install(tmp_path, monkeypatch)
    monkeypatch.setattr(keychain, 'SESSION', {})
    monkeypatch.setattr(keychain, '_lib', lambda: None)  # never the real Keychain in the tests
    return root


def profile(**extra):
    return ServerProfile('serv3', '192.0.2.103', 22, 'user', '~/azimuth/calculations', **extra)


def test_keys_need_no_password(server):
    asked = []
    opened = server_access.open_server(None, profile(), ask=lambda p, wrong: asked.append(wrong), waiting=now)
    connection, resources = opened
    assert asked == [] and resources.slurm and resources.logical  # the probe ran «there»
    assert resources.orca.endswith('/orca')  # the fake ORCA in PATH
    assert connection.password is None and keychain.SESSION == {}


def test_password_asked_again_when_wrong(server):
    (server / 'password').write_text('s3cret')
    answers = iter(['wrong', 's3cret'])
    asked = []

    def ask(p, wrong):
        asked.append(wrong)
        return next(answers)

    connection, _ = server_access.open_server(None, profile(), ask=ask, waiting=now)
    # no password first (keys); then asked; the first answer is wrong — asked again with the note
    assert asked == [False, True] and connection.password == 's3cret'
    assert keychain.SESSION[keychain.service_for(profile())] == 's3cret'  # this session only
    again = []
    server_access.open_server(None, profile(), ask=lambda p, w: again.append(w), waiting=now)
    assert again == []  # remembered for the session


def test_cancel_and_too_many_wrong_passwords(server):
    (server / 'password').write_text('s3cret')
    assert server_access.open_server(None, profile(), ask=lambda p, w: None, waiting=now) is None
    with pytest.raises(SshError) as refused:
        server_access.open_server(None, profile(), ask=lambda p, w: 'nope', waiting=now)
    assert refused.value.kind == 'auth'


def test_no_connection_switches_the_vpn_on_once(server, tmp_path, monkeypatch):
    (server / 'offline').write_text('')
    with pytest.raises(SshError) as lost:  # no VPN profile: the message at once
        server_access.open_server(None, profile(), waiting=now)
    assert lost.value.kind == 'connection'
    calls = tmp_path / 'vpn.txt'
    app = tmp_path / 'OpenVPN Connect'
    app.write_text(f'#!/bin/sh\necho "$@" >> {calls}\n')
    app.chmod(0o755)

    def answers(host, port, timeout):
        (server / 'offline').unlink(missing_ok=True)  # the VPN came up
        return True

    monkeypatch.setattr(server_access.vpn, 'reachable', answers)
    monkeypatch.setattr(server_access, 'wait_reachable',
                        lambda p, s, step, check=answers, pause=None, app=None: check(p.host, p.port, 1))
    opened = server_access.open_server(None, profile(vpn_id='17'), waiting=now, connect_app=app)
    assert opened is not None
    import time

    end = time.monotonic() + 5
    while not (calls.exists() and '--connect-shortcut=17' in calls.read_text()) and time.monotonic() < end:
        time.sleep(0.05)
    assert '--connect-shortcut=17' in calls.read_text()


def test_wait_reachable_is_bounded_and_cancellable():
    p = profile()
    assert server_access.wait_reachable(p, 0.2, lambda *a: True, check=lambda *a: False, pause=lambda s: None) is False
    with pytest.raises(InterruptedError):
        server_access.wait_reachable(p, 5, lambda *a: False, check=lambda *a: False, pause=lambda s: None)
    assert server_access.wait_reachable(p, 5, lambda *a: True, check=lambda *a: True)


def test_login_without_a_password_by_the_key_of_the_program(server, tmp_path):
    # «Вход без пароля» — the key is made, put on the server with the password once, and then the server
    # lets in without one (also on Windows, where the password is typed in a console of ssh)
    import shutil

    if shutil.which('ssh-keygen') is None:
        pytest.skip('no ssh-keygen here')
    (server / 'password').write_text('secret')
    home = tmp_path / 'user'
    asked = []
    message = server_access.set_up_key(None, profile(), waiting=now, home=home, windows=False,
                                       ask=lambda p, wrong: asked.append(wrong) or 'secret')
    assert 'ключ' in message and asked == [False]
    public = (home / '.ssh' / 'azimuth_ed25519.pub').read_text().strip()
    assert (server / 'home' / '.ssh' / 'authorized_keys').read_text().splitlines().count(public) == 1
    again = server_access.set_up_key(None, profile(), waiting=now, home=home, windows=False,
                                     ask=lambda p, wrong: pytest.fail('no password the second time'))
    assert 'уже работает' in again
    # Windows: the console of ssh (here: the user typed the password, the key is appended)
    (server / 'home' / '.ssh' / 'authorized_keys').write_text('')
    typed = []

    def console(args):
        typed.append(args)
        with open(server / 'home' / '.ssh' / 'authorized_keys', 'a') as keys:
            keys.write(public + '\n')
        return 0

    message = server_access.set_up_key(None, profile(), waiting=now, home=home, windows=True, console=console)
    assert typed and 'ControlMaster=auto' not in typed[0] and '-i' in typed[0] and 'ключ' in message
