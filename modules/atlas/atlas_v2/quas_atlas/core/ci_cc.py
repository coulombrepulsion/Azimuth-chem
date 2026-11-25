"""Configuration interaction and coupled clusters from the inside: number of determinants, 2x2 CI of
H2/STO-3G, size consistency of CISD vs CCSD, configuration weights of a non-interacting dimer.

HEADER
    Model of the page "КВ и связанные кластеры изнутри" (v1.0 ci-cc.js:
    MOL, lnC, lse, levels, ci2, pairModel, sz, amp; data D = {h2, size}).
    Wilkinson convention, sections 1-8. Hartree atomic units.

§1 THEORY
    Determinant count: N electrons (N/2 alpha, N/2 beta) in n spatial
    orbitals; excitation level k = k_alpha + k_beta, the number of
    determinants with k_alpha alpha and k_beta beta excitations is
    C(a, k_a) C(v, k_a) C(a, k_b) C(v, k_b) (a = N/2 occupied, v = n - a
    virtual); full CI = C(n, a)^2. Computed in logarithms (log-sum-exp)
    to avoid overflow. Orbital counts of the molecules: all-electron,
    spherical d (H2O 7/18*/24/58 ...).
    H2/STO-3G: in the basis of sigma_g^2 and sigma_u^2 the CI matrix is
    [[E_g, K], [K, E_u]] with K = (sigma_g sigma_u | sigma_g sigma_u); its
    lowest root is the full CI. The electronic energies E_g, E_u and K on
    73 distances were computed by the author of v1.0 (data/ci_cc_h2.json);
    the (H2)_n series in 6-31G (10 A apart) with PySCF (HF, CISD, CCSD,
    CCSD(T), FCI).
    n non-interacting H2 in the minimal model: FCI = n e_1 with e_1 =
    (d - sqrt(d^2 + 4K^2))/2, d = E_u - E_g; CISD reduces to an (n+1) x
    (n+1) matrix with the lowest root (d - sqrt(d^2 + 4 n K^2))/2 (grows
    like sqrt n). Dimer: FCI coefficients are products c_i c_j; CCSD
    reproduces c_2^2 through T2^2/2 with t2 = c2/c0; CISD in {00, 20, 02}
    has the root (d - sqrt(d^2 + 8K^2))/2.

§2 ALGORITHM
    As v1.0 (same formula order).

§3 APPLICATIONS
    Endpoints cicc.dets, cicc.h2, cicc.state.

§4 SPECIFICATION
    dets(m, b) -> {e, n, L (ln counts per level), lg, tot, cisd, nS, nD,
      nCISD, nFCI, gb, hi}; h2() -> {R, all, sz1}; state(i) -> {p, r, w0,
      w2, corr, sz0, amp}. Tier: bitwise vs v1.0 on Linux/glibc (EXACT).

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    Math.log/log1p/exp from jsmath; Math.hypot(...) -> js_hypot.
§7 TEST CASES (tests/test_ci_cc.py)
    Total of the level counts = C(n, a)^2 (exact integer, 1e-12 relative
    in logs); singles = 2 a v, doubles = 2 C(a,2) C(v,2) + a^2 v^2; the 2x2
    CI root against numpy.linalg.eigvalsh (1e-12); the CISD (n+1)x(n+1)
    model against an explicit matrix diagonalisation for n = 1..6;
    dimer CISD error > 0; CCSD weights equal FCI weights; vs v1.0.
§8 ERROR ANALYSIS
    Log-sum-exp keeps ~1e-15 relative accuracy for the counts (printed to
    2 digits); all other quantities are closed forms.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from .jsmath import exp, hypot3, js_hypot, log, log1p

D = json.loads((Path(__file__).parent / "data" / "ci_cc_h2.json").read_text(encoding="utf-8"))
P = D["h2"]
SZ = D["size"]
MOL = [{"e": 10, "o": [7, 18, 24, 58]}, {"e": 14, "o": [10, 28, 28, 60]}, {"e": 42, "o": [36, 96, 114, 264]}]
NINF = -math.inf
LN10 = math.log(10)


def ln_c(n, k):
    if k < 0 or k > n:
        return NINF
    s = 0
    for i in range(1, k + 1):
        s += log((n - k + i) / i)
    return s


def lse(a, b):
    if a == NINF:
        return b
    if b == NINF:
        return a
    return max(a, b) + log1p(exp(-abs(a - b)))


def levels(N, n):
    a = N / 2
    v = n - a
    L = []
    for k in range(int(2 * a) + 1):
        s = NINF
        for ka in range(k + 1):
            kb = k - ka
            s = lse(s, ln_c(a, ka) + ln_c(v, ka) + ln_c(a, kb) + ln_c(v, kb))
        if s == NINF:
            break
        L.append(s)
    return L


def dets(m: int, b: int) -> dict:
    M = MOL[m]
    n = M["o"][b]
    L = levels(M["e"], n)
    tot = NINF
    for x in L:
        tot = lse(tot, x)
    cisd = lse(lse(L[0], L[1]), L[2])
    return {"e": M["e"], "n": n, "L": L, "lg": [v / LN10 for v in L], "tot": tot, "cisd": cisd,
            "nS": exp(L[1]), "nD": exp(L[2]), "nCISD": exp(cisd), "nFCI": exp(tot), "gb": exp(tot) * 8 / 1e9,
            "hi": math.ceil(tot / LN10) + 1}


def ci2(p) -> dict:
    a, b, k = p["Eg"], p["Eu"], p["K"]
    d = (b - a) / 2
    s = math.sqrt(d * d + k * k)
    E = (a + b) / 2 - s
    c0, c2 = k, E - a
    nn = js_hypot(c0, c2)
    c0 /= nn
    c2 /= nn
    if c0 < 0:
        c0, c2 = -c0, -c2
    return {"E": E + p["Vnn"], "Ehf": a + p["Vnn"], "c0": c0, "c2": c2}


def pair_model(p, n) -> dict:
    d = p["Eu"] - p["Eg"]
    k = p["K"]
    one = (d - math.sqrt(d * d + 4 * k * k)) / 2
    cisd = (d - math.sqrt(d * d + 4 * n * k * k)) / 2
    return {"fci": n * one, "cisd": cisd}


SZN = [1, 2, 3, 4, 5, 6, 8, 10, 15, 20, 30, 50, 100]


def sz1() -> list:
    rows = []
    for s in SZ:
        c = s["FCI"] - s["HF"]
        n = s["n"]
        rows.append({"n": n, "CISD": (s["CISD"] - s["HF"]) / c, "CCSD": (s["CCSD"] - s["HF"]) / c, "CCSD(T)": (s["CCSD(T)"] - s["HF"]) / c,
                     "FCI": 1, "e": {"CISD": s["CISD"] - s["HF"], "CCSD": s["CCSD"] - s["HF"], "FCI": c}, "s": s,
                     "pn": {k: (s[k] - s["HF"]) * 1000 / n for k in ("FCI", "CISD", "CCSD", "CCSD(T)")}})
    return rows


def h2() -> dict:
    return {"R": [p["R"] for p in P], "all": [ci2(p) for p in P], "sz1": sz1()}


def amp(p) -> dict:
    r = ci2(p)
    fci = [r["c0"] * r["c0"], r["c0"] * r["c2"], r["c0"] * r["c2"], r["c2"] * r["c2"]]
    d = p["Eu"] - p["Eg"]
    k = p["K"]
    lam = (d - math.sqrt(d * d + 8 * k * k)) / 2
    v = [1, k / (lam - d), k / (lam - d)]
    nn = hypot3(*v)
    v = [x / nn for x in v]
    t2 = r["c2"] / r["c0"]
    cc = [1, t2, t2, t2 * t2]
    nc = js_hypot(*cc)
    e1 = r["E"] - p["Vnn"]
    return {"fci": fci, "cisd": [v[0], v[1], v[2], 0], "t2": t2, "ccn": [x / nc for x in cc], "err": (lam - 2 * (e1 - p["Eg"])) * 1000}


def state(i: int) -> dict:
    p = P[i]
    r = ci2(p)
    rows = []
    for n in SZN:
        m = pair_model(p, n)
        rows.append({"n": n, "CISD": m["cisd"] / m["fci"], "CCSD": 1, "FCI": 1, "e": {"CISD": m["cisd"], "FCI": m["fci"]}})
    r10, r100 = pair_model(p, 10), pair_model(p, 100)
    return {"p": p, "r": r, "w0": r["c0"] * r["c0"], "w2": r["c2"] * r["c2"], "corr": (r["E"] - r["Ehf"]) * 1000,
            "sz0": {"rows": rows, "p10": r10["cisd"] / r10["fci"] * 100, "p100": r100["cisd"] / r100["fci"] * 100}, "amp": amp(p)}
