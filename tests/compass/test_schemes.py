"""Display schemes (modules/compass/view/schemes.py).

Oracles, independent of the tested code:
  * Jmol colours of a few elements as printed in the Jmol documentation table (H FFFFFF, C 909090,
    N 3050F8, O FF0D0D, S FFFF30, Fe E06633, Au FFD123, Mt EB0026), the count 109;
  * the default scheme gives exactly the colours of the program before schemes (written out here);
  * grey levels: R = G = B and the order of luminance of the Jmol colours is kept (a hand computation
    of the Rec. 709 weights for O and N);
  * every built-in scheme is valid; every element has a colour in every palette; individual colours
    win over the palette; stored and read again schemes are the same; damaged inputs are refused.
"""

import pytest

from modules.compass.view import schemes
from azimuth.core import SYMBOLS


def test_jmol_colours_from_the_documentation_table():
    expected = {'H': 'FFFFFF', 'C': '909090', 'N': '3050F8', 'O': 'FF0D0D', 'S': 'FFFF30', 'Fe': 'E06633', 'Au': 'FFD123', 'Mt': 'EB0026'}
    assert len(schemes.JMOL) == 109
    for symbol, hex6 in expected.items():
        assert schemes.JMOL[symbol] == hex6
    p = schemes.palette(schemes.BUILTIN['Цвета Jmol'])
    assert p['O'] == '#ff0d0d' and p['Og'] == schemes.NEUTRAL


def test_default_scheme_keeps_the_old_colours():
    old = {'H': '#e2e8ec', 'C': '#45566a', 'N': '#5278d6', 'O': '#df645b', 'F': '#74b887', 'Cl': '#74b887', 'S': '#e9b64b', 'P': '#d28a4d'}
    p = schemes.palette(schemes.DEFAULT)
    assert {k: p[k] for k in old} == old and p['Fe'] == '#9c80b7'
    assert schemes.same(schemes.BUILTIN['Азимут (по умолчанию)'], schemes.DEFAULT)


def test_grey_levels_keep_the_order_of_luminance():
    p = schemes.palette(schemes.BUILTIN['Чёрно-белая'])
    for symbol in ('H', 'C', 'N', 'O', 'S', 'Fe'):
        c = p[symbol]
        assert c[1:3] == c[3:5] == c[5:7]
    # O: 0.2126*255 + 0.7152*13 + 0.0722*13 = 64.45 -> 64 = 0x40; N: 0.2126*48 + 0.7152*80 + 0.0722*248 = 85.33 -> 0x55
    assert p['O'] == '#404040' and p['N'] == '#555555'
    level = lambda s: int(p[s][1:3], 16)  # noqa: E731
    assert level('H') > level('S') > level('C') > level('N') > level('O')


def test_every_scheme_and_palette_is_complete():
    for name, scheme in schemes.BUILTIN.items():
        s = schemes.normalize(scheme)
        p = schemes.palette(s)
        assert set(p) == set(SYMBOLS), name
        assert all(len(c) == 7 and c[0] == '#' for c in p.values())


def test_individual_colours_and_storage():
    s = dict(schemes.BUILTIN['Цвета Jmol'])
    s['colors'] = {'C': '#123ABC'}
    assert schemes.palette(s)['C'] == '#123abc' and schemes.palette(s)['O'] == '#ff0d0d'
    text = schemes.dump({'Моя': s, 'Вторая': schemes.BUILTIN['Стержни']})
    back = schemes.parse(text)
    assert list(back) == ['Моя', 'Вторая'] and schemes.same(back['Моя'], s)
    assert schemes.dump(back) == text


@pytest.mark.parametrize(
    'change',
    [
        {'display_mode': 'wire'},
        {'bond_width': 9.0},
        {'atom_scale': 'big'},
        {'show_bonds': 1},
        {'colors': {'Xx': '#000000'}},
        {'colors': {'C': 'red'}},
        {'extra': True},
    ],
)
def test_damaged_schemes_are_refused(change):
    s = dict(schemes.DEFAULT)
    s.update(change)
    with pytest.raises(ValueError):
        schemes.normalize(s)


def test_damaged_files_are_refused():
    for text in ('nope', '{"version": 2, "schemes": {}}', '{"version": 1, "schemes": {"": {}}}', '{"version": 1, "schemes": {"x": {"grid": true}}}'):
        with pytest.raises(ValueError):
            schemes.parse(text)
    s = dict(schemes.DEFAULT)
    del s['grid']
    with pytest.raises(ValueError):
        schemes.normalize(s)
