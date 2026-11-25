"""Paths between two structures (modules/compass/chemistry/reaction_path.py).

Oracles: the turn of a methyl group of ethane by 60° about the C–C axis, built here from cos/sin; the
linear guess cuts the arc (an H turned by Δφ is r·cos(Δφ/2) from the axis at mid-path), IDPP keeps the
bonds; the linear midpoint is the mean of the ends; a product with the atoms in another order and turned
is renumbered and put back onto the reactant (the ends then differ only by the methyl turn).
"""

from math import acos, cos, dist, radians, sin, sqrt

import pytest

from modules.compass.chemistry import reaction_path as rp
from azimuth.core import Atom, Molecule

CC, CH, Z_H = 1.53, 1.09, 0.36  # Å; the H lies 0.36 Å beyond its C along the axis


def ethane(turn=0.0):
    r = sqrt(CH * CH - Z_H * Z_H)  # the radius of the H circle
    atoms = [Atom('C', 0.0, 0.0, -CC / 2), Atom('C', 0.0, 0.0, CC / 2)]
    for k in range(3):
        a = radians(120 * k)
        atoms.append(Atom('H', r * cos(a), r * sin(a), -CC / 2 - Z_H))
    for k in range(3):
        a = radians(120 * k + 60 + turn)
        atoms.append(Atom('H', r * cos(a), r * sin(a), CC / 2 + Z_H))
    return Molecule('ethane', tuple(atoms))


def c_h(m):
    return [dist(m.atoms[1 if i >= 5 else 0].position, m.atoms[i].position) for i in range(2, 8)]


def test_linear_cuts_the_arc_and_idpp_keeps_the_bonds():
    start, end = ethane(0), ethane(60)
    frames, rmsd = rp.path(start, end, images=5, method='linear', renumber=False)
    middle = frames[3]
    end = frames[-1]  # turned onto the start (Kabsch): both methyls now turn, in opposite senses
    r = sqrt(CH * CH - Z_H * Z_H)
    for i in range(2, 8):
        a, b = start.atoms[i].position, end.atoms[i].position
        turn = acos((a[0] * b[0] + a[1] * b[1]) / (r * r))  # the angle on the circle of radius r
        expected = sqrt((r * cos(turn / 2)) ** 2 + Z_H ** 2)  # the middle of the chord
        assert c_h(middle)[i - 2] == pytest.approx(expected, abs=1e-6)
    assert min(c_h(middle)) < CH - 0.01  # the linear guess shortens the C–H bonds
    for a, b, m in zip(start.atoms, end.atoms, middle.atoms):
        assert m.position == pytest.approx(tuple((a.position[k] + b.position[k]) / 2 for k in range(3)), abs=1e-12)
    smooth, _ = rp.path(start, end, images=5, method='idpp', renumber=False)
    assert len(smooth) == 7 and smooth[0].atoms == start.atoms and smooth[-1].atoms == rp.ends(start, end, False)[1].atoms
    for frame in smooth[1:-1]:
        assert max(abs(x - CH) for x in c_h(frame)) < 0.005
        assert dist(frame.atoms[0].position, frame.atoms[1].position) == pytest.approx(CC, abs=0.005)


def test_renumbered_and_turned_product():
    start, end = ethane(0), ethane(60)
    order = [2, 0, 7, 1, 6, 5, 4, 3]  # H, C, H, C, …: another order of the elements too
    shuffled = Molecule('p', tuple(end.atoms[i] for i in order))
    turned = Molecule('p', tuple(Atom(a.symbol, a.y + 3.0, -a.x, a.z - 1.0) for a in shuffled.atoms))  # 90° and a shift
    s, e, rmsd = rp.ends(start, turned)
    assert [a.symbol for a in e.atoms] == [a.symbol for a in start.atoms]
    assert dist(e.atoms[0].position, start.atoms[0].position) < 0.05  # the carbons stay put
    assert rmsd < 0.6  # only the methyl turn is left (its H move by r·2 sin 30° ≈ 1.03 Å, 3 of 8 atoms)
    with pytest.raises(ValueError):
        rp.ends(start, turned, renumber=False)  # another order without renumbering
    with pytest.raises(ValueError):
        rp.ends(start, Molecule('x', start.atoms[:-1]))
    with pytest.raises(ValueError):
        rp.path(start, end, images=0)
    with pytest.raises(ValueError):
        rp.path(start, end, method='spline')


def test_xyz_frames():
    frames, _ = rp.path(ethane(0), ethane(60), images=2, method='linear', renumber=False)
    from modules.compass.chemistry.formats import read_xyz_frames

    text = rp.frames_xyz(frames)
    back = read_xyz_frames(text)
    assert len(back) == 4 and text.count('frame 3 of 3') == 1
    assert back[1].atoms[2].position == pytest.approx(frames[1].atoms[2].position, abs=1e-8)
