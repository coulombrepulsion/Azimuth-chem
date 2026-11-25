"""Intermolecular interactions: He2 (dispersion only) and the water dimer (hydrogen bond) at HF and
MP2, with and without counterpoise correction; the London R^-6 law.

HEADER
    Model of the page "Межмолекулярные взаимодействия: водородная связь и
    дисперсия" (v1.0 dispersion.js: DD, SYSD, curMin, sec1, sec2).
    Wilkinson convention, sections 1-8.

§1 THEORY
    Interaction energy dE(R) = E(AB) - E(A) - E(B) in hartree; columns:
    HF and MP2 without and with the counterpoise correction (Boys-Bernardi;
    BSSE = raw - cp). He2 in aug-cc-pVDZ on R = 4.4 ... bohr, (H2O)2 in
    6-31G* on R(O...O) in A; the energies were computed by the author of
    v1.0 with PySCF (data/dispersion.json). Display units: cm^-1 for He2
    (1 Eh = 219474.63 cm^-1), kJ/mol for the dimer (2625.4996). Minimum of
    a curve: the lowest grid point, reported only if deeper than 0.02 in the
    display unit and not at the last point. London dispersion: the MP2
    correlation part of the counterpoise-corrected interaction,
    -(dE_MP2,cp - dE_HF,cp), decays as C6/R^6; the slope of log|dE| vs
    log R between 8 and 12 bohr and C6 = |dE(12)| 12^6 are compared with
    the accurate C6(He-He) = 1.46 a.u. References: He2 well depth 7.65
    cm^-1 at R_e = 5.6 bohr; (H2O)2 CCSD(T)/CBS 21.0 kJ/mol at 2.91 A
    (literature values of v1.0, see REPRODUCIBILITY).

§2 ALGORITHM
    As v1.0: scaling of the columns, first lowest point, two-point slope
    in log10.

§3 APPLICATIONS
    Endpoints disp.sys, disp.r6.

§4 SPECIFICATION
    system(name) -> {R, E: {1..4: scaled curves}, tab: [{v1..v4, bsseHF,
      bsseMP2, corrRaw, corrCp}], i0, mins: {hf_cp, mp2_cp, hf_raw, mp2_raw}
      (each {R, E} or None), dHM, dRM, pct}; r6() -> {pts, line, slope, C6m}.
    Tier: bitwise vs v1.0 on Linux/glibc (EXACT).

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    The data are not recomputed at run time; see REPRODUCIBILITY.
§7 TEST CASES (tests/test_dispersion.py)
    BSSE > 0 (raw below cp) at every point of both systems; HF/cp of He2
    has no minimum (repulsive); the R^-6 slope within 0.3 of -6; MP2/cp
    He2 well shallower than the accurate 7.65 cm^-1; vs v1.0.
§8 ERROR ANALYSIS
    Grid minima carry the grid spacing (0.1 bohr / 0.05 A) as the
    uncertainty in R; energies are exact data to ~1e-10 Eh.
"""
from __future__ import annotations

import json
from pathlib import Path

from .jsmath import js_pow, js_round, log10

DD = json.loads((Path(__file__).parent / "data" / "dispersion.json").read_text(encoding="utf-8"))
CM, KJ = 219474.63, 2625.4996
SYS = {"he2": {"k": CM, "R0": 5.6, "ref": {"R": 5.6, "E": -7.65}},
       "w2": {"k": KJ, "R0": 2.9, "ref": {"R": 2.91, "E": -21.0}}}
C6 = 1.46


def col(m, cp):
    return (1 if m == "hf" else 2) + (2 if cp else 0)


def cur_min(name, m, cp):
    pts, k = DD[name]["pts"], SYS[name]["k"]
    j = col(m, cp)
    b = None
    for p in pts:
        if b is None or p[j] < b[j]:
            b = p
    return {"R": b[0], "E": b[j] * k} if (b[j] * k < -0.02 and b is not pts[-1]) else None


def system(name: str) -> dict:
    pts, k = DD[name]["pts"], SYS[name]["k"]
    E = {str(j): [p[j] * k for p in pts] for j in (1, 2, 3, 4)}
    tab = []
    for p in pts:
        v = [None] + [p[j] * k for j in (1, 2, 3, 4)]
        tab.append({"v": v[1:], "bsseHF": v[1] - v[3], "bsseMP2": v[2] - v[4], "corrRaw": v[2] - v[1], "corrCp": v[4] - v[3]})
    i0 = next((i for i, p in enumerate(pts) if abs(p[0] - SYS[name]["R0"]) < 1e-6), -1)
    mins = {"hf_cp": cur_min(name, "hf", True), "mp2_cp": cur_min(name, "mp2", True),
            "hf_raw": cur_min(name, "hf", False), "mp2_raw": cur_min(name, "mp2", False)}
    mH, mM, mMr = mins["hf_cp"], mins["mp2_cp"], mins["mp2_raw"]
    ref = SYS[name]["ref"]
    return {"R": [p[0] for p in pts], "E": E, "tab": tab, "i0": i0, "mins": mins, "ref": ref,
            "dHM": mM["E"] - mH["E"] if (mM and mH) else None,
            "dRM": mMr["E"] - mM["E"] if (mMr and mM) else None,
            "pct": js_round(100 * mM["E"] / ref["E"]) if mM else None}


def r6() -> dict:
    pts = [p for p in DD["he2"]["pts"] if p[0] >= 6.5]
    out = [[p[0], -(p[4] - p[3])] for p in pts]
    pa = next(p for p in pts if abs(p[0] - 8) < 1e-6)
    pb = next(p for p in pts if abs(p[0] - 12) < 1e-6)
    ca, cb = -(pa[4] - pa[3]), -(pb[4] - pb[3])
    slope = (log10(cb) - log10(ca)) / (log10(12) - log10(8))
    return {"pts": out, "line": [[x, C6 / js_pow(x, 6)] for x in (6.5, 12)], "slope": slope, "C6m": cb * js_pow(12, 6)}
