"""Variational method (trial functions, linear variation in a Gaussian basis) and
Rayleigh-Schroedinger perturbation theory for the anharmonic oscillator.

HEADER
    Model of the page "Вариационный метод и теория возмущений" (v1.0
    variational.js: jac, TR, lvm, optFor, optCurve, X4, exact, E1, E2).
    Atomic units.  Wilkinson convention, sections 1-8.

§1 THEORY
    Hydrogen atom (exact E0 = -1/2):
      Slater trial e^-zeta r:   E(zeta) = zeta^2/2 - zeta  (min at zeta = 1, exact);
      Gaussian trial e^-a r^2: E(a) = 3a/2 - 2 sqrt(2a/pi) (min 8/(9 pi) -> -4/(3 pi)).
    Linear variation in N s-Gaussians with even-tempered exponents
    a_k = a0 beta^k: S_ij = (pi/p)^(3/2), H_ij = (3 a b / p) S_ij - 2 pi/p,
    p = a + b; generalised eigenproblem H c = E S c solved by canonical
    orthogonalisation (eigenvectors of S with eigenvalue > 1e-10 s_max,
    X = U s^-1/2, H' = X^T H X).  The roots are upper bounds to the exact
    levels (Hylleraas-Undheim-MacDonald).  a0 and beta are optimised by a
    pattern search in (ln a0, ln beta).
    Perturbation theory for H = p^2/2 + x^2/2 + lambda x^4 in the harmonic
    oscillator basis (40 functions; x^4 from the ladder matrix of x):
      E1 = (3/4)(2n^2 + 2n + 1) lambda,
      E2 = -(34 n^3 + 51 n^2 + 59 n + 21)/8 lambda^2,
    "exact" levels by diagonalising the 20 x 20 parity block.

§2 ALGORITHM
    Cyclic Jacobi (v1.0 jac: up to 80 sweeps, off-norm < 1e-26), eigenvalues
    sorted ascending (stable).  Pattern search: 8 directions, step 0.6
    halved on failure, at most 200 iterations, stop at step < 1e-3; the
    curve of optimised energies for N = 1..10 starts from (0.3, 4) and
    seeds each N from the previous optimum (a0/1.5, max(1.6, 0.85 beta)).

§3 APPLICATIONS
    Endpoints var.trial, var.lvm, var.optimize, var.optcurve, var.pt.

§4 SPECIFICATION
    lvm(N, a0, beta) -> {E (ascending), C (N x m), al, smin, dropped}
    opt_for(N, a0, beta) -> {a0, be, E}
    exact(lambda, n) -> E_n of the anharmonic oscillator.
    Tier: bitwise vs v1.0 on Linux/glibc (pow(x, 1.5) and beta^k use the
    platform pow, as V8).  The optimised curve opt_curve() is a constant of
    the page; it is computed once (about 10 s) and kept in memory.

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    v1.0 memoised exact() by lambda.toFixed(4): two lambdas with the same
    4-decimal key shared a value (difference ~1e-16).  Here the cache key
    is the exact double, so each lambda gets its own value.
§7 TEST CASES (tests/test_variational.py)
    E_slater(1) = -1/2, E_gauss(8/(9 pi)) = -4/(3 pi); linear variation:
    E(N) decreases with N and stays above -1/2 (variational bound); the
    N = 1 Gaussian lvm equals the analytic Gaussian energy at a = a0;
    E1, E2 against a finite-difference fit of exact(lambda) for small
    lambda (1e-6); exact(0, n) = n + 1/2; vs v1.0.
§8 ERROR ANALYSIS
    Jacobi: backward stable, eigenvalue errors ~ u ||H||; the S matrix of
    a nearly dependent basis has condition up to 1e10, the canonical
    orthogonalisation removes directions below 1e-10 s_max so that
    E is accurate to ~1e-6 relative even then.  The 40-function oscillator
    basis truncates the exact levels by < 1e-8 for lambda <= 0.5, n <= 3
    (n = 4 at lambda = 0.5: about 1e-6, below the displayed digits).
"""
from __future__ import annotations

import functools
import math

from .jsmath import exp, js_pow, js_sign, log

PI = math.pi
# ------------------------------------------------------------ Jacobi
def jac(A0):
    n = len(A0)
    A = [list(r) for r in A0]
    V = [[1 if i == j else 0 for j in range(n)] for i in range(n)]
    sqrt = math.sqrt
    for _sw in range(80):
        off = 0.0
        for i in range(n):
            Ai = A[i]
            for j in range(i + 1, n):
                off += Ai[j] * Ai[j]
        if off < 1e-26:
            break
        for p in range(n):
            for q in range(p + 1, n):
                apq = A[p][q]
                if abs(apq) < 1e-300:
                    continue
                th = (A[q][q] - A[p][p]) / (2 * apq)
                t = js_sign(th or 1) / (abs(th) + sqrt(th * th + 1))
                c = 1 / sqrt(t * t + 1)
                s = t * c
                for row in A:
                    a, b = row[p], row[q]
                    row[p] = c * a - s * b
                    row[q] = s * a + c * b
                Ap, Aq = A[p], A[q]
                A[p] = [c * a - s * b for a, b in zip(Ap, Aq)]
                A[q] = [s * a + c * b for a, b in zip(Ap, Aq)]
                for row in V:
                    a, b = row[p], row[q]
                    row[p] = c * a - s * b
                    row[q] = s * a + c * b
    idx = sorted(range(n), key=lambda i: A[i][i])
    return {"val": [A[i][i] for i in idx], "vec": [[r[i] for i in idx] for r in V]}


# ------------------------------------------------------- trial functions
def e_slater(z):
    return z * z / 2 - z


def e_gauss(a):
    return 1.5 * a - 2 * math.sqrt(2 * a / PI)


TRIAL = {"slater": {"E": e_slater, "lo": 0.2, "hi": 2.5, "log": False, "opt": 1},
         "gauss": {"E": e_gauss, "lo": 0.01, "hi": 3, "log": True, "opt": 8 / (9 * PI)}}


def _dens(trial, v, r):
    if trial == "slater":
        return 4 * v * v * v * r * r * exp(-2 * v * r)
    return 4 * PI * r * r * js_pow(2 * v / PI, 1.5) * exp(-2 * v * r * r)


def _log10(x):
    from .jsmath import log10
    return log10(x)


def trial(name: str, v: float) -> dict:
    T = TRIAL[name]
    pts = []
    for i in range(201):
        f = i / 200
        if T["log"]:
            p = js_pow(10, _log10(T["lo"]) + f * (_log10(T["hi"]) - _log10(T["lo"])))
        else:
            p = T["lo"] + f * (T["hi"] - T["lo"])
        pts.append([p, T["E"](p)])
    rr = [i / 240 * 6 for i in range(241)]
    E, Eo = T["E"](v), T["E"](T["opt"])
    Tk = v * v / 2 if name == "slater" else 1.5 * v
    Vp = E - Tk
    return {"curve": pts, "opt": T["opt"], "Eopt": Eo, "E": E, "dE": E + 0.5, "ratio": -Vp / Tk,
            "r": rr, "exact": [4 * r * r * exp(-2 * r) for r in rr], "dens": [_dens(name, v, r) for r in rr]}


# ---------------------------------------------------- linear variation
def lvm(N: int, a0: float, be: float) -> dict:
    al = [a0 * js_pow(be, k) for k in range(N)]
    S, H = [], []
    for i in range(N):
        S.append([])
        H.append([])
        for j in range(N):
            a, b = al[i], al[j]
            p = a + b
            s = js_pow(PI / p, 1.5)
            S[i].append(s)
            H[i].append(3 * a * b / p * s - 2 * PI / p)
    e = jac(S)
    last = e["val"][-1]
    keep = [(v, i) for i, v in enumerate(e["val"]) if v > 1e-10 * last]
    X = [[e["vec"][r][i] / math.sqrt(v) for v, i in keep] for r in range(N)]
    m = len(keep)
    Hp = []
    for p in range(m):
        row = []
        for q in range(m):
            s = 0.0
            for i in range(N):
                Xip, Hi = X[i][p], H[i]
                for j in range(N):
                    s += Xip * Hi[j] * X[j][q]
            row.append(s)
        Hp.append(row)
    f = jac(Hp)
    C = []
    for i in range(N):
        row = []
        for k in range(len(f["vec"][0])):
            s = 0.0
            for p in range(m):
                s += X[i][p] * f["vec"][p][k]
            row.append(s)
        C.append(row)
    return {"E": f["val"], "C": C, "al": al, "smin": e["val"][0] / last, "dropped": N - m}


def lvm_view(N: int, a0: float, be: float) -> dict:
    """Everything section 2 of the page shows for (N, a0, beta)."""
    res = lvm(N, a0, be)
    Es = [lvm(k + 1, a0, be)["E"][0] for k in range(10)]
    c = [r[0] for r in res["C"]]
    nrm = 0.0
    for i in range(N):
        for j in range(N):
            nrm += c[i] * c[j] * js_pow(PI / (res["al"][i] + res["al"][j]), 1.5)
    tot = 0
    for x in c:
        tot = tot + x
    sg = (1 if tot >= 0 else -1) / math.sqrt(nrm)
    rr = [i / 240 * 4 for i in range(241)]

    def phi(r):
        s = 0
        for k, x in enumerate(c):
            s = s + x * exp(-res["al"][k] * r * r)
        return sg * s
    err = res["E"][0] + 0.5
    ex = [-0.5, -0.125, -1 / 18, -1 / 32]
    diff = [res["E"][k] - ex[k] for k in range(min(4, len(res["E"])))]
    return {"E": res["E"], "Es": Es, "exn": ex, "diff": diff, "dropped": res["dropped"], "r": rr, "phi": [phi(r) for r in rr],
            "exact": [exp(-r) / math.sqrt(PI) for r in rr], "err": err, "errm": err * 1000, "errk": err * 627.51}


def opt_for(N: int, a0: float, be: float) -> dict:
    best = [log(a0), log(be)]

    def f(t):
        b = exp(t[1])
        if b < 1.3 or b > 12:
            return 1
        a = exp(t[0])
        if a < 1e-4 or a > 5:
            return 1
        return lvm(N, a, b)["E"][0]
    bv = f(best)
    step = 0.6
    it = 0
    while it < 200 and step > 1e-3:
        imp = False
        for d in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
            t = [best[0] + d[0] * step, best[1] + d[1] * step]
            v = f(t)
            if v < bv - 1e-13:
                bv, best, imp = v, t, True
        if not imp:
            step /= 2
        it += 1
    return {"a0": exp(best[0]), "be": exp(best[1]), "E": bv}


@functools.lru_cache(maxsize=1)
def opt_curve() -> tuple:
    out = []
    a, b = 0.3, 4
    for N in range(1, 11):
        r = opt_for(N, a, b)
        out.append(r)
        a = r["a0"] / 1.5
        b = max(1.6, r["be"] * 0.85)
    return tuple(out)


# ------------------------------------------------- perturbation theory
NBAS = 40


def _x4():
    M = NBAS + 4
    X = [[0.0] * M for _ in range(M)]
    for i in range(M - 1):
        X[i][i + 1] = X[i + 1][i] = math.sqrt((i + 1) / 2)

    def mm(A, B):
        return [[sum_seq(A[i][k] * B[k][j] for k in range(M)) for j in range(M)] for i in range(M)]
    X2 = mm(X, X)
    return mm(X2, X2)


def sum_seq(it):
    s = 0
    for x in it:
        s = s + x
    return s



# Azimuth built at the first calculation that needs it, not on import (see core/postulates.py)
_x4_table = functools.lru_cache(maxsize=1)(_x4)


def __getattr__(name):
    if name == "X4":
        return _x4_table()
    raise AttributeError(name)


@functools.lru_cache(maxsize=4096)
def exact(l: float, n: int) -> float:
    par = n % 2
    idx = list(range(par, NBAS, 2))
    X4 = _x4_table()
    H = [[(i + 0.5 if i == j else 0) + l * X4[i][j] for j in idx] for i in idx]
    return jac(H)["val"][(n - par) // 2]


def E1(n):
    return 0.75 * (2 * n * n + 2 * n + 1)


def E2(n):
    return -(34 * n * n * n + 51 * n * n + 59 * n + 21) / 8


def pt(lam: float, n: int) -> dict:
    ls = [i / 50 * 0.5 for i in range(51)]
    ex = [exact(l, n) for l in ls]
    p1 = [n + 0.5 + E1(n) * l for l in ls]
    p2 = [n + 0.5 + E1(n) * l + E2(n) * l * l for l in ls]
    xs = [-3.5 + i / 280 * 2 * 3.5 for i in range(281)]

    def V(x):
        return x * x / 2 + lam * x * x * x * x
    lev = []
    for k in range(5):
        e = exact(lam, k)
        if e > 6:
            break
        xt = 0
        for x in xs:
            if x > 0 and V(x) >= e:
                xt = x
                break
        lev.append([e, xt])
    e = exact(lam, n)
    q1 = n + 0.5 + E1(n) * lam
    q2 = q1 + E2(n) * lam * lam
    return {"E1": E1(n), "E2": E2(n), "ls": ls, "ex": ex, "p1": p1, "p2": p2, "xs": xs, "V0": [x * x / 2 for x in xs],
            "V": [V(x) for x in xs], "lev": lev, "e": e, "q1": q1, "q2": q2, "d0": n + 0.5 - e, "d1": q1 - e, "d2": q2 - e,
            "r1": abs(q1 - e), "r2": abs(q2 - e)}
