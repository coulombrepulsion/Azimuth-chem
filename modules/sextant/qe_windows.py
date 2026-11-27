"""Quantum ESPRESSO for Windows: the native build of the MSYS2 project, put into .tools/qe without MSYS2 itself.

§1 PURPOSE
    conda-forge has no Quantum ESPRESSO for Windows. The MSYS2 project builds it natively (the package
    mingw-w64-ucrt-x86_64-quantum-espresso of its repository «ucrt64»: pw.exe, ph.exe, dos.exe … and the libraries they
    need as DLL — OpenBLAS, FFTW, HDF5, the run-time of gfortran). The build is serial with OpenMP threads: no MPI.
    A student needs neither MSYS2 nor administrator rights: the packages are plain archives, and the programs run from
    any folder when their DLLs lie beside them.
§2 ALGORITHM
    1. The list of the repository (MIRROR + «ucrt64.db», a tar of «<name>-<version>/desc» compressed by zstd) is read:
       parse_database -> {name: Package(name, version, filename, sha256, size, depends, provides)}.
    2. closure(packages, PACKAGE): the package and everything it depends on, through «provides» (omp is libgomp,
       fc-libs is libgfortran) and without the version conditions («>=1.2»).
    3. Each archive is downloaded, its SHA-256 compared with that of the list, unpacked, and the files of
       «ucrt64/bin» — the .exe of PROGRAMS and every .dll — are written into <root>/.tools/qe/bin. The rest of the
       packages (headers, static libraries: 0.6 GB) is not kept.
    4. zstd: the module of Python 3.14 (compression.zstd) or the package «zstandard» when there is one; else the
       program zstd — in PATH, in the prefix of the tools, or installed there from conda-forge by the package manager
       of «Установить программы» (unzstd_command).
    5. The stack: the programs of the build reserve 2 MB for the stack of the main thread (the header of the .exe), and
       pw.exe on a crystal of two atoms ends with the code 0xC00000FD — the stack overflowed. widen_stack writes STACK
       into SizeOfStackReserve of the header of every .exe kept: address space reserved, memory taken as used. The
       threads of OpenMP take theirs from OMP_STACKSIZE (qe_run.windows_command).
    6. The check: pw.exe run on an empty input prints «Program PWSCF v.…» (only on Windows: elsewhere the files are
       written and not run).
§4 SPECIFICATION
    MIRROR, REPOSITORY, PACKAGE, PROGRAMS (the names of qe_inputs → the .exe of the build), exe_name('pw.x') ->
    'pw.exe'. parse_desc(text) -> Package; parse_database(tar bytes — not compressed) -> {name: Package};
    closure(packages, name) -> [Package] (ValueError names a dependency the list has not);
    wanted(member name) -> the file name to keep or None; unpack(tar bytes, target) -> [names written];
    STACK; widen_stack(bytes of an .exe, size=STACK) -> bytes (ValueError for a file that is not a 64-bit PE);
    decompress(data, zstd=None) -> bytes (ValueError when nothing here reads zstd);
    install(root, fetch=None, zstd=None, say=print, run=None) -> 0 | 1.
    CP2K of the same repository (CP2K_PACKAGE: cp2k.ssmp.exe — threads of OpenMP, no MPI; about 390 MB to download):
    install_cp2k(root, …) -> 0 | 1 puts it into <root>/.tools/cp2k/bin and its data into cp2k_data(prefix);
    unpack(…, programs, data_from, data_to) keeps a folder of a package whole.
§7 TESTS
    tests/sextant/test_qe_windows.py (a list and archives made in the test; the real mirror — by hand,
    tests/data/qe/README.md).
"""

from __future__ import annotations

import hashlib
import io
import re
import tarfile
from dataclasses import dataclass
from pathlib import Path

MIRROR = 'https://mirror.msys2.org/mingw/ucrt64/'
REPOSITORY = 'ucrt64.db'
PACKAGE = 'mingw-w64-ucrt-x86_64-quantum-espresso'
BIN = 'ucrt64/bin/'
# the programs the tasks of Azimuth run (qe_inputs.STEPS) and their names in this build
PROGRAMS = {'pw.x': 'pw.exe', 'ph.x': 'ph.exe', 'dos.x': 'dos.exe', 'projwfc.x': 'projwfc.exe', 'bands.x': 'bands.exe',
            'q2r.x': 'q2r.exe', 'matdyn.x': 'matdyn.exe', 'dynmat.x': 'dynmat.exe', 'pp.x': 'pp.exe'}
STACK = 512 * 1024 * 1024  # bytes: the stack reserved for the main thread of a program
OMP_STACK = '512M'  # OMP_STACKSIZE of a run: the stack of each thread of OpenMP


def widen_stack(data, size=STACK):
    """The bytes of a 64-bit Windows program with SizeOfStackReserve of its header set to size."""
    import struct

    data = bytearray(data)
    if len(data) < 0x40 or data[:2] != b'MZ':
        raise ValueError('not a Windows program')
    pe = struct.unpack_from('<I', data, 0x3C)[0]
    if len(data) < pe + 24 + 80 or data[pe:pe + 4] != b'PE\0\0' or struct.unpack_from('<H', data, pe + 24)[0] != 0x20B:
        raise ValueError('not a 64-bit Windows program')
    struct.pack_into('<Q', data, pe + 24 + 72, int(size))
    return bytes(data)


def exe_name(tool):
    """The file of a program of Quantum ESPRESSO in the Windows build: 'pw.x' -> 'pw.exe'."""
    return PROGRAMS.get(tool) or (tool[:-2] + '.exe' if tool.endswith('.x') else tool)


@dataclass(frozen=True)
class Package:
    name: str
    version: str
    filename: str
    sha256: str
    size: int
    depends: tuple = ()
    provides: tuple = ()


def _bare(name):
    return re.split(r'[<>=]', name, maxsplit=1)[0].strip()


def parse_desc(text):
    fields = {}
    for found in re.finditer(r'%(\w+)%\n(.*?)(?=\n\n|\n*\Z)', text, re.S):
        fields[found.group(1)] = [line.strip() for line in found.group(2).split('\n') if line.strip()]
    try:
        return Package(fields['NAME'][0], fields['VERSION'][0], fields['FILENAME'][0], fields['SHA256SUM'][0].lower(),
                       int(fields.get('CSIZE', ['0'])[0]), tuple(_bare(d) for d in fields.get('DEPENDS', ())),
                       tuple(_bare(p) for p in fields.get('PROVIDES', ())))
    except (KeyError, IndexError, ValueError) as exc:
        raise ValueError(f'a package of the list has no {exc}') from None


def parse_database(data):
    found = {}
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        for member in archive:
            if member.isfile() and member.name.endswith('/desc'):
                package = parse_desc(archive.extractfile(member).read().decode('utf-8', 'replace'))
                found[package.name] = package
    if not found:
        raise ValueError('the list of the repository is empty')
    return found


def closure(packages, name=PACKAGE):
    provided = {}
    for package in packages.values():
        for other in package.provides:
            provided.setdefault(other, package.name)
    found, queue = [], [name]
    while queue:
        wanted_name = queue.pop(0)
        real = wanted_name if wanted_name in packages else provided.get(wanted_name)
        if real is None:
            raise ValueError(f'the repository has no package {wanted_name}')
        if any(p.name == real for p in found):
            continue
        found.append(packages[real])
        queue += list(packages[real].depends)
    return found


def wanted(member, programs=None):
    """The name to keep of a file of a package: a DLL or a program (of PROGRAMS, or of programs) of ucrt64/bin; else
    None."""
    if not member.startswith(BIN) or '/' in member[len(BIN):]:
        return None
    name = member[len(BIN):]
    low = name.lower()
    return name if low.endswith('.dll') or low in (programs or PROGRAMS.values()) else None


def unpack(data, target, programs=None, data_from=None, data_to=None):
    """The files to keep of a package written into target; data_from — a folder of the package kept whole (with its
    subfolders) in data_to: the basis sets and the potentials of CP2K."""
    target = Path(target)
    target.mkdir(parents=True, exist_ok=True)
    written = []
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        for member in archive:
            if data_from and member.isfile() and member.name.startswith(data_from):
                inner = Path(*member.name[len(data_from):].split('/'))
                if '..' in inner.parts:
                    continue
                place = Path(data_to) / inner
                place.parent.mkdir(parents=True, exist_ok=True)
                place.write_bytes(archive.extractfile(member).read())
                continue
            name = wanted(member.name, programs) if member.isfile() else None
            if name is None:
                continue
            body = archive.extractfile(member).read()
            if name.lower().endswith('.exe'):
                body = widen_stack(body)
            (target / name).write_bytes(body)
            written.append(name)
    return written


def decompress(data, zstd=None):
    """The bytes of a zstd stream: by Python when it can, else by the program zstd (its path)."""
    try:
        from compression import zstd as module  # Python 3.14

        return module.decompress(data)
    except ImportError:
        pass
    try:
        import zstandard

        return zstandard.ZstdDecompressor().decompressobj().decompress(data)
    except ImportError:
        pass
    if zstd is None:
        raise ValueError('nothing here reads zstd archives')
    import os
    import subprocess

    flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0) if os.name == 'nt' else 0
    done = subprocess.run([str(zstd), '-d', '-c'], input=data, capture_output=True, creationflags=flags)
    if done.returncode != 0:
        raise ValueError('zstd: ' + done.stderr.decode('utf-8', 'replace').strip()[:300])
    return done.stdout


def needs_program():
    """True when Python itself cannot read zstd here (then the program zstd is wanted)."""
    for name in ('compression.zstd', 'zstandard'):
        try:
            __import__(name)
            return False
        except ImportError:
            continue
    return True


def find_zstd(root):
    """The program zstd: of the prefix of the tools of Azimuth, else of PATH, else None."""
    import shutil

    from modules.sextant import install_tools

    for folder in install_tools.bin_dirs(root):
        for name in ('zstd.exe', 'zstd'):
            if (folder / name).is_file():
                return folder / name
    found = shutil.which('zstd')
    return Path(found) if found else None


def install_zstd(root, say=print):
    """zstd from conda-forge into the prefix of the tools, by the package manager of «Установить программы»."""
    from modules.sextant import install_tools

    tool = install_tools.manager(root)
    if tool is None:
        tool = install_tools.download_micromamba(root)
    target = install_tools.prefix(root)
    verb = 'install' if (target / 'conda-meta').is_dir() else 'create'
    argv = [str(tool), verb, '-y', '-p', str(target), '--override-channels', '-c', install_tools.CHANNEL, 'zstd']
    say('[tools] zstd: ' + ' '.join(argv))
    code = install_tools.run_manager(argv, install_tools.manager_env(root))
    return find_zstd(root) if code == 0 else None


def _fetch(url, timeout=600, attempts=3):
    """The bytes of an address; a connection that broke is tried again (attempts in all)."""
    import time
    import urllib.request

    from modules.compass.chemistry.pubchem import _urlopen  # the certificates of the system, as the other downloads

    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers={'User-Agent': 'Azimuth'})
            with _urlopen(request, timeout) as response:
                return response.read()
        except OSError:
            if attempt + 1 == attempts:
                raise
            time.sleep(2.0 * (attempt + 1))


def _starts(program, folder):
    """The first line «Program PWSCF v.…» pw.exe prints on an empty input, or ''."""
    import os
    import subprocess

    env = dict(os.environ)
    env['PATH'] = os.pathsep.join([str(folder), env.get('PATH', '')])
    flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0) if os.name == 'nt' else 0
    try:
        said = subprocess.run([str(program)], input='', capture_output=True, text=True, env=env, timeout=120,
                              encoding='utf-8', errors='replace', creationflags=flags)
    except (OSError, subprocess.SubprocessError) as exc:
        return '', str(exc)
    text = said.stdout + said.stderr
    return next((s.strip() for s in text.splitlines() if 'PWSCF' in s and 'v.' in s), ''), ' '.join(text.split())[:300]


def install(root, fetch=None, zstd=None, say=print, run=None):
    """Quantum ESPRESSO of MSYS2 into <root>/.tools/qe/bin; 0 — done. fetch(url) -> bytes; zstd — the program (found
    or installed when Python cannot read zstd); run(program, folder) -> (the line of the version, what was said) —
    None: on Windows the program is started, elsewhere not."""
    import os

    from modules.sextant import install_tools

    fetch = fetch or _fetch
    root = Path(root)
    target = install_tools.qe_prefix(root) / 'bin'
    try:
        if zstd is None and needs_program():
            zstd = find_zstd(root) or install_zstd(root, say)
            if zstd is None:
                say('[tools] ERROR: no program to unpack zstd archives (the package zstd of conda-forge was not installed)')
                return 1
        say(f'[tools] Quantum ESPRESSO (Windows, MSYS2): the list of {MIRROR}')
        packages = closure(parse_database(decompress(fetch(MIRROR + REPOSITORY), zstd)))
        total = sum(p.size for p in packages)
        say(f'[tools] {len(packages)} packages, {total / 1e6:.0f} MB to download')
        count = 0
        for k, package in enumerate(packages, 1):
            say(f'[tools] {k}/{len(packages)} {package.filename} ({package.size / 1e6:.1f} MB)')
            data = fetch(MIRROR + package.filename)
            if hashlib.sha256(data).hexdigest() != package.sha256:
                say(f'[tools] ERROR: {package.filename}: the checksum differs from that of the list — the download is '
                    'damaged; try again')
                return 1
            count += len(unpack(decompress(data, zstd), target))
    except (OSError, ValueError, tarfile.TarError) as exc:
        say(f'[tools] ERROR: Quantum ESPRESSO was not installed: {type(exc).__name__}: {exc}')
        return 1
    pw = target / PROGRAMS['pw.x']
    if not pw.is_file():
        say('[tools] ERROR: pw.exe is not in the package')
        return 1
    say(f'[tools] {count} files in {target}')
    if run is None and os.name == 'nt':
        run = _starts
    if run is not None:
        line, said = run(pw, target)
        if not line:
            say('[tools] ERROR: pw.exe does not start: ' + said)
            return 1
        say('[tools] ' + line)
    from modules.sextant import qe_pseudo  # the SSSP pseudopotentials, once

    if not qe_pseudo.installed(root):
        try:
            qe_pseudo.download(root)
        except (OSError, ValueError) as exc:  # the programs are there: the panel offers the download again
            say(f'[tools] ERROR: the pseudopotentials SSSP were not downloaded ({exc}) — Quantum ESPRESSO itself is '
                'installed; press «Скачать псевдопотенциалы» in the panel of the calculation')
            return 1
    say('[tools] done: Quantum ESPRESSO is in ' + str(install_tools.qe_prefix(root)))
    return 0


# CP2K of the same repository: one program (serial with OpenMP threads — no MPI) and the folder of its data
CP2K_PACKAGE = 'mingw-w64-ucrt-x86_64-cp2k'
CP2K_PROGRAM = 'cp2k.ssmp.exe'
CP2K_DATA = 'ucrt64/share/cp2k/data/'


def cp2k_data(prefix):
    """The folder of the basis sets and the potentials of a CP2K installed here (CP2K_DATA_DIR of a run)."""
    return Path(prefix) / 'share' / 'cp2k' / 'data'


def _cp2k_starts(program, folder):
    """The line «CP2K version …» of «cp2k --version», or ''."""
    import os
    import subprocess

    env = dict(os.environ)
    env['PATH'] = os.pathsep.join([str(folder), env.get('PATH', '')])
    env['OMP_NUM_THREADS'] = '1'
    flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0) if os.name == 'nt' else 0
    try:
        said = subprocess.run([str(program), '--version'], capture_output=True, text=True, env=env, timeout=180,
                              encoding='utf-8', errors='replace', creationflags=flags)
    except (OSError, subprocess.SubprocessError) as exc:
        return '', str(exc)
    text = said.stdout + said.stderr
    return (next((s.strip() for s in text.splitlines() if 'CP2K version' in s), ''),
            f'code {said.returncode}: ' + ' '.join(text.split())[:300])


def install_cp2k(root, fetch=None, zstd=None, say=print, run=None):
    """CP2K of MSYS2 into <root>/.tools/cp2k: bin (cp2k.ssmp.exe and the DLLs) and share/cp2k/data; 0 — done. The
    arguments are those of install."""
    import os

    from modules.sextant import install_tools

    fetch = fetch or _fetch
    root = Path(root)
    prefix = install_tools.cp2k_prefix(root)
    target = prefix / 'bin'
    try:
        if zstd is None and needs_program():
            zstd = find_zstd(root) or install_zstd(root, say)
            if zstd is None:
                say('[tools] ERROR: no program to unpack zstd archives (the package zstd of conda-forge was not installed)')
                return 1
        say(f'[tools] CP2K (Windows, MSYS2): the list of {MIRROR}')
        packages = closure(parse_database(decompress(fetch(MIRROR + REPOSITORY), zstd)), CP2K_PACKAGE)
        total = sum(p.size for p in packages)
        say(f'[tools] {len(packages)} packages, {total / 1e6:.0f} MB to download')
        count = 0
        for k, package in enumerate(packages, 1):
            say(f'[tools] {k}/{len(packages)} {package.filename} ({package.size / 1e6:.1f} MB)')
            data = fetch(MIRROR + package.filename)
            if hashlib.sha256(data).hexdigest() != package.sha256:
                say(f'[tools] ERROR: {package.filename}: the checksum differs from that of the list — the download is '
                    'damaged; try again')
                return 1
            count += len(unpack(decompress(data, zstd), target, (CP2K_PROGRAM,), CP2K_DATA, cp2k_data(prefix)))
    except (OSError, ValueError, tarfile.TarError) as exc:
        say(f'[tools] ERROR: CP2K was not installed: {type(exc).__name__}: {exc}')
        return 1
    program = target / CP2K_PROGRAM
    if not program.is_file():
        say('[tools] ERROR: cp2k.ssmp.exe is not in the package')
        return 1
    if not (cp2k_data(prefix) / 'BASIS_MOLOPT').is_file():
        say('[tools] ERROR: the basis sets of CP2K (BASIS_MOLOPT) are not in the package')
        return 1
    say(f'[tools] {count} files in {target}')
    if run is None and os.name == 'nt':
        run = _cp2k_starts
    if run is not None:
        line, said = run(program, target)
        if not line:
            say('[tools] ERROR: cp2k.ssmp.exe does not start: ' + said)
            return 1
        say('[tools] ' + line)
    say('[tools] done: CP2K is in ' + str(prefix))
    return 0
