"""Hydrogens by valence, H → group, element change (modules/compass/chemistry/editing.py)."""

import math
from math import acos, degrees, dist

import pytest

from azimuth.core import Atom, EXAMPLES, Molecule, read_xyz
from modules.compass.chemistry.builder import connections
from modules.compass.chemistry.editing import add_hydrogens, bonds_with_orders, change_element, substitute
from modules.compass.chemistry.names import name


def named(m):
    return name([a.symbol for a in m.atoms], [(i, j) for i, j, _ in connections(m)])


def angle(m, i, j, k):
    a, b, c = (m.atoms[x].position for x in (i, j, k))
    u = [a[t] - b[t] for t in range(3)]
    v = [c[t] - b[t] for t in range(3)]
    return degrees(acos(sum(x * y for x, y in zip(u, v)) / dist(a, b) / dist(c, b)))


BENZENE = [Atom('C', 1.39 * math.cos(t * math.pi / 3), 1.39 * math.sin(t * math.pi / 3), 0) for t in range(6)]


@pytest.mark.parametrize(
    'atoms,added,expected',
    [
        ([Atom('C', 0, 0, 0)], 4, 'метан'),
        ([Atom('C', 0, 0, 0), Atom('C', 1.52, 0, 0)], 6, 'этан'),
        ([Atom('C', 0, 0, 0), Atom('C', 1.34, 0, 0)], 4, 'этен (этилен)'),
        ([Atom('C', 0, 0, 0), Atom('C', 1.20, 0, 0)], 2, 'этин (ацетилен)'),
        ([Atom('C', 0, 0, 0), Atom('O', 1.21, 0, 0)], 2, 'метаналь (формальдегид)'),
        ([Atom('N', 0, 0, 0)], 3, 'аммиак'),
        (BENZENE, 6, 'бензол'),
    ],
)
def test_hydrogens_by_valence_and_bond_length(atoms, added, expected):
    m, n = add_hydrogens(Molecule('', tuple(atoms), None))
    assert n == added and named(m) == expected


def test_shapes():
    m, _ = add_hydrogens(Molecule('', (Atom('C', 0, 0, 0), Atom('C', 1.52, 0, 0)), None))
    assert angle(m, 1, 0, 2) == pytest.approx(109.47, abs=0.01) and angle(m, 2, 0, 3) == pytest.approx(109.47, abs=0.01)
    m, _ = add_hydrogens(Molecule('', (Atom('C', 0, 0, 0), Atom('C', 1.34, 0, 0)), None))
    assert angle(m, 1, 0, 2) == pytest.approx(120, abs=0.01) and all(abs(a.z) < 1e-9 for a in m.atoms)  # planar
    assert add_hydrogens(read_xyz(EXAMPLES['Метан · CH₄']))[1] == 0
    assert bonds_with_orders(Molecule('', (Atom('C', 0, 0, 0), Atom('O', 1.21, 0, 0)), None)) == ((0, 1, 2),)


def test_selected_atoms_only():
    m, n = add_hydrogens(Molecule('', (Atom('C', 0, 0, 0), Atom('C', 1.52, 0, 0)), None), [1])
    assert n == 3 and m.formula == 'C2H3'


def test_substitute_and_change_element():
    methane = read_xyz(EXAMPLES['Метан · CH₄'])
    assert named(substitute(methane, 1, 'Гидроксил · —OH')) == 'метанол'
    assert named(substitute(methane, 1, 'Метил · —CH₃')) == 'этан'
    chloro = change_element(methane, 1, 'Cl')
    assert named(chloro) == 'хлорметан' and dist(chloro.atoms[0].position, chloro.atoms[1].position) == pytest.approx(
        1.78
    )
    with pytest.raises(ValueError):
        substitute(methane, 0, 'Метил · —CH₃')  # carbon has four bonds: not terminal


def test_cleanup_tidies_a_rough_structure():
    import random
    import numpy as np
    from modules.compass.chemistry.cleanup import clean, energy_and_gradient, terms
    from modules.compass.chemistry.editing import perceived_orders

    water = Molecule('w', (Atom('O', 0, 0, 0), Atom('H', 1.2, 0, 0.1), Atom('H', -0.3, 0, 0.8)), ((0, 1, 1), (0, 2, 1)))
    c, _, _ = clean(water)
    assert dist(c.atoms[0].position, c.atoms[1].position) == pytest.approx(0.97, abs=1e-3)
    assert angle(c, 1, 0, 2) == pytest.approx(104.5, abs=0.05)
    benzene, _ = add_hydrogens(Molecule('', tuple(BENZENE), None))
    random.seed(5)
    rough = Molecule(
        'x', tuple(Atom(a.symbol, *[p + random.uniform(-0.1, 0.1) for p in a.position]) for a in benzene.atoms), None
    )
    assert {o for *_, o in perceived_orders(rough) if o != 1} == {1.5}  # orders from valences, not lengths
    c, _, _ = clean(rough)
    ring = [dist(c.atoms[i].position, c.atoms[(i + 1) % 6].position) for i in range(6)]
    assert max(ring) - min(ring) < 0.01 and named(c) == 'бензол'
    t = terms(rough)
    x = np.array([a.position for a in rough.atoms])
    _, g = energy_and_gradient(x, t)
    h = 1e-6
    i, k = 3, 2
    xp = x.copy()
    xp[i, k] += h
    xm = x.copy()
    xm[i, k] -= h
    assert (energy_and_gradient(xp, t)[0] - energy_and_gradient(xm, t)[0]) / 2 / h == pytest.approx(g[i, k], abs=1e-5)


def test_chain_and_molecule_of_an_atom():
    # «Цепочка» and «Молекула целиком» of the move tools. Oracle: the structures by hand —
    # toluene: the methyl is a chain of C and its 3 H up to the ring; a ring atom alone (with its H);
    # benzaldehyde: CHO (C, O, H) up to the ring; hexane: unbranched, all 20 atoms from any atom;
    # a water dimer (no bond between the molecules): one water of three atoms
    from modules.compass.chemistry import library
    from modules.compass.chemistry.editing import chain, connected

    def pick(start):
        return library.molecule(next(k for k in library.keys() if k.startswith(start)))

    def neighbours(m, i):
        return {j if k == i else k for k, j, _ in connections(m) if i in (k, j)}

    toluene = pick('Метилбензол')
    heavy = [i for i, a in enumerate(toluene.atoms) if a.symbol == 'C']
    methyl = next(i for i in heavy if sum(toluene.atoms[j].symbol == 'H' for j in neighbours(toluene, i)) == 3)
    hydrogens = sorted(j for j in neighbours(toluene, methyl) if toluene.atoms[j].symbol == 'H')
    assert chain(toluene, methyl) == sorted([methyl, *hydrogens]) == chain(toluene, hydrogens[0])
    ipso = next(j for j in neighbours(toluene, methyl) if toluene.atoms[j].symbol == 'C')
    assert chain(toluene, ipso) == [ipso]  # a ring atom with no hydrogen: itself
    ring_ch = next(i for i in heavy if i not in (methyl, ipso))
    assert len(chain(toluene, ring_ch)) == 2  # a ring CH: the atom and its hydrogen
    aldehyde = pick('Бензальдегид')
    oxygen = next(i for i, a in enumerate(aldehyde.atoms) if a.symbol == 'O')
    assert sorted(aldehyde.atoms[i].symbol for i in chain(aldehyde, oxygen)) == ['C', 'H', 'O']
    hexane = pick('Гексан')
    assert all(chain(hexane, i) == list(range(20)) for i in range(20))
    water = read_xyz('3\nw\nO 0 0 0\nH 0.96 0 0\nH -0.24 0.93 0')
    dimer = Molecule('dimer', water.atoms + tuple(Atom(a.symbol, a.position[0], a.position[1], a.position[2] + 3.0)
                                                  for a in water.atoms))
    assert connected(dimer, 4) == [3, 4, 5] and connected(dimer, 0) == [0, 1, 2]
    assert chain(dimer, 1) == [0, 1, 2]
