"""Slabs by Miller indices and CIF writing (modules/compass/chemistry/surface.py).

Oracles, independent of the construction: a surface basis of the lattice must have det V = ±1 (it holds the
atoms of one cell); for a cubic cell the 2D cell of the plane (hkl) with coprime indices has the area
a² √(h² + k² + l²) and lies in the plane (A1 · (h, k, l) = A2 · (h, k, l) = 0); rock salt keeps its
composition (Na:Cl = 1:1), its shortest distance a/2 and no two atoms closer; the slab spans `layers`
interplanar spacings d = a / √(h² + k² + l²) per cell volume, with vacuum / 2 below it; a CIF written and
read again gives the same cell, operations and cell content.
"""

from math import dist, gcd, sqrt
from pathlib import Path

import numpy as np
import pytest

from modules.compass.chemistry import crystal as cr
from modules.compass.chemistry import surface as sf

ROOT = Path(__file__).parents[2]
NACL = ROOT / 'examples' / '10-crystals' / 'NaCl_rock_salt.cif'
PLANES = [(1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 0), (1, 1, 1), (2, 1, 0), (3, 2, 1), (1, -1, 0), (-1, 2, 3), (2, 0, 0)]


def rock_salt():
    return cr.parse_cif(NACL.read_text(encoding='utf-8'))


@pytest.mark.parametrize('hkl', PLANES)
def test_surface_basis_spans_the_plane(hkl):
    c = rock_salt()
    a = c.cell.a
    V = np.array(sf.surface_basis(*hkl, c.cell))
    assert abs(round(np.linalg.det(V))) == 1 and abs(np.linalg.det(V) - round(np.linalg.det(V))) < 1e-9
    g = gcd(gcd(*hkl[:2]), hkl[2])
    h = np.array(hkl) // g
    assert V[0] @ h == 0 and V[1] @ h == 0  # in the plane (cubic: the normal is (h, k, l))
    A = V @ np.array(c.cell.vectors())
    area = np.linalg.norm(np.cross(A[0], A[1]))
    assert area == pytest.approx(a * a * sqrt(h @ h), rel=1e-12)


@pytest.mark.parametrize('hkl', [(1, 0, 0), (1, 1, 0), (1, 1, 1), (2, 1, 0)])
def test_rock_salt_slab(hkl):
    c = rock_salt()
    a = c.cell.a
    plate = sf.slab(c, hkl, layers=2, vacuum=12.0)
    assert len(plate.sites) == 2 * 8  # det V = 1: one conventional cell (4 Na + 4 Cl) per layer
    molecule = cr.build(plate, (1, 1, 1))
    symbols = [x.symbol for x in molecule.atoms]
    assert symbols.count('Na') == symbols.count('Cl') == 8
    nearest = min(dist(p.position, q.position) for i, p in enumerate(molecule.atoms) for q in molecule.atoms[:i])
    assert nearest == pytest.approx(a / 2, abs=1e-6)
    cell = np.array(plate.cell.vectors())
    assert cell[0][1] == pytest.approx(0.0, abs=1e-12) and cell[1][2] == pytest.approx(0.0, abs=1e-12)  # a along x, b in xy
    d = a / sqrt(sum(x * x for x in hkl))
    assert cell[2][2] == pytest.approx(2 * d + 12.0, rel=1e-9)  # two spacings and the vacuum along the normal
    z = [p.position[2] for p in molecule.atoms]
    assert min(z) == pytest.approx(6.0, abs=1e-6) and max(z) < 6.0 + 2 * d - 1e-6
    bigger = cr.build(plate, (2, 3, 1))
    assert len(bigger.atoms) == 6 * 16


def test_refusals():
    c = rock_salt()
    for args in (((0, 0, 0),), ((10, 0, 0),)):
        with pytest.raises(ValueError):
            sf.slab(c, *args)
    with pytest.raises(ValueError):
        sf.slab(c, (1, 0, 0), layers=0)
    with pytest.raises(ValueError):
        sf.slab(c, (1, 0, 0), vacuum=-1)


def test_cif_written_and_read_again(tmp_path):
    c = rock_salt()
    again = cr.parse_cif(sf.write_cif(c))
    assert again.cell == c.cell and again.space_group == c.space_group
    assert len(again.operations) == len(c.operations) == 192
    assert {op for op in again.operations} == {op for op in c.operations}
    assert sorted(cr.unit_cell(again)) == sorted(cr.unit_cell(c))
    plate = sf.slab(c, (1, 1, 1), 1, 10.0)
    back = cr.parse_cif(sf.write_cif(plate))
    assert len(cr.unit_cell(back)) == 8 and back.cell.c == pytest.approx(plate.cell.c, abs=1e-6)
    assert sf.operation_text(cr.operation('-y+1/2, x-y, 0.25+z')) == '-y+1/2, x-y, z+1/4'
