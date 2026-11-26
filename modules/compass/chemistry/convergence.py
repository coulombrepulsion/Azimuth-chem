"""Convergence series of a plane-wave calculation: the cutoff and the grid of k-points.

§1 THEORY
    A plane-wave result depends on two numerical parameters that have nothing to do with the crystal: the kinetic
    energy cutoff of the basis (ecutwfc, with ecutrho for the density) and the density of the grid of k-points. Both
    are raised until the quantity of interest stops changing: the total energy per atom (variational in the cutoff:
    it only goes down as the cutoff grows), the pressure (from the stress — it converges more slowly than the energy,
    by the Pulay stress of an incomplete basis) and the gap. A parameter is called converged from the first value
    after which every later one stays within the tolerance of the last, most accurate one.
§2 ALGORITHM
    cutoffs(base, dual): seven values of ecutwfc around the base (the value of the library or of the settings), from
    base − 2·STEP to base + 4·STEP in steps of STEP = 10 Ry, not below FLOOR = 20 Ry, each with ecutrho = dual × ecutwfc
    (dual — that of the library, 4 for norm-conserving files, 8–12 for ultrasoft and PAW).
    grids(base): the grid of the settings multiplied by FACTORS along every axis (an axis of one point — a slab or a
    molecule in a box — stays one), without repeats, in the order of the number of points.
    rows(points): ΔE per atom from the last point (meV), the pressure and the gap as given.
    converged(rows, key, tolerance): the index of the first row from which |x − x_last| ≤ tolerance holds to the end;
    None when even the last but one is outside (the series is too short).
§4 SPECIFICATION
    Point(label, energy eV per cell, atoms, pressure kbar | None, gap eV | None);
    Row(label, energy_per_atom eV, delta meV per atom, pressure, gap); TOLERANCE_MEV = 1.0, TOLERANCE_KBAR = 1.0.
    summary(rows) -> the lines of the conclusion (Russian, keys of tr). ValueError with a message for the user.
§7 TESTS
    tests/compass/test_crystal_convergence.py.
"""

from __future__ import annotations

from dataclasses import dataclass

from azimuth.i18n import tr

STEP, FLOOR = 10.0, 20.0  # Ry
FACTORS = (0.5, 0.75, 1.0, 1.25, 1.5, 2.0)
TOLERANCE_MEV, TOLERANCE_KBAR = 1.0, 1.0


@dataclass(frozen=True)
class Point:
    label: str
    energy: float
    atoms: int
    pressure: float | None = None
    gap: float | None = None


@dataclass(frozen=True)
class Row:
    label: str
    energy_per_atom: float
    delta: float
    pressure: float | None
    gap: float | None


def cutoffs(base, dual=4.0):
    """[(ecutwfc, ecutrho)] of the series around base (Ry), ascending (§2)."""
    if not base or base <= 0 or not dual or dual < 1:
        raise ValueError(tr('Ряд по обрезанию: не задана энергия обрезания.'))
    centre = int(base / STEP + 0.5) * STEP if base >= FLOOR else FLOOR  # 45 → 50 (round() would give 40)
    values = sorted({max(FLOOR, centre + k * STEP) for k in range(-2, 5)})
    return [(float(v), float(round(v * dual, 6))) for v in values]


def grids(base):
    """The grids of the series from the grid (n1, n2, n3) of the settings (§2)."""
    if not base or len(base) != 3 or any(type(n) is not int or n < 1 for n in base):
        raise ValueError(tr('Ряд по k-сетке: сетка задана неверно.'))
    found = []
    for factor in FACTORS:
        grid = tuple(1 if n == 1 else max(1, round(n * factor)) for n in base)
        if grid not in found:
            found.append(grid)
    return sorted(found, key=lambda g: (g[0] * g[1] * g[2], g))


def rows(points):
    """The table of the series, ΔE from its last point."""
    points = [p for p in points if p is not None]
    if len(points) < 3:
        raise ValueError(tr('В ряду меньше трёх посчитанных точек — о сходимости судить не по чему.'))
    last = points[-1].energy / points[-1].atoms
    return [Row(p.label, p.energy / p.atoms, 1000.0 * (p.energy / p.atoms - last), p.pressure, p.gap) for p in points]


def converged(table, key='delta', tolerance=TOLERANCE_MEV):
    """The index of the first row within the tolerance of the last one to the end of the series, or None (§2)."""
    values = [getattr(r, key) for r in table]
    if any(v is None for v in values) or len(values) < 3:
        return None
    last = values[-1]
    first = None
    for k in range(len(values) - 2, -1, -1):
        if abs(values[k] - last) <= tolerance:
            first = k
        else:
            break
    return first


def summary(table):
    """The conclusion of a series: from which value the energy and the pressure stay within the tolerances."""
    lines = []
    energy = converged(table, 'delta', TOLERANCE_MEV)
    if energy is None:
        lines.append(tr('Энергия не сошлась до {:g} мэВ на атом в пределах ряда: продолжите ряд.').format(TOLERANCE_MEV))
    else:
        lines.append(tr('Энергия сошлась до {:g} мэВ на атом начиная с {}.').format(TOLERANCE_MEV, table[energy].label))
    pressure = converged(table, 'pressure', TOLERANCE_KBAR)
    if any(r.pressure is not None for r in table):
        if pressure is None:
            lines.append(tr('Давление не сошлось до {:g} кбар: для оптимизации ячейки нужно значение больше.').format(TOLERANCE_KBAR))
        elif energy is not None and pressure > energy:
            lines.append(tr('Давление сходится медленнее: до {:g} кбар — начиная с {}; для оптимизации ячейки берите '
                            'это значение.').format(TOLERANCE_KBAR, table[pressure].label))
        else:
            lines.append(tr('Давление сошлось до {:g} кбар начиная с {}.').format(TOLERANCE_KBAR, table[pressure].label))
    return lines
