"""Sextant: a calculation on a SLURM server, watched like one on this computer.

HEADER
    RemoteJob has the interface of runner.Job (start, poll, running, stop, elapsed, text, stdout_text, spec, code,
    stopped), so the calculation window, Quill's animation, the hourglass, the stages, «Вывод программы» and the opening
    of the result work unchanged. The difference stays inside: the input is prepared here, sent to the server, put in
    the queue with sbatch; a worker thread watches the queue and copies the growing output into the local job folder,
    where text() reads it as for a local run; at the end the results are downloaded next to it.
    Wilkinson convention, sections 1-8.

§1 THEORY
    The window polls the job every second on its own thread; network calls take from milliseconds (through the open
    ssh connection) to the timeouts of a lost VPN. So nothing in poll() touches the network: a daemon thread does the
    calls and leaves its findings in attributes guarded by a lock. The output of ORCA only grows, so its new part is
    fetched as `tail -c +<size+1>` and appended to the local copy — the whole file is downloaded once, at the end.

§2 ALGORITHM
    prepare_remote(molecule, calculation, constraints, root, plan, setup, ...) — the local folder as runner.job_folder,
      <base>.inp (named after the calculation) with %pal nprocs / %maxcore from the plan (the edited input too,
      cluster.with_processes), job.sh (cluster.job_script), an empty <base>.out; returns a runner.JobSpec (kind 'orca',
      command ('server')).
    RemoteJob(spec, profile, connection, interval=10).start(): the worker:
      1. state 'sending': upload the folder into <profile folder>/<folder name> (ssh.Connection.upload);
      2. sbatch job.sh in that folder; the number from «Submitted batch job N» → job.json (server, folder, id, time);
         no number → state 'failed' with what sbatch printed;
      3. every `interval` s: squeue state ('PENDING' → 'queued', 'RUNNING'/'COMPLETING'/'CONFIGURING' → 'running');
         wc -c of the output, and when it grew, its new bytes appended to the local copy;
         a failed call → state 'offline' with the message, retries after 10, 20, then every 30 s, the time of
         the next try in the message; from the second failure OpenVPN Connect is asked to connect (the VPN profile of
         the server, at most every VPN_RETRY_S) — the job goes on there all the while;
      4. gone from squeue → one last copy of the output, the results downloaded (wanted(names)), code = 0 when the
         output has FINISHED_MARK, else 1; stopped → code = −15 (as a local SIGTERM).
    stop(): asks the worker for scancel <id> (or, before the number is known, not to submit); the code comes from 4.
    poll() → code or None; running ↔ started and code is None.

§3 APPLICATIONS
    modules/sextant/workspace.py: run_on_server() (instead of runner.Job when «Где считать» is the server).

§4 SPECIFICATION
    prepare_remote(molecule, calculation, constraints, root, plan, setup='', now=None, neb=None, text=None) -> JobSpec
    RemoteJob(spec, profile, connection, interval=10.0, sleep=time.sleep)
        .start() -> self; .poll() -> int | None; .running; .stop(); .elapsed() -> float; .text(limit);
        .stdout_text(limit) .state ∈ STATES; .message: str; .job_id: str | None; .remote_dir: str; .join(timeout)
        (tests)
    wanted(names) -> [names to download]; STATES; JOB_JSON.
    submit(spec, profile, connection, after=None) -> job id (sent and queued, not watched; job.json written).
    Send_batch(specs, profile, connection, chosen, setup, name, kind) -> job id — the jobs of a queue sent at
    once and run one after another by one SLURM job (cluster.batch_script); job.json of each has 'batch': True and the
    shared number. BatchItemJob — the watching of one of them (RemoteJob.resume gives it for such a job.json): queued
    until its folder has STARTED, then its output grows as for a job of its own; FINISHED (with the exit code) ends it;
    the shared job gone before → failed (or stopped); stop() leaves SKIP in its folder (the script ends that
    calculation and goes on); scancel of the shared number stops the whole queue (batch_actions._cancel_sent).
    Group.json and the record of the sending of the group in the folder of the script; the markers
    «<time|code> <attempt id>»; SubmissionUncertain when the answer was lost and not settled (job.json without a
    number; BatchItemJob._settle_group asks the server first, the first job settles the group for the others).

§5 PROCEDURES — below.

§6 NOTES prepare_remote writes submission.json (attempt id, token, job name) and az-submit.sh; the sending calls the
    helper (one sbatch per token, the receipt on the server) instead of «sbatch job.sh»; a lost answer is not «failed» —
    the server is asked (receipt, lock, squeue/sacct by the name) and the job is accepted with the number found, or ends
    'uncertain' (code 1) with what to check; nothing is sent twice. resume(info without 'job') asks the server first
    (_settle). submit() uses the same path. A lost connection while sending or downloading the results is tried again
    (_again: 10, 20, 30 s …); a job whose output, copied while it ran, ended normally is finished even when some files
    stayed on the server (said). Submit() — sent and queued without the watching (the rest of a queue at the exit,
    «--dependency=afterany»). Only ORCA for now (the laboratory computes with ORCA); Gaussian, Psi4 and xtb on a server
    are stage 4 of docs/features/REMOTE_CALCULATIONS.md. Coming back to a job after the program was closed (job.json):
    RemoteJob.resume, 0.89.18 (history.py). The output of ORCA is ASCII; bytes are
    appended as they come, so a character split between two fetches is still whole in the file.

§7 TEST CASES tests/sextant/test_remote_job.py: fake ssh, scp, sbatch, squeue, scancel and orca on this computer —
sending,
    queue, growing output, the end and the download, a failed submission, stop, a lost connection and its return.

§8' ROBUSTNESS
    A lost connection never ends the job here (it goes on on the server); only sbatch refusing it or its leaving the
    queue does. Every exception of the worker becomes state 'failed' with a message, never an exception in the window.
"""

from __future__ import annotations

import re
import threading
import time
from dataclasses import replace
from datetime import datetime

from modules.sextant import cluster, runner
from modules.sextant.inputs import input_files
from modules.sextant.ssh import SshError, shell_path
from azimuth.i18n import tr
from azimuth.runtime import runs

STATES = ('new', 'sending', 'queued', 'running', 'offline', 'finished', 'failed', 'stopped', 'uncertain')
JOB_JSON = 'job.json'
RETRY = (10.0, 20.0, 30.0)  # then every 30 s while the connection is lost (was 30, 60, 120, 300 s)
# T10 (PROJECT_RUNTIME_GUIDE.md §13: «job исчез из squeue, вывод задерживается — нет ложного успеха, сверка
# ждёт достаточных доказательств»): a job gone from squeue whose output has no mark of the end is taken as ended only
# after GONE_CHECKS observations in a row with the output not growing (a slow file system, squeue between answers);
# success only by the mark of the program in the output, never by the job being gone
GONE_CHECKS = 3
GONE_WAIT_S = 10.0
OBSERVED = 'observed.json'  # T09: the last state seen on the server and when (kept for the next start)
# T16 (PROJECT_RUNTIME_GUIDE.md §13: a cut transfer never gives a file declared complete): a file of the result is
# downloaded into TRANSFER first and moved into the
# folder of the calculation only when its size is the size the server tells; a cut or short copy is taken again (at
# most VERIFY_TRIES times), and what never came whole is not put there
TRANSFER = '.az-transfer'
VERIFY_TRIES = 3
WINDOWS_INTERVAL_S = 30.0  # the watching on Windows: every login is a new connection (Windows check 2026-11-24)
VPN_RETRY_S = 300.0  # a lost connection — OpenVPN Connect is asked to connect at most this often
_SKIP = re.compile(r'\.tmp|\.densities|\.prop$|^core(\.\d+)?$', re.I)
# the files are named after the calculation, not «input»: kept by their extensions
_KEEP = re.compile(r'^.*\.(out|gbw|molden\.input|molden|hess|engrad|xyz|txt|opt|loc|nbo|cis|cube|log|aux|arc|stdout|dos|cell|pdos|mol|mold|freq|phdos)$', re.I)
# .mold, .freq, .phdos — the phonons of Quantum ESPRESSO (qe_inputs.PHONON_FILE, FREQ_FILE, PHDOS_FILE): they stayed on the
# server, and a run there showed no modes, no dispersion and no phonon DOS (serv3, 2026-11-23)
REMOTE_KINDS = ('orca', 'mopac')  # the programs a server runs (MOPAC: .aux and .arc come back too)
PROGRAM_TITLES = {'orca': 'ORCA', 'mopac': 'MOPAC', 'qe': 'Quantum ESPRESSO', 'cp2k': 'CP2K'}


# the last answer about each group of calculations run by one SLURM job (send_batch), shared by its
# watchers: (server address, job number, local folder of the group) -> (monotonic time, squeue text,
# {folder: (finished, started, skipped)})
_GROUPS = {}
_GROUPS_LOCK = threading.Lock()
_GROUP_MARK = '@@azimuth-group@@'


def _by_number(job_id):
    """The order of the numbers of jobs in a note: 101 before 102 before 1000."""
    text = str(job_id)
    return (len(text), text)


def group_command(job_id, parent, names):
    """One command for a group — the state of its job in squeue, then a line «folder|finished|started|skip»
    for each member folder in parent."""
    import shlex

    folders = ' '.join(shlex.quote(n) for n in names)
    return (f'{cluster.queue_command(job_id)}; echo {_GROUP_MARK}; cd {shell_path(parent)} 2>/dev/null && '
            f'for d in {folders}; do printf "%s|%s|%s|%s\\n" "$d" "$(cat "$d/{cluster.FINISHED}" 2>/dev/null)" '
            f'"$(cat "$d/{cluster.STARTED}" 2>/dev/null)" "$(test -f "$d/{cluster.SKIP}" && echo 1)"; done; true')


def parse_group(text):
    """(squeue text, {folder: (finished, started, skipped)}) from the answer of group_command."""
    head, _, rest = (text or '').partition(_GROUP_MARK)
    markers = {}
    for line in rest.splitlines():
        parts = line.split('|')
        if len(parts) >= 4 and parts[0].strip():
            markers[parts[0].strip()] = (parts[1].strip(), parts[2].strip(), parts[3].strip())
    return head, markers


def read_observed(folder):
    """T09: (state, ISO time) kept by the watching of the calculation in its folder, or None."""
    import json
    from pathlib import Path

    try:
        data = json.loads((Path(folder) / OBSERVED).read_text(encoding='utf-8'))
        return (str(data['state']), str(data['at']))
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _ssh_detail(exc):
    """What ssh itself said (the last line of its error, in brackets at the end of the message), else the message."""
    text = str(exc).strip()
    found = re.search(r'\(([^()]+)\)\s*$', text)
    return found.group(1) if found else text


def wanted(names):
    """The files of a finished job worth bringing back: outputs, orbitals, geometries, Hessian (§2.4)."""
    return [n for n in names if n and not _SKIP.search(n) and _KEEP.match(n)]


def prepare_remote(molecule, calculation, constraints, root, chosen, setup='', now=None, neb=None, text=None, kind='orca'):
    if kind not in REMOTE_KINDS:
        raise ValueError(tr('На сервере считаются ORCA и MOPAC.'))
    calc = replace(calculation, cores=chosen.processes, memory_mb=chosen.maxcore)
    files = input_files(kind, molecule, calc, constraints, neb)  # validates
    main = next(iter(files))  # <base>.inp, named after the calculation (<base>.mop of MOPAC)
    if text is not None:
        if not text.strip():
            raise ValueError(tr('Входной файл пуст.'))
        files[main] = (cluster.with_processes(text.rstrip('\n') + '\n', chosen.processes, chosen.maxcore) if kind == 'orca'
                       else text.rstrip('\n') + '\n')
    if kind == 'mopac':
        files[main] = mopac_threads(files[main], chosen.processes)
    guess = runner.start_orbitals(kind, calc)  # uploaded with the folder
    folder = runner.job_folder(root, molecule, kind, now or datetime.now())
    for name, content in files.items():
        # newline='\n': the files go to Linux; on Windows Python wrote \r\n, and sbatch refused job.sh («DOS line
        # breaks»), bash read «cd …\r» (the owner's Windows, 2026-11-24)
        (folder / name).write_text(content, encoding='utf-8', newline='\n')
    runner.copy_start_orbitals(guess, folder)
    base = main.rsplit('.', 1)[0]
    (folder / 'job.sh').write_text(cluster.job_script(chosen, setup, f'az-{molecule.formula}', base, kind), encoding='utf-8',
                                   newline='\n')
    output = folder / f'{base}.out'
    output.write_bytes(b'')
    # the intent of sending — the attempt id and the token — kept before anything reaches the server
    (folder / runs.HELPER).write_text(runs.helper_script(), encoding='ascii', newline='\n')
    runs.write(folder, runs.new_submission(name_hint=molecule.formula))
    return runner.JobSpec(kind, folder, ('server',), output, {}, output)


def prepare_qe(folder, steps, chosen, setup='', name='crystal', kind='qe'):
    """A job of Quantum ESPRESSO for the server in its prepared folder (the inputs of the steps and the
    pseudopotentials in pseudo/, written by qe_window.QePanel): job.sh (cluster.job_script, program 'qe'), the helper
    and the intent of sending (as prepare_remote), an empty pw.out. Returns the JobSpec of kind 'qe'. Kind
    'cp2k' — its input azimuth.inp, the output cp2k.out (cluster.cp2k_lines)."""
    from pathlib import Path

    folder = Path(folder)
    (folder / 'job.sh').write_text(cluster.job_script(chosen, setup, f'az-{kind}-{name}', 'pw', kind, steps),
                                   encoding='utf-8', newline='\n')
    output = folder / ('cp2k.out' if kind == 'cp2k' else 'pw.out')
    output.write_bytes(b'')
    (folder / runs.HELPER).write_text(runs.helper_script(), encoding='ascii', newline='\n')
    runs.write(folder, runs.new_submission(name_hint=f'{kind}-{name}'))
    return runner.JobSpec(kind, folder, ('server',), output, {}, output)


def submit(spec, profile, connection, after=None):
    """The folder of a prepared job (prepare_remote) sent and put in the SLURM queue without watching it — the
    queue sent before the program closes; after — the number of the job it waits for (sbatch --dependency=afterany:N:
    one after another on the server as when Azimuth sends them, a failure does not stop the next). job.json is written,
    so the watching is taken up later (RemoteJob.resume). A dependency on a job SLURM no longer knows (it ended long
    ago) is refused by sbatch — then the job is queued without it. Returns the number; ValueError when not queued."""
    job = RemoteJob(spec, profile, connection)
    job._intent()
    connection.upload(spec.folder, job.remote_dir.rsplit('/', 1)[0])
    extras = [(f'--dependency=afterany:{int(after)}',), ()] if after else [()]
    job_id, answer = job._queue(extras)
    if job_id is None:
        raise ValueError(tr('Сервер не поставил расчёт в очередь: ') + answer)
    job.job_id = job_id
    job._write_json()
    return job_id


def send_batch(specs, profile, connection, chosen, setup, name, kind='orca'):
    """The prepared jobs (prepare_remote, in the order of the queue) uploaded, the script of the queue written
    into a folder of its own next to them and submitted once; job.json of every job: the shared number, 'batch': True.
    Returns the number; ValueError when the server did not queue it.
    The folder of the script has group.json (group id, the ordered attempt ids,
    folders and SHA-256 of the inputs) and the record of the sending of the group (azimuth/runtime/runs.py); the script
    is submitted through the helper of the token, the markers of each job name its attempt. A lost answer → the server
    is asked; not settled → SubmissionUncertain (job.json of the jobs without a number, 'group' — the local folder of
    the group: their watching settles it first) — never sent again, never one by one."""
    from pathlib import Path

    if not specs:
        raise ValueError(tr('Нечего отправлять.'))
    parent = profile.folder.strip().rstrip('/') or '~'
    root = Path(specs[0].folder).parent
    folder = root / (re.sub(r'[^A-Za-z0-9._-]', '_', root.name)[:60] + cluster.BATCH_FOLDER_SUFFIX)
    folder.mkdir(parents=True, exist_ok=True)
    members = []
    for spec in specs:
        own = runs.read(spec.folder)
        if own is None:  # a folder prepared
            own = runs.new_submission()
            runs.write(spec.folder, own)
        members.append((spec.folder.name, spec.output.name.rsplit('.', 1)[0], own.attempt_id))
    group = runs.read(folder)
    if group is not None and group.state in ('submitting', 'uncertain', 'accepted'):  # this folder was sent before
        if [m.get('attempt') for m in runs.read_group(folder).get('members', [])] != [m[2] for m in members]:
            raise ValueError(tr(f'Очередь уже отправлялась из папки {folder} — её состояние: {group.state}. Новая '
                                'отправка — новой очередью.'))
    else:
        group = runs.new_submission(name_hint=name[3:] if name.startswith('az-') else name)
        runs.write_group(folder, group.attempt_id, [
            {'attempt': attempt, 'folder': job_folder, 'base': base,
             'sha256': runs.digest(root / job_folder, base, kind)} for job_folder, base, attempt in members])
        (folder / runs.HELPER).write_text(runs.helper_script(), encoding='ascii', newline='\n')
        (folder / 'batch.sh').write_text(cluster.batch_script(chosen, setup, name, members, kind), encoding='utf-8',
                                         newline='\n')
        group = runs.moved(group, 'submitting', server=profile.title(), folder=f'{parent}/{folder.name}')
        runs.write(folder, group)
    remote = shell_path(f'{parent}/{folder.name}')
    job_id, why = None, ''
    for _ in range(3):
        if group.state == 'accepted':
            job_id = group.job_id
            break
        try:
            # all the folders in one archive and the sbatch in the same ssh — two exchanges with the server
            # instead of two for every calculation
            result = connection.upload_packed([spec.folder for spec in specs] + [folder], parent,
                                              then=runs.helper_command(remote, group, (), 'batch.sh'), timeout=600)
        except SshError as exc:
            if exc.kind not in ('connection', 'timeout'):
                runs.write(folder, runs.moved(group, 'rejected', note=str(exc)))
                raise
            try:
                found = runs.verdict(connection.run(runs.find_command(remote, group), timeout=60)
                                     .out.decode('utf-8', errors='replace'))
            except SshError:
                found = ('uncertain', None)
            if found[0] == 'absent':
                continue  # the helper never ran: the same token again
            if found[0] == 'accepted':
                group = runs.moved(group, 'accepted', found[1], note='the answer was lost; found on the server')
                runs.write(folder, group)
                job_id = group.job_id
                break
            why = str(exc) if found[0] == 'uncertain' else f'several jobs of the token: {", ".join(sorted(found[1], key=_by_number))}'
            group = runs.moved(group, 'uncertain', note=why)
            runs.write(folder, group)
            break
        answer = (result.out.decode('utf-8', errors='replace') + '\n' + result.err).strip()
        job_id = runs.answer_job(answer) if result.code == 0 else None
        if job_id is None:
            runs.write(folder, runs.moved(group, 'rejected', note=answer[:300]))
            raise ValueError(tr('Сервер не поставил очередь расчётов: ') + (answer or tr(f'код {result.code}')))
        group = runs.moved(group, 'accepted', job_id)
        runs.write(folder, group)
        break
    for spec in specs:
        job = BatchItemJob(spec, profile, connection)
        job.job_id = job_id
        job.group_dir = str(folder)
        job._write_json()
    if job_id is None:
        raise SubmissionUncertain(tr(f'Связь прервалась при постановке очереди; неизвестно, принял ли её сервер '
                                     f'(метка {group.name}, папка {parent}/{folder.name}). Повторно она не '
                                     'отправлена — Секстант проверит это сам, когда связь вернётся.'))
    return job_id


class SubmissionUncertain(ValueError):
    """The server may have accepted the queue — the jobs are not sent again (nor one by one)."""


def mopac_threads(text, threads):
    """«THREADS=n» on the first line of keywords of a .mop (MOPAC takes every core of the machine otherwise —
    on a shared server the job keeps to the cores SLURM gave it, with OMP_NUM_THREADS of job.sh); a THREADS written by
    hand stays. ASSUMPTION: one THREADS on the first job of the file holds for the run (MOPAC 2016 manual: «THREADS=n —
    set the number of threads»); not yet checked on the servers."""
    lines = text.split('\n')
    if lines and not re.search(r'\bTHREADS\s*=', lines[0], re.I):
        lines[0] = lines[0].rstrip() + f' THREADS={int(threads)}'
    return '\n'.join(lines)


class RemoteJob:
    def __init__(self, spec, profile, connection, interval=10.0, sleep=time.sleep):
        self.spec = spec
        self.profile = profile
        self.connection = connection
        # the OpenSSH of Windows logs in anew for every command (no ControlMaster): asked less often there
        self.interval = max(interval, WINDOWS_INTERVAL_S) if getattr(connection, 'windows', False) is True else interval
        self._sleep = sleep
        self._lock = threading.Lock()
        self._stop_asked = threading.Event()
        self._thread = None
        self.state = 'new'
        self.message = ''
        self.local_warning = ''  # a failed write on this computer while the server job goes on
        self.failure = None  # azimuth/runtime/errors.Category of an end by an exception
        self.job_id = None
        self.code = None
        self.started = None
        self.finished = None
        self.stopped = False
        self.size = 0
        self.seen = None  # T09: (state, ISO time) of the last answer of the server
        self._gone = 0
        self._gone_size = -1
        parent = profile.folder.strip().rstrip('/') or '~'
        self.remote_dir = f'{parent}/{spec.folder.name}'

    @classmethod
    def resume(cls, folder, output, profile, connection, info, interval=10.0, sleep=time.sleep):
        """The watching of a calculation sent before (the program was closed meanwhile) taken up again — from
        job.json of its folder (info): the same number in the queue and folder on the server; nothing is sent again.
        Still in the queue → watched as before; gone → the output and the results are downloaded (§2.3–4)."""
        from pathlib import Path

        output = Path(output)
        kind = info.get('program', 'orca') if isinstance(info, dict) else 'orca'  # MOPAC too
        spec = runner.JobSpec(kind if kind in REMOTE_KINDS else 'orca', Path(folder), ('server',), output, {}, output)
        if isinstance(info, dict) and info.get('batch') and cls is RemoteJob:  # one of a queue sent at once
            cls = BatchItemJob
        job = cls(spec, profile, connection, interval, sleep)
        job.job_id = str(info['job']) if info.get('job') else None  # None — the answer of sbatch was lost
        job.remote_dir = info.get('folder') or job.remote_dir
        job.size = output.stat().st_size if output.is_file() else 0
        job._resumed = True
        if isinstance(info, dict) and info.get('group'):
            job.group_dir = info['group']
        job.seen = read_observed(folder)  # T09: what was seen before the program closed
        return job

    # -- the interface of runner.Job ---------------------------------------------------------
    def start(self):
        self.started = time.monotonic()
        self._thread = threading.Thread(target=self._work, name='azimuth-remote-job', daemon=True)
        self._thread.start()
        return self

    @property
    def running(self):
        return self.started is not None and self.code is None

    def poll(self):
        return self.code

    def stop(self):
        if not self.running:
            return
        self.stopped = True
        self._stop_asked.set()

    def elapsed(self):
        if self.started is None:
            return 0.0
        return (self.finished or time.monotonic()) - self.started

    def text(self, limit=32_000_000):
        return runner._read_end(self.spec.output, limit)

    def stdout_text(self, limit=1_000_000):
        return runner._read_end(self.spec.output, limit)

    def join(self, timeout=None):
        if self._thread is not None:
            self._thread.join(timeout)

    # -- the worker --------------------------------------------------------------------------
    def _said(self, message):
        warning = self.local_warning
        return f'{message} {warning}'.strip() if warning and warning not in message else message

    def _set(self, state, message=''):
        with self._lock:
            self.state = state
            self.message = self._said(message)

    def _failed(self, exc, message):
        """The end by an exception, with its category (azimuth/runtime/errors.py) kept as self.failure —
        what kind of failure it was and whether an outside action may be repeated."""
        from azimuth.runtime.errors import advice, classify

        self.failure = classify(exc)
        hint = advice(self.failure)  # what to do next, by the kind of the failure
        self._end(1, 'failed', f'{message} {hint}' if hint and hint not in message else message)

    def _end(self, code, state, message=''):
        with self._lock:
            self.state = state
            self.message = self._said(message)
            self.finished = time.monotonic()
            self.code = code

    def _observed(self, state):
        """T09: the server answered — the state and the time kept (in the folder when the state changed, so
        that the next start can say what was known and how long ago)."""
        when = datetime.now().isoformat(timespec='seconds')
        changed = self.seen is None or self.seen[0] != state or not getattr(self, '_kept', False)
        self.seen = (state, when)
        if changed:  # the first answer to this watcher (taken up after a restart) too
            try:
                from azimuth.projects import atomic_json

                atomic_json(self.spec.folder / OBSERVED, {'state': state, 'at': when})
                self._kept = True
            except (OSError, ValueError, TypeError):
                pass  # a help for the next start, never a failure of the job

    def _last_seen(self):
        """«последний ответ сервера — 14:02 10.11, шёл»: what is known when the server does not answer ('' — nothing)."""
        if not self.seen:
            return ''
        state, when = self.seen
        names = {'queued': tr('в очереди'), 'running': tr('шёл'), 'gone': tr('уже не в очереди')}
        try:
            at = datetime.fromisoformat(when).strftime('%H:%M %d.%m')
        except (TypeError, ValueError):
            at = str(when)
        return tr('последний ответ сервера — ') + at + (', ' + names[state] if state in names else '')

    def _remote_sizes(self, names):
        """T16: {name: size in bytes} the server tells for these files of the folder ({} when it cannot)."""
        import shlex

        try:
            text = self._again(lambda: self.connection.text(
                f'cd {self._remote()} && wc -c -- ' + ' '.join(shlex.quote(n) for n in names), timeout=60))
        except SshError:
            return {}
        sizes = {}
        for line in (text or '').splitlines():
            parts = line.strip().split(None, 1)
            if len(parts) == 2 and parts[0].isdigit() and parts[1] in names:
                sizes[parts[1]] = int(parts[0])
        return sizes

    def _download_verified(self, names):
        """T16: names downloaded into TRANSFER, each moved into the folder of the calculation only when it is
        whole — its size is the one the server tells (or, when the server tells none, scp ended without an error);
        a cut transfer (an error of the connection, tried again by _again) or a short copy is taken again, at most
        VERIFY_TRIES times. Raises SshError naming the files that never came whole; their parts are removed, a file
        of the folder is never replaced by a part."""
        import os
        import shutil

        sizes = self._remote_sizes(names)
        # a folder of its own: two watchers of one calculation (a restarted process of the tools next to the old one)
        # took the same one and one of them failed «File exists» (2026-11-24)
        stage = self.spec.folder / f'{TRANSFER}-{id(self):x}'
        left = list(names)
        for _ in range(VERIFY_TRIES):
            stage.mkdir(exist_ok=True)
            try:
                self._again(lambda: self.connection.download(left, self.remote_dir, stage))
            except SshError:
                if not any((stage / n).is_file() for n in left):
                    shutil.rmtree(stage, ignore_errors=True)
                    raise
            short = []
            for name in left:
                part = stage / name
                if part.is_file() and (name not in sizes or part.stat().st_size == sizes[name]):
                    os.replace(part, self.spec.folder / name)
                else:
                    short.append(name)
            left = short
            if not left:
                break
        shutil.rmtree(stage, ignore_errors=True)
        if left:
            raise SshError(tr('Файлы пришли не полностью: ') + ', '.join(left), 'command')

    def _gone_for_sure(self):
        """T10: the job is not in the queue — enough evidence that it ended? Yes at once when the output has
        the mark of the end or the job was stopped; else after GONE_CHECKS answers in a row with the output not
        growing (it grew: the count starts again)."""
        if self.stopped or runner.finished_normally(self.spec.kind, self.text(), 0):
            return True
        if self.size != self._gone_size:
            self._gone_size, self._gone = self.size, 1
        else:
            self._gone += 1
        return self._gone >= GONE_CHECKS

    def _exit_marked(self):
        """The job wrote its end (cluster.EXIT_MARK, the exit code): it ended, nothing more to wait for."""
        try:
            text = self.connection.text(f'cat {self._remote(cluster.EXIT_MARK)} 2>/dev/null', timeout=30)
        except SshError:
            return False
        return bool(re.fullmatch(r'-?\d+', (text or '').strip()))

    def _remote(self, name=''):
        return shell_path(self.remote_dir + ('/' + name if name else ''))

    def _write_json(self):
        """Written to a temporary file and moved over job.json (a cut write leaves the old one or none)."""
        data = {'server': self.profile.title(), 'address': self.profile.address(), 'folder': self.remote_dir,
                'job': self.job_id, 'sent': datetime.now().isoformat(timespec='seconds'), 'program': self.spec.kind}
        if isinstance(self, BatchItemJob):
            data['batch'] = True  # the number is that of the whole queue
            if getattr(self, 'group_dir', ''):
                data['group'] = self.group_dir  # the local folder of the group (its record of the sending)
        from azimuth.runtime import records  # in the database of the project of the folder, else the file

        records.write(self.spec.folder, JOB_JSON, data)

    def _wait(self, seconds):
        """Sleep in short steps; True when stop was asked meanwhile."""
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if self._stop_asked.is_set():
                return True
            self._sleep(min(0.2, max(0.0, end - time.monotonic())))
        return self._stop_asked.is_set()

    def _work(self):
        try:
            if getattr(self, '_resumed', False) and self.job_id is None:
                self._settle()  # was it accepted? — asked, never sent again
            elif getattr(self, '_resumed', False):
                known = self._last_seen()
                self._set('queued', tr(f'Снова слежу за расчётом (задача {self.job_id}).') + (f' ({known})' if known else ''))
            else:
                self._send()
            if self.code is None:
                self._watch()
        except SshError as exc:
            self._failed(exc, str(exc))
        except Exception as exc:  # noqa: BLE001 — never an exception in the window (§8')
            self._failed(exc, f'{type(exc).__name__}: {exc}')

    def _again(self, action, attempts=None):
        """Action() again after a lost connection (RETRY: 10, 20, 30 s; at most len(RETRY) + 3 tries) — a
        moment without the server must not end the job (a download at the end of a job, an upload at its start). Other
        errors, the stop asked and the last failure are raised."""
        attempts = attempts or len(RETRY) + 3
        failures = 0
        while True:
            try:
                return action()
            except SshError as exc:
                if exc.kind not in ('connection', 'timeout') or failures + 1 >= attempts:
                    raise
                delay = RETRY[min(failures, len(RETRY) - 1)]
                failures += 1
                if failures >= 2:
                    self._reconnect_vpn()
                self._set(self.state, tr(f'Нет связи с сервером · повтор через {delay:.0f} с.') + ' '
                          + tr('Ответ ssh: ') + _ssh_detail(exc))
                if self._wait(delay):
                    raise

    def _send(self):
        """The upload and the queueing. «Остановить» during the upload ends it at once (ssh.abort_on: scp killed) and
        nothing is queued; pressed while sbatch is answering (that call is never cut: its answer decides whether a job
        exists) — the job accepted is taken off the queue at once and the calculation ends «stopped»."""
        self._set('sending', tr('Отправка на сервер…'))
        self._intent()
        if self._stop_asked.is_set():
            self._end(-15, 'stopped', tr('Остановлен до отправки на сервер.'))
            return
        parent = self.remote_dir.rsplit('/', 1)[0]
        from modules.sextant import ssh

        ssh.abort_on(self._stop_asked)
        try:
            self._again(lambda: self.connection.upload(self.spec.folder, parent))  # a lost moment of the connection
        except SshError as exc:
            if exc.kind != 'stopped':
                raise
        finally:
            ssh.abort_on(None)
        if self._stop_asked.is_set():
            self._end(-15, 'stopped', tr('Остановлен до постановки в очередь.'))
            return
        job_id, answer = self._queue([()])
        if job_id is None:
            if answer is not None:
                self._end(1, 'failed', tr('Сервер не поставил расчёт в очередь: ') + answer)
            return
        self._accepted(job_id)
        if self._stop_asked.is_set():  # pressed while sbatch answered: off the queue now, not on the next look
            try:
                self.connection.run(cluster.cancel_command(job_id), timeout=30)
            except SshError:
                pass
            self._end(-15, 'stopped', tr(f'Остановлен: задача {job_id} снята с очереди сервера.'))

    def _accepted(self, job_id):
        self.job_id = job_id
        # the server has the job now — a failed local note (a full disk, a folder
        # gone) is said, with the number to find it by, and the job is still watched; it was «failed» with code 1, the
        # watching stopped and job.json for the history was missing
        try:
            self._write_json()
        except OSError as exc:
            self.local_warning = tr(f'Расчёт поставлен на сервер (задача {job_id}, папка {self.remote_dir}), но записать '
                                    f'{JOB_JSON} на этом компьютере не удалось: {exc}. Запишите номер задачи — без '
                                    'этого файла история не сможет снова подключиться к расчёту.')
        self._set('queued', tr(f'В очереди (задача {job_id}).'))

    # -- one sbatch per token (azimuth/runtime/runs.py) ----------------------------------
    def _intent(self):
        """The record of the sending (and the helper) in the job folder — made by prepare_remote; a folder prepared
        gets them here, still before the call."""
        folder = self.spec.folder
        if not (folder / runs.HELPER).is_file():
            (folder / runs.HELPER).write_text(runs.helper_script(), encoding='ascii', newline='\n')
        sub = runs.read(folder)
        if sub is None:
            sub = runs.new_submission(name_hint=self.spec.output.stem.split('_')[0])
            runs.write(folder, sub)
        return sub

    def _record(self, sub):
        """The record moved on; a failed write after the server accepted the job is said, never a reason to send
        again (T08): the receipt on the server keeps the number."""
        try:
            runs.write(self.spec.folder, sub)
        except OSError as exc:
            if sub.state in ('accepted', 'uncertain'):
                self.local_warning = tr(f'Не удалось записать сведения об отправке на этом компьютере ({exc}); '
                                        f'расчёт на сервере в папке {self.remote_dir}.')
            else:
                raise
        return sub

    def _queue(self, extras):
        """(job id, '') — accepted (also when the answer was lost and the server was asked); (None, why) — refused;
        (None, None) — not known: the job ended here as 'failed' with the state 'uncertain' of the record and what to
        check, no sending again. extras — the sbatch options to try in turn (a dependency SLURM forgot → without it)."""
        sub = self._intent()
        if sub.state == 'accepted' and sub.job_id:
            return sub.job_id, ''
        if sub.state not in ('prepared', 'submitting'):
            self._end(1, 'failed', tr(f'Эта отправка уже была ({sub.state}); новая попытка — новый расчёт.'))
            return None, None
        if sub.state == 'prepared':
            sub = self._record(runs.moved(sub, 'submitting', server=self.profile.title(), folder=self.remote_dir))
        rounds = 0
        for extra in extras:
            while True:
                try:
                    result = self.connection.run(runs.helper_command(self._remote(), sub, extra), timeout=60)
                except SshError as exc:
                    if exc.kind not in ('connection', 'timeout'):  # refused before the command ran (a key, a password)
                        self._record(runs.moved(sub, 'rejected', note=str(exc)))
                        raise
                    found, job = self._find(sub, str(exc))
                    if found == 'absent' and rounds < 2:  # the helper never ran: the same token again, not a 2nd job
                        rounds += 1
                        parent = self.remote_dir.rsplit('/', 1)[0]
                        self._again(lambda: self.connection.upload(self.spec.folder, parent))
                        continue
                    if found == 'accepted':
                        self._record(runs.moved(sub, 'accepted', job, note='the answer was lost; found on the server'))
                        return job, ''
                    self._uncertain(sub, found, job, str(exc))
                    return None, None
                answer = (result.out.decode('utf-8', errors='replace') + '\n' + result.err).strip()
                job = runs.answer_job(answer) if result.code == 0 else None
                if job:
                    self._record(runs.moved(sub, 'accepted', job))
                    return job, ''
                break
            if extra and 'depend' in answer.lower():
                continue
            self._record(runs.moved(sub, 'rejected', note=answer[:300]))
            return None, answer or tr(f'код {result.code}')
        self._record(runs.moved(sub, 'rejected', note=answer[:300]))
        return None, answer or tr(f'код {result.code}')

    def _find(self, sub, why=''):
        """runs.verdict of what the server knows of the token; the server out of reach → ('uncertain', None)."""
        self._set('sending', tr('Связь прервалась при постановке в очередь — проверяю, принял ли сервер расчёт…'))
        try:
            text = self._again(lambda: self.connection.run(runs.find_command(self._remote(), sub), timeout=60))
        except SshError:
            return 'uncertain', None
        return runs.verdict(text.out.decode('utf-8', errors='replace'))

    def _uncertain(self, sub, found, job, why):
        ids = ', '.join(sorted(job, key=_by_number)) if found == 'conflict' else ''  # squeue lists them in any order
        note = f'several jobs of the token: {ids}' if ids else (why or 'the answer of the server is not known')
        if sub.state != 'uncertain':
            self._record(runs.moved(sub, 'uncertain', note=note))
        if found == 'conflict':
            text = tr(f'Связь прервалась при постановке в очередь, и на сервере несколько заданий с меткой этой '
                      f'отправки ({sub.name}): {ids}. Автоматически ничего не отправлено; проверьте их в папке '
                      f'{self.remote_dir}.')
        else:
            text = tr(f'Связь прервалась при постановке в очередь; неизвестно, принял ли сервер расчёт. Повторно он '
                      f'не отправлен. Когда связь вернётся — «Проверить на сервере» в истории расчётов '
                      f'(метка задания {sub.name}, папка {self.remote_dir}).')
        self._end(1, 'uncertain', text)

    def _settle(self):
        """A record 'uncertain' (or 'submitting' left by a crash) taken up: the server is asked; one job found → the
        record settled with the reason and the job watched; else the same message, no sending."""
        sub = runs.read(self.spec.folder)
        if sub is None or sub.state not in ('submitting', 'uncertain'):
            self._end(1, 'failed', tr('Нет сведений об отправке этого расчёта.'))
            return
        found, job = self._find(sub)
        if found == 'accepted':
            if sub.state == 'uncertain':
                sub = runs.settle(sub, job, 'checked on the server: the receipt or the only job of the token')
            else:
                sub = runs.moved(sub, 'accepted', job, note='found on the server after a restart')
            self._record(sub)
            self._accepted(job)
            return
        if found == 'absent':  # no lock of the token: the helper never ran, nothing reached sbatch
            reason = 'the server never got this sending (no lock of the token)'
            self._record(runs.settle(sub, '', reason, 'rejected') if sub.state == 'uncertain'
                         else runs.moved(sub, 'rejected', note=reason))
            self._end(1, 'failed', tr('Сервер не получал этот расчёт — он не в очереди. Запустите его заново.'))
            return
        self._uncertain(sub, found, job, '')

    def _poll(self):
        """One login for the state of the job, the size of its output and the end it wrote (cluster.EXIT_MARK):
        (queue state or None, size or None, True/False — None when the answer did not say). It was two or three logins
        every interval, each a new connection on Windows."""
        out, mark = self._remote(self.spec.output.name), self._remote(cluster.EXIT_MARK)
        text = self.connection.text(f'{cluster.queue_command(self.job_id)}; echo "@size $(wc -c < {out} 2>/dev/null '
                                    f'|| echo 0)"; if [ -s {mark} ]; then echo "@exit $(cat {mark})"; '
                                    'else echo "@exit"; fi; true', timeout=30)
        size, marked, rest = None, None, []
        for line in (text or '').splitlines():
            if line.startswith('@size'):
                value = line[5:].strip()
                size = int(value) if value.isdigit() else None
            elif line.startswith('@exit'):
                marked = bool(re.fullmatch(r'-?\d+', line[5:].strip()))
            else:
                rest.append(line)
        return cluster.queue_state('\n'.join(rest)), size, marked

    def _fetch_output(self, size=None):
        # wc -c, not stat -c %s: the same on Linux servers and in the macOS tests (BSD stat has no -c)
        if size is None:
            size_text = self.connection.text(f'wc -c < {self._remote(self.spec.output.name)} 2>/dev/null || echo 0',
                                             timeout=30).strip()
            size = int(size_text) if size_text.isdigit() else 0
        if size > self.size:
            result = self.connection.run(f'tail -c +{self.size + 1} {self._remote(self.spec.output.name)}', timeout=120)
            chunk = result.out[: size - self.size]
            try:
                with open(self.spec.output, 'ab') as f:
                    f.write(chunk)
            except OSError as exc:  # the copy here stops growing, the job on the server goes on
                self.local_warning = tr(f'Копия вывода на этом компьютере не обновляется ({exc}); расчёт на сервере '
                                        f'идёт (задача {self.job_id}, папка {self.remote_dir}).')
                return
            self.size += len(chunk)

    def _reconnect_vpn(self):
        """The VPN of the profile, switched on again (the server is behind it and the connection is lost)."""
        if not getattr(self.profile, 'vpn_id', ''):
            return False
        now = time.monotonic()
        if now - getattr(self, '_vpn_asked', -1e9) < VPN_RETRY_S:
            return False
        self._vpn_asked = now
        try:
            from modules.sextant import vpn

            app = vpn.find_connect()
            if app is None:
                return False
            vpn.connect(app, self.profile.vpn_id)
            return True
        except Exception:  # noqa: BLE001 — the VPN is a help, never a failure of the job
            return False

    def _watch(self):
        failures = 0
        while True:
            if self._stop_asked.is_set():
                try:
                    self.connection.run(cluster.cancel_command(self.job_id), timeout=30)
                except SshError:
                    pass
                self._stop_asked.clear()
                self.stopped = True
                self._set(self.state, tr(f'Останавливаю: задача {self.job_id} снята с очереди сервера, забираю вывод…'))
            try:
                state, size, marked = self._poll()
                self._fetch_output(size)
                failures = 0
            except SshError as exc:
                if exc.kind in ('connection', 'timeout'):
                    delay = RETRY[min(failures, len(RETRY) - 1)]
                    failures += 1
                    if failures >= 2:
                        self._reconnect_vpn()
                    when = datetime.now().strftime('%H:%M:%S')
                    known = self._last_seen()
                    # what ssh said — «why the watching cannot connect is not said» (Windows check 2026-11-24)
                    self._set('offline', tr(f'Нет связи с сервером · попытка в {when}, следующая через {delay:.0f} с. '
                                            'Расчёт там продолжается.') + (f' ({known})' if known else '')
                              + ' ' + tr('Ответ ssh: ') + _ssh_detail(exc))
                    if self._wait(delay):
                        continue
                    continue
                raise
            if state is None:
                self._observed('gone')
                if marked or (marked is None and self._exit_marked()) or self._gone_for_sure():
                    self._finish()
                    return
                self._set('running', tr(f'Задачи {self.job_id} уже нет в очереди сервера — жду вывод, чтобы убедиться, '
                                        'что расчёт закончен.'))
                self._wait(min(self.interval, GONE_WAIT_S))
                continue
            self._gone, self._gone_size = 0, -1
            if state.upper() == 'PENDING':
                self._observed('queued')
                self._set('queued', tr(f'В очереди (задача {self.job_id}).'))
            else:
                self._observed('running')
                self._set('running', tr(f'Идёт на сервере (задача {self.job_id}).'))
            self._wait(self.interval)

    def _finish(self):
        self._set('running', tr('Расчёт закончен, скачиваю результат…'))
        missing = ''
        try:  # with retries; the output copied while it ran is enough to tell the end
            self._again(self._fetch_output)
            names = self._again(lambda: self.connection.text(f'ls -1 {self._remote()}', timeout=30)).split()
            take = [n for n in wanted(names) if n != self.spec.output.name]
            if take:
                self._download_verified(take)
            self._download_verified([self.spec.output.name])
        except SshError as exc:
            missing = str(exc)
        try:  # the scratch files of an ORCA that failed or was stopped do not stay on the server
            self.connection.run(f'cd {self._remote()} && rm -f -- *.tmp *.tmp.*', timeout=60)
        except (SshError, OSError):
            pass
        text = self.text()
        left = (' ' + tr(f'Не все файлы скачались ({missing}) — они на сервере в папке {self.remote_dir}.')
                if missing else '')
        if self.stopped:
            self._end(-15, 'stopped', tr('Расчёт остановлен.') + left)
        elif runner.finished_normally(self.spec.kind, text, 0):  # «JOB ENDED NORMALLY» of MOPAC
            self._end(0, 'finished', tr('Расчёт закончен.') + left)
        elif missing:
            raise SshError(missing)
        else:
            name = PROGRAM_TITLES.get(self.spec.kind, self.spec.kind)
            why = self._job_log()  # what the job itself printed: «orca not found in PATH» is there, not in the output
            self._end(1, 'failed', tr(f'{name} завершилась с ошибкой — см. вывод программы.')
                      + (tr(' Сервер: ') + why if why else ''))

    def _job_log(self):
        """The last lines the job script printed on the server — slurm-<number>.out, or az-nohup.out of a server
        without SLURM ('' when there are none or the server does not answer)."""
        if not self.job_id:
            return ''
        names = f'az-nohup.out slurm-{int(self.job_id)}.out *.stdout'  # .stdout — what MOPAC printed itself
        try:
            text = self.connection.text(f'cd {self._remote()} && for f in {names}; do test -s "$f" && tail -n 4 "$f"; '
                                        'done; true', timeout=30)
        except (SshError, ValueError):
            return ''
        return ' '.join(line.strip() for line in text.splitlines() if line.strip())[:500]


class BatchItemJob(RemoteJob):
    """One calculation of a queue run by one SLURM job (send_batch): nothing is sent, its folder is watched."""

    def _work(self):
        try:
            if self.job_id is None and not self._settle_group():
                return
            self._set('queued', tr(f'Ждёт своей очереди на сервере (задача {self.job_id}).'))
            self._watch_markers()
        except SshError as exc:
            self._failed(exc, str(exc))
        except Exception as exc:  # noqa: BLE001 — never an exception in the window (§8')
            self._failed(exc, f'{type(exc).__name__}: {exc}')

    def _settle_group(self):
        """The answer to the sending of the queue was lost — the record of the group here (another job of the
        queue may have settled it already), else the server is asked; True when the number is known."""
        from pathlib import Path

        folder = Path(getattr(self, 'group_dir', '') or '')
        group = runs.read(folder) if str(folder) not in ('', '.') else None
        if group is None:
            self._end(1, 'failed', tr('Нет сведений об отправке этой очереди.'))
            return False
        if group.state != 'accepted':
            self._set('sending', tr('Проверяю, принял ли сервер очередь…'))
            try:
                text = self._again(lambda: self.connection.run(runs.find_command(shell_path(group.folder), group),
                                                               timeout=60))
                found, job = runs.verdict(text.out.decode('utf-8', errors='replace'))
            except SshError:
                found, job = 'uncertain', None
            if found == 'accepted':
                group = (runs.settle(group, job, 'checked on the server: the receipt or the only job of the token')
                         if group.state == 'uncertain' else runs.moved(group, 'accepted', job, note='found on the server'))
                self._record_group(folder, group)
            elif found == 'absent':
                reason = 'the server never got this sending (no lock of the token)'
                self._record_group(folder, runs.settle(group, '', reason, 'rejected') if group.state == 'uncertain'
                                   else runs.moved(group, 'rejected', note=reason))
                self._end(1, 'failed', tr('Сервер не получал эту очередь — расчёт не в очереди. Запустите его заново.'))
                return False
            else:
                ids = ', '.join(sorted(job, key=_by_number)) if found == 'conflict' else ''  # squeue lists them in any order
                self._end(1, 'uncertain', tr(f'Неизвестно, принял ли сервер очередь (метка {group.name}'
                                             + (f'; заданий с ней несколько: {ids}' if ids else '')
                                             + f', папка {group.folder}). Повторно ничего не отправлено.'))
                return False
        self.job_id = group.job_id
        try:
            self._write_json()
        except OSError as exc:
            self.local_warning = tr(f'Записать {JOB_JSON} не удалось ({exc}); очередь — задача {self.job_id}.')
        return True

    def _record_group(self, folder, group):
        try:
            runs.write(folder, group)
        except OSError as exc:
            self.local_warning = tr(f'Не удалось записать сведения об отправке очереди ({exc}).')

    def _attempt(self):
        own = runs.read(self.spec.folder)
        return own.attempt_id if own is not None else ''

    def _members(self):
        """The folders of the calculations of the group on the server, in its order (group.json of the local
        folder of the group); this calculation's own at least."""
        names = []
        if getattr(self, 'group_dir', ''):
            try:
                names = [str(m['folder']) for m in runs.read_group(self.group_dir).get('members', []) if m.get('folder')]
            except (OSError, ValueError, KeyError, TypeError):
                names = []
        own = self.spec.folder.name
        return names if own in names else names + [own]

    def _observe(self):
        """(the state in squeue, finished, started, skipped) of this calculation — from one command for the whole group
        (squeue of the shared job and the markers of every member folder), shared by the watchers of the group: the next
        calculation of the queue, taken up when this one ends (or one by one after a restart, when the server ran many
        meanwhile), uses the answer of less than an interval ago instead of asking again. An SshError is raised as
        before (the watching handles the lost connection)."""
        key = (self.profile.address(), str(self.job_id), str(getattr(self, 'group_dir', '') or self.spec.folder.parent))
        own = self.spec.folder.name
        now = time.monotonic()
        with _GROUPS_LOCK:
            seen = _GROUPS.get(key)
        if seen is None or now - seen[0] > self.interval * 0.9 or own not in seen[2]:
            text = self.connection.text(group_command(self.job_id, self.remote_dir.rsplit('/', 1)[0], self._members()),
                                        timeout=60)
            seen = (time.monotonic(),) + parse_group(text)
            with _GROUPS_LOCK:
                _GROUPS[key] = seen
        finished, started, skipped = seen[2].get(own, ('', '', ''))
        return (cluster.queue_state(seen[1]),) + self._own_markers(finished, started, skipped)

    def _markers(self):
        command = (f'cd {self._remote()} 2>/dev/null && printf "%s|%s|%s" "$(cat {cluster.FINISHED} 2>/dev/null)" '
                   f'"$(cat {cluster.STARTED} 2>/dev/null)" "$(test -f {cluster.SKIP} && echo 1)"')
        answer = self.connection.text(command + ' || echo "||"', timeout=30).strip()
        finished, started, skipped = (answer.split('|') + ['', '', ''])[:3]
        return self._own_markers(finished, started, skipped)

    def _own_markers(self, finished, started, skipped):
        # a marker names its attempt («<code or time> <attempt>»); a marker of another attempt is not this one's
        mine = self._attempt()
        def own(marker):
            parts = marker.split()
            return bool(parts) and (len(parts) < 2 or not mine or parts[1] in (mine, '-'))
        finished, started = finished.strip(), started.strip()
        return (finished.split()[0] if own(finished) else ''), own(started), bool(skipped.strip())

    def _queue_log(self):
        """The last lines of slurm-<number>.out of the folder of the queue on the server ('' when there are
        none or the server does not answer) — «orca not found in PATH» stayed there unseen."""
        from pathlib import Path

        group = Path(getattr(self, 'group_dir', '') or '').name
        if not group or not self.job_id:
            return ''
        remote = self.remote_dir.rsplit('/', 1)[0] + '/' + group + f'/slurm-{self.job_id}.out'
        try:
            text = self.connection.text(f'tail -n 3 {shell_path(remote)} 2>/dev/null || true', timeout=30)
        except SshError:
            return ''
        return ' '.join(line.strip() for line in text.splitlines() if line.strip())[:400]

    def _watch_markers(self):
        failures = 0
        while True:
            if self._stop_asked.is_set():  # «Пропустить»: the script ends this calculation and goes on
                try:
                    self.connection.run(f'touch {self._remote(cluster.SKIP)}', timeout=30)
                except SshError:
                    pass
                self._stop_asked.clear()
                self.stopped = True
            try:
                state, finished, started, _ = self._observe()  # one answer for the whole group
                if started:
                    self._fetch_output()
                failures = 0
            except SshError as exc:
                if exc.kind in ('connection', 'timeout'):
                    delay = RETRY[min(failures, len(RETRY) - 1)]
                    failures += 1
                    if failures >= 2:
                        self._reconnect_vpn()
                    when = datetime.now().strftime('%H:%M:%S')
                    known = self._last_seen()
                    self._set('offline', tr(f'Нет связи с сервером · попытка в {when}, следующая через {delay:.0f} с. '
                                            'Очередь там продолжается.') + (f' ({known})' if known else ''))
                    self._wait(delay)
                    continue
                raise
            if finished:
                self._finish()
                return
            if state is None and not self._gone_for_sure():  # T10: the marker may come late
                self._observed('gone')
                self._set('running' if started else 'queued',
                          tr(f'Задачи очереди {self.job_id} уже нет на сервере — жду отметку конца этого расчёта.'))
                self._wait(min(self.interval, GONE_WAIT_S))
                continue
            if state is not None:
                self._gone, self._gone_size = 0, -1
                self._observed('running' if started else 'queued')
            if state is None:  # the job of the queue ended (or was cancelled) before this calculation did
                if started:
                    self._finish()
                elif self.stopped:
                    self._end(-15, 'stopped', tr('Расчёт пропущен.'))
                else:
                    why = self._queue_log()  # what the job of the queue said (its slurm-<номер>.out)
                    self._end(1, 'failed', tr(f'Задача очереди на сервере (номер {self.job_id}) закончилась раньше, '
                                              'чем дошла до этого расчёта.') + (tr(' Сервер: ') + why if why else ''))
                return
            if not started:
                self._set('queued', tr(f'Ждёт своей очереди на сервере (задача {self.job_id}).'))
            else:
                self._set('running', tr(f'Идёт на сервере (очередь — задача {self.job_id}).'))
            self._wait(self.interval)

