"""Transition-state theory: Eyring rate constant, Arrhenius parameters, kinetic isotope
effect from zero-point energies, Wigner tunnelling correction.

HEADER
    Model of the page "Скорость реакции: переходное состояние" (v1.0
    kinetics.js: rate, draw, chart, the "own reaction" form).  Wilkinson
    convention, sections 1-8.

§1 THEORY
    Eyring equation (canonical TST, transmission coefficient 1):
        k = (k_B T / h) exp(dS‡/R) exp(-dH‡/(R T)),   dG‡ = dH‡ - T dS‡.
    First order: t½ = ln 2 / k; second order with c0 = 1 mol/L: t½ = 1/k.
    Arrhenius parameters of a unimolecular reaction (or one in solution):
        Ea = dH‡ + R T,   A = e (k_B T / h) exp(dS‡/R).
    Primary H/D isotope effect when the C-H stretch is lost in the TS:
        nu_D = nu_H / sqrt(mu_D/mu_H),  mu_H = 12*1/13, mu_D = 12*2/14,
        k_H/k_D = exp(h c (nu_H - nu_D) / (2 k_B T)).
    Wigner correction: kappa = 1 + (h c |nu‡| / k_B T)^2 / 24.
    From quantum-chemical free energies (hartree): dG‡ = (G_TS - G_R) E_h;
    for a bimolecular reaction in solution the standard state 1 bar -> 1 mol/L
    adds -RT ln(RT / (p° V°)), p° = 1e5 Pa, V° = 1e-3 m^3.

§2 ALGORITHM
    Direct evaluation, in the operation order of v1.0.

§3 APPLICATIONS
    Endpoints kin.state, kin.custom (pages/kinetics.py).

§4 SPECIFICATION
    state(dH kJ/mol, dS J/(mol K), T K, n in {1, 2}, nu cm^-1, im cm^-1) ->
      {dG, k, t, Ea, A, chart: {lt0, lt1, ltG, y0, y1}, kie: {r, nD, half,
      halfkJ, kie}, tun: {w, kap}}.
    custom(Gr, Gt hartree, T K, n, sol bool, im cm^-1 >= 0) ->
      {dG, corr, k, t, w, kap, kk} or {err: "nonpositive", dG}.
    Constants: CODATA 2018 exact h, k_B, N_A; E_h = 2625.4996394799 kJ/mol;
    c2 = hc/k_B = 1.438776877 cm K.  Tier: bitwise vs v1.0 (exp, log,
    log10 from core.jsmath).

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    ln 2 and e are the double constants Math.LN2, Math.E.
§7 TEST CASES (tests/test_kinetics.py)
    Oracles: dG‡ = 90 kJ/mol, 298.15 K -> k = 1.06e-3 s^-1 (k_B T/h =
    6.2124e12 s^-1); every 5.708 kJ/mol multiplies t½ by 10 at 298.15 K
    (R T ln 10); Ea - dH‡ = R T; Wigner kappa(1000i cm^-1, 298.15 K) =
    1 + 23.287/24; vs v1.0 on a grid of inputs.
§8 ERROR ANALYSIS
    A handful of correctly rounded operations and fdlibm exp/log (< 1 ulp):
    relative error < 10u.  k spans 1e-20..1e13 without overflow for the
    page's slider ranges (|exponent| < 60).
"""
from __future__ import annotations

import math

from .jsmath import exp, log, log10

H = 6.62607015e-34
KB = 1.380649e-23
NA = 6.02214076e23
R = KB * NA
EH = 2625.4996394799
C2 = 1.438776877
LN2 = 0.6931471805599453   # Math.LN2
E = 2.718281828459045      # Math.E


def rate(dH: float, dS: float, T: float) -> float:
    """Eyring k (s^-1 or L/(mol s)) for dH‡ in kJ/mol, dS‡ in J/(mol K)."""
    return KB * T / H * exp(dS / R) * exp(-dH * 1000 / (R * T))


def _lt(g: float, T: float, bi: bool) -> float:
    k = KB * T / H * exp(-g * 1000 / (R * T))
    return log10(1 / k if bi else LN2 / k)


def state(dH: float, dS: float, T: float, n: int, nu: float, im: float) -> dict:
    bi = n == 2
    dG = dH - T * dS / 1000
    k = rate(dH, dS, T)
    t = 1 / k if bi else LN2 / k
    Ea = dH + R * T / 1000
    A = E * KB * T / H * exp(dS / R)
    lt0, lt1 = _lt(40, T, bi), _lt(140, T, bi)
    chart = {"lt0": lt0, "lt1": lt1, "ltG": _lt(dG, T, bi),
             "y0": math.floor(lt0) - 1, "y1": math.ceil(lt1) + 1}
    r = math.sqrt((24 / 14) / (12 / 13))
    nD = nu / r
    u = (nu - nD) / 2 * C2 / T
    kie = {"r": r, "nD": nD, "half": (nu - nD) / 2, "halfkJ": (nu - nD) / 2 * 0.01196266, "kie": exp(u)}
    w = im * C2 / T
    return {"dG": dG, "k": k, "t": t, "Ea": Ea, "A": A, "chart": chart, "kie": kie,
            "tun": {"w": w, "kap": 1 + w * w / 24}}


def custom(Gr: float, Gt: float, T: float, n: int, sol: bool, im: float) -> dict:
    dG = (Gt - Gr) * EH
    corr = 0.0
    if sol and n == 2:
        corr = -R * T * log(R * T / (1e5 * 1e-3)) / 1000
        dG += corr
    if dG <= 0:
        return {"err": "nonpositive", "dG": dG}
    k = KB * T / H * exp(-dG * 1000 / (R * T))
    t = 1 / k if n == 2 else LN2 / k
    w = im * C2 / T
    kap = 1 + w * w / 24
    out = {"dG": dG, "corr": corr, "k": k, "t": t, "w": w, "kap": kap, "kk": k * kap}
    if n == 2 and not sol:
        # 2.6.0: with 1-bar energies a bimolecular k is in bar^-1 s^-1 (t½ at 1 bar of each reactant);
        # the same k per concentration: k_c = k_p R T / p°, in L/(mol s)
        out["kc"] = k * R * T / 1e5 * 1000
    return out
