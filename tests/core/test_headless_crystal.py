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


def test_a_crystal_of_a_project(tmp_path):
    # ROADMAP 25: the crystal of a project of «Компас · Кристалл» — the one shown, or one of its crystals by id or title
    from azimuth import crystal_projects

    manifest = crystal_projects.create(tmp_path, 'Si', SILICON)
    second = crystal_projects.add(manifest, SALT, 'NaCl')
    crystal_projects.set_active(manifest, crystal_projects.FIRST)
    made, title = hc.crystal({'project': str(Path(manifest).parent)})  # the folder of the project, the crystal shown
    assert abs(made.cell.a - 5.431) < 0.01 and title == crystal_projects.title(manifest)
    salt, _ = hc.crystal({'project': str(manifest), 'crystal': second})
    assert abs(salt.cell.a - 5.64) < 0.05
    named = crystal_projects.info(manifest, second).get('title')
    assert abs(hc.crystal({'project': str(manifest), 'crystal': named})[0].cell.a - salt.cell.a) < 1e-9
    with pytest.raises(ValueError, match='no crystal .* there are: crystal'):
        hc.crystal({'project': str(manifest), 'crystal': 'nothing'})
    with pytest.raises(ValueError, match='not a project of a crystal'):
        hc.crystal({'project': str(tmp_path)})


def test_the_files_of_the_panel_beside_the_inputs(tmp_path, library, monkeypatch):
    # path.json of the bands, elastic.json, eos.json — written by the job as by the panel (qe_run), so that the result
    # tells the gap along the path, the elastic constants and a₀ (they were missing without the window)
    bands = hc.prepare('qe', {'cif': SILICON}, {'task': qe_inputs.BANDS_TASK})
    names = [name for name, _ in bands.extras]
    assert names == ['path.json']
    import json

    path = json.loads(bands.extras[0][1])
    assert path['x'] and any(label == 'Γ' for _, label in path['ticks'])
    assert [n for n, _ in hc.prepare('qe', {'cif': SILICON}, {'task': qe_inputs.EOS_TASK}).extras] == ['eos.json']
    assert [n for n, _ in hc.prepare('qe', {'cif': SALT}, {'task': qe_inputs.ELASTIC_TASK}).extras] == ['elastic.json']
    assert hc.prepare('qe', {'cif': SILICON}).extras == () and hc.prepare('cp2k', {'cif': SILICON}).extras == ()
    tools = tmp_path / 'tools'
    program = install_tools.qe_prefix(tools) / 'bin' / 'pw.x'
    program.parent.mkdir(parents=True)
    program.write_text('#!/bin/sh\n', encoding='utf-8')
    program.chmod(0o755)
    monkeypatch.setattr(install_tools, 'qe_program', lambda *a, **k: program)
    spec = hc.job(bands, tmp_path / 'jobs', tools)
    assert json.loads((spec.folder / 'path.json').read_text(encoding='utf-8')) == path
    folder, _ = hc.server_folder(bands, tmp_path / 'server', tools)
    assert (folder / 'path.json').is_file()


def _folder(tmp_path, output, inputs=(), extras=()):
    import shutil

    folder = tmp_path / output.split('.')[0]
    folder.mkdir()
    shutil.copy(DATA / 'qe' / output, folder / 'pw.out')
    for name, text in [*inputs, *extras]:
        (folder / name).write_text(text, encoding='utf-8')
    return folder


def test_the_series_read_from_their_folders(tmp_path, library):
    # ROADMAP 25: the summary of a series. Oracles: the recorded runs of pw.x 7.6 and the values the tests of the panel
    # check on them (tests/compass/test_band_gap.py, test_equation_of_state.py, test_crystal_convergence.py,
    # test_elastic.py)
    from modules.compass.chemistry import convergence

    # the bands of silicon along the path the job writes: indirect, 0.574 eV, the top at Γ, the bottom 85 % to X
    path = dict(hc.prepare('qe', {'cif': SILICON}, {'task': qe_inputs.BANDS_TASK}).extras)['path.json']
    gap = hc.result(_folder(tmp_path, 'si_bands_pw76.out', extras=[('path.json', path)]))['band_gap']
    assert gap['kind'] == 'indirect' and gap['gap_ev'] == pytest.approx(0.5741, abs=1e-4)
    assert gap['valence_top']['where'] == 'Γ' and '85 %' in gap['conduction_bottom']['where']
    assert gap['direct_gap_ev'] == pytest.approx(2.5628, abs=1e-4) and gap['occupied_bands'] == 4
    # the equation of state: V₀ between the fifth and the sixth volume, B₀ 88.8 GPa, a₀ = 5.469 Å (PBE)
    eos_json = dict(hc.prepare('qe', {'cif': SILICON}, {'task': qe_inputs.EOS_TASK}).extras)['eos.json']
    eos = hc.result(_folder(tmp_path, 'si_eos_pw76.out', [('eos1.in', '')], [('eos.json', eos_json)]))['equation_of_state']
    assert len(eos['points']) == 7 and eos['points'][4]['volume_A3'] < eos['v0_A3'] < eos['points'][5]['volume_A3']
    assert eos['b0_gpa'] == pytest.approx(88.8, abs=0.3) and eos['b0_prime'] == pytest.approx(4.34, abs=0.05)
    assert eos['cell_of_the_file_at_v0']['a'] == pytest.approx(5.469, abs=0.003)
    # the convergence by ecutwfc: the table and from which cutoff it converged
    cuts = [(f'cut{n}.in', f"&SYSTEM\n  ecutwfc = {w}\n/\n") for n, w in enumerate((20, 30, 40, 50, 60, 70), 1)]
    series = hc.result(_folder(tmp_path, 'si_cutoff_pw76.out', cuts))['convergence']
    assert series['kind'] == 'ecutwfc' and [r['value'] for r in series['rows']][0] == '20 Ry' and len(series['rows']) == 6
    assert series['rows'][-1]['delta_mev_per_atom'] == 0
    from tests.compass.test_crystal_convergence import CUTOFF_CONVERGED

    assert series['energy_converged_from'] == series['rows'][CUTOFF_CONVERGED]['value']
    assert series['summary'] and series['tolerances']['energy_mev_per_atom'] == convergence.TOLERANCE_MEV
    # the elastic constants of MgO
    plan = (DATA / 'qe' / 'mgo_elastic.json').read_text(encoding='utf-8')
    elastic = hc.result(_folder(tmp_path, 'mgo_elastic_pw76.out', extras=[('elastic.json', plan)]))['elastic']
    assert (elastic['c11_gpa'], elastic['c12_gpa'], elastic['c44_gpa']) == pytest.approx((276.3, 92.1, 143.2), abs=0.1)
    assert elastic['bulk_gpa'] == pytest.approx(153.5, abs=0.1) and elastic['stable']
    # a file of its own, not pw.out of a job: no series looked for beside it
    assert 'band_gap' not in hc.result(DATA / 'qe' / 'si_bands_pw76.out')
