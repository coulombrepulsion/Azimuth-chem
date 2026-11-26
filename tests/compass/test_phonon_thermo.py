"""The thermodynamics of a crystal from its phonon density of states (modules/compass/chemistry/phonon_thermo.py).

Oracles. An Einstein crystal — all 3N oscillators at one frequency (a narrow peak here): the closed formulas of one
oscillator, written here: C = 3Nk x²eˣ/(eˣ − 1)², S = 3Nk [x/(eˣ − 1) − ln(1 − e⁻ˣ)], E₀ = 3N hν/2. A Debye spectrum
g = 9N ν²/ν_D³ fed in as numbers must give back its own Θ_D at every temperature and by the fit; its second moment is
⟨ν²⟩ = 3ν_D²/5, so Θ_∞ = Θ_D exactly. The limits of the Debye function: 1 − (Θ/T)²/20 at high T, (4π⁴/5)(T/Θ)³ at
low T (per 3Nk). The real phonon density of states of NaCl (matdyn.x 7.6, tests/data/qe/nacl_dispersion.phdos);
measured for NaCl: S°(298 K) = 72.1 J/(mol·K), C_P(298 K) = 50.5 J/(mol·K), Θ_D(0 K) = 321 K (handbook values).
"""

from math import exp, log, pi
from pathlib import Path

import numpy as np
import pytest

from modules.compass.chemistry import phonon_thermo as pt
from modules.spectrum.readers import qe

DATA = Path(__file__).resolve().parents[1] / 'data' / 'qe'
R = 8.314462618  # J/(mol K)


def einstein(frequency=200.0, atoms=2):
    nu = np.linspace(1.0, 400.0, 39901)
    g = np.exp(-0.5 * ((nu - frequency) / 0.2) ** 2)
    return nu, g, atoms


def debye_spectrum(theta=300.0, atoms=1):
    top = theta * pt.KB / pt.HC  # ν_D, cm⁻¹
    nu = np.linspace(0.0, top, 60001)
    return nu, 9 * atoms * nu ** 2 / top ** 3, top


def test_an_einstein_crystal():
    nu, g, atoms = einstein()
    clean_nu, clean_g, dropped = pt.normalized(nu, g, atoms)
    assert pt._integral(clean_g, clean_nu) == pytest.approx(6.0) and dropped == pytest.approx(0.0, abs=1e-9)
    for temperature in (50.0, 300.0, 1000.0):
        x = pt.HC * 200.0 / (pt.KB * temperature)
        heat, entropy, thermal, free, zero = pt.functions(clean_nu, clean_g, temperature)
        assert heat / (6 * pt.KB) == pytest.approx(x * x * exp(x) / (exp(x) - 1) ** 2, rel=1e-4)
        assert entropy / (6 * pt.KB) == pytest.approx(x / (exp(x) - 1) - log(1 - exp(-x)), rel=1e-4)
        assert thermal == pytest.approx(6 * pt.HC * 200.0 / (exp(x) - 1), rel=1e-4) and zero == pytest.approx(3 * pt.HC * 200.0, rel=1e-6)
        assert entropy == pytest.approx((thermal - free) / temperature, rel=1e-9)  # S = (U − F)/T
    rows = pt.table(nu, g, atoms, units=1, temperatures=(300.0, 3000.0))
    assert rows[1].heat == pytest.approx(6 * R, rel=2e-3) and rows[0].heat < rows[1].heat  # Dulong and Petit: 3NR
    assert pt.table(nu, g, atoms, units=2, temperatures=(300.0,))[0].heat == pytest.approx(rows[0].heat / 2)
    assert pt.KB * pt.EV * pt.NA == pytest.approx(R, rel=1e-9)


def test_the_debye_function_and_its_temperature():
    assert pt.debye_heat(3000.0, 300.0) / (3 * pt.KB) == pytest.approx(1 - (300.0 / 3000.0) ** 2 / 20, rel=1e-5)
    assert pt.debye_heat(10.0, 300.0) / (3 * pt.KB) == pytest.approx(4 * pi ** 4 / 5 * (10.0 / 300.0) ** 3, rel=1e-4)
    assert pt.debye_heat(300.0, 300.0, atoms=2) == pytest.approx(2 * pt.debye_heat(300.0, 300.0))
    assert pt.debye_heat(300.0, 300.0) / (3 * pt.KB) == pytest.approx(0.9517, abs=2e-4)  # the tabulated D(1)
    for theta in (150.0, 428.0):
        assert pt.debye_temperature(100.0, pt.debye_heat(100.0, theta), 1) == pytest.approx(theta, rel=1e-6)
    assert pt.debye_temperature(100.0, 3 * pt.KB) is None and pt.debye_temperature(100.0, 0.0) is None
    # a Debye spectrum given as numbers: one Θ at every temperature, by the fit and by the second moment
    nu, g, top = debye_spectrum(300.0)
    rows = pt.table(nu, g, 1, temperatures=(20.0, 100.0, 300.0, 800.0))
    assert [r.theta for r in rows] == pytest.approx([300.0] * 4, rel=3e-3)
    found = pt.summary(nu, g, 1, rows=rows)
    assert found.theta_fit == pytest.approx(300.0, rel=3e-3) and found.theta_high == pytest.approx(300.0, rel=2e-3)
    assert found.limit == pytest.approx(3 * R) and found.zero_point == pytest.approx(9 / 8 * R * 300.0 / 1000, rel=2e-3)  # E₀ = (9/8) R Θ


def test_the_real_spectrum_of_rock_salt():
    nu, g = qe.read_phdos((DATA / 'nacl_dispersion.phdos').read_text(encoding='utf-8'))
    rows = pt.table(nu, g, atoms=2, units=1)
    found = pt.summary(nu, g, 2, 1, rows)
    room = next(r for r in rows if r.temperature == 300.0)
    assert room.heat == pytest.approx(47.8, abs=0.1) and room.heat < found.limit == pytest.approx(6 * R)
    assert room.entropy == pytest.approx(72.1, abs=0.5)  # measured S°(298 K) = 72.1 J/(mol·K)
    assert 45.0 < room.heat < 50.5  # under the measured C_P by the anharmonic part
    assert rows[0].temperature == 10.0 and rows[0].theta == pytest.approx(321.0, abs=8.0)  # measured Θ_D(0 K) = 321 K
    assert min(r.theta for r in rows if r.temperature <= 100) < 280 < rows[0].theta  # the dip of an ionic crystal
    assert found.theta_fit == pytest.approx(274.0, abs=2.0) and found.theta_high == pytest.approx(278.0, abs=2.0)
    assert found.zero_point == pytest.approx(5.15, abs=0.02) and found.dropped < 1e-5
    assert all(a.heat < b.heat and a.entropy < b.entropy and a.free > b.free for a, b in zip(rows, rows[1:]))
    text = ' '.join(pt.lines(found, room))
    assert '47.8' in text and '274 K' in text and 'отброшены' not in text


def test_imaginary_frequencies_are_said():
    nu = np.linspace(-60.0, 300.0, 3601)
    g = np.exp(-0.5 * ((nu - 200.0) / 10.0) ** 2) + 0.4 * np.exp(-0.5 * ((nu + 30.0) / 6.0) ** 2)
    _, clean, dropped = pt.normalized(nu, g, 1)
    assert dropped == pytest.approx(0.4 * 6 / (10 + 0.4 * 6), abs=5e-3) and clean.min() >= 0
    found = pt.summary(nu, g, 1)
    assert 'отброшены' in ' '.join(pt.lines(found))
    for bad in (([1.0, 2.0], [1.0, 1.0], 1), (list(range(-10, 0)), [1.0] * 10, 1), ([1.0, 2.0, 3.0], [0.0, 0.0, 0.0], 1)):
        with pytest.raises(ValueError):
            pt.normalized(*bad)
    with pytest.raises(ValueError):
        pt.functions(np.array([10.0, 20.0, 30.0]), np.array([1.0, 1.0, 1.0]), 0.0)
    with pytest.raises(ValueError):
        pt.table(nu, g, 1, units=0)
