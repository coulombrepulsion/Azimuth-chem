"""The Atlas topic on the spin states of transition-metal complexes in DFT (spinstates.html): the model
quas_atlas.core.spinstates and its endpoints; no Qt, no browser.

Oracles — lecture 9 of the course «Квантово-химические методы» and its remarks (ORCA 6.0.1, def2-SVP at TPSSh/def2-SVP
geometries, 22.11.2026): the slopes −1.48, −4.69, −7.80 kJ/mol per 1 % of exact exchange and the sign changes at
18.7 % (NCH) and 38.4 % (CO); 10 and 6 exchange pairs of high- and low-spin d⁶ (derivation 6); ⟨S²⟩ = 6.9 of a
quintet — 15 % of the septet (derivation 7); the mean Fe–L 2.138 / 1.999, 2.169 / 1.926, 2.283 / 1.919 Å.
"""

import sys
from math import comb

import pytest

from modules.atlas.paths import ATLAS_HOME

if str(ATLAS_HOME) not in sys.path:
    sys.path.insert(0, str(ATLAS_HOME))

from quas_atlas import api, pages  # noqa: E402,F401  (pages registers the endpoints)
from quas_atlas.core import spinstates  # noqa: E402


def test_the_lines_of_the_lecture():
    g = {c['key']: c for c in spinstates.gap(20)['complexes']}
    assert [round(g[k]['slope'], 2) for k in ('water', 'nch', 'co')] == [-1.48, -4.69, -7.80]
    assert g['water']['zero'] is None
    assert round(g['nch']['zero'], 1) == 18.7 and round(g['co']['zero'], 1) == 38.4
    assert g['water']['at'] < 0 and g['nch']['at'] < 0 < g['co']['at']  # B3LYP: NCH already high-spin
    bp = {c['key']: c['at'] for c in spinstates.gap(0)['complexes']}
    assert bp['nch'] > 0  # BP86: low spin
    assert spinstates.gap(50)['complexes'][2]['points'][-1][1] == -86.5  # BHandHLYP: the carbonyl «high-spin»


def test_counting_exchange_pairs():
    p = spinstates.gap(0)['pairs']
    assert (p['hs'], p['ls']) == (comb(5, 2), comb(3, 2) + comb(3, 2)) == (10, 6)


def test_spin_contamination():
    c = spinstates.contam(2, 6.9)
    assert c['exact'] == 6 and c['next'] == 12 and c['admix'] == pytest.approx(0.15)
    assert spinstates.contam(0, 0)['admix'] == 0 and spinstates.contam(1, 2)['exact'] == 2
    with pytest.raises(ValueError):
        spinstates.contam(0.3, 1)


def test_the_bond_lengths():
    g = spinstates.geom('water')
    assert round(g['mean_q'], 3) == 2.138 and g['mean_s'] == 1.999
    assert round(spinstates.geom('nch')['mean_q'], 3) == 2.168  # the lecture rounds 2.169
    assert round(spinstates.geom('co')['dr'], 2) == 0.36
    assert all(0.1 <= v['mean_q'] - v['mean_s'] <= 0.4 for v in g['all'].values())


def test_the_endpoints():
    assert api.call('spin.gap', {'a': 10})['a'] == 10
    assert api.call('spin.contam', {'S': 2, 's2': 6.0})['excess'] == 0
    assert api.call('spin.geom', {'key': 'co'})['singlet'] == [1.919] * 6
    with pytest.raises(Exception):
        api.call('spin.geom', {'key': 'cn'})
    for name in ('spin.gap', 'spin.contam', 'spin.geom'):
        assert name in api.REGISTRY
