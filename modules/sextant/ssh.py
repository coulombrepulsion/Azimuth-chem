"""Sextant: commands and files on a calculation server through the system ssh and scp.

HEADER
    Every call to a server goes through this module: a command (`run`), a folder up (`upload`), files down
    (`download`). It uses the OpenSSH programs of the system (macOS, Linux, Windows 10+), not a library of its own, so
    the user's keys, ~/.ssh/config, ssh-agent and ProxyJump work as in the Terminal. The password, when the server asks
    for one, comes from the program (the window of Sextant or the Keychain, keychain.py) and is never written to disk or
    put on a command line.
    Wilkinson convention, sections 1-8.

§1 THEORY
    OpenSSH asks for a password through the program named in SSH_ASKPASS when SSH_ASKPASS_REQUIRE=force (OpenSSH 8.4+;
    macOS 12+ has 8.6 or newer). With ControlMaster=auto and a ControlPath the first connection stays open
    (ControlPersist) and every later ssh or scp with the same ControlPath goes through it without a new login — the
    password is asked once per session, and the polling of a calculation (every ~10 s) costs no new handshake.
    Exit code 255 of ssh is its own failure (connection, authentication, host key); any other code is the code of the
    remote command.

§2 ALGORITHM
    options(): -p port, ControlMaster=auto, ControlPath=<control dir>/%C, ControlPersist=10 min, ConnectTimeout=10,
    ServerAliveInterval=15 × 3, StrictHostKeyChecking=accept-new (the key of a new server is remembered in
    known_hosts as after «yes» in the Terminal; a changed key is refused), NumberOfPasswordPrompts=1, -J for the
    intermediate server. environment(): with a password, SSH_ASKPASS = a small script in the control folder that
    prints the variable AZIMUTH_SSH_SECRET, which exists only in the environment of that ssh process;
    SSH_ASKPASS_REQUIRE=force; DISPLAY set (older OpenSSH wants it); stdin closed.
    run(command): ssh <options> user@host <command>; the answer is Result(code, out bytes, err text);
    code 255 → SshError with a kind from the error text. upload(folder, parent): mkdir -p on the server, then
    scp -r -q. Upload_packed(folders, parent, then) — one .tar.gz, one scp, one ssh (unpack + then).
    download(names, remote_dir, folder): one scp with all the remote files. close(): ssh -O exit.
    Remote paths: «~/x» is turned into «x» for scp (relative to the home folder) and into "$HOME"/x for the shell.

§3 APPLICATIONS
    modules/sextant/remote_job.py (sending and watching a calculation), modules/sextant/cluster.py (the probe of
    the server), the «Проверить подключение» button of the server dialog.

§4 SPECIFICATION
    Connection(profile, password=None, ssh='ssh', scp='scp', control_dir=None, timeout=30)
        .options() -> [str]; .target() -> 'user@host'; .environment() -> dict
        .run(command, timeout=None) -> Result(code: int, out: bytes, err: str); raises SshError
        .text(command, timeout=None) -> str (stdout decoded; non-zero code of the command → SshError kind 'command')
        .upload(local_folder, remote_parent) ; .download(names, remote_dir, local_folder) ; .close()
    SshError(message, kind) with kind ∈ KINDS; classify(text) -> kind; shell_path(path) -> str; scp_path(path) -> str.

§5 PROCEDURES — below.

§6 NOTES
    ASSUMPTION: OpenSSH ≥ 8.4 on the user's computer (SSH_ASKPASS_REQUIRE). Windows OpenSSH has no ControlMaster:
    0.89.17 — the Control options are not given there (each command logs in anew); the password goes through
    askpass.cmd (Python prints it), and «Вход без пароля» (ensure_key, install_command; server_access.set_up_key) puts
    the key of the program (~/.ssh/azimuth_ed25519, without a passphrase) on the server once, so no password is needed.
    The control socket lives in /tmp/az-ssh-<uid> (macOS limits the socket path to 104 characters; the per-user
    folder in /var/folders is too long), mode 0700.

§7 TEST CASES tests/sextant/test_ssh.py (fake ssh and scp that run on this computer).

§8' ROBUSTNESS
    Every call has a timeout; a timeout, a missing ssh or an exit code 255 raise SshError with a message for the
    user, never hang the window (the calls are made from a worker thread, remote_job.py).
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from azimuth.i18n import tr

KINDS = ('connection', 'auth', 'hostkey', 'timeout', 'missing', 'command')
_PATTERNS = (
    ('hostkey', r'REMOTE HOST IDENTIFICATION HAS CHANGED|Host key verification failed|host key .* changed'),
    ('auth', r'Permission denied|Authentication failed|Too many authentication failures'),
    ('connection', r'Connection timed out|Operation timed out|No route to host|Connection refused|Network is '
                   r'unreachable|Could not resolve hostname|Name or service not known|Connection closed|'
                   r'Connection reset|kex_exchange_identification|banner exchange'),
)
_LOCAL = threading.local()
_ASKPASS_LOCK = threading.Lock()


def abort_on(event):
    """The calls of this thread end at once when event is set (None — not any more): the program of the call (scp, ssh)
    is killed, SshError of the kind 'stopped'. RemoteJob sets it for the upload of a calculation — «Остановить» did not
    end the upload, the files went on and the job was queued (the owner, 2026-11-24)."""
    _LOCAL.abort = event


MESSAGES = {
    'connection': 'Нет связи с сервером. Подключён ли VPN, и верны ли адрес и порт?',
    'auth': 'Сервер не принял логин или пароль.',
    'hostkey': 'Ключ сервера изменился с прошлого входа. Если сервер не переустанавливали, это может быть подмена: '
               'спросите администратора, прежде чем входить.',
    'timeout': 'Сервер не ответил вовремя.',
    'missing': 'Не найдена программа ssh. На macOS и Linux она есть всегда; на Windows включите «Клиент OpenSSH» в '
               'дополнительных компонентах.',
    'command': 'Команда на сервере завершилась с ошибкой.',
}


def key_path(home=None):
    """The key of «Вход без пароля» — its own file, so that the user's other keys are not touched."""
    return Path(home or Path.home()) / '.ssh' / 'azimuth_ed25519'


_PUBLIC = re.compile(r'^ssh-ed25519 [A-Za-z0-9+/=]+( [A-Za-z0-9._@-]+)?$')


def ensure_key(home=None, keygen='ssh-keygen', comment='azimuth'):
    """The private key file and the text of its public half; made with ssh-keygen (macOS, Linux, Windows 10+)
    without a passphrase when there is none yet. Raises SshError with a message for the user."""
    private = key_path(home)
    public = private.with_name(private.name + '.pub')
    if not (private.is_file() and public.is_file()):
        private.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            done = subprocess.run([keygen, '-q', '-t', 'ed25519', '-N', '', '-C', comment, '-f', str(private)],
                                  stdin=subprocess.DEVNULL, capture_output=True, timeout=30)
        except (OSError, subprocess.SubprocessError) as exc:
            raise SshError(tr(MESSAGES['missing']), 'missing') from exc
        if done.returncode != 0 or not public.is_file():
            raise SshError(tr('Ключ не создан: ') + done.stderr.decode('utf-8', 'replace').strip(), 'command')
    text = public.read_text(encoding='ascii', errors='replace').strip()
    if not _PUBLIC.match(text):
        raise SshError(tr('Файл ключа повреждён: ') + str(public), 'command')
    return private, text


def install_command(public_text):
    """The shell command that adds the public key to ~/.ssh/authorized_keys once (as ssh-copy-id does)."""
    if not _PUBLIC.match(public_text):
        raise ValueError(public_text)
    key = shlex.quote(public_text)
    return ('umask 077 && mkdir -p ~/.ssh && touch ~/.ssh/authorized_keys && '
            f'(grep -qxF {key} ~/.ssh/authorized_keys || printf "%s\\n" {key} >> ~/.ssh/authorized_keys)')


class SshError(ValueError):
    def __init__(self, message, kind='connection'):
        super().__init__(message)
        self.kind = kind


@dataclass(frozen=True)
class Result:
    code: int
    out: bytes
    err: str


def classify(text):
    """The kind of an ssh failure from what ssh printed (exit code 255)."""
    for kind, pattern in _PATTERNS:
        if re.search(pattern, text or '', re.I):
            return kind
    return 'connection'


def shell_path(path):
    """A server path for the remote shell: «~/a b» → "$HOME"/'a b'; others quoted."""
    path = path.strip()
    if path == '~':
        return '"$HOME"'
    if path.startswith('~/'):
        return '"$HOME"/' + shlex.quote(path[2:])
    return shlex.quote(path)


def scp_path(path):
    """A server path for scp: relative to the home folder when it starts with «~/»."""
    path = path.strip()
    if path == '~':
        return '.'
    return path[2:] if path.startswith('~/') else path


def _control_dir():
    base = Path('/tmp') if os.name != 'nt' else Path(tempfile.gettempdir())
    folder = base / f'az-ssh-{os.getuid() if hasattr(os, "getuid") else "user"}'
    folder.mkdir(mode=0o700, exist_ok=True)
    try:
        os.chmod(folder, 0o700)
    except OSError:
        pass
    return folder


class Connection:
    def __init__(self, profile, password=None, ssh='ssh', scp='scp', control_dir=None, timeout=30, windows=None,
                 key=None, batch=False):
        self.profile = profile
        self.password = password or None
        self.windows = os.name == 'nt' if windows is None else windows
        self.key = Path(key) if key is not None else key_path()  # used when the file exists
        self.batch = batch  # no password at all (the check of «Вход без пароля»)
        self.ssh = ssh
        self.scp = scp
        self.control = Path(control_dir) if control_dir else _control_dir()
        self.timeout = timeout

    # -- options -----------------------------------------------------------------------------
    def target(self):
        return f'{self.profile.user.strip()}@{self.profile.host.strip()}'

    def _common(self):
        # the OpenSSH of Windows has no ControlMaster (no Unix sockets): every command logs in anew there
        options = [] if self.windows else [
            '-o', 'ControlMaster=auto',
            '-o', f'ControlPath={self.control / "%C"}',
            '-o', 'ControlPersist=600',
        ]
        if self.key is not None and self.key.is_file():
            options += ['-i', str(self.key)]  # the key of «Вход без пароля»; the user's own keys still work
        if self.batch:
            options += ['-o', 'BatchMode=yes']
        options += [
            '-o', 'ConnectTimeout=10',
            '-o', 'ServerAliveInterval=15',
            '-o', 'ServerAliveCountMax=3',
            '-o', 'StrictHostKeyChecking=accept-new',
            '-o', 'NumberOfPasswordPrompts=1',
        ]
        jump = (self.profile.jump or '').strip()
        if jump:
            options += ['-J', jump]
        return options

    def options(self):
        return ['-p', str(int(self.profile.port))] + self._common()

    def _askpass(self):
        if self.windows:  # a .cmd that prints the variable through Python (any character of the password)
            # no path in the .cmd — cmd.exe reads it in the OEM code page, and a Python under
            # «C:\\Users\\Сергей\\…» would not start; the Python comes from AZIMUTH_SSH_PYTHON of environment()
            helper = self.control / 'askpass.cmd'
            if getattr(sys, 'frozen', False):  # the .exe of the installer has no Python to run — PowerShell
                text = '@powershell -NoProfile -NonInteractive -Command "[Console]::Out.WriteLine($env:AZIMUTH_SSH_SECRET)"\r\n'
            else:
                text = ('@"%AZIMUTH_SSH_PYTHON%" -c "import os,sys;'
                        'sys.stdout.write(os.environ.get(\'AZIMUTH_SSH_SECRET\',\'\')+chr(10))"\r\n')
            # written only when it differs: it was written before every login, and the watchers of two calculations
            # (threads) wrote it while the ssh of another was running it (Windows locks a file in use)
            try:
                same = helper.read_bytes() == text.encode('ascii')
            except (OSError, ValueError):
                same = False
            if not same:
                with _ASKPASS_LOCK:
                    temporary = helper.with_name(f'askpass-{os.getpid()}-{threading.get_ident()}.tmp')
                    temporary.write_text(text, encoding='ascii', newline='')
                    try:
                        os.replace(temporary, helper)
                    except OSError:  # in use by a login now — it has the same text
                        temporary.unlink(missing_ok=True)
            return helper
        helper = self.control / 'askpass.sh'
        if not helper.exists():
            helper.write_text('#!/bin/sh\nprintf \'%s\\n\' "$AZIMUTH_SSH_SECRET"\n', encoding='ascii')
            os.chmod(helper, 0o700)
        return helper

    def environment(self):
        env = dict(os.environ)
        if self.password:
            env['SSH_ASKPASS'] = str(self._askpass())
            env['SSH_ASKPASS_REQUIRE'] = 'force'
            env.setdefault('DISPLAY', ':0')
            env['AZIMUTH_SSH_SECRET'] = self.password
            if self.windows:
                import sys

                python = Path(sys.executable)
                console = python.with_name('python.exe')  # pythonw.exe of the window has no standard output
                env['AZIMUTH_SSH_PYTHON'] = str(console if console.is_file() else python)
        return env

    # -- calls -------------------------------------------------------------------------------
    def _call(self, args, timeout):
        abort = getattr(_LOCAL, 'abort', None)
        try:
            if abort is None:
                done = subprocess.run(
                    args, stdin=subprocess.DEVNULL, capture_output=True, env=self.environment(),
                    timeout=timeout or self.timeout,
                )
            else:
                done = self._stoppable(args, timeout or self.timeout, abort)
        except FileNotFoundError as exc:
            raise SshError(tr(MESSAGES['missing']), 'missing') from exc
        except subprocess.TimeoutExpired as exc:
            raise SshError(tr(MESSAGES['timeout']), 'timeout') from exc
        err = done.stderr.decode('utf-8', errors='replace')
        if done.returncode == 255:
            kind = classify(err)
            detail = err.strip().splitlines()[-1] if err.strip() else ''
            raise SshError(tr(MESSAGES[kind]) + (f' ({detail})' if detail else ''), kind)
        return Result(done.returncode, done.stdout, err)

    def _stoppable(self, args, timeout, abort):
        """subprocess.run that also ends when abort is set (the program killed, SshError 'stopped')."""
        process = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   env=self.environment())
        end = time.monotonic() + timeout if timeout else None
        while True:
            try:
                out, err = process.communicate(timeout=0.2)
                return subprocess.CompletedProcess(args, process.returncode, out, err)
            except subprocess.TimeoutExpired:
                if abort.is_set() or (end is not None and time.monotonic() > end):
                    process.kill()
                    process.communicate()
                    if abort.is_set():
                        raise SshError(tr('Отправка остановлена.'), 'stopped') from None
                    raise subprocess.TimeoutExpired(args, timeout) from None

    def run(self, command, timeout=None):
        return self._call([self.ssh, *self.options(), self.target(), command], timeout)

    def text(self, command, timeout=None):
        result = self.run(command, timeout)
        if result.code != 0:
            detail = result.err.strip().splitlines()[-1] if result.err.strip() else tr(f'код {result.code}')
            raise SshError(tr(MESSAGES['command']) + f' ({detail})', 'command')
        return result.out.decode('utf-8', errors='replace')

    def upload(self, local_folder, remote_parent, timeout=600):
        local_folder = Path(local_folder)
        self.text(f'mkdir -p {shell_path(remote_parent)}')
        destination = f'{self.target()}:{scp_path(remote_parent)}/'
        args = [self.scp, '-q', '-r', '-P', str(int(self.profile.port)), *self._common(), str(local_folder), destination]
        result = self._call(args, timeout)
        if result.code != 0:
            raise SshError(tr('Не удалось загрузить папку расчёта на сервер: ') + result.err.strip(), 'command')

    def upload_packed(self, folders, remote_parent, then='', timeout=600):
        """Many folders sent as one archive — one scp of a .tar.gz into the home folder of the server and one ssh
        that makes the parent, unpacks it there, removes the archive and runs then (in the parent; «sbatch» of the
        queue) — two exchanges with the server for any number of folders (upload: two for every folder). Returns the
        Result of that ssh; SshError when the archive did not go or was not unpacked."""
        import tarfile
        import uuid

        folders = [Path(f) for f in folders]
        name = f'.az-upload-{uuid.uuid4().hex[:12]}.tar.gz'
        with tempfile.TemporaryDirectory(prefix='azimuth-pack-') as temp:
            archive = Path(temp) / name
            with tarfile.open(archive, 'w:gz', compresslevel=6) as tar:
                for folder in folders:
                    tar.add(str(folder), arcname=folder.name)
            args = [self.scp, '-q', '-P', str(int(self.profile.port)), *self._common(), str(archive),
                    f'{self.target()}:{name}']
            result = self._call(args, timeout)
            if result.code != 0:
                raise SshError(tr('Не удалось загрузить папку расчёта на сервер: ') + result.err.strip(), 'command')
        packed, parent = f'"$HOME"/{name}', shell_path(remote_parent)
        command = (f'mkdir -p {parent} && tar -xzf {packed} -C {parent}; code=$?; rm -f {packed}; '
                   f'if [ $code -ne 0 ]; then echo "tar: $code" >&2; exit 90; fi; cd {parent}'
                   + (f' && {then}' if then else ''))
        result = self.run(command, timeout)
        if result.code == 90:
            raise SshError(tr('Не удалось распаковать папки расчётов на сервере: ') + result.err.strip(), 'command')
        return result

    def download(self, names, remote_dir, local_folder, timeout=1800):
        names = [n for n in names if n and '/' not in n and n not in ('.', '..')]
        if not names:
            return
        base = scp_path(remote_dir).rstrip('/')
        sources = [f'{self.target()}:{base}/{name}' for name in names]
        args = [self.scp, '-q', '-p', '-P', str(int(self.profile.port)), *self._common(), *sources, str(local_folder)]
        result = self._call(args, timeout)
        if result.code != 0:
            raise SshError(tr('Не удалось скачать результат с сервера: ') + result.err.strip(), 'command')

    def put(self, paths, remote_dir, timeout=1800):
        """Files and folders of this computer copied into a folder of the server (scp -r; the file manager)."""
        paths = [str(p) for p in paths]
        if not paths:
            return
        destination = f'{self.target()}:{scp_path(remote_dir).rstrip("/") or "/"}/'
        args = [self.scp, '-q', '-r', '-p', '-P', str(int(self.profile.port)), *self._common(), *paths, destination]
        result = self._call(args, timeout)
        if result.code != 0:
            raise SshError(tr('Не удалось загрузить на сервер: ') + result.err.strip(), 'command')

    def get(self, names, remote_dir, local_folder, timeout=1800):
        """Files and folders of a folder of the server copied here (scp -r; the file manager)."""
        names = [n for n in names if n and '/' not in n and n not in ('.', '..')]
        if not names:
            return
        base = scp_path(remote_dir).rstrip('/')
        sources = [f'{self.target()}:{base}/{name}' for name in names]
        args = [self.scp, '-q', '-r', '-p', '-P', str(int(self.profile.port)), *self._common(), *sources,
                str(local_folder)]
        result = self._call(args, timeout)
        if result.code != 0:
            raise SshError(tr('Не удалось скачать с сервера: ') + result.err.strip(), 'command')

    def install_key(self, public_text):
        """Put the public key on the server (this connection logs in with the password once)."""
        self.text(install_command(public_text), timeout=60)

    def close(self):
        if self.windows:
            return  # no master connection to end
        try:
            subprocess.run(
                [self.ssh, *self.options(), '-O', 'exit', self.target()],
                stdin=subprocess.DEVNULL, capture_output=True, timeout=5, env=self.environment(),
            )
        except (OSError, subprocess.SubprocessError):
            pass
