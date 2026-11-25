"""crystal_setting: benzoic acid in its three monoclinic cell choices, the reduced cell of rock salt, the names."""

from pathlib import Path

import numpy as np
import pytest

from modules.compass.chemistry import crystal as cr
from modules.compass.chemistry import crystal_setting as cs
from modules.compass.chemistry import powder

EXAMPLES = Path(__file__).resolve().parents[2] / 'examples' / '10-crystals'


def example(name):
    return cr.parse_cif((EXAMPLES / name).read_text(encoding='utf-8'))


def cartesian_set(crystal, n=1):
    """The atoms of a block 3 × 3 × 3 around the origin, Cartesian, rounded — the same for any cell of the crystal."""
    rows = np.array(crystal.cell.vectors())
    pts = set()
    for symbol, *f, _ in cr.unit_cell(crystal):
        for shift in np.ndindex(3, 3, 3):
            r = (np.array(f) + np.array(shift) - 1) @ rows
            if np.linalg.norm(r) < 6:
                pts.add((symbol, *np.round(r, 2)))
    return pts


def test_the_monoclinic_cell_choices_of_benzoic_acid():
    crystal = example('benzoic_acid.cif')
    names = [cs.entry_name(e) for e, _, _ in cs.settings(crystal)]
    assert names[0] == 'P 1 21/n 1' and 'P 1 21/c 1' in names and 'P 1 21/a 1' in names
    m = next(m for e, m, _ in cs.settings(crystal) if cs.entry_name(e) == 'P 1 21/c 1')
    other = cs.transform(crystal, m)
    assert other.space_group == 'P 1 21/c 1' and len(cr.unit_cell(other)) == len(cr.unit_cell(crystal))
    assert other.cell.volume() == pytest.approx(crystal.cell.volume())
    # the same atoms in space (the cell turned with the axes: compared by the distances to the origin and elements)
    before = sorted((s, round(float(np.linalg.norm(p)), 2)) for s, *p in cartesian_set(crystal))
    after = sorted((s, round(float(np.linalg.norm(p)), 2)) for s, *p in cartesian_set(other))
    assert before == after
    # the powder pattern does not depend on the cell chosen
    one, two = powder.pattern(crystal, stop=40), powder.pattern(other, stop=40)
    assert [round(x.two_theta, 3) for x in one] == [round(x.two_theta, 3) for x in two]


def test_the_reduced_cell_of_rock_salt():
    crystal = example('NaCl_rock_salt.cif')
    reduced = cs.transform(crystal, cs.reduced_matrix(crystal))
    c = reduced.cell
    assert (c.a, c.b, c.c) == pytest.approx((5.64 / 2 ** 0.5,) * 3)
    assert (c.alpha, c.beta, c.gamma) == pytest.approx((60.0,) * 3)
    assert len(cr.unit_cell(reduced)) == 2 and reduced.cell.volume() == pytest.approx(5.64 ** 3 / 4)


def test_names_and_texts():
    assert cs.entry_name(cs.identify(example('CsCl.cif').operations)) == 'P 4/m -3 2/m'
    assert cs.matrix_text([[1, 0, 1], [0, 1, 0], [-1, 0, 0]]) == 'a′ = a+c, b′ = b, c′ = −a'
    with pytest.raises(ValueError):
        cs.transform(example('CsCl.cif'), [[0, 1, 0], [1, 0, 0], [0, 0, 1]])  # left-handed
