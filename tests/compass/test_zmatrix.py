"""Z-matrix, ORCA / Gaussian internal coordinates and optimization constraints."""

import itertools
from math import dist, radians, sin

import pytest

from azimuth.core import (
    Calculation,
    EXAMPLES,
    orca_input,
    project_constraints,
    project_text,
    read_project,
    read_xyz,
    validate_constraints,
)
from modules.compass.chemistry import zmatrix
from modules.compass.chemistry.formats import from_smiles, read_gaussian_input, read_orca_input


def same_shape(a, b):
    n = len(a.atoms)
    return max(
        abs(dist(a.atoms[i].position, a.atoms[j].position) - dist(b.atoms[i].position, b.atoms[j].position))
        for i, j in itertools.combinations(range(n), 2)
    )


@pytest.mark.parametrize(
    'molecule',
    [
        read_xyz(EXAMPLES['Вода · H₂O']),
        read_xyz(EXAMPLES['Метан · CH₄']),
        read_xyz(EXAMPLES['Этан · C₂H₆ · перемещение фрагмента']),
    ],
)
def test_round_trip(molecule):
    rows = zmatrix.build(molecule)
    assert same_shape(molecule, zmatrix.to_cartesian(rows)) < 1e-9
    assert same_shape(molecule, zmatrix.to_cartesian(zmatrix.parse(zmatrix.text(rows).splitlines()))) < 1e-5


def test_ring_and_references_are_earlier_and_bonded():
    m = from_smiles('c1ccccc1')
    rows = zmatrix.build(m)
    assert all(r[1] is None or r[1] < k for k, r in enumerate(rows))
    assert same_shape(m, zmatrix.to_cartesian(rows)) < 1e-9


def test_variables_gaussian_and_orca():
    rows = zmatrix.parse(['O', 'H 1 r1', 'H 1 r1 2 a1', '', 'r1=0.96', 'a1 104.5'])
    w = zmatrix.to_cartesian(rows)
    assert dist(w.atoms[1].position, w.atoms[2].position) == pytest.approx(2 * 0.96 * sin(radians(52.25)), abs=1e-6)
    g, q, m = read_gaussian_input('#p hf\n\nz\n\n0 1\nO\nH 1 r\nH 1 r 2 a\n\nr=0.96\na=104.5\n\n')
    assert same_shape(g, w) < 1e-6 and (q, m) == (0, 1)
    for block in (
        '* gzmt 0 1\nO\nH 1 0.96\nH 1 0.96 2 104.5\n*\n',
        '* int 0 1\nO 0 0 0 0 0 0\nH 1 0 0 0.96 0 0\nH 1 2 0 0.96 104.5 0\n*\n',
    ):
        assert same_shape(read_orca_input('! HF\n' + block)[0], w) < 1e-6
    with pytest.raises(ValueError):
        zmatrix.parse(['O', 'H 1 r9'])


def test_constraints_in_input_and_project():
    w = read_xyz(EXAMPLES['Вода · H₂O'])
    fixed = [('C', (0,)), ('B', (0, 1)), ('A', (1, 0, 2))]
    text = orca_input(w, Calculation(), fixed)
    assert '%geom\n  Constraints\n    { C 0 C }\n    { B 0 1 C }\n    { A 1 0 2 C }\n  end\n  MaxIter 100\nend\n' in text
    assert '%geom' not in orca_input(w, Calculation(task='Энергия'), fixed)
    assert orca_input(w, Calculation()) == orca_input(w, Calculation(), ())
    saved = project_text(w, Calculation(), fixed)
    assert project_constraints(saved) == tuple(fixed) and read_project(saved)[0] == w
    assert project_constraints(project_text(w, Calculation())) == ()
    with pytest.raises(ValueError):
        validate_constraints([('B', (0, 7))], 3)
