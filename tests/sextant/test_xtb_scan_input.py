"""The relaxed scan of xtb — the file xcontrol and the command (modules/sextant/inputs.py)."""

from dataclasses import replace

import pytest

from azimuth.core import SCAN_TASK, Calculation, read_xyz
from modules.sextant import inputs

WATER = read_xyz('3\n\nO 0 0 0\nH 0.96 0 0\nH -0.24 0.93 0')


def test_the_scan_in_xcontrol_and_the_command():
    calc = replace(Calculation(), task=SCAN_TASK, scan_index=0, scan_end=1.5, scan_steps=7)
    files = inputs.input_files('xtb', WATER, calc, [('C', (2,)), ('B', (0, 1))])
    control = files['xcontrol']
    # the scanned coordinate first in $constrain, at its value in the geometry; the frozen atom stays frozen
    assert '$fix\n   atoms: 3\n' in control and '   distance: 1, 2, 0.9600\n' in control
    assert control.index('distance: 1, 2') < control.index('$scan') and '$scan\n   1: 0.9600,1.5000,7\n' in control
    args = inputs.xtb_arguments(calc, [('B', (0, 1))])
    assert '--opt' in args and args[args.index('--input') + 1] == 'xcontrol'
    angle = inputs.xcontrol((), ('A', (1, 0, 2), 104.5, 120.0, 5))
    assert '   angle: 2, 1, 3, 104.50\n' in angle and '1: 104.50,120.00,5' in angle
    assert SCAN_TASK in inputs.PROGRAM_TASKS['xtb'] and 'xtb' in inputs.TASK_OPTIONS['scan_end'][1]


def test_a_scan_without_a_coordinate_is_refused():
    calc = replace(Calculation(), task=SCAN_TASK, scan_end=1.5)
    with pytest.raises(ValueError):
        inputs.input_files('xtb', WATER, calc, [])


def test_gfnff_of_xtb():
    # «Оптимизация GFN-FF (xtb)» — --gfnff instead of --gfn 2
    from modules.sextant.inputs import xtb_arguments

    calc = Calculation(task='Оптимизация', xtb_method='gfnff')
    calc.validate_settings()  # the method of the form stays («GFN-FF» as a method failed the validation)
    args = xtb_arguments(calc)
    assert '--gfnff' in args and '--gfn' not in args and '--opt' in args
    assert xtb_arguments(Calculation(task='Оптимизация'))[1:3] == ['--gfn', '2']
