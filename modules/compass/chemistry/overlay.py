"""Overlay of two structures with the atoms in any order: matching, alignment, deviations.

§1 THEORY
    Two structures of the same composition (a conformer, an optimized and a starting geometry, the
    same molecule from two programs) are compared by the best rigid superposition: the atoms of the
    second structure B are paired with those of the reference A (an atom only with an atom of the same
    element, one to one) and B is turned and shifted so that the root-mean-square distance between
    paired atoms, RMSD = sqrt(sum |a_i - (b_p(i) R + t)|^2 / N), is smallest. For a fixed pairing the
    best proper rotation is given by the Kabsch solution (SVD of the cross-covariance of the centred
    coordinates; t moves the centroid of B onto that of A); for a fixed orientation the best pairing
    is an assignment problem per element (minimum sum of squared distances, Hungarian method). The
    joint problem is solved by alternating the two (each step does not increase the RMSD) from a set
    of starting orientations; it finds the global optimum when one of the starts lies in its basin.
    Starting orientations: the order of the files when the elements are in the same order; the
    principal axes of the two atom clouds (equal weights) with all sign choices; for clouds with two
    equal moments, turns about the unique axis; for a cloud with three equal moments (CH4, SF6), a
    uniform set of rotations. A mirror image is matched only if allowed (then the improper Kabsch
    solution is used where it is better), so enantiomers are told apart by default.
§2 ALGORITHM
    1. Validate: both non-empty, finite coordinates (|x| <= 1e6 A), the same multiset of elements.
    2. Centre A and B. Starts: R = Eb S Ea^T (Ea, Eb: eigenvectors of the gyration tensors, S: a
       diagonal of signs with det R = +1, or any sign when mirrors are allowed); with a degenerate
       pair of moments (relative difference < DEGENERATE) also R = Eb S T_k Ea^T, T_k a turn by
       k * 15 deg about the unique axis (also when two moments are only NEAR — within 30 % — of each other, for each
       such pair: noise turns the axes of the copy); with three: SPHERE_STARTS rotations of a Fibonacci sphere
       sampling of axes times 8 angles. The identity is a start when the element orders agree.
    3. With more than SCREEN starts, each is scored by the RMS distance of every B atom to the
       nearest A atom of its element (no one-to-one pairing; cheap), and the SCREEN best are kept.
    4. For each kept start: pair per element by the Hungarian method on squared distances, Kabsch on
       the pairing, repeat until the pairing no longer changes (at most ITERATIONS times).
    5. The result with the smallest RMSD; ties (within 1e-9 A) keep the earlier start, so the file
       order wins for equivalent pairings.
§3 APPLICATIONS
    Compass: «Наложить структуру для сравнения…» (modules/compass/actions/overlay_actions.py).
§4 SPECIFICATION
    assignment(cost) -> list p, row i assigned to column p[i], minimum sum of cost[i, p[i]];
    cost a finite square array.
    superimpose(reference, other, allow_mirror=False) -> Overlay:
      order[i] index in other of the atom paired with reference atom i;
      aligned Molecule: the atoms of other in the order of reference, moved onto reference;
      renumbered Molecule: the atoms of other in the order of reference, original coordinates;
      rotation (3x3, row-vector convention x R), translation (3), rmsd, rmsd_heavy (None if fewer
      than 2 non-hydrogen atoms), deviations[i] |a_i - aligned_i|, mirrored (det R < 0),
      same_order (order is the identity).
    Raises ValueError for an empty structure, bad coordinates or a different composition.
§5 PROCEDURES - below.
§6 NOTES
    Equal weights for all atoms (as docs/features/GEOMETRY_COMPARISON.md); a mass-weighted fit would favour
    heavy atoms and is not used. The alternation is a local method: for two very different
    conformers the pairing found may be the best among the starts, not the chemically intended one
    (Chemcraft has the same limitation); the deviations show where. Bonds are not used for the
    pairing. Run time: an assignment is O(n^3) with numpy rows (n atoms of one element); a few
    tenths of a second for 200 atoms.
§7 TESTS
    tests/compass/test_overlay.py: the Hungarian method against all permutations of random matrices; a
    structure shuffled, turned and shifted is matched with RMSD ~ 0 (every library molecule);
    against the minimum over all element-preserving permutations (exhaustive Kabsch) for small
    molecules with noise; never worse than the pairing used to make a noisy copy (all library
    molecules, noise 0.1 and 0.3 A); spherical tops and an octahedron in 25 random orientations;
    enantiomers apart unless mirrors are allowed; the composition check. Control breakages caught:
    the proper-rotation correction of Kabsch, the Hungarian comparison, the turns about the unique
    axis, the screening size. Not shown necessary by these tests (kept as insurance for strongly
    distorted structures): the repeated pairing (one pass converged in every case) and the extra
    rotations for three equal moments (the sign starts sufficed).
§8' ROBUSTNESS / ERRORS
    float64 SVD; RMSD of an exact copy ~ 1e-13 A for molecules of 1-60 atoms (sums of n terms of
    rounding 1e-16 * |x| ~ 1e-15). DEGENERATE = 0.05 is generous on purpose: an extra set of starts
    costs only time. Coordinates beyond 1e6 A are refused (overflow of squared sums is far beyond).
"""

from dataclasses import dataclass, replace
from math import cos, pi, sin, sqrt

import numpy as np

from azimuth.core import Atom
from azimuth.i18n import tr

DEGENERATE = 0.05  # relative difference of two moments treated as equal
NEAR = 0.3  # relative difference below which the axes of a noisy copy may be turned: turns about the third axis too
ITERATIONS = 30
SCREEN = 12
SPHERE_STARTS = 48  # axes; times 8 angles
TIE = 1e-9


@dataclass(frozen=True)
class Overlay:
    order: tuple
    aligned: object
    renumbered: object
    rotation: tuple
    translation: tuple
    rmsd: float
    rmsd_heavy: float | None
    deviations: tuple
    mirrored: bool
    same_order: bool


def assignment(cost):
    """Hungarian method (shortest augmenting paths with potentials) for a square cost matrix."""
    c = np.asarray(cost, dtype=float)
    if c.ndim != 2 or c.shape[0] != c.shape[1]:
        raise ValueError('square matrix expected')
    if not np.isfinite(c).all():
        raise ValueError('finite costs expected')
    n = c.shape[0]
    u = np.zeros(n + 1)
    v = np.zeros(n + 1)
    p = np.zeros(n + 1, dtype=int)  # p[j]: row (1-based) assigned to column j; column 0 is the root
    way = np.zeros(n + 1, dtype=int)
    for i in range(1, n + 1):
        p[0] = i
        j0 = 0
        minv = np.full(n + 1, np.inf)
        used = np.zeros(n + 1, dtype=bool)
        while True:
            used[j0] = True
            i0 = p[j0]
            free = ~used[1:]
            current = c[i0 - 1] - u[i0] - v[1:]
            better = free & (current < minv[1:])
            minv[1:][better] = current[better]
            way[1:][better] = j0
            candidates = np.where(free, minv[1:], np.inf)
            j1 = int(np.argmin(candidates)) + 1
            delta = candidates[j1 - 1]
            columns = np.nonzero(used)[0]
            u[p[columns]] += delta
            v[columns] -= delta
            minv[~used] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while j0:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
    result = [0] * n
    for j in range(1, n + 1):
        result[p[j] - 1] = j - 1
    return result


def _kabsch(x, y, allow_mirror):
    """R (row vectors) minimising |x R - y| for centred x, y; improper only if allowed and better."""
    u, _, vt = np.linalg.svd(x.T @ y)
    proper = np.eye(3)
    proper[2, 2] = 1.0 if np.linalg.det(u @ vt) >= 0 else -1.0
    rotation = u @ proper @ vt
    if allow_mirror:
        free = u @ vt
        if np.sum((x @ free - y) ** 2) < np.sum((x @ rotation - y) ** 2) - 1e-15:
            return free
    return rotation


def _frame(x):
    values, vectors = np.linalg.eigh(x.T @ x / len(x))
    return values, vectors


def _turn(axis, angle):
    a = np.asarray(axis, dtype=float)
    a = a / np.linalg.norm(a)
    k = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + sin(angle) * k + (1 - cos(angle)) * (k @ k)


def _starts(x, y, allow_mirror):
    """Starting rotations R (row vectors: y R ~ x) from the principal axes of the centred clouds."""
    va, ea = _frame(x)
    vb, eb = _frame(y)
    scale = max(va.max(), vb.max(), 1e-12)
    gaps = [
        min(abs(va[1] - va[0]), abs(vb[1] - vb[0])) / scale < DEGENERATE,
        min(abs(va[2] - va[1]), abs(vb[2] - vb[1])) / scale < DEGENERATE,
    ]
    # two moments that are only close (thiophene, 1.24 / 1.99 Å², with noise of 0.3 Å per coordinate: 1.46 / 1.87,
    # and the in-plane axes of the copy turned by 53°) also get turns about the third axis — the principal axes alone
    # left every start far from the true orientation
    near = [
        min(abs(va[1] - va[0]), abs(vb[1] - vb[0])) / scale < NEAR,
        min(abs(va[2] - va[1]), abs(vb[2] - vb[1])) / scale < NEAR,
    ]
    turns = [np.eye(3)]
    if all(gaps):  # three equal moments: a spread of rotations
        count = SPHERE_STARTS
        for k in range(count):
            z = 1 - 2 * (k + 0.5) / count
            r = sqrt(max(0.0, 1 - z * z))
            phi = k * pi * (3 - sqrt(5))
            axis = (r * cos(phi), r * sin(phi), z)
            turns += [_turn(axis, m * pi / 4) for m in range(1, 9)]
    else:  # two equal (or close) moments: turns about the third axis (the frame column apart)
        for close, column in ((gaps[0] or near[0], 2), (gaps[1] or near[1], 0)):
            if close:
                axis = np.zeros(3)
                axis[column] = 1.0
                turns += [_turn(axis, m * pi / 12) for m in range(1, 24)]
    out = []
    for sx in (1, -1):
        for sy in (1, -1):
            for sz in (1, -1):
                signs = np.diag([sx, sy, sz])
                for t in turns:
                    rotation = eb @ signs @ t @ ea.T
                    if allow_mirror or np.linalg.det(rotation) > 0:
                        out.append(rotation)
    return out


def _groups(symbols):
    found = {}
    for i, s in enumerate(symbols):
        found.setdefault(s, []).append(i)
    return found


def _pair(x, moved, ga, gb):
    """order[i] = index of the moved atom paired with x[i], per element by the Hungarian method."""
    order = [0] * len(x)
    for symbol, rows in ga.items():
        cols = gb[symbol]
        d = ((x[rows][:, None, :] - moved[cols][None, :, :]) ** 2).sum(axis=2)
        for r, c in zip(rows, assignment(d)):
            order[r] = cols[c]
    return order


def _screen_score(x, moved, ga, gb):
    total = 0.0
    for symbol, rows in ga.items():
        d = ((moved[gb[symbol]][:, None, :] - x[rows][None, :, :]) ** 2).sum(axis=2)
        total += float(d.min(axis=1).sum())
    return total


def _coordinates(molecule, name):
    if molecule is None or not molecule.atoms:
        raise ValueError(tr('Нет атомов для сравнения: ') + name)
    c = np.array([a.position for a in molecule.atoms], dtype=float)
    if not np.isfinite(c).all() or np.abs(c).max() > 1e6:
        raise ValueError(tr('Некорректные координаты для сравнения: ') + name)
    return c


def composition_difference(reference, other):
    """'' if the element counts agree, else a short description of the difference."""

    def counts(m):
        out = {}
        for a in m.atoms:
            out[a.symbol] = out.get(a.symbol, 0) + 1
        return out

    ca, cb = counts(reference), counts(other)
    if ca == cb:
        return ''
    parts = [f'{s}: {ca.get(s, 0)} / {cb.get(s, 0)}' for s in sorted(set(ca) | set(cb)) if ca.get(s, 0) != cb.get(s, 0)]
    return ', '.join(parts)


def superimpose(reference, other, allow_mirror=False):
    """Best superposition of other onto reference with automatic pairing of the atoms (see §4)."""
    a = _coordinates(reference, tr('модель'))
    b = _coordinates(other, tr('сравниваемая структура'))
    difference = composition_difference(reference, other)
    if difference:
        raise ValueError(tr('Состав структур различается (модель / файл): ') + difference)
    sa = [atom.symbol for atom in reference.atoms]
    sb = [atom.symbol for atom in other.atoms]
    ga, gb = _groups(sa), _groups(sb)
    ca, cb = a.mean(axis=0), b.mean(axis=0)
    x, y = a - ca, b - cb
    n = len(a)
    starts = []
    if sa == sb:
        starts.append(('identity', list(range(n))))
    starts += [('rotation', r) for r in _starts(x, y, allow_mirror)]
    if len(starts) > SCREEN:
        head = starts[:1] if starts[0][0] == 'identity' else []
        rest = starts[len(head) :]
        rest.sort(key=lambda s: _screen_score(x, y @ s[1], ga, gb))
        starts = head + rest[: SCREEN - len(head)]
    best = None
    for kind, value in starts:
        if kind == 'identity':
            order = value
            rotation = _kabsch(y[order], x, allow_mirror)
        else:
            rotation = value
            order = _pair(x, y @ rotation, ga, gb)
            rotation = _kabsch(y[order], x, allow_mirror)
        for _ in range(ITERATIONS):
            new = _pair(x, y @ rotation, ga, gb)
            if new == order:
                break
            order = new
            rotation = _kabsch(y[order], x, allow_mirror)
        rmsd = float(np.sqrt(np.mean(np.sum((y[order] @ rotation - x) ** 2, axis=1))))
        if best is None or rmsd < best[0] - TIE:
            best = (rmsd, order, rotation)
    rmsd, order, rotation = best
    fitted = y[order] @ rotation + ca
    translation = ca - cb @ rotation
    deviations = np.sqrt(np.sum((fitted - a) ** 2, axis=1))
    heavy = [i for i, s in enumerate(sa) if s != 'H']
    rmsd_heavy = float(np.sqrt(np.mean(deviations[heavy] ** 2))) if len(heavy) >= 2 else None
    atoms_aligned = tuple(Atom(sa[i], *map(float, fitted[i])) for i in range(n))
    atoms_renumbered = tuple(other.atoms[j] for j in order)
    bonds = _remap_bonds(other.bonds, order)
    return Overlay(
        order=tuple(int(j) for j in order),
        aligned=replace(other, atoms=atoms_aligned, bonds=bonds),
        renumbered=replace(other, atoms=atoms_renumbered, bonds=bonds),
        rotation=tuple(tuple(map(float, row)) for row in rotation),
        translation=tuple(map(float, translation)),
        rmsd=rmsd,
        rmsd_heavy=rmsd_heavy,
        deviations=tuple(map(float, deviations)),
        mirrored=bool(np.linalg.det(rotation) < 0),
        same_order=list(order) == list(range(n)),
    )


def _remap_bonds(bonds, order):
    """Bonds of other (its numbering) in the numbering of reference: new index i holds old order[i]."""
    if bonds is None:
        return None
    new = {old: i for i, old in enumerate(order)}
    return tuple(sorted((min(new[i], new[j]), max(new[i], new[j]), k) for i, j, k in bonds))


def renumber(molecule, order):
    """molecule with atom i taken from old index order[i] (bonds follow)."""
    if sorted(order) != list(range(len(molecule.atoms))):
        raise ValueError('order must be a permutation of the atoms')
    return replace(
        molecule, atoms=tuple(molecule.atoms[j] for j in order), bonds=_remap_bonds(molecule.bonds, order)
    )
