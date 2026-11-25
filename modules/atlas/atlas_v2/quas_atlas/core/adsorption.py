"""Adsorption and magnetism: chemisorption on a d band, the Stoner criterion, the Hubbard dimer and DFT+U.

HEADER
    Model of the page "Адсорбция и магнетизм" (web/<lang>/adsorption.html), Atlas 2026-11-24; lecture 15 of the course
    «Квантово-химические методы» (its derivations 9-12, slides 16, 19-23). Wilkinson convention, sections 1-8.

§1 THEORY
    Chemisorption (Newns–Anderson; the d-band model of Hammer and Nørskov): one level εa of the adsorbate coupled by V
    to the levels of a metal. With one level εd of the metal it is a 2 × 2 problem,
        E± = (εa + εd)/2 ± sqrt(((εa − εd)/2)² + V²);
    the bond is strong when the bonding state is filled and the antibonding one empty — above the Fermi level E_F.
    A metal has a band: here the d band is M levels of a semi-elliptic density of states (centre εd, width W), each
    coupled by V/√M. The states of the adsorbate and the band are the roots of
        E − εa − Σ_k (V²/M)/(E − ε_k) = 0,
    one in every interval between neighbouring ε_k and one outside on each side; the share of the adsorbate in a state
    is w = 1/(1 + Σ_k (V²/M)/(E − ε_k)²). With E_F = 0 and two electrons per filled state, the energy of the bond is
        ΔE = 2 Σ_{E_i<0} E_i − 2 Σ_{ε_k<0} ε_k − 2 min(εa, 0)
    — the states with the coupling against the same levels without it, both filled up to E_F (the electrons come from
    the reservoir at E_F): the energy of the hybridization with the d band, the part of the bond the d-band model
    explains (the sp band, the same for all the metals, shifts εa and is left out). To it Hammer and Nørskov add the
    Pauli repulsion of the filled d states, 2αV²·f (f the filled share of the band; α = 0.05 1/eV here) — without it
    a full band would neither bind nor repel. The higher the d band
    (the closer εd to E_F), the more of the antibonding states lie above E_F and the stronger the bond: Ni, Pd, Pt
    hold hydrogen, Cu less, Au and Ag hardly — a correlation within similar metals, not a law.
    Ferromagnetism (Stoner): turning δn electrons from ↓ to ↑ near E_F costs (δn)²/N(E_F) of kinetic energy (N per
    spin) and gains −I m²/4 = −I(δn)² of exchange (m = 2δn): a moment appears when I·N(E_F) > 1. Here the d band of
    each spin is semi-elliptic (5 states per spin, width W): E_kin,σ(n_σ) = 5·(W/2)·(−2/(3π))·(1 − x²)^{3/2}, x the
    Fermi level of that spin in units of W/2; E(m) = E_σ(n/2 + m/2) + E_σ(n/2 − m/2) − 2E_σ(n/2) − I m²/4, the moment
    is the m of the minimum.
    The Hubbard dimer: two sites, two electrons, hopping t, repulsion U on a site. The triplet cannot hop: E_T = 0;
    the singlet mixes the covalent state (0) and the ionic one (U): E_S = U/2 − sqrt(U²/4 + 4t²). U ≪ t: E_S ≈ −2t
    (the bond of H2 at equilibrium); U ≫ t: E_S ≈ −4t²/U, J = E_T − E_S ≈ 4t²/U (antiferromagnetic exchange; H2
    stretched, NiO).
    DFT+U adds E_U = (U/2) Σ_i n_i(1 − n_i) over chosen orbitals: zero for n = 0 or 1, U/8 for n = 1/2 — a penalty
    for fractional occupations. Its potential V_i = U(1/2 − n_i): a filled orbital goes down by U/2, an empty one up by
    U/2, the gap grows by U.

§2 ALGORITHM
    The levels ε_k of the band: the quantiles (k + 1/2)/M of the semi-ellipse (its CDF 1/2 + (x√(1−x²) + asin x)/π,
    inverted by bisection). The roots of the secular equation by bisection in each interval (the function rises there
    from −∞ to +∞). The projected density of states: each root a Gaussian of width σ with the weight w.
    Stoner: E(m) on a grid of m from 0 to min(n, 10 − n); the minimum.

§3 APPLICATIONS
    Endpoints ads.chem, ads.stoner, ads.hubbard.

§4 SPECIFICATION
    chemisorption(ea, ed, W, V, M=80, sigma=0.15) -> {"E": grid, "pdos": [ρ_a], "band": [ρ_d], "states": [{"E", "w"}],
        "two": {"lower", "upper"}, "dE", "hyb", "pauli", "filled_anti"}  (eV, E_F = 0).
    trend(ea, V) -> {"metals": [{"name", "ed", "W", "dE"}]}.
    stoner(n, W, I, steps=200) -> {"m": [m], "E": [eV], "moment", "N_EF", "product", "E_min"}.
    hubbard(U, t=1) -> {"U": grid, "singlet": [E], "triplet": [E], "at": {"E_S", "J", "J_large_U", "ionic"}}.
    plus_u(U) -> {"n": grid, "E_U": [E], "V": [V], "shift_filled", "shift_empty"}.

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    Standard library only (the site runs it in Pyodide).
§7 TEST CASES (tests/atlas/test_atlas_adsorption.py)
    The 2 × 2 roots; the roots of the band equation satisfy it and their weights sum to 1; a stronger bond when εd
    rises (Ni below Cu below Au); Stoner: no moment when I·N(E_F) < 1, a moment when > 1, N(E_F) from the formula;
    the dimer: E_S → −2t for U = 0 and −4t²/U for large U; DFT+U: U/8 at n = 1/2, ∓U/2.
§8 ERROR ANALYSIS
    The models are those of the lecture: no sp band (it shifts all metals alike), no U on the adsorbate, a d band of
    one shape for every metal; the d-band centres are those of Hammer and Nørskov (relative to E_F).
"""

import math

# the centres of the d bands relative to E_F, eV (B. Hammer, J. K. Nørskov, Adv. Catal. 45, 71 (2000)), and the
# widths of the bands taken here (eV, ≈ of the 5d metals wider than of the 3d and 4d ones)
METALS = [('Ni', -1.29, 4.0), ('Pd', -1.83, 4.5), ('Pt', -2.25, 6.5), ('Cu', -2.67, 3.0), ('Au', -3.56, 6.0),
          ('Ag', -4.30, 3.5)]
ALPHA = 0.05  # 1/eV: the Pauli repulsion 2αV²·f of a filled share f of the d band (Hammer–Nørskov)
# Stoner presets: d electrons, width of the d band (eV), Stoner I (eV) — chosen so that the model gives the moments
STONER = {'Fe': (7.4, 4.0, 0.93), 'Ni': (9.4, 3.2, 1.0), 'Pd': (9.5, 4.6, 0.7), 'Cu': (10.0, 3.0, 0.9)}


def _cdf(x):
    x = max(-1.0, min(1.0, x))
    return 0.5 + (x * math.sqrt(1 - x * x) + math.asin(x)) / math.pi


def _inv_cdf(p):
    lo, hi = -1.0, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if _cdf(mid) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _band_levels(ed, W, M):
    return [ed + W / 2 * _inv_cdf((k + 0.5) / M) for k in range(M)]


def _roots(ea, levels, V):
    c = V * V / len(levels)
    f = lambda E: E - ea - sum(c / (E - e) for e in levels)
    span = max(abs(ea), max(abs(e) for e in levels)) + 4 * abs(V) + 10
    bounds = [-span - 10] + levels + [span + 10]
    out = []
    for a, b in zip(bounds, bounds[1:]):
        gap = (b - a) * 1e-12
        lo, hi = a + gap, b - gap
        for _ in range(80):
            mid = (lo + hi) / 2
            if f(mid) < 0:
                lo = mid
            else:
                hi = mid
        E = (lo + hi) / 2
        w = 1 / (1 + sum(c / (E - e) ** 2 for e in levels))
        out.append({"E": E, "w": w})
    return out


def _bond(ea, ed, W, V, M):
    levels = _band_levels(ed, W, M)
    states = _roots(ea, levels, V)
    hyb = 2 * sum(s["E"] for s in states if s["E"] < 0) - 2 * sum(e for e in levels if e < 0) - 2 * min(ea, 0.0)
    filled = sum(1 for e in levels if e < 0) / M
    return levels, states, hyb, 2 * ALPHA * V * V * filled


def chemisorption(ea=-2.0, ed=-2.25, W=6.5, V=2.0, M=80, sigma=0.15):
    """The adsorbate level coupled to a semi-elliptic d band: its projected DOS, the band, the bond energy."""
    if not (-8 <= ea <= 4 and -6 <= ed <= 2 and 1 <= W <= 10 and 0 <= V <= 5):
        raise ValueError("εa −8..4, εd −6..2, W 1..10, V 0..5 eV")
    levels, states, hyb, pauli = _bond(ea, ed, W, V, M)
    grid = [-10 + 14 * i / 400 for i in range(401)]
    norm = 1 / (sigma * math.sqrt(2 * math.pi))
    pdos = [sum(s["w"] * norm * math.exp(-0.5 * ((E - s["E"]) / sigma) ** 2) for s in states) for E in grid]
    band = [(2 / math.pi) * math.sqrt(max(0.0, 1 - ((E - ed) / (W / 2)) ** 2)) / (W / 2) for E in grid]
    half = (ea + ed) / 2
    root = math.sqrt(((ea - ed) / 2) ** 2 + V * V)
    anti = [s for s in states if s["E"] > half]  # the states on the antibonding side of the adsorbate weight
    filled_anti = sum(s["w"] for s in anti if s["E"] < 0) / max(1e-12, sum(s["w"] for s in anti))
    return {"E": grid, "pdos": pdos, "band": band, "states": states, "two": {"lower": half - root, "upper": half + root},
            "dE": hyb + pauli, "hyb": hyb, "pauli": pauli, "filled_anti": filled_anti}


def trend(ea=-2.0, V=2.0, M=80):
    """The bond energy of the same adsorbate on the d bands of the metals of METALS (their εd and W)."""
    rows = []
    for n, ed, W in METALS:
        _, _, hyb, pauli = _bond(ea, ed, W, V, M)
        rows.append({"name": n, "ed": ed, "W": W, "dE": hyb + pauli})
    return {"metals": rows}


def _ekin(ns, W):
    """The band energy of one spin with ns electrons in a semi-elliptic band of 5 states (centre 0, width W)."""
    x = _inv_cdf(min(1.0, max(0.0, ns / 5)))
    return 5 * (W / 2) * (-2 / (3 * math.pi)) * (1 - x * x) ** 1.5


def stoner(n=7.4, W=4.0, I=0.93, steps=200):
    """E(m) of the Stoner model for n d electrons, the moment of the minimum, N(E_F) per spin and I·N(E_F)."""
    if not (0 <= n <= 10 and 1 <= W <= 12 and 0 <= I <= 2):
        raise ValueError("n 0..10, W 1..12, I 0..2 eV")
    top = min(n, 10 - n)
    ms = [top * i / steps for i in range(steps + 1)]
    base = 2 * _ekin(n / 2, W)
    es = [_ekin((n + m) / 2, W) + _ekin((n - m) / 2, W) - base - I * m * m / 4 for m in ms]
    j = min(range(len(es)), key=lambda i: (round(es[i], 12), ms[i]))
    x = _inv_cdf(min(1.0, max(0.0, n / 10)))
    nef = 5 * (2 / math.pi) * math.sqrt(max(0.0, 1 - x * x)) / (W / 2)
    return {"m": ms, "E": es, "moment": ms[j], "E_min": es[j], "N_EF": nef, "product": I * nef}


def hubbard(U=4.0, t=1.0):
    """The singlet and the triplet of the Hubbard dimer against U (0…20 t), and at the given U."""
    if not (0 <= U <= 40 and 0.1 <= t <= 5):
        raise ValueError("U 0..40, t 0.1..5")
    us = [20 * t * i / 200 for i in range(201)]
    es = lambda u: u / 2 - math.sqrt(u * u / 4 + 4 * t * t)
    ionic = lambda u: 0.5 * (1 - u / 2 / math.sqrt(u * u / 4 + 4 * t * t))  # the weight of the ionic state
    return {"U": us, "singlet": [es(u) for u in us], "triplet": [0.0 for _ in us],
            "at": {"U": U, "E_S": es(U), "J": -es(U), "J_large_U": 4 * t * t / U if U > 0 else None, "ionic": ionic(U)}}


def plus_u(U=4.0):
    """E_U = (U/2)·n(1 − n) of one orbital and its potential U(1/2 − n)."""
    if not 0 <= U <= 12:
        raise ValueError("U 0..12 eV")
    ns = [i / 100 for i in range(101)]
    return {"n": ns, "E_U": [U / 2 * n * (1 - n) for n in ns], "V": [U * (0.5 - n) for n in ns],
            "shift_filled": -U / 2, "shift_empty": U / 2, "half": U / 8}
