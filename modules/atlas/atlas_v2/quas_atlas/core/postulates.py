"""Postulates of quantum mechanics on the particle in a box.

HEADER
    Numerical model of the Atlas page "Postulates and measurement"
    (web/<lang>/postulates.html): superposition, time evolution, energy and
    position measurements with collapse. Port of the v1.0 page script.
    Wilkinson convention, §1-§8.

§1 THEORY
    Units: box length L = 1, hbar = 1, m chosen so that E_n = n^2 E_1 and
    time is measured in T_1 = 2 pi hbar / E_1. Eigenfunctions
        psi_n(x) = sqrt(2) sin(n pi x), 0 <= x <= 1, n = 1..48.
    A state is Psi = sum_n c_n psi_n; its time evolution
        c_n(t) = c_n(t0) exp(-i 2 pi n^2 (t - t0)) (t in T_1).
    Born rule: an energy measurement gives E_n with probability |c_n|^2 and
    leaves psi_n (times the phase c_n(t)/|c_n(t)|). Expectation values:
        <E> = sum |c_n|^2 n^2, <E^2> = sum |c_n|^2 n^4,
        <p^2> = sum |c_n|^2 (n pi)^2,
        <p> = sum_mn c_m^* c_n p_mn, p_mn = -i 2 m n (1 - (-1)^{m+n}) / (m^2 - n^2)
              (purely imaginary; 0 for m + n even),
        <x>, <x^2> from |Psi|^2 by the trapezoidal rule on 401 points.
    Position measurement with resolution sigma (idealised): the result x0
    is drawn from |Psi(x, t)|^2, the new state is the Gaussian packet
    g(x) = exp(-(x - x0)^2 / (4 sigma^2)) inside the box, expanded in psi_n
    (c_n = int psi_n g dx by the trapezoidal rule, then normalised).
    Observables as operators (section 4 of the page): with E in
    E_1 and p in hbar/L,
        H Psi = sum c_n n^2 psi_n, p Psi = -i sum c_n sqrt2 n pi cos(n pi x),
        x Psi = x Psi.
    Psi is an eigenfunction of A when A Psi = lambda Psi; for a normalised
    Psi and Hermitian A, lambda = <A> and ||A Psi - <A> Psi||^2 = <A^2> -
    <A>^2 = (Delta A)^2, so the residual is the spread of the measured values.
    Expectation value from a series (section 5): the mean of N measured E_k
    tends to <E> = sum |c_n|^2 n^2 with standard error Delta E / sqrt N.

§2 ALGORITHM
    prepare(a[4], ph[4]): c_k = a_k/|a| e^{i ph_k} for k < 4, else 0.
    evolve(C, t, t0): c_n e^{i th}, th = -2 pi n^2 (t - t0).
    frame(C, t, t0): evolve; Psi on the grid (terms with |re| + |im| < 1e-9
    skipped); |Psi|^2; observables (§1); probabilities |c_n|^2 / sum.
    sample(P, r): smallest k with r - P_1 - ... - P_k <= 0 (inverse CDF for
    a uniform r in [0, 1) supplied by the caller), capped at the last index.
    measure_energy, measure_many, measure_position as in §1.

§3 APPLICATIONS
    Stationary states (|Psi|^2 constant), beats of superpositions with
    revival at T_1, uncertainty relation Delta x Delta p >= 1/2, collapse
    and repeated measurement, statistics of many measurements approaching
    |c_n|^2, the energy spread of a narrow packet.

§4 SPECIFICATION
    C: list of 48 dicts {re, im} (amplitudes at epoch t0).
    t, t0: float (units of T_1); r: float in [0, 1) (uniform random number
    drawn by the browser); sigma in [0.005, 0.2] (units of L).
    prepare(a, ph) -> C. a: 4 amplitudes >= 0 (not all 0), ph: 4 phases
        in radians.
    frame(C, t, t0) -> {ps2: [401] |Psi|^2, re: [401] Re Psi,
        obs: {E, dE, x, dx, p, dp}, P: [48] probabilities}.
    measure_energy(C, t, t0, r) -> {k (0-based), P, C (collapsed)}.
    measure_many(a, ph, rs) -> {C (prepared), P, ks: [len(rs)]}.
    measure_position(C, t, t0, r, sigma) -> {x0, C, P}.
    operator(C, t, t0, op) -> {re, im: [401] Psi; are, aim: [401] A Psi;
        mean: <A>; spread: ||A Psi - <A> Psi|| (trapezoid on the grid);
        rel: spread / ||A Psi||}. op in {"H", "p", "x"}.
    mean_series(a, ph, rs) -> {P, n2: [48] n^2, mean: <E>, dE, ks,
        running: [len(rs)] mean of the first N outcomes in E_1}.
    Reference: v1.0 postulates.html (fromPrep, Ct, psiAt, probs,
    observables, sample, collapseTo, the bMX handler).
    Equivalence tier ``bound``: same operation order; sin/cos/exp/sqrt/hypot
    from different libm (V8 vs C) -> B = 1e-12 absolute for every returned
    float (§8); the discrete results (k, ks, index of x0) are identical
    unless r falls within 1e-12 of a cumulative-probability boundary.

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    * sample(P) returns index 0 even when P_0 = 0 (r - 0 <= 0); kept
      from v1.0. Math.random() returns exactly 0 with probability 2^-53.
    * Delta E and Delta x use sqrt(<A^2> - <A>^2); for a sharp value the
      difference is rounding noise and the result is ~1e-8, not 0 (shown as
      0,000 on the page).
    * The evolution uses the absolute phase -2 pi n^2 (t - t0); for long
    animations t - t0 grows, and the phase argument (up to 2 pi 48^2 t)
    loses relative precision like any large argument -- harmless here
    (t - t0 < 10^3 gives |th| < 1.5e7, absolute phase error < 4e-9 rad).
§7 TEST CASES (tests/test_atlas_postulates.py; the older cases below were
    checked against v1.0 and are kept as the specification)
    * operator: the spread equals Delta E, Delta p, Delta x of frame() (an
      independent formula: <A^2> - <A>^2 from the amplitudes or |Psi|^2);
      H psi_n = n^2 psi_n exactly; p Psi against a centred finite difference
      of Psi on the grid (error h^2 (n pi)^3 / 6).
    * mean_series: running[-1] is the plain mean of (k+1)^2 over ks.
    * Stationary psi_1: <E> = 1, Delta E = 0, <x> = 1/2, <x^2> = 1/3 - 1/(2 pi^2)
      (closed form; trapezoid error < 1e-9, §8), |Psi|^2 independent of t.
    * Revival: frame(t0 + 1) equals frame(t0) (all phases 2 pi n^2).
    * Uncertainty: Delta x Delta p >= 1/2 for random preparations.
    * psi_1 + psi_2 (equal weights): <E> = 2.5, Delta E = 1.5 exactly.
    * measure_many: frequencies vs |c_n|^2 within 4 binomial standard
      deviations (with a fixed seed: deterministic).
    * Differential test against the v1.0 JavaScript (fixtures).
§8 ERROR ANALYSIS
    |Psi|^2 values are sums of <= 48 terms of size <= sqrt(2) |c|:
    gamma_48 * 48 sqrt 2 ~ 1e-14 absolute; sin/cos differ by <= 1 ulp
    between libraries (relative 2e-16 on each c_n(t)): total <= 1e-13.
    Observables: trapezoid sums of 401 terms of size <= |Psi|^2_max <= 100
    divided by the norm: <= 401 * 100 * u ~ 1e-11 worst case; observed
    < 1e-14. Hence B = 1e-12 for frame values on the fixtures' states and
    B = 1e-11 for <x>, Delta x.
    Model error (not an implementation difference): the trapezoidal rule
    with h = 1/400. By Euler-Maclaurin its error is
        -(h^2/12)(f'(1) - f'(0)) + (h^4/720)(f'''(1) - f'''(0)) - ...
    For f = |psi_n|^2 x^k (k = 0, 1, 2) f' vanishes at both ends
    (sin^2 has a double zero), so the error is O(h^4): with
    |f'''| <= 3 * 2 (n pi)^3 at the ends, for n = 1: 6.25e-11/720 * 372
    ~ 3e-11. The closed-form tests therefore use 1e-9.
"""
from __future__ import annotations

import functools
import math

from .jsmath import cos, exp, js_hypot, sin, sq

NMAX = 48
NG = 401
XS = [i / (NG - 1) for i in range(NG)]
SQRT2 = math.sqrt(2)  # == Math.SQRT2 (correctly rounded constant)


# Azimuth the tables of sin and cos (2 x 48 x 401 values of the correctly rounded jsmath functions, ~0.3 s)
# are built at the first calculation that needs them, not on import: the window of Azimuth imports the models of the
# Atlas while it starts. The same values; PSI and COS stay readable as attributes of this module.
@functools.lru_cache(maxsize=1)
def _psi():
    return [[SQRT2 * sin(n * math.pi * x) for x in XS] for n in range(1, NMAX + 1)]


@functools.lru_cache(maxsize=1)
def _cos():
    return [[SQRT2 * n * math.pi * cos(n * math.pi * x) for x in XS] for n in range(1, NMAX + 1)]


def __getattr__(name):
    if name == "PSI":
        return _psi()
    if name == "COS":
        return _cos()
    raise AttributeError(name)


PIM = [[0.0 if (m == n or (m + n) % 2 == 0) else -2 * m * n * 2 / (m * m - n * n)
        for n in range(1, NMAX + 1)] for m in range(1, NMAX + 1)]


def _check_C(C):
    if len(C) != NMAX or not all(isinstance(z, dict) and set(z) == {"re", "im"} for z in C):
        raise ValueError(f"C must be {NMAX} amplitudes {{re, im}}")
    return [{"re": float(z["re"]), "im": float(z["im"])} for z in C]


def prepare(a: list[float], ph: list[float]) -> list[dict]:
    """Normalised superposition of psi_1..psi_4 with amplitudes a and phases ph."""
    if len(a) != 4 or len(ph) != 4 or any(x < 0 for x in a):
        raise ValueError("a and ph must have 4 entries, a >= 0")
    s = 0.0
    for x in a:
        s = s + x * x
    s = math.sqrt(s) or 1.0
    return [{"re": a[k] / s * cos(ph[k]), "im": a[k] / s * sin(ph[k])} if k < 4 else {"re": 0.0, "im": 0.0}
            for k in range(NMAX)]


def evolve(C, t, t0):
    out = []
    for k, c in enumerate(C):
        n = k + 1
        th = -2 * math.pi * n * n * (t - t0)
        co, si = cos(th), sin(th)
        out.append({"re": c["re"] * co - c["im"] * si, "im": c["re"] * si + c["im"] * co})
    return out


def psi_at(c):
    re = [0.0] * NG
    im = [0.0] * NG
    for k, z in enumerate(c):
        if abs(z["re"]) + abs(z["im"]) < 1e-9:
            continue
        f = _psi()[k]
        for i in range(NG):
            re[i] = re[i] + z["re"] * f[i]
            im[i] = im[i] + z["im"] * f[i]
    return re, im


def probs(C):
    p = [z["re"] * z["re"] + z["im"] * z["im"] for z in C]
    s = 0.0
    for x in p:
        s = s + x
    s = s or 1.0
    return [x / s for x in p]


def observables(c, re, im):
    P = [z["re"] * z["re"] + z["im"] * z["im"] for z in c]
    E = E2 = p2 = 0.0
    for k, w in enumerate(P):
        n = k + 1
        E = E + w * n * n
        E2 = E2 + w * n ** 4
        p2 = p2 + w * sq(n * math.pi)
    x = x2 = nrm = 0.0
    dx = 1 / (NG - 1)
    for i in range(NG):
        d = sq(re[i]) + sq(im[i])
        w = 0.5 if (i == 0 or i == NG - 1) else 1.0
        nrm = nrm + w * d * dx
        x = x + w * d * XS[i] * dx
        x2 = x2 + w * d * XS[i] * XS[i] * dx
    x /= nrm
    x2 /= nrm
    p = 0.0
    for m in range(NMAX):
        if P[m] < 1e-14:
            continue
        for n in range(NMAX):
            q = PIM[m][n]
            if not q:
                continue
            a, b = c[m], c[n]
            imv = a["re"] * b["im"] - a["im"] * b["re"]  # Im(c_m^* c_n)
            p = p + -imv * q
    return {"E": E, "dE": math.sqrt(max(0.0, E2 - E * E)), "x": x, "dx": math.sqrt(max(0.0, x2 - x * x)),
            "p": p, "dp": math.sqrt(max(0.0, p2 - p * p))}


def frame(C, t: float, t0: float) -> dict:
    """|Psi(x, t)|^2, Re Psi, observables and probabilities at time t."""
    C = _check_C(C)
    c = evolve(C, t, t0)
    re, im = psi_at(c)
    return {"ps2": [sq(re[i]) + sq(im[i]) for i in range(NG)], "re": re, "obs": observables(c, re, im),
            "P": probs(C)}


def sample(P, r: float) -> int:
    """Inverse-CDF draw for a uniform r in [0, 1)."""
    if not 0 <= r < 1:
        raise ValueError("r must be in [0, 1)")
    k = 0
    while k < len(P):
        r = r - P[k]
        if r <= 0:
            break
        k += 1
    return min(k, len(P) - 1)


def measure_energy(C, t, t0, r) -> dict:
    """Energy measurement: outcome index, the probabilities, collapsed state."""
    C = _check_C(C)
    P = probs(C)
    k = sample(P, r)
    z = evolve(C, t, t0)[k]
    a = js_hypot(z["re"], z["im"]) or 1.0
    return {"k": k, "P": P,
            "C": [{"re": z["re"] / a, "im": z["im"] / a} if j == k else {"re": 0.0, "im": 0.0} for j in range(NMAX)]}


def measure_many(a, ph, rs) -> dict:
    """len(rs) independent energy measurements on freshly prepared systems."""
    C = prepare(a, ph)
    P = probs(C)
    return {"C": C, "P": P, "ks": [sample(P, r) for r in rs]}


def measure_position(C, t, t0, r, sigma) -> dict:
    """Position measurement with resolution sigma; new state = Gaussian packet."""
    C = _check_C(C)
    if not 0.005 <= sigma <= 0.2:
        raise ValueError("sigma must be in [0.005, 0.2]")
    re, im = psi_at(evolve(C, t, t0))
    P = [sq(re[i]) + sq(im[i]) for i in range(NG)]
    s = 0.0
    for x in P:
        s = s + x
    i = sample([x / s for x in P], r)
    x0 = XS[i]
    g = [exp(-(sq(x - x0)) / (4 * sigma * sigma)) * (1 if 0 < x < 1 else 0) for x in XS]
    dx = 1 / (NG - 1)
    co = []
    for f in _psi():
        sm = 0.0
        for j in range(NG):
            sm = sm + f[j] * g[j] * (0.5 if (j == 0 or j == NG - 1) else 1) * dx
        co.append(sm)
    nn = 0.0
    for v in co:
        nn = nn + v * v
    nn = math.sqrt(nn)
    newC = [{"re": v / nn, "im": 0.0} for v in co]
    return {"x0": x0, "C": newC, "P": probs(newC)}


def _trap(v):
    s = 0.0
    for i, x in enumerate(v):
        s = s + x * (0.5 if (i == 0 or i == NG - 1) else 1.0)
    return s / (NG - 1)




def operator(C, t, t0, op: str) -> dict:
    """A Psi for A = H (E_1), p (hbar/L) or x (L); <A> and the spread ||A Psi - <A> Psi||."""
    C = _check_C(C)
    if op not in ("H", "p", "x"):
        raise ValueError("op must be H, p or x")
    c = evolve(C, t, t0)
    re, im = psi_at(c)
    are, aim = [0.0] * NG, [0.0] * NG
    if op == "x":
        are = [XS[i] * re[i] for i in range(NG)]
        aim = [XS[i] * im[i] for i in range(NG)]
    else:
        for k, z in enumerate(c):
            if abs(z["re"]) + abs(z["im"]) < 1e-9:
                continue
            n = k + 1
            if op == "H":
                f, a, b = _psi()[k], z["re"] * n * n, z["im"] * n * n
            else:  # -i (a + ib) g = b g - i a g
                f, a, b = _cos()[k], z["im"], -z["re"]
            for i in range(NG):
                are[i] = are[i] + a * f[i]
                aim[i] = aim[i] + b * f[i]
    nrm = _trap([sq(re[i]) + sq(im[i]) for i in range(NG)])
    # <A> = <Psi|A Psi> / <Psi|Psi>; real for a Hermitian A (the imaginary part is rounding)
    mean = _trap([re[i] * are[i] + im[i] * aim[i] for i in range(NG)]) / nrm
    if op == "H":
        mean = observables(c, re, im)["E"]  # exact sum; the grid value differs by the quadrature error
    elif op == "p":
        mean = observables(c, re, im)["p"]
    rest = _trap([sq(are[i] - mean * re[i]) + sq(aim[i] - mean * im[i]) for i in range(NG)]) / nrm
    full = _trap([sq(are[i]) + sq(aim[i]) for i in range(NG)]) / nrm
    spread = math.sqrt(max(0.0, rest))
    return {"re": re, "im": im, "are": are, "aim": aim, "mean": mean, "spread": spread,
            "rel": spread / math.sqrt(full) if full > 0 else 0.0}


def mean_series(a, ph, rs) -> dict:
    """Energy measured on len(rs) prepared systems; the running mean against <E>."""
    C = prepare(a, ph)
    P = probs(C)
    ks = [sample(P, r) for r in rs]
    run, s = [], 0.0
    for j, k in enumerate(ks):
        s = s + (k + 1) * (k + 1)
        run.append(s / (j + 1))
    E = E2 = 0.0
    for k, w in enumerate(P):
        E = E + w * (k + 1) ** 2
        E2 = E2 + w * (k + 1) ** 4
    return {"P": P, "n2": [(k + 1) ** 2 for k in range(NMAX)], "mean": E,
            "dE": math.sqrt(max(0.0, E2 - E * E)), "ks": ks, "running": run}
