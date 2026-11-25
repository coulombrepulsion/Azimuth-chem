"""Ideal-gas thermochemistry from vibrational frequencies (RRHO).

HEADER
    Model of the page "Термохимия из частот" (v1.0 thermochemistry.js:
    thermo, draw, chart, the "own molecule" form).  Wilkinson convention,
    sections 1-8.

§1 THEORY
    Ideal gas, rigid rotor, harmonic oscillator; separable partition function
    q = q_t q_r q_v q_e (standard textbook formulas, e.g. McQuarrie,
    Statistical Mechanics, ch. 8):
      translation  q_t = (2 pi m k T / h^2)^(3/2) k T / p,
                   S_t = R (ln q_t + 5/2), H_t = 5/2 R T, Cp_t = 5/2 R (incl. pV);
      rotation     theta_i = h c B_i / k;  linear: q_r = T / (sigma theta),
                   S_r = R (ln q_r + 1), H_r = R T, C_r = R;  nonlinear:
                   q_r = sqrt(pi)/sigma sqrt(T^3 / (theta_A theta_B theta_C)),
                   S_r = R (ln q_r + 3/2), H_r = 3/2 R T, C_r = 3/2 R;
      vibration    u = h c nu / (k T):  S = R (u/(e^u - 1) - ln(1 - e^-u)),
                   H - H0 = R theta/(e^u - 1), C = R u^2 e^u/(e^u - 1)^2,
                   ZPE = 1/2 R theta per mode (terms with u >= 700 vanish);
      electronic   S_e = R ln g (ground state only).
    H_corr = ZPE + H(T) - H(0), G_corr = H_corr - T S.
    Constants CODATA 2018; c = 2.99792458e10 cm/s; E_h = 2625.4996394799
    kJ/mol.  Molecules: average atomic masses, rotational constants from
    equilibrium geometries, experimental fundamentals, S°(298.15 K, 1 bar)
    from NIST-JANAF (data of v1.0).

§2 ALGORITHM
    Direct evaluation in v1.0 operation order; chart on T = 50..2000 K step
    10; own molecule: rotational constants in GHz/MHz converted with
    1e9 / c, frequencies scaled, imaginary ones dropped, optionally raised
    to 100 cm^-1.

§3 APPLICATIONS
    Endpoints therm.mols, therm.state, therm.chart, therm.custom.

§4 SPECIFICATION
    thermo(M, T, p) -> {St, Sr, Sv, Se, S, Ht, Hr, Hv, Hth, Ct, Cr, Cv, Cp, zpe,
    Hc, Gc}  (J/mol, J/(mol K));  M = {m amu, lin, B [cm^-1], sig, g, nu}.
    Tier: bitwise vs v1.0 on Linux/glibc (pow(x, 1.5) is the platform pow,
    as in V8); 1 ulp in q_t elsewhere -> |dS| < 1e-13 J/(mol K).

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    Math.pow(x, 1.5) -> jsmath.js_pow; Math.log/exp -> jsmath (fdlibm).
§7 TEST CASES (tests/test_thermochemistry.py)
    Oracles: S°(298.15) of N2, CO, CO2, H2O, NH3, CH4 within 0.5 J/(mol K)
    of NIST-JANAF (RRHO is accurate for these); Cp -> 7/2 R (linear) and
    4R (nonlinear) as T -> 0 contributions of vibrations vanish; Sackur-
    Tetrode for Ar-like mass independently from math; vs v1.0.
§8 ERROR ANALYSIS
    Sums of < 30 terms of O(10..200) with relative errors ~4u each:
    absolute error < 1e-11 J/(mol K).  The model error (anharmonicity,
    hindered rotors, H2 nuclear spin) is ~0.1-1 J/(mol K) (see §7, page text).
"""
from __future__ import annotations

import math

from .jsmath import exp, js_pow, log

H, KB, C, NA = 6.62607015e-34, 1.380649e-23, 2.99792458e10, 6.02214076e23
R = KB * NA
AMU = 1.66053906660e-27
EH = 2625.4996394799
HCK = H * C / KB

# 2.10.0: H2 (theta_rot = 88 K, not << T) rotates quantum-mechanically, with the nuclear-spin
# statistics of normal hydrogen: para (even J, weight 1) and ortho (odd J, weight 3) at equilibrium;
# the nuclear-spin entropy R ln 4 is not counted (the convention of the tables).  At 298 K: S +0.05,
# Cp 29.10 -> 28.69 J/(mol K) (JANAF 28.84).  QUANTUM_H2 = False reproduces v1.0 / Atlas 0.80.
QUANTUM_H2 = True


def _rot_ortho_para(theta, T):
    s = e1 = e2 = 0.0
    for J in range(0, 80):
        x = theta * J * (J + 1)
        if x / T > 700:
            break
        w = (1 if J % 2 == 0 else 3) * (2 * J + 1) * exp(-x / T)
        s += w
        e1 += w * x
        e2 += w * x * x
    q, m1, m2 = s / 4, e1 / s, e2 / s                   # -> T / (2 theta) at high T
    return R * (log(q) + m1 / T), R * m1, R * (m2 - m1 * m1) / (T * T)


MOL = [{"id": "H₂", "m": 2.016, "lin": True, "B": [60.8606], "sig": 2, "g": 1, "nu": [4161], "S": 130.68, "spin": True},
       {"id": "N₂", "m": 28.014, "lin": True, "B": [1.9982], "sig": 2, "g": 1, "nu": [2330], "S": 191.61},
       {"id": "O₂", "m": 31.998, "lin": True, "B": [1.4457], "sig": 2, "g": 3, "nu": [1556], "S": 205.15},
       {"id": "CO", "m": 28.01, "lin": True, "B": [1.9314], "sig": 1, "g": 1, "nu": [2143], "S": 197.66},
       {"id": "CO₂", "m": 44.009, "lin": True, "B": [0.3916], "sig": 2, "g": 1, "nu": [1333, 667, 667, 2349], "S": 213.79},
       {"id": "H₂O", "m": 18.015, "lin": False, "B": [27.376, 14.586, 9.5159], "sig": 2, "g": 1, "nu": [3657, 1595, 3756],
        "S": 188.84},
       {"id": "NH₃", "m": 17.031, "lin": False, "B": [9.9743, 9.9743, 6.3458], "sig": 3, "g": 1,
        "nu": [3337, 950, 3444, 3444, 1627, 1627], "S": 192.77},
       {"id": "CH₄", "m": 16.043, "lin": False, "B": [5.3086, 5.3086, 5.3086], "sig": 12, "g": 1,
        "nu": [2917, 1534, 1534, 3019, 3019, 3019, 1306, 1306, 1306], "S": 186.25}]


def thermo(M: dict, T: float, p: float) -> dict:
    m = M["m"] * AMU
    qt = js_pow(2 * math.pi * m * KB * T / (H * H), 1.5) * KB * T / p
    St, Ht, Ct = R * (log(qt) + 2.5), 2.5 * R * T, 2.5 * R
    th = [HCK * b for b in M["B"]]
    if M.get("spin") and QUANTUM_H2:
        Sr, Hr, Cr = _rot_ortho_para(th[0], T)
    elif M["lin"]:
        q = T / (M["sig"] * th[0])
        Sr, Hr, Cr = R * (log(q) + 1), R * T, R
    else:
        q = math.sqrt(math.pi) / M["sig"] * math.sqrt(T * T * T / (th[0] * th[1] * th[2]))
        Sr, Hr, Cr = R * (log(q) + 1.5), 1.5 * R * T, 1.5 * R
    Sv = Hv = Cv = zpe = 0
    for n in M["nu"]:
        t = HCK * n
        u = t / T
        zpe += 0.5 * R * t
        if u < 700:
            e = exp(u)
            Sv += R * (u / (e - 1) - log(1 - 1 / e))
            Hv += R * t / (e - 1)
            Cv += R * u * u * e / ((e - 1) * (e - 1))
    Se = R * log(M["g"])
    S, Hth, Cp = St + Sr + Sv + Se, Ht + Hr + Hv, Ct + Cr + Cv
    return {"St": St, "Sr": Sr, "Sv": Sv, "Se": Se, "S": S, "Ht": Ht, "Hr": Hr, "Hv": Hv, "Hth": Hth, "Ct": Ct,
            "Cr": Cr, "Cv": Cv, "Cp": Cp, "zpe": zpe, "Hc": zpe + Hth, "Gc": zpe + Hth - T * S}


def state(M: dict, T: float, p: float) -> dict:
    r = thermo(M, T, p)
    out = {"r": r, "eh": {k: r[k] / 1000 / EH for k in ("zpe", "Hc", "Gc")}, "TS": T * r["S"] / 1000}
    if M.get("S"):
        d = r["S"] - M["S"]
        out["ref"] = {"S": M["S"], "d": d, "pct": 100 * d / M["S"]}
    return out


def chart(M: dict, p: float) -> dict:
    T, pts = 50, []
    while T <= 2000:
        pts.append([T, thermo(M, T, p)])
        T += 10
    return {"pts": pts}


def custom(m: float, B: list, Bu: str, sig: int, g: int, sc: float, nu: list, low: bool) -> dict:
    """Own molecule: unit conversion of B, scaling and filtering of frequencies (v1.0 form logic)."""
    f = 1e9 / 2.99792458e10 if Bu == "GHz" else 1e6 / 2.99792458e10 if Bu == "MHz" else 1
    B = [x * f for x in B]
    im = sum(1 for x in nu if x < 0)
    nu = [x * sc for x in nu if x > 0]
    nlow = sum(1 for x in nu if x < 100)
    if low:
        nu = [max(x, 100) for x in nu]
    lin = len(B) == 1
    return {"mol": {"id": "custom", "custom": True, "m": m, "lin": lin, "B": [B[0]] if lin else B, "sig": sig, "g": g,
                    "nu": nu, "S": None}, "im": im, "low": nlow}
