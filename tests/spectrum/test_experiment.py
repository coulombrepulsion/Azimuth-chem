"""An experimental spectrum over the computed one (modules/spectrum/analysis/experiment.py)."""

import numpy as np
import pytest

from modules.spectrum.analysis import experiment as ex

JCAMP = """##TITLE= test spectrum
##JCAMP-DX= 4.24
##DATA TYPE= INFRARED SPECTRUM
##XUNITS= 1/CM
##YUNITS= ABSORBANCE
##XFACTOR= 1.0
##YFACTOR= 0.001
##FIRSTX= 1000
##LASTX= 1009
##NPOINTS= 10
##XYDATA=(X++(Y..Y))
1000@AJ1j2KT%
1007DJ2K3
##END=
"""


def test_jcamp_asdf_sqz_dif_dup_and_the_y_check():
    # 1000: @ A J1 j2 K T % → 0 1 12 0 2 4 4 (T: the difference +2 once more; %: +0) — the line ends in DIF, so the
    # first Y of the next line (D = 4) is the check value, not a point: then J2 (+12) → 16, K3 (+23) → 39
    e = ex.parse(JCAMP)
    assert e.x_unit == 'cm-1' and e.y_unit == 'absorbance' and e.name == 'test spectrum'
    assert [round(v * 1000) for v in e.y] == [0, 1, 12, 0, 2, 4, 4, 16, 39]
    assert e.x[0] == 1000 and e.x[-1] == 1009


def test_asdf_line_decoding():
    x, values, dif = ex._asdf_line('100@AJ1j2KT%')
    assert x == 100 and values == [0, 1, 12, 0, 2, 4, 4] and dif
    x, values, dif = ex._asdf_line('200 1.5 -2 3e1')
    assert x == 200 and values == [1.5, -2, 30] and not dif
    x, values, dif = ex._asdf_line('300A1B2C3')  # SQZ only
    assert values == [11, 22, 33] and not dif
    x, values, dif = ex._asdf_line('400a1U')  # DUP (U = 3) of a plain value: −11 three times
    assert values == [-11, -11, -11]


def test_text_columns_in_every_usual_form():
    for text in ('x y\n100 1\n200 2\n300 3\n400 2\n500 1\n',
                 'nm;eps\n100;1\n200;2\n300;3\n400;2\n500;1\n',
                 '100,1\n200,2\n300,3\n400,2\n500,1\n',
                 '100\t1,0\n200\t2,0\n300\t3,0\n400\t2,0\n500\t1,0\n',
                 '100 1,0\n200 2,0\n300 3,0\n400 2,0\n500 1,0\n'):
        e = ex.parse(text)
        assert e.x == (100, 200, 300, 400, 500) and e.y == (1, 2, 3, 2, 1), text
    with pytest.raises(ValueError):
        ex.parse('nothing\n1 2\n')


def test_transmittance_becomes_absorbance_with_bands_up():
    x = np.linspace(400, 4000, 400)
    t = 95 - 80 * np.exp(-((x - 1700) / 15) ** 2)  # %T with a band at 1700
    e = ex.Experiment(tuple(x), tuple(t), 'ir')
    assert ex.is_transmittance(e)
    gx, gy = ex.on_axis(e, 'cm-1')
    assert gx[np.argmax(gy)] == pytest.approx(1700, abs=10) and gy.max() == pytest.approx(1)


def test_units_are_turned_to_the_axis():
    e = ex.Experiment((200.0, 250.0, 300.0, 350.0, 400.0), (0, 1, 2, 1, 0))  # nm, for UV
    x, _ = ex.on_axis(e, 'nm')
    assert x[0] == 200
    e = ex.Experiment((3.0, 4.0, 5.0, 6.0, 6.2), (0, 1, 2, 1, 0))  # eV
    x, _ = ex.on_axis(e, 'nm')
    assert x[-1] == pytest.approx(ex.HC_EV_NM / 3.0)


def test_similarity_and_the_best_factor():
    grid = np.linspace(400, 4000, 3000)

    def bands(centres):
        return grid, sum(np.exp(-((grid - c) / 10) ** 2) for c in centres)

    computed = bands([1000, 1750, 3100])
    measured = (grid, bands([960, 1680, 2976])[1])  # the computed × 0.96
    measured = (measured[0], measured[1] / measured[1].max())
    assert ex.similarity(computed, measured) < 0.3
    factor, score = ex.best(lambda f: ex.scaled(computed, f), ex.FACTORS, measured)
    assert factor == pytest.approx(0.96, abs=0.002) and score > 0.98
    assert ex.similarity(computed, (grid + 9000, measured[1])) is None


def test_ecd_sign_counts():
    grid = np.linspace(200, 400, 500)
    band = np.exp(-((grid - 300) / 15) ** 2)
    assert ex.similarity((grid, band), (grid, -band), signed=True) == pytest.approx(-1)
    assert ex.similarity((grid, band), (grid, band), signed=True) == pytest.approx(1)


def test_shift_of_energies():
    assert ex.shifted_nm(np.array([ex.HC_EV_NM / 4.0]), 1.0)[0] == pytest.approx(ex.HC_EV_NM / 5.0)
