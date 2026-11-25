"""UFF: modules/compass/chemistry/uff.py.

Oracles: the numbers of RDKit's own unit tests of UFF (Code/ForceField/UFF/testUFFForceField.cpp — rest lengths and
force constants, among them the amide bond of the UFF paper; Code/GraphMol/ForceFieldHelpers/UFF/testUFFHelpers.cpp —
the atom types of seven molecules), the ethane barrier of the formula (V of C_3 = 2.119 kcal/mol over nine torsions),
finite differences for the gradient, and — when tools/uff_reference.py has been run on a computer with RDKit —
RDKit's energies of the same structures (tests/data/uff/rdkit_uff.json).
"""

import json
from dataclasses import replace
from math import radians
from pathlib import Path

import numpy as np
import pytest

from azimuth.core import Atom, Molecule
from modules.compass.chemistry import uff
from modules.compass.chemistry.formats import from_smiles
from modules.compass.chemistry.uff_params import PARAMS

REFERENCE = Path(__file__).parents[1] / 'data' / 'uff' / 'rdkit_uff.json'


def smiles(text):
    made = from_smiles(text)
    return made[0] if isinstance(made, tuple) else made


def heavy_labels(molecule):
    labels = uff.types(molecule)[0]
    return [label for label, atom in zip(labels, molecule.atoms) if atom.symbol != 'H']


def test_rest_lengths_and_force_constants_of_rdkit_tests():
    c3, c2, n3, cr, nr = (PARAMS[k] for k in ('C_3', 'C_2', 'N_3', 'C_R', 'N_R'))
    cases = ((1.0, c3, c3, 1.514, 1e-4, 699.5918, 1e-4), (2.0, c2, c2, 1.32883, 1e-5, 1034.69, 1e-2),
             (1.0, c3, n3, 1.451071, 1e-5, 1057.27, 1e-2), (1.41, cr, nr, 1.357, 1e-3, 1293.0, 1.0))
    for order, a, b, r0, tol_r, k, tol_k in cases:
        rest = uff._rest_length(order, a, b)
        assert rest == pytest.approx(r0, abs=tol_r)
        assert 2 * uff.G * a[5] * b[5] / rest ** 3 == pytest.approx(k, abs=tol_k)
    # the amide angle C_R–N_R–C_3 of the paper (RDKit: 211.0, «paper has 105.5» — the ½ is in the energy)
    assert uff._angle_constant(radians(120.0), 1.41, 1.0, cr, nr, c3) == pytest.approx(211.0, abs=0.1)


def test_bond_stretch_energy_and_gradient_of_rdkit_test():
    # ethane's C_3–C_3 bond alone, stretched to 1.814 Å as in testUFF2 (E = 31.4816, ∂E/∂x = ∓209.8775)
    ethane = smiles('CC')
    f = uff.build(ethane)
    cc = [n for n, (i, j) in enumerate(f.bonds) if {ethane.atoms[i].symbol, ethane.atoms[j].symbol} == {'C'}]
    alone = replace(f, bonds=f.bonds[cc], bond_k=f.bond_k[cc], bond_r0=f.bond_r0[cc], angles=f.angles[:0],
                    torsions=f.torsions[:0], inversions=f.inversions[:0], pairs=f.pairs[:0])
    x = np.zeros((len(ethane.atoms), 3))
    i, j = f.bonds[cc[0]]
    x[j, 0] = 1.814
    _, g, parts = uff.energy(alone, x)
    assert f.labels[i] == f.labels[j] == 'C_3'
    assert parts['bond'] == pytest.approx(31.4816, abs=1e-4)
    assert g[i, 0] == pytest.approx(-209.8775, abs=1e-4) and g[j, 0] == pytest.approx(209.8775, abs=1e-4)


@pytest.mark.parametrize('text, expected', [
    ('[SiH3]CC(=O)NC', ['Si3', 'C_3', 'C_R', 'O_R', 'N_R', 'C_3']),
    ('CC(=O)C', ['C_3', 'C_2', 'O_2', 'C_3']),
    ('C(=O)S', ['C_2', 'O_2', 'S_3+2']),
    ('SCS(=O)S(=O)(=O)O', ['S_3+2', 'C_3', 'S_3+4', 'O_2', 'S_3+6', 'O_2', 'O_2', 'O_3']),
    ('PCP(O)CP(=O)(=O)', ['P_3+3', 'C_3', 'P_3+3', 'O_3', 'C_3', 'P_3+5', 'O_2', 'O_2']),
    ('C(F)(Cl)(Br)I', ['C_3', 'F_', 'Cl', 'Br', 'I_']),
])
def test_atom_types_of_rdkit_tests(text, expected):
    # testUFFHelpers.cpp names the atoms it checks; the others (O of the sulfonic acid, of P=O) follow the same rules
    labels = heavy_labels(smiles(text))
    assert labels == expected


def test_aromatic_and_conjugated_types():
    assert heavy_labels(smiles('c1ccccc1O')) == ['C_R'] * 6 + ['O_R']  # phenol: the O is conjugated
    assert heavy_labels(smiles('c1cc[nH]c1')) == ['C_R'] * 3 + ['N_R', 'C_R']  # pyrrole (0.106.0 five-rings)
    assert heavy_labels(smiles('c1ccsc1')) == ['C_R'] * 3 + ['S_R', 'C_R']
    assert heavy_labels(smiles('N#CC')) == ['N_1', 'C_1', 'C_3']
    assert heavy_labels(smiles('C=CC=C')) == ['C_R'] * 4  # butadiene: conjugated
    assert heavy_labels(smiles('C=C')) == ['C_2'] * 2


@pytest.mark.parametrize('text', ['CCO', 'CC(=O)N', 'c1ccccc1', 'c1ccsc1', 'CS(C)=O', 'C1CC1', 'C1=CCC1'])
def test_gradient_is_the_derivative_of_the_energy(text):
    molecule = smiles(text)
    f = uff.build(molecule)
    x = np.array([a.position for a in molecule.atoms]) + np.random.default_rng(3).normal(0, 0.05, (len(molecule.atoms), 3))
    _, g, _ = uff.energy(f, x)
    numeric = np.zeros_like(x)
    h = 1e-6
    for i in range(len(x)):
        for k in range(3):
            up, down = x.copy(), x.copy()
            up[i, k] += h
            down[i, k] -= h
            numeric[i, k] = (uff.energy(f, up)[0] - uff.energy(f, down)[0]) / (2 * h)
    assert np.max(np.abs(numeric - g)) < 1e-5


def test_ethane_barrier_is_v_of_c3():
    molecule = uff.optimize(smiles('CC')).molecule
    f = uff.build(molecule)
    x = np.array([a.position for a in molecule.atoms])
    staggered = uff.energy(f, x)[2]['torsion']
    carbon = [i for i, a in enumerate(molecule.atoms) if a.symbol == 'C']
    axis = x[carbon[1]] - x[carbon[0]]
    axis /= np.linalg.norm(axis)
    near = {i for i, a in enumerate(molecule.atoms) if a.symbol == 'H' and np.linalg.norm(x[i] - x[carbon[1]]) < 1.3}
    turn = radians(60.0)
    k = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    rotation = np.eye(3) + np.sin(turn) * k + (1 - np.cos(turn)) * k @ k
    eclipsed = x.copy()
    for i in near:
        eclipsed[i] = x[carbon[1]] + rotation @ (x[i] - x[carbon[1]])
    assert staggered == pytest.approx(0.0, abs=1e-4)
    assert uff.energy(f, eclipsed)[2]['torsion'] == pytest.approx(PARAMS['C_3'][6], abs=1e-3)  # 2.119 kcal/mol


def test_optimization_lowers_the_energy_and_reaches_a_minimum():
    result = uff.optimize(smiles('CCCC'))
    assert result.energy < result.start
    f = uff.build(result.molecule)
    _, g, _ = uff.energy(f, np.array([a.position for a in result.molecule.atoms]))
    assert np.max(np.abs(g)) < 1e-2
    assert set(result.parts) == {'bond', 'angle', 'torsion', 'inversion', 'vdw'}
    # the frozen atoms stay
    start = smiles('CCO')
    moved = uff.optimize(start, movable=[2, 8])
    for i in range(len(start.atoms)):
        if i not in (2, 8):
            assert moved.molecule.atoms[i].position == pytest.approx(start.atoms[i].position)


def test_dummy_atoms_and_unknown_elements_are_refused():
    with pytest.raises(ValueError, match='фиктивные'):
        uff.optimize(Molecule('x', (Atom('C', 0, 0, 0), Atom('X', 1, 0, 0))))


@pytest.mark.skipif(not REFERENCE.exists(), reason='tests/data/uff/rdkit_uff.json: tools/uff_reference.py with RDKit')
def test_energies_as_rdkit():
    # the structures of tests/data/uff/structures.json (shaken off the minimum) given to RDKit: its energy at the same
    # positions, the r0 and k of every bond, the energy after its minimization
    data = json.loads(REFERENCE.read_text(encoding='utf-8'))
    assert len(data['molecules']) >= 15
    for record in data['molecules']:
        atoms = tuple(Atom(s, *p) for s, p in zip(record['symbols'], record['positions']))
        molecule = Molecule(record['name'], atoms, tuple((i, j, int(o)) for i, j, o in record['bonds']))
        f = uff.build(molecule)
        rest = {(int(i), int(j)): (k, r) for (i, j), k, r in zip(f.bonds, f.bond_k, f.bond_r0)}
        for i, j, kb, r0 in record['bond_params']:
            k, r = rest[(min(i, j), max(i, j))]
            assert (k, r) == (pytest.approx(kb, rel=1e-6), pytest.approx(r0, abs=1e-6)), (record['name'], i, j)
        e, _, _ = uff.energy(f, np.array(record['positions']))
        assert e == pytest.approx(record['energy'], abs=1e-4 * max(1.0, abs(record['energy']))), record['name']
        assert uff.optimize(molecule).energy == pytest.approx(record['minimized'], abs=0.05), record['name']


def test_tidy_while_building_with_uff():
    # «Выравнивать по UFF» — the new atoms moved by UFF, the rest stays where it was
    from modules.compass.chemistry.cleanup import tidy_new

    start = smiles('CCO')
    moved = list(start.atoms)
    moved[2] = Atom('O', moved[2].x + 0.4, moved[2].y - 0.3, moved[2].z + 0.2)  # the «new» O placed roughly
    rough = Molecule(start.title, tuple(moved), start.bonds)
    tidied = tidy_new(rough, [2], field='uff')
    assert tidied.atoms[0].position == pytest.approx(rough.atoms[0].position)
    f = uff.build(rough)
    assert uff.energy(f, [a.position for a in tidied.atoms])[0] < uff.energy(f, [a.position for a in rough.atoms])[0]
