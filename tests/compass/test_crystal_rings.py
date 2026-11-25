"""Rings, centroids and π–π stacking (modules/compass/chemistry/crystal_rings.py).

Oracles, by hand:
  * benzene (a regular hexagon of C, 1.39 Å, the H 1.08 Å out on the radii) in a cell with c = 3.6 Å perpendicular to
    its plane: one ring of six C, its centroid at the centre of the hexagon, the normal along c; it stacks with its copy
    one c on — d = 3.6 Å, α = 0, d⊥ = 3.6, offset 0;
  * the same with c tilted by 1.5 Å along a (c = (1.5, 0, 3.5) Å): d = √(1.5² + 3.5²) = 3.808 Å, d⊥ = 3.5 Å, offset 1.5
  Å;
  * with c = 4.5 Å — no stacking (d above 4.0 Å); a cyclohexane-like chair (the atoms ±0.25 Å off the plane) — no ring.
"""

from math import cos, radians, sin, sqrt

from modules.compass.chemistry import crystal as cr
from modules.compass.chemistry import crystal_rings as rg
from modules.compass.chemistry import crystal_symmetry as cs


def benzene_crystal(c=3.6, tilt=0.0, pucker=0.0, a=12.0):
    import numpy as np

    gamma, beta = 90.0, 90.0
    length = sqrt(c * c + tilt * tilt)
    if tilt:
        beta = float(np.degrees(np.arccos(tilt / length)))
    cell = cr.Cell(a, a, length, 90.0, beta, gamma)
    vectors = np.array(cell.vectors())
    inverse = np.linalg.inv(vectors)
    sites = []
    centre = np.array([a / 2, a / 2, 0.0])
    for k in range(6):
        angle = radians(60 * k)
        z = pucker * (1 if k % 2 else -1)
        for symbol, r in (('C', 1.39), ('H', 2.47)):
            p = centre + np.array([r * cos(angle), r * sin(angle), z if symbol == 'C' else z])
            f = p @ inverse
            sites.append(cr.Site(f'{symbol}{k + 1}', symbol, *(float(x) for x in f)))
    return cr.Crystal('benzene', cell, tuple(sites), (cr.operation('x, y, z'),), 'P 1')


def test_benzene_stack():
    crystal = benzene_crystal()
    found_rings, stacks = rg.stacking(crystal, 1.22)
    assert len(found_rings) == 1 and len(found_rings[0].atoms) == 6
    ring = found_rings[0]
    assert all(abs(x - y) < 1e-6 for x, y in zip(ring.centroid, (6.0, 6.0, 0.0)))
    assert abs(abs(ring.normal[2]) - 1) < 1e-9
    assert len(stacks) == 1
    s = stacks[0]
    assert abs(s.distance - 3.6) < 1e-6 and s.angle < 1e-6 and abs(s.perpendicular - 3.6) < 1e-6 and s.offset < 1e-6
    rows = rg.grouped(found_rings, stacks)
    assert rows == [('Cg(C1–C6)···Cg(C1–C6)', s.distance, s.angle, s.perpendicular, s.offset, 1)]


def test_offset_stack():
    found_rings, stacks = rg.stacking(benzene_crystal(3.5, 1.5), 1.22)
    s = stacks[0]
    assert abs(s.distance - sqrt(1.5 ** 2 + 3.5 ** 2)) < 1e-6 and abs(s.perpendicular - 3.5) < 1e-6
    assert abs(s.offset - 1.5) < 1e-6


def test_far_and_puckered():
    assert rg.stacking(benzene_crystal(4.5), 1.22)[1] == ()
    w = cs.walk(benzene_crystal(c=8.0, pucker=0.25), 1.22)
    assert rg.rings(w) == ()


def t_shaped():
    """Benzene A in the plane z = 0 at the middle of a 15 Å cell; benzene B in a plane x = const above it, its lowest
    C–H pointing straight down at the centroid of A, H 2.5 Å above it."""
    import numpy as np

    a = 15.0
    centre = np.array([7.5, 7.5, 0.0])
    sites = []
    for k in range(6):
        angle = radians(60 * k)
        for symbol, r in (('C', 1.39), ('H', 2.47)):
            p = centre + np.array([r * cos(angle), r * sin(angle), 0.0])
            sites.append(cr.Site(f'{symbol}{k + 1}', symbol, *(p / a)))
    top = centre + np.array([0.0, 0.0, 2.5 + 2.47])
    for k in range(6):
        angle = radians(-90 + 60 * k)
        for symbol, r in (('C', 1.39), ('H', 2.47)):
            p = top + np.array([0.0, r * cos(angle), r * sin(angle)])
            sites.append(cr.Site(f'{symbol}{k + 7}', symbol, *(p / a)))
    return cr.Crystal('T', cr.Cell(a, a, a), tuple(sites), (cr.operation('x, y, z'),), 'P 1')


def test_c_h_pi_of_a_t_shape():
    # H7 of B above the centroid of A: H···Cg = 2.5 Å, C–H···Cg = 180°, d⊥ = 2.5, offset 0; the rings are
    # perpendicular — no π–π stack
    crystal = t_shaped()
    found_rings, contacts = rg.ch_pi(crystal, 1.22)
    assert len(found_rings) == 2 and len(contacts) == 1
    x = contacts[0]
    assert abs(x.distance - 2.5) < 1e-6 and abs(x.angle - 180) < 1e-6 and abs(x.perpendicular - 2.5) < 1e-6
    assert x.offset < 1e-6 and rg.stacking(crystal, 1.22)[1] == ()
    rows = rg.ch_pi_grouped(crystal, found_rings, contacts)
    assert rows[0][0] == 'C7–H7···Cg(C1–C6)' and rows[0][5] == 1


def test_marks_on_the_model():
    # the model of the stacked benzene, two cells along c: two rings, one stack between them; the T shape: one C–H···π
    from modules.compass.chemistry import crystal as cr

    marks = rg.model_marks(cr.build(benzene_crystal(), (1, 1, 2), False))
    assert len(marks['rings']) == 2 and len(marks['stacks']) == 1 and marks['ch_pi'] == []
    centroid, corners = marks['rings'][0]
    assert len(corners) == 6
    t = rg.model_marks(cr.build(t_shaped(), (1, 1, 1), False))
    assert len(t['rings']) == 2 and t['stacks'] == [] and len(t['ch_pi']) == 1


def test_the_network_of_stacks_and_c_h_pi():
    # «Показать сеть» по π–π и C–H···π (crystal_contacts.network, kinds 'pi', 'ch_pi'): benzene stacked
    # along c — the molecule of the cell and its two neighbours above and below, 3 × 12 atoms
    from modules.compass.chemistry import crystal_contacts as cc
    from modules.compass.chemistry import crystal_symmetry as cs

    molecule, added = cc.network(benzene_crystal(), ('pi',), 1.22)
    assert added == 2 and len(molecule.atoms) == 36
    assert cc.network(benzene_crystal(), ('hydrogen',), 1.22)[1] == 0  # no hydrogen bonds: the cell alone
    # the T shape: the C–H···π joins the two molecules of the cell (both already there)
    crystal = t_shaped()
    w = cs.walk(crystal, 1.22)
    pairs = cc._pi_pairs(crystal, w, ('ch_pi',), 1.22)
    assert len(pairs) == 1 and w.component[pairs[0][0][0]] != w.component[pairs[0][1][0]]
    molecule, added = cc.network(crystal, ('ch_pi',), 1.22)
    assert added == 0 and molecule.formula == 'C12H12'
