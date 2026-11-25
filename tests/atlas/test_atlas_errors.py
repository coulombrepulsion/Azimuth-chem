"""The Atlas topic on the error of a calculation (errors.html): the model quas_atlas.core.errors and its endpoints; no
Qt, no browser.

Oracles — lecture 18 of the course «Квантово-химические методы»: √(64 + 9 + 1) = 8.6, without the convergence 8.5, with
10 — 13 (derivation 2); σ = 1.25 MAE, MAE 8 → ±20 kJ/mol, e^{20000/(8.314·298)} ≈ 3000 (derivation 3); ethanol: the
atomization error 24, the isodesmic 0, ΔfH = −232.9 against −234 ± 2 (derivation 4); √(2·64·0.2) = 5.1 and √128 = 11.3
(derivation 6); two conformers ΔG = 2 kJ/mol: 69/31 %, ±4 → 8–69 %, ±1 → 23–40 % (derivation 10).
"""

import sys

import pytest

from modules.atlas.paths import ATLAS_HOME

if str(ATLAS_HOME) not in sys.path:
    sys.path.insert(0, str(ATLAS_HOME))

from quas_atlas import api, pages  # noqa: E402,F401  (pages registers the endpoints)
from quas_atlas.core import errors  # noqa: E402


def test_errors_add_in_squares():
    t = errors.total(8, 3, 1)
    assert round(t['total'], 1) == 8.6 and round(t['without_conv'], 1) == 8.5
    assert round(errors.total(8, 3, 10)['total']) == 13
    assert t['linear'] == 12 and sum(t['share']) == pytest.approx(1)


def test_from_the_mean_error_to_an_interval():
    i = errors.interval(8, 298)
    assert i['sigma'] == pytest.approx(1.2533 * 8, rel=1e-4) and round(i['half95']) == 20
    assert 2500 < i['factor'] < 4000  # «≈ 3000»: the rate constant within three orders
    assert i['frac_beyond_mae'] == pytest.approx(0.425, abs=0.002)


def test_isodesmic_ethanol_and_a_related_system():
    d = errors.isodesmic(2, 5, 6, 3, 8, 0.8)
    assert d['atomization'] == 24 and d['isodesmic'] == 0
    assert d['left'] == d['right']
    assert d['dfh'] == pytest.approx(-232.9) and abs(d['dfh'] - d['exp']) < d['exp_err']
    assert round(d['corr'], 1) == 5.1 and round(errors.isodesmic(rho=0)['corr'], 1) == 11.3
    assert errors.isodesmic(rho=1)['corr'] == 0


def test_conformer_shares():
    c = errors.conformers(2, 4, 298.15)
    assert round(100 * c['x2']) == 31 and round(100 * c['lo']) == 8 and round(100 * c['hi']) == 69
    n = errors.conformers(2, 1, 298.15)
    assert (round(100 * n['lo']), round(100 * n['hi'])) == (23, 40)
    assert errors.conformers(0, 0)['x2'] == pytest.approx(0.5)


def test_the_endpoints():
    assert round(api.call('err.sum', {'sm': 8, 'sb': 3, 'sc': 1})['total'], 1) == 8.6
    assert round(api.call('err.interval', {'mae': 8, 'T': 298})['half95']) == 20
    assert api.call('err.isodesmic', {'dch': 2, 'dcc': 5, 'dco': 6, 'doh': 3, 'sigma': 8, 'rho': 0})['isodesmic'] == 0
    assert api.call('err.conformers', {'dG': 0, 's': 1, 'T': 298})['x2'] == pytest.approx(0.5)
    with pytest.raises(Exception):
        api.call('err.sum', {'sm': -1, 'sb': 3, 'sc': 1})
    for name in ('err.sum', 'err.interval', 'err.isodesmic', 'err.conformers'):
        assert name in api.REGISTRY
