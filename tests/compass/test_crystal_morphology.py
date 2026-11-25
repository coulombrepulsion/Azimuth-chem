"""crystal_morphology: the shapes of BFDH of cubic lattices and of benzoic acid; the systematic absences."""

from pathlib import Path

import pytest

from modules.compass.chemistry import crystal as cr
from modules.compass.chemistry import crystal_morphology as cm

EXAMPLES = Path(__file__).resolve().parents[2] / 'examples' / '10-crystals'


def example(name):
    return cr.parse_cif((EXAMPLES / name).read_text(encoding='utf-8'))


def test_the_cube_of_cscl():
    shape = cm.morphology(example('CsCl.cif'))
    assert len(shape.faces) == 6 and len(shape.vertices) == 8
    (form,) = shape.forms
    assert form.hkl == (1, 0, 0) and form.n == 1 and form.share == pytest.approx(1.0)
    assert form.d == pytest.approx(example('CsCl.cif').cell.a)


def test_rock_salt_octahedron_cut_by_the_cube():
    # fcc: {111} d = a/√3; {100} absent until (200), d = a/2 — the octahedron truncated by the cube, 8 + 6 faces
    shape = cm.morphology(example('NaCl_rock_salt.cif'))
    assert [(f.hkl, f.n, f.faces) for f in shape.forms] == [((1, 1, 1), 1, 8), ((1, 0, 0), 2, 6)]
    assert shape.forms[0].d == pytest.approx(5.64 / 3 ** 0.5) and shape.forms[1].d == pytest.approx(2.82)
    assert sum(f.share for f in shape.forms) == pytest.approx(1.0)


def test_a_bcc_lattice_gives_the_rhombic_dodecahedron():
    ops = tuple(cr.operation(t) for t in ('x,y,z', 'x+1/2,y+1/2,z+1/2'))
    bcc = cr.Crystal('W', cr.Cell(3.16, 3.16, 3.16), (cr.Site('W', 'W', 0, 0, 0),), ops)
    shape = cm.morphology(bcc)
    assert len(shape.faces) == 12 and len(shape.vertices) == 14 and shape.forms[0].hkl == (1, 1, 0)


def test_benzoic_acid_is_a_plate():
    # P2₁/c: (00l) only with l even (the glide c) — {001} grows as (002) and still has the largest d: the plate
    shape = cm.morphology(example('benzoic_acid.cif'))
    first = shape.forms[0]
    assert first.hkl == (0, 0, 1) and first.n == 2 and first.share > 0.4


def test_absences():
    ops = example('benzoic_acid.cif').operations
    assert cm.absent((0, 0, 1), ops) and not cm.absent((0, 0, 2), ops) and cm.absent((0, 1, 0), ops)
    assert cm.hkl_text((1, -1, 0)) == '1 −1 0' and cm.hkl_text((1, 1, 1)) == '111'
