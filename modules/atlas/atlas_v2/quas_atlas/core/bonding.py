"""Orbital analysis of the chemical bond: localization as a rotation of orbitals, hybridization from the bond angle,
the donor–acceptor energy E(2) of NBO and the reduced density gradient of NCI.

HEADER
    Model of the page "Связь глазами орбиталей: локализация, NBO, NCI" (web/<lang>/bonding.html), Atlas 2026-11-24;
    lecture 11 of the course «Квантово-химические методы» (derivations 4, 5, 6, 10). Wilkinson convention, §1-8.

§1 THEORY
    A rotation φ1′ = cosθ φ1 + sinθ φ2, φ2′ = −sinθ φ1 + cosθ φ2 of two occupied orbitals multiplies the determinant by
    cos²θ + sin²θ = 1: the energy and the density do not change, but F̂φ′ ≠ εφ′ (the off-diagonal ⟨φ1′|F|φ2′⟩ =
    (ε2 − ε1) sinθ cosθ). The Boys criterion picks θ with the smallest spread Σ(⟨x²⟩ − ⟨x⟩²). Two equal hybrids
    s + λp at an angle θ are orthogonal if 1 + λ² cosθ = 0: λ² = −1/cosθ (109.5° — sp³, 120° — sp², 180° — sp; water
    104.5° — sp⁴, 20 % s in a bond, the two lone pairs (1 − 2·0.20)/2 = 30 % s, sp^2.3). Donor i (filled, εi) and
    acceptor j* (empty, εj*) coupled by Fij: the lower level goes down by ≈ Fij²/(εj* − εi), with the occupation
    E(2) = −ni Fij²/(εj* − εi); exactly, for two electrons, 2(Δ/2 − √((Δ/2)² + F²)) + ... (the 2 × 2 problem).
    NCI: s = |∇ρ|/(2(3π²)^{1/3} ρ^{4/3}) is dimensionless; in an exponential tail s grows without bound, between two
    molecules ∇ρ = 0 at a critical point and s → 0 at a small ρ — a spike on the s(sign(λ2)ρ) plot; λ2 < 0 attraction
    (a bond point), λ2 > 0 repulsion (a ring point).

§2 ALGORITHM
    1D orbitals on a grid (bond functions as normalized Gaussians); closed formulas; NCI: densities of fragments
    ρ = Σ A e^{−a r_i} with analytic gradient and Hessian on a plane through the nuclei, eigenvalues of the 3 × 3
    Hessian by the closed trigonometric formula for a symmetric matrix.

§3 APPLICATIONS
    Endpoints bond.rotate, bond.hybrid, bond.e2, bond.nci.

§4 SPECIFICATION
    rotate(theta) -> {"x", "phi1", "phi2", "rho", "rho0", "spread": [[θ, Σ]], "at": {"spread", "f12", "e1", "e2",
        "drho"}}.
    hybrid(angle, nb) -> {"angle": [..], "s_bond": [..], "at": {"lam2", "s_bond", "s_lp", "lam2_lp"}, "marks"}.
    e2(F, gap, n) -> {"F": [..], "pt": [..], "exact": [..], "at": {"pt", "exact"}} (kJ/mol).
    nci(kind, d) -> {"pts": [[sign(λ2)ρ, s]], "mid": ρ at the contact, "ring": ρ at the ring point}.

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    Standard library only (Pyodide). 1 hartree = 2625.5 kJ/mol. The NCI fragments: A = 0.5, a = 1.8 bohr⁻¹ — model
    tails giving 0.005–0.05 a.u. at contacts of 3–5 bohr, as in real hydrogen bonds and van der Waals contacts.
§7 TEST CASES (tests/atlas/test_atlas_bonding.py)
    The density does not change under the rotation; Boys at 45°; λ² = 3, 2, 1 at 109.47°, 120°, 180°; water 104.5°:
    20 % and 30 % s; E(2) = 2F²/Δ for small F; NCI: no spike for one fragment, a spike at sign(λ2)ρ < 0 for a dimer,
    a positive one at the centre of a ring.
§8 ERROR ANALYSIS
    The orbital and the NCI models are illustrative; the numbers of real NBO analyses differ (O–H hybrids sp^3.3–sp⁴).
"""

import math

HARTREE_KJ = 2625.4996
CF = 2 * (3 * math.pi ** 2) ** (1 / 3)
MARKS = {2: [("H₂S", 92.1), ("H₂O", 104.5)], 3: [("PH₃", 93.3), ("NH₃", 106.7)]}


def _lin(a, b, n):
    return [a + (b - a) * i / (n - 1) for i in range(n)]


def _gauss(xs, c, w=0.8):
    g = [math.exp(-((x - c) / w) ** 2) for x in xs]
    nrm = math.sqrt(sum(v * v for v in g) * (xs[1] - xs[0]))
    return [v / nrm for v in g]


def rotate(theta=0.0, e1=-0.65, e2=-0.45):
    """Two bond orbitals a, b (Gaussians at ±1.5); the canonical φ1,2 = (a ± b)/√2 rotated by θ (degrees)."""
    if not -90 <= theta <= 90:
        raise ValueError("theta −90..90")
    xs = _lin(-5, 5, 401)
    dx = xs[1] - xs[0]
    a, b = _gauss(xs, -1.5), _gauss(xs, 1.5)
    p1 = [(u + v) / math.sqrt(2) for u, v in zip(a, b)]
    p2 = [(u - v) / math.sqrt(2) for u, v in zip(a, b)]
    nrm = math.sqrt(sum(u * u for u in p1) * dx)
    p1 = [u / nrm for u in p1]
    nrm = math.sqrt(sum(u * u for u in p2) * dx)
    p2 = [u / nrm for u in p2]

    def turned(t):
        c, s = math.cos(math.radians(t)), math.sin(math.radians(t))
        return [c * u + s * v for u, v in zip(p1, p2)], [-s * u + c * v for u, v in zip(p1, p2)]

    def spread(f):
        m1 = sum(x * v * v for x, v in zip(xs, f)) * dx
        m2 = sum(x * x * v * v for x, v in zip(xs, f)) * dx
        return m2 - m1 * m1

    def total(t):
        f, g = turned(t)
        return spread(f) + spread(g)

    q1, q2 = turned(theta)
    rho0 = [2 * (u * u + v * v) for u, v in zip(p1, p2)]
    rho = [2 * (u * u + v * v) for u, v in zip(q1, q2)]
    c, s = math.cos(math.radians(theta)), math.sin(math.radians(theta))
    return {"x": xs, "phi1": q1, "phi2": q2, "rho": rho, "rho0": rho0,
            "spread": [[t, total(t)] for t in range(-90, 91, 3)],
            "at": {"spread": total(theta), "f12": (e2 - e1) * s * c, "e1": c * c * e1 + s * s * e2,
                   "e2": s * s * e1 + c * c * e2, "drho": max(abs(u - v) for u, v in zip(rho, rho0))}, "theta": theta}


def _s_of(angle):
    c = math.cos(math.radians(angle))
    return None if c >= 0 else 1 / (1 - 1 / c)  # s share 1/(1 + λ²), λ² = −1/cosθ


def hybrid(angle=104.5, nb=2):
    """The s character of nb equal bond hybrids at the angle (degrees) and of the remaining lone pairs (4 − nb)."""
    if not (90 < angle <= 180 and nb in (2, 3)):
        raise ValueError("angle 90..180, nb 2|3")
    if nb == 3 and angle > 120:
        raise ValueError("three equal bonds: angle ≤ 120")
    hi = 180 if nb == 2 else 120
    angs = _lin(91, hi, 120)
    sb = _s_of(angle)
    nl = 4 - nb
    slp = (1 - nb * sb) / nl if nl else None
    lam = lambda s: (1 - s) / s if s and s > 1e-12 else None
    return {"angle": angs, "s_bond": [_s_of(t) for t in angs],
            "s_lp": [(1 - nb * _s_of(t)) / nl for t in angs],
            "at": {"lam2": lam(sb), "s_bond": sb, "s_lp": slp, "lam2_lp": lam(slp) if slp and slp > 0 else None},
            "marks": [[n, t] for n, t in MARKS[nb]], "nb": nb}


def e2(F=0.05, gap=0.6, n=2.0):
    """The donor–acceptor stabilization: E(2) = −n F²/Δ and the exact lowering of the 2 × 2 problem (kJ/mol)."""
    if not (0 <= F <= 0.3 and 0.1 <= gap <= 2 and 1 <= n <= 2):
        raise ValueError("F 0..0.3, gap 0.1..2, n 1..2")
    Fs = _lin(0, 0.3, 61)
    ex = lambda f: n * (math.sqrt((gap / 2) ** 2 + f * f) - gap / 2) * HARTREE_KJ
    pt = lambda f: n * f * f / gap * HARTREE_KJ
    return {"F": Fs, "pt": [pt(f) for f in Fs], "exact": [ex(f) for f in Fs], "at": {"pt": pt(F), "exact": ex(F)}}


A_FR, A_EXP = 0.5, 1.8


def _centres(kind, d):
    if kind == "one":
        return [(0.0, 0.0)]
    if kind == "dimer":
        return [(-d / 2, 0.0), (d / 2, 0.0)]
    R = d / (2 * math.sin(math.pi / 6))  # a hexagon with the side d
    return [(R * math.cos(k * math.pi / 3), R * math.sin(k * math.pi / 3)) for k in range(6)]


def _eig3(m):
    """Eigenvalues of a symmetric 3 × 3 matrix, ascending (the trigonometric method)."""
    (a, b, c), (_, d, e), (_, _, f) = m
    p1 = b * b + c * c + e * e
    q = (a + d + f) / 3
    if p1 < 1e-30:
        return sorted([a, d, f])
    p2 = (a - q) ** 2 + (d - q) ** 2 + (f - q) ** 2 + 2 * p1
    p = math.sqrt(p2 / 6)
    B = [[(m[i][j] - (q if i == j else 0)) / p for j in range(3)] for i in range(3)]
    r = (B[0][0] * (B[1][1] * B[2][2] - B[1][2] * B[2][1]) - B[0][1] * (B[1][0] * B[2][2] - B[1][2] * B[2][0])
         + B[0][2] * (B[1][0] * B[2][1] - B[1][1] * B[2][0])) / 2
    phi = math.acos(max(-1.0, min(1.0, r))) / 3
    l1 = q + 2 * p * math.cos(phi)
    l3 = q + 2 * p * math.cos(phi + 2 * math.pi / 3)
    return sorted([l1, 3 * q - l1 - l3, l3])


def _point(x, y, cs):
    rho, g = 0.0, [0.0, 0.0, 0.0]
    H = [[0.0] * 3 for _ in range(3)]
    for cx, cy in cs:
        v = (x - cx, y - cy, 0.0)
        r = math.sqrt(v[0] ** 2 + v[1] ** 2) or 1e-9
        e = A_FR * math.exp(-A_EXP * r)
        rho += e
        u = [c / r for c in v]
        for i in range(3):
            g[i] += -A_EXP * e * u[i]
            for j in range(3):
                H[i][j] += A_EXP * e * (A_EXP * u[i] * u[j] - ((1.0 if i == j else 0.0) - u[i] * u[j]) / r)
    return rho, math.sqrt(sum(c * c for c in g)), H


def nci(kind="dimer", d=4.0):
    """The points (sign(λ2)ρ, s) of a plane through the fragments: one fragment, a dimer at distance d (bohr), a
    hexagonal ring with the side d."""
    if not (kind in ("one", "dimer", "ring") and 2.5 <= d <= 7):
        raise ValueError("kind one|dimer|ring, d 2.5..7")
    cs = _centres(kind, d)
    span = max(abs(c) for p in cs for c in p) + 3.0
    n = 81
    pts = []
    for i in range(n):
        for j in range(n):
            x, y = -span + 2 * span * i / (n - 1), -span + 2 * span * j / (n - 1)
            if min(math.hypot(x - cx, y - cy) for cx, cy in cs) < 0.6:
                continue
            rho, gr, H = _point(x, y, cs)
            if rho < 1e-4 or rho > 0.08:
                continue
            s = gr / (CF * rho ** (4 / 3))
            if s > 2:
                continue
            l2 = _eig3(H)[1]
            pts.append([round(math.copysign(rho, l2), 5), round(s, 4)])
    mid = _point(0.0, 0.0, cs)[0] if kind != "one" else None
    side = _point(*(((cs[0][0] + cs[1][0]) / 2, (cs[0][1] + cs[1][1]) / 2)), cs)[0] if kind == "ring" else None
    return {"pts": pts, "mid": mid if kind == "dimer" else side, "ring": mid if kind == "ring" else None,
            "kind": kind, "d": d}
