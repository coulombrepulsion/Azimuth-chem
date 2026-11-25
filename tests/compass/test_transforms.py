from math import pi, dist
import pytest
from azimuth.core import Molecule, Atom
from modules.compass.chemistry.transforms import bond_side, rotate_atoms, stretch_bond


@pytest.fixture
def mol():
    return Molecule(
        'chain',
        (Atom('C', 0, 0, 0), Atom('C', 1.5, 0, 0), Atom('H', 1.5, 1, 0), Atom('H', 0, -1, 0)),
        ((0, 1, 1), (1, 2, 1), (0, 3, 1)),
    )


def test_fragment_bond_cut(mol):
    assert bond_side(mol, 0, 1) == [1, 2]
    assert bond_side(mol, 1, 0) == [0, 3]
    with pytest.raises(ValueError):
        bond_side(mol, 2, 3)


def test_stretch_keeps_fragment_rigid(mol):
    result = stretch_bond(mol, 0, 1, 0.05)
    assert result.atoms[0] == mol.atoms[0] and result.atoms[3] == mol.atoms[3]
    assert result.atoms[1].x == pytest.approx(1.55)
    assert dist(result.atoms[1].position, result.atoms[2].position) == pytest.approx(1)
    assert result.bonds == mol.bonds


def test_torsion_keeps_axis_and_bond_lengths(mol):
    result = rotate_atoms(mol, bond_side(mol, 0, 1), (0, 0, 0), (1, 0, 0), pi / 2)
    assert result.atoms[2].position == pytest.approx((1.5, 0, 1))
    assert result.atoms[0] == mol.atoms[0]
    assert result.atoms[1].position == pytest.approx(mol.atoms[1].position)
    assert result.atoms[3] == mol.atoms[3]


def test_cycle_rejected():
    mol = Molecule(
        'ring', (Atom('C', 0, 0, 0), Atom('C', 1, 0, 0), Atom('C', 0, 1, 0)), ((0, 1, 1), (1, 2, 1), (2, 0, 1))
    )
    with pytest.raises(ValueError, match='цикл'):
        stretch_bond(mol, 0, 1, 0.05)


def test_a_press_turns_the_group_of_the_atom_about_its_pivot():
    # propane — a methyl or its hydrogen pressed turns the methyl about C2
    from azimuth.core import Atom, Molecule
    from modules.compass.chemistry.transforms import angle_fragment

    atoms = [Atom('C', 0.0, 0.0, 0.0), Atom('C', 1.53, 0.0, 0.0), Atom('C', 2.04, 1.44, 0.0)]
    bonds = [(0, 1, 1), (1, 2, 1)]
    for heavy, (x, y) in ((0, (-0.4, -0.9)), (0, (-0.4, 0.5)), (2, (3.1, 1.5))):
        atoms.append(Atom('H', x, y, 0.3))
        bonds.append((heavy, len(atoms) - 1, 1))
    propane = Molecule('propane', tuple(atoms), tuple(bonds))
    assert angle_fragment(propane, 0) == (1, [0, 3, 4])
    assert angle_fragment(propane, 3) == (1, [0, 3, 4])  # its hydrogen: the same methyl
    assert angle_fragment(propane, 5) == (1, [2, 5])
    water = Molecule('water', (Atom('O', 0, 0, 0), Atom('H', 0.96, 0, 0), Atom('H', -0.24, 0.93, 0)), ((0, 1, 1), (0, 2, 1)))
    assert angle_fragment(water, 1) is None  # a hydrogen alone, as before
