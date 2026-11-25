"""From Hückel to NDDO and xtb: how many two-electron integrals each level keeps (Atlas).

HEADER
    Model of the panel "От Хюккеля к xtb: полуэмпирические методы" of the page "Метод Хюккеля"
    (web/<lang>/huckel.html). Wilkinson convention, sections 1-8.

§1 THEORY
    In a basis of N functions the two-electron integrals (μν|λσ) number N⁴/8 (exactly with the 8-fold
    permutational symmetry: M(M + 1)/2 with M = N(N + 1)/2). Semi-empirical methods keep the valence shell
    in a minimal basis (s, p on heavy atoms, s on H) and neglect differential overlap (ZDO, χ_μ χ_ν = 0 for
    μ ≠ ν in two-electron integrals):
        CNDO — one parameter γ_AB per pair of atoms: K(K + 1)/2 values (K atoms);
        INDO — CNDO plus the one-centre exchange integrals of each heavy atom;
        NDDO (MNDO, AM1, PM3, PM6, PM7) — all integrals (μ_Aν_A|λ_Bσ_B) with μ, ν on one atom and λ, σ on one
        atom: Σ_{A ≤ B} m_A m_B (pairs counted once; m_A = n_A(n_A + 1)/2 distinct products on atom A);
        Hückel (π) — no explicit two-electron integrals at all; extended Hückel — none either (overlap kept);
        GFN2-xTB — a tight-binding expansion: monopole, dipole and quadrupole interactions of atomic charges,
        D4 dispersion; parameters for the whole periodic table up to Rn.
    Minimal-basis ab initio (STO-3G) on the same molecule has N = 5 per first-row heavy atom (1s 2s 2p),
    1 per H; a split-valence 6-31G* about 15 per heavy atom and 2 per H.

§2 ALGORITHM
    Direct counts for n heavy atoms (C–F) and m hydrogens.

§3 APPLICATIONS
    Endpoint semi.count.

§4 SPECIFICATION
    count(n, m) -> {"N_val", "ab_sto3g", "ab_631gs", "nddo", "indo", "cndo", "N_sto3g", "N_631gs"}.

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    6-31G* with 6 Cartesian d: 15 functions per C–F atom, 2 per H (6-31G**) would add 3 per H — here 6-31G*, 2.
§7 TEST CASES (tests/test_atlas_course1.py)
    Benzene (6, 6): N_val = 30, NDDO integrals far fewer than ab initio; counts grow as N⁴ vs pairs.
§8 ERROR ANALYSIS
    Exact integer arithmetic.
"""
from __future__ import annotations


def _eri(N: int) -> int:
    M = N * (N + 1) // 2
    return M * (M + 1) // 2


def count(n: int, m: int) -> dict:
    if not (0 <= n <= 5000 and 0 <= m <= 5000 and n + m >= 1):  # was 500 and 1000
        raise ValueError("n, m: 0..5000 atoms")
    nv = 4 * n + m
    pair_heavy = 10  # distinct products s,p on one heavy atom: 4·5/2
    pa = [pair_heavy] * n + [1] * m
    K = n + m
    tot = sum(pa)
    nddo = (tot * tot + sum(x * x for x in pa)) // 2  # Σ_{A<=B} m_A m_B
    indo = K * (K + 1) // 2 + 5 * n  # γ_AB plus a few one-centre exchange integrals per heavy atom (s-p, p-p)
    return {"N_val": nv, "N_sto3g": 5 * n + m, "N_631gs": 15 * n + 2 * m,
            "ab_sto3g": _eri(5 * n + m), "ab_631gs": _eri(15 * n + 2 * m),
            "nddo": nddo, "indo": indo, "cndo": K * (K + 1) // 2}
