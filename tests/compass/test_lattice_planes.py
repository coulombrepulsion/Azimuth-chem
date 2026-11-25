"""lattice_planes: the planes (100) and (111) of a cube and of a block; the spacing."""

import numpy as np
import pytest

from modules.compass.chemistry import crystal as cr
from modules.compass.chemistry import lattice_planes as lp


def test_the_planes_of_a_cube():
    cell = cr.Cell(4.0, 4.0, 4.0)
    squares = lp.planes(cell, (1, 0, 0))
    assert len(squares) == 2 and all(len(p) == 4 for p in squares)  # x = 0 and x = 1
    assert sorted(round(p[0][0], 6) for p in squares) == [0.0, 4.0]
    tri = lp.planes(cell, (1, 1, 1))
    # x + y + z = 1 and 2 cut triangles; 0 and 3 touch a corner only
    assert [len(p) for p in tri] == [3, 3]
    hexagon = lp.planes(cell, (1, 1, 1), (2, 2, 2))
    assert max(len(p) for p in hexagon) == 6  # x + y + z = 3 through the middle of the block
    assert lp.spacing(cell, (1, 1, 1)) == pytest.approx(4.0 / 3 ** 0.5)
    assert lp.spacing(cr.Cell(4.0, 5.0, 6.0, 90, 100, 90), (0, 1, 0)) == pytest.approx(5.0)


def test_the_limits():
    with pytest.raises(ValueError):
        lp.planes(cr.Cell(4.0, 4.0, 4.0), (0, 0, 0))
    with pytest.raises(ValueError):
        lp.planes(cr.Cell(4.0, 4.0, 4.0), (6, 6, 6), (3, 3, 3))  # 55 planes


def test_a_plane_lies_in_its_plane():
    cell = cr.Cell(5.0, 6.0, 7.0, 80, 95, 105)
    rows = np.array(cell.vectors())
    for polygon in lp.planes(cell, (1, -2, 1), (2, 1, 1)):
        f = np.array(polygon) @ np.linalg.inv(rows)
        values = f @ np.array((1, -2, 1))
        assert np.ptp(values) < 1e-9 and abs(values[0] - round(values[0])) < 1e-9
