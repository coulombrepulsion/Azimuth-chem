"""Validation page: RHF energies of seven molecules in three basis sets and the Crawford water test.

HEADER
    The page "Проверка программы" compares the GTO engine (core.gto,
    core.qtaim) with published values: RHF energies of H2, CH4, NH3, H2O,
    HF, N2 and CO in STO-3G, 6-31G* and 6-31G** (reference table with three
    decimals) and, for water in STO-3G at the geometry of T. D. Crawford's
    programming projects, the RHF energy, the MP2 correction, the dipole
    moment and the Mulliken charges.  Wilkinson convention, sections 1-8.

§1 THEORY
    See core.gto (integrals, RHF with DIIS, MP2, dipole) and core.qtaim
    (Mulliken populations).  Nothing new is modelled here.
§2 ALGORITHM
    Geometries from core/data/validation.json (bohr, v1.0 VD); prep + rhf;
    results cached per (molecule, basis).
§3 APPLICATIONS
    pages/validation.py (val.rhf, val.cr).
§4 SPECIFICATION
    rhf_energy(i: 0..6, j: 0..2) -> {"E", "it", "conv"} for MOLS[i], BASES[j].
    crawford() -> {"E", "mp2", "mu", "qO", "qH"}.
    Tier: bitwise vs v1.0 (as core.gto).
§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    mu = Math.hypot of the dipole vector (jsmath.js_hypot).
§7 TEST CASES (tests/test_validation.py)
    Energies within 0.5 mEh of the table (the documented exceptions are
    listed on the page); Crawford values within the page tolerances; exact
    vs the v1.0 fixture.
§8 ERROR ANALYSIS
    The energies are converged to 1e-10 Eh in the density change (core.gto
    §8); the comparison with three-decimal references is limited by the
    rounding of the table (0.5 mEh).
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from . import gto, qtaim
from .jsmath import js_hypot

DATA = json.loads((Path(__file__).parent / "data" / "validation.json").read_text(encoding="utf-8"))
BASES = ("STO-3G", "6-31G*", "6-31G**")


def _atoms(a):
    return [{"el": el, "x": float(x), "y": float(y), "z": float(z)} for el, x, y, z in a]


@lru_cache(maxsize=None)
def rhf_energy(i: int, j: int) -> dict:
    s = gto.prep(_atoms(DATA["mol"][i]["a"]), BASES[j])
    r = gto.rhf(s)
    return {"E": r["E"], "it": r["iterations"], "conv": r["converged"]}


@lru_cache(maxsize=None)
def crawford() -> dict:
    s = gto.prep(_atoms(DATA["cr"]["at"]), "STO-3G")
    r = gto.rhf(s)
    mu = gto.dipole(s, r)
    p = qtaim.pop_analysis(s, r)
    return {"E": r["E"], "mp2": gto.mp2(s, r), "mu": js_hypot(*mu), "qO": p["mul"][0], "qH": p["mul"][1]}
