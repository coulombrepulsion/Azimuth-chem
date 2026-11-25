"""OpenVPN Connect from the program: the list of profiles, connecting, the server answering."""

import os
import socket
import stat
import sys
import time

import pytest

from modules.sextant import vpn

pytestmark = pytest.mark.skipif(os.name == 'nt', reason='the fake OpenVPN Connect is a POSIX script')


def fake_connect(tmp_path, reply):
    exe = tmp_path / 'OpenVPN Connect'
    log = tmp_path / 'calls.txt'
    exe.write_text(f'#!{sys.executable}\nimport sys\nopen({str(log)!r}, "a").write(" ".join(sys.argv[1:]) + "\\n")\n'
                   f'sys.stdout.write({reply!r})\n')
    exe.chmod(exe.stat().st_mode | stat.S_IXUSR)
    return exe, log


def test_profiles_are_read_from_the_reply(tmp_path):
    reply = 'OpenVPN Connect 3.5.0\n[{"id": "1729859400000", "name": "lab", "host": "vpn.lab.ru"}, {"Id": "2", "Name": ""}]'
    exe, log = fake_connect(tmp_path, reply)
    assert vpn.find_connect([tmp_path / 'missing', exe]) == exe and vpn.find_connect([tmp_path / 'missing']) is None
    profiles = vpn.list_profiles(exe)
    assert profiles == [vpn.VpnProfile('1729859400000', 'lab', 'vpn.lab.ru'), vpn.VpnProfile('2', '2', '')]
    assert '--list-profiles' in log.read_text()
    assert vpn.parse_profiles('{"status": "success", "profiles": [{"id": "7", "name": "x"}]}') == [vpn.VpnProfile('7', 'x')]
    with pytest.raises(ValueError):
        vpn.parse_profiles('{"status": "error", "message": "Accept GDPR to use the application."}')
    with pytest.raises(ValueError):
        vpn.parse_profiles('nothing here')


def test_connect_and_import_call_the_app(tmp_path):
    exe, log = fake_connect(tmp_path, '{"status": "success"}')
    vpn.import_profile(exe, tmp_path / 'lab.ovpn', 'lab')
    vpn.connect(exe, '1729859400000')
    vpn.disconnect(exe)
    end = time.monotonic() + 10
    while log.read_text().count('\n') < 3 and time.monotonic() < end:
        time.sleep(0.05)
    calls = log.read_text()
    assert f'--import-profile={tmp_path / "lab.ovpn"} --name=lab' in calls
    assert '--connect-shortcut=1729859400000' in calls and '--disconnect-shortcut' in calls
    with pytest.raises(ValueError):
        vpn.connect(exe, '')


def test_server_answering():
    server = socket.socket()
    server.bind(('127.0.0.1', 0))
    server.listen(1)
    port = server.getsockname()[1]
    try:
        assert vpn.reachable('127.0.0.1', port, 1.0)
    finally:
        server.close()
    assert not vpn.reachable('127.0.0.1', port, 0.5)  # nobody listens there now
    assert not vpn.reachable('no-such-host.invalid', 22, 0.5)


def test_a_slow_name_is_not_waited_for(monkeypatch):
    # the search of a name counts in the timeout (an unknown name took 30 s on macOS; the window of the
    # server asks while it is shown)
    def slow(*args, **kwargs):
        time.sleep(3)
        raise socket.gaierror('too late')

    monkeypatch.setattr(vpn.socket, 'getaddrinfo', slow)
    started = time.monotonic()
    assert not vpn.reachable('slow.example', 22, 0.3)
    assert time.monotonic() - started < 1.0
    assert not vpn.reachable('127.0.0.1', 'not a port', 0.3)


def test_the_window_of_openvpn_connect_is_kept_off_the_program(tmp_path, monkeypatch):
    # «чтобы окно openvpn не перекрывало окно азимута»: after the command the application is hidden (macOS: by its
    # bundle identifier, read from the Info.plist of the application the executable lies in), and when the server has
    # not answered in REVEAL_AFTER_S its window is shown once — it may be asking for a password. The oracles: an
    # Info.plist written here, a clock moved by the pauses, the calls recorded
    import plistlib

    app = tmp_path / 'OpenVPN Connect.app' / 'Contents'
    (app / 'MacOS').mkdir(parents=True)
    (app / 'Info.plist').write_bytes(plistlib.dumps({'CFBundleIdentifier': 'org.openvpn.client.app'}))
    exe = app / 'MacOS' / 'OpenVPN Connect'
    exe.write_text('#!/bin/sh\n')
    assert vpn.bundle_id(exe) == 'org.openvpn.client.app' and vpn.bundle_id(tmp_path / 'none') is None
    assert vpn.hide(tmp_path / 'none') == 0  # not an application: nothing, and no exception
    hidden = []
    monkeypatch.setattr(vpn, '_hide_mac', lambda identifier: hidden.append(identifier) or 1)
    monkeypatch.setattr(vpn.sys, 'platform', 'darwin')
    assert vpn.hide(exe) == 1 and hidden == ['org.openvpn.client.app']
    monkeypatch.setattr(vpn, '_hide_mac', lambda identifier: 1 / 0)
    assert vpn.hide(exe) == 0  # a failure of the system call is never a failure of the VPN
    # «чтобы он подключал openvpn не разворачивая приложение»: the command goes through «open» — a new copy (-n) that
    # is not brought in front (-g) and starts hidden (-j); it hands the command to the running OpenVPN Connect. What
    # that one shows by itself is hidden every HIDE_EVERY_S for HIDE_FOR_S (here: a clock moved by the pauses)
    started, kept = [], []
    monkeypatch.setattr(vpn.subprocess, 'Popen', lambda command, **options: started.append(command))
    monkeypatch.setattr(vpn, 'keep_hidden', lambda e: kept.append(e))
    vpn.connect(exe, '17')
    for _ in range(100):
        if kept:
            break
        time.sleep(0.01)
    bundle = str((tmp_path / 'OpenVPN Connect.app').resolve())
    assert started == [['/usr/bin/open', '-n', '-g', '-j', '-a', bundle, '--args', '--connect-shortcut=17']] and kept == [exe]
    vpn.connect(exe, '17', quiet=False)  # asked to be shown: the executable itself
    assert started[-1] == [str(exe), '--connect-shortcut=17'] and len(kept) == 1
    monkeypatch.undo()
    monkeypatch.setattr(vpn.sys, 'platform', 'darwin')
    ticks, hides = [0.0], []
    monkeypatch.setattr(vpn, '_hide_mac', lambda identifier: hides.append(ticks[0]) or (1 if len(hides) in (3, 4) else 0))
    monkeypatch.setattr('time.monotonic', lambda: ticks[0])
    assert vpn.keep_hidden(exe, 1.0, 0.25, pause=lambda s: ticks.__setitem__(0, ticks[0] + s)) == 2
    assert hides == [0.0, 0.25, 0.5, 0.75]
    # the wait: the server answers at the fourth look; the window is shown once, only after REVEAL_AFTER_S
    clock, shown, looks = [0.0], [], []
    monkeypatch.setattr(vpn, 'reveal', lambda e: shown.append(clock[0]) or True)
    monkeypatch.setattr('time.monotonic', lambda: clock[0])

    def check(host, port, timeout):
        looks.append(clock[0])
        return len(looks) >= 4

    def pause(seconds):
        clock[0] += 10.0

    assert vpn.wait_connected(exe, 'h', 22, 60.0, check, pause) is True
    assert looks == [0.0, 10.0, 20.0, 30.0] and shown == [20.0]
    clock[0], looks[:] = 0.0, []
    assert vpn.wait_connected(exe, 'h', 22, 25.0, lambda *a: False, pause) is False  # never answered
    with pytest.raises(InterruptedError):
        vpn.wait_connected(exe, 'h', 22, 60.0, lambda *a: False, pause, step=lambda: False)


def test_openvpn_gui_of_the_community(tmp_path, monkeypatch):
    # Windows of the owner (2026-11-24): OpenVPN GUI instead of OpenVPN Connect — its connections are the .ovpn files
    # of its config folders, the name is the file without .ovpn; a running GUI takes «--command connect <name>», one not
    # running starts with «--connect <name>»
    exe = tmp_path / 'OpenVPN' / 'bin' / 'openvpn-gui.exe'
    exe.parent.mkdir(parents=True)
    exe.write_text('')
    user = tmp_path / 'home' / 'OpenVPN' / 'config'
    (user / 'lab').mkdir(parents=True)
    (user / 'lab' / 'lab.ovpn').write_text('client\nremote vpn.lab.ru 1194 udp\n')
    (tmp_path / 'OpenVPN' / 'config').mkdir()
    (tmp_path / 'OpenVPN' / 'config' / 'home.ovpn').write_text('client\n')
    monkeypatch.setenv('USERPROFILE', str(tmp_path / 'home'))
    assert vpn.is_gui(exe) and not vpn.is_gui(tmp_path / 'OpenVPN Connect') and vpn.app_name(exe) == 'OpenVPN GUI'
    assert vpn.list_profiles(exe) == [vpn.VpnProfile('lab', 'lab', 'vpn.lab.ru'), vpn.VpnProfile('home', 'home', '')]
    started = []
    monkeypatch.setattr(vpn.subprocess, 'Popen', lambda command, **kw: started.append(command))
    vpn.connect(exe, 'lab', running=True)
    vpn.connect(exe, 'lab', running=False)
    vpn.disconnect(exe, running=True)
    vpn.disconnect(exe, running=False)  # nothing to tell a GUI that is not running
    assert [c[1:] for c in started] == [['--command', 'connect', 'lab'], ['--connect', 'lab'],
                                         ['--command', 'disconnect_all']]
    source = tmp_path / 'new.ovpn'
    source.write_text('client\nremote 10.0.0.1 1194\n')
    copied = vpn.import_profile(exe, source, 'office')
    assert copied.endswith('office.ovpn') and (user / 'office.ovpn').read_text() == source.read_text()
