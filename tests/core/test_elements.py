"""«Таблица Менделеева» of «Справка» — the data (azimuth/elements.py). Oracles: configurations of the
ground states as the tables of NIST give them, written by hand here."""

from azimuth import elements
from azimuth.core import SYMBOLS


def test_configurations_and_shells():
    z = {s: k + 1 for k, s in enumerate(SYMBOLS)}
    assert elements.text(1) == '1s¹' and elements.text(z['C']) == '[He] 2s² 2p²'
    assert elements.text(z['Fe']) == '[Ar] 3d⁶ 4s²' and elements.shells(z['Fe']) == [2, 8, 14, 2]
    assert elements.text(z['Cr']) == '[Ar] 3d⁵ 4s¹' and elements.text(z['Cu']) == '[Ar] 3d¹⁰ 4s¹'
    assert elements.text(z['Pd']) == '[Kr] 4d¹⁰' and elements.text(z['Pt']) == '[Xe] 4f¹⁴ 5d⁹ 6s¹'
    assert elements.text(z['Gd']) == '[Xe] 4f⁷ 5d¹ 6s²' and elements.text(z['U']) == '[Rn] 5f³ 6d¹ 7s²'
    assert elements.text(z['Og']) == '[Rn] 5f¹⁴ 6d¹⁰ 7s² 7p⁶' and elements.text(z['Ne']) == '[He] 2s² 2p⁶'
    for k in range(1, 119):
        assert sum(elements.shells(k)) == k  # every electron in a shell
    assert len(elements.NAMES) == 118 and elements.NAMES['Og'] == 'Оганесон'


def test_masses():
    assert abs(elements.mean_mass('C') - 12.0106) < 0.001 and abs(elements.mean_mass('Cl') - 35.453) < 0.002
    assert elements.mean_mass('Tc') is None and elements.LONGEST['Tc'] == 98
    assert all(s in elements.LONGEST for s in SYMBOLS[:118] if s not in elements.STABLE)


def test_every_element_is_of_one_family():
    names = [symbol for _, _, symbols in elements.CATEGORIES for symbol in symbols.split()]
    assert sorted(names) == sorted(SYMBOLS[:118]) and len(names) == 118
    assert elements.CATEGORY['Fe'][0] == 'Переходные металлы' and elements.CATEGORY['Xe'][0] == 'Благородные газы'
    assert len({colour for _, colour, _ in elements.CATEGORIES}) == len(elements.CATEGORIES)
