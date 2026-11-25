"""Point group, symmetrisation and standard orientation in Compass (modules/compass/chemistry/symmetry.py)."""

import random
from math import dist

import pytest

from azimuth.core import Atom, EXAMPLES, Molecule, read_xyz
from modules.compass.chemistry.symmetry import analyze, group_html


@pytest.mark.parametrize(
    'key,group',
    [
        ('Вода · H₂O', 'C2v'),
        ('Аммиак · NH₃', 'C3v'),
        ('Метан · CH₄', 'Td'),
        ('Этан · C₂H₆ · перемещение фрагмента', 'D3d'),
    ],
)
def test_examples(key, group):
    assert analyze(read_xyz(EXAMPLES[key]))['name'] == group


def test_noisy_methane_is_symmetrised_in_place_without_scaling():
    random.seed(1)
    m = read_xyz(EXAMPLES['Метан · CH₄'])
    noisy = Molecule(
        'x', tuple(Atom(a.symbol, *[c + random.uniform(-0.03, 0.03) for c in a.position]) for a in m.atoms)
    )
    r = analyze(noisy)
    assert r['name'] == 'Td' and r['rmsd'] < 0.1
    sym = r['in_place'].atoms
    ch = [dist(sym[0].position, a.position) for a in sym[1:]]
    assert max(ch) - min(ch) < 1e-9  # four equal C–H
    assert abs(ch[0] - dist(m.atoms[0].position, m.atoms[1].position)) < 0.05  # lengths kept, not scaled to 1
    assert all(dist(a.position, b.position) < 0.1 for a, b in zip(sym, noisy.atoms))  # stays where it was


def test_standard_orientation_of_water():
    w = read_xyz(EXAMPLES['Вода · H₂O'])
    std = analyze(w)['standard'].atoms
    assert abs(std[0].x) < 1e-9 and abs(std[0].y) < 1e-9  # O on the C2 axis (z)
    assert abs(std[1].z - std[2].z) < 1e-9 and abs(std[1].x + std[2].x) + abs(std[1].y + std[2].y) < 1e-9


def test_linear_and_errors():
    co2 = Molecule('c', (Atom('O', -1.16, 0.02, 0), Atom('C', 0, 0, 0), Atom('O', 1.16, -0.01, 0.01)))
    r = analyze(co2)
    assert r['name'] == 'D∞h' and abs(dist(*(a.position for a in r['standard'].atoms[::2])) - 2.32) < 0.01
    assert analyze(Molecule('n', (Atom('Ne', 0, 0, 0),)))['err'] == 'one_atom'
    assert group_html('C2v') == 'C<sub>2v</sub>' and group_html('D∞h') == 'D<sub>∞h</sub>'


@pytest.mark.parametrize('smiles, group', [('N', 'C3v'), ('CC', 'D3d'), ('C', 'Td'), ('c1ccccc1', 'D6h'), ('O', 'C2v')])
def test_no_group_higher_than_the_atoms_allow(smiles, group):
    # at a loose tolerance the nearest-atom mapping let impossible groups through (NH3 C4v, ethane C8v,
    # toluene D2h or D8h): now every operation must permute the atoms and none may sit on another
    from modules.compass.chemistry.formats import from_smiles

    m = from_smiles(smiles)
    for tol in (0.05, 0.1, 0.2, 0.3):
        assert analyze(m, tol)['name'] == group
    assert analyze(from_smiles('Cc1ccccc1'), 0.3)['name'] in ('C1', 'Cs', 'C2v')


def test_point_group_of_one_molecule_only():
    # two separate molecules — no point group, the reason is said; a dummy atom X is not one
    water = (Atom('O', 0, 0, 0.117), Atom('H', 0.757, 0, -0.469), Atom('H', -0.757, 0, -0.469))
    dimer = Molecule('d', water + tuple(Atom(a.symbol, a.x + 3.0, a.y, a.z) for a in water))
    assert analyze(dimer) == {'err': 'several', 'count': 2}
    assert analyze(Molecule('w', water + (Atom('X', 0, 0, -1.0),)))['name'] == 'C2v'


def test_the_point_group_is_remembered_for_the_same_atoms():
    # Spectrum asks for σ at every choice of a molecule with frequencies: the same atoms are not analysed again, and
    # the molecules returned are those of the caller (its title), not of the first one asked
    from dataclasses import replace

    from azimuth.core import Atom, Molecule
    from modules.compass.chemistry import symmetry

    water = Molecule('first', (Atom('O', 0.0, 0.0, 0.117), Atom('H', 0.0, 0.757, -0.467), Atom('H', 0.0, -0.757, -0.467)))
    symmetry._CACHE.clear()
    first = symmetry.analyze(water)
    calls = []
    real = symmetry._analyze
    symmetry._analyze = lambda *a, **k: calls.append(a) or real(*a, **k)
    try:
        again = symmetry.analyze(replace(water, title='second'))
    finally:
        symmetry._analyze = real
    assert calls == [] and again['name'] == first['name'] == 'C2v'
    assert again['standard'].title == 'second' and again['standard'].atoms == first['standard'].atoms
    assert symmetry.analyze(water, 0.2)['name'] == 'C2v' and len(symmetry._CACHE) == 2  # another tolerance
