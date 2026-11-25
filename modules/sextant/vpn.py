"""Sextant: OpenVPN Connect (or, on Windows, OpenVPN GUI) switched on by the program for a server that needs a VPN.

HEADER
    The laboratory cluster answers only through OpenVPN. The program does not make a tunnel itself (that needs the
    rights of the administrator); it asks the user's OpenVPN Connect to connect the chosen profile and waits until the
    server answers. OpenVPN Connect (3.3+) has the command-line options --list-profiles, --import-profile=<file>,
    --connect-shortcut=<profile id> and --disconnect-shortcut (the last two open its window; OpenVPN support article
    41389237225499). It has no option for the state of the connection: «connected» is judged by the server itself —
    a TCP connection to its address and port.
    Wilkinson convention, sections 1-8.

    OpenVPN GUI (the community client of Windows, openvpn-gui.exe of «OpenVPN-2.x-…msi»; the owner's laptop,
    2026-11-24 — the program saw only OpenVPN Connect): its connections are the .ovpn files of its config folders
    (%USERPROFILE%\\OpenVPN\\config and <install>\\config, in subfolders too), named by the file without .ovpn; a
    running GUI takes «--command connect <name>», «--command disconnect_all»; one not running is started with
    «--connect <name>» (it connects at its start). It asks the password itself in its own window.

§2 ALGORITHM
    find_connect(): the executable inside OpenVPN Connect.app (two places the installer uses) or on Windows in Program
    Files. list_profiles(): the output of --list-profiles is JSON (possibly after other lines): the first JSON array or
    object in it, profiles as dicts with an id and a name (key names compared without case). reachable(): socket
    .create_connection with a timeout. connect()/disconnect(): started and left (the app stays), errors as ValueError.
§4 SPECIFICATION
    find_connect(candidates=None) -> Path | None; list_profiles(exe, timeout=20) -> [VpnProfile(id, name, host)];
    import_profile(exe, path, name='', timeout=30) -> str (the reply); connect(exe, profile_id, quiet=True);
    disconnect(exe, quiet=True) — quiet: on macOS the window OpenVPN Connect opens for the command is hidden
    (started hidden by «open -n -g -j», keep_hidden(exe) for HIDE_FOR_S; bundle_id(exe)), so it does not lie over the program; reveal(exe) shows it again;
    wait_connected(exe, host, port, seconds=60, check=None, pause=None, step=None) -> bool — shows it after
    REVEAL_AFTER_S without an answer of the server (it may be asking for a password);
    reachable(host, port, timeout=2.0) -> bool; parse_profiles(text) -> [VpnProfile].
§7 TEST CASES tests/sextant/test_vpn.py (a fake OpenVPN Connect, a local listening socket).
§8' ROBUSTNESS
    A missing app, a timeout or an unreadable reply gives ValueError with a message, never a hang of the window
    (every call has a timeout; connect does not wait).
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from azimuth.i18n import tr

MAC_APPS = (
    Path('/Applications/OpenVPN Connect.app/Contents/MacOS/OpenVPN Connect'),
    Path('/Applications/OpenVPN Connect/OpenVPN Connect.app/Contents/MacOS/OpenVPN Connect'),
)
WINDOWS_APPS = (Path(r'C:\Program Files\OpenVPN Connect\OpenVPN Connect.exe'),
                Path(r'C:\Program Files\OpenVPN\bin\openvpn-gui.exe'),  # OpenVPN GUI of the community
                Path(r'C:\Program Files (x86)\OpenVPN\bin\openvpn-gui.exe'))
GUI_NAME = 'openvpn-gui'  # the executable of OpenVPN GUI (without .exe)


def is_gui(exe):
    """The client is OpenVPN GUI (openvpn-gui.exe), not OpenVPN Connect."""
    return exe is not None and Path(exe).stem.lower() == GUI_NAME


def app_name(exe):
    return 'OpenVPN GUI' if is_gui(exe) else 'OpenVPN Connect'


@dataclass(frozen=True)
class VpnProfile:
    id: str
    name: str
    host: str = ''


def find_connect(candidates=None):
    if candidates is None:
        candidates = MAC_APPS if sys.platform == 'darwin' else WINDOWS_APPS if os.name == 'nt' else ()
    for path in candidates:
        path = Path(path)
        if path.is_file() and os.access(path, os.X_OK):
            return path
    return None


def _run(exe, args, timeout):
    try:
        done = subprocess.run([str(exe), *args], capture_output=True, text=True, timeout=timeout, check=False,
                              encoding='utf-8', errors='replace')  # not the locale code page
    except subprocess.TimeoutExpired as exc:
        raise ValueError(tr('OpenVPN Connect не ответил вовремя.')) from exc
    except OSError as exc:
        raise ValueError(tr('Не удалось запустить OpenVPN Connect: ') + str(exc)) from exc
    return (done.stdout or '') + (done.stderr or '')


def _json_in(text):
    decoder = json.JSONDecoder()
    for i, ch in enumerate(text):
        if ch in '[{':
            try:
                value, _ = decoder.raw_decode(text[i:])
                return value
            except ValueError:
                continue
    return None


def _field(item, *names):
    lower = {str(k).lower(): v for k, v in item.items()}
    for name in names:
        if name in lower and lower[name] not in (None, ''):
            return str(lower[name])
    return ''


def parse_profiles(text):
    value = _json_in(text or '')
    if isinstance(value, dict):
        if str(value.get('status', '')).lower() == 'error':
            raise ValueError(tr('OpenVPN Connect: ') + str(value.get('message') or value.get('error') or 'error'))
        for key in ('profiles', 'data', 'result', 'items'):
            if isinstance(value.get(key), list):
                value = value[key]
                break
    if not isinstance(value, list):
        raise ValueError(tr('Не удалось прочитать список профилей OpenVPN Connect.'))
    found = []
    for item in value:
        if isinstance(item, dict):
            pid = _field(item, 'id', 'profileid', 'profile_id')
            if pid:
                found.append(VpnProfile(pid, _field(item, 'name', 'profilename', 'profile_name') or pid,
                                        _field(item, 'host', 'hostname', 'server')))
    return found


def gui_config_dirs(exe):
    """The folders OpenVPN GUI takes its connections from: the user's and the one of its installation."""
    home = Path(os.environ.get('USERPROFILE') or Path.home())
    return [home / 'OpenVPN' / 'config', Path(exe).resolve().parent.parent / 'config']


def gui_profiles(folders):
    """The connections of OpenVPN GUI: every .ovpn of the folders (subfolders too), the name — the file without .ovpn
    (as the GUI names them), the host — of its first «remote» line."""
    found, seen = [], set()
    for folder in folders:
        try:
            files = sorted(Path(folder).rglob('*.ovpn'))
        except OSError:
            continue
        for path in files:
            if path.stem in seen:
                continue
            seen.add(path.stem)
            host = ''
            try:
                for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
                    words = line.split()
                    if len(words) >= 2 and words[0].lower() == 'remote':
                        host = words[1]
                        break
            except OSError:
                pass
            found.append(VpnProfile(path.stem, path.stem, host))
    return found


def list_profiles(exe, timeout=20):
    if is_gui(exe):
        return gui_profiles(gui_config_dirs(exe))
    return parse_profiles(_run(exe, ['--list-profiles'], timeout))


def import_profile(exe, path, name='', timeout=30):
    if is_gui(exe):  # OpenVPN GUI reads its config folder: the file is put there
        import shutil

        target = gui_config_dirs(exe)[0]
        try:
            target.mkdir(parents=True, exist_ok=True)
            copied = target / ((name or Path(path).stem) + '.ovpn')
            shutil.copyfile(path, copied)
        except OSError as exc:
            raise ValueError(tr('Не удалось положить профиль в папку OpenVPN GUI: ') + str(exc)) from exc
        return str(copied)
    args = [f'--import-profile={path}'] + ([f'--name={name}'] if name else [])
    reply = _run(exe, args, timeout)
    value = _json_in(reply)
    if isinstance(value, dict) and str(value.get('status', '')).lower() == 'error':
        raise ValueError(tr('OpenVPN Connect: ') + str(value.get('message') or value.get('error') or 'error'))
    return reply


HIDE_FOR_S, HIDE_EVERY_S = 6.0, 0.05  # after a command OpenVPN Connect may bring its window up: hidden at once, for 6 s
OPEN = '/usr/bin/open'
REVEAL_AFTER_S = 15.0  # not connected by then — its window is shown: it may be asking for a password


def bundle_id(exe):
    """CFBundleIdentifier of the application exe lies in (…/X.app/Contents/MacOS/exe), or None."""
    import plistlib

    try:
        info = Path(exe).resolve().parent.parent / 'Info.plist'
        with open(info, 'rb') as handle:
            return plistlib.load(handle).get('CFBundleIdentifier') or None
    except (OSError, ValueError):
        return None


def _hide_mac(identifier):
    """[NSRunningApplication hide] of every running application with this bundle identifier — through the
    Objective-C runtime (ctypes; no PyObjC in the program). Hiding another application needs no permission of
    the system (controlling it through System Events would). Returns how many were hidden."""
    import ctypes
    import ctypes.util

    objc = ctypes.cdll.LoadLibrary(ctypes.util.find_library('objc'))
    ctypes.cdll.LoadLibrary(ctypes.util.find_library('AppKit'))
    objc.objc_getClass.restype = ctypes.c_void_p
    objc.objc_getClass.argtypes = [ctypes.c_char_p]
    objc.sel_registerName.restype = ctypes.c_void_p
    objc.sel_registerName.argtypes = [ctypes.c_char_p]

    def send(target, selector, *args, restype=ctypes.c_void_p, argtypes=()):
        call = ctypes.cast(objc.objc_msgSend, ctypes.CFUNCTYPE(restype, ctypes.c_void_p, ctypes.c_void_p, *argtypes))
        return call(target, objc.sel_registerName(selector), *args)

    pool = send(send(objc.objc_getClass(b'NSAutoreleasePool'), b'alloc'), b'init')
    try:
        text = send(objc.objc_getClass(b'NSString'), b'stringWithUTF8String:', identifier.encode('utf-8'),
                    argtypes=(ctypes.c_char_p,))
        apps = send(objc.objc_getClass(b'NSRunningApplication'), b'runningApplicationsWithBundleIdentifier:', text,
                    argtypes=(ctypes.c_void_p,))
        hidden = 0
        for k in range(send(apps, b'count', restype=ctypes.c_ulong) if apps else 0):
            app = send(apps, b'objectAtIndex:', k, argtypes=(ctypes.c_ulong,))
            hidden += bool(send(app, b'hide', restype=ctypes.c_bool))
        return hidden
    finally:
        send(pool, b'drain')


def hide(exe):
    """The window of OpenVPN Connect taken off the screen (macOS: the application hidden, as ⌘H — the application
    in front before it comes back); 0 where it cannot be done (Windows, Linux, an application that is not running).
    Never an exception: the VPN is a help."""
    if sys.platform != 'darwin':
        return 0
    identifier = bundle_id(exe)
    if not identifier:
        return 0
    try:
        return _hide_mac(identifier)
    except Exception:  # noqa: BLE001 — a system without AppKit for this process, a changed runtime
        return 0


def reveal(exe):
    """The window of OpenVPN Connect in front again (it did not connect: it may be asking something)."""
    if sys.platform != 'darwin':
        return False
    app = application(exe)
    if app is None:
        return False
    try:
        subprocess.Popen([OPEN, '-a', str(app)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except OSError:
        return False


def application(exe):
    """The .app the executable lies in (macOS), or None."""
    return next((p for p in Path(exe).resolve().parents if p.suffix == '.app'), None)


def keep_hidden(exe, seconds=HIDE_FOR_S, every=HIDE_EVERY_S, pause=None):
    """For seconds the window of OpenVPN Connect is taken off the screen whenever it shows (hide every `every` s): the
    command makes the application bring its window up by itself, at a moment that is not known. Returns how many
    times something was hidden."""
    import time

    pause = pause or time.sleep
    end, times = time.monotonic() + seconds, 0
    while time.monotonic() < end:
        times += bool(hide(exe))
        pause(every)
    return times


def _start(exe, args, quiet=True):
    """The command given to OpenVPN Connect. Quiet (macOS): started through «open -n -g -j» — in the background and
    hidden, so the application is not brought in front of the program (the owner, 2026-11-23: «чтобы он подключал
    openvpn не разворачивая приложение»; started by its executable it came in front and was hidden 0.6 s later — a
    flash); a running OpenVPN Connect gets the command from this second copy, which ends at once, and what it shows
    by itself is hidden within HIDE_EVERY_S (keep_hidden)."""
    command = [str(exe), *args]
    if os.name == 'nt' and is_gui(exe):  # OpenVPN GUI lives in the tray; its own windows (the password) stay
        try:
            subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError as exc:
            raise ValueError(tr('Не удалось запустить OpenVPN GUI: ') + str(exc)) from exc
        return
    bundle = application(exe) if quiet and sys.platform == 'darwin' and bundle_id(exe) else None
    if bundle is not None:
        command = [OPEN, '-n', '-g', '-j', '-a', str(bundle), '--args', *args]
    try:
        subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=os.name != 'nt')
    except OSError as exc:
        if bundle is None:
            raise ValueError(tr('Не удалось запустить OpenVPN Connect: ') + str(exc)) from exc
        try:  # no «open» (it is a part of macOS): the executable itself, as before
            subprocess.Popen([str(exe), *args], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        except OSError as again:
            raise ValueError(tr('Не удалось запустить OpenVPN Connect: ') + str(again)) from again
    if bundle is not None:
        import threading

        threading.Thread(target=keep_hidden, args=(exe,), name='azimuth-vpn-hide', daemon=True).start()


def gui_running(exe):
    """Whether OpenVPN GUI is running (Windows: tasklist); False when it cannot be told."""
    try:
        done = subprocess.run(['tasklist', '/FI', f'IMAGENAME eq {Path(exe).name}', '/NH'], capture_output=True,
                              text=True, encoding='utf-8', timeout=10, check=False, errors='replace',
                              creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    except (OSError, subprocess.TimeoutExpired):
        return False
    return Path(exe).name.lower() in (done.stdout or '').lower()


def connect(exe, profile_id, quiet=True, running=None):
    if not profile_id:
        raise ValueError(tr('Не выбран профиль VPN.'))
    if is_gui(exe):
        running = gui_running(exe) if running is None else running
        _start(exe, ['--command', 'connect', profile_id] if running else ['--connect', profile_id], False)
        return
    _start(exe, [f'--connect-shortcut={profile_id}'], quiet)


def disconnect(exe, quiet=True, running=None):
    if is_gui(exe):
        if (gui_running(exe) if running is None else running):
            _start(exe, ['--command', 'disconnect_all'], False)
        return
    _start(exe, ['--disconnect-shortcut'], quiet)


def wait_connected(exe, host, port, seconds=60.0, check=None, pause=None, step=None):
    """Wait until host:port answers (the VPN is up), at most seconds; after REVEAL_AFTER_S without an answer the
    window of OpenVPN Connect is shown once — it may be asking for a password. Step() False — given up
    (InterruptedError). True when the server answered."""
    import time

    check, pause = check or reachable, pause or time.sleep
    started, revealed = time.monotonic(), False
    while time.monotonic() - started < seconds:
        if check(host, port, 1.5):
            return True
        if step is not None and step() is False:
            raise InterruptedError
        if not revealed and time.monotonic() - started >= REVEAL_AFTER_S:
            revealed = True
            reveal(exe)
        pause(2.0)
    return False


def reachable(host, port, timeout=2.0):
    """Whether host:port answers within timeout seconds — the search of the name included: the timeout of
    socket.create_connection does not cover it, and an unknown name took 30 s on macOS (the timing of the
    tests; the window of the server asks this while it is shown). The name is looked up in a thread of its own; not
    found in time — False."""
    import threading
    import time

    try:
        port = int(port)
    except (TypeError, ValueError):
        return False
    started = time.monotonic()
    found = []

    def look_up():
        try:
            found.append(socket.getaddrinfo(host, port, type=socket.SOCK_STREAM))
        except (OSError, UnicodeError, ValueError):
            found.append(None)

    worker = threading.Thread(target=look_up, name='azimuth-vpn-lookup', daemon=True)
    worker.start()
    worker.join(timeout)
    if not found or not found[0]:
        return False
    for family, kind, proto, _, address in found[0]:
        left = timeout - (time.monotonic() - started)
        if left <= 0:
            return False
        try:
            with socket.socket(family, kind, proto) as connection:
                connection.settimeout(left)
                connection.connect(address)
                return True
        except OSError:
            continue
    return False
