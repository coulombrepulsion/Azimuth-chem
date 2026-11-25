"""Basis-set superposition error of the water dimer: precomputed energies, counterpoise
correction, minima of the binding curves.

HEADER
    Model of the page "Суперпозиционная ошибка базиса" (v1.0 bsse.js: bars,
    curve, minOf, scan). Wilkinson convention, sections 1-8.

§1 THEORY
    Interaction energy dE = E(AB) - E(A) - E(B). With monomer energies in
    the monomer basis each monomer of the dimer "borrows" functions of the
    partner, which lowers E(AB) artificially (BSSE). Counterpoise (Boys and
    Bernardi 1970): monomers in the full dimer basis (ghost atoms), dE_cp;
    BSSE = dE - dE_cp. Energies HF, MP2, CCSD(T) of (H2O)2 in eleven basis
    sets and MP2 scans in R(O...O) were computed by the author of v1.0
    with PySCF and are data here (data/bsse_water_dimer.json; kcal/mol).
    The minimum of a scan is the vertex of the parabola through the lowest
    point and its two neighbours (three-point interpolation).

§2 ALGORITHM
    bars: per basis raw, cp, BSSE = raw - cp, mean (raw + cp)/2.
    scan: points sorted by R; min_of: argmin k (first on ties), parabola
    y = A x^2 + B x + C through (x_{k-1}, x_k, x_{k+1}), x_m = -B/(2A).

§3 APPLICATIONS
    Endpoints bsse.bars, bsse.scan.

§4 SPECIFICATION
    bars(m in HF, MP2, CCSD(T)) -> {rows: [{b, nbf, raw, cp, bsse, avg}], ref}
    scan(b) -> {raw: [[R, E]], cp, best (aug-cc-pVTZ cp), minRaw: [R, E], minCp}
    Tier: bitwise vs v1.0.

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    The data are not recomputed at run time; see REPRODUCIBILITY.
§7 TEST CASES (tests/test_bsse.py)
    BSSE > 0 for every basis and method (counterpoise always raises dE);
    BSSE decreases from cc-pVDZ to cc-pVQZ; min_of of an exact parabola
    returns its vertex; vs v1.0.
§8 ERROR ANALYSIS
    The interpolation is exact for a parabola; for the scans (0.1 A grid)
    its truncation error is O(h^2 E''') ~ 0.01 A in R, below the precision
    printed (0.01 A, 0.01 kcal/mol). Arithmetic error < 1e-13.
"""
from __future__ import annotations

import json
from pathlib import Path

D = json.loads((Path(__file__).parent / "data" / "bsse_water_dimer.json").read_text(encoding="utf-8"))
METH = ["HF", "MP2", "CCSD(T)"]


def bars(m: str) -> dict:
    rows = []
    for b in D["order"]:
        r = D["bas"][b].get(m)
        if not r:
            continue
        rows.append({"b": b, "nbf": D["bas"][b]["nbf"], "raw": r["raw"], "cp": r["cp"], "bsse": r["raw"] - r["cp"],
                     "avg": (r["raw"] + r["cp"]) / 2})
    return {"rows": rows, "ref": D["ref"].get(m)}


def curve(b: str, kind: str):
    return sorted(([float(R), v["MP2"][kind]] for R, v in D["scan"][b].items()), key=lambda p: p[0])


def min_of(c):
    k = 0
    for i, p in enumerate(c):
        if p[1] < c[k][1]:
            k = i
    if k == 0 or k == len(c) - 1:
        return c[k]
    (x0, y0), (x1, y1), (x2, y2) = c[k - 1], c[k], c[k + 1]
    den = (x0 - x1) * (x0 - x2) * (x1 - x2)
    A = (x2 * (y1 - y0) + x1 * (y0 - y2) + x0 * (y2 - y1)) / den
    B = (x2 * x2 * (y0 - y1) + x1 * x1 * (y2 - y0) + x0 * x0 * (y1 - y2)) / den
    C = (x1 * x2 * (x1 - x2) * y0 + x2 * x0 * (x2 - x0) * y1 + x0 * x1 * (x0 - x1) * y2) / den
    xm = -B / (2 * A)
    return [xm, A * xm * xm + B * xm + C]


def scan(b: str) -> dict:
    raw, cp = curve(b, "raw"), curve(b, "cp")
    best = curve("aug-cc-pVTZ", "cp") if "aug-cc-pVTZ" in D["scan"] else None
    return {"raw": raw, "cp": cp, "best": best, "minRaw": min_of(raw), "minCp": min_of(cp)}
