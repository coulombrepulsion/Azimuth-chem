"""A visible tab is a project; molecule selection and scientific state follow the section, not new tabs."""
from pathlib import Path


from azimuth.core import Molecule
from azimuth import projects
from tests.projects.test_projects import app, window, source_queue  # shared isolated Qt fixtures
from tests.compass.test_formal_charges import CHLORIDE, NITRATE

NEW_NAME = 'Новый проект'
PAIR = 2
SINGLE = 1
SEXTANT, SPECTRUM = 1, 2


def empty(window):
    window.load_molecule(Molecule('', (), ()), record=False)
    window.dirty = False


def ions(tmp_path):
    source = tmp_path / 'Мои молекулы.sdf'
    source.write_text(CHLORIDE + NITRATE)
    return source


class TestProjectTabs:
    def test_names_project_after_database_when_file_opens(self, window, tmp_path):
        # Arrange
        empty(window)
        source = ions(tmp_path)
        # Act
        window.opening_tool.open_path(source)
        project = projects.Project.load(window.research_path())
        # Assert
        assert project.data['name'] == source.stem
        assert len(project.molecules) == PAIR
        assert len(window.project_sessions) == SINGLE
        assert window.project_molecules.count() == PAIR
        assert not hasattr(window, 'document_bar')  # the hidden row of the document tabs is gone

    def test_lists_molecules_as_the_structures_page_when_set_opens(self, window, tmp_path):
        # Arrange
        from modules.compass.panels.trajectory_drawer import PAGES, WIDTH

        empty(window)
        source = ions(tmp_path)
        # Act
        window.opening_tool.open_path(source)
        table = window.project_molecules
        # Assert: the look of «Структуры» of the drawer; that page itself is not offered any more
        assert [table.horizontalHeaderItem(k).text() for k in range(3)] == ['№', 'Название', 'Формула']
        assert table.item(1, 2).text() == 'NO₃' and window.project_pane.width() == WIDTH
        assert window.project_title.text() == 'Структуры'
        assert 'structures' not in PAGES  # the page is gone

    def test_keeps_the_list_when_a_refresh_changes_nothing(self, window, tmp_path):
        # a refresh that would show the same rows leaves the list as it is (it was rebuilt every time: the
        # scroll jumped to the top); a change of the project rebuilds it
        # Arrange
        empty(window)
        window.opening_tool.open_path(ions(tmp_path))
        table = window.project_molecules
        first = table.item(0, 1)
        # Act
        window.refresh_project_navigation()
        kept = table.item(0, 1) is first
        with projects.edit(window.research_path()) as project:
            project.molecules[0]['name'] = 'хлорид'
        window.refresh_project_navigation()
        # Assert
        assert kept and table.item(0, 1).text() == 'хлорид'

    def test_keeps_first_molecule_when_files_are_dropped_into_tab(self, window, tmp_path):
        # Arrange: the example water is already in the current tab
        original = window.own_molecule().formula
        source = tmp_path / 'helium.xyz'
        source.write_text('1\nhelium\nHe 0 0 0')
        # Act
        window.view_tool.drop_paths([source])
        project = projects.Project.load(window.research_path())
        formulas = [project.read_structure(e['structure'])[0].formula for e in project.molecules]
        # Assert
        assert project.data['name'] == NEW_NAME
        assert formulas == [original, 'He']
        assert len(window.project_sessions) == SINGLE

    def test_changes_only_molecule_when_selected_in_sextant(self, window, tmp_path):
        # Arrange
        empty(window)
        window.opening_tool.open_path(ions(tmp_path))
        path = window.research_path()
        window.navigate(SEXTANT)
        # Act
        window.project_molecules.setCurrentRow(1)
        # Assert
        assert window.stack.currentIndex() == SEXTANT
        assert window.research_path() == path
        assert window.molecule.formula == 'NO3'
        expected_charge, singlet = -1, 1
        assert window.charge.value() == expected_charge and window.spin.value() == singlet
        assert window.project_molecules.parentWidget() is window.project_pane
        assert len(window.project_sessions) == SINGLE

    def test_preserves_separate_projects_when_other_file_opens(self, window, tmp_path):
        # Arrange
        empty(window)
        source = ions(tmp_path)
        window.opening_tool.open_path(source)
        first = window.research_path()
        helium = tmp_path / 'helium.xyz'
        helium.write_text('1\nhelium\nHe 0 0 0')
        # Act
        window.opening_tool.open_path(helium)
        second = window.research_path()
        window.project_tabs.setCurrentIndex(0)
        # Assert
        assert first != second
        assert window.research_path() == first
        assert window.project_molecules.count() == PAIR
        assert len(projects.Project.load(second).molecules) == SINGLE

    def test_draft_lives_in_the_projects_folder_and_saving_names_it(self, window, tmp_path):
        # the draft of an opened file has its permanent folder at once —
        # «Проекты/<name of the file>»; «Сохранить» confirms the name and copies nothing
        import os

        from azimuth import project_folders

        # Arrange
        empty(window)
        window.opening_tool.open_path(ions(tmp_path))
        draft = window.research_path()
        # the projects of molecules in «Проекты/Молекулы» (project_folders.kind_root)
        root = project_folders.kind_root(Path(os.environ['AZIMUTH_PROJECTS_DIR']).resolve(), 'molecule')
        # Assert: the folder
        assert draft.parent.parent == root and draft.parent.name.startswith(project_folders.folder_name('Мои молекулы'))
        # (on Windows the name is in Latin letters: «Moi molekuly», project_folders §2)
        assert projects.Project.load(draft).data['draft']
        before = sorted(p.name for p in root.iterdir())  # the folder is shared by the whole run: other drafts are there
        # Act
        title = 'Исследование ионов'
        window.save_project_tab(name=title)
        saved = projects.Project.load(draft)
        # Assert
        assert saved.data['name'] == title and not saved.data['draft'] and saved.data['named']
        assert window.research_path() == draft and window.project_tabs.tabText(0) == title
        assert sorted(p.name for p in root.iterdir()) == before and draft.parent.name in before  # nothing copied

    def test_moves_the_project_folder_whole(self, window, tmp_path):
        # «Перенести проект» — the same id in the new folder, the documents follow, the old folder is gone
        # Arrange
        empty(window)
        window.opening_tool.open_path(ions(tmp_path))
        old = window.research_path()
        ident = projects.Project.load(old).data['id']
        target, title = tmp_path / 'saved', 'Исследование ионов'
        # Act
        window.save_project_tab(folder=target, name=title)
        saved = projects.Project.load(target)
        # Assert
        assert saved.data['name'] == title and not saved.data['draft'] and saved.data['id'] == ident
        assert window.research_path() == saved.path and not old.exists()
        assert window.project_tabs.tabText(0) == title
        assert all(Path(d.research_project_path) == saved.path for d in window.documents if d.research_molecule_id)

    def test_shows_correct_result_when_molecule_changes_in_spectrum(self, window, tmp_path):
        # Arrange
        empty(window)
        source = source_queue(tmp_path / 'source')
        path = window.create_research_project(tmp_path / 'project')
        window.import_project_batch(source.folder)
        project = projects.Project.load(path)
        window.open_project_molecule(project.molecules[0]['id'], stay=True)
        window.refresh_project_navigation()
        # Act
        window.navigate(SPECTRUM)
        window.project_molecules.setCurrentRow(1)
        selected = projects.Project.load(path).molecules[1]
        # Assert
        assert window.stack.currentIndex() == SPECTRUM
        assert window.document().research_molecule_id == selected['id']
        assert Path(window.output_path) == project.absolute(project.current(selected)['output'])
        assert window.result_tabs.isTabVisible(window.topology_tab)

    def test_compass_gets_the_result_of_a_project_molecule(self, window, tmp_path):
        # choosing a molecule with a result in Compass reads it — its steps in the drawer (☰), Spectrum ready; the end
        # of a row of a queue (project_queue_row_ended) shows the result of the molecule on screen
        # Arrange
        empty(window)
        source = source_queue(tmp_path / 'source')
        path = window.create_research_project(tmp_path / 'project')
        window.import_project_batch(source.folder)
        project = projects.Project.load(path)
        window.navigate(0)
        # Act
        window.open_project_molecule(project.molecules[1]['id'], stay=True)
        window.project_section_changed(0)
        # Assert
        output = window.document().output
        assert output is not None and Path(output[3]) == project.absolute(project.current(project.molecules[1])['output'])
        assert window.drawer.steps == tuple(output[0].steps)
        # the buttons of Compass («Атомы», «Связи», «Диполь и силы») get the properties of that result too
        assert window.result_properties is output[0].properties and window.document().properties[0] is output[0].properties
        window.result_properties = None  # another molecule's were shown meanwhile: choosing it again gives them back
        window.project_section_changed(0)
        assert window.result_properties is output[0].properties
        # Act: the row of the molecule shown ends — read once, not again
        window.document().output = None
        assert window.project_queue_row_ended() is True
        # Assert
        assert window.document().output is not None and window.stack.currentIndex() == 0

    def test_t05_the_result_goes_to_the_tab_of_its_attempt(self, window, tmp_path):
        # the tab of the molecule of the attempt, found by the ids at the end — not the tab current
        # at the start (job_document); a closed tab of the molecule is opened again
        from types import SimpleNamespace

        # Arrange
        empty(window)
        window.opening_tool.open_path(ions(tmp_path))
        path = window.research_path()
        first, second = [m['id'] for m in projects.Project.load(path).molecules]
        a = window.open_project_molecule(first, stay=True)
        b = window.open_project_molecule(second, stay=True)
        job = SimpleNamespace(_research_link=(path, {'molecule': first}))
        window.job_document = b  # started while B was on screen
        # Act, Assert: A's tab, though B is current
        assert window.document() is b and window.run_tool.result_tab_of(job) is a
        # Act: A's tab closed — opened again for the result
        window.close_document(next(k for k, d in enumerate(window.documents) if d is a))
        again = window.run_tool.result_tab_of(job)
        # Assert
        assert again is not None and again is not a and again.research_molecule_id == first
        assert sum(1 for d in window.documents if getattr(d, 'research_molecule_id', '') == first) == 1

    def test_prepares_all_molecules_without_submission_when_batch_requested(self, window, tmp_path):
        # Arrange
        empty(window)
        window.opening_tool.open_path(ions(tmp_path))
        # Act
        dialog = window.prepare_whole_project()
        # Assert
        assert window.stack.currentIndex() == SEXTANT
        assert len(dialog.rows) == PAIR
        assert dialog.created is None and window.batch is None
        assert len(window.project_sessions) == SINGLE

    def test_keeps_sdf_properties_when_project_prepares_retry(self, window, tmp_path):
        # Arrange
        empty(window)
        source = tmp_path / 'binding.sdf'
        log_k = '4.25'
        source.write_text(CHLORIDE.replace('$$$$', '> <logK>\n' + log_k + '\n\n$$$$') + NITRATE)
        window.opening_tool.open_path(source)
        # Act
        dialog = window.prepare_whole_project()
        dialog.create_button.click()
        queue = dialog.created
        # Assert
        assert queue is not None
        assert queue.items[0].props['logK'] == log_k
        assert queue.items[0].formal == (-1,)
        assert len(queue.extra['project']['ids']) == PAIR
        assert window.batch is None

    def test_attaches_drawn_molecule_when_empty_project_enters_sextant(self, window, tmp_path):
        # Arrange
        from tests.projects.test_projects import WATER
        empty(window)
        window.new_project_tab()
        window.load_molecule(WATER)
        # Act
        window.navigate(SEXTANT)
        project = projects.Project.load(window.research_path())
        # Assert
        assert len(project.molecules) == SINGLE
        assert window.document().research_molecule_id == project.molecules[0]['id']
        assert window.run_tool.jobs_root() == project.root / 'calculations'


def test_retains_binding_followups_when_project_queue_grows(tmp_path):
    # Arrange
    from azimuth.core import Calculation
    from modules.sextant import batch, binding
    from tests.projects.test_projects import WATER

    project = projects.Project.create(tmp_path / 'project')
    items, extra = binding.plan([('water', WATER, 0, 1, {'logK': '1.5'}, ())], 'Na', bsse=True)
    folder = project.root / 'calculations' / 'binding'
    folder.mkdir()
    queue = batch.Batch('orca', Calculation(), items, folder, purpose='binding', extra=extra)
    ids = [project.add(i.molecule, Calculation(), name=i.name)['id'] for i in items]
    project.save()
    projects.attach(queue, project.path, ids)
    complex_item = items[-1]
    complex_item.state, complex_item.geometry = 'done', complex_item.molecule
    # Act
    added = binding.follow_ups(queue, complex_item)
    projects.extend_queue(queue)
    queue.save()
    reopened = projects.refresh(project.path)
    # Assert
    assert not queue.project_warning
    assert len(reopened.molecules) == len(ids) + len(added)
    assert queue.extra['project']['ids'][:len(ids)] == ids
    assert all(e['attempts'][0]['calculation']['task'] == 'Энергия' for e in reopened.molecules[len(ids):])


def test_keeps_the_result_drawer_reachable_when_tabs_are_projects(window, tmp_path):
    # the list of the molecules has its own sign; ☰ of Compass stays the drawer of the result
    from azimuth.core import read_xyz

    # Arrange
    steps = [read_xyz('2\nH2\nH 0 0 0\nH 0.74 0 0\n'), read_xyz('2\nH2\nH 0 0 0\nH 0.75 0 0\n')]
    # Act
    window.trajectory_tool.load_conformers([(m, -1.0 - 0.001 * k, 0.6 * k, 0.5) for k, m in enumerate(steps)], 'CREST')
    window.navigate(0)
    window.project_section_changed(0)
    window.trajectory_tool.update_result_button()
    # Assert
    assert window.project_menu_button.property('quail_icon') == 'molecule-list'
    assert not window.trajectory_button.isHidden()


def test_slides_the_list_out_and_back_when_its_button_is_pressed(window, app):
    # the panel of the molecules comes out and goes back smoothly, its table never squeezed
    import time

    from azimuth.project_widgets import GAP
    from modules.compass.panels.trajectory_drawer import SLIDE_MS, WIDTH

    # Arrange
    window.show()
    app.processEvents()
    widths = []
    # Act
    window.show_project_molecules()
    end = time.monotonic() + 3 * SLIDE_MS / 1000
    while time.monotonic() < end:
        app.processEvents()
        widths.append(window.project_slide.width())
        time.sleep(0.01)
    opened = window.project_slide.width()
    window.hide_project_molecules()
    end = time.monotonic() + 3 * SLIDE_MS / 1000
    while time.monotonic() < end:
        app.processEvents()
        time.sleep(0.01)
    # Assert
    assert any(0 < w < WIDTH for w in widths)  # it moved through the widths between
    assert opened == WIDTH + GAP and window.project_pane.width() == WIDTH  # the gap on its right only
    assert window.project_pane.y() == 0 and window.project_pane.height() == window.project_slide.height()  # as the page
    assert window.project_pane.objectName() == 'projectPane'  # rounded and outlined as the other cards
    assert window.project_slide.width() == 0 and window.project_slide.isHidden()


def test_batch_mode_ticks_all_and_queues_those_left(window, tmp_path):
    # «Пакетный» — every molecule ticked and chosen for the queue of Sextant; a tick taken off leaves it out;
    # «Одиночный» — the molecule chosen, no queue; no buttons under the table any more
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QPushButton

    # Arrange
    empty(window)
    window.opening_tool.open_path(ions(tmp_path))
    table = window.project_molecules
    # Act
    window.set_project_batch_mode(True)
    # Assert
    assert window.project_mode_tabs.currentIndex() == 1
    assert [table.item(k, 0).checkState() for k in range(table.rowCount())] == [Qt.CheckState.Checked] * PAIR
    assert window.batch_plan['indices'] == [0, 1] and window.run_button.text() == 'Запустить очередь (2)'
    # Act
    table.item(1, 0).setCheckState(Qt.CheckState.Unchecked)
    # Assert
    assert window.batch_plan['indices'] == [0] and len(window.selected_project_molecules()) == SINGLE
    assert projects.Project.load(window.research_path()).data['excluded'] == [
        table.item(1, 0).data(Qt.ItemDataRole.UserRole)]
    # Act
    window.set_project_batch_mode(False)
    # Assert
    assert window.batch_plan is None and window.selected_project_molecules() == [window.document().research_molecule_id]
    texts = {b.text() for b in window.project_pane.findChildren(QPushButton)}
    assert not texts & {'Пакетный расчёт…', 'Рассчитать выбранные…', 'Бейдеровский анализ проекта', 'Результат в Компасе'}


def test_aligns_spectrum_panel_with_the_list_when_spectrum_shows(window, app):
    # the tabs of the result are inside the panel of Spectrum, the panel begins where the list does
    from PySide6.QtCore import QPoint

    # Arrange
    window.show()
    window.navigate(2)
    window.ensure_project_tab()
    window.slide_project_pane(True, animate=False)
    app.processEvents()
    # Act
    panel_top = window.result_panel.mapTo(window, QPoint(0, 0)).y()
    list_top = window.project_pane.mapTo(window, QPoint(0, 0)).y()
    # Assert
    assert window.result_panel.isAncestorOf(window.result_top_row)
    assert panel_top == list_top
    assert not hasattr(window, 'result_tab_rule')  # no rule before the molecule tabs any more


def test_lays_spectrum_tabs_on_its_panels_when_spectrum_shows(window, app):
    # the tabs of the result on the left, right on the top edge of the panels of the page; the tabs without a
    # card of their own framed as one; an empty result — Quill in place of the table of the frequencies
    from PySide6.QtCore import QPoint

    # Arrange
    window.show()
    window.navigate(2)
    window.clear_result()
    app.processEvents()
    header = window.result_tabs.header
    cards = window.result_tabs.group()  # the panel of the tab — the list of its pages and their cards
    # Act
    header_left = header.mapTo(window, QPoint(0, 0)).x()
    header_bottom = header.mapTo(window, QPoint(0, header.height())).y()
    cards_top = cards.mapTo(window, QPoint(0, 0))
    inner = window.records_cards.mapTo(window, QPoint(0, 0))
    # Assert
    # 12 px in
    assert abs(header_left - cards_top.x() - 12) <= 1
    assert cards_top.y() - header_bottom <= 4  # the frame of the tab widget at most
    assert cards_top.x() < inner.x() < cards_top.x() + 20 and cards_top.y() < inner.y()  # the cards inside the panel
    assert all(p.objectName() == 'resultCard' for p in (window.uv_panel, window.topology_panel, window.nci_panel))
    assert window.frequency_table.isHidden() and not window.empty_page.isHidden()
    assert window.result_summary.isHidden()


def test_a_queue_taken_up_opens_its_project_in_compass(window, tmp_path, monkeypatch):
    # resume_batch opens the project of the queue (its tab, its first molecule)
    # and Sextant stays on screen
    from azimuth.core import Calculation
    from modules.sextant import batch
    from tests.projects.test_projects import WATER

    # Arrange
    project = projects.Project.create(tmp_path / 'project')
    ids = [project.add(WATER, Calculation(), name=f'water {k}')['id'] for k in range(2)]
    project.save()
    folder = project.root / 'calculations' / 'queue'
    folder.mkdir(parents=True)
    items = [batch.BatchItem(f'water {k}', WATER, state=state) for k, state in enumerate(('done', 'waiting'))]
    queue = batch.Batch('orca', Calculation(), items, folder, place='local', source='project')
    assert projects.attach(queue, project.path, ids)
    queue.save()
    started = []
    monkeypatch.setattr(window.batch_tool, '_run_batch', lambda q: started.append(q.folder) or q)
    window.navigate(SEXTANT)
    assert window.research_path() != project.path.resolve()
    # Act
    window.batch_tool.resume_batch(str(folder))
    # Assert
    assert Path(window.research_path()).resolve() == project.path.resolve()
    assert window.document().research_molecule_id == ids[0] and window.stack.currentIndex() == SEXTANT
    assert [Path(f).resolve() for f in started] == [folder.resolve()]
    window.batch_tool.resume_batch(str(folder))  # taken up again: the same tab, not a second one
    assert [Path(p).resolve() for p in window.project_sessions].count(project.path.resolve()) == 1


def test_a_finished_queue_of_different_molecules_goes_to_its_project(window, tmp_path):
    # water and ammonia of
    # a project are not conformers — «Перейти в Компас» opens the project with the list of its molecules
    from azimuth.core import Calculation, read_xyz
    from modules.sextant import batch
    from tests.projects.test_projects import WATER

    ammonia = read_xyz('4\nammonia\nN 0 0 0.1\nH 0.94 0 -0.27\nH -0.47 0.81 -0.27\nH -0.47 -0.81 -0.27')
    # Arrange
    project = projects.Project.create(tmp_path / 'project')
    ids = [project.add(m, Calculation(), name=name)['id'] for m, name in ((WATER, 'water'), (ammonia, 'ammonia'))]
    project.save()
    folder = project.root / 'calculations' / 'queue'
    folder.mkdir(parents=True)
    items = [batch.BatchItem(name, m, state='done', energy=e)
             for name, m, e in (('water', WATER, -76.4), ('ammonia', ammonia, -56.5))]
    queue = batch.Batch('orca', Calculation(), items, folder, place='local', source='project')
    assert projects.attach(queue, project.path, ids)
    assert not window.batch_tool.queue_of_conformers(queue)
    window.navigate(SEXTANT)
    window.batch = queue
    # Act
    window.batch_tool.batch_complete()
    # Assert
    assert not window.batch_finished_here and Path(window.batch_project_here) == project.path.resolve()
    assert not window.job_window.compass_button.isHidden()
    assert 'очередь' not in (getattr(window.drawer, 'conformer_source', '') or '')
    window.run_tool.go_to_result('compass')
    assert window.stack.currentIndex() == 0 and Path(window.research_path()).resolve() == project.path.resolve()


def test_molecules_removed_from_the_list_and_put_back(window, tmp_path):
    # «Удалить из проекта…» of the list — the
    # molecule and its tab go, its calculation files stay unless asked; «Вернуть удалённые» puts it back in its place
    # Arrange
    empty(window)
    source = source_queue(tmp_path / 'source')
    path = window.create_research_project(tmp_path / 'project')
    window.import_project_batch(source.folder)
    project = projects.Project.load(path)
    first, second = [e['id'] for e in project.molecules]
    folder = project.absolute(project.current(project.entry(first))['folder'])
    window.open_project_molecule(first, stay=True)
    window.refresh_project_navigation()
    # Act: files kept
    assert window.remove_project_molecules([first], delete_files=False) == [first]
    # Assert
    assert [e['id'] for e in projects.Project.load(path).molecules] == [second]
    assert window.project_molecules.rowCount() == SINGLE and folder.is_dir()
    assert all(getattr(d, 'research_molecule_id', None) != first for d in window.documents)
    # Act: back
    assert window.restore_project_molecules() == [first]
    assert [e['id'] for e in projects.Project.load(path).molecules] == [first, second]
    assert window.project_molecules.rowCount() == PAIR
    # Act: with the files of its calculation — no way back
    assert window.remove_project_molecules([first], delete_files=True) == [first]
    assert not folder.exists() and window.restore_project_molecules() == []
    assert [e['id'] for e in projects.Project.load(path).molecules] == [second]


def test_numbers_from_10_fit_beside_the_ticks_of_the_batch_mode(window, tmp_path):
    # the column «№» holds the tick and two digits; nothing is cut to «…»
    from PySide6.QtCore import Qt

    paths = []
    for k in range(12):
        path = tmp_path / f'he{k:02d}.xyz'
        path.write_text(f'1\nhe{k}\nHe {k} 0 0\n', encoding='utf-8')
        paths.append(path)
    window.open_files_project(paths)
    window.set_project_batch_mode(True)
    table = window.project_molecules
    assert table.rowCount() == 12 and table.item(11, 0).text() == '12'
    assert table.item(11, 0).flags() & Qt.ItemFlag.ItemIsUserCheckable
    metrics = table.fontMetrics()
    assert table.columnWidth(0) >= metrics.horizontalAdvance('12') + 15 + 18
    # a column narrowed by the user ends its text with «…» (ElideRight) — the column «№» is never
    # narrowed (Fixed, as wide as its widest number with the tick: above), so a number is still never cut
    from PySide6.QtWidgets import QHeaderView

    assert table.horizontalHeader().sectionResizeMode(0) == QHeaderView.ResizeMode.Fixed
    window.set_project_batch_mode(False)
    assert table.columnWidth(0) < metrics.horizontalAdvance('12') + 15 + 18  # no tick: narrower again


def test_t23_a_result_of_other_data_is_marked_in_the_list_and_said(window, tmp_path):
    # T23: the charge of a molecule changed after its result — the row says «≠» and why, choosing it says
    # so; the result stays its attempt's (not rebound), the other molecule is not marked
    from dataclasses import replace

    empty(window)
    source = source_queue(tmp_path / 'source')
    path = window.create_research_project(tmp_path / 'project')
    window.import_project_batch(source.folder)
    window.refresh_project_navigation()
    table = window.project_molecules
    assert not any(table.item(k, 1).text().endswith('≠') for k in range(table.rowCount()))
    with projects.edit(path) as project:
        entry = project.molecules[0]
        molecule, calc = project.read_structure(entry['structure'])
        entry['structure'] = project.structure(molecule, replace(calc, charge=1, multiplicity=2))
        current = entry['current']
    window.refresh_project_navigation()
    assert table.item(0, 1).text().endswith('≠') and not table.item(1, 1).text().endswith('≠')
    assert 'заряд, мультиплетность' in table.item(0, 1).toolTip()
    said = []
    window.notify = lambda text, *rest: said.append(text)
    first = projects.Project.load(path).molecules[0]
    window.open_project_molecule(first['id'], stay=True)
    window.document().calculation = None  # the tab keeps the saved settings
    window.document().output = None
    window.navigate(SPECTRUM)
    window.show_project_result()
    assert any('изменились: заряд, мультиплетность' in text for text in said)
    assert window.document().result_mismatch == ('charge', 'multiplicity')
    assert projects.Project.load(path).molecules[0]['current'] == current


class TestAutomaticName:
    """."""

    def test_a_new_project_takes_the_name_of_its_molecule(self, window, tmp_path):
        from PySide6.QtWidgets import QApplication

        from azimuth import project_folders
        from modules.compass.chemistry import library

        # Arrange: «Новый проект (N)» with nothing in it
        empty(window)
        draft = Path(window.new_project_tab())
        assert projects.Project.load(draft).data['name'] == 'Новый проект'
        assert draft.parent.name.startswith(project_folders.folder_name('Новый проект'))
        # Act: a molecule in it, saved; the folder follows after the action under way
        window.load_molecule(library.molecule('Вода · H₂O'))
        window.attach_project_placeholder()  # as at «Сохранить», a change of the section, the tab closed
        QApplication.processEvents()
        # Assert: the name of the molecule, its folder, the tab
        path = window.research_path()
        project = projects.Project.load(path)
        assert project.data['name'] == 'Вода' and project.data['auto_named'] and not project.data.get('named')
        assert path.parent.name.startswith(project_folders.folder_name('Вода')) and not draft.parent.exists()  # «Voda» on Windows
        assert window.project_tabs.tabText(window.project_tabs.currentIndex()).startswith('Вода')
        # once: another molecule changes nothing, a name the user gives replaces it
        window.save_research_project()
        QApplication.processEvents()
        assert window.research_path() == path and projects.Project.load(path).data['name'] == 'Вода'
        window.save_project_tab(name='Мои расчёты')
        assert projects.Project.load(path).data['name'] == 'Мои расчёты'

    def test_the_names(self, window):
        assert window.auto_name([{'name': 'H2O · teaching-demo.out'}]) == 'H2O'
        assert window.auto_name([{'name': 'Вода'}, {'name': 'Аммиак'}, {'name': 'Метан'}]) == 'Вода и ещё 2'
        assert window.auto_name([{'name': ''}]) == '' and window.auto_name([]) == ''


class TestFilesOnlyLookedAt:
    """A file opened to
    look at makes a project for the tab, but its folder does not stay in «Проекты» unless the project changed."""

    def test_the_folder_goes_when_the_tab_closes(self, window, tmp_path):
        empty(window)
        source = ions(tmp_path)
        window.opening_tool.open_path(source)
        path = window.research_path().resolve()
        assert path in window.viewed_projects() and path.parent.is_dir()
        window.close_project_tab(window.project_sessions.index(path))
        assert not path.parent.exists() and source.is_file()  # the file opened stays where it was

    def test_an_edit_keeps_it(self, window, tmp_path):
        empty(window)
        window.opening_tool.open_path(ions(tmp_path))
        path = window.research_path().resolve()
        window.dirty = True  # an edit of the molecule on screen
        window.close_project_tab(window.project_sessions.index(path))
        assert path.is_file() and path not in window.viewed_projects()

    def test_files_added_or_a_name_keep_it(self, window, tmp_path):
        empty(window)
        window.opening_tool.open_path(ions(tmp_path))
        path = window.research_path().resolve()
        window.keep_project(path)  # what «Добавить файлы», «Сохранить» and an edit call
        window.close_project_tab(window.project_sessions.index(path))
        assert path.is_file()

    def test_at_the_end_of_the_program(self, window, tmp_path):
        empty(window)
        window.opening_tool.open_path(ions(tmp_path))
        path = window.research_path().resolve()
        assert window.discard_untouched_projects() == [path] and not path.parent.exists()


def test_the_folder_of_a_saved_project_is_shown(window, tmp_path, monkeypatch):
    # «Показать файл в папке» of a tab of a project shows its project.qcc — it looked only for the single-file project
    # of before
    import subprocess

    # Arrange
    empty(window)
    source = source_queue(tmp_path / 'source')
    path = window.create_research_project(tmp_path / 'project')
    window.import_project_batch(source.folder)
    first = projects.Project.load(path).molecules[0]['id']
    window.open_project_molecule(first, stay=True)
    shown, notes = [], []
    monkeypatch.setattr(subprocess, 'Popen', lambda command, *a, **k: shown.append(command))
    from PySide6.QtGui import QDesktopServices  # Linux: the folder through the desktop, not a program of the system

    monkeypatch.setattr(QDesktopServices, 'openUrl', staticmethod(lambda url: shown.append([url.toLocalFile()]) or True))
    monkeypatch.setattr(window, 'notify', lambda text, *a: notes.append(text))
    # Act
    found = window.file_tool.reveal_file()
    # Assert
    assert window.research_document_path() == path and window.file_tool.tab_file() == path
    assert found == path and shown and str(path.parent) in ' '.join(map(str, shown[0])) and not notes


def test_a_new_molecule_is_a_row_of_the_project(window, tmp_path):
    # «Файл → Новая молекула» — an empty row «Новая молекула» in the list of the project,
    # chosen; the molecule shown before stays; the row is a molecule of the project once something is drawn in it
    from PySide6.QtCore import Qt

    from azimuth.core import EXAMPLES, read_xyz
    from azimuth.project_widgets import NEW_ROW

    # Arrange
    empty(window)
    source = source_queue(tmp_path / 'source')
    path = window.create_research_project(tmp_path / 'project')
    window.import_project_batch(source.folder)
    first = projects.Project.load(path).molecules[0]['id']
    window.open_project_molecule(first, stay=True)
    before = window.own_molecule()
    # Act
    assert window.new_molecule_command()
    # Assert: a third row, chosen, empty; the file still holds two; the first molecule as it was
    table = window.project_molecules
    assert table.rowCount() == PAIR + 1 and table.currentRow() == PAIR
    assert table.item(PAIR, 1).text() == 'Новая молекула' and table.item(PAIR, 2).text() == '—'
    assert not window.own_molecule().atoms and window.build_mode.currentData() == 'atom'
    assert len(projects.Project.load(path).molecules) == PAIR
    assert window.new_molecule_command() and table.rowCount() == PAIR + 1  # once: the empty one is chosen again
    window.open_project_molecule(first, stay=True)
    assert window.own_molecule().atoms == before.atoms and table.rowCount() == PAIR + 1
    table.setCurrentCell(PAIR, 0)  # back to it from the list
    assert not window.own_molecule().atoms and table.item(PAIR, 0).data(Qt.ItemDataRole.UserRole) == NEW_ROW
    # Act: a water drawn into it, then the list
    window.load_molecule(read_xyz(EXAMPLES['Вода · H₂O']))
    window.save_research_project()
    # Assert: a molecule of the project
    project = projects.Project.load(path)
    assert len(project.molecules) == PAIR + 1 and window.document().research_molecule_id == project.molecules[-1]['id']
    assert table.rowCount() == PAIR + 1 and table.item(PAIR, 0).data(Qt.ItemDataRole.UserRole) != NEW_ROW


def test_a_new_molecule_after_one_drawn_of_no_project(window, tmp_path):
    # the molecule drawn of no project is not emptied away — it becomes the draft «Новый проект», the new one
    # its second row
    from azimuth.core import EXAMPLES, read_xyz

    # Arrange
    empty(window)
    window.load_molecule(read_xyz(EXAMPLES['Вода · H₂O']))
    assert window.research_path() is None
    # Act
    assert window.new_molecule_command()
    # Assert
    path = window.research_path()
    assert path is not None and len(projects.Project.load(path).molecules) == SINGLE
    assert window.project_molecules.rowCount() == PAIR and not window.own_molecule().atoms


def test_the_first_molecule_of_an_empty_project_stays_and_empty_ones_go(window, tmp_path, monkeypatch):
    from PySide6.QtCore import Qt

    from azimuth.core import EXAMPLES, read_xyz
    from azimuth.project_widgets import NEW_ROW

    # Arrange: «+» — an empty project; a methane drawn in it (as with the mouse: the title of the empty molecule)
    empty(window)
    path = Path(window.new_project_tab())
    methane = read_xyz(EXAMPLES['Метан · CH₄'])
    window.load_molecule(Molecule('Новая молекула', methane.atoms, methane.bonds))
    # Act
    assert window.new_molecule_command()
    # Assert: the methane is the first molecule of the project, named by its formula; the empty row after it
    path = window.research_path()
    project = projects.Project.load(path)
    assert [e['name'] for e in project.molecules] == ['CH4']
    table = window.project_molecules
    assert table.rowCount() == 2 and table.item(1, 0).data(Qt.ItemDataRole.UserRole) == NEW_ROW
    # Act: «Удалить из проекта» of the empty row — no error, the row goes, the methane is shown
    errors = []
    monkeypatch.setattr(window, 'error', errors.append)
    assert window.remove_project_molecules([NEW_ROW], delete_files=False) == []
    assert not errors and table.rowCount() == 1 and len(window.own_molecule().atoms) == len(methane.atoms)
    # the folder renamed after the first molecule
    # (auto_name_project, after the action under way) — the second «Новая молекула», drawn in, is the project's too
    from PySide6.QtWidgets import QApplication

    QApplication.processEvents()
    renamed = window.research_path()
    assert renamed.parent.name.startswith('CH4')  # «Новый проект (N)» → «CH4»
    assert window.new_molecule_command() and table.rowCount() == 2
    QApplication.processEvents()
    window.load_molecule(read_xyz(EXAMPLES['Вода · H₂O']))
    assert window.new_molecule_command()
    project = projects.Project.load(window.research_path())
    assert [e['name'] for e in project.molecules] == ['CH4', 'Вода'] and table.rowCount() == 3
    window.remove_project_molecules([NEW_ROW], delete_files=False)
    # Act: an empty draft closed — its folder goes; the project with the methane stays
    empty_draft = Path(window.new_project_tab())
    assert window.empty_draft(empty_draft)
    window.close_project_tab(window.project_sessions.index(empty_draft))
    assert not empty_draft.parent.exists() and len(window.project_sessions) == 1
    assert [e['name'] for e in projects.Project.load(window.project_sessions[0]).molecules] == ['CH4', 'Вода']


def test_a_name_that_is_a_formula_follows_the_molecule(window):
    # the molecule called by its formula and the project of it take the new formula; a name given stays
    from PySide6.QtWidgets import QApplication

    from azimuth.core import EXAMPLES, read_xyz

    empty(window)
    window.new_project_tab()
    methane = read_xyz(EXAMPLES['Метан · CH₄'])
    window.load_molecule(Molecule('Новая молекула', methane.atoms, methane.bonds))
    assert window.new_molecule_command()
    QApplication.processEvents()  # the folder renamed after the molecule
    path = window.research_path()
    assert [e['name'] for e in projects.Project.load(path).molecules] == ['CH4']
    assert projects.Project.load(path).data['name'] == 'CH4'
    ethane = read_xyz(EXAMPLES['Этан · C₂H₆ · перемещение фрагмента'])
    # the molecule of the project made another one (new_molecule_command left «Новая молекула» on screen: back to it)
    window.open_project_molecule(projects.Project.load(path).molecules[0]['id'])
    window.load_molecule(ethane)
    window.save_research_project()
    project = projects.Project.load(window.research_path())
    assert [e['name'] for e in project.molecules] == ['C2H6'] and project.data['name'] == 'C2H6'
    with projects.edit(window.research_path()) as named:  # a name given by the user stays
        named.data['molecules'][0]['name'] = 'Мой этан'
    window.load_molecule(methane)
    window.save_research_project()
    assert projects.Project.load(window.research_path()).molecules[0]['name'] == 'Мой этан'


def test_the_conformers_of_a_molecule_are_a_group_of_the_list(window, tmp_path):
    from dataclasses import replace

    from PySide6.QtCore import Qt

    empty(window)
    window.opening_tool.open_path(ions(tmp_path))
    path = window.research_path()
    table = window.project_molecules
    first = table.item(0, 0).data(Qt.ItemDataRole.UserRole)
    molecule, _ = projects.Project.view(path).read_structure(projects.Project.view(path).entry(first)['structure'])
    found = [(replace(molecule, atoms=tuple(replace(a, x=a.x + 0.01 * k) for a in molecule.atoms)), -10.0 + k, 0.5 * k,
              0.5 / (k + 1)) for k in range(3)]
    assert window.add_project_conformers(path, first, found) == 3
    labels = [table.item(k, 0).text() for k in range(table.rowCount())]
    assert labels == ['1', '1.1', '1.2', '1.3', '2'] and table.item(0, 1).text().startswith('▾ ')
    assert 'конформеров: 3' in table.item(0, 1).text() and 'ΔE 0.50' in table.item(2, 1).text()
    window.toggle_conformers(first)  # folded: the molecule and the next one
    assert table.rowCount() == 2 and table.item(0, 1).text().startswith('▸ ')
    window.set_project_batch_mode(True)
    assert len(window.selected_project_molecules()) == 5  # the conformers of the folded molecule are in the batch
    table.item(0, 0).setCheckState(Qt.CheckState.Unchecked)  # the tick of the molecule takes off its conformers too
    assert len(window.selected_project_molecules()) == 1
    table.item(0, 0).setCheckState(Qt.CheckState.Checked)
    assert len(window.selected_project_molecules()) == 5
    window.toggle_conformers(first)
    table.item(2, 0).setCheckState(Qt.CheckState.Unchecked)  # unfolded: one conformer left out
    chosen = window.selected_project_molecules()
    assert len(chosen) == 4 and table.item(2, 0).data(Qt.ItemDataRole.UserRole) not in chosen
    # a new search replaces the conformers not calculated; the molecule taken out takes them along
    with projects.edit(path) as project:
        assert len(projects.set_conformers(project, first, found[:2])) == 2
        assert [e['conformer']['rank'] for e in projects.conformers_of(project, first)] == [1, 2]
        assert len(projects.removal(project, [first])) == 3
    window.set_project_batch_mode(False)


def test_the_group_of_the_molecule_shown_folds(window, tmp_path):
    # the molecule shown kept its group open; and a conformer shown folds with its group too
    from dataclasses import replace

    from PySide6.QtCore import Qt

    empty(window)
    window.opening_tool.open_path(ions(tmp_path))
    path = window.research_path()
    table = window.project_molecules
    first = table.item(0, 0).data(Qt.ItemDataRole.UserRole)
    molecule, _ = projects.Project.view(path).read_structure(projects.Project.view(path).entry(first)['structure'])
    found = [(replace(molecule, atoms=tuple(replace(a, x=a.x + 0.01 * k) for a in molecule.atoms)), -10.0 + k, 0.5 * k,
              0.5) for k in range(3)]
    window.add_project_conformers(path, first, found)
    document = window.document()
    document.research_molecule_id = first  # the molecule itself is shown
    window.refresh_project_navigation()
    assert table.rowCount() == 5
    assert window.toggle_conformers(first) is False and table.rowCount() == 2
    assert window.toggle_conformers(first) is True and table.rowCount() == 5
    conformer = projects.conformers_of(projects.Project.view(path), first)[0]['id']
    document.research_molecule_id = conformer  # one of its conformers is shown
    window.refresh_project_navigation()
    assert window.toggle_conformers(first) is False and table.rowCount() == 2
    assert window.toggle_conformers(first) is True and table.rowCount() == 5


def test_the_conformers_of_a_molecule_drawn_in_no_project_go_to_its_project(window, tmp_path):
    # the molecule of the
    # tab searched was in no project yet — at the end of the search it gets its project and the conformers go under it
    from dataclasses import replace

    from azimuth.core import read_xyz
    from modules.compass.actions.conformer_actions import ConformerWindow

    empty(window)
    methanol = read_xyz('6\nmethanol\nC 0 0 0\nO 1.42 0 0\nH -0.36 1.03 0\nH -0.36 -0.51 0.89\nH -0.36 -0.51 -0.89\n'
                        'H 1.74 0.9 0')
    window.load_molecule(methanol)
    document = window.document()
    w = ConformerWindow(window)
    try:
        path, ident = w.project_place(document)
        assert path and ident and document.research_molecule_id == ident
        found = [(replace(methanol, atoms=tuple(replace(a, x=a.x + 0.01 * k) for a in methanol.atoms)), -5.0 + k,
                  0.3 * k, 0.5) for k in range(2)]
        assert window.add_project_conformers(path, ident, found) == 2
        assert [e['conformer_of'] for e in projects.conformers_of(projects.Project.view(path), ident)] == [ident] * 2
    finally:
        w.close()
        window.dirty = False
        for d in window.all_documents():
            d.dirty = False


def test_a_sliding_panel_steps_in_even_pixels():
    # what is centred beside
    # the panel moves by half its step — whole pixels only when the step is even
    from azimuth.project_widgets import even_step

    widths = [even_step(v) for v in (0, 0.9, 1.0, 3.2, 4.9, 7.0, 263.6, 300)]
    assert all(w % 2 == 0 for w in widths) and widths == sorted(widths) and widths[-1] == 300


def wait_for(condition, ms=3000):
    """Events run until condition() holds or ms pass (PySide6 has no QTest.qWaitFor)."""
    from time import monotonic

    from PySide6.QtTest import QTest

    end = monotonic() + ms / 1000
    while not condition() and monotonic() < end:
        QTest.qWait(20)
    return condition()


def test_the_conformers_fold_and_unfold_smoothly(window, tmp_path):
    # shown, the rows of the
    # conformers shrink to nothing before they go and grow from nothing when they come
    from dataclasses import replace

    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    from modules.compass.panels.trajectory_drawer import SLIDE_MS

    empty(window)
    window.opening_tool.open_path(ions(tmp_path))
    path = window.research_path()
    table = window.project_molecules
    first = table.item(0, 0).data(Qt.ItemDataRole.UserRole)
    molecule, _ = projects.Project.view(path).read_structure(projects.Project.view(path).entry(first)['structure'])
    found = [(replace(molecule, atoms=tuple(replace(a, x=a.x + 0.01 * k) for a in molecule.atoms)), -10.0 + k, 0.5 * k,
              0.5) for k in range(3)]
    window.add_project_conformers(path, first, found)
    window.show()
    window.project_menu_button.setChecked(True)
    window.toggle_project_molecules()
    QTest.qWait(SLIDE_MS + 100)
    assert table.isVisible() and table.rowCount() == 5
    full = table.verticalHeader().defaultSectionSize()
    widths = [table.columnWidth(k) for k in range(3)]
    assert window.toggle_conformers(first) is False
    assert table.rowCount() == 5 and table.item(0, 1).text().startswith('▸')  # still there, shrinking
    # the fold and the list made again after it; in a loaded full run the frames come late (5 rows still
    # there after FOLD_MS + 150 ms) — waited for, not a fixed pause
    wait_for(lambda: table.rowCount() == 2)
    assert table.rowCount() == 2 and all(table.rowHeight(k) == full for k in range(2))
    # the columns stay as they were
    assert [table.columnWidth(k) for k in range(3)] == widths
    assert window.toggle_conformers(first) is True
    assert table.rowCount() == 5 and table.rowHeight(1) < full  # come in at no height
    wait_for(lambda: all(table.rowHeight(k) == full for k in range(5)))
    assert all(table.rowHeight(k) == full for k in range(5))


def test_the_molecules_of_a_project_are_dragged_one_after_another(window, tmp_path):
    # the rows dropped before another row; a molecule goes with its conformers
    from dataclasses import replace

    from PySide6.QtCore import Qt

    empty(window)
    window.opening_tool.open_path(ions(tmp_path))
    path = window.research_path()
    table = window.project_molecules
    ids = [table.item(k, 0).data(Qt.ItemDataRole.UserRole) for k in range(table.rowCount())]
    assert len(ids) == 2 and table.dragEnabled() and window.project_tabs.isMovable()
    first, second = ids
    molecule, _ = projects.Project.view(path).read_structure(projects.Project.view(path).entry(first)['structure'])
    window.add_project_conformers(path, first, [(replace(molecule, atoms=tuple(replace(a, x=a.x + 0.01 * k)
                                                                                for a in molecule.atoms)), -1.0 + k, 0.5 * k, 0.5)
                                                for k in range(2)])
    assert table.rowCount() == 4  # 1, 1.1, 1.2, 2
    assert window.move_project_molecules([3], 0) is True  # «2» dragged to the top
    shown = [table.item(k, 0).data(Qt.ItemDataRole.UserRole) for k in range(table.rowCount())]
    assert shown[0] == second and shown[1] == first and len(shown) == 4  # the conformers still under their molecule
    assert window.move_project_molecules([0], 1) is False  # dropped where it is: nothing changes
    assert window.move_project_molecules([2], 4) is False  # a conformer alone does not move
    assert [e['id'] for e in projects.ordered(projects.Project.view(path)) if not e.get('conformer_of')] == [second, first]


def test_the_conformers_kept_in_the_project_come_back_to_the_drawer(window, tmp_path):
    # read from the project, on the page «Конформеры» of ☰
    from dataclasses import replace

    from PySide6.QtCore import Qt

    empty(window)
    window.opening_tool.open_path(ions(tmp_path))
    path = window.research_path()
    table = window.project_molecules
    first = table.item(0, 0).data(Qt.ItemDataRole.UserRole)
    project = projects.Project.view(path)
    molecule, _ = project.read_structure(project.entry(first)['structure'])
    window.add_project_conformers(path, first, [(replace(molecule, atoms=tuple(replace(a, x=a.x + 0.01 * k)
                                                                                for a in molecule.atoms)), -1.0 + k, 0.4 * k, 0.5)
                                                for k in range(3)])
    window.drawer.load_conformers((), '')  # as after a restart: nothing on the page
    project = projects.Project.view(path)
    assert window.load_project_conformers(project, project.entry(first)) == 3
    assert len(window.drawer.conformers) == 3 and window.drawer.conformers[1][2] == 0.4
    assert window.drawer.conformers_project and window.trajectory_button.isVisibleTo(window)
    conformer = projects.conformers_of(project, first)[0]
    assert window.load_project_conformers(project, conformer) == 3  # a conformer shown: those of its group


def test_no_word_of_a_molecule_result_over_a_crystal(window, monkeypatch):
    from types import SimpleNamespace

    said = []
    monkeypatch.setattr(window, 'notify', lambda text, ms=0: said.append(text))
    document = SimpleNamespace(result_mismatch=('geometry',))
    monkeypatch.setattr(window, 'compass_mode', 'crystal', raising=False)
    window.stack.setCurrentIndex(0)
    assert window.say_result_mismatch(None, {'name': 'C5H10N2'}, document) == ('geometry',)
    assert not said


def test_the_message_of_a_molecule_goes_with_its_subsection(window):
    # a message told in «Компас · Молекула» goes when
    # «Компас · Кристалл» is chosen
    window.stack.setCurrentIndex(0)
    window.crystal_tool.set_compass_mode('molecule')
    window.notify('Результат «C5H10N2» посчитан для прежних данных молекулы', 12000)
    assert window.notice.text()
    try:
        window.crystal_tool.set_compass_mode('crystal')
        assert window.notice.isHidden() and not window.notice.text()
    finally:
        window.crystal_tool.set_compass_mode('molecule')


def test_a_structure_by_smiles_is_a_new_molecule_of_the_project(window, tmp_path):
    empty(window)
    source = source_queue(tmp_path / 'source')
    path = window.create_research_project(tmp_path / 'project')
    window.import_project_batch(source.folder)
    first = projects.Project.load(path).molecules[0]['id']
    window.open_project_molecule(first, stay=True)
    before = window.own_molecule()
    window.opening_tool.load_smiles('CCO')
    window.save_research_project()
    molecules = projects.Project.load(path).molecules
    assert len(molecules) == PAIR + 1 and window.own_molecule().formula == 'C2H6O'
    assert window.document().research_molecule_id == molecules[-1]['id']
    window.open_project_molecule(first, stay=True)
    assert window.own_molecule().atoms == before.atoms  # the molecule shown before is as it was



def test_the_same_molecule_again_is_asked_about(window, tmp_path, monkeypatch):
    empty(window)
    path = window.create_research_project(tmp_path / 'project')
    # the empty tab is the project's, as after «Новый проект» (new_project_tab); create_research_project, used by the
    # tests only, does not mark it — the first ethanol went into a tab of no project, and nothing was there to compare
    window.project_empty_documents[str(path)] = window.document()
    window.opening_tool.load_smiles('CCO')
    window.save_research_project()
    assert len(projects.Project.load(path).molecules) == 1
    asked = []
    monkeypatch.setattr(window, 'confirm_duplicate_molecule', lambda name: asked.append(name) or False)
    window.opening_tool.load_smiles('CCO')  # the same ethanol, the same shape
    window.save_research_project()
    assert len(asked) == 1 and len(projects.Project.load(path).molecules) == 1
    window.opening_tool.load_smiles('COC')  # dimethyl ether: another molecule, nothing asked
    window.save_research_project()
    assert len(asked) == 1 and len(projects.Project.load(path).molecules) == 2
    # a conformer is not a duplicate: ethanol built from the other end — another shape, nothing asked
    window.opening_tool.load_smiles('OCC')
    window.save_research_project()
    assert len(asked) == 1 and len(projects.Project.load(path).molecules) == 3
    monkeypatch.setattr(window, 'confirm_duplicate_molecule', lambda name: asked.append(name) or True)
    window.opening_tool.load_smiles('CCO')
    window.save_research_project()
    assert len(asked) == 2 and len(projects.Project.load(path).molecules) == 4


def test_a_smiles_typed_on_the_russian_layout_is_hinted():
    from modules.compass.actions.opening_actions import has_cyrillic, latin_layout

    assert has_cyrillic('ССЩ') and not has_cyrillic('CC(=O)O')
    assert latin_layout('ССЩ') == 'CCO' and latin_layout('сс(=щ)щ') == 'cc(=o)o'
    assert latin_layout('С№С') == 'C#C' and latin_layout('с1ссссс1') == 'c1ccccc1'

def test_a_molecule_of_the_project_moved_to_a_new_project(window, tmp_path):
    empty(window)
    source = source_queue(tmp_path / 'source')
    path = window.create_research_project(tmp_path / 'project')
    window.import_project_batch(source.folder)
    first, second = (m['id'] for m in projects.Project.load(path).molecules[:2])
    name = projects.Project.load(path).entry(second)['name']
    new = window.project_molecule_to_new_project(second, move=False)
    assert new and Path(new) != Path(path) and len(projects.Project.load(path).molecules) == PAIR
    assert [m['name'] for m in projects.Project.load(new).molecules] == [name]
    window.activate_project_tab([Path(p).resolve() for p in window.project_sessions].index(Path(path).resolve()))
    assert Path(window.research_path()).resolve() == Path(path).resolve()
    moved = window.project_molecule_to_new_project(second, move=True)
    assert moved and [m['id'] for m in projects.Project.load(path).molecules] == [first]
    assert [m['name'] for m in projects.Project.load(moved).molecules] == [name]


def test_molecules_dragged_onto_the_tab_of_another_project(window, tmp_path):
    # the rows dropped on the tab of
    # another project go there (⌥ / Alt — copied, else moved), and its tab is shown
    empty(window)
    source = source_queue(tmp_path / 'source')
    first_path = window.create_research_project(tmp_path / 'first')
    window.import_project_batch(source.folder)
    second_path = window.create_research_project(tmp_path / 'second')

    def tab(path):
        return [Path(p).resolve() for p in window.project_sessions].index(Path(path).resolve())

    window.activate_project_tab(tab(first_path))
    assert Path(window.research_path()).resolve() == Path(first_path).resolve()
    assert not window.project_tab_takes_molecules(tab(first_path))  # not its own tab
    assert window.project_tab_takes_molecules(tab(second_path))
    first, second = (m['id'] for m in projects.Project.load(first_path).molecules[:2])
    name = projects.Project.load(first_path).entry(second)['name']
    made = window.molecules_to_project_tab(tab(second_path), ids=[second], copy=True)
    assert len(made) == 1 and [m['name'] for m in projects.Project.load(second_path).molecules] == [name]
    assert len(projects.Project.load(first_path).molecules) == PAIR  # copied: it stays
    assert Path(window.research_path()).resolve() == Path(second_path).resolve()  # the tab of the other project
    window.activate_project_tab(tab(first_path))
    moved = window.molecules_to_project_tab(tab(second_path), ids=[first])
    assert len(moved) == 1 and len(projects.Project.load(second_path).molecules) == 2
    assert [m['id'] for m in projects.Project.load(first_path).molecules] == [second]  # moved: it left


def test_several_molecules_carried_gather_into_a_pile(window, tmp_path, app):
    from PySide6.QtCore import QPoint, Qt

    empty(window)
    source = source_queue(tmp_path / 'source')
    path = window.create_research_project(tmp_path / 'project')
    window.import_project_batch(source.folder)
    # the list shows the molecules of the project of the tab in front — one of them opened, as the other tests do
    window.open_project_molecule(projects.Project.load(path).molecules[0]['id'], stay=True)
    window.refresh_project_navigation()
    table = window.project_molecules
    window.show()
    app.processEvents()
    pictures = [table.row_picture(row) for row in range(table.rowCount())]
    assert len(pictures) >= 2 and all(not p.isNull() for p, _ in pictures)
    pile = table.pile_picture([p for p, _ in pictures], len(pictures))
    row = pictures[0][0]
    assert pile.width() / pile.devicePixelRatio() > row.width() / row.devicePixelRatio()  # wider: the cards under it
    rows = list(range(table.rowCount()))
    ids = [table.item(row, 0).data(Qt.ItemDataRole.UserRole) for row in rows]
    cursor = window.mapToGlobal(QPoint(10, 10))
    group = table.gather(pictures, cursor, rows)
    assert group.animationCount() == 2  # the pictures fly in one layer (opaque, no fading) and the rows close
    group.setCurrentTime(group.duration())
    app.processEvents()
    header = table.verticalHeader()
    assert all(header.sectionSize(row) == 0 for row in rows)  # they left their places for the pile
    # released, the pile comes to the list whole, then falls apart
    back = table.lay_back(pictures, cursor, ids, pile)
    assert back.animationCount() == 2  # the way of the pile, then the spreading
    from azimuth.project_widgets import flight

    layer, motion = flight(window, [(row, QPoint(0, 0), QPoint(0, 40)), (row, QPoint(0, 0), QPoint(0, 80))], 100)
    motion.setCurrentTime(50)  # the first picture on top: drawn last (paintEvent goes from the last one)
    assert layer.shown[0].top() < layer.shown[1].top()
    motion.setCurrentTime(100)
    back.setCurrentTime(back.duration())
    app.processEvents()
    assert all(header.sectionSize(row) == header.defaultSectionSize() for row in rows)


def test_molecules_dropped_on_plus_make_a_new_project(window, tmp_path):
    empty(window)
    source = source_queue(tmp_path / 'source')
    path = window.create_research_project(tmp_path / 'project')
    window.import_project_batch(source.folder)
    ids = [m['id'] for m in projects.Project.load(path).molecules[:2]]
    names = [projects.Project.load(path).entry(i)['name'] for i in ids]
    assert window.new_project_plus.acceptDrops()
    copied = window.molecules_to_new_project(ids=ids, copy=True)
    assert copied and Path(copied).resolve() != Path(path).resolve()
    assert [m['name'] for m in projects.Project.load(copied).molecules] == names
    assert len(projects.Project.load(path).molecules) == PAIR  # copied: they stay
    assert Path(window.research_path()).resolve() == Path(copied).resolve()  # the new project shown
    window.activate_project_tab([Path(p).resolve() for p in window.project_sessions].index(Path(path).resolve()))
    moved = window.molecules_to_new_project(ids=ids[:1])
    assert [m['name'] for m in projects.Project.load(moved).molecules] == names[:1]
    assert [m['id'] for m in projects.Project.load(path).molecules] == ids[1:]  # moved: it left


def test_molecules_carried_by_the_program_are_put_back_elsewhere(window, tmp_path):
    # several rows are carried by
    # the program; let go nowhere — put back, nothing changed; the window knows the places
    empty(window)
    source = source_queue(tmp_path / 'source')
    path = window.create_research_project(tmp_path / 'project')
    window.import_project_batch(source.folder)
    table = window.project_molecules
    assert table.hover_at == window.molecules_hover and table.drop_at == window.molecules_drop
    before = [m['id'] for m in projects.Project.load(path).molecules]
    window.molecules_hover(None)
    assert window.project_tabs.drop_target == -1 and not window.new_project_plus.property('dropLit')
    assert window.molecules_drop(None, [0, 1], False) is None
    assert [m['id'] for m in projects.Project.load(path).molecules] == before


def test_the_columns_of_the_list_the_history_and_a_name_found(window, tmp_path):
    from azimuth.project_widgets import COLUMNS, COLUMNS_KEY

    window.preferences.remove(COLUMNS_KEY)
    try:
        empty(window)
        window.opening_tool.open_path(ions(tmp_path))
        table = window.project_molecules
        keys = [key for key, _, _ in COLUMNS]
        method, energy = keys.index('method'), keys.index('energy')
        assert table.horizontalHeaderItem(method).text() == 'Метод' and not table.isColumnHidden(method)
        assert table.isColumnHidden(energy) and table.item(0, method).text() == ''  # not calculated yet
        window.show_project_column('energy', True)
        assert not table.isColumnHidden(energy) and 'energy' in window.project_columns_state()['shown']
        window.show_project_column('energy', False)
        assert table.isColumnHidden(energy)
        table.setColumnWidth(keys.index('formula'), 91)  # as the user drags it
        assert window.project_columns_state()['widths']['formula'] == 91
        window.refresh_project_navigation()
        assert table.columnWidth(keys.index('formula')) == 91
        window.reset_project_column_widths()
        assert window.project_columns_state()['widths'] == {}
        first = window.document().research_molecule_id
        assert window.project_attempt_count(first) == 0  # «История расчётов молекулы…» grey
        with projects.edit(window.research_path()) as project:
            project.entry(first)['name'] = 'Cl'  # a name given by the program (its formula)
        assert window.name_found('хлорид-ион')
        view = projects.Project.view(window.research_path())
        assert view.entry(first)['name'] == 'хлорид-ион' and table.item(0, 1).text().startswith('хлорид-ион')
        assert window.name_found('chloride')  # a name of a search follows the next search
        with projects.edit(window.research_path()) as project:
            project.entry(first)['name'], project.entry(first)['name_source'] = 'Мой ион', ''
        assert not window.name_found('хлорид-ион')  # a name the user gave stays
    finally:
        window.preferences.remove(COLUMNS_KEY)


def test_a_cell_cut_to_dots_shows_its_whole_text_on_hover(window, tmp_path, monkeypatch):
    from PySide6.QtCore import QEvent, QPoint
    from PySide6.QtGui import QHelpEvent
    from PySide6.QtWidgets import QToolTip

    from azimuth.project_widgets import COLUMNS_KEY

    shown = []
    monkeypatch.setattr(QToolTip, 'showText', lambda point, text, *rest: shown.append(text))
    try:
        empty(window)
        window.opening_tool.open_path(ions(tmp_path))
        table = window.project_molecules
        item = table.item(0, 1)

        def hover():
            point = table.visualItemRect(item).center()
            table.viewportEvent(QHelpEvent(QEvent.Type.ToolTip, point, table.viewport().mapToGlobal(point)))

        table.setColumnWidth(1, 400)
        hover()
        assert shown == []  # it fits: nothing to say
        table.setColumnWidth(1, 30)
        hover()
        assert shown == [item.text().strip()]
    finally:
        window.preferences.remove(COLUMNS_KEY)


def test_under_a_work_a_new_project_is_made_not_opened(window, tmp_path, monkeypatch):
    from azimuth import tasks

    empty(window)
    path = window.create_research_project(tmp_path / 'project')
    monkeypatch.setitem(tasks._WORK, 'title', 'Расчёт IGMH…')
    before = len(window.project_sessions)
    made = window.new_project_from_plus()
    assert made and len(window.project_sessions) == before + 1
    assert Path(window.research_path()).resolve() == Path(path).resolve()  # the project shown stays

    def said():
        toast = getattr(window, '_page_toast', None)
        return window.notice.text() + (toast.text() if toast is not None else '')

    assert 'когда закончится' in said()
    index = [Path(p).resolve() for p in window.project_sessions].index(Path(made).resolve())
    window.project_tabs.setCurrentIndex(index)  # a press on its tab under the work: not opened
    assert Path(window.research_path()).resolve() == Path(path).resolve()
    assert 'Расчёт IGMH' in said()  # said why
    monkeypatch.setitem(tasks._WORK, 'title', '')
    window.project_tabs.setCurrentIndex(index)  # the work done: opened
    assert Path(window.research_path()).resolve() == Path(made).resolve()


def test_a_project_of_calculations_done_elsewhere(window, tmp_path, monkeypatch):
    # «Файл → Создать проект из
    # расчётов…» — the folder of calculations becomes a project, opened on its molecules with their results
    from tests.projects.test_project_import import calculations

    source = calculations(tmp_path)
    monkeypatch.setattr(window, 'projects_root', lambda kind=None: tmp_path / 'projects')
    said = []
    monkeypatch.setattr(window, 'notify', lambda text, ms=8000: said.append(text))
    window.dirty = False
    manifest = window.project_from_calculations(str(source), 'Расчёты ORCA')
    assert manifest is not None and window.research_path() == manifest
    assert window.project_molecules.rowCount() == 2 and any('3 с результатом из 3' in t for t in said), said


def test_the_list_opened_in_the_crystal_makes_no_project_of_the_molecule(window):
    # 0.249.7, the owner: «открываю кристалл, затем открываю список структур, у меня открывается снова молекула с
    # новым проектом воды, и так каждый раз»
    empty(window)
    window.opening_tool.load_smiles('O')
    window.stack.setCurrentIndex(0)
    window.crystal_tool.set_compass_mode('molecule')
    before = list(window.project_sessions)
    try:
        window.crystal_tool.set_compass_mode('crystal')
        for _ in range(2):
            window.project_menu_button.setChecked(True)
            window.toggle_project_molecules()
            window.project_menu_button.setChecked(False)
            window.toggle_project_molecules()
        assert window.project_sessions == before
        assert window.compass_mode == 'crystal'
    finally:
        window.crystal_tool.set_compass_mode('molecule')
