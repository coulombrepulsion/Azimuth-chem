"""RDKit's UFF numbers for the structures of tests/data/uff/structures.json.

§1 PURPOSE
    The oracle of modules/compass/chemistry/uff.py: the same atoms, bonds (Kekulé orders) and positions given to RDKit,
    which perceives the aromaticity and the types itself; its energy at the given positions, the rest length and force
    constant of every bond, and the energy after its own minimization go to tests/data/uff/rdkit_uff.json, read by
    tests/compass/test_uff.py::test_energies_as_rdkit.
§2 USE
    Run with a Python that has RDKit (the one of «Сделать 3D (RDKit)»), from the folder of Azimuth:
        <python with RDKit> tools/uff_reference.py
§3 NOTES
    Only RDKit and the standard library are imported; the Azimuth code is not.
"""

import json
import sys
from pathlib import Path

from rdkit import Chem, rdBase
from rdkit.Chem import ChemicalForceFields
from rdkit.Geometry import Point3D

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'tests' / 'data' / 'uff' / 'structures.json'
TARGET = ROOT / 'tests' / 'data' / 'uff' / 'rdkit_uff.json'
ORDER = {1.0: Chem.BondType.SINGLE, 2.0: Chem.BondType.DOUBLE, 3.0: Chem.BondType.TRIPLE}


def molecule(record):
    rw = Chem.RWMol()
    for symbol in record['symbols']:
        atom = Chem.Atom(symbol)
        atom.SetNoImplicit(True)
        rw.AddAtom(atom)
    for i, j, order in record['bonds']:
        rw.AddBond(int(i), int(j), ORDER[float(order)])
    mol = rw.GetMol()
    Chem.SanitizeMol(mol)
    conformer = Chem.Conformer(mol.GetNumAtoms())
    for k, (x, y, z) in enumerate(record['positions']):
        conformer.SetAtomPosition(k, Point3D(x, y, z))
    mol.AddConformer(conformer, assignId=True)
    return mol


def main():
    data = json.loads(SOURCE.read_text(encoding='utf-8'))
    out = []
    for record in data['molecules']:
        mol = molecule(record)
        if not ChemicalForceFields.UFFHasAllMoleculeParams(mol):
            print(f'  {record["name"]}: у RDKit нет параметров UFF', flush=True)
            continue
        field = ChemicalForceFields.UFFGetMoleculeForceField(mol)
        energy = field.CalcEnergy()
        bonds = []
        for i, j, _ in record['bonds']:
            kb, r0 = ChemicalForceFields.GetUFFBondStretchParams(mol, int(i), int(j))
            bonds.append([int(i), int(j), kb, r0])
        field.Minimize(maxIts=5000)
        entry = dict(record, energy=energy, minimized=field.CalcEnergy(), bond_params=bonds,
                     aromatic=[a.GetIsAromatic() for a in mol.GetAtoms()],
                     hybridization=[str(a.GetHybridization()) for a in mol.GetAtoms()])
        out.append(entry)
        print(f'  {record["name"]}: E = {energy:.4f}, после минимизации {entry["minimized"]:.4f} ккал/моль', flush=True)
    TARGET.write_text(json.dumps({'rdkit': rdBase.rdkitVersion, 'molecules': out}, indent=1, ensure_ascii=False) + '\n',
                      encoding='utf-8')
    print(f'\n{TARGET}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
