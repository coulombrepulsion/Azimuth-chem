"""Sextant: a SLURM server — its cores and memory, the job script, the job number and its state.

HEADER Before every calculation on a server the program asks the server what it has now: the cores (physical and the
    threads SLURM may count), the free cores, the memory and the free disk in the folder of calculations. From that it
    proposes the number of processes and the memory per process, and writes both consistently into the ORCA input (%pal
    nprocs, %maxcore) and the request to SLURM (sbatch -n, --mem). The laboratory has three servers, each a SLURM
    installation on one machine (partition LocalQ, docs/features/REMOTE_CALCULATIONS.md), with different numbers of
    cores — so nothing about cores is stored in the profile. Wilkinson convention, sections 1-8.

§1 THEORY
    sinfo -N -o '%N|%c|%m|%e|%C|%t': per node the CPUs SLURM schedules, its memory and free memory (MB) and
    allocated/idle/other/total CPUs. SLURM counts hardware threads when the node is configured with them; ORCA's MPI
    processes gain nothing from the second thread of a core, so the processes are counted in physical cores
    (lscpu: Core(s) per socket × Socket(s); Thread(s) per core). The job number is printed by sbatch as «Submitted
    batch job N». SLURM accounting (sacct) is not configured on the laboratory servers: a job that left squeue has
    ended, and the output of ORCA tells how («ORCA TERMINATED NORMALLY»).

§2 ALGORITHM
    PROBE (one shell line, runs with bash -l so that `module` and the user's PATH exist): prints «@key value» lines —
    nproc, lscpu fields, MemTotal, sinfo lines, df -Pk of the folder, the presence of sbatch/squeue/scancel and
    module, and `command -v orca`. parse_probe(text) -> Resources. plan(resources, wanted=None):
      threads = threads per core (1 when unknown); slurm_free = idle CPUs of the node with the most (or nproc);
      physical_free = slurm_free // threads (SLURM counts threads) when SLURM's total equals the logical count,
      else slurm_free; processes = wanted (clamped to 1 … physical total) or max(1, physical_free) or, when none is
      free, the physical total (the job waits); queued = processes > physical_free.
      memory per process = 60 % of free_memory() / processes, rounded down to 100 MB, within 500 … 8000;
      free_memory = MemAvailable (SLURM's FreeMem leaves out the page cache: 13 GB of 502 on serv4 while 447 GB were
      available), else the node memory of SLURM, else MemTotal; mem_request (sbatch --mem, MB) = processes × maxcore ×
      1.25, only when SLURM knows the
      memory of the node (> 1000 MB; a node configured without memory has RealMemory 1 and refuses any --mem).
    job_script(plan, setup, program) -> text of job.sh (#!/bin/bash -l: a login shell, so that `module` exists in the
      job as in the Terminal): #SBATCH -J, -N 1, -n, --mem when known, -o slurm-%j.out;
      the setup lines (e.g. «module add mpi/openmpi-x86_64», «module add orca-6.1.1»); cd "$SLURM_SUBMIT_DIR";
      ORCA by its full path (MPI ORCA needs it) with the output into <base>.out (the name of the calculation); orca_2mkl
      input -molden next to it.
    submitted(text) -> job id | None; queue_state(text) -> 'PENDING' | 'RUNNING' | … | None (not in squeue).
    with_processes(input_text, processes, maxcore) -> the ORCA input with %pal nprocs and %maxcore replaced or added.

§3 APPLICATIONS
    modules/sextant/remote_job.py; the «Запуск расчёта» card (line «serv3: свободно 40 из 48 ядер …»).

§4 SPECIFICATION
    PROBE_KEYS; probe_command(folder, partition='') -> str; parse_probe(text) -> Resources
    Resources(logical, physical, threads, memory_mb, nodes: tuple[Node], disk_free_mb, slurm: bool, orca: str)
    Node(name, cpus, memory_mb, free_mb, alloc, idle, other, total, state)
    plan(resources, wanted=None) -> Plan(processes, maxcore, mem_request, physical, physical_free, queued)
    summary(resources, plan) -> str (for the card); job_script(plan, setup='', name='azimuth', base='input',
    program='orca' | 'mopac') -> str
    free_memory(resources) -> MB | None; suggested_setup(resources, kind='orca') -> str (module or /opt/orca* lines);
    setup_for(own, resources, kind, directives=(), program='') -> str (the lines of the profile + those found for the program;
      directives — the #SBATCH lines of the profile, first); split_setup(setup) -> (#SBATCH lines, commands);
      commands(setup)
    submitted(text) -> str | None; queue_state(text) -> str | None; FINISHED_MARK
    with_processes(text, processes, maxcore) -> str

§5 PROCEDURES — below.

§6 NOTES
    ASSUMPTION: the servers run SLURM ≥ 20 (sinfo %e, %C) and Linux with lscpu and /proc/meminfo; checked against
    the output of serv3 (27 October 2026) for sinfo; lscpu, free and scontrol of the three servers are still asked.
    The 60 % share and the 1.25 margin are the same rule as for this computer (advice.recommended) with a larger
    upper bound for servers.

§7 TEST CASES tests/sextant/test_cluster.py (recorded answers; hyperthreading; a busy node; memory unknown to SLURM).

§8' ROBUSTNESS
    Every field of the probe may be missing or not a number: it is then None and the plan falls back to what is
    known (at least 1 process, 1000 MB). Nothing here touches the network.
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass

from azimuth.i18n import tr

FINISHED_MARK = 'ORCA TERMINATED NORMALLY'
PROBE_KEYS = ('nproc', 'lscpu', 'mem', 'sinfo', 'df', 'has', 'orca')


@dataclass(frozen=True)
class Node:
    name: str
    cpus: int | None
    memory_mb: int | None
    free_mb: int | None
    alloc: int | None
    idle: int | None
    other: int | None
    total: int | None
    state: str


@dataclass(frozen=True)
class Resources:
    logical: int | None
    physical: int | None
    threads: int | None
    memory_mb: int | None
    nodes: tuple
    disk_free_mb: int | None
    slurm: bool
    orca: str
    available_mb: int | None = None  # MemAvailable: free memory including the page cache the system gives back
    orca_dirs: tuple = ()  # /opt/orca*/orca found on the server
    orca_modules: tuple = ()  # environment modules with «orca» in the name
    programs: tuple = ()  # ((name, path), …) — orca, g16, g09, psi4, xtb, crest found in PATH of the login shell
    program_modules: tuple = ()  # environment modules of these programs
    found: tuple = ()  # ((name, path), …) — the files of the programs outside PATH: conda, /opt, the home folder
    mpi_modules: tuple | None = None  # the Open MPI modules of the server; None — the probe did not ask (old answers)
    load: float | None = None  # the 1-minute load average: the cores busy now by what runs there


@dataclass(frozen=True)
class Plan:
    processes: int
    maxcore: int
    mem_request: int | None
    physical: int
    physical_free: int
    queued: bool


# the file names looked for outside PATH (probe_command(search=True)): the environments of conda, /opt, /usr/local and
# the home folder (the owner, 2026-11-22: «в папке должен был быть установлен crest, а еще там xtb») — the names alone,
# five folders deep, 25 s at most
SEARCHED = ('orca', 'xtb', 'crest', 'mopac', 'psi4', 'nwchem', 'pw.x', 'cp2k.psmp', 'cp2k.popt', 'cp2k.ssmp')
SEARCH = ('T=""; command -v timeout >/dev/null 2>&1 && T="timeout 25"; '
          '$T find "$HOME" /opt /usr/local -maxdepth 5 \\( -type f -o -type l \\) \\( '
          + ' -o '.join(f'-name {shlex.quote(n)}' for n in SEARCHED) + ' \\) -perm -100 -not -path "*/pkgs/*" 2>/dev/null | head -n 60 '
          '| sed "s/^/@found /"')


def probe_command(folder, partition='', search=False):
    """One line for `bash -lc`: everything about the server that the plan needs (§2). Partition — the
    nodes of sinfo are of that partition only (the free cores of the partition the jobs go to). Search — the programs
    are looked for outside PATH too (conda, /opt, the home folder; up to 25 s — «Узнать ресурсы», not every sending)."""
    from modules.sextant.ssh import shell_path

    where = shell_path(folder)
    only = f' -p {shlex.quote(partition.strip())}' if (partition or '').strip() else ''
    parts = [
        # without nproc and lscpu (macOS — the fake server of the tests runs the probe on the Mac) the processors
        # and the memory come from getconf and sysctl; a Linux server answers the first lines and ignores these
        'echo "@nproc $(nproc 2>/dev/null || getconf _NPROCESSORS_ONLN 2>/dev/null)"',
        'sysctl -n hw.physicalcpu 2>/dev/null | sed "s/^/@physical /"',
        'sysctl -n hw.memsize 2>/dev/null | sed "s/^/@memsize /"',
        'lscpu 2>/dev/null | grep -E "^(CPU\\(s\\)|Thread\\(s\\) per core|Core\\(s\\) per socket|Socket\\(s\\)):" '
        '| sed "s/^/@lscpu /"',
        'grep -E "^(MemTotal|MemAvailable):" /proc/meminfo 2>/dev/null | sed "s/^/@mem /"',
        f'sinfo -h -N{only} -o "%N|%c|%m|%e|%C|%t" 2>/dev/null | sed "s/^/@sinfo /"',
        f'mkdir -p {where} 2>/dev/null; df -Pk {where} 2>/dev/null | tail -1 | sed "s/^/@df /"',
        'for c in sbatch squeue scancel; do command -v $c >/dev/null 2>&1 && echo "@has $c"; done',
        'type module >/dev/null 2>&1 && echo "@has module"',
        'echo "@orca $(command -v orca 2>/dev/null)"',
        'ls -d /opt/orca*/orca 2>/dev/null | sed "s/^/@orcadir /"',
        'type module >/dev/null 2>&1 && module -t avail 2>&1 | grep -i orca | sed "s/^/@module /"',
        # the Open MPI module ORCA needs: only one the server has goes into the job (serv1 has no mpi/openmpi-x86_64)
        'echo "@mpiprobed"; type module >/dev/null 2>&1 && module -t avail 2>&1 | grep -i openmpi | sed "s/^/@mpimodule /"',
        # the programs of Sextant on the server — in PATH or as modules
        # and MOPAC (mopac, MOPAC2016.exe)
        # and pw.x of Quantum ESPRESSO
        'for p in orca g16 g09 psi4 xtb crest mopac MOPAC2016.exe pw.x cp2k.psmp cp2k.popt cp2k.ssmp cp2k; do '
        'x=$(command -v $p 2>/dev/null) && echo "@prog $p $x"; '
        'done',
        'type module >/dev/null 2>&1 && module -t avail 2>&1 | grep -iE "orca|gaussian|g16|g09|psi4|xtb|crest|mopac|espresso|^qe[-/]|cp2k" '
        '| sed "s/^/@progmodule /"',
    ]
    if search:
        parts += [SEARCH]
    parts += [
        # the cores busy now — a server without SLURM has no other count (the 1-minute load average of Linux)
        'cut -d" " -f1 /proc/loadavg 2>/dev/null | sed "s/^/@load /"',
        'true',  # the code of the probe is its last command's: a server without an ORCA module (serv2) is no failure
    ]
    return 'bash -lc ' + shlex.quote('; '.join(parts))


def _int(text):
    try:
        return int(str(text).strip().split('.')[0])
    except (TypeError, ValueError):
        return None


def parse_probe(text):
    logical = physical = threads = memory = disk = None
    sockets = per_socket = None
    nodes, has, orca = [], set(), ''
    available, dirs, modules = None, [], []
    programs, program_modules = [], []
    found, loads = [], []
    mpi = None
    mac_physical = mac_memory = None
    for raw in (text or '').splitlines():
        line = raw.strip()
        if not line.startswith('@'):
            continue
        key, _, value = line[1:].partition(' ')
        value = value.strip()
        if key == 'nproc':
            logical = _int(value) or logical
        elif key == 'lscpu':
            name, _, number = value.partition(':')
            number = _int(number)
            if name == 'CPU(s)':
                logical = number or logical
            elif name == 'Thread(s) per core':
                threads = number
            elif name == 'Core(s) per socket':
                per_socket = number
            elif name == 'Socket(s)':
                sockets = number
        elif key == 'mem':
            name, _, number = value.partition(':')
            kb = _int(number.split()[0]) if number.split() else None
            if name == 'MemTotal':
                memory = kb // 1024 if kb else None
            elif name == 'MemAvailable':
                available = kb // 1024 if kb else None
        elif key == 'sinfo':
            fields = value.split('|')
            if len(fields) >= 6:
                counts = [_int(x) for x in fields[4].split('/')] if fields[4] else []
                counts = (counts + [None] * 4)[:4]
                nodes.append(Node(fields[0], _int(fields[1]), _int(fields[2]), _int(fields[3]), *counts,
                                  fields[5].strip()))
        elif key == 'df':
            fields = value.split()
            if len(fields) >= 4:
                kb = _int(fields[3])
                disk = kb // 1024 if kb is not None else None
        elif key == 'physical':
            mac_physical = _int(value)
        elif key == 'memsize':
            size = _int(value)
            mac_memory = size // (1024 * 1024) if size else None
        elif key == 'has':
            has.add(value)
        elif key == 'orca':
            orca = value
        elif key == 'orcadir' and value.endswith('/orca'):
            dirs.append(value[: -len('/orca')])
        elif key == 'prog':
            name, _, path = value.partition(' ')
            if name and path.strip():
                programs.append((name, path.strip()))
        elif key == 'found':
            name = value.rsplit('/', 1)[-1]
            if value.startswith('/') and (name, value) not in found:
                found.append((name, value))
        elif key == 'load':
            try:
                loads.append(float(value.replace(',', '.')))
            except ValueError:
                pass
        elif key == 'mpiprobed':
            mpi = mpi or []
        elif key == 'mpimodule':
            name = value.split('(')[0].strip().rstrip(':')
            if name and not name.startswith('/'):
                mpi = (mpi or []) + [name]
        elif key == 'progmodule':
            name = value.split('(')[0].strip().rstrip(':')
            if name and not name.startswith('/') and name not in program_modules:
                program_modules.append(name)
        elif key == 'module':
            name = value.split('(')[0].strip().rstrip(':')
            if name and not name.startswith('/') and name not in modules:
                modules.append(name)
    if per_socket and sockets:
        physical = per_socket * sockets
    elif logical and threads:
        physical = max(1, logical // threads)
    elif mac_physical:  # macOS — sysctl
        physical = mac_physical
        threads = max(1, logical // mac_physical) if logical else None
    if memory is None and mac_memory:
        memory = mac_memory
    return Resources(logical, physical, threads, memory, tuple(nodes), disk, {'sbatch', 'squeue'} <= has, orca,
                     available, tuple(dirs), tuple(modules), tuple(programs), tuple(program_modules),
                     tuple(found), None if mpi is None else tuple(mpi), max(loads) if loads else None)


# where a program of Sextant is on the server (the names of its files and modules)
PROGRAM_FILES = {'orca': ('orca',), 'gaussian': ('g16', 'g09'), 'psi4': ('psi4',), 'xtb': ('xtb',), 'crest': ('crest',),
                 'mopac': ('mopac', 'MOPAC2016.exe'), 'qe': ('pw.x',),  # Quantum ESPRESSO
                 'cp2k': ('cp2k.psmp', 'cp2k.popt', 'cp2k.ssmp', 'cp2k')}
PROGRAM_MODULES = {'orca': ('orca',), 'gaussian': ('gaussian', 'g16', 'g09'), 'psi4': ('psi4',), 'xtb': ('xtb',),
                   'crest': ('crest',), 'mopac': ('mopac',), 'qe': ('espresso', 'qe/', 'qe-'), 'cp2k': ('cp2k',)}


def found_programs(resources):
    """[(program kind, path)] — one path for each program found outside PATH (found_outside), in the order of
    PROGRAM_FILES: the eight copies of xtb in the environments of conda are one line, not eight."""
    return [(kind, found_outside(resources, kind)) for kind in PROGRAM_FILES if found_outside(resources, kind)]


def found_outside(resources, kind):
    """The file of the program found outside PATH (conda, /opt, the home folder) — the shortest path, or ''."""
    files = PROGRAM_FILES.get(kind, (kind,))
    paths = [path for name, path in resources.found if name in files and '/pkgs/' not in path]  # not the cache of conda
    return min(paths, key=lambda path: (path.count('/'), path)) if paths else ''


def find_on_server(resources, kind, setup='', program=''):
    """How the program kind is reached on the server: «/opt/orca6/orca», «модуль prog/orca6.1.1», «строки окружения
    профиля» — or None when the probe found nothing (then the calculation of that program cannot start there).
    Program — the lines of the profile for this program alone (ServerProfile.setup_of): with them it is the user's."""
    if (program or '').strip():
        return tr('строки окружения профиля')
    if kind == 'orca':
        chosen = _orca_of_job(resources, setup)
        if chosen:
            return chosen
    files = PROGRAM_FILES.get(kind, (kind,))
    for name, path in resources.programs:
        if name in files:
            return path
    if kind == 'orca':
        if resources.orca:
            return resources.orca
        if resources.orca_dirs:
            return resources.orca_dirs[0] + '/orca'
    words = PROGRAM_MODULES.get(kind, (kind,))
    for module in resources.program_modules + (resources.orca_modules if kind == 'orca' else ()):
        if any(word in module.lower() for word in words):
            return tr('модуль ') + module
    if setup and any(word in commands(setup).lower() for word in words):  # not a partition called «orca»
        return tr('строки окружения профиля')
    return found_outside(resources, kind) or None


def _orca_of_job(resources, setup=''):
    """The ORCA the job will run, as the setup lines put it into PATH: those of the profile when they name ORCA, else
    the ones found (suggested_setup — the module, else the newest /opt/orca* folder). The ORCA in the PATH of a login
    was reported before, though the job took another: «/opt/orca5/orca» next to /opt/orca6.1.1 the job ran
    (Windows check, serv .103, 2026-11-24). «строки окружения профиля» when they name ORCA in another way; '' when no
    line names it."""
    lines = commands(setup or '')
    own = any(word in lines.lower() for word in PROGRAM_MODULES['orca'])
    if not own:
        lines += '\n' + suggested_setup(resources, 'orca')
    for folder in sorted(resources.orca_dirs, key=_version, reverse=True):
        if re.search(re.escape(folder) + r'(/|:|\s|$)', lines):
            return folder + '/orca'
    for module in resources.orca_modules:
        if re.search(r'\b(?:load|add)\s+' + re.escape(module) + r'(\s|$)', lines):
            return tr('модуль ') + module
    return tr('строки окружения профиля') if own else ''


def _node(resources):
    """The node with the most idle CPUs (the laboratory servers have one)."""
    usable = [n for n in resources.nodes if n.idle is not None or n.cpus is not None]
    if not usable:
        return None
    return max(usable, key=lambda n: (n.idle or 0, n.cpus or 0))


def plan(resources, wanted=None, maxcore=None):
    node = _node(resources)
    threads = resources.threads or 1
    slurm_total = (node.total or node.cpus) if node else None
    logical = resources.logical or slurm_total or 1
    physical = resources.physical or (logical // threads if threads > 1 else logical) or 1
    if node is not None and node.idle is not None:
        free = node.idle
        if threads > 1 and slurm_total and slurm_total >= logical:  # SLURM schedules hardware threads
            free //= threads
    else:
        free = physical
    free = max(0, min(free, physical))
    busy = busy_cores(resources)
    if busy:  # what runs there outside SLURM (or on a server without it) is busy too
        free = max(0, min(free, physical - busy))
    if not resources.slurm:  # nothing there keeps the jobs apart: the cores are shared by this rule alone
        free = max(0, min(free, int(BUSY_SHARE * physical) - (physical - free)))
    if wanted is not None:
        processes = max(1, min(int(wanted), physical))
    else:
        processes = free if free > 0 else physical
    memory = free_memory(resources)
    if maxcore is not None:  # the memory per process of the field of Sextant (advised there before)
        maxcore = max(100, int(maxcore))
    elif memory and memory > 1000:
        maxcore = int(0.6 * memory / processes) // 100 * 100
        maxcore = max(500, min(MAXCORE_LIMIT, maxcore))
    else:
        maxcore = 1000
    known = node is not None and node.memory_mb is not None and node.memory_mb > 1000
    mem_request = int(processes * maxcore * 1.25) if known else None
    return Plan(processes, maxcore, mem_request, physical, free, processes > free)


BUSY_SHARE = 0.8  # the owner, 2026-11-22: «не больше 80% занимать на всех серверах ядер, включая уже занятые»


def busy_cores(resources):
    """The cores busy now by the load of the server (None unknown → 0): 3.4 → 4, 0.2 → 0."""
    return int(resources.load + 0.7) if resources.load else 0


def room(resources):
    """The cores a new calculation may take so that no more than BUSY_SHARE of the node is busy with it."""
    chosen = plan(resources)
    if not resources.slurm:  # plan() has counted it already
        return chosen.physical_free
    return max(0, min(chosen.physical_free, int(BUSY_SHARE * chosen.physical) - (chosen.physical - chosen.physical_free)))


def no_room(resources, chosen, title=''):
    """Why a calculation with the plan chosen cannot start on a server without SLURM now ('' — it can, or the server
    has SLURM: its queue decides). Without SLURM the calculation starts at once (nohup), so the cores must be free."""
    if resources.slurm or chosen.processes <= chosen.physical_free:
        return ''
    most = int(BUSY_SHARE * chosen.physical)
    if chosen.physical_free < 1:
        return tr(f'На сервере {title} нет SLURM — расчёт запускается сразу (nohup), а свободных ядер сейчас нет: занято '
                  f'{chosen.physical - chosen.physical_free} из {chosen.physical}, занимать можно не больше {most} '
                  f'({int(BUSY_SHARE * 100)} %). Подождите, пока расчёты других закончатся.')
    return tr(f'На сервере {title} нет SLURM — расчёт запускается сразу (nohup), а свободно сейчас {chosen.physical_free} '
              f'из {chosen.physical} ядер (занимать можно не больше {most}, {int(BUSY_SHARE * 100)} %). Уменьшите число '
              f'ядер до {chosen.physical_free} или подождите.')


# what is said when the program of a job is not found on the server (server_setup)
NOT_FOUND = {
    'orca': 'На сервере {} не нашлась ORCA. Впишите строки окружения в «Сервер…» (например, module load orca-6.1.1).',
    'mopac': 'На сервере {} не нашёлся MOPAC (mopac в PATH или модуль). Впишите строки окружения в «Сервер…» '
             '(например, module load mopac).',
    'xtb': 'На сервере {} не нашёлся xtb (xtb в PATH или модуль). Впишите строки окружения в «Сервер…» '
           '(например, module load xtb).',
    'cp2k': 'На сервере {} не нашёлся CP2K ни в PATH, ни среди модулей. Впишите строки окружения в «Сервер…» '
            '(например, module load cp2k).',
    'qe': 'На сервере {} не нашёлся pw.x (Quantum ESPRESSO) ни в PATH, ни среди модулей. Впишите строки окружения в '
          '«Сервер…» (например, module load qe).',
}


def server_setup(profile, resources, kind, extra=()):
    """The lines of a job of kind on the server of profile: the #SBATCH lines of the profile and extra, the common lines
    and those of the program (setup_for). ValueError (NOT_FOUND) when the program is not found there. One place for the
    four ways of sending — a calculation of the window, a queue, a crystal (QE, CP2K) and one sent without the window
    (azimuth/headless_server.py): before 0.222.26 each checked on its own, and the checks had drifted apart (a queue
    of ORCA was sent with no ORCA found)."""
    setup = setup_for(profile.setup, resources, kind, list(profile.directives()) + list(extra), profile.setup_of(kind))
    if kind == 'orca':  # ORCA: lines that load something, or orca in PATH (the lines may load it under any name)
        missing = not commands(setup) and not resources.orca
    else:
        missing = find_on_server(resources, kind, setup, profile.setup_of(kind)) is None
    if missing:
        raise ValueError(tr(NOT_FOUND.get(kind, NOT_FOUND['orca'])).format(profile.title()))
    return setup


def server_plan(resources, wanted=None, maxcore=None, title=''):
    """plan() of a job on the server; ValueError (no_room) when a server without SLURM has not the cores free."""
    chosen = plan(resources, wanted=wanted, maxcore=maxcore)
    refused = no_room(resources, chosen, title)
    if refused:
        raise ValueError(refused)
    return chosen


MAXCORE_LIMIT = 8000  # MB per ORCA process, as for this computer (advice.recommended)


def free_memory(resources):
    """The memory a new job can use, MB: MemAvailable of the server (with the page cache, which the system gives back:
    on serv4 SLURM's FreeMem was 13 GB of 502 while 447 GB were available), else SLURM's node memory, else MemTotal."""
    if resources.available_mb and resources.available_mb > 1000:
        return resources.available_mb
    node = _node(resources)
    if node is not None and node.memory_mb and node.memory_mb > 1000:
        return node.memory_mb
    return resources.memory_mb


def _version(text):
    return tuple(int(x) for x in re.findall(r'\d+', text)) or (0,)


def suggested_setup(resources, kind='orca'):
    """Lines that put ORCA (and Open MPI) into PATH in the job: the newest ORCA module of the server, else the newest
    /opt/orca* folder with the Open MPI module. '' when nothing was found (the user writes them). MOPAC — the
    newest MOPAC module, '' when mopac is in PATH or not found."""
    if kind in ('mopac', 'xtb', 'qe', 'cp2k'):  # Quantum ESPRESSO — its module (it brings its MPI); CP2K
        words = PROGRAM_MODULES[kind]
        modules = [m for m in resources.program_modules if any(w in m.lower() for w in words)]
        if modules:
            return f'module load {best_module(modules)}'
        return path_line(resources, kind)
    mpi = mpi_line(resources)
    if resources.orca_modules:
        return f'{mpi}module load {best_module(resources.orca_modules)}'
    if resources.orca_dirs:
        best = max(resources.orca_dirs, key=_version)
        return f'{mpi}export PATH={best}:$PATH\nexport LD_LIBRARY_PATH={best}:$LD_LIBRARY_PATH'
    return path_line(resources, kind)


MPI_MODULE = 'mpi/openmpi-x86_64'  # of the laboratory servers serv2–serv4


def mpi_line(resources):
    """«module load <Open MPI>» with its line end — only a module the server has ('' when it has none: serv1 answered
    «Unable to locate a modulefile for mpi/openmpi-x86_64», 2026-11-23). An answer of the probe from before the
    question (mpi_modules None) keeps the module of the laboratory."""
    if resources.mpi_modules is None or MPI_MODULE in resources.mpi_modules:
        return f'module load {MPI_MODULE}\n'
    if resources.mpi_modules:
        return f'module load {max(resources.mpi_modules, key=_version)}\n'
    return ''


def best_module(modules):
    """The module to load of several of one program: the one without a version in its name is the default the
    administrators keep («prog/orca» next to «prog/orca_4_2_1» — the old 4.2.1 was taken as the «newest», and ORCA was
    not found in the job, serv1 2026-11-23), the shortest of such; else the newest version."""
    plain = [m for m in modules if not re.search(r'\d', m.rsplit('/', 1)[-1])]
    if plain:
        return min(plain, key=lambda m: (len(m), m))
    return max(modules, key=_version)


def path_line(resources, kind):
    """«export PATH=<folder>:$PATH» of the program found outside PATH; '' when it is in PATH or was not found."""
    files = PROGRAM_FILES.get(kind, (kind,))
    if any(name in files for name, _ in resources.programs) or (kind == 'orca' and resources.orca):
        return ''
    path = found_outside(resources, kind)
    return f'export PATH={path.rsplit("/", 1)[0]}:$PATH' if path else ''


def setup_for(own, resources, kind='orca', directives=(), program=''):
    """The lines of the profile are kept and come first;
    the lines found for the program (suggested_setup) are added after them unless the lines of the profile name the
    program themselves (a module or a folder of it — then they are the user's choice for it). Program — the lines of
    the profile for this program alone (ServerProfile.setup_of(kind)): they come after the common ones and nothing
    found on the server is added — «source …/setup» of CP2K next to «module load cp2k» is what the user wrote."""
    head = '\n'.join(directives)  # the #SBATCH lines of the profile (partition, time…) first
    program = (program or '').strip()
    if program:
        body = '\n'.join(t for t in ((own or '').strip(), program) if t)
    else:
        body = _setup_lines(own, resources, kind)
    return '\n'.join(t for t in (head, body) if t)


def _setup_lines(own, resources, kind):
    own = (own or '').strip()
    found = suggested_setup(resources, kind)
    if not own:
        return found
    if any(word in commands(own).lower() for word in PROGRAM_MODULES.get(kind, (kind,))):
        return own
    return own + ('\n' + found if found else '')


def summary(resources, chosen, title=''):
    """«serv3: свободно 40 из 48 ядер, память 256 ГБ, на диске 52 ГБ» for the card."""
    head = (title + ': ') if title else ''
    parts = [tr(f'свободно {chosen.physical_free} из {chosen.physical} ядер')]
    memory = free_memory(resources)
    if memory:
        parts.append(tr(f'свободно памяти {memory / 1024:.0f} ГБ'))
    if resources.disk_free_mb is not None:
        parts.append(tr(f'на диске {resources.disk_free_mb / 1024:.0f} ГБ'))
    return head + ', '.join(parts)


def qe_lines(processes, steps):
    """The body of a job of Quantum ESPRESSO: pw.x found in PATH (after the setup lines), the steps one after
    another (pw.x through mpirun -np N, else srun, else serial; dos.x next to pw.x, serial), each only when the one
    before ended well; everything printed into pw.out, as on this computer."""
    from modules.sextant.qe_inputs import OPTIONAL, PARALLEL

    n = int(processes)
    lines = [
        'cd "$SLURM_SUBMIT_DIR"',
        'export OMP_NUM_THREADS=1',
        'PW="$(command -v pw.x)"',
        'if [ -z "$PW" ]; then echo "Azimuth: pw.x not found in PATH (setup lines of the server profile)" >&2; exit 2; fi',
        'BIN="$(dirname "$PW")"',
        # mpirun first, as for CP2K: under srun the MPI of a build without the PMI of SLURM (the package of conda-forge)
        # started N separate copies of pw.x, each «Number of MPI processes: 1», writing into one pw.out (serv3 2026-11-23)
        f'if [ {n} -gt 1 ] && command -v mpirun >/dev/null 2>&1; then RUN="mpirun -np {n}"; '
        f'elif [ {n} -gt 1 ] && command -v srun >/dev/null 2>&1; then RUN="srun -n {n}"; else RUN=""; fi',
        ': > pw.out',
    ]
    for name, tool in steps:
        exe = '"$PW"' if tool == 'pw.x' else f'"$BIN/{tool}"'
        run = '$RUN ' if tool in PARALLEL else ''  # ph.x in parallel as pw.x
        if tool in OPTIONAL:  # projwfc.x — its own output, its error not the job's
            lines.append(f'{exe} -in {shlex.quote(name)} > {OPTIONAL[tool]} 2>&1 || true')
            continue
        lines.append(f'{run}{exe} -in {shlex.quote(name)} >> pw.out 2>&1 || exit $?')
    lines.append('rm -rf out')  # the wave functions of the run: large, not brought back
    lines.append('exit 0')
    return lines


def cp2k_lines(processes, name='azimuth.inp'):
    """The body of a job of CP2K: the MPI build (cp2k.psmp, cp2k.popt) or another one from PATH, through
    mpirun -np N (else srun, else serial), its output into cp2k.out; the restart files of the wave functions removed."""
    n = int(processes)
    return [
        'cd "$SLURM_SUBMIT_DIR"',
        'export OMP_NUM_THREADS=1',
        'CP2K="$(command -v cp2k.psmp || command -v cp2k.popt || command -v cp2k.ssmp || command -v cp2k)"',
        'if [ -z "$CP2K" ]; then echo "Azimuth: cp2k not found in PATH (setup lines of the server profile)" >&2; exit 2; fi',
        # mpirun first: the Open MPI of the toolchain of CP2K is built without the PMI of SLURM, and under srun every
        # process stopped in MPI_Init («you must use either SLURM's PMI-1 or PMI-2 support», serv3 2026-11-23)
        f'if [ {n} -gt 1 ] && command -v mpirun >/dev/null 2>&1; then RUN="mpirun -np {n}"; '
        f'elif [ {n} -gt 1 ] && command -v srun >/dev/null 2>&1; then RUN="srun -n {n}"; else RUN=""; fi',
        f'$RUN "$CP2K" -i {shlex.quote(name)} > cp2k.out 2>&1',
        'code=$?',
        'rm -f -- *.wfn *.wfn.bak-*',
        'exit $code',
    ]


def split_setup(setup):
    """The setup lines of a job → (#SBATCH lines, the commands). sbatch reads #SBATCH only before the
    first command, so the partition, the time limit and the like written among the setup lines (or of the profile:
    remote.ServerProfile.directives) go into the head of the script."""
    head, body = [], []
    for line in (setup or '').replace('&&', '\n').splitlines():
        line = line.strip()
        if line.upper().startswith('#SBATCH'):
            head.append('#SBATCH' + line[len('#SBATCH'):])
        elif line:
            body.append(line)
    return head, body


def commands(setup):
    """The setup lines that are commands (not #SBATCH)."""
    return '\n'.join(split_setup(setup)[1])


EXIT_MARK = '.az-exit'
# the end of a job, written by the job itself (its exit code): a job no longer in the queue is known to have ended at
# once (it took three answers of the queue with the output not growing — on Windows, whose ssh opens a connection for
# every command, about four minutes for a job that broke at its start, 2026-11-24); a mark left by an earlier run in
# the folder goes first; the queue is asked about the mark only when it does not list the job
END_LINES = [f'rm -f "${{SLURM_SUBMIT_DIR:-.}}/{EXIT_MARK}"', f"trap 'echo $? > \"${{SLURM_SUBMIT_DIR:-.}}/{EXIT_MARK}\"' EXIT"]


def job_script(chosen, setup='', name='azimuth', base='input', program='orca', steps=None):
    """Base — the name of the input without .inp (core.file_base); the output is <base>.out. Program
    'mopac' — one task with chosen.processes threads (OpenMP: -n 1 -c N, OMP_NUM_THREADS), «mopac <base>.mop»; MOPAC
    writes <base>.out, .aux and .arc itself, what it prints goes to <base>.stdout."""
    safe = re.sub(r'[^A-Za-z0-9._-]', '_', name)[:40] or 'azimuth'
    lines = [
        '#!/bin/bash -l',
        f'#SBATCH -J {safe}',
        '#SBATCH -N 1',
    ]
    if program in ('mopac', 'xtb'):  # OpenMP: one task with its threads
        lines += ['#SBATCH -n 1', f'#SBATCH -c {chosen.processes}']
    elif program in ('qe', 'cp2k'):  # MPI tasks of pw.x, one thread each; of CP2K
        lines += [f'#SBATCH -n {chosen.processes}', '#SBATCH -c 1']
    else:
        lines.append(f'#SBATCH -n {chosen.processes}')
    if chosen.mem_request:
        lines.append(f'#SBATCH --mem={chosen.mem_request}M')
    head, body = split_setup(setup)
    lines += head + ['#SBATCH -o slurm-%j.out', '# written by Azimuth (Sextant); one job = one folder', ''] + END_LINES + body
    if program == 'qe':
        return '\n'.join(lines + qe_lines(chosen.processes, steps or (('pw.in', 'pw.x'),)) + [''])
    if program == 'cp2k':
        return '\n'.join(lines + cp2k_lines(chosen.processes) + [''])
    if program == 'xtb':  # the environment of runner.environment for xtb; the arguments of <base>.args
        lines += [
            'cd "$SLURM_SUBMIT_DIR"',
            f'export OMP_NUM_THREADS={chosen.processes} OMP_STACKSIZE=1G OMP_MAX_ACTIVE_LEVELS=1',
            'ulimit -s unlimited 2> /dev/null || true',
            'XTB="$(command -v xtb)"',
            'if [ -z "$XTB" ]; then echo "Azimuth: xtb not found in PATH (setup lines of the server profile)" >&2; exit 2; fi',
            f'eval "\"\$XTB\" $(cat {shlex.quote(base + ".args")})" > {shlex.quote(base + ".out")} 2>&1',
            'exit $?',
            '',
        ]
        return '\n'.join(lines)
    if program == 'mopac':
        lines += [
            'cd "$SLURM_SUBMIT_DIR"',
            f'export OMP_NUM_THREADS={chosen.processes}',
            'MOPAC="$(command -v mopac || command -v MOPAC2016.exe)"',
            'if [ -z "$MOPAC" ]; then echo "Azimuth: mopac not found in PATH (setup lines of the server profile)" >&2; '
            'exit 2; fi',
            f'"$MOPAC" {shlex.quote(base + ".mop")} > {shlex.quote(base + ".stdout")} 2>&1',
            'exit $?',
            '',
        ]
        return '\n'.join(lines)
    lines += [
        'cd "$SLURM_SUBMIT_DIR"',
        'ORCA="$(command -v orca)"',
        'if [ -z "$ORCA" ]; then echo "Azimuth: orca not found in PATH (setup lines of the server profile)" >&2; exit 2; fi',
        f'"$ORCA" {shlex.quote(base + ".inp")} > {shlex.quote(base + ".out")} 2>&1',
        'code=$?',
        f'"$(dirname "$ORCA")/orca_2mkl" {shlex.quote(base)} -molden > /dev/null 2>&1 || true',
        'exit $code',
        '',
    ]
    return '\n'.join(lines)


BATCH_FOLDER_SUFFIX = '-batch'  # the folder of the script of a queue sent at once, next to its jobs
STARTED, FINISHED, SKIP = '.az-started', '.az-finished', '.az-skip'


def batch_script(chosen, setup, name, jobs, program='orca'):
    """One SLURM job that runs the calculations of a queue one after another, as orca.sh of the laboratory runs every
    *.inp of a folder. jobs — [(folder name, base)] of the job folders next to the folder of this script (all in the
    calculation folder of the server). Every job leaves markers in its folder: STARTED (the time), FINISHED (the exit
    code); a job with FINISHED is not run again (the script submitted once more goes on where it stopped); a file SKIP
    made in the folder by Azimuth («Пропустить») ends that calculation (its process group) and the script goes to the
    next. ORCA runs in its own session (setsid where the server has it) so that its MPI processes go with it; orca_2mkl
    writes the Molden file after each; the scratch files are removed. A job is (folder, base, attempt id); STARTED is
    «<time> <attempt>», FINISHED «<exit code> <attempt>», each written to a temporary file and moved (a cut write never
    leaves half a marker)."""
    safe = re.sub(r'[^A-Za-z0-9._-]', '_', name)[:40] or 'azimuth'
    lines = ['#!/bin/bash -l', f'#SBATCH -J {safe}', '#SBATCH -N 1']
    if program in ('mopac', 'xtb'):
        lines += ['#SBATCH -n 1', f'#SBATCH -c {chosen.processes}']
    else:
        lines.append(f'#SBATCH -n {chosen.processes}')
    if chosen.mem_request:
        lines.append(f'#SBATCH --mem={chosen.mem_request}M')
    head, body = split_setup(setup)
    lines += head + ['#SBATCH -o slurm-%j.out',
                     '# written by Azimuth (Sextant): the calculations of a queue one after another in one job', ''] + body
    if program == 'mopac':
        lines += [f'export OMP_NUM_THREADS={chosen.processes}',
                  'PROGRAM="$(command -v mopac || command -v MOPAC2016.exe)"',
                  'if [ -z "$PROGRAM" ]; then echo "Azimuth: mopac not found in PATH" >&2; exit 2; fi']
        run = '"$PROGRAM" "$2.mop" > "$2.stdout" 2>&1'
        after = ''
    elif program == 'xtb':
        lines += [f'export OMP_NUM_THREADS={chosen.processes} OMP_STACKSIZE=1G OMP_MAX_ACTIVE_LEVELS=1',
                  'ulimit -s unlimited 2> /dev/null || true',
                  'PROGRAM="$(command -v xtb)"',
                  'if [ -z "$PROGRAM" ]; then echo "Azimuth: xtb not found in PATH" >&2; exit 2; fi']
        # in a shell of its own (setsid takes a program, not eval): the arguments of <base>.args of the job
        run = 'bash -c \'eval "\\"$0\\" $(cat "$1.args")"\' "$PROGRAM" "$2" > "$2.out" 2>&1'
        after = ''
    else:
        lines += ['PROGRAM="$(command -v orca)"',
                  'if [ -z "$PROGRAM" ]; then echo "Azimuth: orca not found in PATH (setup lines of the server profile)" '
                  '>&2; exit 2; fi']
        run = '"$PROGRAM" "$2.inp" > "$2.out" 2>&1'
        after = '  "$(dirname "$PROGRAM")/orca_2mkl" "$2" -molden > /dev/null 2>&1 || true'
    lines += [
        'ROOT="$(cd "$SLURM_SUBMIT_DIR/.." && pwd)"',
        'if command -v setsid > /dev/null 2>&1; then SESSION=setsid; else SESSION=; fi',
        'run_one() {',
        '  cd "$ROOT/$1" || return',
        f'  [ -f {FINISHED} ] && return',
        f'  rm -f {SKIP}',
        f'  printf "%s %s\\n" "$(date +%s)" "$3" > {STARTED}.tmp && mv -f {STARTED}.tmp {STARTED}',
        f'  $SESSION {run} &',
        '  pid=$!',
        '  while kill -0 "$pid" 2> /dev/null; do',
        f'    if [ -f {SKIP} ]; then kill -TERM -- "-$pid" 2> /dev/null || kill -TERM "$pid" 2> /dev/null; fi',
        '    sleep "${AZ_POLL:-5}"',
        '  done',
        '  wait "$pid"',
        '  code=$?',
    ] + ([after] if after else []) + [
        '  rm -f -- *.tmp *.tmp.*',
        f'  printf "%s %s\\n" "$code" "$3" > {FINISHED}.tmp && mv -f {FINISHED}.tmp {FINISHED}',
        '}',
    ]
    for job in jobs:  # (folder, base, attempt id) — the markers name the attempt they belong to
        folder, base, attempt = (tuple(job) + ('',))[:3]
        lines.append(f'run_one {shlex.quote(folder)} {shlex.quote(base)} {shlex.quote(attempt or "-")}')
    lines += ['exit 0', '']
    return '\n'.join(lines)


def submitted(text):
    match = re.search(r'Submitted batch job (\d+)', text or '')
    return match.group(1) if match else None


def queue_command(job_id):
    """The state of the job: squeue — or, on a server without SLURM, the process started by the helper (nohup,
    azimuth/runtime/runs.py: the number is its pid), while it still runs a script of Azimuth."""
    n = int(job_id)
    return (f'if command -v squeue >/dev/null 2>&1; then squeue -h -j {n} -o "%T|%M|%R" 2>/dev/null; '
            f'elif ps -p {n} -o args= 2>/dev/null | grep -q "\\.sh"; then '
            f'echo "RUNNING|$(ps -p {n} -o etime= | tr -d " ")|nohup"; fi')


def cancel_command(ids):
    """scancel of the numbers — or, without SLURM, the end of the processes started by the helper: the session of
    each (setsid), its group and itself; only a process that runs a script (a pid taken by another program is left)."""
    numbers = [str(int(i)) for i in ([ids] if isinstance(ids, (str, int)) else ids)]
    kill = '; '.join(f'if ps -p {n} -o args= 2>/dev/null | grep -q "\\.sh"; then pkill -TERM -s {n} 2>/dev/null; '
                     f'kill -TERM -- -{n} 2>/dev/null; kill -TERM {n} 2>/dev/null; fi' for n in numbers)
    return f'if command -v scancel >/dev/null 2>&1; then scancel {" ".join(numbers)}; else {kill}; true; fi'


# T10: the states SLURM gives a job that has ended — squeue may still list it for a while (MinJobAge); it
# runs no more, so it is «not in the queue» for the watching (was taken for running until it was forgotten)
ENDED_STATES = ('COMPLETED', 'FAILED', 'CANCELLED', 'TIMEOUT', 'OUT_OF_MEMORY', 'NODE_FAIL', 'PREEMPTED', 'BOOT_FAIL',
                'DEADLINE', 'SPECIAL_EXIT', 'REVOKED')


def queue_state(text):
    """The state of the job from the answer of queue_command; None when it is no longer in the queue (or is
    listed in a state of ENDED_STATES — it runs no more)."""
    for line in (text or '').splitlines():
        state = line.split('|')[0].strip()
        if state:
            return None if state.split()[0].upper() in ENDED_STATES else state
    return None


_PAL = re.compile(r'%pal\b.*?\bend\b', re.I | re.S)
_PAL_LINE = re.compile(r'^(\s*%pal\s+nprocs\s+)\d+(.*)$', re.I | re.M)
_MAXCORE = re.compile(r'^(\s*%maxcore\s+)\d+(.*)$', re.I | re.M)


def with_processes(text, processes, maxcore):
    """The ORCA input with %pal nprocs = processes and %maxcore = maxcore (replaced, or added before the geometry)."""
    out = text
    if _PAL_LINE.search(out):
        out = _PAL_LINE.sub(lambda m: f'{m.group(1)}{processes}{m.group(2)}', out, count=1)
    elif _PAL.search(out):
        out = _PAL.sub(f'%pal nprocs {processes} end', out, count=1)
    else:
        out = _add_before_geometry(out, f'%pal nprocs {processes} end')
    if _MAXCORE.search(out):
        out = _MAXCORE.sub(lambda m: f'{m.group(1)}{maxcore}{m.group(2)}', out, count=1)
    else:
        out = _add_before_geometry(out, f'%maxcore {maxcore}')
    return out


def _add_before_geometry(text, line):
    match = re.search(r'^\s*\*\s*(xyz|xyzfile|int|gzmt)', text, re.I | re.M)
    if match:
        return text[: match.start()] + line + '\n' + text[match.start():]
    return line + '\n' + text
