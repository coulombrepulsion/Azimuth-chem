"""«Мои молекулы» (modules/compass/chemistry/user_molecules.py)."""
import pytest

from azimuth.core import EXAMPLES, read_xyz
from modules.compass.chemistry import library, user_molecules


@pytest.fixture(autouse=True)
def kept():
    before = dict(user_molecules.USER)
    yield
    user_molecules.register(before)


def test_a_molecule_is_kept_with_its_bonds_and_found_by_name():
    water = read_xyz(EXAMPLES['Вода · H₂O'])
    methane = read_xyz(EXAMPLES['Метан · CH₄'])
    from modules.compass.chemistry.builder import connections, place_molecule

    pair = place_molecule(water, methane, (6.0, 0.0, 0.0))
    alone = user_molecules.cut(pair, range(3, 3 + len(methane.atoms)))  # the methane of the pair
    assert alone.formula == 'CH4' and len(alone.bonds) == 4 and all(a < 5 and b < 5 for a, b, _ in alone.bonds)
    text = user_molecules.dump({'Мой метан': alone, 'Вода': water.__class__('Вода', water.atoms, connections(water))})
    found = user_molecules.parse(text)
    assert list(found) == ['Мой метан', 'Вода'] and found['Мой метан'].atoms == alone.atoms
    assert found['Мой метан'].bonds == alone.bonds
    user_molecules.register(found)
    assert library.molecule('Мой метан').formula == 'CH4'  # the building and the menus take it as the library's


def test_names():
    assert user_molecules.check_name('  Мой   метан ') == 'Мой метан'
    for bad in ('', '   ', 'x' * 61, 'Вода · H₂O', user_molecules.GROUP):
        with pytest.raises(ValueError):
            user_molecules.check_name(bad)
    with pytest.raises(ValueError):
        user_molecules.check_name('A', taken={'A'})


def test_a_damaged_file_is_refused():
    for text in ('not json', '{"format": "other"}',
                 '{"format": "azimuth-molecules", "molecules": [{"name": "x", "xyz": "1\\nx\\nQq 0 0 0\\n"}]}',
                 '{"format": "azimuth-molecules", "molecules": [{"name": "x", "xyz": "1\\nx\\nH 0 0 0\\n", "bonds": [[0, 5, 1]]}]}'):
        with pytest.raises(ValueError):
            user_molecules.parse(text)
