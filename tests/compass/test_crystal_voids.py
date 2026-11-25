"""crystal_voids: one atom in a large cell, rock salt, channels and cavities."""

from math import pi
from pathlib import Path

import pytest

from modules.compass.chemistry import crystal as cr
from modules.compass.chemistry import crystal_voids as cv
from modules.spectrum.analysis.contacts import VDW

EXAMPLES = Path(__file__).resolve().parents[2] / 'examples' / '10-crystals'


def p1(cell, sites):
    return cr.Crystal('t', cr.Cell(*cell), tuple(cr.Site(f'{s}{i}', s, *f) for i, (s, f) in enumerate(sites)),
                      (cr.operation('x,y,z'),))


def test_one_atom_in_a_large_cell():
    # every point beyond the van der Waals sphere is reached by a probe further out: V − 4/3 πR³ (whatever the probe)
    one = p1((12, 12, 12), [('Ar', (0, 0, 0))])
    expected = 12 ** 3 - 4 / 3 * pi * VDW['Ar'] ** 3
    for probe in (0.5, 1.2):
        found = cv.voids(one, probe, 0.2)
        assert found.volume == pytest.approx(expected, rel=0.01)
        assert len(found.parts) == 1 and found.parts[0][1] == 'abc'  # open in every direction


def test_rock_salt_and_benzoic_acid_have_no_voids():
    for name in ('NaCl_rock_salt.cif', 'benzoic_acid.cif'):
        found = cv.voids(cr.parse_cif((EXAMPLES / name).read_text(encoding='utf-8')))
        assert found.volume == 0 and not found.parts


def test_channels_and_a_cavity():
    # rows of atoms along c at the corners and the middles of the edges of an 8 × 8 Å base: four channels along c
    rows = p1((8, 8, 3), [('C', (x, y, 0)) for x, y in ((0, 0), (0.5, 0), (0, 0.5), (0.5, 0.5))])
    found = cv.voids(rows, 1.0, 0.2)
    assert [axes for _, axes in found.parts] == ['c'] * 4
    assert sum(v for v, _ in found.parts) == pytest.approx(found.volume)
    # the same base, the rows closed by a layer of atoms at z = ½ of a doubled cell — closed cavities
    caged = p1((8, 8, 6), [('C', (x, y, z)) for x, y in ((0, 0), (0.5, 0), (0, 0.5), (0.5, 0.5)) for z in (0, 0.5)]
               + [('C', (x, y, 0.25)) for x in (0.25, 0.75) for y in (0.25, 0.75)])
    found = cv.voids(caged, 1.0, 0.2)
    assert found.parts and all(axes == '' for _, axes in found.parts)


def test_the_limits():
    with pytest.raises(ValueError):
        cv.voids(p1((5, 5, 5), [('C', (0, 0, 0))]), probe=5.0)
