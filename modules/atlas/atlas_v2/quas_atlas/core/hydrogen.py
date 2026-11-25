"""Hydrogen-like atom: radial functions, real orbitals, densities, energy levels and spectral series.

HEADER
    Model of the page "Атом водорода и атомные орбитали" (v1.0 hydrogen.js:
    lag, R, ORB, psi, drawMap, radial, sample, levels, quiz).  Atomic units
    unless stated.  Wilkinson convention, sections 1-8.

§1 THEORY
    psi_nlm = R_nl(r) Y_lm(theta, phi) with real spherical harmonics Y
    (s, p_x,y,z, five d, seven f; normalisation constants of the page).
      R_nl(r) = N rho^l e^(-rho/2) L_{n-l-1}^{(2l+1)}(rho),  rho = 2 Z r / n,
      N = sqrt((2Z/n)^3 (n-l-1)! / (2n (n+l)!)),
    generalised Laguerre polynomials by the three-term recurrence
      L_{j+1} = ((2j + 1 + a - x) L_j - (j + a) L_{j-1}) / (j + 1).
    E_n = -Z^2 / (2 n^2) E_h; <r> = (3 n^2 - l(l+1)) / (2Z); radial nodes
    n - l - 1, angular nodes l.  Line positions nu = R_M Z^2 (1/n1^2 -
    1/n2^2) with the reduced-mass Rydberg constants of H, He+, Li2+
    (109677.58, 109722.27, 109728.73 cm^-1); levels -hc R_M Z^2/n^2 with the same constants
    (2.10.0; v1.0: -13.6057 Z^2/n^2 eV, LEVEL_MASS = "infinite").
    The point cloud samples |psi|^2 by rejection in the cube |x|,|y|,|z| <=
    0.9 L, L = (2.3 n^2 + 3.5)/Z.

§2 ALGORITHM
    As v1.0, pixel by pixel and point by point.  The map values are
    returned as float32 (v1.0 stored them in a Float32Array) packed in
    base64.  Sampling: random numbers from Python's Mersenne Twister seeded
    by the page (v1.0: Math.random); with numpy the candidates are
    evaluated in batches.

§3 APPLICATIONS
    Endpoints h.map, h.radial, h.cloud, h.levels, h.quiz.

§4 SPECIFICATION
    psi(n, l, k, Z, x, y, z) -> float.  Tier: bitwise vs v1.0 on
    Linux/glibc (rho^l uses the platform pow, as V8) for map, radial,
    levels, quiz; the cloud is a different random sample of the same
    distribution (tier "statistical": the mean distance of the points from
    the nucleus agrees with the exact truncated expectation within 3 sigma).

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    The normalisation N is evaluated once per call with the same
    operations as v1.0 (identical bits).
§7 TEST CASES (tests/test_hydrogen.py)
    Integral of r^2 R^2 = 1 (Simpson, 1e-6) for all n <= 4, l < n; R_10 =
    2 Z^1.5 e^-Zr exactly; nodes of R_30 at r = (9 +- 3 sqrt 3)/2;
    most probable r of 1s = 1/Z; Balmer H-alpha 656.47 nm (vacuum);
    angular functions orthonormal on a Lebedev-like grid (1e-3); vs v1.0.
§8 ERROR ANALYSIS
    The recurrence is stable for x > 0 and k <= 3; values carry errors of
    a few u relative.  The map is quantised to float32 (as in v1.0).
"""
from __future__ import annotations

import base64
import math
import random
import struct

from .jsmath import exp, hypot3, js_pow

EV, BOHR = 27.211386, 0.529177
RYD = {1: 109677.58, 2: 109722.27, 3: 109728.73}

# real angular functions: (id, l, f(x, y, z, r))
ORB = [
    ("s", 0, lambda x, y, z, r: 0.28209479),
    ("pz", 1, lambda x, y, z, r: 0.48860251 * z / r),
    ("px", 1, lambda x, y, z, r: 0.48860251 * x / r),
    ("py", 1, lambda x, y, z, r: 0.48860251 * y / r),
    ("dz2", 2, lambda x, y, z, r: 0.31539157 * (3 * z * z - r * r) / (r * r)),
    ("dxz", 2, lambda x, y, z, r: 1.09254843 * x * z / (r * r)),
    ("dyz", 2, lambda x, y, z, r: 1.09254843 * y * z / (r * r)),
    ("dxy", 2, lambda x, y, z, r: 1.09254843 * x * y / (r * r)),
    ("dx2y2", 2, lambda x, y, z, r: 0.54627422 * (x * x - y * y) / (r * r)),
    ("fz3", 3, lambda x, y, z, r: 0.37317633 * z * (5 * z * z - 3 * r * r) / (r * r * r)),
    ("fxz2", 3, lambda x, y, z, r: 0.45704580 * x * (5 * z * z - r * r) / (r * r * r)),
    ("fyz2", 3, lambda x, y, z, r: 0.45704580 * y * (5 * z * z - r * r) / (r * r * r)),
    ("fxyz", 3, lambda x, y, z, r: 2.89061144 * x * y * z / (r * r * r)),
    ("fzx2y2", 3, lambda x, y, z, r: 1.44530572 * z * (x * x - y * y) / (r * r * r)),
    ("fx3", 3, lambda x, y, z, r: 0.59004359 * x * (x * x - 3 * y * y) / (r * r * r)),
    ("fy3", 3, lambda x, y, z, r: 0.59004359 * y * (3 * x * x - y * y) / (r * r * r)),
]


def fact(n: int) -> int:
    r = 1
    for i in range(2, n + 1):
        r *= i
    return r


def lag(k: int, a: int, x: float) -> float:
    if k == 0:
        return 1
    l0, l1 = 1, 1 + a - x
    for j in range(1, k):
        l2 = ((2 * j + 1 + a - x) * l1 - (j + a) * l0) / (j + 1)
        l0, l1 = l1, l2
    return l1


def _norm(n, l, Z):
    return math.sqrt(js_pow(2 * Z / n, 3) * fact(n - l - 1) / (2 * n * fact(n + l)))


def R(n: int, l: int, Z: int, r: float, N: float | None = None) -> float:
    rho = 2 * Z * r / n
    if N is None:
        N = _norm(n, l, Z)
    return N * exp(-rho / 2) * js_pow(rho, l) * lag(n - l - 1, 2 * l + 1, rho)


def extent(n: int, Z: int) -> float:
    return (n * n * 2.3 + 3.5) / Z


def _psi_fn(n, k, Z):
    l, f = ORB[k][1], ORB[k][2]
    N = _norm(n, l, Z)

    def psi(x, y, z):
        r = hypot3(x, y, z) or 1e-9
        return R(n, l, Z, r, N) * f(x, y, z, r)
    return psi


def map_grid(n: int, k: int, Z: int, plane: str, W: int, H: int) -> dict:
    """psi on the W x H pixel grid of the slice (row-major, top row first), as float32."""
    L = extent(n, Z)
    psi = _psi_fn(n, k, Z)
    vals = []
    mx = 0
    for j in range(H):
        b = (1 - j / (H - 1) * 2) * L
        for i in range(W):
            a = (i / (W - 1) * 2 - 1) * L
            if plane == "xz":
                v = psi(a, 0, b)
            elif plane == "xy":
                v = psi(a, b, 0)
            else:
                v = psi(0, a, b)
            vals.append(v)
            mx = max(mx, abs(v))
    raw = struct.pack(f"<{len(vals)}f", *vals)
    return {"L": L, "W": W, "H": H, "mx": mx, "f32": base64.b64encode(raw).decode("ascii")}


def radial(n: int, k: int, Z: int) -> dict:
    l = ORB[k][1]
    L = extent(n, Z) * 1.1
    N = 600
    rs = [(i + 0.5) / N * L for i in range(N)]
    Rv = [R(n, l, Z, r) for r in rs]
    Pv = [r * r * Rv[i] * Rv[i] for i, r in enumerate(rs)]
    nodes = [(rs[i - 1] + rs[i]) / 2 for i in range(1, N) if Rv[i - 1] * Rv[i] < 0]
    rm = (3 * n * n - l * (l + 1)) / (2 * Z)
    ip = 0
    for i, v in enumerate(Pv):
        if v > Pv[ip]:
            ip = i
    rmp = rs[ip]
    if 0 < ip < len(Pv) - 1:  # parabola through the three grid values around the maximum
        a, b, c = Pv[ip - 1], Pv[ip], Pv[ip + 1]
        dn = a - 2 * b + c
        if dn < 0:
            rmp = rs[ip] + (rs[ip + 1] - rs[ip - 1]) / 2 * (a - c) / (2 * dn)
    E = -Z * Z / (2 * n * n)
    return {"L": L, "rs": rs, "Rv": Rv, "Pv": Pv, "mR": max(abs(v) for v in Rv), "mP": max(Pv), "nodes": nodes,
            "rm": rm, "rmA": rm * BOHR, "ip": ip, "rmp": rmp, "rmpA": rmp * BOHR, "E": E, "Eev": E * EV}


try:  # optional: vectorised sampling (statistical tier, see §4)
    import numpy as _np
except ImportError:  # pragma: no cover
    _np = None


def _cloud_np(n, k, Z, seed, npts):
    l, f = ORB[k][1], ORB[k][2]
    N = _norm(n, l, Z)
    L = extent(n, Z) * 0.9
    g = _np.random.default_rng(seed)

    def psi(P):
        x, y, z = P
        r = _np.sqrt(x * x + y * y + z * z)
        r[r == 0] = 1e-9
        rho = 2 * Z * r / n
        kk, a = n - l - 1, 2 * l + 1
        if kk == 0:
            lg = 1.0
        else:
            l0, l1 = _np.ones_like(rho), 1 + a - rho
            for j in range(1, kk):
                l0, l1 = l1, ((2 * j + 1 + a - rho) * l1 - (j + a) * l0) / (j + 1)
            lg = l1
        return N * _np.exp(-rho / 2) * rho ** l * lg * f(x, y, z, r)

    v = psi((g.random((3, 30000)) * 2 - 1) * L)
    mx = float((v * v).max()) * 1.25
    pts, tries = [], 0
    while len(pts) < npts and tries < 3e6:
        B = int(min(200000, 3e6 - tries))
        P = (g.random((3, B)) * 2 - 1) * L
        v = psi(P)
        acc = _np.nonzero(g.random(B) * mx < v * v)[0]
        need = npts - len(pts)
        if len(acc) >= need:
            acc = acc[:need]
            tries += int(acc[-1]) + 1
        else:
            tries += B
        for i in acc:
            pts.append([float(P[0, i]), float(P[1, i]), float(P[2, i]), 1 if v[i] > 0 else -1])
    return {"L": L, "pts": pts, "tries": tries}


def cloud(n: int, k: int, Z: int, seed: int, npts: int = 5000) -> dict:
    """Rejection sampling of |psi|^2 (v1.0 sample(); random numbers from a seeded generator)."""
    if _np is not None:
        return _cloud_np(n, k, Z, seed, npts)
    L = extent(n, Z) * 0.9
    psi = _psi_fn(n, k, Z)
    rnd = random.Random(seed)
    u = rnd.random
    mx = 0
    for _ in range(30000):
        v = psi((u() * 2 - 1) * L, (u() * 2 - 1) * L, (u() * 2 - 1) * L)
        mx = max(mx, v * v)
    mx *= 1.25
    pts = []
    tries = 0
    while len(pts) < npts and tries < 3e6:
        tries += 1
        x, y, z = (u() * 2 - 1) * L, (u() * 2 - 1) * L, (u() * 2 - 1) * L
        v = psi(x, y, z)
        if u() * mx < v * v:
            pts.append([x, y, z, 1 if v > 0 else -1])
    return {"L": L, "pts": pts, "tries": tries}


# 2.10.0: the level energies use the same reduced-mass Rydberg constant as the lines (H: series limit
# 13.598 eV instead of 13.6057 eV for an infinitely heavy nucleus), so the diagram and the table of
# lines agree.  LEVEL_MASS = "infinite" reproduces v1.0 / Atlas 0.80.
LEVEL_MASS = "reduced"
CM_EV = 1.239841984e-4      # eV per cm^-1 (CODATA 2018)


def _ry_ev(Z):
    return RYD[Z] * CM_EV if LEVEL_MASS == "reduced" else 13.6057


def levels(Z: int, series: int) -> dict:
    RH = RYD[Z]
    ry = _ry_ev(Z)
    lev = [-ry * Z * Z / (k * k) for k in range(1, 8)]
    rows = []
    for n2 in range(series + 1, series + 7):
        nu = RH * Z * Z * (1 / (series * series) - 1 / (n2 * n2))
        rows.append([n2, nu, 1e7 / nu])
    nu_edge = RH * Z * Z / (series * series)
    return {"lev": lev, "e1": -ry * Z * Z / (series * series), "rows": rows,
            "rowsE": [-ry * Z * Z / (n2 * n2) for n2, _, _ in rows], "edge": [nu_edge, 1e7 / nu_edge]}


def quiz(n: int, k: int) -> dict:
    l = ORB[k][1]
    return {"nr": n - l - 1, "l": l, "E": -_ry_ev(1) / (n * n)}
