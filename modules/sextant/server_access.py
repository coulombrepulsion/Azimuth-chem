"""Sextant: opening a server for a calculation — the password, the VPN and what the server has now.

HEADER
    One call before every calculation on a server and from «Узнать ресурсы» of the server dialog: an ssh connection
    that works and the Resources of the server (cluster.parse_probe). The password is asked only when the server
    refuses without it (keys and ssh-agent work without any), and asked again when it was wrong; a server that does
    not answer gets OpenVPN Connect switched on once (the VPN profile of the server profile) and a minute to answer.
    The slow part — ssh, the probe, the wait for the VPN — runs off the window's thread (tasks.run_waiting), so the
    window keeps painting and «Отмена» works.
    Wilkinson convention, sections 1-8.

§2 ALGORITHM
    password = keychain.get (this session, else the Keychain), may be None.
    loop (at most ATTEMPTS passwords):
        connection = ssh.Connection(profile, password); resources = waiting(probe) —
        success: the password, if any, is kept for the session (keychain.put remember=False: the Keychain only when
            the user ticked it in the dialog) → (connection, resources);
        SshError 'auth' → ask(profile, wrong=bool(password)); None → None (cancelled); else try again with it;
        SshError 'connection'/'timeout' and the profile has a VPN profile and OpenVPN Connect is there, the first time
            → vpn.connect, waiting(reachable within VPN_WAIT_S) → True: try again; else the error;
        any other SshError → raised (the window shows its message).
    A cancelled wait (InterruptedError) → None.

§4 SPECIFICATION
    open_server(parent, profile, ask=None, waiting=None, connect_app=None, ssh='ssh', scp='scp')
        -> (Connection, Resources) | None; raises ssh.SshError with a message for the user
    ask_password(parent, profile, wrong) -> str | None (QInputDialog, the text hidden)
    run_in_background(parent, title) -> waiting(work) (tasks.run_waiting)
    wait_reachable(profile, seconds, step, check=vpn.reachable, pause=time.sleep) -> bool
    open_for_watching(parent, profile, …) -> (Connection, Resources | None, why) | None — for taking up the
    watching: a server that does not answer gives an unchecked connection (resources None) instead of an error.
    ATTEMPTS, VPN_WAIT_S.

§7 TEST CASES tests/sextant/test_server_access.py (fake server: without a password, a wrong and a right one, cancelling,
    no connection without and with a VPN profile).
§8' ROBUSTNESS
    The password never goes to the settings, a file or a command line (ssh.py). Every wait has a bound.
"""

from __future__ import annotations

import time

from modules.sextant import cluster, keychain, vpn
from modules.sextant.ssh import Connection, SshError
from azimuth.i18n import tr

ATTEMPTS = 3
VPN_WAIT_S = 60


def ask_password(parent, profile, wrong):
    from PySide6.QtWidgets import QInputDialog, QLineEdit

    text = tr(f'Пароль для {profile.address()}')
    if wrong:
        text = tr('Пароль не подошёл. ') + text
    value, ok = QInputDialog.getText(parent, tr('Вход на сервер'), text + ':', QLineEdit.EchoMode.Password)
    return value if ok and value else None


def set_up_key(parent, profile, connect_app=None, waiting=None, ssh='ssh', home=None, windows=None, console=None,
               ask=None, keygen='ssh-keygen'):
    """«Вход без пароля» — makes the key of the program (ssh.ensure_key) and puts it on the server with the
    password once; then every ssh (also on Windows, whose OpenSSH keeps no connection open) logs in by the key.
    macOS, Linux: the connection of open_server (the password from the window or the Keychain). Windows: the password
    is typed in a console window of ssh itself (console(args) runs it and waits). Returns a message for the user;
    raises SshError when it did not work."""
    import os
    import subprocess

    from modules.sextant import ssh as ssh_module

    windows = os.name == 'nt' if windows is None else windows
    private, public = ssh_module.ensure_key(home, keygen)
    wait = waiting or run_in_background(parent, tr(f'Вход по ключу на {profile.title()}…'))

    def key_works(step=None):
        try:
            return Connection(profile, ssh=ssh, key=private, batch=True, windows=windows).run('true', timeout=30).code == 0
        except SshError as exc:
            if exc.kind == 'auth':
                return False
            raise

    if wait(key_works):
        return tr('Вход по ключу уже работает — пароль не нужен.')
    if windows:
        target = Connection(profile, ssh=ssh, key=private, windows=True)
        args = [ssh, *target.options(), target.target(), ssh_module.install_command(public)]
        if console is None:
            def console(a):
                return subprocess.run(a, creationflags=getattr(subprocess, 'CREATE_NEW_CONSOLE', 0)).returncode
        if wait(lambda step=None: console(args)) != 0:
            raise SshError(tr('Ключ не записан на сервер: пароль не подошёл или окно закрыто.'), 'auth')
    else:
        opened = open_server(parent, profile, ask=ask, connect_app=connect_app, waiting=waiting, ssh=ssh)
        if opened is None:
            return tr('Отменено.')
        connection, _ = opened
        wait(lambda step=None: connection.install_key(public))
    if not wait(key_works):
        raise SshError(tr('Ключ записан, но сервер не пускает по нему — возможно, на сервере запрещён вход по ключам. '
                          'Спросите администратора.'), 'auth')
    return tr('Готово: вход по ключу ') + str(private) + tr(' — пароль больше не спрашивается.')


def run_in_background(parent, title):
    from azimuth.tasks import run_waiting

    return lambda work: run_waiting(parent, title, work, alone=False)


def wait_reachable(profile, seconds, step, check=vpn.reachable, pause=time.sleep, app=None):
    """App — OpenVPN Connect asked to connect: its window was hidden (vpn.connect), and when the server has not
    answered in vpn.REVEAL_AFTER_S it is shown once — it may be asking for a password."""
    started, revealed = time.monotonic(), app is None
    while time.monotonic() - started < seconds:
        if check(profile.host, profile.port, 1.5):
            return True
        if step(0, 0) is False:
            raise InterruptedError
        if not revealed and time.monotonic() - started >= vpn.REVEAL_AFTER_S:
            revealed = True
            vpn.reveal(app)
        pause(2.0)
    return False


def open_server(parent, profile, ask=None, waiting=None, connect_app=None, ssh='ssh', scp='scp', search=False):
    """Search — the programs are looked for outside PATH too (cluster.probe_command; «Узнать ресурсы»)."""
    ask = ask or (lambda p, wrong: ask_password(parent, p, wrong))
    service = keychain.service_for(profile)
    password = keychain.get(service, profile.user)
    vpn_tried = False
    asked = 0
    while True:
        connection = Connection(profile, password=password, ssh=ssh, scp=scp)
        wait = waiting or run_in_background(parent, tr(f'Подключение к серверу {profile.title()}…'))

        def probe(step=None, c=connection):
            return cluster.parse_probe(c.text(cluster.probe_command(profile.folder, profile.partition, search), timeout=90))

        try:
            resources = wait(probe)
        except InterruptedError:
            return None
        except SshError as exc:
            if exc.kind == 'auth' and asked < ATTEMPTS:
                asked += 1
                password = ask(profile, password is not None)
                if password is None:
                    return None
                continue
            if exc.kind in ('connection', 'timeout') and profile.vpn_id and not vpn_tried:
                app = connect_app if connect_app is not None else vpn.find_connect()
                if app is not None:
                    vpn_tried = True
                    try:
                        vpn.connect(app, profile.vpn_id)
                    except ValueError:
                        raise exc from None
                    waiting_vpn = waiting or run_in_background(parent, tr('Подключаю VPN в OpenVPN GUI…') if vpn.is_gui(app)
                                                             else tr('Подключаю VPN в OpenVPN Connect…'))
                    try:
                        answered = waiting_vpn(lambda step=lambda *a: True: wait_reachable(profile, VPN_WAIT_S, step, app=app))
                    except InterruptedError:
                        return None
                    if answered:
                        continue
            raise
        if password:
            keychain.put(service, profile.user, password, remember=False)
        return connection, resources


def open_for_watching(parent, profile, ask=None, waiting=None, connect_app=None, ssh='ssh', scp='scp'):
    """T09 (PROJECT_RUNTIME_GUIDE.md §13: an unreachable server does not stop a project from opening; the last state
    and its age are shown): the server opened to watch calculations sent before — when it
    does not answer (no network, no VPN: SshError 'connection' or 'timeout'), a connection that is not checked is
    given all the same with resources None, and the watching (RemoteJob) says «Нет связи», what it knew last and
    tries again by itself. A wrong password and the other errors are raised as by open_server; None — cancelled.
    -> (Connection, Resources | None, why: '' or the message of the lost connection) | None"""
    try:
        opened = open_server(parent, profile, ask=ask, waiting=waiting, connect_app=connect_app, ssh=ssh, scp=scp)
    except SshError as exc:
        if exc.kind not in ('connection', 'timeout'):
            raise
        password = keychain.get(keychain.service_for(profile), profile.user)
        return Connection(profile, password=password, ssh=ssh, scp=scp), None, str(exc)
    if opened is None:
        return None
    connection, resources = opened
    return connection, resources, ''

