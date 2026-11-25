"""Psi4 1.11 (conda-forge, the installer of Sextant) run on the owner's Mac 2026-11-22 with the inputs Sextant writes
(tests/data/psi4/README.md): the energy of CCSD(T) with the frozen core, TD-DFT with «td-» and D3(BJ), an optimization
without symmetry and its frequencies. Oracles — the outputs themselves and ORCA 6.0.1 for the same CCSD(T)."""

from pathlib import Path

import pytest

from modules.spectrum.readers.psi4 import read_psi4

DATA = Path(__file__).resolve().parents[1] / 'data' / 'psi4'


def read(name):
    return read_psi4((DATA / name).read_text(encoding='utf-8'))


def test_ccsdt_with_the_frozen_core_as_orca():
    out = read('water_ccsdt_fc_psi4-1.11.out')
    assert out.normal_exit and out.final_energy == ('CCSD(T)', pytest.approx(-76.332194197, abs=1e-8))
    # ORCA 6.0.1, its own geometry of water, cc-pVTZ, frozen core (tests/data/orca601/h2o_ccsdt_ccpvtz.out): -76.332171;
    # without the frozen core Psi4 gave -76.345467 — the 1s of oxygen correlated
    assert out.final_energy[1] == pytest.approx(-76.332171, abs=1e-4)


def test_tddft_of_formaldehyde():
    out = read('ch2o_tddft_d3bj_psi4-1.11.out')
    states = out.absorption
    assert out.normal_exit and len(states) == 10
    assert states[0].energy_ev == pytest.approx(3.709, abs=1e-3) and states[0].fosc == 0.0  # n→π*, dark
    assert max(states, key=lambda s: s.fosc).energy_ev == pytest.approx(10.889, abs=1e-3)
    assert out.energies[-1] == pytest.approx(-114.359430729, abs=1e-8)  # D3(BJ) included


def test_optimization_and_frequencies_of_water():
    out = read('water_optfreq_psi4-1.11.out')
    assert out.normal_exit and out.optimization_converged and not out.imaginary
    assert [round(f, 1) for _, f in out.frequencies] == [1638.6, 3792.3, 3887.6]
    # optimize() then frequency() in one file: the steps of the optimization end at FINDIF, and the frequencies belong to
    # the optimized geometry and energy — not to the start (0.222.7: no steps, the energy and the modes of the start)
    assert len(out.steps) == 3 and out.energies[-1] == pytest.approx(-76.358326, abs=1e-6)
    from modules.spectrum.readers.psi4 import _geometries

    first = _geometries((DATA / 'water_optfreq_psi4-1.11.out').read_text(encoding='utf-8'))[0][2]
    assert out.vibration_geometry.atoms == out.geometry.atoms and out.geometry.atoms != first.atoms
