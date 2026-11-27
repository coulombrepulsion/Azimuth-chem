"""How a job of Quantum ESPRESSO is started on this computer: the command, its script and its environment.

§1 PURPOSE
    One place for the two callers — the panel of the crystal calculation (modules/compass/actions/qe_run.py) and a
    calculation without the window (azimuth/headless_crystal.py). No Qt here.
§2 RULES
    POSIX: the programs of the prefix of «Установить программы» (.tools/qe: its bin first in PATH, OPAL_PREFIX — the
    Open MPI 5 of the package, apart from the 4.1 of ORCA), one thread per process; the processes asked for go to
    mpirun of the prefix when it is there. Several steps (bands, the density of states, a series): run.sh — each
    step only after the one before ended well; a program of qe_inputs.OPTIONAL writes its own output, and its error
    is not that of the job.
    Windows: the build of MSYS2 (modules/sextant/qe_windows.py) has no MPI — the processes asked for become threads
    of OpenMP, each with a stack of qe_windows.OMP_STACK. Nothing in the inputs or in the script names a folder: the
    programs are found by PATH (their folder first — their DLLs lie there too), the pseudopotentials are in ./pseudo
    of the job folder (pseudo_files). A path with Russian letters — the name of the user, the folder of the program —
    would otherwise pass through the code page of cmd.exe and through the Fortran run-time, which reads the input as
    bytes. run.bat is written with the line ends of cmd.exe.
§4 SPECIFICATION
    POSIX_SCRIPT, WINDOWS_SCRIPT; posix_command(steps, program, processes, prefix=None, environ=None) and
    windows_command(steps, program, processes, environ=None) -> (command, the text of the script or '', the changes
    of the environment); command(steps, program, processes, prefix=None, windows=None) -> (command, {file name:
    bytes}, changes); pseudo_files(steps) -> the names of the pseudopotential files of the first input;
    beside(text) -> the input with pseudo_dir = './pseudo'.
§7 TESTS tests/sextant/test_qe_local.py, tests/sextant/test_qe_windows.py.
"""

import os
import re
from pathlib import Path

POSIX_SCRIPT, WINDOWS_SCRIPT = 'run.sh', 'run.bat'


def posix_command(steps, program, processes, prefix=None, environ=None):
    import shlex

    from modules.sextant import qe_inputs

    environ = os.environ if environ is None else environ
    changes = {'OMP_NUM_THREADS': '1'}
    parallel = []
    if prefix is not None and (Path(prefix) / 'bin').is_dir():
        changes['PATH'] = os.pathsep.join([str(Path(prefix) / 'bin'), environ.get('PATH', '')])
        changes['OPAL_PREFIX'] = str(prefix)
        mpirun = Path(prefix) / 'bin' / 'mpirun'
        if int(processes) > 1 and mpirun.is_file():
            parallel = [str(mpirun), '-np', str(int(processes))]
    if len(steps) == 1:
        return [*parallel, str(program), '-in', steps[0][0]], '', changes
    lines = ['#!/bin/sh', 'set -e']
    for name, tool, _ in steps:
        exe = Path(program).with_name(tool) if tool != 'pw.x' else Path(program)
        line = ' '.join(shlex.quote(w) for w in [*(parallel if tool in qe_inputs.PARALLEL else []), str(exe), '-in', name])
        if tool in qe_inputs.OPTIONAL:
            line += f' > {qe_inputs.OPTIONAL[tool]} 2>&1 || true'
        lines.append(line)
    return ['/bin/sh', POSIX_SCRIPT], '\n'.join(lines) + '\n', changes


def windows_command(steps, program, processes, environ=None):
    from modules.sextant import qe_inputs, qe_windows

    environ = os.environ if environ is None else environ
    folder = str(Path(program).parent)
    changes = {'PATH': os.pathsep.join([folder, environ.get('PATH', '')]), 'OMP_NUM_THREADS': str(max(1, int(processes))),
               'OMP_STACKSIZE': qe_windows.OMP_STACK}
    if len(steps) == 1:
        return [str(program), '-in', steps[0][0]], '', changes
    lines = ['@echo off']
    for name, tool, _ in steps:
        line = f'{qe_windows.exe_name(tool)} -in {name}'
        if tool in qe_inputs.OPTIONAL:
            lines.append(f'{line} > {qe_inputs.OPTIONAL[tool]} 2>&1')
        else:
            lines.append(f'{line} || exit /b 1')
    return ['cmd', '/d', '/c', WINDOWS_SCRIPT], '\n'.join(lines) + '\n', changes


def command(steps, program, processes, prefix=None, windows=None):
    """(command, {the name of the script: its bytes}, the changes of the environment) of a job on this computer."""
    windows = os.name == 'nt' if windows is None else windows
    if windows:
        argv, script, changes = windows_command(steps, program, processes)
        return argv, ({WINDOWS_SCRIPT: script.replace('\n', '\r\n').encode('ascii')} if script else {}), changes
    argv, script, changes = posix_command(steps, program, processes, prefix)
    return argv, ({POSIX_SCRIPT: script.encode('utf-8')} if script else {}), changes


def pseudo_files(steps):
    """The files of the pseudopotentials the first input names: «Si 28.0850 Si.upf» of ATOMIC_SPECIES."""
    species = steps[0][2].split('ATOMIC_SPECIES')[1].split('CELL_PARAMETERS')[0].strip().splitlines()
    return sorted({line.split()[2] for line in species})


def beside(text):
    """The input with the pseudopotentials named by the folder ./pseudo of the job (Windows, a server)."""
    return re.sub(r"pseudo_dir\s*=\s*'[^']*'", "pseudo_dir = './pseudo'", text)
