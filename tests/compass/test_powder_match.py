"""powder_match: a «measured» pattern of rock salt made from the calculated one — a background, the zero moved by
+0.12°, a cell 0.5 % larger, noise and a peak of another phase."""

from pathlib import Path

import numpy as np
import pytest

from modules.compass.chemistry import crystal as cr
from modules.compass.chemistry import powder
from modules.compass.chemistry import powder_match as pm

CIF = Path(__file__).resolve().parents[2] / 'examples' / '10-crystals' / 'NaCl_rock_salt.cif'


def measured(shift=0.12, strain=0.005, impurity=True):
    lines = powder.pattern(cr.parse_cif(CIF.read_text(encoding='utf-8')), powder.CU, 10, 90)
    x = np.arange(10, 90, 0.02)
    y = powder.curve(x, pm._positions(lines, powder.CU, strain, shift), [line.intensity for line in lines],
                     [0.12] * len(lines))
    y += 30 + 20 * np.exp(-((x - 10) / 15) ** 2)  # the background
    if impurity:
        y += 40 * np.exp(-((x - 33.0) / 0.06) ** 2)
    y += np.random.default_rng(1).normal(0, 0.5, len(x))
    return lines, x, y


def test_the_zero_and_the_cell_are_found():
    lines, x, y = measured()
    m = pm.match(lines, x, y, powder.CU, 0.12)
    assert m.shift == pytest.approx(0.12, abs=0.01) and m.cell_change == pytest.approx(0.005, abs=0.0005)
    assert not m.missing and len(m.pairs) >= len([line for line in lines if line.intensity >= pm.STRONG])
    assert [round(t) for t, _ in m.extra] == [33]  # the peak of «another phase»
    assert m.correlation > 0.85


def test_the_same_pattern_agrees():
    lines, x, y = measured(0.0, 0.0, impurity=False)
    m = pm.match(lines, x, y, powder.CU, 0.12)
    assert abs(m.shift) < 0.01 and abs(m.cell_change) < 3e-4 and m.r_profile < 0.15 and not m.extra


def test_the_background_lies_under_the_pattern():
    _, x, y = measured()
    bg = pm.background(x, y)
    true = 30 + 20 * np.exp(-((x - 10) / 15) ** 2)
    assert np.abs(bg - true).mean() < 0.2  # the noise (σ 0.5) does not pull it down


def test_a_pattern_with_the_alpha2_doublets():
    # a «measured» pattern with Kα₂ (the doublets moved by the same zero and cell) and widths growing with the
    # angle (Caglioti): the zero and the cell are found again, and the calculated curve with the same shape fits it
    # better than the one of Kα₁ alone
    lines = powder.pattern(cr.parse_cif(CIF.read_text(encoding='utf-8')), powder.CU, 10, 90)
    second = powder.alpha2(lines, powder.CU, powder.KA2['Cu Kα₁'])
    uvw = (0.02, -0.005, 0.004)
    x = np.arange(10, 90, 0.01)
    centres = list(pm._positions(lines, powder.CU, 0.003, 0.08)) + list(pm._positions(second, powder.KA2['Cu Kα₁'], 0.003, 0.08))
    every = list(lines) + list(second)
    y = powder.curve(x, centres, [line.intensity for line in every], [powder.caglioti(line.two_theta, *uvw) for line in every])
    y += 25 + np.random.default_rng(2).normal(0, 0.3, len(x))
    shaped = pm.match(lines, x, y, powder.CU, uvw=uvw, alpha2=(powder.KA2['Cu Kα₁'], 0.5))
    plain = pm.match(lines, x, y, powder.CU, 0.1)
    assert abs(shaped.shift - 0.08) < 0.02 and abs(shaped.cell_change - 0.003) < 0.001
    assert shaped.r_profile < 0.5 * plain.r_profile and shaped.correlation > 0.99
