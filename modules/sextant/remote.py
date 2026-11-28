"""Sextant: the server profile for calculations on a cluster (the environment lines of the job).

HEADER «Где считать» in the card «Запуск расчёта»: on this computer (runner.Job) or on a server. The profile of the
    server is what the user enters for his own access: the address, the port, the login, the folder of calculations on
    the server and the command that starts ORCA there (for the laboratory cluster: «module load run_mpi && orca.sh -i
    {folder}», docs/features/REMOTE_CALCULATIONS.md). The password is never stored — it is asked at the connection;
    OpenVPN, if the server needs it, is switched on by the user. The calculation is sent with the program's own job.sh
    (cluster.job_script); the profile keeps the lines that put ORCA into PATH there («setup», e.g. «module load
    orca-6.1.1»); empty — they are found on the server (cluster.suggested_setup). The start command of 0.63.0 is kept in
    old profiles but no longer used or required. Wilkinson convention, sections 1-8.

§2 ALGORITHM
    The profile is kept in the settings of the program as one JSON text (key server/profile), without a password.
    validate() lists what is missing or wrong; remote_command(name) is the line run on the server: «cd <folder> &&
    <command with {folder} = the name of the calculation folder>»; a folder beginning with «~/» stays under $HOME (the
    tilde is not quoted away), every name is quoted for the shell.
    The environment lines: setup — for every job of the profile; setups {kind: lines} — for the jobs of one program
    only (SETUP_KINDS; the owner, 2026-11-22: «окно для строк окружения для каждой программы отдельно» — the lines of
    CP2K must not reach a job of ORCA). setup_of(kind) -> its lines; with them the program is not looked for on the
    server (cluster.setup_for): they are the user's choice for it.
§4 SPECIFICATION ServerProfile(name, host, port, user, folder, command, jump, vpn_id, vpn_name, vpn_disconnect, setup):
    validate() -> [str]; ready() -> bool; address() -> 'user@host:port'; remote_command(name) -> str; to_dict();
    ServerProfile.from_dict(d). load_all(settings) -> [ServerProfile]; save_all(settings, profiles, current=None);
    load(settings) -> the chosen ServerProfile; save(settings, profile, old_title=None); remove(settings, title).
    WHERE_KEY, PROFILES_KEY, CURRENT_KEY. The password is never here: keychain.py. partition, time_limit, account, qos —
    the #SBATCH -p / -t / -A / --qos of every job of the profile (empty — not written: the defaults of the cluster);
    directives() -> ['#SBATCH -p …', …]; validate() checks them (a name of letters, digits, «._-,»; a time as SLURM
    writes it: «MM», «MM:SS», «HH:MM:SS», «D-HH», «D-HH:MM», «D-HH:MM:SS»). Other #SBATCH lines (--gres, --constraint…)
    go into the setup lines: the job script puts them into its head.
§7 TEST CASES tests/sextant/test_remote.py.
§8' ROBUSTNESS
    A damaged JSON in the settings gives an empty profile, never an exception.
"""

from __future__ import annotations

import json
import re
import shlex
from dataclasses import asdict, dataclass, field, fields

from azimuth.i18n import tr

WHERE_KEY = 'sextant_where'  # 'local' or 'server'
PROFILE_KEY = 'server/profile'  # the single profile of the first version
PROFILES_KEY = 'server/profiles'
CURRENT_KEY = 'server/current'
DEFAULT_FOLDER = '~/azimuth/calculations'
SETUP_KINDS = ('orca', 'mopac', 'xtb', 'qe', 'cp2k')  # the programs a server runs (remote_job.PROGRAM_TITLES)
DEFAULT_COMMAND = 'module load run_mpi && orca.sh -i {folder}'
_HOST = re.compile(r'^[A-Za-z0-9._\-\[\]:]+$')
_USER = re.compile(r'^[A-Za-z0-9._\-]+$')
_SLURM_NAME = re.compile(r'^[A-Za-z0-9._,\-]+$')
_SLURM_TIME = re.compile(r'^(\d+-\d{1,2}(:\d{2}){0,2}|\d+(:\d{2}){0,2})$')


@dataclass
class ServerProfile:
    name: str = ''
    host: str = ''
    port: int = 22
    user: str = ''
    folder: str = DEFAULT_FOLDER
    command: str = DEFAULT_COMMAND
    jump: str = ''  # an intermediate server (ProxyJump), user@host:port; empty — none
    vpn_id: str = ''  # the profile of OpenVPN Connect switched on when the server does not answer (vpn.py)
    vpn_name: str = ''
    vpn_disconnect: bool = False  # switch the VPN off when no calculation is left on the server
    setup: str = ''  # lines for job.sh that put ORCA (and MPI) into PATH; '' — found on the server
    partition: str = ''  # #SBATCH -p; '' — the default partition of the cluster
    time_limit: str = ''  # #SBATCH -t (e.g. 2-00:00:00); '' — the default limit of the partition
    account: str = ''  # #SBATCH -A
    qos: str = ''  # #SBATCH --qos
    # the lines of job.sh of one program only ({kind: text}, kinds of SETUP_KINDS): setup above goes into every job of
    # the profile, and the lines CP2K needs («source …/toolchain/install/setup») have no place in a job of ORCA
    setups: dict = field(default_factory=dict)

    def setup_of(self, kind):
        """The lines of the program kind alone ('' — none: they are found on the server)."""
        value = (self.setups or {}).get(kind, '')
        return value.strip() if isinstance(value, str) else ''

    def directives(self):
        out = []
        for option, value in (('-p', self.partition), ('-t', self.time_limit), ('-A', self.account),
                              ('--qos=', self.qos)):
            value = (value or '').strip()
            if value:
                out.append(f'#SBATCH {option}{value}' if option.endswith('=') else f'#SBATCH {option} {value}')
        return out

    def validate(self):
        problems = []
        if not self.host.strip():
            problems.append(tr('Укажите адрес сервера.'))
        elif not _HOST.match(self.host.strip()):
            problems.append(tr('В адресе сервера — только буквы, цифры, точки и дефисы.'))
        if type(self.port) is not int or not 1 <= self.port <= 65535:
            problems.append(tr('Порт — целое число от 1 до 65535.'))
        if not self.user.strip():
            problems.append(tr('Укажите логин.'))
        elif not _USER.match(self.user.strip()):
            problems.append(tr('В логине — только латинские буквы, цифры, точка, дефис и подчёркивание.'))
        if not self.folder.strip():
            problems.append(tr('Укажите папку расчётов на сервере.'))
        elif any(ch in self.folder for ch in '\n\r\0'):
            problems.append(tr('Папка расчётов — одной строкой.'))
        if any(ch in self.command for ch in '\n\r\0'):  # 0.63.0 field, unused
            problems.append(tr('Команда запуска — одной строкой.'))
        if '\0' in self.setup or any('\0' in self.setup_of(kind) for kind in SETUP_KINDS):
            problems.append(tr('В строках окружения — недопустимый символ.'))
        for title, value in ((tr('Раздел (partition)'), self.partition), (tr('Проект (account)'), self.account),
                             ('QoS', self.qos)):
            if value.strip() and not _SLURM_NAME.match(value.strip()):
                problems.append(tr('{} — латинские буквы, цифры, точка, запятая, дефис и подчёркивание.').format(title))
        if self.time_limit.strip() and not _SLURM_TIME.match(self.time_limit.strip()):
            problems.append(tr('Предел времени — как в SLURM: 90 (минуты), 12:00:00 или 2-00:00:00 (дни-часы).'))
        if self.jump.strip() and not re.match(r'^([A-Za-z0-9._\-]+@)?[A-Za-z0-9._\-]+(:\d+)?$', self.jump.strip()):
            problems.append(tr('Промежуточный сервер: логин@адрес:порт.'))
        return problems

    def ready(self):
        return not self.validate()

    def address(self):
        return f'{self.user.strip()}@{self.host.strip()}:{self.port}'

    def title(self):
        return self.name.strip() or self.host.strip()

    def remote_command(self, name):
        folder = self.folder.strip()
        if folder == '~':
            where = '"$HOME"'
        elif folder.startswith('~/'):
            where = '"$HOME"/' + shlex.quote(folder[2:])
        else:
            where = shlex.quote(folder)
        return f'cd {where} && ' + self.command.strip().replace('{folder}', shlex.quote(name))

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        known = {f.name for f in fields(cls)}
        values = {k: v for k, v in (data or {}).items() if k in known}
        profile = cls(**values)
        try:
            profile.port = int(profile.port)
        except (TypeError, ValueError):
            profile.port = 22
        for name in ('name', 'host', 'user', 'folder', 'command', 'jump', 'vpn_id', 'vpn_name', 'setup', 'partition',
                     'time_limit', 'account', 'qos'):
            if not isinstance(getattr(profile, name), str):
                setattr(profile, name, '')
        profile.vpn_disconnect = profile.vpn_disconnect is True
        given = profile.setups if isinstance(profile.setups, dict) else {}
        profile.setups = {kind: given[kind].strip() for kind in SETUP_KINDS
                          if isinstance(given.get(kind), str) and given[kind].strip()}
        return profile


def load_all(settings):
    """All saved profiles (several; the single profile of the first version is taken over)."""
    try:
        text = settings.value(PROFILES_KEY, '')
        items = json.loads(text) if text else []
        profiles = [ServerProfile.from_dict(d) for d in items if isinstance(d, dict)]
    except (TypeError, ValueError):
        profiles = []
    if not profiles:
        try:
            old = settings.value(PROFILE_KEY, '')
            if old:
                profiles = [ServerProfile.from_dict(json.loads(old))]
        except (TypeError, ValueError):
            pass
    return profiles


def save_all(settings, profiles, current=None):
    settings.setValue(PROFILES_KEY, json.dumps([p.to_dict() for p in profiles], ensure_ascii=False))
    if current is not None:
        settings.setValue(CURRENT_KEY, current)


def load(settings):
    """The profile chosen last (or the first one, or an empty one)."""
    profiles = load_all(settings)
    current = settings.value(CURRENT_KEY, '') or ''
    for profile in profiles:
        if profile.title() == current:
            return profile
    return profiles[0] if profiles else ServerProfile()


def save(settings, profile, old_title=None):
    """Save a profile under its title (replacing the one called old_title or the same title) and choose it."""
    profiles = load_all(settings)
    titles = {old_title, profile.title()} - {None}
    profiles = [p for p in profiles if p.title() not in titles]
    profiles.append(profile)
    save_all(settings, profiles, profile.title())
    return profiles


def remove(settings, title):
    profiles = [p for p in load_all(settings) if p.title() != title]
    save_all(settings, profiles, profiles[0].title() if profiles else '')
    return profiles
