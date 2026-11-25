"""Short contacts and hydrogen bonds of a crystal (modules/compass/chemistry/crystal_contacts.py).

Oracles, independent of the tested code:
  * a chain of water molecules along a (P1, a = 2.9 A, O–H1 along a, 0.96 A): H1 of each molecule points at the O
    of the next one, so the hydrogen bond O–H1···O has d = 2.9 − 0.96 = 1.94 A and the angle 180° (by construction);
    the hydrogen-bond network of the molecule in the cell is it and its two neighbours along a (3 molecules);
  * the same water in a cell of 10 A: no contact at all (every distance to an image is above 6 A);
  * rock salt: no molecules, so the network adds none.
  * a chain of linear I–C≡N along a (P1, I–C 2.00, C≡N 1.16, N···I 2.90 Å by construction): the halogen bond
    C–I···N with d = 2.90 Å, the angle 180° and d/Σr = 2.90 / (1.98 + 1.55);
  * two C–Cl in a cell of 15 Å placed by hand: Cl···Cl 3.30 Å with θ1 = 180°, θ2 = 90° (type II — a halogen bond)
    and Cl···Cl 3.40 Å with θ1 = θ2 = 155° (type I — side by side: a van der Waals contact, though θ1 ≥ 150°).
"""

from math import cos, radians, sin

from modules.compass.chemistry import crystal as cr
from modules.compass.chemistry import crystal_contacts as cc
from tests.compass.test_crystal_symmetry import rock_salt


def water_chain(a=2.9):
    cell = cr.Cell(a, 6.0, 6.0)
    h2 = (0.96 * cos(radians(104.5)), 0.96 * sin(radians(104.5)), 0.0)
    sites = (
        cr.Site('O1', 'O', 0.0, 0.0, 0.0),
        cr.Site('H1', 'H', 0.96 / a, 0.0, 0.0),
        cr.Site('H2', 'H', h2[0] / a, h2[1] / 6.0, 0.0),
    )
    return cr.Crystal('water', cell, sites, (cr.operation('x, y, z'),), 'P 1', (), 1, 'H2 O', 1)


def test_the_hydrogen_bond_along_the_chain():
    found = cc.contacts(water_chain(), 1.22)
    bonds = [c for c in found if c.kind == 'hydrogen']
    assert len(bonds) == 1
    hb = bonds[0]
    assert abs(hb.distance - 1.94) < 1e-6 and abs(hb.angle - 180.0) < 1e-6
    assert hb.site[0] == 1 and hb.donor[0] == 0 and hb.acceptor[0] == 0
    atoms = cr.unit_cell(water_chain())
    assert cc.text(hb, atoms) == 'O1–H1···O1'
    rows = cc.grouped(found, atoms)
    assert rows[0][0] == 'hydrogen' and rows[0][5] == 1
    molecule, added = cc.network(water_chain(), ('hydrogen',), 1.22)
    assert added == 2 and len(molecule.atoms) == 9 and molecule.formula == 'H6O3'


def test_no_contacts_in_a_large_cell():
    assert cc.contacts(water_chain(10.0), 1.22) == ()
    molecule, added = cc.network(water_chain(10.0), ('hydrogen',), 1.22)
    assert added == 0 and len(molecule.atoms) == 3


def test_a_salt_has_no_network():
    molecule, added = cc.network(rock_salt(), ('hydrogen',), 1.22)
    assert added == 0 and molecule.atoms == ()


def test_cut_takes_whole_molecules():
    # one atom of each of two molecules of the network gives both molecules whole (6 atoms of 9)
    molecule, _ = cc.network(water_chain(), ('hydrogen',), 1.22)
    from modules.compass.chemistry.builder import connections

    oxygens = [k for k, a in enumerate(molecule.atoms) if a.symbol == 'O']
    part = cc.cut(molecule, [oxygens[0] + 1, oxygens[1]])
    assert len(part.atoms) == 6 and part.formula == 'H4O2'
    assert len(connections(part)) == 4
    assert cc.cut(molecule, []).atoms == ()


def iodine_cyanide_chain():
    a = 2.0 + 1.16 + 2.9
    sites = (cr.Site('I1', 'I', 0.0, 0.0, 0.0), cr.Site('C1', 'C', 2.0 / a, 0.0, 0.0), cr.Site('N1', 'N', 3.16 / a, 0.0, 0.0))
    return cr.Crystal('ICN', cr.Cell(a, 6.0, 6.0), sites, (cr.operation('x, y, z'),), 'P 1', (), 1, 'C I N', 1)


def test_the_halogen_bond_along_the_chain():
    found = cc.contacts(iodine_cyanide_chain())
    bond = next(c for c in found if c.kind == 'halogen')
    assert abs(bond.distance - 2.9) < 1e-6 and abs(bond.angle - 180.0) < 1e-6 and bond.geometry == ''
    assert abs(cc.ratio(bond) - 2.9 / (1.98 + 1.55)) < 1e-9
    molecule, added = cc.network(iodine_cyanide_chain(), ('halogen',))
    assert added == 2 and len(molecule.atoms) == 9  # the molecule of the cell and its two neighbours along a


def two_chlorides(second):
    """C–Cl along x at the origin and a second C–Cl given by (Cl, C) in Å, in a cell of 15 Å."""
    L = 15.0
    points = (('C1', 'C', (0.0, 0.0, 0.0)), ('Cl1', 'Cl', (1.75, 0.0, 0.0)), ('Cl2', 'Cl', second[0]), ('C2', 'C', second[1]))
    sites = tuple(cr.Site(n, e, *(x / L + 0.2 for x in xyz)) for n, e, xyz in points)
    return cr.Crystal('Cl', cr.Cell(L, L, L), sites, (cr.operation('x, y, z'),), 'P 1', (), 1, 'C2 Cl2', 1)


def test_type_one_and_type_two_halogen_contacts():
    from math import cos, radians, sin

    found = cc.contacts(two_chlorides(((5.05, 0.0, 0.0), (5.05, 1.75, 0.0))))  # type II: 180° and 90°
    pair = next(c for c in found if {c.i, c.j} == {1, 2})
    assert pair.kind == 'halogen' and pair.geometry == 'II' and abs(pair.angle - 180) < 1e-6 and abs(pair.angle2 - 90) < 1e-6
    cl = (1.75 + 3.4 * cos(radians(25)), 3.4 * sin(radians(25)), 0.0)
    found = cc.contacts(two_chlorides((cl, (cl[0] + 1.75, cl[1], 0.0))))  # type I: 155° and 155°
    pair = next(c for c in found if {c.i, c.j} == {1, 2})
    assert pair.kind == 'vdw' and pair.geometry == 'I' and abs(pair.angle - 155) < 1e-6 and abs(pair.angle2 - 155) < 1e-6


# the table of hydrogen bonds of a paper — D–H, H···A, D···A, the angle and the symmetry code of the acceptor.
# Oracle: the code applied by hand (cr.operation of its text) to the coordinates of the acceptor in the file, the donor
# and the H taken as they stand in the file (x, y, z) — the distances must be those of the table.

def _benzoic():
    from pathlib import Path

    text = (Path(__file__).resolve().parents[2] / 'examples' / '10-crystals' / 'benzoic_acid.cif').read_text(encoding='utf-8')
    return cr.parse_cif(text)


def _at(crystal, label, code='x, y, z'):
    site = next(s for s in crystal.sites if s.label == label)
    rows, shifts = cr.operation(code)
    f = [sum(rows[i][j] * (site.x, site.y, site.z)[j] for j in range(3)) + float(shifts[i]) for i in range(3)]
    return crystal.cell.cartesian(f)


def _d(p, q):
    return sum((p[k] - q[k]) ** 2 for k in range(3)) ** 0.5


def test_the_hydrogen_bonds_of_benzoic_acid_with_their_symmetry_codes():
    data = _benzoic()
    bonds = cc.hydrogen_bonds(data, cc.contacts(data))
    dimer = bonds[0]  # the carboxylic dimer R²₂(8) about a centre of inversion
    assert (dimer.donor, dimer.hydrogen, dimer.acceptor) == ('O2', 'H2A', 'O1')
    rows, _ = cr.operation(dimer.code)
    assert rows == ((-1, 0, 0), (0, -1, 0), (0, 0, -1))  # an inversion
    for b in bonds:
        assert b.code not in ('', '?')
        a = _at(data, b.acceptor, b.code)
        assert abs(_d(_at(data, b.donor), a) - b.d_da) < 1e-6
        assert abs(_d(_at(data, b.hydrogen), a) - b.d_ha) < 1e-6
        assert abs(_d(_at(data, b.donor), _at(data, b.hydrogen)) - b.d_dh) < 1e-6
    assert abs(dimer.d_da - 2.617) < 0.002 and dimer.count == 4  # O···O of the dimer; Z = 4
    text = cc.hydrogen_table(bonds, decimal=',')
    assert text.splitlines()[1] == 'O2–H2A···O1^i\t0,82\t1,83\t2,617\t161'
    assert '(i) ' + dimer.code in text


def test_a_code_of_a_translation_and_the_identity():
    data = water_chain()
    bonds = cc.hydrogen_bonds(data, cc.contacts(data, 1.22))
    assert len(bonds) == 1 and bonds[0].code in ('x+1, y, z', 'x-1, y, z')
    assert abs(_d(_at(data, 'O1'), _at(data, 'O1', bonds[0].code)) - 2.9) < 1e-6
    assert cc.code_text(((1, 0, 0), (0, 1, 0), (0, 0, 1)), (0, 0, 0)) == 'x, y, z'
    from fractions import Fraction

    assert cc.code_text(((-1, 0, 0), (0, 1, 0), (0, 0, -1)), (1, Fraction(1, 2), Fraction(1, 2))) == '-x+1, y+1/2, -z+1/2'


def test_the_criteria_of_the_contacts_can_be_changed():
    data = _benzoic()
    default = [c for c in cc.contacts(data) if c.kind == 'hydrogen']
    strict = [c for c in cc.contacts(data, hb_angle=165.0) if c.kind == 'hydrogen']
    assert strict and len(strict) < len(default) and all(c.angle >= 165.0 for c in strict)
    assert not any(c.angle < 165.0 for c in strict) and any(c.angle < 165.0 for c in default)
    near = cc.contacts(data, tolerance=0.0)
    assert len(near) < len(cc.contacts(data)) and all(c.distance <= c.vdw_sum + 1e-9 for c in near)


def test_the_network_grows_layer_by_layer():
    # 0.170.0 (Mercury’s «expand contacts»): the water chain along a — each layer adds the next molecule on both
    # sides (2, 4, 6); the carboxylic dimers of benzoic acid alone are finite: more layers add nothing
    for layers, added in ((1, 2), (2, 4), (3, 6)):
        molecule, count = cc.network(water_chain(), ('hydrogen',), 1.22, layers=layers)
        assert count == added and len(molecule.atoms) == 3 * (1 + added)
    data = _benzoic()
    dimer = [c for c in cc.contacts(data) if c.kind == 'hydrogen' and abs(c.distance - cc.hydrogen_bonds(data, cc.contacts(data))[0].d_ha) < 1e-6]
    one, first = cc.network(data, chosen=dimer, layers=1)
    many, more = cc.network(data, chosen=dimer, layers=5)
    assert 0 < first == more <= 4 and len(one.atoms) == len(many.atoms)
    every, _ = cc.network(data, ('hydrogen',), layers=2)
    assert len(every.atoms) > len(many.atoms)


def test_the_contacts_of_a_network_on_its_model():
    # the H···O pairs of the water chain shown — each between two molecules, at the distance of the contact
    from math import dist

    crystal = water_chain()
    found = cc.contacts(crystal)
    model, _ = cc.network(crystal, ('hydrogen',), layers=2)
    pairs = cc.model_contacts(model, crystal, found, ('hydrogen',))
    assert pairs and all(kind == 'hydrogen' for _, _, kind in pairs)
    hydrogen = next(c for c in found if c.kind == 'hydrogen')
    for i, j, _ in pairs:
        a, b = model.atoms[i], model.atoms[j]
        assert {a.symbol, b.symbol} == {'H', 'O'} and abs(dist(a.position, b.position) - hydrogen.distance) < 0.01
    assert cc.model_contacts(model, crystal, found, ('halogen',)) == []
