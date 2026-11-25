"""User fragments (modules/compass/chemistry/user_fragments.py).

Oracles, independent of the tested frame construction:
  * all interatomic distances of the cut group equal those in the model (a rigid motion keeps them);
    the signed volume of four atoms keeps its sign (no reflection: a chiral group keeps its hand);
  * the outside neighbour, moved by the same motion, lies on the -X axis at the bond length (the
    convention of builder.place_fragment), the attachment atom at the origin;
  * placed back with editing.substitute on a hydrogen of benzene, the methyl cut from toluene gives a
    structure whose carbons modules/compass/chemistry/overlay.superimpose matches to toluene with RMSD < 0.1 A
    (only the C-C length of the builder differs) and whose methyl keeps its H-H distances (its turn
    about the bond is free in substitute);
  * a stored and re-read set is the same set (to ROUND decimals), damaged files are refused.
Bound: distances after the motion to 1e-12 A (a few roundings of 1e-16 relative on ~10 A).
"""

from itertools import combinations
from math import dist

import pytest

from modules.compass.chemistry import builder, library
from modules.compass.chemistry.editing import substitute
from modules.compass.chemistry.overlay import superimpose
from modules.compass.chemistry import user_fragments as uf
from modules.compass.chemistry.builder import connections
from azimuth.core import Atom, Molecule


def find(prefix):
    return library.molecule(next(k for k in library.keys() if k.startswith(prefix)))


def volume(a, b, c, d):
    u = [b[k] - a[k] for k in range(3)]
    v = [c[k] - a[k] for k in range(3)]
    w = [d[k] - a[k] for k in range(3)]
    return u[0] * (v[1] * w[2] - v[2] * w[1]) - u[1] * (v[0] * w[2] - v[2] * w[0]) + u[2] * (v[0] * w[1] - v[1] * w[0])


def methyl_of(toluene):
    """Indices of the methyl carbon of toluene and its three hydrogens."""
    bonds = connections(toluene)
    for i, a in enumerate(toluene.atoms):
        if a.symbol != 'C':
            continue
        hs = [j if k == i else k for k, j, _ in bonds if i in (k, j) and toluene.atoms[j if k == i else k].symbol == 'H']
        if len(hs) == 3:
            return i, hs
    raise AssertionError('no methyl')


def test_cut_keeps_distances_hand_and_the_open_bond_on_minus_x():
    toluene = find('Метилбензол')
    c, hs = methyl_of(toluene)
    atoms, bonds = uf.cut(toluene, hs + [c])  # the order of choice does not matter
    assert atoms[0][0] == 'C' and atoms[0][1:] == (0.0, 0.0, 0.0)  # the attachment atom first, at the origin
    assert sorted(bonds) == [(0, 1, 1), (0, 2, 1), (0, 3, 1)]
    original = [toluene.atoms[i].position for i in [c] + hs]
    placed = [a[1:] for a in atoms]
    for i, j in combinations(range(4), 2):
        assert dist(placed[i], placed[j]) == pytest.approx(dist(original[i], original[j]), abs=1e-12)
    assert volume(*placed) * volume(*original) > 0
    ring = next(j if k == c else k for k, j, _ in connections(toluene) if c in (k, j) and toluene.atoms[j if k == c else k].symbol == 'C')
    length = dist(toluene.atoms[ring].position, toluene.atoms[c].position)
    # the ring carbon in the fragment frame: distances to the four atoms are kept, so it is at -length on X
    target = (-length, 0.0, 0.0)
    for p, q in zip(placed, original):
        assert dist(target, p) == pytest.approx(dist(toluene.atoms[ring].position, q), abs=1e-9)


def test_methyl_cut_from_toluene_rebuilds_toluene_on_benzene():
    toluene = find('Метилбензол')
    benzene = find('Бензол')
    c, hs = methyl_of(toluene)
    atoms, bonds = uf.cut(toluene, [c] + hs)
    uf.register({'Мой метил': (atoms, bonds)})
    try:
        h = next(i for i, a in enumerate(benzene.atoms) if a.symbol == 'H')
        rebuilt = substitute(benzene, h, 'Мой метил')
        result = superimpose(toluene, rebuilt)
        assert result.rmsd_heavy < 0.1  # carbons: only the C-C length of the builder differs
        # the methyl itself is rigid: its H-H distances are those of toluene (its turn about the bond is free)
        rc, rhs = methyl_of(rebuilt)
        assert sorted(dist(rebuilt.atoms[a].position, rebuilt.atoms[b].position) for a, b in combinations(rhs, 2)) == (
            pytest.approx(sorted(dist(toluene.atoms[a].position, toluene.atoms[b].position) for a, b in combinations(hs, 2)), abs=1e-9)
        )
        assert 'Мой метил' in builder.FRAGMENT_GROUPS[uf.USER_GROUP]
    finally:
        uf.register({})
    assert 'Мой метил' not in builder.FRAGMENTS and uf.USER_GROUP not in builder.FRAGMENT_GROUPS


def test_group_with_two_open_bonds_is_refused():
    ethanol = find('Этанол')
    carbons = [i for i, a in enumerate(ethanol.atoms) if a.symbol == 'C']
    middle = next(
        i for i in carbons if any(ethanol.atoms[j if k == i else k].symbol == 'O' for k, j, _ in connections(ethanol) if i in (k, j))
    )
    with pytest.raises(ValueError, match='несколько связей'):
        uf.cut(ethanol, [middle])  # bonded to C, O and two H outside


def test_whole_molecule_uses_the_first_chosen_atom_and_a_free_direction():
    water = find('Вода')
    o = next(i for i, a in enumerate(water.atoms) if a.symbol == 'O')
    atoms, bonds = uf.cut(water, [o] + [i for i in range(3) if i != o])
    assert atoms[0][0] == 'O' and len(bonds) == 2
    # the open bond (-X) points away from both hydrogens
    assert all(a[1] > 0 for a in atoms[1:])


def test_store_and_read_again():
    toluene = find('Метилбензол')
    c, hs = methyl_of(toluene)
    frag = {'CH₃ из толуола': uf.cut(toluene, [c] + hs), 'Вода целиком': uf.cut(find('Вода'), [0, 1, 2])}
    text = uf.dump(frag)
    back = uf.parse(text)
    assert list(back) == list(frag)
    for key in frag:
        assert back[key][1] == frag[key][1]
        for a, b in zip(back[key][0], frag[key][0]):
            assert a[0] == b[0] and max(abs(a[k] - b[k]) for k in (1, 2, 3)) <= 0.5e-6 + 1e-12
    assert uf.dump(back) == text  # a fixed point


@pytest.mark.parametrize(
    'text',
    [
        'not json',
        '{"version": 2, "fragments": []}',
        '{"version": 1, "fragments": [{"key": "", "atoms": [["C", 0, 0, 0]]}]}',
        '{"version": 1, "fragments": [{"key": "x", "atoms": [["Xx", 0, 0, 0]]}]}',
        '{"version": 1, "fragments": [{"key": "x", "atoms": [["C", 1, 0, 0]]}]}',
        '{"version": 1, "fragments": [{"key": "x", "atoms": [["C", 0, 0, 0], ["H", 1, 0, 0]], "bonds": [[0, 2, 1]]}]}',
        '{"version": 1, "fragments": [{"key": "x", "atoms": [["C", 0, 0, 0], ["H", 1, 0, 0]], "bonds": [[0, 1, 4]]}]}',
        '{"version": 1, "fragments": [{"key": "x", "atoms": [["C", 0, 0, 0], ["H", "nan", 0, 0]]}]}',
        '{"version": 1, "fragments": [{"key": "x", "atoms": [["C", 0, 0, 0]]}, {"key": "x", "atoms": [["C", 0, 0, 0]]}]}',
    ],
)
def test_damaged_files_are_refused(text):
    with pytest.raises(ValueError):
        uf.parse(text)


def test_names():
    assert uf.check_name('  Мой   фрагмент ') == 'Мой фрагмент'
    with pytest.raises(ValueError):
        uf.check_name('')
    with pytest.raises(ValueError):
        uf.check_name('Метил · —CH₃')  # built in
    with pytest.raises(ValueError):
        uf.check_name('x', taken={'x'})
    with pytest.raises(ValueError):
        uf.check_name('a' * 61)


def test_empty_and_bad_choice():
    m = Molecule('m', (Atom('C', 0, 0, 0),))
    with pytest.raises(ValueError):
        uf.cut(m, [])
    with pytest.raises(ValueError):
        uf.cut(m, [3])
    atoms, bonds = uf.cut(m, [0])
    assert atoms == (('C', 0.0, 0.0, 0.0),) and bonds == ()
