"""azimuth/handbook.py — the data of «Справка → Справочник»: the units against the constants the program computes with,
the solvents and factors as Sextant and Spectrum have them, the links."""

import pytest

from azimuth import handbook


def test_the_units_of_energy_are_those_of_codata_2018_as_the_program_has_them():
    e = handbook.ENERGY
    assert e['эВ'] == pytest.approx(27.211386245988, abs=1e-10)  # modules/spectrum/analysis/dos.py
    assert e['ккал/моль'] == pytest.approx(627.509474, abs=1e-6)  # headless, trajectory_drawer
    assert e['кДж/моль'] == pytest.approx(2625.4996394799, abs=1e-8)
    assert e['см⁻¹'] == pytest.approx(219474.6313632, abs=1e-6)
    assert e['К'] == pytest.approx(315775.02480407, abs=1e-5)
    assert handbook.LENGTH['Å'] == pytest.approx(0.529177210903, abs=1e-12)  # modules/spectrum/readers/qe.py


def test_a_conversion_goes_both_ways_and_through_a_wavelength():
    found = handbook.convert('energy', 1.0, 'эВ')
    assert found['см⁻¹'] == pytest.approx(8065.543937, abs=1e-5)  # orca_spectra.EV_CM
    assert found['нм'] == pytest.approx(1239.841984, abs=1e-5)  # experiment.HC_EV_NM
    back = handbook.convert('energy', found['ккал/моль'], 'ккал/моль')
    assert back['эВ'] == pytest.approx(1.0, abs=1e-12)
    assert handbook.convert('energy', 500, 'нм')['эВ'] == pytest.approx(1239.841984 / 500, abs=1e-9)
    with pytest.raises(ValueError):
        handbook.convert('energy', 0, 'нм')
    assert handbook.convert('dipole', 1, 'e·бор')['Д (дебай)'] == pytest.approx(2.5417464, abs=1e-6)  # CODATA
    assert handbook.units('energy')[-1] == 'нм' and 'нм' not in handbook.ENERGY


def test_the_solvents_are_those_sextant_writes():
    from azimuth.core import SOLVENTS

    rows = {r['key']: r for r in handbook.solvent_rows()}
    assert set(rows) == set(SOLVENTS) - {''}
    assert rows['water']['mopac'] == 'EPS=78.4' and rows['water']['epsilon'] == 78.4
    assert rows['ethanol']['xtb'] is None  # no ALPB ethanol (azimuth_options says the same)
    assert rows['hexane']['psi4'] is None and rows['hexane']['gaussian'] == 'n-Hexane'


def test_the_factors_are_those_of_spectrum():
    b3lyp = {r['basis']: r for r in handbook.factor_rows('B3LYP')}
    assert b3lyp['6-31G*']['factor'] == 0.960 and b3lyp['6-31G*']['uncertainty'] == 0.022  # CCCBDB
    assert {r['method'] for r in handbook.factor_rows()} >= {'HF', 'MP2', 'B3LYP', 'PBE0'}


def test_the_links_of_a_formula_and_the_databases():
    links = dict(handbook.formula_links(' C2H4O '))
    assert links['NIST Chemistry WebBook'] == 'https://webbook.nist.gov/cgi/cbook.cgi?Formula=C2H4O&NoIon=on&Units=SI'
    assert links['PubChem'].endswith('#query=C2H4O')
    assert handbook.formula_links('') == []
    assert all(d['url'].startswith('https://') and d['what'] for d in handbook.DATABASES)
