"""The measured values of simple solids next to a calculation of a crystal (modules/compass/chemistry/measured_solids.py).

Oracles: the numbers of Csonka et al., PRB 79, 155107 (2009), Tables II and V, and Tran, Blaha, PRL 102, 226401 (2009),
Table I, copied into the file (spot-checked here: Si 5.416 / 5.466 Å, 99.2 / 89.2 GPa, 1.17 eV; MgO 4.184 Å, 7.83 eV);
the crystals — the CIF files of examples/10-crystals.
"""

from pathlib import Path

import pytest

from modules.compass.chemistry import crystal as cr, measured_solids as ms

CRYSTALS = Path(__file__).resolve().parents[2] / 'examples' / '10-crystals'


def _read(name):
    return cr.parse_cif((CRYSTALS / name).read_text(encoding='utf-8'))


def test_the_table():
    found = ms.solids()
    assert len(found) == 30 and len({s['formula'] for s in found}) == 30
    si = next(s for s in found if s['formula'] == 'Si')
    assert (si['a_exp'], si['a_pbe'], si['b_exp'], si['b_pbe'], si['gap_exp'], si['space_group']) == (
        5.416, 5.466, 99.2, 89.2, 1.17, 227)
    mgo = next(s for s in found if s['formula'] == 'MgO')
    assert (mgo['a_exp'], mgo['gap_exp'], mgo['space_group']) == (4.184, 7.83, 225)
    for s in found:  # PBE: the lattice of the literature within 3 % of experiment, the modulus smaller or near
        if s['a_exp'] is not None:
            assert abs(s['a_pbe'] - s['a_exp']) / s['a_exp'] < 0.03 and s['b_pbe'] <= s['b_exp'] * 1.06, s['formula']


def test_a_crystal_is_told_by_its_group_and_formula():
    assert ms.identify(_read('Si_diamond.cif'))['formula'] == 'Si'  # _space_group_IT_number 227
    assert ms.identify(_read('NaCl_rock_salt.cif'))['formula'] == 'NaCl'  # only «F m -3 m»: the number found
    assert ms.identify(_read('CsCl.cif')) is None  # Pm-3m: not the rock salt
    assert ms.identify(_read('benzoic_acid.cif')) is None and ms.identify(None) is None
    assert ms.identify(cr.supercell(_read('Si_diamond.cif'), (2, 1, 1))) is None  # P1 of the supercell: not told


def test_the_lines_of_the_panel():
    si = ms.identify(_read('Si_diamond.cif'))
    line = ms.lattice_line(si, 5.469)
    assert '5.416' in line and '5.466' in line and '+1.0 %' in line and '+0.1 %' in line
    assert ms.lattice_line(si) .startswith('Опыт: a = 5.416 Å')
    assert '99.2' in ms.bulk_line(si, 88.8) and '88.8' in ms.bulk_line(si, 88.8)
    assert '1.17' in ms.gap_line(si, 0.574) and '0.57' in ms.gap_line(si, 0.574)
    nacl = ms.identify(_read('NaCl_rock_salt.cif'))
    assert ms.gap_line(nacl) == ''  # no gap of NaCl in Tran, Blaha
    assert ms.lattice_line(None) == '' == ms.bulk_line(None) == ms.gap_line(None)
    assert pytest.approx(ms._percent(5.469, 5.416), abs=0.01) == 0.98
