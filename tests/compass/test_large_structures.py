"""Structures of up to MAX_ATOMS (2000) atoms; the searches of close atoms and of bonds go by cells
(azimuth/core.near_pairs), so they stay fast."""

import random
import time
from math import dist

import pytest

from azimuth.core import MAX_ATOMS, Atom, Molecule, near_pairs, read_xyz
from modules.compass.chemistry import builder, structure_tools as st
from modules.compass.chemistry.cleanup import clean


def water_box(n):
    k = round(n ** (1 / 3)) + 1
    atoms = []
    for i in range(k):
        for j in range(k):
            for m in range(k):
                x, y, z = 3.1 * i, 3.1 * j, 3.1 * m
                atoms += [Atom('O', x, y, z), Atom('H', x + 0.96, y, z), Atom('H', x - 0.24, y + 0.93, z)]
    return Molecule('box', tuple(atoms[: 3 * n]))


def test_near_pairs_are_those_of_all_pairs():
    rnd = random.Random(5)
    for n, cutoff in ((40, 0.1), (300, 1.5), (500, 3.4)):
        points = [(rnd.uniform(-8, 8), rnd.uniform(-8, 8), rnd.uniform(-8, 8)) for _ in range(n)]
        brute = [(j, i) for i in range(n) for j in range(i) if dist(points[i], points[j]) <= cutoff]
        assert near_pairs(points, cutoff) == brute


def test_bonds_by_cells_are_those_of_all_pairs():
    m = water_box(120)
    atoms = m.atoms
    brute = tuple((j, i, 1) for i, a in enumerate(atoms) for j, b in enumerate(atoms[:i])
                  if dist(a.position, b.position) <= 1.22 * (builder.RADII.get(a.symbol, 0.8) + builder.RADII.get(b.symbol, 0.8)))
    assert builder.connections(m) == brute and len(brute) == 240


def test_two_thousand_atoms_open_fast():
    assert MAX_ATOMS == 2000
    m = water_box(MAX_ATOMS // 3)
    start = time.perf_counter()
    read_xyz(m.xyz())
    bonds = builder.connections(m)
    st.overlapping(m)
    assert time.perf_counter() - start < 1.0  # was about 2 s (1 s each for the distances and the bonds)
    assert len(bonds) == 2 * (MAX_ATOMS // 3)
    cleaned, _, _ = clean(Molecule(m.title, m.atoms, bonds), steps=50)
    assert len(cleaned.atoms) == len(m.atoms)


def test_the_limit_is_said():
    m = water_box(MAX_ATOMS // 3 + 1)
    with pytest.raises(ValueError, match=str(MAX_ATOMS)):
        read_xyz(m.xyz())
    close = '3\nw\nO 0 0 0\nH 0.05 0 0\nH -0.24 0.93 0\n'
    with pytest.raises(ValueError, match='0,1'):
        read_xyz(close)
