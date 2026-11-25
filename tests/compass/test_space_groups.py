"""The space groups from their symbols (modules/compass/chemistry/space_groups.py).

Oracles, independent of the tested code:
  * the orders of the groups (International Tables vol. A): P 21/c 4, C 2/c 8, P b c a 8, R -3 18 on hexagonal
    axes and 6 on rhombohedral, F m -3 m and F d -3 m 192, I 41/a 16, P 63/m m c 24;
  * every one of the 530 settings: the point group found by crystal_symmetry.analyse from the operations allows the
    number of the table and is the point group spglib wrote for it, in both notations (two codes: spglib wrote the
    table, ours reads the operations; the Schoenflies symbols of crystal_symmetry.SCHOENFLIES are checked so);
  * the operations of rock salt by its symbol are those listed in examples/10-crystals/NaCl_rock_salt.cif;
  * diamond Si at 1/8 1/8 1/8 in origin choice 2 and at 0 0 0 in origin choice 1: 8 atoms in the cell both ways.
"""

import re
from pathlib import Path

from modules.compass.chemistry import crystal as cr
from modules.compass.chemistry import crystal_symmetry as cs
from modules.compass.chemistry import space_groups as sg

ROOT = Path(__file__).resolve().parents[2]


def test_symbols_and_orders():
    cases = {'P 21/c': (14, 4), 'P21/n': (14, 4), 'P 1 21/n 1': (14, 4), 'C 2/c': (15, 8), 'P b c a': (61, 8),
             'R -3 :H': (148, 18), 'R -3': (148, 18), 'R -3 :R': (148, 6), 'F m -3 m': (225, 192),
             'Fd-3m': (227, 192), 'I 41/a': (88, 16), 'P63/mmc': (194, 24), 'P 2_1 2_1 2_1': (19, 4)}
    for symbol, (number, order) in cases.items():
        g = sg.find(symbol)
        assert g is not None and g['number'] == number and len(sg.operations(g)) == order, symbol
    assert sg.find('P 21/n')['choice'] == 'b2' and sg.find('F d -3 m')['choice'] == '2'
    assert sg.find('F d -3 m :1')['choice'] == '1' and sg.find(hall_symbol='-P 2ybc')['number'] == 14
    assert sg.find(number=166)['choice'] == 'H' and sg.find('no such group') is None


def test_all_settings_agree_with_their_point_groups():
    groups = sg._table()[0]
    assert len(groups) == 530 and len({g['number'] for g in groups}) == 230
    for g in groups:
        ops = tuple(cr.operation(t) for t in sg.operations(g))
        hexagonal = 143 <= g['number'] <= 194 and g['choice'] != 'R'
        cell = (cr.Cell(7, 7, 9, 90, 90, 120) if hexagonal else
                cr.Cell(7, 7, 7, 80, 80, 80) if g['choice'] == 'R' else cr.Cell(7, 8, 9, 90, 100, 90))
        c = cr.Crystal('t', cell, (cr.Site('C1', 'C', 0.11, 0.17, 0.23),), ops, g['full'], (), g['number'], 'C', 0)
        s = cs.analyse(c)
        assert s.notes == () and s.numbers[0] <= g['number'] <= s.numbers[1], g['hall']
        assert s.point_group == g['point_group'] and cs.SCHOENFLIES[s.point_group] == g['schoenflies'], g['hall']


def test_the_closure_in_integers_is_the_closure_in_fractions():
    # crystal_symmetry._missing_products counts the products of the operations in integers (the shifts in
    # 1/D) — the oracle is the count in Fractions (_compose), for settings of every kind, closed and with an
    # operation left out; a rotation with a fraction takes the way of Fractions
    from fractions import Fraction

    for g in sg._table()[0][::15]:
        ops = [cs._key(cr.operation(t)) for t in sg.operations(g)]
        for variant in (ops, ops[:-1]):
            keys = set(variant)
            slow = sum(1 for a in variant for b in variant if cs._compose(a, b) not in keys)
            assert cs._missing_products(variant, keys) == slow, g['hall']
    odd = [(((Fraction(1, 2), 0, 0), (0, 1, 0), (0, 0, 1)), (0, 0, 0)), (cs.I3, (0, 0, 0))]
    assert cs._missing_products(odd, set(odd)) == sum(1 for a in odd for b in odd if cs._compose(a, b) not in set(odd))


def _without_operations(text):
    return re.sub(r"loop_\s*\n_space_group_symop_operation_xyz\s*\n(\s*'[^']*'\s*\n)+", '', text)


def test_rock_salt_by_its_symbol():
    text = (ROOT / 'examples' / '10-crystals' / 'NaCl_rock_salt.cif').read_text(encoding='utf-8')
    listed = cr.parse_cif(text)
    bare = cr.parse_cif(_without_operations(text))
    assert len(bare.operations) == 192 and set(bare.operations) == set(listed.operations)
    assert any('F 4/m -3 2/m' in note for note in bare.notes)
    only_number = _without_operations(text).replace("_symmetry_space_group_name_H-M 'F m -3 m'",
                                                    '_space_group_IT_number 225')
    c = cr.parse_cif(only_number)
    assert set(c.operations) == set(listed.operations) and c.space_group.startswith('F 4/m')


def test_origin_choices_of_diamond():
    head = 'data_Si\n_cell_length_a 5.43\n_cell_length_b 5.43\n_cell_length_c 5.43\n'
    atoms = 'loop_\n_atom_site_label\n_atom_site_fract_x\n_atom_site_fract_y\n_atom_site_fract_z\nSi1 {0} {0} {0}\n'
    two = cr.parse_cif(head + "_symmetry_space_group_name_H-M 'F d -3 m'\n" + atoms.format(0.125))
    one = cr.parse_cif(head + "_symmetry_space_group_name_H-M 'F d -3 m :1'\n" + atoms.format(0))
    assert len(cr.unit_cell(two)) == 8 and len(cr.unit_cell(one)) == 8
