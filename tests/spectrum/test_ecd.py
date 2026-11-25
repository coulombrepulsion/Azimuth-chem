"""Electronic circular dichroism — rotatory strengths from ORCA 5 / 6 and Gaussian 09, the ECD curve.

Contract (modules/spectrum/readers/orca_spectra.py §1, §4): R in 10^-40 cgs per excitation, length and velocity gauge;
delta_epsilon(nu) = sum nu_i R_i / (C_R sigma sqrt(pi)) exp(-((nu - nu_i) / sigma)^2), C_R = 3000 h c ln 10 /
(32 pi^3 N_A). Oracles, independent of the parser and of the curve code:
  * numbers copied by hand from the outputs (ORCA 6.0.1, cclib dvb_td ORCA 5.0, G09 A.02);
  * C_R computed here from CODATA 2018; 4 C_R is the textbook 9.184e-39 of D = 9.184e-39 * integral eps / nu;
  * an independent route through the already verified UV-Vis constant K (test_orca_spectra): the dipole strength
    of one band from f, D = f / (8 pi^2 m_e c nu / (3 h e^2)), equals 4 C_R * integral of eps / nu of uv_curve
    (narrow band: sigma / nu = 0.02 gives a relative error below 1e-3);
  * the curve of one band: its area, its peak height, the Stephens-Harada form written in eV (an independent
    implementation here), the sign of R, the mirror image (all R negated) giving the curve negated.
"""

from dataclasses import replace
from math import log, pi, sqrt
from pathlib import Path

import numpy as np
import pytest

from modules.spectrum.readers.orca_spectra import (
    C_ROTATORY,
    EV_CM,
    K_ABSORPTION,
    Excitation,
    cd_curve,
    read_absorption,
    read_rotatory,
    rotatory_is_zero,
    uv_curve,
)
from modules.spectrum.readers.outputs import read_any

DATA = Path(__file__).parents[1] / 'data'
H, C, N_A, M_E, E = 6.62607015e-27, 2.99792458e10, 6.02214076e23, 9.1093837015e-28, 4.803204712570263e-10


def read(name):
    return (DATA / name).read_bytes().decode('utf-8', errors='replace')


def area(y, x):
    return np.trapezoid(y, x) if hasattr(np, 'trapezoid') else np.trapz(y, x)


def by_label(excitations):
    return {e.label: e for e in excitations}


def test_orca6_length_and_velocity_of_benzaldehyde():
    found = by_label(read_absorption(read('multiwfn/benzaldehyde_cam-b3lyp_orca.out')))
    assert len(found) == 10
    assert (found['1-1A'].r_length, found['1-1A'].r_velocity) == (-0.00042, -0.00023)
    assert (found['6-1A'].r_length, found['6-1A'].r_velocity) == (0.00473, 0.00185)
    assert (found['10-1A'].r_length, found['10-1A'].r_velocity) == (0.00180, 0.00127)
    assert found['6-1A'].rotatory == 0.00185  # the velocity gauge when printed
    assert rotatory_is_zero(found.values())  # planar benzaldehyde is achiral: only numerical noise


def test_orca6_singlets_and_triplets_join_by_label():
    # «1-1A» and «1-3A» share the state number 1: a join by number would mix them up
    found = read_absorption(read('orca601/h2o_tda_triplets.out'))
    assert [e.label for e in found] == ['1-3A', '1-1A', '2-3A', '3-3A', '2-1A', '3-1A']
    assert all(e.r_length is not None and e.r_velocity is not None for e in found)
    assert all(e.rotatory == 0.0 for e in found) and rotatory_is_zero(found)


def test_orca5_one_cd_table_is_the_length_gauge():
    t = read('orca_cclib/dvb_td_orca5.0.out')
    assert read_rotatory(t) == {'1': (0.0, None)}  # the cclib file keeps the first row of the table only
    found = {e.state: e for e in read_absorption(t)}
    assert found[1].r_length == 0.0 and found[1].r_velocity is None and found[1].rotatory == 0.0
    assert all(e.rotatory is None for k, e in found.items() if k != 1)


def test_outputs_without_cd_tables_have_no_rotatory_strengths():
    found = read_absorption(read('orca601/h2o_tddft.out').replace('CD SPECTRUM', 'XX SPECTRUM'))
    assert found and all(e.r_length is None and e.r_velocity is None and e.rotatory is None for e in found)
    assert not rotatory_is_zero(found)  # nothing to judge


def test_gaussian09_rotatory_strengths_of_a_chiral_molecule():
    out = read_any(read('gaussian09/ind_acid_td_g09.out'), 'ind_acid_td_g09.out')
    a = {e.state: e for e in out.absorption}
    assert len(a) == 40 and all(e.r_length is not None and e.r_velocity is not None for e in a.values())
    assert (a[1].r_length, a[1].r_velocity) == (10.8562, 10.9516)
    assert (a[2].r_length, a[2].r_velocity) == (-12.2996, -12.7574)
    assert (a[39].r_length, a[39].r_velocity) == (15.5079, 16.2985)
    assert (a[40].r_length, a[40].r_velocity) == (-3.9281, -4.0478)
    assert not rotatory_is_zero(a.values())
    # the two gauges of one calculation agree within the incompleteness of the basis (here within 1.2·10^-40)
    assert max(abs(e.r_length - e.r_velocity) for e in a.values()) < 1.2


def test_rotatory_constant_from_codata():
    c_r = 3000 * H * C * log(10) / (32 * pi**3 * N_A)
    assert C_ROTATORY == pytest.approx(c_r, rel=1e-5)
    assert 4 * c_r == pytest.approx(9.184e-39, rel=3e-4)  # D = 9.184e-39 * integral of eps / nu (textbooks)


def test_rotatory_constant_agrees_with_the_absorption_constant():
    nu0, f = 40000.0, 0.5
    x, eps = uv_curve([Excitation(1, '1', nu0 / EV_CM, nu0, 1e7 / nu0, f)], 0.1, points=8001)
    nu = 1e7 / x
    d_curve = 4 * C_ROTATORY * -area(eps / nu, nu)
    d_from_f = f / (8 * pi**2 * M_E * C * nu0 / (3 * H * E * E))
    assert d_curve == pytest.approx(d_from_f, rel=1e-3)
    assert 4 * C_ROTATORY * K_ABSORPTION == pytest.approx(3 * H * E * E / (8 * pi**2 * M_E * C), rel=1e-5)


def band(r, nu0=40000.0, state=1):
    return Excitation(state, str(state), nu0 / EV_CM, nu0, 1e7 / nu0, 0.0, 1, None, r)


def test_one_band_area_peak_and_the_form_in_ev():
    nu0, r, fwhm = 40000.0, 25.0, 0.3
    x, y = cd_curve([band(r, nu0)], fwhm, points=8001)
    assert np.all(np.diff(x) > 0)
    nu = 1e7 / x
    assert -area(y, nu) == pytest.approx(nu0 * r * 1e-40 / C_ROTATORY, rel=1e-4)
    assert -area(y / nu, nu) == pytest.approx(r * 1e-40 / C_ROTATORY, rel=2e-3)
    sigma = fwhm * EV_CM / (2 * sqrt(log(2)))
    assert y.max() == pytest.approx(nu0 * r * 1e-40 / (C_ROTATORY * sigma * sqrt(pi)), rel=1e-5)
    assert x[np.argmax(y)] == pytest.approx(1e7 / nu0, abs=0.05)
    # Stephens & Harada (2010), eq. 3, in eV with sigma in eV and the 2.296e-39 of the paper
    e_ev, e0, s_ev = nu / EV_CM, nu0 / EV_CM, fwhm / (2 * sqrt(log(2)))
    stephens = e0 * r * 1e-40 / (2.296e-39 * sqrt(pi) * s_ev) * np.exp(-(((e_ev - e0) / s_ev) ** 2))
    assert np.max(np.abs(y - stephens)) < 5e-4 * y.max()  # 2.296 of the paper is 2.29648 rounded: 2.1e-4


def test_sign_and_mirror_image():
    bands = [band(12.0, 38000.0, 1), band(-30.0, 45000.0, 2), band(7.5, 52000.0, 3)]
    x, y = cd_curve(bands, 0.25)
    assert y[np.argmin(np.abs(x - 1e7 / 45000.0))] < 0 < y[np.argmin(np.abs(x - 1e7 / 38000.0))]
    mirror = [replace(b, r_velocity=-b.r_velocity) for b in bands]
    xm, ym = cd_curve(mirror, 0.25)
    assert np.array_equal(x, xm) and np.allclose(ym, -y, rtol=0, atol=1e-12)


def test_bad_width_and_no_rotatory_strengths():
    with pytest.raises(ValueError):
        cd_curve([band(1.0)], 5.0)
    with pytest.raises(ValueError):
        cd_curve([replace(band(1.0), r_velocity=None)], 0.3)
    with pytest.raises(ValueError):
        cd_curve([replace(band(1.0), r_velocity=float('nan'))], 0.3)
