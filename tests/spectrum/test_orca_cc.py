"""Coupled clusters in ORCA 6.0.1 — the energy read (tests/data/orca601/h2o_*ccsdt_ccpvtz.out) and the inputs.

Oracles: the lines «E(CCSD(T)) ... −76.332171457» (canonical) and «... −76.332003041» (DLPNO) printed by ORCA; DLPNO
recovers the canonical correlation energy to within a fraction of a millihartree (its NormalPNO thresholds)."""

from pathlib import Path

import pytest

from azimuth.core import Calculation, methods_for, read_xyz
from modules.sextant import inputs
from modules.spectrum.readers.outputs import read_any

DATA = Path(__file__).resolve().parents[1] / 'data' / 'orca601'
WATER = read_xyz('3\nwater\nO 0 0 0.117\nH 0 0.757 -0.467\nH 0 -0.757 -0.467\n')


def test_the_energies_of_ccsdt_and_dlpno():
    found = {}
    for name in ('h2o_ccsdt_ccpvtz', 'h2o_dlpno_ccsdt_ccpvtz'):
        text = (DATA / f'{name}.out').read_text(encoding='utf-8')
        out = read_any(text, DATA / f'{name}.out')
        assert out.normal_exit and not out.scf_failed
        found[name] = out.energies[-1]
    assert found['h2o_ccsdt_ccpvtz'] == pytest.approx(-76.332171457, abs=1e-8)
    assert found['h2o_dlpno_ccsdt_ccpvtz'] == pytest.approx(-76.332003041, abs=1e-8)
    assert abs(found['h2o_ccsdt_ccpvtz'] - found['h2o_dlpno_ccsdt_ccpvtz']) < 3e-4


def test_the_coupled_clusters_are_an_energy_only():
    assert {'CCSD(T)', 'DLPNO-CCSD(T)'} <= set(methods_for('orca'))
    assert 'CCSD(T)' in methods_for('gaussian') and 'CCSD(T)' in methods_for('psi4')
    assert 'DLPNO-CCSD(T)' not in methods_for('gaussian') and not {'CCSD(T)'} & set(methods_for('nwchem'))
    dlpno = inputs.preview('orca', WATER, Calculation(method='DLPNO-CCSD(T)', basis='cc-pVTZ', task='Энергия'))
    assert '! DLPNO-CCSD(T) cc-pVTZ AutoAux' in dlpno
    psi4 = inputs.preview('psi4', WATER, Calculation(method='CCSD(T)', basis='cc-pVDZ', task='Энергия'))
    assert 'reference rhf' in psi4 and 'scf_type pk' in psi4 and "energy('ccsd(t)')" in psi4
    for task in ('Оптимизация', 'Оптимизация + частоты', 'Спектр UV-Vis (TD-DFT)'):
        with pytest.raises(ValueError):
            inputs.preview('orca', WATER, Calculation(method='CCSD(T)', basis='cc-pVDZ', task=task))
    with pytest.raises(ValueError):  # no D3 for a coupled cluster
        inputs.preview('orca', WATER, Calculation(method='CCSD(T)', basis='cc-pVDZ', task='Энергия', dispersion='D3BJ'))
