"""The equilibrium of two forms (modules/spectrum/analysis/equilibrium.py).

Oracles, typed in here and not taken from the module: k = 3.166811563e-6 hartree/K and hc/k = 1.438776877 cm·K
(CODATA 2018); K of a pure energy difference, exp(−ΔE/kT); the harmonic partition function from the zero-point level,
q = 1/(1 − e^(−hcν̃/kT)), and ZPE = hcν̃/2 for a single changed mode; q_rot ∝ 1/σ — a symmetry number of 2 halves the
rotational states exactly; the mirror forms multiply K by integers; G_B − G_A of the thermochemistry (another path
through the same numbers: reaction.corrections); the point groups of water (C2v), twisted H2O2 (C2) and CHFClBr (C1).
"""

from dataclasses import replace
from math import exp, log

import pytest

from azimuth.core import read_xyz
from modules.spectrum.analysis import equilibrium, reaction

K_HARTREE = 3.166811563e-6
C2 = 1.438776877  # hc/k, cm·K
WATER = read_xyz('3\nwater\nO 0 0 0.117\nH 0.757 0 -0.469\nH -0.757 0 -0.469')


def form(label, energy=-76.4, frequencies=(1600.0, 3650.0, 3750.0), sigma=2, geometry=WATER):
    return reaction.Species(label, energy, geometry, tuple(frequencies), 1, 0, sigma, 'B3LYP def2-SVP', 'ORCA', '',
                            reaction.counts_of(geometry))


def test_two_equal_forms_are_half_and_half():
    p = equilibrium.point(form('A'), form('B'))
    assert p.constant == pytest.approx(1.0, rel=1e-12) and p.share_a == pytest.approx(0.5) and p.share_b == pytest.approx(0.5)
    assert p.delta_e0 == pytest.approx(0.0, abs=1e-15) and p.delta_g == pytest.approx(0.0, abs=1e-12)
    assert all(v == pytest.approx(1.0, rel=1e-12) for v in p.factors.values())


def test_an_energy_difference_alone():
    for t in (200.0, 298.15, 600.0):
        p = equilibrium.point(form('A'), form('B', energy=-76.4 + 0.002), t)
        assert p.constant == pytest.approx(exp(-0.002 / (K_HARTREE * t)), rel=1e-6)
        assert p.factors['energy'] == pytest.approx(p.constant, rel=1e-9)
        assert p.share_b == pytest.approx(p.constant / (1 + p.constant), rel=1e-9)
    cold, hot = (equilibrium.point(form('A'), form('B', energy=-76.398), t).share_b for t in (200.0, 600.0))
    assert cold < hot < 0.5  # the higher form gains with the temperature and never passes one half


def test_the_symmetry_number_and_the_mirror_forms_are_integers_in_k():
    a, b = form('A'), form('B')
    half = equilibrium.point(a, b, sigma=(1, 2))  # B has half the rotational states
    assert half.constant == pytest.approx(0.5, rel=1e-9) and half.factors['rotational'] == pytest.approx(0.5, rel=1e-9)
    assert equilibrium.point(a, b, sigma=(2, 1)).share_b == pytest.approx(2 / 3, rel=1e-9)
    assert equilibrium.point(replace(a, sigma=2), replace(b, sigma=1)).constant == pytest.approx(2.0, rel=1e-9)  # their own σ
    twin = equilibrium.point(a, b, mirror=(1, 2))  # B — two enantiomers
    assert twin.constant == pytest.approx(2.0, rel=1e-12) and twin.factors['mirror'] == 2.0
    assert twin.delta_g == pytest.approx(-K_HARTREE * 298.15 * log(2.0), rel=1e-6)
    assert equilibrium.point(a, b, mirror=(2, 2)).constant == pytest.approx(1.0, rel=1e-12)


def test_one_softer_mode_by_the_harmonic_partition_function():
    t = 298.15
    a, b = form('A', frequencies=(1600.0, 3650.0, 3750.0)), form('B', frequencies=(400.0, 3650.0, 3750.0))
    p = equilibrium.point(a, b, t)
    q = lambda nu: 1.0 / (1.0 - exp(-C2 * nu / t))  # noqa: E731
    zero_point = 0.5 * (400.0 - 1600.0) * C2 * K_HARTREE  # ΔZPE in hartree: hcΔν̃/2 = (C2 Δν̃ / 2) k
    assert p.delta_e0 == pytest.approx(zero_point, rel=1e-6)
    assert p.factors['vibrational'] == pytest.approx(q(400.0) / q(1600.0), rel=1e-6)
    assert p.constant == pytest.approx(exp(-zero_point / (K_HARTREE * t)) * q(400.0) / q(1600.0), rel=1e-6)
    assert p.factors['translational'] == pytest.approx(1.0, rel=1e-12)  # isomers: the same mass


def test_the_factors_multiply_to_k_and_agree_with_the_gibbs_energies():
    a = form('A', frequencies=(1550.0, 3600.0, 3700.0), sigma=2)
    b = form('B', energy=-76.3985, frequencies=(300.0, 3500.0, 3800.0), sigma=1)
    for t in (200.0, 298.15, 450.0):
        p = equilibrium.point(a, b, t)
        product = 1.0
        for key in equilibrium.FACTORS:
            product *= p.factors[key]
        assert product == pytest.approx(p.constant, rel=1e-9)
        ga = a.energy + reaction.corrections(a, t)[2]
        gb = b.energy + reaction.corrections(b, t)[2]
        assert p.delta_g == pytest.approx(gb - ga, abs=1e-10)
        assert p.constant == pytest.approx(exp(-(gb - ga) / (K_HARTREE * t)), rel=1e-5)
    rows = equilibrium.table(a, b)
    assert [r.temperature for r in rows] == [200.0, 250.0, 300.0, 350.0, 400.0, 450.0, 500.0, 550.0, 600.0]
    assert all(r.share_a + r.share_b == pytest.approx(1.0) for r in rows)


def test_what_is_refused():
    a = form('A')
    with pytest.raises(ValueError, match='частот'):
        equilibrium.point(a, form('B', frequencies=()))
    hf = read_xyz('2\nHF\nH 0 0 0\nF 0 0 0.92')
    with pytest.raises(ValueError, match='состава'):
        equilibrium.point(a, form('B', frequencies=(4100.0,), geometry=hf))
    for bad in (dict(sigma=(0, 1)), dict(mirror=(1, 3)), dict(temperature=0.0)):
        with pytest.raises(ValueError):
            equilibrium.point(a, form('B'), **bad)


def test_mirror_forms_follow_the_point_group():
    peroxide = read_xyz('4\nH2O2\nO 0.0000 0.7375 -0.0528\nO 0.0000 -0.7375 -0.0528\n'
                        'H 0.8190 0.8170 0.4220\nH -0.8190 -0.8170 0.4220')
    chiral = read_xyz('5\nCHFClBr\nC 0.000 0.000 0.000\nH 0.629 0.629 0.629\nF -0.780 -0.780 0.780\n'
                      'Cl -1.020 1.020 -1.020\nBr 1.120 -1.120 -1.120')
    assert equilibrium.mirror_forms(WATER) == 1  # C2v: mirror planes
    assert equilibrium.mirror_forms(peroxide) == 2  # C2: an axis only
    assert equilibrium.mirror_forms(chiral) == 2  # C1


def test_the_doubts_of_the_two_results_are_named():
    a = form('A')
    b = replace(form('B'), level='PBE0 def2-TZVP')
    assert any('уров' in w.lower() for w in equilibrium.warnings(a, b))
    assert equilibrium.warnings(a, form('B')) == []
