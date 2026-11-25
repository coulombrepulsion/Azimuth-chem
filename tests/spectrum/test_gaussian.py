"""Gaussian log files (modules/spectrum/readers/gaussian.py).

Oracles, independent of the parser:
  * numbers copied by hand from the files (Gaussian 16 logs of the cclib test data, tests/data/gaussian);
  * two independent prints of the same quantity in one file: the high-precision normal modes (HPModes)
    against the standard table (2 decimals: 0.005), the archive entry (7 decimals) against «SCF Done»
    and «EUMP2 =», the scan summary (energies and the scanned dihedral, 5 decimals) against the parsed
    points, «Tot=» of the dipole against its components (4 decimals);
  * physics: normal modes in Cartesian displacements are orthogonal in the mass-weighted metric
    (sum_a m_a x_ia . x_ja = 0, masses from the «has atomic number ... and mass» lines); lambda = hc / E
    (hc = 1239.841984 eV nm, CODATA 2018) within the rounding of eV (4 decimals) and nm (2 decimals);
    the Mulliken charges sum to the total charge and the spin densities to the number of unpaired
    electrons; atoms related by the C2h symmetry of divinylbenzene have equal shieldings.
"""

from pathlib import Path
import re

import numpy as np
import pytest

from modules.spectrum.readers.gaussian import is_gaussian, read_gaussian

DATA = Path(__file__).parents[1] / 'data' / 'gaussian'


def text(name):
    return (DATA / name).read_text(encoding='utf-8')


def test_optimization_steps_energies_and_termination():
    log = text('dvb_gopt_g16.log')
    assert is_gaussian(log)
    out = read_gaussian(log)
    assert out.program == 'Gaussian 16' and out.normal_exit and out.optimization_converged and not out.scf_failed
    assert len(out.energies) == 5 and out.energies[-1] == -382.308266602
    assert [s.energy for s in out.steps] == list(out.energies)
    assert all(s.geometry is not None and len(s.geometry.atoms) == 20 for s in out.steps)
    assert out.energies[0] > out.energies[-1]
    assert out.initial_geometry is not None and out.initial_geometry.atoms[1].position == (0.0, 0.0, 1.391558)
    broken = log.replace('Normal termination of Gaussian 16', 'Error termination via Lnk1e in /g16/l502.exe at')
    failed = read_gaussian(broken)
    assert not failed.normal_exit and failed.error_module == 'l502'


def _masses(log):
    return np.array([float(m[1]) for m in re.finditer(r'has atomic number\s+\d+ and mass\s+(\S+)', log)])


def test_frequencies_modes_and_intensities():
    log = text('dvb_ir_g16.log')
    out = read_gaussian(log)
    assert len(out.frequencies) == 54 == 3 * 20 - 6
    assert out.frequencies[0] == (1, 53.1981) and out.frequencies[-1] == (54, 3548.3320)
    first = out.modes[0]
    assert first.intensity == 0.0342 and first.vectors[0] == (0.0, 0.0, -0.08074)
    # the standard low-precision table printed after the HPModes block
    standard = {}
    lines = log.splitlines()
    for k, line in enumerate(lines):
        if line.strip().startswith('Frequencies --') and not line.strip().startswith('Frequencies ---'):
            numbers = [int(x) for x in lines[k - 2].split()]
            for n, v in zip(numbers, line.split('--')[1].split()):
                standard[n] = [float(v), []]
            head = next(j for j in range(k, k + 8) if lines[j].split()[:2] == ['Atom', 'AN'])
            for row in lines[head + 1 : head + 21]:
                f = row.split()
                for c, n in enumerate(numbers):
                    standard[n][1].append([float(x) for x in f[2 + 3 * c : 5 + 3 * c]])
    assert len(standard) == 54
    masses = _masses(log)
    assert len(masses) == 20
    vectors = np.array([m.vectors for m in out.modes])
    for m in out.modes:
        assert abs(standard[m.index][0] - m.frequency) <= 5e-5
        assert np.max(np.abs(np.array(standard[m.index][1]) - np.array(m.vectors))) <= 0.005 + 1e-9
    gram = np.einsum('iak,a,jak->ij', vectors, masses, vectors)
    off = gram - np.diag(np.diag(gram))
    # 5 printed decimals (5e-6) in each of 60 products of size <= 1 with masses <= 12: about 1e-3
    assert np.max(np.abs(off)) < 2e-3 * np.max(np.diag(gram))
    assert out.vibration_geometry is not None and len(out.vibration_geometry.atoms) == 20


def test_mulliken_apt_and_dipole():
    out = read_gaussian(text('dvb_ir_g16.log'))
    props = out.properties
    assert set(props.charges) == {'mulliken', 'apt'}
    assert abs(sum(props.charges['mulliken'])) < 1e-5 * 20 and abs(sum(props.charges['apt'])) < 1e-5 * 20
    water = read_gaussian(text('water_mp2_g16.log'))
    p = water.properties
    m = re.search(r'X=\s*(\S+)\s+Y=\s*(\S+)\s+Z=\s*(\S+)\s+Tot=\s*(\S+)', text('water_mp2_g16.log'))
    assert p.dipole_debye == float(m[4])
    from modules.spectrum.readers.gaussian import DEBYE_GAUSSIAN

    assert np.linalg.norm(p.dipole) * DEBYE_GAUSSIAN == pytest.approx(p.dipole_debye, abs=2e-4)
    # the dipole of the Mulliken point charges points the same way (H side positive)
    positions = np.array([a.position for a in p.geometry.atoms])
    point = np.array(p.charges['mulliken']) @ positions
    assert point @ np.array(p.dipole) > 0


def test_open_shell_spins():
    out = read_gaussian(text('dvb_un_sp_g16.log'))
    p = out.properties
    assert sum(p.charges['mulliken']) == pytest.approx(1.0, abs=1e-5 * 20)
    assert sum(p.spins['mulliken']) == pytest.approx(1.0, abs=1e-5 * 20)
    assert p.charges['mulliken'][0] == 0.055742 and p.spins['mulliken'][0] == 0.213022


def test_correlated_final_energy_from_the_archive():
    ccsdt = read_gaussian(text('water_ccsdt_g16.log'))
    assert ccsdt.final_energy == ('CCSD(T)', -75.0177604)
    assert ccsdt.energies[-1] == pytest.approx(-74.9643288, abs=5e-8)  # archive HF= against SCF Done
    log = text('water_mp2_g16.log')
    mp2 = read_gaussian(log)
    printed = float(re.search(r'EUMP2 =\s*(\S+)', log)[1].replace('D', 'E'))
    assert mp2.final_energy[0] == 'MP2' and mp2.final_energy[1] == pytest.approx(printed, abs=5e-8)
    assert read_gaussian(text('dvb_ir_g16.log')).final_energy is None  # DFT: the SCF energy is final


def test_td_excitations():
    out = read_gaussian(text('dvb_td_g16.log'))
    assert len(out.absorption) == 5
    first = out.absorption[0]
    assert (first.state, first.label, first.energy_ev, first.wavelength, first.fosc, first.multiplicity) == (
        1,
        'BU',
        5.3351,
        232.39,
        0.1707,
        1,
    )
    for e in out.absorption:
        assert 1239.841984 / e.energy_ev == pytest.approx(e.wavelength, abs=0.005 + 1239.841984 * 5e-5 / e.energy_ev**2)


def test_nmr_shieldings_follow_symmetry():
    from modules.spectrum.readers.orca_spectra import equivalent_groups

    out = read_gaussian(text('dvb_nmr_g16.log'))
    assert len(out.shieldings) == 20 and (out.shieldings[0].element, out.shieldings[0].isotropic) == ('C', 114.088)
    by_atom = {s.atom: s.isotropic for s in out.shieldings}
    for group in equivalent_groups(out.geometry):
        assert len({by_atom[a] for a in group}) == 1


def _summary_rows(log, name):
    start = log.index('Summary of Optimized Potential Surface Scan')
    values = []
    for line in log[start:].splitlines():
        if line.strip().startswith(name + ' ') or line.strip().startswith(name + '\t'):
            values.extend(float(v) for v in re.findall(r'-?\d+\.\d+', line))
    return values


def test_relaxed_scan_points_against_the_summary():
    log = text('dvb_scan_relaxed_g16.log')
    out = read_gaussian(log)
    scan = out.scan
    assert scan.kind == 'relaxed' and len(scan.points) == 13 and scan.coordinates[0].atoms == (2, 3, 8, 9)
    eigen = [float(v) - 382.0 for v in _summary_rows(log, 'Eigenvalues --')]
    dihedral = _summary_rows(log, 'D25')
    assert len(eigen) == len(dihedral) == 13
    for p, e, d in zip(scan.points, eigen, dihedral):
        assert p.energy == pytest.approx(e, abs=5e-6 + 1e-9)
        difference = (p.values[0] - d + 180) % 360 - 180
        assert abs(difference) < 5e-3  # Gaussian's 5 decimals and the 6 decimals of the coordinates
        assert p.converged
    assert out.steps == ()


def test_unrelaxed_scan():
    out = read_gaussian(text('dvb_scan_unrelaxed_g16.log'))
    scan = out.scan
    assert scan.kind == 'unrelaxed' and scan.coordinates[0].name == 'D7' and len(scan.points) == 13
    assert scan.points[0].values == (-180.0,) and scan.points[0].energy == pytest.approx(-382.29428, abs=6e-6)
    assert all(p.geometry is not None for p in scan.points)


def test_not_gaussian():
    with pytest.raises(ValueError):
        read_gaussian('just text')
