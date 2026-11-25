"""The shape of a crystal by BFDH: the faces of the planes with the largest spacings — as «BFDH
Morphology» of Mercury (CCDC).

§1 THEORY
    The law of Bravais, Friedel, Donnay and Harker: the faces of a crystal are the lattice planes (hkl) with the
    largest interplanar spacing d; the growth rate of a face is inversely proportional to d, so a face stands at the
    distance ∝ 1/d from the centre, and the crystal is the intersection of the half-spaces x·n̂(hkl) ≤ 1/d. Donnay and
    Harker: d is that of the first reflection n(hkl) the space group lets through — a systematic absence (a centring, a
    screw axis, a glide plane) divides d by the smallest n with n(hkl) present (the {100} of an fcc lattice grows as
    {200}). A reflection h is systematically absent when an operation (R, t) of the group keeps it, hR = h, with h·t
    not a whole number. Simple cubic: the cube {100}; fcc (rock salt): the octahedron {111} cut by the cube {200};
    bcc: the rhombic dodecahedron {110}. The shape ignores the bonds and the solvent (the attachment energy does not);
    for many molecular crystals it is near the shape grown from the vapour.
§2 ALGORITHM
    The reciprocal rows B = (A⁻¹)ᵀ, 1/d(h) = |h B|; every primitive h with |h_i| ≤ MAX_INDEX, its d_eff = d / n; the
    PLANES planes with the largest d_eff (and every plane as far as the last of them); the vertices — the points
    where three planes meet inside all the half-spaces; a face — a plane with three vertices or more, in order around
    its centre. Forms — the faces at the same distance (within 1e-6), named by the face with the largest h, k, l.
§4 SPECIFICATION
    morphology(crystal) -> Shape(vertices Å⁻¹, faces [Face(hkl, vertices, normal, area, d)], forms [Form(hkl, d,
    n, faces, area share)], volume); d — that of the reflection n·(hkl) that counts; absent(h, operations) -> bool;
    hkl_text(h).
§7 TESTS tests/compass/test_crystal_morphology.py — the cube of CsCl, the octahedron and cube of rock salt, the
    rhombic dodecahedron of a bcc lattice, a monoclinic plate of benzoic acid.
"""

from dataclasses import dataclass, field
from fractions import Fraction
from itertools import combinations, product
from math import gcd

import numpy as np

MAX_INDEX = 3
PLANES = 40
TOL = 1e-7


@dataclass
class Face:
    hkl: tuple
    vertices: list
    normal: tuple
    area: float
    d: float


@dataclass
class Form:
    hkl: tuple
    d: float
    n: int  # the reflection n·(hkl) that counts (Donnay–Harker)
    faces: int
    share: float  # of the surface


@dataclass
class Shape:
    vertices: list
    faces: list
    forms: list
    volume: float
    cell: list = field(default_factory=list)


def absent(h, operations):
    for rows, shifts in operations:
        hr = tuple(sum(h[i] * rows[i][j] for i in range(3)) for j in range(3))
        if hr == tuple(h):
            phase = sum(Fraction(h[j]) * Fraction(shifts[j]) for j in range(3))
            if phase.denominator != 1:
                return True
    return False


def _name(h):
    return tuple(int(x) for x in h)


def morphology(crystal):
    rows = np.array(crystal.cell.vectors(), dtype=float)
    recip = np.linalg.inv(rows).T
    candidates = []
    for h in product(range(-MAX_INDEX, MAX_INDEX + 1), repeat=3):
        if h == (0, 0, 0) or gcd(gcd(abs(h[0]), abs(h[1])), abs(h[2])) != 1:
            continue
        for n in range(1, 7):
            if not absent(tuple(n * x for x in h), crystal.operations):
                g = np.array(h, dtype=float) @ recip
                d = 1.0 / np.linalg.norm(g)
                candidates.append((d / n, h, n, g / np.linalg.norm(g)))
                break
    candidates.sort(key=lambda c: -c[0])
    if len(candidates) > PLANES:
        last = candidates[PLANES - 1][0]
        candidates = [c for c in candidates if c[0] >= last - 1e-9]
    normals = np.array([c[3] for c in candidates])
    limits = np.array([1.0 / c[0] for c in candidates])
    vertices = []
    for i, j, k in combinations(range(len(candidates)), 3):
        m = normals[[i, j, k]]
        if abs(np.linalg.det(m)) < 1e-9:
            continue
        v = np.linalg.solve(m, limits[[i, j, k]])
        if np.all(normals @ v <= limits + TOL) and not any(np.linalg.norm(v - w) < 1e-7 for w in vertices):
            vertices.append(v)
    p = np.array(vertices)
    faces = []
    for i, (d, h, n, normal) in enumerate(candidates):
        on = [m for m in range(len(p)) if abs(float(p[m] @ normal) - limits[i]) < 1e-6]
        if len(on) < 3:
            continue
        c = p[on].mean(axis=0)
        e1 = p[on[0]] - c
        e1 /= np.linalg.norm(e1)
        e2 = np.cross(normal, e1)
        on.sort(key=lambda m: float(np.arctan2((p[m] - c) @ e2, (p[m] - c) @ e1)))
        area = 0.0
        for a in range(1, len(on) - 1):
            area += float(np.linalg.norm(np.cross(p[on[a]] - p[on[0]], p[on[a + 1]] - p[on[0]]))) / 2
        if area < 1e-9:
            continue
        faces.append(Face(_name(h), on, tuple(float(x) for x in normal), area, float(d)))  # d of n·(hkl)
    total = sum(f.area for f in faces) or 1.0
    distance = {c[1]: 1.0 / c[0] for c in candidates}
    groups = {}
    for f in faces:
        groups.setdefault(round(distance[f.hkl], 6), []).append(f)
    forms = []
    for key in sorted(groups):
        members = groups[key]
        best = max((f.hkl for f in members), key=lambda h: (sum(x >= 0 for x in h), h))
        first = next(c for c in candidates if c[1] == best)
        forms.append(Form(best, float(first[0]), int(first[2]), len(members),
                          sum(f.area for f in members) / total))
    volume = 0.0
    for f in faces:
        for a in range(1, len(f.vertices) - 1):
            volume += abs(float(np.dot(p[f.vertices[0]], np.cross(p[f.vertices[a]], p[f.vertices[a + 1]])))) / 6
    return Shape([tuple(float(x) for x in v) for v in p], faces, forms, volume, rows.tolist())


def hkl_text(h):
    """(1 −1 0) with the signs written out when one is negative, 110 else (the bar over a digit renders badly)."""
    if all(x >= 0 for x in h):
        return ''.join(str(x) for x in h)
    return ' '.join(str(x).replace('-', '−') for x in h)
