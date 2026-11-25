"""Two electrons in a box: Pauli principle, exchange (Fermi) hole, J and K, Coulomb hole from 2x2 CI.

HEADER
    Model of the page "Принцип Паули и обменная дырка" (v1.0 pauli.js:
    phi, psi, dens, conditional, JK, ciInts, ciH, ciE, ciOpt, ciPsi,
    drawMap, drawCICond, drawCIE).  Wilkinson convention, sections 1-8.
    Reduced units: box length 1, hbar = m = 1.

§1 THEORY
    Orbitals of the box [0, 1]: phi_n(x) = sqrt2 sin(n pi x), energy
    n^2 pi^2 / 2.  With A = phi_a(x1) phi_b(x2), B = phi_b(x1) phi_a(x2)
    the spatial parts are: Hartree product A; triplet (A - B)/sqrt2;
    singlet and bosons (A + B)/sqrt2 (A if a = b); single determinant
    |phi_a alpha, phi_b beta|, component alpha(1)beta(2): A/sqrt2 with the
    spin-summed density (A^2 + B^2)/2.  Conditional density of electron 2
    given electron 1 at x1: c(x2) = rho2(x1, x2) / int rho2(x1, x) dx; the
    hole is c minus the reference density (rho_sigma of the same spin, the
    density of the other spin for the determinant, the density without
    permutations for the M_S = 0 triplet); for the same-spin triplet
    int hole = -1 (Fermi hole).
    Interaction: soft Coulomb 1/sqrt((x1 - x2)^2 + d^2), d = 0.05;
    J_ab = <ab|ab>, K_ab = <ab|ba>; energies of the interaction part:
    triplet J - K, Hartree and determinant J, singlet/bosons J + K (J if
    a = b).
    Coulomb hole: CI of the configurations phi1^2 and phi2^2 with strength
    lambda: H11 = 2 E1 + lambda J11, H22 = 8 E1 + lambda J22,
    H12 = lambda K12, E1 = pi^2/2; E(theta) = c^2 H11 + s^2 H22 + 2 c s H12,
    minimum theta* = atan2(-2 H12, H22 - H11)/2.

§2 ALGORITHM
    As v1.0: maps on R x R pixel centres (R = 120; 110 for the CI map),
    x2 from top; trapezoid rule on NG = 301 points for the normalisations;
    J, K by the midpoint rule on NE = 181 points.  Orbital values at the
    grid points are computed once and reused (the same doubles as v1.0's
    repeated calls).

§3 APPLICATIONS
    Endpoints pauli.map, pauli.cond, pauli.orbs, pauli.energy, pauli.cimap,
    pauli.ci.

§4 SPECIFICATION
    Modes H, T, S, D, B; a, b in 1..4; ms in -1, 0, 1; x1 in [0, 1];
    theta in degrees [-45, 45]; lambda in [0.5, 8].  Maps are returned as
    float64 little-endian in base64.  Tier: bitwise vs v1.0 on Linux/glibc
    (EXACT).

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    JS x**2 is x*x (V8); Math.sin/cos are the glibc ports of jsmath.
§7 TEST CASES (tests/test_pauli.py)
    Orbitals orthonormal (trapezoid, 1e-12); triplet psi antisymmetric and
    zero on the diagonal; singlet symmetric; int c = 1; same-spin triplet
    hole integral = -1 to 1e-3 (finite grid); K_aa = J_aa; J, K against an
    independent Gauss-Legendre quadrature (1e-3 relative, the midpoint
    rule is O(h^2) for the cusp-free kernel); CI minimum against the
    eigenvalue of the 2x2 matrix (1e-12) and below E(0); vs v1.0.
§8 ERROR ANALYSIS
    Discretisation: trapezoid on a 1/300 grid (error O(h^2) ~ 1e-5 for the
    normalisation), midpoint 1/181 for J, K (relative ~1e-3, the kernel has
    curvature scale d = 0.05 ~ 9 h).  The page shows 2-3 decimals.
"""
from __future__ import annotations

import base64
import math
import struct

from .jsmath import atan2, cos, js_round, sin

SQRT2 = math.sqrt(2)
PI = math.pi
NG = 301
XS = [i / (NG - 1) for i in range(NG)]
DX = 1 / (NG - 1)
D2 = 0.05 * 0.05
NE = 181
E1 = PI * PI / 2
MODES = ("H", "T", "S", "D", "B")


def phi(n: int, x: float) -> float:
    return SQRT2 * sin(n * PI * x)


def integ(f) -> float:
    s = 0
    for i in range(NG):
        s += f[i] * (0.5 if i == 0 or i == NG - 1 else 1)
    return s * DX


def _psi(mode, a, b, pa1, pb2, pb1, pa2):
    A, B = pa1 * pb2, pb1 * pa2
    if mode == "H":
        return A
    if mode == "T":
        return (A - B) / SQRT2
    if mode == "D":
        return A / SQRT2
    return A if a == b else (A + B) / SQRT2


def _dens(mode, a, b, pa1, pb2, pb1, pa2):
    A, B = pa1 * pb2, pb1 * pa2
    if mode == "H":
        return A * A
    if mode == "T":
        return (A - B) * (A - B) / 2
    if mode == "D":
        return (A * A + B * B) / 2
    return A * A if a == b else (A + B) * (A + B) / 2


def _f64(vals) -> str:
    return base64.b64encode(struct.pack(f"<{len(vals)}d", *vals)).decode("ascii")


def grid_map(mode: str, a: int, b: int, view: str, R: int = 120) -> dict:
    """|psi|^2 (view P) or psi (view W) at the R x R pixel centres, row-major, x2 from the top."""
    f = _dens if view == "P" else _psi
    c1 = [(i + .5) / R for i in range(R)]
    c2 = [1 - (j + .5) / R for j in range(R)]
    a1, b1 = [phi(a, x) for x in c1], [phi(b, x) for x in c1]
    a2, b2 = [phi(a, x) for x in c2], [phi(b, x) for x in c2]
    vals = []
    mx = 0
    for j in range(R):
        for i in range(R):
            v = f(mode, a, b, a1[i], b2[j], b1[i], a2[j])
            vals.append(v)
            mx = max(mx, abs(v))
    return {"R": R, "mx": mx, "f64": _f64(vals)}


def _tab(n):
    return [phi(n, x) for x in XS]


def conditional(mode: str, a: int, b: int, ms: int, x1: float):
    """Conditional density c(x2), reference density, hole and its integral (None: triplet with a = b)."""
    pa, pb = _tab(a), _tab(b)
    sqa, sqb = [v * v for v in pa], [v * v for v in pb]
    pa1, pb1 = phi(a, x1), phi(b, x1)

    def raw():
        return [_dens(mode, a, b, pa1, pb[i], pb1, pa[i]) for i in range(NG)]
    kind = None
    if mode == "H":
        c = sqb
        ref = [sqa[i] + sqb[i] for i in range(NG)]
    elif mode == "T":
        if a == b:
            return None
        r = raw()
        n = integ(r)
        c = [v / n if n > 1e-12 else 0 for v in r]
        if ms:
            ref = [sqa[i] + sqb[i] for i in range(NG)]
        else:
            ref = [(sqa[i] + sqb[i]) / 2 for i in range(NG)]
        kind = "spin" if ms else "noperm"
    elif mode == "D":
        c = sqb
        ref = list(c)
    elif mode == "B":
        r = raw()
        n = integ(r)
        c = [v / n for v in r]
        ref = [sqa[i] + sqb[i] for i in range(NG)]
    else:
        r = raw()
        n = integ(r)
        c = [v / n for v in r]
        ref = [sqa[i] if a == b else (sqa[i] + sqb[i]) / 2 for i in range(NG)]
    h = [v - ref[i] for i, v in enumerate(c)]
    return {"c": c, "ref": ref, "h": h, "hint": integ(h), "c0": c[int(js_round(x1 * (NG - 1)))], "kind": kind}


def orbs(a: int, b: int) -> dict:
    return {"pa": _tab(a), "pb": _tab(b)}


_JK: dict = {}


def JK(a: int, b: int) -> dict:
    k = (a, b)
    if k not in _JK:
        J = K = 0
        xs = [(i + .5) / NE for i in range(NE)]
        w = 1 / NE
        pa, pb = [phi(a, x) for x in xs], [phi(b, x) for x in xs]
        for i in range(NE):
            for j in range(NE):
                d = xs[i] - xs[j]
                v = 1 / math.sqrt(d * d + D2)
                J += pa[i] * pa[i] * pb[j] * pb[j] * v
                K += pa[i] * pb[i] * pa[j] * pb[j] * v
        _JK[k] = {"J": J * w * w, "K": K * w * w}
    return _JK[k]


def energy(a: int, b: int) -> dict:
    """J, K and the interaction energies of the five states (None: triplet forbidden), max for the bars."""
    jk = JK(a, b)
    J, K = jk["J"], jk["K"]
    same = a == b
    rows = [["T", None if same else J - K], ["H", J], ["D", J], ["S", J if same else J + K], ["B", J if same else J + K]]
    return {"J": J, "K": K, "rows": rows, "mx": max(r[1] or 0 for r in rows), "K2": 2 * K}


# ---------- Coulomb hole: 2x2 CI ----------

def ci_h(lam: float):
    J11, J22, K12 = JK(1, 1)["J"], JK(2, 2)["J"], JK(1, 2)["K"]
    return 2 * E1 + lam * J11, 2 * 4 * E1 + lam * J22, lam * K12


def ci_e(th: float, lam: float) -> float:
    H11, H22, H12 = ci_h(lam)
    c, s = cos(th), sin(th)
    return c * c * H11 + s * s * H22 + 2 * c * s * H12


def ci_opt(lam: float) -> float:
    H11, H22, H12 = ci_h(lam)
    return 0.5 * atan2(-2 * H12, H22 - H11)


def _ci_cs(thdeg):
    t = thdeg * PI / 180
    return cos(t), sin(t)


def ci_map(thdeg: float, R: int = 110) -> dict:
    c, s = _ci_cs(thdeg)
    xs1 = [(i + .5) / R for i in range(R)]
    xs2 = [1 - (j + .5) / R for j in range(R)]
    p11, p21 = [phi(1, x) for x in xs1], [phi(2, x) for x in xs1]
    p12, p22 = [phi(1, x) for x in xs2], [phi(2, x) for x in xs2]
    vals = []
    mx = 0
    for j in range(R):
        for i in range(R):
            v = c * p11[i] * p12[j] + s * p21[i] * p22[j]
            v = v * v
            vals.append(v)
            mx = max(mx, v)
    return {"R": R, "mx": mx, "f64": _f64(vals)}


def ci(thdeg: float, lam: float, x1: float) -> dict:
    """Conditional density, hole depth at x1, energy curve and the CI minimum."""
    c_, s_ = _ci_cs(thdeg)
    p1, p2 = _tab(1), _tab(2)
    q1, q2 = phi(1, x1), phi(2, x1)
    raw = []
    for i in range(NG):
        v = c_ * q1 * p1[i] + s_ * q2 * p2[i]
        raw.append(v * v)
    n = integ(raw)
    c = [q / n for q in raw]
    marg = []
    for i in range(NG):
        r = []
        for k in range(NG):
            v = c_ * p1[i] * p1[k] + s_ * p2[i] * p2[k]
            r.append(v * v)
        marg.append(integ(r))
    nm = integ(marg)
    ref = [q / nm for q in marg]
    h = [q - ref[i] for i, q in enumerate(c)]
    i0 = int(js_round(x1 * (NG - 1)))
    dep = 1 - c[i0] / ref[i0] if ref[i0] > 1e-9 else 0
    ths = [-45 + i * 0.5 for i in range(181)]
    Es = [ci_e(t * PI / 180, lam) for t in ths]
    to = ci_opt(lam)
    tod = to * 180 / PI
    t = thdeg * PI / 180
    return {"c": c, "ref": ref, "h": h, "dep": dep, "Es": Es, "lo": min(Es), "hi": max(Es), "toDeg": tod,
            "Eto": ci_e(tod * PI / 180, lam), "Eth": ci_e(thdeg * PI / 180, lam), "to": to,
            "c1": cos(t), "c2": sin(t), "E": ci_e(t, lam), "E0": ci_e(0, lam), "Em": ci_e(to, lam),
            "atMin": abs(t - to) < 0.005}
