"""The first Brillouin zone of a crystal and the path of its band structure.

§1 THEORY
    The reciprocal lattice of a lattice with rows a_i: b_i·a_j = 2π δ_ij, B = 2π (A⁻¹)ᵀ (Å⁻¹). The first Brillouin
    zone is the Wigner–Seitz cell of the reciprocal lattice of the primitive cell: the points k nearer to Γ than to any
    other lattice point G — k·G ≤ |G|²/2 for every G ≠ 0. Its volume is (2π)³/V of the primitive cell: the cube of the
    simple cubic lattice, the truncated octahedron of fcc (14 faces, 24 vertices), the rhombic dodecahedron of bcc
    (12 faces, 14 vertices), the hexagonal prism of hP. The points of high symmetry and the path between them are those
    of the band structures of Quantum ESPRESSO (modules/sextant/qe_paths.LATTICES: Setyawan & Curtarolo, 2010) — in
    fractions of the reciprocal vectors of the conventional cell of the file.
§2 ALGORITHM
    zone(crystal): the primitive rows (crystal.primitive_basis), the reciprocal lattice points G = n·B (|n_i| ≤ 2), the
    30 shortest give the planes; each triple of planes meeting in a point inside all the half-spaces is a vertex
    (merged within 1e-6 Å⁻¹); a face — a plane with three vertices or more, its vertices in order around its centre.
    path_points(crystal) -> the labelled points (Cartesian, Å⁻¹) and the runs of the path.
§4 SPECIFICATION
    Zone(vertices, faces [[vertex index]], volume, reciprocal rows of the primitive cell, of the conventional cell,
    kind, points {label: (x, y, z)}, runs [[label]]); zone(crystal) -> Zone; describe(zone) -> 'Γ–X–M–Γ–R–X | M–R'.
§7 TESTS
    tests/compass/test_brillouin.py — the cube, the truncated octahedron, the rhombic dodecahedron and the hexagonal
    prism: their vertices, faces and volume; every point of the path in the zone or on its surface.
"""

from dataclasses import dataclass, field
from itertools import combinations

TOL = 1e-6
PLANES = 30


@dataclass
class Zone:
    vertices: list
    faces: list
    volume: float
    reciprocal: list  # rows b_i of the primitive cell, Å⁻¹
    conventional: list  # rows b_i of the cell of the file, Å⁻¹
    kind: str
    points: dict = field(default_factory=dict)
    runs: list = field(default_factory=list)
    general: bool = False


def zone(crystal):
    import numpy as np

    from modules.compass.chemistry import crystal as cr
    from modules.sextant import qe_paths

    rows = np.array(crystal.cell.vectors(), dtype=float)
    basis = cr.primitive_basis(crystal)
    primitive = rows if basis is None else basis @ rows
    recip = 2 * np.pi * np.linalg.inv(primitive).T
    conventional = 2 * np.pi * np.linalg.inv(rows).T
    n = np.array([(i, j, k) for i in range(-2, 3) for j in range(-2, 3) for k in range(-2, 3) if (i, j, k) != (0, 0, 0)],
                 dtype=float)
    g = n @ recip
    half = (g * g).sum(axis=1) / 2
    order = np.argsort(half, kind='stable')[:PLANES]
    vertices = []
    for i, j, k in combinations(order, 3):
        m = g[[i, j, k]]
        if abs(np.linalg.det(m)) < 1e-9:
            continue
        v = np.linalg.solve(m, half[[i, j, k]])
        if np.all(g @ v <= half + TOL * (1 + half)) and not any(np.linalg.norm(v - w) < 1e-6 for w in vertices):
            vertices.append(v)
    p = np.array(vertices)
    faces = []
    for i in order:
        on = [m for m in range(len(p)) if abs(float(p[m] @ g[i]) - half[i]) < 1e-6 * (1 + half[i])]
        if len(on) < 3:
            continue
        c = p[on].mean(axis=0)
        normal = g[i] / np.linalg.norm(g[i])
        e1 = p[on[0]] - c
        e1 /= np.linalg.norm(e1)
        e2 = np.cross(normal, e1)
        on.sort(key=lambda m: float(np.arctan2((p[m] - c) @ e2, (p[m] - c) @ e1)))
        faces.append(on)
    volume = 0.0
    for f in faces:
        for a in range(1, len(f) - 1):
            volume += abs(float(np.dot(p[f[0]], np.cross(p[f[a]], p[f[a + 1]])))) / 6
    kind = qe_paths.lattice(crystal)
    labelled, runs = qe_paths.LATTICES[kind]
    points = {label: tuple(float(x) for x in np.array(f, dtype=float) @ conventional) for label, f in labelled.items()}
    return Zone([tuple(float(x) for x in v) for v in p], faces, volume, recip.tolist(), conventional.tolist(), kind,
                points, [list(r) for r in runs], kind == 'other')


def describe(z):
    return ' | '.join('–'.join(run) for run in z.runs)


def inside(z, point, tol=1e-6):
    """True when point (Å⁻¹) is in the zone or on its surface."""
    import numpy as np

    recip = np.array(z.reciprocal)
    n = np.array([(i, j, k) for i in range(-2, 3) for j in range(-2, 3) for k in range(-2, 3) if (i, j, k) != (0, 0, 0)],
                 dtype=float)
    g = n @ recip
    return bool(np.all(g @ np.array(point) <= (g * g).sum(axis=1) / 2 + tol))
