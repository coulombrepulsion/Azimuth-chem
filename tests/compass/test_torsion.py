"""Rotation about a bond (modules/compass/chemistry/torsion.py).

Oracles, independent of the tested code:
  * the dihedral angle against modules/compass/chemistry/zmatrix.dihedral (another implementation) for random
    points, and against hand-made cis (0), trans (180) and +-90 configurations;
  * after set_dihedral the dihedral is the target (that oracle), every interatomic distance inside
    each side is unchanged, the fixed side has not moved at all, and every bond length is kept;
  * a full turn (360) gives the starting geometry back;
  * the scan: frame 0 is the input, consecutive frames differ by the step in the dihedral, n = 360 /
    step frames; the closest contact against a brute force over pairs at graph distance >= 3 (BFS);
    syn butane (0) has a closer contact than anti butane (180);
  * a ring bond and atoms that are not bonded are refused.
Bounds: 1e-9 deg for angles reached; 1e-10 A for distances kept (rotations of ~5 A vectors, float64).
"""

import random
from itertools import combinations
from math import dist

import pytest

from modules.compass.chemistry import library
from modules.compass.chemistry import torsion
from modules.compass.chemistry.zmatrix import dihedral as zdihedral
from modules.compass.chemistry.builder import connections
from azimuth.core import Atom, Molecule


def find(prefix):
    return library.molecule(next(k for k in library.keys() if k.startswith(prefix)))


def butane_chain(m):
    """C1-C2-C3-C4 of butane along its bonds."""
    carbons = [i for i, a in enumerate(m.atoms) if a.symbol == 'C']
    nb = {i: {j if k == i else k for k, j, _ in connections(m) if i in (k, j)} for i in carbons}
    ends = [i for i in carbons if len(nb[i] & set(carbons)) == 1]
    chain = [ends[0]]
    while len(chain) < 4:
        chain.append(next(j for j in nb[chain[-1]] if j in carbons and j not in chain))
    return chain


def wrap(x):
    return (x + 180.0) % 360.0 - 180.0


def test_dihedral_against_another_implementation_and_known_cases():
    rng = random.Random(4)
    for _ in range(200):
        pts = [tuple(rng.uniform(-3, 3) for _ in range(3)) for _ in range(4)]
        m = Molecule('', tuple(Atom('C', *p) for p in pts))
        assert wrap(torsion.dihedral(m, 0, 1, 2, 3) - zdihedral(*pts)) == pytest.approx(0, abs=1e-9)
    cis = Molecule('', (Atom('C', 1, 1, 0), Atom('C', 0, 0, 0), Atom('C', 0, 0, 1), Atom('C', 1, 1, 1)))
    trans = Molecule('', (Atom('C', 1, 0, 0), Atom('C', 0, 0, 0), Atom('C', 0, 0, 1), Atom('C', -1, 0, 1)))
    plus = Molecule('', (Atom('C', 1, 0, 0), Atom('C', 0, 0, 0), Atom('C', 0, 0, 1), Atom('C', 0, 1, 1)))
    assert torsion.dihedral(cis, 0, 1, 2, 3) == pytest.approx(0, abs=1e-12)
    assert abs(torsion.dihedral(trans, 0, 1, 2, 3)) == pytest.approx(180, abs=1e-12)
    assert abs(torsion.dihedral(plus, 0, 1, 2, 3)) == pytest.approx(90, abs=1e-12)
    assert torsion.dihedral(plus, 0, 1, 2, 3) == pytest.approx(zdihedral(*[a.position for a in plus.atoms]), abs=1e-12)


@pytest.mark.parametrize('target', [-120.0, -60.0, 0.0, 60.0, 179.5, 180.0])
def test_set_dihedral_from_either_side(target):
    m = find('Бутан')
    a, b, c, d = butane_chain(m)
    for moving in (c, b):
        r = torsion.set_dihedral(m, a, b, c, d, moving, target)
        assert wrap(zdihedral(*[r.atoms[i].position for i in (a, b, c, d)]) - target) == pytest.approx(0, abs=1e-9)
        turned = set(torsion.side(m, b, c, moving))
        still = [i for i in range(len(m.atoms)) if i not in turned]
        assert all(r.atoms[i] == m.atoms[i] for i in still)  # the fixed side has not moved at all
        for group in (sorted(turned), still):
            for i, j in combinations(group, 2):
                assert dist(r.atoms[i].position, r.atoms[j].position) == pytest.approx(
                    dist(m.atoms[i].position, m.atoms[j].position), abs=1e-10
                )
        for i, j, _ in connections(m):
            assert dist(r.atoms[i].position, r.atoms[j].position) == pytest.approx(
                dist(m.atoms[i].position, m.atoms[j].position), abs=1e-10
            )


def test_full_turn_gives_the_start_back():
    m = find('Бутан')
    _, b, c, _ = butane_chain(m)
    r = torsion.turn(m, b, c, c, 360.0)
    assert max(dist(p.position, q.position) for p, q in zip(r.atoms, m.atoms)) < 1e-10


def graph_distance(m, i):
    nb = {k: set() for k in range(len(m.atoms))}
    for x, y, _ in connections(m):
        nb[x].add(y)
        nb[y].add(x)
    seen, frontier, depth = {i: 0}, [i], 0
    while frontier:
        depth += 1
        nxt = []
        for x in frontier:
            for y in nb[x]:
                if y not in seen:
                    seen[y] = depth
                    nxt.append(y)
        frontier = nxt
    return seen


def test_scan_frames_steps_and_contacts():
    m = find('Бутан')
    a, b, c, d = butane_chain(m)
    frames = torsion.scan(m, b, c, c, 30.0)
    assert len(frames) == 12 and [f[0] for f in frames] == [30.0 * k for k in range(12)]
    assert frames[0][3] is m
    values = [f[1] for f in frames]
    steps = {round(wrap(values[k + 1] - values[k]), 6) for k in range(11)}
    assert len(steps) == 1 and abs(steps.pop()) == pytest.approx(30.0, abs=1e-6)
    group = torsion.side(m, b, c, c)
    for _, _, found, frame in frames[::4]:
        best = min(
            (dist(frame.atoms[i].position, frame.atoms[j].position), i, j)
            for i in group
            for j, g in graph_distance(frame, i).items()
            if j not in group and g >= 3
        )
        assert found[0] == pytest.approx(best[0], abs=1e-12)
    syn = torsion.set_dihedral(m, a, b, c, d, c, 0.0)
    anti = torsion.set_dihedral(m, a, b, c, d, c, 180.0)
    assert torsion.contact(syn, group)[0] < torsion.contact(anti, group)[0]


def test_refusals():
    m = find('Бутан')
    a, b, c, d = butane_chain(m)
    with pytest.raises(ValueError):
        torsion.scan(m, b, c, c, 7.0)  # does not divide 360
    with pytest.raises(ValueError):
        torsion.scan(m, b, c, c, 0.5)  # 720 frames
    with pytest.raises(ValueError):
        torsion.turn(m, a, c, c, 10.0)  # not bonded
    ring = find('Циклогексан')
    i, j, _ = next(e for e in connections(ring) if ring.atoms[e[0]].symbol == 'C' and ring.atoms[e[1]].symbol == 'C')
    with pytest.raises(ValueError, match='цикл'):
        torsion.turn(ring, i, j, j, 10.0)
    assert torsion.reference(m, b, c) == (a, d)  # heavy neighbours preferred
