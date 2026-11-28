"""Azimuth without its window (azimuth/headless.py).

Oracles: the input Sextant writes for the same molecule and settings (inputs.preview); the numbers ORCA 6.0.1 printed
in tests/data/orca601 (the energy, the frequencies, «Zero point energy», «Total Enthalpy», «Final Gibbs free energy»,
the TD-DFT states); the remedy of the doctor for a lack of memory (doctor §2.4); a fake xtb that prints the output of
xtb 6.6.1 of the test data — the job is followed to its result; tools/test.py refuses no option it should and runs
none it should not.
"""

import os
from pathlib import Path
import sys
import time

import pytest

from azimuth import headless
from azimuth.core import Calculation
from modules.sextant import inputs

DATA = Path(__file__).parents[1] / 'data'
POSIX = pytest.mark.skipif(os.name == 'nt', reason='the fake program is a POSIX script')


def test_the_input_is_the_one_of_sextant():
    made, _, _ = headless.molecule({'smiles': 'CC=O', 'title': 'acetaldehyde'})
    calc = Calculation(cores=4, solvent='water', dispersion='D3BJ')  # D3(BJ), as a new window of Sextant
    assert headless.preview('orca', {'smiles': 'CC=O', 'title': 'acetaldehyde'}, {'cores': 4, 'solvent': 'water'}) == \
        inputs.preview('orca', made, calc)
    assert made.title == 'acetaldehyde' and made.formula == 'C2H4O'


def test_a_molecule_from_a_file_brings_its_charge():
    made, charge, multiplicity = headless.molecule({'path': str(DATA / 'orca601' / 'h2o_opt.inp')})
    assert made.formula == 'H2O' and (charge, multiplicity) == (0, 1)
    last, _, _ = headless.molecule({'path': str(DATA / 'orca601' / 'h2o_opt.out')})
    assert last.atoms[0].z == pytest.approx(0.128598)  # the last geometry of the optimization
    with pytest.raises(ValueError):
        headless.molecule({'path': str(DATA / 'orca601' / 'README.md')})
    with pytest.raises(ValueError):
        headless.molecule({})


def test_settings_by_name_and_their_errors():
    calc = headless.calculation({'method': 'PBE0', 'cores': '8', 'ts': 'true', 'temperature': 310})
    assert (calc.method, calc.cores, calc.ts, calc.temperature) == ('PBE0', 8, True, 310.0)
    with pytest.raises(ValueError, match='unknown setting'):
        headless.calculation({'cpu': 4})
    with pytest.raises(ValueError, match='cores'):
        headless.calculation({'cores': 'many'})


def test_the_result_of_an_optimization_with_frequencies():
    found = headless.result(DATA / 'orca601' / 'h2o_optfreq.out')
    assert found['normal_exit'] and found['optimization_converged'] and found['steps'] == 4
    assert found['energy_hartree'] == pytest.approx(-76.321269931369)
    assert found['frequencies_cm1'] == [1637.62, 3786.94, 3881.92] and found['imaginary_frequencies'] == 0
    thermo = found['thermochemistry_hartree']
    assert thermo['sigma'] == 2 and thermo['zpe'] == pytest.approx(0.02120171, abs=2e-8)
    assert thermo['H'] == pytest.approx(-76.29628871, abs=2e-8)
    assert thermo['G'] == pytest.approx(-76.31773280, abs=2e-6)  # ORCA: the same entropy terms, its own rounding
    assert 'problems' not in found
    # water is a molecule of the course: «Опыт» of Spectrum without the window (CCCBDB)
    experiment = found['experiment']
    assert experiment['molecule'] == 'water' and experiment['measured']['dipole_debye'] == 1.857
    assert [p[1] for p in experiment['frequencies']['pairs_in_order']] == [1595, 3657, 3756]
    assert experiment['dipole_computed_debye'] == pytest.approx(2.004, abs=1e-3) and experiment['bonds'][0]['count'] == 2


def test_the_states_of_tddft_and_no_optimization():
    found = headless.result(DATA / 'orca601' / 'h2o_tddft.out')
    assert 'optimization_converged' not in found  # a single point: nothing is said of an optimization
    assert found['excitations'][0] == {'state': 1, 'nm': 162.6, 'ev': 7.62528, 'f': 0.018043051, 'multiplicity': 1}


def test_the_doctor_on_a_run_out_of_memory(tmp_path):
    text = (DATA / 'orca601' / 'h2o_energy.out').read_text(encoding='utf-8')
    (tmp_path / 'h2o.out').write_text(text[:len(text) // 3] + '\nError (ORCA_SCF): Not enough memory available!\n'
                                      'Please increase MaxCore\n', encoding='utf-8')
    found = headless.result(tmp_path, settings={'cores': 8, 'memory_mb': 1000})
    assert not found['normal_exit'] and found['problems']
    assert found['remedies'][0]['changes'] == {'cores': 4, 'memory_mb': 2000}


@POSIX
def test_a_calculation_followed_to_its_result(tmp_path):
    fake = tmp_path / 'xtb'
    output = (DATA / 'xtb' / 'dvb_sp' / 'dvb_sp.out').read_text(encoding='utf-8')
    (tmp_path / 'printed.out').write_text(output, encoding='utf-8')
    fake.write_text(f'#!{sys.executable}\nimport sys, time\ntime.sleep(0.5)\n'
                    f'sys.stdout.write(open({str(tmp_path / "printed.out")!r}, encoding="utf-8").read())\n')
    fake.chmod(0o755)
    jobs = headless.Jobs()
    started = jobs.start_calculation('xtb', {'smiles': 'O'}, {'task': 'Энергия', 'cores': 1}, root=tmp_path / 'jobs',
                                     program=str(fake))
    assert Path(started['folder']).is_dir() and jobs.listing()[0]['kind'] == 'calculation'
    for _ in range(100):
        state = jobs.status(started['job'])
        if state['state'] != 'running':
            break
        time.sleep(0.1)
    assert state['state'] == 'done' and state['exit_code'] == 0
    assert state['result']['energy_hartree'] == pytest.approx(-26.425939358406)
    with pytest.raises(ValueError):
        jobs.status('nope')


def test_the_checks_of_the_program_and_what_they_refuse(tmp_path):
    jobs = headless.Jobs()
    for bad in (('full', None, ['-p', 'evil']), ('full', None, ['--rootdir=/']), ('full', None, ['; rm -rf /']),
                ('anything', None, ()), ('area', '../x', ())):
        with pytest.raises(ValueError):
            jobs.start_tests(*bad)
    started = jobs.start_tests('list')
    for _ in range(300):
        state = jobs.status(started['job'])
        if state['state'] != 'running':
            break
        time.sleep(0.1)
    assert state['state'] == 'passed' and 'Области' in state['tail']
    assert jobs.tests_command('quick', options=['-x', '-k', 'crystal and not slow'])[2:] == [
        'quick', '--', '-x', '-k', 'crystal and not slow']
    assert jobs.tests_command('area', 'projects')[2:] == ['area', 'projects']


def test_a_saddle_gets_the_remedy_of_the_doctor(tmp_path):
    # an optimization with frequencies that ended on a saddle (the first vibration of water made imaginary, as in
    # tests/sextant/test_doctor.py): the doctor's «move along the mode», with the moved geometry to start from
    import re

    text = (DATA / 'orca601' / 'h2o_optfreq.out').read_text(encoding='utf-8')
    found = re.search(r'^\s*6:\s*(\d+\.\d+)\s*cm\*\*-1', text, re.M)
    (tmp_path / 'saddle.out').write_text(text[:found.start(1)] + '-' + text[found.start(1):], encoding='utf-8')
    result = headless.result(tmp_path / 'saddle.out')
    assert result['imaginary_frequencies'] == 1 and result['normal_exit']
    (remedy,) = result['remedies']
    assert remedy['changes'] == {'task': 'Оптимизация + частоты', 'opt_conv': 'tight'}
    moved, _, _ = headless.molecule({'xyz': remedy['start_xyz']})
    assert moved.formula == 'H2O'
    assert remedy['start_xyz'].splitlines()[1].endswith('moved along the imaginary mode')  # not the title of a file
    assert 'remedies' not in headless.result(DATA / 'orca601' / 'h2o_optfreq.out')  # a minimum: nothing


def test_the_options_are_those_the_program_uses():
    orca, xtb, crest, mopac = (headless.options(k) for k in ('orca', 'xtb', 'crest', 'mopac'))
    assert 'B3LYP' in orca['methods'] and 'def2-SVP' in orca['bases'] and 'D3BJ' in orca['dispersions']
    assert xtb['methods'] == ['GFN2-xTB'] and xtb['bases'] == [] and xtb['dispersions'] == []
    assert 'D4' in orca['dispersions'] and 'D4' not in headless.options('psi4')['dispersions']
    assert 'ethanol' not in xtb['solvents'] and 'water' in xtb['solvents']  # no ALPB ethanol in xtb
    assert crest['tasks'] == [] and 'conformer' in crest['note']
    gamess = headless.options('gamess')
    assert 'def2-SVP' not in gamess['bases'] and 'cc-pVDZ' in gamess['bases']  # GAMESS has no def2 sets of its own
    assert 'PM7' in mopac['methods'] and mopac['bases'] == [] and set(mopac['solvents']) <= {''} | set(inputs.MOPAC_EPS)


def test_mopac_gets_the_corrections_of_thermochemistry_without_a_total_energy():
    path = Path(__file__).parents[1] / 'data' / 'mopac' / 'h2o_pm7_force_thermo.out'
    found = headless.result(str(path))
    thermo = found['thermochemistry_hartree']
    assert thermo['sigma'] == 2 and thermo['H'] is None and thermo['G'] is None  # C2v; a heat of formation, no energy
    assert abs(thermo['zpe'] * 627.5095 - 10.094) < 0.01  # «ZERO POINT ENERGY 10.094 KCAL/MOL» of MOPAC 23.2.5


def test_a_crest_search_gives_its_conformers_and_the_problem_of_its_window(tmp_path):
    # the log of CREST 3.0.2 on macOS (its window of 0, crest-lab/crest#431) with four frames as the ensemble
    import shutil

    crest = DATA / 'crest'
    shutil.copy(crest / 'butanediol_gfnff_3.0.2_macos.out', tmp_path / 'C4H10O2_GFN2-xTB.out')
    shutil.copy(crest / 'butanediol_4_frames.xyz', tmp_path / 'crest_conformers.xyz')
    found = headless.result(tmp_path)  # the folder of the calculation
    assert found['program'] == 'CREST 3.0.2' and found['normal_exit'] and found['conformers'] == 4
    assert found['relative_kcal'][0] == 0 and found['relative_kcal'] == sorted(found['relative_kcal'])
    assert abs(found['relative_kcal'][-1] - 12.6) < 0.1  # «0, 3.2, 8.6 and 12.6 kcal/mol» (tests/data/crest)
    assert found['geometry_xyz'].splitlines()[0].strip() == '16'
    assert any('431' in p['why'] or 'CREST' in p['what'] for p in found['problems'])


def test_nmr_gives_the_shieldings():
    found = headless.result(DATA / 'orca601' / 'h2o_nmr.out')
    shield = found['nmr_shielding_ppm']
    assert [x['element'] for x in shield] == ['O', 'H', 'H'] and shield[0]['isotropic'] > 300  # O of water, ~330 ppm
    assert abs(shield[1]['isotropic'] - shield[2]['isotropic']) < 1e-3  # the two H alike


def test_the_options_say_what_is_outside_the_beta():
    from azimuth import headless

    assert headless.options('orca')['checked'] and headless.options('psi4')['checked']
    assert not headless.options('gaussian')['checked'] and not headless.options('gamess')['checked']


def test_a_calculation_from_here_has_the_dispersion_of_a_new_window():
    # a new window of Sextant starts B3LYP-D3(BJ)/def2-SVP; a calculation sent without the window — the same, unless the
    # dispersion is given; a method without parameters of D3 gets none
    assert headless.calculation({}).dispersion == 'D3BJ'  # azimuth/core.py DEFAULT_DISPERSION
    assert headless.calculation({'dispersion': ''}).dispersion == ''
    assert headless.calculation({'method': 'HF'}).dispersion == ''
    assert 'D3BJ' in headless.preview('orca', {'smiles': 'O'}, {'task': 'Энергия'})
