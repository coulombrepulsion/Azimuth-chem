"""Atomic units: CODATA 2018 conversion factors, a unit converter, the
"kinetic versus potential" estimate of the hydrogen-like atom, and a scale
of chemically relevant energies.

HEADER
    Model of the Atlas page "Atomic units" (web/<lang>/units.html); port of
    EH, A0, CAT, conv, sec3 and SC of v1.0. Wilkinson convention, §1-§8.

§1 THEORY
    Atomic units set m_e = e = hbar = 4 pi eps0 = 1. Derived units: bohr
    a0 = 4 pi eps0 hbar^2/(m_e e^2), hartree Eh = e^2/(4 pi eps0 a0), time
    hbar/Eh, dipole e a0. Conversion factors (CODATA 2018, as in v1.0):
    1 Eh = 27.211386245988 eV = 2625.4996394799 kJ/mol = 627.5094740631
    kcal/mol = 219474.6313632 cm^-1 = 315775.02480407 K = 6.579683920502e15
    Hz = 4.3597447222071e-18 J; a0 = 0.529177210903 angstrom;
    e a0 = 2.541746473 D = 8.4783536255e-30 C m; 1 u = 1822.888486209 m_e;
    m_e = 9.1093837015e-31 kg; hbar/Eh = 24.188843265857 as.
    Estimate of the atom's size: an electron confined to radius r around
    charge Z has kinetic energy ~ 1/(2 r^2) and potential energy -Z/r; the
    sum E(r) = 1/(2 r^2) - Z/r has its minimum at r = 1/Z with E = -Z^2/2,
    and there T = -V/2 (virial theorem).

§2 ALGORITHM
    convert: value in the chosen unit -> atomic units (multiply by the
    unit's factor f_u = 1/(units per a.u.)) -> every unit of the category
    (divide by its factor). estimate: closed forms on r = 0.02 + 1.98 i/399,
    i < 400. scale: the twelve energies of the page in hartree, then in
    the requested unit.

§3 APPLICATIONS
    The converter, the energy-versus-radius chart with its minimum, and the
    logarithmic scale from rotational quanta to total energies.

§4 SPECIFICATION
    constants() -> {EH: {eV, kJ, kcal, cm, K, Hz, J}, A0}.
    convert(cat in CAT, unit (a key of that category), value: float) ->
        {au, rows: [[key, value in that unit]] in the page order}.
    estimate(Z: int 1..6, r: float in [0.01, 10]) -> {T, V, E (hartree at r),
        rmin, Emin, rs: [400], Tc, Vc, Ec: [400] (hartree)}.
    scale(unit in {"Eh", "eV", "kJ", "cm"}) -> {eh: [12], v: [12]} in the
        page's listing order.
    Reference: v1.0 units.html. Equivalence tier ``bitwise`` (the same
    multiplications and divisions in the same order; no transcendental
    function is involved).

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    The factors are stored as "units per atomic unit"; the converter's
    factor of a unit is the reciprocal, computed once, exactly as v1.0.
§7 TEST CASES (tests/test_units.py)
    1 Eh -> 27.211386245988 eV; 1 eV -> 8065.5439 cm^-1 (CODATA:
    8065.543937...); round trip unit -> a.u. -> unit within 2u; estimate
    minimum at r = 1/Z, E = -Z^2/2, T = -V/2; bitwise against v1.0.
§8 ERROR ANALYSIS
    Each converted value is v * (1/F_u) / (1/F_k): three roundings,
    relative error <= 3u ~ 7e-16 versus exact decimal arithmetic. The
    constants themselves are the 2018 CODATA recommended values to the
    digits written above (their uncertainty, ~1e-12 relative for Eh in eV,
    is far below the page's display precision).
"""
from __future__ import annotations

EH = {"eV": 27.211386245988, "kJ": 2625.4996394799, "kcal": 627.5094740631, "cm": 219474.6313632,
      "K": 315775.02480407, "Hz": 6.579683920502e15, "J": 4.3597447222071e-18}
A0 = 0.529177210903

CAT = {
    "energy": [("Eh", 1), ("eV", 1 / EH["eV"]), ("kJ", 1 / EH["kJ"]), ("kcal", 1 / EH["kcal"]), ("cm", 1 / EH["cm"]),
               ("K", 1 / EH["K"]), ("Hz", 1 / EH["Hz"]), ("J", 1 / EH["J"])],
    "length": [("a0", 1), ("A", 1 / A0), ("pm", 1 / (100 * A0)), ("nm", 1 / (A0 / 10)), ("m", 1 / (A0 * 1e-10))],
    "dipole": [("au", 1), ("D", 1 / 2.541746473), ("Cm", 1 / 8.4783536255e-30)],
    "mass": [("me", 1), ("u", 1822.888486209), ("kg", 1 / 9.1093837015e-31)],
    "time": [("au", 1), ("as", 1 / 24.188843265857), ("fs", 1 / 0.024188843265857), ("s", 1 / 2.4188843265857e-17)],
}

# energies of the scale, in hartree, in the page's listing order
SCALE_EH = [230.7, 76.06, 290 / EH["eV"], 0.5, 348 / EH["kJ"], 0.37, 0.042, 3700 / EH["cm"], 21 / EH["kJ"],
            1 / EH["kcal"], 298 / EH["K"], 27 / EH["cm"]]
RS = [0.02 + 1.98 * i / 399 for i in range(400)]


def constants() -> dict:
    return {"EH": dict(EH), "A0": A0}


def convert(cat: str, unit: str, value: float) -> dict:
    """Value given in ``unit`` expressed in every unit of the category."""
    if cat not in CAT:
        raise ValueError(f"unknown category {cat}")
    fu = dict(CAT[cat]).get(unit)
    if fu is None:
        raise ValueError(f"unknown unit {unit} for {cat}")
    au = value * fu
    return {"au": au, "rows": [[k, au / f] for k, f in CAT[cat]]}


def estimate(Z: int, r: float) -> dict:
    """E(r) = 1/(2 r^2) - Z/r and its parts, at r and along the chart grid."""
    if not 1 <= Z <= 6:
        raise ValueError("Z must be 1..6")
    if not 0.01 <= r <= 10:
        raise ValueError("r must be in [0.01, 10] bohr")

    def T(x):
        return 1 / (2 * x * x)

    def V(x):
        return -Z / x
    return {"T": T(r), "V": V(r), "E": T(r) + V(r), "rmin": 1 / Z, "Emin": -Z * Z / 2, "rs": RS,
            "Tc": [T(x) for x in RS], "Vc": [V(x) for x in RS], "Ec": [T(x) + V(x) for x in RS]}


def scale(unit: str) -> dict:
    if unit not in ("Eh", "eV", "kJ", "cm"):
        raise ValueError("unit must be Eh, eV, kJ or cm")
    f = 1 if unit == "Eh" else EH[unit]
    return {"eh": list(SCALE_EH), "v": [e * f for e in SCALE_EH]}
