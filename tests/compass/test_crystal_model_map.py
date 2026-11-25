"""crystal_model_map: the modes of CsCl at Γ on a block 2 × 2 × 2; the critical points of the 3 × 3 × 3 CP2K run of CsCl
(Multiwfn, tests/data/multiwfn) on one cell of the file."""

from pathlib import Path

import numpy as np
import pytest

from modules.compass.chemistry import crystal as cr
from modules.compass.chemistry import crystal_field
from modules.compass.chemistry import crystal_model_map as cm
from modules.spectrum.readers import cp2k

DATA = Path(__file__).resolve().parents[1] / 'data'
CIF = Path(__file__).resolve().parents[2] / 'examples' / '10-crystals' / 'CsCl.cif'


def cscl():
    return cr.parse_cif(CIF.read_text(encoding='utf-8'))


def test_the_reader_of_the_vibrations():
    atoms, modes = cp2k.read_vibrations((DATA / 'cp2k' / 'cscl_vibrations.mol').read_text(encoding='utf-8'))
    assert [s for s, _ in atoms] == ['Cs', 'Cl'] and atoms[1][1] == pytest.approx((4.123 / 2,) * 3, abs=1e-4)
    assert [m.frequency for m in modes] == [0, 0, 0, 150.25, 150.25, 150.25]
    assert not modes[0].animatable and modes[3].animatable and modes[3].vectors[1] == (-0.881, 0.0, 0.0)


def test_the_modes_on_a_block():
    crystal = cscl()
    atoms, modes = cp2k.read_vibrations((DATA / 'cp2k' / 'cscl_vibrations.mol').read_text(encoding='utf-8'))
    block = cr.build(crystal, (2, 2, 2), True)
    rows = np.array(crystal.cell.vectors())
    mapped = cm.model_modes(modes, atoms, block, rows, np.eye(3), rows)
    v = mapped[3].vectors
    assert len(v) == len(block.atoms)
    for atom, d in zip(block.atoms, v):  # every Cs moves +x, every Cl −x — on the faces and in the corners too
        assert d == pytest.approx((0.474, 0, 0) if atom.symbol == 'Cs' else (-0.881, 0, 0))


def test_a_supercell_and_a_stretched_cell():
    # the cell computed 2 × 1 × 1 of the file, grown by 1 %: the atoms found by their fractions
    crystal = cscl()
    rows = np.array(crystal.cell.vectors())
    big = np.diag([2.0, 1.0, 1.0]) @ rows * 1.01
    atoms = [('Cs', tuple(np.array(f) @ big)) for f in ((0, 0, 0), (0.5, 0, 0))] + \
            [('Cl', tuple(np.array(f) @ big)) for f in ((0.25, 0.5, 0.5), (0.75, 0.5, 0.5))]
    mapping = crystal_field.mapping_of(crystal, big)
    assert mapping == pytest.approx(np.diag([0.5, 1, 1]))
    block = cr.build(crystal, (2, 1, 1), False)
    found = cm.partners(block.atoms, atoms, rows, mapping, big)
    assert sorted(found) == [0, 1, 2, 3]
    assert all(atoms[k][0] == atom.symbol for atom, k in zip(block.atoms, found))


def test_the_critical_points_of_cscl_on_a_cell():
    from modules.spectrum.wavefunction import crystal_aim, multiwfn

    cell, atoms = crystal_aim.geometry((DATA / 'multiwfn' / 'crystal_cscl333_geometry.molden').read_text(encoding='utf-8'))
    cps = multiwfn.parse_cps((DATA / 'multiwfn' / 'crystal_topology_cp2k-CsCl-20261112-144541__CPprop.txt')
                             .read_text(encoding='utf-8'))
    points = [(p['kind'], tuple(p['xyz']), tuple(p['elements'])) for p in crystal_aim.unique_points(cps, atoms, cell)]
    computed = np.array(cell) * crystal_aim.BOHR
    crystal = cscl()
    rows = np.array(crystal.cell.vectors())
    mapping = crystal_field.mapping_of(crystal, computed)
    placed = cm.model_points(points, rows, mapping, computed, (1, 1, 1))
    ionic = [r for kind, r, extra in placed if kind == 'bond' and sorted(extra) == ['Cl', 'Cs']]
    assert len(ionic) == 8  # Cs–Cl: halfway between Cl at the centre and the 8 Cs of the corners
    centre = rows.sum(axis=0) / 2
    for r in ionic:
        assert 0.3 * np.linalg.norm(centre) < np.linalg.norm(np.array(r) - centre) < 0.7 * np.linalg.norm(centre)
    block = cr.build(crystal, (1, 1, 1), True)
    paths = cm.bond_paths(placed, block)
    assert len(paths) >= 8 and all(p.shape == (3, 3) for p in paths)
