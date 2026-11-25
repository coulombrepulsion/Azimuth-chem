"""The van der Waals volume and surface areas (modules/compass/chemistry/molecular_size.py) against geometry."""

from math import pi

import pytest

from azimuth.core import read_xyz
from modules.compass.chemistry import molecular_size as ms


def test_one_atom_is_a_sphere():
    argon = read_xyz('1\n\nAr 0 0 0')
    r = 1.88
    assert ms.volume(argon, 0.05) == pytest.approx(4 / 3 * pi * r ** 3, rel=0.01)
    assert ms.area(argon) == pytest.approx(4 * pi * r ** 2, rel=1e-12)  # nothing covers its points
    assert ms.area(argon, probe=1.4) == pytest.approx(4 * pi * 3.28 ** 2, rel=1e-12)
    assert ms.size(argon, 0.05)['diameter'] == pytest.approx(2 * r, rel=0.005)


def test_two_spheres_overlap_as_a_lens():
    # two Ar 2.5 Å apart: V = 2·(4/3)πr³ − the lens 2·πh²(3r − h)/3, h = r − d/2; the area loses the two caps 2πrh
    r, d = 1.88, 2.5
    h = r - d / 2
    pair = read_xyz(f'2\n\nAr 0 0 0\nAr {d} 0 0')
    lens = 2 * pi * h * h * (3 * r - h) / 3
    assert ms.volume(pair, 0.05) == pytest.approx(2 * 4 / 3 * pi * r ** 3 - lens, rel=0.01)
    assert ms.area(pair, points=4000) == pytest.approx(2 * (4 * pi * r * r - 2 * pi * r * h), rel=0.01)
    far = read_xyz('2\n\nAr 0 0 0\nAr 10 0 0')
    assert ms.area(far) == pytest.approx(2 * 4 * pi * r * r, rel=1e-12)


def test_dummy_atoms_and_unknown_elements():
    water_x = read_xyz('4\n\nO 0 0 0\nH 0.96 0 0\nH -0.24 0.93 0\nX 0 0 5')
    assert ms.size(water_x, 0.1)['atoms'] == 3
    assert ms.radius('Og') == ms.DEFAULT and ms.radius('C') == 1.70
