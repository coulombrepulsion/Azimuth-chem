"""A measured powder pattern against the calculated one: the background, the zero shift, the agreement,
the lines found and missing, the change of the cell — as the comparison of patterns in Mercury.

§1 THEORY
    A measured pattern y(2θ) = background + the lines of the phase (+ of other phases) + noise. The background is slow:
    the mean in a window of BACKGROUND° of the pattern whose points above it by 2σ of the noise (the peaks) are cut to
    it, repeated from the lower envelope; σ — from the differences of neighbouring points (the median absolute
    deviation). The zero of the goniometer and the displacement of the sample move
    every line by about the same Δ2θ: the shift is the one that best lays the calculated profile on the measured one
    (the largest correlation, searched in ±MAX_SHIFT°). The scale s = Σ y_obs y_calc / Σ y_calc² (least squares); the
    agreement R = √(Σ (y_obs − s y_calc)² / Σ y_obs²) over the pattern (an R_p of a profile without refinement:
    about 10 % — the same phase with its noise; tens of % — other intensities, another phase or a texture) and the
    correlation r. A peak of the
    measured pattern — a local maximum above PEAK of the highest. The zero shift z and the change of the cell ε (every
    d larger by 1 + ε: 2θ = 2 asin(λ / 2d(1 + ε)) + z) are found together: the grid of ε (±3 %) and z (±0.6°) that best
    lays the strong lines on the peaks, then least squares on the peaks matched (Δ2θ ≈ z − (360/π) tan θ · ε). A line
    is matched to the nearest peak within MATCH° of its place; the lines of the phase above STRONG % not found — missing
    (texture, another setting); the
    peaks left — of another phase or an impurity. The cell: d_obs = λ / (2 sin θ_obs) of the matched lines; the mean
    d_obs/d_calc − 1 is the change of the lattice (thermal expansion between the temperature of the CIF and that of
    the measurement, a solid solution); its sign tells the direction: the shift of the zero is the same at all angles,
    that of the cell grows as tan θ.
§4 SPECIFICATION match(lines, xs, ys, wavelength, fwhm=0.1, eta=0.5, uvw=None, alpha2=None) -> Match(shift °, scale,
    r_profile, correlation, background (list), pairs [(line, 2θ_obs, Δ)], missing [line], extra [(2θ, I %)], cell_change
    (relative) | None, measured (x, y − bg, scaled to the calculated 100), calculated (x, y)). The calculated curve with
    the shape of the window — the Lorentzian share eta, the widths of Caglioti uvw = (U, V, W), the Kα₂ lines alpha2 =
    (λ₂, ratio) put by the same zero and cell (the lines are matched by Kα₁, the strongest of each doublet).
§7 TESTS tests/compass/test_powder_match.py — a pattern of rock salt made from the calculated one with a background, a
    shift of +0.12°, a 0.5 % larger cell and a peak of another phase.
"""

from dataclasses import dataclass
from math import asin, degrees, radians

import numpy as np

BACKGROUND = 3.0  # degrees
MAX_SHIFT = 0.6
MAX_STRAIN = 0.03  # ±3 % of d
PEAK = 0.04
MATCH = 0.25
STRONG = 5.0


@dataclass
class Match:
    shift: float
    scale: float
    r_profile: float
    correlation: float
    background: list
    pairs: list
    missing: list
    extra: list
    cell_change: float | None
    measured: tuple
    calculated: tuple


def _window(values, width, how):
    n = len(values)
    half = max(1, width // 2)
    padded = np.concatenate([np.full(half, values[0]), values, np.full(half, values[-1])])
    view = np.lib.stride_tricks.sliding_window_view(padded, 2 * half + 1)[:n]
    return view.min(axis=1) if how == 'min' else view.mean(axis=1)


def background(xs, ys, width=BACKGROUND, rounds=30):
    """The slow background under the peaks: the mean in a window of width° of the pattern with its peaks cut off —
    a point higher than the background by 2σ of the noise (σ from the differences of neighbouring points) is a peak,
    replaced by the background; repeated rounds times from the smoothed lower envelope."""
    xs, ys = np.asarray(xs, float), np.asarray(ys, float)
    step = float(np.median(np.diff(xs))) if len(xs) > 1 else 1.0
    points = max(3, int(width / step))
    d = np.diff(ys)
    sigma = float(np.median(np.abs(d - np.median(d))) / 0.6745 / np.sqrt(2)) if len(d) else 0.0
    bg = _window(_window(ys, points, 'min'), points, 'mean') + 2 * sigma
    for _ in range(rounds):
        bg = _window(np.where(ys > bg + 2 * sigma, bg, ys), points, 'mean')
    return bg


def _positions(lines, wavelength, strain=0.0, shift=0.0):
    """2θ of the lines in a cell larger by strain (d·(1 + strain)) and moved by shift (°)."""
    out = []
    for line in lines:
        q = wavelength / (2 * line.d * (1 + strain))
        out.append(degrees(2 * asin(min(1.0, q))) + shift)
    return np.array(out)


def _peaks(x, y, least):
    inner = (y[1:-1] > y[:-2]) & (y[1:-1] >= y[2:]) & (y[1:-1] > least)
    return [int(k) + 1 for k in np.nonzero(inner)[0]]


def _top(x, y, k):
    """The top of the peak at node k between the nodes (a parabola through three points)."""
    a, b, c = y[k - 1], y[k], y[k + 1]
    curvature = a - 2 * b + c
    return float(x[k] + (0.5 * (a - c) / curvature * (x[k + 1] - x[k]) if curvature else 0.0))


def _pairs(lines, positions, tops, used_limit=MATCH):
    pairs, used = [], set()
    for n in np.argsort([-line.intensity for line in lines]):
        if not len(tops):
            break
        k = int(np.argmin(np.abs(tops - positions[n])))
        if k in used or abs(tops[k] - positions[n]) > used_limit:
            continue
        used.add(k)
        pairs.append((int(n), k))
    return pairs


def match(lines, xs, ys, wavelength, fwhm=0.1, eta=0.5, uvw=None, alpha2=None):
    x, raw = np.asarray(xs, float), np.asarray(ys, float)
    order = np.argsort(x)
    x, raw = x[order], raw[order]
    lines = [line for line in lines if x[0] <= line.two_theta <= x[-1]]
    if len(x) < 10 or not lines:
        raise ValueError('a pattern of 10 points or more and calculated lines in its range are needed')
    bg = background(x, raw)
    obs = raw - bg
    smooth = _window(obs, 3, 'mean')
    top = float(smooth.max()) or 1.0
    found = _peaks(x, smooth, PEAK * top)
    tops = np.array([_top(x, smooth, k) for k in found])
    heights = np.array([smooth[k] for k in found])
    # the shift of the zero and the change of the cell: the best overlap of the strong lines with the peaks found
    strong = [line for line in lines if line.intensity >= 1.0]
    weights = np.array([line.intensity for line in strong])
    zs = np.arange(-MAX_SHIFT, MAX_SHIFT + 1e-9, 0.005)
    best = (-1.0, 0.0, 0.0)
    if len(tops):
        for strain in np.arange(-MAX_STRAIN, MAX_STRAIN + 1e-12, 0.0002):
            p = _positions(strong, wavelength, strain)
            delta = tops[None, None, :] - (p[None, :, None] + zs[:, None, None])
            score = (weights[None, :] * np.exp(-(delta / 0.06) ** 2).max(axis=2)).sum(axis=1)
            k = int(np.argmax(score))
            if score[k] > best[0] + 1e-9:
                best = (float(score[k]), float(zs[k]), float(strain))
    _, shift, strain = best
    # refined by least squares on the matched peaks: Δ2θ ≈ z − (360/π) tan θ · ε
    for _ in range(3):
        positions = _positions(lines, wavelength, strain, shift)
        pairs = _pairs(lines, positions, tops)
        if len(pairs) < 3:
            break
        tan = np.array([np.tan(radians(lines[n].two_theta / 2)) for n, _ in pairs])
        design = np.stack([np.ones(len(pairs)), -360 / np.pi * tan], axis=1)
        observed = np.array([tops[k] - _positions([lines[n]], wavelength)[0] for n, k in pairs])
        if np.ptp(tan) < 0.05:  # the lines too close together: the shift alone
            shift = float(observed.mean())
            continue
        (shift, strain), *_ = np.linalg.lstsq(design, observed, rcond=None)
        shift, strain = float(shift), float(strain)
    positions = _positions(lines, wavelength, strain, shift)
    from modules.compass.chemistry import powder

    centres, heights_, shown_lines = list(positions), [line.intensity for line in lines], list(lines)
    if alpha2:  # the Kα₂ doublets by the same zero and cell
        second = powder.alpha2(lines, wavelength, alpha2[0], alpha2[1])
        by_line = {(line.d, line.hkl): line for line in second}
        doubles = [(line, by_line[(line.d, line.hkl)]) for line in lines if (line.d, line.hkl) in by_line]
        centres += list(_positions([b for _, b in doubles], alpha2[0], strain, shift))
        heights_ += [b.intensity for _, b in doubles]
        shown_lines += [b for _, b in doubles]
    widths = [powder.caglioti(line.two_theta, *uvw) if uvw else fwhm for line in shown_lines]
    calc = powder.curve(x, centres, heights_, widths, eta)
    scale = float(obs @ calc / (calc @ calc)) if calc @ calc else 0.0
    norm = np.linalg.norm(calc) * np.linalg.norm(obs)
    correlation = float(obs @ calc / norm) if norm else 0.0
    r_profile = float(np.sqrt(((obs - scale * calc) ** 2).sum() / (obs ** 2).sum())) if (obs ** 2).sum() else 1.0
    matched = _pairs(lines, positions, tops)
    pairs = sorted(((lines[n], float(tops[k]), float(tops[k] - positions[n])) for n, k in matched),
                   key=lambda p: p[0].two_theta)
    taken = {k for _, k in matched}
    named = {id(lines[n]) for n, _ in matched}
    missing = [line for line in lines if line.intensity >= STRONG and id(line) not in named]
    extra = [(float(tops[k]), 100 * float(heights[k]) / top) for k in range(len(tops))
             if k not in taken and heights[k] >= 2 * PEAK * top]
    shown = obs / top * 100
    calculated = scale * calc / top * 100
    return Match(shift, scale, r_profile, correlation, bg.tolist(), pairs, missing, extra,
                 strain if len(matched) >= 3 else None, (x.tolist(), shown.tolist()), (x.tolist(), calculated.tolist()))
