"""Peptides from a sequence: modules/compass/chemistry/peptide.py.

Oracles: the molecular formulas of the peptides (residues minus one water per peptide bond); the chirality rule of
peptide.py checked on crambin from the PDB (tests/data/protein/1crn.pdb: all 42 non-glycine Cα, 6 Thr and 5 Ile Cβ);
φ, ψ, ω measured back on the built structure; the i → i + 4 hydrogen bonds of an α-helix found by protein.secondary.
"""

from collections import Counter
from pathlib import Path

import numpy as np
import pytest

from modules.compass.chemistry import peptide, protein


def formula(molecule):
    return dict(Counter(a.symbol for a in molecule.atoms))


def residues_of(text):
    found = {}
    for line in text.splitlines():
        if line.startswith('ATOM'):
            found.setdefault((int(line[22:26]), line[17:20]), {})[line[12:16].strip()] = np.array(
                [float(line[30:38]), float(line[38:46]), float(line[46:54])])
    return found


def test_the_rule_of_chirality_on_crambin():
    text = (Path(__file__).parents[1] / 'data' / 'protein' / '1crn.pdb').read_text(encoding='utf-8')
    signs = []
    for (_, name), at in residues_of(text).items():
        names = list(at)
        x = np.array([at[k] for k in names])
        i = {k: n for n, k in enumerate(names)}
        if name != 'GLY':
            signs.append(peptide.chirality(x, i['CA'], i['C'], i['CB'], i['N']))
        if name == 'THR':
            signs.append(peptide.chirality(x, i['CB'], i['OG1'], i['CG2'], i['CA']))
        if name == 'ILE':
            signs.append(peptide.chirality(x, i['CB'], i['CG1'], i['CG2'], i['CA']))
    assert len(signs) == 42 + 6 + 5 and all(s < 0 for s in signs)


def test_formulas_and_errors():
    assert formula(peptide.build('GA', 'extended', relax=False)) == {'N': 2, 'C': 5, 'O': 3, 'H': 10}
    tri = peptide.build('KWP', 'extended', relax=False)  # Lys C6H14N2O2 + Trp C11H12N2O2 + Pro C5H9NO2 − 2 H2O
    assert formula(tri) == {'C': 22, 'H': 31, 'N': 5, 'O': 4}
    for bad, words in (('A', 'от 2'), ('AXB', 'Неизвестные'), ('A' * 31, 'от 2')):
        with pytest.raises(ValueError, match=words):
            peptide.build(bad)


@pytest.mark.parametrize('conformation', ['helix', 'strand', 'extended'])
def test_chirality_and_backbone_angles(conformation):
    sequence = 'ATIVSG'
    molecule = peptide.build(sequence, conformation)
    x = np.array([a.position for a in molecule.atoms])
    chain = protein.backbone(molecule)[0]
    near = protein._neighbours(molecule)
    symbols = [a.symbol for a in molecule.atoms]
    for letter, r in zip(sequence, chain):
        if letter == 'G':
            continue
        cb = next(k for k in near[r.ca] if k not in (r.n, r.c) and symbols[k] != 'H')
        assert peptide.chirality(x, r.ca, r.c, cb, r.n) < 0, letter  # L
        if letter in 'TI':
            rest = [k for k in near[cb] if k != r.ca and symbols[k] != 'H']
            first = next(k for k in rest if symbols[k] == 'O') if letter == 'T' else next(
                k for k in rest if any(symbols[m] == 'C' and m != cb for m in near[k]))
            second = next(k for k in rest if k != first)
            assert peptide.chirality(x, cb, first, second, r.ca) < 0, letter
    phi, psi, _ = peptide.CONFORMATIONS[conformation]

    def angle(value, target):
        return abs((value - target + 180.0) % 360.0 - 180.0)

    for k in range(1, len(chain) - 1):
        a, b, c = chain[k - 1], chain[k], chain[k + 1]
        assert angle(peptide._dihedral(x, a.c, b.n, b.ca, b.c), phi) < 0.5
        assert angle(peptide._dihedral(x, b.n, b.ca, b.c, c.n), psi) < 0.5
        assert angle(peptide._dihedral(x, a.ca, a.c, b.n, b.ca), 180.0) < 0.5


def test_alanine_helix_is_a_helix():
    molecule = peptide.build('A' * 12, 'helix')
    chains = protein.backbone(molecule)
    ss = protein.secondary(molecule, chains)[0]
    assert ss[1:9].count('H') >= 7  # the i → i + 4 C=O···H–N bonds of the α-helix
    assert protein.secondary(peptide.build('A' * 12, 'extended'), protein.backbone(
        peptide.build('A' * 12, 'extended')))[0].count('H') == 0


def test_no_atoms_on_top_of_each_other():
    # the side chains turned to the staggered position with the fewest clashes, the C-terminal COOH turned too
    for sequence, conformation in (('MKTAYIAKQR', 'helix'), ('ACDEFGHIKLMNPQRSTVWY', 'strand'), ('GP', 'extended')):
        molecule = peptide.build(sequence, conformation)
        x = np.array([a.position for a in molecule.atoms])
        near = protein._neighbours(molecule)
        close = {(i, k) for i in range(len(x)) for j in near[i] for k in near[j] | {j}}
        d = np.linalg.norm(x[:, None] - x[None], axis=2)
        nearest = min(d[i, j] for i in range(len(x)) for j in range(i + 1, len(x)) if (i, j) not in close)
        assert nearest > 1.4, (sequence, nearest)
