"""The Atlas topics on molecular dynamics and learned potentials (mlmd.html) and on machine learning in quantum
chemistry (mlqc.html): the model quas_atlas.core.mlpot and its endpoints; no Qt, no browser.

Oracles — lectures 16 and 17 of the course «Квантово-химические методы»: the period 9 fs of an O–H bond (3700 cm⁻¹)
and 64.5 fs of the optical phonon of Si (15.5 THz); the Verlet error ∝ Δt² and Euler's energy growing; δT/T =
sqrt(2/(3N)) — ±31 K for 64 atoms at 300 K; the Eyring rate (kT/h)e^{−ΔG/kT}; δ(MAE) = σ(|e|)/√n with
σ(|e|)/MAE = sqrt(π/2 − 1); the convex hull (−0.44 at x = 0.4 between −0.40 at 1/3 and −0.50 at 1/2).
"""

import math
import re
import sys

import pytest

from modules.atlas.paths import ATLAS_HOME

if str(ATLAS_HOME) not in sys.path:
    sys.path.insert(0, str(ATLAS_HOME))

from quas_atlas import api, pages  # noqa: E402,F401  (pages registers the endpoints)
from quas_atlas.core import mlpot  # noqa: E402


def test_the_periods_of_the_fastest_vibrations():
    assert mlpot.verlet('oh', 0.5)['period'] == pytest.approx(9.01, abs=0.01)
    assert mlpot.verlet('si', 1.0)['period'] == pytest.approx(64.5, abs=0.1)
    assert mlpot.verlet('od', 0.5)['period'] == pytest.approx(9.01 * 3700 / 2700, abs=0.01)


def test_verlet_keeps_the_energy_and_euler_does_not():
    small, big = mlpot.verlet('oh', 0.25), mlpot.verlet('oh', 0.5)
    assert big['max'] / small['max'] == pytest.approx(4, rel=0.1)  # ∝ Δt²
    assert abs(big['drift']) < big['max']  # it oscillates, it does not pile up
    euler = mlpot.verlet('oh', 0.5, 'euler')
    assert euler['drift'] > 100 * big['max']
    assert mlpot.verlet('oh', 4.0)['blown'] and not mlpot.verlet('si', 4.0)['blown']


def test_the_committee_agrees_inside_and_spreads_outside():
    c = mlpot.committee(16, 2.9)
    assert c['err_in'] < 0.005 and c['err_out'] > 50 * c['err_in']
    assert c['sigma_out'] > 10 * c['sigma_in']
    inside = [f for r, f in zip(c['r'], c['flag']) if c['lo'] + 0.05 <= r <= c['hi'] - 0.05]  # away from the edges
    assert not any(inside) and c['flag'][0]  # the compressed bond is flagged for DFT


def test_fluctuations_and_rare_events():
    e = mlpot.events(64, 300, 0.8, 100)
    assert e['rel'] == pytest.approx(math.sqrt(2 / 192)) and e['dT'] == pytest.approx(30.6, abs=0.1)
    k = mlpot.K_B * 300 / mlpot.H_EV * math.exp(-0.8 / (mlpot.K_B * 300))
    assert e['rate'] == pytest.approx(k) and e['events'] == pytest.approx(k * 1e-10)
    assert e['dft_days'] == pytest.approx(1e5 * 180 / 86400)  # 10⁵ steps of 3 min ≈ 200 days (lecture 16)


def test_delta_learning_beats_learning_the_energy():
    d = mlpot.delta(16, 0.5, 0.5)
    assert d['at']['delta'] < d['at']['direct'] / 2
    assert all(b < a for a, b in zip(d['direct'], d['delta']))
    assert d['a_direct'] > 0 and d['a_delta'] > 0
    assert mlpot.delta(16, 0.5, 0.5) == d  # the random choices are fixed


def test_the_uncertainty_of_the_mae():
    r = mlpot.mae(20, 10, 11)
    assert r['rel'] == pytest.approx(math.sqrt(math.pi / 2 - 1) / math.sqrt(20))
    assert r['rel'] == pytest.approx(0.17, abs=0.005)  # 0.75/√20
    a, b = r['a']['at'], r['b']['at']
    assert abs(a['mae'] - b['mae']) < 2 * math.hypot(a['err'], b['err'])  # 10 and 11 on 20 molecules: no difference
    many = mlpot.mae(320, 10, 12)
    assert abs(many['a']['at']['mae'] - many['b']['at']['mae']) > 2 * math.hypot(many['a']['at']['err'], many['b']['at']['err'])


def test_the_convex_hull():
    h = mlpot.hull(-0.40, -0.50, 0.4, -0.41)
    assert h['at_hull'] == pytest.approx(-0.44) and h['above'] == pytest.approx(0.03)
    low = mlpot.hull(-0.40, -0.50, 0.4, -0.50)
    assert low['above'] < 0 and 1 / 3 not in low['new_hull']['x']  # AB₂ falls off the new hull
    assert not mlpot.hull(-0.30, -0.50, 0.4, -0.41)['phases'][1]['on']  # −0.30 at 1/3 is above the line A–AB


def test_the_endpoints():
    assert api.call('ml.verlet', {'system': 'oh', 'method': 'verlet', 'dt': 0.5, 'E0': 0.3})['period'] == pytest.approx(9.0, abs=0.05)
    assert api.call('ml.committee', {'n': 16, 'hi': 2.9})['err_in'] < 0.005
    assert api.call('ml.events', {'N': 64, 'T': 300, 'barrier': 0.8, 'length': 100})['dT'] == pytest.approx(30.6, abs=0.1)
    assert api.call('ml.delta', {'n': 16, 'cheap': 0.5, 'sigma': 0.5})['at']['n'] == 16
    assert api.call('ml.mae', {'n': 20, 'a': 10, 'b': 11})['n'] == 20
    assert api.call('ml.hull', {'e13': -0.4, 'e12': -0.5, 'x': 0.4, 'e': -0.41})['above'] == pytest.approx(0.03)
    with pytest.raises(Exception):
        api.call('ml.verlet', {'system': 'ch', 'method': 'verlet', 'dt': 0.5, 'E0': 0.3})
    for name in ('ml.verlet', 'ml.committee', 'ml.events', 'ml.delta', 'ml.mae', 'ml.hull'):
        assert name in api.REGISTRY


def test_the_pages_name_what_their_scripts_draw():
    web = ATLAS_HOME / 'quas_atlas' / 'web'
    for lang in ('ru', 'en', 'zh'):
        for topic in ('mlmd', 'mlqc'):
            page = (web / lang / f'{topic}.html').read_text(encoding='utf-8')
            script = (web / lang / 'js' / f'{topic}.js').read_text(encoding='utf-8')
            for ident in set(re.findall(r"\$\('([A-Za-z]\w*)'\)", script)):
                assert f'id="{ident}"' in page, f'{lang}/{topic}: #{ident}'
            assert page.count('data-ok="1"') == 4 and f'window.QC_GL_SELF="{topic}"' in page
