"""Conformers: a torsion profile, its minima and barriers, Boltzmann populations, the cost of a grid search.

HEADER
    Model of the page "Конформеры: поиск минимумов" (web/<lang>/conformers.html), Atlas 2026-10-25.
    Wilkinson convention, sections 1-8.

§1 THEORY
    The energy of rotation about one bond is periodic; a three-term Fourier series (as in OPLS/AMBER)
        V(φ) = ½V1 (1 + cos φ) + ½V2 (1 − cos 2φ) + ½V3 (1 + cos 3φ),
    φ the dihedral (180° = anti), describes ethane (V3 only: minima at 60°, 180°, 300°, barrier V3) and
    butane (V1, V2, V3: anti, two gauche, eclipsed barriers). Each local minimum i is a conformer; at
    temperature T their equilibrium fractions are
        p_i = exp(−E_i/RT) / Σ_j exp(−E_j/RT) (energies relative to the lowest; one well each),
    a fair first estimate when the wells have similar widths (otherwise free energies are needed).
    A molecule with n rotatable bonds and k minima per bond has up to k^n combinations: a grid of
    starting structures grows exponentially, which is why CREST explores the surface with metadynamics
    (iMTD-GC) and keeps what lies within an energy window (default 6 kcal/mol = 25.1 kJ/mol), sorting
    duplicates by RMSD (0.125 Å) and energy (0.05 kcal/mol) — CREGEN.
    Model butane parameters (kJ/mol): V1 = 7.2, V2 = −2.1, V3 = 13.8 give gauche ≈ +3.6 (at ±64.5°), the barrier
    anti→gauche ≈ 14 and the syn barrier ≈ 21, close to the usual experimental and ab initio values;
    ethane V3 = 12.0 (barrier 12 kJ/mol).

§2 ALGORITHM
    profile: φ from −180° to 180° with step 1°; minima and maxima: sign changes of the sampled derivative,
    refined by golden-section search on ±1°; populations from the minima energies. grid_cost: k^n starts,
    total time = starts × minutes per optimisation.

§3 APPLICATIONS
    Endpoints conf.profile, conf.cost.

§4 SPECIFICATION
    energy(phi, V1, V2, V3) -> kJ/mol.
    profile(V1, V2, V3, T) -> {"phi": [...], "E": [...], "minima": [{"phi", "E", "p"}], "maxima": [{"phi", "E"}],
                              "Emin": lowest}; energies relative to the lowest minimum.
    grid_cost(n, k, minutes) -> {"starts", "hours", "days"}.

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    R = 8.314462618e-3 kJ/(mol K) (CODATA 2018).
§7 TEST CASES (tests/test_atlas_new_topics.py)
    Ethane: three equal minima, each p = 1/3, barrier = V3. Butane preset: anti lowest, two gauche of equal
    energy 3.5-3.8 kJ/mol, anti fraction at 298 K 0.66-0.70. 3 minima, 10 bonds: 59049 starts.
§8 ERROR ANALYSIS
    Golden-section refinement to 1e-7 degrees; the model (one torsion, rigid rest of the molecule) dominates.
"""
from __future__ import annotations

import math

R = 8.314462618e-3
PRESETS = {"ethane": (0.0, 0.0, 12.0), "butane": (7.2, -2.1, 13.8)}


def energy(phi: float, V1: float, V2: float, V3: float) -> float:
    x = math.radians(phi)
    return 0.5 * V1 * (1 + math.cos(x)) + 0.5 * V2 * (1 - math.cos(2 * x)) + 0.5 * V3 * (1 + math.cos(3 * x))


def _refine(f, a: float, b: float, sign: float) -> float:
    g = (math.sqrt(5) - 1) / 2
    c, d = b - g * (b - a), a + g * (b - a)
    while b - a > 1e-7:
        if sign * f(c) < sign * f(d):
            b = d
        else:
            a = c
        c, d = b - g * (b - a), a + g * (b - a)
    return (a + b) / 2


def profile(V1: float, V2: float, V3: float, T: float = 298.15) -> dict:
    for v in (V1, V2, V3):
        if not -100 <= v <= 100:
            raise ValueError("V: -100..100 kJ/mol")
    if not 1 <= T <= 5000:
        raise ValueError("T: 1..5000 K")
    f = lambda p: energy(p, V1, V2, V3)  # noqa: E731
    phis = list(range(-180, 181))
    raw = [f(p) for p in phis]
    mins, maxs = [], []
    for i in range(360):  # periodic: points -180..179, neighbours wrap around
        a, b, c = raw[(i - 1) % 360], raw[i], raw[(i + 1) % 360]
        p = phis[i]
        if b < a and b <= c:
            x = _refine(f, p - 1, p + 1, 1)
            mins.append(((x + 180) % 360 - 180, f(x)))
        elif b > a and b >= c:
            x = _refine(f, p - 1, p + 1, -1)
            maxs.append(((x + 180) % 360 - 180, f(x)))
    flat = not mins
    if flat:  # a constant profile (all V = 0): no conformers
        mins = [(180.0, f(180.0))]
    e0 = min(e for _, e in mins)
    w = [math.exp(-(e - e0) / (R * T)) for _, e in mins]
    s = sum(w)
    return {
        "phi": phis,
        "E": [e - e0 for e in raw],
        "minima": [{"phi": p, "E": e - e0, "p": wi / s} for (p, e), wi in zip(mins, w)],
        "maxima": [{"phi": p, "E": e - e0} for p, e in maxs],
        "flat": flat,
    }


def grid_cost(n: int, k: int, minutes: float) -> dict:
    if not 1 <= n <= 40 or not 2 <= k <= 12 or not 0 < minutes <= 10000:
        raise ValueError("n: 1..40, k: 2..12, minutes > 0")
    starts = k**n
    hours = starts * minutes / 60
    return {"starts": starts, "hours": hours, "days": hours / 24, "years": hours / 24 / 365.25}
