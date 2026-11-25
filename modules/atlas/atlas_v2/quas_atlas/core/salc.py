"""Reducible representations of ligand orbitals, the reduction formula and SALCs by projection operators.

HEADER
    Model of the panel "Приводимое представление и SALC" of the page "Точечные группы" (web/<lang>/symmetry.html),
    Atlas 2026-10-25. Wilkinson convention, sections 1-8.

§1 THEORY
    N equivalent σ-orbitals φ_1..φ_N of the ligands (H 1s of H₂O, NH₃, CH₄; σ lone pairs of F, Cl, F₆) are moved
    into each other by the symmetry operations R: R φ_k = φ_{R(k)}. The characters of this (permutation)
    representation Γ are the numbers of ligands left in place. The reduction formula gives how many times
    the irreducible representation i occurs:
        n_i = (1/h) Σ_c g_c χ_Γ(c) χ_i(c) (h — group order, g_c — class size).
    The projection operator P^i = (d_i/h) Σ_R χ_i(R) R applied to φ_1 (and, for degenerate i, to the other φ_k)
    gives symmetry-adapted linear combinations; orthonormalised (ligand orbitals taken orthonormal) they are
    the SALCs, n_i d_i of them for every i.
    Conventions: C2v with the molecule in the yz plane (Mulliken 1955: x perpendicular to the plane), so the
    H 1s of H₂O span A1 + B2; C3v σv through the N–H bonds; D3h, Td, D4h (C2′ through the ligands, σv containing
    them), Oh — the usual tables (Cotton, «Chemical Applications of Group Theory»).

§2 ALGORITHM
    The group is generated from 3x3 matrices of a few generators (closure); each operation is assigned to a
    class by its order, determinant and the direction of its axis or of the normal of its plane (rules in
    _classify); the permutation of the ligands by matching R p_k with the positions p_j (1e-6).

§3 APPLICATIONS
    Endpoint sym.salc.

§4 SPECIFICATION
    salc(key) -> {"group", "h", "classes": [{"name", "g"}], "table": [[irrep, d, [χ by class]]], "gamma": [χ_Γ],
                  "reduce": [{"irrep", "n", "terms": [g_c χ_Γ χ_i]}], "salc": [{"irrep", "c": [coefficients]}],
                  "ligands": N, "positions": [[x, y, z]]}.

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    Pure Python; groups of order <= 48.
§7 TEST CASES (tests/test_atlas_course1.py)
    Group orders 4, 6, 12, 24, 16, 48 and class sizes sum to h; the character tables are orthonormal
    (Σ g χ_i χ_j = h δ_ij); H₂O A1 + B2, NH₃ A1 + E, BF₃ A1′ + E′, CH₄ A1 + T2, PtCl₄²⁻ A1g + B1g + Eu,
    SF₆ A1g + Eg + T1u (textbook results); every SALC is normalised and they are mutually orthogonal.
§8 ERROR ANALYSIS
    Integer characters and permutations: exact; Gram–Schmidt on ≤ 6 vectors, errors ~1e-15.
"""
from __future__ import annotations

import math

S3, S2 = math.sqrt(3), math.sqrt(2)


def _mm(A, B):
    return [[sum(A[i][k] * B[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def _mv(A, v):
    return [sum(A[i][k] * v[k] for k in range(3)) for i in range(3)]


def _key(M):
    return tuple(round(x, 6) + 0.0 for row in M for x in row)


def _det(M):
    (a, b, c), (d, e, f), (g, h, i) = M
    return a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)


def _close(gens):
    I = [[1.0 if i == j else 0.0 for j in range(3)] for i in range(3)]
    els = {_key(I): I}
    frontier = [I]
    while frontier:
        nxt = []
        for A in frontier:
            for G in gens:
                B = _mm(G, A)
                k = _key(B)
                if k not in els:
                    els[k] = B
                    nxt.append(B)
        frontier = nxt
        if len(els) > 200:
            raise ValueError("group did not close")
    return list(els.values())


def _order(M):
    A = M
    for n in range(1, 13):
        if all(abs(A[i][j] - (1.0 if i == j else 0.0)) < 1e-9 for i in range(3) for j in range(3)):
            return n
        A = _mm(A, M)
    raise ValueError("order > 12")


def _axis(M, sign):
    """Rotation axis (sign = +1, vector kept) or reflection normal (sign = -1, vector reversed) of M."""
    N = [[M[i][j] + sign * (1.0 if i == j else 0.0) for j in range(3)] for i in range(3)]
    if sign == 1:  # proper: axis from the antisymmetric part, or for order 2 from M + I
        a = [M[2][1] - M[1][2], M[0][2] - M[2][0], M[1][0] - M[0][1]]
        if math.hypot(*a) > 1e-6:
            n = math.hypot(*a)
            return [x / n for x in a]
    cols = [[N[i][j] for i in range(3)] for j in range(3)]
    best = max(cols, key=lambda v: math.hypot(*v))
    n = math.hypot(*best)
    return [x / n for x in best]


def _kind(v):
    """'coord' — along x, y or z; 'z'; 'diag' — other."""
    a = [abs(x) for x in v]
    if max(a) > 1 - 1e-6:
        return "z" if a[2] > 1 - 1e-6 else "coord"
    return "diag"


def _rz(t):
    c, s = math.cos(t), math.sin(t)
    return [[c, -s, 0], [s, c, 0], [0, 0, 1]]


def _diag(a, b, c):
    return [[a, 0, 0], [0, b, 0], [0, 0, c]]


def _classify(group, M):
    d = 1 if _det(M) > 0 else -1
    o = _order(M)
    if o == 1:
        return "E"
    if d == 1:
        ax = _axis(M, 1)
        if group == "C2v":
            return "C2"
        if group in ("C3v",):
            return "C3"
        if group == "D3h":
            return "C3" if o == 3 else "C2"
        if group == "Td":
            return {3: "C3", 2: "C2"}[o]
        if group == "D4h":
            if o == 4:
                return "C4"
            k = _kind(ax)
            return "C2" if k == "z" else ("C2'" if k == "coord" else "C2''")
        if group == "Oh":
            if o == 3:
                return "C3"
            if o == 4:
                return "C4"
            return "C2c" if _kind(ax) in ("coord", "z") else "C2'"
    if all(abs(M[i][j] + (1.0 if i == j else 0.0)) < 1e-9 for i in range(3) for j in range(3)):
        return "i"
    if o == 2:  # a reflection
        nv = _axis(M, -1)
        if group == "C2v":
            return "sv(xz)" if abs(nv[1]) > 1 - 1e-6 else "sv(yz)"
        if group == "C3v":
            return "sv"
        if group == "D3h":
            return "sh" if abs(nv[2]) > 1 - 1e-6 else "sv"
        if group == "Td":
            return "sd"
        if group == "D4h":
            k = _kind(nv)
            return "sh" if k == "z" else ("sv" if k == "coord" else "sd")
        if group == "Oh":
            return "sh" if _kind(nv) in ("coord", "z") else "sd"
    return {3: "S3", 4: "S4", 6: "S6" if group == "Oh" else "S3"}.get(o, "S%d" % o)


C3 = _rz(2 * math.pi / 3)
GROUPS = {
    "C2v": {"gens": [_diag(-1, -1, 1), _diag(-1, 1, 1)],
            "classes": ["E", "C2", "sv(xz)", "sv(yz)"],
            "names": ["E", "C₂", "σᵥ(xz)", "σᵥ′(yz)"],
            "table": [["A₁", 1, [1, 1, 1, 1]], ["A₂", 1, [1, 1, -1, -1]], ["B₁", 1, [1, -1, 1, -1]], ["B₂", 1, [1, -1, -1, 1]]]},
    "C3v": {"gens": [C3, _diag(1, -1, 1)],
            "classes": ["E", "C3", "sv"], "names": ["E", "2C₃", "3σᵥ"],
            "table": [["A₁", 1, [1, 1, 1]], ["A₂", 1, [1, 1, -1]], ["E", 2, [2, -1, 0]]]},
    "D3h": {"gens": [C3, _diag(1, -1, -1), _diag(1, 1, -1)],
            "classes": ["E", "C3", "C2", "sh", "S3", "sv"], "names": ["E", "2C₃", "3C₂", "σₕ", "2S₃", "3σᵥ"],
            "table": [["A₁′", 1, [1, 1, 1, 1, 1, 1]], ["A₂′", 1, [1, 1, -1, 1, 1, -1]], ["E′", 2, [2, -1, 0, 2, -1, 0]],
                      ["A₁″", 1, [1, 1, 1, -1, -1, -1]], ["A₂″", 1, [1, 1, -1, -1, -1, 1]], ["E″", 2, [2, -1, 0, -2, 1, 0]]]},
    "Td": {"gens": [[[0, 0, 1], [1, 0, 0], [0, 1, 0]], [[0, 1, 0], [-1, 0, 0], [0, 0, -1]]],
           "classes": ["E", "C3", "C2", "S4", "sd"], "names": ["E", "8C₃", "3C₂", "6S₄", "6σd"],
           "table": [["A₁", 1, [1, 1, 1, 1, 1]], ["A₂", 1, [1, 1, 1, -1, -1]], ["E", 2, [2, -1, 2, 0, 0]],
                     ["T₁", 3, [3, 0, -1, 1, -1]], ["T₂", 3, [3, 0, -1, -1, 1]]]},
    "D4h": {"gens": [_rz(math.pi / 2), _diag(1, -1, -1), _diag(-1, -1, -1)],
            "classes": ["E", "C4", "C2", "C2'", "C2''", "i", "S4", "sh", "sv", "sd"],
            "names": ["E", "2C₄", "C₂", "2C₂′", "2C₂″", "i", "2S₄", "σₕ", "2σᵥ", "2σd"],
            "table": [["A₁g", 1, [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]], ["A₂g", 1, [1, 1, 1, -1, -1, 1, 1, 1, -1, -1]],
                      ["B₁g", 1, [1, -1, 1, 1, -1, 1, -1, 1, 1, -1]], ["B₂g", 1, [1, -1, 1, -1, 1, 1, -1, 1, -1, 1]],
                      ["Eg", 2, [2, 0, -2, 0, 0, 2, 0, -2, 0, 0]], ["A₁u", 1, [1, 1, 1, 1, 1, -1, -1, -1, -1, -1]],
                      ["A₂u", 1, [1, 1, 1, -1, -1, -1, -1, -1, 1, 1]], ["B₁u", 1, [1, -1, 1, 1, -1, -1, 1, -1, -1, 1]],
                      ["B₂u", 1, [1, -1, 1, -1, 1, -1, 1, -1, 1, -1]], ["Eu", 2, [2, 0, -2, 0, 0, -2, 0, 2, 0, 0]]]},
    "Oh": {"gens": [_rz(math.pi / 2), [[0, 0, 1], [1, 0, 0], [0, 1, 0]], _diag(-1, -1, -1)],
           "classes": ["E", "C3", "C2'", "C4", "C2c", "i", "S4", "S6", "sh", "sd"],
           "names": ["E", "8C₃", "6C₂", "6C₄", "3C₂(=C₄²)", "i", "6S₄", "8S₆", "3σₕ", "6σd"],
           "table": [["A₁g", 1, [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]], ["A₂g", 1, [1, 1, -1, -1, 1, 1, -1, 1, 1, -1]],
                     ["Eg", 2, [2, -1, 0, 0, 2, 2, 0, -1, 2, 0]], ["T₁g", 3, [3, 0, -1, 1, -1, 3, 1, 0, -1, -1]],
                     ["T₂g", 3, [3, 0, 1, -1, -1, 3, -1, 0, -1, 1]], ["A₁u", 1, [1, 1, 1, 1, 1, -1, -1, -1, -1, -1]],
                     ["A₂u", 1, [1, 1, -1, -1, 1, -1, 1, -1, -1, 1]], ["Eu", 2, [2, -1, 0, 0, 2, -2, 0, 1, -2, 0]],
                     ["T₁u", 3, [3, 0, -1, 1, -1, -3, -1, 0, 1, 1]], ["T₂u", 3, [3, 0, 1, -1, -1, -3, 1, 0, 1, -1]]]},
}
_c, _s = math.cos(math.radians(52.25)), math.sin(math.radians(52.25))
MOLECULES = {
    "h2o": ("C2v", [[0, _s, -_c], [0, -_s, -_c]]),
    "nh3": ("C3v", [[math.cos(a), math.sin(a), -0.35] for a in (0, 2 * math.pi / 3, 4 * math.pi / 3)]),
    "bf3": ("D3h", [[math.cos(a), math.sin(a), 0] for a in (0, 2 * math.pi / 3, 4 * math.pi / 3)]),
    "ch4": ("Td", [[1, 1, 1], [1, -1, -1], [-1, 1, -1], [-1, -1, 1]]),
    "ptcl4": ("D4h", [[1, 0, 0], [0, 1, 0], [-1, 0, 0], [0, -1, 0]]),
    "sf6": ("Oh", [[1, 0, 0], [0, 1, 0], [0, 0, 1], [-1, 0, 0], [0, -1, 0], [0, 0, -1]]),
}


def group_data(name):
    g = GROUPS[name]
    ops = _close(g["gens"])
    cls = [_classify(name, M) for M in ops]
    sizes = [cls.count(c) for c in g["classes"]]
    if sum(sizes) != len(ops) or any(s == 0 for s in sizes):
        raise ValueError(f"classes of {name} do not match: {sizes}")
    return ops, cls, sizes


def salc(key: str) -> dict:
    if key not in MOLECULES:
        raise ValueError("unknown molecule")
    gname, pos = MOLECULES[key]
    pos = [[x / math.hypot(*p) for x in p] for p in pos]
    g = GROUPS[gname]
    ops, cls, sizes = group_data(gname)
    h, N = len(ops), len(pos)

    def perm(M):
        out = []
        for p in pos:
            q = _mv(M, p)
            j = next((j for j, r in enumerate(pos) if math.dist(q, r) < 1e-6), None)
            if j is None:
                raise ValueError("an operation moves a ligand off the set")
            out.append(j)
        return out

    perms = [perm(M) for M in ops]
    gamma = []
    for c in g["classes"]:
        k = cls.index(c)
        gamma.append(sum(1 for i, j in enumerate(perms[k]) if i == j))
    red, salcs = [], []
    for irrep, d, chi in g["table"]:
        terms = [sizes[c] * gamma[c] * chi[c] for c in range(len(chi))]
        n = sum(terms) / h
        red.append({"irrep": irrep, "n": round(n), "terms": terms})
        if round(n) == 0:
            continue
        vecs = []
        for k in range(N):  # project every ligand orbital, keep the independent results
            v = [0.0] * N
            for M, P, c in zip(ops, perms, cls):
                v[P[k]] += chi[g["classes"].index(c)] * d / h
            for u in vecs:
                dot = sum(a * b for a, b in zip(u, v))
                v = [a - dot * b for a, b in zip(v, u)]
            nv = math.sqrt(sum(a * a for a in v))
            if nv > 1e-8:
                vecs.append([a / nv for a in v])
            if len(vecs) == round(n) * d:
                break
        salcs += [{"irrep": irrep, "c": [0.0 if abs(a) < 1e-12 else a for a in v]} for v in vecs]
    return {"group": gname, "h": h, "classes": [{"name": nm, "g": s} for nm, s in zip(g["names"], sizes)],
            "table": g["table"], "gamma": gamma, "reduce": red, "salc": salcs, "ligands": N, "positions": pos}
