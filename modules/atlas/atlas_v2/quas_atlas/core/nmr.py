"""NMR: Larmor frequencies, chemical shifts from computed shieldings, first-order multiplets (Atlas).

HEADER
    Model of the page "ЯМР: от экранирования к химическому сдвигу" (web/<lang>/nmr.html).
    Wilkinson convention, sections 1-8.

§1 THEORY
    A nucleus with gyromagnetic ratio γ in a field B0 precesses at ν0 = γ B0 / 2π. The electrons shield it:
    the local field is B0 (1 - σ), σ (ppm) is the isotropic shielding a program prints (GIAO). The chemical
    shift relative to a reference (TMS for 1H and 13C) is
        δ = (σ_ref - σ) / (1 - σ_ref) ≈ σ_ref - σ (σ_ref ≪ 10^6 ppm),
    both shieldings computed with the same method and basis. Empirical linear scaling replaces σ_ref by a
    fitted line σ = b + m δ, i.e. δ = (b - σ) / (-m); m = -1, b = σ_ref gives the plain difference.
    One ppm is |ν0| / 10^6 MHz = |ν0| Hz: 400 Hz at 400 MHz. A first-order multiplet of a nucleus with n
    equivalent spin-1/2 neighbours has n + 1 lines J apart (Hz) with binomial intensities C(n, k); in ppm
    the splitting is J / ν0, so it shrinks at a higher field while shifts (ppm) stay.
    γ/2π, MHz/T (CODATA 2018 for 1H; IUPAC 2001 tables for the others): 1H 42.577478, 13C 10.70838,
    15N -4.31726, 19F 40.07757, 31P 17.25144.

§2 ALGORITHM
    larmor: ν0 = γ B0 for every nucleus. shifts: the linear formula above for each σ. multiplet:
    positions δ + (k - n/2) J / ν0, intensities C(n, k) / 2^n. spectrum: sum of Lorentzians of the
    lines, FWHM w (Hz), sampled on N points of [lo, hi] ppm.

§3 APPLICATIONS
    Endpoints nmr.larmor, nmr.shifts, nmr.multiplet, nmr.spectrum.

§4 SPECIFICATION
    larmor(B0) -> {"nu": {nucleus: MHz}, "hz_per_ppm": {nucleus: Hz}}.
    shifts(sigmas, ref, slope, intercept, exact) -> {"delta": [...], "ref": used reference}.
    multiplet(n, J, nu0, delta) -> {"lines": [[ppm, rel]], "width_ppm", "width_hz"}.
    spectrum(peaks, nu0, fwhm, lo, hi, N) -> {"x": [...], "y": [...]} (y normalised to max 1).

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    Pure Python (math only); sums of < 10^4 terms.
§7 TEST CASES (tests/test_atlas_new_topics.py)
    ν0(1H, 9.3947 T) = 400.0 MHz within 0.01; δ(σ_ref - σ) for TMS itself = 0; a triplet n = 2 has
    intensities 1:2:1 and width 2J; the multiplet width in ppm halves from 300 to 600 MHz.
§8 ERROR ANALYSIS
    The model error (method, basis, solvent, conformers: 0.1-0.3 ppm for 1H, 2-5 ppm for 13C with good
    DFT) dominates the arithmetic (< 1e-12 ppm).
"""
from __future__ import annotations

import math

GAMMA = {"1H": 42.577478, "13C": 10.70838, "15N": -4.31726, "19F": 40.07757, "31P": 17.25144}


def larmor(B0: float) -> dict:
    if not 0 < B0 <= 100:
        raise ValueError("B0: 0..100 T")
    nu = {k: g * B0 for k, g in GAMMA.items()}
    return {"nu": nu, "hz_per_ppm": {k: abs(v) for k, v in nu.items()}}


def shifts(sigmas: list, ref: float, slope: float = -1.0, intercept: float | None = None, exact: bool = False) -> dict:
    if not sigmas or len(sigmas) > 500:
        raise ValueError("1..500 shieldings")
    if slope == 0:
        raise ValueError("slope must not be 0")
    b = ref if intercept is None else intercept
    if exact and slope == -1.0 and intercept is None:
        delta = [(ref - s) / (1 - ref * 1e-6) for s in sigmas]
    else:
        delta = [(b - s) / (-slope) for s in sigmas]
    return {"delta": delta, "ref": b}


def multiplet(n: int, J: float, nu0: float, delta: float = 0.0) -> dict:
    if not 0 <= n <= 12:
        raise ValueError("n: 0..12")
    if not 0 <= J <= 500 or not nu0 > 0:
        raise ValueError("J: 0..500 Hz, nu0 > 0")
    step = J / nu0  # ppm (Hz / MHz)
    lines = [[delta + (k - n / 2) * step, math.comb(n, k) / 2**n] for k in range(n + 1)]
    return {"lines": lines, "width_ppm": n * step, "width_hz": n * J}


def spectrum(peaks: list, nu0: float, fwhm: float = 1.0, lo: float = -1.0, hi: float = 12.0, N: int = 1200) -> dict:
    """peaks: [{"delta": ppm, "count": nuclei, "n": neighbours, "J": Hz}]."""
    if not peaks or len(peaks) > 60 or not 10 <= N <= 5000 or not hi > lo or not fwhm > 0:
        raise ValueError("bad spectrum parameters")
    lines = []
    for p in peaks:
        m = multiplet(int(p.get("n", 0)), float(p.get("J", 0.0)), nu0, float(p["delta"]))
        lines += [[x, w * float(p.get("count", 1))] for x, w in m["lines"]]
    g = fwhm / nu0 / 2  # half width in ppm
    xs = [lo + (hi - lo) * i / (N - 1) for i in range(N)]
    ys = [sum(w * g * g / ((x - c) ** 2 + g * g) for c, w in lines) for x in xs]
    top = max(ys) or 1.0
    return {"x": xs, "y": [y / top for y in ys], "lines": lines}
