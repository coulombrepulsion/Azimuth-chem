"""The doctor of a calculation (modules/sextant/doctor.py) — the remedy for each problem and its limits.

Oracles: the messages the programs print for these failures (the same lines tests/sextant/test_runner.py checks for
runner.diagnose); the rules of doctor §2; the last step of the real optimization tests/data/orca601/h2o_opt.out, read
by the reader of Spectrum.
"""

from pathlib import Path

from azimuth.core import Calculation, read_xyz
from modules.sextant import doctor, runner

DATA = Path(__file__).parents[1] / 'data'
WATER = read_xyz('3\nwater\nO 0 0 0.117\nH 0.757 0 -0.469\nH -0.757 0 -0.469')
SCF = '  SCF NOT CONVERGED AFTER 125 CYCLES\n'
OPT = ('The optimization has not yet converged - more geometry cycles are needed\n'
       '   The optimization did not converge but reached the maximum number of\n   optimization cycles.\n')


def one(kind, text, calc, code=1, **more):
    (remedy,) = doctor.examine(kind, text, code, calc, **more)
    return remedy


def test_scf_gets_harder_convergence_twice_then_advice_only():
    calc = Calculation()
    first = one('orca', SCF, calc)
    assert first.key == doctor.SCF and first.changes == {'slow_conv': 'SlowConv'} and 'трудной' in first.label
    again = one('orca', SCF, doctor.apply(calc, first))
    assert again.changes == {'slow_conv': 'VerySlowConv'}
    last = one('orca', SCF, doctor.apply(doctor.apply(calc, first), again))
    assert last.label == '' and last.changes == {} and last.why  # the advice stays
    # xtb has no such setting: advice only
    assert one('xtb', 'Self consistent charge iterator did not converge', calc).label == ''


def test_an_optimization_goes_on_from_its_last_geometry_with_twice_the_cycles():
    remedy = one('orca', OPT, Calculation(max_cycles=100), code=0)
    assert remedy.key == doctor.OPT and remedy.last_geometry and remedy.changes == {'max_cycles': 200}
    assert one('orca', OPT, Calculation(max_cycles=300), code=0).changes == {'max_cycles': 600}
    assert one('orca', OPT, Calculation(max_cycles=20), code=0).changes == {'max_cycles': 200}  # at least 200
    free = one('orca', OPT, Calculation(max_cycles=0), code=0)  # the program's own limit stays
    assert free.changes == {'max_cycles': 0} and free.last_geometry
    assert doctor.apply(Calculation(max_cycles=100), remedy).max_cycles == 200


def test_memory_halves_the_processes_and_doubles_the_memory_of_each():
    text = 'Error (ORCA_SCF): Not enough memory available!\nPlease increase MaxCore'
    remedy = one('orca', text, Calculation(cores=8, memory_mb=1000))
    assert remedy.changes == {'cores': 4, 'memory_mb': 2000}  # the same total, more for each
    assert one('orca', text, Calculation(cores=1, memory_mb=1000)).changes == {'cores': 1, 'memory_mb': 2000}
    killed = one('orca', 'cut', Calculation(cores=4, memory_mb=1500), code=137)  # killed by the system
    assert killed.key == runner.KILLED and killed.changes == {'cores': 2, 'memory_mb': 3000}


def test_the_other_remedies_and_their_limits():
    calc = Calculation(cores=4)
    assert one('orca', 'mpirun was unable to launch\nORTE', calc).changes == {'cores': 1}  # 4 → 1; more than 16 → 16
    assert one('orca', 'mpirun was unable to launch', Calculation(cores=1)).label == ''
    typo = 'UNRECOGNIZED OR DUPLICATED KEYWORD(S) IN SIMPLE INPUT LINE\n  FOO'
    assert one('orca', typo, calc).label == ''  # not edited by hand: nothing to rebuild
    assert one('orca', typo, calc, edited=True).rebuild_input
    basis = 'There are no basis functions on atom 3'
    assert one('orca', basis, Calculation(basis='6-31G(d)')).changes == {'basis': 'def2-SVP'}
    assert one('orca', basis, Calculation(basis='def2-SVP')).label == ''
    meta = 'Meta-GGA functionals can only be used in combination with the excited-state gradient'
    assert one('orca', meta, Calculation(method='TPSSh')).changes == {'method': 'PBE0'}
    assert one('orca', 'No space left on device', calc).label == ''  # nothing the doctor can do
    assert doctor.examine('orca', 'ORCA TERMINATED NORMALLY', 0, calc) == []


def test_an_impossible_multiplicity_becomes_the_lowest_possible():
    text = 'Error: multiplicity (2) is impossible for 10 electrons'
    remedy = one('orca', text, Calculation(charge=0, multiplicity=2), molecule=WATER)  # 10 electrons
    assert remedy.key == doctor.STATE and remedy.changes == {'multiplicity': 1}
    cation = one('orca', text, Calculation(charge=1, multiplicity=1), molecule=WATER)  # 9 electrons
    assert cation.changes == {'multiplicity': 2}
    assert one('orca', text, Calculation(charge=0, multiplicity=3), molecule=WATER).label == ''  # the parity is right
    assert one('orca', text, Calculation(multiplicity=2)).label == ''  # no molecule: not guessed


def test_the_last_geometry_is_the_last_step_of_the_output():
    path = DATA / 'orca601' / 'h2o_opt.out'
    text = path.read_text(encoding='utf-8', errors='replace')
    from modules.spectrum.readers.outputs import read_any

    steps = read_any(text, str(path)).steps
    last = doctor.last_geometry(text, str(path))
    assert last is not None and [a.position for a in last.atoms] == [a.position for a in steps[-1].geometry.atoms]
    assert doctor.last_geometry('not an output') is None


def test_an_imaginary_frequency_of_a_minimum_is_moved_along_its_mode():
    # an optimization with frequencies that ended on a saddle (the bending mode of water made imaginary in
    # its real output of ORCA 6.0.1) — «Сдвинуть по мнимой моде и оптимизировать заново»: the geometry moved along
    # that mode, the atom that moves most by NUDGE Å, the optimization tight; not for a transition state
    import re
    from pathlib import Path

    from azimuth.core import Calculation
    from modules.spectrum.readers.outputs import read_any

    text = (Path(__file__).parents[1] / 'data' / 'orca601' / 'h2o_optfreq.out').read_text(encoding='utf-8')
    found = re.search(r'^\s*6:\s*(\d+\.\d+)\s*cm\*\*-1', text, re.M)
    saddle = text[:found.start(1)] + '-' + text[found.start(1):]
    calc = Calculation(task='Оптимизация + частоты')
    remedy = doctor.imaginary('orca', saddle, calc)
    assert remedy is not None and remedy.displace and remedy.changes == {'task': 'Оптимизация + частоты', 'opt_conv': 'tight'}
    assert doctor.imaginary('orca', text, calc) is None  # a minimum: nothing
    # −12 cm⁻¹ — a nearly free rotor or noise: practically a minimum, the same remedy offered with that said
    small = text[:found.start(1)] + '-12.00' + text[found.end(1):]
    gentle = doctor.imaginary('orca', small, calc)
    assert gentle.key == doctor.SMALL_IMAGINARY and gentle.changes == remedy.changes
    assert remedy.key == doctor.IMAGINARY and 'практически минимум' in gentle.why
    assert doctor.imaginary('orca', saddle, Calculation(task='Оптимизация + частоты', ts=True)) is None
    moved = doctor.displaced(saddle)
    output = read_any(saddle)
    base = output.vibration_geometry or output.geometry
    shifts = [((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2) ** 0.5 for a, b in zip(moved.atoms, base.atoms)]
    assert abs(max(shifts) - doctor.NUDGE) < 1e-9 and [a.symbol for a in moved.atoms] == [a.symbol for a in base.atoms]


def test_a_stopped_optimization_goes_on_from_its_last_geometry():
    from azimuth.core import Calculation

    remedy = doctor.stopped(Calculation(task='Оптимизация'))
    assert remedy.last_geometry and remedy.label == 'Продолжить с последней геометрии' and remedy.changes == {}
    assert doctor.stopped(Calculation(task='Энергия')) is None


def test_mpi_broken_in_the_middle_of_an_optimization_is_not_a_lack_of_cycles():
    # ORCA prints «has not yet converged» after every
    # cycle; a run of 41 processes on serv3 broke in MPI_Init of orca_propint_mpi in the middle of the optimization
    broken = ('The optimization has not yet converged - more geometry cycles are needed\n' * 3
              + '[serv3:3261577] OPAL ERROR: Unreachable in file ext3x_client.c at line 112\n'
              '*** An error occurred in MPI_Init\n*** on a NULL communicator\n'
              '*** MPI_ERRORS_ARE_FATAL (processes in this communicator will now abort,\n'
              'ORCA finished by error termination in PROPINT\n'
              'Calling Command: mpirun -np 41  /opt/orca6.1.1/orca_propint_mpi x.property.txt x\n')
    keys = [k for k, _ in runner.problem_keys('orca', broken, 1)]
    assert keys == [doctor.MPI]
    calc = Calculation(cores=41, task='Оптимизация + частоты')
    remedy = one('orca', broken, calc)
    assert remedy.changes == {'cores': 16} and remedy.last_geometry and '16' in remedy.label
    assert one('orca', broken, Calculation(cores=8, task='Энергия')).changes == {'cores': 1}
    # the cycles ran out only when ORCA ended normally after them, or said so
    ran_out = 'The optimization has not yet converged - more geometry cycles are needed\n****ORCA TERMINATED NORMALLY****'
    assert [k for k, _ in runner.problem_keys('orca', ran_out, 0)] == [doctor.OPT]
    assert [k for k, _ in runner.problem_keys('orca', OPT, 1)] == [doctor.OPT]
