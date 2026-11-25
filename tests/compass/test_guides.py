"""Vectors and planes on the model (modules/compass/chemistry/guides.py) — without a window."""

from math import cos, radians, sin, sqrt

import pytest

from azimuth.core import read_xyz
from modules.compass.chemistry import guides

RING = [(1.39 * cos(radians(60 * k)), 1.39 * sin(radians(60 * k)), 0.0) for k in range(6)]


def benzene_and_tilted_ring(tilt):
    second = [(x, y * cos(radians(tilt)), y * sin(radians(tilt)) + 3.5) for x, y, _ in RING]
    return read_xyz('12\n\n' + '\n'.join(f'C {x} {y} {z}' for x, y, z in RING + second))


def test_the_sheet_and_the_normal_of_a_ring():
    m = benzene_and_tilted_ring(0)
    sheet = guides.geometry({'kind': 'plane', 'atoms': tuple(range(6))}, m)
    assert all(abs(c[2]) < 1e-9 for c in sheet['corners'])  # in the plane of the ring
    # the rectangle covers the ring (radius 1.39) with 0.8 Å to spare along its own axes
    half = sorted({round(abs(c[k] - sheet['centre'][k]), 6) for c in sheet['corners'] for k in range(2)})
    assert max(half) >= 1.39 + guides.MARGIN - 1e-6
    normal = guides.geometry({'kind': 'normal', 'atoms': tuple(range(6))}, m)
    assert normal['start'] == pytest.approx((0, 0, 0), abs=1e-9)
    assert normal['end'] == pytest.approx((0, 0, guides.NORMAL_LENGTH), abs=1e-9)  # the +z side
    assert guides.geometry({'kind': 'plane', 'atoms': (0, 1, 20)}, m) is None  # an atom no longer there


def test_angles_between_guides():
    m = benzene_and_tilted_ring(30)
    p1, p2 = {'kind': 'plane', 'atoms': tuple(range(6))}, {'kind': 'plane', 'atoms': tuple(range(6, 12))}
    assert guides.angle(p1, p2, m) == pytest.approx(30, abs=1e-9)
    n1 = {'kind': 'normal', 'atoms': tuple(range(6))}
    along_x = {'kind': 'vector', 'points': ((0, 0, 0), (2, 0, 0))}
    up = {'kind': 'vector', 'points': ((0, 0, 0), (0, 0, -1))}
    assert guides.angle(along_x, p1, m) == pytest.approx(0, abs=1e-9)  # a vector in the plane
    assert guides.angle(up, p1, m) == pytest.approx(90, abs=1e-9)  # along the normal
    assert guides.angle(up, n1, m) == pytest.approx(0, abs=1e-9)  # a normal is a line without a sense
    assert guides.angle(along_x, up, m) == pytest.approx(90, abs=1e-9)
    back = {'kind': 'vector', 'points': ((0, 0, 0), (-1, 0, 0))}
    assert guides.angle(along_x, back, m) == pytest.approx(180, abs=1e-9)  # vectors keep their sense
    c0, c3 = {'kind': 'vector', 'atoms': (0, 3)}, {'kind': 'vector', 'atoms': (3, 0)}
    assert guides.angle(c0, c3, m) == pytest.approx(180, abs=1e-9)
    assert guides.angle(n1, p2, m) == pytest.approx(60, abs=1e-9)  # the normal of ring 1 and the tilted ring 2
    assert guides.angle(n1, {'kind': 'normal', 'atoms': tuple(range(6, 12))}, m) == pytest.approx(30, abs=1e-9)
    tilted = {'kind': 'vector', 'points': ((0, 0, 0), (1, 0, 1))}
    assert guides.angle(tilted, p1, m) == pytest.approx(45, abs=1e-9)
    assert sqrt(sum(c * c for c in guides.direction(tilted, m))) == pytest.approx(1)


def test_guides_as_text_and_back():
    m = benzene_and_tilted_ring(0)
    symbols = [a.symbol for a in m.atoms]
    made = [{'kind': 'vector', 'atoms': (4, 1)}, {'kind': 'vector', 'points': ((0, 0, 0), (1.5, 0, -0.25))},
            {'kind': 'normal', 'atoms': tuple(range(6))}, {'kind': 'plane', 'atoms': (6, 7, 8, 9, 10, 11)}]
    written = guides.text(made, 'ru')
    assert guides.text(made[:1], 'en') == 'vector 5 2'  # in English when the program is not in Russian
    assert written.splitlines() == ['вектор 5 2', 'вектор 0 0 0 1.5 0 -0.25', 'нормаль 1-6', 'плоскость 7-12']
    assert guides.parse(written, 12) == made
    again = guides.parse('vector C3 C1  # from C3\nplane C1, C2, C3\n\nнормаль 1 2 3 4', 12, symbols)
    assert again[0] == {'kind': 'vector', 'atoms': (2, 0)} and again[1]['atoms'] == (0, 1, 2)
    assert guides.describe(made[0], symbols) == 'вектор C5 → C2'
    assert guides.describe(made[3], symbols) == 'плоскость C7–C12'
    for bad in ('стрелка 1 2', 'вектор 1', 'вектор 1 1', 'плоскость 1 2', 'вектор 1 2 3 1 2 3', 'нормаль 1-99'):
        with pytest.raises(ValueError):
            guides.parse(bad, 12)
