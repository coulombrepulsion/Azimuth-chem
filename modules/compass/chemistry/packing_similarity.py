"""How alike two crystals of one compound are packed — a cluster of molecules compared, as «Crystal
Packing Similarity» (COMPACK, Chisholm & Motherwell 2005) of Mercury.

§1 THEORY
    Two structures of one compound (two polymorphs, two files of one form, the experiment and a calculation) are
    packed alike when a molecule has the same neighbours at the same places and in the same orientations. The cluster
    of a crystal — the molecule of the asymmetric unit and its nearest molecules by the distance of the centroids, N
    in all (15, as in Mercury). The clusters are laid on each other by the central molecules (the second cluster also
    inverted: the central molecule of the other file may be the inverted copy) (rotation and shift of
    least squares, Kabsch 1976, after the atoms of the two are paired by element); a molecule of the first cluster is
    matched when the nearest molecule of the second (by centroid) is within 20 % of its distance from the centre and
    turned by at most 20° (the tolerances of COMPACK). Then the matched molecules are laid on each other together and
    the RMSD of their atoms is the measure: n/N matched, RMSD_n in Å — 15/15 and some tenths of Å: the same packing.
    Atoms H are left out (their positions in X-ray structures are poor).
§2 ALGORITHM
    cluster(crystal): crystal_symmetry.molecules, their copies by the lattice vectors (|n_i| ≤ 2), the molecule nearest
    the centre of the cell of the largest formula as the centre, the N nearest of the same formula by centroid.
    Pairing two molecules: the principal axes of each (the four right-handed sign choices) give starting rotations;
    then the nearest atom of the same element for each atom, Kabsch, repeated to a fixed point; the best RMSD wins.
§4 SPECIFICATION
    cluster(crystal, n=15) -> [(symbols, xyz (k × 3) Å)] (the centre first); compare(a, b, n=15) -> Similarity(matched,
    n, rmsd, rows [(distance from the centre Å, shift Å, angle °, matched)]); ValueError when the formulas differ or a
    crystal has no molecules (a salt, a framework).
§7 TESTS tests/compass/test_packing_similarity.py — benzoic acid with itself (15/15, 0 Å), with itself in another
    setting (15/15), with its cell stretched by 4 % (15/15, RMSD > 0), with another packing (fewer matched).
"""

from dataclasses import dataclass

import numpy as np

N = 15
DISTANCE_TOLERANCE = 0.20
ANGLE_TOLERANCE = 20.0


@dataclass
class Similarity:
    matched: int
    n: int
    rmsd: float
    rows: list


def _formula(symbols):
    out = {}
    for s in symbols:
        out[s] = out.get(s, 0) + 1
    return tuple(sorted(out.items()))


def cluster(crystal, n=N):
    from modules.compass.chemistry import crystal as cr
    from modules.compass.chemistry import crystal_symmetry as cs

    packing = cs.molecules(cr.main_part(crystal))
    if not packing.molecules:
        raise ValueError('no molecules in the crystal (a salt or a framework)')
    rows = np.array(crystal.cell.vectors(), dtype=float)
    kinds = {}
    for m in packing.molecules:
        kinds.setdefault(_formula(s for s, _ in m if s not in ('H', 'D')), []).append(m)
    formula = max(kinds, key=lambda f: (sum(c for _, c in f), len(kinds[f])))
    copies = []
    for m in kinds[formula]:
        symbols = [s for s, _ in m if s not in ('H', 'D')]
        frac = np.array([f for s, f in m if s not in ('H', 'D')], dtype=float)
        for shift in np.ndindex(5, 5, 5):
            xyz = (frac + np.array(shift) - 2) @ rows
            copies.append((symbols, xyz, xyz.mean(axis=0)))
    middle = np.array([0.5, 0.5, 0.5]) @ rows
    centre = min(copies, key=lambda c: float(np.linalg.norm(c[2] - middle)))
    copies.sort(key=lambda c: float(np.linalg.norm(c[2] - centre[2])))
    return [(c[0], c[1]) for c in copies[:n]]


def _kabsch(p, q):
    """R, t with R p + t ≈ q (rows of points)."""
    pc, qc = p.mean(axis=0), q.mean(axis=0)
    h = (p - pc).T @ (q - qc)
    u, _, vt = np.linalg.svd(h)
    d = np.sign(np.linalg.det(vt.T @ u.T)) or 1.0
    r = vt.T @ np.diag([1, 1, d]) @ u.T
    return r, qc - r @ pc


def _pair(sa, a, sb, b):
    """For each atom of a (after the move), the index of the nearest atom of b of the same element (one to one)."""
    out = [-1] * len(a)
    taken = set()
    d = np.linalg.norm(a[:, None, :] - b[None, :, :], axis=2)
    for i, j in sorted(((i, j) for i in range(len(a)) for j in range(len(b)) if sa[i] == sb[j]),
                       key=lambda ij: d[ij]):
        if out[i] < 0 and j not in taken:
            out[i] = j
            taken.add(j)
    return out


def _fits(sa, a, sb, b):
    """[(R, t, rmsd, pairs)] laying molecule a on molecule b from each of the four starting rotations of the principal
    axes (a molecule near a symmetric shape — benzoic acid turned about its long axis — fits several ways)."""
    found = []
    ca, cb = a - a.mean(axis=0), b - b.mean(axis=0)
    _, _, va = np.linalg.svd(ca)
    _, _, vb = np.linalg.svd(cb)
    for signs in ((1, 1, 1), (1, -1, -1), (-1, 1, -1), (-1, -1, 1)):
        r = vb.T @ np.diag(signs) @ va
        if np.linalg.det(r) < 0:
            r = vb.T @ np.diag([signs[0], signs[1], -signs[2]]) @ va
        t = b.mean(axis=0) - r @ a.mean(axis=0)
        r, t, rmsd, pairs = _refine(sa, a, sb, b, r, t)
        if pairs is not None and not any(np.allclose(r, x[0], atol=1e-6) for x in found):
            found.append((r, t, rmsd, pairs))
    if not found:
        raise ValueError('the molecules have other atoms')
    return sorted(found, key=lambda x: x[2])


def _refine(sa, a, sb, b, r, t, rounds=20):
    """The nearest atom of the same element for each atom, Kabsch, repeated to a fixed point."""
    for _ in range(rounds):
        pairs = _pair(sa, a @ r.T + t, sb, b)
        if min(pairs) < 0:
            return r, t, float('inf'), None
        new_r, new_t = _kabsch(a, b[pairs])
        if np.allclose(new_r, r, atol=1e-10) and np.allclose(new_t, t, atol=1e-10):
            break
        r, t = new_r, new_t
    moved = a @ r.T + t
    pairs = _pair(sa, moved, sb, b)
    if min(pairs) < 0:
        return r, t, float('inf'), None
    return r, t, float(np.sqrt(((moved - b[pairs]) ** 2).sum(axis=1).mean())), pairs


def _angle(r):
    return float(np.degrees(np.arccos(np.clip((np.trace(r) - 1) / 2, -1.0, 1.0))))


def _match(first, second, r, t):
    centre_a = first[0][1].mean(axis=0)
    centres_b = np.array([xyz.mean(axis=0) for _, xyz in second])
    rows, pairs_all = [], []
    for symbols, xyz in first:
        moved = xyz @ r.T + t
        c = moved.mean(axis=0)
        k = int(np.argmin(np.linalg.norm(centres_b - c, axis=1)))
        shift = float(np.linalg.norm(centres_b[k] - c))
        reach = float(np.linalg.norm(xyz.mean(axis=0) - centre_a))
        # the turn of the molecule after the clusters are laid together: one pairing by the nearest atoms, no new start
        local, _, _, pairs = _refine(symbols, moved, second[k][0], second[k][1], np.eye(3), np.zeros(3), rounds=1)
        angle = _angle(local) if pairs is not None else 180.0
        ok = pairs is not None and shift <= max(DISTANCE_TOLERANCE * reach, 0.5) and angle <= ANGLE_TOLERANCE
        rows.append((reach, shift, angle, ok))
        if ok:
            pairs_all.append((xyz, second[k][1][pairs]))
    return rows, pairs_all


def compare(a, b, n=N):
    first, second = cluster(a, n), cluster(b, 2 * n)  # the second larger: a tie at the edge of the first is found
    if _formula(first[0][0]) != _formula(second[0][0]):
        raise ValueError('the crystals hold other molecules')
    best = None
    # the cluster of the second crystal and its mirror image: the central molecule picked there may be the inverted
    # copy of the first one (a centrosymmetric crystal) — its surroundings are then the inverted ones (as COMPACK
    # allows the inversion)
    for other in (second, [(symbols, -xyz) for symbols, xyz in second]):
        for r, t, _, _ in _fits(first[0][0], first[0][1], other[0][0], other[0][1]):
            rows, pairs_all = _match(first, other, r, t)
            if best is None or len(pairs_all) > len(best[1]):
                best = (rows, pairs_all)
    rows, pairs_all = best
    if not pairs_all:
        return Similarity(0, len(first), float('nan'), rows)
    p = np.vstack([x for x, _ in pairs_all])
    q = np.vstack([y for _, y in pairs_all])
    rr, tt = _kabsch(p, q)
    rmsd = float(np.sqrt((((p @ rr.T + tt) - q) ** 2).sum(axis=1).mean()))
    return Similarity(len(pairs_all), len(first), rmsd, rows)
