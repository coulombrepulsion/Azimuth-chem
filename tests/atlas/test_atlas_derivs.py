"""The Atlas topic on properties as derivatives of the energy (derivatives.html): the model quas_atlas.core.derivs and
its endpoints; no Qt, no browser.

Oracles — lecture 1 of the course «Квантово-химические методы» (the Morse curve De = 0.17, a = 1.0, Re = 1.4 a.u. at
R = 1.6: E′ = 0.050460; with exact energies at h = 0.1 the forward error 7.9·10⁻³ and the central −1.1·10⁻³; with the
energies to 10⁻⁶ the best central −9.6·10⁻⁶ at h = 0.01, the forward at h = 10⁻⁵ off by 5·10⁻²; h_opt ≈ 0.017) and
lecture 5 (the finite field: δα ~ 2δE/F²; water α: def2-SVP 5.32, def2-TZVP 6.77, def2-SVPD 9.76, experiment 9.8 a.u.).
"""

import sys

import pytest

from modules.atlas.paths import ATLAS_HOME

if str(ATLAS_HOME) not in sys.path:
    sys.path.insert(0, str(ATLAS_HOME))

from quas_atlas import api, pages  # noqa: E402,F401  (pages registers the endpoints)
from quas_atlas.core import derivs  # noqa: E402


def _at(S, key, h):
    i = min(range(len(S['h'])), key=lambda j: abs(S['h'][j] - h))
    assert S['h'][i] == pytest.approx(h, rel=1e-9)
    return S[key][i]


def test_the_table_of_lecture_1():
    S = derivs.steps(None)
    assert round(S['exact']['d1'], 6) == 0.050460
    assert round(_at(S, 'forward', 0.1), 4) == 0.0079
    assert round(_at(S, 'central', 0.1), 4) == -0.0011
    assert abs(_at(S, 'central', 0.01)) < 2e-5 and abs(_at(S, 'forward', 0.01)) > 5e-4  # h² against h
    R = derivs.steps(6)
    assert R['best']['central']['h'] == pytest.approx(0.01) and f"{R['best']['central']['err']:.1e}" == '-9.6e-06'
    assert f"{_at(R, 'forward', 1e-5):.1e}" == '-5.0e-02'  # the rounding noise δE/h
    assert round(R['h_opt'], 3) == 0.017


def test_more_digits_move_the_optimum_to_a_smaller_step():
    a, b = derivs.steps(6), derivs.steps(10)
    assert b['h_opt'] < a['h_opt'] and abs(b['best']['central']['err']) < abs(a['best']['central']['err'])
    with pytest.raises(ValueError):
        derivs.steps(2)


def test_the_finite_field_noise():
    f = derivs.field(-4, -8)
    assert f['at']['noise_E'] == pytest.approx(2.0)  # 2δE/F² = 2·10⁻⁸/10⁻⁸
    assert abs(f['at']['alpha_E'] - 9.8) > 0.1 and abs(f['at']['alpha_mu'] - 9.8) < 1e-3
    g = derivs.field(-2.7, -8)
    assert abs(g['at']['alpha_E'] - 9.8) < 0.02 and abs(g['at']['mu'] - 0.728) < 1e-4
    big = derivs.field(-1, -12)
    assert abs(big['at']['alpha_E'] - 9.8) > 0.05  # β and γ spoil a large field
    assert g['true']['mu_D'] == pytest.approx(1.85, abs=0.01)


def test_two_levels_and_the_bases():
    t = derivs.twolevel(1.2, 0.3)
    assert t['alpha'] == pytest.approx(9.6)
    a = {b['name']: b['alpha'] for b in t['basis']}
    assert (a['def2-SVP'], a['def2-TZVP'], a['def2-SVPD']) == (5.32, 6.77, 9.76) and t['exp'] == 9.8


def test_the_endpoints():
    assert api.call('der.steps', {'digits': 6})['best']['central']['h'] == pytest.approx(0.01)
    assert api.call('der.field', {'lgF': -3, 'lgdE': -9})['at']['F'] == pytest.approx(1e-3)
    assert api.call('der.twolevel', {'mu01': 1.0, 'dE': 0.5})['alpha'] == pytest.approx(4.0)
    for name in ('der.steps', 'der.field', 'der.twolevel'):
        assert name in api.REGISTRY
