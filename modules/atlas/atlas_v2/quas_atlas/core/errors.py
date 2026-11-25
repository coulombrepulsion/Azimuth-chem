"""The error of a calculation: how independent errors add up, from the mean absolute error of a method to an interval,
the cancellation of errors in isodesmic reactions and by a related reference system, and the populations of
conformers with their uncertainty.

HEADER
    Model of the page "Погрешность расчёта: от ошибки метода к выводу" (web/<lang>/errors.html), Atlas 2026-11-24;
    lecture 18 of the course «Квантово-химические методы» (derivations 2, 3, 4, 6, 10). Wilkinson convention, §1-8.

§1 THEORY
    Independent errors add in squares: σ = √(σ_method² + σ_basis² + σ_conv²) — 8, 3, 1 → 8.6 (without the
    convergence 8.5), with σ_conv = 10 → 13. For normally distributed errors MAE = σ√(2/π) = 0.80σ, σ = 1.25 MAE; 95 %
    of the errors lie within ±2σ (MAE 8 → ±20 kJ/mol); a rate constant through e^{−ΔG‡/RT} is then known to a factor
    e^{2σ/RT} (≈ 3000 at 298 K). Isodesmic reactions: the number of bonds of each type is the same on both sides, and
    systematic bond errors cancel (ethanol: atomization 5·2 + 5 + 6 + 3 = 24, isodesmic 0);
    ΔfH(C2H5OH) = ΔfH(CH3OH) + ΔfH(C2H6) − ΔfH(CH4) − ΔrH = −201.0 − 83.8 + 74.9 − 23.0 = −232.9 (experiment −234 ± 2).
    A related reference: ΔE_corr = ΔE_target + (ΔE_ref^exp − ΔE_ref^calc), σ² = σt² + σr² − 2ρσtσr = 2σ²(1 − ρ):
    ρ = 0.8 → 5.1, ρ = 0 → 11.3 for σ = 8. Two conformers: x2/x1 = e^{−ΔG/RT}; ΔG = 2 ± 4 kJ/mol gives x2 from 8 to 69 %.

§2 ALGORITHM
    The closed formulas above.

§3 APPLICATIONS
    Endpoints err.sum, err.interval, err.isodesmic, err.conformers.

§4 SPECIFICATION
    total(sm, sb, sc) -> {"total", "without_conv", "parts": [σ²], "share": [σ²/Σ]}.
    interval(mae, T) -> {"sigma", "half95", "factor", "x", "pdf", "frac_beyond_mae"}.
    isodesmic(dch, dcc, dco, doh, sigma, rho) -> {"atomization", "isodesmic", "dfh", "exp", "corr", "corr_curve"}.
    conformers(dG, s, T) -> {"x2", "lo", "hi", "curve": [[ΔG, x2]]}.

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    Standard library only (Pyodide). R = 8.314 J/(mol K).
§7 TEST CASES (tests/atlas/test_atlas_errors.py)
    8.6, 8.5 and 13 kJ/mol; σ = 1.25 MAE and ±20 for MAE 8, the factor ≈ 3000; the ethanol −232.9; 5.1 and 11.3;
    the conformer shares 69/31 %, the interval 8–69 % and with σ = 1: 23–40 %.
§8 ERROR ANALYSIS
    The bond errors are the lecture's conventional numbers; the experimental ΔfH(298, gas) are from the NIST WebBook
    (as checked for the lecture); the reaction enthalpy 23.0 kJ/mol is the lecture's ORCA 6.0.1 B3LYP-D3(BJ)/def2-TZVP
    calculation with thermal corrections at 298.15 K.
"""

import math

R = 8.314
DFH = {"CH3OH": -201.0, "C2H6": -83.8, "CH4": -74.9, "C2H5OH": -234.0}
DRH = 23.0
# bonds: C2H5OH + CH4 -> CH3OH + C2H6
BONDS = {"C2H5OH": {"CH": 5, "CC": 1, "CO": 1, "OH": 1}, "CH4": {"CH": 4},
         "CH3OH": {"CH": 3, "CO": 1, "OH": 1}, "C2H6": {"CH": 6, "CC": 1}}


def total(sm=8.0, sb=3.0, sc=1.0):
    """Independent errors added in squares."""
    if not all(0 <= v <= 30 for v in (sm, sb, sc)):
        raise ValueError("0..30 kJ/mol")
    parts = [sm * sm, sb * sb, sc * sc]
    s = sum(parts)
    return {"total": math.sqrt(s), "without_conv": math.sqrt(sm * sm + sb * sb), "parts": parts,
            "share": [p / s if s else 0 for p in parts], "linear": sm + sb + sc}


def interval(mae=8.0, T=298.15):
    """From the mean absolute error to σ and the 95 % interval; the factor in a rate constant."""
    if not (0.5 <= mae <= 30 and 200 <= T <= 1000):
        raise ValueError("mae 0.5..30, T 200..1000")
    sig = mae / math.sqrt(2 / math.pi)
    xs = [-4 * sig + 8 * sig * i / 200 for i in range(201)]
    pdf = [math.exp(-x * x / (2 * sig * sig)) / (sig * math.sqrt(2 * math.pi)) for x in xs]
    beyond = math.erfc(mae / (sig * math.sqrt(2)))
    return {"sigma": sig, "half95": 2 * sig, "factor": math.exp(2 * sig * 1000 / (R * T)), "x": xs, "pdf": pdf,
            "frac_beyond_mae": beyond, "frac_beyond_2s": math.erfc(2 / math.sqrt(2)), "mae": mae}


def isodesmic(dch=2.0, dcc=5.0, dco=6.0, doh=3.0, sigma=8.0, rho=0.8):
    """Systematic bond errors: atomization of ethanol against the isodesmic reaction C2H5OH + CH4 → CH3OH + C2H6;
    the correction by a related reference with correlated errors."""
    d = {"CH": dch, "CC": dcc, "CO": dco, "OH": doh}
    if not (all(0 <= v <= 20 for v in d.values()) and 0 <= sigma <= 30 and -1 <= rho <= 1):
        raise ValueError("bond errors 0..20, sigma 0..30, rho −1..1")
    err = lambda m: sum(n * d[b] for b, n in BONDS[m].items())
    left = {b: BONDS["C2H5OH"].get(b, 0) + BONDS["CH4"].get(b, 0) for b in d}
    right = {b: BONDS["CH3OH"].get(b, 0) + BONDS["C2H6"].get(b, 0) for b in d}
    dfh = DFH["CH3OH"] + DFH["C2H6"] - DFH["CH4"] - DRH
    corr = lambda r: math.sqrt(max(0.0, 2 * sigma * sigma * (1 - r)))
    return {"atomization": err("C2H5OH"), "isodesmic": sum((right[b] - left[b]) * d[b] for b in d),
            "left": left, "right": right, "by_bond": {b: BONDS["C2H5OH"].get(b, 0) * d[b] for b in d},
            "dfh": dfh, "exp": DFH["C2H5OH"], "exp_err": 2.0, "drh": DRH,
            "corr": corr(rho), "corr_curve": [[r / 20, corr(r / 20)] for r in range(-20, 21)], "sigma": sigma}


def _x2(dG, T):
    r = math.exp(-dG * 1000 / (R * T))
    return r / (1 + r)


def conformers(dG=2.0, s=4.0, T=298.15):
    """The share of the second conformer, x2 = r/(1 + r), r = e^{−ΔG/RT}, and its interval at ΔG ± s."""
    if not (-10 <= dG <= 10 and 0 <= s <= 10 and 200 <= T <= 1000):
        raise ValueError("dG −10..10, s 0..10, T 200..1000")
    return {"x2": _x2(dG, T), "lo": _x2(dG + s, T), "hi": _x2(dG - s, T),
            "curve": [[g / 4, _x2(g / 4, T)] for g in range(-80, 81)], "dG": dG, "s": s}
