"""Isotopes of some atoms of a calculation (azimuth/core.py: Calculation.isotopes, isotope_masses,
isotope_text, coordinate_lines; ORCA «M = mass» after the coordinates). Oracle: the masses of IUPAC written here."""

from dataclasses import replace

from azimuth.core import Calculation, isotope_masses, isotope_text, orca_input, read_xyz

WATER = read_xyz('3\nwater\nO 0 0 0.117\nH 0.757 0 -0.469\nH -0.757 0 -0.469\n')


def test_heavy_water_in_the_input_of_orca():
    calc = replace(Calculation(), isotopes=isotope_text({1: 2.014102, 2: 2.014102}, WATER))
    assert calc.isotopes == '2 H 2.014102; 3 H 2.014102'
    text = orca_input(WATER, calc)
    lines = [l for l in text.splitlines() if l.startswith('H ')]
    assert len(lines) == 2 and all(l.endswith('M = 2.014102') for l in lines)
    assert not any('M =' in l for l in text.splitlines() if l.startswith('O '))
    assert 'M =' not in orca_input(WATER, Calculation())  # no isotopes — the file as before


def test_an_isotope_of_an_atom_gone_or_changed_is_left_out():
    assert isotope_masses('2 H 2.014102; 9 H 2.014102; 1 C 13.003355; x', WATER) == {1: 2.014102}
    assert isotope_masses('2 H 2.014102') == {1: 2.014102}  # without the structure: as written


def test_heavy_water_for_gaussian_and_psi4():
    from modules.sextant.inputs import gaussian_input, psi4_input

    calc = replace(Calculation(), isotopes='2 H 2.014102')
    lines = gaussian_input(WATER, calc).splitlines()
    assert any(l.startswith('H(Iso=2) ') for l in lines) and sum(l.startswith('H ') for l in lines) == 1
    assert any(l.startswith('H@2.014102 ') for l in psi4_input(WATER, calc).splitlines())



def test_every_stable_isotope_and_a_mass_of_ones_own():
    from azimuth.core import ISOTOPES, isotope_abundance, isotope_name
    from azimuth.isotope_table import STABLE

    assert len(STABLE) >= 80 and all(abs(sum(x for *_, x in rows) - 1) < 0.003 for rows in STABLE.values())
    assert all(abs(mass - number) < 0.1 for rows in STABLE.values() for number, mass, _ in rows)
    assert [n for n, _ in ISOTOPES['Pt']] == ['¹⁹⁰Pt', '¹⁹²Pt', '¹⁹⁴Pt', '¹⁹⁵Pt', '¹⁹⁶Pt', '¹⁹⁸Pt']
    assert isotope_name('H', 2.014102) == 'D' and isotope_name('Hg', 201.970643) == '²⁰²Hg'
    assert isotope_name('Tc', 97.907) == '⁹⁸Tc'  # a mass of one's own: by its mass number
    assert abs(isotope_abundance('U', 235.04393) - 0.007204) < 1e-9 and isotope_abundance('H', 3.016049) is None
