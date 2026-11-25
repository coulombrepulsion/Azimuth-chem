"""Proteins in Compass: the backbone found in the bonds, the secondary structure, the ribbon.

§1 PURPOSE
    «Вид → Ленты белка»: a protein (a PDB file, a peptide built in Compass) drawn as a ribbon — α-helices as wide red
    bands, β-strands as yellow arrows, the rest as a thin grey tube — over or instead of its atoms, the way students
    first see a protein.
§2 BACKBONE (backbone)
    From the bonds (as Compass perceives them, so a PDB without CONECT or hydrogens works too): a residue is
    N–Cα–C(=O) — Cα a carbon bonded to an N and to a carbonyl carbon (a C with a double bond to an O that has no other
    neighbour: the OH of Ser, Thr and Tyr without its H is not one);
    residue r is followed by s when C of r is bonded to N of s. Chains are the runs of such links; side chains (the
    amide of Asn and Gln, the amine of Lys) do not fit the pattern. The order is that of the chain, not of the file.
§3 SECONDARY STRUCTURE (secondary) — a simplified DSSP (Kabsch and Sander, Biopolymers 22, 2577 (1983)) A hydrogen bond
    C=O(i)···H–N(j) is taken where d(O_i, N_j) ≤ HB_DISTANCE (3.5 Å) and N_j is not the N of a proline (three heavy
    neighbours: no H). α-helix: n-turns at i − 1 and i (bonds i → i + 4) make residues i…i + 3 helical; 3₁₀-turns (i → i
    + 3) at i − 1 and i make i…i + 2 helical where no α-helix is (drawn as a helix, as ribbon programs do). β-bridge
    between i and j (|i − j| > 2): parallel — bonds (i − 1 → j and j → i + 1) or (j − 1 → i and i → j + 1); antiparallel
    — (i → j and j → i) or (i − 1 → j + 1 and j − 1 → i + 1); a strand is a bridged residue with a bridged neighbour
    (DSSP «E»; an isolated bridge «B» is drawn as coil). ASSUMPTION: the distance replaces the electrostatic energy of
    DSSP (≤ −0.5 kcal/mol), so the ends of elements may differ from DSSP and from the HELIX/SHEET records of a PDB file
    by a residue or two.
§4 RIBBON (ribbon)
    A Catmull–Rom spline through the Cα of a chain, SEGMENTS points per residue; the band lies in the peptide plane:
    the direction C→O of every residue, flipped to agree with the previous one, interpolated and made perpendicular to
    the tangent. The cross-section is an ellipse of half-width × half-thickness: helix 1.3 × 0.3 Å, strand 1.0 ×
    0.25 Å with an arrow over the last residue (from 1.6 Å to the tip), coil a tube of 0.3 Å. Colours by element:
    helix #d64550, strand #e8b923, coil #a3abb4. The mesh (surfaces.Mesh, Å) has per-vertex colours and normals.
§5 INTERFACE
    Residue(chain, n, ca, c, o, name); backbone(molecule, orders=None) -> [[Residue]] (chains of ≥ 2 residues);
    secondary(molecule, chains) -> [['H' | 'E' | 'C']] per chain; ribbon(molecule, chains, ss) -> surfaces.Mesh;
    protein_atoms(chains) -> set of the backbone atoms (with the hydrogens and side chains reachable without passing
    another residue's backbone — what «Ленты» hides).
§6 TESTS
    tests/compass/test_protein.py — crambin (1CRN) and ubiquitin (1UBQ) from the PDB: the chains found, the secondary
    structure against the HELIX/SHEET records of the files, the mesh closed and coloured.
"""

from dataclasses import dataclass

import numpy as np

HB_DISTANCE = 3.5  # Å
SEGMENTS = 8
PROFILE = 12
SIZES = {'H': (1.3, 0.3), 'E': (1.0, 0.25), 'C': (0.3, 0.3)}
COLOURS = {'H': (0.839, 0.271, 0.314), 'E': (0.910, 0.725, 0.137), 'C': (0.639, 0.671, 0.706)}
ARROW = 1.6


@dataclass(frozen=True)
class Residue:
    n: int
    ca: int
    c: int
    o: int


def _neighbours(molecule, orders=None, with_orders=False):
    from modules.compass.chemistry.editing import perceived_orders

    bonds = perceived_orders(molecule) if orders is None else orders
    found = [set() for _ in molecule.atoms]
    kinds = {}
    for i, j, o in bonds:
        found[i].add(j)
        found[j].add(i)
        kinds[(min(i, j), max(i, j))] = o
    return (found, kinds) if with_orders else found


def backbone(molecule, orders=None):
    symbols = [a.symbol for a in molecule.atoms]
    near, kinds = _neighbours(molecule, orders, with_orders=True)

    def oxygen_of(c):  # the O of C=O (a hydroxyl of Ser, Thr, Tyr has the order 1 even without its H)
        return next((o for o in sorted(near[c]) if symbols[o] == 'O' and len(near[o]) == 1
                     and kinds[(min(c, o), max(c, o))] >= 1.5), None)

    carbonyl = {i for i, s in enumerate(symbols) if s == 'C' and oxygen_of(i) is not None}
    residues = {}
    for ca, s in enumerate(symbols):
        if s != 'C' or ca in carbonyl:
            continue
        nitrogen = [k for k in near[ca] if symbols[k] == 'N']
        carbon = [k for k in near[ca] if k in carbonyl]
        if len(nitrogen) == 1 and len(carbon) == 1:
            residues[ca] = Residue(nitrogen[0], ca, carbon[0], oxygen_of(carbon[0]))
    by_n = {r.n: r for r in residues.values()}
    following = {}
    for r in residues.values():
        nxt = next((by_n[k] for k in near[r.c] if k in by_n and by_n[k].ca != r.ca), None)
        if nxt is not None:
            following[r.ca] = nxt
    having_previous = {r.ca for r in following.values()}
    chains = []
    for ca in sorted(residues):
        if ca in having_previous:
            continue
        chain, r, seen = [], residues[ca], set()
        while r is not None and r.ca not in seen:
            chain.append(r)
            seen.add(r.ca)
            r = following.get(r.ca)
        if len(chain) >= 2:
            chains.append(chain)
    return chains


def secondary(molecule, chains, orders=None):
    x = np.array([a.position for a in molecule.atoms], float)
    symbols = [a.symbol for a in molecule.atoms]
    near = _neighbours(molecule, orders)
    flat = [(k, i, r) for k, chain in enumerate(chains) for i, r in enumerate(chain)]
    count = len(flat)
    o = x[[r.o for _, _, r in flat]]
    n = x[[r.n for _, _, r in flat]]
    donor = np.array([sum(1 for m in near[r.n] if symbols[m] != 'H') < 3 for _, _, r in flat])
    d = np.linalg.norm(o[:, None, :] - n[None, :, :], axis=2)
    hb = (d <= HB_DISTANCE) & donor[None, :]
    np.fill_diagonal(hb, False)
    place = {(k, i): g for g, (k, i, _) in enumerate(flat)}

    def at(g, step):
        """The residue step along the chain from g, or None at its end."""
        k, i, _ = flat[g]
        return place.get((k, i + step))

    def bond(a, b):
        return a is not None and b is not None and bool(hb[a, b])

    ss = ['C'] * count
    turn4 = [bond(g, at(g, 4)) for g in range(count)]
    for g in range(count):
        before = at(g, -1)
        if before is not None and turn4[before] and turn4[g]:
            for step in range(4):
                h = at(g, step)
                if h is not None:
                    ss[h] = 'H'
    turn3 = [bond(g, at(g, 3)) for g in range(count)]  # 3₁₀-helices: drawn as helices where no α-helix is
    for g in range(count):
        before = at(g, -1)
        if before is not None and turn3[before] and turn3[g]:
            span = [at(g, step) for step in range(3)]
            if all(h is not None and ss[h] == 'C' for h in span):
                for h in span:
                    ss[h] = 'H'
    bridged = [False] * count
    for i in range(count):
        for j in range(count):
            if i == j or (flat[i][0] == flat[j][0] and abs(flat[i][1] - flat[j][1]) <= 2):
                continue
            ip, inx, jp, jn = at(i, -1), at(i, 1), at(j, -1), at(j, 1)
            parallel = (bond(ip, j) and bond(j, inx)) or (bond(jp, i) and bond(i, jn))
            anti = (bond(i, j) and bond(j, i)) or (bond(ip, jn) and bond(jp, inx))
            if parallel or anti:
                bridged[i] = True
    for g in range(count):
        if ss[g] == 'C' and bridged[g] and any(h is not None and bridged[h] for h in (at(g, -1), at(g, 1))):
            ss[g] = 'E'
    result, g = [], 0
    for chain in chains:
        result.append(ss[g:g + len(chain)])
        g += len(chain)
    return result


def _spline(points, segments):
    """Catmull–Rom through the points (the ends repeated); (len − 1)·segments + 1 points and their parameter."""
    p = np.vstack([points[0], points, points[-1]])
    out, where = [], []
    for k in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[k - 1], p[k], p[k + 1], p[k + 2]
        for s in range(segments):
            t = s / segments
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
            where.append(k - 1 + t)
    out.append(points[-1])
    where.append(len(points) - 1)
    return np.array(out), np.array(where)


def ribbon(molecule, chains, ss):
    from modules.compass.view.surfaces import Mesh

    x = np.array([a.position for a in molecule.atoms], float)
    vertices, triangles, normals, colours = [], [], [], []
    angles = np.linspace(0.0, 2 * np.pi, PROFILE, endpoint=False)
    for chain, kinds in zip(chains, ss):
        ca = x[[r.ca for r in chain]]
        sides = []
        for r in chain:
            v = x[r.o] - x[r.c]
            v /= max(np.linalg.norm(v), 1e-9)
            if sides and np.dot(v, sides[-1]) < 0:
                v = -v
            sides.append(v)
        sides = np.array(sides)
        path, where = _spline(ca, SEGMENTS)
        tangent = np.gradient(path, axis=0)
        tangent /= np.maximum(np.linalg.norm(tangent, axis=1), 1e-9)[:, None]
        last_of_strand = {i for i, s in enumerate(kinds) if s == 'E' and (i + 1 == len(kinds) or kinds[i + 1] != 'E')}
        base = len(vertices)
        for m, (point, t, u) in enumerate(zip(path, tangent, where)):
            i = min(int(u), len(chain) - 1)
            f = u - i
            side = sides[i] * (1 - f) + sides[min(i + 1, len(chain) - 1)] * f
            side -= np.dot(side, t) * t
            if np.linalg.norm(side) < 1e-6:
                side = np.cross(t, (1.0, 0.0, 0.0))
            side /= np.linalg.norm(side)
            up = np.cross(t, side)
            kind = kinds[min(int(round(u)), len(kinds) - 1)]
            a, b = SIZES[kind]
            here = min(int(round(u)), len(kinds) - 1)
            if kind == 'E' and here in last_of_strand:  # the arrow: 1.6 Å at the start of the residue, then to its tip
                a = ARROW * max(0.05, 1.0 - (u - (here - 0.5)))
            colour = COLOURS[kind]
            for phi in angles:
                c, s = np.cos(phi), np.sin(phi)
                vertices.append(point + a * c * side + b * s * up)
                normal = (c / a) * side + (s / b) * up
                normals.append(normal / np.linalg.norm(normal))
                colours.append(colour)
            if m:
                ring, prev = base + m * PROFILE, base + (m - 1) * PROFILE
                for q in range(PROFILE):
                    q2 = (q + 1) % PROFILE
                    triangles.append((prev + q, ring + q, ring + q2))
                    triangles.append((prev + q, ring + q2, prev + q2))
    if not vertices:
        return None
    return Mesh(np.array(vertices), np.array(triangles, dtype=int), np.array(normals), '#a3abb4', None,
                np.array(colours))


def protein_atoms(molecule, chains, orders=None):
    """The atoms of the residues of the chains — the backbone and every atom reached from it without crossing to the
    backbone of another residue (side chains, hydrogens); ligands and water are left out."""
    near = _neighbours(molecule, orders)
    backbone_atoms = {a for chain in chains for r in chain for a in (r.n, r.ca, r.c, r.o)}
    found = set(backbone_atoms)
    stack = list(backbone_atoms)
    while stack:
        a = stack.pop()
        for b in near[a]:
            if b not in found:
                found.add(b)
                stack.append(b)
    return found
