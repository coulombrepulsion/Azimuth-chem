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
    5. The check: pw.exe run on an empty input prints «Program PWSCF v.…» (only on Windows: elsewhere the files are
       written and not run).
§4 SPECIFICATION
    MIRROR, REPOSITORY, PACKAGE, PROGRAMS (the names of qe_inputs → the .exe of the build), exe_name('pw.x') ->
    'pw.exe'. parse_desc(text) -> Package; parse_database(tar bytes — not compressed) -> {name: Package};
    closure(packages, name) -> [Package] (ValueError names a dependency the list has not);
    wanted(member name) -> the file name to keep or None; unpack(tar bytes, target) -> [names written];
    decompress(data, zstd=None) -> bytes (ValueError when nothing here reads zstd);
    install(root, fetch=None, zstd=None, say=print, run=None) -> 0 | 1.
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


def wanted(member):
    """The name to keep of a file of a package: a DLL or a program of PROGRAMS of ucrt64/bin; else None."""
    if not member.startswith(BIN) or '/' in member[len(BIN):]:
        return None
    name = member[len(BIN):]
    low = name.lower()
    return name if low.endswith('.dll') or low in PROGRAMS.values() else None


def unpack(data, target):
    target = Path(target)
    target.mkdir(parents=True, exist_ok=True)
    written = []
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        for member in archive:
            name = wanted(member.name) if member.isfile() else None
            if name is None:
                continue
            (target / name).write_bytes(archive.extractfile(member).read())
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
