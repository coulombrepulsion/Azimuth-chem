"""A block by ranges of the coordinates; the molecules coloured by symmetry (crystal_packing.py).

Oracles, counted by hand:
  * rock salt, 0 ≤ x, y, z ≤ 1: the atoms of a cell with its faces — 27 (14 Na, 13 Cl); 0 ≤ x, y, z ≤ the corner,
    three face centres and their Cl between — 4 Na (0 0 0, 0 ½ ½, ½ 0 ½, ½ ½ 0) and 4 Cl (½ ½ ½, ½ 0 0, 0 ½ 0, 0 0 ½);
  * ethanol in P2₁/c (Z = 4, Z′ = 1): whole molecules with the centroid in 0…1 — 4 × 9 atoms; 0…2 along a — 8 × 9;
    each of the 4 molecules of the cell is made by another of the 4 operations: 4 colours, 9 atoms each;
  * rock salt: every atom is a copy by the identity or by a centring vector of F — one colour.
"""

import pytest

from modules.compass.chemistry import crystal_packing as cp
from modules.compass.chemistry import crystal_symmetry as cs
from tests.compass.test_crystal_symmetry import ethanol_crystal, rock_salt


def test_ranges_of_rock_salt():
    block = cp.build_range(rock_salt(), (0, 0, 0), (1, 1, 1))
    assert len(block.atoms) == 27 and sum(a.symbol == 'Na' for a in block.atoms) == 14
    small = cp.build_range(rock_salt(), (0, 0, 0), (0.5, 0.5, 0.5))
    assert sorted(a.symbol for a in small.atoms) == ['Cl'] * 4 + ['Na'] * 4
    with pytest.raises(ValueError):
        cp.build_range(rock_salt(), (1, 0, 0), (0, 1, 1))


def test_whole_molecules_by_range_and_their_colours():
    crystal, _ = ethanol_crystal()
    block = cp.build_range(crystal, (0, 0, 0), (1, 1, 1), whole=True, factor=1.22)
    assert len(block.atoms) == 36
    assert len(cp.build_range(crystal, (0, 0, 0), (2, 1, 1), whole=True, factor=1.22).atoms) == 72
    molecule, _ = cs.whole_molecules(crystal, (1, 1, 1), 1.22)
    found = cp.classes(crystal, molecule)
    assert sorted(found.count(k) for k in set(found)) == [9, 9, 9, 9] and set(found) == {0, 1, 2, 3}
    legend = cp.legend(crystal, molecule)
    assert [count for _, _, count in legend] == [9, 9, 9, 9] and legend[0][1].replace(' ', '') == 'x,y,z'


def test_rock_salt_has_one_colour():
    salt = rock_salt()
    from modules.compass.chemistry import crystal as cr

    assert set(cp.colours(salt, cr.build(salt, (1, 1, 1), True)).values()) == {cp.PALETTE[0]}
