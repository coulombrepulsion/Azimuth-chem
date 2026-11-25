"""Fluorescence and phosphorescence from an optimization of an excited state
(modules/spectrum/analysis/emission.py)."""

from pathlib import Path

import pytest

from modules.spectrum.analysis import emission

DATA = Path(__file__).resolve().parents[1] / 'data'


def test_orca_formaldehyde_s1():
    # ORCA 6.1.1, B3LYP(LibXC)/def2-SVP, %tddft iroot 1: n→π* of formaldehyde — dark, 4.02 eV at the start, 3.40 eV
    # at the relaxed S1 (pyramidal) geometry
    text = (DATA / 'orca611' / 'ch2o_excited_opt_libxc_b3lyp.out').read_text(encoding='utf-8')
    found = emission.read(text, 'ORCA 6.1.1')
    assert found.kind == 'fluorescence' and found.start.root == found.end.root == 1
    assert found.start.energy_ev == pytest.approx(4.0205, abs=1e-3) and found.end.energy_ev == pytest.approx(3.4017, abs=1e-3)
    assert found.stokes_cm == pytest.approx(4991, abs=5) and len(found.absorption) == 3
    assert found.end.fosc == 0 and found.rate is None and 'запрещён' in emission.summary(found)
    assert emission.read((DATA / 'orca601' / 'h2o_tddft.out').read_text(encoding='utf-8'), 'ORCA') is None  # one point


def gaussian(cycles, kind='Singlet'):
    text = ' Entering Gaussian System\n #p td(root=1) opt b3lyp/6-31g(d)\n'
    for energy, f in cycles:
        text += (f' Excited State   1:      {kind}-A      {energy:.4f} eV  {1239.84 / energy:.2f} nm  f={f:.4f}  <S**2>=0.000\n'
                 '      10 -> 11         0.70\n This state for optimization and/or second-order correction.\n'
                 ' Total Energy, E(TD-HF/TD-KS) =  -100.000000000\n'
                 f' Excited State   2:      {kind}-A      {energy + 1:.4f} eV  {1239.84 / (energy + 1):.2f} nm  f=0.2000  <S**2>=0.000\n')
    return text


def test_gaussian_and_the_radiative_rate():
    found = emission.read(gaussian([(4.0, 0.12), (3.6, 0.10), (3.1, 0.10)]), 'Gaussian 16')
    assert found.kind == 'fluorescence' and found.end.energy_ev == 3.1 and found.start.energy_ev == 4.0
    assert len(found.absorption) == 2 and found.absorption[0].energy_ev == 4.0  # the first geometry
    nu = 3.1 * emission.EV_CM
    assert found.rate == pytest.approx(0.6670 * nu ** 2 * 0.10) and found.lifetime_ns == pytest.approx(1e9 / found.rate)
    assert 1 < found.lifetime_ns < 100  # a bright singlet: nanoseconds
    triplet = emission.read(gaussian([(3.0, 0.0), (2.5, 0.0)], 'Triplet'), 'Gaussian 16')
    assert triplet.kind == 'phosphorescence' and triplet.rate is None and 'спин-орбит' in emission.summary(triplet)
