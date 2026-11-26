"""Run ORCA, Gaussian, Psi4 or xtb from Sextant: find the program, prepare a job folder, start, watch, stop.

§1 THEORY
    A calculation is a separate program that reads input files in a working folder and writes its output
    there. ORCA reads one input file (the name is its only argument) and prints the output to stdout; for
    more than one process it starts its parts through Open MPI's mpirun, which must be found in PATH, and it
    must be called by its full path. Gaussian (g16 or g09) reads input.gjf and writes input.log next to it;
    it needs g16root (the folder above the program folder), GAUSS_EXEDIR and a scratch folder GAUSS_SCRDIR.
    Psi4 reads input.dat and writes the output file named after it (-n: threads). xtb (GFN2-xTB) reads an
    XYZ file and options, prints to stdout and writes xtbopt.xyz, xtbopt.log, g98.out, charges, wbo. The
    input files themselves: modules/sextant/inputs.py. Programs started from the macOS Finder see only the
    system PATH (/usr/bin:/bin:/usr/sbin:/sbin), so Homebrew, conda and the program folders are searched.
§2 ALGORITHM
    find_program: the configured path (when it is a program of that kind), then PATH, then the usual
    install folders (newest-looking name first). A file is ORCA only when an orca_* program lies next to it
    (on Linux /usr/bin/orca is the GNOME screen reader), Gaussian only when l1.exe lies next to it.
    prepare: a new folder <root>/<date>_<time>_<formula>_<program> (suffix -2, -3 … if taken) with the
    input files; the environment adds the program's folder, mpirun's folder and the usual folders to PATH,
    the program's folder to (DY)LD_LIBRARY_PATH (ORCA, Gaussian), OMP_NUM_THREADS = processes, for xtb
    OMP_STACKSIZE = 1G (its documentation asks for a large OpenMP stack), for Gaussian g16root,
    GAUSS_EXEDIR = <folder>/bsd:<folder>, GAUSS_SCRDIR = the job folder, for Psi4 PSI_SCRATCH = the job
    folder. ORCA on several processes: macOS (System Integrity Protection) removes every DYLD_*
    variable when ORCA starts mpirun through /bin/sh, and orca_startup_mpi then cannot load libmpi.40.dylib
    («Library not loaded», signal 6 in Startup); mpi_wrapper() writes a small mpirun into
    <job>/.azimuth-mpi (first in PATH after the ORCA folder) that sets (DY)LD_LIBRARY_PATH again from
    AZIMUTH_(DY)LD_LIBRARY_PATH (not removed) and executes the real mpirun. Job: subprocess.Popen in its own session
    (process group), stdout and stderr into the stdout
    file (ORCA, xtb: that is the output; Gaussian, Psi4: <program>.stdout, the output is their own file);
    poll() is called by a timer of the window; stop() sends SIGTERM to the whole group (ORCA's mpirun and
    its parts too), SIGKILL after 3 s. progress(): optimization cycles and the last energy (ORCA:
    «GEOMETRY OPTIMIZATION CYCLE», «FINAL SINGLE POINT ENERGY»; Gaussian: «Step number», «SCF Done:
    E(…) = E»; Psi4: «@… Final Energy:» lines — every SCF, also those of finite-difference frequencies;
    xtb: «energy:» frames in xtbopt.log, else «TOTAL ENERGY»). finished_normally(): exit code 0 and
    «ORCA TERMINATED NORMALLY» / «Normal termination of Gaussian» without «Error termination» /
    «Psi4 exiting successfully» / xtb «normal termination» or «finished run».
§3 APPLICATIONS
    modules/sextant/workspace.py (the «Запуск расчёта» card, the «Расчёт» menu).
§4 SPECIFICATION
    find_program(kind, configured=None, home=None, path_env=None, system=True) -> Path | None, kind ∈ KINDS;
    system=False leaves out the folders outside home (tests)
    check_program(kind, path) -> Path (ValueError with the reason)
    find_mpirun(orca=None, home=None, path_env=None) -> Path | None
    job_folder(root, molecule, kind, now) -> Path (created)
    mpi_wrapper(folder, mpirun, env) -> env (PATH and AZIMUTH_* changed; scripts mpirun, mpiexec written)
    prepare(kind, program, molecule, calculation, constraints, root, now=None, mpirun=None, neb=None, quick=False,
            text=None) -> JobSpec; text: the input edited by hand
    Job(spec): start(), poll() -> None | int, running, stop(), elapsed(), text(limit), stdout_text(limit)
    progress(kind, text, folder=None) -> (cycles, last_energy | None)
    finished_normally(kind, text, code) -> bool; tail(text, lines) -> str; duration(seconds) -> str
    molden_from_gbw(gbw, configured=None) -> Path of <name>.molden.input (orca_2mkl)
    xtb_arguments, xcontrol, xtb_preview, validate_xtb — from inputs.py (kept here for the callers of 0.36.0).
§5 PROCEDURES - below.
§6 NOTES
    ASSUMPTION: the options follow the manuals of xtb 6, Gaussian 16 (g16root/GAUSS_EXEDIR as set by
    g16.profile) and Psi4 1.7 (psi4 input output -n); ORCA ≥ 5 is assumed. The real programs were not run
    in the tests (not installed there); fake programs print their output.
§7 TESTS
    tests/sextant/test_runner.py; tests/test_gui.py::test_sextant_runs_a_program.
§8' ROBUSTNESS
    Nothing is started when the program, mpirun (for more than one ORCA process) or the input is invalid;
    an output larger than the limit is read only at its end for the progress; stop() on a finished job is a
    no-op.
"""

from dataclasses import dataclass, field
from datetime import datetime
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

from modules.sextant.inputs import KINDS, crest_arguments, input_files, validate_xtb, xcontrol, xtb_arguments, xtb_preview  # noqa: F401
from azimuth.core import TASKS, XTB_ORCA, validate_constraints
from azimuth.i18n import tr

# the files are named after the calculation (core.file_base); here the output and what the program prints, by
# the base name of the input: ORCA <base>.out (its stdout), Gaussian <base>.log (+ <base>.stdout), Psi4 <base>.out
# (+ <base>.stdout), xtb and CREST print their output: <base>.out
OUTPUT = {'orca': '{}.out', 'gaussian': '{}.log', 'psi4': '{}.out', 'xtb': '{}.out', 'crest': '{}.out', 'mopac': '{}.out',
          'gamess': '{}.log', 'nwchem': '{}.out'}  # both print their output: it is their stdout
STDOUT = {'orca': '{}.out', 'gaussian': '{}.stdout', 'psi4': '{}.stdout', 'xtb': '{}.out', 'crest': '{}.out',
          'mopac': '{}.stdout', 'gamess': '{}.log', 'nwchem': '{}.out'}  # MOPAC writes <name>.out itself
# GAMESS is started by its script rungms (ASSUMPTION: «rungms JOB VERNO NCPUS» of the GAMESS distribution,
# JOB without .inp; the script is set up for its own computer); NWChem — the program nwchem
PROGRAM_NAMES = {'orca': ('orca',), 'gaussian': ('g16', 'g09'), 'psi4': ('psi4',), 'xtb': ('xtb',), 'crest': ('crest',),
                 'mopac': ('mopac', 'MOPAC2016.exe'), 'gamess': ('rungms',), 'nwchem': ('nwchem',)}
SYSTEM_BIN = ('/opt/homebrew/bin', '/usr/local/bin', '/opt/local/bin', '/usr/bin', '/bin')
CONDA = ('miniconda3', 'miniforge3', 'mambaforge', 'anaconda3', 'opt/miniconda3', 'opt/anaconda3', 'micromamba')


WINDOWS_PROGRAMS = ('.exe', '.cmd', '.bat', '.com')


def _executable(path, windows=None):
    """A file that starts as a program. On Windows os.access(X_OK) is true of any file there is (a .txt
    passed for xtb) — there a program is a file of the kinds Windows starts (WINDOWS_PROGRAMS)."""
    p = Path(path)
    windows = os.name == 'nt' if windows is None else windows
    if windows:
        return p.is_file() and p.suffix.lower() in WINDOWS_PROGRAMS
    return p.is_file() and os.access(p, os.X_OK)


def _is_orca(path):
    p = Path(path)
    return _executable(p) and any(p.parent.glob('orca_*'))


def _is_gaussian(path):
    p = Path(path)
    return _executable(p) and (p.parent / 'l1.exe').exists()


def _is_kind(kind, path):
    if kind == 'orca':
        return _is_orca(path)
    if kind == 'gaussian':
        return _is_gaussian(path)
    return _executable(path)


def _version_key(path):
    return [int(n) for n in re.findall(r'\d+', str(path))]


def _named(base, prefixes):
    try:
        found = [d for d in Path(base).iterdir() if d.is_dir() and d.name.lower().startswith(prefixes)]
    except OSError:
        return []
    return sorted(found, key=_version_key, reverse=True)


def tools_bin():
    """The programs installed by «Установить программы для расчёта» (install_tools.py)."""
    return tools_bins()[0]


def tools_bins():
    """All the folders of those programs — on Windows conda-forge puts them into Library\\bin."""
    from modules.sextant.install_tools import bin_dirs, tool_roots

    # the .tools of this program first, then those of another version next to it (install_tools.tool_roots)
    return [d for root in tool_roots() for d in bin_dirs(root)]


def _search_dirs(kind, home, system=True):
    home = Path(home)
    dirs = list(tools_bins()) if system else []
    outside = (Path('/Applications'), Path('/opt'), Path('/usr/local')) if system else ()
    if kind == 'orca':
        for base in (outside[:1] + (home / 'Applications', home) + outside[1:]):
            for d in _named(base, ('orca',)):
                dirs += [d, d / 'bin']
    elif kind == 'gaussian':
        for variable in ('g16root', 'g09root'):
            if os.environ.get(variable):
                dirs += [Path(os.environ[variable]) / 'g16', Path(os.environ[variable]) / 'g09']
        for base in (home, home / 'Applications') + outside:
            for d in _named(base, ('g16', 'g09', 'gaussian')):
                dirs += [d, d / 'g16', d / 'g09']
    else:
        if kind == 'nwchem' and system:  # «Установить программы для расчёта» puts it into .tools/nwchem
            from modules.sextant.install_tools import nwchem_prefix, tool_roots

            dirs += [nwchem_prefix(root) / 'bin' for root in tool_roots()]
        if kind == 'psi4' and system:  # «Установить программы для расчёта» puts it into .tools/psi4
            from modules.sextant.install_tools import psi4_prefix, tool_roots

            dirs += [psi4_prefix(root) / 'bin' for root in tool_roots()]
        system_conda = [Path('/opt/homebrew/Caskroom/miniforge/base'), Path('/opt/miniconda3')] if system else []
        # on Windows conda keeps the programs of an environment in Library\bin (xtb.exe of conda-forge),
        # Scripts and the environment itself, not in bin
        inside = (('Library', 'bin'), ('Scripts',), (), ('bin',)) if os.name == 'nt' else (('bin',),)
        for base in [home / c for c in CONDA] + system_conda:
            dirs += [base.joinpath(*parts) for parts in inside]
            try:
                dirs += [e.joinpath(*parts) for e in sorted((base / 'envs').iterdir(), key=str) for parts in inside]
            except OSError:
                pass
        for base in (home, home / 'Applications') + outside[:2]:
            dirs += [d / 'bin' for d in _named(base, (kind,))]
    return dirs + ([Path(d) for d in SYSTEM_BIN] if system else [])


def find_program(kind, configured=None, home=None, path_env=None, system=True):
    """The program of this kind: the configured path, PATH, the usual folders; None if not found."""
    if kind not in KINDS:
        raise ValueError(kind)
    if configured and _is_kind(kind, configured):
        return Path(configured)
    path_env = os.environ.get('PATH', '') if path_env is None else path_env
    names = PROGRAM_NAMES[kind]
    if os.name == 'nt':  # a .cmd or .bat too (rungms.bat of GAMESS, a wrapper script)
        names = tuple(n + ext for ext in ('.exe', '.cmd', '.bat') for n in names if not n.lower().endswith('.exe')) + \
            tuple(n for n in names if n.lower().endswith('.exe'))
    dirs = [Path(d) for d in path_env.split(os.pathsep) if d] + _search_dirs(kind, home or Path.home(), system)
    for d in dirs:
        for name in names:
            if _is_kind(kind, d / name):
                return d / name
    return None


def check_program(kind, path):
    p = Path(path)
    if not p.is_file():
        raise ValueError(tr('Файл программы не найден.'))
    if not _executable(p):
        raise ValueError(tr('Этот файл нельзя запустить как программу.'))
    if kind == 'orca' and not _is_orca(p):
        raise ValueError(tr('Это не ORCA: рядом нет её частей (файлов orca_*). Укажите файл orca в папке ORCA.'))
    if kind == 'gaussian' and not _is_gaussian(p):
        raise ValueError(tr('Это не Gaussian: рядом нет её частей (l1.exe и других). Укажите g16 или g09 в папке Gaussian.'))
    return p


# the scratch files a program leaves when it stops on an error or is stopped (ORCA removes its own .tmp only
# on a normal end): ORCA <base>.tmp, <base>_D0.tmp, <base>.tmp.0…; Gaussian Gau-<pid>.rwf/.int/.d2e/.scr/.inp/.chk
# (GAUSS_SCRDIR is the job folder); Psi4 psi.<pid>.<n>
TEMPORARY = re.compile(r'\.tmp($|\.)|^Gau-\d+\.(rwf|int|d2e|scr|inp|chk)$|^psi\.\d+\.\d+$', re.I)


def clean_temporaries(folder):
    """Removes the scratch files of a finished, failed or stopped job from its folder → their names."""
    removed = []
    try:
        entries = list(Path(folder).iterdir())
    except OSError:
        return removed
    for path in entries:
        if TEMPORARY.search(path.name) and path.is_file():
            try:
                path.unlink()
                removed.append(path.name)
            except OSError:  # Windows: still held by a process that has not died yet
                pass
    return sorted(removed)


MSMPI_PAGE = 'https://learn.microsoft.com/message-passing-interface/microsoft-mpi'  # MS-MPI for ORCA on Windows


def msmpi_dirs(environ=None):
    """Where the installer of Microsoft MPI puts mpiexec.exe (MSMPI_BIN, Program Files) — ORCA on Windows runs
    its parallel parts with it."""
    environ = os.environ if environ is None else environ
    dirs = [Path(environ['MSMPI_BIN'])] if environ.get('MSMPI_BIN') else []
    for root in (environ.get('ProgramFiles', 'C:\\Program Files'), 'C:\\Program Files'):
        dirs.append(Path(root) / 'Microsoft MPI' / 'Bin')
    return dirs


def find_mpirun(orca=None, home=None, path_env=None, windows=None, environ=None):
    windows = os.name == 'nt' if windows is None else windows
    path_env = os.environ.get('PATH', '') if path_env is None else path_env
    dirs = [Path(d) for d in path_env.split(os.pathsep) if d]
    if windows:
        dirs = msmpi_dirs(environ) + dirs
    if orca is not None:
        dirs.insert(0, Path(orca).parent)
    home = Path(home or Path.home())
    at = 1 if orca is not None else 0
    dirs[at:at] = tools_bins()  # .tools/calc of the program folder (Library\bin on Windows)
    dirs += [home / c / 'bin' for c in CONDA] + [Path('/opt/openmpi/bin'), home / 'openmpi' / 'bin']
    dirs += [Path(d) for d in SYSTEM_BIN]
    for d in dirs:
        for name in ('mpiexec.exe', 'mpirun.exe') if windows else ('mpirun',):
            if _executable(d / name):
                return d / name
    return None


def _safe(text):
    return re.sub(r'[^0-9A-Za-z_.-]+', '', text)[:40] or 'molecule'


def default_jobs_root(home=None, windows=None, environ=None):
    """Where the folders of the calculations are made until the user chooses another folder. macOS and Linux:
    «Documents/Azimuth/Расчёты», as before. Windows: ORCA, xtb and the other programs there do not open files on a path
    with letters outside Latin, so the folder is «Documents\\Azimuth\\Calculations», and when the home folder itself
    has such letters (a user name in Cyrillic) — «C:\\Users\\Public\\Documents\\Azimuth\\Calculations», or the
    root of the system drive."""
    windows = os.name == 'nt' if windows is None else windows
    environ = os.environ if environ is None else environ
    home = Path(home or Path.home())
    if not windows:
        return home / 'Documents' / 'Azimuth' / 'Расчёты'
    first = home / 'Documents' / 'Azimuth' / 'Calculations'
    if str(first).isascii():
        return first
    public = environ.get('PUBLIC', '')
    if public and public.isascii():
        return Path(public) / 'Documents' / 'Azimuth' / 'Calculations'
    return Path(environ.get('SystemDrive', 'C:') + '\\') / 'Azimuth' / 'Calculations'


def latin_path(path, windows=None):
    """False when the path would trouble a calculation program on Windows (letters outside ASCII); always
    True elsewhere."""
    windows = os.name == 'nt' if windows is None else windows
    return not windows or str(path).isascii()


def start_orbitals(kind, calculation):
    """The .gbw to start from (MORead of ORCA) as a Path, or None; ValueError when it is gone."""
    if kind != 'orca' or not getattr(calculation, 'guess', ''):
        return None
    path = Path(calculation.guess).expanduser()
    if not path.is_file():
        raise ValueError(tr(f'Файл начальных орбиталей не найден: {path}. Выберите другой или уберите его.'))
    return path


def copy_start_orbitals(path, folder):
    """The copy named core.GUESS_FILE in the job folder (ORCA reads it by %moinp); nothing without a path."""
    if path is None:
        return None
    import shutil

    from azimuth.core import GUESS_FILE

    target = Path(folder) / GUESS_FILE
    shutil.copyfile(path, target)
    return target


def job_folder(root, molecule, kind, now):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    base = f'{now:%Y-%m-%d_%H-%M-%S}_{_safe(molecule.formula)}_{kind}'
    folder, n = root / base, 1
    while folder.exists():
        n += 1
        folder = root / f'{base}-{n}'
    folder.mkdir()
    return folder


@dataclass(frozen=True)
class JobSpec:
    kind: str
    folder: Path
    command: tuple
    output: Path
    env: dict = field(repr=False)
    stdout: Path = None  # None: the output itself


def environment(program, kind, cores, mpirun=None, base=None, folder=None):
    env = dict(os.environ if base is None else base)
    here = Path(program).parent
    dirs = [str(here)] + ([str(Path(mpirun).parent)] if mpirun else [])
    dirs += [d for d in SYSTEM_BIN if d not in dirs]
    old = [d for d in env.get('PATH', '').split(os.pathsep) if d and d not in dirs]
    env['PATH'] = os.pathsep.join(dirs + old)
    library = 'DYLD_LIBRARY_PATH' if sys.platform == 'darwin' else 'LD_LIBRARY_PATH'
    if kind == 'crest':  # CREST calls xtb: the folder of an xtb found next to it or in PATH
        env['OMP_STACKSIZE'] = '1G'
    if kind in ('orca', 'gaussian'):
        env[library] = os.pathsep.join(filter(None, (str(here), env.get(library, ''))))
    if mpirun:  # ORCA loads libmpi from the folder of mpirun; a conda Open MPI needs OPAL_PREFIX
        mpi_root = Path(mpirun).parent.parent
        parts = [p for p in env.get(library, '').split(os.pathsep) if p]
        parts.insert(1 if kind in ('orca', 'gaussian') else 0, str(mpi_root / 'lib'))  # after the program's own
        env[library] = os.pathsep.join(parts)
        if (mpi_root / 'conda-meta').is_dir():
            env['OPAL_PREFIX'] = str(mpi_root)
    env['OMP_NUM_THREADS'] = str(cores)
    if kind == 'xtb':
        env['OMP_STACKSIZE'] = '1G'
        env['OMP_MAX_ACTIVE_LEVELS'] = '1'
    if kind == 'gaussian':
        env['g16root' if Path(program).name.startswith('g16') else 'g09root'] = str(here.parent)
        env['GAUSS_EXEDIR'] = os.pathsep.join((str(here / 'bsd'), str(here)))
        if folder is not None:
            env['GAUSS_SCRDIR'] = str(folder)
    if kind == 'psi4' and folder is not None:
        env['PSI_SCRATCH'] = str(folder)
    if kind == 'nwchem':  # a NWChem of conda-forge: its own MPI and basis library without activating its environment
        from modules.sextant.install_tools import nwchem_environment

        env.update(nwchem_environment(program))
    return env


def xtb_for_orca(orca, configured=None, environ=None):
    """The program xtb ORCA is to call for «! XTB2», or None when ORCA finds it by itself (otool_xtb next to ORCA, or
    XTBEXE already set). ORCA 6.0.1 without either: «otool_xtb not available. Trying xtb instead ... failed! Please set
    the XTBEXE environment variable» (code 52). ValueError when there is no xtb on this computer."""
    environ = os.environ if environ is None else environ
    here = Path(orca).parent
    if environ.get('XTBEXE') or any((here / name).is_file() for name in ('otool_xtb', 'otool_xtb.exe')):
        return None
    if configured is None:
        try:
            from azimuth.settings import open_settings

            configured = open_settings().value('programs/xtb', '') or None
        except Exception:  # noqa: BLE001 — no settings (no Qt): the usual folders
            configured = None
    found = find_program('xtb', configured)
    if found is None:
        raise ValueError(tr('Для GFN2-xTB в ORCA нужна программа xtb, она не найдена: «Расчёт → Установить программы для '
                            'расчёта…» ставит её.'))
    return found


MPI_WRAPPER = '.azimuth-mpi'


def mpi_wrapper(folder, mpirun, env):
    """An mpirun that restores the library path macOS removes on the way through /bin/sh."""
    import shlex

    target = Path(folder) / MPI_WRAPPER
    target.mkdir(exist_ok=True)
    env = dict(env)
    lines = ['#!/bin/sh', '# Azimuth: macOS removes DYLD_* when ORCA calls mpirun through /bin/sh; set them again.']
    for name in ('DYLD_LIBRARY_PATH', 'LD_LIBRARY_PATH'):
        if env.get(name):
            env['AZIMUTH_' + name] = env[name]
            lines.append(f'export {name}="$AZIMUTH_{name}"')
    for tool in ('mpirun', 'mpiexec'):
        real = Path(mpirun).with_name(tool) if tool != 'mpirun' and _executable(Path(mpirun).with_name(tool)) else Path(mpirun)
        path = target / tool
        path.write_text('\n'.join(lines + [f'exec {shlex.quote(str(real))} "$@"']) + '\n', encoding='utf-8')
        path.chmod(0o755)
    parts = [d for d in env.get('PATH', '').split(os.pathsep) if d]
    parts.insert(1 if parts else 0, str(target))
    env['PATH'] = os.pathsep.join(parts)
    return env


def prepare(kind, program, molecule, calculation, constraints, root, now=None, mpirun=None, neb=None, quick=False,
            text=None, crest=None):
    """Check everything, then create the job folder with its input; returns what Job starts. text: the
    input file as edited by hand in Sextant (ORCA, Gaussian, Psi4) — written instead of the generated one."""
    if kind not in KINDS:
        raise ValueError(kind)
    program = check_program(kind, program)
    files = input_files(kind, molecule, calculation, constraints, neb)  # validates
    if text is not None and kind in ('orca', 'gaussian', 'psi4', 'mopac', 'gamess', 'nwchem'):  # MOPAC too
        if not text.strip():
            raise ValueError(tr('Входной файл пуст.'))
        main = next(iter(files))
        # Gaussian ends the molecule with a blank line; every program reads a last line only with its newline
        files[main] = text.rstrip('\n') + ('\n\n' if kind == 'gaussian' else '\n')
    if kind == 'orca' and calculation.cores > 1 and mpirun is None:
        if os.name == 'nt':  # on Windows ORCA works with Microsoft MPI, not Open MPI
            raise ValueError(tr('Для нескольких процессов ORCA на Windows нужен Microsoft MPI (mpiexec.exe), он не найден. '
                                'Поставьте 1 процесс или установите MS-MPI (кнопка «Установить MS-MPI…»; '
                                'нужен файл msmpisetup.exe) и перезапустите программу.'))
        raise ValueError(
            tr('Для нескольких процессов ORCA нужен Open MPI (программа mpirun), он не найден. Поставьте 1 процесс или установите Open MPI.')
        )
    guess = start_orbitals(kind, calculation)  # checked before the folder is made
    xtb = xtb_for_orca(program) if kind == 'orca' and getattr(calculation, 'method', '') == XTB_ORCA else None
    folder = job_folder(root, molecule, kind, now or datetime.now())
    for name, text in files.items():
        (folder / name).write_text(text, encoding='utf-8')
    copy_start_orbitals(guess, folder)
    main = next(iter(files))  # <base>.inp / .gjf / .dat / .xyz
    base = Path(main).stem
    if kind == 'orca':
        command = (str(program.resolve()), main)
    elif kind == 'gaussian':
        command = (str(program), main)
    elif kind == 'psi4':
        command = (str(program), main, OUTPUT['psi4'].format(base), '-n', str(calculation.cores))
    elif kind == 'crest':
        command = (str(program), *crest_arguments(calculation, quick, xyz=main, **(crest or {})))  # ewin, mdlen
    elif kind == 'mopac':  # «mopac name.mop» in the folder of the job
        command = (str(program), main)
    elif kind == 'gamess':  # «rungms name 00 n» — the job name without .inp, version 00, processes
        command = (str(program), base, '00', str(calculation.cores))
    elif kind == 'nwchem':  # one process «nwchem name.nw»; more — through mpirun
        if calculation.cores > 1:  # the mpirun of its own prefix first (NWChem of «Установить программы»)
            own = Path(program).parent / 'mpirun'
            found = (own if _executable(own) else None) or mpirun or find_mpirun(program)
            if found is None:
                raise ValueError(tr('Для нескольких процессов NWChem нужен mpirun (Open MPI), он не найден. Поставьте '
                                    '1 процесс или установите Open MPI.'))
            command = (str(found), '-np', str(calculation.cores), str(program), main)
        else:
            command = (str(program), main)
    else:
        fixed = validate_constraints(constraints, len(molecule.atoms)) if 'Opt' in TASKS[calculation.task] else ()
        command = (str(program), *xtb_arguments(calculation, fixed, xyz=main))
    env = environment(program, kind, calculation.cores, mpirun if kind == 'orca' else None, folder=folder)
    if xtb is not None:  # ORCA starts the program xtb for «! XTB2» by this variable
        env['XTBEXE'] = str(xtb)
    if kind == 'orca' and mpirun is not None and calculation.cores > 1 and os.name != 'nt':
        env = mpi_wrapper(folder, mpirun, env)
    return JobSpec(kind, folder, command, folder / OUTPUT[kind].format(base), env, folder / STDOUT[kind].format(base))


def _read_end(path, limit):
    try:
        with open(path, 'rb') as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(0, size - limit))
            return f.read().decode('utf-8', errors='replace')
    except OSError:
        return ''


def kill_tree(pid):
    """Windows: the process pid and every process it started (taskkill /T /F); False when taskkill could not
    do it (the caller then ends the process itself)."""
    try:
        done = subprocess.run(['taskkill', '/T', '/F', '/PID', str(int(pid))], capture_output=True, timeout=20,
                              creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    except (OSError, subprocess.TimeoutExpired):
        return False
    return done.returncode == 0


class Job:
    """One running program; poll() from a timer, never blocks."""

    def __init__(self, spec):
        self.spec = spec
        self.process = None
        self.code = None
        self.started = None
        self.finished = None
        self.stopped = False
        self._kill_at = None

    def start(self):
        out = open(self.spec.stdout or self.spec.output, 'wb')
        try:
            kwargs = {}
            if os.name == 'nt':
                # and no console window — ORCA, xtb and their parts (mpiexec) run hidden, the output goes to
                # the file as before (azimuth/consoles.py does the same for every child)
                hidden = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
                kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP | hidden
            else:
                kwargs['start_new_session'] = True
            self.process = subprocess.Popen(
                self.spec.command,
                cwd=self.spec.folder,
                env=self.spec.env,
                stdin=subprocess.DEVNULL,
                stdout=out,
                stderr=subprocess.STDOUT,
                **kwargs,
            )
        except OSError as exc:
            raise ValueError(tr('Программа не запустилась: ') + str(exc)) from exc
        finally:
            out.close()
        self.started = time.monotonic()
        return self

    @property
    def running(self):
        return self.process is not None and self.code is None

    def poll(self):
        if self.process is None:
            return None
        if self.code is None:
            code = self.process.poll()
            if code is None:
                if self._kill_at is not None and time.monotonic() >= self._kill_at:
                    self._signal(getattr(signal, 'SIGKILL', signal.SIGTERM))
                    self._kill_at = None
                return None
            self.code = code
            self.finished = time.monotonic()
            clean_temporaries(self.spec.folder)  # after any end, an error and a stop too
        return self.code

    def _signal(self, number):
        try:
            if os.name == 'nt':
                # the program and all it started (orca_scf, orca_scfhess …, mpiexec and its processes; the
                # interpreter behind a launcher). terminate() ended only the program started — its parts went on
                # computing after «Остановить». Windows has no gentler stop for a console program: at once.
                if not kill_tree(self.process.pid):
                    self.process.kill()
            else:
                os.killpg(self.process.pid, number)
        except (ProcessLookupError, PermissionError, OSError):
            pass

    def stop(self):
        if not self.running:
            return
        self.stopped = True
        self._signal(signal.SIGTERM)
        self._kill_at = time.monotonic() + 3.0

    def elapsed(self):
        if self.started is None:
            return 0.0
        return (self.finished or time.monotonic()) - self.started

    def text(self, limit=32_000_000):
        """The output of the program ('' while it does not exist)."""
        return _read_end(self.spec.output, limit)

    def stdout_text(self, limit=1_000_000):
        """What the program printed (for Gaussian and Psi4 separate from the output: their error messages)."""
        return _read_end(self.spec.stdout or self.spec.output, limit)


def progress(kind, text, folder=None):
    """(optimization cycles so far, last energy in hartree or None)."""
    if kind == 'orca':
        cycles = len(re.findall(r'GEOMETRY OPTIMIZATION CYCLE', text))
        energies = re.findall(r'FINAL SINGLE POINT ENERGY\s+(-?\d+\.\d+)', text)
        if not cycles and 'DE(CIS)' in text:
            # after TD-DFT ORCA 6 prints as the FINAL SINGLE POINT ENERGY the total energy of the root followed, «E(tot)»
            # (tests/data/orca601/h2o_tddft.out: −76.0408 of root 1; the ground state −76.3210): for a spectrum the
            # energy of the molecule is that of the SCF. An optimization of an excited state goes on minimizing E(tot)
            # and keeps it.
            energies = re.findall(r'^Total Energy\s+:\s+(-?\d+\.\d+) Eh', text, re.M) or energies
    elif kind == 'gaussian':
        cycles = len(re.findall(r'Step number\s+\d+', text))
        energies = re.findall(r'SCF Done:\s+E\(\S+\)\s+=\s+(-?\d+\.\d+)', text)
    elif kind == 'psi4':
        energies = re.findall(r'@\S+ Final Energy:\s+(-?\d+\.\d+)', text)
        cycles = len(energies)
    elif kind == 'mopac':  # «CYCLE: 3 … HEAT: -57.79960» — a heat of formation, not a hartree energy: None
        return len(re.findall(r'^\s*CYCLE:\s+\d+', text, re.M)), None
    elif kind == 'gamess':  # GAMESS 2017 (tests/data/gamess)
        cycles = len(re.findall(r'BEGINNING GEOMETRY SEARCH POINT NSERCH=', text))
        energies = re.findall(r'FINAL \S+ ENERGY IS\s+(-?\d+\.\d+)', text)
    elif kind == 'nwchem':  # NWChem 7.0 (tests/data/nwchem)
        cycles = len(re.findall(r'^\s+Step\s+\d+\s*$', text, re.M))
        energies = re.findall(r'Total (?:DFT|SCF) energy =\s+(-?\d+\.\d+)', text)
    else:
        log = ''
        if folder is not None:
            try:
                log = (Path(folder) / 'xtbopt.log').read_text(encoding='utf-8', errors='replace')
            except OSError:
                log = ''
        energies = re.findall(r'energy:\s*(-?\d+\.\d+)', log)
        cycles = len(energies)
        if not energies:
            energies = re.findall(r'TOTAL ENERGY\s+(-?\d+\.\d+)', text)
    return cycles, (float(energies[-1]) if energies else None)


# the stages of a calculation shown in its window as they are passed: key -> (text, markers by program).
# A stage is passed when one of its markers first appears in the output (ASSUMPTION: the lines of ORCA 5/6,
# Gaussian 16, Psi4 1.7 and xtb 6 as printed by default).
MILESTONES = (
    # more of the way — the input read and the basis built, the first guess, the gradient, the Hessian
    ('setup', 'Входной файл прочитан, базис построен', {
        'gamess': ('ATOMIC BASIS SET',), 'nwchem': ('Basis "ao basis"',),  # tests/data
        'mopac': ('CARTESIAN COORDINATES',),  # MOPAC 23.2.5
        'orca': ('BASIS SET INFORMATION',), 'gaussian': ('Standard basis:', 'General basis read from cards'),
        'psi4': ('Basis Set: ',), 'xtb': ('Calculation Setup',)}),
    ('guess', 'Начальное приближение готово', {
        'orca': ('INITIAL GUESS', 'Initial guess'), 'gaussian': ('Initial guess',),
        'psi4': ('Generating guess',), 'xtb': ('SCC iterations',)}),
    ('scf', 'Самосогласованное поле сошлось', {
        'gamess': ('DENSITY CONVERGED',), 'nwchem': ('Total DFT energy =', 'Total SCF energy ='),
        'mopac': ('SCF FIELD WAS ACHIEVED',),  # MOPAC 23.2.5
        'orca': ('SCF CONVERGED AFTER',), 'gaussian': ('SCF Done:',),
        'psi4': ('Energy and wave function converged',), 'xtb': ('convergence criteria satisfied after',)}),
    ('opt', 'Геометрия оптимизирована', {
        'gamess': ('EQUILIBRIUM GEOMETRY LOCATED',), 'nwchem': ('Optimization converged',),
        'mopac': ('GEOMETRY OPTIMISED',),  # MOPAC 23.2.5
        'orca': ('THE OPTIMIZATION HAS CONVERGED',), 'gaussian': ('Optimization completed.', 'Stationary point found.'),
        'psi4': ('Optimization is complete!',), 'xtb': ('GEOMETRY OPTIMIZATION CONVERGED',)}),
    ('gradient', 'Градиент посчитан (силы на атомах)', {
        'orca': ('CARTESIAN GRADIENT',), 'gaussian': ('Forces (Hartrees/Bohr)',), 'psi4': ('-Total Gradient:',)}),
    ('hessian', 'Гессиан посчитан', {
        'orca': ('ORCA SCF HESSIAN', 'NUMERICAL HESSIAN'), 'gaussian': ('Force constants in Cartesian coordinates',),
        'psi4': ('Computing Second Derivatives',), 'xtb': ('Numerical Hessian',)}),
    ('neb', 'Путь реакции найден', {'orca': ('THE NEB OPTIMIZATION HAS CONVERGED', 'NEB-CI HAS CONVERGED')}),
    # ORCA 6.0.1 prints it after each direction (tests/data/orca601/irc_hcn)
    ('irc', 'Путь IRC дошёл до минимума', {'orca': ('THE IRC HAS CONVERGED',)}),
    ('freq', 'Частоты колебаний посчитаны', {
        'gamess': ('FREQUENCIES IN CM**-1',), 'nwchem': ('Vibrational analysis',),
        'mopac': ('DESCRIPTION OF VIBRATIONS',),  # MOPAC 23.2.5
        'orca': ('VIBRATIONAL FREQUENCIES',), 'gaussian': ('Harmonic frequencies',),
        'psi4': ('Harmonic Vibrational Analysis',), 'xtb': ('vibrational frequencies',)}),
    ('thermo', 'Термохимия посчитана', {
        'gamess': ('THERMOCHEMISTRY AT T=',),
        'mopac': ('CALCULATED THERMODYNAMIC PROPERTIES',),  # MOPAC 23.2.5
        'orca': ('THERMOCHEMISTRY AT',), 'gaussian': ('- Thermochemistry -',),
        'psi4': ('Thermochemistry Components',), 'xtb': ('THERMODYNAMIC',)}),
    ('excited', 'Возбуждённые состояния найдены', {
        'gamess': ('SUMMARY OF TDDFT RESULTS',), 'nwchem': ('Root   1',),
        'orca': ('TD-DFT/TDA EXCITED STATES', 'TD-DFT EXCITED STATES', 'CIS-EXCITED STATES'),
        'gaussian': ('Excitation energies and oscillator strengths',), 'psi4': ('Excitation Energy',)}),
    ('nmr', 'Экранирование ЯМР посчитано', {
        'orca': ('CHEMICAL SHIELDING SUMMARY',), 'gaussian': ('SCF GIAO Magnetic shielding tensor',)}),
    ('charges', 'Заряды на атомах посчитаны', {
        'orca': ('MULLIKEN ATOMIC CHARGES',), 'gaussian': ('Mulliken charges',), 'psi4': ('Mulliken Charges',)}),
)


# what went wrong — a marker in the output (by program) -> what it is and what it may come from. ASSUMPTION:
# the messages of ORCA 5/6, Gaussian 16, Psi4 1.7, xtb 6 as they print them; the first ones found are shown.
CREST_ZERO_WINDOW = 'sorting energy window (EWIN)   :    0.0000 '  # CREST 3.0.2 on macOS


def crest_window_broken(text):
    """CREGEN of this CREST sorted with an energy window of 0 (crest-lab/crest#431)."""
    return CREST_ZERO_WINDOW in (text or '')


PROBLEMS = (
    # ORCA 6.1.1 (Windows run of 2026-11-02) stops an excited-state optimization with B3LYP at once (code 55):
    # «Third functional derivative of a B88 exchange-containing functional requested ... not available natively ...
    # use the LibXC version». ORCA 6.0.1 ran the same input. With «! LibXC(B3LYP)» ORCA 6.1.1 converged in 7 cycles to
    # E(tot) −114.218020 hartree (ORCA 6.0.1, native B3LYP: −114.218015) — the same functional (LibXC ID 475, VWN5).
    ({'orca': ('Third functional derivative', 'not available natively with ORCA')},
     'ORCA не считает оптимизацию возбуждённого состояния с этим функционалом.',
     'Градиент TD-DFT с B3LYP и другими функционалами на обмене B88 ORCA 6.1 считает только через библиотеку LibXC. '
     'В открытом входном файле замените B3LYP на LibXC(B3LYP) — это тот же B3LYP (с VWN5, как в ORCA), — или выберите PBE0.'),
    # CREST 3.0.2 of conda-forge on macOS keeps the energy window of CREGEN at 0 whatever --ewin says
    # (crest-lab/crest#431; tests/data/crest): one conformer is left after any search. CREST 2.12 sorts right.
    ({'crest': (CREST_ZERO_WINDOW,)},
     'CREST отбросил все конформеры, кроме самого низкого.',
     'Это ошибка CREST 3.0.2 на macOS (crest-lab/crest#431): окно энергий сортировки CREGEN всегда 0, флаг --ewin не '
     'действует. Переустановите CREST: «Расчёт → Установить программы для расчёта…» ставит на Mac CREST 2.12.'),
    # ORCA 6.0.1, NEB-CI of HCN → HNC from the two linear structures (2026-11-22): the initial path is interpolated
    # with IDPP, which cannot take the hydrogen through the carbon — «idpp failed to converge», code 64, in 2 s. With
    # the hydrogen moved 0.12 Å off the axis in both ends the same task runs (barrier 47 kcal/mol)
    ({'orca': ('idpp failed to converge', 'idpp initial path was unable to converge')},
     'ORCA не построил начальный путь реакции (NEB).',
     'Путь между начальной и конечной структурой строится интерполяцией, и она не сошлась: структуры слишком далеки '
     'друг от друга или атом по прямой проходит сквозь другой атом (как H в HCN → HNC, если обе молекулы строго '
     'линейны). Сдвиньте этот атом в обеих структурах в ту сторону, где он пойдёт, или возьмите конечную структуру '
     'ближе к начальной.'),
    # ORCA 6.0.1, «! XTB2» with neither otool_xtb next to ORCA nor XTBEXE: «otool_xtb not available. Trying xtb instead
    # ... failed!», code 52 (tests/data/orca601/xtb_neb_hcn). Sextant sets XTBEXE itself (xtb_for_orca); this is for an
    # input run elsewhere or a server without xtb
    ({'orca': ('Please set the XTBEXE environment variable',)},
     'ORCA не нашла программу xtb для метода GFN2-xTB.',
     'Метод «XTB2» считает программа xtb, а ORCA только управляет расчётом. На этом компьютере поставьте xtb через '
     '«Расчёт → Установить программы для расчёта…»; на сервере xtb должна быть в PATH или задана переменной XTBEXE.'),
    ({'mopac': ('GEOMETRY IN ERROR',)},  # MOPAC 23.2.5: «ATOMS 3 AND 2 ARE SEPARATED BY 0.1487 ANGSTROMS»
     'MOPAC не стал считать: два атома слишком близко друг к другу.',
     'Расстояние между какими-то двумя атомами меньше 0,8 Å (в конце вывода MOPAC названы их номера и расстояние) — '
     'обычно это наложившиеся при построении атомы. Раздвиньте или удалите лишний атом в Компасе; «Выровнять '
     'геометрию» исправляет такие структуры.'),
    # MOPAC 23.2.5, «Частоты и термохимия» (FORCE) of water built from SMILES, not optimized: the gradient norm 16 is
    # over its limit of 10 — no frequencies, and still «JOB ENDED NORMALLY», code 0 (the matrix, 2026-11-23)
    ({'mopac': ('GRADIENT IS TOO LARGE TO ALLOW THE FORCE MATRIX',)},
     'MOPAC не стал считать частоты: геометрия не оптимизирована.',
     'Частоты считаются в минимуме энергии (или в переходном состоянии), а здесь градиент слишком велик — MOPAC сам '
     'не оптимизирует. Выберите задачу «Оптимизация + частоты» или сначала оптимизацию, а частоты — на её '
     'геометрии.'),
    ({'orca': ('SCF NOT CONVERGED', 'The SCF is NOT converged', 'SCF not fully converged'),
      'gaussian': ('Convergence failure -- run terminated',), 'psi4': ('SCFConvergenceError', 'Could not converge SCF'),
      'xtb': ('Self consistent charge iterator did not converge', 'SCC is not converged'),
      'nwchem': ('Calculation failed to converge',)},  # NWChem 7.3.0 («dft energy failed» follows), 2026-11-22
     'Самосогласованное поле (SCF) не сошлось.',
     'Трудная электронная структура (переходные металлы, радикалы, близкие по энергии орбитали) или неудачная '
     'геометрия. Включите «Трудная сходимость» в «Дополнительных настройках», проверьте заряд и мультиплетность, '
     'начните с геометрии получше (Компас → «Выровнять геометрию»).'),
    ({'orca': ('The optimization did not converge', 'OPTIMIZATION DID NOT CONVERGE',
               'The optimization has not yet converged'),  # ORCA 6.0.1 (MaxIter reached, it ends normally)
      'gaussian': ('Number of steps exceeded', 'Optimization stopped'), 'psi4': ('OptimizationConvergenceError',),
      'xtb': ('FAILED TO CONVERGE GEOMETRY OPTIMIZATION',),
      'nwchem': ('Failed to converge in maximum number of steps',)},  # NWChem 7.3.0, driver maxiter reached
     'Оптимизация геометрии не сошлась за отведённые циклы.',
     'Увеличьте «Предел циклов» или начните снова с последней геометрии (шаги — в Компасе, «Взять эту геометрию»); '
     'для мягких молекул помогает точный гессиан в начале.'),
    # ORCA 6.0.1 on an excited-state optimization with TPSSh (the user's run): it stops before the
    # SCF — no excited-state gradients for meta-GGA functionals given as a keyword
    ({'orca': ('Meta-GGA functionals can only be used in combination with the excited-state gradient',)},
     'ORCA не считает градиенты возбуждённых состояний с мета-GGA функционалом.',
     'TPSS, TPSSh, r2SCAN и M06-2X не годятся для «Оптимизации возбуждённого состояния» в ORCA — возьмите CAM-B3LYP, '
     'PBE0 или B3LYP.'),
    ({'orca': ('Not enough memory', 'Please increase MaxCore', 'not enough memory'),
      'gaussian': ('galloc: could not allocate memory', 'Out-of-memory', 'could not allocate memory'),
      'psi4': ('MemoryError', 'not enough memory', 'set_memory(): Requested'),  # the last: less than 250 MiB asked
      'xtb': ('memory allocation failed',),
      'nwchem': ('insufficient resources',)},  # NWChem 7.3.0: «mp2_grad:insufficient resources» (benzene, 100 MB)
     'Не хватило памяти.',
     'Увеличьте «Память / процесс» (ORCA: %maxcore) или уменьшите число процессов; для большого базиса нужна память.'),
    ({'orca': ('UNRECOGNIZED OR DUPLICATED KEYWORD', 'INPUT ERROR', 'Unknown identifier'),
      'gaussian': ('Error termination via Lnk1e in', 'QPErr --- A syntax error'), 'psi4': ('SyntaxError',),
      'xtb': ('Invalid input', 'input error')},
     'Ошибка во входном файле.',
     'Неизвестное ключевое слово или неверная строка — обычно после правки файла руками. «Собрать файл заново по '
     'настройкам» вернёт собранный Секстантом.'),
    ({'orca': ('There are no basis functions', 'BASIS SET NOT AVAILABLE', 'has no basis functions', 'no basis set'),
      'gaussian': ('Atomic number out of range for',), 'psi4': ('BasisSetNotFound',)},
     'Базиса нет для одного из элементов.',
     'Выбранный базис не определён для какого-то атома (например, Попла — для тяжёлых элементов). Возьмите def2-SVP, '
     'def2-TZVP или релятивистский базис.'),
    ({'orca': ('multiplicity', 'Multiplicity'), 'gaussian': ('The combination of multiplicity',),
      'psi4': ('Inconsistent or unspecified chg/mult', 'charge and multiplicity')},
     'Заряд и мультиплетность не подходят к молекуле.',
     'Чётное число электронов — нечётная мультиплетность (1, 3…), нечётное — чётная (2, 4…). Проверьте их в '
     '«Дополнительных настройках → Электронное состояние».'),
    ({'orca': ('mpirun', 'ORTE', 'MPI_ABORT', 'PMIX', 'MPI_Init', 'OPAL ERROR', 'MPI_ERRORS_ARE_FATAL'),
      'gaussian': (), 'psi4': ()},
     'Сбой параллельного запуска (MPI).',
     'ORCA с несколькими процессами запускается через Open MPI, и часть процессов не запустилась (в выводе — «An '
     'error occurred in MPI_Init», «OPAL ERROR»). Чаще всего помогает меньше процессов (на сервере — не больше 16) '
     'или другая версия Open MPI в строках окружения сервера; на одном процессе MPI не нужен.'),
    ({'orca': ('No space left on device',), 'gaussian': ('Erroneous write', 'No space left on device'),
      'psi4': ('No space left on device',), 'xtb': ('No space left on device',)},
     'Закончилось место на диске.',
     'Временные файлы расчёта заняли диск: освободите место в папке расчётов или выберите другую папку.'),
)


KILLED = 'Программу остановила система.'  # the key of the problem told by the exit code alone


def diagnose(kind, text, code=None):
    """[(what, why)] — the problems recognised in the output (at most two), or the code when nothing is."""
    return [(tr(what), tr(why)) for what, why in problem_keys(kind, text, code)]


def problem_keys(kind, text, code=None):
    """As diagnose, with the texts not translated — what is the key of the problem (its text in PROBLEMS, or
    KILLED): the doctor of a calculation (modules/sextant/doctor.py) knows a remedy by it."""
    def tr(value):  # the keys, not their translations (diagnose translates)
        return value

    found = []
    tail = text[-400_000:] if text else ''
    for markers, what, why in PROBLEMS:
        if kind == 'orca' and what.startswith('Заряд'):
            # «multiplicity» is printed in every ORCA output: only a line that says it is wrong (before, any
            # «Error» elsewhere in the tail, as in an unconverged optimization of ORCA 6.0.1, made it a false alarm)
            if re.search(r'(?im)^.*(error|impossible).*multiplicity|^.*multiplicity.*(impossible|error)', tail):
                found.append((tr(what), tr(why)))
            if len(found) == 2:
                break
            continue
        if kind == 'orca' and what.startswith('Оптимизация геометрии'):
            # ORCA 6 prints «The optimization has not yet converged» after every cycle but the last, so since
            # 0.89.20 every converged optimization was said to be unconverged; now only without HURRAY after that line
            last = max((tail.rfind(m) for m in markers['orca']), default=-1)
            done = max(tail.rfind('THE OPTIMIZATION HAS CONVERGED'), tail.rfind('HURRAY'))
            # the line of every unfinished cycle says nothing when
            # the run broke in the middle (MPI, memory…) — the cycles ran out only when ORCA said so or ended normally
            said = any(m in tail for m in ('The optimization did not converge', 'OPTIMIZATION DID NOT CONVERGE'))
            if said or (last >= 0 and done < last and 'ORCA TERMINATED NORMALLY' in tail):
                found.append((tr(what), tr(why)))
            if len(found) == 2:
                break
            continue
        if kind == 'orca' and what.startswith('Сбой параллельного') and found:
            # a parallel ORCA that stops for any reason ends with «mpirun detected that one or more processes exited»
            # and «Calling Command: mpirun …»: after an SCF that did not converge the output was also said to have an
            # MPI failure, with «Повторить на одном процессе» (ORCA 6.0.1, 2026-11-22). MPI is the problem only when
            # nothing else is
            continue
        if any(m in tail for m in markers.get(kind, ())):
            found.append((tr(what), tr(why)))
        if len(found) == 2:
            break
    if not found and code is not None and (code in (137, 9) or (code < 0 and code != -15)):
        found.append((KILLED,
                      tr('Чаще всего — нехватка памяти (процесс убит) или завершение сеанса; уменьшите память или процессы.')))
    return found


def milestones(kind, text):
    """The stages passed so far, in the order they appear in the output: [(key, text)]."""
    found = []
    for key, name, markers in MILESTONES:
        places = [text.find(m) for m in markers.get(kind, ())]
        places = [p for p in places if p >= 0]
        if places:
            found.append((min(places), key, name))
    return [(key, name) for _, key, name in sorted(found)]


class OutputProgress:
    """The progress of a running calculation read as its output grows — only the lines added since the last
    look (the window read the last 4 MB of the output every second; a long ORCA optimization or a frequency run
    is tens of MB, and the cycles were counted only in those 4 MB). The cycles, the last energy and the stages
    (progress, milestones) are summed over whole lines; a line still being written waits for its end. An output
    that became shorter (written again) is read again from its start."""

    BLOCK = 8_000_000  # the most read in one look

    def __init__(self, spec):
        self.spec = spec
        self.reset()

    def reset(self):
        self.offset, self.cycles, self.energy, self.stages, self.seen = 0, 0, None, [], False
        self._identity = None

    def update(self):
        """(cycles, energy, stages [(key, text)]) after reading what was added."""
        path = self.spec.output
        try:
            stat = os.stat(path)
        except OSError:
            return self.cycles, self.energy, self.stages
        if stat.st_size < self.offset or (self._identity is not None and stat.st_ino != self._identity):
            self.reset()
        self._identity = stat.st_ino
        if stat.st_size > self.offset:
            try:
                with open(path, 'rb') as f:
                    f.seek(self.offset)
                    data = f.read(self.BLOCK)
            except OSError:
                data = b''
            end = data.rfind(b'\n') + 1  # whole lines only (a UTF-8 character never contains a newline byte)
            if end == 0 and len(data) >= self.BLOCK:
                end = len(data)  # one line longer than a block
            if end:
                self.offset += end
                self.seen = True
                self._add(data[:end].decode('utf-8', errors='replace'))
        if self.spec.kind not in _CHUNKED:  # xtb: the cycles and the energies are in its own log
            cycles, energy = progress(self.spec.kind, '', self.spec.folder)
            if cycles:
                self.cycles, self.energy = cycles, energy
        return self.cycles, self.energy, self.stages

    def _add(self, text):
        cycles, energy = progress(self.spec.kind, text) if self.spec.kind in _CHUNKED else (0, progress(
            self.spec.kind, text)[1])
        self.cycles += cycles
        if energy is not None:
            self.energy = energy
        known = {key for key, _ in self.stages}
        self.stages += [(key, name) for key, name in milestones(self.spec.kind, text) if key not in known]


_CHUNKED = ('orca', 'gaussian', 'psi4', 'mopac', 'gamess', 'nwchem')  # their cycles and energies are counted in the output itself


def path_file(spec):
    """The minimum-energy path ORCA writes after a NEB run, or None. ASSUMPTION: the name
    <input>_MEP_trj.xyz of ORCA 5/6."""
    candidate = spec.folder / (spec.output.stem + '_MEP_trj.xyz')  # named after the calculation
    return candidate if candidate.is_file() else None


def finished_normally(kind, text, code):
    if code != 0:
        return False
    if kind == 'orca':
        return 'ORCA TERMINATED NORMALLY' in text
    if kind == 'gaussian':
        return 'Normal termination of Gaussian' in text and 'Error termination' not in text
    if kind == 'psi4':
        return 'Psi4 exiting successfully' in text
    if kind == 'crest':
        return 'CREST terminated normally' in text
    if kind == 'mopac':  # MOPAC 23.2.5 (tests/data/mopac)
        # two atoms too close: MOPAC computes nothing and still ends with «JOB ENDED NORMALLY», code 0 — the
        # calculation was shown as done, without an energy (water with H···H 0.15 Å, 2026-11-22)
        return 'JOB ENDED NORMALLY' in text and 'GEOMETRY IN ERROR' not in text and 'GRADIENT IS TOO LARGE TO ALLOW THE FORCE MATRIX' not in text
    if kind == 'gamess':  # the marks of the reader (modules/spectrum/readers/gamess.py)
        return bool(re.search(r'EXECUTION OF (?:GAMESS|FIREFLY) TERMINATED NORMALLY', text))
    if kind == 'nwchem':  # modules/spectrum/readers/nwchem.py
        return bool(re.search(r'^\s*Total times\s+cpu:', text, re.M))
    if kind == 'qe':  # every run of pw.x and dos.x ends «JOB DONE.»; an error is a block of «%»
        return 'JOB DONE.' in text and '%%%%%%%%%%' not in text
    if kind == 'cp2k':
        return 'PROGRAM ENDED AT' in text and '[ABORT]' not in text
    return 'normal termination' in text or 'finished run' in text


def tail(text, lines=12):
    return '\n'.join(text.rstrip('\n').splitlines()[-lines:])


def duration(seconds):
    seconds = int(round(seconds))
    s, m, h = tr('с'), tr('мин'), tr('ч')  # units, not patterns: «{} с» would also match «2 мин 05 с»
    if seconds < 60:
        return f'{seconds} {s}'
    minutes, seconds = divmod(seconds, 60)
    if minutes < 60:
        return f'{minutes} {m} {seconds:02d} {s}'
    hours, minutes = divmod(minutes, 60)
    return f'{hours} {h} {minutes:02d} {m}'


def molden_from_gbw(gbw, configured=None, timeout=120):
    """The orbitals of an ORCA result as a Molden file: ORCA keeps them in <name>.gbw, and its own tool
    orca_2mkl (next to the orca program) writes <name>.molden.input next to it — what Spectrum and Compass read.
    An existing Molden file newer than the .gbw is used as it is. ValueError with a message otherwise."""
    gbw = Path(gbw)
    if not gbw.is_file():
        raise ValueError(tr('Нет файла орбиталей ORCA: ') + gbw.name)
    target = gbw.with_name(gbw.stem + '.molden.input')
    if target.is_file() and target.stat().st_mtime >= gbw.stat().st_mtime:
        return target
    orca = find_program('orca', configured)
    if orca is None:
        raise ValueError(tr('Орбитали ORCA лежат в файле .gbw; прочитать его может программа orca_2mkl из ORCA. ORCA не найдена — укажите её в Секстанте («Указать…»).'))
    tool = Path(orca).with_name('orca_2mkl' + ('.exe' if os.name == 'nt' else ''))
    if not tool.is_file():
        raise ValueError(tr('Рядом с ORCA нет программы orca_2mkl: ') + str(tool.parent))
    try:
        subprocess.run(
            [str(tool), gbw.stem, '-molden'], cwd=str(gbw.parent), env=environment(orca, 'orca', 1),
            capture_output=True, timeout=timeout, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError(tr('orca_2mkl не сработала: ') + str(exc)) from exc
    if not target.is_file():
        raise ValueError(tr('orca_2mkl не записала файл Molden: ') + target.name)
    return target
