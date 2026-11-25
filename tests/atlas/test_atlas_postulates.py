"""Atlas «Постулаты»: operators and expectation values (quas_atlas.core.postulates).

Oracles, independent of the tested functions:
  * the spread ||A Psi - <A> Psi|| equals Delta A of frame(), which is computed by another formula
    (<A^2> - <A>^2 from the amplitudes for E and p, from |Psi|^2 for x);
  * H psi_n = n^2 psi_n (definition of the eigenfunctions);
  * p Psi = -i dPsi/dx against a centred finite difference of Psi on the grid;
  * the running mean of mean_series() against the plain mean of (k+1)^2 over its outcomes.
Tolerances: the grid integrals use the trapezoidal rule with h = 1/400; for |A Psi|^2 the first
derivative vanishes at the walls (A Psi or its derivative is zero there), so the error is O(h^4):
h^4/720 * |f'''| <= 6.3e-11 / 720 * 2 (4 * 4 pi)^3 * 4 < 1e-9 for states up to n = 4 (B = 1e-8).
The centred difference has the error h^2/6 |Psi'''| <= h^2/6 * sqrt2 (4 pi)^3 * 4 = 1.2e-2 absolute.
"""

import math
import random
import sys

import pytest

from modules.atlas.paths import ATLAS_HOME

if str(ATLAS_HOME) not in sys.path:
    sys.path.insert(0, str(ATLAS_HOME))

from quas_atlas.core import postulates as m  # noqa: E402

B = 1e-8


def states():
    rnd = random.Random(7)
    for _ in range(6):
        a = [rnd.random() for _ in range(4)]
        ph = [rnd.uniform(0, 2 * math.pi) for _ in range(4)]
        yield m.prepare(a, ph), rnd.random()


@pytest.mark.parametrize('op,key', [('H', 'dE'), ('p', 'dp'), ('x', 'dx')])
def test_spread_is_the_uncertainty(op, key):
    for C, t in states():
        frame = m.frame(C, t, 0.0)
        o = m.operator(C, t, 0.0, op)
        assert o['spread'] == pytest.approx(frame['obs'][key], abs=B)
        assert o['mean'] == pytest.approx(frame['obs'][{'H': 'E', 'p': 'p', 'x': 'x'}[op]], abs=B)


def test_energy_eigenfunctions():
    for n in range(1, 5):
        a = [1.0 if k == n - 1 else 0.0 for k in range(4)]
        o = m.operator(m.prepare(a, [0.0] * 4), 0.0, 0.0, 'H')
        assert o['mean'] == n * n and o['spread'] == pytest.approx(0, abs=B)
        assert max(abs(o['are'][i] - n * n * o['re'][i]) for i in range(m.NG)) < 1e-12
        # psi_n is not an eigenfunction of p: the spread is n pi (<p> = 0, <p^2> = (n pi)^2)
        p = m.operator(m.prepare(a, [0.0] * 4), 0.0, 0.0, 'p')
        assert p['spread'] == pytest.approx(n * math.pi, abs=B) and p['rel'] == pytest.approx(1, abs=B)


def test_momentum_is_minus_i_derivative():
    h = 1 / (m.NG - 1)
    for C, t in states():
        o = m.operator(C, t, 0.0, 'p')
        for i in range(1, m.NG - 1):
            d_re = (o['re'][i + 1] - o['re'][i - 1]) / (2 * h)
            d_im = (o['im'][i + 1] - o['im'][i - 1]) / (2 * h)
            # -i (d_re + i d_im) = d_im - i d_re
            assert o['are'][i] == pytest.approx(d_im, abs=1.2e-2)
            assert o['aim'][i] == pytest.approx(-d_re, abs=1.2e-2)


def test_running_mean_of_a_series():
    rnd = random.Random(3)
    rs = [rnd.random() for _ in range(2000)]
    s = m.mean_series([1, 1, 1, 0], [0, 0, 0, 0], rs)
    assert s['mean'] == pytest.approx((1 + 4 + 9) / 3, abs=1e-12)
    assert s['running'][-1] == pytest.approx(sum((k + 1) ** 2 for k in s['ks']) / len(rs), abs=1e-12)
    # the mean of 2000 outcomes lies within 4 standard errors of <E> (fixed seed: deterministic)
    assert abs(s['running'][-1] - s['mean']) < 4 * s['dE'] / math.sqrt(len(rs))


def test_operator_rejects_unknown_observable():
    with pytest.raises(ValueError):
        m.operator(m.prepare([1, 0, 0, 0], [0] * 4), 0, 0, 'L')
