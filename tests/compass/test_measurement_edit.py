from math import dist
import pytest
from azimuth.core import Atom, Molecule
from modules.compass.chemistry.geometry_tools import measurement
from modules.compass.chemistry.transforms import set_measurement


@pytest.fixture
def chain():
    return Molecule(
        'chain',
        (Atom('C', 0, 1, 0), Atom('C', 0, 0, 0), Atom('C', 1, 0, 0), Atom('C', 1, 1, 1), Atom('H', 2, 1, 1)),
        ((0, 1, 1), (1, 2, 1), (2, 3, 1), (3, 4, 1)),
    )


@pytest.mark.parametrize('indices,target', [([1, 2], 1.6), ([0, 1, 2], 120), ([0, 1, 2, 3], -70), ([0, 1, 2, 3], 175)])
@pytest.mark.parametrize('fragment', [False, True])
def test_exact_edit(chain, indices, target, fragment):
    result = set_measurement(chain, indices, target, fragment)
    assert measurement([result.atoms[i].position for i in indices])[1] == pytest.approx(target, abs=1e-6)
    # an angle by fragments — both sides turn about the middle atom (it stays); else the earlier ones stay
    for i in (indices[1:2] if fragment and len(indices) == 3 else indices[:-1]):
        assert result.atoms[i].position == pytest.approx(chain.atoms[i].position)
    if not fragment:
        for i in set(range(5)) - {indices[-1]}:
            assert result.atoms[i] == chain.atoms[i]
    else:
        assert dist(result.atoms[3].position, result.atoms[4].position) == pytest.approx(
            dist(chain.atoms[3].position, chain.atoms[4].position)
        )
    assert result.bonds == chain.bonds


@pytest.mark.parametrize(
    'indices,target', [([0, 1], float('nan')), ([0, 1], -0.1), ([0, 1, 2], 181), ([0, 1, 2, 3], 200), ([0, 0], 1)]
)
def test_invalid_edit(chain, indices, target):
    with pytest.raises(ValueError):
        set_measurement(chain, indices, target)


def test_ring_fragment_rejected_but_last_atom_can_move():
    m = Molecule(
        'ring', (Atom('C', 0, 0, 0), Atom('C', 1, 0, 0), Atom('C', 0, 1, 0)), ((0, 1, 1), (1, 2, 1), (2, 0, 1))
    )
    with pytest.raises(ValueError, match='цикл'):
        set_measurement(m, [0, 1], 1.5, True)
    assert dist(*[a.position for a in set_measurement(m, [0, 1], 1.5, False).atoms[:2]]) == pytest.approx(1.5)


def test_linear_angle_gets_deterministic_plane():
    m = Molecule('linear', (Atom('C', -1, 0, 0), Atom('C', 0, 0, 0), Atom('C', 1, 0, 0)), ((0, 1, 1), (1, 2, 1)))
    result = set_measurement(m, [0, 1, 2], 110)
    assert measurement([a.position for a in result.atoms])[1] == pytest.approx(110)


def test_ethane_demo_distinguishes_fragment_and_last_atom():
    from azimuth.core import EXAMPLES, read_xyz

    m = read_xyz(EXAMPLES['Этан · C₂H₆ · перемещение фрагмента'])
    fragment = set_measurement(m, [0, 1], 1.8, True)
    single = set_measurement(m, [0, 1], 1.8, False)
    for i in [5, 6, 7]:
        assert fragment.atoms[i] != m.atoms[i]
        assert single.atoms[i] == m.atoms[i]
        assert dist(fragment.atoms[1].position, fragment.atoms[i].position) == pytest.approx(
            dist(m.atoms[1].position, m.atoms[i].position)
        )
    assert fragment.atoms[0] == single.atoms[0] == m.atoms[0]


def test_an_angle_by_fragments_moves_both_sides_by_half():
    # methane, the angle H–C–H made 130°
    from modules.compass.chemistry.formats import from_smiles

    m = from_smiles('C')
    h = [i for i, a in enumerate(m.atoms) if a.symbol == 'H']
    before = measurement([m.atoms[i].position for i in (h[0], 0, h[1])])[1]
    both = set_measurement(m, [h[0], 0, h[1]], 130, True)
    single = set_measurement(m, [h[0], 0, h[1]], 130, False)
    for result in (both, single):
        assert measurement([result.atoms[i].position for i in (h[0], 0, h[1])])[1] == pytest.approx(130, abs=1e-6)
        assert result.atoms[0] == m.atoms[0]
    assert both.atoms[h[0]] != m.atoms[h[0]] and both.atoms[h[1]] != m.atoms[h[1]]  # both hydrogens moved
    assert single.atoms[h[0]] == m.atoms[h[0]]  # one atom only: the first stays
    # each by half: the angle of each to its old place is the same
    turn = [measurement([m.atoms[i].position, m.atoms[0].position, both.atoms[i].position])[1] for i in h[:2]]
    assert turn[0] == pytest.approx((130 - before) / 2, abs=1e-6) and turn[1] == pytest.approx((130 - before) / 2, abs=1e-6)
    assert all(both.atoms[i] == m.atoms[i] for i in h[2:])  # the other hydrogens stay
