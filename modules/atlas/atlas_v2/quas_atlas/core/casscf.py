"""Multiconfigurational methods: CASSCF curves of H2, ethylene torsion and N2 dissociation,
size of the active space (precomputed PySCF data, Atlas 0.80 page "casscf").

HEADER
    Model of the page "Многоконфигурационные методы: CASSCF" (Atlas 0.80,
    casscf.html: h2, eth, n2, lnC, cas).  Wilkinson convention, §1-§8.

§1 THEORY
    CASSCF(n, m): full CI of n electrons in m active orbitals with the
    orbitals optimised; NEVPT2 adds dynamic correlation.  Data (cc-pVDZ,
    PySCF): H2 RHF/UHF/CASSCF(2,2)/FCI with <S^2> of UHF and natural
    occupations; ethylene torsion RHF/CASSCF(2,2)/NEVPT2 (rigid rotor);
    N2 RHF/CCSD/CCSD(T)/CASSCF(6,6)/NEVPT2.  Active-space size: Ms = 0
    determinants C(m, n/2)^2 and singlet CSFs (Weyl) C(m+1, n/2) C(m+1,
    n/2+1)/(m+1), evaluated through ln C = sum ln((n-k+i)/i).
§2 ALGORITHM
    Direct evaluation in the 0.80 JavaScript order.
§3 APPLICATIONS
    Endpoints cas.meta, cas.h2, cas.eth, cas.n2, cas.size.
§4 SPECIFICATION
    h2(i) -> {d: {method: (E - E_FCI) kJ/mol}}; eth(i) -> {r: {method:
    [dE kJ/mol]}, ymax, b, at}; n2(i) -> {rel: {method: [eV or None]},
    De, dT, low}; size(ne, no) -> {n, m, det, csf, gb, mb}.
    Tier: bitwise vs the 0.80 page (V8; ln/exp by core.jsmath).
§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    Data: core/data/casscf_curves.json (array D of the 0.80 page).  None
    marks non-converged CCSD points.
§7 TEST CASES (tests/test_mp2_casscf.py)
    CAS(6,6): 400 determinants, 175 singlet CSFs; CAS(2,2): 4 and 3;
    CAS(12,12) 853776 determinants; CASSCF between RHF and FCI for H2;
    vs the 0.80 page.
§8 ERROR ANALYSIS
    ln C summed in doubles: relative error < 1e-14 per term; the counts
    are printed rounded (exact for < 1e5).
"""
from __future__ import annotations

import json
from pathlib import Path

from .jsmath import exp, log

D = json.loads((Path(__file__).parent / "data" / "casscf_curves.json").read_text(encoding="utf-8"))
HK, EV = 2625.4996, 27.211386
N2K = ("RHF", "CCSD", "CCSDT", "CAS", "NEVPT2")


def meta() -> dict:
    return {"h2": D["h2"], "H2at": 2 * D["hatom"], "eth": D["eth"], "n2": D["n2"]}


def h2(i: int) -> dict:
    p = D["h2"][i]
    return {"d": {k: (p[k] - p["FCI"]) * HK for k in ("RHF", "UHF", "CAS", "FCI")}}


def eth(i: int) -> dict:
    E = D["eth"]
    r = {k: [None if q.get(k) is None else (q[k] - E[0][k]) * HK for q in E] for k in ("RHF", "CAS", "NEVPT2")}
    b = {k: (E[-1][k] - E[0][k]) * HK for k in ("RHF", "CAS", "NEVPT2")}
    p = E[i]
    return {"r": r, "b": b, "at": {k: (p[k] - E[0][k]) * HK for k in ("RHF", "CAS", "NEVPT2")}}


def n2(i: int) -> dict:
    N = D["n2"]
    rel = {k: [None if (q.get(k) is None or N[2].get(k) is None) else (q[k] - N[2][k]) * EV for q in N] for k in N2K}
    last = N[-1]
    De = {k: (last[k] - N[2][k]) * EV for k in ("RHF", "CAS", "NEVPT2")}
    p = N[i]
    dT = ((p["CCSDT"] - N[2]["CCSDT"]) - (p["NEVPT2"] - N[2]["NEVPT2"])) * EV if (p.get("CCSDT") is not None and p.get("NEVPT2") is not None) else None
    return {"rel": rel, "De": De, "dT": dT, "low": -rel["CCSDT"][len(N) - 4]}


def ln_c(n: float, k: float) -> float:
    if k < 0 or k > n:
        return -float("inf")
    s = 0
    i = 1
    while i <= k:
        s += log((n - k + i) / i)
        i += 1
    return s


def size(ne: int, no: int) -> dict:
    n, m = ne, no
    if n > 2 * m:
        n = 2 * m
    det = exp(2 * ln_c(m, n / 2))
    csf = exp(ln_c(m + 1, n / 2) + ln_c(m + 1, n / 2 + 1)) / (m + 1)
    return {"n": n, "m": m, "det": det, "csf": csf, "gb": det * 8 / 1e9, "mb": det * 8 / 1e6}
