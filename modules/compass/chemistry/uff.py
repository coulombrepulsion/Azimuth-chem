"""UFF, the universal force field: energies in kcal/mol and an optimization for Compass.

§1 PURPOSE
    «Правка → Геометрия → Оптимизировать (UFF)» and, when chosen, «Выравнивать при построении»: a published force
    field with real energies (Rappé, Casewit, Colwell, Goddard, Skiff, J. Am. Chem. Soc. 114, 10024 (1992)), not the
    simple tidying field of cleanup.py. The parameters are those of RDKit (uff_params.py), and so are the atom types and
    the terms: the same structure gives the same energy in Azimuth and in RDKit (UFFGetMoleculeForceField), which is how
    it is checked (tests/compass/test_uff.py; tools/uff_reference.py writes RDKit's numbers on a computer with RDKit).
§2 TYPES (types)
    As RDKit's AtomTyper and ConjugHybrid: the symbol (padded with «_»), then the hybridization — 1 (sp), 2 (sp2),
    R (sp2 of C, N, O, S that is aromatic or has a conjugated bond), 3 (sp3), 5, 6 — and the charge marks of S, P, the
    metals (S_3+2, S_3+4, S_3+6, P_3+3, P_3+5, Fe6+2 …); H, the alkali metals and the halogens have no hybridization;
    Mg, Al, Si, P, Sn, Sb, Te, Tl, Pb, Bi, Po are always «3». The hybridization is the number of neighbours and lone
    pairs (4 → sp3, except an atom with at most three neighbours and a conjugated bond: sp2 — the N of an amide or of
    aniline, the O of an ester or of phenol); a bond is conjugated as RDKit marks it (setConjugation: an atom with
    2–3 substituents joins a multiple bond to a candidate with a bond to another candidate).
    Aromatic bonds have the order 1.5: the six-membered rings of editing.aromatize and five-membered rings with
    one N–H/N–R, O or S between four atoms each with a double bond in the ring (pyrrole, furan, thiophene, imidazole,
    indole). ASSUMPTION: RDKit's aromaticity model is wider (4n+2 rings of other sizes, charged rings); there the types
    of the two programs can differ. Metals: the hybridization is the number of neighbours (RDKit counts lone pairs of
    their outer electrons as well) — ASSUMPTION; a type missing from the table is replaced by one of the same element
    and said in the notes.
§3 TERMS (build; kcal/mol, Å)
    bond ½ k (r − r0)²; r0 = ri + rj − 0.1332 (ri + rj) ln n − ri rj (√χi − √χj)² / (χi ri + χj rj),
               k = 664.12 Zi Zj / r0³ (n — the bond order, 1.5 aromatic);
    angle K (C0 + C1 cos θ + C2 cos 2θ) with θ0 of the central atom, or for sp, sp2 and octahedral centres
               K / n² (1 − cos nθ) (n = 1 as 1 + cos θ, 3, 4); an sp2 atom of a three- or four-membered ring gets θ0 of
               150°, 60°, 135° or 90° with the general form; K = 664.12 Zi Zk / rik⁵ · (3 rij rjk (1 − cos² θ0) −
               rik² cos θ0); trigonal-bipyramidal centres as RDKit (axial pair — the most opposite bonds); below 30° the
               penalty exp(−20 (θ − θ0 + 0.25)) of RDKit for the forms with n;
    torsion ½ V (1 − cos nφ0 cos nφ) about every bond between sp2/sp3 atoms not in a triple bond, divided by the
               number of torsions of the bond: sp3–sp3 V = √(Vj Vk), n = 3 (two group-16 atoms: V 2 for O, 6.8 for the
               others, n = 2); sp2–sp2 V = 5 √(Uj Uk) (1 + 4.18 ln n), n = 2; sp2–sp3 V = 1, n = 6, or n = 2 with
               V of the sp2–sp2 form for a group-16 sp3 atom, or V = 2, n = 3 next to another sp2 atom;
    inversion K (C0 + C1 sin Y + C2 cos 2Y) for C, N, O (sp2) and P, As, Sb, Bi with three neighbours, three
               permutations, K = 6 (50 for the C of C=O) / 3;
    vdW D [(x/r)¹² − 2 (x/r)⁶], x = √(xi xj), D = √(Di Dj), for pairs further than 1–3. No charges.
§4 OPTIMIZATION (optimize)
    Limited-memory BFGS with a backtracking line search; the atoms not in movable stay; without a selection the result
    is put back on the start by a rigid fit. Steps until the largest force is below tolerance (kcal/mol/Å).
§5 INTERFACE
    types(molecule) -> (labels, hybridizations, notes); build(molecule) -> Field; energy(field, x) ->
    (E, gradient (n, 3), parts {'bond', 'angle', 'torsion', 'inversion', 'vdw'}); optimize(molecule, movable=None,
    steps=2000, tolerance=1e-3, keep=0) -> Result. ValueError (translated) when the structure cannot be typed.
§6 NOTES
    The structure must have its hydrogens: UFF sees the atoms that are there (an unfilled valence is a radical for
    it). Dummy atoms (X) are not allowed.
"""

from dataclasses import dataclass, field as dataclass_field, replace
from math import cos, log, pi, sin, sqrt

import numpy as np

from azimuth.core import DUMMY, Z, Atom, Molecule
from azimuth.i18n import tr
from modules.compass.chemistry.uff_params import PARAMS

G = 332.06  # bond force constant prefactor (664.12 / 2)
LAMBDA = 0.1332  # the bond-order correction of r0
ANGLE_PENALTY_COS = 0.8660  # RDKit: the penalty for angles below 30°
SIZE_LIMIT = 1500  # atoms: the van der Waals pairs grow as n²
# the elements of the structures checked against RDKit (tests/data/uff/structures.json); for others — the metals above
# all — the program says the result is not checked (AGENTS.md §0)
CHECKED_ELEMENTS = frozenset(('H', 'C', 'N', 'O', 'P', 'S', 'Cl'))

# Outer electrons and default valences as RDKit's periodic table (main groups; metals have no default valence: -1)
NOUTER = {
    'H': 1, 'He': 2, 'Li': 1, 'Be': 2, 'B': 3, 'C': 4, 'N': 5, 'O': 6, 'F': 7, 'Ne': 8, 'Na': 1, 'Mg': 2, 'Al': 3,
    'Si': 4, 'P': 5, 'S': 6, 'Cl': 7, 'Ar': 8, 'K': 1, 'Ca': 2, 'Ga': 3, 'Ge': 4, 'As': 5, 'Se': 6, 'Br': 7, 'Kr': 8,
    'Rb': 1, 'Sr': 2, 'In': 3, 'Sn': 4, 'Sb': 5, 'Te': 6, 'I': 7, 'Xe': 8, 'Cs': 1, 'Ba': 2, 'Tl': 3, 'Pb': 4, 'Bi': 5,
    'Po': 6, 'At': 7, 'Rn': 8,
}
DEFAULT_VALENCE = {
    'H': 1, 'He': 0, 'Li': 1, 'Be': 2, 'B': 3, 'C': 4, 'N': 3, 'O': 2, 'F': 1, 'Ne': 0, 'Na': 1, 'Mg': 2, 'Al': 3,
    'Si': 4, 'P': 3, 'S': 2, 'Cl': 1, 'Ar': 0, 'K': 1, 'Ca': 2, 'Ga': 3, 'Ge': 4, 'As': 3, 'Se': 2, 'Br': 1, 'Kr': 0,
    'Rb': 1, 'Sr': 2, 'In': 3, 'Sn': 2, 'Sb': 3, 'Te': 2, 'I': 1, 'Xe': 0, 'Cs': 1, 'Ba': 2, 'Tl': 1, 'Pb': 2, 'Bi': 3,
    'Po': 2, 'At': 1, 'Rn': 0,
}
ALWAYS_3 = {'Mg', 'Al', 'Si', 'P', 'Sn', 'Sb', 'Te', 'Tl', 'Pb', 'Bi', 'Po'}
GROUP_16 = {'O', 'S', 'Se', 'Te', 'Po'}
# charge marks of RDKit's addAtomChargeFlags (with tolerateChargeMismatch): fixed ones, then those by the valence
FIXED_MARK = {
    **dict.fromkeys(('Cu', 'Ag'), '+1'),
    **dict.fromkeys(('Be', 'Ca', 'Mn', 'Fe', 'Ni', 'Pd', 'Pt', 'Mg', 'Zn', 'Se', 'Cd', 'Te', 'Hg', 'Po'), '+2'),
    **dict.fromkeys(('Sc', 'Cr', 'Co', 'Au', 'Ac', 'Cm', 'Bk', 'Cf', 'Es', 'Fm', 'Md', 'No', 'Lr', 'Ga', 'As', 'In',
                     'Sb', 'Tl', 'Pb', 'Bi'), '+3'),
    **dict.fromkeys(('He', 'Ar', 'Ti', 'Kr', 'Xe', 'Th', 'Pa', 'U', 'Np', 'Pu', 'Am'), '+4'),
    **dict.fromkeys(('V', 'Nb', 'Tc', 'Ta'), '+5'),
    'Mo': '+6',
}
LANTHANIDES = {'La', 'Ce', 'Pr', 'Nd', 'Pm', 'Sm', 'Eu', 'Gd', 'Tb', 'Dy', 'Ho', 'Er', 'Tm', 'Yb', 'Lu'}
SP, SP2, SP3, SP3D, SP3D2, S_ORBITAL = 'sp', 'sp2', 'sp3', 'sp3d', 'sp3d2', 's'


@dataclass
class Field:
    """The terms of one structure; arrays of indices and constants (see §3)."""

    labels: tuple
    notes: tuple
    bonds: np.ndarray  # (m, 2) int
    bond_k: np.ndarray
    bond_r0: np.ndarray
    angles: np.ndarray  # (m, 3) int: i, centre, k
    angle_k: np.ndarray
    angle_order: np.ndarray  # 0 general, 1, 2, 3, 4
    angle_c: np.ndarray  # (m, 3) C0, C1, C2
    angle_theta0: np.ndarray
    torsions: np.ndarray  # (m, 4) int
    torsion_v: np.ndarray
    torsion_n: np.ndarray
    torsion_cos: np.ndarray  # cos nφ0: ±1
    inversions: np.ndarray  # (m, 4) int: i, centre, k, l
    inversion_k: np.ndarray
    inversion_c: np.ndarray  # (m, 3)
    pairs: np.ndarray  # (m, 2) int
    pair_x: np.ndarray
    pair_d: np.ndarray


@dataclass
class Result:
    molecule: Molecule
    energy: float  # kcal/mol
    parts: dict
    steps: int
    labels: tuple
    notes: tuple = ()
    start: float = 0.0  # kcal/mol of the start geometry
    frames: list = dataclass_field(default_factory=list)  # (positions, energy) every keep steps


def _bond_orders(molecule):
    from modules.compass.chemistry.editing import aromatize, perceived_orders

    if any(a.symbol == DUMMY for a in molecule.atoms):
        raise ValueError(tr('UFF: уберите фиктивные атомы X — у них нет параметров.'))
    bonds = aromatize(len(molecule.atoms), perceived_orders(molecule))  # Kekulé rings of a file or SMILES: 1.5
    return {(min(i, j), max(i, j)): float(o) for i, j, o in bonds}


def _rings(neighbours, size):
    found = {}
    for start in range(len(neighbours)):
        stack = [(start, (start,))]
        while stack:
            node, path = stack.pop()
            if len(path) == size:
                if start in neighbours[node]:
                    found.setdefault(frozenset(path), path)
                continue
            for nxt in neighbours[node]:
                if nxt > start and nxt not in path:
                    stack.append((nxt, path + (nxt,)))
    return list(found.values())


def _aromatic_five(symbols, neighbours, order):
    """Five-membered rings with one lone-pair donor (N with three neighbours, O, S, Se with two) and four
    atoms that each have a double or aromatic bond in the ring — their bonds become 1.5; repeated (fused rings).
    The donors (their Kekulé valence counts their ring bonds as single) are returned."""
    donors = set()
    rings = _rings(neighbours, 5)
    changed = True
    while changed:
        changed = False
        for ring in rings:
            edges = [(min(ring[k], ring[(k + 1) % 5]), max(ring[k], ring[(k + 1) % 5])) for k in range(5)]
            if all(order[e] == 1.5 for e in edges):
                continue
            multiple = {a: any(order[e] >= 1.5 and a in e for e in edges) for a in ring}
            plain = [a for a in ring if not multiple[a]]
            if len(plain) != 1:
                continue
            x = plain[0]
            n = len(neighbours[x])
            if not ((symbols[x] in ('N', 'P') and n == 3) or (symbols[x] in ('O', 'S', 'Se') and n == 2)):
                continue
            if any(order[e] == 2 and x not in e and sum(1 for f in edges if order[f] == 2) > 2 for e in edges):
                continue
            for e in edges:
                order[e] = 1.5
            donors.add(x)
            changed = True
    return donors


def _count_atom_elec(symbol, degree, valence):
    dv = DEFAULT_VALENCE.get(symbol, -1)
    if dv <= 1 or degree > 3:
        return -1
    nlp = max(NOUTER[symbol] - dv, 0)
    res = (dv - degree) + nlp
    if res > 1 and valence - degree > 1:
        res = 1
    return res


def _candidate(symbol, degree, valence):
    dv = DEFAULT_VALENCE.get(symbol, -1)
    if dv >= 0 and valence > dv:
        return False
    nouter = NOUTER.get(symbol)
    if nouter is None:
        return False
    z = Z.get(symbol, 0)
    return (z <= 10 or nouter not in (5, 6) or (nouter == 6 and degree < 2)) and _count_atom_elec(symbol, degree,
                                                                                                   valence) > 0


def types(molecule):
    """(labels, hybridizations, notes, orders {(i, j): order}, neighbours) — §2."""
    symbols = [a.symbol for a in molecule.atoms]
    n = len(symbols)
    order = _bond_orders(molecule)
    neighbours = [[] for _ in range(n)]
    for i, j in sorted(order):
        neighbours[i].append(j)
        neighbours[j].append(i)
    donors = _aromatic_five(symbols, neighbours, order)
    aromatic_bond = {e for e, o in order.items() if o == 1.5}
    aromatic = [any((min(i, j), max(i, j)) in aromatic_bond for j in neighbours[i]) for i in range(n)]
    degree = [len(neighbours[i]) for i in range(n)]
    valence = []
    for i in range(n):
        own = [order[(min(i, j), max(i, j))] for j in neighbours[i]]
        arom = sum(1 for o in own if o == 1.5)
        rest = sum(o for o in own if o != 1.5)
        valence.append(int(round(rest + arom + (1 if arom and i not in donors else 0))))
    candidate = [_candidate(symbols[i], degree[i], valence[i]) for i in range(n)]
    conjugated = set(aromatic_bond)
    for a in range(n):  # RDKit markConjAtomBonds
        if not candidate[a] or degree[a] not in (2, 3):
            continue
        for b in neighbours[a]:
            e1 = (min(a, b), max(a, b))
            if order[e1] < 1.5 or not candidate[b]:
                continue
            for c in neighbours[a]:
                if c == b:
                    continue
                if candidate[c] and degree[c] <= 3:
                    conjugated.add(e1)
                    conjugated.add((min(a, c), max(a, c)))
    has_conjugated = [any((min(i, j), max(i, j)) in conjugated for j in neighbours[i]) for i in range(n)]
    hybrid, labels, notes = [], [], []
    for i, s in enumerate(symbols):
        if s == 'H' or s not in NOUTER and s not in PARAMS and not any(k.startswith(s) for k in PARAMS):
            norbs = degree[i]
        elif s not in NOUTER:  # a metal: ASSUMPTION — the neighbours only
            norbs = degree[i]
        else:
            free = NOUTER[s] - valence[i]
            norbs = degree[i] + int(free / 2)
        if s == 'H':
            norbs = degree[i]
        h = {0: S_ORBITAL, 1: S_ORBITAL, 2: SP, 3: SP2, 5: SP3D, 6: SP3D2}.get(norbs)
        if norbs == 4:
            h = SP3 if degree[i] > 3 or not has_conjugated[i] else SP2
        hybrid.append(h)
        key = s + ('_' if len(s) == 1 else '')
        nouter = NOUTER.get(s)
        if nouter not in (1, 7):
            if s in ALWAYS_3:
                key += '3'
            elif s == 'Hg':
                key += '1'
            elif h == SP:
                key += '1'
            elif h == SP2:
                key += 'R' if (aromatic[i] or has_conjugated[i]) and s in ('C', 'N', 'O', 'S') else '2'
            elif h == SP3:
                key += '3'
            elif h == SP3D:
                key += '5'
            elif h == SP3D2:
                key += '6'
        if s == 'P':
            key += {3: '+3', 5: '+5'}.get(valence[i], '+5')
        elif s == 'S' and h != SP2:
            key += {2: '+2', 4: '+4', 6: '+6'}.get(valence[i], '+6')
        elif s in FIXED_MARK:
            key += FIXED_MARK[s]
        elif s in LANTHANIDES:
            key += '+3'
        if key not in PARAMS:
            same = [k for k in PARAMS if k.rstrip('0123456789+-_RZqz') == s or k.split('_')[0] == s]
            same = [k for k in same if k[:len(s)] == s and (len(k) == len(s) or not k[len(s)].islower())]
            if not same:
                raise ValueError(tr('UFF: нет параметров для элемента {}.').format(s))
            notes.append(tr('Атом {} ({}): типа {} нет в UFF, взят {}.').format(i + 1, s, key, same[0]))
            key = same[0]
        labels.append(key)
    return tuple(labels), tuple(hybrid), tuple(notes), order, neighbours


def _rest_length(order, pi_, pj):
    ri, rj, xi, xj = pi_[0], pj[0], pi_[8], pj[8]
    r_bo = -LAMBDA * (ri + rj) * log(order)
    r_en = ri * rj * (sqrt(xi) - sqrt(xj)) ** 2 / (xi * ri + xj * rj)
    return ri + rj + r_bo - r_en


def _angle_constant(theta0, o12, o23, p1, p2, p3):
    c0 = cos(theta0)
    r12 = _rest_length(o12, p1, p2)
    r23 = _rest_length(o23, p2, p3)
    r13 = sqrt(r12 * r12 + r23 * r23 - 2.0 * r12 * r23 * c0)
    beta = 2.0 * G / (r12 * r23)
    pre = beta * p1[5] * p3[5] / r13 ** 5
    rterm = r12 * r23
    return pre * rterm * (3.0 * rterm * (1.0 - c0 * c0) - r13 * r13 * c0)


def _equation17(o, pj, pk):
    return 5.0 * sqrt(pj[7] * pk[7]) * (1.0 + 4.18 * log(o))


def _torsion_params(o, sj, sk, hj, hk, pj, pk, end_sp2):
    if hj == SP3 and hk == SP3:
        v, n, c = sqrt(pj[6] * pk[6]), 3, -1.0
        if o == 1.0 and sj in GROUP_16 and sk in GROUP_16:
            v = sqrt((2.0 if sj == 'O' else 6.8) * (2.0 if sk == 'O' else 6.8))
            n, c = 2, -1.0
        return v, n, c
    if hj == SP2 and hk == SP2:
        return _equation17(o, pj, pk), 2, 1.0
    v, n, c = 1.0, 6, 1.0
    if o == 1.0:
        if (hj == SP3 and sj in GROUP_16 and sk not in GROUP_16) or (hk == SP3 and sk in GROUP_16 and sj not in GROUP_16):
            return _equation17(o, pj, pk), 2, -1.0
        if end_sp2:
            return 2.0, 3, -1.0
    return v, n, c


def _inversion_params(symbol, bound_to_o):
    if symbol in ('C', 'N', 'O'):
        c0, c1, c2 = 1.0, -1.0, 0.0
        k = 50.0 if bound_to_o else 6.0
    else:
        w0 = {'P': 84.4339, 'As': 86.9735, 'Sb': 87.7047, 'Bi': 90.0}[symbol] * pi / 180.0
        c2 = 1.0
        c1 = -4.0 * cos(w0)
        c0 = -(c1 * cos(w0) + c2 * cos(2.0 * w0))
        k = 22.0 / (c0 + c1 + c2)
    return k / 3.0, (c0, c1, c2)


def build(molecule):
    """The terms of §3 for the structure (its bond orders as Compass perceives them)."""
    labels, hybrid, notes, order, neighbours = types(molecule)
    symbols = [a.symbol for a in molecule.atoms]
    n = len(symbols)
    p = [PARAMS[k] for k in labels]
    x0 = np.array([a.position for a in molecule.atoms], dtype=float)
    bonds, bk, br = [], [], []
    for (i, j), o in sorted(order.items()):
        r0 = _rest_length(o, p[i], p[j])
        bonds.append((i, j))
        br.append(r0)
        bk.append(2.0 * G * p[i][5] * p[j][5] / r0 ** 3)
    in3 = set().union(*_rings(neighbours, 3)) if n >= 3 else set()
    in4 = set().union(*_rings(neighbours, 4)) if n >= 4 else set()

    def o_of(a, b):
        return order[(min(a, b), max(a, b))]

    angles, ak, ao, ac, at = [], [], [], [], []

    def add_angle(i, j, k, kind):
        theta0 = p[j][1] * pi / 180.0
        if kind >= 30:
            theta0 = {30: 150.0, 35: 60.0, 40: 135.0, 45: 90.0}[kind] * pi / 180.0
            kind = 0
        force = _angle_constant(theta0, o_of(i, j), o_of(j, k), p[i], p[j], p[k])
        if kind == 0:
            s0, c0 = sin(theta0), cos(theta0)
            c2 = 1.0 / (4.0 * max(s0 * s0, 1e-8))
            coefficients = (c2 * (2.0 * c0 * c0 + 1.0), -4.0 * c2 * c0, c2)
        else:
            coefficients = (0.0, 0.0, 0.0)
        angles.append((i, j, k))
        ak.append(force)
        ao.append(kind)
        ac.append(coefficients)
        at.append(theta0)

    for j in range(n):
        nb = neighbours[j]
        if len(nb) < 2:
            continue
        if hybrid[j] == SP3D and len(nb) == 5:  # RDKit addTrigonalBipyramidAngles
            pairs = [(a, b) for ia, a in enumerate(nb) for b in nb[ia + 1:]]
            unit = {a: (x0[a] - x0[j]) / max(np.linalg.norm(x0[a] - x0[j]), 1e-12) for a in nb}
            ax = min(pairs, key=lambda ab: float(unit[ab[0]] @ unit[ab[1]]))
            eq = [a for a in nb if a not in ax]
            add_angle(ax[0], j, ax[1], 2)
            for a, b in ((eq[0], eq[1]), (eq[0], eq[2]), (eq[1], eq[2])):
                add_angle(a, j, b, 3)
            for a in ax:
                for b in eq:
                    add_angle(a, j, b, 0)
            continue
        for ia, i in enumerate(nb):
            for k in nb[ia + 1:]:
                kind = {SP: 1, SP2: 3, SP3D2: 4}.get(hybrid[j], 0)
                if hybrid[j] == SP2:
                    if j in in3:
                        if (i in in3) != (k in in3):
                            kind = 30
                        elif i in in3 and k in in3:
                            kind = 35
                    elif j in in4:
                        if (i in in4) != (k in in4):
                            kind = 40
                        elif i in in4 and k in in4:
                            kind = 45
                add_angle(i, j, k, kind)
    triple = [any(o_of(i, j) == 3 for j in neighbours[i]) for i in range(n)]
    torsions, tv, tn, tc = [], [], [], []
    for (j, k), o in sorted(order.items()):
        if triple[j] or triple[k] or len(neighbours[j]) < 2 or len(neighbours[k]) < 2:
            continue
        if hybrid[j] not in (SP2, SP3) or hybrid[k] not in (SP2, SP3):
            continue
        here = []
        for a in neighbours[j]:
            if a == k:
                continue
            for d in neighbours[k]:
                if d == j or d == a:
                    continue
                end_sp2 = hybrid[a] == SP2 or hybrid[d] == SP2
                here.append((a, j, k, d) + _torsion_params(o, symbols[j], symbols[k], hybrid[j], hybrid[k], p[j],
                                                           p[k], end_sp2))
        for a, b, c, d, v, nn, cc in here:
            torsions.append((a, b, c, d))
            tv.append(v / len(here))
            tn.append(nn)
            tc.append(cc)
    inversions, ik, icoef = [], [], []
    for j in range(n):
        s = symbols[j]
        if s not in ('C', 'N', 'O', 'P', 'As', 'Sb', 'Bi') or len(neighbours[j]) != 3:
            continue
        if s in ('C', 'N', 'O') and hybrid[j] != SP2:
            continue
        nb = neighbours[j]
        bound = s == 'C' and any(symbols[a] == 'O' and hybrid[a] == SP2 for a in nb)
        force, coefficients = _inversion_params(s, bound)
        for a, b, c in ((nb[0], nb[1], nb[2]), (nb[0], nb[2], nb[1]), (nb[1], nb[2], nb[0])):
            inversions.append((a, j, b, c))
            ik.append(force)
            icoef.append(coefficients)
    close = set(order)
    for j in range(n):
        for ia, a in enumerate(neighbours[j]):
            for b in neighbours[j][ia + 1:]:
                close.add((min(a, b), max(a, b)))
    pairs, px, pd = [], [], []
    for i in range(n):
        for j in range(i + 1, n):
            if (i, j) in close:
                continue
            xij = sqrt(p[i][2] * p[j][2])
            if np.linalg.norm(x0[i] - x0[j]) < 10.0 * xij:  # RDKit's vdwThresh
                pairs.append((i, j))
                px.append(xij)
                pd.append(sqrt(p[i][3] * p[j][3]))

    def ints(rows, width):
        return np.array(rows, dtype=int).reshape(-1, width)

    def floats(rows, width=None):
        a = np.array(rows, dtype=float)
        return a.reshape(-1, width) if width else a.reshape(-1)

    return Field(labels, notes, ints(bonds, 2), floats(bk), floats(br), ints(angles, 3), floats(ak),
                 np.array(ao, dtype=int), floats(ac, 3), floats(at), ints(torsions, 4), floats(tv),
                 np.array(tn, dtype=int), floats(tc), ints(inversions, 4), floats(ik), floats(icoef, 3),
                 ints(pairs, 2), floats(px), floats(pd))


def _add(g, index, values):
    """g[index] += values with repeated indices (np.add.at, by bincount — several times faster)."""
    n = len(g)
    for k in range(3):
        g[:, k] += np.bincount(index, weights=values[:, k], minlength=n)


def _norm(v):
    return np.sqrt(np.einsum('ij,ij->i', v, v))


def energy(f, x):
    """(E kcal/mol, gradient (n, 3), parts) of the field f at the positions x (n, 3) Å."""
    x = np.asarray(x, dtype=float)
    g = np.zeros_like(x)
    parts = {}
    # bonds
    if len(f.bonds):
        i, j = f.bonds[:, 0], f.bonds[:, 1]
        d = x[i] - x[j]
        r = np.maximum(_norm(d), 1e-12)
        dr = r - f.bond_r0
        parts['bond'] = float(0.5 * np.sum(f.bond_k * dr * dr))
        w = (f.bond_k * dr / r)[:, None] * d
        _add(g, i, w)
        _add(g, j, -w)
    else:
        parts['bond'] = 0.0
    # angles
    if len(f.angles):
        i, j, k = f.angles[:, 0], f.angles[:, 1], f.angles[:, 2]
        u, v = x[i] - x[j], x[k] - x[j]
        lu, lv = np.maximum(_norm(u), 1e-12), np.maximum(_norm(v), 1e-12)
        uh, vh = u / lu[:, None], v / lv[:, None]
        c = np.clip(np.einsum('ij,ij->i', uh, vh), -1.0, 1.0)
        s = np.maximum(np.sqrt(1.0 - c * c), 1e-8)
        theta = np.arccos(c)
        o = f.angle_order
        kk = f.angle_k
        e = np.zeros_like(c)
        de = np.zeros_like(c)
        general = o == 0
        c0, c1, c2 = f.angle_c[:, 0], f.angle_c[:, 1], f.angle_c[:, 2]
        cos2 = 2.0 * c * c - 1.0
        e[general] = kk[general] * (c0 + c1 * c + c2 * cos2)[general]
        de[general] = (-kk * (c1 * s + 2.0 * c2 * 2.0 * s * c))[general]
        one = o == 1
        e[one] = (kk * (1.0 + c))[one]
        de[one] = (-kk * s)[one]
        for nn in (2, 3, 4):
            m = o == nn
            if np.any(m):
                e[m] = (kk / nn ** 2 * (1.0 - np.cos(nn * theta)))[m]
                de[m] = (kk / nn * np.sin(nn * theta))[m]
        penalty = (o > 0) & (c > ANGLE_PENALTY_COS)
        if np.any(penalty):
            ex = np.exp(-20.0 * (theta - f.angle_theta0 + 0.25))
            e[penalty] += ex[penalty]
            de[penalty] += -20.0 * ex[penalty]
        parts['angle'] = float(np.sum(e))
        dc = de * (-1.0 / s)  # dE/dcos
        gi = dc[:, None] * (vh - c[:, None] * uh) / lu[:, None]
        gk = dc[:, None] * (uh - c[:, None] * vh) / lv[:, None]
        _add(g, i, gi)
        _add(g, k, gk)
        _add(g, j, -gi - gk)
    else:
        parts['angle'] = 0.0
    # torsions
    if len(f.torsions):
        a, b, c_, d = (f.torsions[:, m] for m in range(4))
        # Blondel and Karplus, J. Comput. Chem. 17, 1132 (1996): F = ri − rj, G = rj − rk, H = rl − rk
        ff, gg, hh = x[a] - x[b], x[b] - x[c_], x[d] - x[c_]
        aa, bb = np.cross(ff, gg), np.cross(hh, gg)
        lg = np.maximum(_norm(gg), 1e-12)
        a2 = np.maximum(np.einsum('ij,ij->i', aa, aa), 1e-16)
        b2 = np.maximum(np.einsum('ij,ij->i', bb, bb), 1e-16)
        phi = np.arctan2(np.einsum('ij,ij->i', np.cross(bb, aa), gg) / lg, np.einsum('ij,ij->i', aa, bb))
        nn = f.torsion_n
        parts['torsion'] = float(np.sum(f.torsion_v / 2.0 * (1.0 - f.torsion_cos * np.cos(nn * phi))))
        w = (f.torsion_v / 2.0 * f.torsion_cos * nn * np.sin(nn * phi))[:, None]  # dE/dφ
        fg = (np.einsum('ij,ij->i', ff, gg) / (a2 * lg))[:, None]
        hg = (np.einsum('ij,ij->i', hh, gg) / (b2 * lg))[:, None]
        ga = -(lg / a2)[:, None] * aa
        gd = (lg / b2)[:, None] * bb
        gb = -ga + fg * aa - hg * bb
        gc = -gd - fg * aa + hg * bb
        _add(g, a, w * ga)
        _add(g, b, w * gb)
        _add(g, c_, w * gc)
        _add(g, d, w * gd)
    else:
        parts['torsion'] = 0.0
    # inversions
    if len(f.inversions):
        i, j, k, l_ = (f.inversions[:, m] for m in range(4))
        u, v, w = x[i] - x[j], x[k] - x[j], x[l_] - x[j]
        nvec = np.cross(u, v)
        ln = np.maximum(_norm(nvec), 1e-12)
        lw = np.maximum(_norm(w), 1e-12)
        nh, wh = nvec / ln[:, None], w / lw[:, None]
        cy = np.clip(np.einsum('ij,ij->i', nh, wh), -1.0, 1.0)
        sy = np.maximum(np.sqrt(1.0 - cy * cy), 1e-8)
        c0, c1, c2 = f.inversion_c[:, 0], f.inversion_c[:, 1], f.inversion_c[:, 2]
        parts['inversion'] = float(np.sum(f.inversion_k * (c0 + c1 * sy + c2 * (2.0 * sy * sy - 1.0))))
        de_ds = f.inversion_k * (c1 + 4.0 * c2 * sy)
        de_dc = de_ds * (-cy / sy)
        gn = (wh - cy[:, None] * nh) / ln[:, None]  # dc/dn
        gw = (nh - cy[:, None] * wh) / lw[:, None]  # dc/dw
        gu = np.cross(v, gn)
        gv = np.cross(gn, u)
        q = de_dc[:, None]
        _add(g, i, q * gu)
        _add(g, k, q * gv)
        _add(g, l_, q * gw)
        _add(g, j, -q * (gu + gv + gw))
    else:
        parts['inversion'] = 0.0
    # van der Waals
    if len(f.pairs):
        i, j = f.pairs[:, 0], f.pairs[:, 1]
        d = x[i] - x[j]
        r = np.maximum(_norm(d), 1e-6)
        q = f.pair_x / r
        q6 = q ** 6
        q12 = q6 * q6
        parts['vdw'] = float(np.sum(f.pair_d * (q12 - 2.0 * q6)))
        de = f.pair_d * (-12.0 * q12 + 12.0 * q6) / r  # dE/dr
        w = (de / r)[:, None] * d
        _add(g, i, w)
        _add(g, j, -w)
    else:
        parts['vdw'] = 0.0
    return sum(parts.values()), g, parts


def _lbfgs(f, x, mask, tolerance, steps, keep=0, memory=8):
    e, g, _ = energy(f, x)
    g = g * mask
    pairs, frames = [], []
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
            q *= 0.05 / max(np.max(np.abs(q)), 1e-12)
        for (s_k, y_k, rho), a in zip(pairs, reversed(alphas)):
            q += s_k * (a - rho * (y_k @ q))
        dvec = -q.reshape(x.shape) * mask
        slope = float(np.sum(dvec * g))
        if slope >= 0:
            pairs.clear()
            dvec = -g * (0.05 / max(np.max(np.abs(g)), 1e-12))
            slope = float(np.sum(dvec * g))
        longest = np.max(np.abs(dvec))
        if longest > 0.2:  # an atom moves 0.2 Å at most per step
            dvec *= 0.2 / longest
            slope *= 0.2 / longest
        size = 1.0
        while True:
            x_new = x + size * dvec
            e_new, g_new, _ = energy(f, x_new)
            if e_new <= e + 1e-4 * size * slope or size < 1e-6:
                break
            size *= 0.5
        g_new = g_new * mask
        s_k, y_k = (x_new - x).ravel(), (g_new - g).ravel()
        sy = float(s_k @ y_k)
        if sy > 1e-12:
            pairs.append((s_k, y_k, 1.0 / sy))
            if len(pairs) > memory:
                pairs.pop(0)
        if size < 1e-6 and abs(e_new - e) < 1e-10:
            x, e, g = x_new, e_new, g_new
            break
        x, e, g = x_new, e_new, g_new
        if keep and step % keep == 0:
            frames.append((x.copy(), float(e)))
    return x, step, frames


def _fit(moved, reference):
    """The moved positions turned and shifted onto the reference (Kabsch)."""
    a = moved - moved.mean(axis=0)
    b = reference - reference.mean(axis=0)
    u, _, vt = np.linalg.svd(a.T @ b)
    sign = np.sign(np.linalg.det(u @ vt)) or 1.0
    rot = u @ np.diag([1.0, 1.0, sign]) @ vt
    return a @ rot + reference.mean(axis=0)


def optimize(molecule, movable=None, steps=2000, tolerance=1e-3, keep=0):
    """The structure at a minimum of UFF (§4): Result with the energy (kcal/mol) and its parts."""
    if len(molecule.atoms) < 2:
        raise ValueError(tr('Для UFF нужно хотя бы два атома.'))
    f = build(molecule)
    x0 = np.array([a.position for a in molecule.atoms], dtype=float)
    mask = np.ones((len(x0), 1))
    if movable:
        mask[:] = 0
        mask[list(movable)] = 1
    start, _, _ = energy(f, x0)
    moving = f
    if movable:  # van der Waals pairs of two fixed atoms are constant — left out while minimizing
        free = mask[:, 0] > 0
        keep_pairs = free[f.pairs[:, 0]] | free[f.pairs[:, 1]] if len(f.pairs) else np.zeros(0, bool)
        moving = replace(f, pairs=f.pairs[keep_pairs], pair_x=f.pair_x[keep_pairs], pair_d=f.pair_d[keep_pairs])
    x, step, frames = _lbfgs(moving, x0.copy(), mask, tolerance, steps, keep)
    if not movable:
        x = _fit(x, x0)
        frames = [(_fit(p, x0), e) for p, e in frames]
    total, _, parts = energy(f, x)
    atoms = tuple(Atom(a.symbol, *map(float, p)) for a, p in zip(molecule.atoms, x))
    return Result(Molecule(molecule.title, atoms, molecule.bonds), float(total), parts, step, f.labels, f.notes,
                  float(start), frames)
