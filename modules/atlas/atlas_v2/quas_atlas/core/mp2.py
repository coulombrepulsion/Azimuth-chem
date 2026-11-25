"""Perturbation theory and MP2: H2 in STO-3G order by order, the MPn series of water,
the MP2 share of the correlation energy (precomputed PySCF data, Atlas 0.80 page "mp2").

HEADER
    Model of the page "Теория возмущений и MP2" (Atlas 0.80, mp2.html:
    h2, partial, ser, tab).  Wilkinson convention, sections 1-8.  Hartree.

§1 THEORY
    Moller-Plesset partitioning H = F + (H - F).  For H2 in a minimal basis
    (two MOs sigma_g, sigma_u): E(0) = 2 eps_g, E(1) = E_HF - V_NN - E(0),
    and the only double excitation gives E(2) = -K^2 / (2 (eps_u - eps_g))
    with K the exchange integral <gg|uu>; the exact (full CI) correlation
    energy E_c = E_FCI - E_HF.  Water (6-31G, all electrons, R_e, 1.5 R_e, 2 R_e): partial
    sums E_HF + sum_{k<=n} E(k) of the MPn series against full CI.  Table:
    MP2 correlation energy as a percentage of CCSD(T) for nine molecules.
§2 ALGORITHM
    Direct evaluation in the 0.80 JavaScript order (sums left to right).
§3 APPLICATIONS
    Endpoints mp2.meta, mp2.h2, mp2.series, mp2.tab.
§4 SPECIFICATION
    h2(i) -> {e0, e1, e2, de, ec, pc, dmf} for the i-th distance;
    series(g) -> {HF, FCI, L: [{n, e, sum, err (mEh)}]} for g in 0, 1, 2;
    tab() -> {rows: [{m, MP2, CCSD, CCSDT, pc}], lo, hi, mLo, mHi}.
    Tier: bitwise vs the 0.80 page (Chromium/V8).
§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    Data: core/data/mp2_series.json (the array D of the 0.80 page, see
    REPRODUCIBILITY.md).  Series keys "1.0", "1.5", "2.0" in file order.
§7 TEST CASES (tests/test_mp2_casscf.py)
    E(0) + E(1) + V_NN = E_HF exactly by construction; E(2) from the
    closed formula equals E_MP2 - E_HF of the data to 1e-6 Eh; the
    partial sums converge to full CI at R_e (|err| < 1e-3 mEh at n = 12);
    vs the 0.80 page.
§8 ERROR ANALYSIS
    The data carry 7-9 decimals: errors of differences ~1e-8 Eh, i.e.
    1e-5 mEh -- far below the printed precision (3 decimals in mEh).
"""
from __future__ import annotations

import json
from pathlib import Path

D = json.loads((Path(__file__).parent / "data" / "mp2_series.json").read_text(encoding="utf-8"))
HK = 2625.4996
GK = list(D["series"])


def meta() -> dict:
    return {"h2": D["h2"], "size": D["size"], "nser": [len(D["series"][k]["En"]) + 1 for k in GK]}


def h2(i: int) -> dict:
    p = D["h2"][i]
    e0 = 2 * p["eg"]
    e1 = p["HF"] - p["Vnn"] - e0
    e2 = p["MP2"] - p["HF"]
    de = p["eu"] - p["eg"]
    ec = p["FCI"] - p["HF"]
    return {"p": p, "e0": e0, "e1": e1, "e2": e2, "de": de, "ec": ec, "pc": e2 / ec * 100, "dmf": (p["MP2"] - p["FCI"]) * HK}


def series(g: int) -> dict:
    s = D["series"][GK[g]]
    out = []
    t = s["HF"]
    for k, e in enumerate(s["En"]):
        t += e
        out.append({"n": k + 2, "e": e, "sum": t, "err": (t - s["FCI"]) * 1000})
    return {"HF": s["HF"], "FCI": s["FCI"], "L": out}


def tab() -> dict:
    rows = []
    for r in D["tab"]:
        ct = r["CCSD"] + r["T"]
        rows.append({"m": r["m"], "MP2": r["MP2"], "CCSD": r["CCSD"], "CCSDT": ct, "pc": r["MP2"] / ct * 100})
    pcs = [r["pc"] for r in rows]
    lo, hi = min(pcs), max(pcs)
    return {"rows": rows, "lo": lo, "hi": hi, "mLo": rows[pcs.index(lo)]["m"], "mHi": rows[pcs.index(hi)]["m"]}
