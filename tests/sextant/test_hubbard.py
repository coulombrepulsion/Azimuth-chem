"""DFT+U of a crystal: modules/sextant/hubbard.py and its lines in the inputs of pw.x and CP2K."""

import pytest

from modules.compass.chemistry import crystal as cr
from modules.sextant import cp2k_inputs as ci, hubbard, qe_inputs as qi


def nickel_oxide():
    # NiO, rock salt, a = 4.177 Å (Fm-3m; written as P1 of the conventional cell — 8 atoms)
    sites = [('Ni', 0, 0, 0), ('Ni', 0, .5, .5), ('Ni', .5, 0, .5), ('Ni', .5, .5, 0),
             ('O', .5, .5, .5), ('O', .5, 0, 0), ('O', 0, .5, 0), ('O', 0, 0, .5)]
    return cr.Crystal('NiO', cr.Cell(4.177, 4.177, 4.177),
                      tuple(cr.Site(f'{s}{k}', s, x, y, z) for k, (s, x, y, z) in enumerate(sites, 1)),
                      (cr.operation('x, y, z'),), 'P 1')


def test_the_values_written():
    assert hubbard.parse('') == () and hubbard.parse('  ') == ()
    assert hubbard.parse('Fe 5.3, Ni 6.2') == (('Fe', '3d', 5.3), ('Ni', '3d', 6.2))
    assert hubbard.parse('Ce=4,5; U-5f 3') == (('Ce', '4f', 4.5), ('U', '5f', 3.0))
    assert hubbard.parse('Mo-4d: 2') == (('Mo', '4d', 2.0),)
    for wrong in ('Fe', 'O 3', 'Fe 20', 'Fe 5, Fe 6', 'железо 5'):
        with pytest.raises(ValueError):
            hubbard.parse(wrong)
    assert hubbard.candidates(['Ni', 'O', 'Ni', 'Ce']) == ['Ni', 'Ce']


def test_the_card_of_pw_and_the_kinds_of_cp2k():
    # the grid: ⌈2π / (4.177 Å · 0.25 Å⁻¹)⌉ = ⌈6.02⌉ = 7; the card of INPUT_PW (QE 7.1 and later, read 2026-11-15):
    # «HUBBARD (ortho-atomic)», «U Mn-3d 5.0»; CP2K:
    # PLUS_U_METHOD of &DFT, &DFT_PLUS_U of &KIND with L and U_MINUS_J (src/input_cp2k_subsys.F, input_cp2k_dft.F)
    u = hubbard.parse('Ni 6.2')
    pseudo = {'Ni': ('ni.upf', 45.0, 360.0), 'O': ('O.upf', 50.0, 400.0)}
    text = qi.pw_input(nickel_oxide(), 'Энергия', pseudo, options=qi.Options(hubbard=u))
    assert text.endswith('K_POINTS automatic\n  7 7 7 0 0 0\nHUBBARD (ortho-atomic)\n  U Ni-3d 6.2\n')
    assert 'HUBBARD' not in qi.pw_input(nickel_oxide(), 'Энергия', pseudo)
    with pytest.raises(ValueError):  # no Fe in NiO
        qi.pw_input(nickel_oxide(), 'Энергия', pseudo, options=qi.Options(hubbard=hubbard.parse('Fe 5')))
    inp = ci.cp2k_input(nickel_oxide(), options=ci.Options(hubbard=u))
    assert '    PLUS_U_METHOD MULLIKEN\n' in inp
    assert ('    &KIND Ni\n      BASIS_SET DZVP-MOLOPT-SR-GTH\n      POTENTIAL GTH-PBE\n      &DFT_PLUS_U T\n        L 2\n'
            '        U_MINUS_J [eV] 6.2\n      &END DFT_PLUS_U\n    &END KIND\n    &KIND O\n      BASIS_SET '
            'DZVP-MOLOPT-SR-GTH\n      POTENTIAL GTH-PBE\n    &END KIND') in inp
    assert 'PLUS_U' not in ci.cp2k_input(nickel_oxide())
