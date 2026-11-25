from dataclasses import replace
import numpy as np
import pytest
from modules.spectrum.readers.cube import read_cube, demo_cube
from modules.spectrum.views.cube_view import surface
from modules.compass.chemistry.geometry_tools import BOHR


def fixture(natoms=1, nval='', counts=(2, 2, 2), tail=None):
    return f'''test
field
{natoms} 1 2 3{nval}
{counts[0]} 1 0 0
{counts[1]} 0 2 0
{counts[2]} 0 0 3
1 1.0 4 5 6
''' + (' '.join(str(i) for i in range(8)) if tail is None else tail)


def test_cube_axes_geometry_and_z_fast_order():
    c = read_cube(fixture())
    assert c.values.shape == (2, 2, 2, 1)
    assert c.values[1, 0, 1, 0] == 5
    assert c.origin == pytest.approx(np.array([1, 2, 3]) * BOHR)
    assert c.axes == pytest.approx(np.diag([1, 2, 3]) * BOHR)
    assert c.molecule.atoms[0].position == pytest.approx(np.array([4, 5, 6]) * BOHR)


def test_angstrom_extension():
    c = read_cube(fixture(counts=(-2, -2, -2)))
    assert c.molecule.atoms[0].position == (4, 5, 6)
    assert c.origin == pytest.approx([1, 2, 3])


def test_multiple_orbitals_interleaved_and_wrapped_ids():
    c = read_cube(fixture(natoms=-1, tail='2 7\n9\n' + ' '.join(str(i) for i in range(16))))
    assert c.ids == (7, 9)
    assert c.values[1, 0, 1, :] == pytest.approx([10, 11])


def test_positive_nval_and_fortran_numbers():
    c = read_cube(fixture(nval=' 2', tail=' '.join(f'{i}D-1' for i in range(16))))
    assert c.values[1, 1, 1, :] == pytest.approx([1.4, 1.5])


@pytest.mark.parametrize(
    'text',
    [
        fixture(tail='1 2'),
        fixture(tail=' '.join(['nan'] * 8)),
        fixture(counts=(-2, 2, 2)),
        fixture(counts=(0, 2, 2)),
        fixture(natoms=-1, tail=''),
        fixture(natoms=-1, nval=' 2'),
        fixture(tail=' '.join(['1e999'] * 8)),
        fixture().replace('0 0 3', '0 2 0'),
        fixture().replace('1 1.0 4 5 6', '0 1.0 4 5 6'),
    ],
)
def test_invalid_cube_is_rejected(text):
    with pytest.raises(ValueError):
        read_cube(text)


def test_size_limits_before_allocating():
    with pytest.raises(ValueError):
        read_cube(fixture(counts=(99999, 99999, 99999)))


def test_signed_surfaces_and_empty_level():
    c = demo_cube()
    pos = surface(c, 0, 0.05)
    neg = surface(c, 0, -0.05)
    assert pos.GetNumberOfPoints() > 0 and neg.GetNumberOfPoints() > 0
    assert pos.GetBounds()[0] > 0 and neg.GetBounds()[1] < 0
    assert surface(c, 0, 50).GetNumberOfPoints() == 0


def test_skew_grid_surface_world_coordinates_and_vtk_array_order():
    # Scalar equals grid x. Iso x=.5 must map through full skew basis.
    c = read_cube(fixture(counts=(-2, -2, -2), tail='0 0 0 0 1 1 1 1'))
    c = replace(c, axes=np.array([[2.0, 0, 0], [1.0, 3, 0], [0, 0, 4.0]]), origin=np.array([10.0, 20, 30]))
    mesh = surface(c, 0, 0.5)
    assert mesh.GetBounds() == pytest.approx((11, 12, 20, 23, 30, 34))


def test_reflected_axis_supported():
    c = demo_cube()
    c = replace(c, axes=c.axes * np.array([-1, 1, 1])[:, None])
    assert surface(c, 0, 0.05).GetNumberOfPoints() > 0
