"""The Atlas topic on the bond through orbitals (bonding.html): the model quas_atlas.core.bonding and its endpoints; no
Qt, no browser.

Oracles — lecture 11 of the course «Квантово-химические методы»: a rotation of two occupied orbitals does not change
the determinant, the energy or the density, but F̂φ′ ≠ εφ′ (derivation 4); λ² = −1/cosθ: 109.5° — sp³, 120° — sp²,
180° — sp, water 104.5° — sp⁴ with 20 % s and the lone pairs 30 % s, sp^2.3 (derivation 5); E(2) = −n F²/Δε as the
second-order limit of the 2 × 2 problem (derivation 6); s = |∇ρ|/(2(3π²)^{1/3}ρ^{4/3}) small at a small ρ only between
fragments, λ2 < 0 attraction, λ2 > 0 repulsion (derivation 10).
"""

import math
import sys

import pytest

from modules.atlas.paths import ATLAS_HOME

if str(ATLAS_HOME) not in sys.path:
    sys.path.insert(0, str(ATLAS_HOME))

from quas_atlas import api, pages  # noqa: E402,F401  (pages registers the endpoints)
from quas_atlas.core import bonding  # noqa: E402


def test_rotation_keeps_the_density():
    for t in (0, 17, 45, -60):
        r = bonding.rotate(t)
        assert r['at']['drho'] < 1e-12
        assert r['at']['e1'] + r['at']['e2'] == pytest.approx(-1.1)  # the trace of F is invariant
    assert bonding.rotate(0)['at']['f12'] == 0 and bonding.rotate(45)['at']['f12'] == pytest.approx(0.1)
    best = min(bonding.rotate(0)['spread'], key=lambda p: p[1])
    assert abs(best[0]) == 45  # the Boys orbitals: each on its own bond


def test_hybrids_from_the_angle():
    assert bonding.hybrid(math.degrees(math.acos(-1 / 3)), 2)['at']['lam2'] == pytest.approx(3)
    assert bonding.hybrid(120, 2)['at']['lam2'] == pytest.approx(2)
    assert bonding.hybrid(180, 2)['at']['lam2'] == pytest.approx(1)
    w = bonding.hybrid(104.5, 2)['at']
    assert round(w['s_bond'], 2) == 0.20 and round(w['s_lp'], 2) == 0.30 and round(w['lam2_lp'], 1) == 2.3
    assert round(w['lam2']) == 4
    n = bonding.hybrid(106.7, 3)['at']
    assert 0 < n['s_bond'] < 0.25 and n['s_lp'] == pytest.approx(1 - 3 * n['s_bond'])
    with pytest.raises(ValueError):
        bonding.hybrid(130, 3)


def test_e2_is_the_second_order_of_the_two_by_two():
    r = bonding.e2(0.01, 0.6, 2)
    assert r['at']['pt'] == pytest.approx(2 * 0.01 ** 2 / 0.6 * bonding.HARTREE_KJ)
    assert r['at']['exact'] == pytest.approx(r['at']['pt'], rel=1e-3)
    big = bonding.e2(0.3, 0.6, 2)['at']
    assert big['pt'] > big['exact']  # the perturbative estimate overshoots at a strong coupling
    assert bonding.e2(0.05, 1.2, 2)['at']['pt'] == pytest.approx(bonding.e2(0.05, 0.6, 2)['at']['pt'] / 2)


def test_nci_spikes():
    one = bonding.nci('one', 4)
    assert min(s for r, s in one['pts'] if abs(r) < 0.03) > 0.5  # no small s at a small density
    dim = bonding.nci('dimer', 4)
    low = [r for r, s in dim['pts'] if s < 0.2]
    assert low and all(r < 0 for r in low) and dim['mid'] == pytest.approx(-max(low), abs=0.003)
    ring = bonding.nci('ring', 4)
    assert any(r > 0 for r, s in ring['pts'] if s < 0.2) and any(r < 0 for r, s in ring['pts'] if s < 0.2)
    assert bonding.nci('dimer', 6)['mid'] < dim['mid']  # farther — a weaker contact


def test_eigenvalues_of_a_symmetric_matrix():
    assert bonding._eig3([[2, 0, 0], [0, -1, 0], [0, 0, 3]]) == [-1, 2, 3]
    v = bonding._eig3([[2, 1, 0], [1, 2, 0], [0, 0, 5]])
    assert v == pytest.approx([1, 3, 5])


def test_the_endpoints():
    assert api.call('bond.rotate', {'theta': 45})['theta'] == 45
    assert api.call('bond.hybrid', {'angle': 120, 'nb': 2})['at']['lam2'] == pytest.approx(2)
    assert api.call('bond.e2', {'F': 0, 'gap': 0.6, 'n': 2})['at']['exact'] == 0
    assert api.call('bond.nci', {'kind': 'one', 'd': 4})['mid'] is None
    with pytest.raises(Exception):
        api.call('bond.nci', {'kind': 'trimer', 'd': 4})
    for name in ('bond.rotate', 'bond.hybrid', 'bond.e2', 'bond.nci'):
        assert name in api.REGISTRY
