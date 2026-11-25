"""packing_similarity: benzoic acid with itself, in another setting, stretched, and a different packing."""

from dataclasses import replace
from pathlib import Path

import pytest

from modules.compass.chemistry import crystal as cr
from modules.compass.chemistry import crystal_setting as cs
from modules.compass.chemistry import packing_similarity as ps

EXAMPLES = Path(__file__).resolve().parents[2] / 'examples' / '10-crystals'


def benzoic():
    return cr.parse_cif((EXAMPLES / 'benzoic_acid.cif').read_text(encoding='utf-8'))


def test_the_same_crystal():
    s = ps.compare(benzoic(), benzoic())
    assert (s.matched, s.n) == (15, 15) and s.rmsd < 1e-9
    assert len(ps.cluster(benzoic())) == 15 and len(ps.cluster(benzoic())[0][0]) == 9  # C7O2 without H


def test_another_setting_is_the_same_packing():
    # P 21/n of the file and P 21/c: other axes, the molecules turned and inverted — the same packing
    crystal = benzoic()
    m = next(m for e, m, _ in cs.settings(crystal) if cs.entry_name(e) == 'P 1 21/c 1')
    s = ps.compare(crystal, cs.transform(crystal, m))
    assert s.matched == 15 and s.rmsd < 1e-9


def test_a_stretched_cell_and_another_packing():
    crystal = benzoic()
    c = crystal.cell
    stretched = replace(crystal, cell=cr.Cell(c.a * 1.04, c.b, c.c, c.alpha, c.beta, c.gamma))
    s = ps.compare(crystal, stretched)
    assert s.matched == 15 and 0.05 < s.rmsd < 0.3
    half = replace(crystal, operations=crystal.operations[:2])  # half of the molecules gone: another packing
    assert ps.compare(crystal, half).matched < 15


def test_salt_and_other_molecules():
    salt = cr.parse_cif((EXAMPLES / 'NaCl_rock_salt.cif').read_text(encoding='utf-8'))
    with pytest.raises(ValueError, match='no molecules'):
        ps.compare(salt, salt)
