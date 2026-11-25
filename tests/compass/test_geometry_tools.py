import pytest
from modules.compass.chemistry.geometry_tools import measurement, coordinate_text, BOHR
from azimuth.core import Molecule, Atom


def test_ordered_geometry():
    assert measurement([(0, 0, 0), (3, 4, 0)])[1] == 5
    assert measurement([(1, 0, 0), (0, 0, 0), (0, 1, 0)])[1] == pytest.approx(90)
    assert measurement([(1, 0, 0), (0, 0, 0), (0, 1, 0), (0, 1, 1)])[1] == pytest.approx(-90)
    assert measurement([(1, 0, 0), (0, 0, 0), (0, 1, 0), (0, 1, -1)])[1] == pytest.approx(90)
    assert measurement([(0, 0, 0)] * 5) == ('', None)
    with pytest.raises(ValueError):
        measurement([(0, 0, 0), (1, 0, 0), (2, 0, 0), (2, 1, 0)])


def test_coordinate_blocks_units():
    mol = Molecule('test', (Atom('H', BOHR, 0, 0),))
    assert '1.0000000000' in coordinate_text(mol, 'ORCA', True)
    assert coordinate_text(mol, 'ORCA', True).startswith('! Bohrs\n* xyz 0 1\n')
    assert coordinate_text(mol, 'NWChem', True).startswith('geometry units au\n')
    assert coordinate_text(mol, 'Gaussian', True, -1, 2).startswith('-1 2\n')
    assert coordinate_text(mol, 'XYZ').startswith('1\ntest\n')
    with pytest.raises(ValueError):
        coordinate_text(mol, 'XYZ', True)
