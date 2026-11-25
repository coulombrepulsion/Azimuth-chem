"""The starting structures of the SMILES builder of Compass (modules/compass/chemistry/formats.from_smiles with the
force field of modules/compass/chemistry/cleanup.py) have the symmetry of the molecule: hypervalent atoms, allene,
fused rings, conjugated single bonds, biaryls."""

from itertools import combinations
from math import acos, degrees, dist

import pytest

from modules.compass.chemistry.formats import from_smiles
from modules.compass.chemistry.symmetry import analyze

CASES = [
    ('FS(F)(F)(F)(F)F', 'Oh'),  # SF6 (was D3 with angles of 75–152°)
    ('FP(F)(F)(F)F', 'D3h'),  # PF5 (was C4v)
    ('F[Xe](F)(F)F', 'D4h'),  # XeF4, square
    ('F[Xe]F', 'D∞h'),  # XeF2, linear
    ('FBr(F)(F)(F)F', 'C4v'),  # BrF5, square pyramid
    ('C=C=C', 'D2d'),  # allene: the CH2 planes perpendicular (was flat D2h)
    ('c1ccc2ccccc2c1', 'D2h'),  # naphthalene (a hydrogen was left inside a ring: Cs, bonds 1.38–1.46 Å)
    ('CC(=O)c1ccccc1', 'Cs'),  # acetophenone: the C=O in the plane of the ring (was C1)
    ('CCOC(C)=O', 'Cs'),  # ethyl acetate (was C1)
    ('O=CC=O', 'C2h'),  # glyoxal, s-trans
    ('c1ccc(cc1)-c1ccccc1', 'D2'),  # biphenyl: the rings turned against each other, not flat
    ('Cc1ccccc1', 'Cs'),  # toluene (was C1)
    ('OO', 'C2'),  # H2O2: the O–H bonds turned ~90° (was flat trans, C2h — a saddle xtb did not leave)
    ('CSSC', 'C2'),  # dimethyl disulfide
    ('C1CC12CC2', 'D2d'),  # spiropentane: the rings perpendicular (was C2v, twisted to 96° and 125°)
    ('Cl/C=C/Cl', 'C2h'),  # trans-1,2-dichloroethene: «/» and «\\» were not read at all
    ('Cl/C=C\\Cl', 'C2v'),  # cis
    ('C/C=C\\C', 'C2v'),  # cis-2-butene
]


@pytest.mark.parametrize('smiles, group', CASES)
def test_builder_gives_the_symmetry(smiles, group):
    assert analyze(from_smiles(smiles), 0.02)['name'] == group


def _angles(m, centre):
    ns = [j if i == centre else i for i, j, _ in m.bonds if centre in (i, j)]
    out = []
    for a, b in combinations(ns, 2):
        u = [m.atoms[a].position[k] - m.atoms[centre].position[k] for k in range(3)]
        v = [m.atoms[b].position[k] - m.atoms[centre].position[k] for k in range(3)]
        c = sum(x * y for x, y in zip(u, v)) / (dist(u, [0] * 3) * dist(v, [0] * 3))
        out.append(round(degrees(acos(max(-1.0, min(1.0, c))))))
    return sorted(out)


def test_octahedral_and_bipyramidal_angles():
    sf6 = from_smiles('FS(F)(F)(F)(F)F')
    s = next(k for k, a in enumerate(sf6.atoms) if a.symbol == 'S')
    assert _angles(sf6, s) == [90] * 12 + [180] * 3
    pf5 = from_smiles('FP(F)(F)(F)F')
    p = next(k for k, a in enumerate(pf5.atoms) if a.symbol == 'P')
    assert _angles(pf5, p) == [90] * 6 + [120] * 3 + [180]


def test_naphthalene_bonds_are_even():
    m = from_smiles('c1ccc2ccccc2c1')
    cc = [dist(m.atoms[i].position, m.atoms[j].position) for i, j, _ in m.bonds if m.atoms[i].symbol == m.atoms[j].symbol == 'C']
    assert max(cc) - min(cc) < 0.01


@pytest.mark.parametrize('smiles', ['CCC(CC(=O)OC)CC', 'CC(C)CCC(CC)C(C)C', 'OC1CCCC1', 'Oc1ccccc1O'])
def test_lbfgs_reaches_the_minimum_of_fire(smiles):
    # the build from SMILES tidies by L-BFGS; oracle — FIRE (the tidying) to the same force
    # from the same start, the energy of L-BFGS is not higher
    from modules.compass.chemistry.cleanup import clean

    start = from_smiles(smiles)
    _, fire_steps, fire = clean(start, steps=20000)
    _, lbfgs_steps, lbfgs = clean(start, steps=20000, method='lbfgs')
    assert lbfgs <= fire + 1e-3
    assert lbfgs_steps < fire_steps


def test_hydrogen_caught_in_a_ring_is_seen():
    # the second tidying with the hydrogens put again runs only for a hydrogen caught near another atom
    from azimuth.core import Atom, Molecule
    from modules.compass.chemistry.formats_smiles import _hydrogen_inside

    free = Molecule('', (Atom('C', 0, 0, 0), Atom('H', 1.09, 0, 0), Atom('C', -1.5, 0, 0)), ((0, 1, 1), (0, 2, 1)))
    caught = Molecule('', (Atom('C', 0, 0, 0), Atom('H', 1.09, 0, 0), Atom('C', 2.2, 0, 0)), ((0, 1, 1), (0, 2, 1)))
    assert not _hydrogen_inside(free) and _hydrogen_inside(caught)


def test_the_methyl_next_to_a_carbonyl_eclipses_it():
    # acetaldehyde, acetone: one H of the methyl syn to C=O (O=C–C–H 0°) — the minimum; anti (180°) was a saddle that
    # xtb and MOPAC kept (an imaginary frequency on the first calculation of a student, 2026-11-21)
    from math import degrees

    import numpy as np

    from modules.compass.chemistry.cleanup import dihedrals

    m = from_smiles('CC=O')
    x = np.array([a.position for a in m.atoms])
    h = [j for i, j, _ in m.bonds if i == 0 and m.atoms[j].symbol == 'H']
    angles = sorted(abs(round(degrees(float(dihedrals(x, *[np.array([q]) for q in (2, 1, 0, k)])[0][0])))) for k in h)
    assert angles == [0, 120, 120]


def test_the_cis_and_trans_of_smiles():
    from modules.compass.chemistry.names import double_bond_stereo, smiles_graph

    for text, kind in (('F/C=C/F', 'trans'), ('F/C=C\\F', 'cis'), ('C(/F)=C/F', 'cis'), ('F\\C=C\\F', 'trans')):
        directed = []
        _, bonds, orders = smiles_graph(text, strict=True, directed=directed)
        assert [s[-1] for s in double_bond_stereo(bonds, orders, directed)] == [kind], text
