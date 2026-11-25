"""NWChem outputs (modules/spectrum/readers/nwchem.py).

Oracles, independent of the parser: other programs for the same calculation — water HF/STO-3G at the same
geometry in Q-Chem 5.4 and GAMESS (US) 2017 (tests/data/qchem, tests/data/gamess): the SCF energies agree to
1e-7 Eh; a second print in the same file — the frequencies against the «Infra Red Intensities» table, the
excitation energies in eV against those in a.u., the CCSD(T) energy against CCSD + the (T) correction; the
total charge and the multiplicity of the input (dvb_td.in: nroots 5; dvb_un_sp_ks.in: charge 1) against the
sum of the Mulliken charges and the number of states. Data: cclib test data (BSD-3-Clause), tests/data/nwchem/README.md.
"""

from pathlib import Path
import gzip
import re

import pytest

from modules.spectrum.readers.nwchem import is_nwchem, read_nwchem
from modules.spectrum.readers.outputs import program, read_any

DATA = Path(__file__).parents[1] / 'data'


def text(name, folder='nwchem'):
    return gzip.decompress((DATA / folder / name).read_bytes()).decode('utf-8')


def test_scf_energy_agrees_with_qchem_and_gamess():
    from modules.spectrum.readers.gamess import read_gamess
    from modules.spectrum.readers.qchem import read_qchem

    out = read_nwchem(text('water_mp2_nwchem-7.0.out.gz'))
    assert out.program == 'NWChem 7.0.0' and out.normal_exit and out.error_module is None
    qchem = read_qchem(text('water_mp2_qchem-5.4.out.gz', 'qchem'))
    gamess = read_gamess(text('water_mp2_gamess-2017.out.gz', 'gamess'))
    assert out.energies[-1] == pytest.approx(qchem.energies[-1], abs=1e-7)
    assert out.energies[-1] == pytest.approx(gamess.energies[-1], abs=1e-7)
    assert out.final_energy == ('MP2', -75.002378700325) and out.geometry.formula == 'H2O'


def test_ccsd_t_is_ccsd_plus_the_correction():
    log = text('water_ccsdt_nwchem-7.0.out.gz')
    out = read_nwchem(log)
    ccsd = float(re.search(r'CCSD total energy / hartree\s*=\s*(\S+)', log)[1])
    correction = float(re.search(r'CCSD\(T\)  correction energy / hartree\s*=\s*(\S+)', log)[1])
    assert out.final_energy[0] == 'CCSD(T)'
    assert out.final_energy[1] == pytest.approx(ccsd + correction, abs=1e-9)


def test_optimization_steps():
    log = text('dvb_gopt_ks_nwchem-7.0.out.gz')
    out = read_nwchem(log)
    assert out.optimization_converged and len(out.steps) == 4
    energies = [s.energy for s in out.steps]
    assert energies == sorted(energies, reverse=True)  # the energy goes down step by step
    assert energies[-1] == pytest.approx(out.energies[-1], abs=1e-8)  # the last SCF energy, printed apart
    assert [a.position for a in out.steps[-1].geometry.atoms] == [a.position for a in out.geometry.atoms]
    assert out.initial_geometry.atoms[0].position == (0.23680554, 1.41416660, 0.0)


def test_frequencies_against_the_intensity_table():
    log = text('dvb_ir_nwchem-7.0.out.gz')
    out = read_nwchem(log)
    assert len(out.frequencies) == 3 * 20 - 6 and out.frequencies[0] == (7, 49.01) and not out.imaginary
    table = re.search(r'Projected Infra Red Intensities\s*\n.*\n.*\n((?:.*\n){60})', log)[1].splitlines()
    rows = {int(r.split()[0]): (float(r.split()[1]), float(r.split()[5])) for r in table}
    for mode in out.modes:
        assert mode.frequency == pytest.approx(rows[mode.index][0], abs=0.006)
        assert mode.intensity == rows[mode.index][1]
        assert mode.animatable and len(mode.vectors) == 20
    assert out.vibration_geometry.formula == 'C10H10'


def test_charges_dipole_and_states():
    neutral = read_nwchem(text('dvb_sp_ks_nwchem-7.0.out.gz'))
    assert sum(neutral.properties.charges['mulliken']) == pytest.approx(0, abs=1e-4)
    assert neutral.properties.dipole_debye == pytest.approx(0, abs=1e-5)  # centre of symmetry (C2h)
    cation = read_nwchem(text('dvb_un_sp_ks_nwchem-7.0.out.gz'))
    assert sum(cation.properties.charges['mulliken']) == pytest.approx(1, abs=1e-4)
    td = read_nwchem(text('dvb_td_nwchem-7.0.out.gz'))
    assert len(td.absorption) == 5 and [e.state for e in td.absorption] == [1, 2, 3, 4, 5]
    first = td.absorption[0]
    assert first.energy_ev == pytest.approx(0.196071264 * 27.211386, abs=1e-3) and first.fosc == 0.1611342389
    assert first.multiplicity == 1 and first.label == 'singlet bu'


def test_recognized_by_read_any():
    log = text('dvb_sp_ks_nwchem-7.0.out.gz')
    assert is_nwchem(log) and program(log) == 'NWChem' and read_any(log).program == 'NWChem 7.0.0'


# -- NWChem 7.3.0 run with the inputs of Sextant (tests/data/nwchem/README.md, «NWChem 7.3.0») -------------------------
# Oracles: the same calculations in Psi4 1.11 and ORCA 6.0.1 that day (docs/plans/TASK_MATRIX.md). Psi4 and NWChem have
# the same B3LYP (VWN1RPA); ORCA's has VWN5 — its numbers are compared where the functional does not enter (MP2).
def test_nwchem73_water_optimization_and_frequencies_agree_with_psi4():
    out = read_any(text('water_optfreq_b3lyp_d3bj_nwchem-7.3.out.gz'))
    assert out.program == 'NWChem 7.3.0' and out.normal_exit and out.optimization_converged and len(out.steps) == 5
    assert out.energies[-1] == pytest.approx(-76.35889974, abs=2e-5)  # Psi4 1.11, B3LYP-D3(BJ)/def2-SVP, DF
    assert [f for _, f in out.frequencies] == pytest.approx([1638.77, 3791.91, 3887.13], abs=0.5)  # Psi4 1.11
    assert len(out.modes) == 3 and len(out.vibration_geometry.atoms) == 3


def test_nwchem73_transition_state_agrees_with_psi4():
    # HCN ⇌ HNC: «task dft saddle», then «task dft freq» — one imaginary frequency; the same search in Psi4 1.11
    from modules.spectrum.readers.psi4 import read_psi4

    out = read_any(text('hcn_ts_b3lyp_d3bj_nwchem-7.3.out.gz'))
    psi4 = read_psi4(text('hcn_ts_b3lyp_d3bj_psi4-1.11.out.gz', 'psi4'))
    mine, theirs = [f for _, f in out.frequencies], [f for _, f in psi4.frequencies]
    assert out.optimization_converged and sum(f < 0 for f in mine) == 1 and len(mine) == 3
    assert mine == pytest.approx(theirs, abs=0.5) and mine[0] == pytest.approx(-1117.7, abs=0.2)
    assert out.energies[-1] == pytest.approx(psi4.energies[-1], abs=2e-5)


def test_nwchem73_tddft_states_agree_with_psi4():
    out = read_any(text('ch2o_tddft_nwchem-7.3.out.gz'))
    states = [(round(e.energy_ev, 2), round(e.fosc, 4)) for e in out.absorption]
    assert len(states) == 10 and states[:3] == [(3.72, 0.0), (8.31, 0.0989), (8.57, 0.0018)]  # Psi4 1.11: the same


def test_nwchem73_nmr_shieldings_are_read():
    # «property shielding»: the isotropic shieldings; ORCA 6.0.1 for the same geometry and basis gives O 337.4, H 31.3
    # (its B3LYP has VWN5 — the numbers agree to 0.2 ppm)
    out = read_any(text('water_nmr_nwchem-7.3.out.gz'))
    assert [(s.atom, s.element) for s in out.shieldings] == [(0, 'O'), (1, 'H'), (2, 'H')]
    assert [s.isotropic for s in out.shieldings] == pytest.approx([337.4, 31.3, 31.3], abs=0.2)
    assert out.shieldings[0].anisotropy == pytest.approx(32.215) and out.shieldings[1].isotropic == out.shieldings[2].isotropic
    assert read_any(text('water_optfreq_b3lyp_d3bj_nwchem-7.3.out.gz')).shieldings == ()


def test_nwchem73_mp2_with_the_frozen_core_agrees_with_orca():
    # «mp2 freeze atomic» of Sextant: MP2/cc-pVDZ of water −76.228415434; ORCA 6.0.1 (frozen core by default)
    # −76.228415381 — to 1e-7 Eh; without it NWChem correlates the 1s of oxygen too: −76.230728
    out = read_any(text('water_mp2_fc_nwchem-7.3.out.gz'))
    assert out.final_energy[0] == 'MP2' and out.final_energy[1] == pytest.approx(-76.228415381, abs=2e-7)


def test_nwchem73_open_shell_cation():
    out = read_any(text('water_cation_nwchem-7.3.out.gz'))
    assert out.normal_exit and out.energies[-1] == pytest.approx(-75.90456852, abs=3e-5)  # Psi4 1.11, the same input
