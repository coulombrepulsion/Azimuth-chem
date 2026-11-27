"""Azimuth without its window: a calculation sent to the SLURM server of a profile of Sextant, watched and read here.

§1 PURPOSE
    The commands of azimuth/headless.py run calculations on this computer; these send one to the server of «Сервер для
    расчётов» — for a language model through tools/azimuth_mcp.py (the owner, 2026-11-22: «доработать программу, чтоб
    ты мог ставить задачи на сервере» — the login by the key, the limits from what the server says is free). The same
    code as the window: remote.ServerProfile of the settings, ssh.Connection, cluster.probe_command / plan / job_script,
    remote_job.prepare_remote and RemoteJob. No Qt here (tests/core/test_architecture_boundaries.py).
§2 RULES — the server is shared, so the limits are in the code, not in the care of the caller:
    1. The login is by the key only (ssh BatchMode): no password is asked, read from the Keychain or given here. A
       server that wants one is refused with what to do («Вход без пароля» of the server window). A server that does
       not answer: OpenVPN Connect is asked to connect the VPN profile the owner chose for it in the server window
       (the owner, 2026-11-22; switch_vpn_on — what the window does itself), its window kept off the screen, and the
       server is asked once more; no profile chosen — said so, nothing is switched on. The VPN is never switched off
       from here.
    2. Only the programs a server runs (remote_job.REMOTE_KINDS: ORCA, MOPAC), found there by the probe.
    3. Cores. A server with SLURM has a queue (the owner, 2026-11-27: «Пусть сам пользователь задает количество ядер —
       если оно больше свободных — встает в очередь»): the cores are those asked for (DEFAULT_CORES without a wish),
       at most cluster.BUSY_SHARE (80 %) of the node for one calculation (queue_ceiling: a larger job would never
       start); more than are free now — sbatch takes the job and it waits (Plan.queued). Memory there: the request
       (processes × memory × 1.25) at most BUSY_SHARE of the memory of the node.
       A server without SLURM (serv1): the calculation is started at once by nohup (azimuth/runtime/runs.py: the
       number is the pid, the time limit kept by timeout), so never more cores than are free now and never so many
       that more than BUSY_SHARE of the node is busy, the cores busy already counted — its load average (the owner,
       2026-11-22; cluster.room, ceiling()); nothing to take — refused; stop ends its own process alone. Memory
       there: the request at most 1 / SHARE of the memory free. Asked for more than a ceiling — refused with the
       ceiling, not cut silently. DEFAULT_MAXCORE per process unless asked.
    4. A time limit is always written: the «-t» of the profile, else HOURS (asked: at most MAX_HOURS).
    5. At most ACTIVE of these calculations at once on a server without SLURM — those of the journal sent to it and
       not known to have ended; a queue of SLURM has no such limit (the owner, 2026-11-27: «такова суть очереди»).
       A sending that never reached the server (no job.json in its folder, and the sending process gone or UNSENT_S
       passed) is written to the journal as ended («not sent») and takes no place.
    6. Every sending is a line of the journal (JOURNAL in the folder of the calculations: the time, the server, the
       folder, the program, the cores, the memory, the limit); its end is another. Only a calculation of the journal
       is taken up again (resume) or stopped; stop is scancel of its own number (RemoteJob.stop). Nothing is deleted
       on the server and no command of the caller is run there.
§3 INTERFACE
    profile(store, name=None) -> ServerProfile (ValueError: none, or what it lacks); connect(profile) -> Connection;
    look(profile, connection, vpn_app=None, vpn_wait=None) -> Resources; switch_vpn_on(profile, app=None, wait=None)
    -> bool; ceiling(resources) -> (cores, physical, free); queue_ceiling(resources) -> the same of a queue;
    choose(resources, cores=None, memory_mb=None) -> cluster.Plan; time_directive(profile, hours=None) -> [str];
    state(store, name=None, root=None, opener=None) -> dict; journal(root) -> [dict]; active(root, now=None, server=None) -> [folders]; close_unsent(root, now=None) -> [folders];
    send(kind, made, calc, store, name=None, cores=None, memory_mb=None, hours=None, root=None, opener=None,
    interval=10.0) -> (RemoteJob, chosen, profile); resume(folder, store, root=None, opener=None, interval=10.0) ->
    RemoteJob; ended(root, folder, state, code). store — anything with .value(key, default): the settings of Azimuth.
§7 TESTS tests/core/test_headless_server.py (the fake server of tests/fake_server.py).
"""

from datetime import datetime
import json
import threading
from pathlib import Path

SHARE = 2  # at most half of the free memory of the node
DEFAULT_CORES = 8
DEFAULT_MAXCORE = 2000  # MB per process
HOURS, MAX_HOURS = 4, 24
ACTIVE = 3
JOURNAL = 'azimuth_server_journal.jsonl'


def profile(store, name=None):
    """The profile called name (its title), else the one chosen in the program."""
    from modules.sextant import remote

    found = remote.load_all(store)
    if not found:
        raise ValueError('no server profile in the settings of Azimuth: fill «Сервер для расчётов» in Sextant first')
    if name:
        chosen = next((p for p in found if p.title() == name or p.name == name), None)
        if chosen is None:
            raise ValueError(f'no server profile {name!r}; there are: {", ".join(p.title() for p in found)}')
    else:
        chosen = remote.load(store)
    missing = chosen.validate()
    if missing:
        raise ValueError(f'the server profile {chosen.title()!r} is not complete: ' + '; '.join(missing))
    return chosen


def connect(chosen):
    """The login by the key only (§2.1): BatchMode, no password in any form."""
    from modules.sextant.ssh import Connection

    return Connection(chosen, password=None, batch=True)


VPN_WAIT_S = 60.0


def switch_vpn_on(chosen, app=None, wait=None):
    """§2.1: the VPN profile the owner chose for this server in «Сервер для расчётов» is asked of OpenVPN Connect, as
    the window does when the server does not answer; True when the server answers within VPN_WAIT_S. No profile
    chosen, or no OpenVPN Connect — False, nothing is done. No other profile and no setting of the VPN is touched."""
    from modules.sextant import vpn

    if not (chosen.vpn_id or '').strip():
        return False
    app = app if app is not None else vpn.find_connect()
    if app is None:
        return False
    vpn.connect(app, chosen.vpn_id)  # its window is hidden (macOS), shown again if it does not connect
    return bool((wait or vpn.wait_connected)(app, chosen.host, chosen.port, VPN_WAIT_S))


def look(chosen, connection, vpn_app=None, vpn_wait=None, search=False):
    """What the server has (cluster.Resources); ValueError that says what the owner has to do when it cannot be asked.
    A server that does not answer and has a VPN profile: the VPN is switched on once (switch_vpn_on) and it is asked
    again."""
    from modules.sextant import cluster
    from modules.sextant.ssh import SshError

    command = cluster.probe_command(chosen.folder, chosen.partition, search)  # search: the programs outside PATH too
    try:
        text = connection.text(command, timeout=90)
    except SshError as exc:
        if exc.kind == 'auth':
            raise ValueError(f'the server {chosen.title()} did not accept the login by the key. No password is used here: '
                             'set up «Вход без пароля» in the window «Сервер для расчётов» of Sextant (it puts the key of '
                             f'the program on the server once), then try again. ({exc})') from None
        if exc.kind not in ('connection', 'timeout'):
            raise
        if not (chosen.vpn_id or '').strip():
            raise ValueError(f'the server {chosen.title()} does not answer, and its profile has no VPN chosen (the card '
                             f'«VPN» of «Сервер для расчётов»): is the VPN on? ({exc})') from None
        try:
            up = switch_vpn_on(chosen, vpn_app, vpn_wait)
        except ValueError as failed:
            raise ValueError(f'the server {chosen.title()} does not answer, and OpenVPN Connect could not be asked to '
                             f'connect «{chosen.vpn_name}»: {failed}') from None
        if not up:
            raise ValueError(f'the server {chosen.title()} does not answer; OpenVPN Connect was asked to connect '
                             f'«{chosen.vpn_name}» and the server still did not answer in {int(VPN_WAIT_S)} s — its window '
                             'is open now: it may be asking for a password') from None
        try:
            text = connection.text(command, timeout=90)
        except SshError as again:
            if again.kind == 'auth':
                raise ValueError(f'the VPN is on, but the server {chosen.title()} did not accept the login by the key '
                                 f'(«Вход без пароля» of the server window). ({again})') from None
            raise ValueError(f'the VPN «{chosen.vpn_name}» is on, but the server {chosen.title()} still does not answer '
                             f'({again})') from None
    return cluster.parse_probe(text)


def ceiling(resources, reserved=0):
    """(the most cores one calculation may take now, the physical cores of the node, the free ones). Reserved — the
    cores of the calculations just sent from here that the load of the server does not show yet (just_sent)."""
    from modules.sextant import cluster

    plan = cluster.plan(resources)
    return max(0, cluster.room(resources) - reserved), plan.physical, max(0, plan.physical_free - reserved)


RECENT_S = 300  # the 1-minute load of a server without SLURM shows a calculation only when it has started to count


def just_sent(root, title, now=None):
    """The cores of the calculations of the journal sent to the server title in the last RECENT_S and still open."""
    now = now or datetime.now()
    open_now, cores = set(active(root)), 0
    for row in journal(root):
        if row.get('event') == 'sent' and row.get('folder') in open_now and row.get('server') == title:
            try:
                age = (now - datetime.fromisoformat(row.get('time', ''))).total_seconds()
            except ValueError:
                continue
            if age < RECENT_S:
                cores += int(row.get('cores') or 0)
    return cores


def queue_ceiling(resources):
    """(the most cores one calculation may ask of a server with SLURM, the physical cores of the node, the free ones):
    BUSY_SHARE of the node, whatever is busy now — what is not free is waited for in the queue."""
    from modules.sextant import cluster

    plan = cluster.plan(resources)
    return max(1, int(cluster.BUSY_SHARE * plan.physical)), plan.physical, plan.physical_free


def _queued(resources, cores, memory_mb):
    """choose() for a server with SLURM: the cores are those asked for; more than are free — the job waits."""
    from modules.sextant import cluster

    most, physical, free = queue_ceiling(resources)
    cores = min(DEFAULT_CORES, most) if cores is None else int(cores)
    if cores < 1:
        raise ValueError('cores: at least 1')
    if cores > most:
        raise ValueError(f'cores: {cores} asked, at most {most} for one calculation ({int(cluster.BUSY_SHARE * 100)} % of '
                         f'the {physical} cores of the node): a larger job would never start')
    maxcore = DEFAULT_MAXCORE if memory_mb is None else int(memory_mb)
    if maxcore < 100:
        raise ValueError('memory_mb: at least 100 MB per process')
    chosen = cluster.plan(resources, wanted=cores, maxcore=maxcore)
    node = cluster._node(resources)
    total = (node.memory_mb if node is not None and node.memory_mb else None) or resources.memory_mb
    request = int(chosen.processes * chosen.maxcore * 1.25)
    if total and request > cluster.BUSY_SHARE * total:
        fits = int(cluster.BUSY_SHARE * total / 1.25 / chosen.processes) // 100 * 100
        raise ValueError(f'memory_mb: {maxcore} MB × {chosen.processes} processes asks {request} MB, more than '
                         f'{int(cluster.BUSY_SHARE * 100)} % of the {total} MB of the node; at most {fits} MB per process '
                         'with these cores')
    return chosen


def choose(resources, cores=None, memory_mb=None, reserved=0):
    """The plan of one calculation within the limits of §2.3; ValueError names the limit crossed. A server with SLURM:
    the plan may ask more cores than are free now (Plan.queued) — sbatch takes the job, and it waits."""
    from modules.sextant import cluster

    if resources.slurm:
        return _queued(resources, cores, memory_mb)
    most, physical, free = ceiling(resources, reserved)
    if most < 1:
        raise ValueError(f'no cores to take on the server now ({free} of {physical} are free, and at most '
                         f'{int(cluster.BUSY_SHARE * 100)} % of them may be busy with the new calculation): try later')
    if cores is None:
        cores = min(DEFAULT_CORES, most)
    cores = int(cores)
    if cores < 1:
        raise ValueError('cores: at least 1')
    if cores > most:
        raise ValueError(f'cores: {cores} asked, at most {most} now ({free} of {physical} are free; with the new '
                         f'calculation at most {int(cluster.BUSY_SHARE * 100)} % of the node may be busy)')
    maxcore = DEFAULT_MAXCORE if memory_mb is None else int(memory_mb)
    if maxcore < 100:
        raise ValueError('memory_mb: at least 100 MB per process')
    chosen = cluster.plan(resources, wanted=cores, maxcore=maxcore)
    memory = cluster.free_memory(resources)
    request = int(chosen.processes * chosen.maxcore * 1.25)
    if memory and request > memory / SHARE:
        fits = int(memory / SHARE / 1.25 / chosen.processes) // 100 * 100
        raise ValueError(f'memory_mb: {maxcore} MB × {chosen.processes} processes asks {request} MB, more than 1/{SHARE} of '
                         f'the {memory} MB free on the server; at most {fits} MB per process with these cores')
    return chosen


def time_directive(chosen, hours=None):
    """The «#SBATCH -t» of the calculation when the profile has none (§2.4)."""
    if (chosen.time_limit or '').strip():
        if hours is not None:
            raise ValueError(f'hours: the profile {chosen.title()} has its own time limit ({chosen.time_limit}) — it is used')
        return []
    hours = HOURS if hours is None else int(hours)
    if not 1 <= hours <= MAX_HOURS:
        raise ValueError(f'hours: from 1 to {MAX_HOURS}')
    return [f'#SBATCH -t {hours:02d}:00:00']


# -- the journal ---------------------------------------------------------------------------------------------------
def jobs_root(root=None):
    from modules.sextant import runner

    return Path(root) if root else runner.default_jobs_root()


def journal(root=None):
    path = jobs_root(root) / JOURNAL
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding='utf-8').splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue  # a cut line: the others are read
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _note(root, **row):
    path = jobs_root(root) / JOURNAL
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {'time': datetime.now().isoformat(timespec='seconds'), **row}
    with open(path, 'a', encoding='utf-8') as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + '\n')
    return row


UNSENT_S = 600  # a sending that has not reached the queue in this time never will (the upload and sbatch take seconds)


def _alive(pid):
    """Is the process of this number running? None when that cannot be told."""
    import os
    import sys

    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return None
    if pid <= 0:
        return None
    if sys.platform == 'win32':
        try:
            import ctypes

            kernel = ctypes.windll.kernel32
            handle = kernel.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
            if not handle:
                return False
            code = ctypes.c_ulong()
            found = kernel.GetExitCodeProcess(handle, ctypes.byref(code))
            kernel.CloseHandle(handle)
            return bool(found) and code.value == 259  # STILL_ACTIVE
        except (OSError, AttributeError, ValueError):
            return None
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return None
    return True


def _unsent(row, now, alive=_alive):
    """A sending of the journal that never reached the server: its folder has no job.json (written when the queue
    accepts the job) and the process that was sending is gone, or UNSENT_S have passed."""
    from modules.sextant import remote_job

    folder = row.get('folder')
    if not folder or (Path(folder) / remote_job.JOB_JSON).is_file():
        return False
    try:
        seconds = (now - datetime.fromisoformat(row.get('time', ''))).total_seconds()
    except (TypeError, ValueError):
        return False
    return seconds > UNSENT_S or (row.get('pid') is not None and alive(row.get('pid')) is False)


def _open_rows(root=None, now=None, server=None):
    """The rows «sent» of the journal without an «ended», not older than the longest time limit."""
    now = now or datetime.now()
    sent, over = [], set()
    for row in journal(root):
        if row.get('event') == 'sent':
            try:
                age = (now - datetime.fromisoformat(row.get('time', ''))).total_seconds() / 3600
            except (TypeError, ValueError):
                age = 0.0
            if age <= MAX_HOURS + 1 and (server is None or row.get('server') == server):
                sent.append(row)
        elif row.get('event') == 'ended':
            over.add(row.get('folder'))
    return [row for row in sent if row.get('folder') and row.get('folder') not in over]


def active(root=None, now=None, server=None, alive=_alive):
    """The folders of the calculations sent from here and not known to have ended. A calculation sent more than
    MAX_HOURS + 1 h ago is not open whatever the journal says: the time limit of its job has ended it (a watcher whose
    process ended before the calculation wrote no «ended»). A sending that never reached the server (_unsent: the
    process ended or lost the connection during the upload) is not open either — it took a place of ACTIVE for a
    day. Server — the title of a server: only the calculations sent there."""
    now = now or datetime.now()
    return [row['folder'] for row in _open_rows(root, now, server) if not _unsent(row, now, alive)]


def close_unsent(root=None, now=None, alive=_alive):
    """The sendings that never reached a server get their «ended» in the journal (state «not sent»); the folders."""
    now = now or datetime.now()
    closed = []
    for row in _open_rows(root, now):
        if _unsent(row, now, alive):
            try:
                _note(root, event='ended', folder=row['folder'], state='not sent', code=None)
            except OSError:
                continue
            closed.append(row['folder'])
    return closed


_ENDING = threading.Lock()


def ended(root, folder, state, code):
    """The end of a calculation of the journal, written once: the watcher of the calculation and a question about its
    state may come here at the same moment (two lines «ended» were seen), so the look and the note are one step."""
    folder = str(folder)
    with _ENDING:
        if folder in [row['folder'] for row in _open_rows(root)]:
            _note(root, event='ended', folder=folder, state=state, code=code)


def _mine(root, folder):
    folder = str(Path(str(folder)).expanduser())
    if not any(row.get('event') == 'sent' and row.get('folder') == folder for row in journal(root)):
        raise ValueError(f'{folder} is not a calculation sent to a server from here (the journal {JOURNAL} of the folder of '
                         'the calculations lists them)')
    return Path(folder)


# -- the commands --------------------------------------------------------------------------------------------------
def _open(store, name, opener, search=False):
    chosen = profile(store, name)
    connection = (opener or connect)(chosen)
    return chosen, connection, look(chosen, connection, search=search)


def state(store, name=None, root=None, opener=None):
    """What the server says now and what one calculation may take; the calculations of the journal still open."""
    from modules.sextant import cluster, remote, remote_job

    close_unsent(root)
    chosen, connection, resources = _open(store, name, opener, search=True)
    if resources.slurm:  # the queue: one calculation may ask up to queue_ceiling, free now or not
        most, physical, free = queue_ceiling(resources)
    else:
        most, physical, free = ceiling(resources, just_sent(root, chosen.title()))
    memory = cluster.free_memory(resources)
    found = {}
    for kind in remote_job.REMOTE_KINDS:
        setup = cluster.setup_for(chosen.setup, resources, kind, chosen.directives(), chosen.setup_of(kind))
        found[kind] = cluster.find_on_server(resources, kind, setup, chosen.setup_of(kind))
    return {
        'server': chosen.title(), 'address': chosen.address(), 'profiles': [p.title() for p in remote.load_all(store)],
        'slurm': resources.slurm,
        'start': ('sbatch: a calculation asking more cores than are free waits in the queue' if resources.slurm
                  else 'nohup (no SLURM): only on free cores'),
        'programs': found, 'found_outside_path': {name: path for name, path in resources.found},
        'load': resources.load,
        'other_programs': {kind: cluster.find_on_server(resources, kind) for kind in cluster.PROGRAM_FILES
                           if kind not in remote_job.REMOTE_KINDS},
        'cores': {'physical': physical, 'free': free, 'most_for_one_calculation': most,
                  'default': min(DEFAULT_CORES, most) if most else 0},
        'memory_mb': {'free': memory, 'default_per_process': DEFAULT_MAXCORE,
                      'most_request': int(memory / SHARE) if memory else None},
        'disk_free_mb': resources.disk_free_mb,
        'time_limit': chosen.time_limit or f'{HOURS} h by default, at most {MAX_HOURS} h',
        'partition': chosen.partition or None,
        # those of this server; the limit ACTIVE counts all of them (Windows check 2026-11-24: the list of .103 showed
        # the calculation sent to .101)
        'calculations_open': active(root, server=chosen.title()),
        'calculations_open_on_other_servers': [f for f in active(root) if f not in active(root, server=chosen.title())],
        'calculations_at_once': None if resources.slurm else ACTIVE,  # a queue has no such limit
        'summary': cluster.summary(resources, cluster.plan(resources), chosen.title()),
    }


def send(kind, made, calc, store, name=None, cores=None, memory_mb=None, hours=None, root=None, opener=None, interval=10.0):
    """One calculation prepared here, sent and put in the queue; watched by the RemoteJob returned (started)."""
    from modules.sextant import cluster, remote_job

    if kind not in remote_job.REMOTE_KINDS:
        raise ValueError(f'a server runs {", ".join(remote_job.REMOTE_KINDS)}, not {kind}')
    close_unsent(root)
    chosen, connection, resources = _open(store, name, opener)
    if not resources.slurm:  # no queue there: the calculations of this server start at once and share its cores
        open_now = active(root, server=chosen.title())
        if len(open_now) >= ACTIVE:
            raise ValueError(f'{len(open_now)} calculations sent from here to {chosen.title()} are not known to have ended '
                             f'(at most {ACTIVE} at once on a server without SLURM): look at them (status or resume) or '
                             'wait — ' + '; '.join(open_now))
    limit = time_directive(chosen, hours)
    setup = cluster.server_setup(chosen, resources, kind, limit)  # the same check as the window: the program found there
    reserved = 0 if resources.slurm else just_sent(root, chosen.title())  # SLURM counts its jobs itself
    plan = choose(resources, cores, memory_mb, reserved)
    spec = remote_job.prepare_remote(made, calc, (), jobs_root(root), plan, setup, kind=kind)
    job = remote_job.RemoteJob(spec, chosen, connection, interval)
    import os

    _note(root, event='sent', folder=str(spec.folder), pid=os.getpid(), server=chosen.title(), program=kind, title=made.title,
          formula=made.formula, task=calc.task, cores=plan.processes, memory_mb=plan.maxcore,
          time_limit=chosen.time_limit or limit[0].split()[-1])
    return job.start(), plan, chosen


def resume(folder, store, root=None, opener=None, interval=10.0):
    """The watching of a calculation of the journal taken up again (this process was restarted): from job.json of its
    folder — the same number in the queue, nothing is sent again."""
    from azimuth.runtime import records
    from modules.sextant import remote, remote_job

    folder = _mine(root, folder)
    info = records.read(folder, remote_job.JOB_JSON)
    if not isinstance(info, dict):
        if str(folder) in [row['folder'] for row in _open_rows(root)]:
            _note(root, event='ended', folder=str(folder), state='not sent', code=None)
        raise ValueError(f'{folder} has no {remote_job.JOB_JSON}: the calculation never reached the queue — it is '
                         'written to the journal as ended; send it again')
    outputs = sorted(p for p in folder.glob('*.out') if not p.name.startswith('slurm-'))
    if not outputs:
        raise ValueError(f'no output file in {folder}')
    title = info.get('server') or ''
    chosen = next((p for p in remote.load_all(store) if p.title() == title), None) or profile(store)
    connection = (opener or connect)(chosen)
    look(chosen, connection)  # the key and the connection are checked before the watcher starts
    return remote_job.RemoteJob.resume(folder, outputs[0], chosen, connection, info, interval).start()
