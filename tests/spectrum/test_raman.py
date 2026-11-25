"""Raman activities and depolarization ratios of ORCA 6.0.1, the Raman intensity, the Sextant input.

Contract: modules/spectrum/analysis/raman.py §1, §4; vibration_data._raman_rows. Oracles, independent of the parser:
  * numbers copied by hand from the user's outputs (tests/data/raman, ORCA 6.0.1, B3LYP/6-31G(d));
  * the symmetry of each mode found here from its displacement vectors (the mirror plane that swaps the two H of
    water): a mode that is not totally symmetric (B2) must have the depolarization ratio 3/4 exactly, a totally
    symmetric one (A1) less (the isotropic polarizability derivative is zero only for the first) — and the
    transition dipole printed in the IR table lies along the C2 axis for A1, across it for B2;
  * the intensity formula written out again here with CODATA 2018 constants, and the laser dependence as the ratio
    of the fourth powers of the scattered wavenumbers.
"""

from dataclasses import replace
from math import exp
from pathlib import Path

import pytest

from azimuth.core import Calculation, orca_input, read_xyz
from modules.spectrum.analysis import raman
from modules.spectrum.readers.outputs import read_any

DATA = Path(__file__).parents[1] / 'data' / 'raman'
H, C, K_B = 6.62607015e-34, 2.99792458e10, 1.380649e-23  # J s, cm/s, J/K


def water(name='h2o_raman_numfreq_orca.out'):
    text = (DATA / name).read_bytes().decode('utf-8')
    return read_any(text, name)


def vibrations(out):
    return {m.index: m for m in out.modes if m.frequency > 0}


def test_water_activities_and_depolarization_as_printed():
    modes = vibrations(water())
    assert sorted(modes) == [6, 7, 8]
    rows = {k: (m.frequency, m.raman_activity, m.depolarization) for k, m in modes.items()}
    assert rows == {6: (1709.38, 7.539542, 0.541696), 7: (3716.81, 77.247856, 0.189020), 8: (3838.92, 38.997507, 0.75)}
    assert [modes[k].intensity for k in (6, 7, 8)] == [79.58, 1.71, 19.76]  # the IR table is read as before
    assert raman.has_raman(water().modes)


def test_depolarization_follows_the_symmetry_of_the_mode():
    out = water()
    for m in vibrations(out).values():
        (_, oy, oz), (_, y1, z1), (_, y2, z2) = m.vectors
        a1 = abs(y2 + y1) < 1e-4 and abs(z2 - z1) < 1e-4 and abs(oy) < 1e-4  # H2 = mirror image of H1
        b2 = abs(y2 - y1) < 1e-4 and abs(z2 + z1) < 1e-4 and abs(oz) < 1e-4  # H2 = minus the mirror image
        assert a1 != b2
        if b2:
            assert m.depolarization == pytest.approx(0.75, abs=1e-6)
        else:
            assert m.depolarization < 0.75 - 0.1
    text = (DATA / 'h2o_raman_numfreq_orca.out').read_text(encoding='utf-8')
    assert '8:   3838.92   0.003911   19.76  0.000318  ( 0.000000 -0.017830 -0.000000)' in text  # B2: dipole along y


def test_analytic_frequencies_give_no_raman_and_say_why():
    out = water('h2o_analytic_freq_no_raman_orca.out')
    assert out.raman_skipped and out.frequencies
    assert not raman.has_raman(out.modes) and all(m.depolarization is None for m in out.modes)
    assert 'NumFreq' in out.assessment and 'NumFreq' not in water().assessment
    assert not water().raman_skipped


def test_intensity_formula_and_the_laser():
    modes = vibrations(water())

    def by_hand(m, laser_nm, t):
        nu0 = 1e7 / laser_nm
        return (nu0 - m.frequency) ** 4 * m.raman_activity / (m.frequency * (1 - exp(-H * C * m.frequency / (K_B * t))))

    for laser in (532.0, 785.0):
        found = raman.intensities(modes.values(), laser, 298.15)
        hand = {k: by_hand(m, laser, 298.15) for k, m in modes.items()}
        top = max(hand.values())
        assert max(found.values()) == pytest.approx(100.0)
        for k in modes:
            assert found[k] == pytest.approx(100 * hand[k] / top, rel=1e-9)
    a, b = raman.intensities(modes.values(), 532.0), raman.intensities(modes.values(), 785.0)
    nu532, nu785 = 1e7 / 532, 1e7 / 785
    expected = ((nu532 - 3716.81) / (nu532 - 1709.38)) ** 4 / (((nu785 - 3716.81) / (nu785 - 1709.38)) ** 4)
    assert (a[7] / a[6]) / (b[7] / b[6]) == pytest.approx(expected, rel=1e-9)
    assert raman.C2 == pytest.approx(H * C / K_B, rel=1e-9)


def test_raman_modes_and_bounds():
    modes = water().modes
    shown = raman.raman_modes(modes, 'activity')
    assert {m.index: m.intensity for m in shown if m.intensity is not None} == {6: 7.539542, 7: 77.247856, 8: 38.997507}
    assert [m.frequency for m in shown] == [m.frequency for m in modes] and shown[8].vectors == modes[8].vectors
    assert max(m.intensity for m in raman.raman_modes(modes, 'intensity') if m.intensity is not None) == pytest.approx(100)
    with pytest.raises(ValueError):
        raman.raman_modes(modes, 'ir')
    with pytest.raises(ValueError):
        raman.intensities(modes, 100.0)
    with pytest.raises(ValueError):
        raman.intensities(modes, 532.0, 0.0)
    with pytest.raises(ValueError):
        raman.intensities([replace(modes[8], frequency=19000.0)], 532.0)  # above the laser line (18797 cm^-1)


WATER = read_xyz('3\nwater\nO 0 0 0.117\nH 0 0.757 -0.467\nH 0 -0.757 -0.467\n')


def test_sextant_raman_input_for_orca():
    calc = Calculation(method='B3LYP', basis='def2-SVP', task='Оптимизация + частоты', raman=True)
    text = orca_input(WATER, calc)
    assert '! B3LYP def2-SVP Opt NumFreq TightSCF' in text and '%elprop\n  Polar 1\nend\n' in text
    assert orca_input(WATER, replace(calc, num_freq=True)).count('NumFreq') == 1
    assert '%elprop' not in orca_input(WATER, replace(calc, task='Энергия'))
    plain = orca_input(WATER, replace(calc, raman=False))
    assert ' Freq ' in plain and 'NumFreq' not in plain and '%elprop' not in plain
    with pytest.raises(ValueError):
        replace(calc, raman=1).validate_settings()


def significant(modes, value):
    """Modes whose value (IR intensity or Raman activity) is above 1e-3 of the largest: a numerical (NumFreq) zero
    of a forbidden band is far below it."""
    top = max(value(m) or 0.0 for m in modes)
    return {m.index for m in modes if (value(m) or 0.0) > 1e-3 * top}


def test_ethylene_mutual_exclusion():
    # D2h: Γ_vib = 3 Ag + Au + 2 B1g + B1u + B2g + 2 B2u + 2 B3u — g modes are seen in Raman only, u modes in IR
    # only, Au in neither (any choice of the axes gives the same counts); the 3 Ag modes are polarized
    modes = list(vibrations(read_any((DATA / 'c2h4_raman_numfreq_orca.out').read_text(encoding='utf-8'), 'c2h4.out')).values())
    assert len(modes) == 12 and all(m.raman_activity is not None and m.intensity is not None for m in modes)
    seen_raman, seen_ir = significant(modes, lambda m: m.raman_activity), significant(modes, lambda m: m.intensity)
    assert len(seen_raman) == 6 and len(seen_ir) == 5 and not seen_raman & seen_ir
    assert raman.seen(modes) == seen_raman
    assert len({m.index for m in modes} - seen_raman - seen_ir) == 1
    polarized = {m.index for m in modes if m.index in seen_raman and m.depolarization < 0.75 - 0.01}
    assert len(polarized) == 3
    assert all(m.depolarization == pytest.approx(0.75, abs=1e-3) for m in modes if m.index in seen_raman - polarized)


def test_formaldehyde_all_modes_in_both_spectra():
    # C2v: Γ_vib = 3 A1 + B1 + 2 B2 — every mode is IR and Raman active; A1 polarized (ρ < 3/4), B1 and B2 not
    modes = list(vibrations(read_any((DATA / 'ch2o_raman_numfreq_orca.out').read_text(encoding='utf-8'), 'ch2o.out')).values())
    assert len(modes) == 6
    indices = {m.index for m in modes}
    assert significant(modes, lambda m: m.raman_activity) == indices and significant(modes, lambda m: m.intensity) == indices
    assert raman.seen(modes) == indices
    rho = sorted(m.depolarization for m in modes)
    assert all(r < 0.75 - 0.01 for r in rho[:3]) and all(r == pytest.approx(0.75, abs=1e-3) for r in rho[3:])
