"""Install the calculation tools: Open MPI 4.1 (parallel ORCA), xtb, CREST from conda-forge.

§1 PURPOSE
    ORCA runs on several processes through Open MPI (Linux, macOS; MS-MPI on Windows), and its macOS and
    Linux builds are linked against Open MPI 4.1 (libmpi.40): another major version does not load. xtb
    and CREST come as conda-forge packages too. Everything goes into one prefix inside the program folder,
    .tools/calc (like .venv): no administrator rights, no change of the shell profile, removed with the
    folder.
§2 ALGORITHM
    manager(): a conda, mamba or micromamba already on the computer (PATH, CONDA_EXE, the usual folders
    ~/miniconda3, ~/miniforge3, ~/mambaforge, ~/anaconda3, /opt/anaconda3, /opt/miniforge3, the Homebrew casks,
    the prefixes of ~/.conda/environments.txt, .tools/bin/micromamba), else micromamba is downloaded from
    micro.mamba.pm (the address of the mamba documentation; when Python has no root certificates — the
    python.org build on macOS — with /usr/bin/curl, which uses the keychain) and the file bin/micromamba of the
    archive is unpacked to .tools/bin. command():
    `<manager> create|install -y -p .tools/calc --override-channels -c https://conda.anaconda.org/conda-forge
    openmpi=4.1 xtb crest`
    (create when the prefix does not exist yet; micromamba and conda take the same words; «crest=2.12» on
    macOS — CREST 3.0.2 there keeps the energy window of CREGEN at 0, crest-lab/crest#431; an installed 3.0.2 is
    replaced by the same command). main() prints every step (the window shows the end of the log) and checks `mpirun
    --version` for 4.1.
§3 APPLICATIONS
    Sextant: «Установить Open MPI…» in the «Запуск расчёта» card and «Расчёт → Установить программы
    для расчёта…»; runner.find_mpirun / find_program look into .tools/calc/bin first.
§4 SPECIFICATION
    QE_PACKAGES = {'qe': 'qe'} — Quantum ESPRESSO into .tools/qe (qe_prefix; its own Open MPI 5), not on Windows;
    qe_program(root, name='pw.x'); install_qe(tool, root) — checked by «Program PWSCF v.» of pw.x on an empty input.
    NWCHEM_PACKAGES = {'nwchem': 'nwchem'} — NWChem into .tools/nwchem (nwchem_prefix; its own MPI), not on Windows;
    nwchem_program(root); install_nwchem(tool, root) — checked by «Total SCF energy» of a helium atom (NWCHEM_CHECK);
    nwchem_environment(program) -> {OPAL_PREFIX, NWCHEM_BASIS_LIBRARY} of its conda prefix.
    PSI4_PACKAGES = {'psi4': 'psi4'} — Psi4 into .tools/psi4 (psi4_prefix; its own Python), not on Windows, with
    PSI4_EXTRAS (the D3 and D4 corrections it calls through QCEngine);
    psi4_program(root); install_psi4(tool, root) — checked by «Total Energy =» of a helium atom (PSI4_CHECK).
    tool_roots() -> [Path] — this folder, then the «Azimuth…» folders next to it and the folder of the
    installed application that have a .tools (the programs of another version found, not installed again).
    PACKAGES = {'openmpi': 'openmpi=4.1', 'xtb': 'xtb', 'crest': 'crest', 'mopac': 'mopac'}; MACOS_PACKAGES — the same
    with 'crest=2.12'; prefix(root) -> Path; manager(root, home=None, path_env=None) -> Path | None;
    command(manager, root, packages, windows=None, darwin=None) -> list[str];
    unpack_micromamba(archive bytes, target) -> Path; check_micromamba(archive, platform) -> archive | ValueError;
    main(argv) -> exit code (python -m modules.sextant.install_tools
    [--root DIR] [openmpi] [xtb] [crest] [mopac]; MOPAC only when named).
§5 PROCEDURES - below.
§6 NOTES
    micromamba is pinned: MICROMAMBA_VERSION from https://micro.mamba.pm/api/micromamba/<platform>/<version>,
    and the archive must match MICROMAMBA_SHA256 of its platform (refused otherwise). The hashes were taken
    2026-11-24 on the owner's Mac (osx-arm64, osx-64, linux-64, linux-aarch64, win-64; «latest» was 2.10.0 then).
    A new version: download the five archives, put the version and their SHA-256 here.
    ASSUMPTION: the conda-forge packages openmpi 4.1.x, xtb and crest for osx-arm64 and linux-64 as of 2026-10.
    Windows: conda-forge has win-64 builds of xtb (6.7.1), MOPAC (23.2.5) and Microsoft MPI (msmpi 10.1.1 —
    mpiexec.exe and smpd.exe, the MPI of ORCA on Windows) — checked 2026-11-03 on anaconda.org; micromamba for win-64
    (Library/bin/micromamba.exe of the archive). «openmpi» means msmpi there; CREST has no Windows build — refused.
    The programs of a Windows prefix are in Library\\bin (bin_dirs). A program frozen into an .exe (PyInstaller):
    the prefix lives in %LOCALAPPDATA%\\Azimuth (Program Files cannot be written), the script is run by the .exe
    itself (`Azimuth.exe --install-tools …`, gui_launcher).
    On macOS crest, xtb and mopac are made files of their own when they are hard links (own_copy: dyld looks for
    their libraries next to the copy in the package cache otherwise), and `crest --version` must print «Version».
§7 TESTS
    tests/sextant/test_install_tools.py (a fake conda records its arguments and creates mpirun).
§8' ROBUSTNESS
    Every failure prints its reason and returns a non-zero code; nothing outside .tools is changed.
"""

import argparse
import io
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile

# the full address, not the name «conda-forge»: a conda of the computer turns a name into the address of its own
# .condarc (channel_alias, custom_channels — a mirror), and an unreachable mirror stopped the installation
CHANNEL = 'https://conda.anaconda.org/conda-forge'
PACKAGES = {'openmpi': 'openmpi=4.1', 'xtb': 'xtb', 'crest': 'crest', 'mopac': 'mopac'}  # MOPAC (conda-forge, 23.x)
WINDOWS_PACKAGES = {'openmpi': 'msmpi', 'xtb': 'xtb', 'mopac': 'mopac'}  # no CREST for Windows
# CREST 3.0.2 of conda-forge on macOS keeps the energy window of CREGEN at 0 («sorting energy window (EWIN) :
# 0.0000» whatever --ewin says, also «--ewin 20.0»): every search ends with one conformer (crest-lab/crest#431; the
# user's Mac, 4 different structures within 12.6 kcal/mol — 3.0.2 kept 1, 2.12 of conda-forge kept 4)
MACOS_PACKAGES = {**PACKAGES, 'crest': 'crest=2.12'}
# Quantum ESPRESSO (pw.x and the other programs of the qe package of conda-forge, 7.6 for osx-arm64 and the
# Linux platforms, none for Windows — checked 2026-11-11 in current_repodata.json) needs Open MPI 5, ORCA 4.1: it goes
# into a prefix of its own, .tools/qe, so that the two MPI never meet
QE_PACKAGES = {'qe': 'qe'}
CP2K_PACKAGES = {'cp2k': 'cp2k'}  # conda-forge builds for Linux only (none for Apple Silicon and Windows)
# NWChem (conda-forge 7.3.1 for osx-arm64, osx-64, linux-64; none for Windows) brings its own MPI: a prefix of its own,
# .tools/nwchem, as Quantum ESPRESSO, so that it never meets the Open MPI 4.1 of ORCA
NWCHEM_PACKAGES = {'nwchem': 'nwchem'}
# a helium atom in STO-3G: NWChem starts, finds its basis library and ends in a second
# Psi4 (conda-forge 1.11: osx-arm64, osx-64, linux-64) — its own prefix with its own Python, so that its libraries never
# meet those of the shared .tools/calc
PSI4_PACKAGES = {'psi4': 'psi4'}
# the dispersion corrections of Psi4 are programs of their own (QCEngine): without them «b3lyp-d3bj» stopped with
# «Program s-dftd3 is registered with QCEngine, but cannot be found» (Psi4 1.11, 2026-11-22)
PSI4_EXTRAS = ('dftd3-python', 'dftd4-python>=3.5', 'gcp-correction')
PSI4_CHECK = 'molecule {\n  He 0 0 0\n}\nset basis sto-3g\nenergy(\'scf\')\n'
NWCHEM_CHECK = 'start check\ngeometry\n  He 0 0 0\nend\nbasis\n  * library sto-3g\nend\ntask scf\n'
CP2K_NAMES = ('cp2k.psmp', 'cp2k.ssmp', 'cp2k.popt', 'cp2k.sopt', 'cp2k')
CP2K_DIRS = ('/opt/homebrew/bin', '/usr/local/bin', str(Path.home() / '.homebrew' / 'bin'))  # Homebrew: «brew install cp2k»
MICROMAMBA_VERSION = '2.10.0'
MICROMAMBA_URL = 'https://micro.mamba.pm/api/micromamba/{}/' + MICROMAMBA_VERSION
MICROMAMBA_SHA256 = {  # the archives of MICROMAMBA_VERSION (2026-11-24)
    'osx-arm64': 'acef4eaab19ec2174ad5a449e5aad981ca326270db819502ff096a92fc31caa6',
    'osx-64': '17b20c4271d65c030a5c86788f5ca86eb575187209f626edabdb8c6a875c6838',
    'linux-64': '9a97976244929bbae28fb1fae504e74a3e7e6d1932870e3a03321f01b7fbd07b',
    'linux-aarch64': '890bc4906e6ab17f1b393f0da21547f75e000078e573a156316ec925b92a4a4c',
    'win-64': '6283f25f8142606d86e81a43c7103b5d4f1d5c2027e3f9d7326eff23b33930d8',
}
CONDA_HOMES = ('miniconda3', 'miniforge3', 'mambaforge', 'anaconda3', 'opt/miniconda3', 'opt/anaconda3', 'micromamba')
# system-wide places of the Anaconda / Miniconda / Miniforge installers and of Homebrew casks on macOS
SYSTEM_CONDA = ('/opt/anaconda3', '/opt/miniconda3', '/opt/miniforge3', '/opt/mambaforge', '/usr/local/anaconda3',
                '/usr/local/miniconda3', '/opt/homebrew/Caskroom/miniforge/base', '/opt/homebrew/Caskroom/miniconda/base',
                '/usr/local/Caskroom/miniforge/base', '/usr/local/Caskroom/miniconda/base', '/opt/homebrew/anaconda3')


def default_root():
    """The folder whose .tools holds the programs installed: the folder of the program; a frozen program
    (the .exe of the installer, in Program Files) — %LOCALAPPDATA%\\Azimuth, which the user can write; the
    Azimuth.app of the disk image (in /Applications, signed: nothing may be added inside it) —
    ~/Library/Application Support/Azimuth."""
    if getattr(sys, 'frozen', False):
        if sys.platform == 'darwin':
            return Path.home() / 'Library' / 'Application Support' / 'Azimuth'
        base = os.environ.get('LOCALAPPDATA') or str(Path.home() / 'AppData' / 'Local')
        return Path(base) / 'Azimuth'
    return Path(__file__).resolve().parents[2]


def tool_roots():
    """The folders whose .tools may hold the programs — the one of this program first, then the folders «Azimuth…» next
    to it (another version unpacked beside) and the folder of the installed application (~/Library/Application
    Support/Azimuth, %LOCALAPPDATA%\\Azimuth) when they have a .tools."""
    first = default_root()
    roots = [first]
    candidates = []
    try:
        candidates += [p for p in first.parent.iterdir() if p.is_dir() and p.name.lower().startswith('azimuth')]
    except OSError:
        pass
    if sys.platform == 'darwin':
        candidates.append(Path.home() / 'Library' / 'Application Support' / 'Azimuth')
    elif os.name == 'nt':
        candidates.append(Path(os.environ.get('LOCALAPPDATA') or str(Path.home() / 'AppData' / 'Local')) / 'Azimuth')
    for folder in sorted(candidates, key=lambda p: str(p)):
        try:
            if folder.resolve() != first.resolve() and (folder / '.tools').is_dir() and folder not in roots:
                roots.append(folder)
        except OSError:
            continue
    return roots


def bin_dirs(root, windows=None):
    """Where the programs of the prefix are — bin (macOS, Linux); Library\\bin, Scripts and the prefix
    itself on Windows (conda-forge puts the .exe of its packages into Library\\bin)."""
    windows = os.name == 'nt' if windows is None else windows
    target = prefix(root)
    return [target / 'Library' / 'bin', target / 'Scripts', target, target / 'bin'] if windows else [target / 'bin']


def prefix(root):
    return Path(root) / '.tools' / 'calc'


def qe_prefix(root):
    """The prefix of Quantum ESPRESSO (its own Open MPI 5)."""
    return Path(root) / '.tools' / 'qe'


def qe_program(root=None, name='pw.x'):
    """Pw.x (or another program of QE) of the prefix of the program, else in PATH, else None."""
    for base in ([root] if root else tool_roots()):  # of another version next to this one too
        path = qe_prefix(base) / 'bin' / name
        if _executable(path):
            return path
    found = shutil.which(name)
    return Path(found) if found else None


def nwchem_prefix(root):
    """The prefix of NWChem (its own MPI)."""
    return Path(root) / '.tools' / 'nwchem'


def nwchem_program(root=None):
    """nwchem of the prefix of the program (of another version next to this one too), else None."""
    for base in ([root] if root else tool_roots()):
        path = nwchem_prefix(base) / 'bin' / 'nwchem'
        if _executable(path):
            return path
    return None


def psi4_prefix(root):
    """The prefix of Psi4 (its own Python)."""
    return Path(root) / '.tools' / 'psi4'


def psi4_program(root=None):
    """psi4 of the prefix of the program (of another version next to this one too), else None."""
    for base in ([root] if root else tool_roots()):
        path = psi4_prefix(base) / 'bin' / 'psi4'
        if _executable(path):
            return path
    return None


def cp2k_prefix(root):
    """The prefix of CP2K (its own MPICH)."""
    return Path(root) / '.tools' / 'cp2k'


def places(root, packages):
    """The folders the packages go to, in their order and each once: Quantum ESPRESSO, NWChem, Psi4 and CP2K have
    prefixes of their own, the rest share .tools/calc."""
    own = {'qe': qe_prefix, 'nwchem': nwchem_prefix, 'psi4': psi4_prefix, 'cp2k': cp2k_prefix}
    found = []
    for package in packages:
        where = own.get(package, prefix)(root)
        if where not in found:
            found.append(where)
    return found


def cp2k_installable(system=None):
    """conda-forge has CP2K for Linux (x86-64, aarch64) only; a Mac takes it from Homebrew («brew install
    cp2k» run by the installer, cp2k_by_brew), Windows — a server."""
    return (system or platform.system()) in ('Linux', 'Darwin')


def cp2k_by_brew(system=None):
    """CP2K of this system comes from Homebrew (macOS: its bottle for Apple Silicon and Intel, with Open MPI)."""
    return (system or platform.system()) == 'Darwin'


BREW_PATHS = ('/opt/homebrew/bin/brew', '/usr/local/bin/brew', str(Path.home() / '.homebrew' / 'bin' / 'brew'))


def brew_program():
    """Homebrew of this Mac (the usual folders first: a program started from the Finder has a short PATH)."""
    for path in BREW_PATHS:
        if _executable(Path(path)):
            return Path(path)
    found = shutil.which('brew')
    return Path(found) if found else None


def cp2k_program(root=None):
    """CP2K of its prefix, else in PATH, else of Homebrew, else None."""
    for base in ([root] if root else tool_roots()):  # of another version next to this one too
        for name in CP2K_NAMES:
            path = cp2k_prefix(base) / 'bin' / name
            if _executable(path):
                return path
    for name in CP2K_NAMES:
        found = shutil.which(name)
        if found:
            return Path(found)
    for folder in CP2K_DIRS:
        for name in CP2K_NAMES:
            if _executable(Path(folder) / name):
                return Path(folder) / name
    return None


def _executable(path):
    p = Path(path)
    return p.is_file() and os.access(p, os.X_OK)


def _registered(home):
    """Prefixes conda itself lists in ~/.conda/environments.txt (the base one among them)."""
    try:
        lines = (Path(home) / '.conda' / 'environments.txt').read_text(encoding='utf-8', errors='replace').splitlines()
    except OSError:
        return []
    return [Path(line.strip()) for line in lines if line.strip()]


def manager(root, home=None, path_env=None, system=True):
    """A conda-compatible package manager on this computer, or None. A program started from the Finder has
    neither CONDA_EXE nor the PATH of the shell, so the usual folders and ~/.conda/environments.txt are read too."""
    root, home = Path(root), Path(home or Path.home())
    path_env = os.environ.get('PATH', '') if path_env is None else path_env
    candidates = [root / '.tools' / 'bin' / ('micromamba.exe' if os.name == 'nt' else 'micromamba')]
    if os.environ.get('CONDA_EXE'):
        candidates.append(Path(os.environ['CONDA_EXE']))
    names = ('micromamba.exe', 'mamba.exe', 'conda.exe') if os.name == 'nt' else ('micromamba', 'mamba', 'conda')
    for name in names:
        candidates += [Path(d) / name for d in path_env.split(os.pathsep) if d]
    bases = [home / c for c in CONDA_HOMES] + _registered(home) + ([Path(p) for p in SYSTEM_CONDA] if system else [])
    for base in bases:
        if os.name == 'nt':  # Miniconda / Miniforge of Windows
            candidates += [base / 'Scripts' / 'mamba.exe', base / 'Scripts' / 'conda.exe', base / 'condabin' / 'conda.bat']
        else:
            candidates += [base / 'bin' / 'mamba', base / 'bin' / 'conda', base / 'condabin' / 'conda']
    return next((c for c in candidates if _executable(c)), None)


def command(tool, root, packages, windows=None, darwin=None):
    windows = os.name == 'nt' if windows is None else windows
    darwin = platform.system() == 'Darwin' if darwin is None else darwin  # CREST 2.12 on macOS
    if list(packages) == ['cp2k']:  # CP2K into its own prefix
        target = cp2k_prefix(root)
        verb = 'install' if (target / 'conda-meta').is_dir() else 'create'
        return [str(tool), verb, '-y', '-p', str(target), '--override-channels', '-c', CHANNEL, CP2K_PACKAGES['cp2k']]
    if list(packages) == ['nwchem']:  # NWChem into its own prefix
        target = nwchem_prefix(root)
        verb = 'install' if (target / 'conda-meta').is_dir() else 'create'
        return [str(tool), verb, '-y', '-p', str(target), '--override-channels', '-c', CHANNEL,
                NWCHEM_PACKAGES['nwchem']]
    if list(packages) == ['psi4']:  # Psi4 into its own prefix
        target = psi4_prefix(root)
        verb = 'install' if (target / 'conda-meta').is_dir() else 'create'
        return [str(tool), verb, '-y', '-p', str(target), '--override-channels', '-c', CHANNEL,
                PSI4_PACKAGES['psi4'], *PSI4_EXTRAS]
    if list(packages) == ['qe']:  # Quantum ESPRESSO into its own prefix
        target = qe_prefix(root)
        verb = 'install' if (target / 'conda-meta').is_dir() else 'create'
        return [str(tool), verb, '-y', '-p', str(target), '--override-channels', '-c', CHANNEL, QE_PACKAGES['qe']]
    target = prefix(root)
    verb = 'install' if (target / 'conda-meta').is_dir() else 'create'
    specs = [(WINDOWS_PACKAGES if windows else MACOS_PACKAGES if darwin else PACKAGES)[p] for p in packages]
    return [str(tool), verb, '-y', '-p', str(target), '--override-channels', '-c', CHANNEL, *specs]


def own_copy(path):
    """A program the package manager hard-linked from its package cache becomes a file of its own. macOS resolves
    @rpath (@loader_path/../lib) of a hard-linked executable from another of its names — the copy in the cache, where
    lib/ is not: CREST 2.12 first linked into another environment stops with «dyld: Library not loaded:
    @rpath/libomp.dylib … tried: '/opt/anaconda3/pkgs/crest-2.12-hd8c59f4_0/bin/../lib/libomp.dylib'».
    Returns True when the file was copied."""
    path = Path(path)
    try:
        if path.is_symlink() or not path.is_file() or os.stat(path).st_nlink < 2:
            return False
        temporary = path.with_name(path.name + '.azimuth-copy')
        shutil.copy2(path, temporary)
        os.replace(temporary, path)
        return True
    except OSError:
        return False


def platform_name():
    system, machine = platform.system(), platform.machine().lower()
    if system == 'Darwin':
        return 'osx-arm64' if machine in ('arm64', 'aarch64') else 'osx-64'
    if system == 'Linux':
        return 'linux-aarch64' if machine in ('arm64', 'aarch64') else 'linux-64'
    if system == 'Windows':
        return 'win-64'
    return None


def unpack_micromamba(archive, target):
    """bin/micromamba (Library/bin/micromamba.exe of the Windows build) of a .tar.bz2 archive (bytes) written
    to target (executable)."""
    names = ('bin/micromamba', 'Library/bin/micromamba.exe')
    with tarfile.open(fileobj=io.BytesIO(archive), mode='r:bz2') as tar:
        member = next((m for m in tar.getmembers() if m.name.lstrip('./') in names), None)
        if member is None or not member.isfile():
            raise ValueError('the archive has no bin/micromamba')
        data = tar.extractfile(member).read()
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    target.chmod(0o755)
    return target


def check_micromamba(archive, name):
    """The archive (bytes) of micromamba for the platform name, or ValueError when its SHA-256 is not the pinned one."""
    import hashlib

    digest = hashlib.sha256(archive).hexdigest()
    if digest != MICROMAMBA_SHA256.get(name):
        raise ValueError(f'micromamba {MICROMAMBA_VERSION} for {name}: the checksum {digest} is not the expected one '
                         '— the download is refused')
    return archive


def download_micromamba(root):
    import urllib.error
    import urllib.request

    name = platform_name()
    if name is None:
        raise ValueError('no micromamba build for this system')
    url = MICROMAMBA_URL.format(name)
    print(f'[tools] downloading micromamba: {url}', flush=True)
    try:
        with urllib.request.urlopen(url, timeout=120) as response:
            archive = response.read()
    except urllib.error.URLError as exc:
        if 'CERTIFICATE_VERIFY_FAILED' not in str(exc):
            raise
        # the Python of python.org on macOS has no root certificates until «Install Certificates.command»;
        # the system curl checks the certificate with the keychain of macOS (the check stays on)
        print('[tools] Python has no root certificates here — downloading with /usr/bin/curl', flush=True)
        archive = curl(url)
    check_micromamba(archive, name)
    name = 'micromamba.exe' if os.name == 'nt' else 'micromamba'
    return unpack_micromamba(archive, Path(root) / '.tools' / 'bin' / name)


def curl(url, program='/usr/bin/curl'):
    if not _executable(program):
        raise OSError('no /usr/bin/curl')
    done = subprocess.run([program, '-fsSL', '--max-time', '300', url], capture_output=True, timeout=320)
    if done.returncode != 0:
        raise OSError('curl: ' + done.stderr.decode('utf-8', 'replace').strip())
    return done.stdout


def manager_env(root):
    """The environment of the package manager: micromamba keeps its cache in .tools; conda does not ask the channel
    for its notices (the notices of a channel of the mirror in .condarc were asked even with the full address)."""
    env = dict(os.environ)
    env.setdefault('MAMBA_ROOT_PREFIX', str(Path(root) / '.tools' / 'mamba'))
    env['CONDA_NUMBER_CHANNEL_NOTICES'] = '0'
    return env


def run_manager(argv, env):
    """The package manager run with its output copied to this output (the log of the window): with an inherited
    console conda.exe of Windows opened a window of its own and its reason never reached install.log."""
    flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0) if os.name == 'nt' else 0
    try:
        process = subprocess.Popen(argv, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, creationflags=flags)
    except OSError as exc:
        print(f'[tools] ERROR: the package manager does not start: {exc}', flush=True)
        return 1
    for line in iter(process.stdout.readline, b''):
        print(line.decode('utf-8', 'replace').rstrip(), flush=True)
    process.stdout.close()
    return process.wait()


def main(argv=None):
    parser = argparse.ArgumentParser(description='Install Open MPI 4.1, xtb and CREST into .tools/calc')
    parser.add_argument('packages', nargs='*', help='openmpi, xtb, crest (default: all three)')
    parser.add_argument('--root', default=str(default_root()))
    parser.add_argument('--log', default='', help='0.91.57: the log file (the .exe of the installer has no console)')
    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):  # a console in cp1251 (Russian Windows) cannot print «→»: UTF-8, else «?»
        try:
            stream.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, ValueError, OSError):
            pass
    root = Path(args.root)
    windows = os.name == 'nt'
    packages = list(dict.fromkeys(args.packages or (['openmpi', 'xtb'] if windows else ['openmpi', 'xtb', 'crest'])))
    if windows and 'crest' in packages:  # no CREST for Windows on conda-forge
        print('[tools] CREST has no build for Windows — skipped (it runs on macOS and Linux, or on a server).', flush=True)
        packages.remove('crest')
        if not packages:
            return 2
    if windows and 'qe' in packages:  # no Quantum ESPRESSO for Windows on conda-forge
        print('[tools] Quantum ESPRESSO has no build for Windows — skipped (it runs on macOS and Linux, or on a server).',
              flush=True)
        packages.remove('qe')
        if not packages:
            return 2
    if windows and 'nwchem' in packages:  # no NWChem for Windows on conda-forge
        print('[tools] NWChem has no build for Windows — skipped (it runs on macOS and Linux, or on a server).', flush=True)
        packages.remove('nwchem')
        if not packages:
            return 2
    if windows and 'psi4' in packages:  # ASSUMPTION: the win-64 build of conda-forge is not checked here
        print('[tools] Psi4 is installed here on macOS and Linux only — on Windows: a server or its own installer '
              '(psicode.org).', flush=True)
        packages.remove('psi4')
        if not packages:
            return 2
    if 'cp2k' in packages and cp2k_by_brew():  # a Mac — the others from conda-forge, then CP2K of Homebrew
        rest = [p for p in packages if p != 'cp2k']
        code = main(rest + ['--root', str(root)]) if rest else 0
        return install_cp2k_brew() if code == 0 else code
    if 'cp2k' in packages and not cp2k_installable():
        print('[tools] CP2K has no conda-forge build for this system — on a Mac: «brew install cp2k» in the Terminal '
              '(Homebrew); on Windows: a server.', flush=True)
        packages.remove('cp2k')
        if not packages:
            return 2
    unknown = [p for p in packages if p not in PACKAGES and p not in QE_PACKAGES and p not in CP2K_PACKAGES
               and p not in NWCHEM_PACKAGES and p not in PSI4_PACKAGES]
    if unknown:
        print('[tools] ERROR: unknown package: ' + ', '.join(unknown), flush=True)
        return 2
    print(f'[tools] 1/3 package manager ({", ".join(packages)} → {prefix(root)})', flush=True)
    tool = manager(root)
    if tool is None:
        try:
            tool = download_micromamba(root)
        except (OSError, ValueError) as exc:
            print(f'[tools] ERROR: no conda/mamba and micromamba could not be downloaded: {exc}', flush=True)
            return 1
    print(f'[tools] using {tool}', flush=True)
    qe = 'qe' in packages
    cp2k = 'cp2k' in packages
    nwchem = 'nwchem' in packages
    psi4 = 'psi4' in packages
    packages = [p for p in packages if p not in ('qe', 'cp2k', 'nwchem', 'psi4')]
    if not packages:  # Quantum ESPRESSO, NWChem, Psi4, CP2K — each into its own prefix
        return _separate(tool, root, qe, nwchem, cp2k, psi4)
    argv_ = command(tool, root, packages)
    print('[tools] 2/3 ' + ' '.join(argv_), flush=True)
    env = manager_env(root)
    code = run_manager(argv_, env)
    if code != 0:
        print(f'[tools] ERROR: the package manager ended with code {code}', flush=True)
        return code
    print('[tools] 3/3 check', flush=True)
    if windows:  # the programs asked for are there (MS-MPI: mpiexec.exe and its smpd.exe)
        wanted = {'openmpi': ('mpiexec.exe', 'smpd.exe'), 'xtb': ('xtb.exe',), 'mopac': ('mopac.exe',)}
        for package in packages:
            for name in wanted.get(package, ()):
                where = next((d / name for d in bin_dirs(root, True) if (d / name).is_file()), None)
                if where is None:
                    print(f'[tools] ERROR: {name} was not installed', flush=True)
                    return 1
                print(f'[tools] {name}: {where}', flush=True)
        print('[tools] done', flush=True)
        return 0
    if 'openmpi' in packages:
        mpirun = prefix(root) / 'bin' / 'mpirun'
        if not _executable(mpirun):
            print('[tools] ERROR: mpirun was not installed', flush=True)
            return 1
        env['OPAL_PREFIX'] = str(prefix(root))
        try:
            version = subprocess.run([str(mpirun), '--version'], capture_output=True, text=True, env=env, timeout=60,
                                     encoding='utf-8', errors='replace').stdout
        except (OSError, subprocess.SubprocessError) as exc:
            print(f'[tools] ERROR: mpirun --version failed: {exc}', flush=True)
            return 1
        print('[tools] ' + (version.strip().splitlines() or [''])[0], flush=True)
        if '4.1' not in version:
            print('[tools] ERROR: ORCA needs Open MPI 4.1', flush=True)
            return 1
    for name in ('xtb', 'crest', 'mopac'):
        if name in packages and not _executable(prefix(root) / 'bin' / name):
            print(f'[tools] ERROR: {name} was not installed', flush=True)
            return 1
        if name in packages and platform.system() == 'Darwin' and own_copy(prefix(root) / 'bin' / name):
            print(f'[tools] {name}: a copy of its own instead of a hard link to the package cache', flush=True)
    if 'crest' in packages:  # it starts (its libraries load) and says its version
        try:
            said = subprocess.run([str(prefix(root) / 'bin' / 'crest'), '--version'], capture_output=True, text=True,
                                  env=env, timeout=60, encoding='utf-8', errors='replace')
            text = said.stdout + said.stderr
        except (OSError, subprocess.SubprocessError) as exc:
            text = str(exc)
        line = next((s.strip() for s in text.splitlines() if 'Version' in s), '')
        if not line:
            print('[tools] ERROR: crest does not start: ' + ' '.join(text.split())[:300], flush=True)
            return 1
        print('[tools] crest ' + line, flush=True)
    print('[tools] done: the tools are in ' + str(prefix(root)), flush=True)
    return _separate(tool, root, qe, nwchem, cp2k, psi4)


def _separate(tool, root, qe, nwchem, cp2k, psi4=False):
    """The programs of their own prefixes, one after another; the first failure stops."""
    for wanted, install in ((qe, install_qe), (nwchem, install_nwchem), (psi4, install_psi4), (cp2k, install_cp2k)):
        if wanted:
            code = install(tool, root)
            if code != 0:
                return code
    return 0


def install_nwchem(tool, root):
    """NWChem into .tools/nwchem; checked by a helium atom in STO-3G (NWCHEM_CHECK): the program starts, finds its
    basis library and prints «Total SCF energy»."""
    import tempfile

    argv_ = command(tool, root, ['nwchem'])
    print('[tools] NWChem: ' + ' '.join(argv_), flush=True)
    env = manager_env(root)
    code = run_manager(argv_, env)
    if code != 0:
        print(f'[tools] ERROR: the package manager ended with code {code}', flush=True)
        return code
    program = nwchem_prefix(root) / 'bin' / 'nwchem'
    if not _executable(program):
        print('[tools] ERROR: nwchem was not installed', flush=True)
        return 1
    if platform.system() == 'Darwin' and own_copy(program):
        print('[tools] nwchem: a copy of its own instead of a hard link to the package cache', flush=True)
    env.update(nwchem_environment(program))
    with tempfile.TemporaryDirectory(prefix='azimuth-nwchem-') as folder:
        (Path(folder) / 'check.nw').write_text(NWCHEM_CHECK, encoding='ascii')
        try:
            said = subprocess.run([str(program), 'check.nw'], cwd=folder, capture_output=True, text=True, env=env,
                                  timeout=300, encoding='utf-8', errors='replace')
            text = said.stdout + said.stderr
        except (OSError, subprocess.SubprocessError) as exc:
            text = str(exc)
    line = next((s.strip() for s in text.splitlines() if 'Total SCF energy' in s), '')
    if not line:
        print('[tools] ERROR: nwchem does not start or finds no basis library: ' + ' '.join(text.split())[-300:],
              flush=True)
        return 1
    print('[tools] NWChem: ' + line, flush=True)
    print('[tools] done: NWChem is in ' + str(nwchem_prefix(root)), flush=True)
    return 0


def install_psi4(tool, root):
    """Psi4 into .tools/psi4; checked by a helium atom in STO-3G (PSI4_CHECK): the program starts (its Python and
    libraries load) and prints «Total Energy =»."""
    import tempfile

    argv_ = command(tool, root, ['psi4'])
    print('[tools] Psi4: ' + ' '.join(argv_), flush=True)
    env = manager_env(root)
    code = run_manager(argv_, env)
    if code != 0:
        print(f'[tools] ERROR: the package manager ended with code {code}', flush=True)
        return code
    program = psi4_prefix(root) / 'bin' / 'psi4'
    if not _executable(program):
        print('[tools] ERROR: psi4 was not installed', flush=True)
        return 1
    with tempfile.TemporaryDirectory(prefix='azimuth-psi4-') as folder:
        (Path(folder) / 'check.in').write_text(PSI4_CHECK, encoding='ascii')
        env['PSI_SCRATCH'] = folder
        try:
            said = subprocess.run([str(program), 'check.in', 'check.out'], cwd=folder, capture_output=True, text=True,
                                  env=env, timeout=300, encoding='utf-8', errors='replace')
            text = said.stdout + said.stderr
            out = Path(folder) / 'check.out'
            if out.is_file():
                text += out.read_text(encoding='utf-8', errors='replace')
        except (OSError, subprocess.SubprocessError) as exc:
            text = str(exc)
    line = next((s.strip() for s in text.splitlines() if 'Total Energy =' in s), '')
    if not line:
        print('[tools] ERROR: psi4 does not start: ' + ' '.join(text.split())[-300:], flush=True)
        return 1
    print('[tools] Psi4: ' + line, flush=True)
    print('[tools] done: Psi4 is in ' + str(psi4_prefix(root)), flush=True)
    return 0


def nwchem_environment(program):
    """What a NWChem of a conda prefix needs without the activation of its environment: its own MPI (OPAL_PREFIX for an
    Open MPI) and the basis library of the prefix (NWCHEM_BASIS_LIBRARY), when they are there."""
    base = Path(program).resolve().parent.parent
    env = {}
    if (base / 'conda-meta').is_dir():
        env['OPAL_PREFIX'] = str(base)
        for library in (base / 'share' / 'nwchem' / 'libraries', base / 'share' / 'nwchem' / 'data' / 'libraries'):
            if library.is_dir():
                env['NWCHEM_BASIS_LIBRARY'] = str(library) + os.sep
                break
    return env


def install_cp2k(tool, root):
    """CP2K into .tools/cp2k; checked by «cp2k --version» (it starts, its libraries load)."""
    argv_ = command(tool, root, ['cp2k'])
    print('[tools] CP2K: ' + ' '.join(argv_), flush=True)
    env = manager_env(root)
    code = run_manager(argv_, env)
    if code != 0:
        print(f'[tools] ERROR: the package manager ended with code {code}', flush=True)
        return code
    program = next((cp2k_prefix(root) / 'bin' / n for n in CP2K_NAMES if _executable(cp2k_prefix(root) / 'bin' / n)), None)
    return _cp2k_starts(program, env, cp2k_prefix(root))


def install_cp2k_brew(brew=None):
    """«brew install cp2k» (no administrator rights: Homebrew is the user's); checked by «cp2k --version».
    No Homebrew — what to do, code 1 (the installer of Homebrew asks for the password: the user runs it)."""
    brew = brew or brew_program()
    if brew is None:
        print('[tools] ERROR: Homebrew not found. Install it from https://brew.sh (the command there, in the Terminal), '
              'then choose CP2K here again — or run «brew install cp2k» yourself.', flush=True)
        return 1
    print(f'[tools] CP2K: {brew} install cp2k', flush=True)
    env = dict(os.environ)
    env.update(HOMEBREW_NO_ENV_HINTS='1', HOMEBREW_NO_INSTALL_CLEANUP='1')
    env['PATH'] = os.pathsep.join([str(Path(brew).parent), '/usr/bin', '/bin', '/usr/sbin', '/sbin', env.get('PATH', '')])
    code = subprocess.call([str(brew), 'install', 'cp2k'], env=env)
    if code != 0:
        print(f'[tools] ERROR: Homebrew ended with code {code}', flush=True)
        return code
    return _cp2k_starts(cp2k_program(), env, Path(brew).parent)


def _cp2k_starts(program, env, where):
    if program is None:
        print('[tools] ERROR: cp2k was not installed', flush=True)
        return 1
    try:
        said = subprocess.run([str(program), '--version'], capture_output=True, text=True, env=env, timeout=120,
                              encoding='utf-8', errors='replace')
        text = said.stdout + said.stderr
    except (OSError, subprocess.SubprocessError) as exc:
        text = str(exc)
    line = next((s.strip() for s in text.splitlines() if 'CP2K version' in s), '')
    if not line:
        print('[tools] ERROR: cp2k does not start: ' + ' '.join(text.split())[:300], flush=True)
        return 1
    print('[tools] ' + line, flush=True)
    print('[tools] done: CP2K is in ' + str(where), flush=True)
    return 0


def install_qe(tool, root):
    """Quantum ESPRESSO into .tools/qe; checked by running pw.x on an empty input: it starts (its libraries load)
    and prints «Program PWSCF v.…» before it stops for want of an input."""
    argv_ = command(tool, root, ['qe'])
    print('[tools] Quantum ESPRESSO: ' + ' '.join(argv_), flush=True)
    env = manager_env(root)
    code = run_manager(argv_, env)
    if code != 0:
        print(f'[tools] ERROR: the package manager ended with code {code}', flush=True)
        return code
    pw = qe_prefix(root) / 'bin' / 'pw.x'
    if not _executable(pw):
        print('[tools] ERROR: pw.x was not installed', flush=True)
        return 1
    if platform.system() == 'Darwin' and own_copy(pw):
        print('[tools] pw.x: a copy of its own instead of a hard link to the package cache', flush=True)
    env['OPAL_PREFIX'] = str(qe_prefix(root))  # its own Open MPI 5
    try:
        said = subprocess.run([str(pw)], input='', capture_output=True, text=True, env=env, timeout=120,
                              encoding='utf-8', errors='replace')
        text = said.stdout + said.stderr
    except (OSError, subprocess.SubprocessError) as exc:
        text = str(exc)
    line = next((s.strip() for s in text.splitlines() if 'PWSCF' in s and 'v.' in s), '')
    if not line:
        print('[tools] ERROR: pw.x does not start: ' + ' '.join(text.split())[:300], flush=True)
        return 1
    print('[tools] ' + line, flush=True)
    from modules.sextant import qe_pseudo  # the SSSP pseudopotentials, once

    if not qe_pseudo.installed(root):
        try:
            qe_pseudo.download(root)
        except (OSError, ValueError) as exc:
            print(f'[tools] ERROR: the pseudopotentials SSSP were not downloaded: {exc}', flush=True)
            return 1
    print('[tools] done: Quantum ESPRESSO is in ' + str(qe_prefix(root)), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
