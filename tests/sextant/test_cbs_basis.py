"""The extrapolation to the complete basis set as a «basis» of ORCA (azimuth/core_bases.py CBS_BASES).

Oracles: the keyword of the ORCA manual, «Extrapolate(X/Y,family)», and the real run of ORCA 6.0.1 with the input
Sextant writes (tests/data/orca601/cbs_h2o: water, DLPNO-CCSD(T), cc-pVDZ and cc-pVTZ); the numbers of its block
«Extrapolation of energy» copied by hand, and the two-point formulas applied to its own energies with the exponents it
prints (α = 4.420, β = 2.460): E_SCF(X) = E_CBS + A·exp(−α√X), E_corr(CBS) = (X^β E_X − Y^β E_Y)/(X^β − Y^β).
"""

from math import exp, sqrt
from pathlib import Path

import pytest

from azimuth.core import CBS_BASES, Calculation, bases_for, orca_input, read_xyz
from modules.sextant import inputs
from modules.spectrum.readers.orca import read_output

WATER = read_xyz('3\nwater\nO 0 0 0.117\nH 0.757 0 -0.469\nH -0.757 0 -0.469')
RUN = Path(__file__).resolve().parents[1] / 'data' / 'orca601' / 'cbs_h2o'


def calc(**changes):
    return Calculation(**{'method': 'DLPNO-CCSD(T)', 'basis': 'CBS(cc-pVDZ/TZ)', 'task': 'Энергия', 'cores': 4,
                          'memory_mb': 1500, **changes})


def test_the_input_is_the_one_orca_ran():
    text = orca_input(WATER, calc())
    assert text.splitlines()[1] == '! DLPNO-CCSD(T) Extrapolate(2/3,cc) AutoAux TightSCF'
    ran = (RUN / 'h2o_dlpno_cbs23.inp').read_text(encoding='utf-8')
    assert text.splitlines()[1:4] == ran.splitlines()[1:4]
    keywords = {'CBS(cc-pVTZ/QZ)': 'Extrapolate(3/4,cc)', 'CBS(aug-cc-pVDZ/TZ)': 'Extrapolate(2/3,aug-cc)',
                'CBS(def2-SVP/TZVPP)': 'Extrapolate(2/3,def2)', 'CBS(def2-TZVPP/QZVPP)': 'Extrapolate(3/4,def2)'}
    for basis, keyword in keywords.items():
        assert keyword in orca_input(WATER, calc(basis=basis, method='MP2')).splitlines()[1]
    assert set(keywords) | {'CBS(cc-pVDZ/TZ)'} == set(CBS_BASES)


def test_only_orca_and_only_an_energy_of_a_correlated_method():
    assert CBS_BASES <= set(bases_for('orca'))
    for kind in ('gaussian', 'psi4'):
        assert not CBS_BASES & set(bases_for(kind))
    for wrong in (dict(method='B3LYP'), dict(method='HF'), dict(method='MP2', task='Оптимизация'),
                  dict(element_basis='O=cc-pVTZ'), dict(relativistic='DKH')):
        with pytest.raises(ValueError, match='CBS'):
            orca_input(WATER, calc(**wrong))
    with pytest.raises(ValueError, match='экстраполяция'):
        orca_input(WATER, calc(basis='cc-pVDZ', element_basis='O=CBS(cc-pVDZ/TZ)'))
    for method in ('MP2', 'CCSD(T)', 'DLPNO-CCSD(T)'):
        assert orca_input(WATER, calc(method=method))


def test_the_input_is_read_back_and_named_safely():
    text = orca_input(WATER, calc())
    found = inputs.read_settings('orca', text)
    assert found['basis'] == 'CBS(cc-pVDZ/TZ)' and found['method'] == 'DLPNO-CCSD(T)'
    assert list(inputs.input_files('orca', WATER, calc())) == ['H2O_DLPNO-CCSDT_CBScc-pVDZ-TZ.inp']


def test_the_result_of_the_real_run():
    out = read_output((RUN / 'h2o_dlpno_cbs23.out').read_text(encoding='utf-8'))
    assert out.energies[-1] == pytest.approx(-76.377553420951, abs=1e-12)
    scheme, scf, corr, total = out.cbs
    assert (scheme, scf, corr, total) == ('2/3', -76.067036533, -0.310516888, -76.377553421)
    assert scf + corr == pytest.approx(total, abs=2e-9)
    # the two-point formulas on the energies ORCA printed for cc-pVDZ and cc-pVTZ
    scf2, scf3, corr2, corr3, alpha, beta = -76.026793645, -76.057160680, -0.214070521, -0.274945454, 4.420, 2.460
    e2, e3 = exp(-alpha * sqrt(2)), exp(-alpha * sqrt(3))
    assert (scf2 * e3 - scf3 * e2) / (e3 - e2) == pytest.approx(scf, abs=2e-8)
    assert (2 ** beta * corr2 - 3 ** beta * corr3) / (2 ** beta - 3 ** beta) == pytest.approx(corr, abs=2e-8)


def test_an_ordinary_output_has_no_cbs():
    out = read_output((RUN.parent / 'h2o_optfreq.out').read_text(encoding='utf-8'))
    assert out.cbs is None
