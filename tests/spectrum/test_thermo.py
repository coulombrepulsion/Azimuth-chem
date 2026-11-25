"""Thermochemistry (modules/spectrum/analysis/thermo.py).

Oracles: the thermochemistry printed by Psi4 1.7 for divinylbenzene (cclib test data, the same frequencies
and geometry; σ = 2, 298.15 K, 101325 Pa): ZPE, E, H, S by parts, G, Cv; the standard molar entropy of argon
gas (NIST: 154.846 J/(mol·K) at 1 bar, 298.15 K), converted here to 1 atm; the symmetry numbers of the
textbook point groups; the limits of Grimme's quasi-RRHO.
"""

from math import log
from pathlib import Path

import pytest

from modules.spectrum.analysis import thermo
from modules.spectrum.readers.psi4 import read_psi4
from azimuth.core import Atom, Molecule

DATA = Path(__file__).parents[1] / 'data' / 'psi4'
PER_MOL = thermo.HARTREE * thermo.NA  # J/mol per hartree


def dvb():
    out = read_psi4((DATA / 'dvb_ir_rhf_psi4-1.7.out').read_text(encoding='utf-8'))
    return out, out.vibration_geometry or out.geometry


def test_divinylbenzene_against_psi4():
    out, geometry = dvb()
    r = thermo.thermochemistry(geometry, out.frequencies, out.energies[-1], sigma=2)
    assert r.modes == 54 and not r.linear and not r.notes
    # printed by Psi4 with 8 decimals; the frequencies are printed with 4 (about 1e-8 Eh in ZPE)
    assert r.zpe == pytest.approx(0.19168059, abs=5e-8)
    assert r.thermal_energy == pytest.approx(0.19888892, abs=5e-8)
    assert r.enthalpy == pytest.approx(0.19983311, abs=5e-8)
    assert r.gibbs == pytest.approx(0.16038928, abs=5e-8)
    assert r.entropy * 1e3 == pytest.approx(0.13229523, abs=1e-7)  # mEh/K (S of the 4-decimal frequencies)
    parts = {k: v[1] * 1e3 for k, v in r.parts.items()}
    assert parts['translational'] == pytest.approx(0.06454379, abs=5e-8)
    assert parts['rotational'] == pytest.approx(0.04484891, abs=5e-8)
    assert parts['vibrational'] == pytest.approx(0.02290253, abs=5e-8)
    assert sum(v[2] for v in r.parts.values()) * 1e3 == pytest.approx(0.04602885, abs=5e-8)
    assert r.total(r.gibbs) == pytest.approx(-379.60972224, abs=1e-7)
    assert r.total(r.enthalpy) == pytest.approx(-379.57027841, abs=1e-7)


def test_argon_sackur_tetrode():
    r = thermo.thermochemistry(Molecule('Ar', (Atom('Ar', 0.0, 0.0, 0.0),)), (), None)
    s = r.entropy * PER_MOL
    nist = 154.846 - 8.314462618 * log(101325 / 1e5)  # 1 bar -> 1 atm
    nist += 1.5 * 8.314462618 * log(39.9623831 / 39.948)  # the isotope 40Ar instead of the average mass
    assert s == pytest.approx(nist, abs=0.01)
    assert r.modes == 0 and r.zpe == 0 and r.thermal_energy * PER_MOL == pytest.approx(1.5 * 8.314462618 * 298.15, rel=1e-9)


def test_linear_molecule_and_left_out_frequencies():
    co2 = Molecule('CO2', (Atom('C', 0, 0, 0), Atom('O', 0, 0, 1.16), Atom('O', 0, 0, -1.16)))
    r = thermo.thermochemistry(co2, (667.0, 667.0, 1333.0, 2349.0), None, sigma=2)
    assert r.linear and r.modes == 4 and not r.notes
    assert r.parts['rotational'][0] * PER_MOL == pytest.approx(8.314462618 * 298.15, rel=1e-9)  # E_rot = RT
    one = thermo.thermochemistry(co2, (667.0, 667.0, 1333.0, 2349.0), None, sigma=1)
    assert (one.parts['rotational'][1] - r.parts['rotational'][1]) * PER_MOL == pytest.approx(8.314462618 * log(2), rel=1e-9)
    bad = thermo.thermochemistry(co2, ((1, -120.0), (2, 667.0), (3, 667.0), (4, 1333.0), (5, 2349.0)), None, sigma=2)
    assert bad.left_out == (-120.0,) and bad.modes == 4 and any('Мнимых' in n for n in bad.notes)
    # a small imaginary frequency (the nearly free methyl of toluene in GFN2-xTB: −11 cm⁻¹) is not called a saddle
    small = thermo.thermochemistry(co2, ((1, -11.0), (2, 667.0), (3, 667.0), (4, 1333.0), (5, 2349.0)), None, sigma=2)
    assert any('Маленьких мнимых' in n for n in small.notes) and not any('не минимум' in n for n in small.notes)
    assert not any('Маленьких' in n for n in bad.notes)
    few = thermo.thermochemistry(co2, (667.0, 1333.0), None)
    assert any('ожидается 4' in n for n in few.notes)
    triplet = thermo.thermochemistry(co2, (667.0, 667.0, 1333.0, 2349.0), None, multiplicity=3, sigma=2)
    assert triplet.parts['electronic'][1] * PER_MOL == pytest.approx(8.314462618 * log(3), rel=1e-9)
    for kwargs in ({'temperature': 0}, {'pressure': -1}, {'sigma': 0}):
        with pytest.raises(ValueError):
            thermo.thermochemistry(co2, (667.0,), None, **kwargs)


def test_quasi_rrho_limits():
    out, geometry = dvb()
    plain = thermo.thermochemistry(geometry, out.frequencies, None, sigma=2)
    quasi = thermo.thermochemistry(geometry, out.frequencies, None, sigma=2, qrrho=True)
    assert quasi.thermal_energy == plain.thermal_energy  # only the entropy changes
    assert quasi.parts['vibrational'][1] < plain.parts['vibrational'][1]  # the 137 cm⁻¹ mode is damped
    _, _, s_high, _ = thermo._vibration([3000.0], 298.15, False)
    _, _, q_high, _ = thermo._vibration([3000.0], 298.15, True)
    assert abs(q_high - s_high) < 1e-5 * thermo.R  # w = 1 − 1.2e-6 at 3000 cm⁻¹
    # near 0 the harmonic S grows without limit, the quasi-RRHO one stays below that of a free rotor with
    # the moment B_av (μ' → B_av): R (1/2 + ln √(8π³ B_av k T / h²)), about 5.5 R at 298 K
    limit = thermo.R * (0.5 + log((8 * 3.141592653589793 ** 3 * 1e-44 * thermo.KB * 298.15 / thermo.H ** 2) ** 0.5))
    for nu in (5.0, 0.01):
        _, _, s_low, _ = thermo._vibration([nu], 298.15, False)
        _, _, q_low, _ = thermo._vibration([nu], 298.15, True)
        assert q_low < limit and q_low < s_low
    assert s_low > limit  # 0.01 cm⁻¹: the harmonic entropy is already larger than any rotor's


def test_symmetry_numbers_and_multiplicity():
    expected = {'C1': 1, 'Cs': 1, 'Ci': 1, 'C2': 2, 'C2v': 2, 'C3v': 3, 'C2h': 2, 'D2h': 4, 'D3h': 6,
                'D6h': 12, 'D3d': 6, 'Td': 12, 'Oh': 24, 'Ih': 60, 'S4': 2, 'D∞h': 2, 'C∞v': 1, '': 1}
    assert {g: thermo.symmetry_number(g) for g in expected} == expected
    assert thermo.multiplicity('Multiplicity           Mult            ....    3\n') == 3
    assert thermo.multiplicity(' Charge =  1 Multiplicity = 2\n') == 2
    assert thermo.multiplicity('Geometry (in Angstrom), charge = 0, multiplicity = 1:\n') == 1
    assert thermo.multiplicity('nothing') == 1


def test_multiplicity_of_every_program_and_none_when_absent():
    # GAMESS, NWChem and Q-Chem print it too (doublet cations of the cclib data); nothing printed — None,
    # not a silent singlet (multiplicity() keeps 1 for the callers that say so)
    import gzip

    data = Path(__file__).parents[1] / 'data'
    for name in ('gamess/dvb_un_sp_gamess-2017.out.gz', 'nwchem/dvb_un_sp_ks_nwchem-7.0.out.gz',
                 'qchem/dvb_sp_un_qchem-5.4.out.gz'):
        text = gzip.decompress((data / name).read_bytes()).decode('utf-8')
        assert thermo.find_multiplicity(text) == 2, name
    for name in ('gamess/dvb_sp_gamess-2017.out.gz', 'nwchem/dvb_sp_ks_nwchem-7.0.out.gz', 'qchem/dvb_sp_qchem-5.4.out.gz'):
        assert thermo.find_multiplicity(gzip.decompress((data / name).read_bytes()).decode('utf-8')) == 1, name
    assert thermo.find_multiplicity('nothing') is None and thermo.multiplicity('nothing') == 1


def test_vibrations_stay_finite_at_low_temperature():
    # 3000 cm-1 at 10 K overflowed ((e^x - 1)^2, x = 431); now the closed forms with exp(-x): the energy is
    # the zero-point energy, entropy and heat capacity vanish; at high T the classical limits hold
    import math

    zpe, e, s, cv = thermo._vibration([3000.0, 50.0], 1.0, False)
    theta = thermo.H * thermo.C * 3000.0 * 100.0 / thermo.KB
    assert all(math.isfinite(v) for v in (zpe, e, s, cv))
    assert e == pytest.approx(zpe, rel=1e-12) and s >= 0 and cv >= 0
    zpe, e, s, cv = thermo._vibration([3000.0], 10.0, False)
    assert e == pytest.approx(thermo.R * theta / 2, rel=1e-12) and s < 1e-150 and cv < 1e-150
    _, e, _, cv = thermo._vibration([10.0], 5000.0, False)  # x = 0.003: E - ZPE -> RT, Cv -> R
    assert cv == pytest.approx(thermo.R, rel=1e-5)
    for T in (1.0, 10.0, 298.15, 5000.0):  # the whole range of the window
        assert all(math.isfinite(v) for v in thermo._vibration([5.0, 1000.0, 4000.0], T, True))


# MOPAC — its own THERMO table (MOPAC 23.2.5) as the oracle of our RRHO numbers


def _mopac(name):
    from modules.spectrum.readers.mopac import read_mopac

    path = Path(__file__).parents[1] / 'data' / 'mopac' / f'{name}.out'
    return read_mopac(path.read_text(encoding='utf-8'), path), path.read_text(encoding='utf-8')


def test_mopac_thermo_table_is_read():
    output, _ = _mopac('h2o_pm7_force_thermo')
    assert output.mopac_thermo == ((298.0, -57.8, 2373.5129, 8.0571, 45.0509), (398.0, -56.983, 3190.1265, 8.2942, 47.4122))
    output, _ = _mopac('c6h6_pm7_force_thermo')
    assert len(output.mopac_thermo) == 22 and output.mopac_thermo[0][0] == 298.0
    assert _mopac('h2o_pm7_opt')[0].mopac_thermo == ()


def test_rrho_reproduces_mopac_thermo():
    per = thermo.HARTREE * thermo.NA / 4.184  # cal/mol per hartree
    for name, sigma in (('h2o_pm7_force_thermo', 2), ('c6h6_pm7_force_thermo', 12)):
        output, _ = _mopac(name)
        for t, hof, h, cp, s in output.mopac_thermo[:4]:
            r = thermo.thermochemistry(output.vibration_geometry, output.frequencies, None, t, 101325.0, 1, sigma)
            assert (r.enthalpy - r.zpe) * per == pytest.approx(h, abs=0.01), (name, t)  # MOPAC: H without ZPE
            # MOPAC weighs atoms with average masses (18.0152 for water): S_trans + S_rot 0.001-0.005 apart
            assert r.entropy * per == pytest.approx(s, abs=0.01), (name, t)
    output, _ = _mopac('h2o_pm7_force_thermo')
    r = thermo.thermochemistry(output.vibration_geometry, output.frequencies, None, 298.0, 101325.0, 1, 2)
    parts = {k: v[1] * per for k, v in r.parts.items()}
    assert parts['vibrational'] == pytest.approx(0.0184, abs=1e-3)
    assert parts['rotational'] == pytest.approx(10.4257, abs=2e-3)
    assert parts['translational'] == pytest.approx(34.6068, abs=2e-3)


def test_mopac_multiplicity():
    assert thermo.find_multiplicity(_mopac('h2o_pm7_force_thermo')[1]) == 1  # RHF, doubly occupied levels only
    assert thermo.find_multiplicity(_mopac('ch3_pm7_uhf_doublet_force')[1]) == 2  # «DOUBLET STATE CALCULATION»
