"""The Atlas topic on conical intersections and biradicals (conical.html): the model quas_atlas.core.conical and its
endpoints; no Qt, no browser.

Oracles — lecture 7 of the course «Квантово-химические методы»: E± = H̄ ± √(Δ² + H12²), the gap 2|H12| (derivation 5);
the seam of dimension N_int − 2, ethylene 12 → 10 (TD-DFT one less condition); the cone E± = Ē ± √(g²x² + h²y²) and the
demonstration's gap 2|hy| = 0.36 at h = 0.6, y = 0.3 (derivation 6); the two-centre model ΔE_ST ≈ 4t²/U − 2K
(derivation 7); the Yamaguchi formula and p-benzyne: E_T − E_BS = 10.3 kJ/mol, ⟨S²⟩_BS = 1 → about 21 (derivation 8);
the benzynes 157 / 88 / 16 kJ/mol (Wenthold, Squires, Lineberger 1998).
"""

import sys

import pytest

from modules.atlas.paths import ATLAS_HOME

if str(ATLAS_HOME) not in sys.path:
    sys.path.insert(0, str(ATLAS_HOME))

from quas_atlas import api, pages  # noqa: E402,F401  (pages registers the endpoints)
from quas_atlas.core import conical  # noqa: E402


def test_avoided_and_true_crossing():
    a = conical.cross(0.1, 0)
    assert a['gap'] == pytest.approx(0.2) and not a['crossing']
    i = a['x'].index(min(a['x'], key=abs))
    assert a['hi'][i] - a['lo'][i] == pytest.approx(0.2)
    b = conical.cross(0.1, 1)
    assert b['crossing'] and b['gap'] == 0
    assert all(h >= l for h, l in zip(a['hi'], a['lo']))


def test_the_cone_and_the_seam():
    c = conical.cone(1.0, 0.6, 0.3, 0.0, 0, 6)
    assert c['gap_y0'] == pytest.approx(0.36)
    assert (c['n_int'], c['seam'], c['seam_tddft']) == (12, 10, 11)
    j0, i0 = c['y'].index(0.0), c['x'].index(0.0)
    assert c['gap'][j0][i0] == 0 and min(min(r) for r in c['gap']) == 0
    td = conical.cone(1.0, 0.6, 0.3, 0.0, 1, 6)
    assert td['gap_y0'] == 0 and all(row[i0] == 0 for row in td['gap'])  # a whole line of degeneracy
    assert conical.cone(atoms=2)['seam'] < 0  # a diatomic: no seam of one symmetry


def test_the_two_centre_model():
    r = conical.twosite(0.5, 4.0, 0.0)
    assert r['at']['approx'] == pytest.approx(0.25 * conical.EV_KJ)
    assert r['at']['exact'] == pytest.approx((5 ** 0.5 - 2) * conical.EV_KJ)  # 0.236 eV
    assert conical.twosite(0.0, 4.0, 0.02)['at']['exact'] < 0  # no hopping: the triplet (Hund)
    t = [b['t_fit'] for b in r['benzynes']]
    assert t[0] > t[1] > t[2] > 0  # o > m > p
    for b in r['benzynes']:
        assert conical._exact(b['t_fit'], 4.0, 0.0)[0] * conical.EV_KJ == pytest.approx(b['exp'], abs=1e-6)


def test_yamaguchi_and_p_benzyne():
    y = conical.yamaguchi(10.3, 1.0)
    assert y['at']['dest'] == pytest.approx(20.6) and round(y['at']['dest']) == 21 and y['at']['w'] == 0.5
    assert y['at']['ziegler'] == pytest.approx(20.6) and y['exp'] == 16
    v = {m['name']: m['value'] for m in y['methods']}
    assert v['RKS'] < 0 < v['CASSCF'] < v['NEVPT2'] < y['exp']
    assert conical.yamaguchi(10.3, 0.0)['at']['dest'] == pytest.approx(10.3)


def test_the_endpoints():
    assert api.call('cone.cross', {'c': 0.2, 'sym': 0})['gap'] == pytest.approx(0.4)
    assert api.call('cone.cone', {'g': 1, 'h': 0.6, 'y0': 0.3, 'tilt': 0, 'tddft': 0, 'atoms': 6})['seam'] == 10
    assert api.call('cone.twosite', {'t': 0.5, 'U': 4, 'K': 0})['at']['split'] == pytest.approx(1.0)
    assert api.call('cone.yamaguchi', {'dE': 10, 's2': 1})['at']['dest'] == pytest.approx(20)
    with pytest.raises(Exception):
        api.call('cone.cross', {'c': 0.2, 'sym': 2})
    for name in ('cone.cross', 'cone.cone', 'cone.twosite', 'cone.yamaguchi'):
        assert name in api.REGISTRY
