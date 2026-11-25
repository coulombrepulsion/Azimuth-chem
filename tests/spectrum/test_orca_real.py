"""Regression oracles transcribed from supplied ORCA output, not parser results."""

from pathlib import Path
import pytest
from modules.spectrum.readers.orca import read_output

FIXTURES = Path(__file__).parents[1] / 'fixtures' / 'orca-real'


@pytest.mark.parametrize(
    'name,module,scf,mpi',
    [
        ('pada_Y_neutral_local1_DKH_fixed', 'LEANSCF', True, True),
        ('padpa_Y_new_ver_DKH_neutral_redoing_again_tightopt_fixed', 'LEANSCF', True, True),
        ('padp_Y_neutral_new_basis_nitrate_v4_no_water_DKH_tightopt_fixed', 'GUESS', False, True),
        ('y_charged_DKH_fixed', 'Startup', False, True),
    ],
)
def test_real_error_diagnostics(name, module, scf, mpi):
    output = read_output((FIXTURES / (name + '.txt')).read_text())
    assert output.error_module == module
    assert output.scf_failed is scf
    assert output.mpi_cpu_error is mpi
    assert output.termination_status == 'аварийное (' + module + ')'
    assert not output.normal_exit


def test_real_frequency_columns_and_displacements():
    output = read_output((FIXTURES / 'completed-frequencies.txt').read_text())
    assert len(output.vibration_geometry.atoms) == 25
    assert len(output.frequencies) == len(output.modes) == 75
    assert sum(m.animatable for m in output.modes) == 69
    assert sum(m.intensity is not None for m in output.modes) == 69
    assert not output.imaginary
    assert output.modes[6].frequency == 63.43
    assert output.modes[6].intensity == 72.36  # Int column, not eps or T**2.
    assert output.modes[6].vectors[0][0] == 0.006801
    assert all(len(m.vectors) == 25 for m in output.modes)


def test_missing_termination_is_not_error():
    output = read_output('ORCA\nCalculation still running\n')
    assert output.error_module is None
    assert output.termination_status == 'не подтверждено'


def test_normal_termination_is_preserved():
    output = read_output('ORCA TERMINATED NORMALLY')
    assert output.error_module is None
    assert output.termination_status == 'нормальное'
