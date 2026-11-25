"""Proteins: modules/compass/chemistry/protein.py and the PDB files without CONECT for standard residues.

Oracles: crambin (1CRN) and ubiquitin (1UBQ) from the Protein Data Bank (files.rcsb.org, CC0; downloaded by the user
2026-11-08) — their sequences (46 and 76 residues in one chain) and the HELIX/SHEET records written by the authors.
The simplified DSSP agrees with the records on at least 85 % of the residues and exactly on the main helices and the
first strands; the 3₁₀-helix 56–59 of ubiquitin is found as a helix.
"""

from pathlib import Path

import numpy as np
import pytest

from modules.compass.chemistry import protein as pr
from modules.compass.chemistry.formats import read_pdb

DATA = Path(__file__).parents[1] / 'data' / 'protein'


def load(name):
    text = (DATA / f'{name}.pdb').read_text(encoding='utf-8')
    return text, read_pdb(text)


def records(text, length):
    ss = ['C'] * length
    for line in text.splitlines():
        if line.startswith('HELIX'):
            first, last, kind = int(line[21:25]), int(line[33:37]), 'H'
        elif line.startswith('SHEET'):
            first, last, kind = int(line[22:26]), int(line[33:37]), 'E'
        else:
            continue
        for k in range(first, last + 1):
            ss[k - 1] = kind
    return ss


def test_standard_residues_get_their_bonds_by_distance():
    # 1CRN has CONECT only for the three S–S bridges: Compass drew 3 bonds for 327 atoms
    text, molecule = load('1crn')
    from modules.compass.chemistry.builder import connections

    assert molecule.bonds is None and len(connections(molecule)) == 337  # 46 residues, three S–S among them
    assert len(text.split('\nCONECT')) - 1 == 6


@pytest.mark.parametrize('name, length', [('1crn', 46), ('1ubq', 76)])
def test_backbone_and_secondary_structure(name, length):
    text, molecule = load(name)
    chains = pr.backbone(molecule)
    assert [len(c) for c in chains] == [length]
    ss = pr.secondary(molecule, chains)[0]
    expected = records(text, length)
    agree = sum(a == b for a, b in zip(ss, expected)) / length
    assert agree >= 0.85, (''.join(ss), ''.join(expected))
    if name == '1ubq':
        assert ss[22:34] == ['H'] * 12  # the α-helix 23–34
        assert ss[55:58] == ['H'] * 3  # the 3₁₀-helix 56–59 (class 5 in the file)
        assert ss[0:6] == ['E'] * 6
    else:
        assert ss[0:4] == ['E'] * 4 and ss[6:17] == ['H'] * 11


def test_ribbon_mesh():
    _, molecule = load('1ubq')
    chains = pr.backbone(molecule)
    ss = pr.secondary(molecule, chains)
    mesh = pr.ribbon(molecule, chains, ss)
    rings = (76 - 1) * pr.SEGMENTS + 1
    assert mesh.vertices.shape == (rings * pr.PROFILE, 3) and mesh.colors.shape == mesh.vertices.shape
    assert mesh.triangles.max() < len(mesh.vertices) and len(mesh.triangles) == (rings - 1) * pr.PROFILE * 2
    assert np.allclose(np.linalg.norm(mesh.normals, axis=1), 1.0)
    assert {tuple(c) for c in mesh.colors} == set(pr.COLOURS.values())
    centre = np.array([a.position for a in molecule.atoms]).mean(axis=0)
    assert np.linalg.norm(mesh.vertices.mean(axis=0) - centre) < 6.0  # the ribbon lies on the protein


def test_peptide_side_chains_are_not_backbone():
    # the amide of Asn and the amine of Lys do not start residues of their own
    from modules.compass.chemistry.formats import from_smiles

    made = from_smiles('NCC(=O)NC(C)C(=O)NC(CC(N)=O)C(=O)NC(CCCCN)C(=O)O')
    molecule = made[0] if isinstance(made, tuple) else made
    chains = pr.backbone(molecule)
    assert [len(c) for c in chains] == [4] and len(pr.protein_atoms(molecule, chains)) == len(molecule.atoms)
