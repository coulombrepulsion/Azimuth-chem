"""«Выровнять геометрию»: a quick, simple force field for a hand-built structure.

Terms (all harmonic, energies in arbitrary units):
    bonds k_b (r − r0)², r0 = single-bond length (builder.bond_length) × 1, 0.915 (aromatic),
               0.875 (double), 0.79 (triple) (C–C 1.52, benzene 1.39, C=C 1.33, C≡C 1.20 Å); the orders are
               perceived from the valences when the structure has hydrogens (editing.perceived_orders),
               so a rough hand-built geometry does not decide them;
    angles k_a (cos θ − cos θ0)², θ0 by the VSEPR shape of the central atom (editing.shape:
               steric number = neighbours + lone pairs) — 180° linear, 120° trigonal, otherwise
               109.47° (104.5° for O and S with two neighbours, 107° for N and P with three);
    rings in a five-membered ring the ring angles are 108° and the exocyclic angles of a flat
               atom 126°; the heteroatom of an aromatic five-ring (N–H, O, S with single bonds while
               the other four ring atoms carry multiple bonds) is flat, the ring itself too (planarity of
               every four consecutive ring atoms), and its bonds have aromatic lengths: C–C × 0.915,
               heteroatom–C × 0.95 of a single bond;
    planarity k_p V² for an atom with three neighbours and a double or aromatic bond (or flat as above),
               V = (a − c)·((b − c) × (d − c)) (the volume they span: zero when flat);
    repulsion k_r (d0 − d)² for d < d0 between atoms more than two bonds apart,
               d0 = 0.75 (R_i + R_j) with van der Waals radii (Bondi; 1.8 Å otherwise).
    torsions about a single bond between two tetrahedral atoms, one of them without lone pairs
               (C, Si, Ge, Sn; the other C-like or N, P, O, S), not in a three- or four-membered ring (hydrogens
               may still be missing: the shape comes from the bond orders): k₃ (1 + cos 3φ) over every
               dihedral a–j–k–d (shared by the n pairs, a barrier of 2 k₃ per bond: staggered, not eclipsed)
               and, when a and d are both heavy atoms and the bond is not in a ring, k₁ (1 + cos φ)
               (anti before gauche, as in butane: gauche stays a local minimum near 62°); about a double or
               aromatic bond between two flat atoms k₂ (1 − cos 2φ) per dihedral — the bond stays flat and
               keeps cis or trans as built.
An atom with five or six electron domains (SF6, PF5, SF4, XeF4, BrF5) gets octahedral or trigonal-bipyramidal
angle targets (90°, 120°, 180°; the trans pairs are the straightest ones of the start geometry) instead of 109.5°;
the ends of an allene C=C=C are perpendicular (k₂ (1 + cos 2φ)); a single bond that joins two flat atoms, or a
flat atom and an O or S with two neighbours, stays flat (K_CONJ (1 − cos 2φ); s-trans for C=C–C=C and O=C–C=O,
syn O=C–O–X for acids and esters), a biaryl bond turns by about 45° (K_CONJ (1 + cos 4φ)), and a CH3 next to a
C=X keeps one bond in the plane of C=X, eclipsing it (k₃ (1 − cos 3φ)). An O–O or S–S bond has no torsion (its
minimum is neither staggered nor flat): formats.from_smiles turns it to the measured dihedral before tidying. formats.from_smiles puts the hydrogens again by the
tidied heavy atoms when strain is left (a hydrogen placed while a ring was open, as in naphthalene).
No electrostatics: the result is a tidy starting structure for a quantum-chemical
optimization, not a minimum of any real energy. Minimisation: FIRE (fast inertial relaxation), at
most 2000 steps, until the largest force is below 1e-3. Only the chosen atoms move if a selection is
given; otherwise the result is put back on the input by a rigid fit (no drift, no turning).

Straighten(molecule, moving) turns acyclic chains to anti before tidying (SMILES, a new atom);
tidy_new(molecule, new) tidies a structure right after an atom or a group was added in Compass: the
missing hydrogens are added for the time of the tidying (so a bare skeleton gets tetrahedral angles), the
new atoms are turned anti to the chain, and only the new atoms, those hydrogens and the end atoms next to
them move; everything else stays where it was. Structures over LIVE_LIMIT atoms are left as they are.
"""

from math import cos, radians

import numpy as np

from azimuth.core import Atom, Molecule, near_pairs
from modules.compass.chemistry.builder import bond_length, checked, covalent_single
from modules.compass.chemistry.editing import VALENCE_ELECTRONS, aromatize, perceived_orders, shape

VDW = {'H': 1.20, 'C': 1.70, 'N': 1.55, 'O': 1.52, 'F': 1.47, 'P': 1.80, 'S': 1.80, 'Cl': 1.75, 'Br': 1.85, 'I': 1.98}
K_BOND, K_ANGLE, K_REP, K_PLANE = 300.0, 60.0, 20.0, 40.0
# torsions (per bond: 3-fold staggering, 1-fold anti preference of a heavy-atom chain, 2-fold flatness)
K_T3, K_T1, K_T2 = 2.0, 0.6, 4.0
K_CONJ = 1.5  # a conjugated single bond stays flat (weaker than a double bond, so crowding may twist it)
JITTER = 0.02  # Å
LIVE_LIMIT = 300  # atoms: above this tidy_new does nothing (the repulsion list grows as n²)
# r0 / single-bond length, in the middle of the windows of editing.bonds_with_orders
FACTOR = {1: 1.0, 1.5: 0.915, 2: 0.875, 3: 0.79}


def _ideal_angle(symbol, orders):
    form = shape(symbol, orders)  # VSEPR steric number (editing.shape)
    if form == 'linear':
        return 180.0
    if form == 'trigonal':
        return 120.0
    if symbol in ('O', 'S', 'Se') and len(orders) == 2:
        return 104.5
    if symbol in ('N', 'P', 'As') and len(orders) == 3:
        return 107.0
    return 109.4712206


NOBLE = {'Kr': 8, 'Xe': 8}  # XeF4 square, XeF2 linear (steric number only)


def _steric(symbol, orders):
    """VSEPR steric number (neighbours + lone pairs); 0 for an element without a valence-electron count."""
    valence = VALENCE_ELECTRONS.get(symbol, NOBLE.get(symbol))
    if valence is None:
        return 0
    return len(orders) + max(0, int((valence - sum(orders)) // 2))


def _hypervalent_angles(x, c, ns, steric):
    """Target angles of an atom with five or six electron domains, {(a, b): degrees}.
    Six domains (SF6, BrF5, XeF4): octahedral, the pairs that are nearest to straight in the start geometry are
    trans (180°, each atom in one such pair at most), the rest 90°. Five domains (PF5, SF4, ClF3): trigonal
    bipyramid, lone pairs equatorial; the straightest pair is axial (180°), axial–equatorial 90°, equatorial
    pairs 120°."""
    def angle(a, b):
        u, v = x[a] - x[c], x[b] - x[c]
        return float(np.dot(u, v) / max(np.linalg.norm(u) * np.linalg.norm(v), 1e-12))
    pairs = sorted(((angle(a, b), (min(a, b), max(a, b))) for n, a in enumerate(ns) for b in ns[n + 1:]))
    target = {}
    if steric == 6:
        used = set()
        for _, (a, b) in pairs:  # the most negative cosine first: the straightest pairs
            if a not in used and b not in used:
                used.update((a, b))
                target[(a, b)] = 180.0
        for _, pair in pairs:
            target.setdefault(pair, 90.0)
    else:
        axial = set(pairs[0][1])
        for _, (a, b) in pairs:
            if (a, b) == pairs[0][1]:
                target[(a, b)] = 180.0
            else:
                target[(a, b)] = 90.0 if axial & {a, b} else 120.0
    return target


def _rings5(neighbours):
    """Five-membered rings as tuples of atoms in ring order (each ring once)."""
    found = {}
    for start in range(len(neighbours)):
        stack = [(start, (start,))]
        while stack:
            node, path = stack.pop()
            if len(path) == 5:
                if start in neighbours[node]:
                    found.setdefault(frozenset(path), path)
                continue
            for nxt in neighbours[node]:
                if nxt > start and nxt not in path:
                    stack.append((nxt, path + (nxt,)))
    return list(found.values())


def terms(molecule):
    atoms = molecule.atoms
    bonds = aromatize(len(atoms), perceived_orders(molecule))  # Kekulé rings of a file or SMILES too
    b_i, b_j, b_r0 = [], [], []
    neighbours = [[] for _ in atoms]
    orders = [[] for _ in atoms]
    for i, j, o in bonds:
        b_i.append(i)
        b_j.append(j)
        s, t = atoms[i].symbol, atoms[j].symbol
        # single bonds: builder.bond_length (with its measured exceptions); multiple: radii x FACTOR
        r0 = bond_length(s, t, 1) if o == 1 else covalent_single(s, t) * FACTOR.get(o, 1.0)
        b_r0.append(r0)
        neighbours[i].append(j)
        neighbours[j].append(i)
        orders[i].append(o)
        orders[j].append(o)
    # five-membered rings: ring angles 108° (a regular pentagon), exocyclic angles of a
    # flat ring atom 126°, and the heteroatom of an aromatic five-ring (pyrrole N-H, furan O,
    # thiophene S: single bonds only, the other four atoms carry multiple bonds) is flat too
    ring_pairs = [set() for _ in atoms]  # (a, b) with a-c-b consecutive in a five-ring
    flat_rings = []  # aromatic five-rings: all five atoms in one plane
    flat = [_ideal_angle(atoms[c].symbol, orders[c]) == 120.0 for c in range(len(atoms))]
    in_ring5 = [False] * len(atoms)
    bond_index = {(min(i, j), max(i, j)): n for n, (i, j) in enumerate(zip(b_i, b_j))}
    for ring in _rings5(neighbours):
        multiple = [any(o in (2, 1.5) for o in orders[k]) for k in ring]
        hetero = None
        if multiple.count(False) == 1 and atoms[ring[multiple.index(False)]].symbol in ('N', 'O', 'S', 'Se', 'P'):
            hetero = ring[multiple.index(False)]
            flat[hetero] = True
            flat_rings.append(ring)
            # aromatic bond lengths: ring C-C as aromatic, hetero-C 0.95 of a single bond
            # (thiophene C-S 1.71, furan C-O 1.36, pyrrole C-N 1.37 Å)
            for n in range(5):
                a, b = ring[n], ring[(n + 1) % 5]
                k = bond_index[(min(a, b), max(a, b))]
                factor = 0.95 if hetero in (a, b) else FACTOR[1.5]
                b_r0[k] = covalent_single(atoms[a].symbol, atoms[b].symbol) * factor
        for n, c in enumerate(ring):
            in_ring5[c] = True
            if c == hetero and len(neighbours[c]) == 2:
                continue  # its ring angle follows from the flat ring (thiophene 92°, furan 106°)
            a, b = ring[n - 1], ring[(n + 1) % 5]
            ring_pairs[c].add((min(a, b), max(a, b)))
    a_a, a_c, a_b, a_c0 = [], [], [], []
    x0 = np.array([a.position for a in atoms], dtype=float)
    for c, ns in enumerate(neighbours):
        if len(ns) < 2:
            continue
        steric = _steric(atoms[c].symbol, orders[c])
        if steric in (5, 6) and len(ns) >= 2:  # SF6, PF5, SF4, XeF4… (was 109.5° for every pair)
            for (a, b), angle in _hypervalent_angles(x0, c, ns, steric).items():
                a_a.append(a)
                a_c.append(c)
                a_b.append(b)
                a_c0.append(cos(radians(angle)))
            continue
        if flat[c] and in_ring5[c] and len(ns) == 2 and not ring_pairs[c]:
            continue  # the heteroatom of an aromatic five-ring: no angle target (see above)
        ideal = 120.0 if flat[c] else _ideal_angle(atoms[c].symbol, orders[c])
        # a tetrahedral atom in two three-membered rings (spiropentane): 137° between the bonds of the two rings (D2d).
        # With 109.5° the spiro atom twisted its rings to 96° and 125° (C2v). One ring (cyclopropane) stays as it was
        in3 = {n: m for n in ns for m in ns if m != n and m in neighbours[n]} if not flat[c] else {}
        if len(in3) < 4:
            in3 = {}
        for x in range(len(ns)):
            for y in range(x + 1, len(ns)):
                pair = (min(ns[x], ns[y]), max(ns[x], ns[y]))
                angle = (
                    108.0 if pair in ring_pairs[c] else (126.0 if flat[c] and in_ring5[c] and len(ns) == 3 else ideal)
                )
                if in3 and in3.get(ns[x]) != ns[y]:
                    angle = 137.0  # a bond of each ring
                a_a.append(ns[x])
                a_c.append(c)
                a_b.append(ns[y])
                a_c0.append(cos(radians(angle)))
    p_c, p_a, p_b, p_d = [], [], [], []
    for c, ns in enumerate(neighbours):
        if len(ns) == 3 and flat[c]:
            p_c.append(c)
            p_a.append(ns[0])
            p_b.append(ns[1])
            p_d.append(ns[2])
    for ring in flat_rings:  # four consecutive ring atoms span no volume
        for n in range(5):
            q, r, s, u = (ring[(n + k) % 5] for k in range(4))
            p_c.append(r)
            p_a.append(q)
            p_b.append(s)
            p_d.append(u)
    close = set()
    for i, ns in enumerate(neighbours):
        close.update((min(i, j), max(i, j)) for j in ns)
        for x in ns:
            for y in ns:
                if x < y:
                    close.add((x, y))
    r_i, r_j, r_d0 = [], [], []
    if len(atoms) <= LIVE_LIMIT:
        candidates = ((i, j) for i in range(len(atoms)) for j in range(i + 1, len(atoms)))
    else:  # a large structure — only pairs that start within reach (the longest d0 and 1.5 Å of travel)
        reach = 0.75 * 2 * max(VDW.get(a.symbol, 1.8) for a in atoms) + 1.5
        candidates = near_pairs([a.position for a in atoms], reach)
    for i, j in candidates:
        if (i, j) not in close:
            r_i.append(i)
            r_j.append(j)
            r_d0.append(0.75 * (VDW.get(atoms[i].symbol, 1.8) + VDW.get(atoms[j].symbol, 1.8)))
    t_a, t_j, t_k, t_d, t_n, t_f, t_s = [], [], [], [], [], [], []
    order_of = {(min(i, j), max(i, j)): o for i, j, o in bonds}
    for (j, k), o in order_of.items():
        ends_j = [a for a in neighbours[j] if a != k]
        ends_k = [d for d in neighbours[k] if d != j]
        if not ends_j or not ends_k:
            continue
        if o == 1 and not flat[j] and not flat[k]:
            # tetrahedral on both sides, one end C-like (C–C, C–N, C–O, C–S…; not H2O2 or N2H4, whose minima
            # are not staggered), and not in a three- or four-membered ring
            if not _staggered_bond(atoms, neighbours, flat, orders, j, k):
                continue
            if set(ends_j) & set(ends_k) or any(set(neighbours[a]) & set(ends_k) for a in ends_j):
                continue
            pairs = [(a, d) for a in ends_j for d in ends_k]
            ring = _in_ring(neighbours, j, k)
            for a, d in pairs:
                t_a.append(a), t_j.append(j), t_k.append(k), t_d.append(d)
                t_n.append(3), t_f.append(K_T3 / len(pairs)), t_s.append(1.0)
                if not ring and atoms[a].symbol != 'H' and atoms[d].symbol != 'H':
                    heavy = sum(atoms[x].symbol != 'H' for x in ends_j) * sum(atoms[x].symbol != 'H' for x in ends_k)
                    t_a.append(a), t_j.append(j), t_k.append(k), t_d.append(d)
                    t_n.append(1), t_f.append(K_T1 / heavy), t_s.append(1.0)
        elif o in (2, 1.5) and flat[j] and flat[k]:
            for a in ends_j:
                for d in ends_k:
                    t_a.append(a), t_j.append(j), t_k.append(k), t_d.append(d)
                    t_n.append(2), t_f.append(K_T2), t_s.append(-1.0)
        elif o == 1 and not _in_ring(neighbours, j, k):
            # conjugation keeps a single bond flat when it joins two flat atoms (styrene, butadiene,
            # acetophenone, oxalic acid) or a flat atom and an O with two neighbours (esters, acids);
            # a tetrahedral C next to a C=X keeps one of its bonds in the plane of C=X (acetyl CH3)
            for c, e, ends_c, ends_e in ((j, k, ends_j, ends_k), (k, j, ends_k, ends_j)):
                if not flat[c]:
                    continue
                if flat[e] or (atoms[e].symbol in ('O', 'S') and len(neighbours[e]) == 2):
                    if flat[e] and c > e:
                        continue  # both flat: once per bond
                    # biaryl (biphenyl): the rings turn about 45° against each other (D2; gas phase 44°)
                    biaryl = 1.5 in orders[c] and 1.5 in orders[e]
                    for a in ends_c:
                        for d in ends_e:
                            t_a.append(a), t_j.append(c), t_k.append(e), t_d.append(d)
                            t_n.append(4 if biaryl else 2), t_f.append(K_CONJ / (len(ends_c) * len(ends_e)))
                            t_s.append(1.0 if biaryl else -1.0)
                            if biaryl or order_of[(min(a, c), max(a, c))] != 2:
                                continue
                            if flat[e] and order_of[(min(d, e), max(d, e))] == 2:
                                # C=C–C=C, O=C–C=O: s-trans (butadiene, glyoxal, oxalic acid)
                                t_a.append(a), t_j.append(c), t_k.append(e), t_d.append(d)
                                t_n.append(1), t_f.append(K_T1), t_s.append(1.0)
                            elif not flat[e]:
                                # O=C–O–X syn: the H of an acid and the alkyl of an ester (Z) on the side of C=O
                                t_a.append(a), t_j.append(c), t_k.append(e), t_d.append(d)
                                t_n.append(1), t_f.append(K_T1), t_s.append(-1.0)
                elif atoms[e].symbol in NO_LONE_PAIR and not flat[e] and all(o2 == 1 for o2 in orders[e]):
                    doubled = [a for a in ends_c if order_of[(min(a, c), max(a, c))] == 2]
                    for a in doubled:
                        for d in ends_e:
                            # the bond syn to C=X — eclipsing it (acetaldehyde, acetone, propene: the methyl H
                            # eclipses C=O / C=C). Was anti (1 + cos 3φ): the H eclipsed the other substituent of
                            # the flat atom, a saddle xtb and MOPAC did not leave (2026-11-21, MAIN_PATH)
                            t_a.append(a), t_j.append(c), t_k.append(e), t_d.append(d)
                            t_n.append(3), t_f.append(K_T3 / len(ends_e)), t_s.append(-1.0)
    # a cumulene C=C=C (allene): the planes of the two ends are perpendicular (D2d, not flat D2h)
    for c, ns in enumerate(neighbours):
        if len(ns) == 2 and all(order_of[(min(c, m), max(c, m))] == 2 for m in ns) and all(flat[m] for m in ns):
            k, l = ns
            for a in neighbours[k]:
                for d in neighbours[l]:
                    if c not in (a, d):
                        t_a.append(a), t_j.append(k), t_k.append(l), t_d.append(d)
                        t_n.append(2), t_f.append(K_T2), t_s.append(1.0)
    arr = lambda v, t=int: np.array(v, dtype=t)
    return (
        arr(b_i),
        arr(b_j),
        arr(b_r0, float),
        arr(a_a),
        arr(a_c),
        arr(a_b),
        arr(a_c0, float),
        arr(r_i),
        arr(r_j),
        arr(r_d0, float),
        arr(p_c),
        arr(p_a),
        arr(p_b),
        arr(p_d),
        arr(t_a),
        arr(t_j),
        arr(t_k),
        arr(t_d),
        arr(t_n, float),
        arr(t_f, float),
        arr(t_s, float),
    )


def _in_ring(neighbours, j, k):
    """True when j and k stay connected without the bond j–k (the bond lies in a ring)."""
    seen, stack = {j}, [j]
    while stack:
        node = stack.pop()
        for nxt in neighbours[node]:
            if node == j and nxt == k:
                continue
            if nxt == k:
                return True
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return False


def _cross(a, b):
    """Row-wise cross product of (n, 3) arrays. Np.cross on small arrays spent most of its time in moveaxis and
    axis checks (half of «Выровнять геометрию» and of a SMILES build)."""
    c = np.empty(np.broadcast_shapes(a.shape, b.shape))
    c[:, 0] = a[:, 1] * b[:, 2] - a[:, 2] * b[:, 1]
    c[:, 1] = a[:, 2] * b[:, 0] - a[:, 0] * b[:, 2]
    c[:, 2] = a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]
    return c


def _dot(a, b):
    return np.einsum('ij,ij->i', a, b)


def dihedrals(x, a, j, k, d):
    """Dihedral angles a–j–k–d (radians, −π…π) and their gradients with respect to the four atoms."""
    f, g, h = x[a] - x[j], x[j] - x[k], x[d] - x[k]
    m, n = _cross(f, g), _cross(h, g)
    gg = _dot(g, g)
    lg = np.maximum(np.sqrt(gg), 1e-9)
    mm = np.maximum(_dot(m, m), 1e-12)
    nn = np.maximum(_dot(n, n), 1e-12)
    phi = -np.arctan2(_dot(_cross(m, n), g) / lg, _dot(m, n))
    da = -(lg / mm)[:, None] * m
    dd = (lg / nn)[:, None] * n
    fg = (_dot(f, g) / (lg * lg))[:, None]
    hg = (_dot(h, g) / (lg * lg))[:, None]
    dj = -da - fg * da - hg * dd
    dk = -dd + fg * da + hg * dd
    return phi, da, dj, dk, dd


NO_LONE_PAIR = {'C', 'Si', 'Ge', 'Sn'}
TETRA = NO_LONE_PAIR | {'N', 'P', 'As', 'O', 'S', 'Se'}


def _staggered_bond(atoms, neighbours, flat, orders, j, k):
    """A single bond whose torsions are staggered: both ends tetrahedral (not flat, not linear), one without
    lone pairs and the other C-like or N, P, O, S."""
    for c in (j, k):
        if flat[c] or atoms[c].symbol not in TETRA or _ideal_angle(atoms[c].symbol, orders[c]) == 180.0:
            return False
        if any(o != 1 for o in orders[c]):
            return False
    return atoms[j].symbol in NO_LONE_PAIR or atoms[k].symbol in NO_LONE_PAIR


def straighten(molecule, moving=None):
    """A heavy-atom chain set to anti before tidying: about every acyclic single bond p–j between two
    tetrahedral atoms (as for the torsions) the side of j is turned so that a heavy neighbour of p and one of j
    are anti (180°). moving: only those atoms may turn (a newly added atom or group; the rest stays put).
    Bonds are visited from the first heavy atom outwards, so a chain comes out as a zigzag."""
    atoms = molecule.atoms
    n = len(atoms)
    if n < 4:
        return molecule
    bonds = aromatize(n, perceived_orders(molecule))
    neighbours = [[] for _ in atoms]
    orders = [[] for _ in atoms]
    for i, j, o in bonds:
        neighbours[i].append(j)
        neighbours[j].append(i)
        orders[i].append(o)
        orders[j].append(o)
    flat = [_ideal_angle(atoms[c].symbol, orders[c]) == 120.0 for c in range(n)]
    heavy = [a.symbol != 'H' for a in atoms]
    x = np.array([a.position for a in atoms], dtype=float)
    allowed = set(range(n)) if moving is None else set(moving)
    start = next((i for i in range(n) if heavy[i]), None)
    if start is None:
        return molecule
    order, seen = [], set()
    for root in [start] + [i for i in range(n) if heavy[i]]:
        if root in seen:
            continue
        seen.add(root)
        queue = [root]
        while queue:
            p = queue.pop(0)
            for j in neighbours[p]:
                if j not in seen and heavy[j]:
                    seen.add(j)
                    order.append((p, j))
                    queue.append(j)
    changed = False
    for p, j in order:
        if not _staggered_bond(atoms, neighbours, flat, orders, p, j) or _in_ring(neighbours, p, j):
            continue
        ends_p = [a for a in neighbours[p] if a != j and heavy[a]]
        ends_j = [d for d in neighbours[j] if d != p and heavy[d] and d in allowed]
        if not ends_p or not ends_j:
            continue
        if any(heavy[d] and d not in allowed for d in neighbours[j] if d != p):
            continue  # j already has a fixed branch: the new atom takes a free staggered place (clean)
        side, stack = {j}, [j]  # the atoms beyond j
        while stack:
            node = stack.pop()
            for nxt in neighbours[node]:
                if nxt != p and nxt not in side:
                    side.add(nxt)
                    stack.append(nxt)
        turn = sorted((side - {j}) & allowed)
        if not turn or p in side:
            continue
        a, d = ends_p[0], ends_j[0]
        phi = float(dihedrals(x, *[np.array([v]) for v in (a, p, j, d)])[0][0])
        angle = np.pi - abs(phi)
        if abs(angle) < 1e-3:
            continue
        axis = x[j] - x[p]
        axis /= max(np.linalg.norm(axis), 1e-9)
        for sign in (1.0, -1.0):  # the direction that makes the dihedral 180°
            th = sign * angle
            v = x[turn] - x[j]
            moved = x[j] + v * np.cos(th) + np.cross(axis, v) * np.sin(th) + np.outer(v @ axis, axis) * (1 - np.cos(th))
            trial = x.copy()
            trial[turn] = moved
            if abs(abs(float(dihedrals(trial, *[np.array([q]) for q in (a, p, j, d)])[0][0])) - np.pi) < 1e-3:
                x = trial
                changed = True
                break
    if not changed:
        return molecule
    return Molecule(molecule.title, tuple(Atom(a.symbol, *map(float, q)) for a, q in zip(atoms, x)), molecule.bonds)


def energy_and_gradient(x, t):
    """The energy and its gradient (n, 3). The forces of all terms are gathered and summed per atom by one
    bincount per coordinate (np.add.at, called 16 times per step, was the other half of the time); the arithmetic of the
    terms is unchanged."""
    b_i, b_j, b_r0, a_a, a_c, a_b, a_c0, r_i, r_j, r_d0, p_c, p_a, p_b, p_d, t_a, t_j, t_k, t_d, t_n, t_f, t_s = t
    rows, forces = [], []
    e = 0.0
    if len(b_i):
        d = x[b_i] - x[b_j]
        r = np.sqrt(_dot(d, d))
        dr = r - b_r0
        e += K_BOND * float(dr @ dr)
        f = (2 * K_BOND * dr / np.maximum(r, 1e-9))[:, None] * d
        rows += [b_i, b_j]
        forces += [f, -f]
    if len(a_c):
        u = x[a_a] - x[a_c]
        v = x[a_b] - x[a_c]
        lu = np.maximum(np.sqrt(_dot(u, u)), 1e-9)
        lv = np.maximum(np.sqrt(_dot(v, v)), 1e-9)
        c = _dot(u, v) / (lu * lv)
        dc = c - a_c0
        e += K_ANGLE * float(dc @ dc)
        w = 2 * K_ANGLE * dc
        du = (v / (lu * lv)[:, None] - (c / (lu * lu))[:, None] * u) * w[:, None]
        dv = (u / (lu * lv)[:, None] - (c / (lv * lv))[:, None] * v) * w[:, None]
        rows += [a_a, a_b, a_c]
        forces += [du, dv, -(du + dv)]
    if len(p_c):
        u = x[p_a] - x[p_c]
        v = x[p_b] - x[p_c]
        w = x[p_d] - x[p_c]
        vw = _cross(v, w)
        vol = _dot(u, vw)
        e += K_PLANE * float(vol @ vol)
        k = (2 * K_PLANE * vol)[:, None]
        ga, gb, gd = k * vw, k * _cross(w, u), k * _cross(u, v)
        rows += [p_a, p_b, p_d, p_c]
        forces += [ga, gb, gd, -(ga + gb + gd)]
    if len(r_i):
        d = x[r_i] - x[r_j]
        r = np.sqrt(_dot(d, d))
        over = r_d0 - r
        m = over > 0
        if m.any():
            e += K_REP * float(over[m] @ over[m])
            f = (-2 * K_REP * over[m] / np.maximum(r[m], 1e-9))[:, None] * d[m]
            rows += [r_i[m], r_j[m]]
            forces += [f, -f]
    if len(t_a):
        phi, da, dj, dk, dd = dihedrals(x, t_a, t_j, t_k, t_d)
        e += float(np.sum(t_f * (1 + t_s * np.cos(t_n * phi))))
        w = (-t_f * t_s * t_n * np.sin(t_n * phi))[:, None]
        rows += [t_a, t_j, t_k, t_d]
        forces += [w * da, w * dj, w * dk, w * dd]
    if not rows:
        return e, np.zeros_like(x)
    index = np.concatenate(rows)
    values = np.concatenate(forces)
    n = len(x)
    g = np.empty_like(x)
    for c in range(3):
        g[:, c] = np.bincount(index, values[:, c], minlength=n)
    return e, g


def _fit(moved, reference):
    """Rigid (no reflection) fit of moved onto reference."""
    a = moved - moved.mean(axis=0)
    b = reference - reference.mean(axis=0)
    u, _, vt = np.linalg.svd(a.T @ b)
    s = np.eye(3)
    s[2, 2] = 1 if np.linalg.det(u @ vt) >= 0 else -1
    return a @ (u @ s @ vt) + reference.mean(axis=0)


def _lbfgs(x, t, mask, tolerance, steps, memory=8):
    """Limited-memory BFGS with a backtracking line search — the same minimum as FIRE in tens to hundreds
    of evaluations instead of thousands (the build from SMILES); (x, steps, energy)."""
    e, g = energy_and_gradient(x, t)
    g = g * mask
    pairs = []
    step = 0
    for step in range(1, steps + 1):
        if np.max(np.abs(g)) < tolerance:
            break
        q = g.ravel().copy()
        alphas = []
        for s_k, y_k, rho in reversed(pairs):
            a = rho * (s_k @ q)
            alphas.append(a)
            q -= a * y_k
        if pairs:
            s_k, y_k, _ = pairs[-1]
            q *= (s_k @ y_k) / (y_k @ y_k)
        else:
            q *= 0.1 / max(np.max(np.abs(q)), 1e-12)  # the first step moves an atom by 0.1 Å at most
        for (s_k, y_k, rho), a in zip(pairs, reversed(alphas)):
            q += s_k * (a - rho * (y_k @ q))
        d = -q.reshape(x.shape) * mask
        slope = float(np.sum(d * g))
        if slope >= 0:  # not downhill: start the memory again along the force
            pairs.clear()
            d = -g * (0.1 / max(np.max(np.abs(g)), 1e-12))
            slope = float(np.sum(d * g))
        longest = np.max(np.abs(d))
        if longest > 0.3:  # an atom moves 0.3 Å at most per step
            d *= 0.3 / longest
            slope *= 0.3 / longest
        size = 1.0
        while True:
            x_new = x + size * d
            e_new, g_new = energy_and_gradient(x_new, t)
            if e_new <= e + 1e-4 * size * slope or size < 1e-4:
                break
            size *= 0.5
        g_new = g_new * mask
        s_k, y_k = (x_new - x).ravel(), (g_new - g).ravel()
        sy = float(s_k @ y_k)
        if sy > 1e-12:
            pairs.append((s_k, y_k, 1.0 / sy))
            if len(pairs) > memory:
                pairs.pop(0)
        x, e, g = x_new, e_new, g_new
    return x, step, e


def clean(molecule, movable=None, steps=2000, tolerance=1e-3, method='fire'):
    """(cleaned Molecule, number of steps, final energy); tolerance: the largest force left, method: 'fire' or
    'lbfgs'."""
    if len(molecule.atoms) < 2:
        return molecule, 0, 0.0
    t = terms(molecule)
    x0 = np.array([a.position for a in molecule.atoms], dtype=float)
    mask = np.ones((len(x0), 1))
    if movable:
        mask[:] = 0
        mask[list(movable)] = 1
    # a small fixed jitter, so that an exactly eclipsed bond (a saddle of the torsions, zero force) is
    # not kept; the same structure always gives the same result
    x = x0 + mask * np.random.default_rng(7).uniform(-JITTER, JITTER, x0.shape)
    if method == 'lbfgs':
        x, step, e = _lbfgs(x, t, mask, tolerance, steps)
        steps = 0  # the FIRE loop below is skipped
    else:
        e, g = energy_and_gradient(x, t)
        step = 0
    v = np.zeros_like(x)
    dt, alpha, n_pos = 0.02, 0.1, 0
    for step in range(step + 1, steps + 1):  # FIRE
        f = -g * mask
        if np.max(np.abs(f)) < tolerance:
            break
        power = np.sum(f * v)
        if power > 0:
            n_pos += 1
            v = (1 - alpha) * v + alpha * np.linalg.norm(v) * f / max(np.linalg.norm(f), 1e-12)
            if n_pos > 5:
                dt = min(dt * 1.1, 0.1)
                alpha *= 0.99
        else:
            n_pos = 0
            v[:] = 0
            dt *= 0.5
            alpha = 0.1
        v += dt * f
        x = x + dt * v
        e, g = energy_and_gradient(x, t)
    if not movable:
        x = _fit(x, x0)
    atoms = tuple(Atom(a.symbol, *map(float, p)) for a, p in zip(molecule.atoms, x))
    return checked(Molecule(molecule.title, atoms, molecule.bonds)), step, float(e)


def tidy_new(molecule, new, steps=600, field='simple'):
    """The structure after an atom or a group was added (new: their indices), tidied around them; field 'uff'
    the same atoms moved by UFF (uff.optimize) instead of the simple field — the simple one if UFF cannot
    type the structure."""
    from modules.compass.chemistry.editing import add_hydrogens

    n0 = len(molecule.atoms)
    new = sorted({i for i in new if 0 <= i < n0})
    if not new or n0 < 2 or n0 > LIVE_LIMIT:
        return molecule
    full, _ = add_hydrogens(molecule)
    if full.bonds is None:
        return molecule
    temporary = set(range(n0, len(full.atoms)))
    neighbours = [set() for _ in full.atoms]
    for i, j, _ in full.bonds:
        neighbours[i].add(j)
        neighbours[j].add(i)
    grown = set(new) | {h for h in temporary if neighbours[h] & set(new)}
    full = straighten(full, moving=grown)
    near = set(new) | {j for i in new for j in neighbours[i]}
    degree = [len(neighbours[i] - temporary) for i in range(n0)]  # in the structure as drawn
    movable = set(new) | temporary | {j for i in near for j in neighbours[i] if j < n0 and degree[j] == 1}
    cleaned = None
    if field == 'uff':
        from modules.compass.chemistry import uff

        try:
            cleaned = uff.optimize(full, sorted(movable), steps=steps, tolerance=0.05).molecule
        except ValueError:
            cleaned = None
    if cleaned is None:
        cleaned, _, _ = clean(full, sorted(movable), steps)
    return checked(Molecule(molecule.title, cleaned.atoms[:n0], molecule.bonds))
