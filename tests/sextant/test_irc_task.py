"""The task «Путь от переходного состояния (IRC)» of Sextant (azimuth/core.py irc_block, modules/sextant/inputs.py).

Oracles: the %irc keywords of the ORCA 6.0 manual (Direction, InitHess calc_anfreq / calc_numfreq, MaxIter) and the
input of the real run of ORCA 6.0.1 that went from the HCN ⇄ HNC transition state to both minima
(tests/data/orca601/irc_hcn: the same keywords); the refusals the module promises for the other programs.
"""

from math import dist
from pathlib import Path

import pytest

from azimuth.core import IRC_TASK, Calculation, orca_input, read_xyz
from modules.sextant import inputs, runner
from modules.spectrum.readers.orca_scan import read_scan, with_trajectory

RUN = Path(__file__).resolve().parents[1] / 'data' / 'orca601' / 'irc_hcn'

TS = read_xyz('3\nHCN TS\nC 0.011651 0.038583 0\nN 1.197696 -0.037722 0\nH 0.460653 1.149139 0')


def test_the_orca_input_goes_both_ways_from_the_transition_state():
    text = orca_input(TS, Calculation(task=IRC_TASK, cores=1))
    assert text.splitlines()[1] == '! B3LYP def2-SVP IRC TightSCF'
    assert '%irc\n  Direction both\n  InitHess calc_anfreq\n  MaxIter 100\nend\n' in text
    assert '%geom' not in text and 'Opt' not in text  # not an optimization: no constraints, no OptTS


def test_the_steps_and_the_hessian_are_the_settings_of_the_task():
    assert inputs.task_options('orca', IRC_TASK) == ('max_cycles', 'num_freq', 'guess')
    text = orca_input(TS, Calculation(task=IRC_TASK, max_cycles=30, num_freq=True, cores=1))
    assert '  InitHess calc_numfreq\n  MaxIter 30\n' in text
    assert 'MaxIter' not in orca_input(TS, Calculation(task=IRC_TASK, max_cycles=0, cores=1))  # ORCA's own limit
    # no analytic Hessian of the correlated methods in ORCA: numerically; HF has one
    assert 'calc_numfreq' in orca_input(TS, Calculation(task=IRC_TASK, method='MP2', basis='def2-SVP', cores=1))
    assert 'calc_anfreq' in orca_input(TS, Calculation(task=IRC_TASK, method='HF', basis='def2-SVP', cores=1))


def test_only_orca_is_offered_the_task():
    assert IRC_TASK in inputs.tasks_for('orca')
    for kind in ('gaussian', 'psi4', 'xtb', 'mopac', 'gamess', 'nwchem'):
        assert IRC_TASK not in inputs.tasks_for(kind), kind
        assert inputs.task_options(kind, IRC_TASK) == ()
    with pytest.raises(ValueError, match='IRC'):
        inputs.input_files('gaussian', TS, Calculation(task=IRC_TASK))


def test_an_orca_input_with_irc_is_read_back_as_the_task():
    text = orca_input(TS, Calculation(task=IRC_TASK, cores=1))
    assert inputs.read_settings('orca', text)['task'] == IRC_TASK


def test_the_real_run_is_read_as_a_path_through_the_transition_state():
    # ORCA 6.0.1, B3LYP-D3BJ/def2-SVP, MaxIter 40, from the OptTS geometry (one imaginary frequency, 1117i cm⁻¹).
    # Oracles: the rows of «IRC PATH SUMMARY» copied by hand; the C–H and N–H distances of the end frames, computed
    # here from the coordinates of the trajectory file and not by the reader.
    text = (RUN / 'hcn_irc.out').read_text(encoding='utf-8')
    scan = read_scan(text)
    assert scan.kind == 'irc' and len(scan.points) == 61
    assert scan.reference == 29 and scan.points[29].ts and scan.points[29].energy == -93.225730
    assert scan.points[0].energy == -93.301863 and scan.points[-1].energy == -93.280245
    scan = with_trajectory(scan, (RUN / 'hcn_irc_IRC_Full_trj.xyz').read_text(encoding='utf-8'))
    first, last = scan.points[0].geometry.atoms, scan.points[-1].geometry.atoms
    c_h = dist(*((a.x, a.y, a.z) for a in (first[0], first[2])))
    n_h = dist(*((a.x, a.y, a.z) for a in (last[1], last[2])))
    assert 1.0 < c_h < 1.15 and 0.95 < n_h < 1.05  # HCN at one end, HNC at the other
    stages = [key for key, _ in runner.milestones('orca', text)]
    assert 'irc' in stages and 'opt' not in stages
