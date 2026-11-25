"""crystal_field: the valence density and the ELF of the real CELL_OPT of CsCl (CP2K 2026.2) on the cell of the file."""

from pathlib import Path

import numpy as np
import pytest

from azimuth.core import Atom, Molecule
from modules.compass.chemistry import crystal as cr
from modules.compass.chemistry import crystal_field as cf
from modules.compass.chemistry import crystal_pdos as cp
from modules.spectrum.readers import cp2k

DATA = Path(__file__).resolve().parents[1] / 'data' / 'cp2k' / 'cscl_cellopt'
CIF = Path(__file__).resolve().parents[2] / 'examples' / '10-crystals' / 'CsCl.cif'


@pytest.fixture(scope='module')
def wave():
    return cp.wavefunction((DATA / 'azimuth-MOS-1_9.molden').read_text(encoding='utf-8'), cp2k.last_cell(DATA))


def test_the_density_holds_the_valence_electrons(wave):
    # GTH-PBE: Cs 9 + Cl 7 valence electrons in the cell; the cell computed (5.28 Å after the CELL_OPT) is the cell of
    # the file stretched — the fractions map one to one
    cell = np.array(cp2k.last_cell(DATA))
    rho = cf.cell_field(wave, cell, np.eye(3), 'density', step=0.2)
    assert cf.integral(rho, cell) == pytest.approx(16.0, abs=1e-3)
    assert rho.min() >= -1e-12 and rho.max() > 0.1


def test_the_elf_of_cscl(wave):
    cell = np.array(cp2k.last_cell(DATA))
    elf = cf.cell_field(wave, cell, np.eye(3), 'elf', step=0.2)
    assert 0.0 <= elf.min() and elf.max() <= 1.0
    n = elf.shape[0]
    diagonal = [elf[i, i, i] for i in range(n)]
    # the shells around Cs (0, 0, 0) and Cl (½, ½, ½) are paired electrons, ELF > 0.8; between them it falls
    assert max(diagonal[1:n // 2]) > 0.8 and max(diagonal[n // 2 - 3:n // 2 + 4]) > 0.8
    assert min(diagonal[n // 4: n // 2]) < 0.3


def test_the_cube_over_a_block():
    cell = cr.parse_cif(CIF.read_text(encoding='utf-8')).cell
    rows = np.array(cell.vectors())
    values = np.arange(4 * 5 * 6, dtype=float).reshape(4, 5, 6)
    atoms = [Atom('Cs', *(np.array(f) @ rows)) for f in ((0, 0, 0), (2, 2, 2), (0, 2, 0))]
    cube = cf.model_cube(values, rows, Molecule('block', tuple(atoms)), 'ρ')
    assert cube.values.shape == (9, 11, 13, 1)  # 2 cells along each edge and the closing layer
    assert np.allclose(cube.values[4, 5, 6, 0], values[0, 0, 0]) and np.allclose(cube.axes[0], rows[0] / 4)
    assert np.allclose(cube.origin, 0)


def test_the_map_of_a_supercell():
    crystal = cr.parse_cif(CIF.read_text(encoding='utf-8'))
    rows = np.array(crystal.cell.vectors()) * 3 * 1.004  # a 3 × 3 × 3 run, the cell grown by 0.4 %
    assert np.allclose(cf.mapping_of(crystal, rows), np.eye(3) / 3)
