"""Independent geometric oracles, see docs/features/GEOMETRY_COMPARISON.md."""

from dataclasses import replace
import pytest
from azimuth.core import Atom, Molecule
from modules.spectrum.analysis.comparison import align


def mol(points):
    return Molecule('test', tuple(Atom('C', *p) for p in points))


def test_known_rigid_transform():
    source = mol([(0, 0, 0), (1, 0, 0), (0, 2, 0), (0, 0, 3)])
    target = mol([(4 - a.y, 5 + a.x, 6 + a.z) for a in source.atoms])
    fitted, rmsd = align(source, target)
    assert rmsd < 1e-12
    for a, b in zip(fitted.atoms, target.atoms):
        assert a.position == pytest.approx(b.position, abs=1e-12)


def test_stretched_pair():
    _, rmsd = align(mol([(0, 0, 0), (1, 0, 0)]), mol([(0, 0, 0), (2, 0, 0)]))
    assert rmsd == pytest.approx(0.5, abs=1e-12)


def test_reflection_not_allowed():
    source = mol([(0, 0, 0), (1, 0, 0), (0, 2, 0), (0, 0, 3)])
    _, rmsd = align(source, mol([(-a.x, a.y, a.z) for a in source.atoms]))
    assert rmsd > 0.1


def test_mismatched_order():
    source = mol([(0, 0, 0)])
    with pytest.raises(ValueError):
        align(source, replace(source, atoms=(Atom('O', 0, 0, 0),)))


def test_single_atom():
    _, rmsd = align(mol([(1, 2, 3)]), mol([(4, 5, 6)]))
    assert rmsd == 0


@pytest.mark.parametrize('value', [float('nan'), float('inf'), 1e7])
def test_invalid_coordinate(value):
    with pytest.raises(ValueError):
        align(mol([(value, 0, 0)]), mol([(0, 0, 0)]))
