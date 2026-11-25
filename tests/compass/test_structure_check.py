"""«Проверить структуру», явная сольватация, протоны (modules/compass/chemistry/structure_check.py).

Oracles: the counts of electrons and the parities written by hand; distances set by construction; the library
molecules (water, methanol) whose valences are known.
"""

from math import dist

from azimuth.core import Atom, Molecule, read_xyz
from modules.compass.chemistry import library, structure_check as sc

WATER = read_xyz('3\nwater\nO 0 0 0.117\nH 0.757 0 -0.469\nH -0.757 0 -0.469\n')


def levels(problems):
    return [p.level for p in problems]


def test_a_good_water_has_nothing_to_say():
    assert sc.check(WATER, 0, 1) == []


def test_the_multiplicity_against_the_electrons():
    assert levels(sc.check(WATER, 0, 2)) == ['error']  # 10 electrons — 1, 3, …
    assert sc.check(WATER, 1, 2) == [] or 'error' not in levels(sc.check(WATER, 1, 2))  # 9 electrons — 2
    assert 'error' in levels(sc.check(WATER, 1, 1))


def test_atoms_on_top_of_each_other():
    crowded = Molecule('x', WATER.atoms + (Atom('H', 0.75, 0.0, -0.45),), None)
    found = [p for p in sc.check(crowded, 0, 2) if p.level == 'error']  # 11 electrons: a doublet
    assert found and set(found[0].atoms) == {1, 3}


def test_a_missing_hydrogen_and_a_neutral_ammonium():
    oh = Molecule('OH', (WATER.atoms[0], WATER.atoms[1]), None)  # a hydroxyl: O with one bond
    assert any(p.level == 'warning' and p.atoms == (0,) for p in sc.check(oh, 0, 1))
    assert all(p.level != 'warning' for p in sc.check(oh, 0, 2))  # a radical asked for: a note at most
    ammonium, _ = sc.protonate(library.molecule('Аммиак · NH₃'), 0)
    assert any('N⁺' in p.text for p in sc.check(ammonium, 0, 1))
    assert not any('N⁺' in p.text for p in sc.check(ammonium, 1, 1))


def test_two_parts_are_a_note():
    far = Molecule('2', WATER.atoms + tuple(Atom(a.symbol, a.x + 6, a.y, a.z) for a in WATER.atoms), None)
    assert levels(sc.check(far, 0, 1)) == ['note']


def test_solvation_puts_whole_molecules_without_overlaps_and_repeats():
    water = library.molecule('Вода · H₂O')
    solvated, placed = sc.solvate(WATER, water, 6, seed=3, shell=False)
    assert placed == 6 and len(solvated.atoms) == 3 + 6 * 3
    for k in range(3, len(solvated.atoms), 3):
        new = solvated.atoms[k:k + 3]
        others = solvated.atoms[:k]
        assert min(dist(a.position, b.position) for a in new for b in others) >= 2.0 - 1e-9
    again, _ = sc.solvate(WATER, water, 6, seed=3, shell=False)
    assert again == solvated
    assert sc.check(solvated, 0, 1)[0].level == 'note'  # seven parts — said, not an error


def test_protons_on_and_off_and_carried():
    methanol = library.molecule('Метанол · CH₄O')
    oxygen = next(k for k, a in enumerate(methanol.atoms) if a.symbol == 'O')
    on, h = sc.protonate(methanol, oxygen)
    assert len(on.atoms) == len(methanol.atoms) + 1 and on.atoms[h].symbol == 'H'
    assert 0.9 < dist(on.atoms[h].position, on.atoms[oxygen].position) < 1.05
    off, owner = sc.deprotonate(on, h)
    assert len(off.atoms) == len(methanol.atoms) and owner == oxygen
    anion, _ = sc.deprotonate(methanol, oxygen)
    assert anion.formula == 'CH3O'
    carbon = next(k for k, a in enumerate(methanol.atoms) if a.symbol == 'C')
    hydroxyl = next(j if i == oxygen else i for i, j, _ in methanol.bonds
                    if oxygen in (i, j) and methanol.atoms[j if i == oxygen else i].symbol == 'H')
    moved, new = sc.move_proton(methanol, hydroxyl, carbon)
    assert moved.formula == methanol.formula and moved.atoms[new].symbol == 'H'
    assert dist(moved.atoms[new].position, moved.atoms[carbon if carbon < hydroxyl else carbon - 1].position) < 1.2


def test_the_first_shell_is_held_by_hydrogen_bonds():
    # methanol has one acceptor (O) and one donor (its O–H): two waters, each in a hydrogen bond at 1.9 Å, O···O near
    # 2.8–2.9 Å
    methanol = library.molecule('Метанол · CH₄O')
    water = library.molecule('Вода · H₂O')
    oxygen = next(k for k, a in enumerate(methanol.atoms) if a.symbol == 'O')
    solvated, placed = sc.solvate(methanol, water, 2, seed=5)
    assert placed == 2
    n = len(methanol.atoms)
    for start in (n, n + 3):
        piece = solvated.atoms[start:start + 3]
        o = next(a for a in piece if a.symbol == 'O')
        assert 2.6 < dist(o.position, methanol.atoms[oxygen].position) < 3.1  # O–H···O or O···H–O
        others = [a for k, a in enumerate(solvated.atoms[:start])]
        heavy = [dist(a.position, b.position) for a in piece for b in others if a.symbol != 'H' and b.symbol != 'H']
        assert min(heavy) > 2.4
    # a solvent without hydrogens to give (THF) takes the donor of the structure only, the rest round it
    thf = library.molecule('Оксолан (тетрагидрофуран) · C₄H₈O')
    solvated, placed = sc.solvate(methanol, thf, 1, seed=5)
    o_thf = next(a for a in solvated.atoms[n:] if a.symbol == 'O')
    assert placed == 1 and 2.6 < dist(o_thf.position, methanol.atoms[oxygen].position) < 3.1


def test_the_places_of_the_first_shell_are_counted():
    methanol = library.molecule('Метанол · CH₄O')
    water = library.molecule('Вода · H₂O')
    assert sc.shell_places(methanol, water) == 3  # the two lone pairs of its O and its O–H
    assert sc.shell_places(methanol, library.molecule('Бензол · C₆H₆')) == 0
    report = {}
    _, placed = sc.solvate(methanol, water, 5, seed=5, report=report)
    assert placed == 5 and report == {'shell': 3, 'places': 3, 'taken': 0}
    # run again, the waters put
    # before are not sites; two of the three places are taken, the third is filled now
    solvated, _ = sc.solvate(methanol, water, 2, seed=5)
    report = {}
    again, placed = sc.solvate(solvated, water, 3, seed=7, report=report)
    assert placed == 3 and report == {'shell': 1, 'places': 1, 'taken': 2}
    # the new ones stand round methanol — each nearer to a methanol atom than ~5.5 Å, not out on the old waters
    n = len(solvated.atoms)
    for start in range(n, len(again.atoms), 3):
        piece = again.atoms[start:start + 3]
        assert min(dist(a.position, b.position) for a in piece for b in methanol.atoms) < 5.5


def test_the_solvent_is_taken_away():
    methanol = library.molecule('Метанол · CH₄O')
    solvated, _ = sc.solvate(methanol, library.molecule('Вода · H₂O'), 4, seed=5)
    clean, removed = sc.without_solvent(solvated)
    assert removed == 4 and clean.formula == methanol.formula and len(clean.atoms) == len(methanol.atoms)
    assert sc.without_solvent(methanol) == (methanol, 0)  # nothing round it
    assert sc.without_solvent(WATER)[1] == 0  # water alone is the structure, not a solvent
    ammonia = library.molecule('Аммиак · NH₃')  # a small structure in a bigger solvent stays the structure
    in_benzene, _ = sc.solvate(ammonia, library.molecule('Бензол · C₆H₆'), 2, seed=2)
    assert sc.without_solvent(in_benzene)[0].formula == 'H3N'


CAFFEINE = read_xyz("""24
caffeine
O 0.4700 2.5688 0.0006
O -3.1271 -0.4436 -0.0003
N -0.9686 -1.3125 0.0000
N 2.2182 0.1412 -0.0003
N -1.3477 1.0797 -0.0001
N 1.4119 -1.9372 0.0002
C 0.8579 0.2592 -0.0008
C 0.3897 -1.0264 -0.0004
C 0.0307 1.4220 -0.0006
C -1.9061 -0.2495 -0.0004
C 2.5032 -1.1998 0.0003
C -1.4276 -2.6960 0.0008
C 3.1926 1.2061 0.0003
C -2.2969 2.1881 0.0007
H 3.5163 -1.5787 0.0008
H -1.0451 -3.1973 -0.8937
H -2.5186 -2.7596 0.0011
H -1.0447 -3.1963 0.8957
H 4.1992 0.7801 0.0002
H 3.0468 1.8092 -0.8992
H 3.0466 1.8083 0.9004
H -1.8087 3.1651 -0.0003
H -2.9322 2.1027 0.8881
H -2.9346 2.1021 -0.8849
""")


def test_a_flat_nitrogen_is_not_an_acceptor():
    # its three N–CH₃ are flat (their lone pairs in the rings) — only
    # the two O and the N of the five-membered ring take a hydrogen bond; ammonia (pyramidal) does
    acceptors, donors, taken = sc.solute_sites(CAFFEINE)
    # two lone pairs on each carbonyl O, one on the ring N
    assert sorted(CAFFEINE.atoms[k].symbol for k, _ in acceptors) == ['N', 'O', 'O', 'O', 'O'] and donors == []
    assert taken == 0
    assert [k for k, _ in sc.solute_sites(library.molecule('Аммиак · NH₃'))[0]] == [0]
    water = library.molecule('Вода · H₂O')
    report = {}
    first, _ = sc.solvate(CAFFEINE, water, 8, report=report)
    assert report == {'shell': 5, 'places': 5, 'taken': 0}
    report = {}
    sc.solvate(first, water, 8, report=report)  # again: the five places are taken by the waters of before
    assert report == {'shell': 0, 'places': 0, 'taken': 5}


def test_the_first_shell_alone():
    water = library.molecule('Вода · H₂O')
    shelled, placed = sc.solvate(CAFFEINE, water, sc.shell_places(CAFFEINE, water), around=False)
    assert placed == 5 and len(shelled.atoms) == len(CAFFEINE.atoms) + 15
    report = {}
    assert sc.solvate(shelled, water, sc.shell_places(shelled, water), around=False, report=report)[1] == 0
    assert report == {'shell': 0, 'places': 0, 'taken': 5}  # full: the message says the five are taken
    # water round water: four — two on its lone pairs, two on its hydrogens (a tetrahedron)
    assert sc.solvate(water, water, sc.shell_places(water, water), around=False)[1] == 4
