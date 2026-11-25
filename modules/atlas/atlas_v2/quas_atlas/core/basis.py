"""Basis sets: Gaussian expansions of the Slater 1s function, the hydrogen atom in s-Gaussians,
the one-Gaussian virial example, and the size of standard basis sets for a molecule.

HEADER
    Model of the page "Базисные наборы" (v1.0 basis.js: STONG, gN, hMats,
    Econtr, jac, Evar, nm, optimize, slater, gsum, overlapSTO, Ea,
    atomInfo, parse, draw3).  Wilkinson convention, sections 1-8.  Atomic
    units.

§1 THEORY
    Normalised s-Gaussian g(a; r) = (2a/pi)^(3/4) exp(-a r^2).  For the
    one-electron atom with nuclear charge Z, between normalised Gaussians
    with p = a_i + a_j and N = g-norms product:
      S_ij = N (pi/p)^(3/2),  T_ij = N 3 a_i a_j / p (pi/p)^(3/2),
      V_ij = -N 2 pi Z / p.
    A fixed contraction sum d_i g_i has E = d^T (T+V) d / d^T S d (STO-nG
    coefficients and exponents of Hehre, Stewart and Pople 1969 for zeta =
    1).  With fixed exponents the best coefficients follow from the linear
    variational method H c = E S c, solved by symmetric orthogonalisation
    X = U w^(-1/2) (Jacobi diagonalisation of S, then of X^T H X).  The
    exponents themselves are optimised by Nelder-Mead in ln a.  The exact
    energy is -1/2 E_h (1 E_h = 2625.5 kJ/mol).  The overlap with the Slater
    function sqrt(1/pi) e^-r is int 4 pi r^2 STO g dr / sqrt(int 4 pi r^2
    g^2 dr), midpoint rule h = 0.002 on [0, 30).
    One Gaussian (part 2): T = 3a/2, V = -2 sqrt(2a/pi); minimum at
    a* = 8/(9 pi), E* = -4/(3 pi) with V = -2T (virial theorem).
    Part 3 counts functions and primitives per atom from the shell
    structure of each basis ((primitives)/[contracted]; 6d for the Pople
    sets marked dc), occupied orbitals floor(n_e/2), two-electron integrals
    ~ N^4/8 (8 bytes each), HF time ~ (N/N_STO-3G)^4.

§2 ALGORITHM
    Exactly as v1.0 (cyclic Jacobi with the threshold 1e-24 on the
    off-diagonal sum of squares; Nelder-Mead with reflection 1, expansion
    2, contraction 1/2, shrink 1/2, stop at |F_n - F_0| < 1e-13, restarted
    with steps 0.5, 0.2, 0.05).  The energy-optimised sets n = 1..6 are
    computed once per process (v1.0: at page load).

§3 APPLICATIONS
    Endpoints basis.part1, basis.optimize, basis.part2, basis.part3.

§4 SPECIFICATION
    part1(set in sto/opt/cust, n, cust exponents, scale lin/log) -> {a, d,
      bad, curves, numbers, cmp table}.
    part2(la = log10 a) -> {a, T, V, E, ratio, am, lam, Em, atMin, curves}.
    part3(formula) -> {err, a} | {at, heavy, nH, ne, occ, rows, ...};
      err in empty, syntax, element.
    Tier: bitwise vs v1.0 on Linux/glibc (EXACT).

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    Math.pow -> js_pow, Math.exp/log/log10 -> jsmath; x**2 -> x*x; the
    stable sort of V8 equals Python's sorted with a key.
§7 TEST CASES (tests/test_basis.py)
    One Gaussian: Econtr equals the closed form 3a/2 - 2 sqrt(2a/pi); the
    optimised n = 1 exponent is 8/(9 pi) (1e-6) with E = -4/(3 pi) and
    V = -2T; STO-2G/3G/6G and optimised n = 4 energies against an
    independent fine-grid radial quadrature (1e-7); optimised energies
    decrease with n and stay above -1/2; Evar <= Econtr for the STO-nG
    exponents; a singular custom set gives None; numbers of basis
    functions of H2O for all eleven sets (7, 13, 13, 19, 25, 29, 30, 24,
    41, 58, 115); parser error codes; vs v1.0.
§8 ERROR ANALYSIS
    Analytic integrals; the energies are converged by Nelder-Mead to
    ~1e-13 in the function value (exponents to ~1e-6 relative).  The
    overlap quadrature has error O(h^2) ~ 1e-7.
"""
from __future__ import annotations

import math
import re
import threading

from .jsmath import exp, js_pow, js_sign, log, log10

PI = math.pi
HART = 2625.5
STONG = {
    1: {"a": [0.270950], "d": [1.0]},
    2: {"a": [0.851819, 0.151623], "d": [0.430129, 0.678914]},
    3: {"a": [2.227660, 0.405771, 0.109818], "d": [0.154329, 0.535328, 0.444635]},
    6: {"a": [23.10303, 4.235915, 1.185056, 0.4070539, 0.1580884, 0.06510954],
        "d": [0.009163596, 0.04936149, 0.1685383, 0.3705627, 0.4164915, 0.1303340]},
}


def _div(x: float, y: float) -> float:
    """x / y with IEEE semantics (JS): 0/0 = NaN, x/0 = +-Infinity (all-zero coefficients of a singular custom set)."""
    if y == 0:
        if x == 0 or math.isnan(x):
            return math.nan
        return math.copysign(math.inf, x) * math.copysign(1, y)
    return x / y


def gN(a: float) -> float:
    return js_pow(2 * a / PI, 0.75)


def h_mats(a, Z=1):
    n = len(a)
    S, T, V = [], [], []
    for i in range(n):
        S.append([])
        T.append([])
        V.append([])
        for j in range(n):
            p = a[i] + a[j]
            N = gN(a[i]) * gN(a[j])
            s = js_pow(PI / p, 1.5)
            S[i].append(N * s)
            T[i].append(N * 3 * a[i] * a[j] / p * s)
            V[i].append(-N * 2 * PI * Z / p)
    return S, T, V


def econtr(a, d, Z=1) -> dict:
    S, T, V = h_mats(a, Z)
    n = len(a)
    s = h = 0
    for i in range(n):
        for j in range(n):
            s += d[i] * d[j] * S[i][j]
            h += d[i] * d[j] * (T[i][j] + V[i][j])
    tt = 0
    for i in range(n):
        y = 0
        for j in range(n):
            y = y + d[i] * d[j] * T[i][j]
        tt = tt + y
    return {"E": _div(h, s), "norm": s, "T": _div(tt, s)}


def jac(A0):
    n = len(A0)
    A = [list(r) for r in A0]
    V = [[1 if i == j else 0 for j in range(n)] for i in range(n)]
    for _sw in range(100):
        off = 0
        for i in range(n):
            for j in range(i + 1, n):
                off += A[i][j] * A[i][j]
        if off < 1e-24:
            break
        for p in range(n):
            for q in range(p + 1, n):
                if abs(A[p][q]) < 1e-16:
                    continue
                th = (A[q][q] - A[p][p]) / (2 * A[p][q])
                t = js_sign(th or 1) / (abs(th) + math.sqrt(th * th + 1))
                c = 1 / math.sqrt(t * t + 1)
                s = t * c
                for k in range(n):
                    x, y = A[k][p], A[k][q]
                    A[k][p] = c * x - s * y
                    A[k][q] = s * x + c * y
                for k in range(n):
                    x, y = A[p][k], A[q][k]
                    A[p][k] = c * x - s * y
                    A[q][k] = s * x + c * y
                for k in range(n):
                    x, y = V[k][p], V[k][q]
                    V[k][p] = c * x - s * y
                    V[k][q] = s * x + c * y
    return [A[i][i] for i in range(n)], V


def evar(a, Z=1):
    """Lowest root of H c = E S c for fixed exponents (None if S is numerically singular)."""
    n = len(a)
    S, T, V = h_mats(a, Z)
    H = [[T[i][j] + V[i][j] for j in range(n)] for i in range(n)]
    w, U = jac(S)
    if min(w) < 1e-10:
        return None
    X = [[x / math.sqrt(w[j]) for j, x in enumerate(r)] for r in U]
    Hp = []
    for i in range(n):
        row = []
        for j in range(n):
            s = 0
            for k in range(n):
                for l in range(n):
                    s += X[k][i] * H[k][l] * X[l][j]
            row.append(s)
        Hp.append(row)
    e, C = jac(Hp)
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
    tot = 0
    for x in c:
        tot = tot + x
    if tot < 0:
        c = [-x for x in c]
    return {"E": e[m], "c": c}


def nelder_mead(f, x0, step=0.5, it=4000):
    n = len(x0)
    P = [list(x0)]
    for i in range(n):
        x = list(x0)
        x[i] += step
        P.append(x)
    F = [f(p) for p in P]
    for _k in range(it):
        idx = sorted(range(n + 1), key=lambda i: F[i])
        P = [P[i] for i in idx]
        F = [F[i] for i in idx]
        if abs(F[n] - F[0]) < 1e-13:
            break
        c = []
        for j in range(n):
            s = 0
            for p in P[:n]:
                s = s + p[j]
            c.append(s / n)
        xr = [v + (v - P[n][j]) for j, v in enumerate(c)]
        fr = f(xr)
        if fr < F[0]:
            xe = [v + 2 * (v - P[n][j]) for j, v in enumerate(c)]
            fe = f(xe)
            if fe < fr:
                P[n], F[n] = xe, fe
            else:
                P[n], F[n] = xr, fr
        elif fr < F[n - 1]:
            P[n], F[n] = xr, fr
        else:
            xc = [v + 0.5 * (P[n][j] - v) for j, v in enumerate(c)]
            fc = f(xc)
            if fc < F[n]:
                P[n], F[n] = xc, fc
            else:
                for i in range(1, n + 1):
                    P[i] = [P[0][j] + 0.5 * (v - P[0][j]) for j, v in enumerate(P[i])]
                    F[i] = f(P[i])
    return P[0], F[0]


def optimize(n: int, Z=1, start=None) -> dict:
    x0 = [log(v) for v in start] if start else [log(0.1 * js_pow(4, i)) for i in range(n)]

    def f(x):
        r = evar([exp(v) for v in x], Z)
        return r["E"] if r else 1
    x, fx = nelder_mead(f, x0)
    x, fx = nelder_mead(f, x, 0.2)
    x, fx = nelder_mead(f, x, 0.05)
    return {"a": sorted(exp(v) for v in x), "E": fx}


_OPT: dict = {}
_OPT_LOCK = threading.Lock()


def opt(n: int) -> dict:
    """Energy-optimised exponents of n = 1..6 (v1.0 OPT, computed once). Azimuth under a lock — the server is a
    ThreadingHTTPServer, and a second request during the first filling saw a partial table (KeyError: 3, a 500)."""
    with _OPT_LOCK:
        if not _OPT:
            table = {k: optimize(k) for k in range(1, 7)}
            _OPT.update(table)
    return _OPT[n]


def slater(r: float, z=1) -> float:
    return math.sqrt(z * z * z / PI) * exp(-z * r)


def gsum(r: float, a, d) -> float:
    s = 0
    for i, x in enumerate(a):
        s = s + d[i] * gN(x) * exp(-x * r * r)
    return s


def overlap_sto(a, d, z=1) -> float:
    s = nn = 0
    h = 0.002
    r = h / 2
    while r < 30:
        g = gsum(r, a, d)
        s += 4 * PI * r * r * slater(r, z) * g * h
        nn += 4 * PI * r * r * g * g * h
        r += h
    return _div(s, math.sqrt(nn))


def current(set_: str, n: int, cust) -> dict:
    if set_ == "sto":
        s = STONG[n]
        return {"a": s["a"], "d": s["d"], "bad": False}
    if set_ == "opt":
        o = opt(n)
        return {"a": o["a"], "d": evar(o["a"])["c"], "bad": False}
    v = evar(cust)
    return {"a": list(cust), "d": v["c"] if v else [0 for _ in cust], "bad": not v}


def _tf(v, lg):
    return log(abs(v) + 1e-300) if lg else v


def part1(set_: str, n: int, cust, sc: str) -> dict:
    B = current(set_, n, cust)
    a, d = B["a"], B["d"]
    lg = sc == "log"
    rmax = 8 if lg else 4
    N = 400
    rs = [rmax * i / N for i in range(N + 1)]
    prim = []
    for i, x in enumerate(a):
        if lg and d[i] <= 0:
            prim.append(None)
            continue
        prim.append([_tf(d[i] * gN(x) * exp(-x * r * r), lg) for r in rs])
    sl = [_tf(slater(r), lg) for r in rs]
    gs = [_tf(gsum(r, a, d), lg) for r in rs]
    rr = [5 * i / 400 for i in range(401)]
    radS, radG = [], []
    for r in rr:
        v = slater(r)
        radS.append(4 * PI * r * r * (v * v))
        v = gsum(r, a, d)
        radG.append(4 * PI * r * r * (v * v))
    ec = econtr(a, d)
    ov = overlap_sto(a, d)
    err = ec["E"] + 0.5
    V = ec["E"] - ec["T"]
    cmp = []
    for k in range(1, 7):
        s = STONG.get(k)
        es = econtr(s["a"], s["d"])["E"] if s else None
        o = opt(k)
        cmp.append({"n": k, "es": es, "esErr": (es + 0.5) * HART if s else None, "eo": o["E"], "eoErr": (o["E"] + 0.5) * HART})
    return {"a": a, "d": d, "bad": B["bad"], "rs": rs, "prim": prim, "sl": sl, "gs": gs, "s0": slater(0),
            "rr": rr, "radS": radS, "radG": radG,
            "E": ec["E"], "errm": err * 1000, "errkj": err * HART, "ov": ov, "psi0": gsum(0, a, d),
            "T": ec["T"], "V": V, "VT": _div(V, ec["T"]), "cmp": cmp}


def ea(a: float) -> dict:
    return {"T": 1.5 * a, "V": -2 * math.sqrt(2 * a / PI)}


def part2(la: float) -> dict:
    a = js_pow(10, la)
    xs = [-2 + 2.6 * i / 260 for i in range(261)]
    cT, cV, cE = [], [], []
    for x in xs:
        e = ea(js_pow(10, x))
        cT.append([x, e["T"]])
        cV.append([x, e["V"]])
        cE.append([x, e["T"] + e["V"]])
    e = ea(a)
    E = e["T"] + e["V"]
    am = 8 / (9 * PI)
    return {"a": a, "T": e["T"], "V": e["V"], "E": E, "VT": e["V"] / e["T"], "am": am, "lam": log10(am),
            "Em": -4 / (3 * PI), "atMin": abs(a - am) / am < 0.01, "cT": cT, "cV": cV, "cE": cE}


# ---------- part 3: size of standard basis sets ----------
SH = {
    "STO-3G": {"H": [[0, 3]], "X": [[0, 3], [0, 3], [1, 3]]},
    "3-21G": {"H": [[0, 2], [0, 1]], "X": [[0, 3], [0, 2], [1, 2], [0, 1], [1, 1]]},
    "6-31G": {"H": [[0, 3], [0, 1]], "X": [[0, 6], [0, 3], [1, 3], [0, 1], [1, 1]]},
    "6-31G(d)": {"H": [[0, 3], [0, 1]], "X": [[0, 6], [0, 3], [1, 3], [0, 1], [1, 1], [2, 1]], "dc": True},
    "6-31G(d,p)": {"H": [[0, 3], [0, 1], [1, 1]], "X": [[0, 6], [0, 3], [1, 3], [0, 1], [1, 1], [2, 1]], "dc": True},
    "6-31+G(d,p)": {"H": [[0, 3], [0, 1], [1, 1]], "X": [[0, 6], [0, 3], [1, 3], [0, 1], [1, 1], [0, 1], [1, 1], [2, 1]], "dc": True},
    "6-311G(d,p)": {"H": [[0, 3], [0, 1], [0, 1], [1, 1]], "X": [[0, 6], [0, 3], [1, 3], [0, 1], [1, 1], [0, 1], [1, 1], [2, 1]]},
    "cc-pVDZ": {"H": {"p": [4, 1], "c": [2, 1]}, "X": {"p": [9, 4, 1], "c": [3, 2, 1]}},
    "aug-cc-pVDZ": {"H": {"p": [5, 2], "c": [3, 2]}, "X": {"p": [10, 5, 2], "c": [4, 3, 2]}},
    "cc-pVTZ": {"H": {"p": [5, 2, 1], "c": [3, 2, 1]}, "X": {"p": [10, 5, 2, 1], "c": [4, 3, 2, 1]}},
    "cc-pVQZ": {"H": {"p": [6, 3, 2, 1], "c": [4, 3, 2, 1]}, "X": {"p": [12, 6, 3, 2, 1], "c": [5, 4, 3, 2, 1]}},
}
LL = "spdfg"
ZZ = {"H": 1, "B": 5, "C": 6, "N": 7, "O": 8, "F": 9}


def ncomp(l: int, dc) -> int:
    return 6 if l == 2 and dc else 2 * l + 1


def atom_info(b: str, el: str) -> dict:
    d = SH[b]
    s = d["H"] if el == "H" else d["X"]
    if isinstance(s, list):
        cnt, pr = [0, 0, 0], [0, 0, 0]
        for l, n in s:
            cnt[l] += 1
            pr[l] += n
        nf = np_ = 0
        for l, n in s:
            nf += ncomp(l, d.get("dc"))
            np_ += n * ncomp(l, d.get("dc"))
        tag = lambda arr: "".join(f"{x}{LL[l]}" if x else "" for l, x in enumerate(arr))  # noqa: E731
        return {"nf": nf, "np": np_, "note": "(" + tag(pr) + ")/[" + tag(cnt) + "]"}
    nf = np_ = 0
    for l, x in enumerate(s["c"]):
        nf += x * (2 * l + 1)
    for l, x in enumerate(s["p"]):
        np_ += x * (2 * l + 1)
    tag = lambda arr: "".join(f"{x}{LL[l]}" for l, x in enumerate(arr))  # noqa: E731
    return {"nf": nf, "np": np_, "note": "(" + tag(s["p"]) + ")/[" + tag(s["c"]) + "]"}


def parse(f: str) -> dict:
    rest = re.sub(r"\s", "", f)
    if not rest:
        return {"err": "empty"}
    if re.sub(r"([A-Z][a-z]?)(\d*)", "", rest, flags=re.ASCII):
        return {"err": "syntax"}
    out: dict = {}
    for m in re.finditer(r"([A-Z][a-z]?)(\d*)", rest, re.ASCII):
        if m.group(1) not in ZZ:
            return {"err": "element", "a": [m.group(1)]}
        out[m.group(1)] = out.get(m.group(1), 0) + (int(m.group(2)) if m.group(2) else 1)
    return {"at": out}


def part3(f: str) -> dict:
    P = parse(f)
    if "err" in P:
        return P
    at = P["at"]
    heavy = sum(v for e, v in at.items() if e != "H")
    nH = at.get("H", 0)
    ne = sum(ZZ[e] * v for e, v in at.items())
    rows = []
    for b in SH:
        nf = np_ = 0
        for e, v in at.items():
            i = atom_info(b, e)
            nf += i["nf"] * v
            np_ += i["np"] * v
        rows.append({"b": b, "nf": nf, "np": np_, "nX": atom_info(b, "C")["note"], "nHn": atom_info(b, "H")["note"]})
    occ = ne // 2
    base = rows[0]["nf"]
    for r in rows:
        ri = js_pow(r["nf"], 4) / 8
        r["ints"] = ri
        r["mem"] = ri * 8
        r["rel"] = js_pow(r["nf"] / base, 4)
        r["direct"] = ri * 8 > 4 * js_pow(1024, 3)
    return {"heavy": heavy, "nH": nH, "ne": ne, "occ": occ, "rows": rows}
