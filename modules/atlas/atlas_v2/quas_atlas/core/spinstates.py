"""Spin states of transition-metal complexes in DFT: the spin gap against the share of exact exchange, spin
contamination and the check of a solution, and the geometry that depends on the spin.

HEADER
    Model of the page "Спиновые состояния комплексов в DFT" (web/<lang>/spinstates.html), Atlas 2026-11-24; lecture
    9 of the course «Квантово-химические методы» (derivations 6 and 7, slides 11–14). Wilkinson convention, §1-8.

§1 THEORY
    Exchange: −K_ij for every pair of electrons with parallel spins. d⁶ high spin 5α + 1β: C(5,2) = 10 pairs; low spin
    3α + 3β: C(3,2) + C(3,2) = 6 pairs — four more in the high-spin state. Hartree–Fock has exact exchange and no
    correlation (the high spin too low), a GGA overestimates delocalization (the low spin too low). A hybrid
    E_xc = a E_x^HF + (1 − a) E_x^DFT + E_c gives ΔE(a) ≈ ΔE(0) − k a, the slope k larger for a more covalent
    metal–ligand bond. Spin contamination: ⟨S²⟩_exact = S(S + 1); for an unrestricted determinant
    ⟨S²⟩ = S(S + 1) + N_β − Σ_ij |⟨φ_i^α|φ_j^β⟩|² ≥ S(S + 1); the admixture of the next state S + 1 is
    (⟨S²⟩ − S(S + 1))/((S + 1)(S + 2) − S(S + 1)) — 6.9 for a quintet: 15 % of the septet. The high-spin state puts two
    electrons on the antibonding e_g*: the bonds are 0.1–0.4 Å longer, so each state is optimized separately (the
    adiabatic difference).

§2 ALGORITHM
    Least-squares lines through the five functionals of the lecture; closed formulas.

§3 APPLICATIONS
    Endpoints spin.gap, spin.contam, spin.geom.

§4 SPECIFICATION
    gap(a) -> {"complexes": [{"key", "points": [[a, ΔE]], "slope", "icept", "zero", "at"}], "functionals": [[name, a]],
        "pairs": {"hs", "ls"}}.
    contam(S, s2) -> {"exact", "next", "admix", "excess", "ladder": [[S, S(S+1)]]}.
    geom(key) -> {"quintet": [r×6], "singlet": [r×6], "mean_q", "mean_s", "dr"}.

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    Standard library only (Pyodide). ΔE = E_HS − E_LS in kJ/mol, negative: the high-spin ground state.
§7 TEST CASES (tests/atlas/test_atlas_spin.py)
    The slopes −1.48, −4.69, −7.80 kJ/mol per 1 % and the sign changes at 18.7 % (NCH) and 38.4 % (CO); 10 and 6
    exchange pairs; ⟨S²⟩ = 6.9 for a quintet — 15 % of the septet; the mean Fe–L lengths of the lecture.
§8 ERROR ANALYSIS
    The data: ORCA 6.0.1, def2-SVP at TPSSh/def2-SVP geometries (quintet and singlet optimized separately), the
    teacher's calculation of 22.11.2026 (lecture 9, remarks). The points of different families do not lie exactly on
    one line (PBE0 above B3LYP for CO).
"""

FUNCTIONALS = [("BP86", 0.0), ("TPSSh", 10.0), ("B3LYP", 20.0), ("PBE0", 25.0), ("BHandHLYP", 50.0)]
GAPS = {"water": [-116.2, -122.5, -135.5, -172.2, -184.1],
        "nch": [99.8, 40.0, -16.9, -39.4, -137.2],
        "co": [317.1, 206.8, 119.5, 123.1, -86.5]}
BONDS = {"water": ((2.121, 2.146), 1.999), "nch": ((2.161, 2.172), 1.926), "co": ((2.254, 2.298), 1.919)}


def _fit(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    return b, my - b * mx


def gap(a=20.0):
    """ΔE(HS − LS) of three Fe(II) complexes for five functionals, the lines through them and their values at a %."""
    if not 0 <= a <= 60:
        raise ValueError("a 0..60 %")
    xs = [f[1] for f in FUNCTIONALS]
    out = []
    for key, ys in GAPS.items():
        b, c = _fit(xs, ys)
        out.append({"key": key, "points": [[x, y] for x, y in zip(xs, ys)], "slope": b, "icept": c,
                    "zero": -c / b if -c / b > 0 else None, "at": c + b * a})
    return {"complexes": out, "functionals": [list(f) for f in FUNCTIONALS], "pairs": {"hs": 10, "ls": 6}, "a": a}


def contam(S=2.0, s2=6.9):
    """The exact ⟨S²⟩ of spin S, the excess of a measured s2 and the admixture of the state S + 1."""
    if not (0 <= S <= 3 and abs(2 * S - round(2 * S)) < 1e-9 and 0 <= s2 <= 20):
        raise ValueError("S 0, ½, …, 3; s2 0..20")
    ex, nx = S * (S + 1), (S + 1) * (S + 2)
    return {"exact": ex, "next": nx, "excess": s2 - ex, "admix": (s2 - ex) / (nx - ex),
            "ladder": [[k / 2, k / 2 * (k / 2 + 1)] for k in range(0, 9)], "S": S, "s2": s2}


def geom(key="water"):
    """The six Fe–L bonds of the quintet (two short, four long) and of the singlet."""
    if key not in BONDS:
        raise ValueError("key water|nch|co")
    (short, long_), rs = BONDS[key]
    q = [short, short, long_, long_, long_, long_]
    mq = sum(q) / 6
    return {"quintet": q, "singlet": [rs] * 6, "mean_q": mq, "mean_s": rs, "dr": mq - rs,
            "all": {k: {"mean_q": (2 * v[0][0] + 4 * v[0][1]) / 6, "mean_s": v[1]} for k, v in BONDS.items()}}
