"""crystal_pdos: the periodic overlap and the Mulliken PDOS of the real CELL_OPT of CsCl (CP2K 2026.2), the .pdos files
of CP2K and the files of projwfc.x."""

from pathlib import Path

import numpy as np
import pytest

from modules.compass.chemistry import crystal_pdos as cp
from modules.spectrum.readers import cp2k

DATA = Path(__file__).resolve().parents[1] / 'data' / 'cp2k' / 'cscl_cellopt'


@pytest.fixture(scope='module')
def levels():
    return cp.levels_from_molden((DATA / 'azimuth-MOS-1_9.molden').read_text(encoding='utf-8'), cp2k.last_cell(DATA))


def test_the_orbitals_of_csCl_by_element_and_l(levels):
    # 2 atoms in a cell of 5.28 Å: a function overlaps many images — with them the orbitals are orthonormal (checked in
    # levels_from_molden) and the shares of every orbital add up to 1
    assert np.allclose(sum(levels.weights.values()), 1.0, atol=1e-5)
    assert levels.complete and len(levels.energies) == 27 and levels.occupations[:8].tolist() == [2.0] * 8

    def main(k):
        return max(levels.weights, key=lambda key: levels.weights[key][k])

    order = np.argsort(levels.energies)
    occupied = [k for k in order if levels.occupations[k] > 0]
    # Cs 5s, Cl 3s, Cs 5p (3), Cl 3p (3) — the valence band at the top; the lowest empty level Cs 6s
    assert [main(k) for k in occupied] == [('Cs', 0), ('Cl', 0)] + [('Cs', 1)] * 3 + [('Cl', 1)] * 3
    empty = [k for k in order if levels.occupations[k] == 0]
    assert main(empty[0]) == ('Cs', 0)
    assert levels.weights[('Cl', 1)][occupied[-1]] == pytest.approx(0.95, abs=0.02)


def test_the_curves_and_the_cache(levels, tmp_path):
    found = cp.curves(levels, fwhm=0.3)
    step = found.x[1] - found.x[0]
    assert found.e0 == pytest.approx(levels.energies[levels.occupations > 0].max())
    assert found.total.sum() * step == pytest.approx(2 * len(levels.energies), rel=1e-3)  # 2 electrons per level
    assert sum(y for _, y in found.parts) == pytest.approx(found.total, abs=1e-3)
    assert [n for n, _ in found.parts] == ['Cl', 'Cs'] and 'Cl p' in [n for n, _ in found.orbitals]
    cp.write_levels(tmp_path, levels)
    again = cp.read_levels(tmp_path)
    assert np.allclose(again.energies, levels.energies, atol=1e-5)
    assert np.allclose(again.weights[('Cl', 1)], levels.weights[('Cl', 1)], atol=1e-5)


def test_the_periodic_overlap_is_symmetric():
    from modules.spectrum.analysis.gto import Shell

    shells = [Shell(0, 0, False, [0.3, 1.2], [0.6, 0.5]), Shell(1, 1, False, [0.25], [1.0]),
              Shell(1, 2, True, [0.4], [1.0])]
    centres = np.array([[0.0, 0.0, 0.0], [2.0, 1.0, 0.5]])
    cell = np.diag([6.0, 6.5, 7.0])
    s = cp.periodic_overlap(shells, centres, cell)
    assert np.allclose(s, s.T, atol=1e-12)
    # an image of the cell gives the same overlap
    moved = cp.periodic_overlap(shells, centres + np.array([[0, 0, 0], [6.0, 0, 0]]), cell)
    assert np.allclose(s, moved, atol=1e-10)


def test_the_pdos_files_of_cp2k(tmp_path):
    head = '#     MO Eigenvalue [a.u.]      Occupation                 s                 p                 d\n'
    (tmp_path / 'azimuth-k1-1_3.pdos').write_text(
        '# Projected DOS for atomic kind Cs at iter step i = 3, E(Fermi) =     0.06 a.u.\n' + head +
        '     1    -0.30   2.0   0.9   0.1   0.0\n     2     0.05   0.0   0.5   0.0   0.3\n', encoding='utf-8')
    (tmp_path / 'azimuth-k1-1_1.pdos').write_text('old', encoding='utf-8')  # an earlier step: not read
    (tmp_path / 'azimuth-k2-1_3.pdos').write_text(
        '# Projected DOS for atomic kind Cl at iter step i = 3, E(Fermi) =     0.06 a.u.\n' + head +
        '     1    -0.30   2.0   0.0   0.0   0.0\n     2     0.05   0.0   0.0   0.2   0.0\n', encoding='utf-8')
    found = cp.levels_from_cp2k_pdos(tmp_path)
    assert found.source == 'pdos' and found.complete
    assert found.energies == pytest.approx([-0.30 * cp.HARTREE_EV, 0.05 * cp.HARTREE_EV])
    assert found.weights[('Cs', 0)] == pytest.approx([0.9, 0.5]) and found.weights[('Cl', 1)] == pytest.approx([0, 0.2])


def test_the_files_of_projwfc(tmp_path):
    grid = '\n'.join(f'{e:.3f} {g:.3f} {g:.3f}' for e, g in ((-1.0, 0.5), (0.0, 1.0), (1.0, 0.2)))
    (tmp_path / 'azimuth.pdos_tot').write_text('# E (eV)  dos(E)  pdos(E)\n' + grid, encoding='utf-8')
    for name in ('azimuth.pdos_atm#1(Si)_wfc#1(s)', 'azimuth.pdos_atm#2(Si)_wfc#1(s)', 'azimuth.pdos_atm#1(Si)_wfc#2(p)'):
        (tmp_path / name).write_text('# E (eV)  ldos(E)  pdos(E)\n' + grid, encoding='utf-8')
    found = cp.qe_curves(tmp_path)
    assert found.parts[0][0] == 'Si' and found.parts[0][1] == pytest.approx([1.5, 3.0, 0.6])
    assert dict(found.orbitals)['Si s'] == pytest.approx([1.0, 2.0, 0.4])
