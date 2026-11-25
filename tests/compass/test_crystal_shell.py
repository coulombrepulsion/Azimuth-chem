"""The molecular shell of a crystal (modules/compass/chemistry/crystal_shell.py).

Oracles, independent of the tested code:
  * an argon atom in a primitive cubic cell of 4 Å: within 4.0 Å the 6 atoms of the faces, within 5.7 Å (√2 · 4 = 5.66)
    also the 12 of the edges (18), within 6.95 Å (√3 · 4 = 6.93) also the 8 of the corners (26) — counted by hand;
  * argon in a face-centred cubic cell of 5.26 Å (the four centring operations): the 12 nearest neighbours at
    a/√2 = 3.72 Å — the closest packing of balls;
  * benzoic acid (the example of the program, P 2₁/n): the symmetry code of each neighbour applied by hand
    (cr.operation of its text) to the coordinates of the file puts its atoms where the shell has them; within 4 Å
    the molecular coordination number is 14 (Kitaigorodsky: 12 or 14 in most organic crystals);
  * rock salt has no molecules: no shell.
"""

from pathlib import Path

import pytest

from modules.compass.chemistry import crystal as cr
from modules.compass.chemistry import crystal_shell as sh
from tests.compass.test_crystal_symmetry import rock_salt

CENTRING = ('x, y, z', 'x, y+1/2, z+1/2', 'x+1/2, y, z+1/2', 'x+1/2, y+1/2, z')


def argon(a, operations=('x, y, z',)):
    return cr.Crystal('Ar', cr.Cell(a, a, a), (cr.Site('Ar1', 'Ar', 0.0, 0.0, 0.0),),
                      tuple(cr.operation(o) for o in operations), 'P 1', (), 1, 'Ar', 1)


def benzoic():
    path = Path(__file__).resolve().parents[2] / 'examples' / '10-crystals' / 'benzoic_acid.cif'
    return cr.parse_cif(path.read_text(encoding='utf-8'))


def test_the_shells_of_a_cubic_lattice():
    for radius, count in ((4.0, 6), (5.7, 18), (6.95, 26)):
        found = sh.shell(argon(4.0), radius=radius)
        assert len(found.neighbours) == count and found.centre_atoms == 1 and len(found.molecule.atoms) == count + 1
    near = sh.shell(argon(5.26, CENTRING), radius=3.8)
    assert len(near.neighbours) == 12 and all(abs(n.distance - 5.26 / 2 ** 0.5) < 1e-9 for n in near.neighbours)


def test_the_codes_of_the_neighbours_put_them_where_they_are():
    data = benzoic()
    found = sh.shell(data, radius=4.0)
    assert len(found.neighbours) == 14
    labels = [s.label for s in data.sites]
    start = found.centre_atoms
    for n in found.neighbours:
        rows, shifts = cr.operation(n.code)
        for k, label in enumerate(labels):  # the atoms of a molecule follow the order of the sites of the file
            site = data.sites[k]
            f = [sum(rows[i][j] * (site.x, site.y, site.z)[j] for j in range(3)) + float(shifts[i]) for i in range(3)]
            want = data.cell.cartesian(f)
            got = found.molecule.atoms[start + k]
            assert abs(got.x - want[0]) + abs(got.y - want[1]) + abs(got.z - want[2]) < 1e-6, (n.code, label)
        start += len(labels)
    assert found.neighbours[0].code == '-x+1, -y, -z+1' and found.neighbours[0].pair == ('H2A', 'O1')  # the dimer
    distances = [n.distance for n in found.neighbours]
    assert distances == sorted(distances) and max(distances) <= 4.0


def test_van_der_waals_contacts_and_the_centre_from_the_model():
    data = benzoic()
    touching = sh.shell(data, radius=0.0, vdw=True)
    assert 0 < len(touching.neighbours) < len(sh.shell(data, radius=4.0).neighbours)
    found = sh.shell(data, radius=4.0)
    atoms = found.molecule.atoms
    centre = sh.locate(data, [(a.x, a.y, a.z) for a in atoms[:found.centre_atoms]])
    assert centre == set(found.centres)
    everything = sh.locate(data, [(a.x, a.y, a.z) for a in atoms])
    assert everything == set(found.centres) | {(n.component, n.translation) for n in found.neighbours}
    other = sh.shell(data, centre=everything - set(found.centres), radius=1.0)  # 14 centres
    assert other.centre_atoms == 14 * found.centre_atoms


def test_a_salt_has_no_shell():
    with pytest.raises(ValueError):
        sh.shell(rock_salt())
