"""Window tests — Sextant: inputs, tasks, runs, queues, conformers and the windows of calculations (split from
test_gui.py on 2026-11-08)."""

from tests.gui_support import *  # noqa: F401,F403 — the fixtures app, window and the helpers
from tests.fake_programs import program_script


def test_default_workflow(window):
    assert 'B3LYP D3BJ def2-SVP Opt Freq' in window.preview.toPlainText()  # D3(BJ) by default (BETA_PLAN)
    assert window.export_button.isEnabled()
    window.demo_output()
    assert window.energy_table.rowCount() == 2
    assert window.frequency_table.rowCount() == 9
    assert 'УЧЕБНЫЙ ПРИМЕР' in window.output_source.text()


def test_invalid_edit_disables_export(window):
    window.table.item(0, 1).setText('invalid')
    assert not window.export_button.isEnabled()
    assert not window.preview.toPlainText()
    window.table.item(0, 1).setText('0')
    assert window.export_button.isEnabled()


def test_spin_validation_in_ui(window):
    window.spin.setValue(2)
    assert not window.export_button.isEnabled()
    window.charge.setValue(1)
    assert window.export_button.isEnabled()


@pytest.mark.parametrize('kind', ['mopac', 'xtb'])
def test_start_with_mopac_or_xtb_chosen_makes_an_input(window, app, kind):
    # the user — with MOPAC kept from the last time, Sextant said at once «Метод, базис или задача не
    # поддерживаются» until another program was chosen and back: the list of basis sets (of methods for xtb) was empty
    from azimuth.core import BASES, METHODS

    saved = window.preferences.value('sextant_program')
    window.preferences.setValue('sextant_program', kind)
    another = Studio(example=True, probe_machine=False)
    try:
        assert another.program_kind() == kind
        calc = another.calculation()
        assert calc.basis in BASES and calc.method in METHODS
        another.input_tool.refresh_input()
        assert another.input_error.isHidden() and another._generated
    finally:
        another.dirty = False
        another.close()
        window.preferences.setValue('sextant_program', saved or 'orca')


def test_input_echo_is_the_starting_geometry():
    from modules.spectrum.readers.orca import read_output

    text = (
        'ORCA\n|  1> ! HF Opt\n|  2> * xyz 0 1\n|  3> O 0 0 0\n|  4> H 1.10 0 0.30\n|  5> H -1.10 0 0.30\n|  6> *\n'
        'GEOMETRY OPTIMIZATION CYCLE 1\nCARTESIAN COORDINATES (ANGSTROEM)\n---\nO 0 0 0\nH 1.1 0 0.3\nH -1.1 0 0.3\n\n'
        'FINAL SINGLE POINT ENERGY -75\n'
    )
    out = read_output(text)
    assert [a.position for a in out.initial_geometry.atoms] == [(0, 0, 0), (1.1, 0, 0.3), (-1.1, 0, 0.3)]
    assert read_output('ORCA\n|  1> * xyzfile 0 1 a.xyz\n').initial_geometry is None


def test_sextant_runs_a_program(window, app, tmp_path, monkeypatch):
    # «Программа» xtb, its command in the preview, the run of a fake xtb (it prints the xtb 6.6.1
    # single point of the cclib data and writes charges, wbo and the coordinate file it names next to it),
    # the result opened in Spectrum;
    # a missing program is refused with a message and nothing is started
    import sys
    import time

    data = Path(__file__).parents[1] / 'data' / 'xtb' / 'dvb_sp'
    fake = tmp_path / 'bin' / 'xtb'
    fake.parent.mkdir()
    fake = program_script(
        fake,
        f'#!{sys.executable}\nimport shutil, sys\n'
        f'assert sys.argv[1].endswith(".xyz") and sys.argv[2:4] == ["--gfn", "2"]\n'
        f'for name in ("charges", "wbo", "dvb_sp.xyz"):\n    shutil.copy({str(data)!r} + "/" + name, name)\n'
        f'sys.stdout.write(open({str(data / "dvb_sp.out")!r}).read())\n'
    )
    saved = window.preferences.value('sextant_program')
    configured = {'xtb': str(fake), 'orca': None}
    monkeypatch.setattr(window.run_tool, 'configured_program', lambda kind: configured[kind])
    monkeypatch.setattr(window.run_tool, 'jobs_root', lambda: tmp_path / 'jobs')
    try:
        window.navigate(1)
        window.program.setCurrentIndex(window.program.findData('xtb'))
        assert not window.method.isEnabled() and not window.basis.isEnabled() and window.cores.isEnabled()
        assert re.search(r'xtb \S+_GFN2-xTB\.xyz --gfn 2 --chrg 0 --uhf 0 --ohess --cycles 100 -P 2', window.preview.toPlainText())
        assert window.found_program == fake and window.run_button.isEnabled()
        window.task.setCurrentIndex(window.task.findText('Энергия'))
        job = window.run_tool.run_calculation()
        assert job is not None and window.stop_button.isEnabled() and not window.run_button.isEnabled()
        assert job.spec.output.with_suffix('.xyz').read_text(encoding='utf-8') == window.coordinate_tool.table_molecule().xyz()
        end = time.monotonic() + 30
        while window.run_tool.poll_job() is None:
            assert time.monotonic() < end, 'the fake xtb did not finish'
            app.processEvents()
            time.sleep(0.05)
        assert not window.job_timer.isActive() and not window.stop_button.isEnabled()
        assert 'завершён' in window.run_status.text()
        # a single point without spectra is looked at in Compass, in the tab it was started from; the
        # section does not change by itself at the end — «Перейти в Компас» of the window goes there
        assert window.stack.currentIndex() == 1 and window.output.program == 'xtb 6.6.1'
        assert len(window.documents) == 1 and window.result_properties.bond_kind == 'Wiberg'
        jw = window.job_window  # the stages passed and where to look at the result
        assert 'scf' in jw.stage_keys and not jw.stages.isHidden() and 'сошлось' in jw.stages.text()
        assert jw.spectrum_button.isHidden() and not jw.compass_button.isHidden()
        assert window.run_tool.go_to_result('compass') == 'compass' and window.stack.currentIndex() == 0
        window.navigate(1)
        assert window.task.property('quail_center')  # the choice is drawn centred
        assert window.output.energies == (-26.425939358406,)  # the TOTAL ENERGY of the cclib run
        assert window.output.properties.bond_kind == 'Wiberg'  # wbo was read next to the output

        configured['xtb'] = None
        monkeypatch.setattr('modules.sextant.runner.find_program', lambda kind, configured=None: None)
        errors = []
        monkeypatch.setattr(window, 'error', lambda exc: errors.append(str(exc)))
        before = list((tmp_path / 'jobs').iterdir())
        assert window.run_tool.run_calculation() is None and errors and 'не найдена' in errors[0]
        assert list((tmp_path / 'jobs').iterdir()) == before
    finally:
        window.program.setCurrentIndex(0)
        if saved is None:
            window.preferences.remove('sextant_program')
        else:
            window.preferences.setValue('sextant_program', saved)


def test_sextant_gaussian_psi4_solvent_and_dispersion(window, monkeypatch):
    # the preview follows the program, the solvent and the dispersion; what a program cannot do is
    # shown as an error and the run button is off; xtb switches the dispersion off; the chosen program's file
    saved = window.preferences.value('sextant_program')
    try:
        window.navigate(1)
        window.program.setCurrentIndex(window.program.findData('gaussian'))
        window.solvent.setCurrentIndex(window.solvent.findData('water'))
        window.dispersion.setCurrentIndex(window.dispersion.findData('D3BJ'))
        text = window.preview.toPlainText()
        # 100 cycles of the optimization by default — MaxCycles in the route
        assert '#P B3LYP/def2SVP Opt=MaxCycles=100 Freq EmpiricalDispersion=GD3BJ SCRF=(CPCM,Solvent=Water) SCF=Tight' in text
        assert window.calculation().solvent == 'water' and window.calculation().dispersion == 'D3BJ'
        window.dispersion.setCurrentIndex(window.dispersion.findData('D4'))
        assert not window.input_error.isHidden()
        assert 'D4' in window.input_error.text() and not window.run_button.isEnabled()
        window.program.setCurrentIndex(window.program.findData('psi4'))
        assert not window.input_error.isHidden()  # optimization in a solvent: no PCM gradients in Psi4
        window.solvent.setCurrentIndex(0)
        assert not window.input_error.isHidden() and 'D4' in window.input_error.text()  # no D4 in Psi4 1.11 either
        window.dispersion.setCurrentIndex(window.dispersion.findData('D3BJ'))
        assert window.input_error.isHidden() and "frequency('b3lyp-d3bj')" in window.preview.toPlainText()
        assert window.task.findText('ЯМР (экранирование)') < 0  # Psi4 does not offer what it cannot do
        window.task.setCurrentIndex(window.task.findText('Спектр UV-Vis (TD-DFT)'))
        assert 'tdscf_states 10' in window.preview.toPlainText()
        written = []
        monkeypatch.setattr(window, 'save_text', lambda title, pattern, text, name: written.append((pattern, text, name)))
        window.input_tool.export_program_input()
        # the file is named after the calculation
        assert written[0][2] == 'H2O_B3LYP_def2-SVP.dat' and "energy('td-b3lyp-d3bj')" in written[0][1]
        window.program.setCurrentIndex(window.program.findData('xtb'))
        assert not window.dispersion.isEnabled() and not window.method.isEnabled()
        window.task.setCurrentIndex(window.task.findText('Оптимизация'))
        window.solvent.setCurrentIndex(window.solvent.findData('chloroform'))
        assert '--opt --alpb chcl3' in window.preview.toPlainText() and window.input_error.isHidden()
    finally:
        window.program.setCurrentIndex(0)
        window.solvent.setCurrentIndex(0)
        window.dispersion.setCurrentIndex(0)
        if saved is None:
            window.preferences.remove('sextant_program')
        else:
            window.preferences.setValue('sextant_program', saved)


def test_reaction_path_window_and_neb_input(window, app, tmp_path):
    # the end renumbered and laid on the start, IDPP images in the steps drawer, the XYZ frames, ORCA
    # NEB-CI in Sextant with end.xyz; the other programs refuse the task
    from math import cos, radians, sin, sqrt

    from modules.compass.chemistry.formats import read_xyz_frames
    from modules.sextant import inputs
    from azimuth.core import NEB_TASK, Atom, Molecule

    def ethane(turn):
        r = sqrt(1.09 ** 2 - 0.36 ** 2)
        atoms = [Atom('C', 0, 0, -0.765), Atom('C', 0, 0, 0.765)]
        atoms += [Atom('H', r * cos(radians(120 * k)), r * sin(radians(120 * k)), -1.125) for k in range(3)]
        atoms += [Atom('H', r * cos(radians(120 * k + 60 + turn)), r * sin(radians(120 * k + 60 + turn)), 1.125) for k in range(3)]
        return Molecule('ethane', tuple(atoms))

    show_model(window, app)
    window.dirty = False
    window.load_molecule(ethane(0))
    end = ethane(60)
    shuffled = Molecule('eclipsed', tuple(end.atoms[i] for i in (2, 0, 7, 1, 6, 5, 4, 3)))
    w = window.compass_dialogs.path()
    assert w.set_end(shuffled, 'eclipsed.xyz') and 'RMSD' in w.end_label.text()
    assert [a.symbol for a in w.end.atoms] == [a.symbol for a in window.molecule.atoms]
    w.images.setValue(4)
    frames = w.build()
    assert len(frames) == 6 and window.browsing and len(window.drawer.steps) == 6
    saved = w.save_xyz(tmp_path / 'path.xyz')
    assert len(read_xyz_frames((tmp_path / 'path.xyz').read_text(encoding='utf-8'))) == 6 and saved
    window.trajectory_tool.set_trajectory_open(False)
    w.to_sextant()
    try:
        assert window.stack.currentIndex() == 1 and window.program_kind() == 'orca'
        text = window.preview.toPlainText()
        assert '! B3LYP D3BJ def2-SVP NEB-CI TightSCF' in text and 'neb_end_xyzfile "end.xyz"' in text and 'nimages 4' in text
        assert '# end.xyz' in text and window.input_error.isHidden()
        calc = window.calculation()
        assert calc.task == NEB_TASK
        files = inputs.input_files('orca', window.coordinate_tool.table_molecule(), calc, (), window.input_tool.neb_settings())
        assert len(files) == 2 and next(iter(files)).endswith('.inp') and 'end.xyz' in files and files['end.xyz'].startswith('8\n')
        for kind in ('gaussian', 'psi4', 'xtb'):
            with pytest.raises(ValueError):
                inputs.input_files(kind, window.coordinate_tool.table_molecule(), calc)
        window.neb_end = None
        window.input_tool.refresh_input()
        assert not window.input_error.isHidden() and 'конечную структуру' in window.input_error.text()
    finally:
        window.task.setCurrentIndex(window.task.findText('Оптимизация + частоты'))
        window.program.setCurrentIndex(0)


def test_conformer_search_window(window, app, tmp_path, monkeypatch):
    # butane — three candidates in the table and the drawer, a fake xtb gives each an energy that
    # depends on the C–C–C–C dihedral (anti lowest), the ranking, the shares, «Взять выбранный», XYZ
    import sys
    import time

    from modules.compass.chemistry import library, torsion
    from modules.compass.chemistry.formats import read_xyz_frames

    fake = tmp_path / 'bin' / 'xtb'
    fake.parent.mkdir()
    fake = program_script(
        fake,
        f'#!{sys.executable}\n'
        'import math, shutil, sys\n'
        'lines = open(sys.argv[1]).read().split("\\n")\n'
        'p = [list(map(float, l.split()[1:4])) for l in lines[2:6]]\n'
        'def sub(a, b): return [a[k] - b[k] for k in range(3)]\n'
        'def cross(a, b): return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]\n'
        'b1, b2, b3 = sub(p[1], p[0]), sub(p[2], p[1]), sub(p[3], p[2])\n'
        'n1, n2 = cross(b1, b2), cross(b2, b3)\n'
        'phi = math.atan2(math.sqrt(sum(x*x for x in b2)) * sum(b1[k]*n2[k] for k in range(3)), sum(n1[k]*n2[k] for k in range(3)))\n'
        'energy = -15.0 + 0.0015 * (1 + math.cos(phi))\n'
        'shutil.copy(sys.argv[1], "xtbopt.xyz")\n'
        'print("      |                           x T B                           |")\n'
        'print("   * xtb version 6.6.1 (fake)")\n'
        'print("   *** GEOMETRY OPTIMIZATION CONVERGED AFTER 1 ITERATIONS ***")\n'
        'print(f"          | TOTAL ENERGY      {energy:.12f} Eh   |")\n'
        'print(" * finished run on 2026/10/24")\n'
    )
    monkeypatch.setattr(window.run_tool, 'configured_program', lambda kind: str(fake) if kind == 'xtb' else None)
    monkeypatch.setattr(window.run_tool, 'jobs_root', lambda: tmp_path / 'jobs')
    show_model(window, app)
    window.dirty = False
    butane = library.molecule(next(k for k in library.keys() if k.startswith('Бутан')))
    window.load_molecule(butane)
    w = window.compass_dialogs.conformers()
    try:
        rows = w.search()
        # the conformers on their own page of the drawer, its tab appears with them
        assert not window.drawer.steps and window.drawer.page() == 'conformers'
        assert len(rows) == 3 and w.table.rowCount() == 3 and window.browsing and len(window.drawer.conformers) == 3
        assert window.drawer.tab_bar.isTabVisible(5) and window.drawer.width() == 372  # a list of the pages
        assert w.refine()
        end = time.monotonic() + 60
        while w.timer.isActive():
            assert time.monotonic() < end, 'the fake xtb did not finish'
            w.poll()
            app.processEvents()
            time.sleep(0.02)
        # CREGEN: gauche+ and gauche− have the same energy and rotational constants — one conformer
        # with two rotamers, so two rows, and the gauche share counts twice
        assert len(w.rows) == 2 and w.rows[0][3] == 0.0 and [r[5] for r in w.rows] == [1, 2]
        a, b, c, d = 0, 1, 2, 3  # the chain of the library butane: C0–C1–C2–C3
        assert abs(abs(torsion.dihedral(w.rows[0][0], a, b, c, d)) - 180) < 1e-6  # anti is lowest
        dE = 0.0015 * 1.5 * 627.5094740631
        assert w.rows[1][3] == pytest.approx(dE, rel=1e-6) and sum(r[4] for r in w.rows) == pytest.approx(1.0)
        from math import exp

        assert w.rows[1][4] / w.rows[0][4] == pytest.approx(2 * exp(-dE / (0.0019872043 * 298.15)), rel=1e-6)
        assert window.drawer.conformers[0][1] == pytest.approx(-15.0, abs=1e-9)
        window.drawer.select_conformer(1)  # the chosen conformer is on the model
        assert [x.position for x in window.molecule.atoms] == [
            pytest.approx(x.position, abs=1e-7) for x in window.drawer.conformers[1][0].atoms]
        tab = window.current_document
        window.new_document()  # another tab has no conformers: no tab «Конформеры»
        assert not window.drawer.tab_bar.isTabVisible(5) and not window.drawer.conformers
        window.switch_document(tab)  # back: they are kept, the chosen one too
        assert len(window.drawer.conformers) == 2 and window.drawer.conformer_current == 1
        window.close_document(len(window.documents) - 1)
        window.trajectory_tool.set_trajectory_open(True, 'conformers')
        w.show_row(1)
        saved = w.save_xyz(tmp_path / 'conformers.xyz')
        assert len(read_xyz_frames(saved.read_text(encoding='utf-8'))) == 2
        assert w.take(1) and not window.browsing
        assert abs(abs(torsion.dihedral(window.molecule, a, b, c, d)) - 60) < 1e-4
    finally:
        w.close()


def test_conformer_window_bee_colony(window, app, tmp_path, monkeypatch):
    # «Пчелиный поиск (ABC)» — every structure it asks for is an xtb run (a fake xtb: the energy of the
    # C–C–C–C dihedral of butane, the geometry as given); all runs in one folder ABC_…; the conformers kept go to the
    # table and to «Конформеры» of the drawer, anti near the top
    import sys
    import time

    from modules.compass.chemistry import library, torsion

    fake = tmp_path / 'bin' / 'xtb'
    fake.parent.mkdir()
    fake = program_script(
        fake,
        f'#!{sys.executable}\n'
        'import math, shutil, sys\n'
        'lines = open(sys.argv[1]).read().split("\\n")\n'
        'p = [list(map(float, l.split()[1:4])) for l in lines[2:6]]\n'
        'def sub(a, b): return [a[k] - b[k] for k in range(3)]\n'
        'def cross(a, b): return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]\n'
        'b1, b2, b3 = sub(p[1], p[0]), sub(p[2], p[1]), sub(p[3], p[2])\n'
        'n1, n2 = cross(b1, b2), cross(b2, b3)\n'
        'phi = math.atan2(math.sqrt(sum(x*x for x in b2)) * sum(b1[k]*n2[k] for k in range(3)), sum(n1[k]*n2[k] for k in range(3)))\n'
        'energy = -15.0 + 0.0015 * (1 + math.cos(phi))\n'
        'shutil.copy(sys.argv[1], "xtbopt.xyz")\n'
        'print("   * xtb version 6.6.1 (fake)")\n'
        'print("   *** GEOMETRY OPTIMIZATION CONVERGED AFTER 1 ITERATIONS ***")\n'
        'print(f"          | TOTAL ENERGY      {energy:.12f} Eh   |")\n'
        'print(" * finished run on 2026/10/28")\n'
    )
    monkeypatch.setattr(window.run_tool, 'configured_program', lambda kind: str(fake) if kind == 'xtb' else None)
    monkeypatch.setattr(window.run_tool, 'jobs_root', lambda: tmp_path / 'jobs')
    # a fixed seed — the fake xtb does not optimize, so with 2 iterations the colony finds anti only in about
    # 3 runs of 4 (40 seeds tried: 10 ended at 44-85° from anti); seed 0 reaches anti exactly
    from modules.compass.chemistry import abc_search

    unseeded = abc_search.search
    monkeypatch.setattr(abc_search, 'search', lambda *a, **k: unseeded(*a, **{**k, 'seed': 0}))
    show_model(window, app)
    window.dirty = False
    butane = library.molecule(next(k for k in library.keys() if k.startswith('Бутан')))
    window.load_molecule(butane)
    w = window.compass_dialogs.conformers()
    try:
        w.abc_confs.setValue(2)
        w.abc_iterations.setValue(2)
        assert w.run_abc() and w.mode == 'abc' and not w.abc_button.isEnabled()
        assert 'глобальный поиск' in w.status.text() and 'xtb № 1' in w.status.text()  # where the search is
        w.abc_progress.update(stage='local', local=3, local_max=2, taken=2, rejected=1)
        assert 'локальный поиск 3 из не больше 2 · найдено 2, отвергнуто 1' in w.abc_status('x')
        w.abc_progress.update(stage='global')
        end = time.monotonic() + 120
        while w.timer.isActive():
            assert time.monotonic() < end, 'the bee colony did not finish'
            w.poll()
            app.processEvents()
            time.sleep(0.01)
        assert w.rows and w.abc is None and w.abc_button.isEnabled() and w.abc_count > 3
        folders = list((tmp_path / 'jobs').iterdir())
        assert len(folders) == 1 and folders[0].name.startswith('ABC_')
        assert abs(abs(torsion.dihedral(w.rows[0][0], 0, 1, 2, 3)) - 180) < 40  # the lowest is close to anti
        assert window.drawer.page() == 'conformers' and window.drawer.conformer_source == 'конформеры (ABC)'
    finally:
        w.close()


def test_conformer_window_runs_crest(window, app, tmp_path, monkeypatch):
    # a fake crest checks its options and writes crest_conformers.xyz (three frames: the structure,
    # a duplicate 0.006 kcal/mol higher, the same structure 3.1 kcal/mol higher, and one 7 kcal/mol higher
    # beyond the energy window); the window reads and sorts it as CREGEN does
    import sys
    import time

    from modules.compass.chemistry import library

    fake = tmp_path / 'bin' / 'crest'
    fake.parent.mkdir()
    fake = program_script(
        fake,
        f'#!{sys.executable}\n'
        'import sys\n'
        'assert sys.argv[1].endswith(".xyz") and sys.argv[2:4] == ["--gfn2", "--chrg"] and "--quick" in sys.argv\n'
        'assert sys.argv[sys.argv.index("--ewin") + 1] == "6" and sys.argv[sys.argv.index("--mdlen") + 1] == "x2"\n'
        # the window of CREGEN; twice the metadynamics for a small molecule (butane, 14 atoms)
        'lines = open(sys.argv[1]).read().splitlines()\n'
        'body = "\\n".join(lines[2:])\n'
        'with open("crest_conformers.xyz", "w") as f:\n'
        '    for e in (-15.0, -14.99999, -14.995, -14.988):\n'
        '        f.write(f"{lines[0]}\\n  {e:.8f}\\n{body}\\n")\n'
        'print(" CREST terminated normally.")\n'
    )
    monkeypatch.setattr(window.run_tool, 'configured_program', lambda kind: str(fake) if kind == 'crest' else None)
    monkeypatch.setattr(window.run_tool, 'jobs_root', lambda: tmp_path / 'jobs')
    show_model(window, app)
    window.dirty = False
    window.load_molecule(library.molecule(next(k for k in library.keys() if k.startswith('Бутан'))))
    w = window.compass_dialogs.conformers()
    try:
        w.quick.setChecked(True)
        assert w.run_crest()
        assert w.spinner.running()  # the compass turns while CREST searches
        # «Свернуть» — the search goes on behind, the board of the long work shows it (the left panel)
        assert w.away_button.isEnabled() and w.put_away() and not w.isVisible()
        assert window.activities.get('conformers').parked and window.activities.running()
        end = time.monotonic() + 30
        while w.timer.isActive():
            assert time.monotonic() < end, 'the fake crest did not finish'
            w.poll()
            app.processEvents()
            time.sleep(0.02)
        energies = [r[2] for r in w.rows]
        assert not w.spinner.running()
        assert window.activities.get('conformers').state == 'done'  # put away: its end waits in the panel
        w.reopen()
        assert window.activities.get('conformers') is None  # seen in its window
        assert energies == [-15.0, -14.995]  # duplicate dropped (ΔE < 0.05 kcal/mol, RMSD 0), 7 kcal/mol beyond 6
        # the conformers are a page of their own in the drawer, not steps
        assert w.rows[1][3] == pytest.approx(0.005 * 627.5094740631, rel=1e-9) and len(window.drawer.conformers) == 2
        # the structure beyond the window is named, with how far above it lies
        assert 'Выше окна: 1, ближайшая на 7.5 ккал/моль' in w.status.text()
        assert 'Initial geometry optimization failed' in w.crest_failure(' Initial geometry optimization failed!')
        assert 'crest.out' in w.crest_failure('anything else')
    finally:
        w.close()


def test_sextant_offers_open_mpi(window, monkeypatch, tmp_path):
    # ORCA on 2 processes without mpirun — the «Установить Open MPI…» button; one process or an
    # mpirun found — no button; the dialog asks first (the test answer is «No»: nothing is installed)

    orca = tmp_path / 'orca_6' / 'orca'
    orca.parent.mkdir()
    orca = program_script(orca, '')
    (orca.parent / 'orca_scf').write_text('')
    monkeypatch.setattr(window.run_tool, 'configured_program', lambda kind: str(orca) if kind == 'orca' else None)
    monkeypatch.setattr('modules.sextant.runner.find_mpirun', lambda *a, **k: None)
    window.program.setCurrentIndex(window.program.findData('orca'))
    window.run_tool.refresh_program_path()
    window.cores.setValue(2)
    window.input_tool.refresh_input()
    assert window.mpi_button.isVisibleTo(window.mpi_button.parentWidget())
    window.cores.setValue(1)
    assert not window.mpi_button.isVisibleTo(window.mpi_button.parentWidget())
    from PySide6.QtWidgets import QMessageBox

    asked = []
    monkeypatch.setattr(QMessageBox, 'question', lambda *a, **k: asked.append(a[1]) or QMessageBox.StandardButton.No)
    assert window.run_tool.install_tools_dialog(('openmpi',)) is None and window.install_job is None and asked
    window.cores.setValue(2)


def test_install_menu_offers_mopac_and_ticks_what_is_missing(window, monkeypatch, tmp_path):
    # the menu item asks which
    # programs — MPI, xtb, CREST (not on Windows), MOPAC; those not found are ticked, a found one says «уже есть»
    from modules.sextant import runner

    xtb = tmp_path / 'xtb.exe'
    monkeypatch.setattr(runner, 'find_mpirun', lambda *a, **k: None)
    monkeypatch.setattr(runner, 'find_program', lambda kind, configured=None, **k: xtb if kind == 'xtb' else None)
    started = []
    monkeypatch.setattr(window.install_tool, 'start_install', lambda packages: started.append(packages) or 'job')
    tool = window.install_tool
    from modules.sextant import install_tools

    monkeypatch.setattr(install_tools, 'qe_program', lambda *a, **k: None)
    offered = [p for p, _, _ in tool.offered()]
    # + Quantum ESPRESSO (on Windows — the build of MSYS2), not ticked by itself
    # CP2K — conda-forge on Linux; Homebrew on a Mac
    assert offered == (['openmpi', 'xtb', 'mopac', 'qe'] if os.name == 'nt'
                       else ['openmpi', 'xtb', 'crest', 'mopac', 'qe', 'nwchem', 'psi4', 'cp2k'])
    assert window.run_tool.install_tools_dialog(chosen=('mopac',)) == 'job' and started == [('mopac',)]
    from PySide6.QtWidgets import QCheckBox

    ticks = {t.text(): t for t in tool.choice_box.findChildren(QCheckBox)}
    assert any('MOPAC' == text for text in ticks) and any(text.startswith('xtb') and 'уже есть' in text for text in ticks)
    if os.name != 'nt':
        assert any(text.startswith('Quantum ESPRESSO') for text in ticks)
    assert window.run_tool.install_tools_dialog(chosen=()) is None and started == [('mopac',)]  # nothing ticked
    # by itself the menu ticks only xtb and MOPAC (not found); the large ones say their size
    from PySide6.QtWidgets import QDialog

    monkeypatch.setattr(QDialog, 'exec', lambda self: QDialog.DialogCode.Rejected)
    assert window.run_tool.install_tools_dialog() is None and started == [('mopac',)]
    ticked = {t.text() for t in tool.choice_box.findChildren(QCheckBox) if t.isChecked()}
    assert ticked == {'MOPAC'}  # xtb is there already
    if os.name != 'nt':
        texts = [t.text() for t in tool.choice_box.findChildren(QCheckBox)]
        assert any(t.startswith('Quantum ESPRESSO — ≈ 280') for t in texts) and 'CREST' in texts


def test_sextant_job_window_and_options(window, app, tmp_path, monkeypatch):
    # the methods and basis sets follow the program (Gaussian: ωB97X-D, no r2SCAN; ORCA: the other way
    # round) under family headers; solvent, dispersion and memory in a non-modal dialog with a summary on the
    # page; a started calculation opens its own window (minimized and restored with the main window), the run
    # button is off and painted grey (QPushButton#primary:disabled), «Остановить» stops it
    import sys
    import time

    from azimuth.app import STYLE as style

    saved = window.preferences.value('sextant_program')
    try:
        window.navigate(1)
        window.program.setCurrentIndex(window.program.findData('gaussian'))
        methods = [window.method.itemData(i) for i in range(window.method.count())]
        assert 'ωB97X-D' in methods and 'r2SCAN' not in methods and window.method.currentData() == 'B3LYP'
        header = window.method.model().item(0)
        assert window.method.itemData(0) is None and not header.isEnabled()  # «Хартри — Фок»: a header
        window.basis.setCurrentIndex(window.basis.findData('6-31G**'))
        assert '#P B3LYP/6-31G(d,p) Opt=MaxCycles=100 Freq EmpiricalDispersion=GD3BJ SCF=Tight' in window.preview.toPlainText()
        window.program.setCurrentIndex(window.program.findData('orca'))
        methods = [window.method.itemData(i) for i in range(window.method.count())]
        assert 'ωB97X-D3' in methods and 'ωB97X-D' not in methods and window.basis.currentData() == '6-31G**'
        dialog = window.show_options()
        assert dialog.isVisible() and not dialog.isModal()
        window.solvent.setCurrentIndex(window.solvent.findData('water'))
        window.dispersion.setCurrentIndex(window.dispersion.findData('D3BJ'))
        assert 'CPCM(Water)' in window.preview.toPlainText() and 'D3BJ' in window.preview.toPlainText()
        # the solvent is in the form; the dispersion — in the section «Задача» of the dialog by default (setup_rows)
        assert not dialog.isAncestorOf(window.solvent) and dialog.isAncestorOf(window.dispersion)
        assert 'заряд ' not in window.options_summary.text()  # in the card of the molecule
        window.method.setCurrentIndex(window.method.findData('M06-2X'))
        assert not window.dispersion.isEnabled() and window.calculation().dispersion == ''
        assert window.preview.toPlainText().splitlines()[1].startswith('! M062X 6-31G** ')
        dialog.close()
        window.solvent.setCurrentIndex(0)
        window.dispersion.setCurrentIndex(0)
        assert 'QPushButton#primary:disabled' in style

        fake = tmp_path / 'bin' / 'xtb'
        fake.parent.mkdir()
        fake = program_script(fake, f'#!{sys.executable}\nimport time\nprint("xtb started", flush=True)\ntime.sleep(60)\n')
        monkeypatch.setattr(window.run_tool, 'configured_program', lambda kind: str(fake) if kind == 'xtb' else None)
        monkeypatch.setattr(window.run_tool, 'jobs_root', lambda: tmp_path / 'jobs')
        window.program.setCurrentIndex(window.program.findData('xtb'))
        window.task.setCurrentIndex(window.task.findText('Энергия'))
        job = window.run_tool.run_calculation()
        jw = window.job_window
        assert job is not None and jw.isVisible() and jw.isWindow() and not window.run_button.isEnabled()
        assert 'xtb' in jw.heading.text() and str(job.spec.folder) not in jw.details.text() and jw.bar.maximum() == 0
        from modules.sextant.job_window import subscript

        assert subscript(window.coordinate_tool.table_molecule().formula) in jw.heading.text()  # H₂O, C₆H₆
        assert subscript('C6H12O6') == 'C₆H₁₂O₆' and not hasattr(jw, 'log')  # no copy of the output any more
        assert not hasattr(jw, 'minimize_button') and jw.compass_button.isHidden() and jw.spectrum_button.isHidden()
        assert window.job_window_button.isHidden()  # the calculation is a panel of the card, no «Окно расчёта»
        top = window.window()
        top.showMinimized()
        app.processEvents()
        if top.isMinimized():  # some platforms (offscreen) keep the state; then the window follows
            assert jw.isMinimized() and jw.followed
            top.showNormal()
            app.processEvents()
            assert not jw.isMinimized()
        window.run_tool.stop_calculation()
        end = time.monotonic() + 15
        while window.run_tool.poll_job() is None:
            assert time.monotonic() < end, 'the fake xtb was not stopped'
            app.processEvents()
            time.sleep(0.05)
        assert 'остановлен' in jw.status.text() and jw.bar.maximum() == 1 and window.run_button.isEnabled()
        # next to the button only the time, the status in its tooltip; the output file itself, followed
        assert 'остановлен' in window.run_time.toolTip() and 'остановлен' not in window.run_time.text()
        assert window.run_time.text() and not window.run_time.isHidden()
        with open(job.spec.output, 'a', encoding='utf-8') as f:  # the fake may be stopped before it prints anything
            f.write('xtb started\n')
        out = window.run_tool.open_output()
        assert out is not None and out.isVisible() and 'xtb started' in out.view.toPlainText()
        with open(job.spec.output, 'a', encoding='utf-8') as f:
            f.write('one more line\n')
        assert out.refresh() and out.view.toPlainText().rstrip().endswith('one more line')
        assert not out.refresh()  # nothing new
        out.find.setText('started')
        assert out.find_next()
        out.close()
        jw.close_button.click()
        assert not jw.isVisible() and jw.parked and window.show_job_window().isVisible() and not jw.parked
        jw.hide()
        # with Sextant on screen the calculation is a card in the place of the input file («Входной файл»
        # brings the file back, «Окно расчёта» the calculation); elsewhere a window that the hourglass of the hub opens;
        # back in Sextant the window closes and the card is in its place again
        window.show()
        window.navigate(1)
        app.processEvents()
        assert window.sextant_shown()
        assert window.show_job_window() is jw and jw.docked and not jw.isWindow() and window.job_slot.isAncestorOf(jw)
        assert jw.isVisible() and jw.close_button.isHidden() and not jw.input_button.isHidden() and not jw.parked
        assert window.preview_card.isHidden() and not window.job_slot.isHidden() and window.job_window_button.isHidden()
        # 0.249.5: stop, output and the folder of the calculation in the row of «Запустить расчёт»; the results and
        # «Входной файл» at the bottom inside the card
        assert jw.controls.parentWidget() is window.job_controls_slot and jw.controls.isVisible()
        assert jw.frame.isAncestorOf(jw.input_button) and jw.frame.isAncestorOf(jw.compass_button)
        assert not hasattr(window, 'jobs_folder_button')
        jw.input_button.click()  # the file back, the calculation goes on
        assert jw.controls.isVisible()  # «Остановить» stays at hand with the file shown
        assert not window.preview_card.isHidden() and window.job_slot.isHidden() and not window.job_window_button.isHidden()
        assert window.preview_card.isAncestorOf(window.job_window_button)  # on the card of the input file
        window.job_window_button.click()
        assert window.preview_card.isHidden() and not window.job_slot.isHidden()
        window.navigate(0)  # leaving Sextant: out of its place and hidden; the hourglass stands for it
        assert not jw.docked and jw.isWindow() and not jw.isVisible() and jw.parked
        assert window.show_job_window().isVisible() and jw.isWindow() and not jw.close_button.isHidden()
        assert jw.input_button.isHidden()
        assert jw.controls.parentWidget() is jw.frame  # a window of its own: the group at its bottom
        window.navigate(1)
        assert jw.docked and jw.isVisible() and not jw.isWindow() and not jw.parked and window.preview_card.isHidden()
        window.hide()
    finally:
        window.program.setCurrentIndex(0)
        if saved is None:
            window.preferences.remove('sextant_program')
        else:
            window.preferences.setValue('sextant_program', saved)


def test_sextant_edited_input_is_checked_and_run(window, app, tmp_path, monkeypatch):
    # the input file is edited in its panel; «Запустить расчёт» checks it (a mistake: the lines are tinted and
    # the user is asked; «Исправить» starts nothing), the edited text is what runs; «Собрать заново» brings the
    # generated one back; xtb stays read-only. The card: the mark of the program, its name and a tick, no path; the
    # two columns of the page start level
    import time

    orca = tmp_path / 'orca_6' / 'orca'
    orca.parent.mkdir()
    orca = program_script(orca, 'import sys\nsys.exit(1)\n')  # ends with an error at once: no result to open
    (orca.parent / 'orca_scf').write_text('')
    monkeypatch.setattr(window.run_tool, 'configured_program', lambda kind: str(orca) if kind == 'orca' else None)
    monkeypatch.setattr(window.run_tool, 'jobs_root', lambda: tmp_path / 'jobs')
    saved = window.preferences.value('sextant_program')
    try:
        show_model(window, app)
        window.navigate(1)
        app.processEvents()
        window.program.setCurrentIndex(window.program.findData('orca'))
        window.cores.setValue(1)
        window.run_tool.refresh_program_path()
        assert window.program_path.text() == 'ORCA' and not window.program_found.isHidden()
        assert str(orca) in window.program_path.toolTip() and not window.program_badge.pixmap().isNull()
        # the card of the molecule heads the right column, level with the setup; the input file below it
        assert window.calc_card.mapTo(window, QPoint(0, 0)).y() == \
            window.program.parentWidget().mapTo(window, QPoint(0, 0)).y()
        assert window.preview.mapTo(window, QPoint(0, 0)).y() > window.calc_card.mapTo(window, QPoint(0, 0)).y()
        generated = window.preview.toPlainText()
        assert not window.preview.isReadOnly() and not window.input_edited and window.input_edited_row.isHidden()
        window.preview.setPlainText(generated.rstrip().rsplit('\n', 1)[0] + '\n')  # the closing «*» removed
        assert window.input_edited and not window.input_edited_row.isHidden()
        asked = []
        monkeypatch.setattr(window.input_tool, 'confirm_input_problems', lambda problems: asked.append(problems) or False)
        assert window.run_tool.run_calculation() is None and window.job is None and asked
        assert any('*' in p.text for p in asked[0]) and window.preview.extraSelections()
        window.preview.setPlainText(generated + '# my own line\n')
        asked.clear()
        job = window.run_tool.run_calculation()
        assert job is not None and not asked and '# my own line' in job.spec.output.with_suffix('.inp').read_text(encoding='utf-8')
        assert 'вручную' in window.job_window.details.text()
        end = time.monotonic() + 15
        while window.run_tool.poll_job() is None:
            assert time.monotonic() < end, 'the fake orca did not finish'
            app.processEvents()
            time.sleep(0.05)
        assert window.input_edited and '# my own line' in window.preview.toPlainText()  # kept after the run
        window.charge.setValue(1)
        window.spin.setValue(2)
        assert 'изменились' in window.input_edited_note.text()  # the settings moved on, the file did not
        window.charge.setValue(0)
        window.spin.setValue(1)
        edit = window.input_tool.stored_input_edit()
        assert edit is not None and window.input_tool.reset_input() == generated and not window.input_edited
        window.input_tool.restore_input_edit(edit)
        assert window.input_edited and window.preview.toPlainText() == edit[0]
        window.program.setCurrentIndex(window.program.findData('xtb'))
        assert not window.input_edited and window.preview.isReadOnly() and window.input_tool.edited_input() is None
        window.job_window.hide()
    finally:
        window.program.setCurrentIndex(0)
        if saved is None:
            window.preferences.remove('sextant_program')
        else:
            window.preferences.setValue('sextant_program', saved)
        window.dirty = False


def test_sextant_where_to_calculate(window, app, monkeypatch, tmp_path):
    # «Этот компьютер» / «Сервер» — two switches with icons; for the server its profile instead of the program
    # found here, «Сервер…» instead of «Указать…»; the profile is kept without a password; a run on the server checks
    # the profile (the sending itself is the next stage)
    import time

    from modules.sextant import remote
    from modules.sextant.server_dialog import ServerDialog

    saved = {key: window.preferences.value(key) for key in (remote.WHERE_KEY, remote.PROFILE_KEY, remote.PROFILES_KEY,
                                                         remote.CURRENT_KEY, 'sextant_program')}
    try:
        window.navigate(1)
        window.program.setCurrentIndex(window.program.findData('orca'))
        local, server = window.where_buttons['local'], window.where_buttons['server']
        from azimuth.ui import SegmentButton

        assert isinstance(local, SegmentButton) and local.glyph == 'computer' and server.glyph == 'server'
        window.run_tool.set_where('local')
        assert local.isChecked() and window.server_button.isHidden() and not window.choose_program_button.isHidden()
        # both only icons, the chosen one marked (nothing in Sextant unfolds)
        assert not local.expanded and not server.expanded and local.width() == server.width() == server.SMALL
        local.grab()
        for key in (remote.PROFILE_KEY, remote.PROFILES_KEY, remote.CURRENT_KEY):
            window.preferences.remove(key)
        server.click()
        assert window.where == 'server' and window.preferences.value(remote.WHERE_KEY) == 'server'
        assert server.isChecked() and not local.isChecked() and not server.expanded
        assert not window.server_button.isHidden() and window.choose_program_button.isHidden()
        assert 'не настроен' in window.program_path.text() and window.program_found.isHidden()
        dialog = ServerDialog(remote.ServerProfile(), window)
        # the login is the window; the settings of the server slide out on «Настройки сервера» (the window widens by
        # the panel, its left edge in place) and back
        assert dialog.settings_panel.isHidden() and not dialog.settings_shown()
        narrow = dialog.width()
        assert dialog.toggle_settings() and dialog.settings_shown() and dialog.width() > narrow + 300
        assert dialog.settings_button.text() == 'Скрыть настройки сервера'
        assert not dialog.toggle_settings() and dialog.settings_panel.isHidden() and dialog.width() == narrow
        dialog.accept()  # empty: refused, the reasons shown
        assert not dialog.problems.isHidden() and 'адрес' in dialog.problems.text()
        assert dialog.settings_shown() or 'папку' not in dialog.problems.text()  # a wrong folder: the settings out
        dialog.host.setText('10.0.0.5')
        dialog.user.setText('student')
        dialog.name.setText('Кластер')
        assert 'student@10.0.0.5:22' in dialog.preview.text() and 'найдётся на сервере' in dialog.preview.text()
        dialog.setup.setPlainText('module load orca-6.1.1')  # the environment lines instead of a start command
        assert 'module load orca-6.1.1' in dialog.preview.text() and dialog.profile().setup == 'module load orca-6.1.1'
        assert dialog.command.isHidden() and not dialog.probe_button.isHidden()
        dialog.setup.setPlainText('')
        dialog.close()
        if os.name != 'nt':  # OpenVPN Connect, a fake one: its profiles, connecting when the server does not answer
            import socket
            import sys

            calls = tmp_path / 'calls.txt'
            fake = tmp_path / 'OpenVPN Connect'
            fake = program_script(fake, f'#!{sys.executable}\nimport sys\nopen({str(calls)!r}, "a").write(" ".join(sys.argv[1:]) + "\\n")\n'
                            'print(\'[{"id": "17", "name": "lab", "host": "vpn.lab.ru"}]\')\n')
            probe = ServerDialog(dialog.profile(), window, connect_app=fake)
            assert [p.id for p in probe.load_vpn_profiles()] == ['17'] and probe.vpn.currentData() == '17'
            listening = socket.socket()
            listening.bind(('127.0.0.1', 0))
            listening.listen(1)
            probe.host.setText('127.0.0.1')
            probe.port.setValue(listening.getsockname()[1])
            assert probe.check() and '✓' in probe.status.text()
            listening.close()
            assert not probe.check() and probe.timer.isActive() and 'VPN' in probe.status.text()
            end = time.monotonic() + 10
            while '--connect-shortcut=17' not in (calls.read_text() if calls.exists() else '') and time.monotonic() < end:
                time.sleep(0.05)
            assert '--connect-shortcut=17' in calls.read_text()
            assert probe.profile().vpn_id == '17' and probe.profile().vpn_name.startswith('lab')
            # the VPN by hand: «Подключить VPN» asks for the profile of the list and waits for the server, «Отключить
            # VPN» asks OpenVPN Connect to disconnect; without a profile chosen there is nothing to connect
            probe.timer.stop()
            calls.write_text('')
            assert probe.vpn_on.isEnabled() and probe.vpn_off.isEnabled() and probe.vpn_on.toolTip() == 'Подключить VPN'
            assert probe.connect_vpn() and probe.timer.isActive() and 'окно скрыто' in probe.status.text()
            assert probe.disconnect_vpn() and not probe.timer.isActive() and 'отключает' in probe.status.text()
            end = time.monotonic() + 10
            while len((calls.read_text() if calls.exists() else '').split()) < 2 and time.monotonic() < end:
                time.sleep(0.05)
            # two programs started one after another write in the order the system runs them, not that of the clicks
            assert sorted(calls.read_text().split()) == ['--connect-shortcut=17', '--disconnect-shortcut']
            probe.vpn.setCurrentIndex(probe.vpn.findData(''))
            assert not probe.vpn_on.isEnabled() and probe.vpn_off.isEnabled() and not probe.connect_vpn()
            assert 'Выберите профиль VPN' in probe.status.text()
            probe.reject()
            assert not probe.timer.isActive()
        # several profiles: saved under their names, chosen from the list; the password never in the settings
        from modules.sextant import keychain

        window.preferences.remove(remote.PROFILES_KEY)
        many = ServerDialog(remote.ServerProfile(), window, connect_app=tmp_path / 'none', settings=window.preferences)
        assert many.objectName() == 'workspace' and not many.profiles.isHidden() and many.profiles.currentData() is None
        for title, host in (('Кластер', '10.0.0.5'), ('Дома', '192.168.1.2')):
            many.new_profile()
            many.name.setText(title)
            many.host.setText(host)
            many.user.setText('student')
            many.password.setText('secret-' + title)
            many.remember.setChecked(False)  # only for this run of the program
            assert many.save()
        stored = window.preferences.value(remote.PROFILES_KEY)
        assert [p.title() for p in remote.load_all(window.preferences)] == ['Кластер', 'Дома'] and 'secret' not in stored
        assert keychain.SESSION[keychain.service_for(remote.load(window.preferences))] == 'secret-Дома'
        many.profiles.setCurrentIndex(many.profiles.findData('Кластер'))
        assert many.host.text() == '10.0.0.5' and many.password.text() == 'secret-Кластер'
        assert [p.title() for p in many.remove_profile()] == ['Дома'] and many.host.text() == '192.168.1.2'
        many.reject()
        keychain.SESSION.clear()
        window.preferences.remove(remote.PROFILES_KEY)
        remote.save(window.preferences, dialog.profile())
        window.run_tool.refresh_program_path()
        assert window.program_path.text() == 'ORCA · Кластер' and 'student@10.0.0.5:22' in window.program_path.toolTip()
        # the run opens the server first; cancelled there (the password window, the VPN) — nothing is sent
        from modules.sextant import server_access

        opened = []
        monkeypatch.setattr(server_access, 'open_server', lambda parent, p, **k: opened.append(p.address()))
        assert window.run_tool.run_calculation() is None and window.job is None and opened == ['student@10.0.0.5:22']
        local.click()
        assert window.where == 'local' and window.server_button.isHidden()
    finally:
        window.run_tool.set_where('local')
        for key, value in saved.items():
            if value is None:
                window.preferences.remove(key)
            else:
                window.preferences.setValue(key, value)


@pytest.mark.skipif(os.name == 'nt', reason='the fake server is a set of POSIX scripts')
def test_sextant_runs_on_a_server(window, app, tmp_path, monkeypatch):
    # «Сервер» → the server is asked what it has, the number of processes chosen, the calculation goes there
    # (the fake SLURM server of tests/fake_server.py: ssh, scp, sbatch, squeue, scancel, orca on this computer), the
    # window shows it like a local run, the result comes back and opens; the processes reach the input and sbatch
    import time

    from PySide6.QtWidgets import QInputDialog

    from modules.sextant import keychain, remote
    from tests import fake_server

    server = fake_server.install(tmp_path, monkeypatch)
    monkeypatch.setenv('FAKE_ORCA_OUTPUT', str(Path(__file__).parents[1] / 'data' / 'orca_cclib' / 'dvb_gopt_orca6.0.out'))
    monkeypatch.setattr(keychain, '_lib', lambda: None)
    monkeypatch.setattr(window.run_tool, 'jobs_root', lambda: tmp_path / 'jobs')
    asked = []

    def how_many(*args, **kw):  # no question — the processes are those of the panel
        asked.append(args)
        return 7, True

    monkeypatch.setattr(QInputDialog, 'getInt', how_many)
    saved = {key: window.preferences.value(key) for key in (remote.WHERE_KEY, remote.PROFILES_KEY, remote.CURRENT_KEY,
                                                         'sextant_program')}
    opened = []
    try:
        window.navigate(1)
        window.program.setCurrentIndex(window.program.findData('orca'))
        window.preferences.remove(remote.PROFILES_KEY)
        remote.save(window.preferences, remote.ServerProfile('serv3', 'serv3.lab', 22, 'user', '~/azimuth/calculations',
                                                             setup='export AZ_TEST=1'))
        window.run_tool.set_where('server')
        window.cores.setValue(1)
        window.cores.setValue(3)  # set in the panel after the server was chosen: kept, not replaced by the advice
        # (a value other than the one there — the same value is no change, and the advice may take its place)
        window.task.setCurrentIndex(window.task.findText('Оптимизация'))
        monkeypatch.setattr(window.opening_tool, 'open_example_path', lambda path, go=True, done=None: (opened.append(path), done and done()))
        job = window.run_tool.run_calculation()
        assert job is not None and job.remote_dir.startswith('~/azimuth/calculations/') and window.job is job
        assert asked == [] and window.cores.value() == 3
        assert window.job_window.windowTitle().endswith('· serv3') and '3 проц.' in window.job_window.details.text()
        end = time.monotonic() + 40
        while window.run_tool.poll_job() is None:
            assert time.monotonic() < end, 'the fake server did not finish'
            app.processEvents()
            time.sleep(0.05)
        assert job.code == 0 and job.state == 'finished' and 'завершён' in window.run_status.text()
        assert opened == [str(job.spec.output)] and (job.spec.folder / (job.spec.output.stem + '.molden.input')).exists()
        there = server / 'home' / 'azimuth' / 'calculations' / job.spec.folder.name
        assert '%pal nprocs 3 end' in (there / job.spec.output.with_suffix('.inp').name).read_text()
        assert '#SBATCH -n 3' in (there / 'job.sh').read_text() and 'export AZ_TEST=1' in (there / 'job.sh').read_text()
        assert not window.stop_button.isEnabled() and window.run_button.isEnabled()
        # back to this computer — its advice; to the server again — the advice of the server, in the panel
        from modules.sextant import cluster

        window.run_tool.set_where('local')
        title, resources = window.run_tool.server_resources
        window.run_tool.set_where('server')
        advised = cluster.plan(resources)
        assert (window.cores.value(), window.memory.value()) == (advised.processes, advised.maxcore)
        assert 'serv3' in window.cores.toolTip() and asked == []
    finally:
        window.run_tool.set_where('local')
        for key, value in saved.items():
            if value is None:
                window.preferences.remove(key)
            else:
                window.preferences.setValue(key, value)


def test_the_server_dialog_keeps_the_partition_and_the_time_limit(window, app):
    # the rows «SLURM: раздел / время», «SLURM: проект / QoS» of the profile, said under the setup lines
    from modules.sextant import remote
    from modules.sextant.server_dialog import ServerDialog

    profile = remote.ServerProfile('hpc', 'hpc.univ', 22, 'u', partition='long', time_limit='2-00:00:00', account='chem')
    dialog = ServerDialog(profile, window)
    try:
        kept = dialog.profile()
        assert (kept.partition, kept.time_limit, kept.account, kept.qos) == ('long', '2-00:00:00', 'chem', '')
        assert '-p long' in dialog.preview.text() and '-t 2-00:00:00' in dialog.preview.text()
        dialog.time_limit.setText('two days')
        assert any('Предел времени' in p for p in dialog.profile().validate())
    finally:
        dialog.close()
        dialog.deleteLater()


@pytest.mark.skipif(os.name == 'nt', reason='the fake server is a set of POSIX scripts')
def test_two_calculations_on_a_server_at_the_same_time(window, app, tmp_path, monkeypatch):
    # a single calculation on the server is moved aside into its own window, the card takes the next one; both are
    # followed to their ends, each in its own window; «Расчёт → Другие расчёты на сервере» lists the one moved aside
    import time

    from azimuth.runtime.places import Slotted
    from modules.sextant import keychain, remote
    from tests import fake_server

    fake_server.install(tmp_path, monkeypatch)
    monkeypatch.setenv('FAKE_ORCA_OUTPUT', str(Path(__file__).parents[1] / 'data' / 'orca_cclib' / 'dvb_gopt_orca6.0.out'))
    monkeypatch.setenv('FAKE_ORCA_DELAY', '2.5')
    monkeypatch.setattr(keychain, '_lib', lambda: None)
    monkeypatch.setattr(window.run_tool, 'jobs_root', lambda: tmp_path / 'jobs')
    saved = {key: window.preferences.value(key) for key in (remote.WHERE_KEY, remote.PROFILES_KEY, remote.CURRENT_KEY,
                                                         'sextant_program')}
    monkeypatch.setattr(window.opening_tool, 'open_example_path', lambda path, go=True, done=None: done and done())
    try:
        show_model(window, app)
        window.navigate(1)
        window.program.setCurrentIndex(window.program.findData('orca'))
        window.preferences.remove(remote.PROFILES_KEY)
        remote.save(window.preferences, remote.ServerProfile('serv3', 'serv3.lab', 22, 'user', '~/azimuth/calculations'))
        window.run_tool.set_where('server')
        window.task.setCurrentIndex(window.task.findText('Энергия'))
        first = window.run_tool.run_calculation()
        assert first is not None and first.running and window.run_button.isEnabled()  # the next one can be started
        assert window.parked_server_jobs() == []
        second = window.run_tool.run_calculation()
        assert second is not None and second is not first and window.job is second and first.running
        parked = window.parked_server_jobs()
        assert [(p, r) for p, _, r in parked] == [('server~2', True)] and 'serv3' in parked[0][1]
        slot = Slotted.slots(window).of_job(first)
        assert slot.place == 'server~2' and slot.job_window is not window.job_window
        assert slot.job_window.place == 'server~2' and not slot.job_window.docked and slot.job_window.isVisible()
        end = time.monotonic() + 60
        while first.running or second.running:
            assert time.monotonic() < end, 'the fake server did not finish'
            window.run_tool.poll_job()
            app.processEvents()
            time.sleep(0.05)
        window.run_tool.poll_job()
        assert first.code == 0 and second.code == 0 and slot.job_done
        assert 'завершён' in slot.job_window.status.text() and 'завершён' in window.run_status.text()
        assert [(p, r) for p, _, r in window.parked_server_jobs()] == [('server~2', False)]
        window.show_parked_job('server~2')
        assert slot.job_window.isVisible()
    finally:
        window.run_tool.set_where('local')
        for key, value in saved.items():
            if value is None:
                window.preferences.remove(key)
            else:
                window.preferences.setValue(key, value)


@pytest.mark.skipif(os.name == 'nt', reason='the fake server is a set of POSIX scripts')
def test_sextant_launch_card_and_two_places(window, app, tmp_path, monkeypatch):
    # the molecule and the launch in one card (a thin rule between, no title); the sliders of «Дополнительные
    # настройки» and the gear of the server; «Окно расчёта» at the bottom of the input file, the arrow forward; no
    # «Вывод программы» in the card; the folder of the calculations chosen and kept; «Проверить подключение» gives a
    # tick or a cross; a calculation on this computer does not keep the button of the server off
    from types import SimpleNamespace

    from modules.sextant import remote

    show_model(window, app)
    window.navigate(1)
    app.processEvents()
    assert window.calc_card.isAncestorOf(window.run_button) and window.calc_card.isAncestorOf(window.calc_rule)
    assert window.options_button.property('quail_icon') == 'sliders' and window.server_button.property('quail_icon') == 'gear'
    assert window.preview_card.isAncestorOf(window.job_window_button) and window.job_window_button.property('quail_icon') == 'forward'
    assert not hasattr(window, 'output_button') and len(window.job_windows()) == 2
    saved = {key: window.preferences.value(key) for key in ('jobs_folder', remote.PROFILES_KEY, remote.CURRENT_KEY, remote.WHERE_KEY)}
    try:
        assert window.run_tool.choose_jobs_folder(str(tmp_path / 'calcs')) == tmp_path / 'calcs'
        assert window.run_tool.jobs_root() == tmp_path / 'calcs'  # the button «Папка для расчётов…» went (0.249.5)
        # the check logs in as the calculation does (the fake server), shows the free cores and memory, then
        # asks again every SERVER_PING_S seconds: the server goes offline — a cross, back — a tick
        import time

        from modules.sextant import keychain
        from tests import fake_server

        server = fake_server.install(tmp_path, monkeypatch)
        monkeypatch.setattr(keychain, 'SESSION', {})
        monkeypatch.setattr(keychain, '_lib', lambda: None)
        monkeypatch.setattr(window, 'SERVER_PING_S', 0.2)
        window.preferences.remove(remote.PROFILES_KEY)
        remote.save(window.preferences, remote.ServerProfile('serv3', '192.0.2.103', 22, 'user', '~/azimuth/calculations'))
        window.run_tool.set_where('server')
        assert not window.check_server_button.isHidden() and window.server_mark.isHidden()
        assert not window.server_files_button.isHidden()  # between «Сервер…» and the check
        xs = [w.mapTo(window, w.rect().topLeft()).x() for w in (window.server_button, window.server_files_button,
                                                                 window.check_server_button)]
        assert xs == sorted(xs)  # in the row: «Сервер…», the files, the check
        from azimuth import tasks

        def no_window(*args, **kwargs):  # the check opens no waiting window, only the spinner turns
            raise AssertionError('a waiting window was opened')

        monkeypatch.setattr(tasks, 'run_waiting', no_window)
        window.program.setCurrentIndex(window.program.findData('orca'))
        assert window.run_tool.check_server() and window.server_mark.text().startswith('✓') and 'ядер' in window.server_mark.text()
        assert not window.server_spinner.running() and window.server_spinner.isHidden()
        # is the program there — the fake ORCA is in PATH of the server, Gaussian is not
        assert not window.program_found.isHidden() and 'на сервере serv3' in window.program_found.toolTip()
        # Gaussian is not run by a server at all (0.249.15): the calculation goes to this computer, «Сервер» says why
        window.program.setCurrentIndex(window.program.findData('gaussian'))
        assert window.where == 'local' and 'Gaussian' in window.where_buttons['server'].toolTip()
        window.program.setCurrentIndex(window.program.findData('orca'))
        window.run_tool.set_where('server')
        assert window.run_tool.check_server() and not window.program_found.isHidden()
        window.server_spinner.start()
        window.server_spinner.grab()  # it paints
        window.server_spinner.stop()
        assert 'serv3: свободно' in window.server_mark.toolTip() and window.server_watch_timer.isActive()

        def wait_for(mark):
            end = time.monotonic() + 15
            while not window.server_mark.text().startswith(mark):
                assert time.monotonic() < end, window.server_mark.text()
                app.processEvents()
                time.sleep(0.05)

        (server / 'offline').write_text('')
        wait_for('✗')
        assert 'Connection timed out' in window.server_mark.toolTip() or 'связ' in window.server_mark.toolTip()
        (server / 'offline').unlink()
        wait_for('✓')
        window.run_tool.set_where('local')
        assert window.check_server_button.isHidden() and window.server_mark.isHidden()
        assert window.server_files_button.isHidden()
        assert not window.server_watch_timer.isActive()
        busy = SimpleNamespace(running=True, code=None, stop=lambda: None)
        with window.at_place('local'):
            window.job = busy
        window.input_tool.refresh_input()
        assert window.run_tool.job_running() and not window.run_button.isEnabled()
        window.run_tool.set_where('server')
        assert window.job is None and not window.run_tool.job_running() and window.run_button.isEnabled()
        window.run_tool.set_where('local')
        assert window.job is busy and not window.run_button.isEnabled()
    finally:
        with window.at_place('local'):
            window.job = None
        for key, value in saved.items():
            if value is None:
                window.preferences.remove(key)
            else:
                window.preferences.setValue(key, value)
        window.run_tool.set_where(saved[remote.WHERE_KEY] or 'local')
        window.navigate(0)


def test_job_window_shows_the_way_and_the_problem(window, app):
    # «Ход расчёта» over the stages; a failure — what it is and what it may come from, under them
    jw = window.job_window
    jw.begin('H₂O')
    assert jw.stages_title.isHidden() and jw.problem.isHidden()
    jw.add_stage('setup', 'Входной файл прочитан, базис построен')
    assert not jw.stages_title.isHidden() and jw.stages_title.text() == 'Ход расчёта'
    assert jw.show_problems([('Не хватило памяти.', 'Увеличьте память.')])
    assert not jw.problem.isHidden() and 'Не хватило памяти.' in jw.problem.text()
    jw.begin('H₂O')
    assert jw.problem.isHidden() and jw.stages_title.isHidden()


def test_open_an_input_file_in_sextant(window, app, tmp_path):
    # an ORCA input opened in Sextant — the molecule, the program, the method, the basis, the task, the charge and
    # multiplicity, and the file itself kept as the edited input; the title of the file on one line
    show_model(window, app)
    window.confirm_replace = lambda: True
    path = tmp_path / 'oh.inp'
    path.write_text('! PBE0 def2-TZVP Opt TightSCF\n%pal nprocs 3 end\n* xyz 0 2\nO 0 0 0\nH 0 0 0.97\n*\n', encoding='utf-8')
    assert window.input_tool.open_input_file(str(path)) == 'orca'
    calc = window.calculation()
    assert window.molecule.formula == 'HO' and (calc.method, calc.basis, calc.task) == ('PBE0', 'def2-TZVP', 'Оптимизация')
    assert (calc.charge, calc.multiplicity) == (0, 2) and window.stack.currentIndex() == 1
    assert window.input_edited and '%pal nprocs 3 end' in window.preview.toPlainText()
    assert window.input_tool.edited_input().startswith('! PBE0 def2-TZVP Opt')
    assert not window.preview_title.wordWrap()
    window.input_tool.reset_input()
    window.navigate(0)


def test_sextant_page_keeps_less_text(window, app):
    # no note on the calculation programs, no memory line in the card of the molecule; what the lines of the
    # input mean is behind «?» next to its title (a popup), for every program
    window.navigate(1)
    window.program.setCurrentIndex(window.program.findData('orca'))
    assert not hasattr(window, 'programs_note')
    assert 'Электронов' in window.state_info.text() and 'Память' not in window.state_info.text()
    # the card says how big the calculation is (the atoms, the basis functions, method/basis and the task)
    assert 'базисных функций' in window.state_info.text() and 'Атомов: ' in window.state_info.text()
    assert window.preview_notice.isHidden() and '%pal' in window.input_help_button.toolTip()
    assert window.input_help_button.text() == '?' and '%maxcore' in window.show_input_help()
    window.program.setCurrentIndex(window.program.findData('gaussian'))
    assert '%nprocshared' in window.input_help_button.toolTip() and 'Память' not in window.state_info.text()
    window.program.setCurrentIndex(window.program.findData('orca'))


def test_sextant_families_state_advice_and_advanced_settings(window, app, monkeypatch):
    # the method and the basis are chosen through families (a menu of families with submenus); charge and
    # multiplicity follow the structure until changed by hand (then a remark); the advice is applied with a
    # button; the advanced settings reach the input file; the computer's resources are advised
    from modules.sextant import advice as adv
    from azimuth.core import Atom, Calculation, Molecule

    saved = window.preferences.value('sextant_program')
    try:
        window.navigate(1)
        window.program.setCurrentIndex(window.program.findData('orca'))
        menu = window.method_picker.open_menu()
        families = [a for a in menu.actions() if a.menu() is not None]
        assert families and all(a.menu().actions() for a in families)  # every family opens its methods
        hybrid = next(a.menu() for a in families if 'гибрид' in a.text() and 'двойн' not in a.text())
        next(a for a in hybrid.actions() if a.text() == 'PBE0').trigger()
        assert window.method.currentData() == 'PBE0' and window.method_picker.text() == 'PBE0'
        menu.close()
        window.basis.setCurrentIndex(window.basis.findData('def2-TZVP'))
        assert window.basis_picker.text() == 'def2-TZVP'
        window.method.setEnabled(False)
        assert not window.method_picker.isEnabled()
        window.method.setEnabled(True)

        nh4 = Molecule('nh4', (Atom('N', 0, 0, 0), Atom('H', 0.63, 0.63, 0.63), Atom('H', -0.63, -0.63, 0.63),
                               Atom('H', -0.63, 0.63, -0.63), Atom('H', 0.63, -0.63, -0.63)))
        window.load_molecule(nh4)
        window.input_tool.refresh_input()
        assert (window.charge.value(), window.spin.value()) == (1, 1) and window.state_note.isHidden()
        window.charge.setValue(0)
        window.spin.setValue(2)
        assert not window.state_note.isHidden() and 'заряд 1' in window.state_note.text()
        window.load_molecule(read_xyz(EXAMPLES['Вода · H₂O']))
        window.input_tool.refresh_input()
        assert (window.charge.value(), window.spin.value()) == (0, 1)  # another composition: the structure again

        window.task.setCurrentIndex(window.task.findText('Оптимизация + частоты'))
        found = window.current_advice()
        assert (found.method, found.basis) == ('B3LYP', 'def2-SVP')
        assert 'B3LYP' in window.method_picker.toolTip() and 'def2-SVP' in window.basis_picker.toolTip()
        menu = window.method_picker.open_menu()
        first = menu.actions()[0]
        assert not first.icon().isNull() and 'B3LYP' in first.text()  # the gold star is its icon
        first.trigger()  # the method and its dispersion
        menu.close()
        menu = window.basis_picker.open_menu()
        menu.actions()[0].trigger()
        menu.close()
        calc = window.calculation()
        assert (calc.method, calc.basis, calc.dispersion) == ('B3LYP', 'def2-SVP', 'D3BJ')
        dialog = window.show_options()
        # sections on the left, one page on the right, the window of one size whatever is shown; the processes
        # and the memory are in the form, not in the dialog
        names = [name for name, page in dialog.groups]
        assert names[0] == 'Электронное состояние' and 'Релятивистские поправки' in names
        # the settings of optimization, frequencies and TD-DFT are under the task in the form, not here
        assert 'Возбуждённые состояния (TD-DFT)' not in names and 'Оптимизация и частоты' not in names
        assert not dialog.isAncestorOf(window.cores) and not dialog.isAncestorOf(window.ts)
        size = dialog.size()
        assert dialog.open_group('SCF и интегрирование') is not None and dialog.current_section() == 'SCF и интегрирование'
        app.processEvents()
        assert window.grid.isVisibleTo(dialog) and dialog.size() == size
        dialog.open_group('Релятивистские поправки')
        assert window.relativistic.isVisibleTo(dialog) and not window.grid.isVisibleTo(dialog) and dialog.size() == size
        window.relativistic.setCurrentIndex(window.relativistic.findData('DKH'))
        assert ' DKH' in window.preview.toPlainText().splitlines()[1] and 'DKH2' in window.options_summary.text()
        # the fields of the dialog show their values in the middle; a switch takes the whole width
        assert window.max_cycles.alignment() & Qt.AlignmentFlag.AlignHCenter
        assert window.scf_level.width() <= dialog.pages.width()
        window.relativistic.setCurrentIndex(0)
        dialog.close()

        window.ts.setChecked(True)
        window.opt_conv.setCurrentIndex(window.opt_conv.findData('tight'))
        window.max_cycles.setValue(77)
        window.orbitals.setChecked(True)
        text = window.preview.toPlainText()
        assert 'OptTS' in text and 'TightOpt' in text and 'MaxIter 77' in text and 'Print[P_MOs] 1' in text
        assert 'изменено настроек: 4' in window.options_summary.text() and not hasattr(window, 'extra')
        window.apply_calculation_options(Calculation())
        assert window.advanced_count() == 0 and 'OptTS' not in window.preview.toPlainText()

        monkeypatch.setattr(adv, 'machine', lambda: adv.Machine(16, 8, 16384))
        assert window.apply_machine() == (7, 1400) and window.cores.value() == 7 and window.memory.value() == 1400
        assert '8 ядер' in window.cores.toolTip() and '1400 МБ' in window.memory.toolTip()
    finally:
        window.program.setCurrentIndex(0)
        if saved is None:
            window.preferences.remove('sextant_program')
        else:
            window.preferences.setValue('sextant_program', saved)


def test_sextant_molecule_card(window, app):
    # Sextant shows the molecule to be calculated (small, turned by the mouse), its formula and a rough time;
    # the input file can take the whole column
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest

    show_model(window, app)
    window.navigate(1)
    app.processEvents()
    assert window.calc_thumb.molecule is not None and window.calc_thumb.molecule.atoms
    assert window.calc_formula.text() and window.time_estimate.text().startswith('Примерное время')
    # «К молекуле в Компасе» next to «Что считаем»; charge and multiplicity in «Дополнительные настройки…»
    assert window.calc_card.isAncestorOf(window.to_compass_button)
    assert window.options_dialog.isAncestorOf(window.charge) and window.options_dialog.isAncestorOf(window.spin)
    assert 'заряд ' not in window.options_summary.text() and 'Заряд: 0' in window.state_info.text()
    # the tabs above all the sections are those of the projects; Sextant has no row of its own
    assert not hasattr(window, 'sextant_tab_row') and not window.project_tabs.isHidden()
    yaw = window.calc_thumb.yaw
    QTest.mousePress(window.calc_thumb, Qt.MouseButton.LeftButton, pos=QPoint(40, 40))
    QTest.mouseMove(window.calc_thumb, QPoint(90, 50))
    QTest.mouseRelease(window.calc_thumb, Qt.MouseButton.LeftButton, pos=QPoint(90, 50))
    assert window.calc_thumb.yaw != yaw
    assert window.calc_quill.isHidden() and not window.calc_thumb.isHidden()
    window.new_document()  # no atoms — Quill with the magnifier next to «Атомов пока нет»
    window.update_calc_card()
    assert window.calc_formula.text() == 'Атомов пока нет'
    assert not window.calc_quill.isHidden() and window.calc_thumb.isHidden()
    window.expand_input_button.click()
    assert window.calc_card.isHidden()
    window.expand_input_button.click()
    assert not window.calc_card.isHidden()
    window.navigate(0)


def test_dummy_atom_in_compass_and_sextant(window, app):
    # the dummy atom X — in the periodic table, drawn as a small point with a dashed ring, in the coordinates
    # as X; Sextant leaves it out of the input file and of the constraints
    from modules.compass.panels.periodic import PeriodicTable

    show_model(window, app)
    window.confirm_replace = lambda: True
    table = PeriodicTable('C', window)
    assert 'X' in table.buttons
    table.close()
    mol = read_xyz('4\nw\nO 0 0 0\nX 0 0 1.2\nH 0.7586 0 0.5043\nH -0.7586 0 0.5043\n')
    saved = list(getattr(window, 'constraints', []))
    try:
        window.load_molecule(mol)
        window.viewer.grab()
        window.element.setCurrentText('X')
        assert window.element.currentText() == 'X'
        window.element.setCurrentText('C')
        window.constraints = [('B', (0, 2)), ('B', (0, 1))]
        assert window.calculation_molecule().formula == 'H2O' and len(window.calculation_molecule().atoms) == 3
        assert window.calculation_constraints() == (('B', (0, 1)),)
        window.program.setCurrentIndex(window.program.findData('orca'))
        window.input_tool.refresh_input()
        text = window.preview.toPlainText()
        rows = [line.split() for line in text.splitlines() if len(line.split()) == 4]
        assert rows and all(r[0] not in ('X', 'DA') for r in rows)
    finally:
        window.constraints = saved
        window.viewer.constraints = list(saved)
        for d in window.all_documents():
            d.dirty = False
        window.dirty = False


def test_tasks_drop_superseded_answers(app):
    # the answer of a task comes back in the window's thread; a newer request for the same key supersedes the
    # older one, cancel drops it, a failure goes to failed
    import threading
    import time

    from azimuth.tasks import Tasks

    tasks = Tasks()
    got, errors, threads = [], [], []
    gate = threading.Event()

    def slow(value):
        def work():
            threads.append(threading.current_thread() is not threading.main_thread())
            gate.wait(5)
            return value
        return work

    tasks.run('a', slow(1), got.append)
    tasks.run('a', slow(2), got.append)  # supersedes the first
    tasks.run('b', lambda: 1 / 0, got.append, errors.append)
    tasks.run('c', slow(3), got.append)
    tasks.cancel('c')
    assert tasks.busy('a') and not tasks.busy('c')
    time.sleep(0.05)
    gate.set()
    assert tasks.wait(5, app)
    assert got == [2] and isinstance(errors[0], ZeroDivisionError) and all(threads)


def test_big_output_is_read_in_the_background(window, app, monkeypatch):
    # an output bigger than BACKGROUND_BYTES is read and parsed in a worker thread: open_path returns at once,
    # the result is shown later (in its tab, the steps drawer opened by the continuation); a small one as before
    show_model(window, app)
    window.confirm_replace = lambda: True
    path = Path(__file__).parents[2] / 'examples' / 'optimization-demo.out'
    monkeypatch.setattr(window, 'BACKGROUND_BYTES', 10)
    shown = []
    original = window.display_output
    monkeypatch.setattr(window, 'display_output', lambda *a, **k: shown.append(a[1]) or original(*a, **k))
    try:
        window.opening_tool.open_path(str(path))
        assert not shown and window.tasks.busy()
        assert window.tasks.wait(20, app)
        assert shown == ['optimization-demo.out'] and len(window.drawer.steps) == 5 and window.trajectory_button.isChecked()
        window.trajectory_tool.set_trajectory_open(False)
        monkeypatch.setattr(window, 'BACKGROUND_BYTES', 10**9)
        assert window.open_output_path(str(path), show=False) is True and shown[-1] == 'optimization-demo.out'
    finally:
        window.trajectory_tool.set_trajectory_open(False)
        for d in window.all_documents():
            d.dirty = False
        window.dirty = False


def test_waiting_has_no_dialog_and_holds_nothing_back(window, app):
    # run_waiting shows no progress dialog: the title and «Esc — отменить» on the pill; Esc stops the work
    # (InterruptedError). The clicks go through, no busy cursor
    # over the program; a second work, another tab, another project wait (held, said); in another section the work is
    # on the board of the left panel with its section, back in its own it leaves the panel
    import time

    from PySide6.QtCore import QTimer
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QProgressDialog

    from azimuth import tasks
    from azimuth.tasks import run_waiting

    window.show()
    window.navigate(0)
    app.processEvents()
    seen = {}
    said = []
    original = window.notify
    window.notify = lambda text, ms=8000: (said.append(text), original(text, ms))
    documents = len(window.documents)

    def press():
        seen['cursor'] = QApplication.overrideCursor()
        # the line of the work on a pill of its own (busy_status), the messages on the notice
        pill = window.busy_pill()
        seen['bar'] = pill.text() if pill is not None else ''
        from azimuth.ui import Spinner

        seen['spinner'] = [s for s in pill.findChildren(Spinner) if s.isVisible()] if pill is not None else []
        seen['busy'] = tasks.busy()
        seen['dialogs'] = [w for w in QApplication.topLevelWidgets() if isinstance(w, QProgressDialog) and w.isVisible()]
        clicked = []
        button = window.next_button
        button.clicked.connect(lambda *a: clicked.append(1))
        QTest.mouseClick(button, Qt.MouseButton.LeftButton)  # goes through: «К параметрам расчёта» — Sextant
        seen['clicked'] = list(clicked)
        seen['section'] = window.stack.currentIndex()
        item = window.activities.get(tasks.WAITING)
        seen['parked'] = item is not None and item.parked and item.section == 'compass'
        try:
            run_waiting(window, 'Второй', lambda step: 1)
            seen['second'] = 'ran'
        except InterruptedError:
            seen['second'] = 'held'
        seen['held'] = tasks.held()
        seen['refused'] = any('Идёт расчёт: «Считаю»' in t for t in said)
        window.navigate(0)
        item = window.activities.get(tasks.WAITING)
        seen['back'] = item is not None and not item.parked
        QTest.keyClick(window, Qt.Key.Key_Escape)

    def work(step):
        end = time.monotonic() + 10
        while step(0, 0) and time.monotonic() < end:
            time.sleep(0.02)
        if not step(0, 0):
            raise InterruptedError()
        return 'not stopped'

    QTimer.singleShot(800, press)
    try:
        with pytest.raises(InterruptedError):
            run_waiting(window, 'Считаю…', work)
    finally:
        del window.notify
    assert seen['cursor'] is None and not seen['dialogs'] and seen['clicked'] == [1] and seen['section'] == 1
    assert seen['bar'].startswith('Считаю') and 'Esc — отменить' in seen['bar']
    assert len(seen['spinner']) == 1 and seen['busy'] == 'Считаю…'
    assert seen['parked'] and seen['second'] == 'held' and seen['held'] and seen['refused'] and seen['back']
    assert not tasks.busy() and window.activities.get(tasks.WAITING) is None and len(window.documents) == documents
    assert QApplication.overrideCursor() is None and not window.notice.text().endswith('Esc — отменить')
    assert not window.notice.property('busy')
    # the next work of the same action, begun at once in another section, keeps the section of the first
    time.sleep(tasks.CHAIN_S)  # the work above is over long enough: a new action
    window.navigate(2)
    QTimer.singleShot(150, lambda: window.navigate(0))  # the user leaves for Compass while the first step goes on
    run_waiting(window, 'Шаг 1', lambda step: (time.sleep(0.5), 1)[1])
    assert window.stack.currentIndex() == 0
    seen.clear()

    QTimer.singleShot(100, lambda: seen.update(item=window.activities.get(tasks.WAITING)))
    assert run_waiting(window, 'Шаг 2', lambda step: (time.sleep(0.5), 2)[1]) == 2
    item = seen.get('item')
    assert item is not None and item.section == 'spectrum' and item.parked
    # ended in another section — the sign stays, done; opened (its section shown) it goes
    item = window.activities.get(tasks.WAITING)
    assert item is not None and item.state == 'done' and item in window.activities.shown()
    window.activities.seen(tasks.WAITING)
    assert window.activities.get(tasks.WAITING) is None
    time.sleep(tasks.CHAIN_S)
    window.navigate(0)


def test_a_wait_from_deep_in_spectrum_turns_on_its_pill(window, app):
    # a panel many parents below
    # the window (the cards of «Делокализация») — the window is found, the ring turns on the pill of Spectrum
    import time

    from PySide6.QtCore import QTimer
    from PySide6.QtTest import QTest

    from azimuth.tasks import run_waiting
    from azimuth.ui import Spinner

    window.show()
    window.navigate(2)
    app.processEvents()
    panel = window.deloc_panel
    depth, widget = 0, panel
    while widget is not None and widget is not window:
        depth, widget = depth + 1, widget.parentWidget()
    seen = {}

    def look():
        toast = window.busy_pill()  # the pill of the work itself
        seen['ring'] = toast is not None and any(s.isVisible() and s.kind == 'spectrum'  # the drawn spectrum
                                                 for s in toast.findChildren(Spinner))
        seen['text'] = toast.text() if toast is not None else ''
        QTest.keyClick(window, Qt.Key.Key_Escape)

    def work(step):
        end = time.monotonic() + 10
        while step(0, 0) and time.monotonic() < end:
            time.sleep(0.02)
        raise InterruptedError()

    QTimer.singleShot(800, look)
    with pytest.raises(InterruptedError):
        run_waiting(panel, 'Индексы делокализации…', work)
    assert widget is window and seen['text'].startswith('Индексы делокализации') and seen['ring'], depth
    window.navigate(0)


def test_fields_are_built_off_the_window_thread(window, app):
    # an orbital or the density is computed in a worker thread while the window paints (run_waiting): the
    # result comes back to the caller, an error and «Отмена» (InterruptedError) are raised again; the field of the
    # orbital window is computed once for showing and saving the same orbital on the same grid
    import threading

    from azimuth.tasks import run_waiting

    seen = []

    def work(step):
        seen.append(threading.current_thread() is not threading.main_thread())
        assert step(1, 2)
        return 42

    assert run_waiting(window, 'test', work, 2) == 42 and seen == [True]
    with pytest.raises(ZeroDivisionError):
        run_waiting(window, 'test', lambda step: 1 / 0)
    with pytest.raises(InterruptedError):
        run_waiting(window, 'test', lambda step: (_ for _ in ()).throw(InterruptedError('cancelled')))
    text = (Path(__file__).parents[1] / 'data' / 'orbitals' / 'molden5.7_water_mp2.molden').read_text(encoding='utf-8')
    dialog = window.open_orbitals_text(text, 'water.molden')
    try:
        dialog.select(dialog.orbital_set.frontier()[0])
        dialog.step.setCurrentIndex(0)  # coarse: quick
        first = dialog.orbital_field()
        assert first is not None and dialog.orbital_field() is first  # kept for «Сохранить CUBE»
        dialog.step.setCurrentIndex(1)
        assert dialog.orbital_field() is not first
    finally:
        dialog.close()


def test_relaxed_scan_task_takes_its_coordinate_from_the_constraints(window, app):
    # «Скан ППЭ с релаксацией» — the coordinate among the constraints of Compass (with its value now), the end
    # (+0.5 Å for a bond, +30° for an angle) and the points; without a bond or an angle the form says what to do
    from azimuth.core import SCAN_TASK, coordinate_value

    saved = list(getattr(window, 'constraints', []) or [])
    window.navigate(1)
    window.program.setCurrentIndex(window.program.findData('orca'))
    try:
        window.constraints = [('C', (2,)), ('B', (0, 1)), ('A', (1, 0, 2))]
        window.task.setCurrentIndex(window.task.findText(SCAN_TASK))
        app.processEvents()
        assert window.scan_index.isVisibleTo(window) and window.scan_end.isVisibleTo(window)
        assert not window.ts.isVisibleTo(window)
        mol = window.calculation_molecule()
        bond = coordinate_value(mol, 'B', (0, 1))
        assert window.scan_index.count() == 2 and window.scan_index.itemText(0).startswith('r(')
        assert window.scan_end.value() == pytest.approx(bond + 0.5, abs=1e-3) and window.scan_end.suffix() == ' Å'
        assert 'B 0 1 = ' in window.preview.toPlainText() and '{ C 2 C }' in window.preview.toPlainText()
        window.scan_index.setCurrentIndex(1)
        window.scan_coordinate_chosen()
        angle = coordinate_value(mol, 'A', (1, 0, 2))
        assert window.scan_end.value() == pytest.approx(angle + 30.0, abs=0.1) and window.scan_end.suffix() == '°'
        assert 'A 1 0 2 = ' in window.preview.toPlainText() and window.calculation().scan_index == 1
        window.program.setCurrentIndex(window.program.findData('gaussian'))
        assert ' S 9 ' in window.preview.toPlainText()  # ten points by default: nine steps
        window.constraints = [('C', (2,))]
        window.input_tool.refresh_input()
        assert window.scan_index.itemText(0).startswith('Нет')
        assert not window.input_error.isHidden() and 'Ограничения оптимизации' in window.input_error.text()
    finally:
        window.constraints = saved
        window.program.setCurrentIndex(window.program.findData('orca'))
        window.task.setCurrentIndex(0)
        window.input_tool.refresh_input()



def test_two_dimensional_scan_in_sextant(window, app):
    # «Вторая координата» and «Конец 2» under the scan
    # of ORCA; the input has two lines in Scan (the form verified on ORCA 6.0.1, tests/data/scan2d/inputs)
    from azimuth.core import SCAN_TASK, coordinate_value

    saved = list(getattr(window, 'constraints', []) or [])
    window.navigate(1)
    window.program.setCurrentIndex(window.program.findData('orca'))
    from modules.sextant.setup_rows import MOVABLE

    window.setup_rows.set_outside(MOVABLE)  # every field in the card (the second coordinate is inside by default)
    try:
        window.constraints = [('B', (0, 1)), ('A', (1, 0, 2))]
        window.task.setCurrentIndex(window.task.findText(SCAN_TASK))
        app.processEvents()
        window.input_tool.refresh_input()
        assert window.scan2_index.isVisibleTo(window) and window.scan2_end.isVisibleTo(window)
        assert window.scan2_index.count() == 3 and window.scan2_index.itemText(0).startswith('Нет')
        assert window.calculation().scan2_index == -1 and window.preview.toPlainText().count(' = ') == 1
        window.scan2_index.setCurrentIndex(2)
        window.scan2_coordinate_chosen()
        angle = coordinate_value(window.calculation_molecule(), 'A', (1, 0, 2))
        assert window.scan2_end.value() == pytest.approx(angle + 30.0, abs=0.1) and window.scan2_end.suffix() == '°'
        text = window.preview.toPlainText()
        assert 'B 0 1 = ' in text and 'A 1 0 2 = ' in text and window.calculation().scan2_index == 1
        window.program.setCurrentIndex(window.program.findData('xtb'))
        app.processEvents()
        assert not window.scan2_index.isVisibleTo(window)
    finally:
        window.setup_rows.reset()
        window.constraints = saved
        window.program.setCurrentIndex(window.program.findData('orca'))
        window.task.setCurrentIndex(0)
        window.input_tool.refresh_input()


def test_start_orbitals_of_an_earlier_calculation_in_sextant(window, app, tmp_path, monkeypatch):
    # «Орбитали» under the task (ORCA only): the folder button chooses the .gbw (the dialog opens at the .gbw
    # next to the result of the tab), the cross takes it away; the input gets MORead and %moinp
    from PySide6.QtWidgets import QFileDialog

    gbw = tmp_path / 'earlier.gbw'
    gbw.write_bytes(b'x')
    window.navigate(1)
    window.program.setCurrentIndex(window.program.findData('orca'))
    asked = []
    monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *a, **k: (asked.append(a[2]) or str(gbw), ''))
    try:
        app.processEvents()
        # in «Дополнительные настройки…» (section «Начальное приближение»), not under the task in the form
        assert window.guess.window() is window.options_dialog and window.guess.isEnabled()
        assert not window.guess.clear_button.isEnabled()
        assert 'MORead' not in window.preview.toPlainText()
        window.guess.choose_button.click()
        assert window.guess.path() == str(gbw) and window.guess.name.text() == 'earlier.gbw' and asked
        assert 'MORead' in window.preview.toPlainText() and '%moinp "start-orbitals.gbw"' in window.preview.toPlainText()
        assert window.calculation().guess == str(gbw) and 'earlier.gbw' in window.options_summary.text()
        window.program.setCurrentIndex(window.program.findData('gaussian'))
        assert not window.guess.isEnabled() and window.calculation().guess == ''
        window.program.setCurrentIndex(window.program.findData('orca'))
        window.guess.clear_button.click()
        assert window.guess.path() == '' and 'MORead' not in window.preview.toPlainText()
    finally:
        window.guess.set_path('')


def test_sextant_tasks_and_their_settings_follow_the_program(window, app):
    # each program lists only its tasks (MOPAC: energy, optimization, + frequencies); the settings of the task
    # are under it in the form — only those the program writes; rows a program does not use (basis of MOPAC) are hidden
    from azimuth.core import TASKS
    from azimuth.i18n import KEY_ROLE
    from modules.sextant import inputs

    show_model(window, app)
    window.dirty = False
    window.load_molecule(read_xyz(EXAMPLES['Вода · H₂O']))
    window.navigate(1)
    app.processEvents()
    from modules.sextant.setup_rows import MOVABLE

    window.setup_rows.set_outside(MOVABLE)  # every field in the card: the rows of the tasks are looked at there
    try:
        window.program.setCurrentIndex(window.program.findData('orca'))
        from modules.sextant.chain_steps import CHAIN_ROLE

        # the chains after the tasks, after a line (their own key: CHAIN_ROLE)
        plain = lambda: [window.task.itemData(i, KEY_ROLE) for i in range(window.task.count())  # noqa: E731
                         if window.task.itemData(i, KEY_ROLE) and not window.task.itemData(i, CHAIN_ROLE)]
        assert plain() == list(TASKS)
        # a task chosen by the user brings its method and its settings
        window.task.setCurrentIndex(window.task.findText('Спектр UV-Vis (TD-DFT)'))
        window.task_chosen()
        assert window.calculation().method == 'CAM-B3LYP'
        window.task.setCurrentIndex(window.task.findText('ЯМР (экранирование)'))
        window.task_chosen()
        assert (window.calculation().method, window.calculation().grid) == ('PBE0', 'fine')
        window.task.setCurrentIndex(window.task.findText('Оптимизация + частоты'))
        window.task_chosen()
        assert window.calculation().opt_conv == 'tight' and window.calculation().grid == ''
        # the solvation model next to the solvent (ORCA, Gaussian), the stability analysis under «Энергия»
        window.solvent.setCurrentIndex(window.solvent.findData('water'))
        app.processEvents()
        assert window.solvent_model.isVisibleTo(window)
        window.solvent_model.setCurrentIndex(window.solvent_model.findData('smd'))
        assert 'smd true' in window.preview.toPlainText()
        window.solvent.setCurrentIndex(0)
        app.processEvents()
        assert not window.solvent_model.isVisibleTo(window)
        window.solvent_model.setCurrentIndex(0)
        window.task.setCurrentIndex(window.task.findText('Энергия'))
        app.processEvents()
        assert window.stability.isVisibleTo(window)
        window.task.setCurrentIndex(window.task.findText('Оптимизация + частоты'))
        app.processEvents()
        assert window.task_box.isVisibleTo(window) and 'Оптимизация + частоты' in window.task_heading.text()
        for widget in (window.ts, window.opt_conv, window.max_cycles, window.temperature, window.pressure, window.raman):
            assert widget.isVisibleTo(window), widget
        assert not window.states.isVisibleTo(window) and not window.options_dialog.isAncestorOf(window.ts)
        window.task.setCurrentIndex(window.task.findText('Спектр UV-Vis (TD-DFT)'))
        app.processEvents()
        assert window.states.isVisibleTo(window) and window.triplets.isVisibleTo(window)
        assert not window.ts.isVisibleTo(window) and not window.root.isVisibleTo(window)
        window.states.setValue(7)
        assert 'nroots 7' in window.preview.toPlainText().lower()
        window.states.setValue(10)
        window.task.setCurrentIndex(window.task.findText('Энергия'))
        app.processEvents()
        assert window.task_box.isVisibleTo(window) and window.stability.isVisibleTo(window)  # under «Энергия»
        height = window.program.height()
        window.task.setCurrentIndex(window.task.findText('Оптимизация возбуждённого состояния (TD-DFT)'))
        app.processEvents()
        # the number of states and the root share a row: the form keeps its size (8 rows squeezed every field)
        assert window.states.isVisibleTo(window) and window.root.isVisibleTo(window) and window.program.height() == height
        assert not window.triplets.isVisibleTo(window)  # the excited-state optimization follows a singlet
        window.task.setCurrentIndex(window.task.findText('Переходное состояние + частоты'))
        app.processEvents()
        assert 'OptTS Freq' in window.preview.toPlainText() and not window.ts.isVisibleTo(window)
        window.task.setCurrentIndex(window.task.findText('Частоты и термохимия'))
        app.processEvents()
        assert ' Freq ' in window.preview.toPlainText().splitlines()[1] and 'без оптимизации' in window.task_note.text()
        window.task.setCurrentIndex(window.task.findText('ЯМР (экранирование)'))
        window.program.setCurrentIndex(window.program.findData('mopac'))
        app.processEvents()
        assert plain() == list(inputs.MOPAC_TASKS)
        assert window.calculation().task == 'Оптимизация + частоты'  # NMR is not in MOPAC: told and replaced
        assert window.ts.isVisibleTo(window) and window.temperature.isVisibleTo(window)
        assert not window.opt_conv.isVisibleTo(window) and not window.pressure.isVisibleTo(window)
        assert not window.basis_picker.isVisibleTo(window) and not window.dispersion.isVisibleTo(window)
        assert not window.memory.isVisibleTo(window) and window.method_picker.isVisibleTo(window)
        assert 'def2' not in window.state_info.text() and 'PM7 · ' in window.state_info.text()
        window.program.setCurrentIndex(window.program.findData('xtb'))
        app.processEvents()
        assert len(plain()) == 5 and not window.method_picker.isVisibleTo(window)  # + «Частоты и термохимия» (--hess),
        # скан
        window.program.setCurrentIndex(window.program.findData('orca'))
        app.processEvents()
        assert window.basis_picker.isVisibleTo(window) and window.memory.isVisibleTo(window)
        assert window.calculation().task == 'Оптимизация + частоты'
    finally:
        window.setup_rows.reset()
        window.program.setCurrentIndex(window.program.findData('orca'))


def test_conformer_window_methods_and_their_settings(window, app, monkeypatch):
    # the method in a drop-down list, only its settings shown; the one suggested for the molecule; the defaults
    from modules.compass.chemistry import library
    from modules.compass.actions.conformer_actions import ConformerWindow

    show_model(window, app)
    window.dirty = False
    window.load_molecule(library.molecule(next(k for k in library.keys() if k.startswith('Бутан'))))
    w = window.compass_dialogs.conformers()
    try:
        w.show()
        app.processEvents()
        assert w.objectName() == 'workspace' and w.go_button.objectName() == 'primary'
        assert w.method.currentData() == 'scan' and w.limit.isVisibleTo(w) and not w.mdlen.isVisibleTo(w)
        assert w.limit.value() == 200 and w.abc_confs.value() == 10 and w.energy_window.value() == 6.0
        assert w.mdlen.value() == 2.0  # butane, 14 atoms: CREST would give it the shortest metadynamics
        heights = {}  # the height of each method the same, however it was come to
        for key, shown, hidden in (('abc', w.abc_confs, w.limit), ('crest', w.mdlen, w.abc_confs), ('scan', w.step, w.quick),
                                   ('abc', w.abc_confs, w.limit)):
            w.method.setCurrentIndex(w.method.findData(key))
            app.processEvents()
            assert shown.isVisibleTo(w) and not hidden.isVisibleTo(w)
            # no description under the choice — every method is told behind «?» by it
            assert w.method_note.text() == '?' and all(title in w.method_note.help for _, title, _ in ConformerWindow.METHODS)
            assert w.energy_window.isVisibleTo(w) and w.temperature.isVisibleTo(w)  # shared by all
            # the window fixed to the settings of the method chosen, nothing over anything
            assert w.minimumSize() == w.maximumSize() == w.size()
            heights[key] = w.height()
            pages = w.pages.mapTo(w, w.pages.rect().bottomLeft()).y()
            assert pages <= w.energy_window.mapTo(w, w.energy_window.rect().topLeft()).y()
        assert len(heights) == 3 and heights['abc'] < heights['scan']  # back from «Перебор»: lower at once
        assert [ConformerWindow.suggested_method(n) for n in (0, 4, 5, 10, 11)] == ['scan', 'scan', 'abc', 'abc', 'crest']
        w.refine_auto.setChecked(False)
        w.method.setCurrentIndex(w.method.findData('scan'))  # the loop above ends on ABC
        rows = w.start_search()  # the scan without xtb: the candidates only, «Уточнить в xtb» enabled
        assert len(rows) == 3 and w.refine_button.isEnabled() and w.job is None
        # 2026-11-18 only the columns with something in them — the candidates have
        # their score, no energies yet
        assert not w.table.isColumnHidden(1) and all(w.table.isColumnHidden(j) for j in (2, 3, 4))
        # with «Сразу уточнить» the candidates are
        # kept for xtb, not shown — the table empty, the drawer not opened again for them
        drawer = window.drawer
        loaded = []
        monkeypatch.setattr(window.trajectory_tool, 'load_conformers', lambda *a, **k: loaded.append(a))
        kept = w.search(show=False)
        assert len(kept) == 3 and w.table.rowCount() == 0 and not loaded
        # an open drawer opened again stays where it is (no second slide)
        window.trajectory_tool.set_trajectory_open(True, 'conformers')
        drawer.slide.setCurrentTime(drawer.slide.duration())
        app.processEvents()
        drawer.open_drawer(True)
        assert drawer.slide.state() != drawer.slide.State.Running
    finally:
        w.close()


def test_queue_of_conformers(window, app, tmp_path, monkeypatch):
    # the conformers of the drawer run as a queue with the same settings: the dialog checks those within
    # 3 kcal/mol; the jobs go one after another (a failure does not stop the queue); at the end the table in «Анализ»
    # and the conformers sorted again by the new energies on the page «Конформеры»; a queue left unfinished is offered
    # again («Продолжить очередь»)
    import sys
    import time
    from dataclasses import replace as _replace

    from modules.sextant import batch as batches
    from modules.sextant.batch_actions import OPEN_KEY, BatchDialog

    data = Path(__file__).parents[1] / 'data' / 'xtb' / 'dvb_sp'
    water = window.coordinate_tool.table_molecule()
    x0 = water.atoms[0].x
    fake = tmp_path / 'bin' / 'xtb'
    fake.parent.mkdir()
    # the energy depends on the shift of the first atom: shift 1 is lower than shift 0; shift 2 fails
    fake = program_script(
        fake,
        f'#!{sys.executable}\nimport sys\n'
        f'lines = open(sys.argv[1]).read().splitlines()\nshift = round(float(lines[2].split()[1]) - {x0!r})\n'
        f'if shift == 2:\n    sys.exit(1)\n'
        f'text = open({str(data / "dvb_sp.out")!r}).read()\n'
        f'sys.stdout.write(text.replace("-26.425939358406", "%.12f" % (-26.4 - 0.002 * shift)))\n'
    )
    saved = window.preferences.value('sextant_program')
    monkeypatch.setattr(window.run_tool, 'configured_program', lambda kind: str(fake) if kind == 'xtb' else None)
    monkeypatch.setattr(window.run_tool, 'jobs_root', lambda: tmp_path / 'jobs')

    def shifted(k):
        return _replace(water, atoms=tuple(_replace(a, x=a.x + k) for a in water.atoms))

    try:
        window.navigate(0)
        window.trajectory_tool.load_conformers([(shifted(0), -26.40, 0.0, 0.6), (shifted(1), -26.399, 0.6, 0.3),
                                (shifted(2), -26.39, 6.3, 0.1)], 'CREST')
        window.navigate(1)
        window.program.setCurrentIndex(window.program.findData('xtb'))
        window.task.setCurrentIndex(window.task.findText('Энергия'))
        window.input_tool.refresh_input()
        assert not window.batch_button.isHidden()
        source, rows = window.batch_tool.batch_source()
        assert source == 'CREST' and len(rows) == 3 and rows[2][2] == 6.3
        dialog = BatchDialog(window, source, [(name, delta) for name, _, delta, _, _ in rows])
        assert dialog.count.value() == 2 and dialog.chosen() == [0, 1]  # within 3 kcal/mol
        dialog.count.setValue(3)
        assert dialog.chosen() == [0, 1, 2]
        dialog.deleteLater()
        again = BatchDialog(window, source, [(name, delta) for name, _, delta, _, _ in rows], [0, 2])
        assert again.chosen() == [0, 2]  # «Изменить выбор…» starts from the choice made
        again.deleteLater()
        # the queue chosen is seen in the card of the calculation; «Запустить очередь» starts it
        assert window.batch_banner.isHidden() and window.run_button.text() == 'Запустить расчёт'
        window.batch_tool.set_batch_plan([0, 1, 2])
        assert not window.batch_banner.isHidden() and 'Очередь: 3 из 3 · CREST' in window.batch_banner_text.text()
        assert window.run_button.text() == 'Запустить очередь (3)' and window.batch_button.isChecked()
        window.batch_tool.clear_batch_plan()
        assert window.batch_banner.isHidden() and not window.batch_button.isChecked()
        window.batch_tool.set_batch_plan([0, 1, 2])
        queue = window.run_tool.run_calculation()
        assert queue is window.batch and window.batch_plan is None and window.run_button.text() == 'Идёт очередь…'
        # while it runs, the band tells the queue that runs — not a choice to start again
        assert not window.batch_banner.isHidden() and 'Идёт очередь: 1 из 3' in window.batch_banner_text.text()
        assert window.batch_tool.batch_change_button.isHidden() and window.batch_tool.batch_cancel_button.isHidden()
        assert queue is not None and window.batch is queue and queue.items[0].state == 'running'
        assert window.preferences.value(OPEN_KEY) == str(queue.folder)
        jw = window.job_window
        assert not jw.queue.isHidden() and not jw.skip_button.isHidden() and 'Очередь 1 из 3' in jw.heading.text()
        # while the queue runs, one line each above the list; the stages — their last line in a kept line
        assert jw.compact and not jw.heading.wordWrap() and not jw.status.wordWrap() and jw.stages_title.isHidden()
        assert jw.stages.maximumHeight() == jw.stages.fontMetrics().lineSpacing()
        jw.add_stage('a', 'один')
        jw.add_stage('b', 'два')
        assert 'два' in jw.stages.text() and 'один' not in jw.stages.text() and jw.stages_title.isHidden()
        end = time.monotonic() + 60
        while window.batch is not None:
            assert time.monotonic() < end, 'the queue did not finish'
            window.run_tool.poll_job()
            app.processEvents()
            time.sleep(0.05)
        assert [item.state for item in queue.items] == ['done', 'done', 'failed']
        assert window.batch_banner.isHidden() and window.run_button.text() == 'Запустить расчёт'  # over
        assert not jw.compact and jw.heading.wordWrap()  # over: in full again
        assert queue.items[1].energy == pytest.approx(-26.402)
        assert window.preferences.value(OPEN_KEY) is None and window.resume_batch_button.isHidden()
        # the conformers again, the lowest first: the second one is now the first
        conformers = window.drawer.conformers
        assert len(conformers) == 2 and conformers[0][1] == pytest.approx(-26.402)
        assert conformers[1][2] == pytest.approx(0.002 * batches.HARTREE_KCAL) and 'очередь' in window.drawer.conformer_source
        assert conformers[0][0].atoms[0].x == pytest.approx(x0 + 1)
        table = list((queue.folder / 'Анализ').glob('batch_energies.csv'))
        assert table and 'ошибка' in table[0].read_text(encoding='utf-8-sig')
        assert not jw.compass_button.isHidden() and jw.skip_button.isHidden() and 'закончена' in window.run_status.text()
        assert window.run_tool.go_to_result('compass') == 'compass' and window.drawer.page() == 'conformers'
        # a queue left by closing the program: «Продолжить очередь»
        left = batches.Batch('xtb', queue.calc, [batches.BatchItem('c', shifted(0))], queue.folder.parent / 'left')
        left.folder.mkdir()
        left.save()
        window.preferences.setValue(OPEN_KEY, str(left.folder))
        window.navigate(1)
        window.batch_tool.update_batch_buttons()
        assert not window.resume_batch_button.isHidden()
        # a choice is forgotten when the rows of the drawer change (another search)
        window.batch_tool.set_batch_plan([0, 1])
        window.trajectory_tool.load_conformers([(shifted(0), None, None, None), (shifted(1), None, None, None)], 'xtb')
        window.input_tool.refresh_input()
        assert window.batch_plan is None and window.batch_banner.isHidden()
    finally:
        window.preferences.remove(OPEN_KEY)
        window.program.setCurrentIndex(0)
        if saved is None:
            window.preferences.remove('sextant_program')
        else:
            window.preferences.setValue('sextant_program', saved)


def test_fukui_queue_and_window(window, app, tmp_path, monkeypatch):
    # the task «Функции Фукуи (N, N+1, N−1)» of Sextant (ORCA) makes a queue of three single points of the molecule at
    # its geometry — the anion and the cation doublets; then, for the result N of such a queue, «±» → «Функции Фукуи…»:
    # a fake Multiwfn gives the Hirshfeld charges of each wavefunction (the recorded output of water, its charges
    # changed), f⁺ f⁻ f⁰ Δf go onto the model, the table into «Анализ» of the queue, the window tells the sites
    from PySide6.QtWidgets import QMenu

    from azimuth.core import FUKUI_TASK
    from modules.sextant import batch as batches
    from modules.spectrum.readers.orca_properties import Properties

    started = []
    monkeypatch.setattr(window.batch_tool, '_run_batch', lambda queue: started.append(queue) or queue)
    monkeypatch.setattr(window.run_tool, 'jobs_root', lambda: tmp_path / 'jobs')
    show_model(window, app)
    window.dirty = False
    window.load_molecule(read_xyz(EXAMPLES['Вода · H₂O']))
    window.navigate(1)
    app.processEvents()
    window.program.setCurrentIndex(window.program.findData('gaussian'))
    assert window.task.findText(FUKUI_TASK) < 0  # Gaussian: no file of orbitals for Multiwfn
    window.program.setCurrentIndex(window.program.findData('orca'))
    window.task.setCurrentIndex(window.task.findText(FUKUI_TASK))
    window.task_chosen()
    assert window.calculation().basis == 'def2-SVPD'  # the anion needs diffuse functions
    queue = window.run_tool.run_calculation()
    assert queue is started[0] and queue.purpose == 'fukui' and queue.calc.task == 'Энергия'
    assert [(i.charge, i.multiplicity) for i in queue.items] == [(0, 1), (-1, 2), (1, 2)]
    assert batches.Batch.load(queue.folder).purpose == 'fukui'
    window.task.setCurrentIndex(window.task.findText('Энергия'))
    # the queue done: three job folders with their outputs and Molden files
    data = Path(__file__).parents[1] / 'data' / 'multiwfn'
    recorded = (data / 'pop_water_hirshfeld.txt').read_text(encoding='utf-8')
    charges = {'n': (-0.30463436, 0.15231718, 0.15231718), 'anion': (-0.70, -0.15, -0.15), 'cation': (0.10, 0.45, 0.45)}
    for k, (key, item) in enumerate(zip(('n', 'anion', 'cation'), queue.items)):
        job = queue.folder / f'job{k}'
        job.mkdir()
        item.output, item.state = str(job / 'water.out'), 'done'
        (job / 'water.out').write_text('ORCA', encoding='utf-8')
        (job / 'water.molden.input').write_text(f'[Molden Format]\n{key}\n', encoding='utf-8')
        head, tail = recorded.split('Final atomic charges:')
        for was, now in zip((-0.30463436, 0.15231718, 0.15231718), charges[key]):
            tail = tail.replace(f' {was:.8f}', f' {now:.8f}', 1)
        (tmp_path / f'{key}.txt').write_text(head + 'Final atomic charges:' + tail, encoding='utf-8')
    queue.items[0].energy, queue.items[1].energy, queue.items[2].energy = -76.0, -75.95, -75.55
    queue.save()
    fake = fake_program(tmp_path / 'bin', f'''
key = open('input.molden', encoding='utf-8').read().split()[2]
cat(os.path.join({q(tmp_path)}, key + '.txt'))
''')
    old = window.preferences.value('multiwfn_program', '')
    window.preferences.setValue('multiwfn_program', str(fake))
    water = read_xyz(EXAMPLES['Вода · H₂O'])
    window.result_properties, window.result_source = Properties(geometry=water), 'water.out'
    window.output_path = queue.items[0].output
    window.sibling_molden, window.sibling_gbw = Path(queue.items[0].output).with_name('water.molden.input'), None
    try:
        menu = QMenu()
        window.property_tool.fill_properties_menu(menu)
        assert {a.text(): a for a in leaf_actions(menu)}['Функции Фукуи…'].isEnabled()
        dialog = window.property_tool.show_fukui(window.property_tool.fukui_folder())
        props = window.result_properties
        assert props.charges['fukui+'] == pytest.approx((0.39536564, 0.30231718, 0.30231718))
        assert props.charges['fukui-'] == pytest.approx((0.40463436, 0.29768282, 0.29768282))
        assert sum(props.charges['dual']) == pytest.approx(0, abs=1e-9) and window.overlay_choice['atom'] == 'fukui-plus'
        assert dialog.leaders()['plus'] == 'O1' and dialog.table.rowCount() == 3
        assert 'O1' in dialog.sites.text() and '12.25' in dialog.summary.text()  # IP = 0.45 Eh
        tables = queue.folder / 'Анализ'
        assert (tables / 'fukui_atoms.csv').is_file() and (tables / 'fukui_global.csv').is_file()
        dialog.close()
        window.output_path = str(tmp_path / 'other.out')
        assert window.property_tool.fukui_folder() is None
    finally:
        window.preferences.setValue('multiwfn_program', old)
        window.sibling_molden = None
        window.result_properties = None
        window.output_path = None


def test_cda_queue_and_window(window, app, tmp_path, monkeypatch):
    # the task «Донорно-акцепторная связь CDA» of Sextant (ORCA) — fragment 1 from the atoms
    # selected in Compass, a queue of the complex (fragment 1 first) and the two fragments; then, for the result of the
    # complex, «Связи» → «Донорно-акцепторная связь (CDA)…»: a fake Multiwfn gives the recorded CDA of H3N→BH3 (Multiwfn
    # 2026.7.15, ORCA B3LYP/def2-SVP), the window tells d, b, r, the table goes into «Анализ» of the queue
    import gzip

    from PySide6.QtWidgets import QMenu

    from azimuth.core import CDA_TASK
    from modules.sextant import batch as batches
    from modules.spectrum.readers.orbital_files import read_orbitals
    from modules.spectrum.readers.orca_properties import Properties

    data = Path(__file__).parents[1] / 'data' / 'multiwfn'
    moldens = {part: gzip.decompress((data / f'cda_nh3bh3_{part}.molden.gz').read_bytes()).decode('utf-8')
               for part in ('complex', 'frag1', 'frag2')}
    complex_ = read_orbitals(moldens['complex']).molecule  # N H H H B H H H
    started = []
    monkeypatch.setattr(window.batch_tool, '_run_batch', lambda queue: started.append(queue) or queue)
    monkeypatch.setattr(window.run_tool, 'jobs_root', lambda: tmp_path / 'jobs')
    show_model(window, app)
    window.dirty = False
    # the acceptor written first (B H H H N H H H): the queue puts fragment 1 (NH3) first in the complex
    order = [4, 5, 6, 7, 0, 1, 2, 3]
    window.load_molecule(Molecule('H3NBH3', tuple(complex_.atoms[k] for k in order)))
    window.navigate(1)
    app.processEvents()
    window.program.setCurrentIndex(window.program.findData('gaussian'))
    assert window.task.findText(CDA_TASK) < 0  # Gaussian: no file of orbitals for Multiwfn
    window.program.setCurrentIndex(window.program.findData('orca'))
    window.task.setCurrentIndex(window.task.findText(CDA_TASK))
    window.task_chosen()
    assert window.cda_atoms.isVisibleTo(window) and window.cda_pick.isVisibleTo(window)
    assert 'укажите атомы фрагмента 1' in window.task_note.text()
    window.viewer.selected = [4, 5, 6, 7]
    assert window.cda_from_selection() == 'N5–H8' and window.cda_atoms.text() == 'N5–H8'  # with the elements
    assert 'фрагмент 1 — H3N' in window.task_note.text() and 'фрагмент 2 — BH3' in window.task_note.text()
    queue = window.run_tool.run_calculation()
    assert queue is started[0] and queue.purpose == 'cda' and queue.calc.task == 'Энергия'
    assert [(i.molecule.formula, i.charge, i.multiplicity) for i in queue.items] == [
        ('BH6N', 0, 1), ('H3N', 0, 1), ('BH3', 0, 1)]
    assert [a.symbol for a in queue.items[0].molecule.atoms] == ['N', 'H', 'H', 'H', 'B', 'H', 'H', 'H']
    assert batches.Batch.load(queue.folder).extra == {'fragments': [[4, 5, 6, 7], [0, 1, 2, 3]],
                                                      'order': [4, 5, 6, 7, 0, 1, 2, 3]}
    window.task.setCurrentIndex(window.task.findText('Энергия'))
    # the queue done: three job folders with their outputs and Molden files
    for k, (part, item) in enumerate(zip(('complex', 'frag1', 'frag2'), queue.items)):
        job = queue.folder / f'job{k}'
        job.mkdir()
        item.output, item.state = str(job / f'{part}.out'), 'done'
        (job / f'{part}.out').write_text('ORCA', encoding='utf-8')
        (job / f'{part}.molden.input').write_text(moldens[part], encoding='utf-8')
    queue.save()
    fake = fake_program(tmp_path / 'bin', f'''
assert args[0] == 'complex.molden' and answers(4) == '16 2 frag1.molden frag2.molden', (args, lines)
cat({q(data / 'cda_nh3bh3_menu.txt')})
''')
    old = window.preferences.value('multiwfn_program', '')
    window.preferences.setValue('multiwfn_program', str(fake))
    window.result_properties, window.result_source = Properties(geometry=complex_), 'complex.out'
    window.output_path = queue.items[0].output
    window.sibling_molden, window.sibling_gbw = Path(queue.items[0].output).with_name('complex.molden.input'), None
    try:
        menu = QMenu()
        window.property_tool.fill_properties_menu(menu, 'bonds')
        assert {a.text(): a for a in leaf_actions(menu)}['Донорно-акцепторная связь (CDA)…'].isEnabled()
        dialog = window.property_tool.show_cda(window.property_tool.cda_folder())
        assert dialog.result['sum']['d'] == 0.268420 and dialog.formulas == ('H3N', 'BH3')
        assert '0.268' in dialog.summary.text() and 'почти чистое донирование' in dialog.summary.text()
        assert dialog.table.rowCount() == 10 and dialog.chosen() == 7  # the B–N σ orbital chosen first
        assert dialog.orbital_button.isVisibleTo(dialog)
        tables = queue.folder / 'Анализ'
        assert (tables / 'cda_orbitals.csv').is_file()
        assert any(p.name.endswith('_multiwfn_cda.txt') for p in (queue.folder / 'job0' / 'Анализ').iterdir())
        dialog.close()
        window.output_path = str(tmp_path / 'other.out')
        assert window.property_tool.cda_folder() is None
    finally:
        window.preferences.setValue('multiwfn_program', old)
        window.sibling_molden = None
        window.result_properties = None
        window.output_path = None
        window.cda_atoms.clear()


def test_heavy_elements_advice_and_element_bases(window, app):
    # the user — «А программа автоматически советует базис для каждого атома?» → «Оба делай»: the advice knows
    # the lanthanides (DKH2 with SARC, set with the basis) and the 5d metals; «Базисы по элементам» in the dialog of the
    # advanced settings write NewGTO in ORCA
    show_model(window, app)
    window.load_molecule(Molecule('EuCl2', (Atom('Eu', 0, 0, 0), Atom('Cl', 0, 0, 2.6), Atom('Cl', 0, 0, -2.6))))
    window.navigate(1)
    app.processEvents()
    window.program.setCurrentIndex(window.program.findData('orca'))
    window.spin.setValue(8)
    window.task.setCurrentIndex(window.task.findText('Энергия'))
    found = window.task_chosen()
    assert found.relativistic == 'DKH' and window.relativistic.currentData() == 'DKH'
    assert 'SARC' in found.text
    text = window.preview.toPlainText()
    assert 'DKH-def2-TZVP' in text and 'NewGTO Eu "SARC-DKH-TZVP" end' in text
    window.relativistic.setCurrentIndex(window.relativistic.findData(''))
    window.load_molecule(Molecule('FeCl2', (Atom('Fe', 0, 0, 0), Atom('Cl', 0, 0, 2.1), Atom('Cl', 0, 0, -2.1))))
    window.spin.setValue(5)
    assert window.add_element_basis('Fe', 'def2-TZVP') == 'Fe=def2-TZVP'
    assert window.add_element_basis('Cl', 'def2-SVP') == 'Cl=def2-SVP; Fe=def2-TZVP'
    app.processEvents()
    text = window.preview.toPlainText()
    assert '  NewGTO Fe "def2-TZVP" end\n' in text and window.calculation().basis_of('Fe') == 'def2-TZVP'
    assert window.advanced_count() >= 1


def test_descriptor_window_fits_a_constant(window, app, tmp_path):
    # the data items of an SDF set go with its structures; the window fits a descriptor against a constant
    from modules.sextant import batch
    from modules.sextant.descriptor_view import DescriptorWindow
    from tests.sextant.test_descriptors import SDF, crown

    show_model(window, app)
    window.confirm_replace = lambda: True
    window.opening_tool.hydrogens_on_open = lambda: False
    sdf = tmp_path / 'set.sdf'
    sdf.write_text(SDF.replace('  1  0  0', '  1  0  0'), encoding='utf-8')
    window.opening_tool.open_path(str(sdf))
    document = window.document()
    molecule = window.batch_tool.structure_rows()[1][0]
    assert window.batch_tool.structure_record(document, molecule)[0]['logK_Cs_z=1.0_T=25_I=0.1'] == '1,25'
    items = [batch.BatchItem(f'L{k}', crown(2.9 + 0.1 * k), 1, 1, state='done', energy=-100.0 - 0.01 * k,
                             props={'logK': str(1.0 + 0.5 * k)}) for k in range(4)]
    queue = batch.Batch('orca', window.calculation(), items, tmp_path / 'queue')
    queue.folder.mkdir()
    dialog = DescriptorWindow(window, queue)
    try:
        assert dialog.y_box.currentData() == 'logK'
        result = dialog.choose('E, Eh', 'logK')
        assert result.n == 4 and result.r2 == pytest.approx(1.0)
        written = dialog.save()
        assert {p.name for p in written} == {'descriptors_table.csv', 'descriptors_fit.csv'}
        assert dialog.save_picture(tmp_path / 'fit.png').is_file()
    finally:
        dialog.close()


def test_binding_queue_is_chosen_and_its_inputs_carry_tasks_and_ghosts(window, app, tmp_path):
    # «Комплексы с ионом» in the choice of the queue; the ion is a single point, BSSE marks ghost atoms
    from modules.sextant import batch, binding
    from modules.sextant.batch_actions import BatchDialog
    from tests.sextant.test_binding import formate

    dialog = BatchDialog(window, 'Структуры: 2', [('a', None), ('b', None)], None, {'orca': True}, flat=[1])
    try:
        assert dialog.binding() is None
        dialog.binding_box.setChecked(True)
        dialog.ion.setCurrentIndex(dialog.ion.findData('Cs'))
        dialog.bsse.setChecked(True)
        assert dialog.binding() == {'ion': 'Cs', 'charge': 1, 'bsse': True}
        assert '1' in dialog.flat_note.text()
    finally:
        dialog.close()
    items, extra = binding.plan([('formate', formate(), -1, 1, {}, ())], 'Cs', bsse=True)
    queue = batch.Batch('orca', replace(window.calculation(), task='Оптимизация'), items, tmp_path, purpose='binding',
                        extra=extra)
    calc, text = window.batch_tool.batch_item_input(queue, items[0])
    assert calc.task == 'Энергия' and text is None and calc.charge == 1
    items[1].state, items[1].geometry, items[1].energy = 'done', formate(), -189.0
    window.batch_tool.batch_item_input(queue, items[2])  # the complex is put on the optimized ligand
    items[2].state, items[2].geometry, items[2].energy = 'done', items[2].molecule, -209.0
    added = binding.follow_ups(queue, items[2])
    calc, text = window.batch_tool.batch_item_input(queue, added[1])
    assert calc.task == 'Энергия' and 'Cs : ' in text and '* xyz -1 1' in text


def test_queue_searches_the_best_conformer_first_when_settings_ask(window, app, tmp_path, monkeypatch):
    # «Настройки → Расчёты» — the switch and the method; each structure of a new queue gets its lowest
    # conformer (here the turns of butane with a fake xtb) before its calculation, and the queue keeps the choice
    import time

    from azimuth import defaults
    from modules.sextant.batch_conformers import METHODS
    from tests.fake_programs import fake_program
    from tests.compass.test_batch_conformers import FAKE_XTB, butane

    fake = fake_program(tmp_path / 'bin', FAKE_XTB, name='xtb')
    monkeypatch.setattr(window.run_tool, 'configured_program', lambda kind: str(fake) if kind == 'xtb' else None)
    monkeypatch.setattr(window.run_tool, 'jobs_root', lambda: tmp_path / 'jobs')
    program = window.program.currentData()  # the choice of xtb below must not reach the next tests
    dialog = window.show_settings('jobs')
    try:
        assert not dialog.conformer_switch.isChecked() and not dialog.conformer_method.isEnabled()
        assert dialog.conformer_method.count() == len(METHODS)
        dialog.conformer_switch.setChecked(True)
        dialog.conformer_method.setCurrentIndex(dialog.conformer_method.findData('scan'))
        assert defaults.get('batch_conformers') and defaults.get('batch_conformer_method') == 'scan'
        dialog.close()
        window.confirm_replace = lambda: True
        for name in ('A', 'B'):  # a set is a project
            (tmp_path / f'{name}.xyz').write_text(butane().xyz(), encoding='utf-8')
        window.open_files_project([tmp_path / 'A.xyz', tmp_path / 'B.xyz'])
        window.navigate(1)
        window.program.setCurrentIndex(window.program.findData('xtb'))
        window.task.setCurrentIndex(window.task.findText('Энергия'))
        queue = window.batch_tool.start_batch([0, 1], 'local')
        assert queue.extra['conformers'] == {'method': 'scan'}
        end = time.monotonic() + 90
        while not queue.done() and time.monotonic() < end:
            app.processEvents()
            time.sleep(0.05)
        assert queue.done() and [i.state for i in queue.items] == ['done', 'done']
        assert all('перебор поворотов' in i.props['conformer'] for i in queue.items)
        assert (queue.folder / 'conformers' / '01').is_dir()
    finally:
        defaults.put('batch_conformers', False, window.preferences)
        defaults.put('batch_conformer_method', 'auto', window.preferences)
        window.program.setCurrentIndex(max(0, window.program.findData(program)))


def test_the_next_calculation_of_a_queue_does_not_bring_the_window_up(window, app, tmp_path, monkeypatch):
    # away from Sextant the window of
    # the calculation stays hidden behind the hourglass while the queue goes on; back in Sextant the card follows it
    import time
    from dataclasses import replace as _replace

    from tests.fake_programs import fake_program

    data = Path(__file__).parents[1] / 'data' / 'xtb' / 'dvb_sp'
    water = window.coordinate_tool.table_molecule()
    # a fake xtb that starts on Windows too (a .cmd next to the script; a file with #! does not start there — the first
    # run on Windows)
    fake = fake_program(tmp_path / 'bin', f'import sys, time\ntime.sleep(0.3)\n'
                        f'sys.stdout.write(open({str(data / "dvb_sp.out")!r}).read())', name='xtb')
    monkeypatch.setattr(window.run_tool, 'configured_program', lambda kind: str(fake) if kind == 'xtb' else None)
    monkeypatch.setattr(window.run_tool, 'jobs_root', lambda: tmp_path / 'jobs')
    saved = window.preferences.value('sextant_program')
    try:
        window.navigate(0)
        window.trajectory_tool.load_conformers([(_replace(water, atoms=tuple(_replace(a, x=a.x + k) for a in water.atoms)), -26.4 + k,
                                 0.0, 0.3) for k in range(3)], 'CREST')
        window.navigate(1)
        window.program.setCurrentIndex(window.program.findData('xtb'))
        window.task.setCurrentIndex(window.task.findText('Энергия'))
        window.input_tool.refresh_input()
        window.batch_tool.set_batch_plan([0, 1, 2])
        queue = window.run_tool.run_calculation()
        assert queue is not None and queue.items[0].state == 'running'
        window.navigate(0)
        jw = window.job_window
        jw.park()  # away from Sextant, the window hidden («Скрыть»; offscreen the main window is never «shown», so
        app.processEvents()  # job_follow does not take the card out of it by itself)
        assert not jw.isVisible() and jw.parked
        seen = set()
        end = time.monotonic() + 60
        while window.batch is not None:
            assert time.monotonic() < end, 'the queue did not finish'
            window.run_tool.poll_job()
            app.processEvents()
            seen.add(jw.isVisible())
            time.sleep(0.05)
        assert seen == {False} and [item.state for item in queue.items] == ['done'] * 3
    finally:
        from modules.sextant.batch_actions import OPEN_KEY

        window.preferences.remove(OPEN_KEY)
        window.program.setCurrentIndex(0)
        if saved is None:
            window.preferences.remove('sextant_program')
        else:
            window.preferences.setValue('sextant_program', saved)


def test_the_list_of_a_long_queue_stays_inside_the_card(window, app):
    # the list of 40
    # structures scrolls inside the card, its bottom never below it; the one that runs (after names wrapped onto two
    # lines) is brought into sight
    from types import SimpleNamespace

    states = ['done'] * 30 + ['running'] + ['waiting'] * 9
    items = [SimpleNamespace(name=f'molecule_{k:02d}' + ('_with_a_very_long_name_that_wraps' * (k % 3 == 0)),
                             state=state, energy=None if state != 'done' else -76.4, note='')
             for k, state in enumerate(states)]
    counts = {s: states.count(s) for s in set(states)}
    counts.setdefault('failed', 0)
    queue = SimpleNamespace(items=items, counts=lambda: counts, done=lambda: False)
    jw = window.job_window
    jw.undock()
    jw.begin('Очередь 31 из 40: molecule_30 · xTB', 'Энергия')
    for k in range(6):
        jw.add_stage(f's{k}', f'Стадия {k}')
    jw.show_batch(queue)
    jw.show()
    jw.resize(560, 420)
    for _ in range(5):
        app.processEvents()
    scroll = jw.queue_scroll
    bottom = scroll.mapTo(jw.frame, scroll.rect().bottomLeft()).y()
    assert bottom <= jw.frame.height() and scroll.height() >= 3 * jw.queue.fontMetrics().lineSpacing()
    middle = jw.queue_line_middle(30)
    shown = scroll.verticalScrollBar().value()
    assert shown <= middle <= shown + scroll.viewport().height()
    jw.hide()


def test_a_conformer_search_reports_in_the_window_of_its_place(window):
    # the timer of a search wrote into the window of the place chosen now
    import time
    from types import SimpleNamespace

    window.navigate(1)
    window.run_tool.set_where('local')
    local = window.job_window
    window.run_tool.set_where('server')
    there = window.job_window
    assert local is not there
    before = there.status.text()
    queue = SimpleNamespace(place='local')
    stage = SimpleNamespace(done=False, started=time.monotonic(), step=(2, 5))
    window.batch_tool._conformer_tick(queue, None, stage, None, 'Поиск')  # «Где считать» is the server now
    assert local.status.text().startswith('Поиск · 2 из 5') and there.status.text() == before
    assert window.job_place() == 'server'  # the choice of the user is left as it is
    window.run_tool.set_where('local')


def test_combo_rows_have_their_height_and_a_picker_closes_on_a_second_press(window, app, monkeypatch):
    # the items of «Программа» and «Растворитель» do not overlap; a second press of the method button closes its menu
    from azimuth.ui import ROW_HEIGHT

    window.navigate(1)
    app.processEvents()
    for combo in (window.program, window.task, window.solvent):
        window.style_combo(combo)
        view = combo.view()
        assert all(view.sizeHintForRow(k) >= ROW_HEIGHT for k in range(combo.count()))
        assert all(view.sizeHintForRow(k) >= view.fontMetrics().height() + 12 for k in range(combo.count()))
    picker = window.method_picker
    monkeypatch.setattr(picker, 'underMouse', lambda: True)
    menu = picker.open_menu()
    assert menu is not None
    menu.hide()  # the press on the button closed it …
    assert picker.open_menu() is None  # … and the same press reaching the button does not open it again
    again = picker.open_menu()  # a press of its own opens it
    assert again is not None
    again.hide()


def test_the_doctor_repeats_a_failed_calculation_with_its_remedy(window, app, tmp_path, monkeypatch):
    # a calculation whose SCF did not converge — the window of the calculation offers «Повторить с трудной
    # сходимостью SCF»; one press puts SlowConv into the settings and starts the calculation again (the second run of
    # the fake ORCA, which sees SlowConv in its input, ends normally); the button is offered once
    import time

    real = Path(__file__).parents[1] / 'data' / 'orca601' / 'h2o_energy.out'  # a whole output for the run that works
    orca = tmp_path / 'orca_6' / 'orca'
    orca.parent.mkdir()
    orca = program_script(orca, 'import sys\n'
                          'if "slowconv" in open(sys.argv[1], encoding="utf-8").read().lower():\n'
                          f'    sys.stdout.write(open({str(real)!r}, encoding="utf-8", errors="replace").read())\n'
                          '    sys.exit(0)\n'
                          'print("  SCF NOT CONVERGED AFTER 125 CYCLES")\nsys.exit(1)\n')
    (orca.parent / 'orca_scf').write_text('')
    monkeypatch.setattr(window.run_tool, 'configured_program', lambda kind: str(orca) if kind == 'orca' else None)
    monkeypatch.setattr(window.run_tool, 'jobs_root', lambda: tmp_path / 'jobs')
    saved = window.preferences.value('sextant_program')

    def finished():
        end = time.monotonic() + 15
        while window.run_tool.poll_job() is None:
            assert time.monotonic() < end, 'the fake orca did not finish'
            app.processEvents()
            time.sleep(0.05)

    try:
        show_model(window, app)
        window.navigate(1)
        app.processEvents()
        window.program.setCurrentIndex(window.program.findData('orca'))
        window.cores.setValue(1)
        window.task.setCurrentIndex(max(0, window.task.findData('Энергия')))
        assert window.calculation().slow_conv == ''
        first = window.run_tool.run_calculation()
        assert first is not None
        finished()
        panel = window.job_window
        assert first.code == 1 and 'SCF' in panel.problem.text()
        assert panel.remedy_button.text() == 'Повторить с трудной сходимостью SCF' and not panel.remedy_button.isHidden()
        # Act: one press
        panel.remedy_button.click()
        app.processEvents()
        second = window.job
        assert second is not None and second is not first and window.calculation().slow_conv == 'SlowConv'
        assert 'slowconv' in second.spec.output.with_suffix('.inp').read_text().lower()
        assert first.spec.output.is_file()  # the calculation before stays with its files
        finished()
        assert second.code == 0 and panel.remedy_button.isHidden()  # it ended normally: nothing to offer
        window.job_window.hide()
    finally:
        window.slow_conv.setCurrentIndex(0)
        window.program.setCurrentIndex(0)
        if saved is None:
            window.preferences.remove('sextant_program')
        else:
            window.preferences.setValue('sextant_program', saved)
        window.dirty = False


def test_interaction_energy_of_a_pair_with_bsse(window, app, tmp_path, monkeypatch):
    # a water dimer → the task «Энергия взаимодействия с BSSE» of ORCA: a queue of five single points (the pair,
    # each molecule with the ghosts of the other, each alone); at its end ΔE(CP) in the message
    from azimuth.core import INTERACTION_TASK
    from tests.sextant.test_interaction import water_dimer

    started = []
    monkeypatch.setattr(window.batch_tool, '_run_batch', lambda queue: started.append(queue) or queue)
    monkeypatch.setattr(window.run_tool, 'jobs_root', lambda: tmp_path / 'jobs')
    show_model(window, app)
    window.dirty = False
    window.load_molecule(water_dimer())
    window.navigate(1)
    app.processEvents()
    window.program.setCurrentIndex(window.program.findData('gaussian'))
    assert window.task.findText(INTERACTION_TASK) < 0  # the ghost atoms are written for ORCA only
    window.program.setCurrentIndex(window.program.findData('orca'))
    window.task.setCurrentIndex(window.task.findText(INTERACTION_TASK))
    window.task_chosen()
    assert 'Пять расчётов' in window.task_note.text()
    queue = window.run_tool.run_calculation()
    assert queue is started[0] and queue.purpose == 'interaction' and len(queue.items) == 5
    calc, text = window.batch_tool.batch_item_input(queue, queue.items[1])
    assert calc.task == 'Энергия' and 'O : ' in text
    for item, energy in zip(queue.items, (-152.000, -76.002, -75.990, -76.000, -75.989)):
        item.state, item.energy = 'done', energy
    found = window.batch_tool.interaction_complete(queue)
    assert abs(found['dE_cp'] + 5.02) < 0.01
    window.task.setCurrentIndex(window.task.findText('Энергия'))


def test_the_installation_is_shown_not_the_idle_card(window, app, tmp_path, monkeypatch):
    # the window of the calculation shows the installation — its title — while it runs and after it, not the line of an
    # empty window
    import sys

    from modules.sextant import install_tools

    monkeypatch.setattr(install_tools, 'default_root', lambda: tmp_path)
    fake = tmp_path / 'fake_install.py'
    fake.write_text('print("[tools] done")\n', encoding='utf-8')
    window.navigate(1)
    app.processEvents()
    import modules.sextant.install_actions as ia

    real_job = ia.runner.Job

    class Quick(real_job):
        def __init__(self, spec):
            spec = ia.runner.JobSpec(spec.kind, spec.folder, (sys.executable, str(fake)), spec.output, spec.env, spec.stdout)
            super().__init__(spec)

    monkeypatch.setattr(ia.runner, 'Job', Quick)
    job = window.install_tool.start_install(('xtb',))
    assert job is not None
    assert 'Расчёта ещё не было' not in window.job_window.status.text()
    assert window.job_window.heading.text() == 'Установка программ для расчёта'
    import time

    deadline = time.monotonic() + 10
    while window.install_job is not None and time.monotonic() < deadline:
        time.sleep(0.05)
        window.install_tool.poll_install()
    window.show_job_window()  # opened again after it: still the installation
    assert 'Расчёта ещё не было' not in window.job_window.status.text()
    # «Вывод программы» after it shows its log (it answered «Вывода ещё нет» after a failed one, Windows 2026-11-24)
    assert window.install_tool.last is job
    shown = window.run_tool.open_output()
    assert shown is not None and any(str(p).endswith('install.log') for p in shown.paths)
    shown.timer.stop()
    shown.close()


def test_a_row_of_buttons_goes_on_to_the_next_row(app):
    # the five buttons of the crystal page after a CP2K run were one row
    # wider than the card, and the column of the settings was pressed narrow — azimuth.ui.flow_layout wraps them
    from PySide6.QtWidgets import QPushButton, QWidget

    from azimuth.ui import flow_layout

    holder = QWidget()
    flow = flow_layout(8)
    holder.setLayout(flow)
    buttons = [QPushButton('Кнопка с длинной надписью номер %d' % k) for k in range(5)]
    for b in buttons:
        flow.addWidget(b)
    widest = max(b.sizeHint().width() for b in buttons)
    one_row = buttons[0].sizeHint().height()
    assert flow.minimumSize().width() < 2 * widest  # no longer the sum of the five
    assert flow.heightForWidth(10 * widest) == one_row
    assert flow.heightForWidth(widest + 10) == 5 * one_row + 4 * 8
    buttons[4].hide()  # a hidden button takes no place
    assert flow.heightForWidth(widest + 10) == 4 * one_row + 3 * 8


def test_a_separator_of_a_list_is_a_thin_line(app):
    from PySide6.QtWidgets import QComboBox, QStyleOptionViewItem

    from azimuth.ui import thin_separators

    combo = QComboBox()
    combo.addItem('ORCA', 'orca')
    combo.insertSeparator(1)
    combo.addItem('Quantum ESPRESSO', 'qe')
    delegate = thin_separators(combo)
    assert thin_separators(combo) is delegate  # once
    model = combo.model()
    option = QStyleOptionViewItem()
    assert delegate.sizeHint(option, model.index(1, 0)).height() == 9
    assert delegate.sizeHint(option, model.index(0, 0)).height() > 9


def test_descriptor_window_says_there_is_nothing_to_fit(window, app, tmp_path):
    # a note instead of the plot, the window no taller than the screen
    from modules.sextant import batch
    from modules.sextant.descriptor_view import DescriptorWindow
    from tests.sextant.test_descriptors import crown

    items = [batch.BatchItem(f'L{k}', crown(2.9 + 0.1 * k), 1, 1, state='done', energy=-100.0 - 0.01 * k)
             for k in range(2)]
    queue = batch.Batch('orca', window.calculation(), items, tmp_path / 'queue')
    queue.folder.mkdir()
    dialog = DescriptorWindow(window, queue)
    try:
        assert dialog.plot.isHidden() and dialog.choice_row.isHidden() and not dialog.picture_button.isEnabled()
        assert 'SDF' in dialog.summary.text()
        room = dialog.screen().availableGeometry()
        assert dialog.height() <= room.height() and dialog.width() <= room.width()
    finally:
        dialog.close()


def test_one_blue_button_and_the_gold_of_the_next_step(window, app):
    # one blue main action on a card or a window, «Закрыть» white, a switch that is on light blue, the gold frame of the
    # next step
    import azimuth.app as styles
    from modules.sextant.job_window import gold_star

    card = window.job_window
    card.show_results(compass=True, spectrum=True)
    assert card.spectrum_button.objectName() == 'primary' and card.spectrum_button.property('next')
    assert card.compass_button.objectName() == '' and not card.compass_button.property('next')
    card.show_results(compass=True, spectrum=False)
    assert card.compass_button.objectName() == 'primary' and card.compass_button.property('next')
    assert 'QPushButton#primary[next="true"] {border: 2px solid #e2bf78;}' in styles.STYLE  # lighter still
    assert 'QPushButton:checked, QPushButton[on="true"] {background: #e4ecf8;' in styles.STYLE
    assert not gold_star().isNull()


def test_the_buttons_of_the_result_are_named_by_the_section_shown(window, app):
    card = window.job_window
    card.show_results(compass=True, spectrum=True)
    words = {}
    for index in (0, 1, 2):
        window.stack.setCurrentIndex(index)
        words[index] = (card.compass_button.text(), card.spectrum_button.text())
    assert words[0] == ('Открыть', 'Открыть в Спектре')
    assert words[1] == ('Открыть в Компасе', 'Открыть в Спектре')
    assert words[2] == ('Открыть в Компасе', 'Открыть')
    window.stack.setCurrentIndex(1)


def test_a_structure_with_errors_is_asked_about_before_the_calculation(window, monkeypatch):
    # atoms on top of each other — «Всё равно
    # запустить?»; a good structure goes on without a question
    from PySide6.QtWidgets import QMessageBox

    from azimuth.core import read_xyz

    asked = []
    answer = [QMessageBox.StandardButton.No]
    monkeypatch.setattr(QMessageBox, 'question', lambda *a, **k: (asked.append(a[2]), answer[0])[1])
    window.load_molecule(read_xyz('3\nwater\nO 0 0 0.117\nH 0.757 0 -0.469\nH -0.757 0 -0.469\n'), record=False)
    window.charge.setValue(0)
    window.spin.setValue(1)
    assert window.run_tool.structure_ready() and asked == []
    window.load_molecule(read_xyz('4\nx\nO 0 0 0.117\nH 0.757 0 -0.469\nH -0.757 0 -0.469\nH 0.757 0 -0.169\n'),  # 0.3 Å from an H: read_xyz takes it (≥ 0.1 Å)
                         record=False)
    window.spin.setValue(2)
    assert not window.run_tool.structure_ready() and 'слишком близко' in asked[-1]
    answer[0] = QMessageBox.StandardButton.Yes
    assert window.run_tool.structure_ready()


def test_a_chain_of_calculations_runs_its_steps_on_the_geometry_before(window, app, tmp_path, monkeypatch):
    # 2026-11-21 («Расчёт → Цепочка расчётов»): an optimization with frequencies, then the energy with a larger basis
    # at the geometry it gave — one queue; the second step takes the final geometry of the first (the fake ORCA prints
    # the optimization of divinylbenzene, so the water of the tab becomes C10H10 there), its basis the larger one
    import time

    from modules.sextant import chain

    data = Path(__file__).parents[1] / 'data' / 'orca_cclib' / 'dvb_gopt_orca6.0.out'
    orca = tmp_path / 'orca_6' / 'orca'
    orca.parent.mkdir()
    orca = program_script(orca, f'import sys\nsys.stdout.write(open({str(data)!r}, encoding="utf-8").read())\n')
    (orca.parent / 'orca_scf').write_text('')
    monkeypatch.setattr(window.run_tool, 'configured_program', lambda kind: str(orca) if kind == 'orca' else None)
    monkeypatch.setattr(window.run_tool, 'jobs_root', lambda: tmp_path / 'jobs')
    saved = window.preferences.value('sextant_program')
    try:
        window.navigate(1)
        window.program.setCurrentIndex(window.program.findData('orca'))
        window.cores.setValue(1)
        basis = window.calculation().basis
        # a file edited by hand does not go into the chain — asked first;
        # «Отмена» starts nothing, «Запустить по настройкам» starts the steps made by the settings
        from PySide6.QtWidgets import QMessageBox

        asked = []
        reply = [QMessageBox.StandardButton.Cancel]
        monkeypatch.setattr(QMessageBox, 'question', lambda *a, **k: asked.append(a[2]) or reply[0])
        monkeypatch.setattr(window.input_tool, 'edited_input', lambda: '! my own line')
        assert window.batch_tool.start_chain('big', 'local') is None and 'шаги цепочки' in asked[-1]
        reply[0] = QMessageBox.StandardButton.Yes
        queue = window.batch_tool.start_chain('big', 'local')
        monkeypatch.undo()
        monkeypatch.setattr(window.run_tool, 'configured_program', lambda kind: str(orca) if kind == 'orca' else None)
        monkeypatch.setattr(window.run_tool, 'jobs_root', lambda: tmp_path / 'jobs')
        assert queue is not None and queue.purpose == 'chain'
        assert [i.props['task'] for i in queue.items] == ['Оптимизация + частоты', 'Энергия']
        end = time.monotonic() + 90
        while not queue.done() and time.monotonic() < end:
            app.processEvents()
            time.sleep(0.05)
        assert [i.state for i in queue.items] == ['done', 'done']
        assert queue.items[0].geometry is not None and queue.items[1].molecule.formula == 'C10H10'
        calc, _ = window.batch_tool.batch_item_input(queue, queue.items[1])
        assert calc.task == 'Энергия' and calc.basis == chain.larger_basis(basis)
        while 'Цепочка закончена' not in window.run_status.text() and time.monotonic() < end:  # the end comes 0.3 s
            app.processEvents()  # after the last step (batch_job_finished → start_next_batch_item → batch_complete)
            time.sleep(0.05)
        assert 'Цепочка закончена' in window.run_status.text()
    finally:
        if saved is not None:
            window.preferences.setValue('sextant_program', saved)


def test_the_keys_of_the_run(window):
    # Ctrl+Enter starts the calculation, Ctrl+. stops it — on the page of Sextant, as its buttons allow
    from PySide6.QtGui import QKeySequence

    keys = {s.key().toString() for s in window.run_shortcuts}
    assert {QKeySequence('Ctrl+Return').toString(), QKeySequence('Ctrl+.').toString()} <= keys
    window.run_button.setEnabled(False)
    try:
        assert window.run_by_key() is False  # the button cannot be pressed: the keys do nothing either
    finally:
        window.run_button.setEnabled(True)
    window.stop_button.setEnabled(False)
    assert window.stop_by_key() is False


def test_a_chain_chosen_in_the_list_of_tasks(window, app, monkeypatch):
    # a chain in «Задача» shows its steps under it; the first is the form's, the second has its own method and basis
    # (following the form until chosen by hand); «Запустить расчёт» starts the chain with them
    from modules.sextant.chain_steps import CHAIN_ROLE

    saved = window.preferences.value('sextant_program')
    started = []
    monkeypatch.setattr(window.batch_tool, '_run_batch', lambda queue: started.append(queue) or queue)
    try:
        window.navigate(1)
        window.program.setCurrentIndex(window.program.findData('orca'))
        app.processEvents()
        assert not window.main_form.isRowVisible(window.chain_steps)
        window.task.setCurrentIndex(window.task.findData('uv', CHAIN_ROLE))
        assert window.calculation().task == 'Оптимизация + частоты'  # the form and the input: of the first step
        assert window.main_form.isRowVisible(window.chain_steps) and len(window.chain_steps.rows) == 2
        rows = window.chain_steps.table()
        assert rows[1][0] == 'Спектр UV-Vis (TD-DFT)' and rows[1][1:] == rows[0][1:]  # follows the form
        window.basis.setCurrentIndex(window.basis.findData('def2-TZVP'))
        assert window.chain_steps.table()[1][2] == 'def2-TZVP'
        method = window.chain_steps.rows[1][1]
        method.setCurrentIndex(method.findData('CAM-B3LYP'))
        method.activated.emit(method.currentIndex())  # chosen by hand: it stays
        window.basis.setCurrentIndex(window.basis.findData('def2-SVP'))
        assert window.chain_steps.table()[1][1:] == ('CAM-B3LYP', 'def2-SVP')
        queue = window.run_tool.run_calculation()
        assert started and queue is started[-1] and queue.purpose == 'chain'
        assert queue.items[1].props['calc'] == {'method': 'CAM-B3LYP'} and 'CAM-B3LYP/def2-SVP' in queue.items[1].name
        window.task.setCurrentIndex(window.task.findText('Энергия'))
        assert not window.main_form.isRowVisible(window.chain_steps)
    finally:
        window.task.setCurrentIndex(window.task.findText('Оптимизация + частоты'))
        if saved is not None:
            window.preferences.setValue('sextant_program', saved)


def test_the_setup_fits_its_column_for_every_task(window, app):
    # «Постановка задачи» has a column of at most 500 px: a list as wide as its longest item («Цепочка: Оптимизация +
    # частоты → энергия в большем базисе», 460 px) made the card 648 px and the edge of the column cut every field on
    # the right — on a window of 1133 points, as on the screen of the owner
    window.resize(1133, 730)
    window.show()
    window.navigate(1)
    scroll = window.setup_scroll
    column = scroll.parentWidget()
    for k in range(window.task.count()):
        window.task.setCurrentIndex(k)
        app.processEvents()
        need = scroll.widget().minimumSizeHint().width()
        assert need <= column.maximumWidth(), (window.task.itemText(k), need)
        assert scroll.widget().width() >= need, window.task.itemText(k)  # nothing cut on the right
        assert column.maximumWidth() <= max(500, need)  # no wider than wished, or than the fields need
    window.task.setCurrentIndex(0)
    app.processEvents()
    assert column.maximumWidth() == 500  # «Энергия» fits: the column narrow again
    # the card of the setup is as white as the card of the molecule: the style of its scroll area made it see through
    # to the grey of the window (0.222.4)
    setup, molecule = scroll.widget(), window.calc_card
    a = setup.grab().toImage().pixelColor(setup.width() // 2, 10)
    b = molecule.grab().toImage().pixelColor(molecule.width() // 2, 10)
    assert (a.red(), a.green(), a.blue()) == (b.red(), b.green(), b.blue())


def test_the_setup_fits_the_window_of_a_laptop_for_every_task(window, app):
    # the owner, 0.222.0: «убери прокрутку постановки задачи. Все должно влезать» — no scroll bar, and with the
    # fields of the card by default every task of every program fits the window of 1133 × 730 points
    from PySide6.QtCore import Qt

    from modules.sextant.setup_rows import DEFAULT_OUTSIDE

    window.resize(1133, 730)
    window.show()
    window.navigate(1)
    window.setup_rows.reset()
    scroll = window.setup_scroll
    assert scroll.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert window.setup_rows.outside() == set(DEFAULT_OUTSIDE)
    for p in range(window.program.count()):
        window.program.setCurrentIndex(p)
        for k in range(window.task.count()):
            if not window.task.itemText(k):
                continue  # the line before the chains
            window.task.setCurrentIndex(k)
            app.processEvents()
            need = scroll.widget().minimumSizeHint().height()
            assert need <= scroll.height(), (window.program.currentText(), window.task.itemText(k), need, scroll.height())
            assert window.height() <= 730 + 1, (window.program.currentText(), window.task.itemText(k), window.height())
    window.program.setCurrentIndex(0)


def test_the_fields_of_the_setup_move_between_the_card_and_the_dialog(window, app):
    from azimuth.i18n import set_combo_key
    from modules.sextant import setup_rows as sr

    rows = window.setup_rows
    rows.reset()
    window.navigate(1)
    window.program.setCurrentIndex(window.program.findData('orca'))
    set_combo_key(window.task, 'Оптимизация + частоты')
    app.processEvents()
    card, inside = window.main_form, window.options_dialog.forms[-1]
    assert rows.form_of(window.calc_title) is inside and rows.form_of(window.calc_hessian) is inside  # rarer: inside
    assert rows.form_of(window.dispersion) is inside
    assert rows.form_of(window.solvent_widget) is card and rows.form_of(window.ts) is card
    assert rows.form_of(window.program) is card and rows.form_of(window.method_picker) is card
    assert window.options_dialog.groups[-1][0] == 'Задача'
    # outside again, in its place in the card: after the basis, before the resources
    rows.toggle('dispersion', True)
    assert rows.form_of(window.dispersion) is card
    order = [card.itemAt(r, card.ItemRole.FieldRole).widget() for r in range(card.rowCount())
             if card.itemAt(r, card.ItemRole.FieldRole) is not None]
    assert order.index(window.basis_picker) < order.index(window.dispersion) < order.index(window.resources_widget)
    assert window.preferences.value(sr.KEY) is not None and 'dispersion' in rows.saved()
    # a program without the field hides it wherever it stands, and shows it again
    rows.toggle('dispersion', False)
    window.program.setCurrentIndex(window.program.findData('xtb'))
    assert not rows.visible(window.dispersion) and window.dispersion.isHidden()
    window.program.setCurrentIndex(window.program.findData('orca'))
    assert rows.visible(window.dispersion) and not window.dispersion.isHidden()
    # the rows of the task: inside, the heading of the task follows what is left in the card
    set_combo_key(window.task, 'Оптимизация + частоты')
    rows.toggle('ts', False)
    assert rows.form_of(window.ts) is inside
    shown = window.update_task_box()
    assert 'ts' in shown and not window.ts.isHidden()
    assert window.task_box.isHidden()  # no row of the task in the card: no heading
    rows.toggle('opt_conv', True)
    assert not window.task_box.isHidden()
    # «Поля…»: an item per movable field, checked when it stands outside
    menu = rows.menu()
    items = [a for a in menu.actions() if a.isCheckable()]
    assert [a.data() for a in items] == list(sr.MOVABLE)
    assert {a.data() for a in items if a.isChecked()} == rows.outside()
    rows.reset()
    assert rows.outside() == set(sr.DEFAULT_OUTSIDE) and rows.form_of(window.ts) is card



def test_what_is_outside_the_beta_is_marked(window, app):
    # AGENTS.md §0: Gaussian and GAMESS (inputs never run) say «не проверено» in the list, with the reason in the tip;
    # the programs of the beta do not
    from PySide6.QtCore import Qt

    from modules.sextant import inputs

    for key in ('gaussian', 'gamess'):
        k = window.program.findData(key)
        assert window.program.itemText(k).endswith('· не проверено')
        assert window.program.itemData(k, Qt.ItemDataRole.ToolTipRole) == inputs.UNVERIFIED[key]
    for key in ('orca', 'xtb', 'mopac', 'psi4', 'nwchem'):
        k = window.program.findData(key)
        assert 'не проверено' not in window.program.itemText(k) and key not in inputs.UNVERIFIED


def test_a_new_window_starts_with_d3bj(window, app):
    # the defaults of teaching (docs/plans/BETA_PLAN.md): B3LYP/def2-SVP with D3(BJ) — «! B3LYP D3BJ def2-SVP …»;
    # a method without parameters for it switches it off, and the choice comes back with B3LYP
    from azimuth.core import DEFAULT_DISPERSION

    assert DEFAULT_DISPERSION == 'D3BJ' and window.dispersion.currentData() == 'D3BJ'
    calc = window.calculation()
    assert (calc.method, calc.basis, calc.dispersion) == ('B3LYP', 'def2-SVP', 'D3BJ')
    window.method.setCurrentIndex(window.method.findData('HF'))
    app.processEvents()
    assert window.calculation().dispersion == ''
    window.method.setCurrentIndex(window.method.findData('B3LYP'))
    app.processEvents()
    assert window.calculation().dispersion == 'D3BJ'


def test_the_server_dialog_keeps_the_lines_of_each_program(window, app):
    # «Строки окружения для»: «Все программы» — the lines of every job; a program — the lines of its jobs only. The
    # field shows the lines of the one chosen, those of the others are kept; «·» marks who has lines
    from modules.sextant import remote
    from modules.sextant.server_dialog import ServerDialog

    cp2k = 'module load cp2k\nsource /opt/cp2k/tools/toolchain/install/setup'
    profile = remote.ServerProfile('serv3', '192.0.2.103', 22, 'user', setup='export PATH=/opt/mopac/bin:$PATH',
                                   setups={'cp2k': cp2k})
    dialog = ServerDialog(profile, window)
    try:
        box = dialog.setup_program
        assert [box.itemData(k) for k in range(box.count())] == ['', 'orca', 'mopac', 'qe', 'cp2k']
        assert [box.itemText(k) for k in range(box.count())] == ['Все программы ·', 'ORCA', 'MOPAC', 'Quantum ESPRESSO', 'CP2K ·']
        assert dialog.setup.toPlainText() == profile.setup and dialog.profile() == profile
        box.setCurrentIndex(box.findData('cp2k'))
        assert dialog.setup.toPlainText() == cp2k and 'Перед CP2K в задаче' in dialog.preview.text()
        assert 'source /opt/cp2k' in dialog.preview.text()
        box.setCurrentIndex(box.findData('orca'))
        assert dialog.setup.toPlainText() == '' and 'ORCA найдётся на сервере сама' in dialog.setup.placeholderText()
        dialog.setup.setPlainText('module load orca-6.1.1')
        box.setCurrentIndex(0)  # back to the common lines: what was typed for ORCA is kept
        assert dialog.setup.toPlainText() == profile.setup and box.itemText(1) == 'ORCA ·'
        kept = dialog.profile()
        assert kept.setup == profile.setup and kept.setups == {'orca': 'module load orca-6.1.1', 'cp2k': cp2k}
        box.setCurrentIndex(box.findData('cp2k'))
        dialog.setup.setPlainText('')  # emptied: no lines of CP2K, it is looked for on the server again
        assert dialog.profile().setups == {'orca': 'module load orca-6.1.1'}
        dialog.fill(remote.ServerProfile('other', 'h', 22, 'u'))  # another profile: nothing of this one is left
        assert dialog.profile().setups == {} and dialog.profile().setup == ''
    finally:
        dialog.close()
        dialog.deleteLater()


def test_the_button_of_the_server_settings_opens_them(window, app):
    # the button itself, not the method: clicked(bool) of a plain button is False, and given to toggle_settings as
    # «shown» it hid the hidden panel — «кнопка … ничего не открывает». And the window of the login is narrow: its
    # width is not set by a row of six buttons («по ширине … уже», «еще уже»)
    import time

    from modules.sextant import remote
    from modules.sextant.server_dialog import ServerDialog

    dialog = ServerDialog(remote.ServerProfile('serv3', '192.0.2.103', 22, 'user'), window)
    try:
        dialog.show()
        narrow = dialog.width()
        assert narrow <= 500 and dialog.settings_button.text() == 'Настройки сервера'
        dialog.settings_button.click()
        end = time.monotonic() + 3
        while dialog.width() < narrow + 300 and time.monotonic() < end:
            QTest.qWait(30)
        assert dialog.settings_shown() and dialog.width() > narrow + 300
        assert dialog.settings_button.text() == 'Скрыть настройки сервера' and dialog.height() <= 730
        dialog.settings_button.click()
        end = time.monotonic() + 3
        while dialog.settings_shown() and time.monotonic() < end:
            QTest.qWait(30)
        assert not dialog.settings_shown() and dialog.width() == narrow
        # the buttons of the login stand in its card, «Узнать ресурсы» under them
        for item in (dialog.check_button, dialog.key_button, dialog.probe_button):
            assert dialog.login_card.isAncestorOf(item)
    finally:
        dialog.close()
        dialog.deleteLater()


def test_the_card_of_the_molecule_is_no_taller_than_its_rows(window, app):
    # «под методом и задачей много пустого места — его могла бы занять более высокая панель входного файла»: on a
    # large window the card took the height of its size hint, which counts the wrapped lines as if it were narrow. The
    # oracle: the height its layout needs at the width it has; the input file gets the rest
    window.show()
    window.navigate(1)
    for size in ((1728, 1050), (1440, 900)):
        window.resize(*size)
        QTest.qWait(200)
        card = window.calc_card
        need = max(card.layout().heightForWidth(card.width()), card.minimumSizeHint().height())
        assert card.height() <= need and card.maximumHeight() == need
        assert card.sizeHint().height() > need  # what the layout would have given it
        # the input file is the taller of the two (the card is taller where no program is found: its lines of
        # installation — the machines of GitHub)
        assert window.preview_card.height() > card.height()


def test_the_server_settings_are_as_wide_as_the_login_and_say_nothing_twice(window, app):
    # «окно настройки сервера при раскрытии … одной ширины … лишние фразы … убери»: the panel is as wide as the card
    # of the login, the lines «Вход: … / Перед ORCA в задаче: …» are not shown (they are the tip of the field)
    import time

    from modules.sextant import remote
    from modules.sextant.server_dialog import ServerDialog

    dialog = ServerDialog(remote.ServerProfile('serv1', '192.0.2.101', 10002, 'user'), window)
    try:
        dialog.show()
        app.processEvents()
        tall, top = dialog.height(), dialog.name.mapTo(dialog, dialog.name.rect().topLeft()).y()
        dialog.toggle_settings(True)
        end = time.monotonic() + 3
        while dialog.settings_panel.width() < dialog.settings_panel_target() and time.monotonic() < end:
            app.processEvents()
        app.processEvents()
        # «немного смещается по высоте»: the settings out — the window is as tall as before, the fields of the login
        # stand where they stood, and the title of the card of the calculations is level with «Вход»
        from PySide6.QtWidgets import QLabel

        assert dialog.height() == tall and dialog.name.mapTo(dialog, dialog.name.rect().topLeft()).y() == top
        titles = {t.text(): t.mapTo(dialog, t.rect().topLeft()).y() for t in dialog.findChildren(QLabel)
                  if t.text() in ('Вход', 'Расчёты на сервере')}
        assert len(titles) == 2 and abs(titles['Вход'] - titles['Расчёты на сервере']) <= 2, titles
        assert dialog.settings_panel.width() == dialog.login_card.width(), (dialog.settings_panel.width(), dialog.login_card.width())
        assert dialog.width() < 1000 and dialog.preview.isHidden()
        assert 'user@192.0.2.101:10002' in dialog.setup.toolTip()
        # nothing lies over anything: the rows of the card of the calculations stand one under another
        tops = [w.mapTo(dialog, w.rect().topLeft()).y() for w in (dialog.folder, dialog.setup_program, dialog.setup, dialog.partition, dialog.account)]
        bottoms = [w.mapTo(dialog, w.rect().bottomLeft()).y() for w in (dialog.folder, dialog.setup_program, dialog.setup, dialog.partition)]
        assert all(top > bottom for top, bottom in zip(tops[1:], bottoms)), (tops, bottoms)
    finally:
        dialog.close()
        dialog.deleteLater()


def test_the_resources_fill_the_lines_of_a_program_found_outside_path(window, app, monkeypatch):
    # «Заполни окружение»: MOPAC found only in an environment of conda gets its line written (the next sending does
    # not search the folders), the lines the user wrote are kept, and what was found outside PATH is said (xtb, CREST)
    from modules.sextant import cluster, remote, server_access
    from modules.sextant.server_dialog import ServerDialog

    resources = cluster.parse_probe('@nproc 20\n@lscpu Core(s) per socket: 10\n@lscpu Socket(s): 2\n@orca /opt/orca/orca\n'
                                    '@prog orca /opt/orca/orca\n@found /opt/anaconda3/envs/mopac/bin/mopac\n'
                                    '@found /home/user/xtb/bin/xtb\n@found /opt/cp2k/exe/local/cp2k.psmp\n@load 3.2\n')
    asked = {}

    def opened(parent, profile, **options):
        asked.update(options)
        return None, resources

    monkeypatch.setattr(server_access, 'open_server', opened)
    profile = remote.ServerProfile('serv1', '192.0.2.101', 10002, 'user', '~/calc', setups={'cp2k': 'module load cp2k'})
    dialog = ServerDialog(profile, window)
    try:
        assert dialog.probe() is resources and asked['search'] is True
        kept = dialog.profile()
        assert kept.setups == {'mopac': 'export PATH=/opt/anaconda3/envs/mopac/bin:$PATH', 'cp2k': 'module load cp2k'}
        status = dialog.status.text()
        assert 'свободно 13 из 20 ядер' in status and 'nohup' in status  # 16 may be busy, 3 are
        assert 'Строки окружения вписаны: MOPAC' in status and 'xtb — /home/user/xtb/bin/xtb' in status
        assert dialog.probe_button.isEnabled()
        # a long answer (eight lines) makes the window taller, it does not squeeze the fields of the login over each
        # other (the owner's screenshot, 2026-11-23); the copies in the package cache of conda are not listed
        dialog.show()
        app.processEvents()
        before = dialog.height()
        many = ''.join(f'@found /opt/anaconda3/envs/env{k}/bin/xtb\n@found /opt/anaconda3/pkgs/xtb-6.{k}/bin/xtb\n' for k in range(9))
        resources = cluster.parse_probe('@nproc 48\n@orca /opt/orca/orca\n@prog orca /opt/orca/orca\n' + many)
        assert cluster.found_programs(resources) == [('xtb', '/opt/anaconda3/envs/env0/bin/xtb')]
        dialog.status.setText('\n'.join(f'строка ответа сервера {k}: ' + 'путь/' * 12 for k in range(8)))
        app.processEvents()
        assert dialog.height() > before
        fields = (dialog.name, dialog.host, dialog.port, dialog.user, dialog.password)
        tops = [w.mapTo(dialog, w.rect().topLeft()).y() for w in fields]
        bottoms = [w.mapTo(dialog, w.rect().bottomLeft()).y() for w in fields]
        assert all(top >= bottom for top, bottom in zip(tops[1:], bottoms)), (tops, bottoms)
    finally:
        dialog.close()
        dialog.deleteLater()


def test_the_vpn_is_waited_for_without_holding_the_window(window, app, tmp_path, monkeypatch):
    # «при попытке включения openvpn окно зависает»: a server that does not answer and has a VPN — OpenVPN Connect is
    # asked, the answer is waited for by the timer (no waiting that holds the clicks), then what was asked is done
    import os
    import sys
    import time

    import pytest

    from modules.sextant import remote, server_access, vpn
    from modules.sextant.server_dialog import ServerDialog
    from tests.fake_programs import program_script

    if os.name == 'nt':
        pytest.skip('the fake OpenVPN Connect is a POSIX script')
    fake = program_script(tmp_path / 'OpenVPN Connect', f'#!{sys.executable}\nprint("[]")\n')
    up = {'now': False}
    monkeypatch.setattr(vpn, 'reachable', lambda host, port, timeout=2.0: up['now'])
    calls = []
    monkeypatch.setattr(server_access, 'open_server', lambda parent, profile, **options: calls.append(options) or None)
    profile = remote.ServerProfile('serv1', '192.0.2.101', 10002, 'user', '~/calc', vpn_id='17', vpn_name='lab')
    dialog = ServerDialog(profile, window, connect_app=fake)
    try:
        dialog.vpn.addItem('lab', '17')
        dialog.vpn.setCurrentIndex(dialog.vpn.findData('17'))
        assert dialog.probe() is None and dialog.timer.isActive() and not calls  # the server was not asked yet
        assert dialog.probe_button.isEnabled() and 'Подключаю VPN' in dialog.status.text()
        up['now'] = True
        end = time.monotonic() + 5
        while not calls and time.monotonic() < end:
            dialog._wait_step()
            app.processEvents()
            time.sleep(0.02)
        assert calls and calls[0]['search'] is True and not dialog.timer.isActive()  # «Узнать ресурсы» went on by itself
    finally:
        dialog.timer.stop()
        dialog.close()
        dialog.deleteLater()


def test_the_server_is_offered_only_for_the_programs_it_runs(window):
    # ROADMAP, Sextant 1 («честно показывать в интерфейсе, что где считается»): a server runs ORCA and MOPAC; for
    # the others «Сервер» says so (its tip; pressed — the status line, the place stays this computer) — the error
    # came only after «Запустить расчёт», and a button switched off said nothing (the owner's Windows, 2026-11-28)
    from modules.sextant import remote

    saved = {key: window.preferences.value(key) for key in (remote.WHERE_KEY, 'sextant_program')}
    try:
        window.navigate(1)
        window.program.setCurrentIndex(window.program.findData('orca'))
        window.run_tool.set_where('server')
        server = window.where_buttons['server']
        assert window.where == 'server' and server.isEnabled()
        window.program.setCurrentIndex(window.program.findData('gaussian'))
        assert window.where == 'local' and server.isEnabled() and 'Gaussian' in server.toolTip()
        assert 'Сервер' not in window.program_missing_text.text()
        server.click()  # pressed: stays here, and the status line tells why
        assert window.where == 'local' and window.where_buttons['local'].isChecked()
        assert 'ORCA и MOPAC' in window.run_status.text() and 'Gaussian' in window.run_status.text()
        window.program.setCurrentIndex(window.program.findData('mopac'))
        assert server.isEnabled() and 'Сервер…' in server.toolTip()
    finally:
        window.program.setCurrentIndex(window.program.findData('orca'))
        window.run_tool.set_where('local')
        for key, value in saved.items():
            if value is None:
                window.preferences.remove(key)
            else:
                window.preferences.setValue(key, value)
