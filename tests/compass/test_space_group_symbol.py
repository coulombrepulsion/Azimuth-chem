"""The Hermann–Mauguin symbol read part by part and the Bravais lattice (space_group_symbol.py).

Oracles — International Tables A, Table 2.1.3.1 (the directions of the positions) and the textbook readings, written
out here by hand:
  * P2₁/c (= P 1 2₁/c 1): a 2₁ screw axis along b with a c-glide perpendicular to b; primitive monoclinic mP;
  * Pnma: an n-glide ⊥ a, a mirror ⊥ b, an a-glide ⊥ c; oP;
  * Fm-3m (NaCl): mirrors ⊥ ⟨100⟩, −3 along ⟨111⟩, mirrors ⊥ ⟨110⟩; cF;
  * P6₃/mmc: a 6₃ screw along [001] (60° and half the period) with a mirror ⊥ [001]; hP;
  * I4₁/amd: 4₁ along [001] — 90° and a quarter of the period; d-glide ⊥ ⟨110⟩; tI;
  * C2/c is the base-centred mC, an A-centred orthorhombic cell is oC, R-3c is hR;
  * the nodes of one cell: P — 8 corners, I — 9, C — 10, F — 14, R (hexagonal axes) — 8 + 2 inside.
"""

import pytest

from modules.compass.chemistry import space_group_symbol as sg


def test_the_symbol_parsed_short_and_full():
    assert sg.parse('P21/c') == ('P', ['21/c'])
    assert sg.parse('P 1 21/c 1') == ('P', ['1', '21/c', '1'])
    assert sg.parse('Fm-3m') == ('F', ['m', '-3', 'm'])
    assert sg.parse('P63/mmc') == ('P', ['63/m', 'm', 'c'])
    assert sg.parse('I41/amd') == ('I', ['41/a', 'm', 'd'])
    assert sg.parse('C 2/c') == ('C', ['2/c'])
    for bad in ('', 'X21', 'P2x', 'P 23/c', 'P 6/q'):
        with pytest.raises(ValueError):
            sg.parse(bad)


def test_what_the_positions_say():
    lines = sg.explain('P21/c', 'моноклинная')
    assert 'mP' in lines[1]
    assert lines[2].startswith('2₁/c вдоль b:') and 'винтовая ось 2₁' in lines[2] and 'сдвиг на ½ c, перпендикулярная b' in lines[2]
    lines = sg.explain('Pnma', 'ромбическая')
    assert lines[2].startswith('n:') and lines[2].endswith('перпендикулярная a')
    assert lines[3] == 'm: зеркальная плоскость, перпендикулярная b'
    assert lines[4].startswith('a:') and 'сдвиг на ½ a' in lines[4] and lines[4].endswith('перпендикулярная c')
    lines = sg.explain('Fm-3m', 'кубическая')
    assert 'cF' in lines[1] and lines[3].startswith('−3 вдоль ⟨111⟩') and '120°' in lines[3]
    assert lines[2].endswith('перпендикулярная ⟨100⟩') and lines[4].endswith('перпендикулярная ⟨110⟩')
    lines = sg.explain('P63/mmc', 'гексагональная')
    assert 'hP' in lines[1] and '60°' in lines[2] and 'сдвиг на 1/2 периода' in lines[2] and 'перпендикулярная [001]' in lines[2]
    lines = sg.explain('I41/amd', 'тетрагональная')
    assert 'tI' in lines[1] and 'сдвиг на 1/4 периода' in lines[2] and 'четверть диагонали' in lines[4]
    assert sg.explain('P-1', 'триклинная')[2] == '−1: центр инверсии'


def test_the_bravais_lattices():
    assert sg.bravais('моноклинная', 'C')[0] == 'mC' and sg.bravais('моноклинная', 'A')[0] == 'mC'
    assert sg.bravais('ромбическая', 'A')[0] == 'oC' and sg.bravais('ромбическая', 'F')[0] == 'oF'
    assert sg.bravais('тригональная', 'R')[0] == 'hR' and sg.bravais('тригональная', 'P')[0] == 'hP'
    assert sg.bravais('кубическая', 'I') == ('cI', 'кубическая объёмноцентрированная')
    assert sg.bravais('', 'P') is None
    codes = {sg.bravais(system, c)[0] for system in sg.PEARSON for c in 'PABCIFR' if sg.bravais(system, c)}
    assert codes == set(sg.LATTICE_NAMES) and len(codes) == 14


def test_the_nodes_of_a_cell_and_a_block():
    assert [len(sg.lattice_nodes(c)) for c in 'PICFR'] == [8, 9, 10, 14, 10]
    assert (0.5, 0.5, 0.5) in sg.lattice_nodes('I') and (0.5, 0.5, 0.0) in sg.lattice_nodes('C')
    assert len(sg.lattice_nodes('P', (2, 2, 2))) == 27 and len(sg.lattice_nodes('I', (2, 1, 1))) == 12 + 2
