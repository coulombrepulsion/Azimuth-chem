"""The isotope pattern of a molecular ion (modules/spectrum/analysis/isotopes.py)."""

import pytest

from modules.spectrum.analysis import isotopes


def test_chlorine_and_bromine():
    cl2 = isotopes.pattern({'Cl': 2})
    assert [s for s, _, _ in cl2] == [0, 2, 4]
    ratio = [round(p, 2) for _, _, p in cl2]
    assert ratio == [100.0, round(100 * 2 * 0.2424 / 0.7576, 2), round(100 * (0.2424 / 0.7576) ** 2, 2)]  # 63.99, 10.24
    assert cl2[0][1] == pytest.approx(2 * 34.968852682)
    br2 = isotopes.pattern({'Br': 2})
    middle = [p for s, _, p in br2 if s == 2][0]
    assert middle == 100 and [round(p) for _, _, p in br2] == [51, 100, 49]  # the 1:2:1 of two bromines


def test_carbon_thirteen_and_exact_masses():
    methane = isotopes.pattern({'C': 1, 'H': 4})
    assert methane[1][0] == 1 and methane[1][2] == pytest.approx(100 * (0.0107 / 0.9893 + 4 * 0.000115 / 0.999885),
                                                                 rel=1e-3)
    assert isotopes.monoisotopic({'H': 2, 'O': 1}) == pytest.approx(18.0105646863, abs=1e-6)
    assert isotopes.average({'H': 2, 'O': 1}) == pytest.approx(18.015, abs=0.002)
    counts = isotopes.formula_counts('C6H5Cl')
    assert counts == {'C': 6, 'H': 5, 'Cl': 1}
    # chlorobenzene: M+2 about a third of M (Cl) and M+1 about 6.5 % (six carbons)
    peaks = {s: p for s, _, p in isotopes.pattern(counts)}
    assert peaks[2] == pytest.approx(32.0, abs=1.0) and peaks[1] == pytest.approx(6.6, abs=0.3)


def test_errors():
    for bad in ('', 'c6h6', 'C6H(5)', '6C'):
        with pytest.raises(ValueError):
            isotopes.formula_counts(bad)
    with pytest.raises(ValueError):  # Pt has its isotopes now (azimuth/isotope_table.py); Tc has no stable one
        isotopes.pattern({'Tc': 1})
    assert isotopes.pattern({'Pt': 1})[0][0] == 0  # the platinum of 190 first
