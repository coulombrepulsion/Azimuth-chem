"""Normal vibrations of small molecules: valence force field, mass-weighted Hessian, symmetry
species of the modes, IR/Raman activity, reduction of Gamma_3N.

HEADER
    Model of the page "Нормальные колебания" (v1.0 vibrations.js: MASS,
    MOLS, angleList, energy, jacobi, permOf, charOn, fullGroup, applyOp,
    gram, solve, act, gamma, newQ). Wilkinson convention, sections 1-8.
    Coordinates in angstrom, masses in u, force constants in mdyn/A
    (stretch), mdyn A/rad^2 (bend), mdyn/A (out of plane).

§1 THEORY
    Harmonic valence force field V = sum k_r (r - r0)^2 / 2 + sum k_theta
    (theta - theta0)^2 / 2 + sum k_h (h - h0)^2 / 2 (h: height of the
    central atom over the plane of its three neighbours). Cartesian
    Hessian F by central differences (step 1e-4 A); mass-weighted
    F_ij / sqrt(m_i m_j) diagonalised (cyclic Jacobi); the 6 (linear: 5)
    lowest eigenvalues are translations/rotations. Wavenumber
    nu = 1302.79 sqrt(lambda) cm^-1 for lambda in mdyn/(A u)
    (1302.79 = sqrt(1e5 N/m / u) / (2 pi c)). The symmetry species of a
    degenerate set of modes follows from its characters chi(R) = sum q.R q
    and the reduction formula n_Gamma = (1/h) sum_classes n_c chi(R)
    chi_Gamma(R); sets of several species are split by the projection
    operators (d/h) sum_g chi_Gamma(g) R(g) and Gram-Schmidt. Linear
    molecules are treated in D2h (C2v) and labelled by C_inf rotation
    characters: Sigma (non-degenerate), Pi (chi(C_phi) = 2 cos phi), Delta;
    g/u from inversion, +/- from sigma_v. IR active: the species contains
    x, y or z; Raman active: it contains a quadratic function.
    Gamma_3N = N_R chi(R) with N_R the unshifted atoms and chi(R) = tr R;
    Gamma_trans = tr R, Gamma_rot = det(R) tr R (linear: the species of
    R_x, R_y only); Gamma_vib = Gamma_3N - Gamma_trans - Gamma_rot.
    Experimental fundamentals (cm^-1, in the order of decreasing calculated
    frequency within a species) are data of v1.0 (Herzberg / NIST WebBook
    vibrational tables; see REPRODUCIBILITY).

§2 ALGORITHM
    As v1.0, step by step (same loops, same sort orders: V8's stable sort
    equals Python's sorted with a key).

§3 APPLICATIONS
    Endpoints vib.list, vib.mol.

§4 SPECIFICATION
    mol(m) -> {M, G, modes: [{lab, deg, lam, wn, nu, vc, irr, chi, act:
      {ir, ra}, irrep}], gam: {un, pa, g3, gt, gr, gv, grl?, gvl?, nred,
      nv}, ans: [n_vib, n_sets, n_IR, n_Raman]}.
    Tier: bitwise vs v1.0 on Linux/glibc (EXACT).

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    permOf may return -1 (no image of an atom): v1.0 then writes to the
    array property "-3".."-1" (no effect) -- here the atom is skipped; the
    class index -1 of fullGroup is skipped likewise.
§7 TEST CASES (tests/test_vibrations.py)
    Number of modes 3N-6 / 3N-5; species against the textbook reductions
    (H2O 2A1 + B2, NH3 2A1 + 2E, CH4 A1 + E + 2T2, SF6 A1g + Eg + 2T1u +
    T2g + T2u, CO2 Sigma_g+ + Sigma_u+ + Pi_u); Gamma_vib reduction equals
    the classification of the computed modes; modes orthonormal (mass-
    weighted, 1e-10); the six zero eigenvalues are ~0; mutual exclusion
    for centrosymmetric molecules; diatomic-like check: the stretching
    frequency of a single bond k, mu: 1302.79 sqrt(k/mu); vs v1.0.
§8 ERROR ANALYSIS
    Central differences: truncation O(h^2) ~ 1e-8, rounding u/h^2 ~ 1e-8
    relative; eigenvalues to ~1e-7, wavenumbers to ~1e-4 cm^-1 (printed
    as integers: the experimental values are shown, the calculated ones
    only order and classify). Degeneracy threshold 2e-4 relative.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

from .jsmath import acos, cos, hypot3, js_round, js_sign, sin

CT = json.loads((Path(__file__).parent / "data" / "vibrations_ct.json").read_text(encoding="utf-8"))
for _G in CT.values():          # JS numbers are doubles: keep -0.0 in products such as 0 * (-1)
    for _c in _G["classes"]:
        _c["M"] = [[float(x) for x in r] for r in _c["M"]]
MASS = {"H": 1.008, "B": 11.009, "C": 12.011, "N": 14.007, "O": 15.999, "F": 18.998, "S": 32.06}
MOLS = [
    {"id": "h2o", "name": "H₂O", "grp": "C2v", "lin": False,
     "at": [["O", 0, 0, 0], ["H", 0, 0.757, 0.587], ["H", 0, -0.757, 0.587]], "bonds": [[0, 1, 7.7], [0, 2, 7.7]], "ang": [[1, 0, 2, 0.70]],
     "exp": {"A<sub>1</sub>": [3657, 1595], "B<sub>2</sub>": [3756]}},
    {"id": "h2co", "name": "H₂CO", "grp": "C2v", "lin": False,
     "at": [["C", 0, 0, 0], ["O", 0, 0, 1.205], ["H", 0, 0.945, -0.584], ["H", 0, -0.945, -0.584]], "bonds": [[0, 1, 12.1], [0, 2, 4.4], [0, 3, 4.4]],
     "ang": [[1, 0, 2, 0.75], [1, 0, 3, 0.75], [2, 0, 3, 0.45]], "oop": [[0, 1, 2, 3, 1.6]],
     "exp": {"A<sub>1</sub>": [2783, 1746, 1500], "B<sub>1</sub>": [1167], "B<sub>2</sub>": [2843, 1249]}},
    {"id": "nh3", "name": "NH₃", "grp": "C3v", "lin": False,
     "at": [["N", 0, 0, 0], ["H", 0.9375, 0, -0.381], ["H", -0.46875, 0.81190, -0.381], ["H", -0.46875, -0.81190, -0.381]],
     "bonds": [[0, 1, 6.4], [0, 2, 6.4], [0, 3, 6.4]], "ang": [[1, 0, 2, 0.55], [1, 0, 3, 0.55], [2, 0, 3, 0.55]],
     "exp": {"A<sub>1</sub>": [3337, 950], "E": [3444, 1627]}},
    {"id": "bf3", "name": "BF₃", "grp": "D3h", "lin": False,
     "at": [["B", 0, 0, 0], ["F", 1.307, 0, 0], ["F", -0.6535, 1.13190, 0], ["F", -0.6535, -1.13190, 0]],
     "bonds": [[0, 1, 7.3], [0, 2, 7.3], [0, 3, 7.3]], "ang": [[1, 0, 2, 0.55], [1, 0, 3, 0.55], [2, 0, 3, 0.55]], "oop": [[0, 1, 2, 3, 0.55]],
     "exp": {"A<sub>1</sub>′": [888], "A<sub>2</sub>″": [691], "E′": [1454, 480]}},
    {"id": "ch4", "name": "CH₄", "grp": "Td", "lin": False,
     "at": [["C", 0, 0, 0], ["H", 0.6276, 0.6276, 0.6276], ["H", 0.6276, -0.6276, -0.6276], ["H", -0.6276, 0.6276, -0.6276], ["H", -0.6276, -0.6276, 0.6276]],
     "bonds": [[0, 1, 5.0], [0, 2, 5.0], [0, 3, 5.0], [0, 4, 5.0]],
     "ang": [[1, 0, 2, 0.46], [1, 0, 3, 0.46], [1, 0, 4, 0.46], [2, 0, 3, 0.46], [2, 0, 4, 0.46], [3, 0, 4, 0.46]],
     "exp": {"A<sub>1</sub>": [2917], "E": [1534], "T<sub>2</sub>": [3019, 1306]}},
    {"id": "sf6", "name": "SF₆", "grp": "Oh", "lin": False,
     "at": [["S", 0, 0, 0], ["F", 1.561, 0, 0], ["F", -1.561, 0, 0], ["F", 0, 1.561, 0], ["F", 0, -1.561, 0], ["F", 0, 0, 1.561], ["F", 0, 0, -1.561]],
     "bonds": [[0, 1, 5.3], [0, 2, 5.3], [0, 3, 5.3], [0, 4, 5.3], [0, 5, 5.3], [0, 6, 5.3]], "ang": "cis90:1.0",
     "exp": {"A<sub>1g</sub>": [775], "E<sub>g</sub>": [643], "T<sub>1u</sub>": [939, 614], "T<sub>2g</sub>": [524], "T<sub>2u</sub>": [347]}},
    {"id": "co2", "name": "CO₂", "grp": "Dinfh", "sub": "D2h", "lin": True,
     "at": [["C", 0, 0, 0], ["O", 0, 0, 1.162], ["O", 0, 0, -1.162]], "bonds": [[0, 1, 15.5], [0, 2, 15.5]], "ang": [[1, 0, 2, 0.57]],
     "exp": {"Σ<sub>g</sub><sup>+</sup>": [1333], "Σ<sub>u</sub><sup>+</sup>": [2349], "Π<sub>u</sub>": [667]}, "num": [1333, 667, 2349]},
    {"id": "hcn", "name": "HCN", "grp": "Cinfv", "sub": "C2v", "lin": True,
     "at": [["C", 0, 0, 0], ["H", 0, 0, -1.065], ["N", 0, 0, 1.153]], "bonds": [[0, 1, 5.8], [0, 2, 17.9]], "ang": [[1, 0, 2, 0.20]],
     "exp": {"Σ<sup>+</sup>": [3311, 2097], "Π": [712]}, "num": [3311, 712, 2097]},
    {"id": "c2h2", "name": "C₂H₂", "grp": "Dinfh", "sub": "D2h", "lin": True,
     "at": [["C", 0, 0, 0.601], ["C", 0, 0, -0.601], ["H", 0, 0, 1.662], ["H", 0, 0, -1.662]], "bonds": [[0, 1, 15.7], [0, 2, 5.9], [1, 3, 5.9]],
     "ang": [[1, 0, 2, 0.12], [0, 1, 3, 0.12]],
     "exp": {"Σ<sub>g</sub><sup>+</sup>": [3374, 1974], "Σ<sub>u</sub><sup>+</sup>": [3289], "Π<sub>g</sub>": [612], "Π<sub>u</sub>": [730]}},
]
LINACT = {"Σ<sup>+</sup>": [1, 1], "Π": [1, 1], "Σ<sub>g</sub><sup>+</sup>": [0, 1], "Σ<sub>u</sub><sup>+</sup>": [1, 0], "Π<sub>u</sub>": [1, 0],
          "Π<sub>g</sub>": [0, 1], "Σ<sub>g</sub><sup>−</sup>": [0, 0], "Σ<sub>u</sub><sup>−</sup>": [0, 0], "Σ<sup>−</sup>": [0, 0]}
_XYZ = re.compile(r"(^|[^R])[xyz]")


def vsub(a, b):
    return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]


def vdot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def vcross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def vlen(a):
    return math.sqrt(vdot(a, a))


def angle_list(M):
    if not isinstance(M["ang"], str):
        return M["ang"]
    k = float(M["ang"].split(":")[1])
    out = []
    for i in range(1, len(M["at"])):
        for j in range(i + 1, len(M["at"])):
            a, b = M["at"][i][1:], M["at"][j][1:]
            c = vdot(a, b) / vlen(a) / vlen(b)
            if abs(c) < 0.5:
                out.append([i, 0, j, k])
    return out


def energy(M, X, X0, angs=None):
    E = 0
    P = lambda i: [X[3 * i], X[3 * i + 1], X[3 * i + 2]]  # noqa: E731
    P0 = lambda i: [X0[3 * i], X0[3 * i + 1], X0[3 * i + 2]]  # noqa: E731
    for i, j, k in M["bonds"]:
        d = vlen(vsub(P(i), P(j))) - vlen(vsub(P0(i), P0(j)))
        E += 0.5 * k * d * d
    for i, c, j, k in (angs if angs is not None else angle_list(M)):
        def th(a):
            u, v = vsub(a(i), a(c)), vsub(a(j), a(c))
            return acos(max(-1, min(1, vdot(u, v) / vlen(u) / vlen(v))))
        d = th(P) - th(P0)
        E += 0.5 * k * d * d
    for c, a, b, d_, k in M.get("oop", []):
        def h(Q):
            n = vcross(vsub(Q(b), Q(a)), vsub(Q(d_), Q(a)))
            return vdot(vsub(Q(c), Q(a)), n) / vlen(n)
        z = h(P) - h(P0)
        E += 0.5 * k * z * z
    return E


def jacobi(A0):
    n = len(A0)
    A = [list(r) for r in A0]
    V = [[1 if i == j else 0 for j in range(n)] for i in range(n)]
    for _sw in range(100):
        off = 0
        for i in range(n):
            for j in range(i + 1, n):
                off += A[i][j] * A[i][j]
        if off < 1e-22:
            break
        for p in range(n):
            for q in range(p + 1, n):
                if abs(A[p][q]) < 1e-14:
                    continue
                th = (A[q][q] - A[p][p]) / (2 * A[p][q])
                t = (1 if th == 0 or th != th else js_sign(th)) / (abs(th) + math.sqrt(th * th + 1))   # Math.sign(th||1)
                c = 1 / math.sqrt(t * t + 1)
                s = t * c
                for k in range(n):
                    akp, akq = A[k][p], A[k][q]
                    A[k][p] = c * akp - s * akq
                    A[k][q] = s * akp + c * akq
                for k in range(n):
                    apk, aqk = A[p][k], A[q][k]
                    A[p][k] = c * apk - s * aqk
                    A[q][k] = s * apk + c * aqk
                for k in range(n):
                    vkp, vkq = V[k][p], V[k][q]
                    V[k][p] = c * vkp - s * vkq
                    V[k][q] = s * vkp + c * vkq
    return [A[i][i] for i in range(n)], V


def perm_of(M, R):
    out = []
    for a in M["at"]:
        p = [R[r][0] * a[1] + R[r][1] * a[2] + R[r][2] * a[3] for r in range(3)]
        out.append(next((j for j, b in enumerate(M["at"]) if b[0] == a[0] and hypot3(b[1] - p[0], b[2] - p[1], b[3] - p[2]) < 1e-3), -1))
    return out


def vdot3(a, b):
    s = 0
    for i in range(len(a)):
        s += a[i] * b[i]
    return s


def apply_op(M, R, v, pm=None):
    pm = perm_of(M, R) if pm is None else pm
    w = [0] * len(v)
    for a in range(len(M["at"])):
        b = pm[a]
        if b < 0:
            continue
        for r in range(3):
            w[3 * b + r] = R[r][0] * v[3 * a] + R[r][1] * v[3 * a + 1] + R[r][2] * v[3 * a + 2]
    return w


def char_on(M, R, vecs):
    pm = perm_of(M, R)
    s = 0
    for v in vecs:
        s += vdot3(apply_op(M, R, v, pm), v)
    return s


def mmul(A, B):
    return [[r[0] * B[0][j] + r[1] * B[1][j] + r[2] * B[2][j] for j in range(3)] for r in A]


def meq(A, B):
    return all(abs(A[i][j] - B[i][j]) <= 1e-6 for i in range(3) for j in range(3))


_FULL: dict = {}


def full_group(gk):
    if gk in _FULL:
        return _FULL[gk]
    G = CT[gk]
    L = [c["M"] for c in G["classes"]]
    grew = True
    while grew and len(L) < 200:
        grew = False
        n = len(L)
        for i in range(n):
            for j in range(n):
                P = mmul(L[i], L[j])
                if not any(meq(P, Q) for Q in L):
                    L.append(P)
                    grew = True
    inv = lambda A: [[A[0][0], A[1][0], A[2][0]], [A[0][1], A[1][1], A[2][1]], [A[0][2], A[1][2], A[2][2]]]  # noqa: E731
    cls = [-1] * len(L)
    for k, c in enumerate(G["classes"]):
        for g in L:
            cj = mmul(mmul(g, c["M"]), inv(g))
            q = next((qq for qq, Q in enumerate(L) if meq(Q, cj)), -1)
            if q >= 0:
                cls[q] = k
    _FULL[gk] = [{"M": M, "cls": cls[i]} for i, M in enumerate(L)]
    return _FULL[gk]


def gram(vs, want):
    out = []
    for v in vs:
        w = list(v)
        for u in out:
            d = vdot3(w, u)
            for q in range(len(w)):
                w[q] -= d * u[q]
        n = math.sqrt(vdot3(w, w))
        if n > 1e-6:
            out.append([x / n for x in w])
            if len(out) == want:
                break
    return out


def rot_z(phi):
    c, s = cos(phi), sin(phi)
    return [[c, -s, 0], [s, c, 0], [0, 0, 1]]


def _reduce(G, chi, ir):
    s = 0
    for k, c in enumerate(G["classes"]):
        s = s + c["n"] * chi[k] * ir["chi"][k]
    return s / G["h"]


def solve(M) -> list:
    n = len(M["at"])
    N = 3 * n
    X0 = []
    for a in M["at"]:
        X0 += [a[1], a[2], a[3]]
    h = 1e-4
    angs = angle_list(M)
    H = [[0] * N for _ in range(N)]
    for i in range(N):
        for j in range(i, N):
            def f(di, dj):
                X = list(X0)
                X[i] += di
                X[j] += dj
                return energy(M, X, X0, angs)
            v = (f(h, h) - f(h, -h) - f(-h, h) + f(-h, -h)) / (4 * h * h)
            H[i][j] = H[j][i] = v
    m = []
    for a in M["at"]:
        w = MASS[a[0]]
        m += [w, w, w]
    Hm = [[x / math.sqrt(m[i] * m[j]) for j, x in enumerate(r)] for i, r in enumerate(H)]
    val, vec = jacobi(Hm)
    nz = 5 if M["lin"] else 6
    idx = sorted(range(N), key=lambda i: val[i])[nz:]
    sets: list = []
    for i in sorted(idx, key=lambda i: -val[i]):
        last = sets[-1] if sets else None
        if last and abs(val[i] - val[last[0]]) < 2e-4 * max(0.05, abs(val[i])):
            last.append(i)
        else:
            sets.append([i])
    gk = M["sub"] if M["lin"] else M["grp"]
    G = CT[gk]
    FG = full_group(gk)
    modes = []
    for st in sets:
        vm = [[r[i] for r in vec] for i in st]
        chi = [char_on(M, c["M"], vm) for c in G["classes"]]
        mult = [_reduce(G, chi, ir) for ir in G["irreps"]]
        present = [[js_round(x), k] for k, x in enumerate(mult) if js_round(x) > 0]
        if len(present) == 1 or M["lin"]:
            parts = [vm]
        else:
            parts = []
            for cnt, k in present:
                ir = G["irreps"][k]
                proj = []
                for v in vm:
                    w = [0] * len(v)
                    for g in FG:
                        c = ir["chi"][g["cls"]] if g["cls"] >= 0 else None
                        if not c:
                            continue
                        Dv = apply_op(M, g["M"], v)
                        for q in range(len(w)):
                            w[q] += c * Dv[q]
                    proj.append(w)
                parts.append(gram(proj, cnt * ir["dim"]))
        for pv in parts:
            if not pv:
                continue
            lam = 0
            for i in st:
                lam = lam + val[i]
            lam = lam / len(st)
            c2 = [char_on(M, c["M"], pv) for c in G["classes"]]
            k = next((kk for kk, ir in enumerate(G["irreps"])
                      if abs(_reduce(G, c2, ir) - len(pv) / ir["dim"]) < 1e-3 and len(pv) % ir["dim"] == 0), -1)
            d = len(pv) if M["lin"] else (G["irreps"][k]["dim"] if k >= 0 else len(pv))
            for q in range(0, len(pv), d):
                vv = pv[q:q + d]
                modes.append({"lam": lam, "vm": vv, "deg": len(vv)})
    for md in modes:
        md["wn"] = 1302.79 * math.sqrt(max(0, md["lam"]))
        md["vc"] = [[x / math.sqrt(m[k]) for k, x in enumerate(v)] for v in md["vm"]]
    for md in modes:
        chi = [char_on(M, c["M"], md["vm"]) for c in G["classes"]]
        md["chi"] = chi
        md["irr"] = [k for k, ir in enumerate(G["irreps"]) if js_round(_reduce(G, chi, ir)) > 0]
        if M["lin"]:
            R = rot_z(2 * math.pi / 7)
            cz = char_on(M, R, md["vm"])
            sv = char_on(M, [[1, 0, 0], [0, -1, 0], [0, 0, 1]], md["vm"])
            iv = char_on(M, [[-1, 0, 0], [0, -1, 0], [0, 0, -1]], md["vm"])
            lab = "Σ" if md["deg"] == 1 else ("Π" if abs(cz - 2 * cos(2 * math.pi / 7)) < 1e-3 else "Δ")
            sub = ("g" if iv > 0 else "u") if M["grp"] == "Dinfh" else ""
            md["lab"] = lab + (f"<sub>{sub}</sub>" if sub else "") + (("<sup>+</sup>" if sv > 0 else "<sup>−</sup>") if md["deg"] == 1 else "")
        else:
            md["lab"] = G["irreps"][md["irr"][0]]["lab"] if len(md["irr"]) == 1 else "?"
    modes = sorted(modes, key=lambda md: -md["lam"])
    used: dict = {}
    for md in modes:
        L = M["exp"].get(md["lab"], [])
        k = used.get(md["lab"], 0)
        md["nu"] = L[k] if k < len(L) else None
        used[md["lab"]] = k + 1
    # nu_1, nu_2, ... in the conventional order: symmetry species in the order of the
    # character table (totally symmetric first), by decreasing frequency within a species;
    # the historical order for CO2 and HCN (M["num"])
    ordr = M.get("num") or [v for L in M["exp"].values() for v in L]

    def pos(nu):
        return ordr.index(nu) if nu in ordr else 99
    return sorted(modes, key=lambda md: (pos(md["nu"]), -(md["nu"] or 0)))


def act(M, md) -> dict:
    if M["lin"]:
        a = LINACT.get(md["lab"], [0, 0])
        return {"ir": bool(a[0]), "ra": bool(a[1])}
    ir = CT[M["grp"]]["irreps"][md["irr"][0]]
    return {"ir": bool(_XYZ.search(ir["lin"])), "ra": bool(ir["quad"])}


def gamma(M) -> dict:
    gk = M["sub"] if M["lin"] else M["grp"]
    G = CT[gk]
    n = len(M["at"])
    tr = lambda m: m[0][0] + m[1][1] + m[2][2]  # noqa: E731
    det = lambda m: (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1]) - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])  # noqa: E731
                     + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))
    un = [sum(1 for a, j in enumerate(perm_of(M, c["M"])) if j == a) for c in G["classes"]]
    pa = [tr(c["M"]) for c in G["classes"]]
    g3 = [u * pa[k] for k, u in enumerate(un)]
    gt = pa
    gr = [det(c["M"]) * pa[k] for k, c in enumerate(G["classes"])]
    gv = [x - gt[k] - gr[k] for k, x in enumerate(g3)]
    out = {"gk": gk, "un": un, "pa": pa, "g3": g3, "gt": gt, "gr": gr, "gv": gv}
    if M["lin"]:
        Rx = [ir for ir in G["irreps"] if re.search(r"R[xy]", ir["lin"])]
        grl = []
        for k in range(len(G["classes"])):
            s = 0
            for ir in Rx:
                s = s + ir["chi"][k]
            grl.append(s)
        gvl = [x - gt[k] - grl[k] for k, x in enumerate(g3)]
        out.update(grl=grl, gvl=gvl)
        gv = gvl
    out["nred"] = [js_round(_reduce(G, gv, ir)) for ir in G["irreps"]]
    out["nv"] = 3 * n - 5 if M["lin"] else 3 * n - 6
    return out


_CACHE: dict = {}


def mol(i: int) -> dict:
    if i in _CACHE:
        return _CACHE[i]
    M = MOLS[i]
    modes = solve(M)
    out_modes = []
    for md in modes:
        a = act(M, md)
        ir = None if M["lin"] else {k: CT[M["grp"]]["irreps"][md["irr"][0]][k] for k in ("lab", "lin", "quad")}
        out_modes.append({"lab": md["lab"], "deg": md["deg"], "lam": md["lam"], "wn": md["wn"], "nu": md["nu"], "vc": md["vc"],
                          "irr": md["irr"], "chi": md["chi"], "act": a, "irrep": ir})
    gam = gamma(M)
    G = CT[gam["gk"]]
    meta = {k: M[k] for k in ("id", "name", "grp", "lin", "at", "bonds")}
    meta["sub"] = M.get("sub")
    ans = [gam["nv"], len(modes), sum(1 for m in out_modes if m["act"]["ir"]), sum(1 for m in out_modes if m["act"]["ra"])]
    _CACHE[i] = {"M": meta, "G": {"h": G["h"], "classes": [{"n": c["n"], "tex": c["tex"]} for c in G["classes"]], "irreps": G["irreps"]},
                 "modes": out_modes, "gam": gam, "ans": ans}
    return _CACHE[i]


def mol_list() -> list:
    return [{"id": M["id"], "name": M["name"], "grp": M["grp"], "lin": M["lin"]} for M in MOLS]
