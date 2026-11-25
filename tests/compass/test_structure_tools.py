"""modules/compass/chemistry/structure_tools.py: the structure tools of the Compass menus, as in Chemcraft."""

from math import dist

import pytest

from azimuth.core import Atom, Molecule
from modules.compass.chemistry import structure_tools as st

WATER = Molecule('water', (Atom('O', 0.0, 0.0, 0.117), Atom('H', 0.757, 0.0, -0.469), Atom('H', -0.757, 0.0, -0.469)))


def two_waters():
    shifted = tuple(Atom(a.symbol, a.x + 3.0, a.y, a.z) for a in WATER.atoms)
    return Molecule('dimer', WATER.atoms + shifted)


def close(a, b, eps=1e-6):
    return all(abs(x - y) < eps for x, y in zip(a, b))


def test_selection_tools():
    assert st.expand(WATER, [0]) == [0, 1, 2] and st.expand(WATER, [1]) == [0, 1]
    assert st.parse_numbers('1-2, 3', 3) == [0, 1, 2] and st.parse_numbers(' 3–2 ', 3) == [1, 2]
    with pytest.raises(ValueError):
        st.parse_numbers('1, a', 3)
    with pytest.raises(ValueError):
        st.parse_numbers('4', 3)
    assert st.numbers_text([0, 1, 2, 4]) == '1–3, 5'
    assert st.in_box(WATER, (0.0, None, None), (None, None, None)) == [0, 1]
    assert st.pairs([2, 0, 1]) == [(0, 1), (0, 2), (1, 2)]
    assert st.bond_angles(WATER) == [(1, 0, 2)] and st.bond_angles(WATER, [0, 1]) == []


def test_frames_keep_the_distances():
    d = [dist(WATER.atoms[i].position, WATER.atoms[j].position) for i, j in st.pairs(range(3))]
    for m in (st.origin_at(WATER, 1), st.axes_on(WATER, 0, 1, 2), st.along(WATER, 1, 2, 'z'), st.inverted(WATER)):
        assert all(abs(x - dist(m.atoms[i].position, m.atoms[j].position)) < 1e-9 for x, (i, j) in zip(d, st.pairs(range(3))))
    assert close(st.origin_at(WATER, 1).atoms[1].position, (0, 0, 0))
    framed = st.axes_on(WATER, 0, 1, 2)
    assert close(framed.atoms[0].position, (0, 0, 0)) and abs(framed.atoms[1].y) < 1e-9 and abs(framed.atoms[1].z) < 1e-9
    assert framed.atoms[1].x > 0 and abs(framed.atoms[2].z) < 1e-9 and framed.atoms[2].y > 0
    lined = st.along(WATER, 1, 2, 'z')
    assert close(lined.atoms[1].position, (0, 0, 0)) and lined.atoms[2].z > 1.5 and abs(lined.atoms[2].x) < 1e-9
    assert close(st.inverted(WATER).atoms[0].position, (0, 0, -0.117))
    shaken = st.shaken(WATER, 0.01, seed=1)
    assert all(dist(a.position, b.position) <= 0.0174 for a, b in zip(WATER.atoms, shaken.atoms))
    with pytest.raises(ValueError):
        st.axes_on(WATER, 0, 1, 1)


def test_atoms_and_bonds():
    doubled = Molecule('w', WATER.atoms + (Atom('H', 0.757, 0.0, -0.4),))
    assert st.overlapping(doubled) == [3] and st.without(doubled, [3]).atoms == WATER.atoms
    assert st.without_bonds_of(WATER, [1]).bonds == ((0, 2, 1),) or st.without_bonds_of(WATER, [1]).bonds == ((2, 0, 1),)
    assert st.rebonded(Molecule('w', WATER.atoms, ())).bonds is None
    assert [a.symbol for a in st.with_element(WATER, [1, 2], 'F').atoms] == ['O', 'F', 'F']
    m, k = st.with_dummy_at_centre(WATER, [1, 2])
    assert k == 3 and m.atoms[3].symbol == 'X' and close(m.atoms[3].position, (0, 0, -0.469))


def test_data_of_the_structure():
    data = st.inertia(WATER)
    a, b, c = data['moments']
    assert a < b < c and abs(a + b - c) < 1e-6 and data['kind'] == 'asymmetric'  # planar: I_C = I_A + I_B
    assert abs(data['B_cm'][2] * c - st.B_CM) < 1e-9
    framed = st.principal_frame(WATER)
    again = st.inertia(framed)
    assert all(abs(x - y) < 1e-6 for x, y in zip(again['moments'], data['moments']))
    assert st.inertia(Molecule('co2', (Atom('O', 0, 0, -1.16), Atom('C', 0, 0, 0), Atom('O', 0, 0, 1.16))))['kind'] == 'linear'
    s = st.statistics(WATER)
    assert s['atoms'] == {'H': 2, 'O': 1} and s['bonds'] == {'O–H': 2} and s['bond_count'] == 2
    parts = st.fragments(two_waters())
    assert parts == [[0, 1, 2], [3, 4, 5]]
    w = st.masses(WATER)
    assert w['formula'] == 'H2O' and abs(w['exact'] - 18.010565) < 1e-5 and abs(w['average'] - 18.015) < 1e-6 and not w['missing']


# -- «Правка» — the whole molecule, the order of the atoms, all bonds off, shift and turn, planes -------------
def test_whole_molecules_and_the_order_of_atoms():
    from azimuth.core import read_xyz
    from modules.compass.chemistry import structure_tools as st

    two = read_xyz('6\n\nO 0 0 0\nH 0.96 0 0\nH -0.24 0.93 0\nO 5 0 0\nH 5.96 0 0\nH 4.76 0.93 0')
    assert st.whole(two, [4]) == [3, 4, 5] and st.whole(two, [1, 3]) == list(range(6)) and st.whole(two, []) == []
    # the selected first, in the order of the clicks; the others keep theirs
    moved, order = st.selected_first(two, [5, 3])
    assert order == [5, 3, 0, 1, 2, 4] and [a.symbol for a in moved.atoms] == ['H', 'O', 'O', 'H', 'H', 'H']
    assert moved.atoms[0].position == two.atoms[5].position
    # methane written H first: every H after its carbon
    methane = read_xyz('5\n\nH 0 0 1.09\nC 0 0 0\nH 1.03 0 -0.36\nH -0.51 0.89 -0.36\nH -0.51 -0.89 -0.36')
    ordered, order = st.hydrogens_after(methane)
    assert order == [1, 0, 2, 3, 4] and [a.symbol for a in ordered.atoms] == ['C', 'H', 'H', 'H', 'H']
    # stored bonds follow the atoms; «Удалить все связи» leaves none (not «by distance»)
    bonded = two.__class__('w', two.atoms[:3], ((0, 1, 1), (0, 2, 1)))
    assert st.selected_first(bonded, [2])[0].bonds == ((1, 2, 1), (0, 1, 1))  # O was 0, now 1; H2 was 2, now 0
    assert st.without_bonds(bonded).bonds == ()


def test_shift_and_turn():
    from math import dist

    from azimuth.core import read_xyz
    from modules.compass.chemistry import structure_tools as st

    water = read_xyz('3\n\nO 0 0 0\nH 0.96 0 0\nH -0.24 0.93 0')
    # 90° about z through the centre of the atoms, then 1 Å along x: the shape is kept
    turned = st.transformed(water, [], shift=(1, 0, 0), angle=90, axis='z')
    centre = (0.24, 0.31, 0.0)  # (0 + 0.96 − 0.24) / 3, (0 + 0 + 0.93) / 3
    assert all(abs(a - b) < 1e-12 for a, b in zip(turned.atoms[0].position, (centre[0] + 0.31 + 1, centre[1] - 0.24, 0)))
    for i, j in ((0, 1), (0, 2), (1, 2)):
        assert abs(dist(turned.atoms[i].position, turned.atoms[j].position)
                   - dist(water.atoms[i].position, water.atoms[j].position)) < 1e-12
    # only the selected atom, about the O–H1 bond: H2 goes round the axis, O and H1 stay
    flipped = st.transformed(water, [2], angle=180, through=(0, 1))
    assert flipped.atoms[:2] == water.atoms[:2]
    assert all(abs(a - b) < 1e-12 for a, b in zip(flipped.atoms[2].position, (-0.24, -0.93, 0)))


def test_planes_of_two_rings():
    # two hexagons 1.39 Å in radius, parallel, 3.5 Å apart and shifted 1.5 Å — a parallel-displaced π-stack; then the
    # second turned by 30° about the x axis
    from math import cos, radians, sin, sqrt

    import pytest

    from azimuth.core import read_xyz
    from modules.compass.chemistry import structure_tools as st

    ring = [(1.39 * cos(radians(60 * k)), 1.39 * sin(radians(60 * k)), 0.0) for k in range(6)]
    lines = [f'C {x} {y} {z}' for x, y, z in ring] + [f'C {x + 1.5} {y} {z + 3.5}' for x, y, z in ring]
    stack = read_xyz('12\n\n' + '\n'.join(lines))
    r = st.planes(stack, range(6), range(6, 12))
    assert r['angle'] < 1e-6 and abs(r['b_from_a'] - 3.5) < 1e-9 and abs(r['offset'] - 1.5) < 1e-9
    assert abs(r['centres'] - sqrt(3.5 ** 2 + 1.5 ** 2)) < 1e-9 and r['first']['rms'] < 1e-12
    tilted = [(x, y * cos(radians(30)), y * sin(radians(30)) + 3.5) for x, y, _ in ring]
    lines = [f'C {x} {y} {z}' for x, y, z in ring] + [f'C {x} {y} {z}' for x, y, z in tilted]
    assert abs(st.planes(read_xyz('12\n\n' + '\n'.join(lines)), range(6), range(6, 12))['angle'] - 30) < 1e-9
    # a puckered ring: the deviations alternate ±0.2 Å
    chair = read_xyz('6\n\n' + '\n'.join(f'C {x} {y} {0.2 * (-1) ** k}' for k, (x, y, _) in enumerate(ring)))
    p = st.plane(chair, range(6))
    assert abs(p['rms'] - 0.2) < 1e-9 and all(abs(abs(d) - 0.2) < 1e-9 for _, d in p['deviations'])
    with pytest.raises(ValueError):
        st.plane(chair, [0, 1])


def test_internal_coordinates():
    # H2O2 with a 90° dihedral: 3 bonds, 2 angles, 1 dihedral; a dummy atom has none
    from azimuth.core import read_xyz
    from modules.compass.chemistry import structure_tools as st

    peroxide = read_xyz('5\n\nO 0 0 0\nO 1.45 0 0\nH -0.32 0.94 0\nH 1.77 0 0.94\nX 0 0 4')
    found = st.internal_coordinates(peroxide)
    assert [(i, j) for i, j, _ in found['bonds']] == [(0, 1), (0, 2), (1, 3)]
    assert abs(found['bonds'][0][2] - 1.45) < 1e-9
    assert [(i, j, k) for i, j, k, _ in found['angles']] == [(1, 0, 2), (0, 1, 3)]
    (i, j, k, m, phi), = found['dihedrals']
    assert (i, j, k, m) == (2, 0, 1, 3) and abs(abs(phi) - 90) < 1e-6
