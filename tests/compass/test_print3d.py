"""A model for 3D printing (modules/compass/chemistry/print3d.py).

Oracles, independent of the tested code:
  * a closed body wound outward: every edge belongs to exactly two triangles, used once in each direction, and the
    signed volume (the divergence theorem, Σ a·(b × c)/6) is positive;
  * the icosphere inscribed in a sphere of radius r: its volume a little below 4/3 πr³ (within 4 % at two
    subdivisions — 320 faces); the cylinder of 20 sides: the prism n/2 r² sin(2π/n) h;
  * the binary STL: 84 + 50 n bytes, the count written after the 80-byte header, the corners read back;
  * water (3 atoms, 2 bonds) at 10 mm/Å: three balls, two rods of at least the printable thickness, the size of the
    model the span of its atoms plus the balls.
"""

import struct
from collections import Counter
from math import pi, sin

import numpy as np
import pytest

from azimuth.core import Atom, Molecule
from modules.compass.chemistry import print3d


def closed_outward(tris):
    edges = Counter()
    for t in np.round(tris, 6):
        for a, b in ((0, 1), (1, 2), (2, 0)):
            edges[(tuple(t[a]), tuple(t[b]))] += 1
    return all(n == 1 and edges.get((b, a)) == 1 for (a, b), n in edges.items())


def water():
    return Molecule('water', (Atom('O', 0.0, 0.0, 0.0), Atom('H', 0.757, 0.586, 0.0), Atom('H', -0.757, 0.586, 0.0)), None)


def test_a_ball_and_a_rod_are_closed_bodies():
    ball = print3d.icosphere((1.0, 2.0, 3.0), 2.0)
    assert len(ball) == 320 and closed_outward(ball)
    assert 0.96 * 4 / 3 * pi * 8 < print3d.volume(ball) < 4 / 3 * pi * 8
    rod = print3d.cylinder((0, 0, 0), (0, 0, 5.0), 1.0, sides=20)
    assert closed_outward(rod)
    assert print3d.volume(rod) == pytest.approx(20 / 2 * sin(2 * pi / 20) * 5.0, rel=1e-9)
    slanted = print3d.cylinder((1, 2, 3), (4, -1, 7), 0.5)
    assert closed_outward(slanted) and print3d.volume(slanted) > 0


def test_water_at_a_printable_size(tmp_path):
    model = print3d.parts(water(), scale=10, rod=0.05, min_rod=1.6)
    names = sorted(p.name for p in model)
    assert names == ['H', 'O', 'bonds']
    bonds = next(p for p in model if p.name == 'bonds')
    assert len(bonds.triangles) == 2 * (4 * print3d.SIDES)  # two rods, each a side of 2n and two caps of n
    # the rod of 0.05 Å would be 1 mm across — made 1.6 mm: the corners of the first rod (O–H) lie 0.8 mm from its axis
    h = np.array([7.57, 5.86, 0.0])
    axis = h / np.linalg.norm(h)
    corners = bonds.triangles[:4 * print3d.SIDES].reshape(-1, 3)
    off = corners - np.outer(corners @ axis, axis)
    far = np.linalg.norm(off, axis=1)
    assert far.max() == pytest.approx(0.8, abs=1e-6)
    dx, dy, dz = print3d.size(model)
    assert dx == pytest.approx(2 * 7.57 + 2 * 2.5, abs=0.05) and dz == pytest.approx(2 * 3.5, abs=0.05)
    path = print3d.write_stl(model, tmp_path / 'water.stl')
    data = path.read_bytes()
    n = sum(len(p.triangles) for p in model)
    assert len(data) == 84 + 50 * n and struct.unpack('<I', data[80:84])[0] == n
    first = np.frombuffer(data[84 + 12:84 + 48], '<f4').reshape(3, 3)
    assert np.allclose(first, model[0].triangles[0], atol=1e-4)
    text = print3d.write_vrml(model, tmp_path / 'water.wrl').read_text(encoding='utf-8')
    assert text.startswith('#VRML V2.0 utf8') and text.count('Shape {') == 3 and text.count('-1,') == n


def test_colours_halves_and_cell_edges():
    colors = {'O': '#df645b', 'H': '#e2e8ec'}
    model = print3d.parts(water(), colors=colors, edges=[((0, 0, 0), (1, 0, 0))])
    assert {p.color for p in model if p.name == 'bonds'} == set(colors.values())
    cell = next(p for p in model if p.name == 'cell')
    assert closed_outward(cell.triangles)
    hidden = print3d.parts(water(), hidden={1})
    assert sorted(p.name for p in hidden) == ['H', 'O', 'bonds']
    assert len(next(p for p in hidden if p.name == 'bonds').triangles) == 4 * print3d.SIDES
    with pytest.raises(ValueError):
        print3d.parts(Molecule('', (), None))
