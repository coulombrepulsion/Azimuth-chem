"""Potential energy surface of collinear H + H2 (LEPS), reaction path,
stationary points, trajectories, isotope effects and an avoided crossing.

HEADER
    Numerical model of the Atlas page "Potential energy surface"
    (web/<lang>/pes.html).  Port of leps, grad, hess, eig2, the TS search,
    IRC, zpePerp, analyse, descend, newton, runTraj, the Wigner/ZPE table
    and the Landau-Zener section of v1.0.  Wilkinson convention, §1-§8.

§1 THEORY
    LEPS surface (London-Eyring-Polanyi-Sato) for three H atoms on a line,
    r1 = r(HA-HB), r2 = r(HB-HC), r3 = r1 + r2 (angstrom, eV):
        E = [Q1 + Q2 + Q3 - sqrt(((J1-J2)^2 + (J2-J3)^2 + (J3-J1)^2)/2)]/(1+k) + D
    with Morse-derived Coulomb and exchange integrals (x = e^{-b (r - r0)})
        Q = D/4 [(3 + k) x^2 - (2 + 6k) x],  J = D/4 [(1 + 3k) x^2 - (6 + 2k) x],
    D = 4.746 eV, b = 1.942 A^-1, r0 = 0.742 A, Sato parameter k = 0.14;
    the energy origin is shifted by +D so that H + H2 (r1 -> inf, r2 = r0)
    is at 0.  Masses 1.008 (H), 2.014 (D) u.
    Derivatives by central differences: gradient step h = 1e-5 A,
    Hessian h = 1e-4 A (mixed derivative by the 4-point formula).
    Vibrational analysis: with equal masses m, the kinetic metric in
    (r1, r2) is G/m, G = [[2, -1], [-1, 2]]; frequencies are the
    eigenvalues of G H / m converted to cm^-1 by 521.5 sqrt(|lambda|/m)
    (lambda in eV/A^2/u); a negative eigenvalue is an imaginary frequency.
    Transition state: the minimum of E along r1 = r2 (symmetric saddle),
    located on a 1e-5-A grid.  IRC: steepest descent in the metric G from
    TS +- 0.004 A along the negative-curvature eigenvector, adaptive step
    (halved when the direction turns by more than acos 0.9, else grown 10 %
    up to 0.004 A), until |grad|_G < 2e-3 or a bond exceeds 3.05 A.
    Zero-point energy perpendicular to the path: the Cartesian Hessian of
    the 3 atoms projected onto the complement of the path tangent and of
    the centre-of-mass translation, ZPE = (1/2) h nu (one mode).
    Classical dynamics: velocity Verlet, dt = 0.05 fs, units u, A, fs, eV
    (a = 0.009648 F/m, KE = 103.64 m v^2/2); the molecule optionally starts
    with its zero-point vibrational energy at a given phase.
    Kinetic isotope effect: effective barriers V + ZPE(TS) - ZPE(reactants)
    and the Wigner tunnelling factor kappa = 1 + (h nu^\\ddagger / kT)^2 / 24.
    Avoided crossing Na + Cl: covalent 40 e^{-R/0.45}, ionic
    1.53 - 14.40/R + 1319 e^{-R/0.32} (eV, A), adiabatic energies
    (a + b)/2 -+ sqrt(((b - a)/2)^2 + V^2), crossing R_c = 14.40/1.53;
    Landau-Zener P = exp(-2 pi V^2 / (hbar v |Delta F|)), |Delta F| =
    14.40 / R_c^2.

§2 ALGORITHM
    As in §1; all loops, step rules, thresholds and grids are those of
    v1.0 (listed in the functions below).

§3 APPLICATIONS
    Map of the surface with contours, the IRC and the TS; analysis of any
    point (gradient, curvatures, frequencies, classification); gradient
    descent ending in a valley -- or in the TS when started on r1 = r2;
    Newton's method converging to whichever stationary point is near;
    reactive and non-reactive trajectories and their dependence on the
    vibrational phase; ZPE-corrected barriers, KIE and tunnelling; the
    Born-Oppenheimer breakdown at an avoided crossing.

§4 SPECIFICATION
    E(r1, r2) -> eV.  iso in {"H", "D"}.
    static() -> {TS: {r, E}, IRC: [arr, arr] (arr = [{r1, r2, s, E}]),
        PATH: [{r1, r2, s, E, zH, zD}], ZR: {H, D}, iTS, BAR: {H, D},
        NUI: {H, D}, EZPE: {H, D}, map: {N: 180, E: [N*N] (row j = r2 from R1 down)},
        cont: {M: 140, E: [(M+1)^2] (row j = r2 from R0 up)}}.
    analyse(r1, r2, iso) -> {e, g, gn, ev: [{l, v}], fr: [l], wn: [nu
        cm^-1, signed: negative = imaginary], nneg, kind in {"valley",
        "min", "ts", "saddle2", "slope"}}.
    descend(r1, r2, iso) -> {trail, p, a: analyse(p), edge: bool}.
    newton(r1, r2, iso) -> {trail, ok, r, a or None, away: bool}.
    trajectory(Ecol, vib, phase, iso) -> {frames: [{t, r1, r2}], react,
        Ezpe}.  series(Ecol, iso) -> {react: [24 bools]}.
    kie(T) -> {kH, kD, ratio}.  lz(lv, v) -> {V, full/zoom curves, dF,
        P, P2}.
    Reference: v1.0 pes.html.  Equivalence tier ``bound`` (§8).

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    * static() costs ~3 s in CPython (30 000 energies for the TS, two IRC
      branches of up to 20 000 steps, the 180^2 map and the 141^2 contour
      grid) and is memoised.
    * The finite-difference steps and all thresholds are kept from v1.0;
      the Hessian by differences with h = 1e-4 has rounding noise
      ~ eps |E| / h^2 ~ 1e-7 eV/A^2 -- irrelevant for the page, but it is
      the dominant source of differences between implementations (§8).
§7 TEST CASES (tests/test_pes.py)
    * Asymptote: E(10, r0) = 0 to 1e-12 (H + H2 at the origin); the
      Morse limit E(10, 10) = D = 4.746 eV (three free atoms).
    * Symmetry E(r1, r2) = E(r2, r1) exactly (the formula is symmetric).
    * TS on the diagonal with exactly one negative eigenvalue of G H,
      barrier ~0.4 eV (classic LEPS for H3 with k = 0.14).
    * Analytic gradient (differentiating Q, J) vs the finite differences:
      agreement within h^2 |E'''|/6 + eps |E|/h (§8).
    * Energy conservation of the Verlet trajectory: |Delta E_tot| < 1e-3 eV
      over 400 fs (second-order integrator, dt = 0.05 fs).
    * Differential test against the v1.0 JavaScript with the bounds of §8.
§8 ERROR ANALYSIS
    E: ~10 operations with two exp and one sqrt per call: relative
    difference between implementations <= ~1e-15 (2-3 ulp of |E| <= 5).
    Gradient by differences: difference (f(r+h) - f(r-h))/(2h) carries the
    E-noise divided by h: <= 2 * 5e-15 / 2e-5 = 5e-10 eV/A.
    Hessian: noise 4 * 5e-15 / 1e-8 = 2e-6 eV/A^2 (diagonal), similar for
    the mixed term; eigenvalues inherit it (well separated), eigenvectors
    tilt by noise/gap ~ 1e-7.  Frequencies: relative 1e-7.
    Iterations (IRC, descent, Newton, Verlet): every step uses gradients
    with the 5e-10 noise; descent and IRC are contractive transversally,
    and step-size decisions (dot product < 0.9, norm < 2e-3) flip only at
    near-ties; trajectories (Verlet) are chaotic only near the TS ridge.
    The tests therefore compare: E and static grids at 1e-12 relative;
    gradients 1e-8; Hessians and curvatures 1e-4 (absolute, eV/A^2);
    frequencies 0.05 cm^-1; iterated paths at 1e-6 A; trajectory frames at
    1e-4 A, with the reaction outcome identical.
"""
from __future__ import annotations

import functools
import math

from .jsmath import cos, exp, js_hypot, js_pow, sin, sq

LP = {"D": 4.746, "b": 1.942, "r0": 0.742}
SATO, DE = 0.14, 4.746
MISO = {"H": 1.008, "D": 2.014}
G = [[2, -1], [-1, 2]]
R0, R1 = 0.5, 3.0
AC, KE = 0.009648, 103.64
RC = 14.40 / 1.53


# ------------------------------------------------------------------ surface
def leps(r1, r2, k):
    D, b, r0 = LP["D"], LP["b"], LP["r0"]

    def QJ(r):
        e1 = exp(-b * (r - r0))
        e2 = e1 * e1
        return D / 4 * ((3 + k) * e2 - (2 + 6 * k) * e1), D / 4 * ((1 + 3 * k) * e2 - (6 + 2 * k) * e1)
    Q1, J1 = QJ(r1)
    Q2, J2 = QJ(r2)
    Q3, J3 = QJ(r1 + r2)
    return (Q1 + Q2 + Q3 - math.sqrt(0.5 * (sq(J1 - J2) + sq(J2 - J3) + sq(J3 - J1)))) / (1 + k)


def E(r1, r2):
    return leps(r1, r2, SATO) + DE


def grad(f, r1, r2, h=1e-5):
    return [(f(r1 + h, r2) - f(r1 - h, r2)) / (2 * h), (f(r1, r2 + h) - f(r1, r2 - h)) / (2 * h)]


def hess(f, r1, r2, h=1e-4):
    a = (f(r1 + h, r2) - 2 * f(r1, r2) + f(r1 - h, r2)) / h / h
    c = (f(r1, r2 + h) - 2 * f(r1, r2) + f(r1, r2 - h)) / h / h
    b = (f(r1 + h, r2 + h) - f(r1 + h, r2 - h) - f(r1 - h, r2 + h) + f(r1 - h, r2 - h)) / (4 * h * h)
    return [[a, b], [b, c]]


def gradE(r1, r2):
    return grad(E, r1, r2)


def hessE(r1, r2):
    return hess(E, r1, r2)


def eig2(A):
    """Eigenpairs of a 2x2 matrix (closed form; larger eigenvalue first)."""
    tr = A[0][0] + A[1][1]
    dt = A[0][0] * A[1][1] - A[0][1] * A[1][0]
    d = math.sqrt(max(0.0, tr * tr / 4 - dt))
    ls = [tr / 2 + d, tr / 2 - d]

    def vec(lam):
        if abs(A[0][1]) > 1e-12:
            v = [A[0][1], lam - A[0][0]]
        elif abs(A[1][0]) > 1e-12:
            v = [lam - A[1][1], A[1][0]]
        else:
            v = [1, 0] if abs(A[0][0] - lam) < abs(A[1][1] - lam) else [0, 1]
        n = js_hypot(*v)
        return [x / n for x in v]
    return [{"l": x, "v": vec(x)} for x in ls]


def mm2(A, B):
    return [[A[0][0] * B[0][0] + A[0][1] * B[1][0], A[0][0] * B[0][1] + A[0][1] * B[1][1]],
            [A[1][0] * B[0][0] + A[1][1] * B[1][0], A[1][0] * B[0][1] + A[1][1] * B[1][1]]]


def wn(l, m):
    """Signed frequency (cm^-1) of a G H eigenvalue; negative = imaginary."""
    v = 521.5 * math.sqrt(abs(l) / m)
    return -v if l < 0 else v


# ------------------------------------------------------------------ static data
def _ts():
    b = [0.0, 1e9]
    r = 0.8
    while r < 1.1:
        e = E(r, r)
        if e < b[1]:
            b = [r, e]
        r += 1e-5
    return {"r": b[0], "E": b[1]}


def _irc(TS):
    GH = mm2(G, hessE(TS["r"], TS["r"]))
    neg = next(x for x in eig2(GH) if x["l"] < 0)["v"]
    out = []
    for sg in (1, -1):
        r = [TS["r"] + sg * 0.004 * neg[0], TS["r"] + sg * 0.004 * neg[1]]
        s = 0.0
        arr = [{"r1": TS["r"], "r2": TS["r"], "s": 0.0, "E": TS["E"]}]
        prev = None
        h = 0.004
        for i in range(20000):
            g = gradE(*r)
            Gg = [G[0][0] * g[0] + G[0][1] * g[1], G[1][0] * g[0] + G[1][1] * g[1]]
            n = math.sqrt(g[0] * Gg[0] + g[1] * Gg[1])
            if n < 2e-3:
                break
            d = [Gg[0] / n, Gg[1] / n]
            if prev and d[0] * prev[0] + d[1] * prev[1] < 0.9:
                h = max(h / 2, 2e-4)
            else:
                h = min(h * 1.1, 0.004)
            prev = d
            r = [r[0] - d[0] * h, r[1] - d[1] * h]
            s += h
            if i % 2 == 0:
                arr.append({"r1": r[0], "r2": r[1], "s": sg * s, "E": E(*r)})
            if r[0] > 3.05 or r[1] > 3.05:
                break
        out.append(arr)
    return out


def zpe_perp(r1, r2, dr, m):
    """Zero-point energy (eV) of the vibration perpendicular to the path direction dr."""
    H = hessE(r1, r2)
    B = [[-1, 1, 0], [0, -1, 1]]
    Hx = [[B[0][i] * (H[0][0] * B[0][j] + H[0][1] * B[1][j]) + B[1][i] * (H[1][0] * B[0][j] + H[1][1] * B[1][j])
           for j in range(3)] for i in range(3)]
    Gi = [[2 / 3, 1 / 3], [1 / 3, 2 / 3]]
    a = [Gi[0][0] * dr[0] + Gi[0][1] * dr[1], Gi[1][0] * dr[0] + Gi[1][1] * dr[1]]
    t = [B[0][i] * a[0] + B[1][i] * a[1] for i in range(3)]
    tn = js_hypot(*t)
    t = [x / tn for x in t]
    c = [x / math.sqrt(3) for x in (1, 1, 1)]
    P = [[(1 if i == j else 0) - t[i] * t[j] - c[i] * c[j] for j in range(3)] for i in range(3)]
    tr = 0.0
    for i in range(3):
        for j in range(3):
            for k in range(3):
                tr += P[i][j] * Hx[j][k] * P[k][i]
    lam = max(0.0, tr / m)
    return 0.5 * 521.5 * math.sqrt(lam) * 1.23984e-4


@functools.lru_cache(maxsize=1)
def static() -> dict:
    """TS, IRC, path with ZPE, barriers, map and contour grids (see §4)."""
    TS = _ts()
    IRC = _irc(TS)
    pts = list(reversed(IRC[1])) + IRC[0][1:]
    PATH = []
    for i, p in enumerate(pts):
        a, b = pts[max(0, i - 8)], pts[min(len(pts) - 1, i + 8)]
        dr = [b["r1"] - a["r1"], b["r2"] - a["r2"]]
        PATH.append(dict(p, zH=zpe_perp(p["r1"], p["r2"], dr, MISO["H"]), zD=zpe_perp(p["r1"], p["r2"], dr, MISO["D"])))
    ZR = {"H": PATH[0]["zH"], "D": PATH[0]["zD"]}
    iTS = next(i for i, p in enumerate(PATH) if p["s"] == 0)
    BAR = {"H": TS["E"] + PATH[iTS]["zH"] - ZR["H"], "D": TS["E"] + PATH[iTS]["zD"] - ZR["D"]}
    lneg = next(x for x in eig2(mm2(G, hessE(TS["r"], TS["r"]))) if x["l"] < 0)["l"]
    NUI = {k: _jsround(521.5 * math.sqrt(abs(lneg) / MISO[k])) for k in ("H", "D")}
    N = 180
    grid = [E(R0 + (i + .5) / N * (R1 - R0), R1 - (j + .5) / N * (R1 - R0)) for j in range(N) for i in range(N)]
    M = 140
    cont = [E(R0 + i / M * (R1 - R0), R0 + j / M * (R1 - R0)) for j in range(M + 1) for i in range(M + 1)]
    return {"TS": TS, "IRC": IRC, "PATH": PATH, "ZR": ZR, "iTS": iTS, "BAR": BAR, "NUI": NUI,
            "EZPE": {k: _ezpe(MISO[k]) for k in ("H", "D")},
            "map": {"N": N, "E": grid}, "cont": {"M": M, "E": cont}}


def _ezpe(m):
    """Zero-point energy of the harmonic H2/D2 used to start trajectories (eV)."""
    kf = 2 * DE * 1.942 * 1.942
    w = math.sqrt(kf * AC / (m / 2))
    return 0.5 * w * 0.6582 / 1


def _jsround(x):
    from .jsmath import js_round
    return int(js_round(x))


# ------------------------------------------------------------------ point analysis
def analyse(r1, r2, iso) -> dict:
    """Energy, gradient, curvatures, frequencies and the kind of point."""
    e = E(r1, r2)
    g = gradE(r1, r2)
    gn = js_hypot(*g)
    H = hessE(r1, r2)
    ev = eig2(H)
    fr = [x["l"] for x in eig2(mm2(G, H))]
    nneg = sum(1 for x in ev if x["l"] < 0)
    if gn < 0.03:
        if nneg == 0 and min(x["l"] for x in ev) < 1.5 and max(r1, r2) > 1.8:
            kind = "valley"
        elif nneg == 0:
            kind = "min"
        elif nneg == 1:
            kind = "ts"
        else:
            kind = "saddle2"
    else:
        kind = "slope"
    return {"r1": r1, "r2": r2, "e": e, "g": g, "gn": gn, "ev": ev, "fr": fr,
            "wn": [wn(l, MISO[iso]) for l in fr], "nneg": nneg, "kind": kind}


def descend(r1, r2, iso) -> dict:
    """Steepest descent with the page's step rule (see v1.0 descend)."""
    r = [r1, r2]
    tr = [list(r)]
    n = 0
    while n < 6000:
        g = gradE(*r)
        gn = js_hypot(*g)
        if gn < 2e-3:
            break
        st = min(0.004, 0.004 * gn / 2 + 0.0005) / max(gn, 1e-9)
        r = [r[0] - st * g[0], r[1] - st * g[1]]
        if n % 6 == 0:
            tr.append(list(r))
        if r[0] > R1 or r[1] > R1 or r[0] < R0 or r[1] < R0:
            break
        n += 1
    tr.append(list(r))
    p = [min(R1 - 0.01, max(R0, r[0])), min(R1 - 0.01, max(R0, r[1]))]
    return {"trail": tr, "r": r, "p": p, "a": analyse(p[0], p[1], iso), "edge": r[0] >= R1 or r[1] >= R1}


def newton(r1, r2, iso) -> dict:
    """Newton steps -H^-1 grad (capped at 0.3 A) to a stationary point."""
    r = [r1, r2]
    tr = [list(r)]
    ok = False
    for _ in range(40):
        g, H = gradE(*r), hessE(*r)
        dt = H[0][0] * H[1][1] - H[0][1] * H[1][0]
        if abs(dt) < 1e-9:
            break
        d = [(H[1][1] * g[0] - H[0][1] * g[1]) / dt, (-H[1][0] * g[0] + H[0][0] * g[1]) / dt]
        dn = js_hypot(*d)
        if dn > 0.3:
            d = [x * 0.3 / dn for x in d]
        r = [r[0] - d[0], r[1] - d[1]]
        tr.append(list(r))
        if js_hypot(*gradE(*r)) < 1e-4:
            ok = True
            break
        if r[0] < 0.4 or r[1] < 0.4 or r[0] > 4 or r[1] > 4:
            break
    inside = ok and R0 <= r[0] <= R1 and R0 <= r[1] <= R1
    return {"trail": tr, "ok": inside, "r": r, "a": analyse(r[0], r[1], iso) if inside else None,
            "away": r[0] > R1 or r[1] > R1}


# ------------------------------------------------------------------ dynamics
def trajectory(Ecol, vib, phase, iso) -> dict:
    """Collinear A + BC collision by velocity Verlet (units u, A, fs, eV)."""
    m = MISO[iso]
    r0, kf = 0.742, 2 * DE * 1.942 * 1.942
    mu2 = m / 2
    w = math.sqrt(kf * AC / mu2)
    Ezpe = 0.5 * w * 0.6582 / 1
    A = math.sqrt(2 * Ezpe / kf) if vib else 0
    ph = phase * math.pi / 180
    r2 = r0 + A * cos(ph)
    dr2 = -A * w * sin(ph)
    mu = 2 * m / 3
    vrel = math.sqrt(2 * Ecol / (mu * KE))
    x = [-3.0, 0, r2]
    x[0] = x[1] - 3.0
    v = [vrel * 2 / 3, -vrel / 3 - dr2 / 2, -vrel / 3 + dr2 / 2]
    frames = []
    dt = 0.05

    def force(x):
        r1, r2 = x[1] - x[0], x[2] - x[1]
        g = gradE(r1, r2)
        return [g[0], -g[0] + g[1], -g[1]]
    F = force(x)
    t = 0.0
    while t <= 400:
        if _jsround(t / dt) % 10 == 0:
            frames.append({"t": t, "r1": x[1] - x[0], "r2": x[2] - x[1]})
        v = [q + 0.5 * dt * AC * F[i] / m for i, q in enumerate(v)]
        x = [q + dt * v[i] for i, q in enumerate(x)]
        F = force(x)
        v = [q + 0.5 * dt * AC * F[i] / m for i, q in enumerate(v)]
        r1, r2 = x[1] - x[0], x[2] - x[1]
        if (r1 > 3.2 or r2 > 3.2) and t > 20:
            break
        t += dt
    last = frames[-1]
    return {"frames": frames, "react": last["r2"] > last["r1"], "Ezpe": Ezpe}


def series(Ecol, iso) -> dict:
    return {"react": [trajectory(Ecol, True, p, iso)["react"] for p in range(0, 360, 15)]}


def kie(T: float) -> dict:
    """Wigner tunnelling factors and the ZPE barrier ratio at temperature T."""
    st = static()
    kT = 8.617e-5 * T
    k = {}
    for i in ("H", "D"):
        u = st["NUI"][i] * 1.23984e-4 / kT
        k[i] = 1 + u * u / 24
    return {"kH": k["H"], "kD": k["D"], "ratio": exp((st["BAR"]["D"] - st["BAR"]["H"]) / kT)}


# ------------------------------------------------------------------ avoided crossing
def Ecov(R):
    return 40 * exp(-R / 0.45)


def Eion(R):
    return 1.53 - 14.40 / R + 1319 * exp(-R / 0.32)


def adi(R, V):
    a, b = Ecov(R), Eion(R)
    m = (a + b) / 2
    d = math.sqrt(sq((b - a) / 2) + V * V)
    return [m - d, m + d]


def lz(lv: float, v: float) -> dict:
    """Diabatic/adiabatic curves and Landau-Zener probabilities."""
    V = js_pow(10, lv)

    def curves(Ra, Rb):
        Rs = [Ra + (Rb - Ra) * i / 399 for i in range(400)]
        ad = [adi(R, V) for R in Rs]
        return {"cov": [Ecov(R) for R in Rs], "ion": [Eion(R) for R in Rs], "lo": [a[0] for a in ad], "hi": [a[1] for a in ad]}
    dF = 14.40 / RC / RC
    P = exp(-2 * math.pi * V * V / (6.582e-16 * v * 1e10 * dF))
    return {"V": V, "RC": RC, "full": curves(1.5, 14), "zoom": curves(RC - 1.2, RC + 1.2), "dF": dF, "P": P,
            "P2": 2 * P * (1 - P)}
