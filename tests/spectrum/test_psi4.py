"""Psi4 outputs (modules/spectrum/readers/psi4.py).

Oracles, independent of the parser: another program for the same calculation — water HF/STO-3G at the
same geometry in Gaussian 16 (tests/data/gaussian/water_ccsdt_g16.log): the SCF energies agree to 1e-7
Eh and the dipole moments to the 4 printed decimals; a second print in the same file — the frequency
table against the «post-proj all modes» list (4 decimals); the total charge and spin from the geometry
header against the sums of the Mulliken charges and spins; the final optimized geometry against the
geometry of the last step. Data: cclib test data (BSD-3-Clause), tests/data/psi4/README.md.
"""

from pathlib import Path
import re

import numpy as np
import pytest

from modules.spectrum.readers.psi4 import is_psi4, read_psi4

DATA = Path(__file__).parents[1] / 'data' / 'psi4'


def text(name):
    return (DATA / name).read_text(encoding='utf-8')


def test_scf_energy_and_dipole_agree_with_gaussian():
    from modules.spectrum.readers.gaussian import read_gaussian

    out = read_psi4(text('water_ccsdt_psi4-1.7.out'))
    assert out.program == 'Psi4 1.7' and out.normal_exit
    gaussian = read_gaussian((DATA.parent / 'gaussian' / 'water_ccsdt_g16.log').read_text(encoding='utf-8'))
    assert out.energies[-1] == pytest.approx(gaussian.energies[-1], abs=1e-7)
    assert out.properties.dipole_debye == pytest.approx(gaussian.properties.dipole_debye, abs=5e-5 + 1e-6)
    assert out.final_energy == ('CCSD(T)', -75.017834880709472)


def test_df_mp2_final_energy():
    out = read_psi4(text('water_mp2_psi4-1.7.out'))
    assert out.final_energy == ('MP2', -75.0024556907484765)


def test_optimization_steps():
    out = read_psi4(text('dvb_gopt_rhf_psi4-1.7.out'))
    assert out.optimization_converged and len(out.steps) == 5
    energies = [s.energy for s in out.steps]
    assert energies == list(out.energies) and energies[-1] == min(energies)
    last = np.array([a.position for a in out.steps[-1].geometry.atoms])
    final = np.array([a.position for a in out.geometry.atoms])
    assert np.max(np.abs(last - final)) < 1e-9
    assert out.geometry.atoms[0].position == (-1.393991595118, 0.221470431596, 0.0)


def test_findif_frequencies_and_reference_geometry():
    log = text('dvb_ir_rhf_psi4-1.7.out')
    assert is_psi4(log)
    out = read_psi4(log)
    assert len(out.frequencies) == 54 and out.frequencies[0] == (7, 137.2531)
    assert len(out.energies) == 1  # the reference, not the 74 displaced points
    # the reference geometry is the input geometry: the same energy as the single point at it (another job)
    single = read_psi4(text('dvb_sp_rhf_psi4-1.7.out'))
    assert out.energies[0] == pytest.approx(single.energies[0], abs=1e-8)
    listed = re.search(r"post-proj  all modes:\[(.*?)\]", log, re.S)[1]
    values = [float(v.strip("'").rstrip('i')) for v in listed.split()]
    assert [round(f, 4) for _, f in out.frequencies] == pytest.approx(values[6:], abs=1e-9)
    assert all(m.vectors is not None and len(m.vectors) == 20 for m in out.modes)
    assert all(m.intensity is not None and m.intensity >= 0 for m in out.modes)
    assert [a.position for a in out.vibration_geometry.atoms] == [a.position for a in out.geometry.atoms]


def test_open_shell_mulliken_sums():
    log = text('dvb_sp_uhf_psi4-1.7.out')
    out = read_psi4(log)
    header = re.search(r'charge = (-?\d+), multiplicity = (\d+)', log)
    charge, multiplicity = int(header[1]), int(header[2])
    p = out.properties
    assert sum(p.charges['mulliken']) == pytest.approx(charge, abs=20 * 5e-6)
    assert sum(p.spins['mulliken']) == pytest.approx(multiplicity - 1, abs=20 * 5e-6)


def test_not_psi4():
    with pytest.raises(ValueError):
        read_psi4('text')


def test_a_transition_state_search_gives_its_steps_and_its_last_geometry():
    # Psi4 1.11, HCN ⇌ HNC, «Переходное состояние + частоты» of Sextant: opt_type ts with full_hess_every 0 — a Hessian
    # by finite differences stands BEFORE the first step. The file had no steps, and its geometry and energy were those
    # of the start. The steps are the rows of the table of OPTKING, not the geometries displaced for the Hessian; the
    # oracle of the energies is that table, of the geometry — «Final optimized geometry» of the file
    import gzip

    log = gzip.decompress((DATA / 'hcn_ts_b3lyp_d3bj_psi4-1.11.out.gz').read_bytes()).decode('utf-8')
    out = read_psi4(log)
    table = [float(m[1]) for m in re.finditer(r'^\s*\d+\s+(-93\.\d{8})\s+\S+\s+\S+.*~\s*$', log, re.M)]
    assert len(table) == 3 and [s.energy for s in out.steps] == table and out.optimization_converged
    assert out.energies[-1] == pytest.approx(table[-1], abs=5e-8) and out.energies[-1] != pytest.approx(table[0], abs=1e-6)
    final = log[log.index('Final optimized geometry and variables'):]
    row = re.search(r'^\s*N\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)', final, re.M)
    nitrogen = next(a for a in out.geometry.atoms if a.symbol == 'N')
    assert nitrogen.position == pytest.approx(tuple(float(v) for v in row.groups()), abs=1e-8)
    start = out.steps[0].geometry.atoms
    assert max(abs(a.x - b.x) + abs(a.y - b.y) for a, b in zip(start, out.geometry.atoms)) > 0.01  # it moved
    freqs = [f for _, f in out.frequencies]
    assert len(freqs) == 3 and sum(f < 0 for f in freqs) == 1 and freqs[0] == pytest.approx(-1117.708)
