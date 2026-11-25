"""UV-Vis and NMR from ORCA outputs (modules/spectrum/readers/orca_spectra.py).

Oracles, independent of the parser:
  * numbers copied by hand from the files (tests/data/orca_cclib, cclib test data);
  * ORCA 6 prints each excitation in eV and in cm^-1: their ratio is 1 eV = 8065.543937 cm^-1 (CODATA)
    within the rounding of the printed digits (0.05 cm^-1 -> 6e-6 eV, plus 5e-7 eV): 1e-5 eV;
    wavelength = 1e7 / wavenumber within 0.05 nm printed + 0.05 cm^-1 -> 0.06 nm;
  * the absorption constant K = pi e^2 N_A / (1000 ln 10 m_e c^2) computed here from CODATA 2018 values;
    K / sqrt(pi) = 1.3062974e8, the factor of Gaussian's UV-Vis plot (independent source);
  * the area under the curve, integral of epsilon d(wavenumber), equals K * sum f (normalised Gaussians;
    +-4 sigma keeps 1 - 1.5e-8 of each band; the trapezoid rule on 6000 points: rtol 1e-4);
  * NMR: ORCA prints equal shieldings for atoms related by the C2h symmetry of divinylbenzene: the
    groups of topologically equivalent atoms are exactly these pairs.
"""

from math import pi, sqrt, log
from pathlib import Path

import numpy as np
import pytest

from modules.spectrum.readers.orca import read_output
from modules.spectrum.readers.orca_spectra import (
    EV_CM,
    K_ABSORPTION,
    Excitation,
    equivalent_groups,
    read_absorption,
    read_shieldings,
    shifts,
    uv_curve,
)

DATA = Path(__file__).parents[1] / 'data' / 'orca_cclib'


def text(name):
    return (DATA / name).read_text(encoding='utf-8')


def test_orca6_absorption_table():
    found = read_absorption(text('dvb_td_orca6.0.out'))
    assert len(found) == 10 and [e.multiplicity for e in found].count(3) == 5
    bright = max(found, key=lambda e: e.fosc)
    assert (bright.label, bright.energy_ev, bright.wavenumber, bright.wavelength, bright.fosc) == (
        '2-1Bu',
        5.731321,
        46226.2,
        216.3,
        1.170940055,
    )
    for e in found:
        assert e.wavenumber / EV_CM == pytest.approx(e.energy_ev, abs=1e-5)
        assert 1e7 / e.wavenumber == pytest.approx(e.wavelength, abs=0.06)
        if e.multiplicity == 3:
            assert e.fosc == 0.0


def test_orca5_absorption_table_with_spin_forbidden_rows():
    found = read_absorption(text('dvb_td_orca5.0.out'))
    assert len(found) == 10
    first = found[0]  # the lowest triplet, 25241.0 cm^-1, printed as «spin forbidden (mult=3)»
    assert (first.state, first.wavenumber, first.fosc, first.multiplicity) == (6, 25241.0, 0.0, 3)
    bright = max(found, key=lambda e: e.fosc)
    assert (bright.state, bright.wavenumber, bright.fosc) == (2, 46230.3, 1.171011871)
    # the same molecule and method in ORCA 6.0: the same bright state within 0.01 eV
    six = max(read_absorption(text('dvb_td_orca6.0.out')), key=lambda e: e.fosc)
    assert bright.energy_ev == pytest.approx(six.energy_ev, abs=0.01)


def test_rocis_layout_keeps_ground_state_excitations():
    found = read_absorption(text('dvb_rocis_orca5.0.out'))
    assert len(found) == 28 and all(e.wavenumber > 0 for e in found)
    assert max(e.fosc for e in found) > 0


def test_absorption_constant_from_codata():
    e = 4.803204712570263e-10  # esu (CODATA 2018 e = 1.602176634e-19 C, times c/10)
    n_a, m_e, c = 6.02214076e23, 9.1093837015e-28, 2.99792458e10
    k = pi * e * e * n_a / (1000 * log(10) * m_e * c * c)
    assert K_ABSORPTION == pytest.approx(k, rel=1e-5)
    assert k / sqrt(pi) == pytest.approx(1.3062974e8, rel=1e-6)


def test_uv_curve_area_and_peak():
    found = read_absorption(text('dvb_td_orca6.0.out'))
    x, y = uv_curve(found, 0.3, points=6000)
    assert np.all(np.diff(x) > 0)
    nu = 1e7 / x
    area = -np.trapezoid(y, nu) if hasattr(np, 'trapezoid') else -np.trapz(y, nu)
    assert area == pytest.approx(K_ABSORPTION * sum(e.fosc for e in found), rel=1e-4)
    alone = uv_curve([Excitation(1, '1', 5.0, 5.0 * EV_CM, 1e7 / (5.0 * EV_CM), 0.5)], 0.3, points=6001)
    peak = alone[0][np.argmax(alone[1])]
    assert peak == pytest.approx(1e7 / (5.0 * EV_CM), abs=0.1)
    sigma = 0.3 * EV_CM / (2 * sqrt(log(2)))
    assert alone[1].max() == pytest.approx(K_ABSORPTION * 0.5 / (sigma * sqrt(pi)), rel=1e-5)
    with pytest.raises(ValueError):
        uv_curve(found, 5.0)
    with pytest.raises(ValueError):
        uv_curve([e for e in found if e.fosc == 0], 0.3)


def test_nmr_shieldings_groups_and_shifts():
    out = text('dvb_nmr_orca6.0.out')
    found = read_shieldings(out)
    assert len(found) == 20 and (found[0].element, found[0].isotropic, found[0].anisotropy) == ('C', 114.398, 147.504)
    assert (found[19].element, found[19].isotropic) == ('H', 27.108)
    geometry = read_output(out).geometry
    groups = equivalent_groups(geometry)
    assert len(groups) == 10 and all(len(g) == 2 for g in groups)
    by_atom = {s.atom: s.isotropic for s in found}
    for a, b in groups:
        assert by_atom[a] == by_atom[b]  # ORCA: symmetric partners, equal shieldings
    rows = shifts(found, {'C': 190.0}, groups)
    carbon = [r for r in rows if r[1] == 'C']
    hydrogen = [r for r in rows if r[1] == 'H']
    assert len(carbon) == 5 and len(hydrogen) == 5 and all(r[2] is None for r in hydrogen)
    assert carbon[0][2] == pytest.approx(190.0 - 114.398) and carbon[0][0] == (0, 1)


def test_methyl_protons_are_averaged_and_mirror_partners_grouped():
    from modules.compass.chemistry import library

    ethanol = library.molecule(next(k for k in library.keys() if k.startswith('Этанол')))
    symbols = [a.symbol for a in ethanol.atoms]
    groups = equivalent_groups(ethanol)
    hydrogen = sorted(len(g) for g in groups if symbols[g[0]] == 'H')
    assert hydrogen == [1, 2, 3]  # OH, CH2 (mirror partners in the Cs conformer), CH3 (rotor)


def test_other_outputs_have_neither():
    for name in ('water_mp2_orca5.0.out', 'dvb_gopt_orca6.0.out'):
        assert read_absorption(text(name)) == () and read_shieldings(text(name)) == ()
    output = read_output(text('dvb_td_orca6.0.out'))
    assert len(output.absorption) == 10 and output.shieldings == ()
