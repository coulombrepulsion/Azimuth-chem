"""The powder X-ray diffraction pattern (modules/compass/chemistry/powder.py).

Oracles, independent of the tested code:
  * f(0) of every neutral atom and ion of the Waasmaier–Kirfel table is its number of electrons (Z − charge), within
    0.04 electron (the accuracy of their fits at s = 0: at most 0.038, Os);
  * rock salt (F m -3 m, Na at 0 0 0, Cl at 1/2 1/2 1/2): F = 4 (f_Na + f_Cl) for h, k, l all even, 4 (f_Na − f_Cl)
    for all odd, 0 for mixed; multiplicities of m-3m {111} 8, {200} 6, {220} 12, {311} 24, {222} 8 (textbook);
    the intensities written here from these formulas with Lp = (1 + cos² 2θ) / (sin² θ cos θ) — and the pattern
    of the PDF card 05-0628 (Swanson & Fuyat 1953) in its order: 200 strongest, then 220, 222 and 111 weak;
    the line 200 at 2θ = 31.70° (d = a / 2 = 2.8201 Å, Cu Kα₁: 2 arcsin(1.54059 / 5.6402));
  * silicon (diamond, F d -3 m origin choice 2, 8 atoms): 200 and 222 absent (h + k + l = 4n + 2), 111 strongest,
    then 220 and 311 (PDF 27-1402);
  * a displacement U = 0.01 Å² lowers |F|² by exp(-16 π² U s²).
"""

from math import asin, cos, exp, pi, radians, sin, sqrt, tan
import json
from pathlib import Path

import pytest

from modules.compass.chemistry import crystal as cr
from modules.compass.chemistry import powder
from tests.compass.test_crystal_symmetry import rock_salt


def test_f0_at_zero_is_the_number_of_electrons():
    ions = json.loads(powder.TABLE.read_text(encoding='utf-8'))['ions']
    assert len(ions) == 211
    for name, (z, c, a, b) in ions.items():
        charge = 0
        if name.endswith(('+', '-')):
            digits = ''.join(ch for ch in name if ch.isdigit())
            charge = int(digits or 1) * (1 if name.endswith('+') else -1)
        assert abs(c + sum(a) - (z - charge)) < 0.04, name  # the fits reproduce f(0) within 0.04 electrons (Os: 0.038)
    assert abs(powder.f0('Na', 0) - 11) < 0.01 and powder.f0('X', 0.3) == 0.0


def _expected_rock_salt(wavelength):
    a = 5.6402
    rows = {}
    for hkl, m in (((1, 1, 1), 8), ((2, 0, 0), 6), ((2, 2, 0), 12), ((3, 1, 1), 24), ((2, 2, 2), 8)):
        d = a / sqrt(sum(x * x for x in hkl))
        s = 1 / (2 * d)
        fna, fcl = powder.f0('Na', s), powder.f0('Cl', s)
        f = 4 * (fna + fcl) if hkl[0] % 2 == 0 else 4 * (fna - fcl)
        theta = asin(wavelength / (2 * d))
        rows[hkl] = (2 * theta * 180 / pi, m * f * f * (1 + cos(2 * theta) ** 2) / (sin(theta) ** 2 * cos(theta)))
    top = max(i for _, i in rows.values())
    return {h: (t, 100 * i / top) for h, (t, i) in rows.items()}


def test_rock_salt():
    lines = powder.pattern(rock_salt(), powder.CU, 20, 60)
    expected = _expected_rock_salt(powder.CU)
    found = {line.hkl: line for line in lines}
    assert set(found) == set(expected)  # the mixed hkl (100, 110, 210 …) are absent
    for hkl, (t, i) in expected.items():
        assert abs(found[hkl].two_theta - t) < 1e-6 and abs(found[hkl].intensity - i) < 1e-6
    assert found[(1, 1, 1)].multiplicity == 8 and found[(3, 1, 1)].multiplicity == 24
    assert abs(found[(2, 0, 0)].two_theta - 31.70) < 0.01
    by_intensity = [line.hkl for line in sorted(lines, key=lambda x: -x.intensity)]
    assert by_intensity[:2] == [(2, 0, 0), (2, 2, 0)] and found[(1, 1, 1)].intensity < 25


def silicon():
    text = ('data_Si\n_cell_length_a 5.4309\n_cell_length_b 5.4309\n_cell_length_c 5.4309\n'
            "_space_group_name_H-M_alt 'F d -3 m :2'\nloop_\n_atom_site_label\n_atom_site_fract_x\n"
            '_atom_site_fract_y\n_atom_site_fract_z\nSi1 0.125 0.125 0.125\n')
    return cr.parse_cif(text)


def test_silicon_from_the_symbol():
    c = silicon()
    assert len(c.operations) == 192 and len(cr.unit_cell(c)) == 8
    lines = powder.pattern(c, powder.CU, 20, 80)
    found = {line.hkl for line in lines}
    assert (2, 0, 0) not in found and (2, 2, 2) not in found and {(1, 1, 1), (2, 2, 0), (3, 1, 1)} <= found
    order = [line.hkl for line in sorted(lines, key=lambda x: -x.intensity)][:3]
    assert order == [(1, 1, 1), (2, 2, 0), (3, 1, 1)]


def test_displacement_and_profile():
    salt = rock_salt()
    warm = cr.Crystal(salt.title, salt.cell, tuple(cr.Site(s.label, s.symbol, s.x, s.y, s.z, 1.0, '', (), 0.01)
                                                    for s in salt.sites), salt.operations, salt.space_group)
    cold = {line.hkl: line.f2 for line in powder.pattern(salt, powder.CU, 20, 60)}
    hot = {line.hkl: line for line in powder.pattern(warm, powder.CU, 20, 60)}
    for hkl, line in hot.items():
        s = 1 / (2 * line.d)
        assert abs(line.f2 / cold[hkl] - exp(-16 * pi * pi * 0.01 * s * s)) < 1e-9
    lines = powder.pattern(salt, powder.CU, 20, 60)
    xs, ys = powder.profile(lines, 20, 60, 0.01, 0.1, 0.0)
    peak = max(range(len(ys)), key=ys.__getitem__)
    assert abs(xs[peak] - 31.70) < 0.02 and abs(max(ys) - 100) < 1e-9
    back = powder.read_xy('# measured\n' + powder.write_xy(xs, ys))
    assert len(back[0]) == len(xs) and abs(back[1][peak] - 100) < 1e-3
    with pytest.raises(ValueError):
        powder.pattern(salt, powder.CU, 60, 20)
    with pytest.raises(ValueError):
        powder.read_xy('nothing here\n')


# the Kα₂ line, the preferred orientation of March–Dollase, the widths of Caglioti. Oracles: Bragg's law at λ(Kα₂) =
# 1.5444274 Å (Hölzer 1997) and the textbook splitting Δ2θ ≈ 2 tan θ Δλ/λ; the March–Dollase weights of the reflections
# of rock salt counted by hand (the 6 of {200}: 2 along the axis 001, 4 across; the 12 of {220}: 4 across, 8 at 45°);
# the mean of P over the sphere is 1 (Dollase 1986); FWHM² = U tan² θ + V tan θ + W.

def _lp(theta):
    return (1 + cos(2 * theta) ** 2) / (sin(theta) ** 2 * cos(theta))


def test_the_alpha2_line():
    lines = powder.pattern(rock_salt(), powder.CU, 20, 100)
    second = powder.alpha2(lines, powder.CU, powder.KA2['Cu Kα₁'])
    assert len(second) == len(lines) and all(line.alpha2 for line in second)
    for one, two in zip(lines, second):
        assert two.hkl == one.hkl and abs(two.two_theta - 2 * asin(1.5444274 / (2 * one.d)) * 180 / pi) < 1e-9
        t1 = radians(one.two_theta) / 2
        split = 2 * tan(t1) * (1.5444274 - 1.5405929) / 1.5405929 * 180 / pi
        assert abs((two.two_theta - one.two_theta) - split) < 0.003 * max(1.0, split)
        t2 = radians(two.two_theta) / 2
        assert abs(two.intensity / one.intensity - 0.5 * _lp(t2) / _lp(t1)) < 1e-12
    assert 0.07 < second[1].two_theta - lines[1].two_theta < 0.09  # 200 at 31.7°: Kα₁ and Kα₂ 0.08° apart
    xs, ys = powder.profile(lines + second, 30.5, 33, 0.002, 0.03, 0.0)  # narrow lines: two tops, the second half as high
    tops = [k for k in range(1, len(ys) - 1) if ys[k] > ys[k - 1] and ys[k] >= ys[k + 1] and ys[k] > 5]
    assert len(tops) == 2 and abs(ys[tops[1]] / ys[tops[0]] - 0.5) < 0.03


def test_the_preferred_orientation_of_march_dollase():
    salt = rock_salt()
    plain = {line.hkl: line for line in powder.pattern(salt, powder.CU, 20, 60)}
    same = {line.hkl: line for line in powder.pattern(salt, powder.CU, 20, 60, texture=((0, 0, 1), 1.0))}
    assert all(abs(same[h].intensity - plain[h].intensity) < 1e-9 for h in plain)
    r = 0.8
    textured = {line.hkl: line for line in powder.pattern(salt, powder.CU, 20, 60, texture=((0, 0, 1), r))}
    p0, p90 = r ** -3, r ** 1.5
    p45 = (r * r / 2 + 1 / (2 * r)) ** -1.5
    w200, w220 = (2 * p0 + 4 * p90) / 6, (4 * p90 + 8 * p45) / 12
    want = plain[(2, 2, 0)].intensity / plain[(2, 0, 0)].intensity * w220 / w200
    assert abs(textured[(2, 2, 0)].intensity / textured[(2, 0, 0)].intensity - want) < 1e-9
    assert textured[(2, 0, 0)].f2 == plain[(2, 0, 0)].f2  # the structure factors themselves untouched
    n = 200_000  # the mean over the sphere: cos α uniform in [−1, 1]
    mean = sum(powder.march(-1 + (2 * k + 1) / n, 0.6) for k in range(n)) / n
    assert abs(mean - 1) < 1e-4
    with pytest.raises(ValueError):
        powder.pattern(salt, powder.CU, 20, 60, texture=((0, 0, 0), 0.8))


def test_the_widths_of_caglioti():
    assert abs(powder.caglioti(60.0, 0, 0, 0.01) - 0.1) < 1e-12
    assert abs(powder.caglioti(90.0, 0.04, 0, 0) - 0.2) < 1e-12  # tan 45° = 1
    assert abs(powder.caglioti(90.0, 0.01, -0.01, 0.01) - 0.1) < 1e-12
    lines = (powder.Line(30.0, 3.0, (1, 0, 0), 1, 100.0, 1.0), powder.Line(120.0, 1.0, (2, 0, 0), 1, 100.0, 1.0))
    xs, ys = powder.profile(lines, 20, 140, 0.002, uvw=(0.05, 0.0, 0.002), eta=0.0)
    step = xs[1] - xs[0]
    left = sum(y for x, y in zip(xs, ys) if x < 75) * step
    right = sum(y for x, y in zip(xs, ys) if x >= 75) * step
    assert abs(left / right - 1) < 0.01  # equal intensities — equal areas, though the second line is 5 times wider
    assert max(ys[:len(ys) // 2]) > 2 * max(ys[len(ys) // 2:])


def test_the_anomalous_dispersion():
    # f = f₀ + f′ + i f″ — rock salt with Cu Kα: F(hkl) = 4 (f_Na ± f_Cl), each f with the f′, f″ of the
    # table, |F|² = Re² + Im² written out here; the table against the International Tables C, 4.2.6.8 (Cromer &
    # Liberman), within 0.05 electron: Fe with Cu Kα f′ = −1.134, f″ = 3.197; Cu with Cu Kα −2.019, 0.589; and an
    # arbitrary wavelength has no f′, f″
    salt = rock_salt()
    plain = {line.hkl: line for line in powder.pattern(salt, powder.CU, 20, 60)}
    found = {line.hkl: line for line in powder.pattern(salt, powder.CU, 20, 60, anomalous=True)}
    (na1, na2), (cl1, cl2) = powder.dispersion('Na', powder.CU), powder.dispersion('Cl', powder.CU)
    for hkl in ((1, 1, 1), (2, 0, 0)):
        d = found[hkl].d
        s = 1 / (2 * d)
        sign = 1 if hkl[0] % 2 == 0 else -1
        re = 4 * (powder.f0('Na', s) + na1 + sign * (powder.f0('Cl', s) + cl1))
        im = 4 * (na2 + sign * cl2)
        assert found[hkl].f2 / found[hkl].multiplicity == pytest.approx(re * re + im * im, rel=1e-9)
        assert found[hkl].f2 != pytest.approx(plain[hkl].f2, rel=1e-4)
    assert powder.dispersion('Fe', powder.CU) == pytest.approx((-1.134, 3.197), abs=0.05)
    assert powder.dispersion('Cu', powder.CU) == pytest.approx((-2.019, 0.589), abs=0.05)
    assert powder.tube(powder.KA2['Mo Kα₁']) == 'Mo Kα₁' and powder.tube(1.0) is None
    with pytest.raises(ValueError):
        powder.pattern(salt, 1.0, 20, 60, anomalous=True)
