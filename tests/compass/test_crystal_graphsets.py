"""Graph sets of hydrogen bonds (modules/compass/chemistry/crystal_graphsets.py).

Oracles, from the definitions of Etter (Acta Cryst. B46, 256, 1990), counted here by hand:
  * the chain of water molecules along a (tests/compass/test_crystal_contacts.water_chain): H1 of each molecule bonds
    the O of the next, the repeat is O–H1 — C(2);
  * a formic acid dimer about a centre of inversion (P -1, one molecule in the asymmetric unit, a 15 Å cell — the dimer
    alone; O···O 2.93 Å, H···O 1.96 Å, C···centre 2.1 Å): the two O–H···O=C bonds are one kind, the ring
    O=C–O–H···O=C–O–H···, 8 atoms, 2 acceptors, 2 hydrogens —
    R²₂(8) (the textbook example);
  * the same dimer in P 1 (two independent molecules, Z′ = 2): each bond is a kind of its own — D at the first level;
  * the second level: the two kinds of the dimer in P 1 make the ring together — R²₂(8); two independent
    water molecules along a doubled chain (O1–H1···O2, O2–H3···O1) — each D at the first level, together the chain
    C²₂(4) (the repeat O1–H1···O2–H3···, 2 acceptors, 2 hydrogens);
  * the same name for a bond inside one molecule: S(n) with n the atoms of the ring (a planar six-ring H–O–C–C–C=O
    built here, the hydrogen bond H···O closing it — S(6)).
"""

from math import cos, radians, sin

from modules.compass.chemistry import crystal as cr
from modules.compass.chemistry import crystal_contacts as cc
from modules.compass.chemistry import crystal_graphsets as gs
from tests.compass.test_crystal_contacts import water_chain

FORMIC = (  # Å, the plane z = 0; the centre of inversion of the dimer at the origin
    ('C1', 'C', 2.1, 0.0),
    ('O1', 'O', 2.1 + 1.22 * cos(radians(120)), 1.22 * sin(radians(120))),
    ('O2', 'O', 2.1 + 1.32 * cos(radians(240)), 1.32 * sin(radians(240))),
    ('H2', 'H', None, None),
    ('H1', 'H', 3.19, 0.0),
)


def formic():
    atoms = {label: (x, y) for label, _, x, y in FORMIC if x is not None}
    o2, o1 = atoms['O2'], atoms['O1']
    target = (-o1[0], -o1[1])  # O1 of the other molecule
    d = ((target[0] - o2[0]) ** 2 + (target[1] - o2[1]) ** 2) ** 0.5
    atoms['H2'] = (o2[0] + 0.97 * (target[0] - o2[0]) / d, o2[1] + 0.97 * (target[1] - o2[1]) / d)
    return [(label, symbol, *atoms[label]) for label, symbol, _, _ in FORMIC]


def dimer(independent=False):
    a = 15.0
    cell = cr.Cell(a, a, a)
    sites = [cr.Site(label, symbol, x / a, y / a, 0.0) for label, symbol, x, y in formic()]
    ops = (cr.operation('x, y, z'),)
    if independent:
        sites += [cr.Site(s.label + 'b', s.symbol, -s.x, -s.y, -s.z) for s in sites]
    else:
        ops += (cr.operation('-x, -y, -z'),)
    return cr.Crystal('formic', cell, tuple(sites), ops, 'P -1' if not independent else 'P 1')


def hydrogen_sets(crystal):
    found = cc.contacts(crystal, 1.22)
    rows = cc.grouped(found, cr.unit_cell(crystal))
    names = gs.for_contacts(crystal, found, 1.22)
    assert all(not name for row, name in zip(rows, names) if row[0] != 'hydrogen')
    return [(row[1], name) for row, name in zip(rows, names) if name]  # the H···C contacts of the table get none (§6)


def test_the_water_chain():
    assert hydrogen_sets(water_chain()) == [('O1–H1···O1', 'C(2)')]


def test_the_acid_dimer_ring():
    found = hydrogen_sets(dimer())
    assert found == [('O2–H2···O1', 'R²₂(8)')]


def test_two_independent_molecules():
    found = hydrogen_sets(dimer(independent=True))
    assert sorted(name for _, name in found) == ['D', 'D'] and len(found) == 2


def test_a_ring_inside_a_molecule():
    # H–O1–C1–C2–C3=O2 on a hexagon of side 1.40 Å, the O–H shortened to 0.97 along its side: the H···O2 side about
    # 1.8 Å closes the ring
    import numpy as np

    corners = [np.array([cos(radians(60 * k)), sin(radians(60 * k))]) * 1.4 for k in range(6)]
    h = corners[1] + (corners[0] - corners[1]) * (1 - 0.97 / 1.4)
    atoms = [('O1', 'O', corners[1]), ('C1', 'C', corners[2]), ('C2', 'C', corners[3]), ('C3', 'C', corners[4]),
             ('O2', 'O', corners[5]), ('H1', 'H', h)]
    a = 15.0
    sites = tuple(cr.Site(label, symbol, p[0] / a + 0.5, p[1] / a + 0.5, 0.5) for label, symbol, p in atoms)
    crystal = cr.Crystal('ring', cr.Cell(a, a, a), sites, (cr.operation('x, y, z'),), 'P 1')
    found = hydrogen_sets(crystal)
    assert found == [('O1–H1···O2', 'S(6)')]
    assert gs.name('R', 8, 2, 2) == 'R²₂(8)' and gs.name('D', 2) == 'D'


def double_water_chain(a=2.9):
    """Two independent water molecules along a, the cell twice the chain of water_chain."""
    cell = cr.Cell(2 * a, 6.0, 6.0)
    h2 = (0.96 * cos(radians(104.5)), 0.96 * sin(radians(104.5)))
    sites = []
    for k, (o, h, h_) in enumerate((('O1', 'H1', 'H2'), ('O2', 'H3', 'H4'))):
        x = k * 0.5
        sites += [cr.Site(o, 'O', x, 0.0, 0.0), cr.Site(h, 'H', x + 0.96 / (2 * a), 0.0, 0.0),
                  cr.Site(h_, 'H', x + h2[0] / (2 * a), h2[1] / 6.0, 0.0)]
    return cr.Crystal('water2', cell, tuple(sites), (cr.operation('x, y, z'),), 'P 1')


def second(crystal):
    found = cc.contacts(crystal, 1.22)
    rows = cc.grouped(found, cr.unit_cell(crystal))
    return [(rows[i][1], rows[j][1], text) for i, j, text in gs.second_level(crystal, found, 1.22)]


def test_the_second_level_ring_of_two_independent_molecules():
    found = second(dimer(independent=True))
    assert [text for _, _, text in found] == ['R²₂(8)']
    assert second(dimer()) == []  # one kind of bond: nothing at the second level


def test_the_second_level_chain():
    crystal = double_water_chain()
    assert sorted(name for _, name in hydrogen_sets(crystal)) == ['D', 'D']
    found = second(crystal)
    assert len(found) == 1 and found[0][2] == 'C²₂(4)'
    assert {found[0][0], found[0][1]} == {'O1–H1···O2', 'O2–H3···O1'}
