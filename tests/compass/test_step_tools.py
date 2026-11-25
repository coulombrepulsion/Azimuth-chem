"""The steps of a calculation and its modes as data (modules/compass/chemistry/step_tools.py)."""

from types import SimpleNamespace

import pytest

from azimuth.core import read_xyz
from modules.compass.chemistry import step_tools


def water(r):
    return read_xyz(f'3\n\nO 0 0 0\nH {r} 0 0\nH -0.24 0.93 0')


STEPS = [SimpleNamespace(cycle=k + 1, energy=e, geometry=water(r))
         for k, (r, e) in enumerate(((1.10, -5.0), (1.00, -5.02), (0.96, -5.03)))] + \
        [SimpleNamespace(cycle=4, energy=None, geometry=None)]


def test_steps_as_one_xyz_and_a_table():
    text = step_tools.steps_xyz(STEPS)
    assert text.count('\n3\n') + text.startswith('3\n') == 3  # three frames, the step without a geometry left out
    assert 'шаг 2 · E = -5.0200000000 Eh' in text
    from modules.compass.chemistry.formats import read_xyz_frames

    assert [round(f.atoms[1].position[0], 2) for f in read_xyz_frames(text)] == [1.10, 1.00, 0.96]
    rows = step_tools.coordinate_rows(STEPS)
    assert len(rows) == 9 and rows[3] == (2, 1, 'O', 0.0, 0.0, 0.0) and rows[4][3] == 1.0


def test_a_parameter_along_the_steps():
    assert [(n, round(v, 6)) for n, v, _ in step_tools.parameter_series(STEPS, (0, 1))] == [(1, 1.1), (2, 1.0), (3, 0.96)]
    angles = step_tools.parameter_series(STEPS, (1, 0, 2))
    assert all(90 < v < 110 for _, v, _ in angles) and angles[0][2] == -5.0
    with pytest.raises(ValueError):
        step_tools.parameter_series(STEPS, (0,))
    with pytest.raises(ValueError):
        step_tools.parameter_series(STEPS[3:], (0, 1))  # no geometry at all


def test_the_angle_of_two_guides_along_the_steps():
    plane = {'kind': 'plane', 'atoms': (0, 1, 2)}
    vector = {'kind': 'vector', 'atoms': (0, 1)}
    assert [round(a, 9) for _, a, _ in step_tools.guide_series(STEPS, plane, vector)] == [0.0, 0.0, 0.0]


def test_the_modes_the_selected_atoms_move_in():
    stretch = SimpleNamespace(index=7, frequency=3700.0, vectors=((0, 0, 0), (0.7, 0, 0), (0, 0, 0)))
    bend = SimpleNamespace(index=6, frequency=1600.0, vectors=((0.1, 0, 0), (0.3, 0.3, 0), (0.3, -0.3, 0)))
    empty = SimpleNamespace(index=1, frequency=0.0, vectors=())
    found = step_tools.involvement([bend, stretch, empty], [1])
    assert [i for i, _, _ in found] == [7, 6] and found[0][2] == 1.0
    assert found[1][2] == pytest.approx(0.18 / (0.01 + 0.18 + 0.18))
