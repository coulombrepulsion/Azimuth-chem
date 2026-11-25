"""Torsions of the simple force field, anti chains, tidying while building (modules/compass/chemistry/cleanup.py)."""

import numpy as np
import pytest

from azimuth.core import Atom, Molecule
from modules.compass.chemistry.builder import place_atom, place_fragment
from modules.compass.chemistry import library
from modules.compass.chemistry.cleanup import clean, dihedrals, energy_and_gradient, straighten, terms, tidy_new


def xyz(m):
    return np.array([a.position for a in m.atoms], dtype=float)


def dihedral(m, *q):
    return abs(float(np.degrees(dihedrals(xyz(m), *[np.array([i]) for i in q])[0][0])))


def angle(m, a, b, c):
    x = xyz(m)
    u, v = x[a] - x[b], x[c] - x[b]
    return float(np.degrees(np.arccos(u @ v / np.linalg.norm(u) / np.linalg.norm(v))))


def turned(m, j, k, degrees):
    """The side of k (without j) turned about j–k."""
    x = xyz(m)
    near = {i: set() for i in range(len(x))}
    for a, b, _ in m.bonds:
        near[a].add(b)
        near[b].add(a)
    side, stack = {k}, [k]
    while stack:
        for q in near[stack.pop()]:
            if q != j and q not in side:
                side.add(q)
                stack.append(q)
    axis = (x[k] - x[j]) / np.linalg.norm(x[k] - x[j])
    t = np.radians(degrees)
    for i in side - {k}:
        v = x[i] - x[k]
        x[i] = x[k] + v * np.cos(t) + np.cross(axis, v) * np.sin(t) + axis * (axis @ v) * (1 - np.cos(t))
    return Molecule(m.title, tuple(Atom(a.symbol, *map(float, p)) for a, p in zip(m.atoms, x)), m.bonds)


def test_dihedral_gradient_is_exact():
    rng = np.random.default_rng(3)
    for _ in range(10):
        x = rng.normal(size=(4, 3))
        q = [np.array([i]) for i in range(4)]
        phi, *grads = dihedrals(x, *q)
        for atom, g in enumerate(grads):
            for c in range(3):
                plus, minus = x.copy(), x.copy()
                plus[atom, c] += 1e-6
                minus[atom, c] -= 1e-6
                numeric = (dihedrals(plus, *q)[0] - dihedrals(minus, *q)[0]) / 2e-6
                assert numeric[0] == pytest.approx(g[0, c], abs=1e-5)


@pytest.mark.parametrize('key', ['Бутан · C₄H₁₀', 'Циклогексан · C₆H₁₂', 'Метилбензол (толуол) · C₇H₈', 'Этанол · C₂H₆O'])
def test_energy_gradient_with_torsions(key):
    m = library.molecule(key)
    t = terms(m)
    assert len(t) == 21 and len(t[14]) > 0  # torsion terms present
    x = xyz(m) + np.random.default_rng(1).normal(scale=0.05, size=xyz(m).shape)
    _, g = energy_and_gradient(x, t)
    for i in range(3):
        for c in range(3):
            plus, minus = x.copy(), x.copy()
            plus[i, c] += 1e-6
            minus[i, c] -= 1e-6
            numeric = (energy_and_gradient(plus, t)[0] - energy_and_gradient(minus, t)[0]) / 2e-6
            assert numeric == pytest.approx(g[i, c], abs=1e-4)


def test_butane_and_ethane_are_staggered():
    butane = library.molecule('Бутан · C₄H₁₀')
    assert dihedral(butane, 0, 1, 2, 3) == pytest.approx(180, abs=0.5)
    for start, end in [(150, 180), (120, 180), (100, 62), (70, 62), (0, 62)]:
        m = turned(butane, 1, 2, start - 180)
        assert dihedral(clean(m)[0], 0, 1, 2, 3) == pytest.approx(end, abs=2)  # eclipsed 0° leaves the saddle
    ethane = library.molecule('Этан · C₂H₆')
    eclipsed = clean(turned(ethane, 0, 1, 60))[0]
    hs = [i for i, a in enumerate(ethane.atoms) if a.symbol == 'H']
    left = [h for h in hs if any({0, h} == {p, q} for p, q, _ in ethane.bonds)]
    right = [h for h in hs if h not in left]
    assert sorted(round(dihedral(eclipsed, left[0], 0, 1, h)) for h in right) == [60, 60, 180]


def test_lone_pair_bonds_rings_and_flat_bonds_keep_their_shape():
    for key in ('Пероксид водорода · H₂O₂', 'Гидразин · N₂H₄', 'Циклогексан · C₆H₁₂', 'Циклопропан · C₃H₆', 'Бензол · C₆H₆'):
        m = library.molecule(key)
        assert np.sqrt(((xyz(clean(m)[0]) - xyz(m)) ** 2).sum(1).mean()) < 0.01, key


def test_straighten_makes_anti_chains_from_smiles():
    from modules.compass.chemistry.formats import from_smiles

    for smiles, n in [('CCCCCC', 6), ('CCOCC', 5)]:
        m = from_smiles(smiles)
        heavy = [i for i, a in enumerate(m.atoms) if a.symbol != 'H']
        assert len(heavy) == n
        for q in range(n - 3):
            assert dihedral(m, *heavy[q : q + 4]) == pytest.approx(180, abs=3), smiles
    ring = from_smiles('C1CCCCC1')
    assert dihedral(ring, 0, 1, 2, 3) == pytest.approx(55, abs=8)  # a chair, not straightened
    assert straighten(Molecule('', (Atom('C', 0, 0, 0),), ())).atoms[0].position == (0, 0, 0)


def test_tidy_while_building_a_chain_and_a_branch():
    m = Molecule('m', (Atom('C', 0, 0, 0),), ())
    for _ in range(5):  # click, click, click: hexane skeleton without hydrogens
        n = len(m.atoms)
        before = xyz(m)
        m = tidy_new(place_atom(m, 'C', (0, 0, 0), anchor=n - 1), [n])
        if n > 2:  # the atoms drawn before (except a chain end) stay put
            assert np.allclose(xyz(m)[1 : n - 1], before[1 : n - 1])
    assert all(angle(m, i, i + 1, i + 2) == pytest.approx(109.47, abs=1) for i in range(4))
    assert all(dihedral(m, i, i + 1, i + 2, i + 3) == pytest.approx(180, abs=3) for i in range(3))
    n = len(m.atoms)
    phenyl = tidy_new(place_fragment(m, 'Фенил · —C₆H₅', (0, 0, 0), anchor=2), range(n, n + 11))
    for other in (1, 3):
        assert angle(phenyl, other, 2, n) == pytest.approx(109.5, abs=4)
    ring = xyz(phenyl)[n : n + 6]
    assert np.linalg.svd(ring - ring.mean(0))[1][-1] < 0.01  # still flat
    big = Molecule('x', tuple(Atom('C', i * 3.0, 0, 0) for i in range(400)), ())
    assert tidy_new(big, [399]) is big  # too large: left as it is


def test_hydrogens_while_building_follow_the_valences():
    # «Достраивать водороды при построении» — make_room before the bond, hydrogens_for after it
    from collections import Counter

    from modules.compass.chemistry.editing import hydrogens_for, make_room

    def formula(m):
        return ''.join(f'{k}{v}' for k, v in sorted(Counter(a.symbol for a in m.atoms).items()))

    def build(m, anchor, symbol='C', order=1):
        start = m
        if anchor is not None:
            m, anchor = make_room(m, anchor, order)
        r = place_atom(m, symbol, (0, 0, 0), anchor, order)
        old = {a.position for a in start.atoms}
        new = [i for i, a in enumerate(r.atoms) if a.position not in old and a.symbol != 'H']
        near = {j for i, j, _ in r.bonds if i in new} | {i for i, j, _ in r.bonds if j in new}
        targets = sorted(set(new) | {j for j in near if r.atoms[j].symbol != 'H'} | ({anchor} if anchor is not None else set()))
        r = hydrogens_for(r, targets)
        if anchor is not None:
            r = tidy_new(r, [i for i, a in enumerate(r.atoms) if a.position not in old])
        return r

    carbons = lambda m: [i for i, a in enumerate(m.atoms) if a.symbol == 'C']  # noqa: E731
    m = build(Molecule('', (), ()), None)
    assert formula(m) == 'C1H4'  # a carbon in the empty field is methane
    for expected in ('C2H6', 'C3H8', 'C4H10'):
        m = build(m, carbons(m)[-1])
        assert formula(m) == expected
    c = carbons(m)
    assert dihedral(m, *c[:4]) == pytest.approx(180, abs=3)
    x = xyz(m)
    d = np.linalg.norm(x[:, None] - x[None], axis=2) + np.eye(len(x)) * 9
    assert d.min() > 1.0  # no atoms on top of each other
    assert formula(build(m, c[-1], 'C', 2)) == 'C5H10'  # a double bond takes two hydrogens of the end carbon
    assert formula(build(m, c[1], 'O')) == 'C4H10O1'  # a branch on CH2: 2-butanol
    water = hydrogens_for(Molecule('', (Atom('O', 0, 0, 0),), ()), [0])
    assert formula(water) == 'H2O1'
    assert make_room(water, 1)[0] is water  # a hydrogen itself is not touched
