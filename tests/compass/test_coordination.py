"""modules/compass/chemistry/coordination.py — the oracles are geometry itself (angles between ideal directions,
the sums of the radii of Cordero 2008 written out here) and the charges known for the complexes."""

import math

import numpy as np
import pytest

from modules.compass.chemistry import coordination as co

# Cordero et al. 2008, written out independently of the program's tables
CORDERO = {'Fe': 1.32, 'Pt': 1.36, 'Ni': 1.24, 'Co': 1.26, 'Cu': 1.32, 'Ru': 1.46, 'O': 0.66, 'N': 0.71, 'C': 0.76,
           'Cl': 1.02, 'P': 1.07}


def xyz(molecule):
    return np.array([[a.x, a.y, a.z] for a in molecule.atoms])


def donors(built):
    return [j for i, j, _ in built.molecule.bonds if i == 0]


def angles(built):
    p = xyz(built.molecule)
    found = []
    d = donors(built)
    for a in range(len(d)):
        for b in range(a + 1, len(d)):
            u, v = p[d[a]] - p[0], p[d[b]] - p[0]
            found.append(round(math.degrees(math.acos(np.clip(u @ v / np.linalg.norm(u) / np.linalg.norm(v), -1, 1))), 2))
    return sorted(found)


@pytest.mark.parametrize('geometry, expected', [
    ('linear', [180.0]),
    ('trigonal', [120.0] * 3),
    ('tetrahedral', [109.47] * 6),
    ('square', [90.0] * 4 + [180.0] * 2),
    ('bipyramid', [90.0] * 6 + [120.0] * 3 + [180.0]),
    ('pyramid', [90.0] * 8 + [180.0] * 2),
    ('octahedral', [90.0] * 12 + [180.0] * 3),
    ('pentagonal', [72.0] * 5 + [90.0] * 10 + [144.0] * 5 + [180.0]),
])
def test_angles_between_donors(geometry, expected):
    built = co.build('Fe', geometry, 'F')
    assert angles(built) == expected


def test_distances_are_sums_of_radii():
    for metal, ligand, donor in (('Fe', 'H2O', 'O'), ('Pt', 'Cl', 'Cl'), ('Ni', 'CO', 'C'), ('Ru', 'NH3', 'N'),
                                 ('Ni', 'PH3', 'P')):
        built = co.build(metal, 'tetrahedral', ligand)
        p = xyz(built.molecule)
        for j in donors(built):
            assert built.molecule.atoms[j].symbol == donor
            assert np.linalg.norm(p[j] - p[0]) == pytest.approx(CORDERO[metal] + CORDERO[donor], abs=1e-9)


def test_ligands_keep_their_shape():
    built = co.build('Fe', 'octahedral', 'H2O', oxidation=2)
    p = xyz(built.molecule)
    for o in donors(built):
        hs = [j for i, j, _ in built.molecule.bonds if i == o]
        assert len(hs) == 2
        for h in hs:
            assert np.linalg.norm(p[h] - p[o]) == pytest.approx(0.958, abs=1e-9)
        u, v = p[hs[0]] - p[o], p[hs[1]] - p[o]
        assert math.degrees(math.acos(u @ v / np.linalg.norm(u) / np.linalg.norm(v))) == pytest.approx(104.5, abs=1e-6)
    assert built.clashes == ()
    ni = co.build('Ni', 'tetrahedral', 'CO')
    p = xyz(ni.molecule)
    for c in donors(ni):  # linear M–C–O
        o = [j for i, j, order in ni.molecule.bonds if i == c][0]
        assert np.cross(p[c] - p[0], p[o] - p[c]) == pytest.approx(np.zeros(3), abs=1e-9)
        assert (3 in [order for i, j, order in ni.molecule.bonds if i == c])


def test_charges_and_formulas():
    assert co.build('Fe', 'octahedral', 'H2O', 2).charge == 2
    platinum = co.build('Pt', 'square', 'Cl', 2)
    assert platinum.charge == -2 and platinum.molecule.formula == 'Cl4Pt'
    assert co.build('Ni', 'tetrahedral', 'CO', 0).charge == 0
    assert co.build('Fe', 'octahedral', 'CN', 3).charge == -3
    cobalt = co.build('Co', 'octahedral', '5 NH3, Cl', 3)
    assert cobalt.charge == 2 and cobalt.molecule.formula == 'ClCoH15N5'
    assert cobalt.molecule.title == '[Co(NH3)5Cl]'


def test_parse_and_refusals():
    assert co.parse_ligands('cl, Cl, nh3,NH3', 4) == ['Cl', 'Cl', 'NH3', 'NH3']
    assert co.parse_ligands('h2o', 3) == ['H2O'] * 3
    with pytest.raises(ValueError):
        co.parse_ligands('Cl, Cl', 4)
    with pytest.raises(ValueError):
        co.parse_ligands('Xy', 4)
    with pytest.raises(ValueError):
        co.build('Fe', 'cube', 'Cl')
    with pytest.raises(ValueError):
        co.build('Og', 'octahedral', 'Cl')


def test_crowding_reported():
    built = co.build('Ni', 'pentagonal', 'PH3')  # seven PH3 on a small Ni: the H of neighbours meet
    assert built.clashes
    assert {(built.molecule.atoms[i].symbol, built.molecule.atoms[j].symbol) for i, j, _ in built.clashes} == {('H', 'H')}
    for i, j, distance in built.clashes:
        assert distance < 0.7 * (1.20 + 1.20)  # Bondi H
    for metal, geometry, ligand in (('Fe', 'octahedral', 'H2O'), ('Co', 'octahedral', 'NH3'), ('Pt', 'square', 'Cl'),
                                    ('Fe', 'octahedral', 'PH3'), ('Fe', 'bipyramid', 'CO')):
        assert co.build(metal, geometry, ligand).clashes == ()  # real complexes are not called crowded
