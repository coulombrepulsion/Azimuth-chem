"""azimuth/headless_crystal.py — a calculation of a crystal without the window.

Oracles: the inputs are those of the panel (modules/sextant/qe_inputs.py, cp2k_inputs.py — their own tests check the
physics); here — that the settings reach them, that what the panel chooses is chosen (the Γ supercell and the grid of
CP2K), and that the results are those of the recorded outputs of the real programs (tests/data/qe, tests/data/cp2k:
Quantum ESPRESSO 7.6, CP2K 2026.2).
"""

from pathlib import Path

import pytest

from azimuth import headless, headless_crystal as hc
from modules.sextant import cp2k_inputs, install_tools, qe_inputs, qe_local, qe_pseudo

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'tests' / 'data'
SILICON = (ROOT / 'examples' / '10-crystals' / 'Si_diamond.cif').read_text(encoding='utf-8')
SALT = (ROOT / 'examples' / '10-crystals' / 'NaCl_rock_salt.cif').read_text(encoding='utf-8')


@pytest.fixture
def library(monkeypatch, tmp_path):
    """The pseudopotentials as if installed: a table of two elements (file, ecutwfc, ecutrho) and their files (Windows
    copies them beside the job)."""
    folder = tmp_path / 'pseudo'
    folder.mkdir()
    for name in ('Si.upf', 'Na.upf', 'Cl.upf'):
        (folder / name).write_text('<UPF/>', encoding='utf-8')
    monkeypatch.setattr(qe_pseudo, 'installed', lambda *a, **k: True)
    monkeypatch.setattr(qe_pseudo, 'table', lambda *a, **k: {'Si': ('Si.upf', 30.0, 240.0), 'Na': ('Na.upf', 66.0, 528.0),
                                                           'Cl': ('Cl.upf', 45.0, 360.0)})
    monkeypatch.setattr(qe_pseudo, 'folder', lambda *a, **k: folder)
    monkeypatch.setattr(qe_inputs, 'valence', lambda *a, **k: 4.0)


def test_what_is_a_crystal(tmp_path):
    made, title = hc.crystal({'cif': SILICON, 'title': 'Si'})
    assert title == 'Si' and abs(made.cell.a - 5.431) < 0.01
    path = tmp_path / 'salt.cif'
    path.write_text(SALT, encoding='utf-8')
    assert hc.crystal({'path': str(path)})[1] == 'salt'
    for wrong, said in (({}, 'a crystal is'), ({'path': str(tmp_path / 'none.cif')}, 'no file'), ({'cif': 'nothing'}, 'not read')):
        with pytest.raises(ValueError, match=said):
            hc.crystal(wrong)
    (tmp_path / 'water.xyz').write_text('3\n\nO 0 0 0\nH 0 0 1\nH 0 1 0\n', encoding='utf-8')
    with pytest.raises(ValueError, match='not a CIF file'):
        hc.crystal({'path': str(tmp_path / 'water.xyz')})


def test_the_tasks_and_the_settings_offered():
    qe = hc.options('qe')
    assert qe['tasks'][:3] == list(qe_inputs.TASKS) and qe_inputs.BANDS_TASK in qe['tasks'] and qe_inputs.EOS_TASK in qe['tasks']
    assert qe['settings']['vdw'] == '' and qe['also']['spacing'] == qe_inputs.SPACING and 'pbesol' in qe['functionals']
    cp2k = hc.options('cp2k')
    assert cp2k['tasks'] == list(cp2k_inputs.TASKS) and cp2k['settings']['basis'] == 'DZVP-MOLOPT-SR-GTH'
    with pytest.raises(ValueError, match='crystals are computed by: qe, cp2k'):
        hc.options('orca')


def test_the_inputs_of_quantum_espresso(library):
    made = hc.prepare('qe', {'cif': SILICON, 'title': 'Si'}, {'task': 'Энергия'})
    assert [(name, tool) for name, tool, _ in made.steps] == [('pw.in', 'pw.x')] and made.atoms == 2  # the primitive cell
    text = made.steps[0][2]
    assert "calculation = 'scf'" in text and 'nat = 2' in text and 'ecutwfc = 30' in text and 'Si.upf' in text
    whole = hc.prepare('qe', {'cif': SILICON}, {'primitive': False, 'supercell': [2, 1, 1], 'ecutwfc': 45, 'ecutrho': 360,
                                               'functional': 'pbesol', 'vdw': 'd3bj', 'grid': [3, 6, 6]})
    text = whole.steps[0][2]
    assert whole.atoms == 16 and 'nat = 16' in text and 'ecutwfc = 45' in text and 'ecutrho = 360' in text
    assert "vdw_corr = 'dft-d3'" in text and 'dftd3_version = 4' in text and '3 6 6 0 0 0' in text
    assert whole.library['name'].startswith('SSSP') and 'PBEsol' in whole.library['name']  # the files of the functional
    dos = hc.preview('qe', {'cif': SILICON}, {'task': qe_inputs.DOS_TASK})
    assert list(dos) == ['scf.in', 'nscf.in', 'dos.in', 'projwfc.in']
    series = hc.prepare('qe', {'cif': SILICON}, {'task': qe_inputs.CUTOFF_TASK})
    names = [name for name, _, _ in series.steps]  # from the cut-off of the pseudopotential up: as many as fit
    assert names == [f'cut{n}.in' for n in range(1, len(names) + 1)] and 5 <= len(names) <= 7
    for settings, said in (({'tsk': 1}, "unknown setting 'tsk'"), ({'task': 'Полёт'}, 'has no task'),
                           ({'supercell': [2, 2]}, 'three whole numbers'), ({'grid': 'x'}, 'three whole numbers'),
                           ({'ecutwfc': 'много'}, 'is not understood'), ({'order': 'spiral'}, "'' or 'afm'")):
        with pytest.raises(ValueError, match=said):
            hc.prepare('qe', {'cif': SILICON}, settings)


def test_no_pseudopotentials_is_said(monkeypatch):
    monkeypatch.setattr(qe_pseudo, 'installed', lambda *a, **k: False)
    with pytest.raises(ValueError, match='are not installed'):
        hc.prepare('qe', {'cif': SILICON})


def test_the_inputs_of_cp2k():
    # the panel repeats the cell until its edges reach 10 Å (the Γ point) and takes the grid of the elements
    made = hc.prepare('cp2k', {'cif': SILICON, 'title': 'Si'})
    text = made.steps[0][2]
    assert made.steps[0][0] == cp2k_inputs.INPUT and 'RUN_TYPE ENERGY' in text and '      CUTOFF 400' in text
    assert made.atoms == 54 and '11.52' in text  # 3 × 3 × 3 of the primitive cell of 3.84 Å
    salt = hc.prepare('cp2k', {'cif': SALT}, {'task': 'Оптимизация с ячейкой', 'vdw': '', 'processes': 4})
    assert '      CUTOFF 950' in salt.steps[0][2] and 'RUN_TYPE CELL_OPT' in salt.steps[0][2] and salt.processes == 4
    assert 'VDW_POTENTIAL' not in salt.steps[0][2]
    own = hc.prepare('cp2k', {'cif': SALT}, {'supercell': [1, 1, 1], 'primitive': False, 'cutoff': 600})
    assert own.atoms == 8 and '      CUTOFF 600' in own.steps[0][2]


def test_the_job_written(tmp_path, library, monkeypatch):
    tools = tmp_path / 'tools'
    program = install_tools.qe_prefix(tools) / 'bin' / 'pw.x'
    program.parent.mkdir(parents=True)
    program.write_text('#!/bin/sh\n', encoding='utf-8')
    program.chmod(0o755)
    monkeypatch.setattr(install_tools, 'qe_program', lambda *a, **k: program)
    spec = hc.job(hc.prepare('qe', {'cif': SILICON, 'title': 'Si diamond'}, {'task': qe_inputs.BANDS_TASK}), tmp_path / 'jobs',
                  tools)
    assert spec.folder.parent == tmp_path / 'jobs' and spec.folder.name.startswith('qe-Si_diamond-')
    assert spec.output == spec.folder / 'pw.out' and (spec.folder / 'scf.in').is_file() and (spec.folder / 'bands.in').is_file()
    if qe_local.POSIX_SCRIPT in spec.command:  # not Windows: the steps one after another
        script = (spec.folder / qe_local.POSIX_SCRIPT).read_text(encoding='utf-8')
        assert script.splitlines()[:2] == ['#!/bin/sh', 'set -e'] and script.count('-in ') == 2
    monkeypatch.setattr(install_tools, 'qe_program', lambda *a, **k: None)
    with pytest.raises(ValueError, match='Quantum ESPRESSO is not found'):
        hc.job(hc.prepare('qe', {'cif': SILICON}), tmp_path / 'jobs', tools)
    monkeypatch.setattr(install_tools, 'cp2k_program', lambda *a, **k: None)
    with pytest.raises(ValueError, match='CP2K is not found'):
        hc.job(hc.prepare('cp2k', {'cif': SILICON}), tmp_path / 'jobs', tools)


def test_the_commands_of_a_job():
    steps = [(name, tool, '') for name, tool in qe_inputs.STEPS[qe_inputs.DOS_TASK]]
    command, script, changes = qe_local.posix_command(steps, '/opt/qe/bin/pw.x', 4, None, {'PATH': '/usr/bin'})
    assert command == ['/bin/sh', 'run.sh'] and changes == {'OMP_NUM_THREADS': '1'}  # no prefix: nothing of it named
    lines = script.splitlines()
    assert lines[2] == '/opt/qe/bin/pw.x -in scf.in' and lines[4] == '/opt/qe/bin/dos.x -in dos.in'
    assert lines[5] == '/opt/qe/bin/projwfc.x -in projwfc.in > projwfc.out 2>&1 || true'
    one, script, _ = qe_local.posix_command([('pw.in', 'pw.x', '')], '/opt/qe/bin/pw.x', 1)
    assert one == ['/opt/qe/bin/pw.x', '-in', 'pw.in'] and script == ''
    argv, files, changes = qe_local.command(steps, 'C:/qe/bin/pw.exe', 2, windows=True)
    assert argv == ['cmd', '/d', '/c', 'run.bat'] and files['run.bat'].startswith(b'@echo off\r\npw.exe -in scf.in')
    assert changes['OMP_NUM_THREADS'] == '2'
    text = "  pseudo_dir = '/home/user/.tools/qe/pseudo/SSSP'\nATOMIC_SPECIES\n  Si 28.085 Si.upf\n  O 15.999 O.upf\nCELL_PARAMETERS"
    assert "pseudo_dir = './pseudo'" in qe_local.beside(text) and qe_local.pseudo_files([('pw.in', 'pw.x', text)]) == ['O.upf', 'Si.upf']


def test_the_results_of_the_recorded_runs():
    # a series of pw.x 7.6: the elastic constants of MgO, 19 runs
    found = hc.result(DATA / 'qe' / 'mgo_elastic_pw76.out')
    assert found['program'].startswith('Quantum ESPRESSO 7.6') and found['normal_exit'] and found['done']
    assert len(found['runs']) == 19 and all(run['done'] and run['energy_ry'] < 0 for run in found['runs'])
    assert found['energy_ry'] == found['runs'][-1]['energy_ry'] and found['energy_ev'] == pytest.approx(found['energy_ry'] * 13.605693, rel=1e-6)
    bands = hc.result(DATA / 'qe' / 'si_bands_pw76.out')  # scf, then the bands (no energy): the energy of the scf
    assert len(bands['runs']) == 2 and bands['energy_ry'] == bands['runs'][0]['energy_ry'] < 0 and bands['done']
    magnetic = hc.result(DATA / 'qe' / 'nio_magnetic_pw76.out')
    assert len(magnetic['runs']) == 3 and 'magnetization_bohr' in magnetic
    # CP2K 2026.2: an optimization of the cell
    cp2k = hc.result(DATA / 'cp2k' / 'cellopt.out')
    assert cp2k['program'].startswith('CP2K') and cp2k['energy_hartree'] < 0 and cp2k['steps'] >= 1
    assert cp2k['energy_ev'] == pytest.approx(cp2k['energy_hartree'] * 27.211386, rel=1e-6)
    # the reader of the molecules sends a crystal here by the name of its output
    assert headless.result(DATA / 'cp2k' / 'cellopt.out', 'cp2k')['program'].startswith('CP2K')
    with pytest.raises(ValueError, match='is not an output of Quantum ESPRESSO or CP2K'):
        hc.result(ROOT / 'README.md')


def test_the_programs_of_crystals_are_listed():
    found = headless.programs()
    assert 'qe' in found and 'cp2k' in found and 'orca' in found
