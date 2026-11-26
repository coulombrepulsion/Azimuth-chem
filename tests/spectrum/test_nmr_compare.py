"""Computed chemical shifts against the measured ones (modules/spectrum/analysis/nmr_compare.py).

Oracles, by hand. Four signals, computed δ 170.0, 130.0, 60.0, 20.5 against measured 171.2, 128.9, 61.5, 21.0: the
errors −1.2, +1.1, −1.5, −0.5 → MAE = 4.3 / 4 = 1.075, RMSE = √((1.44 + 1.21 + 2.25 + 0.25) / 4) = √1.2875 = 1.13468,
the largest −1.5 (the third). A line through points that lie on σ = 185 − 1.02 δ exactly gives a = 185, b = −1.02,
r² = 1 and corrected shifts equal to the measured ones, whatever the reference was.
"""

from math import sqrt

import pytest

from modules.spectrum.analysis import nmr_compare as nc

# (atoms 0-based, element, δ, σ) with a reference of 184.0
ROWS = [((0,), 'C', 170.0, 14.0), ((1,), 'C', 130.0, 54.0), ((2, 3), 'C', 20.5, 163.5), ((4,), 'C', 60.0, 124.0)]


def test_the_lines_of_the_measured_spectrum():
    found = nc.parse('C1 77,2\nH3, H4, H5: 2.15 # methyl\n\n128.4\n  3 4 21\n# a remark alone\n')
    assert found == [nc.Measured((1,), 77.2), nc.Measured((3, 4, 5), 2.15), nc.Measured((), 128.4), nc.Measured((3, 4), 21.0)]
    assert nc.parse('') == [] and nc.parse('-0.5') == [nc.Measured((), -0.5)]
    with pytest.raises(ValueError, match='не нашлось числа'):
        nc.parse('carbonyl')
    with pytest.raises(ValueError, match='номера атомов'):
        nc.parse('1.5 77.2')


def test_the_signals_matched_by_their_order():
    found = nc.pairs(ROWS, nc.parse('21.0\n171.2\n61.5\n128.9'))
    assert [(p.atoms, p.calc, p.exp) for p in found] == [((0,), 170.0, 171.2), ((1,), 130.0, 128.9), ((4,), 60.0, 61.5),
                                                        ((2, 3), 20.5, 21.0)]
    s = nc.stats(found)
    assert s.count == 4 and s.mae == pytest.approx(1.075) and s.rmse == pytest.approx(sqrt(1.2875))
    assert s.largest == pytest.approx(-1.5) and found[s.largest_at].atoms == (4,)
    with pytest.raises(ValueError, match='Сигналов в расчёте 4, в эксперименте 3'):
        nc.pairs(ROWS, nc.parse('1\n2\n3'))


def test_the_signals_matched_by_the_numbers_of_the_atoms():
    found = nc.pairs(ROWS, nc.parse('C5 61.5\nC3 21.0\nC1 171.2'))  # a part of the spectrum, in any order
    assert [(p.atoms, p.calc, p.exp) for p in found] == [((4,), 60.0, 61.5), ((2, 3), 20.5, 21.0), ((0,), 170.0, 171.2)]
    # one measured signal for two computed ones (not resolved): the mean by the number of the nuclei
    merged = nc.pairs(ROWS, nc.parse('1 2 150\n3 4 21'))[0]
    assert merged.atoms == (0, 1) and merged.calc == pytest.approx(150.0) and merged.sigma == pytest.approx(34.0)
    weighted = nc.pairs(ROWS, nc.parse('2 3 4 60'))[0]
    assert weighted.sigma == pytest.approx((54.0 + 2 * 163.5) / 3)
    for text, message in (('C9 10', 'Атома 9 нет'), ('C1 170\nC1 171', 'два экспериментальных'), ('C1 170\n21', 'не у всех')):
        with pytest.raises(ValueError, match=message):
            nc.pairs(ROWS, nc.parse(text))
    with pytest.raises(ValueError):
        nc.pairs([], nc.parse('1.0'))
    with pytest.raises(ValueError):
        nc.pairs(ROWS, [])


def test_the_linear_correction():
    measured = [171.2, 128.9, 61.5, 21.0]
    exact = [nc.Pair((k,), 185.0 - 1.02 * d, 184.0 - (185.0 - 1.02 * d), d) for k, d in enumerate(measured)]
    fit = nc.linear(exact)
    assert fit.a == pytest.approx(185.0) and fit.b == pytest.approx(-1.02) and fit.r2 == pytest.approx(1.0)
    assert fit.shifts == pytest.approx(measured) and fit.stats.mae == pytest.approx(0.0, abs=1e-9)
    assert nc.stats(exact).mae > 1.0  # the same points by the reference molecule are off: the slope is not −1
    real = nc.pairs(ROWS, nc.parse('171.2\n128.9\n61.5\n21.0'))
    fit = nc.linear(real)
    assert fit.stats.mae < nc.stats(real).mae and -1.05 < fit.b < -0.95 and fit.r2 > 0.999
    # least squares by hand: the residuals of σ sum to zero and are orthogonal to δ
    residual = [p.sigma - (fit.a + fit.b * p.exp) for p in real]
    assert sum(residual) == pytest.approx(0.0, abs=1e-9)
    assert sum(r * p.exp for r, p in zip(residual, real)) == pytest.approx(0.0, abs=1e-7)
    with pytest.raises(ValueError, match='три'):
        nc.linear(real[:2])
    with pytest.raises(ValueError, match='совпадают'):
        nc.linear([nc.Pair((k,), 10.0, 1.0, 5.0) for k in range(3)])
    assert nc.stats([nc.Pair((0,), 10.0, None, 5.0)]) is None and nc.stats([]) is None


def test_the_signals_too_close_to_tell_apart():
    found = [nc.Pair((0,), 54.0, 130.0, 128.9), nc.Pair((1,), 54.8, 129.2, 130.1), nc.Pair((2,), 124.0, 60.0, 61.5)]
    assert nc.doubtful(found, 2.0) == [(0, 1)] and nc.doubtful(found, 0.5) == []
