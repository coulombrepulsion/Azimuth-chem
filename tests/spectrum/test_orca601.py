"""Spectrum reads the outputs of ORCA 6.0.1 that the input files of Sextant gave on the user's Mac
(tests/data/orca601, README there); the oracles are the numbers ORCA printed in the same files."""

from math import dist
from pathlib import Path

import pytest

from modules.spectrum.analysis import thermo
from modules.spectrum.readers.outputs import read_any

DATA = Path(__file__).parents[1] / 'data' / 'orca601'


def read(name):
    return read_any((DATA / f'{name}.out').read_text(encoding='utf-8'))


@pytest.mark.parametrize('name, energy', [
    ('h2o_energy', -76.321017742317), ('h2o_opt', -76.321269931369), ('h2o_optfreq', -76.321269931369),
    ('h2o_cpcm_water', -76.330199319868), ('h2o_d3bj', -76.321591608146), ('h2o_d4', -76.321326776489),
    ('h2o_rijcosx', -76.321017742317), ('h2o_zora', -76.405978037102), ('h2o_nmr', -76.321017742317),
    ('h2o_verytight_hirshfeld', -76.321017742292),
    ('h2o_tddft', -76.321017742), ('h2o_tda_triplets', -76.321017742),  # the ground state (E(SCF)), not E(tot)
    ('ch2o_excited_opt', -114.218015455087),  # on the surface of the excited state: E(tot)
])
def test_every_output_ends_normally_and_gives_its_energy(name, energy):
    out = read(name)
    assert out.normal_exit and out.error_module is None
    assert out.energies[-1] == pytest.approx(energy, abs=1e-9)


def test_tddft_keeps_the_excited_state_apart():
    out = read('h2o_tddft')
    assert out.excited_energy == (1, pytest.approx(-76.040793827, abs=1e-9))
    first = out.absorption[0]  # «0-1A -> 1-1A 7.625280 61502.0 162.6 0.018043051»
    assert (first.energy_ev, first.wavelength, first.fosc) == (pytest.approx(7.62528), 162.6, pytest.approx(0.018043051))
    assert len(out.absorption) == 3 and len(read('h2o_tda_triplets').absorption) == 6
    excited = read('ch2o_excited_opt')
    assert excited.optimization_converged and len(excited.steps) == 7 and excited.excited_energy is None


def test_optimizations_and_the_frozen_bond():
    for name in ('h2o_opt', 'h2o_optfreq', 'h2o_opt_frozen_oh'):
        out = read(name)
        assert out.optimization_converged and len(out.steps) == 4, name
    g = read('h2o_opt_frozen_oh').geometry
    start = dist((0.0, 0.0, 0.117), (0.0, 0.757, -0.467))  # O–H of the input, frozen by «{ B 0 1 C }»
    assert dist(g.atoms[0].position, g.atoms[1].position) == pytest.approx(start, abs=2e-4)
    assert dist(g.atoms[0].position, g.atoms[2].position) > start + 0.005  # the other O–H relaxed


def test_frequencies_and_the_thermochemistry_printed_by_orca():
    out = read('h2o_optfreq')
    assert [round(f, 2) for _, f in out.frequencies if f > 0] == [1637.62, 3786.94, 3881.92]
    r = thermo.thermochemistry(out.vibration_geometry or out.geometry, out.frequencies, out.energies[-1], sigma=2)
    # ORCA: ZPE 0.02120171, total thermal energy −76.29723292, total enthalpy −76.29628871, final entropy term
    # 0.02144409, G − E(el) 0.00353714 Eh (298.15 K, C2v, σ = 2)
    assert r.zpe == pytest.approx(0.02120171, abs=1e-7)  # printed to 8 decimals
    assert r.energy + r.thermal_energy == pytest.approx(-76.29723292, abs=1e-7)  # printed to 8 decimals
    assert r.energy + r.enthalpy == pytest.approx(-76.29628871, abs=1e-7)  # printed to 8 decimals
    assert r.temperature * r.entropy == pytest.approx(0.02144409, abs=1e-6)  # ours 0.0214436: constants differ by ~0.5 µEh
    assert r.gibbs == pytest.approx(0.00353714, abs=1e-6)
    # the six zeros ORCA prints for translations and rotations are not «imaginary or zero modes»
    assert r.notes == ()


def test_nmr_and_charges():
    shieldings = read('h2o_nmr').shieldings  # «0 O 345.924 31.821», «1 H 31.780 18.796»
    assert [(s.element, s.isotropic, s.anisotropy) for s in shieldings] == [
        ('O', 345.924, 31.821), ('H', 31.78, 18.796), ('H', 31.78, 18.796)]
    charges = read('h2o_verytight_hirshfeld').properties.charges
    assert charges['hirshfeld'][:3] == pytest.approx((-0.319030, 0.159517, 0.159517))
