"""Frames of a vibration and geometries displaced along a mode (modules/spectrum/readers/vibration_data.py).

Oracles, independent of the tested code: the formula x(t) = x0 + A sin(2 pi k / n) v with the largest |v| = 1,
written out here; half a period later every atom is displaced the opposite way; the largest displacement of
one atom over the frames is A (n divisible by 4); the two displaced geometries are mirror images about the
equilibrium; the ratios of the displacements of the atoms are those of the printed vectors; the XYZ frames
read back with the program's XYZ reader (formats.read_xyz_frames) give the same coordinates to the 8 printed
decimals (5e-9 A).
"""

from math import dist, pi, sin

import pytest

from modules.compass.chemistry.formats import read_xyz_frames
from modules.spectrum.readers.vibration_data import (
    Vibration,
    displaced_along,
    frames_xyz,
    normalized_vectors,
    vibration_frames,
)
from azimuth.core import Atom, Molecule

WATER = Molecule('w', (Atom('O', 0.0, 0.0, 0.1173), Atom('H', 0.0, 0.7572, -0.4692), Atom('H', 0.0, -0.7572, -0.4692)))
# a symmetric-stretch-like mode as ORCA prints it (not normalized)
MODE = Vibration(7, 3657.0, ((0.0, 0.0, -0.0687), (0.0, -0.5771, 0.5452), (0.0, 0.5771, 0.5452)), 4.2)


def test_frames_follow_the_formula_and_the_half_period():
    v = normalized_vectors(MODE)
    assert max(sum(c * c for c in row) ** 0.5 for row in v) == pytest.approx(1.0, abs=1e-15)
    frames = vibration_frames(WATER, v, 0.3, 20)
    assert len(frames) == 20 and frames[0].atoms == WATER.atoms
    for k, frame in enumerate(frames):
        s = 0.3 * sin(2 * pi * k / 20)
        for a, b, row in zip(frame.atoms, WATER.atoms, v):
            assert a.position == pytest.approx(tuple(p + s * d for p, d in zip(b.position, row)), abs=1e-12)
    for k in range(10):
        for a, b, c in zip(frames[k].atoms, frames[k + 10].atoms, WATER.atoms):
            assert tuple(x - z for x, z in zip(a.position, c.position)) == pytest.approx(
                tuple(z - y for y, z in zip(b.position, c.position)), abs=1e-12
            )
    largest = max(dist(a.position, b.position) for f in frames for a, b in zip(f.atoms, WATER.atoms))
    assert largest == pytest.approx(0.3, abs=1e-12)


def test_displaced_geometries_are_mirror_images_with_the_mode_ratios():
    v = normalized_vectors(MODE)
    plus = displaced_along(WATER, v, 0.2, 1)
    minus = displaced_along(WATER, v, 0.2, -1)
    shifts = [dist(a.position, c.position) for a, c in zip(plus.atoms, WATER.atoms)]
    assert max(shifts) == pytest.approx(0.2, abs=1e-12)
    printed = [sum(x * x for x in row) ** 0.5 for row in MODE.vectors]
    for s, p in zip(shifts, printed):
        assert s / max(shifts) == pytest.approx(p / max(printed), abs=1e-12)
    for a, b, c in zip(plus.atoms, minus.atoms, WATER.atoms):
        assert tuple((x + y) / 2 for x, y in zip(a.position, b.position)) == pytest.approx(c.position, abs=1e-12)


def test_xyz_frames_read_back():
    frames = vibration_frames(WATER, normalized_vectors(MODE), 0.25, 12)
    text = frames_xyz(frames, 'mode 7, 3657.00 cm-1')
    back = read_xyz_frames(text)
    assert len(back) == 12 and back[3].title.endswith('frame 4/12')
    for f, g in zip(frames, back):
        for a, b in zip(f.atoms, g.atoms):
            assert a.symbol == b.symbol and dist(a.position, b.position) < 5e-9 * 3**0.5


def test_refusals():
    v = normalized_vectors(MODE)
    for bad in (dict(amplitude=0.0), dict(amplitude=3.0), dict(count=3), dict(count=241)):
        args = {'amplitude': 0.3, 'count': 20, **bad}
        with pytest.raises(ValueError):
            vibration_frames(WATER, v, args['amplitude'], args['count'])
    with pytest.raises(ValueError):
        displaced_along(WATER, v, 0.2, 0)
    with pytest.raises(ValueError):
        displaced_along(WATER, v, -0.1, 1)
    with pytest.raises(ValueError):
        vibration_frames(WATER, v[:2], 0.3, 20)
