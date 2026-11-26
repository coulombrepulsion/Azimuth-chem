"""The heat capacity and the thermodynamic functions of a crystal from its phonon density of states; the Debye model.

§1 THEORY
    In the harmonic approximation a crystal is a set of independent oscillators, 3N per cell of N atoms, with the
    density of states g(ν), ∫ g dν = 3N. With x = hν/kT, per cell:
        zero-point energy   E₀ = ∫ g ½hν dν,
        internal energy     U(T) = E₀ + ∫ g hν / (eˣ − 1) dν,
        free energy         F(T) = E₀ + kT ∫ g ln(1 − e⁻ˣ) dν,
        entropy             S(T) = k ∫ g [x / (eˣ − 1) − ln(1 − e⁻ˣ)] dν   (= (U − F)/T),
        heat capacity       C_V(T) = k ∫ g x² eˣ / (eˣ − 1)² dν.
    At high temperature C_V → 3Nk (Dulong and Petit), at low temperature C_V ∝ T³.
    Debye replaces g(ν) by 9N ν²/ν_D³ up to ν_D = kΘ_D/h: C_V = 9Nk (T/Θ_D)³ ∫₀^{Θ_D/T} x⁴eˣ/(eˣ − 1)² dx, one
    parameter for the whole curve. A real crystal has no single Θ_D: the Debye temperature that reproduces C_V at
    each T, Θ(T), is a curve — nearly flat for a simple metal, with a dip for an ionic crystal whose optical branches
    lie apart from the acoustic ones. Two numbers are given: Θ_D that fits the C_V(T) of the table by least squares,
    and the high-temperature one from the second moment of the spectrum, Θ_∞ = (h/k) √(5⟨ν²⟩/3).
    What a calorimeter measures is C_P; C_P − C_V = α²BVT (α — the thermal expansion, B — the bulk modulus) is a few
    per cent at room temperature and is not in a harmonic calculation.
§2 ALGORITHM
    normalized(nu, g, atoms): the negative (imaginary) frequencies and those under FLOOR are dropped — their share of
    the states is returned for a warning — and g is scaled to ∫ g dν = 3·atoms (the trapezoid rule; matdyn.x prints
    g on an even grid). functions(nu, g, T): the integrals of §1 by the trapezoid rule, eV and eV/K per cell.
    debye_heat(T, theta, atoms): the Debye integral by the trapezoid rule on DEBYE_POINTS points (the integrand is
    x² at small x). debye_temperature(T, cv, atoms): Θ of one point by bisection (C_V falls monotonically with Θ);
    None when cv is not under the limit 3Nk. fit_debye(temperatures, heats, atoms): Θ_D minimizing Σ (C_V^D − C_V)²
    by a golden-section search between 10 and 3000 K.
§4 SPECIFICATION
    KB eV/K, HC eV·cm, NA; TEMPERATURES — 10 … 300 K by 10 and 350 … 1000 by 50; FLOOR = 1 cm⁻¹.
    Row(temperature, heat J/(mol K), entropy J/(mol K), energy kJ/mol (U − E₀), free kJ/mol (F − E₀), theta K | None);
    «mol» — of formula units: table(nu, g, atoms, units, temperatures) with units = formula units in the cell.
    Summary(zero_point kJ/mol, theta_fit K, theta_high K, limit J/(mol K), dropped — the share of the states left
    out). summary(nu, g, atoms, units, rows). lines(summary, row at 298 K) -> the conclusion (Russian, keys of tr).
    ValueError with a message for the user.
§7 TESTS
    tests/compass/test_phonon_thermo.py — an Einstein crystal and a Debye spectrum in closed form; the real phonon
    density of states of NaCl (matdyn.x 7.6).
"""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

import numpy as np

from azimuth.i18n import tr

KB = 8.617333262e-5  # eV/K
HC = 1.239841984e-4  # eV·cm: hν of 1 cm⁻¹
NA = 6.02214076e23
EV = 1.602176634e-19  # J
FLOOR = 1.0  # cm⁻¹
DEBYE_POINTS = 2001
TEMPERATURES = tuple(range(10, 301, 10)) + tuple(range(350, 1001, 50))


def _integral(y, x):
    return float(np.sum((y[1:] + y[:-1]) * np.diff(x)) / 2.0)


def normalized(nu, g, atoms):
    """(ν, g scaled to 3·atoms states, the share of the states dropped as imaginary or under FLOOR)."""
    nu, g = np.array(nu, dtype=float), np.array(g, dtype=float)
    if len(nu) < 3 or len(nu) != len(g) or atoms < 1:
        raise ValueError(tr('Термодинамика: в фононной плотности состояний слишком мало точек.'))
    whole = _integral(np.abs(g), nu)
    keep = nu >= FLOOR
    if keep.sum() < 3 or whole <= 0:
        raise ValueError(tr('Термодинамика: в фононной плотности состояний нет положительных частот.'))
    part = _integral(np.clip(g[keep], 0.0, None), nu[keep])
    if part <= 0:
        raise ValueError(tr('Термодинамика: в фононной плотности состояний нет положительных частот.'))
    return nu[keep], np.clip(g[keep], 0.0, None) * (3.0 * atoms / part), max(0.0, 1.0 - part / whole)


def functions(nu, g, temperature):
    """(C_V eV/K, S eV/K, U − E₀ eV, F − E₀ eV, E₀ eV) per cell at T (§1); nu, g — of normalized()."""
    if not temperature > 0:
        raise ValueError(tr('Термодинамика: температура должна быть больше нуля.'))
    energy = HC * nu
    x = energy / (KB * temperature)
    small = np.exp(-np.minimum(x, 700.0))  # e⁻ˣ
    bose = small / (1.0 - small)  # 1 / (eˣ − 1)
    log = np.log1p(-small)
    heat = KB * _integral(g * x * x * small / (1.0 - small) ** 2, nu)
    entropy = KB * _integral(g * (x * bose - log), nu)
    thermal = _integral(g * energy * bose, nu)
    free = KB * temperature * _integral(g * log, nu)
    return heat, entropy, thermal, free, _integral(g * energy / 2.0, nu)


def debye_heat(temperature, theta, atoms=1):
    """C_V of the Debye model, eV/K per cell of `atoms` atoms."""
    top = theta / temperature
    x = np.linspace(0.0, top, DEBYE_POINTS)
    y = np.zeros_like(x)
    inner = x[1:]
    small = np.exp(-np.minimum(inner, 700.0))
    y[1:] = inner ** 4 * small / (1.0 - small) ** 2
    return 9.0 * atoms * KB * _integral(y, x) / top ** 3


def debye_temperature(temperature, heat, atoms=1):
    """Θ(T): the Debye temperature that gives this C_V (eV/K per cell) at T; None outside 0 < C_V < 3Nk."""
    limit = 3.0 * atoms * KB
    if not 0.0 < heat < limit * (1.0 - 1e-6):
        return None
    low, high = 1e-3 * temperature, 200.0 * temperature
    if debye_heat(temperature, high, atoms) > heat:
        return None
    for _ in range(80):
        middle = 0.5 * (low + high)
        if debye_heat(temperature, middle, atoms) > heat:
            low = middle
        else:
            high = middle
    return 0.5 * (low + high)


def fit_debye(temperatures, heats, atoms=1):
    """Θ_D of the least squares of C_V over the temperatures given (heats — eV/K per cell)."""
    def miss(theta):
        return sum((debye_heat(t, theta, atoms) - c) ** 2 for t, c in zip(temperatures, heats))

    ratio = (sqrt(5.0) - 1.0) / 2.0
    low, high = 10.0, 3000.0
    a, b = high - ratio * (high - low), low + ratio * (high - low)
    fa, fb = miss(a), miss(b)
    for _ in range(60):
        if fa < fb:
            high, b, fb = b, a, fa
            a = high - ratio * (high - low)
            fa = miss(a)
        else:
            low, a, fa = a, b, fb
            b = low + ratio * (high - low)
            fb = miss(b)
    return 0.5 * (low + high)


@dataclass(frozen=True)
class Row:
    temperature: float
    heat: float
    entropy: float
    energy: float
    free: float
    theta: float | None


@dataclass(frozen=True)
class Summary:
    zero_point: float
    theta_fit: float
    theta_high: float
    limit: float
    dropped: float


def table(nu, g, atoms, units=1, temperatures=TEMPERATURES):
    """[Row] per mole of formula units (units of them in the cell of `atoms` atoms)."""
    if units < 1:
        raise ValueError(tr('Термодинамика: число формульных единиц в ячейке — от 1.'))
    nu, g, _ = normalized(nu, g, atoms)
    joule, kilo = EV * NA / units, EV * NA / units / 1000.0
    rows = []
    for t in temperatures:
        heat, entropy, thermal, free, _ = functions(nu, g, float(t))
        rows.append(Row(float(t), heat * joule, entropy * joule, thermal * kilo, free * kilo,
                        debye_temperature(float(t), heat, atoms)))
    return rows


def summary(nu, g, atoms, units=1, rows=None):
    clean_nu, clean_g, dropped = normalized(nu, g, atoms)
    rows = rows if rows is not None else table(nu, g, atoms, units)
    joule = EV * NA / units
    second = _integral(clean_g * clean_nu ** 2, clean_nu) / (3.0 * atoms)
    fit = fit_debye([r.temperature for r in rows], [r.heat / joule for r in rows], atoms)
    zero = functions(clean_nu, clean_g, 300.0)[4]
    return Summary(zero * joule / 1000.0, fit, HC / KB * sqrt(5.0 * second / 3.0), 3.0 * atoms * KB * joule, dropped)


def lines(found, room=None):
    text = [tr('Гармоническая термодинамика по фононной плотности состояний, на моль формульных единиц. Энергия нулевых '
               'колебаний {} кДж/моль.').format(f'{found.zero_point:.2f}')]
    if room is not None:
        text.append(tr('При {} K: C_V = {} Дж/(моль·К) ({} % предела Дюлонга — Пти {}), S = {} Дж/(моль·К).').format(
            f'{room.temperature:g}', f'{room.heat:.2f}', f'{100 * room.heat / found.limit:.0f}', f'{found.limit:.2f}',
            f'{room.entropy:.2f}'))
    text.append(tr('Температура Дебая: {} K по подгонке C_V(T), {} K по второму моменту спектра (высокие температуры).')
                .format(f'{found.theta_fit:.0f}', f'{found.theta_high:.0f}'))
    text.append(tr('Опыт даёт C_P: она больше C_V на α²BVT — несколько процентов при комнатной температуре.'))
    if found.dropped > 0.005:
        text.append(tr('Мнимые частоты и частоты ниже {:g} см⁻¹ отброшены — {} % состояний: структура не в минимуме или '
                       'мала сетка q, числам доверять нельзя.').format(FLOOR, f'{100 * found.dropped:.1f}'))
    return text
