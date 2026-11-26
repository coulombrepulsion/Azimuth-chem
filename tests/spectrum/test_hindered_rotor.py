"""A hindered internal rotation (modules/spectrum/analysis/hindered_rotor.py).

Oracles, not taken from the module: the levels of a free plane rotor, E_m = m²ħ²/2I (0, 1, 1, 4, 4, 9 … in units
of B), and its classical partition function √(8π³IkT)/(σh); the harmonic limit of a high threefold barrier
V = (V₀/2)(1 − cos 3φ): ω = 3√(V₀/2I), E₀ → ħω/2 (lowered by the anharmonicity of the cosine, −9ħ²/(32 I) to first
order), three wells and σ = 3 → q_hr → q_ho; hot — the classical partition function of Pitzer and Gwinn,
q_free·e^(−u)·I₀(u), u = V₀/2kT; the reduced moment of H₂O₂ computed here from the coordinates of its
geometry (two O–H tops about the O–O axis, I = m_H r⊥² each, I_red = I₁I₂/(I₁ + I₂)); the energies of the real scan of
ORCA 6.0.1 (tests/data/scan2d/h2o2_scan1d_orca.out) copied by hand from its table: the cis barrier
E(0°) − E(120°) = 0.01321533 Eh and the trans one E(180°) − E(120°) = 0.00088605 Eh. Constants typed in: CODATA 2018.
"""

from math import exp, log, pi, sqrt
from pathlib import Path

import numpy as np
import pytest

from azimuth.core import read_xyz
from modules.spectrum.analysis import hindered_rotor as hr
from modules.spectrum.readers.orca_scan import read_scan

H, KB, HARTREE, C, AMU = 6.62607015e-34, 1.380649e-23, 4.3597447222071e-18, 299792458.0, 1.66053906660e-27
HBAR = H / (2 * pi)
DATA = Path(__file__).resolve().parents[1] / 'data' / 'scan2d'
FLAT = hr.Potential((0.0,), (0.0,), 0.0, 0.0, 0.0, 0.0, 0.0)


def threefold(v0):
    """V = (V₀/2)(1 − cos 3φ): minimum 0 at φ = 0, curvature 9V₀/2."""
    return hr.Potential((v0 / 2, 0.0, 0.0, -v0 / 2), (0.0, 0.0, 0.0, 0.0), 0.0, 0.0, v0, 4.5 * v0, 0.0)


def test_the_free_rotor():
    moment = 1.0e-47
    b = HBAR ** 2 / (2 * moment) / HARTREE
    assert hr.rotational_constant(moment) == pytest.approx(b, rel=1e-12)
    levels = hr.levels(FLAT, moment)
    assert levels[:7] / b == pytest.approx([0, 1, 1, 4, 4, 9, 9], abs=1e-9)
    for t in (300.0, 1000.0):
        classical = sqrt(8 * pi ** 3 * moment * KB * t) / H
        r = hr.row(FLAT, moment, 1, 100.0, t)
        assert r.q_hr == pytest.approx(classical, rel=1e-6) and r.q_free == pytest.approx(classical, rel=1e-12)
        assert hr.row(FLAT, moment, 3, 100.0, t).q_hr == pytest.approx(classical / 3, rel=1e-6)  # σ divides q
    assert hr.row(FLAT, moment, 1, 100.0, 300.0).zpe_hr == pytest.approx(0.0, abs=1e-15)


def test_a_high_barrier_is_a_harmonic_oscillator():
    v0, moment = 0.02, 5.0e-47  # 12.6 kcal/mol
    potential = threefold(v0)
    omega = 3 * sqrt(v0 * HARTREE / (2 * moment))
    nu = omega / (2 * pi * C * 100.0)
    assert hr.harmonic_wavenumber(potential, moment) == pytest.approx(nu, rel=1e-12)
    levels = hr.levels(potential, moment)
    half = 0.5 * HBAR * omega / HARTREE
    first_order = -9 * HBAR ** 2 / (32 * moment) / HARTREE  # ⟨−(81V₀/48)φ⁴⟩ of the ground state, ⟨φ⁴⟩ = 3(ħ/2Iω)²
    assert levels[0] == pytest.approx(half + first_order, rel=2e-3)
    assert levels[:3] == pytest.approx([levels[0]] * 3, abs=1e-9)  # three wells: a threefold lowest level
    r = hr.row(potential, moment, 3, None, 150.0)
    assert r.q_hr == pytest.approx(r.q_ho, rel=3e-3) and abs(r.correction) * 627.5 < 0.02
    assert r.q_ho == pytest.approx(1 / (1 - exp(-H * C * 100 * nu / (KB * 150.0))), rel=1e-12)
    assert r.zpe_ho == pytest.approx(half, rel=1e-12)


def test_the_levels_do_not_depend_on_the_size_of_the_basis():
    potential, moment = threefold(0.004), 5.0e-47
    assert np.abs(hr.levels(potential, moment, 200)[:80] - hr.levels(potential, moment)[:80]).max() < 1e-12


def test_between_the_limits_and_with_the_temperature():
    v0, moment = 0.003, 5.0e-47  # 1.9 kcal/mol: kT at 600 K is 1.2 kcal/mol
    potential = threefold(v0)
    rows = hr.table(potential, moment, 3)
    assert [r.temperature for r in rows] == [200.0, 250.0, 300.0, 350.0, 400.0, 450.0, 500.0, 550.0, 600.0]
    for r in rows:
        kt = KB * r.temperature / HARTREE
        assert r.correction == pytest.approx(r.g_hr - r.g_ho)
        assert r.factor == pytest.approx(exp(-r.correction / kt), rel=1e-12)
        assert r.g_hr == pytest.approx(r.zpe_hr - kt * log(r.q_hr), rel=1e-12)
        assert r.zpe_hr < r.zpe_ho  # a cosine well is softer than its parabola
    # hot: the classical partition function of Pitzer and Gwinn from the bottom of the well,
    # q = q_free · e^(−u) · I₀(u), u = V₀/2kT — the quantum sum must come to it
    for t in (2000.0, 5000.0):
        r = hr.row(potential, moment, 3, None, t)
        kt = KB * t / HARTREE
        u = v0 / (2 * kt)
        classical = r.q_free * exp(-u) * float(np.i0(u))
        assert r.q_hr * exp(-r.zpe_hr / kt) == pytest.approx(classical, rel=5e-3)
        assert r.q_hr < r.q_ho  # far above the barrier the oscillator promises states the rotor does not have
    assert hr.row(potential, moment, 3, None, 5000.0).q_hr / hr.row(potential, moment, 3, None, 5000.0).q_free > 0.9


def test_the_scan_of_hydrogen_peroxide():
    scan = read_scan((DATA / 'h2o2_scan1d_orca.out').read_text(encoding='utf-8', errors='replace'))
    points = hr.points_of(scan)
    assert len(points) == 7 and hr.cover_of(points) == 'mirror'
    potential = hr.fit(points, 'mirror')
    assert all(potential.value(a) == pytest.approx(e, abs=1e-5) for a, e in points)
    assert potential.value(240.0) == pytest.approx(potential.value(120.0), abs=1e-9)  # V(−φ) = V(φ)
    assert 105.0 < potential.minimum_angle < 135.0 or 225.0 < potential.minimum_angle < 255.0
    assert potential.barrier == pytest.approx(0.01321533, rel=0.01)  # the cis barrier, the highest
    assert potential.value(180.0) - potential.minimum == pytest.approx(0.00088605, rel=0.1)  # the trans one
    geometry = scan.points[scan.reference].geometry
    j, k = scan.coordinates[0].atoms[1:3]
    moment = hr.reduced_moment(geometry, j, k)
    # by hand: each hydrogen about the O–O axis
    xyz = np.array([a.position for a in geometry.atoms])
    axis = (xyz[1] - xyz[0]) / np.linalg.norm(xyz[1] - xyz[0])
    tops = []
    for hydrogen in (2, 3):
        r = xyz[hydrogen] - xyz[0]
        tops.append(1.00782503223 * AMU * float(np.linalg.norm(np.cross(r, axis))) ** 2 * 1e-20)
    assert moment == pytest.approx(tops[0] * tops[1] / (tops[0] + tops[1]), rel=1e-6)
    assert moment / AMU * 1e20 == pytest.approx(0.459, abs=0.005)
    rows = hr.table(potential, moment, 1, None, (200.0, 298.15, 600.0))
    assert all(r.q_ho < r.q_hr < r.q_free * 1.05 for r in rows)  # two wells and a low trans barrier
    assert all(r.factor > 1 for r in rows)


def test_what_a_scan_covers():
    round_ = [(a, 0.0) for a in np.linspace(0.0, 360.0, 13)]
    assert hr.cover_of(round_) == 'full' and hr.cover_of(round_[:-1]) == 'full'
    assert hr.cover_of([(a, 0.0) for a in range(0, 181, 30)]) == 'mirror'
    assert hr.cover_of([(a, 0.0) for a in range(0, 180, 30)]) == 'period2'
    assert hr.cover_of([(a, 0.0) for a in range(0, 121, 20)]) == 'period3'
    assert hr.cover_of([(a, 0.0) for a in range(0, 91, 15)]) is None
    third = [(a, 0.001 * (1 - np.cos(np.radians(3 * a)))) for a in range(0, 121, 15)]
    potential = hr.fit(third, 'period3')
    assert potential.barrier == pytest.approx(0.002, rel=1e-6)
    assert potential.value(200.0) == pytest.approx(0.001 * (1 - np.cos(np.radians(600.0))), abs=1e-9)
    assert len(hr.unfold(round_, 'full')) == 12  # 0° and 360° are one point


def test_what_is_refused():
    with pytest.raises(ValueError, match='двугранного'):
        hr.points_of(None)
    with pytest.raises(ValueError, match='оборот'):
        hr.fit([(a, 0.0) for a in range(0, 91, 15)], 'full')  # a quarter of the turn
    with pytest.raises(ValueError):
        hr.unfold([(0.0, 0.0)] * 6, 'half')
    benzene_ring = read_xyz('6\nring\nC 1.39 0 0\nC 0.695 1.204 0\nC -0.695 1.204 0\nC -1.39 0 0\nC -0.695 -1.204 0\n'
                            'C 0.695 -1.204 0')
    with pytest.raises(ValueError, match='цикл'):
        hr.reduced_moment(benzene_ring, 0, 1)
    acetylene = read_xyz('4\nHCCH\nH 0 0 -1.66\nC 0 0 -0.6\nC 0 0 0.6\nH 0 0 1.66')
    with pytest.raises(ValueError, match='на оси'):
        hr.reduced_moment(acetylene, 1, 2)
    potential = threefold(0.003)
    for bad in (dict(temperature=0.0), dict(sigma=0), dict(wavenumber=-5.0)):
        with pytest.raises(ValueError):
            hr.row(potential, 5.0e-47, **{'sigma': 1, **bad})
