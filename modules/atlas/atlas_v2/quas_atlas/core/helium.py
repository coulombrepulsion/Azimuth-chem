"""Two-electron atoms: independent-particle, perturbation, effective-charge and Hylleraas
variational energies; the Coulomb hole.

HEADER
    Model of the page "Атом гелия и электронная корреляция" (v1.0
    helium.js: I3, mul, integ, dS, dU, dT, mats, jacW, lowest, optZ, psiAt,
    rows, sec2, sec3).  Atomic units.  Wilkinson convention, sections 1-8.

§1 THEORY
    H = -1/2 (nabla_1^2 + nabla_2^2) - Z/r1 - Z/r2 + 1/r12 (infinite nuclear
    mass).  Hylleraas coordinates s = r1 + r2, t = r1 - r2, u = r12; trial
    functions psi = e^{-zeta s} sum_k c_k s^a u^b t^c (1S, t even).  With
    the volume element proportional to u (s^2 - t^2) ds du dt, 0 <= u <= s,
    0 <= t <= u, every matrix element reduces to
        I(a, b, c, z) = (a+b+c+2)! / ((c+1)(b+c+2)(2 zeta)^(a+b+c+3)),
    the kinetic energy to products of first derivatives (d/ds, d/du, d/dt
    with the cross terms s(u^2 - t^2) and t(s^2 - u^2)) and the potential to
    the polynomial 4Z s - s^2 + t^2 (Hylleraas 1929; Bethe and Salpeter,
    Quantum Mechanics of One- and Two-Electron Atoms, §32).  The
    generalised eigenproblem is solved by canonical orthogonalisation; zeta
    is optimised by golden-section search (80 steps on [0.3 Z, 4 Z]).
    Simple models: E = -Z^2 (no repulsion), first-order perturbation
    -Z^2 + 5Z/8, effective charge -(Z - 5/16)^2 with
    E(zeta) = zeta^2 - 2 Z zeta + 5 zeta / 8.  Reference: Hartree-Fock limits
    and exact non-relativistic energies of H-, He, Li+, Be2+ (tabulated,
    e.g. Clementi & Roetti 1974; Pekeris 1959; Drake 1988).
    Coulomb hole: conditional density of electron 2 on the axis through the
    nucleus and electron 1, with the 6-term Hylleraas function, normalised
    by a 140 x 48 (r, cos) quadrature; compared with the uncorrelated
    Hartree-Fock density |phi_HF|^2 (2.10.0; v1.0: the 1-term optimum
    zeta^3/pi e^{-2 zeta |z|}, HOLE_REF = "1term").  <r12> and <1/r12>
    without correlation are those of the HF product.

§2 ALGORITHM
    As v1.0 (polynomials as lists [coef, a, b, c]; Jacobi with up to 200
    sweeps; golden section with g = 0.618034).

§3 APPLICATIONS
    Endpoints he.table, he.zeta, he.hole.

§4 SPECIFICATION
    hylleraas(Z) -> {1|2|3|6: {z, E, c}} (memoised); table(Z), zeta_view(Z,
    zeta), hole(Z, r1) -> the values the page prints and draws.
    Tier: bitwise vs v1.0 on Linux/glibc ((2 zeta)^n via the platform pow,
    as V8).

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    The factorial table is built in doubles (FACT[i] = FACT[i-1] * i) as in
    v1.0, so values above 2^53 are rounded identically.
§7 TEST CASES (tests/test_helium.py)
    1-term Hylleraas = effective-charge result -(Z - 5/16)^2 at zeta = Z -
    5/16 (to 1e-12); 6-term He energy within 1e-3 of -2.903724 and above it
    (variational); H- bound with 2 terms (E < -0.5); E(zeta) minimum at Z -
    5/16; virial ratio V/T = -2 at the optimum; vs v1.0.
§8 ERROR ANALYSIS
    The overlap matrices are well conditioned for these small bases
    (cond < 1e6); Jacobi eigenvalues ~u ||H||; the golden section stops at
    a bracket of 0.618^80 * 3.7 Z (below u), so zeta is converged to the
    flatness of E(zeta) (|dE| < u |E|).
"""
from __future__ import annotations

import functools
import math

from .jsmath import exp, js_pow, js_sign, sq

FACT = [1.0]
for _i in range(1, 60):
    FACT.append(FACT[-1] * _i)


def I3(a, b, c, z):
    return FACT[a + b + c + 2] / ((c + 1) * (b + c + 2) * js_pow(2 * z, a + b + c + 3))


def mul(P, Q):
    return [[p[0] * q[0], p[1] + q[1], p[2] + q[2], p[3] + q[3]] for p in P for q in Q]


def integ(P, z):
    s = 0
    for k, a, b, c in P:
        s = s + (k * I3(a, b, c, z) if (k and a >= 0 and b >= 0 and c >= 0) else 0)
    return s


def dS(P, z):
    R = []
    for k, a, b, c in P:
        if a > 0:
            R.append([k * a, a - 1, b, c])
        R.append([-z * k, a, b, c])
    return R


def dU(P):
    return [[k * b, a, b - 1, c] for k, a, b, c in P if b > 0]


def dT(P):
    return [[k * c, a, b, c - 1] for k, a, b, c in P if c > 0]


W = [[1, 2, 1, 0], [-1, 0, 1, 2]]


def mats(basis, z, Z):
    n = len(basis)
    ph = [[[1, a, b, c]] for a, b, c in basis]
    ds = [dS(p, z) for p in ph]
    du = [dU(p) for p in ph]
    dt = [dT(p) for p in ph]
    A1 = [[1, 1, 2, 0], [-1, 1, 0, 2]]
    A2 = [[1, 2, 0, 1], [-1, 0, 2, 1]]
    L = [[4 * Z, 1, 1, 0], [-1, 2, 0, 0], [1, 0, 0, 2]]
    S, H = [], []
    for i in range(n):
        S.append([])
        H.append([])
        for j in range(n):
            N = integ(mul(W, mul(ph[i], ph[j])), z)
            M = integ(mul(W, mul(ds[i], ds[j]) + mul(dt[i], dt[j]) + mul(du[i], du[j])), z)
            M += integ(mul(du[i], mul(A1, ds[j]) + mul(A2, dt[j])), z) + integ(mul(du[j], mul(A1, ds[i]) + mul(A2, dt[i])), z)
            Lv = integ(mul(L, mul(ph[i], ph[j])), z)
            S[i].append(N)
            H[i].append(M - Lv)
    return S, H


def jacW(A0):
    n = len(A0)
    A = [list(r) for r in A0]
    V = [[1 if i == j else 0 for j in range(n)] for i in range(n)]
    for _sw in range(200):
        off = 0.0
        for i in range(n):
            for j in range(i + 1, n):
                off += sq(A[i][j])
        if off < 1e-26:
            break
        for p in range(n):
            for q in range(p + 1, n):
                if abs(A[p][q]) < 1e-18:
                    continue
                th = (A[q][q] - A[p][p]) / (2 * A[p][q])
                t = js_sign(th or 1) / (abs(th) + math.sqrt(th * th + 1))
                c = 1 / math.sqrt(t * t + 1)
                s = t * c
                for row in A:
                    x, y = row[p], row[q]
                    row[p] = c * x - s * y
                    row[q] = s * x + c * y
                Ap, Aq = A[p], A[q]
                A[p] = [c * x - s * y for x, y in zip(Ap, Aq)]
                A[q] = [s * x + c * y for x, y in zip(Ap, Aq)]
                for row in V:
                    x, y = row[p], row[q]
                    row[p] = c * x - s * y
                    row[q] = s * x + c * y
    return [A[i][i] for i in range(n)], V


def lowest(basis, z, Z):
    S, H = mats(basis, z, Z)
    n = len(basis)
    w, V = jacW(S)
    if min(w) < 1e-12 * max(w):
        return None
    X = [[x / math.sqrt(w[j]) for j, x in enumerate(r)] for r in V]
    Hp = []
    for i in range(n):
        row = []
        for j in range(n):
            s = 0.0
            for k in range(n):
                for l in range(n):
                    s += X[k][i] * H[k][l] * X[l][j]
            row.append(s)
        Hp.append(row)
    e, C = jacW(Hp)
    m = 0
    for i, x in enumerate(e):
        if x < e[m]:
            m = i
    c = []
    for r in X:
        s = 0
        for k, x in enumerate(r):
            s = s + x * C[k][m]
        c.append(s)
    s0 = js_sign(c[0]) or 1
    return {"E": e[m], "c": [x * s0 for x in c]}


def opt_z(basis, Z, lo=0.3, hi=4):
    a, b = lo * Z, hi * Z
    g = 0.618034

    def f(z):
        r = lowest(basis, z, Z)
        return r["E"] if r else 1e9
    x1, x2 = b - g * (b - a), a + g * (b - a)
    f1, f2 = f(x1), f(x2)
    for _k in range(80):
        if f1 < f2:
            b, x2, f2 = x2, x1, f1
            x1 = b - g * (b - a)
            f1 = f(x1)
        else:
            a, x1, f1 = x1, x2, f2
            x2 = a + g * (b - a)
            f2 = f(x2)
    z = (a + b) / 2
    return {"z": z, **lowest(basis, z, Z)}


BASES = {1: [[0, 0, 0]], 2: [[0, 0, 0], [0, 1, 0]], 3: [[0, 0, 0], [0, 1, 0], [0, 0, 2]],
         6: [[0, 0, 0], [0, 1, 0], [0, 0, 2], [1, 0, 0], [2, 0, 0], [0, 2, 0]]}
SYS = {1: {"hf": -0.487930, "ex": -0.527751, "thr": -0.5}, 2: {"hf": -2.861680, "ex": -2.903724, "thr": -2},
       3: {"hf": -7.236415, "ex": -7.279913, "thr": -4.5}, 4: {"hf": -13.611299, "ex": -13.655566, "thr": -8}}
KJ = 2625.5


@functools.lru_cache(maxsize=8)
def hylleraas(Z: int) -> dict:
    return {k: opt_z(BASES[k], Z) for k in (1, 2, 3, 6)}


def psi_at(basis, res, r1, r2, r12):
    s, t, u = r1 + r2, r1 - r2, r12
    acc = 0
    for k, (a, b, c) in enumerate(basis):
        acc = acc + res["c"][k] * js_pow(s, a) * js_pow(u, b) * js_pow(t, c)
    return exp(-res["z"] * s) * acc


def table(Z: int) -> dict:
    s, h = SYS[Z], hylleraas(Z)
    E = [-Z * Z, -Z * Z + 5 * Z / 8, -(sq(Z - 5 / 16)), s["hf"], h[2]["E"], h[3]["E"], h[6]["E"], s["ex"]]
    rows = []
    for i, e in enumerate(E):
        err = e - s["ex"]
        rows.append({"E": e, "err": err, "errk": err * KJ, "aerr": abs(err), "part": (s["hf"] - e) / (s["hf"] - s["ex"]) if i >= 4 else None,
                     "unbound": e > s["thr"] and i > 0})
    ec = s["ex"] - s["hf"]
    return {"rows": rows, "ec": ec, "eck": ec * KJ, "ecp": abs(ec / s["ex"]) * 100, "thr": s["thr"], "aec": -ec}


def zeta_view(Z: int, zeta: float) -> dict:
    def T(x):
        return x * x

    def Vn(x):
        return -2 * Z * x

    def Ve(x):
        return 5 * x / 8

    def E(x):
        return T(x) + Vn(x) + Ve(x)
    x1 = max(4.5, Z + 1)
    xs = [(x1 - 0) * i / 299 for i in range(300)]
    zm = Z - 5 / 16
    return {"x1": x1, "xs": xs, "T": [T(x) for x in xs], "Vn": [Vn(x) for x in xs], "Ve": [Ve(x) for x in xs],
            "E": [E(x) for x in xs], "zm": zm, "Ezm": E(zm), "Ez": E(zeta), "Tz": T(zeta), "Vnz": Vn(zeta),
            "Vez": Ve(zeta), "ratio": (Vn(zeta) + Ve(zeta)) / T(zeta), "EZ": E(Z), "Eopt": -zm * zm}


RG = [(i + 0.5) / 140 for i in range(140)]
CG = [-1 + (2 * i + 1) / 48 for i in range(48)]


def _r12(basis, rs, power):
    num = den = 0
    for i in range(len(basis)):
        for j in range(len(basis)):
            a1, b1, c1 = basis[i]
            a2, b2, c2 = basis[j]
            k = rs["c"][i] * rs["c"][j]
            for w, a, b, c in ((1, 2, 1, 0), (-1, 0, 1, 2)):
                den += k * w * I3(a + a1 + a2, b + b1 + b2, c + c1 + c2, rs["z"])
                num += k * w * I3(a + a1 + a2, b + b1 + b2 + power, c + c1 + c2, rs["z"])
    return num / den


# 2.10.0: the Coulomb hole is measured from the Hartree-Fock function (the uncorrelated limit), not
# from the 1-term product: the difference of the two then contains only correlation, no orbital
# relaxation.  HOLE_REF = "1term" reproduces v1.0 / Atlas 0.80.
HOLE_REF = "hf"
HF_REL = tuple(0.18 * 1.6 ** k for k in range(10))   # even-tempered 1s Slater exponents / Z


def _s_ov(a, b):
    return 8 * (a * b) ** 1.5 / (a + b) ** 3


def _j_exp(a, b):
    """Coulomb energy of two normalised densities a^3/(8 pi) e^{-a r} and b^3/(8 pi) e^{-b r}."""
    return a * b * (a * a + 3 * a * b + b * b) / (2 * (a + b) ** 3)


@functools.lru_cache(maxsize=8)
def hf_orbital(Z: int) -> dict:
    """Closed-shell Roothaan-Hartree-Fock 1s^2 in 10 even-tempered 1s Slater functions (exponents
    Z * 0.18 * 1.6^k): within 2e-5 Eh of the HF limits of SYS (He: 1e-7). {E, J, z, c}."""
    z = [Z * r for r in HF_REL]
    n = len(z)
    S = [[_s_ov(z[i], z[j]) for j in range(n)] for i in range(n)]
    h = [[0.5 * z[i] * z[j] * S[i][j] - Z * 4 * (z[i] * z[j]) ** 1.5 / (z[i] + z[j]) ** 2 for j in range(n)] for i in range(n)]
    G = [[[[S[i][j] * S[k][l] * _j_exp(z[i] + z[j], z[k] + z[l]) for l in range(n)] for k in range(n)]
          for j in range(n)] for i in range(n)]
    w, V = jacW(S)
    keep = [k for k in range(n) if w[k] > 1e-10 * max(w)]
    X = [[V[i][k] / math.sqrt(w[k]) for k in keep] for i in range(n)]
    m_ = len(keep)
    P = [[0.0] * n for _ in range(n)]
    E = En = jj = 0.0
    c = [0.0] * n
    for it in range(400):
        F = [[h[i][j] + sum(P[k][l] * G[i][j][k][l] for k in range(n) for l in range(n)) for j in range(n)] for i in range(n)]
        Fp = [[sum(X[k][a] * F[k][l] * X[l][b] for k in range(n) for l in range(n)) for b in range(m_)] for a in range(m_)]
        e, C = jacW(Fp)
        m = min(range(m_), key=lambda q: e[q])
        c = [sum(X[i][k] * C[k][m] for k in range(m_)) for i in range(n)]
        if c[n // 2] < 0:
            c = [-x for x in c]
        hh = sum(c[i] * c[j] * h[i][j] for i in range(n) for j in range(n))
        jj = sum(c[i] * c[j] * c[k] * c[l] * G[i][j][k][l] for i in range(n) for j in range(n) for k in range(n) for l in range(n))
        En = 2 * hh + jj
        Pn = [[c[i] * c[j] for j in range(n)] for i in range(n)]
        P = Pn if it == 0 else [[0.5 * P[i][j] + 0.5 * Pn[i][j] for j in range(n)] for i in range(n)]   # damping
        if it > 3 and abs(En - E) < 1e-13:
            break
        E = En
    return {"E": En, "J": jj, "z": z, "c": c}


def _hf_phi2(orb, r):
    """|phi_HF(r)|^2 (one electron, normalised)."""
    v = sum(c * math.sqrt(z ** 3 / math.pi) * math.exp(-z * r) for c, z in zip(orb["c"], orb["z"]))
    return v * v


_GL = None


def _gauss_legendre(n=96):
    global _GL
    if _GL is None:
        xs, ws = [], []
        for i in range(1, n + 1):
            x = math.cos(math.pi * (i - 0.25) / (n + 0.5))
            for _ in range(100):
                p0, p1 = 1.0, x
                for k in range(2, n + 1):
                    p0, p1 = p1, ((2 * k - 1) * x * p1 - (k - 1) * p0) / k
                dp = n * (x * p1 - p0) / (x * x - 1)
                dx = p1 / dp
                x -= dx
                if abs(dx) < 1e-15:
                    break
            xs.append(x)
            ws.append(2 / ((1 - x * x) * dp * dp))
        _GL = (xs, ws)
    return _GL


def _mean_r12_exp(a, b):
    """<r12> between normalised densities a^3/(8 pi) e^{-a r} and b^3/(8 pi) e^{-b r}: the angular
    average r> + r<^2 / (3 r>), inner radial integral analytic, outer by Gauss-Legendre on r = t/(1-t)."""
    def U(nn, x):        # int_x^inf r^n e^{-b r} dr
        t, term = 0.0, 1.0
        for k in range(nn + 1):
            if k:
                term *= b * x / k
            t += term
        return math.factorial(nn) / b ** (nn + 1) * math.exp(-b * x) * t

    def L(nn, x):
        return math.factorial(nn) / b ** (nn + 1) - U(nn, x)
    xs, ws = _gauss_legendre()
    acc = 0.0
    for x, w in zip(xs, ws):
        t = (x + 1) / 2
        r = t / (1 - t)
        jac = 0.5 / (1 - t) ** 2
        inner = b ** 3 / 2 * (r * L(2, r) + L(4, r) / (3 * r) + U(3, r) + r * r * U(1, r) / 3)
        acc += w * jac * a ** 3 / 2 * r * r * math.exp(-a * r) * inner
    return acc


@functools.lru_cache(maxsize=8)
def hf_mean_r12(Z: int) -> float:
    orb = hf_orbital(Z)
    z, c = orb["z"], orb["c"]
    n = len(z)
    pair = [(c[i] * c[j] * _s_ov(z[i], z[j]), z[i] + z[j]) for i in range(n) for j in range(n)]
    cache = {}
    tot = 0.0
    for w1, a in pair:
        for w2, b in pair:
            key = (a, b)
            if key not in cache:
                cache[key] = _mean_r12_exp(a, b)
            tot += w1 * w2 * cache[key]
    return tot


def hole(Z: int, r1: float) -> dict:
    h = hylleraas(Z)
    res, b6, z1 = h[6], BASES[6], h[1]["z"]
    rmax = 9 / res["z"]
    dr = rmax / len(RG)
    norm = same = 0
    for q in RG:
        r = q * rmax
        for c in CG:
            r12 = math.sqrt(max(0, r1 * r1 + r * r - 2 * r1 * r * c))
            p = sq(psi_at(b6, res, r1, r, r12)) * 2 * math.pi * r * r * dr * (2 / len(CG))
            norm += p
            if c > 0:
                same += p

    def cond(z):
        r, r12 = abs(z), abs(z - r1)
        return sq(psi_at(b6, res, r1, r, r12)) / norm

    if HOLE_REF == "hf":
        orb = hf_orbital(Z)

        def unc(z):
            return _hf_phi2(orb, abs(z))
    else:
        def unc(z):
            return js_pow(z1, 3) / math.pi * exp(-2 * z1 * abs(z))
    zr = min(4, 6 / res["z"] + 0.5)
    zs = [-zr + 2 * zr * i / 499 for i in range(500)]
    cv, uv = [cond(z) for z in zs], [unc(z) for z in zs]
    return {"zr": zr, "zs": zs, "cond": cv, "unc": uv, "dv": [a - b for a, b in zip(cv, uv)],
            "ru": hf_mean_r12(Z) if HOLE_REF == "hf" else _r12(BASES[1], h[1], 1), "rc": _r12(b6, res, 1),
            "iu": hf_orbital(Z)["J"] if HOLE_REF == "hf" else _r12(BASES[1], h[1], -1), "ic": _r12(b6, res, -1),
            "same": same / norm * 100}
