"""The output of pw.x (modules/spectrum/readers/qe.py).

Oracles — the numbers printed in the real outputs (tests/data/qe, pw.x 7.6), read here by eye:
  * silicon, scf, 8 atoms: «!    total energy = -67.69688399 Ry», «highest occupied level (ev): 6.2304», «P= 18.90»,
    converged, JOB DONE; the cell of the start 5.431 Å along each axis;
  * the primitive cell of silicon, vc-relax: four «!» energies, the last −16.92455412 Ry, «Final enthalpy =
    −16.9245215836 Ry», 2 BFGS steps (the last «number of bfgs steps = 1»), the final cell with the first vector
    (3.866076314, 0, 0) Å and the atoms at 0 and ¼; that cell as a crystal: a = b = c = 3.8661 Å, 60° (fcc primitive),
    the cubic constant a√2 = 5.4674 Å (PBE: about 5.47).
"""

from math import sqrt
from pathlib import Path

from modules.spectrum.readers import qe

DATA = Path(__file__).resolve().parents[1] / 'data' / 'qe'


def test_silicon_scf():
    text = (DATA / 'si_scf_pw76.out').read_text(encoding='utf-8')
    r = qe.read(text)
    assert qe.is_qe(text) and r.version.startswith('7.6') and r.calculation == 'scf' and r.nat == 8
    assert r.energy == -67.69688399 and abs(r.energy_hartree + 33.848441995) < 1e-9
    assert r.highest == 6.2304 and r.fermi is None and r.pressures == [18.90]
    assert r.converged and r.done and r.error == '' and r.atoms == ()
    assert all(abs(r.cell[k][k] - 5.431) < 1e-4 for k in range(3))
    assert qe.final_crystal(r) is None


def test_silicon_vc_relax():
    r = qe.read((DATA / 'si2_vcrelax_pw76.out').read_text(encoding='utf-8'))
    assert r.calculation == 'vc-relax' and len(r.energies) == 4 and r.energy == -16.92455412
    assert r.enthalpy == -16.9245215836 and r.steps == 2 and r.converged and r.done
    assert r.cell[0] == (3.866076314, -0.0, 0.0)
    assert [s for s, _ in r.atoms] == ['Si', 'Si'] and abs(r.atoms[1][1][0] - 0.25) < 1e-8
    crystal = qe.final_crystal(r, 'Si')
    c = crystal.cell
    assert abs(c.a - 3.866076) < 1e-5 and abs(c.b - c.a) < 1e-5 and abs(c.alpha - 60) < 1e-4 and abs(c.gamma - 60) < 1e-4
    assert abs(c.a * sqrt(2) - 5.4674) < 1e-3 and len(crystal.sites) == 2


def test_an_error_block():
    text = ('     Program PWSCF v.7.6 starts on 11Nov2026\n %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%\n'
            '     Error in routine readpp (2):\n     file Si.upf not found\n'
            ' %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%\n')
    r = qe.read(text)
    assert 'file Si.upf not found' in r.error and not r.done and r.energy is None


def test_the_primitive_cell_gives_a_quarter_of_the_energy():
    # the same silicon in the primitive cell of crystal.primitive (2 atoms) and in the conventional one (8):
    # E(8) / 4 = E(2) within 0.1 mRy (the k grids differ), the same pressure within 0.05 kbar
    big = qe.read((DATA / 'si_scf_pw76.out').read_text(encoding='utf-8'))
    small = qe.read((DATA / 'si_primitive_scf_pw76.out').read_text(encoding='utf-8'))
    assert small.nat == 2 and abs(big.energy / 4 - small.energy) < 1e-4
    assert abs(big.pressures[-1] - small.pressures[-1]) < 0.05
