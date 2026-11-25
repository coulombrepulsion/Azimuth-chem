"""Q-Chem outputs (modules/spectrum/readers/qchem.py).

Oracles, independent of the parser: another program for the same calculation — water MP2/STO-3G (frozen core)
in GAMESS (US) 2017 (tests/data/gamess): the MP2 energies agree to 1e-7 Eh; a second print in the same file —
«Final energy is» of the optimizer against the last step, «Total energy for state n» minus the SCF energy
against the excitation energy in eV, «Sum of atomic charges» against the sum of the Mulliken charges, the
multiplicity (a doublet cation: one unpaired electron) against the sum of the spins; the number of normal
modes 3N − 6. Data: cclib test data (BSD-3-Clause), tests/data/qchem/README.md.
"""

from pathlib import Path
import gzip
import re

import pytest

from modules.spectrum.readers.outputs import program, read_any
from modules.spectrum.readers.qchem import is_qchem, read_qchem

DATA = Path(__file__).parents[1] / 'data'


def text(name, folder='qchem'):
    return gzip.decompress((DATA / folder / name).read_bytes()).decode('utf-8')


def test_mp2_agrees_with_gamess_and_the_correlated_ladder():
    from modules.spectrum.readers.gamess import read_gamess

    out = read_qchem(text('water_mp2_qchem-5.4.out.gz'))
    assert out.program == 'Q-Chem 5.4' and out.normal_exit
    gamess = read_gamess(text('water_mp2_gamess-2017.out.gz', 'gamess'))
    assert out.final_energy[0] == 'MP2' and out.final_energy[1] == pytest.approx(gamess.final_energy[1], abs=1e-7)
    assert read_qchem(text('water_ccsdt_qchem-5.4.out.gz')).final_energy == ('CCSD(T)', -75.0177603)
    assert read_qchem(text('water_mp4_qchem-5.4.out.gz')).final_energy == ('MP4', -75.016143404)


def test_optimization_steps():
    log = text('dvb_gopt_qchem-5.4.out.gz')
    out = read_qchem(log)
    assert out.optimization_converged and len(out.steps) == 5
    final = float(re.search(r'Final energy is\s+(\S+)', log)[1])
    assert out.steps[-1].energy == pytest.approx(final, abs=1e-8)
    assert out.geometry.atoms[0].position == (1.4151037309, 0.2406820315, 0.0)


def test_frequencies():
    out = read_qchem(text('dvb_ir_qchem-5.4.out.gz'))
    assert len(out.frequencies) == 54 and out.frequencies[0] == (1, 47.24) and not out.imaginary
    assert all(m.animatable and len(m.vectors) == 20 for m in out.modes) and out.modes[0].intensity == 0.031
    water = read_qchem(text('water_ir_qchem-5.4.out.gz'))
    assert len(water.frequencies) == 3 and all(m.intensity is not None for m in water.modes)


def test_charges_spins_dipole_and_states():
    log = text('dvb_sp_un_qchem-5.4.out.gz')
    cation = read_qchem(log)
    total = float(re.findall(r'Sum of atomic charges =\s*(\S+)', log)[-1])
    assert sum(cation.properties.charges['mulliken']) == pytest.approx(total, abs=1e-5)
    assert total == pytest.approx(1, abs=1e-5)
    assert sum(cation.properties.spins['mulliken']) == pytest.approx(1, abs=1e-4)
    water = read_qchem(text('water_mp2_qchem-5.4.out.gz'))
    assert water.properties.dipole_debye == 1.6735
    log = text('dvb_td_qchem-5.4.out.gz')
    td = read_qchem(log)
    assert len(td.absorption) == 10
    scf = td.energies[-1]
    state = float(re.findall(r'Total energy for state\s+1:\s+(\S+)', log)[-1])
    assert td.absorption[0].energy_ev == pytest.approx((state - scf) * 27.211386, abs=2e-3)


def test_recognized_by_read_any():
    log = text('dvb_sp_qchem-5.4.out.gz')
    assert is_qchem(log) and program(log) == 'Q-Chem' and read_any(log).program == 'Q-Chem 5.4'
