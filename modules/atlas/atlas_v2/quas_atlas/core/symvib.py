"""Normal modes of the symmetry-page models in a model force field, and their symmetry.

HEADER
    Port of the "колебания: модельное силовое поле" part of v1.0
    symmetry.js (buildTerms ... cleanBasis, vibLinLabel).  Wilkinson
    convention, sections 1-8.

§1 THEORY
    A valence force field: harmonic bond stretches k (r - r0)^2 (bonded
    pairs; weak k for non-bonded pairs closer than 2.6), angle bends
    k_a (theta - theta0)^2, an out-of-plane term for three-coordinated atoms,
    and torsions 0.15 (1 - cos(phi - phi0)).  Force constants depend weakly
    on the masses (arbitrary but symmetric, so that accidental degeneracies
    are rare).  The Cartesian Hessian F is obtained by central finite
    differences (step 1e-4) of each term; the mass-weighted Hessian
    M^-1/2 F M^-1/2 is diagonalised (cyclic Jacobi).  The 3N - 6 (3N - 5)
    largest eigenvalues are the vibrations; eigenvalues equal within
    2e-4 w_max form one (degenerate) set.  The symmetry species of a set
    follows from its character chi(R) = sum_modes q . R q under the
    operations of each class (reduction formula); sets that contain several
    species (accidental degeneracy) are split with the projection operators
    P_Gamma = (d/h) sum_g chi_Gamma(g) R(g).  Degenerate components are
    rotated to diagonalise the symmetrised action of reflections and C2
    rotations, so that they transform "like x", "like y".
    Frequencies are not physical (model force constants); the symmetry of
    the modes is exact.

§2 ALGORITHM
    As in v1.0 (function names kept): build_terms, hessian, jacobi,
    normal_modes, classify_set, projectors, vib_sets, clean_basis,
    vib_lin_label.

§3 APPLICATIONS
    Endpoint sym.vib ("Колебания" tab).

§4 SPECIFICATION
    vib_sets(atoms, bonds, G, B, linear) -> {'sets': [{'set': [mode], 'n':
    multiplicities or None, 'acc': bool?}], 'floppy': int, 'wmax': float};
    mode = {'w', 'q', 'u'} (eigenvalue, mass-weighted eigenvector,
    Cartesian displacement).  Bitwise equal to v1.0 in Chromium 141 (sin,
    cos, atan2, acos and hypot from core.jsmath).  Tier: bitwise vs v1.0.

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    * Jacobi rotations update whole rows and columns; the Python loops keep
      the element order of v1.0 (each element is computed by the same two
      products and one sum, so vectorising over k would not change bits,
      but plain loops are kept for clarity).
    * permOf returns -1 for an atom without an image; v1.0 then writes to
      index -3..-1 of a JS array (a no-op); here the atom is skipped.
§7 TEST CASES (tests/test_symmetry.py)
    H2O: 3 modes 2A1 + B1; CH4: A1 + E + 2T2 (9 modes, sets of 1, 2, 3, 3);
    every mode set is orthonormal in the mass-weighted metric; projectors
    are idempotent on the modes; vs Chromium for all page models.
§8 ERROR ANALYSIS
    Finite differences with h = 1e-4 on terms of size O(1): truncation
    O(h^2) ~ 1e-8, rounding O(u/h^2) ~ 1e-8 relative -> Hessian entries
    accurate to ~1e-8; eigenvectors of non-degenerate modes to ~1e-8 /
    gap.  The degeneracy threshold 2e-4 w_max is far above this and the
    character of a set is an integer to ~1e-6, so species are exact.
"""
from __future__ import annotations

import math

from .jsmath import acos, atan2, cos, hypot3, js_hypot, js_round, js_sign, sin, sq
from .symmetry import INV, PI, ZZ, ax_letter, cross, dot, info, mm, mv, nrm, plane_name, reduce_rep, refl, rot, tp

MASS = {"H": 1, "D": 2, "B": 11, "C": 12, "N": 14, "O": 16, "F": 19, "S": 32, "Cl": 35, "Se": 79, "Br": 80, "X": 56,
        "P": 31, "Si": 28, "Xe": 131, "I": 127, "Fe": 56, "Pt": 195, "Co": 59, "Ni": 59, "Cu": 64, "Ru": 101, "Li": 7,
        "Na": 23, "Mg": 24, "Al": 27, "As": 75, "Sb": 122, "Te": 128}


def _ms(t):
    return MASS.get(t) or 20


def vsub(a, b):
    return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]


def angle_of(a, b):
    """Math.atan2(Math.hypot(...cross(a,b)), dot(a,b))."""
    a0, a1, a2 = a
    b0, b1, b2 = b
    return atan2(hypot3(a1 * b2 - a2 * b1, a2 * b0 - a0 * b2, a0 * b1 - a1 * b0), a0 * b0 + a1 * b1 + a2 * b2)


def _angle3(x0, x1, x2):
    """angle_of(vsub(x0, x1), vsub(x2, x1)) without temporaries (same operations)."""
    a0, a1, a2 = x0[0] - x1[0], x0[1] - x1[1], x0[2] - x1[2]
    b0, b1, b2 = x2[0] - x1[0], x2[1] - x1[1], x2[2] - x1[2]
    return atan2(hypot3(a1 * b2 - a2 * b1, a2 * b0 - a0 * b2, a0 * b1 - a1 * b0), a0 * b0 + a1 * b1 + a2 * b2)


def _dih(x):
    """Dihedral angle of v1.0 (b1 = x1-x0, ...; n1 = b1 x b2, n2 = b2 x b3; m = n1 x b2/|b2|)."""
    p0, p1, p2, p3 = x
    b10, b11, b12 = p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]
    b20, b21, b22 = p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2]
    b30, b31, b32 = p3[0] - p2[0], p3[1] - p2[1], p3[2] - p2[2]
    n10, n11, n12 = b11 * b22 - b12 * b21, b12 * b20 - b10 * b22, b10 * b21 - b11 * b20
    n20, n21, n22 = b21 * b32 - b22 * b31, b22 * b30 - b20 * b32, b20 * b31 - b21 * b30
    l = hypot3(b20, b21, b22)
    u0, u1, u2 = b20 / l, b21 / l, b22 / l
    m0, m1, m2 = n11 * u2 - n12 * u1, n12 * u0 - n10 * u2, n10 * u1 - n11 * u0
    return atan2(m0 * n20 + m1 * n21 + m2 * n22, n10 * n20 + n11 * n21 + n12 * n22)


def build_terms(atoms, bonds):
    """Force-field terms [(ids, f)] with f(x) the energy for positions x of atoms ids."""
    nb = [[] for _ in atoms]
    for i, j in bonds:
        nb[i].append(j)
        nb[j].append(i)
    T = []
    P = [a["p"] for a in atoms]
    t_ = [a["t"] for a in atoms]
    bonded = {f"{min(i, j)},{max(i, j)}" for i, j in bonds}

    def stretch(k, r0):
        def f(x):
            a, b = x
            return k * sq(hypot3(a[0] - b[0], a[1] - b[1], a[2] - b[2]) - r0)
        return f

    for i, j in bonds:
        r0 = js_hypot(*vsub(P[i], P[j]))
        k = 5 * (1 + 0.13 * ((_ms(t_[i]) + _ms(t_[j])) % 7))
        T.append(([i, j], stretch(k, r0)))
    n = len(atoms)
    for i in range(n):
        for j in range(i + 1, n):
            if f"{i},{j}" in bonded:
                continue
            r0 = js_hypot(*vsub(P[i], P[j]))
            if r0 > 2.6:
                continue
            k = 0.06 * (1 + 0.1 * ((_ms(t_[i]) + _ms(t_[j])) % 5))
            T.append(([i, j], stretch(k, r0)))

    def bend(ka, t0):
        return lambda x: ka * sq(_angle3(x[0], x[1], x[2]) - t0)

    def vol(x):
        u = [nrm(vsub(x[k], x[0])) for k in (1, 2, 3)]
        return dot(cross(u[0], u[1]), u[2])

    def oop(v0):
        return lambda x: 0.5 * sq(vol(x) - v0)

    for j in range(n):
        nj = nb[j]
        for p in range(len(nj)):
            for q in range(p + 1, len(nj)):
                i, k = nj[p], nj[q]
                t0 = angle_of(vsub(P[i], P[j]), vsub(P[k], P[j]))
                ka = 0.8 * (1 + 0.11 * ((_ms(t_[i]) + _ms(t_[j]) + _ms(t_[k])) % 5))
                T.append(([i, j, k], bend(ka, t0)))
        if len(nj) == 3:
            ids = [j, *nj]
            T.append((ids, oop(vol([P[k] for k in ids]))))

    def tors(p0):
        return lambda x: 0.15 * (1 - cos(_dih(x) - p0))

    for j, k in bonds:
        for i in nb[j]:
            if i == k:
                continue
            for l in nb[k]:
                if l == j or l == i:
                    continue
                ids = [i, j, k, l]
                x0 = [P[t] for t in ids]
                if sin(angle_of(vsub(x0[0], x0[1]), vsub(x0[2], x0[1]))) < 0.2 or \
                        sin(angle_of(vsub(x0[1], x0[2]), vsub(x0[3], x0[2]))) < 0.2:
                    continue
                T.append((ids, tors(_dih(x0))))
    return T


def hessian(atoms, bonds):
    N = len(atoms)
    n = 3 * N
    H = [[0.0] * n for _ in range(n)]
    h = 1e-4
    hh, h4 = h * h, 4 * h * h
    for ids, f in build_terms(atoms, bonds):
        m = len(ids)
        x = [list(atoms[i]["p"]) for i in ids]
        for a in range(3 * m):
            ia, ca = a // 3, a % 3
            for b in range(a, 3 * m):
                ib, cb = b // 3, b % 3
                if a == b:
                    o = x[ia][ca]
                    x[ia][ca] = o + h
                    ep = f(x)
                    x[ia][ca] = o - h
                    em = f(x)
                    x[ia][ca] = o
                    e0 = f(x)
                    v = (ep - 2 * e0 + em) / hh
                else:
                    oa, ob = x[ia][ca], x[ib][cb]

                    def s(da, db):
                        x[ia][ca] = oa + da
                        x[ib][cb] = ob + db
                        e = f(x)
                        x[ia][ca] = oa
                        x[ib][cb] = ob
                        return e
                    v = (s(h, h) - s(h, -h) - s(-h, h) + s(-h, -h)) / h4
                A, Bq = 3 * ids[ia] + ca, 3 * ids[ib] + cb
                H[A][Bq] += v
                if A != Bq:
                    H[Bq][A] += v
    return H


try:  # optional: the same element-wise operations, vectorised (see §6)
    import numpy as _np
except ImportError:  # pragma: no cover - pure-Python path below
    _np = None


def jacobi(A0):
    """Cyclic Jacobi (v1.0 jacobi): eigenvalues w and eigenvector matrix V (columns)."""
    if _np is not None and len(A0) > 12:
        return _jacobi_np(A0)
    return _jacobi_py(A0)


def _jacobi_np(A0):
    """jacobi with numpy rows/columns: every element is c*x - s*y or s*x + c*y as in the loop
    (one IEEE multiply per factor, then one add; numpy does not fuse separate ufunc calls),
    so the result is bitwise that of _jacobi_py."""
    n = len(A0)
    A = _np.array(A0, dtype=float)
    V = _np.eye(n)
    for _sweep in range(60):
        off = 0.0
        L = A.tolist()
        for p in range(n):
            Lp = L[p]
            for q in range(p + 1, n):
                off += Lp[q] * Lp[q]
        if off < 1e-22:
            break
        for p in range(n):
            for q in range(p + 1, n):
                apq = float(A[p, q])
                if abs(apq) < 1e-14:
                    continue
                th = (float(A[q, q]) - float(A[p, p])) / (2 * apq)
                t = js_sign(th or 1) / (abs(th) + math.sqrt(th * th + 1))
                c = 1 / math.sqrt(t * t + 1)
                s = t * c
                cp, cq = A[:, p].copy(), A[:, q].copy()
                A[:, p] = c * cp - s * cq
                A[:, q] = s * cp + c * cq
                rp, rq = A[p, :].copy(), A[q, :].copy()
                A[p, :] = c * rp - s * rq
                A[q, :] = s * rp + c * rq
                vp, vq = V[:, p].copy(), V[:, q].copy()
                V[:, p] = c * vp - s * vq
                V[:, q] = s * vp + c * vq
    return [float(A[i, i]) for i in range(n)], V.tolist()


def _jacobi_py(A0):
    n = len(A0)
    A = [list(r) for r in A0]
    V = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    for _sweep in range(60):
        off = 0.0
        for p in range(n):
            Ap = A[p]
            for q in range(p + 1, n):
                off += Ap[q] * Ap[q]
        if off < 1e-22:
            break
        for p in range(n):
            for q in range(p + 1, n):
                apq = A[p][q]
                if abs(apq) < 1e-14:
                    continue
                th = (A[q][q] - A[p][p]) / (2 * apq)
                t = js_sign(th or 1) / (abs(th) + math.sqrt(th * th + 1))
                c = 1 / math.sqrt(t * t + 1)
                s = t * c
                for row in A:
                    akp, akq = row[p], row[q]
                    row[p] = c * akp - s * akq
                    row[q] = s * akp + c * akq
                Ap, Aq = A[p], A[q]
                A[p] = [c * apk - s * aqk for apk, aqk in zip(Ap, Aq)]
                A[q] = [s * apk + c * aqk for apk, aqk in zip(Ap, Aq)]
                for row in V:
                    vkp, vkq = row[p], row[q]
                    row[p] = c * vkp - s * vkq
                    row[q] = s * vkp + c * vkq
    return [A[i][i] for i in range(n)], V


def perm_of(M, atoms):
    """Image index of every atom under M (-1 if none), as v1.0 permOf (first match within 2e-3).

    |dx|, |dy|, |dz| < 2e-3 is a necessary condition for Math.hypot < 2e-3 (V8's
    hypot is never below the largest |component|), so the cheap test only
    skips candidates the exact test would reject."""
    out = []
    for a in atoms:
        q0, q1, q2 = mv(M, a["p"])
        t = a["t"]
        j = -1
        for k, b in enumerate(atoms):
            p = b["p"]
            d0, d1, d2 = q0 - p[0], q1 - p[1], q2 - p[2]
            if (b["t"] == t and -2e-3 < d0 < 2e-3 and -2e-3 < d1 < 2e-3 and -2e-3 < d2 < 2e-3
                    and hypot3(d0, d1, d2) < 2e-3):
                j = k
                break
        out.append(j)
    return out


def act_disp(M, perm, u):
    out = [0.0] * len(u)
    for a, b in enumerate(perm):
        if b < 0:
            continue
        v = mv(M, [u[3 * a], u[3 * a + 1], u[3 * a + 2]])
        out[3 * b], out[3 * b + 1], out[3 * b + 2] = v
    return out


def dot3n(a, b):
    s = 0.0
    for x, y in zip(a, b):
        s += x * y
    return s


def _u(q, atoms):
    return [x / math.sqrt(_ms(atoms[k // 3]["t"])) for k, x in enumerate(q)]


def normal_modes(atoms, bonds, linear):
    n = 3 * len(atoms)
    H = hessian(atoms, bonds)
    m = [_ms(a["t"]) for a in atoms]
    for i in range(n):
        Hi = H[i]
        for j in range(n):
            Hi[j] /= math.sqrt(m[i // 3] * m[j // 3])
    w, V = jacobi(H)
    idx = sorted(range(n), key=lambda i: w[i])
    nz = 5 if linear else 6
    wmax = max(w)
    modes = [{"w": w[i], "q": [r[i] for r in V]} for i in idx[nz:]]
    floppy = sum(1 for md in modes if md["w"] < 1e-6 * wmax)
    for md in modes:
        md["u"] = [x / math.sqrt(m[k // 3]) for k, x in enumerate(md["q"])]
    modes.reverse()
    sets = []
    for md in modes:
        if sets and abs(sets[-1][0]["w"] - md["w"]) < 2e-4 * wmax:
            sets[-1].append(md)
        else:
            sets.append([md])
    return {"sets": sets, "floppy": floppy, "wmax": wmax}


def classify_set(st, atoms, B):
    ct = B["ct"]
    chi = [0.0] * len(ct["classes"])
    Qt = tp(B["Q"])
    for j, c in enumerate(ct["classes"]):
        M = mm(mm(B["Q"], c["M"]), Qt)
        perm = perm_of(M, atoms)
        s = 0.0
        for md in st:
            s += dot3n(md["q"], act_disp(M, perm, md["q"]))
        chi[j] = s
    return [int(js_round(x)) for x in reduce_rep(chi, ct)]


def projectors(G, atoms, B):
    ct, h = B["ct"], len(G)
    perms = [perm_of(M, atoms) for M in G]

    def make(ir):
        f = (ir["dim"] / 2 if ir["merged"] else ir["dim"]) / h

        def P(v):
            out = [0.0] * len(v)
            for g, M in enumerate(G):
                c = ir["chi"][B["opCol"][g]]
                if abs(c) < 1e-12:
                    continue
                r = act_disp(M, perms[g], v)
                fc = f * c
                for i in range(len(v)):
                    out[i] += fc * r[i]
            return out
        return P

    return [make(ir) for ir in ct["irreps"]]


def vib_sets(atoms, bonds, G, B, linear):
    nm = normal_modes(atoms, bonds, linear)
    ct = B["ct"] if B else None
    PR = None
    res = []
    for st in nm["sets"]:
        if not B:
            res.append({"set": st, "n": None})
            continue
        n = classify_set(st, atoms, B)
        if sum(n) > 1:
            PR = PR or projectors(G, atoms, B)
            for j, cnt in enumerate(n):
                if not cnt:
                    continue
                d = ct["irreps"][j]["dim"]
                basis = []
                for md in st:
                    v = PR[j](md["q"])
                    for b in basis:
                        c = dot3n(v, b)
                        v = [x - c * b[i] for i, x in enumerate(v)]
                    l = math.sqrt(dot3n(v, v))
                    if l > 1e-4 and len(basis) < cnt * d:
                        basis.append([x / l for x in v])
                for c in range(cnt):
                    sub = [{"w": st[0]["w"], "q": q, "u": _u(q, atoms)} for q in basis[c * d:(c + 1) * d]]
                    nn = [0] * len(n)
                    nn[j] = 1
                    res.append({"set": sub, "n": nn, "acc": True})
        else:
            res.append({"set": st, "n": n})
    for r in res:
        r["set"] = clean_basis(r["set"], G, atoms)
    return {"sets": res, "floppy": nm["floppy"], "wmax": nm["wmax"]}


def clean_basis(st, G, atoms):
    if len(st) < 2:
        return st
    V = [list(md["q"]) for md in st]
    blocks = [list(range(len(V)))]

    def sc(f):
        l = (plane_name(f["ax"]) if f["t"] == "s" else ax_letter(f["ax"])) if f.get("ax") else None
        return (0 if l else 2) + (0 if f["t"] == "s" else 1)

    ops = []
    for M in G:
        f = info(M)
        if f["t"] == "s" or (f["t"] == "C" and f["n"] == 2):
            ops.append((sc(f), M))
    ops = [M for _, M in sorted(ops, key=lambda p: p[0])]
    for M in ops:
        if all(len(b) < 2 for b in blocks):
            break
        perm = perm_of(M, atoms)
        nb = []
        for b in blocks:
            if len(b) < 2:
                nb.append(b)
                continue
            DV = [act_disp(M, perm, V[k]) for k in b]
            A = [[(dot3n(V[k], DV[j]) + dot3n(V[l], DV[i])) / 2 for j, l in enumerate(b)] for i, k in enumerate(b)]
            w, E = jacobi(A)
            nv = []
            for c in range(len(b)):
                v = [0.0] * len(V[0])
                for i, k in enumerate(b):
                    e, Vk = E[i][c], V[k]
                    for t in range(len(v)):
                        v[t] += e * Vk[t]
                nv.append(v)
            ordr = sorted(range(len(w)), key=lambda x: -w[x])
            for i, c in enumerate(ordr):
                V[b[i]] = nv[c]
            cur = [b[0]]
            for i in range(1, len(ordr)):
                if abs(w[ordr[i]] - w[ordr[i - 1]]) < 1e-6:
                    cur.append(b[i])
                else:
                    nb.append(cur)
                    cur = [b[i]]
            nb.append(cur)
        blocks = nb
    return [{"w": st[k]["w"], "q": q, "u": _u(q, atoms)} for k, q in enumerate(V)]


def vib_lin_label(st, atoms, d_inf_h: bool) -> dict:
    """Species of a mode set of a linear molecule (v1.0 vibLinLabel)."""
    def chi_of(M):
        perm = perm_of(M, atoms)
        s = 0.0
        for md in st:
            s += dot3n(md["q"], act_disp(M, perm, md["q"]))
        return s

    if len(st) == 1:
        lab = "Σ<sup>" + ("+" if chi_of(refl([0, 1, 0])) > 0 else "−") + "</sup>"
    else:
        x = chi_of(rot(ZZ, PI / 6)) / 2
        m = int(js_round(acos(max(-1.0, min(1.0, x))) / (PI / 6)))
        lab = ["Σ", "Π", "Δ", "Φ"][m] if 0 <= m < 4 else "?"
    if d_inf_h:
        g = "g" if chi_of(INV) > 0 else "u"
        if lab[:1] in "ΣΠΔΦ" and lab[:1]:
            lab = lab[0] + "<sub>" + g + "</sub>" + lab[1:]
    base = "".join(_strip_tags(lab))
    if d_inf_h:
        ir = base in ("Σu+", "Πu")
        ra = base in ("Σg+", "Πg", "Δg")
    else:
        ir = base in ("Σ+", "Π")
        ra = base in ("Σ+", "Π", "Δ")
    return {"lab": lab, "ir": ir, "ra": ra}


def _strip_tags(s: str):
    out, inside = [], False
    for ch in s:
        if ch == "<":
            inside = True
        elif ch == ">":
            inside = False
        elif not inside:
            out.append(ch)
    return out
