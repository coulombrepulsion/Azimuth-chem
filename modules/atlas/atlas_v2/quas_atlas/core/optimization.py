"""Geometry optimisation on the symmetric potential-energy surface of H2O (HF/6-31G*, C2v):
bicubic-spline interpolation, steepest descent (fixed step and line search), Newton-Raphson,
BFGS, harmonic frequencies by the Wilson GF method, contour lines.

HEADER
    Model of the page "Оптимизация геометрии" (v1.0 optimization.js: PES,
    OPT = {spl, sev, E, grad, hess, eig2, run, freqs}, MIN, SEG).
    Wilkinson convention, sections 1-8. r in A (bohr inside the
    optimiser), theta in degrees (radians inside), E in hartree.

§1 THEORY
    E(r, theta) on a 33 x 33 grid r = 0.80..1.20 A, theta = 80..140 deg
    (both O-H bonds equal), computed by the author of v1.0 with PySCF
    (data/optimization_h2o_pes.json). Interpolation: natural cubic
    spline along theta for every r row, then along r through the
    interpolated column (unit knot spacing in index space). Gradient by
    central differences (1e-4), Hessian by central differences of the
    gradient (2e-3), symmetrised. Steepest descent u <- u - alpha g;
    steepest descent with golden-section line search (bracket doubling
    from 0.2, 30 golden steps); Newton-Raphson u <- u - H^-1 g with the
    step capped at 0.3; BFGS with backtracking (Armijo c = 1e-4, initial
    step capped at 0.3) and the update B += y y^T / (s.y) - B s s^T B /
    (s.B s) when s.y > 1e-12. Convergence |g| < 1e-5. Harmonic
    frequencies of the A1 block (Wilson, Decius, Cross): S1 = (dr1 +
    dr2)/sqrt2, S2 = theta; F from the Hessian, G elements for the
    symmetric internal coordinates with masses 1.00782503 and 15.99491462
    u; nu = sign(l) sqrt|l| x 219474.63 cm^-1.

§2 ALGORITHM
    As v1.0 step by step. Contours: marching squares on a 97 x 97
    resampled grid for the levels 1, 2, 5, ... 200 kJ/mol above the
    minimum.

§3 APPLICATIONS
    Endpoints opt.static, opt.runs.

§4 SPECIFICATION
    run(method, start (r A, theta deg), step) -> {path: [{u, e, g, rt,
      neg?, out?, de}], nE, nG, nH, stop in conv/max/out}.
    Tier: bitwise vs v1.0 on Linux/glibc (EXACT).

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    The interpolated surface is only C2 between grid points; the methods
    see the spline, not the original HF surface.
§7 TEST CASES (tests/test_optimization.py)
    The spline reproduces the grid values at the knots (1e-12); all
    methods from three starts converge to the same minimum (1e-4 A,
    0.01 deg); Newton needs <= 6 steps; BFGS < steepest descent steps;
    minimum r = 0.947 A, theta = 105.5 deg (HF/6-31G* literature
    0.947 A, 105.5 deg); Hessian eigenvalues positive; frequencies within
    1 % of the HF/6-31G* harmonic values (1827 and 4070 cm^-1, NIST
    CCCBDB) ; vs v1.0.
§8 ERROR ANALYSIS
    Spline interpolation error O(h^4) on a 0.0125 A / 1.875 deg grid
    (~1e-7 Eh); finite-difference gradients O(h^2) ~ 1e-8; Hessian
    O(h^2) ~ 1e-6 relative -> frequencies to ~1 cm^-1.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from .jsmath import cos, js_hypot, js_sign, log10, sin  # noqa: F401

PES = json.loads((Path(__file__).parent / "data" / "optimization_h2o_pes.json").read_text(encoding="utf-8"))
BOHR = 0.52917721092
D2R = math.pi / 180
KJ = 2625.4996


def spl(y):
    n = len(y)
    u, z = [0.0] * n, [0.0] * n
    for i in range(1, n - 1):
        p = 0.5 * z[i - 1] + 2
        z[i] = -0.5 / p
        u[i] = (3 * (y[i + 1] - 2 * y[i] + y[i - 1]) - 0.5 * u[i - 1]) / p
    for k in range(n - 2, -1, -1):
        z[k] = z[k] * z[k + 1] + u[k]
    return z


def sev(y, z, x):
    n = len(y)
    i = math.floor(x)
    if i < 0:
        i = 0
    if i > n - 2:
        i = n - 2
    b = x - i
    a = 1 - b
    return a * y[i] + b * y[i + 1] + ((a * a * a - a) * z[i] + (b * b * b - b) * z[i + 1]) / 6


ROWS = [(r, spl(r)) for r in PES["E"]]


def ir(r):
    return (r - PES["r"][0]) / (PES["r"][1] - PES["r"][0]) * (PES["r"][2] - 1)


def it(t):
    return (t - PES["t"][0]) / (PES["t"][1] - PES["t"][0]) * (PES["t"][2] - 1)


def inside(r, t):
    a, b = ir(r), it(t)
    return 0 <= a <= PES["r"][2] - 1 and 0 <= b <= PES["t"][2] - 1


def E(r, t):
    b = it(t)
    col = [sev(y, z, b) for y, z in ROWS]
    return sev(col, spl(col), ir(r))


def to_u(r, t):
    return [r / BOHR, t * D2R]


def from_u(u):
    return [u[0] * BOHR, u[1] / D2R]


def Eu(u):
    r, t = from_u(u)
    return E(r, t)


def grad(u):
    h = [1e-4, 1e-4]
    out = []
    for k in range(2):
        a, b = list(u), list(u)
        a[k] += h[k]
        b[k] -= h[k]
        out.append((Eu(a) - Eu(b)) / (2 * h[k]))
    return out


def hess(u):
    h = 2e-3
    H = [[0, 0], [0, 0]]
    for k in range(2):
        a, b = list(u), list(u)
        a[k] += h
        b[k] -= h
        ga, gb = grad(a), grad(b)
        for j in range(2):
            H[j][k] = (ga[j] - gb[j]) / (2 * h)
    o = (H[0][1] + H[1][0]) / 2
    H[0][1] = H[1][0] = o
    return H


def eig2(H):
    a, b, d = H[0][0], H[0][1], H[1][1]
    m = (a + d) / 2
    x = (a - d) / 2
    q = math.sqrt(x * x + b * b)
    return [m - q, m + q]


def in_u(u):
    r, t = from_u(u)
    return inside(r, t)


def nrm(g):
    return js_hypot(g[0], g[1])


def run(method, start, step=0.5, tol=1e-5, maxit=200) -> dict:
    u = to_u(start[0], start[1])
    path = []
    cnt = {"E": 0, "G": 0, "H": 0}
    stop = "max"
    B = [[1, 0], [0, 1]]

    def Ef(v):
        cnt["E"] += 1
        return Eu(v)

    def Gf(v):
        cnt["G"] += 1
        return grad(v)
    e, g = Ef(u), Gf(u)
    path.append({"u": list(u), "e": e, "g": nrm(g)})
    for _it in range(maxit):
        if nrm(g) < tol:
            stop = "conv"
            break
        if method in ("sd", "sdls"):
            d = [-g[0], -g[1]]
        elif method == "nr":
            cnt["H"] += 1
            H = hess(u)
            det = H[0][0] * H[1][1] - H[0][1] * H[1][0]
            d = [-(H[1][1] * g[0] - H[0][1] * g[1]) / det, -(-H[1][0] * g[0] + H[0][0] * g[1]) / det]
            if eig2(H)[0] <= 0:
                path[-1]["neg"] = True
        else:
            det = B[0][0] * B[1][1] - B[0][1] * B[1][0]
            d = [-(B[1][1] * g[0] - B[0][1] * g[1]) / det, -(-B[1][0] * g[0] + B[0][0] * g[1]) / det]
        un = None
        if method == "sd":
            un = [u[0] + step * d[0], u[1] + step * d[1]]
        elif method == "nr":
            L, cap = nrm(d), 0.3
            s = cap / L if L > cap else 1
            un = [u[0] + s * d[0], u[1] + s * d[1]]
        elif method == "sdls":
            a, b = 0, 0.2

            def f(s):
                v = [u[0] + s * d[0], u[1] + s * d[1]]
                return Ef(v) if in_u(v) else 1e9
            while f(b) < f(b / 2) and b < 50:
                b *= 2
            gr = (math.sqrt(5) - 1) / 2
            c = b - gr * (b - a)
            dd = a + gr * (b - a)
            fc, fd = f(c), f(dd)
            for _k in range(30):
                if fc < fd:
                    b = dd
                    dd = c
                    fd = fc
                    c = b - gr * (b - a)
                    fc = f(c)
                else:
                    a = c
                    c = dd
                    fc = fd
                    dd = a + gr * (b - a)
                    fd = f(dd)
            s = (a + b) / 2
            un = [u[0] + s * d[0], u[1] + s * d[1]]
        else:
            s = 1
            slope = g[0] * d[0] + g[1] * d[1]
            L = nrm(d)
            if L > 0.3:
                s = 0.3 / L
            for _k in range(30):
                v = [u[0] + s * d[0], u[1] + s * d[1]]
                if in_u(v) and Ef(v) <= e + 1e-4 * s * slope:
                    un = v
                    break
                s *= 0.5
            if un is None:
                un = [u[0] + s * d[0], u[1] + s * d[1]]
        if not in_u(un):
            stop = "out"
            path.append({"u": un, "e": math.nan, "g": math.nan, "out": True})
            break
        en, gn = Ef(un), Gf(un)
        if method == "bfgs":
            s_ = [un[0] - u[0], un[1] - u[1]]
            y = [gn[0] - g[0], gn[1] - g[1]]
            sy = s_[0] * y[0] + s_[1] * y[1]
            if sy > 1e-12:
                Bs = [B[0][0] * s_[0] + B[0][1] * s_[1], B[1][0] * s_[0] + B[1][1] * s_[1]]
                sBs = s_[0] * Bs[0] + s_[1] * Bs[1]
                for i in range(2):
                    for j in range(2):
                        B[i][j] += y[i] * y[j] / sy - Bs[i] * Bs[j] / sBs
        u, e, g = un, en, gn
        path.append({"u": list(u), "e": e, "g": nrm(g)})
    if nrm(g) < tol:
        stop = "conv"
    for p in path:
        p["rt"] = from_u(p["u"])
    return {"path": path, "nE": cnt["E"], "nG": cnt["G"], "nH": cnt["H"], "stop": stop}


def freqs(r, t):
    u = to_u(r, t)
    H = hess(u)
    R, th = u[0], u[1]
    AMU = 1822.888486
    mH, mO = 1 / (1.00782503 * AMU), 1 / (15.99491462 * AMU)
    SQ2 = math.sqrt(2)
    F = [[H[0][0] / 2, H[0][1] / SQ2], [H[1][0] / SQ2, H[1][1]]]
    G = [[mH + mO * (1 + cos(th)), -SQ2 * mO * sin(th) / R], [-SQ2 * mO * sin(th) / R, 2 / (R * R) * (mH + mO * (1 - cos(th)))]]
    GF = [[G[0][0] * F[0][0] + G[0][1] * F[1][0], G[0][0] * F[0][1] + G[0][1] * F[1][1]],
          [G[1][0] * F[0][0] + G[1][1] * F[1][0], G[1][0] * F[0][1] + G[1][1] * F[1][1]]]
    tr = GF[0][0] + GF[1][1]
    det = GF[0][0] * GF[1][1] - GF[0][1] * GF[1][0]
    q = math.sqrt(max(0, tr * tr / 4 - det))
    return [js_sign(l) * math.sqrt(abs(l)) * 219474.63 for l in (tr / 2 - q, tr / 2 + q)]


_MIN: dict = {}


def minimum() -> dict:
    if not _MIN:
        q = run("nr", [0.95, 105])
        p = q["path"][-1]
        _MIN.update(r=p["rt"][0], t=p["rt"][1], e=p["e"])
    return dict(_MIN)


R0, R1, T0, T1 = 0.80, 1.20, 80, 140
LEV = [1, 2, 5, 10, 20, 50, 100, 200]


def contours():
    n = 96
    m = minimum()
    G = [[(E(R0 + (R1 - R0) * i / n, T0 + (T1 - T0) * j / n) - m["e"]) * KJ for j in range(n + 1)] for i in range(n + 1)]
    P = lambda i, j: [R0 + (R1 - R0) * i / n, T0 + (T1 - T0) * j / n]  # noqa: E731
    out = [[] for _ in LEV]
    for li, lv in enumerate(LEV):
        for i in range(n):
            for j in range(n):
                v = [G[i][j], G[i + 1][j], G[i + 1][j + 1], G[i][j + 1]]
                c = [P(i, j), P(i + 1, j), P(i + 1, j + 1), P(i, j + 1)]
                pts = []
                for e in range(4):
                    a, b = v[e], v[(e + 1) % 4]
                    if (a - lv) * (b - lv) < 0:
                        f = (lv - a) / (b - a)
                        A, Bq = c[e], c[(e + 1) % 4]
                        pts.append([A[0] + f * (Bq[0] - A[0]), A[1] + f * (Bq[1] - A[1])])
                if len(pts) == 2:
                    out[li].append(pts)
                elif len(pts) == 4:
                    out[li].append([pts[0], pts[1]])
                    out[li].append([pts[2], pts[3]])
    return out


_STATIC: dict = {}


def static() -> dict:
    if not _STATIC:
        m = minimum()
        Hm = hess(to_u(m["r"], m["t"]))
        _STATIC.update(MIN=m, SEG=contours(), ev=eig2(Hm), f=freqs(m["r"], m["t"]))
    return _STATIC


METHODS = ("sd", "sdls", "nr", "bfgs")


def runs(start, step) -> dict:
    m = minimum()
    out = {}
    for meth in METHODS:
        q = run(meth, start, step)
        for p in q["path"]:
            p["de"] = (p["e"] - m["e"]) * KJ
        out[meth] = q
    return out
