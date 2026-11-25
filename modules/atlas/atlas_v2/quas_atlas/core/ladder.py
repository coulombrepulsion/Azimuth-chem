"""Hierarchy of correlation methods and Jacob's ladder: errors vs FCI, cost scaling, timings,
atomisation energies (precomputed PySCF data).

HEADER
    Model of the page "Иерархия методов и лестница Якова" (v1.0 ladder.js:
    fci, cost, binom, fit, times, mae, taeT). Wilkinson convention, §1-§8.

§1 THEORY
    Within one basis set full CI (FCI) is exact; MP2, CISD, CCSD, CCSD(T)
    approximate it. Errors E_method - E_FCI of HF and H2O (6-31G, frozen
    core, data/ladder_methods.json) along symmetric stretching (r/r_e = k)
    show the single-reference breakdown. Fraction of the correlation
    energy recovered: (E - E_HF)/(E_FCI - E_HF). Formal cost N^p (HF 4,
    MP2 5, CISD/CCSD 6, CCSD(T) 7); the FCI space of n electrons in m
    orbitals (alpha and beta strings) has C(m, n/2)^2 determinants
    (H2O/6-31G frozen core: C(12, 4)^2). Measured timings t(N) give the
    effective exponent as the least-squares slope of log t vs log N over
    the three largest N. Atomisation energies of nine molecules with DFT
    functionals of the five rungs (Perdew 2001) and wave-function methods,
    against a CCSD(T)/CBS reference; mean absolute errors. All energies
    and timings were computed by the author of v1.0 with PySCF.

§2 ALGORITHM
    Direct evaluation in v1.0 order (binomials r = r (n-k+i)/i in doubles).

§3 APPLICATIONS
    Endpoints lad.meta, lad.fci, lad.cost, lad.times, lad.tae.

§4 SPECIFICATION
    fci(mol) -> {pts: [{k, err: {method: mEh or None}, frac, E}]}; cost(f) ->
    {fac: [f^p], d1, dF}; times() -> {series: {m: [[log N, log t]]}, slope};
    tae(i) -> {ref, rows: [[method, De, De - ref]]}. Tier: bitwise vs v1.0
    on Linux/glibc (f^p by the platform pow).

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    Missing values (non-converged CCSD, timings not run) stay None.
§7 TEST CASES (tests/test_ladder.py)
    At equilibrium the hierarchy is ordered |MP2| > |CISD| > |CCSD| >
    |CCSD(T)| errors (HF); CCSD(T) below FCI at k = 2.5 (the known
    non-variational failure); C(12, 4)^2 = 245025; the slope of exact
    power-law data is recovered; vs v1.0.
§8 ERROR ANALYSIS
    Differences of energies ~100 Eh given to 1e-8: errors carry 1e-8 Eh
    (1e-5 mEh); binomials exact below 2^53, beyond rounded (only printed
    with 2 significant digits).
"""
from __future__ import annotations

import json
from pathlib import Path

from .jsmath import js_pow, log10

D = json.loads((Path(__file__).parent / "data" / "ladder_methods.json").read_text(encoding="utf-8"))
ME = ["MP2", "CISD", "CCSD", "CCSD(T)"]
COSTP = [4, 5, 6, 6, 7, None]
TM = ["HF", "MP2", "CCSD", "(T)"]
WF = ["HF", "MP2", "CCSD", "CCSD(T)"]


def fci(mol: str) -> dict:
    pts = []
    for q in D["fci"][mol]:
        ec = q["FCI"] - q["HF"]
        err = {m: ((q[m] - q["FCI"]) * 1000 if q.get(m) is not None else None) for m in ["HF"] + ME + ["FCI"]}
        frac = {m: ((q[m] - q["HF"]) / ec * 100 if q.get(m) is not None else None) for m in ["HF"] + ME + ["FCI"]}
        pts.append({"k": q["k"], "E": {m: q.get(m) for m in ["HF"] + ME + ["FCI"]}, "err": err, "frac": frac})
    return {"pts": pts}


def binom(n, k):
    r = 1
    for i in range(1, k + 1):
        r = r * (n - k + i) / i
    return r


def cost(f: int) -> dict:
    b1 = binom(12, 4)
    bF = binom(12 * f, 4 * f)
    return {"fac": [js_pow(f, p) if p else None for p in COSTP], "d1": b1 * b1, "dF": bF * bF}


def fit(pts):
    n = len(pts)
    if n < 2:
        return None
    sx = sy = sxx = sxy = 0
    for x, y in pts:
        sx += x
        sy += y
        sxx += x * x
        sxy += x * y
    return (n * sxy - sx * sy) / (n * sxx - sx * sx)


def times() -> dict:
    S = D["scal"]
    series, slope = {}, {}
    for m in TM:
        pts = [[log10(s["nbf"]), log10(s[m])] for s in S if s.get(m)]
        series[m] = pts
        slope[m] = fit(pts[-3:])
    return {"nbf": [s["nbf"] for s in S], "lognbf": [log10(s["nbf"]) for s in S], "series": series, "slope": slope}


def tae() -> dict:
    T = D["tae"]
    rows = {}
    for m in T["mols"]:
        ref = T["ref"][m]
        rows[m] = {k: [v[m], v[m] - ref] for k, v in T["val"].items()}
    return {"mols": T["mols"], "ref": T["ref"], "mae": T["mae"], "rows": rows}
