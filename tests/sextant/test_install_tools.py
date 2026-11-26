"""Installing Open MPI 4.1, xtb and CREST into .tools/calc (modules/sextant/install_tools.py).

A fake conda in a temporary PATH records its arguments and creates the prefix with mpirun (printing
«Open MPI 4.1.6»), xtb and crest; the oracles are the command line conda-forge documents
(create -p PREFIX -c https://conda.anaconda.org/conda-forge openmpi=4.1 …) and the files the script must check. The environment of an ORCA
job gets OPAL_PREFIX and the library folder of a conda Open MPI.
"""

import io
import os
import platform
import stat
import sys
import tarfile

import pytest

from modules.sextant import install_tools as it
from modules.sextant import runner

POSIX = pytest.mark.skipif(os.name == 'nt', reason='the fake conda is a POSIX script')

FAKE_CONDA = """#!{python}
import pathlib, sys
args = sys.argv[1:]
pathlib.Path({log!r}).open('a').write(' '.join(args) + '\\n')
prefix = pathlib.Path(args[args.index('-p') + 1])
(prefix / 'conda-meta').mkdir(parents=True, exist_ok=True)
(prefix / 'bin').mkdir(exist_ok=True)
(prefix / 'lib').mkdir(exist_ok=True)
for name, text in (('mpirun', 'print("mpirun (Open MPI) {version}")'), ('xtb', 'pass'),
                   ('crest', 'print("       Version {crest}, the fake")'),  # 0.92.2: install_tools asks crest --version
                   ('pw.x', 'print("     Program PWSCF v.{qe} starts on 11Nov2026")'),
                   ('nwchem', 'print("         Total SCF energy =     {nwchem}")'),  # 0.128.0
                   ('psi4', 'import sys; open(sys.argv[2], "w").write("    Total Energy =  -2.8077839575\\n")')):
    path = prefix / 'bin' / name
    path.write_text('#!{python}\\nimport os\\n' + text + '\\n')
    path.chmod(0o755)
"""


def fake_conda(folder, log, version='4.1.6', crest='2.12', qe='7.6', nwchem='-2.807783957'):
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / ('conda.exe' if os.name == 'nt' else 'conda')  # the names searched on Windows
    path.write_text(FAKE_CONDA.format(python=sys.executable, log=str(log), version=version, crest=crest, qe=qe,
                                      nwchem=nwchem))
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


class Environment:
    """PATH, HOME and CONDA_EXE replaced for one test (the real conda of the computer is not touched)."""

    def __init__(self, **values):
        self.values = values

    def __enter__(self):
        self.saved = {k: os.environ.get(k) for k in ('PATH', 'HOME', 'CONDA_EXE')}
        os.environ.pop('CONDA_EXE', None)
        os.environ.update(self.values)
        return self

    def __exit__(self, *exc):
        for k, v in self.saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_command_and_manager(tmp_path, monkeypatch):
    monkeypatch.delenv('CONDA_EXE', raising=False)  # a terminal with conda activated (base) sets it
    root = tmp_path / 'azimuth'
    tool = fake_conda(tmp_path / 'bin', tmp_path / 'log')
    assert it.manager(root, home=tmp_path / 'home', path_env=str(tool.parent), system=False) == tool
    assert it.command(tool, root, ['openmpi', 'xtb'], windows=False, darwin=False) == [
        str(tool), 'create', '-y', '-p', str(root / '.tools' / 'calc'), '--override-channels', '-c', 'https://conda.anaconda.org/conda-forge', 'openmpi=4.1', 'xtb',
    ]
    (root / '.tools' / 'calc' / 'conda-meta').mkdir(parents=True)
    assert it.command(tool, root, ['crest'], windows=False)[1] == 'install'  # the prefix exists: add to it
    # CREST 2.12 on macOS (3.0.2 of conda-forge keeps the energy window of CREGEN at 0, crest-lab/crest#431)
    assert it.command(tool, root, ['xtb', 'crest'], windows=False, darwin=True)[-2:] == ['xtb', 'crest=2.12']
    assert it.command(tool, root, ['crest'], windows=False, darwin=False)[-1] == 'crest'


def test_windows_packages_and_folders(tmp_path):
    # conda-forge has win-64 builds of xtb, MOPAC and Microsoft MPI (msmpi) — «openmpi» means msmpi there;
    # the programs of a Windows prefix are in Library\bin; micromamba of Windows is Library/bin/micromamba.exe
    root = tmp_path / 'azimuth'
    command = it.command('micromamba.exe', root, ['openmpi', 'xtb', 'mopac'], windows=True)
    assert command[-3:] == ['msmpi', 'xtb', 'mopac'] and command[1] == 'create'
    target = it.prefix(root)
    assert it.bin_dirs(root, windows=True)[0] == target / 'Library' / 'bin'
    assert it.bin_dirs(root, windows=False) == [target / 'bin']
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w:bz2') as tar:
        data = b'MZ micromamba'
        info = tarfile.TarInfo('Library/bin/micromamba.exe')
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))
    made = it.unpack_micromamba(buffer.getvalue(), tmp_path / '.tools' / 'bin' / 'micromamba.exe')
    assert made.read_bytes() == data


def test_unpack_micromamba(tmp_path):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w:bz2') as tar:
        data = b'#!/bin/sh\necho micromamba\n'
        info = tarfile.TarInfo('bin/micromamba')
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))
        info = tarfile.TarInfo('info/about.json')
        info.size = 2
        tar.addfile(info, io.BytesIO(b'{}'))
    target = it.unpack_micromamba(buffer.getvalue(), tmp_path / '.tools' / 'bin' / 'micromamba')
    assert target.read_bytes() == data and os.access(target, os.X_OK)
    empty = io.BytesIO()
    with tarfile.open(fileobj=empty, mode='w:bz2'):
        pass
    with pytest.raises(ValueError):
        it.unpack_micromamba(empty.getvalue(), tmp_path / 'x')


@POSIX
def test_main_with_a_fake_conda(tmp_path):
    root = tmp_path / 'azimuth'
    root.mkdir()
    log = tmp_path / 'conda.log'
    tool = fake_conda(tmp_path / 'bin', log)
    with Environment(PATH=str(tool.parent), HOME=str(tmp_path / 'home')):
        assert it.main(['--root', str(root)]) == 0
        assert it.main(['--root', str(root), 'xtb']) == 0  # a second run installs into the same prefix
    calls = log.read_text().splitlines()
    crest = 'crest=2.12' if platform.system() == 'Darwin' else 'crest'
    assert calls[0].startswith('create -y -p ') and calls[0].endswith('--override-channels -c https://conda.anaconda.org/conda-forge openmpi=4.1 xtb ' + crest)
    assert calls[1].startswith('install -y -p ') and calls[1].endswith('https://conda.anaconda.org/conda-forge xtb')
    assert (root / '.tools' / 'calc' / 'bin' / 'mpirun').is_file()


@POSIX
def test_main_refuses_another_open_mpi(tmp_path):
    root = tmp_path / 'azimuth'
    root.mkdir()
    tool = fake_conda(tmp_path / 'bin', tmp_path / 'log', version='5.0.3')
    with Environment(PATH=str(tool.parent), HOME=str(tmp_path / 'home')):
        assert it.main(['--root', str(root), 'openmpi']) == 1  # ORCA is linked against Open MPI 4.1


def test_orca_environment_with_a_conda_open_mpi(tmp_path):
    mpi = tmp_path / 'calc'
    (mpi / 'conda-meta').mkdir(parents=True)
    (mpi / 'bin').mkdir()
    orca = tmp_path / 'orca_6' / 'orca'
    env = runner.environment(orca, 'orca', 4, mpi / 'bin' / 'mpirun', base={'PATH': '/usr/bin'})
    library = 'DYLD_LIBRARY_PATH' if sys.platform == 'darwin' else 'LD_LIBRARY_PATH'
    assert env['OPAL_PREFIX'] == str(mpi)
    assert env[library].split(os.pathsep)[:2] == [str(orca.parent), str(mpi / 'lib')]
    assert env['PATH'].split(os.pathsep)[:2] == [str(orca.parent), str(mpi / 'bin')]
    plain = runner.environment(orca, 'orca', 4, tmp_path / 'opt' / 'bin' / 'mpirun', base={})
    assert 'OPAL_PREFIX' not in plain  # not a conda prefix: Open MPI knows its own place


def test_conda_listed_in_environments_txt(tmp_path):
    # from the Finder there is no CONDA_EXE and no shell PATH; conda's own list of its prefixes names base
    home = tmp_path / 'home'
    base = tmp_path / 'somewhere' / 'anaconda3'
    # the conda of Windows lies in Scripts\conda.exe of the prefix
    tool = fake_conda(base / ('Scripts' if os.name == 'nt' else 'bin'), tmp_path / 'log')
    (home / '.conda').mkdir(parents=True)
    (home / '.conda' / 'environments.txt').write_text(f'{base}\n{base}/envs/chem\n')
    saved = os.environ.pop('CONDA_EXE', None)
    try:
        assert it.manager(tmp_path / 'azimuth', home=home, path_env='', system=False) == tool
    finally:
        if saved is not None:
            os.environ['CONDA_EXE'] = saved


def test_micromamba_is_pinned_and_checked(tmp_path, monkeypatch):
    # one version for all five platforms, each with its SHA-256 (64 hex digits); an archive of another hash is
    # refused before anything is written
    assert it.MICROMAMBA_URL.format('osx-arm64').endswith('/osx-arm64/' + it.MICROMAMBA_VERSION)
    assert set(it.MICROMAMBA_SHA256) == {'osx-arm64', 'osx-64', 'linux-64', 'linux-aarch64', 'win-64'}
    assert all(len(h) == 64 and int(h, 16) >= 0 for h in it.MICROMAMBA_SHA256.values())
    import hashlib
    import urllib.request

    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w:bz2') as tar:
        data = b'#!/bin/sh\necho micromamba\n'
        info = tarfile.TarInfo('bin/micromamba')
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))
    archive = buffer.getvalue()
    with pytest.raises(ValueError):
        it.check_micromamba(archive, 'linux-64')  # not the pinned build
    with pytest.raises(ValueError):
        it.check_micromamba(archive, 'beos-1')  # no hash for it

    class Response(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(it, 'platform_name', lambda: 'linux-64')
    monkeypatch.setattr(urllib.request, 'urlopen', lambda url, timeout=0: Response(archive))
    with pytest.raises(ValueError):
        it.download_micromamba(tmp_path)
    assert not (tmp_path / '.tools').exists()
    monkeypatch.setitem(it.MICROMAMBA_SHA256, 'linux-64', hashlib.sha256(archive).hexdigest())
    target = it.download_micromamba(tmp_path)
    assert target.read_bytes() == data


@POSIX
def test_curl_fallback(tmp_path):
    fake = tmp_path / 'curl'
    fake.write_text('#!/bin/sh\nprintf "archive bytes"\n')
    fake.chmod(0o755)
    assert it.curl('https://example.org/x', program=str(fake)) == b'archive bytes'
    failing = tmp_path / 'curl2'
    failing.write_text('#!/bin/sh\necho "no route" >&2\nexit 7\n')
    failing.chmod(0o755)
    with pytest.raises(OSError):
        it.curl('https://example.org/x', program=str(failing))


@POSIX
def test_a_hard_linked_program_becomes_a_file_of_its_own(tmp_path):
    # macOS looked for libomp.dylib of a hard-linked crest next to its copy in the package cache
    cache = tmp_path / 'pkgs' / 'crest-2.12' / 'bin' / 'crest'
    cache.parent.mkdir(parents=True)
    cache.write_bytes(b'#!/bin/sh\necho crest\n')
    cache.chmod(0o755)
    linked = tmp_path / 'calc' / 'bin' / 'crest'
    linked.parent.mkdir(parents=True)
    os.link(cache, linked)
    assert os.stat(linked).st_nlink == 2
    assert it.own_copy(linked) and os.stat(linked).st_nlink == 1 and os.stat(cache).st_nlink == 1
    assert linked.read_bytes() == cache.read_bytes() and os.access(linked, os.X_OK)
    assert not it.own_copy(linked) and not it.own_copy(tmp_path / 'none')
    assert not (linked.parent / 'crest.azimuth-copy').exists()


@POSIX
def test_a_crest_that_does_not_start_is_an_error(tmp_path):
    root = tmp_path / 'azimuth'
    root.mkdir()
    tool = fake_conda(tmp_path / 'bin', tmp_path / 'conda.log')
    text = tool.read_text().replace('print("       Version 2.12, the fake")', 'import sys; sys.exit(6)')
    tool.write_text(text)
    with Environment(PATH=str(tool.parent), HOME=str(tmp_path / 'home')):
        assert it.main(['--root', str(root), 'crest']) == 1
        assert it.main(['--root', str(root), 'xtb']) == 0


@POSIX
def test_quantum_espresso_into_its_own_prefix(tmp_path, monkeypatch):
    # «qe» goes into .tools/qe (its Open MPI 5 apart from the 4.1 of ORCA); with xtb — two calls, xtb first;
    # pw.x is checked by its «Program PWSCF v.» on an empty input
    from modules.sextant import qe_pseudo

    fetched = []  # the SSSP library is fetched once, after pw.x
    monkeypatch.setattr(qe_pseudo, 'download', lambda root: fetched.append(root))
    root = tmp_path / 'azimuth'
    root.mkdir()
    log = tmp_path / 'conda.log'
    tool = fake_conda(tmp_path / 'bin', log)
    with Environment(PATH=str(tool.parent), HOME=str(tmp_path / 'home')):
        assert it.main(['--root', str(root), 'qe']) == 0
        assert it.main(['--root', str(root), 'xtb', 'qe']) == 0
    calls = log.read_text().splitlines()
    assert calls[0] == f'create -y -p {root / ".tools" / "qe"} --override-channels -c https://conda.anaconda.org/conda-forge qe'
    assert calls[1].endswith('https://conda.anaconda.org/conda-forge xtb') and str(root / '.tools' / 'calc') in calls[1]
    assert calls[2].startswith('install -y -p ' + str(root / '.tools' / 'qe'))
    assert it.qe_program(root) == root / '.tools' / 'qe' / 'bin' / 'pw.x' and len(fetched) == 2


@POSIX
def test_a_pw_x_that_does_not_start_is_an_error(tmp_path, monkeypatch):
    from modules.sextant import qe_pseudo

    monkeypatch.setattr(qe_pseudo, 'download', lambda root: None)
    root = tmp_path / 'azimuth'
    root.mkdir()
    tool = fake_conda(tmp_path / 'bin', tmp_path / 'log', qe='')
    broken = (tmp_path / 'bin' / 'conda').read_text().replace('Program PWSCF v.', 'nothing')
    (tmp_path / 'bin' / 'conda').write_text(broken)
    with Environment(PATH=str(tool.parent), HOME=str(tmp_path / 'home')):
        assert it.main(['--root', str(root), 'qe']) == 1


def test_the_root_of_a_built_program(monkeypatch, tmp_path):
    # 0.91.55 / a built program cannot write into its own folder (Program Files; the signed Azimuth.app in
    # /Applications) — the programs it installs go to the folder of the user
    import sys
    from pathlib import Path

    from modules.sextant import install_tools

    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(Path, 'home', classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(sys, 'platform', 'darwin')
    assert install_tools.default_root() == tmp_path / 'Library' / 'Application Support' / 'Azimuth'
    monkeypatch.setattr(sys, 'platform', 'win32')
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path / 'Local'))
    assert install_tools.default_root() == tmp_path / 'Local' / 'Azimuth'


@POSIX
def test_nwchem_into_its_own_prefix(tmp_path):
    # «nwchem» goes into .tools/nwchem (its own MPI, apart from the Open MPI 4.1 of ORCA), after the others; it is
    # checked by a helium atom: «Total SCF energy» printed
    root = tmp_path / 'azimuth'
    root.mkdir()
    log = tmp_path / 'conda.log'
    tool = fake_conda(tmp_path / 'bin', log)
    with Environment(PATH=str(tool.parent), HOME=str(tmp_path / 'home')):
        assert it.main(['--root', str(root), 'nwchem']) == 0
        assert it.main(['--root', str(root), 'xtb', 'nwchem']) == 0
    calls = log.read_text().splitlines()
    assert calls[0] == f'create -y -p {root / ".tools" / "nwchem"} --override-channels -c https://conda.anaconda.org/conda-forge nwchem'
    assert calls[1].endswith('https://conda.anaconda.org/conda-forge xtb') and str(root / '.tools' / 'calc') in calls[1]
    assert calls[2].startswith('install -y -p ' + str(root / '.tools' / 'nwchem'))
    assert it.nwchem_program(root) == root / '.tools' / 'nwchem' / 'bin' / 'nwchem'
    assert it.command(tool, root, ['nwchem'])[-1] == 'nwchem'


@POSIX
def test_psi4_into_its_own_prefix(tmp_path, monkeypatch):
    # «psi4» goes into .tools/psi4 (its own Python); it is checked by a helium atom: «Total Energy =» in its output
    root = tmp_path / 'azimuth'
    root.mkdir()
    log = tmp_path / 'conda.log'
    tool = fake_conda(tmp_path / 'bin', log)
    with Environment(PATH=str(tool.parent), HOME=str(tmp_path / 'home')):
        assert it.main(['--root', str(root), 'psi4']) == 0
        assert it.main(['--root', str(root), 'xtb', 'psi4']) == 0
    calls = log.read_text().splitlines()
    assert calls[0] == (f'create -y -p {root / ".tools" / "psi4"} --override-channels -c https://conda.anaconda.org/conda-forge psi4 '
                        'dftd3-python dftd4-python>=3.5 gcp-correction')  # D3 and D4 for Psi4: programs of their own
    assert calls[1].endswith('https://conda.anaconda.org/conda-forge xtb') and str(root / '.tools' / 'calc') in calls[1]
    assert calls[2].startswith('install -y -p ' + str(root / '.tools' / 'psi4'))
    assert it.psi4_program(root) == root / '.tools' / 'psi4' / 'bin' / 'psi4'
    assert it.places(root, ('xtb', 'psi4')) == [root / '.tools' / 'calc', root / '.tools' / 'psi4']
    from modules.sextant import runner

    monkeypatch.setattr(it, 'tool_roots', lambda: [root])  # the runner finds the Psi4 installed here
    assert root / '.tools' / 'psi4' / 'bin' in runner._search_dirs('psi4', tmp_path / 'home')


@POSIX
def test_a_psi4_that_does_not_start_is_an_error(tmp_path):
    root = tmp_path / 'azimuth'
    root.mkdir()
    tool = fake_conda(tmp_path / 'bin', tmp_path / 'log')
    broken = (tmp_path / 'bin' / 'conda').read_text().replace('Total Energy =', 'ImportError: libint2')
    (tmp_path / 'bin' / 'conda').write_text(broken)
    with Environment(PATH=str(tool.parent), HOME=str(tmp_path / 'home')):
        assert it.main(['--root', str(root), 'psi4']) == 1


@POSIX
def test_a_nwchem_without_its_energy_is_an_error(tmp_path):
    root = tmp_path / 'azimuth'
    root.mkdir()
    tool = fake_conda(tmp_path / 'bin', tmp_path / 'log')
    broken = (tmp_path / 'bin' / 'conda').read_text().replace('Total SCF energy', 'no basis library')
    (tmp_path / 'bin' / 'conda').write_text(broken)
    with Environment(PATH=str(tool.parent), HOME=str(tmp_path / 'home')):
        assert it.main(['--root', str(root), 'nwchem']) == 1


def test_the_environment_of_a_conda_nwchem(tmp_path):
    # without the activation of its environment: OPAL_PREFIX of its own MPI and the basis library of the prefix
    base = tmp_path / 'nwchem'
    (base / 'conda-meta').mkdir(parents=True)
    (base / 'bin').mkdir()
    (base / 'share' / 'nwchem' / 'libraries').mkdir(parents=True)
    program = base / 'bin' / 'nwchem'
    program.write_text('')
    env = it.nwchem_environment(program)
    assert env['OPAL_PREFIX'] == str(base.resolve())
    assert env['NWCHEM_BASIS_LIBRARY'] == str((base / 'share' / 'nwchem' / 'libraries').resolve()) + os.sep
    assert runner.environment(program, 'nwchem', 1, base={'PATH': ''})['OPAL_PREFIX'] == str(base.resolve())
    assert it.nwchem_environment(tmp_path / 'elsewhere' / 'nwchem') == {}  # not a conda prefix: nothing set


def test_the_folders_of_an_installation_are_said_as_they_are(tmp_path):
    # the panel said «nwchem → .tools/calc»: NWChem, Quantum ESPRESSO and CP2K go to folders of their own
    from modules.sextant import install_tools

    assert install_tools.places(tmp_path, ('nwchem',)) == [tmp_path / '.tools' / 'nwchem']
    assert install_tools.places(tmp_path, ('openmpi', 'xtb', 'crest', 'qe', 'nwchem')) == [
        tmp_path / '.tools' / 'calc', tmp_path / '.tools' / 'qe', tmp_path / '.tools' / 'nwchem']


def test_the_channel_is_an_address_that_no_condarc_turns_into_a_mirror(tmp_path):
    # a conda of the computer with «custom_channels: conda-forge: <mirror>» in its .condarc took the mirror for the name
    # «conda-forge» even with --override-channels (Windows check, the mirror did not answer): the address goes as it is
    for packages in (['xtb', 'mopac'], ['qe'], ['nwchem'], ['psi4'], ['cp2k']):
        argv = it.command(tmp_path / 'conda', tmp_path, packages, windows=True, darwin=False)
        assert argv[argv.index('-c') + 1] == 'https://conda.anaconda.org/conda-forge'
        assert 'conda-forge' not in argv  # never the bare name
    assert it.manager_env(tmp_path)['CONDA_NUMBER_CHANNEL_NOTICES'] == '0'


def test_the_output_of_the_package_manager_goes_to_the_log(tmp_path, capsys):
    # the reason of a failure must reach install.log: the output is read and printed here, not left to a console
    talker = tmp_path / 'talker.py'
    talker.write_text('import sys\nprint("Collecting package metadata")\n'
                      'print("CondaHTTPError: HTTP 000 CONNECTION FAILED", file=sys.stderr)\nsys.exit(3)\n',
                      encoding='utf-8')
    assert it.run_manager([sys.executable, str(talker)], dict(os.environ)) == 3
    said = capsys.readouterr().out
    assert 'Collecting package metadata' in said and 'CONNECTION FAILED' in said
    assert it.run_manager([str(tmp_path / 'no-such-manager')], dict(os.environ)) == 1
    assert 'does not start' in capsys.readouterr().out
