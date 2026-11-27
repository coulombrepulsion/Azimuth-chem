"""Quantum ESPRESSO for Windows from the repository of MSYS2 (modules/sextant/qe_windows.py) and its run
(modules/compass/actions/qe_run.windows_command).

Oracles: a repository made here — a list of four packages in the format of pacman («%NAME%» blocks; the real one read
on 2026-11-26 gave the fields used) and their archives, each with files in and out of ucrt64/bin; the SHA-256 of each
archive computed here by hashlib. zstd is replaced by an identity: what unpacks zstd is of the system, not of Azimuth.
"""

import hashlib
import io
import tarfile

import pytest

from modules.sextant import install_tools, qe_windows as qw


def archive(files):
    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode='w') as tar:
        for name, content in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))
    return data.getvalue()


def desc(name, version, depends=(), provides=(), content=b''):
    text = (f'%FILENAME%\n{name}-{version}-any.pkg.tar.zst\n\n%NAME%\n{name}\n\n%VERSION%\n{version}\n\n'
            f'%CSIZE%\n{len(content)}\n\n%SHA256SUM%\n{hashlib.sha256(content).hexdigest()}\n\n')
    if depends:
        text += '%DEPENDS%\n' + '\n'.join(depends) + '\n\n'
    if provides:
        text += '%PROVIDES%\n' + '\n'.join(provides) + '\n\n'
    return text


def program(tag, stack=2 * 1024 * 1024):
    """The least a 64-bit Windows program has for its header to be read: MZ, the place of «PE», the optional header
    of PE32+ with the stack reserved, then the tag."""
    import struct

    data = bytearray(0x40 + 24 + 112)
    data[:2] = b'MZ'
    struct.pack_into('<I', data, 0x3C, 0x40)
    data[0x40:0x44] = b'PE\0\0'
    struct.pack_into('<H', data, 0x40 + 24, 0x20B)
    struct.pack_into('<Q', data, 0x40 + 24 + 72, stack)
    return bytes(data) + tag


def stack_of(data):
    import struct

    return struct.unpack_from('<Q', data, struct.unpack_from('<I', data, 0x3C)[0] + 24 + 72)[0]


QE = archive({'ucrt64/bin/pw.exe': program(b'pw'), 'ucrt64/bin/ph.exe': program(b'ph'), 'ucrt64/bin/epw.exe': b'MZ epw',
              'ucrt64/bin/epw_pp.py': b'#', 'ucrt64/include/qe/kinds.mod': b'm', 'ucrt64/lib/libqe.a': b'a' * 100,
              'ucrt64/bin/sub/inner.dll': b'no'})
BLAS = archive({'ucrt64/bin/libopenblas.dll': b'MZ blas', 'ucrt64/lib/libopenblas.a': b'a'})
GOMP = archive({'ucrt64/bin/libgomp-1.dll': b'MZ gomp'})
OTHER = archive({'ucrt64/bin/unrelated.dll': b'MZ'})
PREFIX = 'mingw-w64-ucrt-x86_64-'
FILES = {PREFIX + 'quantum-espresso-7.6-1-any.pkg.tar.zst': QE, PREFIX + 'openblas-0.3.34-1-any.pkg.tar.zst': BLAS,
         PREFIX + 'libgomp-16.2.0-7-any.pkg.tar.zst': GOMP, PREFIX + 'gimp-3.0-1-any.pkg.tar.zst': OTHER}


def database(broken=False):
    return archive({
        'mingw-w64-ucrt-x86_64-quantum-espresso-7.6-1/desc': desc(
            PREFIX + 'quantum-espresso', '7.6-1', (PREFIX + 'openblas>=0.3', PREFIX + 'omp'), content=QE).encode(),
        'mingw-w64-ucrt-x86_64-openblas-0.3.34-1/desc': desc(
            PREFIX + 'openblas', '0.3.34-1', (PREFIX + 'omp',), content=b'other' if broken else BLAS).encode(),
        'mingw-w64-ucrt-x86_64-libgomp-16.2.0-7/desc': desc(
            PREFIX + 'libgomp', '16.2.0-7', provides=(PREFIX + 'omp=16',), content=GOMP).encode(),
        'mingw-w64-ucrt-x86_64-gimp-3.0-1/desc': desc(PREFIX + 'gimp', '3.0-1', content=OTHER).encode(),
    })


def test_the_list_of_the_repository_and_what_the_package_needs():
    packages = qw.parse_database(database())
    assert set(packages) == {PREFIX + n for n in ('quantum-espresso', 'openblas', 'libgomp', 'gimp')}
    qe = packages[qw.PACKAGE]
    assert qe.version == '7.6-1' and qe.filename == PREFIX + 'quantum-espresso-7.6-1-any.pkg.tar.zst'
    assert qe.depends == (PREFIX + 'openblas', PREFIX + 'omp') and qe.sha256 == hashlib.sha256(QE).hexdigest()
    # the dependencies through «provides» (omp is libgomp), each once, without what nothing asks for
    assert [p.name for p in qw.closure(packages)] == [PREFIX + n for n in ('quantum-espresso', 'openblas', 'libgomp')]
    del packages[PREFIX + 'libgomp']
    with pytest.raises(ValueError, match='omp'):
        qw.closure(packages)
    with pytest.raises(ValueError):
        qw.parse_database(archive({'readme': b'x'}))
    with pytest.raises(ValueError, match='SHA256SUM'):
        qw.parse_desc('%NAME%\nx\n\n%VERSION%\n1\n\n%FILENAME%\nx.pkg\n')


def test_what_is_kept_of_a_package(tmp_path):
    assert qw.wanted('ucrt64/bin/pw.exe') == 'pw.exe' and qw.wanted('ucrt64/bin/libfftw3-3.dll') == 'libfftw3-3.dll'
    assert qw.wanted('ucrt64/bin/epw.exe') is None and qw.wanted('ucrt64/lib/libqe.a') is None
    assert qw.wanted('ucrt64/bin/sub/inner.dll') is None and qw.wanted('usr/bin/pw.exe') is None
    assert sorted(qw.unpack(QE, tmp_path / 'bin')) == ['ph.exe', 'pw.exe']
    written = (tmp_path / 'bin' / 'pw.exe').read_bytes()
    assert written.endswith(b'pw') and len(written) == len(program(b'pw')) and not (tmp_path / 'bin' / 'sub').exists()
    # Windows, 2026-11-27: pw.exe of the package (2 MB of stack) ended on Si₂ with the code 0xC00000FD; the stack of
    # every program kept is widened, a DLL is written as it is
    assert stack_of(program(b'pw')) == 2 * 1024 * 1024 and stack_of(written) == qw.STACK == 512 * 1024 * 1024
    assert written == qw.widen_stack(program(b'pw')) and qw.widen_stack(written) == written
    for wrong in (b'', b'MZ pw', b'#!/bin/sh' + bytes(300), program(b'x').replace(b'PE\0\0', b'NE\0\0')):
        with pytest.raises(ValueError):
            qw.widen_stack(wrong)
    assert qw.exe_name('pw.x') == 'pw.exe' and qw.exe_name('projwfc.x') == 'projwfc.exe'
    assert qw.exe_name('turbo_lanczos.x') == 'turbo_lanczos.exe'
    from modules.sextant import qe_inputs

    tools = {tool for steps in qe_inputs.STEPS.values() for _, tool in steps}
    assert tools <= set(qw.PROGRAMS)  # every program a task runs is kept


def _install(tmp_path, monkeypatch, files=FILES, broken=False, run=None):
    from modules.sextant import qe_pseudo

    monkeypatch.setattr(qw, 'decompress', lambda data, zstd=None: data)
    monkeypatch.setattr(qw, 'needs_program', lambda: False)
    fetched_pseudo = []
    monkeypatch.setattr(qe_pseudo, 'installed', lambda root, library=None: False)
    monkeypatch.setattr(qe_pseudo, 'download', lambda root: fetched_pseudo.append(root))
    asked, said = [], []

    def fetch(url):
        asked.append(url)
        assert url.startswith(qw.MIRROR)
        name = url[len(qw.MIRROR):]
        if name != qw.REPOSITORY and name not in files:
            raise OSError(f'HTTP Error 404: {name}')  # what urllib raises is an OSError
        return database(broken) if name == qw.REPOSITORY else files[name]

    code = qw.install(tmp_path, fetch=fetch, say=said.append, run=run)
    return code, asked, said, fetched_pseudo


def test_the_installation(tmp_path, monkeypatch):
    started = []
    code, asked, said, pseudo = _install(tmp_path, monkeypatch,
                                         run=lambda program, folder: (started.append(program) or 'Program PWSCF v.7.6', ''))
    target = tmp_path / '.tools' / 'qe' / 'bin'
    assert code == 0 and sorted(p.name for p in target.iterdir()) == ['libgomp-1.dll', 'libopenblas.dll', 'ph.exe', 'pw.exe']
    assert [a[len(qw.MIRROR):] for a in asked] == [qw.REPOSITORY, *list(FILES)[:3]]  # not the package nothing needs
    assert started == [target / 'pw.exe'] and pseudo == [tmp_path] and 'Program PWSCF v.7.6' in said[-2]
    assert install_tools.qe_program(tmp_path, windows=True) == target / 'pw.exe'
    assert install_tools.qe_program(tmp_path, 'ph.x', windows=True) == target / 'ph.exe'
    assert install_tools.qe_program(tmp_path, 'dos.x', windows=True) is None  # not in this made-up package


def test_what_stops_the_installation(tmp_path, monkeypatch):
    code, _, said, _ = _install(tmp_path / 'a', monkeypatch, broken=True)
    assert code == 1 and 'checksum' in said[-1] and 'openblas' in said[-1]
    code, _, said, _ = _install(tmp_path / 'b', monkeypatch, run=lambda program, folder: ('', 'libgfortran-5.dll not found'))
    assert code == 1 and 'does not start' in said[-1] and 'libgfortran' in said[-1]
    lacking = {k: v for k, v in FILES.items() if 'gomp' not in k}
    code, _, said, _ = _install(tmp_path / 'c', monkeypatch, files=lacking)
    assert code == 1 and 'was not installed' in said[-1]
    monkeypatch.setattr(qw, 'needs_program', lambda: True)
    monkeypatch.setattr(qw, 'find_zstd', lambda root: None)
    monkeypatch.setattr(qw, 'install_zstd', lambda root, say=print: None)
    said = []
    assert qw.install(tmp_path / 'd', fetch=lambda url: b'', say=said.append) == 1 and 'zstd' in said[-1]


def test_the_run_on_windows():
    from pathlib import Path

    from modules.compass.actions import qe_run
    from modules.sextant import qe_inputs

    program = Path('C:/Azimuth/.tools/qe/bin/pw.exe')
    command, script, changes = qe_run.windows_command([('pw.in', 'pw.x', '')], program, 6)
    assert command == [str(program), '-in', 'pw.in'] and script == ''
    assert changes['OMP_NUM_THREADS'] == '6' and changes['PATH'].startswith(str(program.parent))  # threads, not MPI
    assert changes['OMP_STACKSIZE'] == '512M'  # the stack of each thread, as that of the main one (qe_windows.STACK)
    steps = [(name, tool, '') for name, tool in qe_inputs.STEPS[qe_inputs.DOS_TASK]]
    command, script, _ = qe_run.windows_command(steps, program, 2)
    assert command == ['cmd', '/d', '/c', 'run.bat']
    lines = script.splitlines()
    assert lines[0] == '@echo off' and lines[1] == 'pw.exe -in scf.in || exit /b 1'
    assert any(line.startswith('projwfc.exe -in ') and line.endswith('> projwfc.out 2>&1') for line in lines)
    assert len(lines) == 1 + len(steps) and script.isascii()  # no folder named: nothing for the code page to spoil
    assert 'mpirun' not in script and 'C:' not in script


CP2K = archive({'ucrt64/bin/cp2k.ssmp.exe': program(b'cp2k'), 'ucrt64/bin/libcp2k.dll': b'MZ cp2k',
                'ucrt64/bin/grid_unittest.ssmp.exe': program(b'unit'), 'ucrt64/include/cp2k/libcp2k.h': b'h',
                'ucrt64/share/cp2k/data/BASIS_MOLOPT': b'basis', 'ucrt64/share/cp2k/data/GTH_POTENTIALS': b'gth',
                'ucrt64/share/cp2k/data/xc_section/pbe.sec': b'pbe', 'ucrt64/share/licenses/cp2k/LICENSE': b'l'})


def test_cp2k_of_the_same_repository(tmp_path, monkeypatch):
    # Windows, 2026-11-27: the package of MSYS2 holds cp2k.ssmp.exe (no MPI), libcp2k.dll, some unit tests and the data
    files = {PREFIX + 'cp2k-2026.2-2-any.pkg.tar.zst': CP2K, PREFIX + 'openblas-0.3.34-1-any.pkg.tar.zst': BLAS,
             PREFIX + 'libgomp-16.2.0-7-any.pkg.tar.zst': GOMP}
    listing = archive({
        'mingw-w64-ucrt-x86_64-cp2k-2026.2-2/desc': desc(PREFIX + 'cp2k', '2026.2-2', (PREFIX + 'openblas', PREFIX + 'omp'),
                                                          content=CP2K).encode(),
        'mingw-w64-ucrt-x86_64-openblas-0.3.34-1/desc': desc(PREFIX + 'openblas', '0.3.34-1', (PREFIX + 'omp',),
                                                              content=BLAS).encode(),
        'mingw-w64-ucrt-x86_64-libgomp-16.2.0-7/desc': desc(PREFIX + 'libgomp', '16.2.0-7', provides=(PREFIX + 'omp',),
                                                             content=GOMP).encode()})
    monkeypatch.setattr(qw, 'decompress', lambda data, zstd=None: data)
    monkeypatch.setattr(qw, 'needs_program', lambda: False)
    said, started = [], []

    def fetch(url):
        name = url[len(qw.MIRROR):]
        return listing if name == qw.REPOSITORY else files[name]

    code = qw.install_cp2k(tmp_path, fetch=fetch, say=said.append,
                           run=lambda found, folder: (started.append(found) or 'CP2K version 2026.2', ''))
    prefix = tmp_path / '.tools' / 'cp2k'
    assert code == 0, said
    assert sorted(p.name for p in (prefix / 'bin').iterdir()) == ['cp2k.ssmp.exe', 'libcp2k.dll', 'libgomp-1.dll',
                                                                   'libopenblas.dll']  # not the unit tests
    data = qw.cp2k_data(prefix)
    assert (data / 'BASIS_MOLOPT').read_bytes() == b'basis' and (data / 'xc_section' / 'pbe.sec').read_bytes() == b'pbe'
    assert not (prefix / 'share' / 'licenses').exists() and not (prefix / 'include').exists()
    assert stack_of((prefix / 'bin' / 'cp2k.ssmp.exe').read_bytes()) == qw.STACK  # as pw.exe
    assert started == [prefix / 'bin' / 'cp2k.ssmp.exe'] and 'CP2K version 2026.2' in said[-2] and 'done' in said[-1]
    found = install_tools.cp2k_program(tmp_path)
    assert found == prefix / 'bin' / 'cp2k.ssmp.exe'
    # a run: threads instead of processes, the stack of each, the data named (the path compiled in is not of this disk)
    env = install_tools.cp2k_environment(found, 4, {'PATH': 'X'})
    assert env['OMP_NUM_THREADS'] == '4' and env['OMP_STACKSIZE'] == '512M'
    assert env['CP2K_DATA_DIR'] == str(data) and env['PATH'].startswith(str(prefix / 'bin'))
    mpi = install_tools.cp2k_environment('/opt/homebrew/bin/cp2k.psmp', 4, {'PATH': 'X'})
    assert mpi['OMP_NUM_THREADS'] == '1' and 'CP2K_DATA_DIR' not in mpi and 'OMP_STACKSIZE' not in mpi
    # no data in the package: said, not left for the first calculation to find
    bare = {**files, PREFIX + 'cp2k-2026.2-2-any.pkg.tar.zst': archive({'ucrt64/bin/cp2k.ssmp.exe': program(b'cp2k')})}
    listing = archive({'mingw-w64-ucrt-x86_64-cp2k-2026.2-2/desc': desc(
        PREFIX + 'cp2k', '2026.2-2', content=bare[PREFIX + 'cp2k-2026.2-2-any.pkg.tar.zst']).encode()})
    files = bare
    assert qw.install_cp2k(tmp_path / 'other', fetch=fetch, say=said.append, run=None if False else lambda *a: ('x', '')) == 1
    assert 'BASIS_MOLOPT' in said[-1]

