"""brillouin: the first Brillouin zones of the cubic and hexagonal lattices, the points of the paths in them."""

from math import pi

import pytest

from modules.compass.chemistry import brillouin
from modules.compass.chemistry import crystal as cr


def cif(group, a, c=None, gamma=90):
    return cr.parse_cif(f"""data_t
_cell_length_a {a}
_cell_length_b {a}
_cell_length_c {c or a}
_cell_angle_alpha 90
_cell_angle_beta 90
_cell_angle_gamma {gamma}
_symmetry_space_group_name_H-M '{group}'
loop_
_atom_site_label
_atom_site_type_symbol
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
X1 Cu 0 0 0
""")


@pytest.mark.parametrize('group, a, kind, vertices, faces, cells', [
    ('P m -3 m', 4.0, 'cP', 8, 6, 1), ('F m -3 m', 3.61, 'cF', 24, 14, 4), ('I m -3 m', 2.87, 'cI', 14, 12, 2)])
def test_cubic_zones(group, a, kind, vertices, faces, cells):
    z = brillouin.zone(cif(group, a))
    assert (z.kind, len(z.vertices), len(z.faces)) == (kind, vertices, faces)
    assert z.volume == pytest.approx((2 * pi) ** 3 / (a ** 3 / cells), rel=1e-9)
    assert all(brillouin.inside(z, p) for p in z.points.values())


def test_fcc_points():
    # X at 2π/a on a square face, L at √3/2 · 2π/a on a hexagonal face (the centres of the faces: on the surface)
    a = 3.61
    z = brillouin.zone(cif('F m -3 m', a))
    norm = lambda v: sum(x * x for x in v) ** 0.5  # noqa: E731
    assert norm(z.points['X']) == pytest.approx(2 * pi / a) and norm(z.points['L']) == pytest.approx(3 ** 0.5 * pi / a)
    assert brillouin.describe(z) == 'Γ–X–W–K–Γ–L–U–W–L–K | U–X'


def test_hexagonal_prism():
    z = brillouin.zone(cif('P 6/m m m', 2.46, 6.7, 120))
    assert (z.kind, len(z.vertices), len(z.faces)) == ('hP', 12, 8)
    cell = cr.Cell(2.46, 2.46, 6.7, 90, 90, 120)
    assert z.volume == pytest.approx((2 * pi) ** 3 / cell.volume(), rel=1e-9)
    assert all(brillouin.inside(z, p) for p in z.points.values())
