"""The equation of state of a crystal from a series of volumes: the Birch–Murnaghan fit, V₀, B₀ and B₀′.

§1 THEORY
    The energy of a crystal near its equilibrium volume, third-order Birch–Murnaghan (Birch 1947):
        E(V) = E₀ + (9 V₀ B₀ / 16) { [(V₀/V)^⅔ − 1]³ B₀′ + [(V₀/V)^⅔ − 1]² [6 − 4 (V₀/V)^⅔] },
    V₀ — the equilibrium volume, B₀ = −V dP/dV = V d²E/dV² at V₀ — the bulk modulus, B₀′ = dB/dP. With x = V^(−⅔) and
    y = x/x₀ − 1 it is a cubic polynomial without a linear term, E = E₀ + (9 V₀ B₀ / 16) [2 y² + (B₀′ − 4) y³] — so a
    cubic polynomial in x fitted by linear least squares is the Birch–Murnaghan fit itself, with nothing to iterate:
    x₀ — its minimum, B₀ = (4/9) E″(x₀) x₀^(7/2), B₀′ = 4 + (2/3) E‴(x₀) x₀ / E″(x₀).
    The pressure P(V) = −dE/dV = (3 B₀ / 2) [(V₀/V)^(7/3) − (V₀/V)^(5/3)] {1 + ¾ (B₀′ − 4) [(V₀/V)^⅔ − 1]}.
    Units: E in eV, V in Å³, B in eV/Å³ = 160.21766208 GPa.
§2 ALGORITHM
    fit(volumes, energies): at least five distinct volumes; the polynomial in x (the energies from their mean, x
    scaled by its mean — a well-conditioned system); its stationary points, the one with E″ > 0; ValueError when it
    lies outside the volumes computed (the series does not bracket the minimum) or the curve has no minimum.
    series(count, span): the factors of the volume, symmetric about 1. scaled(crystal, factor): the same fractions
    in a cell whose edges are multiplied by factor^⅓. points_of_runs(results): [(V Å³, E eV)] of the runs of pw.x.
§4 SPECIFICATION
    Fit(e0 eV, v0 Å³, b0 GPa, b0_prime, rms eV, volumes, energies); energy(fit, V) eV; pressure(fit, V) GPa.
    RY = 13.605693122994 eV. ValueError with a message for the user.
§7 TESTS
    tests/compass/test_equation_of_state.py.
§8 ERROR ANALYSIS
    B₀ is a second derivative: energies converged to 1e-5 eV per cell and volumes within ±6 % give B₀ to about 1 %;
    B₀′, a third derivative, to a few tenths. The cutoff matters more than the fit: the stress (and so V₀) converges
    more slowly with ecutwfc than the energy — check the series at a higher cutoff.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np

from azimuth.i18n import tr

GPA = 160.21766208  # GPa per eV/Å³
RY = 13.605693122994  # eV
SPAN, COUNT = 0.06, 7


@dataclass(frozen=True)
class Fit:
    e0: float
    v0: float
    b0: float
    b0_prime: float
    rms: float
    volumes: tuple
    energies: tuple


def series(count=COUNT, span=SPAN):
    """The factors of the volume: `count` of them from 1 − span to 1 + span."""
    if count < 5 or not 0.005 <= span <= 0.3:
        raise ValueError(tr('Ряд объёмов: не меньше пяти точек, размах от 0,5 до 30 %.'))
    return tuple(float(v) for v in np.linspace(1 - span, 1 + span, count))


def scaled(crystal, factor):
    """The crystal with its volume multiplied by factor (the edges by factor^⅓, the fractions kept)."""
    s = factor ** (1.0 / 3.0)
    cell = crystal.cell
    return replace(crystal, cell=replace(cell, a=cell.a * s, b=cell.b * s, c=cell.c * s))


def fit(volumes, energies):
    """The Birch–Murnaghan fit of E (eV) against V (Å³) (§1, §2)."""
    pairs = sorted({(round(float(v), 9), float(e)) for v, e in zip(volumes, energies)})
    if len({v for v, _ in pairs}) < 5:
        raise ValueError(tr('Для уравнения состояния нужно не меньше пяти разных объёмов.'))
    v = np.array([p[0] for p in pairs])
    e = np.array([p[1] for p in pairs])
    if (v <= 0).any() or not np.isfinite(v).all() or not np.isfinite(e).all():
        raise ValueError(tr('Объёмы и энергии должны быть конечными числами, объёмы — больше нуля.'))
    x = v ** (-2.0 / 3.0)
    scale, shift = x.mean(), e.mean()
    t = x / scale
    coefficients = np.polyfit(t, e - shift, 3)  # of t³, t², t, 1
    first = np.polyder(coefficients)
    second = np.polyder(first)
    roots = [float(r.real) for r in np.roots(first) if abs(r.imag) < 1e-9 and np.polyval(second, r.real) > 0]
    if not roots:
        raise ValueError(tr('У кривой E(V) нет минимума: проверьте энергии ряда.'))
    t0 = min(roots, key=lambda r: abs(r - 1.0))
    if not t.min() <= t0 <= t.max():
        raise ValueError(tr('Минимум E(V) лежит вне посчитанных объёмов: сдвиньте или расширьте ряд.'))
    x0 = t0 * scale
    v0 = x0 ** -1.5
    e2 = float(np.polyval(second, t0)) / scale ** 2  # d²E/dx²
    e3 = float(np.polyval(np.polyder(second), t0)) / scale ** 3
    b0 = 4.0 / 9.0 * e2 * x0 ** 3.5
    found = Fit(float(np.polyval(coefficients, t0)) + shift, float(v0), float(b0 * GPA), float(4.0 + 2.0 / 3.0 * e3 * x0 / e2),
                0.0, tuple(v.tolist()), tuple(e.tolist()))
    rms = float(np.sqrt(np.mean((np.array([energy(found, each) for each in v]) - e) ** 2)))
    return replace(found, rms=rms)


def energy(found, volume):
    """E(V) of the fit, eV."""
    eta = (found.v0 / volume) ** (2.0 / 3.0)
    return found.e0 + 9.0 * found.v0 * (found.b0 / GPA) / 16.0 * ((eta - 1) ** 3 * found.b0_prime + (eta - 1) ** 2 * (6 - 4 * eta))


def pressure(found, volume):
    """P(V) of the fit, GPa."""
    ratio = found.v0 / volume
    return 1.5 * found.b0 * (ratio ** (7.0 / 3.0) - ratio ** (5.0 / 3.0)) * (1 + 0.75 * (found.b0_prime - 4) * (ratio ** (2.0 / 3.0) - 1))


def volume_of(cell):
    """The volume (Å³) of a 3 × 3 cell in Å."""
    return abs(float(np.linalg.det(np.array(cell, dtype=float))))


def points_of_runs(results):
    """[(V Å³, E eV)] of the runs of pw.x (modules.spectrum.readers.qe.Result) that gave an energy and a cell."""
    found = []
    for r in results:
        if r is not None and r.energy is not None and getattr(r, 'cell', None):
            found.append((volume_of(r.cell), r.energy * RY))
    return found
