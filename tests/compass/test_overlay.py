"""Overlay of structures with any atom order (modules/compass/chemistry/overlay.py).

Oracles, independent of the tested search:
  * with noise, the RMSD is never above that of the pairing used to make the copy (an upper bound);
  * the Hungarian method against the minimum over all permutations (itertools) of random matrices;
  * a structure whose atoms are shuffled, turned by a random rotation and shifted: the true pairing
    gives RMSD 0, so the result must have RMSD below the rounding bound B (every library molecule);
  * small molecules with noise: the minimum over every element-preserving permutation of a plain
    Kabsch fit (exhaustive; modules/spectrum/analysis/comparison.py for the fit) must equal the found RMSD;
  * enantiomers (CHFClBr and its mirror image) cannot be superimposed by a proper rotation (the RMSD
    stays large) but are with mirrors allowed (RMSD ~ 0, mirrored);
  * renumbering by the found order gives a structure that comparison.align fits in the plain order.
Bound B: coordinates up to ~10 A, a rotation and a shift in float64 change each coordinate by a few
1e-15 A; the Kabsch fit adds the same order; B = 1e-9 A leaves six orders of margin.
"""

import itertools
import math
import random

import numpy as np
import pytest

from modules.compass.chemistry import library
from modules.compass.chemistry.overlay import assignment, renumber, superimpose
from modules.spectrum.analysis.comparison import align
from azimuth.core import Atom, Molecule

B = 1e-9


def rotation(rng):
    q = np.array([rng.gauss(0, 1) for _ in range(4)])
    w, x, y, z = q / np.linalg.norm(q)
    return np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
        ]
    )


def moved(molecule, rng, noise=0.0, shuffle=True):
    order = list(range(len(molecule.atoms)))
    if shuffle:
        rng.shuffle(order)
    r = rotation(rng)
    shift = np.array([rng.uniform(-5, 5) for _ in range(3)])
    atoms = []
    for j in order:
        a = molecule.atoms[j]
        p = np.array(a.position) @ r + shift + np.array([rng.gauss(0, noise) for _ in range(3)])
        atoms.append(Atom(a.symbol, *map(float, p)))
    return Molecule('moved', tuple(atoms)), order


def test_hungarian_against_all_permutations():
    rng = random.Random(7)
    for n in range(1, 8):
        for _ in range(6):
            cost = np.array([[rng.uniform(-3, 10) for _ in range(n)] for _ in range(n)])
            if rng.random() < 0.3:
                cost = np.round(cost)  # ties
            p = assignment(cost)
            assert sorted(p) == list(range(n))
            best = min(sum(cost[i, q[i]] for i in range(n)) for q in itertools.permutations(range(n)))
            assert sum(cost[i, p[i]] for i in range(n)) == pytest.approx(best, abs=1e-9)


def test_every_library_molecule_is_found_after_shuffle_turn_and_shift():
    rng = random.Random(11)
    for key in library.keys():
        m = library.molecule(key)
        if len(m.atoms) < 2:
            continue
        other, _ = moved(m, rng)
        result = superimpose(m, other)
        assert result.rmsd < B, (key, result.rmsd)
        assert max(result.deviations) < 10 * B
        assert not result.mirrored
        # the renumbered copy pairs atom by atom with the model
        assert [a.symbol for a in result.renumbered.atoms] == [a.symbol for a in m.atoms]
        _, plain = align(result.renumbered, m)
        assert plain < B


def test_with_noise_never_worse_than_the_true_pairing():
    # the pairing used to make the copy is one admissible pairing: the optimum cannot be worse
    rng = random.Random(1)
    for noise in (0.1, 0.3):
        for key in library.keys():
            m = library.molecule(key)
            if len(m.atoms) < 3:
                continue
            other, order = moved(m, rng, noise=noise)
            inverse = [0] * len(order)
            for new, old in enumerate(order):
                inverse[old] = new
            _, true = align(renumber(other, inverse), m)
            assert superimpose(m, other).rmsd <= true + 1e-9, (key, noise)


def exhaustive(reference, other):
    """Minimum Kabsch RMSD over all permutations within each element."""
    sa = [a.symbol for a in reference.atoms]
    sb = [a.symbol for a in other.atoms]
    groups = sorted(set(sa))
    rows = {s: [i for i, t in enumerate(sa) if t == s] for s in groups}
    cols = {s: [i for i, t in enumerate(sb) if t == s] for s in groups}
    best = math.inf
    for choice in itertools.product(*(itertools.permutations(cols[s]) for s in groups)):
        order = [0] * len(sa)
        for s, perm in zip(groups, choice):
            for r, c in zip(rows[s], perm):
                order[r] = c
        _, rmsd = align(renumber(other, order), reference)
        best = min(best, rmsd)
    return best


@pytest.mark.parametrize('prefix', ['Вода', 'Аммиак', 'Метан ·', 'Этен', 'Метаналь', 'Метанол', 'Тетрахлорметан'])
def test_small_molecules_with_noise_against_exhaustive_search(prefix):
    key = next(k for k in library.keys() if k.startswith(prefix))
    rng = random.Random(3)
    m = library.molecule(key)
    for noise in (0.05, 0.25, 0.25):
        other, _ = moved(m, rng, noise=noise)
        found = superimpose(m, other).rmsd
        assert found == pytest.approx(exhaustive(m, other), abs=1e-9)


@pytest.mark.parametrize('prefix', ['Метан ·', 'Тетрахлорметан', 'Тетрафторметан'])
def test_spherical_tops_in_any_orientation(prefix):
    # three equal moments: the principal axes are arbitrary, the sampled rotations must find the fit
    key = next(k for k in library.keys() if k.startswith(prefix))
    m = library.molecule(key)
    rng = random.Random(5)
    for _ in range(25):
        other, _ = moved(m, rng)
        assert superimpose(m, other).rmsd < B


def test_octahedron_in_any_orientation():
    d = 1.56
    sf6 = Molecule(
        'SF6',
        (Atom('S', 0, 0, 0),)
        + tuple(Atom('F', *(d * s * (k == i) for k in range(3))) for i in range(3) for s in (1, -1)),
    )
    rng = random.Random(9)
    for _ in range(25):
        other, _ = moved(sf6, rng)
        assert superimpose(sf6, other).rmsd < B


def test_enantiomers_need_a_mirror():
    # CHFClBr: a tetrahedral centre with four different substituents
    c = Molecule(
        'CHFClBr',
        (
            Atom('C', 0, 0, 0),
            Atom('H', 0.63, 0.63, 0.63),
            Atom('F', -0.78, -0.78, 0.78),
            Atom('Cl', -1.0, 1.0, -1.0),
            Atom('Br', 1.1, -1.1, -1.1),
        ),
    )
    mirror = Molecule('mirror', tuple(Atom(a.symbol, -a.x, a.y, a.z) for a in c.atoms))
    proper = superimpose(c, mirror)
    assert proper.rmsd > 0.3 and not proper.mirrored
    free = superimpose(c, mirror, allow_mirror=True)
    assert free.rmsd < B and free.mirrored


def test_same_order_is_kept_for_identical_files():
    m = library.molecule(library.keys()[0])
    result = superimpose(m, m)
    assert result.same_order and result.rmsd < B


def test_composition_must_agree():
    water = Molecule('w', (Atom('O', 0, 0, 0), Atom('H', 0.96, 0, 0), Atom('H', -0.24, 0.93, 0)))
    peroxide = Molecule('p', (Atom('O', 0, 0, 0), Atom('O', 1.4, 0, 0), Atom('H', -0.3, 0.9, 0)))
    with pytest.raises(ValueError, match='Состав'):
        superimpose(water, peroxide)
    with pytest.raises(ValueError):
        superimpose(water, Molecule('e', ()))


def test_renumber_moves_bonds():
    m = Molecule('m', (Atom('C', 0, 0, 0), Atom('O', 1.2, 0, 0), Atom('H', -0.5, 0.9, 0)), ((0, 1, 2), (0, 2, 1)))
    r = renumber(m, [1, 2, 0])  # new 0 = old O, new 1 = old H, new 2 = old C
    assert [a.symbol for a in r.atoms] == ['O', 'H', 'C']
    assert r.bonds == ((0, 2, 2), (1, 2, 1))
    with pytest.raises(ValueError):
        renumber(m, [0, 0, 1])
