"""The map of a two-dimensional relaxed scan: energies on a grid, isolines, the valley.

§1 PURPOSE
    A scan of two coordinates (ORCA «%geom Scan» with two lines: for every value of the first all values of the second)
    is a surface E(q₁, q₂). Compass draws it as a coloured map with isolines; a click on a point shows its geometry. The
    valley — the lowest point of every column — shows where the relaxed path of the first coordinate runs.
§2 ALGORITHM
    grid: the distinct values of each coordinate (rounded to 1e-6), the points put in their cells; a missing or failed
    point is NaN. fine: bilinear interpolation of the grid (factor cells per cell) for the colours and the isolines.
    isolines: marching squares on the fine grid, the crossing on every edge by linear interpolation; cells with a NaN
    corner are skipped. levels: «nice» steps (1, 2, 2.5, 5 × 10ⁿ) giving about count levels between the lowest and the
    highest energy. valley: for every value of the first coordinate the second with the lowest energy.
§3 INTERFACE
    Grid(xs, ys, energy (len(ys), len(xs)) hartree with NaN, index (len(ys), len(xs)) point index or -1, labels);
    grid(scan) -> Grid or None (not two coordinates); fine(xs, ys, z, factor) -> (fx, fy, fz); levels(lo, hi, count=10)
    -> list; isolines(xs, ys, z, level) -> [((x1, y1), (x2, y2))]; valley(g) -> [(x, y, index)]; minimum(g) ->
    (x, y, index); nearest(g, x, y, sx=1, sy=1) -> index (sx, sy scale the axes to comparable lengths).
§4 TESTS
    tests/spectrum/test_scan_map.py — the water 5 × 5 scan of the two O–H bonds of ORCA 6.0.1 (tests/data/scan2d):
    the map is symmetric, E(r₁, r₂) = E(r₂, r₁), the minimum near the optimized 0.96 Å.
"""

from dataclasses import dataclass
from math import floor, log10

import numpy as np


@dataclass
class Grid:
    xs: np.ndarray
    ys: np.ndarray
    energy: np.ndarray
    index: np.ndarray
    labels: tuple


def grid(scan):
    if scan is None or len(scan.coordinates) != 2 or not scan.points:
        return None
    xs = np.array(sorted({round(p.values[0], 6) for p in scan.points}))
    ys = np.array(sorted({round(p.values[1], 6) for p in scan.points}))
    if len(xs) < 2 or len(ys) < 2:
        return None
    energy = np.full((len(ys), len(xs)), np.nan)
    index = np.full((len(ys), len(xs)), -1, dtype=int)
    col = {v: k for k, v in enumerate(xs)}
    row = {v: k for k, v in enumerate(ys)}
    for k, p in enumerate(scan.points):
        i, j = row[round(p.values[1], 6)], col[round(p.values[0], 6)]
        index[i, j] = k
        if p.energy is not None:
            energy[i, j] = p.energy
    labels = tuple(c.label + (', ' + c.unit if c.unit else '') for c in scan.coordinates)
    return Grid(xs, ys, energy, index, labels)


def fine(xs, ys, z, factor=8):
    """Bilinear refinement: (fx, fy, fz) with factor sub-cells per cell."""
    fx = np.linspace(xs[0], xs[-1], (len(xs) - 1) * factor + 1)
    fy = np.linspace(ys[0], ys[-1], (len(ys) - 1) * factor + 1)
    ix = np.clip(np.searchsorted(xs, fx, side='right') - 1, 0, len(xs) - 2)
    iy = np.clip(np.searchsorted(ys, fy, side='right') - 1, 0, len(ys) - 2)
    tx = (fx - xs[ix]) / (xs[ix + 1] - xs[ix])
    ty = (fy - ys[iy]) / (ys[iy + 1] - ys[iy])
    z00 = z[np.ix_(iy, ix)]
    z01 = z[np.ix_(iy, ix + 1)]
    z10 = z[np.ix_(iy + 1, ix)]
    z11 = z[np.ix_(iy + 1, ix + 1)]
    a, b = tx[None, :], ty[:, None]
    fz = z00 * (1 - a) * (1 - b) + z01 * a * (1 - b) + z10 * (1 - a) * b + z11 * a * b
    return fx, fy, fz


def levels(lo, hi, count=10):
    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo:
        return []
    raw = (hi - lo) / count
    power = 10 ** floor(log10(raw))
    step = min((m * power for m in (1, 2, 2.5, 5, 10) if m * power >= raw), default=10 * power)
    first = np.ceil(lo / step) * step
    return [float(v) for v in np.arange(first, hi, step) if v > lo]


def isolines(xs, ys, z, level):
    """Segments of the isoline z = level (marching squares; the two saddle cases joined by the centre value)."""
    segments = []
    for i in range(len(ys) - 1):
        for j in range(len(xs) - 1):
            c = (z[i, j], z[i, j + 1], z[i + 1, j + 1], z[i + 1, j])
            if any(np.isnan(v) for v in c):
                continue
            p = ((xs[j], ys[i]), (xs[j + 1], ys[i]), (xs[j + 1], ys[i + 1]), (xs[j], ys[i + 1]))
            cross = []
            for e in range(4):
                a, b = c[e], c[(e + 1) % 4]
                if (a < level) != (b < level):
                    t = (level - a) / (b - a)
                    pa, pb = p[e], p[(e + 1) % 4]
                    cross.append((e, (pa[0] + t * (pb[0] - pa[0]), pa[1] + t * (pb[1] - pa[1]))))
            if len(cross) == 2:
                segments.append((cross[0][1], cross[1][1]))
            elif len(cross) == 4:
                centre = sum(c) / 4
                first_low = c[0] < level
                if (centre < level) == first_low:  # the corner 0 joins the centre: pair the edges 0–1 and 2–3
                    segments += [(cross[0][1], cross[3][1]), (cross[1][1], cross[2][1])]
                else:
                    segments += [(cross[0][1], cross[1][1]), (cross[2][1], cross[3][1])]
    return segments


def valley(g):
    found = []
    for j, x in enumerate(g.xs):
        column = g.energy[:, j]
        if np.all(np.isnan(column)):
            continue
        i = int(np.nanargmin(column))
        found.append((float(x), float(g.ys[i]), int(g.index[i, j])))
    return found


def minimum(g):
    i, j = np.unravel_index(np.nanargmin(g.energy), g.energy.shape)
    return float(g.xs[j]), float(g.ys[i]), int(g.index[i, j])


def nearest(g, x, y, sx=1.0, sy=1.0):
    best, found = None, -1
    for i, yv in enumerate(g.ys):
        for j, xv in enumerate(g.xs):
            if g.index[i, j] < 0:
                continue
            d = ((xv - x) / sx) ** 2 + ((yv - y) / sy) ** 2
            if best is None or d < best:
                best, found = d, int(g.index[i, j])
    return found
