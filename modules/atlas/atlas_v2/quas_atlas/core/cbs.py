"""Basis-set convergence and complete-basis-set (CBS) extrapolation of precomputed energies.

HEADER
    Model of the page "Сходимость по базису и предел полного базиса" (v1.0
    cbs.js: corr, cbsC, tae, taeCBS, val, limit, conv, xtab, taeC).
    Wilkinson convention, sections 1-8.

§1 THEORY
    In the correlation-consistent series cc-pVXZ (X = 2, 3, 4, 5) the
    correlation energy converges as E_c(X) = E_c(CBS) + A X^-3 (Helgaker,
    Klopper, Koch, Noga 1997); two consecutive X, Y give
        E_c(CBS) = (X^3 E_c(X) - Y^3 E_c(Y)) / (X^3 - Y^3),
    while the Hartree-Fock energy converges almost exponentially and is
    taken from the largest basis. Atomisation energy D_e = sum_atoms E -
    E(molecule) (CCSD(T)), x 627.5095 kcal/mol per hartree; its CBS value
    uses HF(QZ) + the TZ/QZ correlation extrapolation for every species.
    HF, MP2, CCSD, CCSD(T) energies of nine molecules and their atoms in
    cc-pVXZ were computed by the author of v1.0 with PySCF (data
    data/cbs_energies.json; geometries not stated on the page).

§2 ALGORITHM
    Direct evaluation in v1.0 operation order.

§3 APPLICATIONS
    Endpoints cbs.meta, cbs.conv, cbs.xtab, cbs.tae.

§4 SPECIFICATION
    conv(m, q in 0..3) -> {xs, nbf, v, L, xinv, steps, toL, ratios, remain, remainKcal}
      q: 0 HF (E_h), 1 E_c(MP2) (mE_h), 2 E_c(CCSD(T)) (mE_h), 3 D_e (kcal/mol).
    xtab(p in 0..2) -> {rows: [{m, e, x, b, de, dx}], has5} (pairs 2/3, 3/4, 4/5)
    tae() -> {err: [[D_e(X) - D_e(CBS) for X = 2, 3, 4]], tab: [[D_e(2), (3), (4), CBS]]}
    Tier: bitwise vs v1.0 on Linux/glibc (X^-3 by the platform pow, as V8).

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    X**3 with integer X is exact in both languages.
§7 TEST CASES (tests/test_cbs.py)
    The extrapolation formula is exact for E = E_inf + A X^-3; HF steps
    shrink (DZ->TZ > TZ->QZ > QZ->5Z) for every molecule with 5Z; CBS D_e of
    N2 below the experimental 228.5 kcal/mol by less than 2.5 (D_e = D_0 + ZPE
    removal); found 226.6, i.e. 1.9 below -- the known shortfall of valence
    CCSD(T)/CBS(TZ/QZ) without core-valence correlation; vs v1.0.
§8 ERROR ANALYSIS
    Energies ~1e2 hartree with 9 decimals: differences of correlation
    energies lose ~1e-14 relative; the extrapolation amplifies the
    difference by Y^3/(Y^3 - X^3) < 2.5 -> errors < 1e-11 mE_h, far below
    the 0.1 mE_h printed.
"""
from __future__ import annotations

import json
from pathlib import Path

from .jsmath import js_pow

D = json.loads((Path(__file__).parent / "data" / "cbs_energies.json").read_text(encoding="utf-8"))
S = D["e"]
HK = 627.5095
PAIRS = [(2, 3), (3, 4), (4, 5)]


def xs_of(sp):
    return sorted(int(k) for k in S[sp])


def corr(sp, X, m):
    return S[sp][str(X)][m] - S[sp][str(X)]["HF"]


def cbs_c(sp, m, X, Y):
    a, b = corr(sp, X, m), corr(sp, Y, m)
    return (X ** 3 * a - Y ** 3 * b) / (X ** 3 - Y ** 3)


def _sum_atoms(m, E):
    s = 0
    for a, n in D["comp"][m].items():
        s = s + n * E(a)
    return s


def tae(m, X):
    def E(sp):
        return S[sp][str(X)]["CCSD(T)"]
    return (_sum_atoms(m, E) - E(m)) * HK


def tae_cbs(m, X, Y):
    def E(sp):
        return S[sp][str(Y)]["HF"] + cbs_c(sp, "CCSD(T)", X, Y)
    return (_sum_atoms(m, E) - E(m)) * HK


def _val(m, X, q):
    if q == 0:
        return S[m][str(X)]["HF"]
    if q == 1:
        return corr(m, X, "MP2") * 1000
    if q == 2:
        return corr(m, X, "CCSD(T)") * 1000
    return tae(m, X)


def _limit(m, q):
    xs = xs_of(m)
    Y = xs[-1]
    if q == 0:
        return None
    if q == 3:
        return tae_cbs(m, 3, 4)
    return cbs_c(m, "MP2" if q == 1 else "CCSD(T)", Y - 1, Y) * 1000


def meta() -> dict:
    return {"mols": D["mols"], "has5": [m for m in D["mols"] if "5" in S[m]]}


def conv(i: int, q: int) -> dict:
    m = D["mols"][i]
    xs = xs_of(m)
    v = [_val(m, X, q) for X in xs]
    L = _limit(m, q)
    st = [v[j + 1] - v[j] for j in range(len(xs) - 1)]
    out = {"xs": xs, "nbf": [S[m][str(X)]["nbf"] for X in xs], "v": v, "L": L, "xinv": [js_pow(X, -3) for X in xs],
           "steps": [None] + st, "toL": [x - L for x in v] if L is not None else None,
           "ratios": [st[j] / s for j, s in enumerate(st[1:])]}
    if L is not None:
        out["remain"] = abs(v[-1] - L)
        out["remainKcal"] = abs(v[-1] - L) / 1000 * HK
    return out


def _best(m):
    return cbs_c(m, "CCSD(T)", 4, 5) if "5" in S[m] else cbs_c(m, "CCSD(T)", 3, 4)


def xtab(p: int) -> dict:
    X, Y = PAIRS[p]
    rows = []
    for m in D["mols"]:
        if str(Y) not in S[m]:
            continue
        b, e, x = _best(m) * 1000, corr(m, Y, "CCSD(T)") * 1000, cbs_c(m, "CCSD(T)", X, Y) * 1000
        rows.append({"m": m, "e": e, "x": x, "b": b, "de": e - b, "dx": x - b})
    return {"rows": rows, "has5": meta()["has5"]}


def tae_all() -> dict:
    err, tab = [], []
    for m in D["mols"]:
        ref = tae_cbs(m, 3, 4)
        err.append([tae(m, X) - ref for X in (2, 3, 4)])
        tab.append([tae(m, X) for X in (2, 3, 4)] + [ref])
    return {"err": err, "tab": tab}
