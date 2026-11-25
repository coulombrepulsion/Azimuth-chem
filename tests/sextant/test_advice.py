"""Charge, multiplicity, resources and the method advice of Sextant (modules/sextant/advice.py).

Oracles by hand: NH4+ — N with four bonds, +1, singlet; water — neutral singlet; OH — 9 electrons, doublet;
the atoms C (³P), N (⁴S), Cr (⁷S) by Hund's rules; O₂ triplet; BH4− −1. Resources: an 8-core 16 GB machine
gives 7 processes and 0.6·16384/7 MB rounded down to 100. Advice: the methods and bases exist in the program.
"""

from modules.sextant import advice
from azimuth.core import Atom, Molecule, bases_for, methods_for

WATER = Molecule('w', (Atom('O', 0, 0, 0.117), Atom('H', 0, 0.757, -0.469), Atom('H', 0, -0.757, -0.469)))
NH4 = Molecule('nh4', (Atom('N', 0, 0, 0), Atom('H', 0.63, 0.63, 0.63), Atom('H', -0.63, -0.63, 0.63),
                       Atom('H', -0.63, 0.63, -0.63), Atom('H', 0.63, -0.63, -0.63)))
BH4 = Molecule('bh4', tuple(Atom('B' if a.symbol == 'N' else 'H', a.x * 1.2, a.y * 1.2, a.z * 1.2) for a in NH4.atoms))
OH = Molecule('oh', (Atom('O', 0, 0, 0), Atom('H', 0.97, 0, 0)))
O2 = Molecule('o2', (Atom('O', 0, 0, 0), Atom('O', 1.21, 0, 0)))


def test_charge_and_multiplicity():
    assert advice.guess_state(WATER)[:2] == (0, 1)
    assert advice.guess_state(NH4)[:2] == (1, 1)
    assert advice.guess_state(BH4)[:2] == (-1, 1)
    assert advice.guess_state(OH)[:2] == (0, 2)
    assert advice.guess_state(O2)[:2] == (0, 3)
    for symbol, mult in (('C', 3), ('N', 4), ('Cr', 7), ('Ne', 1), ('Fe', 5)):
        assert advice.guess_state(Molecule('a', (Atom(symbol, 0, 0, 0),)))[:2] == (0, mult)
    assert advice.guess_state(Molecule('e', (), ())) == (0, 1, '')


def test_resources():
    assert advice.recommended(advice.Machine(16, 8, 16384)) == (7, 1400)
    assert advice.recommended(advice.Machine(2, None, None)) == (1, 1000)
    assert advice.recommended(advice.Machine(4, 2, 2048)) == (2, 600)
    assert advice.recommended(advice.Machine(64, 32, 1_000_000)) == (16, 8000)
    m = advice.machine()
    assert m.logical >= 1 and (m.memory_mb is None or m.memory_mb > 100)


def test_method_advice_is_available_in_the_program():
    for kind in ('orca', 'gaussian', 'psi4'):
        for task in ('Энергия', 'Оптимизация + частоты', 'Спектр UV-Vis (TD-DFT)', 'ЯМР (экранирование)'):
            for mol, charge, mult in ((WATER, 0, 1), (OH, -1, 1), (OH, 0, 2)):
                a = advice.recommend(mol, task, kind, charge, mult)
                assert a.method in methods_for(kind) and a.basis in bases_for(kind) and a.text.endswith('.')
    assert advice.recommend(WATER, 'Энергия', 'orca').method == 'MP2'  # a few atoms: MP2/cc-pVTZ
    a = advice.recommend(WATER, 'Оптимизация + частоты', 'orca')
    assert (a.method, a.basis, a.dispersion) == ('B3LYP', 'def2-SVP', 'D3BJ')
    assert advice.recommend(OH, 'Оптимизация', 'gaussian', -1, 1).basis == '6-31+G*'  # Gaussian: no def2-SVPD
    assert advice.recommend(OH, 'Оптимизация', 'orca', -1, 1).basis == 'def2-SVPD'
    assert advice.recommend(WATER, 'Спектр UV-Vis (TD-DFT)', 'orca').method == 'CAM-B3LYP'
    assert advice.recommend(WATER, 'Энергия', 'xtb') is None
