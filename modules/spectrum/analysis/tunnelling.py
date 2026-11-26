"""Tunnelling corrections to the rate constant of transition state theory: Wigner and Eckart.

§1 THEORY
    Transition state theory treats the motion over the barrier classically. A light particle (a hydrogen atom, a
    proton) also passes under the top of the barrier, and is partly reflected above it; the rate constant is
    multiplied by the transmission coefficient
        κ(T) = (e^{V_f/kT} / kT) ∫ P(E) e^{−E/kT} dE,
    where P(E) is the quantum probability to pass a one-dimensional barrier at the energy E (counted from the
    reactant side) and V_f the height of the barrier from that side; κ = 1 for the classical P (0 under the top, 1
    above it).
    Wigner (1932): the barrier is a parabola of the curvature of the imaginary frequency ν‡, and only the first term
    in ħ is kept: κ = 1 + (1/24)(hν‡/kT)². Good while hν‡ < kT or so; it knows nothing of the height of the barrier.
    Eckart (1930): the barrier V(x) = A y/(1 + y) + B y/(1 + y)², y = e^{2πx/L}, goes from 0 (the reactants) through
    the top V_f to A = V_f − V_r (the products), B = (√V_f + √V_r)². Its transmission is known exactly:
        P(E) = 1 − [cosh 2π(α − β) + cosh 2πδ] / [cosh 2π(α + β) + cosh 2πδ],
        α = ½ √(E/C), β = ½ √((E − A)/C), δ = ½ √((B − C)/C)   (cos 2π|δ| in place of cosh when B < C),
    with C = h²/(8 μ L²). The width L and the mass μ enter only through C, and C follows from the curvature at the
    top: C = (hν‡)² B / (16 V_f V_r). So the three numbers of a calculation — ν‡ and the two barrier heights with the
    zero-point energies — fix the barrier. The heights are those of the vibrationally adiabatic profile: ΔE₀ = ΔE +
    ΔZPE from each side.
§2 ALGORITHM
    wigner(nu, T). transmission(E, forward, reverse, nu): P of §1 for E ≥ max(0, A), 0 below; the hyperbolic cosines
    are handled by their exponents (the arguments reach hundreds). eckart(nu, forward, reverse, T): the integral of
    §1 by the trapezoid rule over POINTS energies from max(0, A) to V_f + SPAN·kT, in the variable E; the integrand
    is smooth and the grid is denser than its scale kT by two orders.
§4 SPECIFICATION
    nu — the modulus of the imaginary wavenumber, cm⁻¹; forward, reverse — the barrier heights V_f, V_r > 0, hartree;
    T in K. wigner -> κ ≥ 1; eckart -> κ > 0; transmission -> 0 … 1. ValueError (a message for the user) for ν ≤ 0,
    T ≤ 0 or a barrier that is not positive. Constants of modules/spectrum/analysis/thermo.py.
§6 NOTES
    Both are one-dimensional: the reaction path is assumed straight (no corner cutting), so for a transfer of
    hydrogen at low temperature the true κ is larger than Eckart's. A correction larger than about 10 says that the
    number itself is not to be trusted, only its order.
§7 TESTS
    tests/spectrum/test_tunnelling.py — the transmission against a numerical solution of the Schrödinger equation
    for the same barrier, the limits of κ.
"""

from __future__ import annotations

import math

import numpy as np

from azimuth.i18n import tr
from modules.spectrum.analysis import thermo

POINTS = 20001
SPAN = 60.0  # kT above the top of the barrier
CM = 100.0 * thermo.H * 299792458.0 / thermo.HARTREE  # hartree in one cm⁻¹


def _check(nu, temperature):
    if not nu > 0:
        raise ValueError(tr('Туннельная поправка: нужна мнимая частота переходного состояния.'))
    if not temperature > 0:
        raise ValueError(tr('Туннельная поправка: температура должна быть больше нуля.'))


def wigner(nu, temperature=298.15):
    _check(nu, temperature)
    u = nu * CM * thermo.HARTREE / (thermo.KB * temperature)
    return 1.0 + u * u / 24.0


def _log_cosh(x):
    x = np.abs(x)
    return x + np.log1p(np.exp(-2.0 * x)) - math.log(2.0)


def transmission(energy, forward, reverse, nu):
    """P(E) of the Eckart barrier (§1); energy — a number or an array, hartree from the reactant side."""
    if not (forward > 0 and reverse > 0 and nu > 0):
        raise ValueError(tr('Туннельная поправка Эккарта: барьеры в обе стороны должны быть больше нуля.'))
    e = np.atleast_1d(np.array(energy, dtype=float))
    a = forward - reverse
    b = (math.sqrt(forward) + math.sqrt(reverse)) ** 2
    c = (nu * CM) ** 2 * b / (16.0 * forward * reverse)
    allowed = e >= max(0.0, a)
    safe = np.where(allowed, e, max(0.0, a))
    alpha = 0.5 * np.sqrt(safe / c)
    beta = 0.5 * np.sqrt(np.maximum(safe - a, 0.0) / c)
    minus, plus = _log_cosh(2 * math.pi * (alpha - beta)), _log_cosh(2 * math.pi * (alpha + beta))
    if b >= c:
        delta = _log_cosh(2 * math.pi * 0.5 * math.sqrt((b - c) / c))
        top = np.logaddexp(minus, delta)
        bottom = np.logaddexp(plus, delta)
        found = 1.0 - np.exp(top - bottom)
    else:
        cosine = math.cos(2 * math.pi * 0.5 * math.sqrt((c - b) / c))
        found = 1.0 - (np.exp(minus) + cosine) / (np.exp(plus) + cosine)
    found = np.where(allowed, np.clip(found, 0.0, 1.0), 0.0)
    return float(found[0]) if np.ndim(energy) == 0 else found


def eckart(nu, forward, reverse, temperature=298.15):
    _check(nu, temperature)
    if not (forward > 0 and reverse > 0):
        raise ValueError(tr('Туннельная поправка Эккарта: барьеры в обе стороны должны быть больше нуля.'))
    kt = thermo.KB * temperature / thermo.HARTREE
    low = max(0.0, forward - reverse)
    energies = np.linspace(low, forward + SPAN * kt, POINTS)
    weights = transmission(energies, forward, reverse, nu) * np.exp(-(energies - forward) / kt)
    step = energies[1] - energies[0]
    return float((weights.sum() - 0.5 * (weights[0] + weights[-1])) * step / kt)
