"""Crystals: cell volume and density, interplanar spacings and a powder pattern, cubic packings.

HEADER
    Model of the page "Кристаллы: решётка и ячейка" (web/<lang>/crystals.html), Atlas 2026-10-25.
    Wilkinson convention, sections 1-8.

§1 THEORY
    A crystal is a lattice of identical cells a, b, c, α, β, γ. The cell volume is
        V = abc sqrt(1 − cos²α − cos²β − cos²γ + 2 cosα cosβ cosγ),
    the density ρ = Z M / (N_A V) for Z formula units of molar mass M in the cell. A family of lattice
    planes (hkl) has the spacing d with 1/d² = h·G*·h, G* the inverse of the metric tensor
    G = [[a², ab cosγ, ac cosβ], [ab cosγ, b², bc cosα], [ac cosβ, bc cosα, c²]] (cubic: d = a/√(h²+k²+l²)).
    X-rays of wavelength λ reflect at the Bragg angle: λ = 2d sin θ. Centred lattices extinguish
    reflections: I — h + k + l odd; F — h, k, l of mixed parity; diamond (F with a two-atom basis) also
    all-even with h + k + l = 4n + 2; a hexagonal close packing of atoms (hcp; the oxygens of ice Ih) — h − k = 3n
    with l odd. Cubic packings: atoms per cell Z = 1 (simple, sc), 2 (body-centred,
    bcc), 4 (face-centred, fcc), 8 (diamond); touching spheres of radius r give a = 2r, 4r/√3, 2√2 r, 8r/√3
    and the packing fractions π/6, √3π/8, π/(3√2), √3π/16; coordination numbers 6, 8, 12, 4.
    N_A = 6.02214076e23 mol⁻¹ (exact, SI 2019); Cu Kα1 λ = 1.540593 Å.

§2 ALGORITHM
    cell: the formulas above. pattern: h, k, l in −hmax..hmax, the extinction rule of the centring, d from
    G*, 2θ for d > λ/2; reflections of equal d (to 1e-6 Å) are one line whose multiplicity is their number.

§3 APPLICATIONS
    Endpoints cr.presets, cr.cell, cr.pattern, cr.packing.

§4 SPECIFICATION
    cell(a, b, c, al, be, ga, Z, M) -> {"V" (Å³), "rho" (g/cm³), "G": metric tensor}.
    pattern(a, b, c, al, be, ga, centring, lam, hmax, n) -> {"lines": [{"hkl", "d", "tt", "mult"}]} sorted by 2θ.
    packing(kind) -> {"Z", "pf", "cn", "a_over_r"}.

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    The 3x3 inverse by cofactors; angles in degrees at the interface.
§7 TEST CASES (tests/test_atlas_new_topics.py)
    NaCl a = 5.6402 Å, Z = 4, M = 58.443: ρ = 2.164 g/cm³; Cu fcc: first line (111) at 2θ = 43.3°; Si
    (diamond): (200) absent, (220) present; hexagonal V = a²c√3/2; packing fractions as above.
§8 ERROR ANALYSIS
    Relative errors ~1e-15 for cells far from degenerate; the model (perfect, rigid lattice) dominates.
"""
from __future__ import annotations

import math

NA = 6.02214076e23
CU_KA1 = 1.540593
PRESETS = {
    "nacl": {"a": 5.6402, "b": 5.6402, "c": 5.6402, "al": 90, "be": 90, "ga": 90, "Z": 4, "M": 58.443, "cent": "F"},
    "cu": {"a": 3.6149, "b": 3.6149, "c": 3.6149, "al": 90, "be": 90, "ga": 90, "Z": 4, "M": 63.546, "cent": "F"},
    "fe": {"a": 2.8665, "b": 2.8665, "c": 2.8665, "al": 90, "be": 90, "ga": 90, "Z": 2, "M": 55.845, "cent": "I"},
    "si": {"a": 5.4310, "b": 5.4310, "c": 5.4310, "al": 90, "be": 90, "ga": 90, "Z": 8, "M": 28.0855, "cent": "D"},
    "diamond": {"a": 3.5668, "b": 3.5668, "c": 3.5668, "al": 90, "be": 90, "ga": 90, "Z": 8, "M": 12.011, "cent": "D"},
    "po": {"a": 3.359, "b": 3.359, "c": 3.359, "al": 90, "be": 90, "ga": 90, "Z": 1, "M": 209.0, "cent": "P"},
    "ice": {"a": 4.5181, "b": 4.5181, "c": 7.3560, "al": 90, "be": 90, "ga": 120, "Z": 4, "M": 18.015, "cent": "H"},
}
PACKING = {
    "sc": (1, math.pi / 6, 6, 2.0),
    "bcc": (2, math.sqrt(3) * math.pi / 8, 8, 4 / math.sqrt(3)),
    "fcc": (4, math.pi / (3 * math.sqrt(2)), 12, 2 * math.sqrt(2)),
    "diamond": (8, math.sqrt(3) * math.pi / 16, 4, 8 / math.sqrt(3)),
}


def _check(a, b, c, al, be, ga):
    if not all(0.5 <= x <= 100 for x in (a, b, c)) or not all(20 <= x <= 160 for x in (al, be, ga)):
        raise ValueError("cell: a, b, c 0.5..100 Å, angles 20..160°")


def metric(a, b, c, al, be, ga):
    ca, cb, cg = (math.cos(math.radians(x)) for x in (al, be, ga))
    return [[a * a, a * b * cg, a * c * cb], [a * b * cg, b * b, b * c * ca], [a * c * cb, b * c * ca, c * c]]


def _inv(m):
    (a, b, c), (d, e, f), (g, h, i) = m
    det = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)
    if det <= 0:
        raise ValueError("these angles do not make a cell")
    co = [[e * i - f * h, c * h - b * i, b * f - c * e], [f * g - d * i, a * i - c * g, c * d - a * f],
          [d * h - e * g, b * g - a * h, a * e - b * d]]
    return [[x / det for x in row] for row in co], det


def cell(a, b, c, al, be, ga, Z, M) -> dict:
    _check(a, b, c, al, be, ga)
    if not 1 <= Z <= 1000 or not 0 < M <= 1e5:
        raise ValueError("Z: 1..1000, M > 0")
    G = metric(a, b, c, al, be, ga)
    _, det = _inv(G)
    V = math.sqrt(det)
    return {"V": V, "rho": Z * M / (NA * V * 1e-24), "G": G}


def allowed(h, k, l, cent):  # noqa: E741
    if cent == "I":
        return (h + k + l) % 2 == 0
    if cent == "H":  # hexagonal close packing of the atoms (hcp, ice Ih oxygens): h − k = 3n with l odd is absent
        return not ((h - k) % 3 == 0 and l % 2 == 1)
    if cent in ("F", "D"):
        par = {h % 2, k % 2, l % 2}
        if len(par) != 1:
            return False
        if cent == "D" and par == {0}:
            return (h + k + l) % 4 == 0
        return True
    return True


def pattern(a, b, c, al, be, ga, cent="P", lam=CU_KA1, hmax=4, n=12) -> dict:
    _check(a, b, c, al, be, ga)
    if cent not in ("P", "I", "F", "D", "H") or not 0.1 <= lam <= 5 or not 1 <= hmax <= 6 or not 1 <= n <= 60:
        raise ValueError("bad pattern parameters")
    Gs, _ = _inv(metric(a, b, c, al, be, ga))
    found = {}
    r = range(-hmax, hmax + 1)
    for h in r:
        for k in r:
            for l in r:  # noqa: E741
                if (h, k, l) == (0, 0, 0) or not allowed(h, k, l, cent):
                    continue
                v = (h, k, l)
                inv_d2 = sum(v[i] * Gs[i][j] * v[j] for i in range(3) for j in range(3))
                d = 1 / math.sqrt(inv_d2)
                s = lam / (2 * d)
                if s >= 1:
                    continue
                key = round(d, 6)
                if key in found:
                    found[key]["mult"] += 1
                    if min(v) >= 0 and (min(found[key]["hkl"]) < 0 or v > tuple(found[key]["hkl"])):
                        found[key]["hkl"] = list(v)
                else:
                    found[key] = {"hkl": list(v), "d": d, "tt": 2 * math.degrees(math.asin(s)), "mult": 1}
    lines = sorted(found.values(), key=lambda x: x["tt"])[:n]
    return {"lines": lines}


def packing(kind: str) -> dict:
    if kind not in PACKING:
        raise ValueError("kind: sc, bcc, fcc, diamond")
    Z, pf, cn, ar = PACKING[kind]
    return {"Z": Z, "pf": pf, "cn": cn, "a_over_r": ar}
