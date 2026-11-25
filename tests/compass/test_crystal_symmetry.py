"""The symmetry of a crystal from its operations; whole molecules (modules/compass/chemistry/crystal_symmetry.py).

Oracles, independent of the tested code:
  * the 32 crystallographic point groups generated here from their textbook generators have the orders of
    the International Tables (1, 2, 2, 2, 4, ... 48) and pairwise different numbers of elements of each type;
  * the elements of P2_1/c, Pnma-like glides, P3_1, P4_2 and Fm-3m named as in ITA vol. A (2_1 along b
    through x = 0, z = 1/4; c-glide perpendicular to b at y = 1/4; the inversion centre at the origin; 3_1;
    4_2; n and b glides), written here by hand;
  * rock salt: F centring, m-3m, Z = 4 from the cell content, rho = 2.164 g/cm3 (4 x 58.443 g/mol over
    N_A x 5.6402^3 A^3; also the value of the Atlas page «Кристаллы»), an infinite framework (3D);
  * an ethanol molecule put across a face of a P2_1/c cell: 4 whole molecules of 9 atoms, each with the
    bond lengths of the free molecule and its centroid inside the cell; Z = 4, Z' = 1;
  * graphite in P1: two infinite layers (2D).
"""

from fractions import Fraction
from itertools import permutations, product
from math import dist, sqrt
from pathlib import Path

from modules.compass.chemistry import crystal as cr
from modules.compass.chemistry import crystal_symmetry as cs

ROOT = Path(__file__).resolve().parents[2]
F = Fraction


def op(text):
    return cr.operation(text)


def test_the_32_point_groups():
    orders = [len(cs._closure(g)) for *_, g in cs.POINT_GROUPS]
    assert orders == [1, 2, 2, 2, 4, 4, 4, 8, 4, 4, 8, 8, 8, 8, 16, 3, 6, 6, 6, 12, 6, 6, 12, 12, 12, 12, 24, 12,
                      24, 24, 24, 48]
    assert len({cs.signature(cs._closure(g)) for *_, g in cs.POINT_GROUPS}) == 32
    numbers = [n for _, _, lo, hi, _ in cs.POINT_GROUPS for n in range(lo, hi + 1)]
    assert numbers == list(range(1, 231))


def test_elements_of_p21c():
    screw = cs.describe(op('-x, y+1/2, -z+1/2'))
    assert screw['symbol'] == '2₁' and screw['axis'] == (0, 1, 0)
    assert screw['point'][0] == 0 and screw['point'][2] == F(1, 4)
    assert 'x = 0' in screw['text'] and 'z = 1/4' in screw['text']
    centre = cs.describe(op('-x, -y, -z'))
    assert centre['symbol'] == '-1' and centre['point'] == (0, 0, 0)
    glide = cs.describe(op('x, -y+1/2, z+1/2'))
    assert glide['symbol'] == 'c' and glide['axis'] == (0, 1, 0) and glide['text'].endswith('y = 1/4')
    assert cs.describe(op('x, y, z'))['symbol'] == '1'


def test_screws_and_glides():
    assert cs.describe(op('-y, x-y, z+1/3'))['symbol'] == '3₁'
    assert cs.describe(op('-y, x-y, z+2/3'))['symbol'] == '3₂'
    assert cs.describe(op('-y, x, z+1/2'))['symbol'] == '4₂'
    assert cs.describe(op('-y, x, z+1/4'))['symbol'] == '4₁'
    assert cs.describe(op('-y, x, z+3/4'))['symbol'] == '4₃'
    b = cs.describe(op('-x+1/2, y+1/2, z'))
    assert b['symbol'] == 'b' and b['axis'] == (1, 0, 0) and b['text'].endswith('x = 1/4')
    n = cs.describe(op('x+1/2, y+1/2, -z'))
    assert n['symbol'] == 'n' and n['axis'] == (0, 0, 1)
    assert cs.describe(op('x+1/4, y+1/4, -z'))['symbol'] == 'd'
    m = cs.describe(op('x, y, -z'))
    assert m['symbol'] == 'm' and m['text'].endswith('z = 0')
    four = cs.describe(op('y, -x, -z'))
    assert four['symbol'] == '-4' and four['point'] == (0, 0, 0)
    t = cs.describe(op('x+1/2, y+1/2, z'))
    assert t['symbol'] == 't'


def rock_salt():
    ops = []
    for perm in permutations(range(3)):
        for signs in product((1, -1), repeat=3):
            rows = [[0, 0, 0] for _ in range(3)]
            for i in range(3):
                rows[i][perm[i]] = signs[i]
            for t in ((0, 0, 0), (0, F(1, 2), F(1, 2)), (F(1, 2), 0, F(1, 2)), (F(1, 2), F(1, 2), 0)):
                ops.append((tuple(map(tuple, rows)), t))
    cell = cr.Cell(5.6402, 5.6402, 5.6402)
    sites = (cr.Site('Na1', 'Na', 0, 0, 0), cr.Site('Cl1', 'Cl', 0.5, 0.5, 0.5))
    return cr.Crystal('NaCl', cell, sites, tuple(ops), 'F m -3 m', (), 225, 'Cl Na', 4)


def test_rock_salt():
    s = cs.analyse(rock_salt())
    assert s.centring == 'F' and s.point_group == 'm-3m' and s.system == 'кубическая' and s.numbers == (221, 230)
    assert s.z == 4 and s.notes == ()
    assert abs(s.density - 4 * (22.990 + 35.45) / 6.02214076e23 / (5.6402 ** 3 * 1e-24)) < 1e-9
    assert abs(s.density - 2.164) < 0.001
    packing = cs.molecules(rock_salt())
    assert packing.molecules == () and [dim for dim, _ in packing.frameworks] == [3]


def ethanol_crystal(formula=True):
    lines = (ROOT / 'examples' / '8-compare' / 'ethanol.xyz').read_text().splitlines()[2:]
    atoms = [(w[0], tuple(float(x) for x in w[1:4])) for w in (line.split() for line in lines) if w]
    cell = cr.Cell(9.0, 10.0, 11.0, 90, 100, 90)
    vectors = cell.vectors()
    # fractional coordinates of the molecule moved so that it sticks out of the face x = 0
    import numpy as np

    inverse = np.linalg.inv(np.array(vectors).T)
    sites = []
    for k, (symbol, r) in enumerate(atoms):
        f = inverse @ (np.array(r) + np.array(cell.cartesian((0.02, 0.3, 0.2))))
        sites.append(cr.Site(f'{symbol}{k}', symbol, *(float(x) for x in f)))
    ops = tuple(op(t) for t in ('x, y, z', '-x, y+1/2, -z+1/2', '-x, -y, -z', 'x, -y+1/2, z+1/2'))
    return cr.Crystal('EtOH', cell, tuple(sites), ops, 'P 1 21/c 1', (), 14, 'C2 H6 O' if formula else '', 0), atoms


def test_whole_molecules_across_the_faces():
    crystal, atoms = ethanol_crystal()
    s = cs.analyse(crystal)
    assert s.point_group == '2/m' and s.centring == 'P' and s.z == 4 and s.z_prime == 1 and s.formula == 'C2H6O'
    packing = cs.molecules(crystal, 1.22)
    assert len(packing.molecules) == 4 and packing.frameworks == ()
    free = sorted(round(dist(a[1], b[1]), 6) for a in atoms for b in atoms if a is not b)
    for molecule in packing.molecules:
        assert len(molecule) == 9
        centre = [sum(f[k] for _, f in molecule) / 9 for k in range(3)]
        assert all(0 <= c < 1 for c in centre)
        xyz = [crystal.cell.cartesian(f) for _, f in molecule]
        mine = sorted(round(dist(p, q), 6) for p in xyz for q in xyz if p is not q)
        assert all(abs(a - b) < 1e-5 for a, b in zip(free, mine))
    molecule, _ = cs.whole_molecules(crystal, (2, 1, 1), 1.22)
    assert len(molecule.atoms) == 72 and 'C2H6O' in packing.text
    plain = cs.analyse(ethanol_crystal(False)[0])
    assert plain.z == 4  # the greatest common divisor of C8 H24 O4


def test_graphite_layers():
    c = cr.parse_cif((ROOT / 'examples' / '10-crystals' / 'graphite_P1.cif').read_text())
    packing = cs.molecules(c)
    assert packing.molecules == () and [dim for dim, _ in packing.frameworks] == [2, 2]


def test_the_number_of_the_file_is_checked():
    crystal = rock_salt()
    wrong = cr.Crystal(crystal.title, crystal.cell, crystal.sites, crystal.operations, '', (), 14, '', 0)
    assert any('14' in note for note in cs.analyse(wrong).notes)
    broken = cr.Crystal('x', cr.Cell(5, 5, 5), crystal.sites, (op('x,y,z'), op('-y,x,z')), '', (), 0, '', 0)
    assert any('не замкнуты' in note for note in cs.analyse(broken).notes)


def test_cif_fields():
    text = (ROOT / 'examples' / '10-crystals' / 'NaCl_rock_salt.cif').read_text()
    text += '\n_space_group_IT_number 225\n_chemical_formula_sum \'Cl Na\'\n_cell_formula_units_Z 4\n'
    c = cr.parse_cif(text)
    assert c.number == 225 and c.formula_sum == 'Cl Na' and c.formula_z == 4
    s = cs.analyse(c)
    assert s.z == 4 and s.point_group == 'm-3m' and s.notes == ()


def test_the_elements_inside_the_cell():
    # P2_1/c inside one cell, its faces included (ITA vol. A, the diagram of No. 14): 2_1 axes along b at
    # x = 0, 1/2, 1 and z = 1/4, 3/4 (6); inversion centres at every point with coordinates 0, 1/2, 1 (27); c-glide
    # planes at y = 1/4 and 3/4 (2)
    from collections import Counter

    crystal, _ = ethanol_crystal()
    found = cs.elements(crystal)
    assert Counter(e['symbol'] for e in found) == {'2₁': 6, '-1': 27, 'c': 2}
    glide = next(e for e in found if e['symbol'] == 'c')
    assert len(glide['frac']) == 4 and {round(p[1], 9) for p in glide['frac']} in ({0.25}, {0.75})
    square = cs._clip_plane((1, 1, 0), 1)
    assert len(square) == 4 and all(abs(p[0] + p[1] - 1) < 1e-12 for p in square)
    assert cs._clip_line((0, 0, 0), (1, 1, 1)) == ((0, 0, 0), (1, 1, 1))
    assert cs._clip_line((0.5, 0.5, 2), (1, 0, 0)) is None


def test_packing_coefficient_of_touching_spheres():
    # argon (Bondi 1.88 A) as touching spheres: simple cubic a = 2r gives pi/6 = 0.5236, face-centred
    # a = 2 sqrt 2 r gives pi/(3 sqrt 2) = 0.7405; an empty-looking cell of one atom in 10 A gives 4/3 pi r^3 / 1000
    from math import pi

    r = 1.88
    one = (cr.Site('Ar1', 'Ar', 0, 0, 0),)
    simple = cr.Crystal('sc', cr.Cell(2 * r, 2 * r, 2 * r), one, (op('x,y,z'),))
    assert abs(cs.packing_coefficient(simple) - pi / 6) < 0.01
    corners = ('x,y,z', 'x,y+1/2,z+1/2', 'x+1/2,y,z+1/2', 'x+1/2,y+1/2,z')
    fcc = cr.Crystal('fcc', cr.Cell(*(2 * sqrt(2) * r,) * 3), one, tuple(op(t) for t in corners))
    assert abs(cs.packing_coefficient(fcc) - pi / (3 * sqrt(2))) < 0.01
    lone = cr.Crystal('lone', cr.Cell(10, 10, 10), (cr.Site('Ar1', 'Ar', 0.5, 0.5, 0.5),), (op('x,y,z'),))
    assert abs(cs.packing_coefficient(lone) - 4 / 3 * pi * r ** 3 / 1000) < 0.003


def test_coordination_polyhedra():
    # an octahedron has 8 triangular faces, a cube 6 squares, a tetrahedron 4 triangles; points in a plane — none;
    # rock salt 2 x 2 x 2: the Na inside the block are octahedra of 6 Cl
    octahedron = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
    faces = cs.hull_faces(octahedron)
    assert len(faces) == 8 and all(len(f) == 3 for f in faces)
    cube = [(x, y, z) for x in (0, 1) for y in (0, 1) for z in (0, 1)]
    faces = cs.hull_faces(cube)
    assert len(faces) == 6 and all(len(f) == 4 for f in faces)
    assert len(cs.hull_faces([(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)])) == 4
    assert cs.hull_faces([(0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0)]) == []
    block = cr.build(rock_salt(), (2, 2, 2), True)
    found = cs.polyhedra(block)
    assert len(found) == 13 and all(symbol == 'Na' and len(f) == 8 for _, symbol, f in found)  # the 13 Na inside
    text = (ROOT / 'examples' / '10-crystals' / 'CsCl.cif').read_text()
    cubes = cs.polyhedra(cr.build(cr.parse_cif(text), (2, 2, 2), True))
    assert any(symbol == 'Cs' and len(f) == 6 for _, symbol, f in cubes)


def test_z_of_a_molecular_crystal_counts_its_molecules():
    # «CCl, Z = 12,
    # Z′ = 3» — the formula unit is the molecule: C6Cl6, Z = 2, Z′ = ½ (P21/c, the molecule on an inversion centre)
    from fractions import Fraction
    from pathlib import Path

    from modules.compass.chemistry import crystal as cr
    from modules.compass.chemistry import crystal_energetics as ce
    from modules.compass.chemistry import crystal_symmetry as cs

    crystal = cr.parse_cif((Path(__file__).resolve().parents[1] / 'data' / 'crystal' / 'clbenz.cif').read_text())
    found = cs.analyse(crystal)
    assert (found.formula, found.z, found.z_prime) == ('C6Cl6', 2, Fraction(1, 2))
    assert cs.empirical_formula(crystal) == 'C6Cl6'
    assert 'нет металлов' in ce.ionic_problem(crystal)  # no H, yet molecular: the ionic model is grey
