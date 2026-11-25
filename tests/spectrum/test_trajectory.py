from pathlib import Path
from modules.spectrum.readers.orca import read_output

BLOCK = 'CARTESIAN COORDINATES (ANGSTROEM)\n-----\nO 0 0 0\nH 1 0 0\nH 0 1 0\n\n'


def cycle(n, energy='-75.0', coords=BLOCK):
    return f'GEOMETRY OPTIMIZATION CYCLE {n}\n' + coords + (f'FINAL SINGLE POINT ENERGY {energy}\n' if energy else '')


def test_no_invented_trajectory_from_unlabelled_energies():
    assert not read_output('ORCA\n' + BLOCK + 'FINAL SINGLE POINT ENERGY -75\nFINAL SINGLE POINT ENERGY -76').steps


def test_missing_energy_does_not_shift_geometries():
    result = read_output(cycle(1) + cycle(2, None) + cycle(3, '-76'))
    assert [s.energy for s in result.steps] == [-75, None, -76]
    assert all(s.geometry is not None for s in result.steps)


def test_final_frequency_energy_not_assigned_to_optimization():
    result = read_output(cycle(1) + 'THE OPTIMIZATION HAS CONVERGED\n' + BLOCK + 'FINAL SINGLE POINT ENERGY -99')
    assert result.steps[0].energy == -75
    assert result.energies == (-75, -99)


def test_missing_geometry_not_carried_forward():
    result = read_output(cycle(1) + cycle(2, '-76', coords=''))
    assert result.steps[1].geometry is None
    assert result.steps[1].energy == -76


def test_truncated_geometry_not_displayed_as_complete():
    result = read_output(cycle(1) + cycle(2, None, coords=BLOCK.replace('H 0 1 0', 'H 0 1')))
    assert result.steps[1].geometry is None


def test_atom_count_change_rejected_for_step():
    result = read_output(cycle(1) + cycle(2, coords=BLOCK.replace('H 0 1 0\n', '')))
    assert result.steps[1].geometry is None


def test_ambiguous_multiple_energies_are_not_guessed():
    result = read_output(cycle(1) + 'FINAL SINGLE POINT ENERGY -76\n')
    assert result.steps[0].energy is None


def test_fortran_energy_and_nonsequential_cycle_numbers():
    result = read_output(cycle(4, '-7.5D+01') + cycle(7, '-7.6D+01'))
    assert [(s.cycle, s.energy) for s in result.steps] == [(4, -75), (7, -76)]


def test_demo_trajectory():
    result = read_output((Path(__file__).parents[2] / 'examples/optimization-demo.out').read_text())
    assert result.demo and len(result.steps) == 5
    assert result.steps[0].geometry.atoms[1].x == 1.02
    assert result.steps[-1].geometry.atoms[1].x == 0.7586
