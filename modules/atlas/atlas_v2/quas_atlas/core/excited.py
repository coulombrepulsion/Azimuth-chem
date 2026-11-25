"""Vibronic spectra in the displaced-oscillator model; singlet-triplet splitting; spectrum
from computed transitions.

HEADER
    Model of the page "Возбуждённые состояния и спектры" (v1.0 excited.js:
    pois, gauss, draw, pot, spec, jab, spec2).  Wilkinson convention, §1-§8.

§1 THEORY
    Ground and excited states are harmonic in a dimensionless coordinate q,
    E0(q) = w q^2 / 2 and E1(q) = E00 - w/2 + w (q - D)^2 / 2, with the same
    vibrational quantum w and displacement D = sqrt(2 S) (Huang-Rhys factor
    S).  From v = 0 of one state the Franck-Condon factors to level v of the
    other are Poisson: |<0|v>|^2 = e^-S S^v / v!.  Absorption lines lie at
    E00 + v w, fluorescence lines at E00 - v w (mirror image); each line is
    broadened by a Gaussian of FWHM fw, exp(-4 ln2 (E - E_v)^2 / fw^2).
    Vertical absorption E00 + S w, vertical emission E00 - S w, Stokes shift
    2 S w.  Exchange: E(S1) - E(T1) = 2K.  lambda(nm) = 1239.84198 / E(eV);
    1 eV = 8065.544 cm^-1.

§2 ALGORITHM
    As v1.0: the envelope on 301 points of [E00 - span, E00 + span], span =
    (S + 4) w + 2 fw, v = 0..nv, nv = ceil(S + 6 sqrt(S + 1)) + 4; the
    potential curves on 121 steps of q (accumulated step, as v1.0); the
    computed-transition spectrum on 501 points, maxima = strict local maxima
    above 5 % of the largest value.

§3 APPLICATIONS
    Endpoints exc.state, exc.jab, exc.spectrum.

§4 SPECIFICATION
    state(S, w_cm, E00 eV, fw_cm) -> {w, fw, wcm, fwcm, lam00, ea, ee, st, stcm,
        lamA, lamE, vmax, lamMax, pot: {D, q0, q1, e0, e1, g: [[q, E]],
        x: [[q, E]], lev: [[e, h, e2]], ev}, spec: {x0, x1, nv, ab, em,
        sticks: [[v, h]], E: grid}}
    jab(E1, K) -> {ET, lam1, lamT}
    spectrum(rows [[E, f]], unit 'eV'|'nm', fw eV) -> {tr, emin, emax, pts,
        mx, fm, pk} (rows validated: E > 0, f >= 0, fw > 0).
    Tier: bitwise vs v1.0 (exp from core.jsmath).

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    Math.LN2 is the double 0.6931471805599453.
§7 TEST CASES (tests/test_excited.py)
    sum_v FC(v) = 1 (to 1e-15 for S <= 5 with v <= 60); S = 0: only the 0-0
    line; mirror symmetry ab(E00 + x) = em(E00 - x); vmax = floor(S) for
    non-integer S; vs v1.0.
§8 ERROR ANALYSIS
    Poisson weights by repeated multiplication: relative error <= v u;
    Gaussians: fdlibm exp (< 1 ulp) of an argument with relative error
    ~5u; envelope sums of < 60 positive terms: relative error < 70u.
"""
from __future__ import annotations

import math

from .jsmath import exp

CM, NM = 8065.544, 1239.84198
LN2 = 0.6931471805599453


def pois(S: float, v: int) -> float:
    p = exp(-S)
    for k in range(1, v + 1):
        p *= S / k
    return p


def gauss(x: float, x0: float, fw: float) -> float:
    return exp(-4 * LN2 * (x - x0) * (x - x0) / (fw * fw))


def _pot(S, w, E00):
    D = math.sqrt(2 * S)
    q0, q1 = -3.2, max(3.2, D + 3.2)
    e0, e1 = -0.15 * w - 0.1, E00 + max(5, S + 3) * w

    def par(q, off):
        out = []
        x = q0
        while x <= q1 + 1e-9:
            e = off + 0.5 * w * (x - q) * (x - q)
            if not e > e1 + 0.2:
                out.append([x, e])
            x += (q1 - q0) / 120
        return out
    # 2.6.0: both curves have the same frequency, so the excited minimum lies at E00 and the gap
    # between the two v = 0 levels is E00 (before: minimum at E00 - w/2, gap E00 - w/2).
    lev = [[(v + 0.5) * w, math.sqrt(2 * (v + 0.5)), E00 + (v + 0.5) * w] for v in range(6)]
    return {"D": D, "q0": q0, "q1": q1, "e0": e0, "e1": e1, "g": par(0, 0), "x": par(D, E00),
            "lev": lev, "ev": E00 + 0.5 * w * D * D}


def _spec(S, w, E00, fw):
    span = (S + 4) * w + 2 * fw
    x0, x1 = E00 - span, E00 + span
    nv = math.ceil(S + 6 * math.sqrt(S + 1)) + 4
    P = [pois(S, v) for v in range(nv + 1)]
    E, ab, em = [], [], []
    amx, amax = 0, E00
    for i in range(301):
        e = x0 + (x1 - x0) * i / 300
        a = m = 0
        for v in range(nv + 1):
            p = pois(S, v)
            a += p * gauss(e, E00 + v * w, fw)
            m += p * gauss(e, E00 - v * w, fw)
        E.append(e)
        ab.append(a)
        em.append(m)
        if a > amx:
            amx, amax = a, e
    mx = max([amx] + em)
    pm = max(P)
    sticks = [[v, P[v] / pm] for v in range(nv + 1) if not P[v] < 1e-3]
    return {"x0": x0, "x1": x1, "nv": nv, "E": E, "ab": [a / mx for a in ab], "em": [m / mx for m in em],
            "sticks": sticks, "amax": amax}


def state(S: float, w_cm: float, E00: float, fw_cm: float) -> dict:
    w, fw = w_cm / CM, fw_cm / CM
    sp = _spec(S, w, E00, fw)
    ea, ee, st = E00 + S * w, E00 - S * w, 2 * S * w
    vmax = 0
    for v in range(1, 40):
        if pois(S, v) > pois(S, vmax):
            vmax = v
    return {"w": w, "fw": fw, "wcm": w * CM, "fwcm": fw * CM, "lam00": NM / E00, "ea": ea, "ee": ee, "st": st,
            "stcm": st * CM, "lamA": NM / ea, "lamE": NM / ee, "vmax": vmax, "lamMax": NM / sp["amax"],
            "pot": _pot(S, w, E00), "spec": sp}


def jab(E1: float, K: float) -> dict:
    ET = E1 - 2 * K
    return {"ET": ET, "K2": 2 * K, "lam1": NM / E1, "lamT": NM / ET if ET else None}


def spectrum(rows, unit: str, fw: float) -> dict:
    if not rows or any(len(r) < 2 or not r[0] > 0 or not r[1] >= 0 for r in rows) or not fw > 0:
        return {"err": "input"}
    tr = [{"e": NM / e if unit == "nm" else e, "f": f} for e, f in ((r[0], r[1]) for r in rows)]
    emin = max(0.5, min(t["e"] for t in tr) - 3 * fw)
    emax = max(t["e"] for t in tr) + 3 * fw
    N, pts, mx = 500, [], 0
    for i in range(N + 1):
        e = emin + (emax - emin) * i / N
        s = 0
        for t in tr:
            s += t["f"] * gauss(e, t["e"], fw)
        pts.append([e, s])
        mx = max(mx, s)
    if not mx > 0:
        return {"err": "zero", "tr": tr}
    pk = [[pts[i][0], pts[i][1] / mx, NM / pts[i][0]] for i in range(1, N)
          if pts[i][1] > pts[i - 1][1] and pts[i][1] >= pts[i + 1][1] and pts[i][1] > 0.05 * mx]
    return {"tr": tr, "emin": emin, "emax": emax, "pts": [[e, v / mx] for e, v in pts], "mx": mx,
            "fm": max(t["f"] for t in tr), "pk": pk}
