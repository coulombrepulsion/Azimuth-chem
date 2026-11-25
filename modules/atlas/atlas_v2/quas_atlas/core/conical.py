"""Conical intersections and biradicals: the non-crossing rule, the double cone and its branching plane, the
two-centre model of a biradical and the Yamaguchi formula for broken-symmetry DFT.

HEADER
    Model of the page "Конические пересечения и бирадикалы" (web/<lang>/conical.html), Atlas 2026-11-24; lecture 7 of
    the course «Квантово-химические методы» (derivations 5–8). Wilkinson convention, sections 1-8.

§1 THEORY
    Two states in two diabatic functions: H = [[H11, H12], [H12, H22]], E± = H̄ ± √(Δ² + H12²), H̄ = (H11 + H22)/2,
    Δ = (H11 − H22)/2. E+ = E− only if Δ = 0 and H12 = 0: two conditions. A diatomic has one coordinate — the curves
    of one symmetry avoid each other (the gap 2|H12|); of different symmetry H12 ≡ 0 and they cross. A polyatomic
    with N_int = 3N − 6 coordinates has a seam of dimension N_int − 2 (von Neumann, Wigner 1929). Near a point of the
    seam Δ ≈ g·x, H12 ≈ h·y (x along the gradient difference g, y along the coupling vector h — the branching plane):
    E± ≈ Ē ± √(g²x² + h²y²), a double cone; along the other N_int − 2 coordinates E+ = E−. In linear-response TD-DFT
    the coupling of S0 and S1 is zero: one condition, the seam of dimension N_int − 1 and a wrong cone.
    Two centres a, b, two electrons, hopping t, repulsion U, direct exchange K: the triplet −K, the covalent singlet
    +K coupled by 2t to the ionic singlet at U; E_S = (K + U)/2 − √(((U − K)/2)² + 4t²), and to second order
    ΔE_ST = E_T − E_S ≈ 4t²/U − 2K (the kinetic exchange). ε+ − ε− = 2|t|.
    Broken symmetry: E_BS ≈ w E_S + (1 − w) E_T, ⟨S²⟩_BS = 2(1 − w), hence the Yamaguchi formula
    ΔE_ST ≈ 2(E_T − E_BS)/(⟨S²⟩_T − ⟨S²⟩_BS); at ⟨S²⟩_BS = 1: E_S = 2E_BS − E_T (the Ziegler sum rule).

§2 ALGORITHM
    The closed formulas above on grids; the hopping t that gives a measured ΔE_ST is found by bisection of the exact
    two-centre expression (monotone in t).

§3 APPLICATIONS
    Endpoints cone.cross, cone.cone, cone.twosite, cone.yamaguchi.

§4 SPECIFICATION
    cross(c, sym) -> {"x", "d1", "d2", "lo", "hi", "gap", "crossing"}.
    cone(g, h, y0, tilt, tddft, atoms) -> {"x", "y", "gap" (grid), "sec0": {"lo", "hi"}, "sec": {...}, "gap_y0",
        "n_int", "seam", "seam_tddft"}.
    twosite(t, U, K) -> {"t", "exact", "approx" (kJ/mol), "at": {"exact", "approx", "ES", "ET", "split"},
        "benzynes": [{"name", "exp", "casscf", "nevpt2", "t_fit"}]}.
    yamaguchi(dE, s2) -> {"s2", "curve", "at": {"dest", "w", "ziegler"}, "methods": [{"name", "value"}], "exp"}.

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    Standard library only (the site runs it in Pyodide). 1 eV = 96.485 kJ/mol.
§7 TEST CASES (tests/atlas/test_atlas_conical.py)
    The gap 2|h y| = 0.36 at y = 0.3 for h = 0.6 (the lecture's demonstration); ethylene N_int 12, seam 10 (TD-DFT
    11); the two-centre singlet to second order 4t²/U − 2K; p-benzyne E_T − E_BS = 10.3 kJ/mol, ⟨S²⟩_BS = 1:
    ΔE_ST ≈ 21 (Ziegler), experiment 16.
§8 ERROR ANALYSIS
    The benzyne numbers are the lecture's (ORCA 6.0.1, def2-SVP, CASSCF(2,2) geometries, 21.11.2026; experiment
    Wenthold, Squires, Lineberger, JACS 120, 5279 (1998)); the model surfaces are illustrative.
"""

import math

EV_KJ = 96.485
BENZYNES = [("o", 157.0, 123.0, 164.0), ("m", 88.0, 48.0, 74.0), ("p", 16.0, 2.0, 10.0)]
PBENZYNE = {"rks": -90.0, "bs": 10.3, "casscf": 2.0, "nevpt2": 10.0, "exp": 16.0}


def _lin(a, b, n):
    return [a + (b - a) * i / (n - 1) for i in range(n)]


def cross(c=0.1, sym=0):
    """Two diabatic parabolas 0.5(x ± 1)² coupled by c (sym 1: different symmetry, the coupling is zero)."""
    if not (0 <= c <= 0.5 and sym in (0, 1)):
        raise ValueError("c 0..0.5, sym 0|1")
    cc = 0.0 if sym else c
    xs = _lin(-2, 2, 161)
    d1 = [0.5 * (x + 1) ** 2 for x in xs]
    d2 = [0.5 * (x - 1) ** 2 for x in xs]
    lo, hi = [], []
    for a, b in zip(d1, d2):
        m, r = (a + b) / 2, math.hypot((a - b) / 2, cc)
        lo.append(m - r)
        hi.append(m + r)
    return {"x": xs, "d1": d1, "d2": d2, "lo": lo, "hi": hi, "gap": 2 * cc, "crossing": cc == 0, "c": cc}


def _branches(x, y, g, h, tilt):
    m, r = tilt * x, math.hypot(g * x, h * y)
    return m - r, m + r


def cone(g=1.0, h=0.6, y0=0.3, tilt=0.0, tddft=0, atoms=6):
    """The double cone E± = tilt·x ± √(g²x² + h²y²) on a grid of the branching plane, its sections at y = 0 and
    y = y0, and the dimension of the seam for a molecule of `atoms` atoms (tddft 1: h = 0)."""
    if not (0.2 <= g <= 2 and 0 <= h <= 2 and -1 <= y0 <= 1 and -1 <= tilt <= 1 and tddft in (0, 1)
            and 2 <= atoms <= 30):
        raise ValueError("g 0.2..2, h 0..2, y0 −1..1, tilt −1..1, tddft 0|1, atoms 2..30")
    hh = 0.0 if tddft else h
    xs, ys = _lin(-1, 1, 41), _lin(-1, 1, 41)
    gap = [[2 * math.hypot(g * x, hh * y) for x in xs] for y in ys]
    sx = _lin(-1, 1, 121)

    def sec(y):
        b = [_branches(x, y, g, hh, tilt) for x in sx]
        return {"lo": [p[0] for p in b], "hi": [p[1] for p in b]}

    n_int = 1 if atoms == 2 else 3 * atoms - 6
    return {"x": xs, "y": ys, "gap": gap, "sx": sx, "sec0": sec(0.0), "sec": sec(y0), "gap_y0": 2 * abs(hh * y0),
            "n_int": n_int, "seam": n_int - 2, "seam_tddft": n_int - 1, "h": hh}


def _exact(t, U, K):
    es = (K + U) / 2 - math.sqrt(((U - K) / 2) ** 2 + 4 * t * t)
    return -K - es, es


def _t_fit(dest_ev, U, K):
    """The hopping t (eV) of the exact two-centre model that gives ΔE_ST = dest_ev (None if out of reach)."""
    lo, hi = 0.0, 5.0
    if _exact(lo, U, K)[0] > dest_ev or _exact(hi, U, K)[0] < dest_ev:
        return None
    for _ in range(60):
        mid = (lo + hi) / 2
        if _exact(mid, U, K)[0] < dest_ev:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def twosite(t=0.5, U=4.0, K=0.02):
    """ΔE_ST (kJ/mol) of the two-centre model, exact and to second order, against the hopping t (eV); the t that
    reproduces the measured splittings of the three benzynes."""
    if not (0 <= t <= 2 and 1 <= U <= 10 and 0 <= K <= 0.3):
        raise ValueError("t 0..2, U 1..10, K 0..0.3 eV")
    ts = _lin(0, 2, 101)
    exact = [_exact(x, U, K)[0] * EV_KJ for x in ts]
    approx = [(4 * x * x / U - 2 * K) * EV_KJ for x in ts]
    d, es = _exact(t, U, K)
    return {"t": ts, "exact": exact, "approx": approx,
            "at": {"exact": d * EV_KJ, "approx": (4 * t * t / U - 2 * K) * EV_KJ, "ES": es, "ET": -K, "split": 2 * t},
            "benzynes": [{"name": n, "exp": e, "casscf": c, "nevpt2": v, "t_fit": _t_fit(e / EV_KJ, U, K)}
                         for n, e, c, v in BENZYNES]}


def yamaguchi(dE=10.3, s2=1.0):
    """The singlet–triplet splitting from E_T − E_BS = dE (kJ/mol) and ⟨S²⟩_BS = s2 (⟨S²⟩_T = 2), the Yamaguchi
    formula, against s2; p-benzyne by the methods of the lecture."""
    if not (0 <= dE <= 100 and 0 <= s2 <= 1.5):
        raise ValueError("dE 0..100 kJ/mol, s2 0..1.5")
    ss = _lin(0, 1.5, 61)
    p = PBENZYNE
    dest = 2 * dE / (2 - s2)
    return {"s2": ss, "curve": [2 * dE / (2 - s) for s in ss], "at": {"dest": dest, "w": 1 - s2 / 2, "ziegler": 2 * dE},
            "methods": [{"name": "RKS", "value": p["rks"]}, {"name": "E_T − E_BS", "value": dE},
                        {"name": "Yamaguchi", "value": dest}, {"name": "CASSCF", "value": p["casscf"]},
                        {"name": "NEVPT2", "value": p["nevpt2"]}], "exp": p["exp"]}
