"""Ligand-field splitting of d orbitals by the angular overlap model (AOM): levels, ground-state
filling with pairing energy, high/low spin crossover, Jahn-Teller curve, octahedral quiz.

HEADER
    Model of the page "Кристаллическое поле и поле лигандов" (v1.0
    crystal-field.js: DORB, GEO, LIG, aomMatrix, jac, levels, fill, OHC,
    cfgE, jtPlot, CX, ohCfg).  Wilkinson convention, sections 1-8.
    Energies in cm^-1.

§1 THEORY
    Real d orbitals as quadratic forms d(r) = r^T Q r (normalised so that
    the sigma overlap with a ligand on the z axis is 1 for d_z2).  For a
    ligand in direction n: sigma factor F_sigma(d) = n^T Q n, pi factor
    F_pi(d) = (2/sqrt3) (Q n - F_sigma n) (vector).  AOM matrix
    V_ij = sum_L f_L (e_sigma F_sigma,i F_sigma,j + e_pi F_pi,i . F_pi,j)
    (Schaeffer and Joergensen 1965), minus the d-s mixing term e_ds S_i S_j,
    S_i = sum_L f_L F_sigma,i, e_ds = 0.25 e_sigma (2.7.0; zero in O_h, T_d).  Octahedron: Delta_o = 3 e_sigma -
    4 e_pi; tetrahedron Delta_t = 4/9 Delta_o.  Tetragonal distortion: the
    axial ligands weighted by t (octahedron), in the Jahn-Teller curve the
    axial by 1 - 2 delta and the equatorial by 1 + delta (mean field
    constant), plus an elastic energy 15 e_sigma delta^2.  Levels relative
    to the barycentre; ground state by enumerating occupations 0/1/2 of
    the five levels minimising sum n_k E_k + P n_pairs (ties: more unpaired
    electrons).  Spin-only moment mu = sqrt(n(n+2)) mu_B; LFSE in kJ/mol =
    cm^-1 x 0.0119627.  Ligand parameters e_sigma, e_pi are illustrative
    values of v1.0.

§2 ALGORITHM
    As v1.0 (Jacobi with 50 sweeps and thresholds 1e-14; stable sort by
    (E, orbital index); depth-first enumeration in the order 0, 1, 2).

§3 APPLICATIONS
    Endpoints cf.state, cf.cx.

§4 SPECIFICATION
    state(geo, t, lig, nd, P) -> {L, lv: [{E, orb}], groups, f: {occ, E,
      tot, pairs, unp}, Do, mu, lfseKJ, lfseDo, Dt, DtRatio, t2gN, egN, hs,
      jt}.  Tier: bitwise vs v1.0 on Linux/glibc (EXACT).

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    Integer coordinates are converted to doubles (signed zeros as in JS).
§7 TEST CASES (tests/test_crystal_field.py)
    Octahedron: Delta_o = 3 e_sigma - 4 e_pi exactly (1e-9), e_g at
    +0.6 Delta_o and t_2g at -0.4 Delta_o; tetrahedron: Delta_t / Delta_o =
    4/9 for e_pi = 0; barycentre zero; d8 square planar diamagnetic; spin
    crossover exactly at Delta_o = P for d6; Jahn-Teller: d9 minimum off
    centre, d3 at delta = 0; ohCfg: LFSE of d6 low spin = -2.4 and d5 high
    spin = 0; vs v1.0.
§8 ERROR ANALYSIS
    Jacobi converged to off-diagonal norm 1e-7 (threshold 1e-14 on the
    sum of squares) for matrix entries ~1e4 cm^-1: eigenvalues to ~1e-10
    relative; degeneracy grouping uses a 1 cm^-1 window.
"""
from __future__ import annotations

import math

from .jsmath import js_round, js_sign

r3 = math.sqrt(3) / 2
s3 = 1 / math.sqrt(3)
c120, s120 = -0.5, math.sqrt(3) / 2
DORB = [
    ("z2", [[-.5, 0, 0], [0, -.5, 0], [0, 0, 1]]),
    ("x2y2", [[r3, 0, 0], [0, -r3, 0], [0, 0, 0]]),
    ("xy", [[0, r3, 0], [r3, 0, 0], [0, 0, 0]]),
    ("xz", [[0, 0, r3], [0, 0, 0], [r3, 0, 0]]),
    ("yz", [[0, 0, 0], [0, 0, r3], [0, r3, 0]]),
]
DORB = [(i, [[float(x) for x in r] for r in Q]) for i, Q in DORB]


def _f(L):
    return [float(L[0]), float(L[1]), float(L[2])] + L[3:]


GEO = {
    "oct": [[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1, "ax"], [0, 0, -1, "ax"]],
    "tet": [[s3, s3, s3], [s3, -s3, -s3], [-s3, s3, -s3], [-s3, -s3, s3]],
    "sq": [[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0]],
    "spy": [[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1]],
    "tbp": [[0, 0, 1], [0, 0, -1], [1, 0, 0], [c120, s120, 0], [c120, -s120, 0]],
    "lin": [[0, 0, 1], [0, 0, -1]],
}
GEO = {k: [_f(L) for L in v] for k, v in GEO.items()}
# ligands: name, e_sigma, e_pi (cm^-1), illustrative values
LIG = [["I⁻", 4300, 900], ["Br⁻", 5000, 1000], ["Cl⁻", 5500, 1000], ["F⁻", 7900, 2000], ["H₂O", 7500, 1400], ["NH₃", 7200, 0],
       ["en", 7500, 0], ["CN⁻", 8500, -800], ["CO", 9000, -1200]]
OHC = {4: [[3, 1], [4, 0]], 5: [[3, 2], [5, 0]], 6: [[4, 2], [6, 0]], 7: [[5, 2], [6, 1]]}
CX = [["[Ti(H₂O)₆]³⁺", 1, 0], ["[Cr(H₂O)₆]³⁺", 3, 0], ["[Mn(H₂O)₆]³⁺", 4, 0], ["[Fe(H₂O)₆]³⁺", 5, 0], ["[Fe(CN)₆]³⁻", 5, 1],
      ["[Fe(H₂O)₆]²⁺", 6, 0], ["[Fe(CN)₆]⁴⁻", 6, 1], ["[Co(NH₃)₆]³⁺", 6, 1], ["[CoF₆]³⁻", 6, 0], ["[Co(H₂O)₆]²⁺", 7, 0],
      ["[Ni(H₂O)₆]²⁺", 8, 0], ["[Cu(H₂O)₆]²⁺", 9, 0], ["[V(H₂O)₆]³⁺", 2, 0], ["[Mn(CN)₆]³⁻", 4, 1]]


def mv(Q, v):
    return [Q[i][0] * v[0] + Q[i][1] * v[1] + Q[i][2] * v[2] for i in range(3)]


DS_RATIO = 0.25   # 2.7.0: d-s mixing parameter e_ds = DS_RATIO * e_sigma (typical 0.2-0.3)


def aom_matrix(g, t, es, ep, te=None, ds=None):
    te = 1 if te is None else te
    ds = DS_RATIO if ds is None else ds      # read at call time (tests can set DS_RATIO = 0)
    M = [[0] * 5 for _ in range(5)]
    S = [0.0] * 5     # sum over ligands of f_L F_sigma,i (couples d to the metal s orbital)
    for L in GEO[g]:
        n = L[:3]
        f = t if (len(L) > 3 and L[3] == "ax" and g == "oct") else (te if g == "oct" else 1)
        if f == 0:
            continue
        sig = []
        for _, Q in DORB:
            q = mv(Q, n)
            sig.append(q[0] * n[0] + q[1] * n[1] + q[2] * n[2])
        pi = []
        for i, (_, Q) in enumerate(DORB):
            q = mv(Q, n)
            pi.append([(x - sig[i] * n[k]) * 2 / math.sqrt(3) for k, x in enumerate(q)])
        for i in range(5):
            for j in range(5):
                M[i][j] += f * (es * sig[i] * sig[j] + ep * (pi[i][0] * pi[j][0] + pi[i][1] * pi[j][1] + pi[i][2] * pi[j][2]))
        for i in range(5):
            S[i] += f * sig[i]
    if ds:
        # 2.7.0: d-s mixing (Smith 1977; Deeth & Gerloch): V_ij -= e_ds S_i S_j.  Zero for O_h and T_d
        # (S = 0); in a square plane it lowers d_z2 by 4 e_ds, which makes d8 planar complexes with
        # strong ligands diamagnetic (as observed).  ds = 0 reproduces v1.0 / Atlas 0.80 exactly.
        eds = ds * es
        for i in range(5):
            for j in range(5):
                M[i][j] -= eds * S[i] * S[j]
    return M


def jac(A0):
    n = len(A0)
    A = [list(r) for r in A0]
    V = [[1 if i == j else 0 for j in range(n)] for i in range(n)]
    for _sw in range(50):
        off = 0
        for i in range(n):
            for j in range(i + 1, n):
                off += A[i][j] * A[i][j]
        if off < 1e-14:
            break
        for p in range(n):
            for q in range(p + 1, n):
                if abs(A[p][q]) < 1e-14:
                    continue
                th = (A[q][q] - A[p][p]) / (2 * A[p][q])
                t = (1 if th == 0 or th != th else js_sign(th)) / (abs(th) + math.sqrt(th * th + 1))
                c = 1 / math.sqrt(t * t + 1)
                s = t * c
                for k in range(n):
                    a, b = A[k][p], A[k][q]
                    A[k][p] = c * a - s * b
                    A[k][q] = s * a + c * b
                for k in range(n):
                    a, b = A[p][k], A[q][k]
                    A[p][k] = c * a - s * b
                    A[q][k] = s * a + c * b
                for k in range(n):
                    a, b = V[k][p], V[k][q]
                    V[k][p] = c * a - s * b
                    V[k][q] = s * a + c * b
    return [A[i][i] for i in range(n)], V


def levels(g, t, es, ep, te=None, ds=None):
    val, vec = jac(aom_matrix(g, t, es, ep, te, ds))
    mean = 0
    for v in val:
        mean = mean + v
    mean = mean / 5
    out = []
    for k, E in enumerate(val):
        b = 0
        for i in range(5):
            if abs(vec[i][k]) > abs(vec[b][k]):
                b = i
        out.append({"E": E - mean, "orb": b})
    return sorted(out, key=lambda o: (o["E"], o["orb"]))


def fill(lv, n, P):
    best = None
    occ = [0] * 5

    def rec(i, left):
        nonlocal best
        if i == 5:
            if left:
                return
            E = 0
            pairs = unp = 0
            for k in range(5):
                E += occ[k] * lv[k]["E"]
                if occ[k] == 2:
                    pairs += 1
                if occ[k] == 1:
                    unp += 1
            tot = E + P * pairs
            if best is None or tot < best["tot"] - 1e-6 or (abs(tot - best["tot"]) < 1e-6 and unp > best["unp"]):
                best = {"occ": list(occ), "E": E, "tot": tot, "pairs": pairs, "unp": unp}
            return
        for o in range(min(2, left) + 1):
            occ[i] = o
            rec(i + 1, left - o)
        occ[i] = 0
    rec(0, n)
    return best


def cfg_e(t, e, D, P):
    pairs = max(0, t - 3) + max(0, e - 2)
    return -0.4 * D * t + 0.6 * D * e + P * pairs


def jt(es, ep, nd, P, ds=None):
    k = 15 * es
    dl = [-0.2 + i * 0.005 for i in range(81)]
    f0 = fill(levels("oct", 1, es, ep, None, ds), nd, P)
    occ0, t0 = f0["occ"], f0["tot"]
    E = [fill(levels("oct", 1 - 2 * d, es, ep, 1 + d, ds), nd, P)["tot"] + k * d * d - t0 for d in dl]
    im = 0
    for i, e in enumerate(E):
        if e < E[im]:
            im = i
    # 2.6.0: the curve is symmetric in delta; mark the elongated minimum (delta > 0), the one observed
    if dl[im] < 0:
        mirror = len(dl) - 1 - im
        if E[mirror] <= E[im] + 1e-9 * max(1.0, abs(E[im])):
            im = mirror
    t2, eg = sum(occ0[:3]), sum(occ0[3:])
    strong = eg in (1, 3)
    weak = not strong and t2 % 3 != 0
    return {"dl": dl, "E": E, "im": im, "t2": t2, "eg": eg, "strong": strong, "weak": weak}


def state(geo, tAx, lig, nd, P, ds=None) -> dict:
    _, es, ep = LIG[lig]
    lv = levels(geo, tAx, es, ep, None, ds)
    f = fill(lv, nd, P)
    oh = levels("oct", 1, es, ep, None, ds)
    Do = oh[4]["E"] - oh[0]["E"]
    groups: list = []
    for i, l in enumerate(lv):
        g = groups[-1] if groups else None
        if g and abs(l["E"] - lv[g[0]]["E"]) < 1:
            g.append(i)
        else:
            groups.append([i])
    hs = None
    if nd in OHC:
        h, lo = OHC[nd]
        Dmax = 40000
        pts = [0, 1500, Dmax, Do]
        hs = {"cfg": [h, lo], "pts": pts, "E": [[cfg_e(c[0], c[1], Dv, P) for Dv in pts] for c in (h, lo)]}
        hs["isLS"] = hs["E"][1][3] < hs["E"][0][3]
    Dt = lv[4]["E"] - lv[0]["E"]
    return {"L": GEO[geo], "lv": lv, "groups": groups, "f": f, "Do": Do, "mu": math.sqrt(f["unp"] * (f["unp"] + 2)),
            "lfseKJ": f["E"] * 0.0119627, "lfseDo": f["E"] / Do, "Dt": Dt, "DtRatio": Dt / Do,
            "t2gN": sum(f["occ"][:3]), "egN": sum(f["occ"][3:]), "hs": hs, "jt": jt(es, ep, nd, P, ds)}


def oh_cfg(n, ls) -> dict:
    if ls:
        t = min(6, n)
        e = n - t
    else:
        a = min(3, n)
        r = n - a
        b = min(2, r)
        r -= b
        c = min(3, r)
        r -= c
        t = a + c
        e = b + r
    unp = (t if t <= 3 else 6 - t) + (e if e <= 2 else 4 - e)
    return {"t": t, "e": e, "unp": unp, "lfse": js_round((-0.4 * t + 0.6 * e) * 10) / 10}


def cx() -> list:
    return [{"name": nm, "n": n, "ls": ls, "c": oh_cfg(n, ls)} for nm, n, ls in CX]
