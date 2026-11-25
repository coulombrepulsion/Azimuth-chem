"""Rings of the molecules of a crystal: centroids, planes and π–π stacking.

§1 THEORY A planar ring of 5–7 atoms (aromatic rings, their heteroatom analogues) has a centroid Cg (the mean of its
    atoms) and a mean plane (the least-squares plane through them; its normal is the singular vector of the smallest
    singular value of the centred coordinates). Two rings of different molecules stack (π–π) when their centroids are
    near and their planes nearly parallel; the geometry is told by the distance Cg···Cg (d), the angle α between the
    planes, the perpendicular distance of Cg(I) from the plane of J (d⊥) and the offset (slippage) √(d² − d⊥²) — the
    quantities of PLATON (Spek, Acta Cryst. D65, 148, 2009) and of the review of Janiak (J. Chem. Soc., Dalton Trans.
    2000, 3885): face- to-face stacking at d about 3.3–3.8 Å, usually offset by 1–2 Å.
§2 ALGORITHM
    rings(walk): in each molecule (a component without periodicity) the cycles of 5–7 atoms of the bond graph without a
    chord (no bond between two atoms of the cycle that are not neighbours in it — the smallest rings of fused systems),
    each once, of the elements C, N, O, S, Se, B, P, kept when planar (the largest distance of an atom from the mean
    plane at most PLANAR); their atoms unwrapped (crystal_symmetry.walk shifts), the centroid and the normal.
    stacking(crystal): every pair of rings (I in the cell copy, J moved by the 27 lattice vectors {−1, 0, 1}³; a ring
    and itself only moved) of different copies of molecules with d <= CG_LIMIT and α <= ANGLE_LIMIT; sorted by d.
    grouped(found): the pairs that the symmetry repeats (the same labels, d within 1e-3 Å) are one row with a count.
§3 APPLICATIONS
    modules/compass/actions/crystal_actions.py: the table «π–π-стопки» of the «Контакты» window.
§4 SPECIFICATION
    Ring(atoms (indices of the cell), labels, centroid (Å), normal); rings(walk) -> tuple of Ring;
    Stack(first, second (ring indices), shift, distance, angle, perpendicular, offset); stacking(crystal, factor=None)
    -> (rings, tuple of Stack); grouped(rings, found) -> [(text 'Cg(C1–C6)···Cg(C1–C6)', d, α, d⊥, offset, count)].
§5 PROCEDURES - below.
§6 NOTES CG_LIMIT = 4.0 Å and ANGLE_LIMIT = 20°: the face-to-face range of Janiak (d < 3.8 Å) with a margin; PLATON
    lists up to 6 Å — the longer ones are not stacking. Rings of infinite frameworks (graphite layers) are not looked
    for. C–H···π — a hydrogen bonded to a carbon near the centroid of a ring of another molecule: H···Cg ≤ CH_PI_LIMIT
    (3.0 Å), the angle C–H···Cg ≥ 120° and the angle between H→Cg and the normal of the ring ≤ 30° (the usual criteria
    of the X–H···π contacts of PLATON; to be compared with its manual before a release). model_marks(molecule): the
    rings, stacks and C–H···π of the model on the screen (its own bonds), for the marks on the model.
§7 TESTS
    tests/compass/test_crystal_rings.py.
§8' ROBUSTNESS / ERRORS
    A crystal without molecules or rings gives empty tuples; the cycle search is bounded by the ring size (7).
"""

from dataclasses import dataclass

RING_ELEMENTS = ('C', 'N', 'O', 'S', 'Se', 'B', 'P')
PLANAR = 0.1  # Å
CG_LIMIT = 4.0  # Å
ANGLE_LIMIT = 20.0  # degrees
SHIFTS = tuple((i, j, k) for i in (-1, 0, 1) for j in (-1, 0, 1) for k in (-1, 0, 1))


@dataclass(frozen=True)
class Ring:
    atoms: tuple
    labels: tuple
    centroid: tuple
    normal: tuple
    component: int


@dataclass(frozen=True)
class Stack:
    first: int
    second: int
    shift: tuple
    distance: float
    angle: float
    perpendicular: float
    offset: float


def _neighbours(w, k):
    return {m for m, _ in w.edges[k]}


def cycles(adjacent, symbols, members):
    """The chordless cycles of 5–7 atoms of RING_ELEMENTS among members, each once; adjacent(k) -> set of neighbours."""
    allowed = {k for k in members if symbols[k] in RING_ELEMENTS}
    found = {}
    for start in sorted(allowed):
        stack = [(start, (start,))]
        while stack:
            k, path = stack.pop()
            for m in adjacent(k):
                if m not in allowed or m < start:
                    continue
                if m == start and len(path) >= 5:
                    key = frozenset(path)
                    if key not in found and len(key) == len(path):
                        found[key] = path
                    continue
                if m in path or len(path) >= 7:
                    continue
                stack.append((m, path + (m,)))
    out = []
    for path in found.values():
        n = len(path)
        if not any(path[(i + j) % n] in adjacent(path[i]) for i in range(n) for j in range(2, n - 1)):
            out.append(path)
    return out


def _plane(points):
    import numpy as np

    centre = points.mean(axis=0)
    _, _, vt = np.linalg.svd(points - centre)
    normal = vt[-1]
    return centre, normal, float(np.abs((points - centre) @ normal).max())


def _cycles(w, members):
    return cycles(lambda k: _neighbours(w, k), [a[0] for a in w.atoms], members)


def rings(walk):
    import numpy as np

    w = walk
    members = {}
    for i, c in enumerate(w.component):
        if not w.periods[c]:
            members.setdefault(c, []).append(i)
    out = []
    for c, atoms in members.items():
        for path in _cycles(w, atoms):
            points = np.array([(w.frac[k] + np.array(w.shift[k])) @ w.vectors for k in path])
            centre, normal, worst = _plane(points)
            if worst > PLANAR:
                continue
            labels = tuple(w.atoms[k][4] or f'{w.atoms[k][0]}{k + 1}' for k in path)
            out.append(Ring(tuple(path), labels, tuple(float(x) for x in centre), tuple(float(x) for x in normal), c))
    return tuple(out)


def stacking(crystal, factor=None):
    import numpy as np

    from modules.compass.chemistry import crystal_symmetry as cs

    w = cs.walk(crystal, factor)
    found_rings = rings(w)
    stacks = []
    vectors = np.array(w.vectors, dtype=float)
    for i, a in enumerate(found_rings):
        ca, na = np.array(a.centroid), np.array(a.normal)
        for j, b in enumerate(found_rings):
            if j < i:
                continue
            for s in SHIFTS:
                if a.component == b.component and s == (0, 0, 0):
                    continue  # one copy of a molecule (the same ring, or two rings of it)
                if i == j and s <= (0, 0, 0):
                    continue  # a ring with its own copy: each pair once
                cb = np.array(b.centroid) + np.array(s, dtype=float) @ vectors
                d = float(np.linalg.norm(cb - ca))
                if d > CG_LIMIT:
                    continue
                cos = abs(float(na @ np.array(b.normal)))
                angle = float(np.degrees(np.arccos(min(1.0, cos))))
                if angle > ANGLE_LIMIT:
                    continue
                perpendicular = abs(float((cb - ca) @ np.array(b.normal)))
                offset = float(np.sqrt(max(d * d - perpendicular * perpendicular, 0.0)))
                stacks.append(Stack(i, j, s, d, angle, perpendicular, offset))
    return found_rings, tuple(sorted(stacks, key=lambda x: x.distance))


def _natural(label):
    import re

    return [int(x) if x.isdigit() else x for x in re.split(r'(\d+)', label)]


def ring_text(ring):
    """'Cg(C1–C6)': the first and the last label of the ring in natural order."""
    labels = sorted(ring.labels, key=_natural)
    return f'Cg({labels[0]}–{labels[-1]})'


def grouped(found_rings, found):
    rows = []
    for x in found:
        t = f'{ring_text(found_rings[x.first])}···{ring_text(found_rings[x.second])}'
        for row in rows:
            if row[0] == t and abs(row[1] - x.distance) < 1e-3:
                row[5] += 1
                break
        else:
            rows.append([t, x.distance, x.angle, x.perpendicular, x.offset, 1])
    return [tuple(r) for r in rows]


# -- C–H···π and the marks on the model ------------------------------------------------------------------
CH_PI_LIMIT = 3.0  # Å, H···Cg
CH_PI_ANGLE = 120.0  # degrees, C–H···Cg at least
CH_PI_GAMMA = 30.0  # degrees, between H→Cg and the normal of the ring at most


@dataclass(frozen=True)
class HPi:
    hydrogen: int
    carbon: int
    ring: int
    shift: tuple
    distance: float
    angle: float
    perpendicular: float
    offset: float


def _angle(a, b, c):
    import numpy as np

    u, v = a - b, c - b
    nu, nv = np.linalg.norm(u), np.linalg.norm(v)
    if nu < 1e-9 or nv < 1e-9:
        return 0.0
    return float(np.degrees(np.arccos(np.clip(u @ v / (nu * nv), -1.0, 1.0))))


def _ch_pi(hydrogens, centroids, normals, cart):
    """(h, c, ring, H···Cg, angle C–H···Cg, d⊥, offset) for H (with their C) near ring centroids, by the criteria."""
    import numpy as np

    out = []
    for h, c, ph in hydrogens:
        for r, (cg, normal) in enumerate(zip(centroids, normals)):
            d = float(np.linalg.norm(cg - ph))
            if d > CH_PI_LIMIT:
                continue
            angle = _angle(cart[c], ph, cg)
            gamma = float(np.degrees(np.arccos(min(1.0, abs(float((cg - ph) @ normal)) / d))))
            if angle < CH_PI_ANGLE or gamma > CH_PI_GAMMA:
                continue
            perpendicular = abs(float((ph - cg) @ normal))
            out.append((h, c, r, d, angle, perpendicular, float(np.sqrt(max(d * d - perpendicular ** 2, 0.0)))))
    return out


def ch_pi(crystal, factor=None):
    """(rings, tuple of HPi): the C–H of the cell near the centroids of rings of other copies of molecules."""
    import numpy as np

    from modules.compass.chemistry import crystal_symmetry as cs

    w = cs.walk(crystal, factor)
    found_rings = rings(w)
    vectors = np.array(w.vectors, dtype=float)
    cart = {}
    hydrogens = []
    for k, atom in enumerate(w.atoms):
        if atom[0] != 'H' or w.periods[w.component[k]]:
            continue
        carbons = [(m, s) for m, s in w.edges[k] if w.atoms[m][0] == 'C']
        if not carbons:
            continue
        m, s = carbons[0]
        ph = (w.frac[k] + np.array(w.shift[k])) @ vectors
        cart[(k, m)] = (w.frac[m] + np.array(w.shift[k]) + np.array(s)) @ vectors  # the C next to this H
        hydrogens.append((k, m, ph))
    out = []
    for shift in SHIFTS:
        moved = np.array(shift, dtype=float) @ vectors
        centroids = [np.array(r.centroid) + moved for r in found_rings]
        normals = [np.array(r.normal) for r in found_rings]
        for h, c, r, d, angle, perpendicular, offset in _ch_pi(hydrogens, centroids, normals,
                                                              {c: cart[(h, c)] for h, c, _ in hydrogens}):
            if found_rings[r].component == w.component[h] and shift == (0, 0, 0):
                continue  # within one copy of a molecule
            out.append(HPi(h, c, r, shift, d, angle, perpendicular, offset))
    return found_rings, tuple(sorted(out, key=lambda x: x.distance))


def ch_pi_grouped(crystal, found_rings, found):
    from modules.compass.chemistry import crystal as cr

    atoms = cr.unit_cell(crystal)

    def label(k):
        return atoms[k][4] or f'{atoms[k][0]}{k + 1}'

    rows = []
    for x in found:
        t = f'{label(x.carbon)}–{label(x.hydrogen)}···{ring_text(found_rings[x.ring])}'
        for row in rows:
            if row[0] == t and abs(row[1] - x.distance) < 1e-3:
                row[5] += 1
                break
        else:
            rows.append([t, x.distance, x.angle, x.perpendicular, x.offset, 1])
    return [tuple(r) for r in rows]


def model_marks(molecule):
    """The rings of the model (Cartesian; its bonds) with the π–π stacks and C–H···π between fragments:
    {'rings': [(centroid, [corner points])], 'stacks': [(cg, cg)], 'ch_pi': [(h point, cg)]} — for the viewer."""
    import numpy as np

    from modules.compass.chemistry.builder import connections

    n = len(molecule.atoms)
    neighbours = [set() for _ in range(n)]
    for i, j, _ in connections(molecule):
        neighbours[i].add(j)
        neighbours[j].add(i)
    fragment = [-1] * n
    for start in range(n):
        if fragment[start] >= 0:
            continue
        stack = [start]
        fragment[start] = start
        while stack:
            k = stack.pop()
            for m in neighbours[k]:
                if fragment[m] < 0:
                    fragment[m] = start
                    stack.append(m)
    cart = np.array([a.position for a in molecule.atoms], dtype=float).reshape(n, 3)
    symbols = [a.symbol for a in molecule.atoms]
    found = []
    for path in cycles(lambda k: neighbours[k], symbols, range(n)):
        centre, normal, worst = _plane(cart[list(path)])
        if worst <= PLANAR:
            found.append((path, centre, normal))
    marks = {'rings': [(tuple(c), [tuple(cart[k]) for k in path]) for path, c, _ in found], 'stacks': [], 'ch_pi': []}
    for i, (pa, ca, na) in enumerate(found):
        for pb, cb, nb in found[i + 1:]:
            if fragment[pa[0]] == fragment[pb[0]]:
                continue
            d = float(np.linalg.norm(cb - ca))
            angle = float(np.degrees(np.arccos(min(1.0, abs(float(na @ nb))))))
            if d <= CG_LIMIT and angle <= ANGLE_LIMIT:
                marks['stacks'].append((tuple(ca), tuple(cb)))
    hydrogens = []
    for k in range(n):
        if symbols[k] == 'H':
            carbons = [m for m in neighbours[k] if symbols[m] == 'C']
            if carbons:
                hydrogens.append((k, carbons[0], cart[k]))
    for h, c, r, *_ in _ch_pi(hydrogens, [x[1] for x in found], [x[2] for x in found], cart):
        if fragment[h] != fragment[found[r][0][0]]:
            marks['ch_pi'].append((tuple(cart[h]), tuple(found[r][1])))
    return marks
