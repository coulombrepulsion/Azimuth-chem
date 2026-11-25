"""modules/sextant/runner.py: finding ORCA and xtb, the xtb command and xcontrol, the job folder, running
a fake program to the end and stopping one with its child process.

The oracles are written here by hand: the xtb options and the xcontrol text from the xtb documentation
(«Commandline Usage», «Detailed Input»), the ORCA input from azimuth.core.orca_input, the energies printed
by the fake programs below.
"""

from datetime import datetime
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

from modules.sextant import runner
from tests.fake_programs import alive, program_script
from azimuth.core import Atom, Calculation, Molecule, orca_input

WATER = Molecule('water', (Atom('O', 0.0, 0.0, 0.117), Atom('H', 0.0, 0.757, -0.469), Atom('H', 0.0, -0.757, -0.469)))
BUTANE_LIKE = Molecule('c4', tuple(Atom('C', 1.5 * i, 0.3 * (i % 2), 0.0) for i in range(4)))
NOW = datetime(2026, 10, 24, 1, 2, 3)
POSIX = pytest.mark.skipif(os.name == 'nt', reason='the fake programs are POSIX scripts')

FAKE_ORCA = """#!{python}
import sys, pathlib
text = pathlib.Path(sys.argv[1]).read_text()
assert '* xyz 0 1' in text
print('                                 * O   R   C   A *')
for cycle, energy in enumerate((-76.30, -76.32, -76.33), 1):
    print('*' * 40); print(f'*  GEOMETRY OPTIMIZATION CYCLE {{cycle}}  *'); print('*' * 40)
    print(f'FINAL SINGLE POINT ENERGY      {{energy:.9f}}')
print('                             ****ORCA TERMINATED NORMALLY****')
"""

SLEEPER = """#!{python}
import subprocess, sys, time, pathlib
child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
pathlib.Path('child.pid').write_text(str(child.pid))
print('started', flush=True)
time.sleep(60)
"""


def script(path, text):
    """A fake program; on Windows a .cmd with the script next to it (the tests of finding, running and
    stopping the programs run on Windows too) — the path returned is the one to give."""
    return program_script(path, text.format(python=sys.executable))


def orca_folder(base):
    base.mkdir(parents=True)
    (base / 'orca_scf').write_text('')
    return script(base / 'orca', FAKE_ORCA)


def wait(job, seconds=30):
    end = time.monotonic() + seconds
    while job.poll() is None:
        assert time.monotonic() < end, 'the job did not end'
        time.sleep(0.05)
    return job.code


def test_xtb_arguments_follow_the_documentation():
    calc = Calculation(task='Оптимизация + частоты', charge=0, multiplicity=1, cores=4)
    # 100 optimization cycles by default (--cycles, xtb 6 «Commandline Usage»); none for a single point
    assert runner.xtb_arguments(calc) == ['molecule.xyz', '--gfn', '2', '--chrg', '0', '--uhf', '0', '--ohess', '--cycles', '100',
                                          '-P', '4']
    assert runner.xtb_arguments(calc, xyz='C2H6_GFN2-xTB.xyz')[0] == 'C2H6_GFN2-xTB.xyz'
    calc = Calculation(task='Энергия', charge=-1, multiplicity=3, cores=1)
    assert runner.xtb_arguments(calc) == ['molecule.xyz', '--gfn', '2', '--chrg', '-1', '--uhf', '2', '-P', '1']
    calc = Calculation(task='Оптимизация', cores=2)
    assert runner.xtb_arguments(calc, (('B', (0, 1)),))[-6:] == ['--input', 'xcontrol', '--cycles', '100', '-P', '2']
    assert '--opt' in runner.xtb_arguments(calc)


def test_xcontrol_text():
    text = runner.xcontrol((('C', (0,)), ('C', (3,)), ('B', (0, 1)), ('A', (1, 0, 2)), ('D', (0, 1, 2, 3))))
    assert text == (
        '$fix\n   atoms: 1,4\n'
        '$constrain\n   force constant=0.5\n'
        '   distance: 1, 2, auto\n   angle: 2, 1, 3, auto\n   dihedral: 1, 2, 3, 4, auto\n'
        '$end\n'
    )
    assert runner.xcontrol(()) == ''
    assert runner.xcontrol((('B', (2, 4)),)) == '$constrain\n   force constant=0.5\n   distance: 3, 5, auto\n$end\n'


def test_xtb_preview_and_validation():
    text = runner.xtb_preview(WATER, Calculation(task='Оптимизация', cores=2), (('B', (0, 1)),))
    assert 'xtb H2O_GFN2-xTB.xyz --gfn 2 --chrg 0 --uhf 0 --opt --input xcontrol --cycles 100 -P 2' in text
    assert '# H2O_GFN2-xTB.xyz\n' in text
    assert WATER.xyz() in text and 'distance: 1, 2, auto' in text
    energy = runner.xtb_preview(WATER, Calculation(task='Энергия'), (('B', (0, 1)),))
    assert 'xcontrol' not in energy  # constraints only for an optimization
    with pytest.raises(ValueError):
        runner.validate_xtb(WATER, Calculation(multiplicity=2))  # 10 electrons: a doublet is impossible
    with pytest.raises(ValueError):
        runner.validate_xtb(Molecule('u', (Atom('U', 0.0, 0.0, 0.0),)), Calculation(multiplicity=1))  # Z = 92
    with pytest.raises(ValueError):
        runner.validate_xtb(Molecule('empty', ()), Calculation())
    runner.validate_xtb(Molecule('i2', (Atom('I', 0, 0, 0), Atom('I', 0, 0, 2.67))), Calculation())  # Z = 53 is fine


def test_find_program(tmp_path):
    home = tmp_path / 'home'
    old = orca_folder(home / 'orca_5_0_4')
    new = orca_folder(home / 'orca_6_0_1')
    assert runner.find_program('orca', home=home, path_env='', system=False) == new  # the newest-looking folder
    assert runner.find_program('orca', configured=str(old), home=home, path_env='', system=False) == old
    lonely = tmp_path / 'bin'
    lonely.mkdir()
    reader = script(lonely / 'orca', '#!/bin/sh\n')  # the screen reader of GNOME: no orca_* next to it
    assert runner.find_program('orca', home=tmp_path / 'nobody', path_env=str(lonely), system=False) is None
    with pytest.raises(ValueError):
        runner.check_program('orca', reader)
    assert runner.find_program('orca', configured=str(reader), home=home, path_env='', system=False) == new
    xtb = script(home / 'miniforge3' / 'envs' / 'chem' / 'bin' / 'xtb', '#!/bin/sh\n')
    assert runner.find_program('xtb', home=home, path_env='', system=False) == xtb
    if os.name == 'nt':  # conda on Windows keeps xtb.exe in Library\bin of the environment
        other = tmp_path / 'home2'
        conda = script(other / 'miniforge3' / 'envs' / 'chem' / 'Library' / 'bin' / 'xtb', '#!/bin/sh\n')
        assert runner.find_program('xtb', home=other, path_env='', system=False) == conda
    assert runner.find_program('xtb', home=tmp_path / 'nobody', path_env='', system=False) is None
    assert runner.find_program('xtb', home=tmp_path / 'nobody', path_env=str(xtb.parent), system=False) == xtb
    plain = tmp_path / 'plain.txt'
    plain.write_text('')
    with pytest.raises(ValueError):
        runner.check_program('xtb', plain)  # not executable
    with pytest.raises(ValueError):
        runner.check_program('xtb', tmp_path / 'missing')


def test_job_folder_names(tmp_path):
    first = runner.job_folder(tmp_path / 'jobs', WATER, 'xtb', NOW)
    second = runner.job_folder(tmp_path / 'jobs', WATER, 'xtb', NOW)
    assert first.name == '2026-10-24_01-02-03_H2O_xtb' and second.name == '2026-10-24_01-02-03_H2O_xtb-2'
    assert first.is_dir() and second.is_dir()


@POSIX
def test_prepare_orca_and_xtb(tmp_path):
    orca = orca_folder(tmp_path / 'orca_6')
    root = tmp_path / 'jobs'
    calc = Calculation(task='Оптимизация', cores=2)
    with pytest.raises(ValueError):
        runner.prepare('orca', orca, WATER, calc, (), root, NOW)  # 2 processes, no mpirun
    assert not root.exists() or not any(root.iterdir())  # nothing was created
    mpirun = script(tmp_path / 'mpi' / 'mpirun', '#!/bin/sh\n')
    spec = runner.prepare('orca', orca, WATER, calc, (('B', (0, 1)),), root, NOW, mpirun=mpirun)
    # the files are named after the calculation (formula_method_basis)
    assert (spec.folder / 'H2O_B3LYP_def2-SVP.inp').read_text() == orca_input(WATER, calc, (('B', (0, 1)),))
    assert spec.command == (str(orca.resolve()), 'H2O_B3LYP_def2-SVP.inp')
    assert spec.output == spec.stdout == spec.folder / 'H2O_B3LYP_def2-SVP.out'
    path = spec.env['PATH'].split(os.pathsep)
    assert path[0] == str(orca.parent) and path[1] == str(spec.folder / runner.MPI_WRAPPER) and path[2] == str(mpirun.parent)
    library = 'DYLD_LIBRARY_PATH' if sys.platform == 'darwin' else 'LD_LIBRARY_PATH'
    assert spec.env[library].split(os.pathsep)[0] == str(orca.parent) and spec.env['OMP_NUM_THREADS'] == '2'

    xtb = script(tmp_path / 'xbin' / 'xtb', '#!/bin/sh\n')
    spec = runner.prepare('xtb', xtb, WATER, calc, (('B', (0, 1)),), root, NOW)
    assert (spec.folder / 'H2O_GFN2-xTB.xyz').read_text() == WATER.xyz()
    assert (spec.folder / 'xcontrol').read_text() == runner.xcontrol((('B', (0, 1)),))
    assert spec.command == (str(xtb), *runner.xtb_arguments(calc, (('B', (0, 1)),), 'H2O_GFN2-xTB.xyz'))
    assert spec.env['OMP_STACKSIZE'] == '1G' and spec.output.name == 'H2O_GFN2-xTB.out'
    spec = runner.prepare('xtb', xtb, WATER, Calculation(task='Энергия', cores=1), (('B', (0, 1)),), root, NOW)
    assert not (spec.folder / 'xcontrol').exists() and '--input' not in spec.command
    with pytest.raises(ValueError):
        runner.prepare('xtb', xtb, Molecule('u', (Atom('U', 0, 0, 0),)), Calculation(), (), root, NOW)


def test_a_fake_orca_runs_to_the_end(tmp_path):
    orca = orca_folder(tmp_path / 'orca_6')
    spec = runner.prepare('orca', orca, WATER, Calculation(task='Оптимизация', cores=1), (), tmp_path / 'jobs', NOW)
    job = runner.Job(spec).start()
    assert wait(job) == 0 and not job.running and job.elapsed() > 0
    text = job.text()
    assert runner.finished_normally('orca', text, job.code)
    assert runner.progress('orca', text) == (3, pytest.approx(-76.33, abs=1e-12))
    assert runner.tail(text, 1).strip() == '****ORCA TERMINATED NORMALLY****'
    job.stop()  # a finished job: nothing happens
    assert not job.stopped


def test_stop_ends_the_program_and_its_child(tmp_path):
    sleeper = script(tmp_path / 'xbin' / 'xtb', SLEEPER)
    spec = runner.prepare('xtb', sleeper, WATER, Calculation(task='Энергия', cores=1), (), tmp_path / 'jobs', NOW)
    job = runner.Job(spec).start()
    pid_file = spec.folder / 'child.pid'
    end = time.monotonic() + 20
    while not (pid_file.exists() and pid_file.read_text()):
        assert time.monotonic() < end and job.poll() is None
        time.sleep(0.05)
    child = int(pid_file.read_text())
    for name in ('H2O.tmp', 'H2O_D0.tmp', 'H2O.tmp.0', 'Gau-1234.rwf'):  # the scratch of a stopped job
        (spec.folder / name).write_text('scratch')
    job.stop()
    code = wait(job, 10)
    assert job.stopped and code != 0 and not runner.finished_normally('xtb', job.text(), code)
    left = {p.name for p in spec.folder.iterdir()}
    assert not left & {'H2O.tmp', 'H2O_D0.tmp', 'H2O.tmp.0', 'Gau-1234.rwf'} and spec.output.name in left
    end = time.monotonic() + 10
    while alive(child):  # the child was in the same process group (on Windows: in the tree of the program) — it ended too
        assert time.monotonic() < end, 'the child process is still alive'
        time.sleep(0.05)


def test_scratch_files_are_told_from_the_results(tmp_path):
    """Only the scratch files go — the outputs, orbitals, Hessian, checkpoint and the input stay."""
    scratch = ('x.tmp', 'x_D0.tmp', 'x.tmp.12', 'x.bas.tmp', 'Gau-77.rwf', 'Gau-77.int', 'Gau-77.d2e', 'Gau-77.scr',
               'psi.4242.35')
    kept = ('x.out', 'x.gbw', 'x.hess', 'x.inp', 'x.chk', 'x.log', 'x_trj.xyz', 'x.molden.input', 'temperature.txt',
            'x.densities', 'tmp')
    for name in scratch + kept:
        (tmp_path / name).write_text('')
    (tmp_path / 'sub.tmp').mkdir()  # folders are never removed
    assert runner.clean_temporaries(tmp_path) == sorted(scratch)
    assert {p.name for p in tmp_path.iterdir()} == set(kept) | {'sub.tmp'}
    assert runner.clean_temporaries(tmp_path / 'missing') == []


def test_progress_of_xtb(tmp_path):
    (tmp_path / 'xtbopt.log').write_text(
        '3\n energy: -5.070544440612 gnorm: 0.1\nO 0 0 0\nH 0 0 1\nH 0 1 0\n'
        '3\n energy: -5.070600000000 gnorm: 0.01\nO 0 0 0\nH 0 0 1\nH 0 1 0\n'
    )
    assert runner.progress('xtb', '', tmp_path) == (2, -5.0706)
    out = '          | TOTAL ENERGY               -5.070544440612 Eh   |\n'
    assert runner.progress('xtb', out, tmp_path / 'none') == (0, -5.070544440612)
    assert runner.progress('orca', 'nothing yet') == (0, None)


def test_finished_normally_and_texts():
    assert runner.finished_normally('xtb', ' * finished run on 2026/10/24\nnormal termination of xtb\n', 0)
    assert not runner.finished_normally('xtb', 'normal termination of xtb', 1)
    assert not runner.finished_normally('orca', 'ORCA finished by error termination in SCF', 0)
    assert not runner.finished_normally('orca', '****ORCA TERMINATED NORMALLY****', 2)
    assert runner.duration(5) == '5 с' and runner.duration(125) == '2 мин 05 с' and runner.duration(3725) == '1 ч 02 мин'
    assert runner.tail('a\nb\nc\n', 2) == 'b\nc'


FAKE_PSI4 = """#!{python}
import sys, pathlib
inp, out = sys.argv[1], sys.argv[2]
assert sys.argv[3:] == ['-n', '1'] and "energy('b3lyp')" in pathlib.Path(inp).read_text()
print('psi4 says hello on stdout')
pathlib.Path(out).write_text(
    '    Psi4: An Open-Source Ab Initio Electronic Structure Package\\n'
    '  @DF-RKS Final Energy:   -76.38\\n'
    '*** Psi4 exiting successfully. Buy a developer a beer!\\n'
)
"""


@POSIX
def test_gaussian_and_psi4_jobs(tmp_path):
    # Gaussian is recognized by l1.exe next to g16; its output is input.log, written by itself, and
    # its environment carries g16root, GAUSS_EXEDIR and the scratch folder; Psi4 writes <name>.out itself
    home = tmp_path / 'home'
    lonely = script(home / 'bin' / 'g16', '#!/bin/sh\n')
    assert runner.find_program('gaussian', home=home, path_env=str(lonely.parent), system=False) is None
    g16 = script(home / 'g16' / 'g16', '#!/bin/sh\n')
    (g16.parent / 'l1.exe').write_text('')
    assert runner.find_program('gaussian', home=home, path_env='', system=False) == g16
    with pytest.raises(ValueError):
        runner.check_program('gaussian', lonely)
    spec = runner.prepare('gaussian', g16, WATER, Calculation(task='Энергия', cores=1), (), tmp_path / 'jobs', NOW)
    name = 'H2O_B3LYP_def2-SVP'
    assert spec.command == (str(g16), f'{name}.gjf') and spec.output.name == f'{name}.log' and spec.stdout.name == f'{name}.stdout'
    assert (spec.folder / f'{name}.gjf').read_text().startswith('%nprocshared=1\n%mem=1000MB\n#P B3LYP/def2SVP SCF=Tight\n')
    assert spec.env['g16root'] == str(home) and spec.env['GAUSS_SCRDIR'] == str(spec.folder)
    assert spec.env['GAUSS_EXEDIR'].split(os.pathsep) == [str(g16.parent / 'bsd'), str(g16.parent)]

    psi4 = script(home / 'miniconda3' / 'envs' / 'p4' / 'bin' / 'psi4', FAKE_PSI4)
    assert runner.find_program('psi4', home=home, path_env='', system=False) == psi4
    spec = runner.prepare('psi4', psi4, WATER, Calculation(task='Энергия', cores=1), (), tmp_path / 'jobs', NOW)
    assert spec.command == (str(psi4), f'{name}.dat', f'{name}.out', '-n', '1') and spec.env['PSI_SCRATCH'] == str(spec.folder)
    job = runner.Job(spec).start()
    assert wait(job) == 0 and runner.finished_normally('psi4', job.text(), job.code)
    assert runner.progress('psi4', job.text()) == (1, -76.38)
    assert job.stdout_text().strip() == 'psi4 says hello on stdout'
    with pytest.raises(ValueError):
        runner.prepare('psi4', psi4, WATER, Calculation(task='ЯМР (экранирование)'), (), tmp_path / 'jobs', NOW)


def test_gaussian_progress_and_end():
    text = (
        ' SCF Done:  E(RB3LYP) =  -76.4089  A.U. after   10 cycles\n Step number   1 out of a maximum of  20\n'
        ' SCF Done:  E(RB3LYP) =  -76.4100  A.U. after    8 cycles\n Step number   2 out of a maximum of  20\n'
        ' Normal termination of Gaussian 16 at Sat Oct 24 01:02:03 2026.\n'
    )
    assert runner.progress('gaussian', text) == (2, -76.41)
    assert runner.finished_normally('gaussian', text, 0)
    assert not runner.finished_normally('gaussian', text + ' Error termination via Lnk1e\n', 0)  # Opt Freq: 2nd step failed
    assert not runner.finished_normally('psi4', 'Psi4 exiting successfully', 1)


@POSIX
def test_mpi_wrapper_restores_the_library_path(tmp_path):
    # macOS drops DYLD_* on the way ORCA → /bin/sh → mpirun («Library not loaded: libmpi.40.dylib»);
    # the wrapper is started here without the variable (as the shell would) and must hand it to mpirun
    library = 'DYLD_LIBRARY_PATH' if sys.platform == 'darwin' else 'LD_LIBRARY_PATH'
    # the fake mpirun is a Python program, not a /bin/sh script: on macOS /bin/sh itself drops DYLD_* (the
    # real mpirun is a binary and keeps them)
    mpirun = script(
        tmp_path / 'mpi' / 'bin' / 'mpirun',
        '#!{python}\nimport os, sys\nprint(" ".join(sys.argv[1:]) + "|" + os.environ.get("' + library + '", ""))\n',
    )
    orca = orca_folder(tmp_path / 'orca_6')
    spec = runner.prepare('orca', orca, WATER, Calculation(task='Энергия', cores=2), (), tmp_path / 'jobs', NOW, mpirun=mpirun)
    wrapper = spec.folder / runner.MPI_WRAPPER / 'mpirun'
    assert spec.env['AZIMUTH_' + library] == spec.env[library] and str(tmp_path / 'mpi' / 'lib') in spec.env[library]
    stripped = {k: v for k, v in spec.env.items() if k != library}
    out = subprocess.run([str(wrapper), '-np', '2', 'x'], env=stripped, capture_output=True, text=True).stdout.strip()
    assert out == '-np 2 x|' + spec.env[library]
    one = runner.prepare('orca', orca, WATER, Calculation(task='Энергия', cores=1), (), tmp_path / 'jobs', NOW, mpirun=mpirun)
    assert not (one.folder / runner.MPI_WRAPPER).exists()  # one process: ORCA does not call mpirun


def test_milestones_in_the_order_they_appear():
    # the stages shown in the window of the calculation
    orca = 'x\nSCF CONVERGED AFTER 9 CYCLES\n...\nTHE OPTIMIZATION HAS CONVERGED\nSCF CONVERGED AFTER 3 CYCLES\nVIBRATIONAL FREQUENCIES\n'
    assert [k for k, _ in runner.milestones('orca', orca)] == ['scf', 'opt', 'freq']
    assert runner.milestones('gaussian', ' SCF Done:  E(RB3LYP) = -76.4\n Harmonic frequencies (cm**-1)')[1][0] == 'freq'
    assert runner.milestones('xtb', '*** convergence criteria satisfied after 9 iterations ***') == [('scf', 'Самосогласованное поле сошлось')]
    assert runner.milestones('psi4', '') == [] and runner.milestones('xtb', 'CHEMICAL SHIELDING SUMMARY') == []


@pytest.mark.skipif(os.name == 'nt', reason='the fake ORCA tools are POSIX scripts')
def test_molden_from_gbw_with_orca_2mkl(tmp_path):
    # the orbitals of an ORCA result are in input.gbw; orca_2mkl next to orca writes input.molden.input
    import stat

    folder = tmp_path / 'orca'
    folder.mkdir()
    orca, tool = folder / 'orca', folder / 'orca_2mkl'
    orca.write_text('#!/bin/sh\nexit 0\n')
    tool.write_text('#!/bin/sh\necho "[Molden Format]" > "$1.molden.input"\n')
    for f in (orca, tool):
        f.chmod(f.stat().st_mode | stat.S_IXUSR)
    job = tmp_path / 'job'
    job.mkdir()
    gbw = job / 'input.gbw'
    gbw.write_bytes(b'orbitals')
    path = runner.molden_from_gbw(gbw, str(orca))
    assert path == job / 'input.molden.input' and path.read_text().startswith('[Molden Format]')
    assert runner.molden_from_gbw(gbw, str(orca)) == path  # newer than the .gbw: used as it is
    with pytest.raises(ValueError):
        runner.molden_from_gbw(job / 'missing.gbw', str(orca))


def test_problems_of_a_failed_calculation_and_more_stages():
    # what went wrong, from the messages the programs print (ASSUMPTION of runner.PROBLEMS: ORCA 5/6, Gaussian 16,
    # Psi4 1.7, xtb 6), and the earlier stages of the way
    orca_scf = 'INITIAL GUESS\n...\n                   *****************************\n  SCF NOT CONVERGED AFTER 125 CYCLES\n'
    found = runner.diagnose('orca', orca_scf, 1)
    assert found and found[0][0].startswith('Самосогласованное поле') and 'Трудная сходимость' in found[0][1]
    assert runner.diagnose('orca', 'Error (ORCA_SCF): Not enough memory available!\nPlease increase MaxCore', 1)[0][0] \
        == 'Не хватило памяти.'
    assert runner.diagnose('gaussian', ' Number of steps exceeded,  NStep=  100\n Error termination via Lnk1e', 1)[0][0] \
        .startswith('Оптимизация геометрии')
    assert runner.diagnose('orca', 'UNRECOGNIZED OR DUPLICATED KEYWORD(S) IN SIMPLE INPUT LINE\n  FOO', 1)[0][0] \
        == 'Ошибка во входном файле.'
    assert runner.diagnose('orca', 'Total Charge  ... 0\nMultiplicity ... 1\nORCA TERMINATED NORMALLY', 1) == []
    killed = runner.diagnose('orca', 'cycle 3', 137)
    assert killed and 'нехватка памяти' in killed[0][1]
    assert runner.diagnose('orca', 'stopped', -15) == []  # «Остановить» is not a problem
    keys = [k for k, _ in runner.milestones('orca', 'BASIS SET INFORMATION\nINITIAL GUESS\nSCF CONVERGED AFTER 9\n'
                                                     'CARTESIAN GRADIENT\n')]
    assert keys == ['setup', 'guess', 'scf', 'gradient']


def test_jobs_folder_has_a_latin_path_on_windows(tmp_path):
    # on Windows the programs do not open files on a path with Cyrillic letters — the default folder of the
    # calculations is «Calculations» and leaves a Cyrillic home folder; macOS and Linux keep «Расчёты»
    from modules.sextant.runner import default_jobs_root, latin_path

    assert default_jobs_root(tmp_path, windows=False).name == 'Расчёты'
    latin = tmp_path / 'sergei'
    assert default_jobs_root(latin, windows=True) == latin / 'Documents' / 'Azimuth' / 'Calculations' or not str(latin).isascii()
    cyrillic = tmp_path / 'Сергей'
    root = default_jobs_root(cyrillic, windows=True, environ={'PUBLIC': 'C:\\Users\\Public'})
    assert str(root).isascii() and root.name == 'Calculations' and 'Public' in str(root)
    root = default_jobs_root(cyrillic, windows=True, environ={'SystemDrive': 'D:'})
    assert str(root).startswith('D:') and str(root).isascii()
    assert latin_path('C:\\Users\\sergei\\Calc', windows=True) and not latin_path(cyrillic, windows=True)
    assert latin_path(cyrillic, windows=False)


def test_microsoft_mpi_is_found_for_orca_on_windows(tmp_path, monkeypatch):
    # ORCA on Windows runs its parallel parts with mpiexec.exe of Microsoft MPI (MSMPI_BIN, Program Files)
    import stat

    from modules.sextant import runner
    from modules.sextant.runner import find_mpirun, msmpi_dirs

    # the .tools of the program folder come first (find_mpirun): on a Windows with xtb installed there is an mpiexec.exe of
    # conda-forge in .tools\calc\Library\bin, found before the one of this test (Windows check 2026-11-25)
    monkeypatch.setattr(runner, 'tools_bins', lambda: [])
    bin_dir = tmp_path / 'Microsoft MPI' / 'Bin'
    bin_dir.mkdir(parents=True)
    mpiexec = bin_dir / 'mpiexec.exe'
    mpiexec.write_text('')
    mpiexec.chmod(mpiexec.stat().st_mode | stat.S_IXUSR)
    assert bin_dir in msmpi_dirs({'MSMPI_BIN': str(bin_dir)})
    assert bin_dir in msmpi_dirs({'ProgramFiles': str(tmp_path)})
    assert find_mpirun(home=tmp_path, path_env='', windows=True, environ={'MSMPI_BIN': str(bin_dir)}) == mpiexec
    assert find_mpirun(home=tmp_path, path_env='', windows=True, environ={'ProgramFiles': str(tmp_path)}) == mpiexec
    assert find_mpirun(home=tmp_path, path_env='', windows=False, environ={'MSMPI_BIN': str(bin_dir)}) != mpiexec


def test_diagnose_of_an_unconverged_orca_optimization():
    # an optimization out of cycles ends «normally»; it
    # is said, and an «Error» elsewhere in the output is no longer taken for a wrong multiplicity
    from modules.sextant.runner import diagnose

    unconverged = ('  The optimization has not yet converged - more geometry cycles are needed\n'
                   ' Gradient Error estimate 1e-3\n Multiplicity           Mult            ....    1\n'
                   '****ORCA TERMINATED NORMALLY****\n')
    assert [what for what, _ in diagnose('orca', unconverged, 0)] == ['Оптимизация геометрии не сошлась за отведённые циклы.']
    # the line is printed after every cycle but the last — a converged run (HURRAY) is not unconverged
    from pathlib import Path

    converged = (Path(__file__).parents[1] / 'data' / 'orca601' / 'h2o_opt.out').read_text(encoding='utf-8')
    assert converged.count('has not yet converged') == 3 and diagnose('orca', converged, 0) == []
    wrong = 'Error : multiplicity (2) is odd and number of electrons (10) is even -> impossible\n'
    assert [what for what, _ in diagnose('orca', wrong, 1)] == ['Заряд и мультиплетность не подходят к молекуле.']


def test_diagnose_names_the_meta_gga_excited_state_gradient():
    # the user's ORCA 6.0.1 run — TPSSh, «Оптимизация возбуждённого состояния», stopped before the SCF
    from pathlib import Path

    text = (Path(__file__).parents[1] / 'data' / 'orca601' / 'h2o_excited_opt_tpssh_meta_gga.out').read_text(encoding='utf-8')
    found = runner.diagnose('orca', text, 1)
    assert found and 'мета-GGA' in found[0][0] and 'CAM-B3LYP' in found[0][1]


def test_start_from_the_orbitals_of_an_earlier_calculation(tmp_path):
    # MORead — the chosen .gbw is copied into the job folder as core.GUESS_FILE, which %moinp names; a file
    # gone is said before anything is made
    from azimuth.core import GUESS_FILE

    orca = orca_folder(tmp_path / 'orca_6')
    root = tmp_path / 'jobs'
    old = tmp_path / 'earlier' / 'H2O_B3LYP_def2-SVP.gbw'
    old.parent.mkdir()
    old.write_bytes(b'\x00orbitals')
    calc = Calculation(task='Оптимизация', cores=1, guess=str(old))
    spec = runner.prepare('orca', orca, WATER, calc, (), root, NOW)
    text = (spec.folder / 'H2O_B3LYP_def2-SVP.inp').read_text()
    assert 'MORead' in text.splitlines()[1] and f'%moinp "{GUESS_FILE}"' in text
    assert (spec.folder / GUESS_FILE).read_bytes() == b'\x00orbitals'
    made = sorted(root.iterdir())
    with pytest.raises(ValueError, match='не найден'):
        runner.prepare('orca', orca, WATER, Calculation(cores=1, guess=str(tmp_path / 'gone.gbw')), (), root, NOW)
    assert sorted(root.iterdir()) == made  # no folder for the refused one
    xtb = script(tmp_path / 'xbin' / 'xtb', '#!/bin/sh\n')
    spec = runner.prepare('xtb', xtb, WATER, Calculation(task='Оптимизация', guess=str(old)), (), root, NOW)
    assert not (spec.folder / GUESS_FILE).exists()  # not a program that reads it


def test_diagnose_of_orca_6_1_without_a_third_derivative():
    # ORCA 6.1.1 (Windows) has no native third derivative of B88 exchange for the TD-DFT gradient
    from pathlib import Path

    from modules.spectrum.readers.outputs import read_any

    data = Path(__file__).parents[1] / 'data' / 'orca611'
    failed = (data / 'ch2o_excited_opt_b3lyp.out').read_text(encoding='utf-8')
    found = runner.diagnose('orca', failed, 55)
    assert found[0][0] == 'ORCA не считает оптимизацию возбуждённого состояния с этим функционалом.'
    assert 'LibXC(B3LYP)' in found[0][1]
    text = (data / 'ch2o_excited_opt_libxc_b3lyp.out').read_text(encoding='utf-8')
    libxc = read_any(text)
    assert libxc.normal_exit and libxc.optimization_converged and len(libxc.steps) == 7
    assert libxc.energies[-1] == pytest.approx(-114.218020274221, abs=1e-9)  # E(tot) of root 1 (ORCA 6.0.1: −114.218015)
    assert libxc.excited_energy is None and runner.diagnose('orca', text, 0) == []


def test_crest_3_0_2_on_macos_sorts_with_a_window_of_zero():
    # CREST 3.0.2 of conda-forge on macOS (the user's Mac, 2026-11-07; crest-lab/crest#431): «sorting energy
    # window (EWIN) : 0.0000» whatever --ewin says — four frames 0–12.6 kcal/mol apart sorted with --ewin 20 kept one;
    # CREST 2.12 kept four
    data = Path(__file__).parents[1] / 'data' / 'crest'
    for name in ('butanediol_gfnff_3.0.2_macos.out', 'cregen_ewin20_3.0.2_macos.out', 'cregen_ewin20.0_3.0.2_macos.out'):
        text = (data / name).read_text(encoding='utf-8')
        assert runner.finished_normally('crest', text, 0) and runner.crest_window_broken(text)
        problems = runner.diagnose('crest', text)
        assert problems and 'кроме самого низкого' in problems[0][0] and '2.12' in problems[0][1]
    good = (data / 'cregen_ewin20_2.12_macos.out').read_text(encoding='utf-8')
    assert 'conformer energy window  /kcal :  20.0000' in good and 'number of unique conformers for further calc            4' in good
    assert not runner.crest_window_broken(good) and not runner.diagnose('crest', good)
    assert not runner.crest_window_broken('') and not runner.crest_window_broken(None)


def test_output_progress_reads_only_what_was_added(tmp_path):
    # the window of the calculation counts the cycles and the stages over the whole output, reading only the
    # lines added since the last look; oracle — runner.progress and runner.milestones of the whole text at once
    out = tmp_path / 'job.out'
    spec = runner.JobSpec('orca', tmp_path, (), out, {})
    follower = runner.OutputProgress(spec)
    assert follower.update() == (0, None, []) and not follower.seen
    cycle = ('GEOMETRY OPTIMIZATION CYCLE 1\nSCF CONVERGED AFTER 9 CYCLES\n'
             'FINAL SINGLE POINT ENERGY      -76.30000000\n')
    out.write_text('BASIS SET INFORMATION\n' + cycle + 'FINAL SINGLE POINT ENER', encoding='utf-8')
    first = follower.update()
    assert first[0] == 1 and first[1] == -76.3  # the last line, not finished, waits
    with out.open('a', encoding='utf-8') as f:
        f.write('GY      -76.31000000\n' + cycle.replace('-76.3', '-76.4') * 2)
    whole = out.read_text(encoding='utf-8')
    cycles, energy, stages = follower.update()
    assert (cycles, energy) == runner.progress('orca', whole) == (3, -76.4)
    assert stages == runner.milestones('orca', whole)
    out.write_text(cycle, encoding='utf-8')  # written again, shorter: from the start
    assert follower.update()[0] == 1


def test_the_energy_of_a_tddft_spectrum_is_that_of_the_ground_state():
    # ORCA 6.0.1 prints after TD-DFT the total energy of root 1 as «FINAL SINGLE POINT ENERGY»: the progress of a
    # spectrum shows the SCF energy of the molecule, not that of its first excited state
    from pathlib import Path

    text = (Path(__file__).parents[1] / 'data' / 'orca601' / 'h2o_tddft.out').read_text(encoding='utf-8')
    assert runner.progress('orca', text) == (0, pytest.approx(-76.32101774231734, abs=1e-10))


def test_diagnose_of_a_neb_whose_initial_path_was_not_built():
    # ORCA 6.0.1, «Путь реакции (NEB-CI)» of HCN → HNC from two exactly linear structures (the real output, code 64 in
    # 2 s): the IDPP interpolation cannot take H through C. Before, the calculation failed without a word of why
    text = (Path(__file__).parents[1] / 'data' / 'orca601' / 'hcn_neb_idpp_failed.out').read_text(encoding='utf-8')
    found = runner.diagnose('orca', text, 64)
    assert len(found) == 1 and found[0][0] == 'ORCA не построил начальный путь реакции (NEB).'
    assert 'сквозь другой атом' in found[0][1]
    ok = (Path(__file__).parents[1] / 'data' / 'orca601' / 'h2o_opt.out').read_text(encoding='utf-8')
    assert runner.diagnose('orca', ok, 0) == []


def test_a_parallel_orca_that_stops_for_its_own_reason_is_not_an_mpi_failure():
    # ORCA 6.0.1 on 2 processes, the SCF limited to 4 iterations (the real output): it ends with «mpirun detected that
    # one or more processes exited with non-zero status» and «Calling Command: mpirun …», as every parallel ORCA that
    # stops does. The output was said to have two problems, the second «Сбой параллельного запуска (MPI)» with the
    # remedy «Повторить на одном процессе»
    data = Path(__file__).parents[1] / 'data'
    text = (data / 'orca601' / 'h2o_scf_maxiter4_parallel.out').read_text(encoding='utf-8')
    assert 'mpirun detected' in text and 'the SCF has not converged' in text
    assert [what for what, _ in runner.diagnose('orca', text, 0)] == ['Самосогласованное поле (SCF) не сошлось.']
    # an MPI failure alone is still one (the message of Open MPI when the processes do not start)
    alone = runner.diagnose('orca', 'An error occurred in MPI_Init\nOPAL ERROR: Unreachable\n', 1)
    assert [what for what, _ in alone] == ['Сбой параллельного запуска (MPI).']


def test_diagnose_of_nwchem_and_of_a_psi4_with_too_little_memory():
    # NWChem 7.3.0 (real outputs, tests/data/nwchem/README.md): the SCF limited to 2 iterations — «Calculation failed to
    # converge», code 255; MP2/def2-TZVP of benzene with 100 MB — «mp2_grad:insufficient resources», code 1. Neither
    # was recognised: NWChem had no messages in PROBLEMS. Psi4 1.11 asked for 200 MB stops with «set_memory():
    # Requested …; minimum 250 MiB» (the line of its stdout)
    import gzip

    data = Path(__file__).parents[1] / 'data' / 'nwchem'
    scf = gzip.decompress((data / 'water_scf_failed_nwchem-7.3.out.gz').read_bytes()).decode('utf-8')
    memory = gzip.decompress((data / 'benzene_mp2_100mb_nwchem-7.3.out.gz').read_bytes()).decode('utf-8')
    assert [what for what, _ in runner.diagnose('nwchem', scf, 255)] == ['Самосогласованное поле (SCF) не сошлось.']
    assert [what for what, _ in runner.diagnose('nwchem', memory, 1)] == ['Не хватило памяти.']
    cycles = gzip.decompress((data / 'glycine_opt_maxiter3_nwchem-7.3.out.gz').read_bytes()).decode('utf-8')
    assert [what for what, _ in runner.diagnose('nwchem', cycles, 255)] == ['Оптимизация геометрии не сошлась за отведённые циклы.']
    good = gzip.decompress((data / 'water_optfreq_b3lyp_d3bj_nwchem-7.3.out.gz').read_bytes()).decode('utf-8')
    assert runner.diagnose('nwchem', good, 0) == []
    psi4 = ('psi4.driver.p4util.exceptions.ValidationError: set_memory(): Requested 1.91e+02 MiB (2e+02 MB); minimum '
            '250 MiB (263 MB). Please, sir, I want some more.\n')
    assert [what for what, _ in runner.diagnose('psi4', psi4, 1)] == ['Не хватило памяти.']


def test_a_mopac_that_refused_the_geometry_did_not_finish_normally():
    # MOPAC 23.2.5, water with two hydrogens 0.15 Å apart (the real output): «GEOMETRY IN ERROR», nothing computed —
    # and «JOB ENDED NORMALLY» with code 0 at the end. The calculation was shown as done, with no energy and no word
    data = Path(__file__).parents[1] / 'data' / 'mopac'
    text = (data / 'h2o_atoms_too_close.out').read_text(encoding='utf-8')
    assert 'JOB ENDED NORMALLY' in text and not runner.finished_normally('mopac', text, 0)
    found = runner.diagnose('mopac', text, 0)
    assert [what for what, _ in found] == ['MOPAC не стал считать: два атома слишком близко друг к другу.']
    good = (data / 'c2h4_pm7_force.out').read_text(encoding='utf-8')
    assert runner.finished_normally('mopac', good, 0) and runner.diagnose('mopac', good, 0) == []
    # «Частоты и термохимия» of a geometry far from a minimum (water from SMILES, the gradient 16 > 10): MOPAC computes no
    # frequencies and still «ENDED NORMALLY» — the calculation was shown as done, without frequencies and a word
    refused = (data / 'h2o_force_gradient_too_large.out').read_text(encoding='utf-8')
    assert 'JOB ENDED NORMALLY' in refused and not runner.finished_normally('mopac', refused, 0)
    assert [what for what, _ in runner.diagnose('mopac', refused, 0)] == [
        'MOPAC не стал считать частоты: геометрия не оптимизирована.']
