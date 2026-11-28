"""Window tests — Multiwfn and the analyses of the density: charges, surfaces, topology, orbitals on the model (split
from test_gui.py on 2026-11-08)."""

from tests.gui_support import *  # noqa: F401,F403 — the fixtures app, window and the helpers


def test_orbital_and_esp_surfaces_in_compass(window, app):
    # from the orbital window to the Compass model: the HOMO of water (two phases), the level, the
    # opacity, an edit hides it and undo shows it again, the ESP map with its scale, «Убрать поверхность»
    pytest.importorskip('vtk')
    from modules.spectrum.analysis.orbitals import density_cube

    show_model(window, app)
    window.dirty = False
    text = (Path(__file__).parents[1] / 'data' / 'orbitals' / 'molden5.7_water_mp2.molden').read_text(encoding='utf-8')
    dialog = window.open_orbitals_text(text, 'water.molden')
    try:
        # the ESP is Multiwfn's and reads the file of the orbitals: orbitals given as text have no ESP button
        assert dialog.target.currentData() == 'compass' and not dialog.esp_button.isVisibleTo(dialog)
        homo, _ = dialog.orbital_set.frontier()
        dialog.select(homo)
        dialog.show_orbital()
        surface = window.viewer.surface
        assert surface is not None and len(surface['meshes']) == 2 and window.stack.currentIndex() == 0
        assert [a.symbol for a in window.molecule.atoms] == ['O', 'H', 'H']
        window.viewer.resize(500, 400)
        shown = window.viewer.surface_triangles()
        assert shown is not None and len(shown[1]) == sum(len(m.triangles) for m in surface['meshes'])
        # the vertices VTK draws are where QPainter draws them; the fine meshes are built on demand
        import numpy as np

        mine = np.concatenate([window.viewer.project_vertices(m.vertices)[m.triangles][:, :, :2] for m in surface['meshes']])
        assert np.allclose(np.sort(mine.ravel()), np.sort(shown[0].ravel()), atol=1e-9)
        fine, opacity = window.viewer.surface_meshes()
        assert len(fine) == 2 and opacity == surface['opacity'] and surface['fine'] is fine
        assert sum(len(m.triangles) for m in fine) >= sum(len(m.triangles) for m in surface['meshes'])
        assert window.viewer.surface_meshes(fine=False)[0] is surface['meshes']
        window.viewer.grab()
        assert window.surface_tool.set_surface_level(0.08)
        assert sum(len(m.triangles) for m in window.viewer.surface['meshes']) > 0
        window.surface_tool.set_surface_opacity(1.0)
        assert window.viewer.surface['opacity'] == 1.0
        window.surface_tool.fill_surface_menu(window.surface_menu)
        assert any(a.text() == 'Убрать поверхность' for a in window.surface_menu.actions())
        moved = window.molecule.atoms[1]
        window.model_menu_tool.edit_structure(replace(window.molecule, atoms=(window.molecule.atoms[0], replace(moved, x=moved.x + 0.2), window.molecule.atoms[2])))
        assert window.viewer.surface_triangles() is None  # another structure: not drawn
        window.undo_geometry()
        assert window.viewer.surface_triangles() is not None
        cube = density_cube(dialog.orbital_set, step=0.15)
        with pytest.raises(ValueError):  # no map of the Mulliken point charges any more
            window.surface_tool.show_surface(cube, 'esp', dialog.orbital_set, title='ESP')
        window.surface_tool.clear_surface()
        assert window.viewer.surface is None
    finally:
        dialog.close()


def test_density_panel_in_compass(window, app):
    # a field put on the model from the orbital window of Spectrum hands the work over to Compass (the window
    # hides) with the orbitals, ρ, the ESP, −∇²ρ, QTAIM and the slice for the same orbitals. These are the
    # pages «Орбитали» (Орбитали | Поверхности) and «QTAIM» (Точки | Срез) of the drawer on the left, its ☰ closes and
    # opens it on the same page; another tab drops them. «Орбитали», «Поверхности», «QTAIM» — pages of their
    # own; the button of what is on the model blue, its row lit; the grids kept
    pytest.importorskip('vtk')
    show_model(window, app)
    window.dirty = False
    text = (Path(__file__).parents[1] / 'data' / 'orbitals' / 'molden5.7_water_mp2.molden').read_text(encoding='utf-8')
    dialog = window.open_orbitals_text(text, 'water.molden')
    drawer = window.density_drawer
    try:
        homo, _ = dialog.orbital_set.frontier()
        dialog.select(homo)
        dialog.show_orbital()
        assert not dialog.isVisible() and drawer.isVisible() and window.trajectory_button.isChecked()
        # no graphics effect on the drawer (with it the drawer was not painted after a hand-over of QTAIM);
        # its shadow is a widget of its own on its right
        panel_frame = window.drawer
        assert panel_frame.graphicsEffect() is None and panel_frame.shadow.isVisible()
        assert panel_frame.shadow.geometry().left() == panel_frame.geometry().right() + 1
        assert window.drawer.page() == 'orbitals' and window.drawer.tab_bar.isTabEnabled(2) and not window.browsing
        assert not hasattr(window, 'density_button')  # no panel on the right any more
        assert drawer.orbital_set is dialog.orbital_set
        # three pages of the drawer, no sub-tabs; the model moved right by half of the drawer
        assert window.drawer.tab_bar.tabText(3) == 'Поверхности' and window.drawer.tab_bar.isTabEnabled(3)
        # the pages in a drop-down list — only those with something in them; the width of before
        chooser = window.drawer.tab_bar
        offered = [chooser.tabText(k) for k in chooser.offered_pages()]
        assert {'Орбитали', 'Поверхности', 'QTAIM'} <= set(offered) and window.drawer.width() == 372
        assert ('Частоты' in offered) == bool(window.drawer.modes) and ('Оптимизация' in offered) == bool(window.drawer.steps)
        assert chooser.count() == 6 and chooser.findData(3) >= 0
        super(type(chooser), chooser).setCurrentIndex(chooser.findData(3))  # the user picks «Поверхности» in the list
        assert window.drawer.page() == 'surfaces'
        window.drawer.set_page('orbitals')
        assert window.viewer.inset == window.drawer.width()
        assert window.stack.currentIndex() == 0
        assert drawer.orbitals_table.rowCount() == len(dialog.orbital_set.orbitals) and drawer.current_orbital() == homo
        assert all(drawer.orbitals_table.item(homo, c).textAlignment() & Qt.AlignmentFlag.AlignHCenter for c in range(4))
        assert not hasattr(drawer, 'density_button') and not hasattr(drawer, 'esp_button')  # ρ and ESP: «Поверхности»
        assert not drawer.spin_button.isVisibleTo(window.drawer)  # a closed shell
        drawer.grids[0].setCurrentIndex(0)  # coarse: quick
        assert drawer.step.currentIndex() == 0 and drawer.grids[1].currentIndex() == 0  # one grid on every page
        # the orbital is on the model: its row lit, the button blue; a second press takes it away, the button white
        assert drawer.orbitals_table.item(homo, 0).font().bold() and drawer.orbital_button.property('on')
        # the light set again touches only the rows it changes: every cell was set at each call, and the table of the
        # orbitals of caffeine stood the window for 10–15 s on Windows (2026-11-28)
        from PySide6.QtWidgets import QTableWidgetItem

        touched = []
        original = QTableWidgetItem.setFont
        QTableWidgetItem.setFont = lambda item, font: (touched.append(item.row()), original(item, font))
        try:
            drawer.refresh_lights()
            assert touched == []  # nothing changed — nothing set
            drawer.orbitals_table.lit_rows = {homo - 1}  # as if the row before had been lit
            drawer.refresh_lights()
            assert set(touched) == {homo - 1, homo}
        finally:
            QTableWidgetItem.setFont = original
        assert drawer.orbitals_table.item(homo, 0).font().bold() and not drawer.orbitals_table.item(homo - 1, 0).font().bold()
        drawer.orbital_button.click()
        assert window.surface_source is None and drawer.shown is None and not drawer.orbital_button.property('on')
        assert not drawer.orbitals_table.item(homo, 0).font().bold()
        drawer.orbital_button.click()  # built here now
        cube = window.surface_source['cube']
        assert drawer.cubes and drawer.orbital_button.property('on')
        drawer.orbital_button.click()
        drawer.orbital_button.click()  # shown again from what was built — the same grid, nothing computed
        assert window.surface_source['kind'] == 'orbital' and window.surface_source['cube'] is cube
        assert drawer.orbital_button.property('on')
        drawer.orbitals_table.selectRow(homo - 1)  # another row: the button white, the row shown stays lit
        assert not drawer.orbital_button.property('on') and drawer.orbitals_table.item(homo, 0).font().bold()
        assert drawer.show_density() and window.surface_source['kind'] == 'density'
        assert not drawer.orbitals_table.item(homo, 0).font().bold()
        window.surface_tool.clear_surface()  # from the menu: nothing lit any more
        assert drawer.shown is None
        drawer.orbitals_table.selectRow(homo)
        host = window.drawer.orbitals_host  # the content takes the whole height of the page
        assert host.stretch(host.count() - 1) == 0 and host.stretch(0) == 1
        assert drawer.show_orbital() and window.surface_source['kind'] == 'orbital'
        assert not drawer.spinners['orbitals'].running()  # the ring turned only while it was computed
        # Shift+click on another row puts
        # it over the first one with colours of its own; again — it goes; the row chosen stays (Qt, QTest: gui_support)
        drawer.orbitals_table.show()
        meshes = len(window.viewer.surface['meshes'])
        other = homo - 1
        cell = drawer.orbitals_table.visualItemRect(drawer.orbitals_table.item(other, 0)).center()
        QTest.mouseClick(drawer.orbitals_table.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ShiftModifier, cell)
        assert drawer.overlay_rows() == [other] and drawer.current_orbital() == homo
        assert len(window.viewer.surface['meshes']) > meshes and ' + ' in window.viewer.surface['legend']
        colours = {m.color for m in window.viewer.surface['meshes']}
        assert '#2e9e5b' in colours or '#d9a12b' in colours  # the second pair
        assert drawer.orbitals_table.item(other, 0).font().bold() and drawer.orbitals_table.item(homo, 0).font().bold()
        assert drawer.toggle_overlay(other) == [] and len(window.viewer.surface['meshes']) == meshes
        assert drawer.toggle_overlay(other) == [other]
        assert drawer.show_orbital() and drawer.overlay_rows() == []  # shown anew: alone, no orbitals over it
        drawer.orbitals_table.selectRow(homo)
        # the surfaces are Multiwfn's and need the file of the orbitals — given as text, there is none
        assert not drawer.update_surfaces_page() and not drawer.surfaces_list.isEnabled()
        assert 'файл этих орбиталей' in drawer.surfaces_hint.text()
        # a tree — the groups are branches, the surfaces their leaves
        texts = [item.text(0).strip() for item in drawer.surface_items()]
        assert 'Плотность и её производные' in drawer.surface_groups() and any(t.startswith('ELF') for t in texts)
        assert 'Плотность и её производные' not in texts
        assert all(drawer.surfaces_list.topLevelItem(g).isExpanded() for g in range(len(drawer.surface_groups())))
        assert not any(t.startswith('Спиновая') for t in texts)  # a closed shell
        assert drawer.current_choice(drawer.surfaces_list.topLevelItem(0)) is None  # a group is not a surface
        # Δρ — a heading, the steps, icon buttons; «Убрать» and «Показать Δρ» wait for the fragments
        panel = drawer.panel
        assert not panel.add_fragment_button.text() and panel.add_fragment_button.toolTip().startswith('Добавить')
        assert not panel.drop_fragment_button.isEnabled() and not panel.difference_button.isEnabled()
        # the meaning and the steps of Δρ behind «?» of its heading, no lines of the page
        assert panel.fragment_steps.text() == '?' and '«+»' in panel.fragment_steps.help and 'ρ(молекула)' in panel.fragment_steps.help
        window.drawer.set_page('surfaces')
        assert drawer.isVisible() and window.drawer.pages.currentIndex() == 3
        assert drawer.panel.surfaces_page.isVisibleTo(window.drawer)  # Δρ under the list is there
        window.drawer.set_page('aim')
        assert drawer.isVisible() and window.drawer.pages.currentIndex() == 4 and drawer.panel is not None
        # the page was empty — the points, the button and the list are seen
        assert drawer.panel.aim_page.isVisibleTo(window.drawer) and drawer.panel.table.isVisibleTo(window.drawer)
        assert drawer.panel.find_button.isVisibleTo(window.drawer)
        # the critical points are Multiwfn's, it reads the file of the orbitals — given as text, there is none
        assert not drawer.panel.find_button.isEnabled() and drawer.panel.find_points() is None
        assert drawer.panel.table.columnCount() == 6  # the short list — type, atoms, ρ, ∇²ρ, H; + №
        # «Перейти в Спектр» on every page of the panel
        assert window.drawer.spectrum_button.isVisibleTo(window.drawer)
        assert window.drawer.spectrum_button.property('quail_icon') == 'spectrum'
        window.drawer.close_button.click()
        assert drawer.isHidden() and not window.trajectory_button.isChecked() and window.viewer.inset == 0
        window.trajectory_button.click()
        assert drawer.isVisible() and drawer.panel is not None and window.drawer.page() == 'aim'
        window.new_document()
        assert drawer.panel is None and not window.drawer.tab_bar.isTabEnabled(2)
        assert window.trajectory_button.isHidden()  # an empty tab — nothing for the drawer, no ☰
        window.close_document(window.current_document)
    finally:
        window.surface_tool.clear_aim()
        window.surface_tool.clear_surface()
        dialog.close()
        window.trajectory_tool.set_trajectory_open(False)
        for d in window.all_documents():
            d.dirty = False
        window.dirty = False


def test_electron_density_window(window, app, tmp_path):
    # «Анализ ЭП…» of the orbital window: −∇²ρ and Δρ on the Compass model, the QTAIM table and the points
    # with the bond paths on the model, the slice map and its pictures; the points are Multiwfn's (a fake one
    # with the recorded CPprop.txt of this water), the orbitals opened from their file
    pytest.importorskip('vtk')
    show_model(window, app)
    window.dirty = False
    fchk = tmp_path / 'water.fchk'
    fchk.write_text((Path(__file__).parents[2] / 'examples' / '6-orbitals' / 'water_mp2_gaussian16.fchk')
                    .read_text(encoding='utf-8'), encoding='utf-8')
    old = window.preferences.value('multiwfn_program', '')
    window.preferences.setValue('multiwfn_program', str(fake_multiwfn(tmp_path)))
    orbitals = window.open_orbitals_path(fchk)
    assert orbitals.esp_button.isVisibleTo(orbitals)
    d = orbitals.density_analysis()
    try:
        assert orbitals.density_analysis() is d and d.target.currentData() == 'compass'
        assert not hasattr(d, 'laplacian') and not hasattr(d, 'draw_slice')  # Multiwfn's, and in Spectrum
        assert [d.tabs.tabText(k) for k in range(d.tabs.count())] == ['QTAIM', 'Разность Δρ']
        d.step.setCurrentIndex(0)  # the coarse grid: quick
        d.add_fragment(orbitals.orbital_set, 'water again')
        cube, integral = d.difference()
        assert abs(integral) < 1e-9 and '∫Δρ' in d.status.text()
        assert d.find_button.isEnabled()
        top = d.find_points()
        # all the points — the 3 nuclei and the 2 bonds; the bond atoms from Multiwfn; the detailed table
        assert top is not None and d.table.rowCount() == 5 and '✓' in d.aim_summary.text()
        # the folder of the tables of the points («Анализ» next to the file of the orbitals) at one click
        assert d.folder_button.isEnabled() and d.tables_place() == tmp_path / 'Анализ'
        assert (tmp_path / 'Анализ' / 'water_qtaim_bonds.csv').is_file()
        assert d.table.columnCount() == 17 and d.table.horizontalHeaderItem(15).text() == 'λ2'
        # the interaction named — the O–H of water are chemical bonds, the nuclei have none
        assert d.table.horizontalHeaderItem(3).text() == 'Взаимодействие'
        assert [d.table.item(k, 3).text() for k in range(5)] == ['', '', '', 'ковалентная связь', 'ковалентная связь']
        assert 'Без критической точки' not in d.aim_summary.text()
        assert not (tmp_path / 'Анализ' / 'water_qtaim_contacts.csv').exists()
        # the points numbered within their kind — the nuclei by atom, then the bonds
        assert [d.table.item(k, 0).text() for k in range(5)] == ['n1', 'n2', 'n3', 'b1', 'b2']
        assert not d.table.isColumnHidden(1)
        assert d.kind_filter.itemText(0).endswith('· 5') and d.kind_filter.itemText(2).endswith('· 2')
        assert d.model_button.text() == 'Показать на модели Компаса'
        assert d.points_on_model()
        assert d.model_button.text() == 'Убрать с модели' and d.model_button.isChecked()
        aim = window.viewer.aim
        assert len(aim['points']) == 5 and len(aim['paths']) == 2 and aim['selected'] is None
        assert aim['labels'] == ['n1', 'n2', 'n3', 'b1', 'b2']  # drawn next to the points
        # the weak interactions of the search are drawn as bonds of their kind — water has none; given,
        # they are drawn (an atom out of the molecule left out) and stay when the points go
        found = window.viewer.found_contacts
        assert found['contacts'] == [] and found['atoms'] == window.molecule.atoms
        found['contacts'] = [(0, 1, 'hydrogen'), (1, 2, 'vdw'), (0, 2, 'halogen'), (0, 99, 'vdw')]
        assert window.viewer.aim_contacts() == found['contacts'][:3]
        window.viewer.resize(400, 300)
        window.viewer.grab()
        window.surface_tool.clear_aim()
        assert window.viewer.aim is None and len(window.viewer.aim_contacts()) == 3
        assert d.points_on_model()  # the points again (the search has none: the lines of water — none)
        assert window.viewer.aim_contacts() == []
        # the hand-over: the drawer of Compass and the tab «Топология ЭП» of Spectrum got the same points
        panel = window.density_drawer.panel
        assert panel is not None and panel.topology is top and panel.table.columnCount() == 6
        assert panel.model_button.text() == 'Убрать с модели'
        assert window.topology_panel.topology is top and window.topology_panel.table.rowCount() == 5
        # in Spectrum a click only chooses the row (no jump to Compass), a double click marks it there; the
        # button of the model is the icon of Compass
        spectrum = window.topology_panel
        assert spectrum.model_button.property('quail_icon') == 'compass' and spectrum.model_button.text() == ''
        assert [spectrum.table.item(k, 0).text() for k in range(5)] == ['n1', 'n2', 'n3', 'b1', 'b2']
        window.navigate(2)
        spectrum.table.selectRow(4)  # the mark follows on the model, Spectrum stays
        assert window.stack.currentIndex() == 2 and window.viewer.aim['selected'] is not None
        spectrum.kind_filter.setCurrentIndex(spectrum.kind_filter.findData('bond'))
        assert window.stack.currentIndex() == 2 and window.viewer.aim['labels'] == ['b1', 'b2']
        spectrum.kind_filter.setCurrentIndex(0)
        spectrum.table.selectRow(4)
        spectrum.table.cellDoubleClicked.emit(4, 2)
        assert window.stack.currentIndex() == 0 and window.viewer.aim['selected'] is not None
        # only the kind of the point opened (a bond) goes to the model; the panel of Compass follows it
        assert window.viewer.aim['labels'] == ['b1', 'b2'] and len(window.viewer.aim['paths']) == 2
        compass = window.density_drawer.panel
        assert compass.kind_filter.currentData() == 'bond' and compass.table.rowCount() == 2
        assert spectrum.kind_filter.currentData() == 'all' and spectrum.table.rowCount() == 5
        spectrum.table.clearSelection()
        d.points_on_model()
        assert compass.kind_filter.currentData() == 'all' and window.viewer.aim['labels'] == ['n1', 'n2', 'n3', 'b1', 'b2']
        d.kind_filter.setCurrentIndex(d.kind_filter.findData('bond'))
        assert d.table.rowCount() == 2 and len(window.viewer.aim['points']) == 2
        assert d.table.item(0, 2).text() == 'O1–H2' and d.table.item(1, 2).text() == 'O1–H3'
        # one kind — no column «Тип», the same numbers as in the table of all the points
        assert d.table.isColumnHidden(1) and window.viewer.aim['labels'] == ['b1', 'b2']
        d.table.selectRow(1)  # the row is marked on the model — a pulsing ring
        assert window.viewer.aim['selected'] is not None
        window.viewer.resize(500, 400)
        window.viewer.show()
        window.viewer.repaint()
        assert window.viewer._pulse.isActive()
        assert window.viewer.pulse_radius(0.0) == (6.5, 1.0)
        assert window.viewer.pulse_radius(window.viewer.PULSE_PERIOD / 2)[0] == pytest.approx(15.0)
        # a second click on the row, Esc or a click on the empty field of the model let the point go (Qt, QTest:
        # gui_support)
        d.table.show()
        cell = d.table.visualItemRect(d.table.item(1, 0)).center()
        QTest.mouseClick(d.table.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, cell)
        assert not d.table.selectionModel().hasSelection() and window.viewer.aim['selected'] is None
        d.table.selectRow(1)
        assert window.viewer.aim['selected'] is not None
        QTest.keyClick(d.table, Qt.Key.Key_Escape)
        assert not d.table.selectionModel().hasSelection() and window.viewer.aim['selected'] is None
        d.table.selectRow(1)
        assert window.surface_tool.unmark_aim() and window.viewer.aim['selected'] is None
        assert not d.table.selectionModel().hasSelection() and window.viewer.aim['points']  # the points stay
        d.table.selectRow(1)
        window.viewer.emptyClicked.emit()
        assert window.viewer.aim['selected'] is None
        d.kind_filter.setCurrentIndex(d.kind_filter.findData('nucleus'))
        assert d.table.rowCount() == 3 and not window.viewer.aim['paths'] and d.table.item(0, 2).text() == 'O1'
        d.kind_filter.setCurrentIndex(d.kind_filter.findData('ring'))
        assert d.table.rowCount() == 0
        d.kind_filter.setCurrentIndex(0)
        window.viewer.grab()
        window.surface_tool.fill_surface_menu(window.surface_menu)
        assert any(a.text() == 'Убрать критические точки' for a in window.surface_menu.actions())
        assert 'ρ' in d.table_text() and 'O1–H2' in d.table_text()
        # one button takes the points away, and every view of them follows
        assert not d.toggle_points() and window.viewer.aim is None
        panel = window.density_drawer.panel  # the panel of Compass may be built again while going between them
        assert panel is not None and panel.topology is top
        assert d.model_button.text() == 'Показать на модели Компаса' and panel.model_button.text() == 'На модель'
        window.viewer._pulse_tick()
        assert not window.viewer._pulse.isActive()
        assert panel.toggle_points() and window.viewer.aim is not None
        window.surface_tool.clear_aim()
        assert window.viewer.aim is None
    finally:
        window.preferences.setValue('multiwfn_program', old)
        d.close()
        orbitals.close()


def test_orbitals_of_an_orca_result_from_its_gbw(window, app, tmp_path, monkeypatch):
    # an ORCA result keeps its orbitals in <name>.gbw: Spectrum offers «Орбитали…» and Compass «Орбитали и
    # плотность этого расчёта…» and «Анализ электронной плотности…»; the Molden file is made by orca_2mkl on demand
    import shutil

    from modules.sextant import runner

    data = Path(__file__).parents[1] / 'data'
    out = tmp_path / 'input.out'
    shutil.copy(data / 'orca_cclib' / 'water_mp2_orca5.0.out', out)
    (tmp_path / 'input.gbw').write_bytes(b'orbitals')
    window.open_output_path(str(out), show=False)
    assert window.result_orbitals() == tmp_path / 'input.gbw' and not window.orbitals_button.isHidden()
    window.surface_tool.fill_surface_menu(window.surface_menu)
    texts = [a.text() for a in window.surface_menu.actions()]
    assert 'Орбитали и плотность…' in texts and 'Поверхности…' in texts and 'Критические точки (QTAIM)…' in texts
    assert all(len(a.toolTip()) < 60 for a in window.surface_menu.actions() if a.text())  # short tooltips
    molden = tmp_path / 'input.molden.input'
    shutil.copy(data / 'orbitals' / 'molden5.7_water_mp2.molden', molden)
    monkeypatch.setattr(runner, 'molden_from_gbw', lambda gbw, configured=None: molden)
    dialog = window.open_sibling_orbitals(analysis=True)
    try:
        assert dialog is not None and dialog.density_dialog is not None and window.sibling_molden == molden
    finally:
        if dialog.density_dialog is not None:
            dialog.density_dialog.close()
        dialog.close()
    for d in window.all_documents():
        d.dirty = False
    window.dirty = False


def test_multiwfn_charges_on_the_model(window, app, tmp_path):
    # «±» → «Заряды ADCH и CM5 (Multiwfn)…» on the wavefunction of the result: a fake Multiwfn prints the
    # outputs of Multiwfn 2026.7.15 recorded for the water of examples/6-orbitals; the charges go onto the model (ADCH
    # chosen), CM5 is in the menu, the output is kept next to the file
    from PySide6.QtWidgets import QMenu

    data = Path(__file__).parents[1] / 'data' / 'multiwfn'
    both = tmp_path / 'both.txt'
    both.write_text((data / 'water_fchk_adch_2026.7.15.txt').read_text(encoding='utf-8')
                    + (data / 'water_fchk_cm5_2026.7.15.txt').read_text(encoding='utf-8'), encoding='utf-8')
    fake = fake_program(tmp_path, f'''
if not os.path.isfile('input.fchk'):
    sys.exit(3)
cat({q(both)})
''')
    folder = tmp_path / 'Расчёт воды'
    folder.mkdir()
    fchk = folder / 'water.fchk'
    fchk.write_text((Path(__file__).parents[2] / 'examples' / '6-orbitals' / 'water_mp2_gaussian16.fchk')
                    .read_text(encoding='utf-8'), encoding='utf-8')
    old = window.preferences.value('multiwfn_program', '')
    window.preferences.setValue('multiwfn_program', str(fake))
    window.result_properties, window.result_source = None, ''
    window.sibling_molden, window.sibling_gbw = fchk, None
    try:
        menu = QMenu()
        window.property_tool.fill_properties_menu(menu)
        item = next(a for a in leaf_actions(menu) if a.text().startswith('Заряды ADCH и CM5'))
        assert item.isEnabled()
        assert window.property_tool.multiwfn_charges()
        props = window.result_properties
        assert props.charges['adch'] == (-0.58474246, 0.29237123, 0.29237123)
        assert props.charges['cm5'][0] == pytest.approx(-0.6149238)
        assert window.overlay_choice['atom'] == 'adch'
        assert (folder / 'Анализ' / 'water_multiwfn_charges.txt').is_file()  # the subfolder «Анализ»
        window.property_tool.fill_properties_menu(menu)
        titles = {a.text(): a.isEnabled() for a in leaf_actions(menu)}
        assert titles['Заряды ADCH'] and titles['Заряды CM5']
        window.sibling_molden = None
        window.property_tool.fill_properties_menu(menu)
        assert not next(a for a in leaf_actions(menu) if a.text().startswith('Заряды ADCH и CM5')).isEnabled()
    finally:
        window.preferences.setValue('multiwfn_program', old)
        window.sibling_molden = None
        window.result_properties = None
        window.overlay_choice['atom'] = None


def test_multiwfn_nci_on_the_model(window, app, tmp_path):
    # «Поверхность на модели → Слабые взаимодействия (Multiwfn) → NCI по промолекулярной плотности» for the
    # structure on the model: a fake Multiwfn gives the grids recorded with Multiwfn 2026.7.15 for the S22 water dimer;
    # the RDG surface is coloured by sign(λ₂)ρ, the legend is the NCI scale, the plot has the H-bond spike
    from PySide6.QtWidgets import QMenu

    data = Path(__file__).parents[1] / 'data' / 'multiwfn'
    one, two = (data / f'dimer_nci_promol_{f}.cub.gz' for f in ('func1', 'func2'))
    fake = fake_program(tmp_path, f'''
if not os.path.isfile('input.xyz'):
    sys.exit(3)
gunzip({q(one)}, 'func1.cub')
gunzip({q(two)}, 'func2.cub')
echo(' Version 2026.7.15 (release date is the same as version name)')
''')
    old = window.preferences.value('multiwfn_program', '')
    window.preferences.setValue('multiwfn_program', str(fake))
    window.dirty = False
    window.load_molecule(read_xyz((data / 'water_dimer_s22.xyz').read_text(encoding='utf-8')))
    window.sibling_molden = window.sibling_gbw = None
    try:
        menu = QMenu()
        window.surface_tool.fill_surface_menu(menu)
        sub = next(a.menu() for a in menu.actions() if a.menu() is not None and a.text() == 'Слабые взаимодействия')
        items = {a.text(): a.isEnabled() for a in sub.actions() if a.text()}
        assert items['NCI по промолекулярной плотности (без расчёта)']
        assert not items['NCI по волновой функции результата'] and not items['График RDG — sign(λ₂)ρ в Спектре']
        assert window.surface_tool.multiwfn_nci('promolecular')
        source = window.surface_source
        assert source['kind'] == 'nci' and source['level'] == 0.5
        surface = window.viewer.surface
        assert surface['scale'] == 'nci' and surface['meshes'][0].colors is not None
        mesh = surface['meshes'][0]
        assert mesh.values.min() < -0.02  # the hydrogen bond is on the surface
        window.viewer.grab()  # the legend paints
        plot = window.nci_panel  # the tab «NCI» of Spectrum, not a window
        assert window.result_tabs.isTabVisible(window.nci_tab) and plot.result[0] == 'nci'
        xs, ys = plot.plot.points
        assert len(xs) > 100 and xs[ys < 0.5].max() < -0.01
        plot.plot.grab()
        assert plot.save_png(tmp_path / 'nci.png') and (tmp_path / 'nci.png').stat().st_size > 1000
        # the domain of the hydrogen bond named in the table, numbered on the plot and on the model
        assert [d.kind for d in plot.domains] == ['hydrogen'] and plot.table.rowCount() == 1
        assert plot.table.item(0, 0).text() == 'водородная' and plot.table.item(0, 1).text() == 'O1–H3···O4'
        assert 'Emamian' in plot.table.item(0, 1).toolTip()
        assert [m[2] for m in plot.plot.marks] == [1] and plot.plot.marks[0][0] < -0.02
        markers = window.viewer.surface['markers']
        assert [m[2] for m in markers] == ['1'] and not markers[0][3]
        plot.table.selectRow(0)
        assert plot.plot.chosen == 0 and window.viewer.surface['markers'][0][3]
        window.viewer.grab()
        window.surface_tool.fill_surface_menu(menu)
        sub = next(a.menu() for a in menu.actions() if a.menu() is not None and a.text() == 'Слабые взаимодействия')
        assert next(a for a in sub.actions() if a.text().startswith('График')).isEnabled()
        assert window.surface_tool.set_surface_level(0.4)
        assert plot.table.rowCount() == 1 and plot.plot.level == 0.4  # the domains of the new level
        assert window.surface_tool.show_nci_plot(True) is plot and window.stack.currentIndex() == 2
        assert window.result_tabs.currentWidget() is plot
        window.navigate(0)
    finally:
        window.preferences.setValue('multiwfn_program', old)
        window.surface_tool.clear_surface()
        window.nci_result = None


def test_multiwfn_igmh_between_the_molecules(window, app, tmp_path):
    # «Слабые взаимодействия → IGMH между молекулами» on the S22 water dimer: a fake Multiwfn gives the grids,
    # atmdg.txt and the output recorded with Multiwfn 2026.7.15 (tools/record_multiwfn_igmh.py); the surface δg_inter
    # coloured by sign(λ₂)ρ, the domain of the hydrogen bond with the δG of its atom pairs, the table of the pairs
    import gzip

    data = Path(__file__).parents[1] / 'data' / 'multiwfn'
    folder = tmp_path / 'Расчёт'
    folder.mkdir()
    molden = folder / 'dimer.molden.input'
    molden.write_bytes(gzip.decompress((data / 'igmh_dimer.molden.gz').read_bytes()))
    fake = fake_program(tmp_path, f'''
assert answers(5) == '20 11 2 1-3 4-6', lines
gunzip({q(data / 'igmh_dimer_sl2r.cub.gz')}, 'sl2r.cub')
gunzip({q(data / 'igmh_dimer_dg_inter.cub.gz')}, 'dg_inter.cub')
cp({q(data / 'igmh_dimer_atmdg.txt')}, 'atmdg.txt')
cat({q(data / 'igmh_dimer_output.txt')})
''')
    old = window.preferences.value('multiwfn_program', '')
    window.preferences.setValue('multiwfn_program', str(fake))
    window.dirty = False
    window.load_molecule(read_xyz((data / 'water_dimer_s22.xyz').read_text(encoding='utf-8')))
    window.sibling_molden, window.sibling_gbw = molden, None
    try:
        assert window.surface_tool.multiwfn_igmh()
        source = window.surface_source
        assert source['kind'] == 'igmh' and source['level'] == 0.005 and window.viewer.surface['scale'] == 'nci'
        panel = window.nci_panel
        assert panel.result[0] == 'igmh' and [d.kind for d in panel.domains] == ['hydrogen']
        assert panel.domains[0].dg == pytest.approx(0.179166, abs=1e-5)
        assert panel.pairs_table.rowCount() == 9 and panel.pairs_table.item(0, 0).text() == 'H3···O4'
        assert panel.pairs_table.item(0, 2).text() == '44.4' and 'H3 67 %' in panel.atoms_note.text()
        assert [m[2] for m in window.viewer.surface['markers']] == ['1']
        assert (folder / 'Анализ' / 'dimer_igmh_domains.csv').is_file()
        assert (folder / 'Анализ' / 'dimer_igmh_extrema.csv').is_file()
        panel.plot.grab()
        window.viewer.grab()
    finally:
        window.preferences.setValue('multiwfn_program', old)
        window.surface_tool.clear_surface()
        window.nci_result = None
        window.sibling_molden = None


def test_multiwfn_esp_and_topology(window, app, tmp_path):
    # «Поверхность на модели → ESP на молекулярной поверхности (Multiwfn)» and «QTAIM → Multiwfn» on the water
    # of examples/6-orbitals: a fake Multiwfn gives the files recorded with Multiwfn 2026.7.15; the surface ρ = 0.001
    # coloured by its ESP with the two extrema on the model, the summary window; the critical points in the table
    data = Path(__file__).parents[1] / 'data' / 'multiwfn'
    fake = fake_program(tmp_path, f'''
if answer(0) == '2':
    cp({q(data / "water_fchk_CPprop_2026.7.15.txt")}, 'CPprop.txt')
    cat({q(data / "water_fchk_topology_2026.7.15.txt")})
if answer(0) == '12':
    gunzip({q(data / "water_fchk_esp_vtx.txt.gz")}, 'vtx.txt')
    gunzip({q(data / "water_fchk_esp_surf.cub.gz")}, 'surf.cub')
    cat({q(data / "water_fchk_esp_2026.7.15.txt")})
''')
    folder = tmp_path / 'Расчёт воды'
    folder.mkdir()
    fchk = folder / 'water.fchk'
    fchk.write_text((Path(__file__).parents[2] / 'examples' / '6-orbitals' / 'water_mp2_gaussian16.fchk')
                    .read_text(encoding='utf-8'), encoding='utf-8')
    old = window.preferences.value('multiwfn_program', '')
    window.preferences.setValue('multiwfn_program', str(fake))
    window.dirty = False
    window.sibling_molden, window.sibling_gbw = fchk, None
    try:
        from PySide6.QtWidgets import QMenu

        menu = QMenu()
        window.surface_tool.fill_surface_menu(menu)
        surface_menu = next(a.menu() for a in menu.actions() if a.menu() is not None and a.text() == 'Молекулярная поверхность')
        item = next(a for a in surface_menu.actions() if a.text().startswith('ESP на молекулярной'))  # a submenu
        assert [a.text().split(' ')[0] for a in surface_menu.actions()] == ['ESP', 'ALIE', 'LEA', 'LEAE']
        assert item.isEnabled()
        assert window.surface_tool.multiwfn_esp()
        assert window.surface_source['kind'] == 'esp-surface'
        surface = window.viewer.surface
        mesh = surface['meshes'][0]
        assert mesh.colors is not None and mesh.values.min() < -0.05 and mesh.values.max() > 0.04
        markers = surface['markers']
        assert [m[1] for m in markers] == ['#2c64c8', '#d7302f'] and all(m[3] for m in markers)
        assert markers[0][2] == '−43.5' and surface['limit'] == pytest.approx(0.0693185919)
        window.viewer.grab()
        # no window — the extrema and the summary are CSV files in the folder of the calculation
        assert not hasattr(window, 'esp_report')
        extrema = csv_rows(folder / 'Анализ' / 'water_esp_extrema.csv')  # in «Анализ», «;» and «,»
        summary = csv_rows(folder / 'Анализ' / 'water_esp_summary.csv')
        assert len(extrema) == 3 and extrema[1][4] == '-43.4981' and len(summary) >= 15
        assert ';' in (folder / 'Анализ' / 'water_esp_extrema.csv').read_text(encoding='utf-8-sig').split('\n')[0]
        assert (folder / 'Анализ' / 'water_multiwfn_esp.txt').is_file()
        # QTAIM: the points of Multiwfn in the table of the drawer, the bond paths on the model
        drawer = window.density_tool.open_density_drawer(tab=2)
        panel = window.density_drawer.panel
        assert panel is not None and getattr(panel, 'multiwfn', None) is not None
        window.viewer.found_contacts = None
        topology = panel.find_points_multiwfn()
        assert topology is not None and topology.counts == {'n': 3, 'b': 2, 'r': 0, 'c': 0}
        # the weak interactions of the search go onto the model at once (water: none)
        assert window.viewer.found_contacts['contacts'] == []
        panel.kind_filter.setCurrentIndex(panel.kind_filter.findData('bond'))  # only the bonds
        assert panel.table.rowCount() == 2 and panel.table.item(0, 3).text() == '0.3515'
        assert panel.table.item(0, 1).text() == 'связь' and panel.table.item(0, 5).text().startswith('-')  # H < 0
        assert panel.table.item(0, 0).text() == 'b1' and panel.table.isColumnHidden(1)
        assert len(topology.paths) == 2
        assert panel.points_on_model() and window.viewer.aim is not None
        # the tables of the points by kinds in the folder of the calculation
        analysis = folder / 'Анализ'
        assert (analysis / 'water_qtaim_bonds.csv').is_file() and (analysis / 'water_qtaim_nuclei.csv').is_file()
        assert not (analysis / 'water_qtaim_rings.csv').exists()
        # the detailed table in Spectrum, the same points
        assert window.topology_panel.topology is topology and window.result_tabs.isTabVisible(window.topology_tab)
        # another tab shown and this one again — the orbitals, the points and the kind chosen are back, not read nor
        # searched again
        tool, mine = window.density_tool, window.document()
        orbital_set = window.density_drawer.orbital_set
        window.document = lambda: 'another tab'
        tool.update_density_button()
        assert window.density_drawer.panel is None
        del window.document  # the method of the class again
        assert window.document() is mine
        tool.update_density_button()
        panel = window.density_drawer.panel
        assert panel is not None and panel.topology is topology and window.density_drawer.orbital_set is orbital_set
        assert panel.kind_filter.currentData() == 'bond' and panel.table.rowCount() == 2
        window.refresh_topology_tab()
        assert window.topology_panel.topology is topology
        del drawer
    finally:
        window.preferences.setValue('multiwfn_program', old)
        window.surface_tool.clear_surface()
        window.esp_result = None
        window.sibling_molden = None


def test_multiwfn_elf_and_lol_on_the_model(window, app, tmp_path):
    # «Поверхность на модели → ELF (Multiwfn)» and «LOL (Multiwfn)» for the water of examples/6-orbitals: a fake
    # Multiwfn gives the grids recorded with Multiwfn 2026.7.15 (cropped around the molecule)
    from PySide6.QtWidgets import QMenu

    data = Path(__file__).parents[1] / 'data' / 'multiwfn'
    fake = fake_program(tmp_path, f'''
if answer(1) == '9':
    gunzip({q(data / "water_fchk_ELF.cub.gz")}, 'ELF.cub')
if answer(1) == '10':
    gunzip({q(data / "water_fchk_LOL.cub.gz")}, 'LOL.cub')
cat({q(data / "elf_water_2026.7.15.txt")})
''')
    fchk = tmp_path / 'water.fchk'
    fchk.write_text((Path(__file__).parents[2] / 'examples' / '6-orbitals' / 'water_mp2_gaussian16.fchk')
                    .read_text(encoding='utf-8'), encoding='utf-8')
    old = window.preferences.value('multiwfn_program', '')
    window.preferences.setValue('multiwfn_program', str(fake))
    window.dirty = False
    window.sibling_molden, window.sibling_gbw = fchk, None
    try:
        menu = QMenu()
        window.surface_tool.fill_surface_menu(menu)
        functions = next(a.menu() for a in menu.actions() if a.menu() is not None and a.text() == 'Функции на сетке')
        items = {a.text().split(' ')[0]: a for a in functions.actions() if a.text()}  # a submenu
        # no choice of the grid in the submenu any more (one «Сетка расчёта»): 12 functions
        assert items['ELF'].isEnabled() and items['LOL'].isEnabled() and len(functions.actions()) >= 12
        assert all(len(a.toolTip()) < 60 for a in menu.actions() if a.text())  # short tooltips
        assert window.surface_tool.multiwfn_function('elf')
        assert (tmp_path / 'Анализ' / 'water_elf_extrema.csv').is_file()  # the attractors of ELF as a table
        source = window.surface_source
        assert source['kind'] == 'elf' and source['level'] == 0.8
        assert window.viewer.surface['meshes'] and window.surface_tool.set_surface_level(0.9)
        assert window.surface_tool.multiwfn_function('lol') and window.surface_source['kind'] == 'lol'
        window.viewer.grab()
        # the page «Поверхности» of the drawer — ELF from the list, a second press takes it away
        window.surface_tool.clear_surface()
        drawer = window.density_tool.open_density_drawer(tab=1)
        assert drawer is not None and window.drawer.page() == 'surfaces' and drawer.update_surfaces_page()
        assert drawer.surfaces_list.isEnabled() and 'Анализ' in drawer.surfaces_hint.text()
        # all is there — no line over the tree; the tree in its rounded frame (azimuth/app.py)
        assert not drawer.surfaces_hint.isVisibleTo(window.drawer) and drawer.surfaces_list.objectName() == 'surfacesTree'
        assert not drawer.surface_items()[0].toolTip(0)  # no tooltip repeating its row
        assert drawer.choose_surface('ELF') is not None
        assert drawer.show_choice() and window.surface_source['kind'] == 'elf'
        assert drawer.choice_button.property('on')  # lit while it is on the model
        elf = window.surface_source['cube']
        assert not drawer.show_choice() and window.surface_source is None and not drawer.choice_button.property('on')
        assert drawer.show_choice() and window.surface_source['cube'] is elf  # kept: not computed again
        # another grid — what is on the model is built again on it
        window.surface_tool.set_nci_grid('high')
        assert window.surface_source is not None and window.surface_source['kind'] == 'elf'
        assert window.surface_source['cube'] is not elf and drawer.choice_button.property('on')
        window.surface_tool.clear_surface()
        # one grid: «Сетка расчёта» of the menu and «Сетка» of the drawer
        window.surface_tool.set_nci_grid('high')
        assert drawer.step.currentIndex() == 2
        drawer.grids[1].setCurrentIndex(0)
        assert window.surface_tool.nci_grid() == 'low' and drawer.grids[0].currentIndex() == 0
        grids = next(a.menu() for a in menu.actions() if a.menu() is not None and a.text() == 'Сетка расчёта')
        assert len(grids.actions()) == 3
        assert not any(a.text().startswith('Грубая') for a in functions.actions())  # no second choice of the grid
        # without Multiwfn: the items are off with a hint, the page says how to install it
        window.preferences.setValue('multiwfn_program', '')
        window.surface_tool.fill_surface_menu(menu)
        functions = next(a.menu() for a in menu.actions() if a.menu() is not None and a.text() == 'Функции на сетке')
        assert not any(a.isEnabled() for a in functions.actions() if a.text())
        assert not drawer.update_surfaces_page() and 'brew install multiwfn' in drawer.surfaces_hint.text()
        assert any(a.text() == 'Программа Multiwfn…' for a in menu.actions())
    finally:
        window.preferences.setValue('multiwfn_program', old)
        window.surface_tool.clear_surface()
        window.sibling_molden = None
        window.trajectory_tool.set_trajectory_open(False)


def test_multiwfn_bond_orders_composition_and_orbital_grid(window, app, tmp_path):
    # «±» → «Порядки связей: Майер, Виберг, FBO, LBO…» and the switch between them; the column «Состав» of the
    # orbitals in the drawer; the orbital on the model from the grid of Multiwfn. A fake Multiwfn: the composition and
    # the HOMO grid recorded with Multiwfn 2026.7.15 for this water; the bond orders written here in its format
    from PySide6.QtWidgets import QMenu

    data = Path(__file__).parents[1] / 'data' / 'multiwfn'
    orders = tmp_path / 'orders.txt'
    block = ' #    1:         1(O )    2(H )    {0}\n #    2:         1(O )    3(H )    {0}\n'
    orders.write_text(''.join(f'{head}\n{block.format(value)} If outputting bond order matrix to bndmat.txt? (y/n)\n'
                              for head, value in (('Bond orders with absolute value >=  0.050000', '0.91234567'),
                                                  ('Bond orders with absolute value >=  0.050000', '0.88888888'),
                                                  ('The total bond order >=  0.050000', '0.77777777'),
                                                  ('The bond orders >=  0.050000', '0.66666666'))), encoding='utf-8')
    fake = fake_program(tmp_path, f'''
if answer(0) == '9':
    cat({q(orders)})
if answer(0) == '8':
    cat({q(data / "water_fchk_composition_2026.7.15.txt")})
if answer(0) == '5':
    gunzip({q(data / "water_fchk_homo.cub.gz")}, 'MOvalue.cub')
''')
    fchk = tmp_path / 'water.fchk'
    fchk.write_text((Path(__file__).parents[2] / 'examples' / '6-orbitals' / 'water_mp2_gaussian16.fchk')
                    .read_text(encoding='utf-8'), encoding='utf-8')
    old = window.preferences.value('multiwfn_program', '')
    window.preferences.setValue('multiwfn_program', str(fake))
    window.dirty = False
    window.result_properties, window.result_source = None, ''
    window.sibling_molden, window.sibling_gbw = fchk, None
    try:
        menu = QMenu()
        window.property_tool.fill_properties_menu(menu)
        assert next(a for a in leaf_actions(menu) if a.text().startswith('Порядки связей:')).isEnabled()
        assert window.property_tool.multiwfn_bond_orders()
        props = window.result_properties
        assert set(props.bond_sets) == {'Mayer', 'Wiberg-Löwdin', 'Fuzzy', 'Laplacian'}
        assert props.bond_kind == 'Mayer' and props.mayer_bonds[0] == (0, 1, 0.91234567)
        assert window.overlay_choice['bonds']
        assert window.property_tool.choose_bond_set('Fuzzy') and window.result_properties.mayer_bonds[0][2] == 0.77777777
        window.property_tool.fill_properties_menu(menu)
        checked = [a.text().strip() for a in leaf_actions(menu) if a.isCheckable() and a.isChecked()]
        assert 'Нечёткие порядки связей (FBO)' in checked
        # the drawer: the composition column, the orbital from the grid of Multiwfn
        window.density_tool.open_density_drawer(tab=0)
        drawer = window.density_drawer
        assert drawer.composition_button.isEnabled()
        shares = drawer.show_composition()
        assert shares == {4: {0: 93.124, 1: 3.438, 2: 3.438}}
        assert drawer.orbitals_table.item(4, 4).text() == 'O1 93 % · H2 3 % · H3 3 %'
        drawer.orbitals_table.selectRow(4)
        assert drawer.show_orbital()
        assert window.surface_source['cube'].values.shape[:3] == (25, 22, 22)  # Multiwfn's grid
    finally:
        window.preferences.setValue('multiwfn_program', old)
        window.surface_tool.clear_surface()
        window.sibling_molden = None
        window.result_properties = None
        window.overlay_choice['bonds'] = False


def test_maps_and_profiles(window, app, tmp_path):
    # Spectrum «Карты и профили»: ρ of water in the plane of its atoms and along O1–H2 from a fake Multiwfn
    # (the files recorded with Multiwfn 2026.7.15); the data and the extrema go to the folder of the calculation
    from azimuth.core import read_xyz

    data = Path(__file__).parents[1] / 'data' / 'multiwfn'
    fake = fake_program(tmp_path, f'''
if answer(0) == '3':
    gunzip({q(data / "water_fchk_rho_line_O1-H2.txt.gz")}, 'line.txt')
if answer(0) == '4':
    gunzip({q(data / "water_fchk_rho_plane_1-2-3.txt.gz")}, 'plane.txt')
''')
    fchk = tmp_path / 'water.fchk'
    fchk.write_text((Path(__file__).parents[2] / 'examples' / '6-orbitals' / 'water_mp2_gaussian16.fchk')
                    .read_text(encoding='utf-8'), encoding='utf-8')
    panel = window.field_panel
    water = read_xyz('3\nwater\nO 0 0 0.1191596\nH 0 0.7906505 -0.4766384\nH 0 -0.7906505 -0.4766384\n')
    old = (panel.source, panel.geometry)
    panel.source, panel.geometry = (lambda: (fake, fchk, 1)), (lambda: water)
    try:
        panel.set_atoms(3, ['O', 'H', 'H'])  # the atoms with their elements
        assert [b.text() for b in panel.plane_atoms] == ['O1', 'H2', 'H3']
        box = panel.line_atoms[1]
        assert box.valueFromText('H3') == 3 and box.valueFromText('2') == 2
        from PySide6.QtGui import QValidator

        assert box.validate('H3', 2)[0] == QValidator.State.Acceptable
        assert box.validate('O3', 2)[0] == QValidator.State.Intermediate  # atom 3 is an H
        assert box.validate('x', 1)[0] == QValidator.State.Invalid
        assert panel.build_map() is not None and panel.map_view.data is not None
        _, _, atoms, extrema = panel.map_view.data
        assert sorted(label for *_, label in atoms) == ['H2', 'H3', 'O1'] and len(extrema) >= 3
        panel.map_view.grab()
        assert (tmp_path / 'Анализ' / 'water_rho_plane_1-2-3.csv').is_file()
        rows = csv_rows(tmp_path / 'Анализ' / 'water_rho_plane_1-2-3_extrema.csv')
        assert rows[1][1] == 'максимум' and rows[1][-2] == 'O1'
        assert panel.build_line() is not None
        _, _, marks, extrema, log = panel.line_view.data
        assert [label for _, label in marks] == ['O1', 'H2'] and log
        assert [e['kind'] for e in extrema] == ['max', 'min', 'max']
        panel.line_view.grab()
        rows = csv_rows(tmp_path / 'Анализ' / 'water_rho_line_1-2_extrema.csv')
        assert rows[2][1] == 'минимум' and abs(float(rows[2][2]) - 0.3515) < 1e-3  # the bond critical point
        assert panel.save_picture(tmp_path / 'line.png') and (tmp_path / 'line.png').stat().st_size > 1000
    finally:
        panel.source, panel.geometry = old


def test_natural_transition_orbitals_in_uv_vis(window, app, tmp_path):
    # «NTO» of TD-DFT (ORCA DoNTO): the pairs of the state chosen under the spectrum; the compass icon puts the
    # hole or the particle NTO on the model; without the .nto file next to the output it says what is needed
    from modules.spectrum.analysis import nto

    source = Path(__file__).parents[2] / 'examples' / '5-uv-vis-nmr' / 'divinylbenzene_tddft_orca6.out'
    text = source.read_text(encoding='utf-8')
    out = tmp_path / 'dvb_td.out'
    out.write_text(text, encoding='utf-8')
    window.display_output(text, out.name, True, str(out))
    panel = window.uv_panel
    assert panel.nto_note.isHidden()  # no DoNTO in this output
    entry = nto.NtoState(1, 4.1, 'dvb_td.s1.nto', (nto.NtoPair(34, 35, 'a', 0.987), nto.NtoPair(33, 36, 'a', 0.011)))
    shown = []
    real = panel.nto_show
    try:
        panel.set_ntos({1: entry}, lambda e, which: shown.append((e.state, which)) or True)
        panel.table.setCurrentCell(0, 0)
        assert not panel.nto_note.isHidden() and not panel.nto_button.isHidden()
        assert panel.nto_note.text().endswith('34a → 35a · 0.987; 33a → 36a · 0.011')
        assert panel.nto_on_model('particle') and shown == [(1, 'particle')]
        assert panel.nto_menu() is not None
        panel.table.setCurrentCell(1, 0)
        assert not panel.nto_button.isEnabled() and 'выберите состояние' in panel.nto_note.text()
        panel.set_ntos({1: entry}, real)
        panel.table.setCurrentCell(0, 0)
        assert not panel.nto_on_model('hole') and 'DoNTO' in panel.nto_note.text()  # no dvb_td.s1.nto here
    finally:
        panel.set_ntos({}, real)


def test_delocalization_and_aromaticity_tab(window, app, tmp_path):
    # «Делокализация» — the rings with HOMA at once; DI and LI and FLU, PDI, MCI from a fake Multiwfn that
    # answers with the outputs recorded for benzaldehyde (tests/data/multiwfn/fuzzy_benzaldehyde_*.txt)
    import gzip
    data = Path(__file__).parents[1] / 'data' / 'multiwfn'
    out = tmp_path / 'benzaldehyde.out'
    out.write_text((data / 'benzaldehyde_cam-b3lyp_orca.out').read_text(encoding='utf-8'), encoding='utf-8')
    (tmp_path / 'benzaldehyde.molden.input').write_bytes(
        gzip.decompress((data / 'benzaldehyde_cam-b3lyp_def2-svpd.molden.gz').read_bytes()))
    fake = fake_program(tmp_path, f'''
if answer(1) == '4':
    cat({q(data / "fuzzy_benzaldehyde_lidi.txt")})
if answer(1) == '5':
    cat({q(data / "fuzzy_benzaldehyde_pdi.txt")}, {q(data / "fuzzy_benzaldehyde_flu.txt")}, {q(data / "fuzzy_benzaldehyde_mci.txt")})
''')
    old = window.preferences.value('multiwfn_program', '')
    window.preferences.setValue('multiwfn_program', str(fake))
    try:
        window.display_output(out.read_text(encoding='utf-8'), out.name, True, str(out))
        panel = window.deloc_panel
        assert window.result_tabs.isTabVisible(window.deloc_tab)
        assert panel.rings == [(2, 3, 4, 5, 6, 7)] and panel.ring_table.item(0, 0).text() == 'C3–C4–C5–C6–C7–C8'
        assert 0.98 < float(panel.ring_table.item(0, 1).text()) <= 1.0 and panel.ring_table.item(0, 2).text() == ''
        assert panel.compute_di()
        assert panel.pair_table.item(0, 0).text() == 'O1–C2' and panel.pair_table.item(0, 1).text() == '2.096'
        assert panel.atom_table.rowCount() == 14 and panel.atom_table.item(0, 1).text() == '7.155'
        assert panel.compute_rings()
        assert [panel.ring_table.item(0, c).text() for c in (2, 3, 4, 5)] == ['0.0012', '0.0981', '0.0176', '0.5100']
        assert (tmp_path / 'Анализ' / 'benzaldehyde_multiwfn_delocalization.txt').is_file()
    finally:
        window.preferences.setValue('multiwfn_program', old)
        window.sibling_molden = None


def test_multiwfn_resp_charges(window, app, tmp_path):
    # «±» → «Заряды RESP…»: a fake Multiwfn answers 7 → 18 → 1 with the output of Multiwfn 2026.7.15 recorded
    # for this water and writes its input.chg; the charges go onto the model, the output and «water_resp.chg» into
    # «Анализ»
    from PySide6.QtWidgets import QMenu

    data = Path(__file__).parents[1] / 'data' / 'multiwfn'
    fake = fake_program(tmp_path, f'''
if answers(4) == '7 18 1 y':
    cat({q(data / "resp_water_standard_chg.txt")})
    cp({q(data / "resp_water_standard_chg__input.chg")}, 'input.chg')
''')
    folder = tmp_path / 'Вода'
    folder.mkdir()
    fchk = folder / 'water.fchk'
    fchk.write_text((Path(__file__).parents[1] / 'data' / 'orbitals' / 'water_mp2_g16.fchk').read_text(encoding='utf-8'),
                    encoding='utf-8')
    old = window.preferences.value('multiwfn_program', '')
    window.preferences.setValue('multiwfn_program', str(fake))
    window.result_properties, window.result_source = None, ''
    window.sibling_molden, window.sibling_gbw = fchk, None
    try:
        menu = QMenu()
        window.property_tool.fill_properties_menu(menu)
        assert {a.text(): a for a in leaf_actions(menu)}['Заряды RESP…'].isEnabled()
        assert window.property_tool.multiwfn_resp()
        assert window.result_properties.charges['resp'] == (-0.5891260132, 0.2945630066, 0.2945630066)
        assert window.overlay_choice['atom'] == 'resp'
        assert (folder / 'Анализ' / 'water_multiwfn_resp.txt').is_file()
        assert (folder / 'Анализ' / 'water_resp.chg').read_text(encoding='utf-8').startswith('O')
        window.property_tool.fill_properties_menu(menu)
        assert {a.text(): a.isEnabled() for a in leaf_actions(menu)}['Заряды RESP']
    finally:
        window.preferences.setValue('multiwfn_program', old)
        window.sibling_molden = None
        window.result_properties = None


def test_multiwfn_hirshfeld_and_aim_charges(window, app, tmp_path):
    # «±» → «Заряды Хиршфельда…» and «Заряды и спины AIM (бассейны Бейдера)…» on the wavefunction of the
    # result: a fake Multiwfn answers 7 … and 17 … with the outputs of Multiwfn 2026.7.15 recorded for this water
    # (tests/data/multiwfn/pop_*.txt); the charges go onto the model, the outputs into «Анализ»; Hirshfeld is off when
    # the output of the program has it already
    from PySide6.QtWidgets import QMenu

    data = Path(__file__).parents[1] / 'data' / 'multiwfn'
    fake = fake_program(tmp_path, f'''
if answer(0) == '7':
    cat({q(data / "pop_water_hirshfeld.txt")})
if answer(0) == '17':
    cat({q(data / "pop_water_basins_exact.txt")})
''')
    folder = tmp_path / 'Вода'
    folder.mkdir()
    fchk = folder / 'water.fchk'
    fchk.write_text((Path(__file__).parents[1] / 'data' / 'orbitals' / 'water_mp2_g16.fchk').read_text(encoding='utf-8'),
                    encoding='utf-8')
    old = window.preferences.value('multiwfn_program', '')
    window.preferences.setValue('multiwfn_program', str(fake))
    window.result_properties, window.result_source = None, ''
    window.sibling_molden, window.sibling_gbw = fchk, None
    try:
        menu = QMenu()
        window.property_tool.fill_properties_menu(menu)
        items = {a.text(): a for a in leaf_actions(menu)}
        assert items['Заряды Хиршфельда…'].isEnabled() and items['Заряды и спины AIM (бассейны Бейдера)…'].isEnabled()
        assert window.property_tool.multiwfn_hirshfeld()
        assert window.result_properties.charges['hirshfeld'] == (-0.30463436, 0.15231718, 0.15231718)
        assert window.overlay_choice['atom'] == 'hirshfeld'
        assert window.property_tool.multiwfn_aim()
        props = window.result_properties
        assert props.charges['aim'] == pytest.approx((-0.7524717892, 0.3759454574, 0.3759445228))
        assert 'aim' not in props.spins  # a closed shell: no spin integration
        assert props.charges['hirshfeld'][0] == -0.30463436  # kept
        assert window.overlay_choice['atom'] == 'aim'
        assert (folder / 'Анализ' / 'water_multiwfn_aim.txt').is_file()
        assert (folder / 'Анализ' / 'water_multiwfn_hirshfeld.txt').is_file()
        window.property_tool.fill_properties_menu(menu)
        titles = {a.text(): a.isEnabled() for a in leaf_actions(menu)}
        # computed here by Multiwfn, it can be computed again, as the others
        assert titles['Заряды AIM (бассейны Бейдера)'] and titles['Заряды Хиршфельда…']
        from dataclasses import replace

        printed = replace(window.result_properties, charges={**window.result_properties.charges,
                                                             'hirshfeld': (-0.3, 0.15, 0.15)})
        window.result_properties = printed  # as if the program of the result printed them: nothing to compute
        menu.clear()
        window.property_tool.fill_properties_menu(menu)
        assert not {a.text(): a.isEnabled() for a in leaf_actions(menu)}['Заряды Хиршфельда…']
    finally:
        window.preferences.setValue('multiwfn_program', old)
        window.sibling_molden = None
        window.result_properties = None
        window.overlay_choice['atom'] = None


def test_multiwfn_spins_of_an_open_shell(window, app, tmp_path):
    # for an open shell «Заряды Хиршфельда…» brings the Hirshfeld spin populations too (15 …), and the AIM basins their
    # spins (17 … 5); a fake Multiwfn answers with the outputs recorded for the UKS cation of divinylbenzene
    data = Path(__file__).parents[1] / 'data' / 'multiwfn'
    fake = fake_program(tmp_path, f'''
if answer(0) == '7':
    cat({q(data / "pop_cation_hirshfeld.txt")})
if answer(0) == '15':
    cat({q(data / "pop_cation_hirshfeld3_spin.txt")})
if answer(0) == '17':
    cat({q(data / "pop_cation_basins_spin.txt")})
''')
    molden = tmp_path / 'cation.molden'
    molden.write_text((Path(__file__).parents[1] / 'data' / 'orbitals' / 'molden5.7_dvb_un_sp.molden')
                      .read_text(encoding='utf-8'), encoding='utf-8')
    old = window.preferences.value('multiwfn_program', '')
    window.preferences.setValue('multiwfn_program', str(fake))
    window.result_properties, window.result_source = None, ''
    window.sibling_molden, window.sibling_gbw = molden, None
    try:
        assert window.property_tool.multiwfn_hirshfeld()
        props = window.result_properties
        assert sum(props.charges['hirshfeld']) == pytest.approx(1.0, abs=1e-5)
        assert props.spins['hirshfeld'][14] == 0.24689878 and sum(props.spins['hirshfeld']) == pytest.approx(1.0, abs=1e-5)
        assert window.property_tool.multiwfn_aim()
        props = window.result_properties
        assert props.spins['aim'][14] == 0.29160260 and sum(props.charges['aim']) == pytest.approx(1.0, abs=2e-3)
        assert props.spins['hirshfeld'][0] == 0.16103607  # kept
    finally:
        window.preferences.setValue('multiwfn_program', old)
        window.sibling_molden = None
        window.result_properties = None
        window.overlay_choice['atom'] = None


def test_localized_orbitals_in_the_drawer(window, app, tmp_path):
    # «Орбитали» of the drawer — «Локализованные · Пипек — Меззи»: a fake Multiwfn answers 19 … with the output and the
    # new.fch recorded for this water (Multiwfn 2026.7.15); the table shows the LMOs — a core, two bonds, two lone
    # pairs, «—» for their energies, the atoms in «Состав»; the file of the LMOs is kept in «Анализ» and an LMO goes
    # onto the model from it; «Канонические орбитали» bring the table back
    data = Path(__file__).parents[1] / 'data' / 'multiwfn'
    fake = fake_program(tmp_path, f'''
if answer(0) == '19':
    gunzip({q(data / "lmo_water_pm__new.fch.gz")}, 'new.fch')
    cat({q(data / "lmo_water_pm.txt")})
if answer(0) == '5':
    gunzip({q(data / "water_fchk_homo.cub.gz")}, 'MOvalue.cub')
''')
    folder = tmp_path / 'Вода'
    folder.mkdir()
    fchk = folder / 'water.fchk'
    fchk.write_text((Path(__file__).parents[1] / 'data' / 'orbitals' / 'water_mp2_g16.fchk').read_text(encoding='utf-8'),
                    encoding='utf-8')
    old = window.preferences.value('multiwfn_program', '')
    window.preferences.setValue('multiwfn_program', str(fake))
    window.dirty = False
    window.result_properties, window.result_source = None, ''
    window.sibling_molden, window.sibling_gbw = fchk, None
    try:
        window.density_tool.open_density_drawer(tab=0)
        drawer = window.density_drawer
        kind = drawer.orbital_kind
        assert kind.isEnabled() and kind.currentData() == 'canonical'
        assert drawer.orbitals_table.item(4, 3).text() == 'ВЗМО'
        kind.setCurrentIndex(kind.findData('pm'))
        assert drawer.table_set is not drawer.orbital_set
        table = drawer.orbitals_table
        assert [table.item(r, 3).text() for r in range(5)] == ['остов', 'связь', 'связь', 'НП', 'НП']
        assert table.item(1, 1).text() == '—' and table.item(1, 4).text() == 'O1–H2 63/34 %'
        assert table.item(5, 1).text() != '—'  # the virtual orbitals keep their energies
        assert 'связей 2' in drawer.panel.status.text()
        # told over the model, not a line of the drawer
        assert not drawer.panel.status.isVisibleTo(window.drawer) 
        toast = getattr(window, '_page_toast', None)  # no status line — the pill of the page
        assert 'связей 2' in window.notice.text() + window.statusBar().currentMessage() + (toast.text() if toast else '')
        assert (folder / 'Анализ' / 'water_lmo_pm.fch').is_file()
        assert window.property_tool.orbitals_file(drawer.table_set) == folder / 'Анализ' / 'water_lmo_pm.fch'
        table.selectRow(1)
        assert drawer.show_orbital()
        assert window.surface_source['orbitals'] is drawer.table_set and 'ЛМО 2' in window.surface_source['title']
        assert table.item(1, 0).font().bold()
        kind.setCurrentIndex(kind.findData('canonical'))
        assert drawer.table_set is drawer.orbital_set and drawer.orbitals_table.item(4, 3).text() == 'ВЗМО'
        assert not drawer.orbitals_table.item(1, 0).font().bold()  # the LMO on the model is not this orbital 2
        kind.setCurrentIndex(kind.findData('pm'))  # computed once: no second run
        assert drawer.table_set is drawer.lmos['pm'][0]
    finally:
        window.preferences.setValue('multiwfn_program', old)
        window.surface_tool.clear_surface()
        window.sibling_molden = None
        window.result_properties = None


def test_localized_orbitals_of_an_open_shell(window, app, tmp_path):
    # the cation of divinylbenzene (UKS, Molden): the LMOs of α and β, the β rows numbered from 1 again, each with its
    # kind
    data = Path(__file__).parents[1] / 'data' / 'multiwfn'
    answers = tmp_path / 'answers.txt'
    fake = fake_program(tmp_path, f'''
with open({q(answers)}, 'w', encoding='utf-8') as out:
    out.write('\\n'.join(lines) + '\\n')
gunzip({q(data / "lmo_cation_pm_mulliken__new.fch.gz")}, 'new.fch')
cat({q(data / "lmo_cation_pm_mulliken.txt")})
''')
    molden = tmp_path / 'cation.molden'
    molden.write_text((Path(__file__).parents[1] / 'data' / 'orbitals' / 'molden5.7_dvb_un_sp.molden')
                      .read_text(encoding='utf-8'), encoding='utf-8')
    old = window.preferences.value('multiwfn_program', '')
    window.preferences.setValue('multiwfn_program', str(fake))
    window.dirty = False
    window.result_properties, window.result_source = None, ''
    window.sibling_molden, window.sibling_gbw = molden, None
    try:
        window.density_tool.open_density_drawer(tab=0)
        drawer = window.density_drawer
        drawer.orbital_kind.setCurrentIndex(drawer.orbital_kind.findData('pm'))
        assert answers.read_text().split()[:3] == ['19', '-9', '1']
        table = drawer.orbitals_table
        rows = {table.item(r, 0).text(): table.item(r, 3).text() for r in range(table.rowCount())}
        assert rows['1 α'] == 'остов' and rows['1 β'] == 'остов'
        assert rows['11 α'] == 'связь' and rows['34 β'] in ('связь', 'делок.', 'НП', 'остов')
        assert rows['36 α'] == ''  # a virtual α orbital: canonical
    finally:
        window.preferences.setValue('multiwfn_program', old)
        window.sibling_molden = None
        window.result_properties = None


def test_fukui_surfaces_on_the_model(window, app, tmp_path):
    # f⁺, f⁻, f⁰, Δf as ± surfaces from the three
    # wavefunctions of the queue. The wavefunctions: the water of the test data with one more electron in the LUMO
    # (N + 1) and one less in the HOMO (N − 1) — frozen orbitals, so f⁺ = |LUMO|² (the oracle: orbital_cube)
    import re

    import numpy as np

    from azimuth.core import Calculation
    from modules.sextant import batch as batches
    from modules.spectrum.readers.orbital_files import read_orbitals
    from modules.spectrum.analysis.orbitals import orbital_cube

    pytest.importorskip('vtk')
    show_model(window, app)
    window.dirty = False
    text = (Path(__file__).parents[1] / 'data' / 'orbitals' / 'molden5.7_water_mp2.molden').read_text(encoding='utf-8')
    occupations = list(re.finditer(r'Occup=\s*([\d.]+)', text))

    def changed(k, value):
        m = occupations[k]
        return text[:m.start(1)] + f'{value:.6f}' + text[m.end(1):]

    n = read_orbitals(text)
    window.load_molecule(n.molecule)
    items = []
    for k, (content, charge, mult) in enumerate(((text, 0, 1), (changed(5, 1.0), -1, 2), (changed(4, 1.0), 1, 2))):
        job = tmp_path / 'fukui' / f'job{k}'
        job.mkdir(parents=True)
        (job / 'water.out').write_text('ORCA', encoding='utf-8')
        (job / 'water.molden.input').write_text(content, encoding='utf-8')
        items.append(batches.BatchItem(f'water {k}', n.molecule, charge, mult, state='done', output=str(job / 'water.out'),
                                       folder=str(job)))
    queue = batches.Batch('orca', Calculation(task='Энергия'), items, tmp_path / 'fukui', purpose='fukui')
    queue.save()
    grid = window.preferences.value('multiwfn_grid')
    window.surface_tool.set_nci_grid('low')  # 0.25 Å — quick
    try:
        assert window.property_tool.fukui_surface('plus', queue.folder)
        source = window.surface_source
        assert source['kind'] == 'fukui' and source['title'].startswith('f⁺') and window.viewer.surface['meshes']
        lumo = orbital_cube(n, 5, step=0.25).values[..., 0]
        assert np.allclose(source['cube'].values[..., 0], lumo ** 2, atol=1e-10)
        kept = window._fukui_fields
        assert window.property_tool.fukui_surface('dual', queue.folder) and window._fukui_fields is kept  # not computed again
        assert window.surface_source['title'].startswith('Δf')
        assert (queue.folder / 'Анализ' / 'fukui_dual_extrema.csv').is_file()
        from modules.spectrum.views.fukui_view import FukuiDialog

        shown = []
        dialog = FukuiDialog(window, ['O', 'H', 'H'], {k: (0.0, 0.0, 0.0) for k in ('n', 'anion', 'cation')},
                             {k: (0.4, 0.3, 0.3) for k in ('plus', 'minus', 'zero', 'dual')}, None,
                             surface=shown.append)
        assert list(dialog.surface_buttons) == ['plus', 'minus', 'zero', 'dual']
        dialog.surface_buttons['minus'].click()
        assert shown == ['minus']
        dialog.close()
    finally:
        window.surface_tool.clear_surface()
        window.preferences.setValue('multiwfn_grid', grid or 'low')


def test_the_charges_of_aim_come_back_when_the_result_is_opened_again(window, tmp_path):
    # kept as values beside the output of the
    # basins, taken back with the other charges computed for these orbitals
    import json

    from azimuth.core import Atom, Molecule
    from modules.spectrum.readers.orca_properties import Properties
    from modules.spectrum.wavefunction import field_tables

    molden = tmp_path / 'water.molden.input'
    molden.write_text('[Molden Format]\n', encoding='utf-8')
    water = Molecule('water', (Atom('O', 0, 0, 0), Atom('H', 0.96, 0, 0), Atom('H', -0.24, 0.93, 0)), ())
    field_tables.save_output(molden, 'aim_values', json.dumps({'charges': [-1.1, 0.55, 0.55], 'spins': None}))
    old = window.sibling_molden
    window.sibling_molden = molden
    try:
        props = window.property_tool.saved_charges(Properties(water))
        assert props.charges['aim'] == (-1.1, 0.55, 0.55) and 'aim' not in props.spins
    finally:
        window.sibling_molden = old
