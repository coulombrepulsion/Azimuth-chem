"""GAMESS (US) and Firefly outputs (modules/spectrum/readers/gamess.py).

Oracles, independent of the parser: another program for the same calculation — water MP2/STO-3G in Firefly 8.0
and Q-Chem 5.4 (agree to 1e-7 Eh); a second print in the same file — the energy of the last NSERCH against the
final geometry, the TD-DFT summary (E(state) − E(ground) against ΔE in eV), the populations against the charges
(charge = Z − population); the input of the transition state (nh3_ts_ir: one imaginary frequency) and the
number of modes 3N − 6 after the translations and rotations named by GAMESS itself. Data: cclib test data
(BSD-3-Clause), tests/data/gamess/README.md.
"""

from pathlib import Path
import gzip

import pytest

from modules.spectrum.readers.gamess import IR_KM, is_gamess, read_gamess
from modules.spectrum.readers.outputs import program, read_any

DATA = Path(__file__).parents[1] / 'data' / 'gamess'


def text(name):
    return gzip.decompress((DATA / name).read_bytes()).decode('utf-8')


def test_mp2_agrees_with_firefly():
    out = read_gamess(text('water_mp2_gamess-2017.out.gz'))
    assert out.program == 'GAMESS (US) 20 APR 2017 (R1)' and out.normal_exit and out.error_module is None
    firefly = read_gamess(text('water_mp2_firefly-8.0.out.gz'))
    assert firefly.program == 'Firefly 8.0.1'
    assert out.final_energy[0] == firefly.final_energy[0] == 'MP2'
    assert out.final_energy[1] == pytest.approx(firefly.final_energy[1], abs=1e-7)
    assert read_gamess(text('water_ccsdt_gamess-2017.out.gz')).final_energy == ('CCSD(T)', -76.2299053356)


def test_optimization_steps():
    out = read_gamess(text('dvb_gopt_a_gamess-2017.out.gz'))
    assert out.optimization_converged and len(out.steps) == 7
    assert out.steps[-1].energy == pytest.approx(out.energies[-1], abs=1e-9)
    final, last = out.geometry.atoms, out.steps[-1].geometry.atoms
    assert max(abs(a - b) for x, y in zip(final, last) for a, b in zip(x.position, y.position)) < 1e-5
    firefly = read_gamess(text('dvb_gopt_a_firefly-8.0.out.gz'))
    assert firefly.optimization_converged and len(firefly.steps) > 1 and firefly.energies


def test_frequencies_and_transition_state():
    out = read_gamess(text('dvb_ir_gamess-2017.out.gz'))
    assert len(out.frequencies) == 54 and out.frequencies[0] == (7, 47.87) and not out.imaginary
    assert out.modes[2].intensity == pytest.approx(0.00808 * IR_KM, rel=1e-9)  # printed in D²/(amu·Å²)
    assert all(m.animatable and len(m.vectors) == 20 for m in out.modes)
    ts = read_gamess(text('nh3_ts_ir_gamess-2017.out.gz'))
    assert len(ts.frequencies) == 6 and ts.imaginary == ((1, -825.18),)
    firefly = read_gamess(text('dvb_ir_firefly-8.0.out.gz'))
    assert len(firefly.frequencies) == 54


def test_charges_dipole_and_states():
    neutral = read_gamess(text('dvb_sp_gamess-2017.out.gz'))
    assert sum(neutral.properties.charges['mulliken']) == pytest.approx(0, abs=1e-4)
    cation = read_gamess(text('dvb_un_sp_gamess-2017.out.gz'))
    assert sum(cation.properties.charges['mulliken']) == pytest.approx(1, abs=1e-4)
    water = read_gamess(text('water_mp2_gamess-2017.out.gz'))
    assert water.properties.dipole_debye == pytest.approx(1.5994, abs=1e-4)
    td = read_gamess(text('dvb_td_gamess-2017.out.gz'))
    assert len(td.absorption) == 10 and td.absorption[0].fosc == 0.6722
    assert td.absorption[0].energy_ev == pytest.approx((-384.4995231645 + 384.6644423987) * 27.211386, abs=2e-3)


def test_recognized_by_read_any():
    log = text('dvb_sp_gamess-2017.out.gz')
    assert is_gamess(log) and program(log) == 'GAMESS' and read_any(log).program.startswith('GAMESS (US)')
