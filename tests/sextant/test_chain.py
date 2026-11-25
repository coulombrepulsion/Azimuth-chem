"""«Расчёт → Цепочка расчётов» of Sextant (modules/sextant/chain.py) — the steps of a preset, a step on the
geometry of the one before, the larger basis."""

from dataclasses import replace
from types import SimpleNamespace

import pytest

from azimuth.core import Calculation, read_xyz
from modules.sextant import chain

WATER = read_xyz('3\nwater\nO 0 0 0\nH 0.96 0 0\nH -0.24 0.93 0\n')


def test_the_larger_basis():
    assert chain.larger_basis('def2-SVP') == 'def2-TZVP' and chain.larger_basis('def2-TZVP') == 'def2-QZVP'
    assert chain.larger_basis('def2-TZVPP') == 'def2-QZVPP' and chain.larger_basis('cc-pVDZ') == 'cc-pVTZ'
    assert chain.larger_basis('aug-cc-pVTZ') == 'aug-cc-pVQZ' and chain.larger_basis('6-31G(d)') == '6-311+G(2d,p)'
    assert chain.larger_basis('STO-3G') == 'def2-TZVP'


def test_the_steps_of_a_preset_and_the_programs():
    calc = Calculation(basis='def2-SVP', charge=-1, multiplicity=2)
    steps = chain.steps('big', calc)
    assert [s[1] for s in steps] == ['Оптимизация + частоты', 'Энергия'] and steps[1][2] == {'basis': 'def2-TZVP'}
    items = chain.items('uv', WATER, calc)
    assert [i.props['task'] for i in items] == ['Оптимизация + частоты', 'Спектр UV-Vis (TD-DFT)']
    assert items[0].name.startswith('1. ') and items[0].charge == -1 and items[0].multiplicity == 2
    assert chain.available('uv', 'orca') and chain.available('nmr', 'gaussian')
    assert not chain.available('uv', 'xtb') and not chain.available('nmr', 'psi4')


def test_a_step_on_the_geometry_of_the_one_before():
    items = chain.items('nmr', WATER, Calculation())
    queue = SimpleNamespace(items=items)
    assert chain.prepare(queue, items[0]) is False
    with pytest.raises(ValueError):
        chain.prepare(queue, items[1])  # the optimization is not done
    shorter = replace(WATER, atoms=tuple(replace(a, x=a.x * 0.99) for a in WATER.atoms))
    items[0].state, items[0].geometry = 'done', shorter
    assert chain.prepare(queue, items[1]) and items[1].molecule is shorter


def test_the_steps_with_their_own_method_and_basis():
    # a step of its own method and basis; what
    # equals the form is not written in; the first step is the form's
    calc = Calculation(method='B3LYP', basis='def2-SVP')
    items = chain.items('uv', WATER, calc, [{}, {'method': 'CAM-B3LYP', 'basis': 'def2-TZVP'}])
    assert items[0].props['calc'] == {} and items[1].props['calc'] == {'method': 'CAM-B3LYP', 'basis': 'def2-TZVP'}
    assert items[1].name == '2. Спектр UV-Vis (TD-DFT) · CAM-B3LYP/def2-TZVP'
    same = chain.items('big', WATER, calc, [{}, {'method': 'B3LYP', 'basis': 'def2-TZVP'}])
    assert same[1].props['calc'] == {'basis': 'def2-TZVP'}  # the method of the form: not written in
    assert chain.items('uv', WATER, calc, None)[1].props['calc'] == {}
