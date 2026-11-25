"""Crystals: CIF reading, the unit cell, supercells (modules/compass/chemistry/crystal.py).

Oracles, independent of the tested code:
  * the cell vectors have the lengths a, b, c and the angles alpha, beta, gamma between them (dot
    products), and the volume formula equals the determinant of the vectors;
  * rock salt, Fm-3m, the 192 operations generated here (48 signed permutations x 4 centring
    translations): 4 Na and 4 Cl in the cell, the shortest Na-Cl distance a/2, Na-Na a/sqrt 2; the cell
    with the atoms on its faces, edges and corners is the textbook picture: 14 Na (8 corners, 6 faces)
    and 13 Cl (12 edges, 1 centre); a 2x2x2 block has 64 atoms;
  * P2_1/c (4 operations): a general position gives 4 atoms, a site on the inversion centre 2
    (the multiplicities 4e and 2a of the International Tables);
  * the CIF syntax: uncertainties in parentheses, quoted operations, comments, a text field, the element
    from the type symbol ('Na1+') or the label ('Cl1'); missing operations mean P1 (said in the notes).
"""

from itertools import permutations, product
from math import acos, degrees, dist, sqrt

import pytest

from modules.compass.chemistry import crystal as cr


def angle(u, v):
    return degrees(acos(sum(a * b for a, b in zip(u, v)) / sqrt(sum(a * a for a in u) * sum(b * b for b in v))))


def det(m):
    return (
        m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
        - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
        + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0])
    )


@pytest.mark.parametrize(
    'cell',
    [(5.64, 5.64, 5.64, 90, 90, 90), (2.46, 2.46, 6.71, 90, 90, 120), (7.1, 8.3, 9.2, 81.5, 95.3, 104.7)],
)
def test_cell_vectors_lengths_angles_volume(cell):
    c = cr.Cell(*cell).validate()
    va, vb, vc = c.vectors()
    for v, length in zip((va, vb, vc), cell[:3]):
        assert sqrt(sum(x * x for x in v)) == pytest.approx(length, abs=1e-12)
    assert angle(vb, vc) == pytest.approx(cell[3], abs=1e-9)
    assert angle(va, vc) == pytest.approx(cell[4], abs=1e-9)
    assert angle(va, vb) == pytest.approx(cell[5], abs=1e-9)
    assert c.volume() == pytest.approx(det((va, vb, vc)), rel=1e-12)


def fm3m_operations():
    ops = []
    for perm in permutations(range(3)):
        for signs in product((1, -1), repeat=3):
            for t in ((0, 0, 0), (0, '1/2', '1/2'), ('1/2', 0, '1/2'), ('1/2', '1/2', 0)):
                parts = []
                for row in range(3):
                    term = ('-' if signs[row] < 0 else '') + 'xyz'[perm[row]]
                    parts.append(term + (f'+{t[row]}' if t[row] else ''))
                ops.append(', '.join(parts))
    return ops


def rock_salt(a=5.64):
    ops = '\n'.join(f"'{o}'" for o in fm3m_operations())
    return f"""# rock salt, written for the test
data_NaCl
_cell_length_a {a}(1)
_cell_length_b {a}(1)
_cell_length_c {a}(1)
_cell_angle_alpha 90
_cell_angle_beta 90.0
_cell_angle_gamma 90.00(0)
_symmetry_space_group_name_H-M 'F m -3 m'
_publ_section_comment
;
A text field: loop_ and _tags inside it are text, not CIF.
;
loop_
_space_group_symop_operation_xyz
{ops}
loop_
_atom_site_label
_atom_site_type_symbol
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
_atom_site_occupancy
Na1 Na1+ 0 0 0 1
Cl1 Cl1- 0.5 0.5 0.5 1.0(0)
"""


def test_rock_salt_cell_and_distances():
    c = cr.parse_cif(rock_salt())
    assert len(c.operations) == 192 and c.space_group == 'F m -3 m' and c.notes == ()
    cell = cr.unit_cell(c)
    assert sorted(s for s, *_ in cell) == ['Cl'] * 4 + ['Na'] * 4
    m = cr.build(c)
    na = [a.position for a in m.atoms if a.symbol == 'Na']
    cl = [a.position for a in m.atoms if a.symbol == 'Cl']
    assert min(dist(p, q) for p in na for q in cl) == pytest.approx(5.64 / 2, abs=1e-9)
    assert min(dist(p, q) for p in na for q in na if p != q) == pytest.approx(5.64 / sqrt(2), abs=1e-9)


def test_rock_salt_cell_with_faces_and_a_block():
    c = cr.parse_cif(rock_salt())
    m = cr.build(c, (1, 1, 1), faces=True)
    assert sum(a.symbol == 'Na' for a in m.atoms) == 14 and sum(a.symbol == 'Cl' for a in m.atoms) == 13
    assert len(cr.build(c, (2, 2, 2)).atoms) == 64
    assert len(cr.build(c, (5, 5, 5)).atoms) == 1000  # the limit is MAX_ATOMS = 2000 (was 500)
    with pytest.raises(ValueError):
        cr.build(c, (7, 7, 7))  # 2744 atoms


def p21c(extra=''):
    return f"""data_test
_cell_length_a 7.50
_cell_length_b 9.10
_cell_length_c 11.20
_cell_angle_beta 104.5
loop_
_symmetry_equiv_pos_as_xyz
x,y,z
-x,1/2+y,1/2-z
-x,-y,-z
x,1/2-y,1/2+z
loop_
_atom_site_label
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
C1 0.1234(3) 0.2345(2) 0.3456(4)
Fe1 0 0 0  # on the inversion centre
{extra}"""


def test_multiplicities_in_p21c():
    c = cr.parse_cif(p21c())
    symbols = [s for s, *_ in cr.unit_cell(c)]
    assert symbols.count('C') == 4 and symbols.count('Fe') == 2
    edges = cr.cell_edges(c.cell)
    assert len(edges) == 12
    lengths = sorted(round(dist(p, q), 9) for p, q in edges)
    assert lengths == [7.5] * 4 + [9.1] * 4 + [11.2] * 4


def test_syntax_and_refusals():
    assert cr.element('Cl1') == 'Cl' and cr.element('C12a') == 'C' and cr.element('x', 'Fe3+') == 'Fe'
    assert cr.number('1.234(5)') == 1.234 and cr.number('?') is None
    rows, t = cr.operation('-y+1/2, x-y, 0.25+z')
    assert rows == ((0, -1, 0), (1, -1, 0), (0, 0, 1)) and [float(v) for v in t] == [0.5, 0.0, 0.25]
    p1 = cr.parse_cif('data_x\n_cell_length_a 3\n_cell_length_b 3\n_cell_length_c 3\nloop_\n_atom_site_label\n_atom_site_fract_x\n_atom_site_fract_y\n_atom_site_fract_z\nO1 0 0 0\n')
    assert len(p1.operations) == 1 and p1.notes and 'P1' in p1.notes[0]
    for bad in (
        'no data block',
        'data_x\n_cell_length_a 3\n',  # no b, c
        'data_x\n_cell_length_a 3\n_cell_length_b 3\n_cell_length_c 3\n',  # no atoms
        'data_x\n_cell_length_a 3\n_cell_length_b 3\n_cell_length_c 3\n_cell_angle_alpha 170\n_cell_angle_beta 170\n'
        '_cell_angle_gamma 170\nloop_\n_atom_site_label\n_atom_site_fract_x\n_atom_site_fract_y\n_atom_site_fract_z\nO1 0 0 0\n',
    ):
        with pytest.raises(ValueError):
            cr.parse_cif(bad)
    with pytest.raises(ValueError):
        cr.operation('x, y')
    with pytest.raises(ValueError):
        cr.operation('x, y, 1/2')


def test_one_part_of_a_disorder():
    # _atom_site_disorder_group: a methyl group in two positions (groups 1 and 2, occupancy 0.6 and 0.4);
    # one part keeps the ordered atoms and group 1
    text = (
        'data_dis\n_cell_length_a 10\n_cell_length_b 10\n_cell_length_c 10\nloop_\n_atom_site_label\n'
        '_atom_site_fract_x\n_atom_site_fract_y\n_atom_site_fract_z\n_atom_site_occupancy\n_atom_site_disorder_group\n'
        'C1 0.1 0.1 0.1 1 .\nC2 0.25 0.1 0.1 0.6 1\nC2B 0.1 0.25 0.1 0.4 2\nO1 0.1 0.1 0.25 1 ?\n'
    )
    c = cr.parse_cif(text)
    assert [s.disorder for s in c.sites] == ['', '1', '2', ''] and cr.disorder_groups(c) == ('1', '2')
    part = cr.main_part(c)
    assert [s.label for s in part.sites] == ['C1', 'C2', 'O1'] and 'часть 1' in part.notes[-1]
    assert cr.main_part(part).notes == part.notes
    assert [s.label for s in cr.main_part(c, '2').sites] == ['C1', 'C2B', 'O1']
    ordered = cr.parse_cif(text.replace(' 1 .\n', ' 1 .\n').replace('_atom_site_disorder_group\n', '_atom_site_x\n'))
    assert cr.disorder_groups(ordered) == () and cr.main_part(ordered) is ordered


def test_the_block_as_a_crystal_of_p1():
    # the 27 atoms of a cell of rock salt with its faces (8 corners + 6 faces Na, 12 edges + 1 centre Cl —
    # counted by hand) keep the labels of the file, numbered on repetition, and their fractions (1 on the far faces);
    # an atom added by hand is named by its symbol and number; the text is a CIF that reads back with the same atoms
    from azimuth.core import Atom, Molecule
    from modules.compass.chemistry import surface
    from tests.compass.test_crystal_symmetry import rock_salt

    salt = rock_salt()
    block = cr.build(salt, (1, 1, 1), True)
    found = cr.block_crystal(salt, block)
    labels = [s.label for s in found.sites]
    assert len(found.sites) == 27 and sum(s.symbol == 'Na' for s in found.sites) == 14
    assert labels.count('Na1') == 1 and 'Na1_14' in labels and 'Cl1_13' in labels and len(set(labels)) == 27
    assert any((s.x, s.y, s.z) == (1.0, 1.0, 1.0) for s in found.sites) and found.space_group == 'P 1'
    extra = Molecule('x', block.atoms + (Atom('O', 1.0, 1.0, 1.0),))
    last = cr.block_crystal(salt, extra).sites[-1]
    assert last.label == 'O28' and last.occupancy == 1.0
    back = cr.parse_cif(surface.write_cif(found))
    assert [s.label for s in back.sites] == labels and len(back.operations) == 1


def test_the_primitive_cell():
    # oracles by hand: rock salt (F, a = 5.6402 Å) — the primitive cell of the fcc lattice: a/√2 = 3.9882 Å,
    # 60°, a quarter of the volume, 1 Na and 1 Cl; a body-centred lattice (I, a = 2.87 Å, one site) — √3 a / 2 = 2.4855 Å,
    # 109.47° (cos = −1/3), half the volume, 1 atom; a primitive crystal (P) stays as it is
    from math import acos, degrees, sqrt

    from tests.compass.test_crystal_symmetry import rock_salt

    salt = rock_salt()
    p = cr.primitive(salt)
    c = p.cell
    assert len(p.sites) == 2 and sorted(s.symbol for s in p.sites) == ['Cl', 'Na']
    assert all(abs(x - 5.6402 / sqrt(2)) < 1e-6 for x in (c.a, c.b, c.c))
    assert all(abs(x - 60) < 1e-6 for x in (c.alpha, c.beta, c.gamma))
    assert abs(c.volume() - salt.cell.volume() / 4) < 1e-6 and len(cr.unit_cell(p)) == 2
    text = ('data_W\n_cell_length_a 2.87\n_cell_length_b 2.87\n_cell_length_c 2.87\n'
            "_space_group_name_H-M_alt 'I m -3 m'\nloop_\n_atom_site_label\n_atom_site_fract_x\n"
            '_atom_site_fract_y\n_atom_site_fract_z\nW1 0 0 0\n')
    bcc = cr.parse_cif(text)
    q = cr.primitive(bcc)
    assert len(q.sites) == 1 and abs(q.cell.a - sqrt(3) * 2.87 / 2) < 1e-6
    assert abs(q.cell.alpha - degrees(acos(-1 / 3))) < 1e-6 and abs(q.cell.volume() - 2.87 ** 3 / 2) < 1e-6
    plain = cr.Crystal('p', cr.Cell(3, 4, 5), (cr.Site('C1', 'C', 0, 0, 0),), (cr.operation('x, y, z'),), 'P 1')
    assert cr.primitive(plain) is plain
