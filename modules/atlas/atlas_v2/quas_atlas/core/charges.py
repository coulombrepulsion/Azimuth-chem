"""Atomic charges: Mulliken, Loewdin and Bader charges of nine molecules in four basis sets,
point-charge dipoles against the dipole of the total density.

HEADER
    Model of the page "Атомные заряды: сравнение схем" (v1.0 charges.js:
    labels, uniq, draw, chart, dip). Wilkinson convention, sections 1-8.
    Coordinates in bohr, charges in e, dipoles in debye.

§1 THEORY
    Partial charges are not observables; each scheme partitions the RHF
    density differently. Mulliken: q_A = Z_A - sum_{mu in A} (PS)_mumu;
    Loewdin: the same in the symmetrically orthogonalised basis,
    q_A = Z_A - sum_{mu in A} (S^1/2 P S^1/2)_mumu; Bader (QTAIM): Z_A minus
    the density integrated over the zero-flux basin of A. The dipole of a
    set of point charges is mu_q = sum_A q_A R_A (origin-independent for a
    neutral molecule); the dipole of the total density mu = sum_A Z_A R_A -
    int r rho(r) dr is the physical one. 1 e a0 = 2.541746 D. The
    density dipole and the point-charge dipole are compared in magnitude
    and in direction (sign of mu . mu_q). Experimental dipole moments
    (magnitudes; NIST CCCBDB, experimental section): H2O 1.85, NH3 1.47,
    HF 1.83, LiH 5.88, LiF 6.33, CO 0.11, F2CO 0.95; CH4 and CO2 are zero by
    symmetry.

§2 ALGORITHM
    The RHF results (energy, number of basis functions, charges, dipole in
    a.u.) were computed by the author of v1.0 and are data here
    (data/charges_rhf.json). The 6-31G* and 6-31G** sets use six
    Cartesian d functions (nbf of H2O/6-31G* = 19). Point-charge dipole:
    v_c += q_A R_A,c over the atoms in order, |v| by hypot.

§3 APPLICATIONS
    Endpoints charges.meta, charges.view, charges.series.

§4 SPECIFICATION
    view(m, b) -> {id, nbf, E, q: {mul, low, bad|None}, mu, exp,
      dip: {scheme: {mq, dir}|None}}; dir = 1 (same direction), -1
      (opposite), 0 (either dipole < 0.05 D, direction not meaningful).
    series(m, i) -> charge of atom i in the four basis sets, per scheme.
    Tier: bitwise vs v1.0 on Linux/glibc (EXACT).

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    The data are not recomputed at run time; see REPRODUCIBILITY. Bader
    charges of HF/STO-3G are missing (v1.0: no hydrogen basin found).
§7 TEST CASES (tests/test_charges.py)
    Charges of every molecule, basis and scheme sum to zero (neutral, 1e-3
    from the 4-digit rounding); |mu| = 0 for CH4 and CO2; Mulliken q(Li) <
    0 in LiH/STO-3G (the textbook artefact); STO-3G Mulliken charges and
    dipoles reproduced by an independent PySCF run (optional, if PySCF is
    installed); vs v1.0.
§8 ERROR ANALYSIS
    The stored charges and dipoles carry 4 decimals: the point-charge
    dipole has an absolute error <= 0.5e-4 * sum |R_A| * 2.54 D (< 0.003 D
    for these molecules), below the 0.01 D printed. The Bader charges come
    from a numerical basin integration and break the symmetry slightly: the
    point-charge dipole of CH4 is up to 0.013 D instead of 0.
"""
from __future__ import annotations

import json
from pathlib import Path

from .jsmath import hypot3

D = json.loads((Path(__file__).parent / "data" / "charges_rhf.json").read_text(encoding="utf-8"))
B = ["STO-3G", "6-31G", "6-31G*", "6-31G**"]
SCH = ["mul", "low", "bad"]
AU2D = 2.541746
EXP = {"H2O": 1.85, "NH3": 1.47, "HF": 1.83, "LiH": 5.88, "LiF": 6.33, "CO": 0.11, "F2CO": 0.95, "CH4": 0, "CO2": 0}


def labels(m: dict) -> list[str]:
    cnt: dict = {}
    out = []
    for a in m["at"]:
        cnt[a[0]] = cnt.get(a[0], 0) + 1
        many = sum(1 for x in m["at"] if x[0] == a[0]) > 1
        out.append(a[0] + (str(cnt[a[0]]) if many else ""))
    return out


def uniq(m: dict) -> list[int]:
    seen, out = [], []
    for i, a in enumerate(m["at"]):
        if a[0] not in seen:
            seen.append(a[0])
            out.append(i)
    return out


def meta() -> dict:
    return {"B": B, "mols": [{"id": m["id"], "n": m["n"], "L": labels(m), "uniq": uniq(m),
                              "hasH": any(a[0] == "H" for a in m["at"])} for m in D]}


def point_dipole(m: dict, q: list[float]) -> list[float]:
    v = [0, 0, 0]
    for i, a in enumerate(m["at"]):
        for c in range(3):
            v[c] += q[i] * a[c + 1]
    return v


def view(mi: int, b: str) -> dict:
    m = D[mi]
    r = m["b"][b]
    mu = hypot3(*r["mu"]) * AU2D
    dip = {}
    for k in SCH:
        if not r.get(k):
            dip[k] = None
            continue
        v = point_dipole(m, r[k])
        mq = hypot3(*v) * AU2D
        dot = v[0] * r["mu"][0] + v[1] * r["mu"][1] + v[2] * r["mu"][2]
        dip[k] = {"mq": mq, "dir": (1 if dot >= 0 else -1) if (mu > 0.05 and mq > 0.05) else 0}
    return {"id": m["id"], "nbf": r["nbf"], "E": r["E"], "q": {k: r.get(k) or None for k in SCH}, "mu": mu,
            "exp": EXP[m["id"]], "dip": dip}


def series(mi: int, i: int) -> list[list]:
    m = D[mi]
    return [[m["b"][b][k][i] if m["b"][b].get(k) else None for b in B] for k in SCH]
