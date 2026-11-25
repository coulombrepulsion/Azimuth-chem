"""Continuum solvation: Born model of ion hydration; C-PCM results for neutral molecules.

HEADER
    Model of the page "Модели растворителя" (v1.0 solvation.js: born,
    bornD, pcm, epsD). Wilkinson convention, sections 1-8.

§1 THEORY
    Born: a charge z e in a spherical cavity of radius a inside a dielectric
    continuum of permittivity eps gains
        dG = -(N_A e^2 / (8 pi eps0)) (z^2 / a) (1 - 1/eps)
           = -694.7 z^2 / a(Angstrom) (1 - 1/eps) kJ/mol.
    With Shannon crystal radii (CN 6) the model overestimates hydration
    energies (Marcus 1991) by up to a factor of two; Latimer, Pitzer and
    Slansky (1939) enlarge the cavity by ~0.85 A (cations) and ~0.1 A
    (anions).
    C-PCM (conductor-like polarisable continuum): electrostatic solvation
    free energies of eleven neutral molecules and, for water and acetone,
    their dependence on eps -- precomputed by the author of v1.0 with PySCF
    (method as stated on the page) and kept here as data
    (data/solvation_cpcm.json; experimental values: FreeSolv, water: Ben-Naim
    and Marcus). The eps dependence is compared with the Born-like factor
    (eps - 1)/eps normalised to water (eps = 78.36).

§2 ALGORITHM
    Direct evaluation; the dashed curve on e = 1, 1.05, 1.05^2, ... <= 80
    (repeated multiplication, as v1.0).

§3 APPLICATIONS
    Endpoints solv.born, solv.pcm, solv.eps.

§4 SPECIFICATION
    born(eps > 0, dp, dm Angstrom) -> {rows: [{s, z, r, a, ex, b}], mae}
    pcm() -> {mols, r: {mol: {dG, exp}}, mae} (kcal/mol)
    eps_curve(i in {0, 1}) -> {m, ks, vals, curve: [[e, v]], pct}
    Tier: bitwise vs v1.0 (only +, -, *, /, abs).

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    The C-PCM numbers are not recomputed (no PySCF at run time); see
    REPRODUCIBILITY for their provenance.
§7 TEST CASES (tests/test_solvation.py)
    Born(Na+, a = 1.02 A, eps = 78.4) = -672 kJ/mol (the page's exercise);
    dG -> 0 as eps -> 1; dG scales as z^2/a; pct for water = 100 at
    eps = 78.36; vs v1.0.
§8 ERROR ANALYSIS
    A few correctly rounded operations: relative error < 5u. The model
    error (factor ~2 for crystal radii) dwarfs any numerical error.
"""
from __future__ import annotations

import json
from pathlib import Path

DATA = json.loads((Path(__file__).parent / "data" / "solvation_cpcm.json").read_text(encoding="utf-8"))

# Shannon crystal radii (CN 6), Angstrom; experimental hydration free energies (Marcus 1991), kJ/mol
ION = [("Li⁺", 1, 0.76, -475), ("Na⁺", 1, 1.02, -365), ("K⁺", 1, 1.38, -295), ("Rb⁺", 1, 1.52, -275),
       ("Cs⁺", 1, 1.67, -250), ("F⁻", -1, 1.33, -465), ("Cl⁻", -1, 1.81, -340), ("Br⁻", -1, 1.96, -315),
       ("I⁻", -1, 2.20, -275)]


def born_energy(z: int, a: float, e: float) -> float:
    """Born solvation free energy, kJ/mol (a in Angstrom)."""
    return -694.7 * z * z / a * (1 - 1 / e)


def born(eps: float, dp: float, dm: float) -> dict:
    rows = []
    for s, z, r, ex in ION:
        a = r + (dp if z > 0 else dm)
        rows.append({"s": s, "z": z, "r": r, "a": a, "ex": ex, "b": born_energy(z, a, eps)})
    tot = 0
    for r in rows:
        tot = tot + abs(r["b"] - r["ex"])
    return {"rows": rows, "mae": tot / len(rows)}


def pcm() -> dict:
    M = DATA["mols"]
    tot = 0
    for m in M:
        tot = tot + abs(DATA["r"][m]["dG"] - DATA["r"][m]["exp"])
    return {"mols": M, "r": {m: {"dG": DATA["r"][m]["dG"], "exp": DATA["r"][m]["exp"]} for m in M},
            "epsMols": DATA["epsMols"], "mae": tot / len(M)}


def eps_curve(i: int) -> dict:
    m = DATA["epsMols"][i]
    pr = sorted(((float(k), v) for k, v in DATA["r"][m]["eps"].items()), key=lambda x: x[0])
    ks, vals = [k for k, _ in pr], [v for _, v in pr]
    vW, fW = vals[-1], (78.36 - 1) / 78.36
    curve = []
    e = 1.0
    while e <= 80:
        curve.append([e, vW * ((e - 1) / e) / fW])
        e *= 1.05
    i5 = next(j for j, k in enumerate(ks) if abs(k - 4.81) < 0.01)
    return {"m": m, "ks": ks, "vals": vals, "curve": curve, "pct": vals[i5] / vW * 100}
