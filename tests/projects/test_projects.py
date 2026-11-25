"""Portable projects: byte-preserving import, stable membership, actual outputs and independent chemical oracles."""

from dataclasses import replace
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication

from azimuth.app import Studio
from azimuth.core import Calculation, read_xyz
from azimuth import projects
from modules.sextant import batch, batch_retry

DATA = Path(__file__).parents[1] / 'data'
MOPAC_OUTPUT = DATA / 'mopac' / 'h2o_pm7_opt.out'
WATER = read_xyz('3\nwater\nO 0 0 0\nH 0.96 0 0\nH -0.24 0.93 0')
CALC = Calculation(method='PM7', task='Оптимизация')
WATER_PM7_HEAT = -57.79986
ORBITAL_BYTES = b'untouched orbital data'
PAIR = 2
ONE = 1
THREE_ATTEMPTS = 3
DONE, FAILED, RUNNING = 'done', 'failed', 'running'


@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(app, tmp_path, monkeypatch):
    monkeypatch.setenv('AZIMUTH_RECOVERY_DIR', str(tmp_path / 'recovery'))
    owner = Studio(example=True, probe_machine=False)
    owner.unfinished.timer.stop()
    try:
        yield owner
    finally:
        owner.dirty = False
        for document in owner.all_documents():
            document.dirty = False
        owner.close()
        owner.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def source_queue(root, count=PAIR, kind='mopac', calc=CALC, output=MOPAC_OUTPUT):
    root.mkdir()
    items = []
    for k in range(count):
        folder = root / str(k)
        folder.mkdir()
        result = folder / 'water.out'
        shutil.copy2(output, result)
        (folder / 'wavefunction.dat').write_bytes(ORBITAL_BYTES)
        items.append(batch.BatchItem(f'water {k}', WATER, state=DONE, folder=str(folder), output=str(result)))
    queue = batch.Batch(kind, calc, items, root)
    queue.save()
    return queue


def new_retry(parent, root, indices=(0,)):
    requests = [(k, WATER, 0, 1, 'input') for k in indices]
    return batch_retry.prepare(parent, requests, CALC, 'mopac', 'local', root)


def finish_retry(queue, output=MOPAC_OUTPUT):
    folder = queue.folder / 'job'
    folder.mkdir()
    result = folder / 'water.out'
    shutil.copy2(output, result)
    queue.items[0].folder, queue.items[0].output = str(folder), str(result)
    queue.finished(queue.items[0], DONE)


class TestPortableProject:
    def test_keeps_files_and_results_when_copied_project_is_moved(self, tmp_path):
        # Arrange
        source = source_queue(tmp_path / 'source')
        original = (source.folder / 'batch.json').read_bytes()
        project = projects.Project.create(tmp_path / 'project')
        # Act
        copied = project.import_batch(source.folder)
        relative_copy = copied.relative_to(project.root)
        moved = tmp_path / 'moved'
        shutil.move(project.root, moved)
        reopened = projects.refresh(moved / projects.MANIFEST)
        entries = reopened.result_items()
        # Assert
        assert len(entries) == PAIR
        assert all(Path(i.output).is_relative_to(moved) for _, _, i in entries)
        assert entries[0][2].heat == pytest.approx(WATER_PM7_HEAT)
        assert (moved / relative_copy / '0/wavefunction.dat').read_bytes() == ORBITAL_BYTES
        assert (source.folder / 'batch.json').read_bytes() == original

    def test_keeps_membership_when_same_batch_is_imported_twice(self, tmp_path):
        # Arrange
        source = source_queue(tmp_path / 'source')
        project = projects.Project.create(tmp_path / 'project')
        first = project.import_batch(source.folder)
        # Act
        second = project.import_batch(source.folder)
        # Assert
        assert first == second and len(project.molecules) == PAIR

    def test_keeps_last_success_when_retries_fail_or_old_queue_syncs(self, tmp_path):
        # Arrange
        source = source_queue(tmp_path / 'source', ONE)
        project = projects.Project.create(tmp_path / 'project')
        parent = batch.Batch.load(project.import_batch(source.folder))
        ident = project.molecules[0]['id']
        first = project.current(project.molecules[0])['id']
        # Act: a failure does not destroy the previous result
        retry = new_retry(parent, tmp_path / 'wrong-root')
        retry.finished(retry.items[0], FAILED)
        failed = projects.Project.load(project.path)
        # Assert
        assert failed.entry(ident)['current'] == first
        assert retry.folder.is_relative_to(project.root)
        # Act: a successful retry of that failure stays attached to the same molecule
        again = new_retry(retry, tmp_path / 'wrong-root')
        finish_retry(again)
        current = projects.Project.load(project.path).entry(ident)['current']
        parent.save()
        saved = projects.Project.load(project.path)
        # Assert
        assert len(saved.molecules) == ONE
        assert len(saved.entry(ident)['attempts']) == THREE_ATTEMPTS
        assert saved.entry(ident)['current'] == current and current != first
        assert saved.entry(ident)['attempts'][0]['input']['xyz'] == WATER.xyz()

    def test_keeps_ready_result_when_new_output_cannot_be_read(self, tmp_path):
        # Arrange
        source = source_queue(tmp_path / 'source', ONE)
        project = projects.Project.create(tmp_path / 'project')
        parent = batch.Batch.load(project.import_batch(source.folder))
        ident, before = project.molecules[0]['id'], project.molecules[0]['current']
        retry = new_retry(parent, project.root)
        broken = tmp_path / 'broken.out'
        broken.write_text('not a result')
        # Act
        finish_retry(retry, broken)
        saved = projects.Project.load(project.path)
        # Assert
        assert saved.entry(ident)['current'] == before
        assert not saved.entry(ident)['attempts'][-1]['usable']

    @pytest.mark.parametrize('absolute', [False, True])
    def test_rejects_escape_when_reference_points_outside_project(self, tmp_path, absolute):
        # Arrange
        project = projects.Project.create(tmp_path / 'project')
        path = str(tmp_path / 'outside') if absolute else '../outside'
        # Act / Assert
        with pytest.raises(ValueError, match='относительным|not in the subpath|not in the same path'):
            project.absolute(path)

    def test_preserves_selection_order_when_subset_is_retried(self, tmp_path):
        # Arrange
        source = source_queue(tmp_path / 'source', count=THREE_ATTEMPTS)
        project = projects.Project.create(tmp_path / 'project')
        parent = batch.Batch.load(project.import_batch(source.folder))
        order = (2, 0)
        expected = [project.molecules[k]['id'] for k in order]
        # Act
        retry = new_retry(parent, project.root, order)
        # Assert
        assert retry.extra['project']['ids'] == expected

    def test_preserves_running_status_when_project_is_refreshed(self, tmp_path):
        # Arrange
        project = projects.Project.create(tmp_path / 'project')
        entry = project.add(WATER, CALC)
        project.save()
        queue = source_queue(project.root / 'calculations' / 'active', ONE)
        queue.items[0].state = RUNNING
        projects.attach(queue, project.path, [entry['id']])
        # Act
        refreshed = projects.refresh(project.path)
        # Assert
        assert refreshed.entry(entry['id'])['attempts'][0]['state'] == RUNNING
        assert refreshed.current(refreshed.entry(entry['id'])) is None

    def test_a_queue_of_drawer_conformers_is_a_subgroup_of_its_molecule(self, tmp_path):
        # a queue of the drawer conformers bound — on reopening, its rows stand under the molecule
        # Arrange
        project = projects.Project.create(tmp_path / 'project')
        parent = project.add(WATER, CALC, name='H2O')
        other = project.add(WATER, CALC, name='other')
        rows = [project.add(WATER, CALC, name=f'Конформер {k}') for k in (1, 2)]
        project.save()
        queue = source_queue(project.root / 'calculations' / 'conformers', PAIR)
        queue.purpose = 'conformers'
        queue.items[1].start_delta = 0.5
        queue.extra['origin'] = {'project': project.data['id'], 'molecule': parent['id']}
        projects.attach(queue, project.path, [e['id'] for e in rows])
        # Act
        refreshed = projects.refresh(project.path)
        # Assert
        assert [e['name'] for e in refreshed.molecules] == ['H2O', 'H2O · 1', 'H2O · 2', 'other']
        assert [e['conformer']['rank'] for e in projects.conformers_of(refreshed, parent['id'])] == [1, 2]
        assert projects.conformers_of(refreshed, parent['id'])[1]['conformer']['delta'] == 0.5
        assert other['id'] in {e['id'] for e in refreshed.molecules}

    def test_leaves_queue_unbound_when_its_folder_is_outside_the_project(self, tmp_path):
        # a queue in another jobs folder (Settings) is not bound — no ValueError of a path outside the project
        # Arrange
        project = projects.Project.create(tmp_path / 'project')
        entry = project.add(WATER, CALC)
        project.save()
        queue = source_queue(tmp_path / 'elsewhere', ONE)
        # Act
        bound = projects.attach(queue, project.path, [entry['id']])
        # Assert
        assert not bound and 'project' not in queue.extra
        assert projects.Project.load(project.path).data['batches'] == []

    def test_recovers_finished_single_result_when_callback_was_missed(self, tmp_path):
        # Arrange
        project = projects.Project.create(tmp_path / 'project')
        entry = project.add(WATER, CALC, 'mopac')
        folder = project.root / 'calculations' / 'single'
        folder.mkdir()
        output = folder / 'water.out'
        attempt_id = 'single-attempt'
        project.record(entry['id'], attempt_id, WATER, CALC, 'mopac', RUNNING, folder, output)
        project.save()
        shutil.copy2(MOPAC_OUTPUT, output)
        # Act
        reopened = projects.refresh(project.path)
        # Assert
        assert reopened.entry(entry['id'])['current'] == attempt_id
        assert reopened.result_items()[0][2].heat == pytest.approx(WATER_PM7_HEAT)

    def test_copies_start_orbitals_when_project_moves_without_source(self, tmp_path):
        # Arrange
        guess = tmp_path / 'original.gbw'
        guess.write_bytes(ORBITAL_BYTES)
        project = projects.Project.create(tmp_path / 'project')
        entry = project.add(WATER, replace(CALC, guess=str(guess)))
        project.save()
        # Act
        moved = tmp_path / 'moved'
        shutil.move(project.root, moved)
        guess.unlink()
        reopened = projects.Project.load(moved)
        _, calc = reopened.read_structure(reopened.entry(entry['id'])['structure'])
        # Assert
        assert Path(calc.guess).is_relative_to(moved)
        assert Path(calc.guess).read_bytes() == ORBITAL_BYTES

    def test_analyses_only_current_result_when_old_and_failed_attempts_exist(self, tmp_path):
        # Arrange
        from modules.spectrum.wavefunction import batch_qtaim
        from tests.spectrum.test_batch_qtaim import FCHK, recorded

        output = DATA / 'orca601/h2o_energy.out'
        source = source_queue(tmp_path / 'source', ONE, 'orca', Calculation(task='Энергия'), output)
        shutil.copy2(FCHK, source.folder / '0/water.fchk')
        project = projects.Project.create(tmp_path / 'project')
        parent = batch.Batch.load(project.import_batch(source.folder))
        retry = new_retry(parent, project.root)
        retry.finished(retry.items[0], FAILED)
        calls = []
        # Act: only the external Multiwfn execution is replaced by its recorded output
        records = projects.refresh(project.path).result_items()
        results = batch_qtaim.analyse('multiwfn', [item for _, _, item in records], run=recorded(calls))
        # Assert
        assert len(calls) == ONE and len(results) == ONE
        expected_counts = {'n': 3, 'b': 2, 'r': 0, 'c': 0}
        assert results[0].topology.counts == expected_counts


class TestProjectWorkflow:
    def test_prepares_queue_without_running_when_molecules_are_selected(self, window, tmp_path):
        # Arrange
        path = window.create_research_project(tmp_path / 'project')
        xyz = tmp_path / 'helium.xyz'
        xyz.write_text('1\nhelium\nHe 0 0 0')
        window.import_project_structures([xyz])
        ids = [entry['id'] for entry in projects.Project.load(path).molecules]
        # Act
        dialog = window.prepare_project_calculations(ids)
        # Assert
        assert len(dialog.rows) == PAIR and dialog.created is None and window.batch is None
        assert path.is_file()

    def test_history_window_keeps_only_history_and_files_when_shown(self, window, tmp_path):
        # «История и файлы проекта»: the buttons doing what the pane of the tab does are gone, and the window
        # opens only when asked (it opened by itself when a project was made)
        # Arrange
        from PySide6.QtWidgets import QPushButton

        window.create_research_project(tmp_path / 'project')
        shown_by_itself = getattr(window, '_project_dialog', None) is not None
        # Act
        panel = window.show_research_project()
        texts = {b.text() for b in panel.findChildren(QPushButton)}
        # Assert
        assert not shown_by_itself and panel.windowTitle() == 'История и файлы проекта'
        assert {'История расчётов молекулы', 'Добавить молекулы из файлов…', 'Добавить пакет расчётов…'} <= texts
        assert not texts & {'Новый проект…', 'Открыть проект…', 'Сохранить', 'Открыть структуру',
                            'Подготовить расчёты выбранных…', 'QTAIM всего проекта', 'Закрыть проект'}
        panel.close()

    def test_keeps_attempt_identity_when_single_job_is_reopened(self, window, tmp_path):
        # Arrange
        path = window.create_research_project(tmp_path / 'project')
        ident = projects.Project.load(path).molecules[0]['id']
        folder = window.run_tool.jobs_root() / 'single'
        folder.mkdir()
        output = folder / 'water.out'
        shutil.copy2(MOPAC_OUTPUT, output)
        job = SimpleNamespace(spec=SimpleNamespace(folder=folder, output=output), message='')
        # Act
        window.register_project_job(job, CALC, 'mopac')
        window.finish_project_job(job, 'finished')
        window.close_project_tab(window.project_sessions.index(path))  # the tab is the project
        window.open_project_path(path)
        again = SimpleNamespace(spec=job.spec, message='')
        window.register_project_job(again, CALC, 'mopac')
        window.finish_project_job(again, 'finished')
        project = projects.Project.load(path)
        # Assert
        assert window.research_path() == path
        assert len(project.molecules) == ONE
        assert len(project.entry(ident)['attempts']) == ONE
        assert project.current(project.entry(ident))['usable']

    def test_preserves_attempt_input_when_editable_structure_changes(self, window, tmp_path):
        # Arrange
        path = window.create_research_project(tmp_path / 'project')
        folder = window.run_tool.jobs_root() / 'job'
        folder.mkdir()
        output = folder / 'water.out'
        shutil.copy2(MOPAC_OUTPUT, output)
        job = SimpleNamespace(spec=SimpleNamespace(folder=folder, output=output), message='')
        window.register_project_job(job, CALC, 'mopac')
        old = projects.Project.load(path).molecules[0]['attempts'][0]['input']
        helium = read_xyz('1\nHe\nHe 0 0 0')
        # Act
        window.load_molecule(helium)
        window.save_project()
        saved = projects.Project.load(path)
        # Assert
        assert saved.read_structure(saved.molecules[0]['structure'])[0].formula == helium.formula
        assert saved.molecules[0]['attempts'][0]['input'] == old

    def test_preserves_ionic_charges_and_flat_flag_when_project_reopens(self, window, tmp_path):
        # Arrange
        from tests.compass.test_formal_charges import CHLORIDE, NITRATE, ACETIC

        window.preferences.setValue('hydrogens_on_open', True)
        path = window.create_research_project(tmp_path / 'project')
        source = tmp_path / 'ions.sdf'
        source.write_text(CHLORIDE + NITRATE + ACETIC)
        # Act
        window.import_project_structures([source])
        saved = projects.Project.load(path)
        chloride, nitrate, acetic = saved.molecules[-3:]
        window.open_project_molecule(chloride['id'])
        # Assert
        expected_charge, singlet = -1, 1
        assert window.charge.value() == expected_charge and window.spin.value() == singlet
        assert window.document().file_formal == (expected_charge,)
        assert window.molecule.formula == 'Cl'
        assert saved.absolute(chloride['source']).read_bytes() == source.read_bytes()
        assert nitrate['formal'] == [1, 0, -1, -1]
        assert acetic['flat']
        # Act
        window.save_project()
        window.close_project_tab(window.project_sessions.index(path))  # the tab is the project
        window.open_project_path(path)
        window.open_project_molecule(acetic['id'])
        # Assert
        assert window.document().structure_flat == (window.molecule,)
        assert window.molecule.formula == 'C2H4O2'

    def test_creates_independent_copy_when_project_is_saved_as(self, window, tmp_path):
        # Arrange
        path = window.create_research_project(tmp_path / 'original')
        original = projects.Project.load(path)
        fixture = original.root / 'calculations' / 'retained.dat'
        fixture.write_bytes(ORBITAL_BYTES)
        target = tmp_path / 'copy'
        # Act
        window.copy_research_project(target)
        copied = projects.Project.load(target)
        # Assert
        assert copied.data['id'] != original.data['id']
        assert copied.data['name'] == target.name
        assert copied.molecules == projects.Project.load(path).molecules
        assert (target / 'calculations' / fixture.name).read_bytes() == fixture.read_bytes()

    def test_leaves_other_tabs_alone_when_a_project_is_open(self, window, tmp_path, monkeypatch):
        # Arrange
        path = window.create_research_project(tmp_path / 'project')
        before = len(projects.Project.load(path).molecules)
        window.new_document('other', read_xyz('1\nHe\nHe 0 0 0'))
        asked = []
        monkeypatch.setattr(window, 'save_project_as', lambda: asked.append(True))
        # Act
        window.save_project()
        # Assert
        assert asked == [True]
        assert len(projects.Project.load(path).molecules) == before
        assert window.research_document_path() is None
        assert window.run_tool.jobs_root() != path.parent / 'calculations'

    def test_opens_project_when_one_queue_belongs_elsewhere(self, window, tmp_path):
        # Arrange
        path = window.create_research_project(tmp_path / 'project')
        stray = path.parent / 'calculations' / 'stray'
        stray.mkdir()
        (stray / batch.FILE).write_text('{broken', encoding='utf-8')
        with projects.edit(path) as project:
            project.data['batches'].append('calculations/stray')
        # Act
        refreshed = projects.refresh(path)
        # Assert
        assert refreshed.skipped == ['calculations/stray']
