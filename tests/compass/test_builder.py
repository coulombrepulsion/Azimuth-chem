from math import dist
import json
import pytest
from azimuth.core import Molecule, Calculation, project_text, read_project, orca_input, read_xyz
from modules.compass.chemistry.builder import *

EMPTY = Molecule('Новая молекула', (), ())


def test_free_atom_is_placed_exactly():
    mol = place_atom(EMPTY, 'C', (1.2, -2.5, 3.1))
    assert mol.atoms[0].position == (1.2, -2.5, 3.1)
    assert mol.bonds == ()


def test_attach_atom_has_requested_length_and_bond():
    mol = place_atom(EMPTY, 'C', (0, 0, 0))
    mol = place_atom(mol, 'O', (50, 50, 50), anchor=0, order=2, length=1.22)
    assert dist(mol.atoms[0].position, mol.atoms[1].position) == pytest.approx(1.22)
    assert mol.bonds == ((0, 1, 2),)


@pytest.mark.parametrize('name', FRAGMENTS)
def test_fragment_internal_geometry_survives_rotation(name):
    mol = place_atom(EMPTY, 'C', (0, 0, 0))
    mol = place_atom(mol, 'H', (0, 0, 0), anchor=0)
    built = place_fragment(mol, name, (0, 0, 0), anchor=0, length=1.5)
    assert len(built.atoms) == 2 + len(FRAGMENTS[name])
    assert (0, 2, 1) in built.bonds
    assert dist(built.atoms[0].position, built.atoms[2].position) == pytest.approx(1.5)
    template = FRAGMENTS[name]
    for i in range(len(template)):
        for j in range(i):
            assert dist(built.atoms[i + 2].position, built.atoms[j + 2].position) == pytest.approx(
                dist(template[i][1:], template[j][1:])
            )
    read_xyz(built.xyz())


def test_delete_reindexes_edges():
    mol = place_fragment(EMPTY, 'Метил · —CH₃', (0, 0, 0))
    result = delete_atoms(mol, [1])
    assert len(result.atoms) == 3 and result.bonds == ((0, 1, 1), (0, 2, 1))
    assert delete_atoms(result, range(3)) == EMPTY


def test_bond_cycle_and_break_stay_broken():
    mol = place_atom(place_atom(EMPTY, 'C', (0, 0, 0)), 'O', (1.22, 0, 0))
    for order in (1, 2, 3):
        mol = set_bond(mol, 1, 0, order)
        assert mol.bonds == ((0, 1, order),)
    assert connections(set_bond(mol, 0, 1, 0)) == ()


def test_moving_keeps_explicit_connectivity():
    mol = place_atom(place_atom(EMPTY, 'C', (0, 0, 0)), 'H', (0, 0, 0), anchor=0)
    moved = move_atom(mol, 1, (4, 2, 0))
    assert moved.bonds == mol.bonds and moved.atoms[1].position == (4, 2, 0)


def test_overlap_rejected():
    mol = place_atom(EMPTY, 'C', (0, 0, 0))
    with pytest.raises(ValueError):
        place_atom(mol, 'H', (0, 0, 0))


def test_project_roundtrip_preserves_bonds_and_draft_spin():
    mol = place_fragment(EMPTY, 'Метил · —CH₃', (0, 0, 0))
    # Draft electron parity can be incomplete; export remains blocked.
    restored, calc = read_project(project_text(mol, Calculation()))
    assert restored == mol
    with pytest.raises(ValueError):
        orca_input(restored, calc)


def test_empty_project_roundtrip_and_export_block():
    assert read_project(project_text(EMPTY, Calculation()))[0] == EMPTY
    with pytest.raises(ValueError):
        orca_input(EMPTY, Calculation())


@pytest.mark.parametrize(
    'edges', [[[0, 99, 1]], [[0, 0, 1]], [[0, 1, 7]], [[0, 1, 1], [1, 0, 2]], [[0, 1, '1']], 'broken']
)
def test_bad_project_bonds(edges):
    mol = place_atom(place_atom(EMPTY, 'C', (0, 0, 0)), 'O', (1.22, 0, 0))
    data = json.loads(project_text(mol, Calculation()))
    data['bonds'] = edges
    with pytest.raises(ValueError):
        read_project(json.dumps(data))


def test_version_one_project_still_opens():
    data = {'format': 'qcc-studio', 'version': 1, 'xyz': '1\nHe\nHe 0 0 0', 'calculation': {}}
    assert read_project(json.dumps(data))[0].atoms[0].symbol == 'He'
