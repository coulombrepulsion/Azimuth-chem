"""modules/compass/chemistry/identity.py: the same molecule whatever its atom order and geometry."""

from azimuth.core import Atom, Molecule
from modules.compass.chemistry.identity import find_same, same_shape, same_structure, structure_key


def _ethanol(order=(0, 1, 2)):
    heavy = [Atom('C', 0.0, 0.0, 0.0), Atom('C', 1.52, 0.0, 0.0), Atom('O', 2.0, 1.3, 0.0)]
    atoms = tuple(heavy[i] for i in order)
    index = {old: new for new, old in enumerate(order)}
    bonds = ((index[0], index[1], 1), (index[1], index[2], 1))
    return Molecule('ethanol', atoms, bonds)


def _dimethyl_ether():
    atoms = (Atom('C', 0.0, 0.0, 0.0), Atom('O', 1.4, 0.0, 0.0), Atom('C', 2.0, 1.3, 0.0))
    return Molecule('ether', atoms, ((0, 1, 1), (1, 2, 1)))


def test_the_same_graph_in_another_order_is_the_same_molecule():
    assert same_structure(_ethanol(), _ethanol((2, 0, 1)))
    assert structure_key(_ethanol()) == structure_key(_ethanol((1, 2, 0)))


def test_isomers_are_different_molecules():
    assert not same_structure(_ethanol(), _dimethyl_ether())


def test_the_first_same_one_is_found():
    candidates = [('ether', _dimethyl_ether()), ('ethanol', _ethanol((2, 1, 0)))]
    assert find_same(_ethanol(), candidates) == 1
    assert find_same(_dimethyl_ether(), [('ethanol', _ethanol())]) is None


def _butane(torsion_deg, order=(0, 1, 2, 3), turn=0.0):
    # the carbon chain only: C1–C2–C3–C4 with this torsion; turn — the whole copy turned about z (a copy, moved)
    from math import cos, radians, sin

    t = radians(torsion_deg)
    points = [(-1.25, 0.9, 0.0), (0.0, 0.0, 0.0), (1.54, 0.0, 0.0), (2.79, 0.9 * cos(t), 0.9 * sin(t))]
    c, s = cos(turn), sin(turn)
    points = [(c * x - s * y + 3.0, s * x + c * y - 1.0, z) for x, y, z in points]
    atoms = tuple(Atom('C', *points[i]) for i in order)
    index = {old: new for new, old in enumerate(order)}
    return Molecule('butane', atoms, tuple((index[i], index[i + 1], 1) for i in range(3)))


def test_conformers_are_not_the_same_molecule_again():
    anti, gauche = _butane(180), _butane(60)
    assert same_structure(anti, gauche) and not same_shape(anti, gauche)
    assert find_same(gauche, [('anti', anti)]) is None
    copy = _butane(180, order=(3, 1, 0, 2), turn=1.0)  # the same shape, turned, moved and numbered otherwise
    assert same_shape(anti, copy) and find_same(copy, [('anti', anti)]) == 0
    assert find_same(gauche, [('anti', anti)], shape=False) == 0  # the graph alone
