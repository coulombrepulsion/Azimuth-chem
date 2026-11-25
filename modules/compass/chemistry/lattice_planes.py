"""The lattice planes (hkl) drawn in a block of cells — the planes of a reflection of the powder pattern
seen in the crystal, as Mercury shows «hkl planes».

§1 THEORY The planes (hkl) of a lattice are h x + k y + l z = m (x, y, z — fractions of the cell, m — whole numbers);
    the distance between neighbours d = 1/|h a* + k b* + l c*|, the d of the reflection hkl in the law of Bragg λ = 2 d
    sin θ (the reflection 2h 2k 2l is the family with every second plane between those of hkl).
§2 ALGORITHM
    For a block of n₁ × n₂ × n₃ cells: m from the least to the greatest h·f over the corners of the block; the plane
    meets the 12 edges of the block in 3 to 6 points (the fractions where h·f = m on an edge), merged, ordered by the
    angle around their centre in the plane — a polygon (Cartesian, Å).
§4 SPECIFICATION
    planes(cell, hkl, n=(1, 1, 1), limit=40) -> [polygon [(x, y, z)]]; spacing(cell, hkl) -> d Å; ValueError for
    (0 0 0) or more than limit planes.
§7 TESTS tests/compass/test_lattice_planes.py — (100) of a cube: two squares; (111): triangles and hexagons; the
spacing.
"""

from itertools import product

import numpy as np


def spacing(cell, hkl):
    rows = np.array(cell.vectors(), dtype=float)
    g = np.array(hkl, dtype=float) @ np.linalg.inv(rows).T
    return float(1.0 / np.linalg.norm(g))


def planes(cell, hkl, n=(1, 1, 1), limit=40):
    h = np.array(hkl, dtype=float)
    if not h.any():
        raise ValueError('(0 0 0) is not a plane')
    rows = np.array(cell.vectors(), dtype=float)
    n = np.array(n, dtype=float)
    corners = np.array(list(product(*[(0.0, k) for k in n])))
    values = corners @ h
    lo, hi = int(np.ceil(values.min() - 1e-9)), int(np.floor(values.max() + 1e-9))
    if hi - lo + 1 > limit:
        raise ValueError(f'more than {limit} planes in the block')
    edges = []
    for i in range(8):
        for j in range(i + 1, 8):
            if np.sum(np.abs(corners[i] - corners[j]) > 0) == 1:
                edges.append((corners[i], corners[j]))
    normal = h @ np.linalg.inv(rows).T
    normal /= np.linalg.norm(normal)
    out = []
    for m in range(lo, hi + 1):
        points = []
        for a, b in edges:
            va, vb = a @ h - m, b @ h - m
            if abs(va) < 1e-9 and abs(vb) < 1e-9:
                points += [a, b]
            elif va * vb <= 0 and abs(va - vb) > 1e-12:
                points.append(a + (b - a) * va / (va - vb))
        unique = []
        for p in points:
            if not any(np.linalg.norm(p - q) < 1e-7 for q in unique):
                unique.append(p)
        if len(unique) < 3:
            continue
        xyz = np.array(unique) @ rows
        centre = xyz.mean(axis=0)
        e1 = xyz[0] - centre
        if np.linalg.norm(e1) < 1e-9:
            continue
        e1 /= np.linalg.norm(e1)
        e2 = np.cross(normal, e1)
        order = np.argsort([np.arctan2((x - centre) @ e2, (x - centre) @ e1) for x in xyz])
        out.append([tuple(float(c) for c in xyz[k]) for k in order])
    return out
