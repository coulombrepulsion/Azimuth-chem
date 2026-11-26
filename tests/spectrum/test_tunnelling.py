"""Tunnelling corrections of Wigner and Eckart (modules/spectrum/analysis/tunnelling.py).

Oracles. The transmission of the Eckart barrier — against the Schrödinger equation solved here numerically for the
same potential V(x) = A y/(1 + y) + B y/(1 + y)², y = e^{2πx/L} (Numerov from the product side, where the wave is
e^{ik₂x}, to the reactant side, where it is matched to a e^{ik₁x} + b e^{−ik₁x}; P = k₂/(k₁|a|²)), with a mass and a
width chosen here: nothing of the closed formula is used but the link between the width and the imaginary frequency,
hν‡ = √(16 V_f V_r C / B), C = π²/(2μL²) in atomic units — the curvature of that potential at its top, checked here
by a finite difference too. The limits: κ → 1 for ν → 0; Eckart → Wigner while hν ≪ kT ≪ V; κ the same in both
directions (detailed balance); Wigner by hand: 1000 cm⁻¹ at 300 K, hν/kT = 1.4388 × 1000/300 = 4.796 → 1 + 23.0/24.
"""

from math import exp, pi, sqrt

import numpy as np
import pytest

from modules.spectrum.analysis import tunnelling as tn

KCAL = 1 / 627.509474
MASS, WIDTH, VF, VR = 1836.15, 2.0, 0.020, 0.030  # a proton, bohr, hartree


def potential(x):
    y = np.exp(2 * pi * x / WIDTH)
    a, b = VF - VR, (sqrt(VF) + sqrt(VR)) ** 2
    return a * y / (1 + y) + b * y / (1 + y) ** 2


def frequency():
    """ν‡ in cm⁻¹ of the potential above: hν = √(16 V_f V_r C / B) hartree."""
    c = pi ** 2 / (2 * MASS * WIDTH ** 2)
    return sqrt(16 * VF * VR * c / (sqrt(VF) + sqrt(VR)) ** 2) / tn.CM


def numerov(energy, edge=14.0, points=28001):
    x = np.linspace(-edge, edge, points)
    h = x[1] - x[0]
    f = 2 * MASS * (potential(x) - energy)  # ψ'' = f ψ
    k1, k2 = sqrt(2 * MASS * energy), sqrt(2 * MASS * (energy - (VF - VR)))
    psi = np.zeros(points, dtype=complex)
    psi[-1], psi[-2] = np.exp(1j * k2 * x[-1]), np.exp(1j * k2 * x[-2])
    w = 1 - h * h * f / 12
    for n in range(points - 2, 0, -1):
        psi[n - 1] = ((12 - 10 * w[n]) * psi[n] - w[n + 1] * psi[n + 1]) / w[n - 1]
    # ψ = a e^{ik₁x} + b e^{−ik₁x} at the two leftmost points
    m = np.array([[np.exp(1j * k1 * x[0]), np.exp(-1j * k1 * x[0])], [np.exp(1j * k1 * x[1]), np.exp(-1j * k1 * x[1])]])
    a, _ = np.linalg.solve(m, psi[:2])
    return k2 / (k1 * abs(a) ** 2)


def test_the_barrier_is_the_one_meant():
    # its top is V_f, its far side V_f − V_r, and its curvature at the top gives the frequency
    x = np.linspace(-6, 6, 240001)
    v = potential(x)
    top = int(np.argmax(v))
    assert v[top] == pytest.approx(VF, rel=1e-9) and v[0] == pytest.approx(0.0, abs=1e-9) and v[-1] == pytest.approx(VF - VR, abs=1e-9)
    h = x[1] - x[0]
    curvature = (v[top + 1] - 2 * v[top] + v[top - 1]) / (h * h)
    assert sqrt(-curvature / MASS) / tn.CM == pytest.approx(frequency(), rel=1e-4)  # ω = √(−V″/μ)
    assert frequency() == pytest.approx(1771.0, abs=2.0)


def test_the_transmission_against_the_schrodinger_equation():
    nu = frequency()
    for energy in (0.008, 0.014, 0.018, 0.020, 0.022, 0.030):  # under the top, at it, above
        assert tn.transmission(energy, VF, VR, nu) == pytest.approx(numerov(energy), rel=2e-3), energy
    assert tn.transmission(0.014, VF, VR, nu) < 0.01 < tn.transmission(0.018, VF, VR, nu) < 0.5 < tn.transmission(0.022, VF, VR, nu)
    values = tn.transmission(np.array([0.0, 0.01, 0.02, 0.2]), VF, VR, nu)
    assert values[0] == 0.0 and values[-1] == pytest.approx(1.0, abs=1e-6) and np.all(np.diff(values) > 0)
    # from the product side the barrier is V_r and the same energy lies VR − VF higher: the same probability
    assert tn.transmission(0.018 + VR - VF, VR, VF, nu) == pytest.approx(tn.transmission(0.018, VF, VR, nu), rel=1e-9)
    assert tn.transmission(0.005, VR, VF, nu) == 0.0  # under the reactant side of the reverse reaction


def test_the_coefficient_of_wigner():
    assert tn.wigner(1000.0, 300.0) == pytest.approx(1 + (1.438777 * 1000 / 300) ** 2 / 24, rel=1e-5)
    assert tn.wigner(1000.0, 300.0) == pytest.approx(1.9584, abs=1e-4) and tn.wigner(1e-3, 300.0) == pytest.approx(1.0)
    assert tn.wigner(500.0, 600.0) < tn.wigner(500.0, 300.0) < tn.wigner(1500.0, 300.0)


def test_the_coefficient_of_eckart():
    barrier = 10 * KCAL
    assert tn.eckart(1.0, barrier, barrier, 300.0) == pytest.approx(1.0, abs=1e-3)  # no curvature: the classical rate, to the step of the energy grid
    # hν ≪ kT ≪ V: the first quantum correction is Wigner's
    assert tn.eckart(100.0, 30 * KCAL, 30 * KCAL, 300.0) == pytest.approx(tn.wigner(100.0, 300.0), abs=2e-3)
    assert tn.eckart(500.0, 30 * KCAL, 30 * KCAL, 1000.0) == pytest.approx(tn.wigner(500.0, 1000.0), abs=5e-3)
    # a narrow barrier at room temperature: more than Wigner says, and the more the colder
    assert tn.eckart(1000.0, barrier, barrier, 300.0) == pytest.approx(3.018, abs=0.005)
    assert tn.eckart(1000.0, barrier, barrier, 300.0) > tn.wigner(1000.0, 300.0)
    assert tn.eckart(1000.0, barrier, barrier, 200.0) > tn.eckart(1000.0, barrier, barrier, 300.0) > tn.eckart(1000.0, barrier, barrier, 600.0) > 1
    # detailed balance: the same coefficient for the reaction and its reverse
    assert tn.eckart(1500.0, 10 * KCAL, 20 * KCAL, 300.0) == pytest.approx(tn.eckart(1500.0, 20 * KCAL, 10 * KCAL, 300.0), rel=1e-9)
    # the integral itself, by a sum written here on another grid
    kt = 300.0 * 3.166811563e-6
    grid = np.linspace(0.0, barrier + 80 * kt, 400001)
    by_hand = float(np.trapezoid(tn.transmission(grid, barrier, barrier, 1000.0) * np.exp(-(grid - barrier) / kt), grid) / kt)
    assert tn.eckart(1000.0, barrier, barrier, 300.0) == pytest.approx(by_hand, rel=1e-5)
    assert exp(-80.0) < 1e-30  # what is left above the grid


def test_what_is_refused():
    for bad in (dict(nu=0.0), dict(temperature=0.0), dict(forward=0.0), dict(reverse=-0.01)):
        with pytest.raises(ValueError):
            tn.eckart(**{'nu': 1000.0, 'forward': 0.02, 'reverse': 0.02, 'temperature': 300.0, **bad})
    with pytest.raises(ValueError):
        tn.wigner(-5.0, 300.0)
    with pytest.raises(ValueError):
        tn.transmission(0.01, 0.0, 0.02, 1000.0)
