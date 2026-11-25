"""Gas-phase equilibrium constants from tabulated enthalpies and RRHO thermochemistry.

HEADER
    Model of the page "Равновесие: от энергии к константе" (v1.0
    equilibrium.js: calc, draw, chart, sens, the example and own-reaction
    forms).  Wilkinson convention, sections 1-8.

§1 THEORY
    For a reaction sum_i nu_i X_i = 0 of ideal gases with p° = 1 bar:
      dH°(T) = dH°(0 K) + sum nu_i [H_i(T) - H_i(0)],
      dH°(0 K) = dH°(298.15) - sum nu_i [H_i(298.15) - H_i(0)],
      dE_el = dH°(0 K) - dZPE           (back-calculated electronic energy),
      dS°(T) = sum nu_i S_i(T),  dG° = dH° - T dS°,
      ln K = -dG° / (R T),  K = prod (p_i/p°)^nu_i.
    H_i(T) - H_i(0), ZPE_i, S_i: rigid rotor / harmonic oscillator
    (core.thermochemistry); dfH°(298.15) and dfG°(298.15): NIST-JANAF.
    An error d in dG° changes K by exp(d/(RT)); a factor 10 in K is
    RT ln 10 (5.71 kJ/mol at 298.15 K).
    From quantum-chemical output (hartree): dE = sum nu E_i, dG = sum nu
    (E_i + G_corr,i).

§2 ALGORITHM
    Direct sums in v1.0 order; chart T = 200..1500 K step 10, sign change of
    dG° located by linear interpolation in the first bracketing interval.

§3 APPLICATIONS
    Endpoints eq.reactions, eq.state, eq.sens, eq.chart, eq.example, eq.custom.

§4 SPECIFICATION
    calc(i, T) -> {dEel, dZPE, dH0, dHth, dH, dS, dG, lnK, dn} (kJ/mol,
    J/(mol K)); state adds K, lgK, mTdS, g298 (tabulated dG°).  Tier:
    bitwise vs v1.0 on Linux/glibc (thermo uses the platform pow, see
    core.thermochemistry §4).

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    Math.LN10 is the double 2.302585092994046.
§7 TEST CASES (tests/test_equilibrium.py)
    Oracles: RRHO dG°(298) of the four reactions within 2 kJ/mol of the
    JANAF values (dfG); van 't Hoff consistency d lnK/dT = dH°/(R T^2)
    (central difference, 1e-4 relative); 10^K-step equals R T ln 10; vs v1.0.
§8 ERROR ANALYSIS
    Sums of < 6 terms of magnitude <= 1000 kJ/mol: absolute error < 1e-12
    kJ/mol; exp of |ln K| < 200: relative error of K < 1e-13.  The model
    error (RRHO, JANAF uncertainty ~0.1-1 kJ/mol) dominates.
"""
from __future__ import annotations

from .jsmath import exp
from .thermochemistry import EH, MOL, R, thermo

P0 = 1e5
LN10 = 2.302585092994046
DFH = {"H₂": 0, "N₂": 0, "O₂": 0, "CO": -110.527, "CO₂": -393.522, "H₂O": -241.826, "NH₃": -45.898, "CH₄": -74.873}
DFG = {"H₂": 0, "N₂": 0, "O₂": 0, "CO": -137.163, "CO₂": -394.389, "H₂O": -228.582, "NH₃": -16.367, "CH₄": -50.768}
RX = [[["N₂", -1], ["H₂", -3], ["NH₃", 2]], [["CO", -1], ["H₂O", -1], ["CO₂", 1], ["H₂", 1]],
      [["CH₄", -1], ["H₂O", -1], ["CO", 1], ["H₂", 3]], [["H₂", -2], ["O₂", -1], ["H₂O", 2]]]
"""Stoichiometry of the page's reactions: NH3 synthesis, water-gas shift, steam reforming, H2 combustion."""


def mol(s):
    return next(m for m in MOL if m["id"] == s)


def calc(i: int, T: float) -> dict:
    r = RX[i]
    dH298 = dHth298 = dZPE = 0
    for s, v in r:
        dH298 += v * DFH[s]
        t = thermo(mol(s), 298.15, P0)
        dHth298 += v * t["Hth"] / 1000
        dZPE += v * t["zpe"] / 1000
    dH0 = dH298 - dHth298
    dEel = dH0 - dZPE
    dHth = dS = 0
    for s, v in r:
        t = thermo(mol(s), T, P0)
        dHth += v * t["Hth"] / 1000
        dS += v * t["S"]
    dH = dH0 + dHth
    dG = dH - T * dS / 1000
    lnK = -dG * 1000 / (R * T)
    dn = 0
    for _, v in r:
        dn = dn + v
    return {"dEel": dEel, "dZPE": dZPE, "dH0": dH0, "dHth": dHth, "dH": dH, "dS": dS, "dG": dG, "lnK": lnK, "dn": dn}


def state(i: int, T: float) -> dict:
    c = calc(i, T)
    g = 0
    for s, v in RX[i]:
        g = g + v * DFG[s]
    return {"c": c, "mTdS": -T * c["dS"] / 1000, "K": exp(c["lnK"]), "lgK": c["lnK"] / LN10, "g298": g}


def sens(d: float, T: float) -> dict:
    f = exp(-d * 1000 / (R * T))
    return {"f": f, "fmax": max(f, 1 / f), "k10": R * T * LN10 / 1000}


def chart(i: int) -> dict:
    pts = []
    T = 200
    while T <= 1500:
        c = calc(i, T)
        pts.append([T, {"dG": c["dG"], "dH": c["dH"], "mTdS": -T * c["dS"] / 1000, "lgK": c["lnK"] / LN10}])
        T += 10
    Tx = None
    for k in range(1, len(pts)):
        a, b = pts[k - 1][1]["dG"], pts[k][1]["dG"]
        if a * b <= 0 and a != b:
            Tx = pts[k - 1][0] + 10 * a / (a - b)
            break
    return {"pts": pts, "Tx": Tx}


def example() -> dict:
    """Model quantum-chemistry numbers for NH3 synthesis (v1.0 'example' button)."""
    E = {"N₂": -109.40000, "H₂": -1.17000}
    c = calc(0, 298.15)
    E["NH₃"] = (E["N₂"] + 3 * E["H₂"] + c["dEel"] / EH) / 2
    return {"rows": [[s, v, E[s], thermo(mol(s), 298.15, P0)["Gc"] / 1000 / EH] for s, v in RX[0]]}


def custom(T: float, rows: list) -> dict:
    """K from (coefficient, E, G_corr) per species, energies in hartree."""
    dE = dG = dn = 0
    for k, e, g in rows:
        dE += k * e
        dG += k * (e + g)
        dn += k
    dEk, dGk = dE * EH, dG * EH
    return {"dE": dE, "dG": dG, "dn": dn, "dEk": dEk, "dGk": dGk, "K": exp(-dGk * 1000 / (R * T))}
