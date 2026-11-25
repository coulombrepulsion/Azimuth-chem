"""Born-Oppenheimer separation and vibrational levels: the Morse oscillator.

HEADER
    Numerical model of the Atlas page "Born-Oppenheimer and vibrations"
    (web/<lang>/bo.html).  Port of P, U, Uh, morsePsi, harmPsi, turn and the
    expectation values of v1.0.  Wilkinson convention, §1-§8.

§1 THEORY
    The electronic energy of H2 is modelled by the Morse potential
        U(R) = D_e (1 - e^{-a (R - R_e)})^2,
    D_e = 0.1745 Eh (4.75 eV), R_e = 1.401 bohr, a = 1.0288 bohr^-1
    (omega_e of H2 = 4401 cm^-1).  For nuclear reduced mass mu (electron
    masses) the Schroedinger equation is solved exactly (Morse 1929):
        omega = a sqrt(2 D_e / mu),  lambda = sqrt(2 mu D_e) / a,
        E_v = omega (v + 1/2) - omega^2 (v + 1/2)^2 / (4 D_e),
        v = 0 .. v_max = floor(lambda - 1/2),
        psi_v(R) proportional to z^s e^{-z/2} L_v^{(2s)}(z),
        z = 2 lambda e^{-a (R - R_e)},  s = lambda - v - 1/2,
    L the generalised Laguerre polynomial; omega_e x_e = omega^2/(4 D_e).
    Harmonic approximation U_h = D_e a^2 (R - R_e)^2 with E_v = omega (v + 1/2),
    psi_v proportional to H_v(x) e^{-x^2/2}, x = sqrt(mu omega)(R - R_e).
    Classical turning points: harmonic R_e -+ sqrt(E/(D_e a^2)); Morse
    R_e - ln(1 + q)/a and R_e - ln(1 - q)/a, q = sqrt(E/D_e) (20 bohr when
    q >= 1, i.e. unbound).  Time scales: period 2 pi / omega, zero-point
    amplitude sqrt(1/(2 mu omega)), and (m_e/mu)^{1/4}.

§2 ALGORITHM
    Laguerre polynomials by the three-term recurrence
        (j + 1) L_{j+1} = (2j + 1 + alpha - z) L_j - (j + alpha) L_{j-1},
        L_0 = 1, L_1 = 1 + alpha - z;
    to avoid overflow the factor z^s e^{-z/2} is formed as
    exp(s ln z - z/2 - max) (shift by the largest exponent on the grid).
    Hermite: H_{j+1} = 2x H_j - 2j H_{j-1}, H_0 = 1, H_1 = 2x.
    Normalisation on the grid R_i = 0.35 + 0.0045 i, i < 1400, by the
    rectangle rule sum psi_i^2 dR = 1; <R> and <R^2> by the same rule.

§3 APPLICATIONS
    The page plots the potentials, the levels and the chosen wavefunction
    (or density), compares Morse and harmonic spacings, shows E_0, D_0 =
    D_e - E_0, the number of bound levels, the isotope effect (H2, HD, D2,
    T2 and any mu), and why the electron/nuclear time-scale ratio
    justifies the Born-Oppenheimer separation.

§4 SPECIFICATION
    state(mu: float in [1, 1e5], pot in {"morse", "harm", "both"},
          v: int >= 0) -> {DE, RE (model constants, for drawing),
      p: {w, lam, vmax, xe, E: [E_0..E_{max(vmax,0)}], Eh: [Eh_0..Eh_60]},
      turnM: [[ra, rb]] for each E_v, turnH: [[ra, rb]] for each Eh_v,
      U: [1400], Uh: [1400] (hartree on the grid),
      v: v after the page's clamp (v <= max(0, vmax) unless harmonic only),
      kv: the level drawn, psi: [1400] or None, mR, dR (bohr),
      ts: {per (fs), zp (angstrom), inv (= 1/mu), q4 (= mu^-1/4)} }.
    Energies in hartree, lengths in bohr unless stated.
    Reference: v1.0 bo.html.  Equivalence tier ``bound``: same order of
    operations; exp/log/pow/sqrt from different libm: B = 1e-12 relative
    for levels, potentials, turning points and time scales, B = 1e-10
    relative (to max |psi|) for the wavefunctions (§8).

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    * The level lists are long enough for every index the page uses:
      Eh up to v = 60 (the harmonic-only view caps v at 60), E up to v_max.
    * For mu -> 2 m_e there is a single bound level (v_max = 0): the page's
      "nothing is bound" warning.
§7 TEST CASES (tests/test_bo.py)
    * Exact Morse energies satisfy E_{v+1} - E_v = omega - 2 omega x_e (v+1)
      (closed form) and the last level lies below D_e.
    * Wavefunctions: normalised (1 to 1e-12 by construction), orthogonal
      for v != v' to the grid quadrature error (|<v|v'>| < 1e-6), and the
      harmonic psi_0 matches the Gaussian closed form.
    * Isotope scaling omega proportional to mu^{-1/2}: omega(D2)/omega(H2)
      = sqrt(mu_H2/mu_D2).
    * Differential test against the v1.0 JavaScript.
§8 ERROR ANALYSIS
    Level energies: two products and a quotient of rounded quantities
    with omega from one sqrt: relative error <= 8u; difference between
    implementations dominated by sqrt (correctly rounded in both) -> in
    practice bitwise; B = 1e-12 relative is generous.
    Wavefunctions: the Laguerre recurrence for alpha = 2s > 0 and z > 0 is
    stable in the forward direction for the dominant solution (the
    polynomial itself); each step adds <= 4u relative, v <= ~130 steps:
    <= 1e-13 relative.  exp/log differences (<= 1 ulp each) enter through
    s ln z - z/2 - max, whose magnitude can reach ~ 1e3 near the left edge
    (z large), where 1 ulp of the exponent (2e-13 absolute) gives relative
    2e-13 in exp; normalisation divides by a sum of 1400 squares (gamma
    ~ 1e-13).  Overall 1e-12 relative to max |psi|; tests use 1e-10 to
    cover the summation order of the max-shift.
    Turning points use log(1 +- q): relative error <= 2u for q away from 1.
"""
from __future__ import annotations

import functools
import math
from .jsmath import exp, js_pow, log, sq

DE, RE, A = 0.1745, 1.401, 1.0288
AMU, AUT, BOHR = 1822.888, 0.0241888, 0.529177
RG = [0.35 + i * 0.0045 for i in range(1400)]
DR = RG[1] - RG[0]


def params(mu: float) -> dict:
    w = A * math.sqrt(2 * DE / mu)
    lam = math.sqrt(2 * mu * DE) / A
    return {"w": w, "lam": lam, "vmax": math.floor(lam - 0.5), "xe": w * w / (4 * DE)}


def E_morse(w, k):
    return w * (k + 0.5) - w * w * sq(k + 0.5) / (4 * DE)


def E_harm(w, k):
    return w * (k + 0.5)


def U(R):
    return DE * sq(1 - exp(-A * (R - RE)))


def Uh(R):
    return DE * A * A * sq(R - RE)


def morse_psi(k: int, lam: float):
    """Normalised Morse eigenfunction v = k on the grid, or None if unbound."""
    s = lam - k - 0.5
    al = 2 * s
    if s <= 0:
        return None
    ln, L = [], []
    for R in RG:
        z = 2 * lam * exp(-A * (R - RE))
        l0, l1 = 1.0, 1 + al - z
        Lk = l0 if k == 0 else l1
        for j in range(1, k):
            l2 = ((2 * j + 1 + al - z) * l1 - (j + al) * l0) / (j + 1)
            l0, l1, Lk = l1, l2, l2
        ln.append(s * log(z) - z / 2)
        L.append(Lk)
    m = max(ln)
    y = [exp(x - m) * L[i] for i, x in enumerate(ln)]
    acc = 0.0
    for b in y:
        acc = acc + b * b
    nn = math.sqrt(acc * DR)
    return [x / nn for x in y]


def harm_psi(k: int, mu: float, w: float):
    """Normalised harmonic-oscillator eigenfunction on the grid."""
    c = math.sqrt(mu * w)
    y = []
    for R in RG:
        x = c * (R - RE)
        h0, h1 = 1.0, 2 * x
        h = h0 if k == 0 else h1
        for j in range(1, k):
            h2 = 2 * x * h1 - 2 * j * h0
            h0, h1, h = h1, h2, h2
        y.append(h * exp(-x * x / 2))
    acc = 0.0
    for b in y:
        acc = acc + b * b
    nn = math.sqrt(acc * DR)
    return [x / nn for x in y]


def turn(E: float, harmonic: bool) -> list[float]:
    """Classical turning points of level energy E."""
    if harmonic:
        d = math.sqrt(E / (DE * A * A))
        return [RE - d, RE + d]
    q = math.sqrt(E / DE)
    return [RE - log(1 + q) / A, RE - log(1 - q) / A if q < 1 else 20.0]


@functools.lru_cache(maxsize=256)
def _levels(mu: float) -> dict:
    p = params(mu)
    w = p["w"]
    E = [E_morse(w, k) for k in range(max(p["vmax"], 0) + 1)]
    Eh = [E_harm(w, k) for k in range(61)]
    return {"p": dict(p, E=E, Eh=Eh), "turnM": [turn(e, False) for e in E], "turnH": [turn(e, True) for e in Eh]}


_UG = [U(R) for R in RG]
_UHG = [Uh(R) for R in RG]


@functools.lru_cache(maxsize=512)
def state(mu: float, pot: str, v: int) -> dict:
    """Everything the page draws for reduced mass mu, potential view and level v."""
    if not 1 <= mu <= 1e5:
        raise ValueError("mu must be in [1, 1e5] electron masses")
    if pot not in ("morse", "harm", "both"):
        raise ValueError("pot must be morse, harm or both")
    if v < 0:
        raise ValueError("v must be >= 0")
    lv = _levels(mu)
    p = lv["p"]
    harm_only = pot == "harm"
    vmax = math.inf if harm_only else p["vmax"]
    if v > vmax:
        v = max(0, p["vmax"])
    kv = min(v, 60 if harm_only else p["vmax"])
    psi = harm_psi(kv, mu, p["w"]) if harm_only else morse_psi(kv, p["lam"])
    mR = m2 = 0.0
    if psi:
        for i, y in enumerate(psi):
            mR = mR + y * y * RG[i] * DR
            m2 = m2 + y * y * RG[i] * RG[i] * DR
    w = p["w"]
    ts = {"per": 2 * math.pi / w * AUT, "zp": math.sqrt(1 / (2 * mu * w)) * BOHR, "inv": 1 / mu,
          "q4": js_pow(1 / mu, 0.25)}
    return dict(lv, DE=DE, RE=RE, U=_UG, Uh=_UHG, v=v, kv=kv, psi=psi, mR=mR, dR=math.sqrt(max(0.0, m2 - mR * mR)), ts=ts)
