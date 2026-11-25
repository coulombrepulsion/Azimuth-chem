"""editing.bond_by_replacing: a drag from an atom ended on another atom bonds them."""

from math import dist

from azimuth.core import Atom, Molecule
from modules.compass.chemistry.builder import bond_length, connections
from modules.compass.chemistry.editing import bond_by_replacing


def _water(x):
    return (Atom('O', x, 0.0, 0.0), Atom('H', x + 0.96, 0.0, 0.0), Atom('H', x - 0.24, 0.93, 0.0))


def test_an_atom_of_another_molecule_is_replaced_and_brought_to_the_bond():
    # two waters 5 Å apart; carbon dragged from the first oxygen onto a hydrogen of the second
    two = Molecule('two', _water(0.0) + _water(5.0), ((0, 1, 1), (0, 2, 1), (3, 4, 1), (3, 5, 1)))
    result = bond_by_replacing(two, 0, 5, 'C')
    assert result.atoms[5].symbol == 'C' and len(result.atoms) == 6
    bonds = {frozenset((i, j)) for i, j, _ in connections(result)}
    assert frozenset((0, 5)) in bonds and frozenset((3, 5)) in bonds  # the old bond stays: the two are joined
    assert abs(dist(result.atoms[0].position, result.atoms[5].position) - bond_length('O', 'C', 1)) < 1e-6
    # the second water moved whole: its own distances as before
    assert abs(dist(result.atoms[3].position, result.atoms[4].position) - dist(two.atoms[3].position, two.atoms[4].position)) < 1e-9
    assert result.atoms[1].position == two.atoms[1].position  # the first one stays


def test_an_atom_of_the_same_molecule_closes_a_ring_where_it_is():
    chain = Molecule('chain', tuple(Atom('C', 1.5 * i, 0.3 * (i % 2), 0.0) for i in range(5)),
                     tuple((i, i + 1, 1) for i in range(4)))
    result = bond_by_replacing(chain, 0, 4, 'N')
    assert result.atoms[4].symbol == 'N' and result.atoms[4].position == chain.atoms[4].position
    assert frozenset((0, 4)) in {frozenset((i, j)) for i, j, _ in connections(result)}


def test_the_same_atom_is_refused():
    import pytest

    with pytest.raises(ValueError):
        bond_by_replacing(Molecule('one', _water(0.0), ((0, 1, 1), (0, 2, 1))), 1, 1, 'C')
