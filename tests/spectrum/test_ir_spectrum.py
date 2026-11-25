"""Analytic broadening oracles; see docs/features/IR_SPECTRUM.md."""

from math import sqrt, log, pi
import numpy as np
import pytest
from modules.spectrum.analysis.ir_spectrum import broaden
from modules.spectrum.readers.vibration_data import Vibration


def test_area_and_half_height():
    x, y = broaden((Vibration(1, 1000, intensity=100),), 20)
    peak = 100 / (20 / (2 * sqrt(2 * log(2))) * sqrt(2 * pi))
    assert np.interp(1000, x, y) == pytest.approx(peak, rel=1e-12)
    assert np.interp(990, x, y) == pytest.approx(peak / 2, rel=1e-12)
    assert np.interp(1010, x, y) == pytest.approx(peak / 2, rel=1e-12)
    assert np.trapezoid(y, x) == pytest.approx(100, rel=1e-6)


def test_superposition_and_missing_data():
    m = Vibration(2, 1000, intensity=5)
    x, y = broaden((m,), 20)
    xx, yy = broaden((m, m, Vibration(3, -20, intensity=99), Vibration(4, 500)), 20)
    assert np.array_equal(x, xx)
    assert np.array_equal(y * 2, yy)


@pytest.mark.parametrize('width', [0, 1, 201, float('nan')])
def test_invalid_width(width):
    with pytest.raises(ValueError):
        broaden((), width)


def test_zero_intensity():
    _, y = broaden((Vibration(1, 1000, intensity=0),), 20)
    assert not y.any()
