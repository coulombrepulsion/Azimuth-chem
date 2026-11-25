"""The Atlas topic on the search for a transition state and the reaction path (tsneb.html): the model
quas_atlas.core.tsearch and its endpoints; no Qt, no browser.

Oracles — lecture 3 of the course «Квантово-химические методы» (derivation 2): on E = (x² − 1)² + y² from (0.8, 0.3)
with the radius 0.3 the steps (0.5, 0), (0.2, 0), (−0.018, 0), (0, 0) and λ = (−4, 2); the Newton step to (1.11, 0);
the Müller–Brown surface (Theor. Chim. Acta 53, 75 (1979)): minima A (−0.558, 1.442) −146.70 and C (−0.050, 0.467)
−80.77, the saddle (−0.822, 0.624) −40.66 between them.
"""

import math
import re
import sys

import pytest

from modules.atlas.paths import ATLAS_HOME

if str(ATLAS_HOME) not in sys.path:
    sys.path.insert(0, str(ATLAS_HOME))

from quas_atlas import api, pages  # noqa: E402,F401  (pages registers the endpoints)
from quas_atlas.core import tsearch  # noqa: E402


def test_the_steps_of_the_lecture():
    f = tsearch.follow(0.8, 0.3, 'x', 0.3)
    pts = [(round(p[0], 3), round(p[1], 3)) for p in f['ef'][:5]]
    assert pts == [(0.8, 0.3), (0.5, 0.0), (0.2, 0.0), (-0.018, 0.0), (0.0, 0.0)]
    assert f['found'] and f['steps'] == 4
    assert f['lam'] == [pytest.approx(-4.0, abs=1e-4), pytest.approx(2.0, abs=1e-4)]
    assert [round(v, 2) for v in f['newton'][1][:2]] == [1.1, 0.0]  # Newton goes to the minimum (its step 0.313 clipped)
    free = tsearch.follow(0.8, 0.3, 'x', 1.0)
    assert [round(v, 2) for v in free['newton'][1][:2]] == [1.11, 0.0]  # unclipped: the (1.11, 0) of the lecture
    ends = sorted(round(p[-1][0], 2) for p in f['irc'])
    assert ends == [-1.0, 1.0] and all(abs(p[-1][1]) < 1e-3 for p in f['irc'])


def test_following_the_wrong_mode_finds_no_saddle():
    f = tsearch.follow(0.8, 0.3, 'y', 0.3)
    assert not f['found'] and f['irc'] == [] and f['steps'] is None


def test_the_mueller_brown_points():
    assert tsearch.mb(*tsearch.MB_MIN_A)[0] == pytest.approx(-146.70, abs=0.01)
    assert tsearch.mb(*tsearch.MB_MIN_C)[0] == pytest.approx(-80.77, abs=0.01)
    s = tsearch.mb_saddle()
    assert (round(s['x'], 3), round(s['y'], 3), round(s['E'], 2)) == (-0.822, 0.624, -40.66)
    for x, y in (tsearch.MB_MIN_A, tsearch.MB_MIN_C, (s['x'], s['y'])):
        assert math.hypot(*tsearch.mb(x, y)[1:]) < 0.02
    lam = tsearch._eig2(*tsearch._hess(tsearch.mb, s['x'], s['y']))
    assert lam[0][0] < 0 < lam[1][0]  # one negative eigenvalue


def test_the_elastic_band():
    true = tsearch.neb(9, 50, 'ci')
    assert true['top_distance'] < 0.01 and true['barrier'] == pytest.approx(true['true_barrier'], abs=0.1)
    plain = tsearch.neb(9, 50, 'plain')
    assert plain['barrier'] < 0.8 * plain['true_barrier']  # cut corners, images slid to the ends
    neb = tsearch.neb(9, 50, 'neb')
    assert plain['barrier'] < neb['barrier'] <= true['barrier'] + 1e-6
    d = [math.dist(a, b) for a, b in zip(neb['images'], neb['images'][1:])]
    assert max(d) / min(d) < 1.2  # the springs keep the images evenly spaced along the path


def test_the_scan_breaks():
    s = tsearch.scan('y')
    assert abs(s['max_f'] - s['max_b']) > 5  # forward and backward differ
    assert s['forward']['E'][0] == pytest.approx(s['E_A'], abs=0.01)


def test_the_endpoints():
    assert api.call('ts.follow', {'x0': 0.8, 'y0': 0.3, 'mode': 'x', 'radius': 0.3})['steps'] == 4
    assert api.call('ts.neb', {'n': 9, 'k': 50, 'kind': 'ci'})['top_distance'] < 0.01
    assert len(api.call('ts.scan', {'coord': 'x'})['forward']['q']) == 41
    with pytest.raises(Exception):
        api.call('ts.neb', {'n': 9, 'k': 50, 'kind': 'string'})
    for name in ('ts.follow', 'ts.neb', 'ts.scan'):
        assert name in api.REGISTRY


def test_the_page_names_what_its_script_draws():
    web = ATLAS_HOME / 'quas_atlas' / 'web'
    for lang in ('ru', 'en', 'zh'):
        page = (web / lang / 'tsneb.html').read_text(encoding='utf-8')
        script = (web / lang / 'js' / 'tsneb.js').read_text(encoding='utf-8')
        for ident in set(re.findall(r"\$\('([A-Za-z]\w*)'\)", script)):
            assert f'id="{ident}"' in page, f'{lang}: #{ident}'
        assert page.count('data-ok="1"') == 4 and 'window.QC_GL_SELF="tsneb"' in page
