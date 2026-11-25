"""Physical contract: rigid motions preserve lengths, angles and signed torsions.

Expected values come from a 3-4-5 triangle and orthogonal Cartesian axes,
not from the implementation under test.
"""
import pytest
from modules.compass.chemistry.geometry_tools import measurement

DISTANCE = ((0, 0, 0), (3, 4, 0))
ANGLE = ((1, 0, 0), (0, 0, 0), (0, 1, 0))
TORSION = ((1, 0, 0), (0, 0, 0), (0, 1, 0), (0, 1, 1))
TOLERANCE = 1e-8

@pytest.mark.parametrize('points,expected', [(DISTANCE, 5.0), (ANGLE, 90.0), (TORSION, -90.0)])
@pytest.mark.parametrize('offset', [(0, 0, 0), (17, -23, 41), (100000, -100000, 100000)])
def test_preserves_measurement_when_rotated_and_translated(points, expected, offset):
    # Arrange: cyclic axis permutation is a proper rotation, not reflection.
    transformed = [(z + offset[0], x + offset[1], y + offset[2]) for x, y, z in points]
    # Act
    _, actual = measurement(transformed)
    # Assert
    assert actual == pytest.approx(expected, abs=TOLERANCE)

@pytest.mark.parametrize('scale', [0.01, 2.5, 1000.0])
@pytest.mark.parametrize('points,expected', [(ANGLE, 90.0), (TORSION, -90.0)])
def test_preserves_angle_when_coordinates_change_scale(points, expected, scale):
    # Arrange
    scaled = [tuple(scale * value for value in point) for point in points]
    # Act
    _, actual = measurement(scaled)
    # Assert
    assert actual == pytest.approx(expected, abs=TOLERANCE)


def test_reverses_signed_torsion_when_geometry_is_mirrored():
    # Arrange
    reflected = [(-x, y, z) for x, y, z in TORSION]
    expected = 90.0
    # Act
    _, actual = measurement(reflected)
    # Assert
    assert actual == pytest.approx(expected, abs=TOLERANCE)
