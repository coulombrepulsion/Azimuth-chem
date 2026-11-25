"""Window tests — Compass: building, selecting, measuring, viewing and the model (split from test_gui.py on 2026-11-08)."""

from tests.gui_support import *  # noqa: F401,F403 — the fixtures app, window and the helpers
from tests.fake_programs import program_script


def test_mouse_places_atom_at_clicked_position(window, app):
    window.new_molecule()
    window.element.setCurrentText('C')
    show_model(window, app)
    point = QPoint(window.viewer.width() // 2 + 100, window.viewer.height() // 2 - 50)
    QTest.mouseClick(window.viewer, Qt.MouseButton.LeftButton, pos=point)
    assert len(window.molecule.atoms) == 1
    # the first atom is the origin wherever it was put; it stays under the click
    assert window.molecule.atoms[0].position == pytest.approx((0, 0, 0), abs=1e-7)
    projected = window.viewer.projected()[0][0]
    assert abs(projected.x() - point.x()) < 0.01 and abs(projected.y() - point.y()) < 0.01
    # a second atom bonded to it: the origin is the middle of the bond, the view turns about it, nothing moves
    # (without «Выравнивать при построении», which may move the first atom a little)
    window.bond_length.setValue(1.5)
    tidy = window.tidy_live_action.isChecked()
    window.tidy_live_action.setChecked(False)
    try:
        QTest.mouseClick(window.viewer, Qt.MouseButton.LeftButton, pos=point)
    finally:
        window.tidy_live_action.setChecked(tidy)
    a, b = (atom.position for atom in window.molecule.atoms)
    assert len(window.molecule.atoms) == 2 and tuple(x + y for x, y in zip(a, b)) == pytest.approx((0, 0, 0), abs=1e-7)
    assert window.viewer.camera()[0] == (0.0, 0.0, 0.0)
    first = window.viewer.projected()[0][0]
    assert abs(first.x() - point.x()) < 0.01 and abs(first.y() - point.y()) < 0.01


def test_molecule_put_where_clicked_with_its_centre_at_the_origin(window, app):
    # a molecule of the library in the empty field: where the click was, centred at the origin
    from math import fsum

    window.new_molecule()
    show_model(window, app)
    window.model_menu_tool.choose_molecule('Бензол · C₆H₆')
    point = QPoint(window.viewer.width() // 2 - 120, window.viewer.height() // 2 + 60)
    QTest.mouseClick(window.viewer, Qt.MouseButton.LeftButton, pos=point)
    atoms = window.molecule.atoms
    assert window.molecule.formula == 'C6H6'
    assert [fsum(a.position[k] for a in atoms) / len(atoms) for k in range(3)] == pytest.approx([0, 0, 0], abs=1e-7)
    centre = window.viewer.screen((0, 0, 0))
    assert abs(centre.x() - point.x()) < 0.01 and abs(centre.y() - point.y()) < 0.01


def test_the_origin_put_in_an_atom_of_a_drawn_molecule_stays_there(window):
    # the centring of a drawn structure is for building only; an edit of the coordinates is kept
    window.new_molecule()
    window.element.setCurrentText('C')
    window.place_on_model((0, 0, 0), None)
    window.place_on_model((0, 0, 0), 0)  # C–C: the origin in the middle of the bond
    assert window.molecule.atoms[1].position != pytest.approx((0, 0, 0), abs=1e-3)
    window.viewer.set_selection([1])
    window.chem_actions['origin'].trigger()
    assert window.molecule.atoms[1].position == pytest.approx((0, 0, 0), abs=1e-7)
    window.place_on_model((0, 0, 0), 1)  # building on: the origin chosen stays where it was put
    assert window.molecule.atoms[1].position == pytest.approx((0, 0, 0), abs=1e-7)
    # «И с тремя тоже не уверен»: «Оси по трём выделенным атомам» — the first at the origin, the second on +X, the third
    # in the plane XY (Y > 0), in a drawn molecule too
    window.place_on_model((0, 0, 0), 0)
    window.viewer.set_selection([0, 1, 2])
    window.chem_actions['axes3'].trigger()
    a, b, c = (window.molecule.atoms[i].position for i in (0, 1, 2))
    assert a == pytest.approx((0, 0, 0), abs=1e-7)
    assert b[1] == pytest.approx(0, abs=1e-7) and b[2] == pytest.approx(0, abs=1e-7) and b[0] > 0
    assert c[2] == pytest.approx(0, abs=1e-7) and c[1] > 0


def test_a_structure_from_a_file_keeps_its_coordinates(window):
    # only a structure drawn (centred) is kept centred; the coordinates of a file stay
    from azimuth.core import Atom, Molecule

    window.load_molecule(Molecule('', (Atom('C', 5, 5, 5),)))
    window.element.setCurrentText('O')
    window.build_mode.setCurrentIndex(1)
    window.place_on_model((0, 0, 0), 0)
    assert window.molecule.atoms[0].position == pytest.approx((5, 5, 5), abs=0.05)  # not moved to the centre


def test_mouse_attaches_atom_and_undo_redo(window, app):
    window.new_molecule()
    window.element.setCurrentText('C')
    show_model(window, app)
    QTest.mouseClick(
        window.viewer, Qt.MouseButton.LeftButton, pos=QPoint(window.viewer.width() // 2, window.viewer.height() // 2)
    )
    window.element.setCurrentText('O')
    window.bond_order.setCurrentText('2')
    window.bond_length.setValue(1.22)
    point = window.viewer.projected()[0][0].toPoint()
    QTest.mouseClick(window.viewer, Qt.MouseButton.LeftButton, pos=point)
    assert len(window.molecule.atoms) == 2 and window.molecule.bonds == ((0, 1, 2),)
    window.undo_geometry()
    assert len(window.molecule.atoms) == 1
    window.redo_geometry()
    assert len(window.molecule.atoms) == 2 and window.molecule.bonds == ((0, 1, 2),)


def test_fragments_can_be_placed_and_attached(window, app):
    window.new_molecule()
    window.build_mode.setCurrentIndex(2)
    window.fragment.setCurrentText('Метил · —CH₃')
    show_model(window, app)
    QTest.mouseClick(
        window.viewer, Qt.MouseButton.LeftButton, pos=QPoint(window.viewer.width() // 2, window.viewer.height() // 2)
    )
    assert window.molecule.formula == 'CH3'
    window.fragment.setCurrentText('Гидроксил · —OH')
    QTest.mouseClick(window.viewer, Qt.MouseButton.LeftButton, pos=window.viewer.projected()[0][0].toPoint())
    assert window.molecule.formula == 'CH4O' and window.table.rowCount() == 6
    assert (0, 4, 1) in window.molecule.bonds


def test_selection_bond_change_delete_and_undo(window, app):
    show_model(window, app)
    a = window.viewer.projected()[0][0].toPoint()
    b = window.viewer.projected()[1][0].toPoint()
    QTest.mouseClick(window.viewer, Qt.MouseButton.LeftButton, pos=a)
    QTest.mouseClick(window.viewer, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ShiftModifier, pos=b)
    assert len(window.viewer.selected) == 2 and window.bond_button.isEnabled()
    window.apply_bond(remove=True)
    assert all({a, b} != {0, 1} for a, b, o in connections(window.molecule))
    window.bond_order.setCurrentText('2')
    window.apply_bond()
    assert (0, 1, 2) in connections(window.molecule)
    window.remove_atom()
    assert len(window.molecule.atoms) == 1
    window.undo_geometry()
    assert len(window.molecule.atoms) == 3


def test_mouse_drag_moves_atom_but_keeps_bonds(window, app):
    show_model(window, app)
    window.build_mode.setCurrentIndex(3)
    original = window.molecule.atoms[1].position
    original_bonds = connections(window.molecule)
    point = window.viewer.projected()[1][0].toPoint()
    QTest.mousePress(window.viewer, Qt.MouseButton.LeftButton, pos=point)
    QTest.mouseMove(window.viewer, point + QPoint(50, 20), 10)
    QTest.mouseRelease(window.viewer, Qt.MouseButton.LeftButton, pos=point + QPoint(50, 20))
    assert window.molecule.atoms[1].position != original
    assert connections(window.molecule) == original_bonds
    window.undo_geometry()
    assert window.molecule.atoms[1].position == pytest.approx(original)


def test_invalid_coordinate_cannot_be_overwritten_by_builder(window, monkeypatch):
    errors = []
    monkeypatch.setattr(window, 'error', lambda exc: errors.append(str(exc)))
    count = len(window.molecule.atoms)
    window.table.item(0, 1).setText('invalid')
    window.place_on_model((10, 10, 10), None)
    assert errors and len(window.molecule.atoms) == count
    assert window.table.item(0, 1).text() == 'invalid'
    window.undo_geometry()
    assert window.table.item(0, 1).text() != 'invalid'


def test_empty_canvas_no_stale_molecule(window):
    window.new_molecule()
    assert window.viewer.molecule.atoms == ()
    assert window.table.rowCount() == 0 and not window.export_button.isEnabled()
    restored, _ = read_project(project_text(window.molecule, window.calculation()))
    assert restored.atoms == ()


def test_builder_fits_small_window(window, app):
    show_model(window, app)
    window.resize(1050, 730)
    app.processEvents()
    page = window.structure_tabs.widget(0)
    assert window.viewer.geometry().bottom() < page.height()
    assert window.selection_info.geometry().bottom() < page.height()


def test_view_coordinate_inverse_after_rotation(window):
    view = window.viewer
    view.yaw = 0.7
    view.pitch = -0.4
    for vector in [(1, 0, 0), (0, 1, 0), (0, 0, 1), (2.3, -0.7, 4.1)]:
        assert view.from_view(view.to_view(vector)) == pytest.approx(vector)


def test_table_edit_history_and_sync(window):
    original = window.molecule.atoms[1].x
    window.structure_tabs.setCurrentIndex(1)
    window.table.item(1, 1).setText('1.02')
    assert window.viewer.molecule.atoms[1].x == 1.02
    window.undo_geometry()
    assert window.molecule.atoms[1].x == original
    window.redo_geometry()
    assert window.table.item(1, 1).text() == '1.02000000'


def test_periodic_table_all_elements_and_selection(window, app):
    from azimuth.core import SYMBOLS

    window.show_periodic_table()
    app.processEvents()
    dialog = window.periodic_dialog
    # the 118 elements and the dummy atom X
    assert set(dialog.buttons) == set(SYMBOLS) | {'X'} and len(dialog.buttons) == 119
    dialog.buttons['Xe'].click()
    assert window.element.currentText() == 'Xe'
    assert window.viewer.mode == 'atom' and not dialog.isVisible()
    window.place_on_model((20, 0, 0), None)
    assert window.molecule.atoms[-1].symbol == 'Xe'


@pytest.mark.parametrize(
    'mode,expected', [('element', ['O', 'H', 'H']), ('number', ['1', '2', '3']), ('both', ['O1', 'H2', 'H3'])]
)
def test_atom_labels_are_center_label_only(window, mode, expected):
    window.label_mode.setCurrentIndex(window.label_mode.findData(mode))
    assert [window.viewer.atom_label(i) for i in range(3)] == expected
    assert window.preferences.value('atom_labels') == mode
    window.label_mode.setCurrentIndex(0)


def test_label_buttons_exclusive_and_toggle_off(window):
    window.label_mode.setCurrentIndex(window.label_mode.findData('none'))
    for key in ['number', 'element', 'both']:
        window.label_buttons[key].click()
        assert window.viewer.label_mode == key
        assert sum(b.isChecked() for b in window.label_buttons.values()) == 1
        window.label_buttons[key].click()
        assert window.viewer.atom_label(0) == ''
        assert not any(b.isChecked() for b in window.label_buttons.values())


def test_mode_specific_controls(window, app):
    # editing the structure (atom / fragment / molecule buttons) and moving (atom / fragment / molecule) are separate
    show_model(window, app)
    structure = [window.element_button, window.fragment_button, window.molecule_button]
    movers = list(window.move_kind_buttons.values())
    assert not any(b.isVisible() for b in structure + movers)
    window.edit_toggle.click()
    assert (
        window.viewer.mode == 'atom'
        and all(b.isVisible() for b in structure)
        and not any(b.isVisible() for b in movers)
    )
    assert window.element_button.isChecked() and not window.fragment_button.isChecked()
    window.model_menu_tool.choose_fragment('Гидроксил · —OH')
    assert (
        window.viewer.mode == 'fragment'
        and window.fragment_button.isChecked()
        and not window.element_button.isChecked()
    )
    assert [a.text() for a in window.model_menu_tool.fragment_menu().actions() if a.isChecked()] == ['Гидроксил · —OH']
    assert window.choice_label.text() == 'Гидроксил · —OH'
    window.edit_toggle.click()
    assert window.viewer.mode == 'view' and not any(b.isVisible() for b in structure + movers)
    window.move_kind.setCurrentIndex(2)
    window.move_button.click()
    assert (
        window.viewer.mode == 'move'
        and all(b.isVisible() for b in movers)
        and not any(b.isVisible() for b in structure)
    )
    assert window.move_button.isChecked() and not window.edit_toggle.isChecked()
    assert window.move_kind_buttons['atom'].isChecked() and window.viewer.move_target == 'atom'  # an atom by default
    window.move_kind_buttons['molecule'].click()
    assert window.viewer.move_target == 'molecule' and [
        k for k, b in window.move_kind_buttons.items() if b.isChecked()
    ] == ['molecule']
    window.move_button.click()
    assert window.viewer.mode == 'view'


def test_right_click_on_bond_sets_its_order(window, app):
    show_model(window, app)
    window.load_molecule(read_xyz(EXAMPLES['Этан · C₂H₆ · перемещение фрагмента']))
    a, b = 0, 1
    menu = window.model_menu_tool.bond_menu(a, b)
    assert [x.text() for x in menu.actions() if not x.isSeparator()] == [
        'Одинарная связь',
        'Двойная связь',
        'Тройная связь',
        'Ароматическая (линия и пунктир)',  # the types and the colour of a bond (as Chemcraft)
        'Частичная / координационная (пунктир)',
        'Цвет связи…',
        'Закрепить длину связи для оптимизации',
        'Разорвать связь',
        'Вращать вокруг этой связи…',
    ]
    assert menu.actions()[0].isChecked()
    menu.actions()[1].trigger()
    from modules.compass.chemistry.builder import connections

    assert next(o for i, j, o in connections(window.molecule) if {i, j} == {a, b}) == 2
    window.undo_geometry()
    assert next(o for i, j, o in connections(window.molecule) if {i, j} == {a, b}) == 1
    # the viewer finds the bond between the two projected carbons
    p, q = window.viewer.projected()[a][0], window.viewer.projected()[b][0]
    assert window.viewer.bond_at((p + q) / 2) in ((a, b), (b, a))


def test_summary_names_the_structure_or_shows_the_formula(window, app):
    show_model(window, app)
    window.load_molecule(read_xyz(EXAMPLES['Вода · H₂O']))
    assert window.molecule_info.text() == 'H₂O  /  атомов: 3'  # the formula and the atoms only
    window.iupac_button.click()
    assert window.molecule_info.text() == 'вода  /  H₂O  /  атомов: 3'
    window.element.setCurrentText('Xe')
    window.build_mode.setCurrentIndex(1)
    window.place_on_model((6, 0, 0), None)
    assert window.molecule.title == '' and window.molecule_info.text() == 'H₂OXe  /  атомов: 4'
    window.undo_geometry()
    assert window.molecule_info.text().startswith('вода')


def test_measurement_fields_clear_and_update(window):
    window.viewer.set_selection([1])
    assert float(window.measure_fields[0].text()) == pytest.approx(0.7586)
    assert window.measure_fields[3].text() == ''
    window.viewer.set_selection([1, 0])
    assert window.measure_fields[3].text().endswith('Å')
    assert all(not f.text() for f in window.measure_fields[:3])
    window.viewer.set_selection([1, 0, 2])
    assert window.measure_fields[3].text().endswith('°')
    window.viewer.set_selection([])
    assert all(not f.text() for f in window.measure_fields)
    window.fragment.setCurrentText('Метил · —CH₃')
    window.build_mode.setCurrentIndex(2)
    window.place_on_model((10, 0, 0), None)
    window.viewer.set_selection([0, 1, 2, 3, 4])
    assert not window.measure_fields[3].text()


def test_coordinate_unit_toggle_no_geometry_change(window):
    from modules.compass.chemistry.geometry_tools import BOHR

    mol = window.molecule
    dirty = window.dirty
    history = len(window.undo_history)
    for i in range(4):
        window.coord_units.setCurrentIndex(1)
        assert float(window.table.item(1, 1).text()) == pytest.approx(mol.atoms[1].x / BOHR)
        window.coord_units.setCurrentIndex(0)
    assert window.molecule == mol and window.dirty == dirty and len(window.undo_history) == history
    window.coord_units.setCurrentIndex(1)
    window.table.item(1, 1).setText('2')
    assert window.molecule.atoms[1].x == pytest.approx(2 * BOHR)
    window.undo_geometry()
    assert window.molecule.atoms[1].x == pytest.approx(mol.atoms[1].x, abs=1e-8)
    window.coord_format.setCurrentText('XYZ')
    assert not window.coord_units.isEnabled() and window.coord_units.currentIndex() == 0
    assert window.coord_text.toPlainText().startswith('3\n')


def test_bond_toggle_and_keyboard_scope(window, app):
    show_model(window, app)
    window.viewer.set_selection([0, 1])
    window.viewer.setFocus()
    original = connections(window.molecule)
    QTest.keyClick(window.viewer, Qt.Key.Key_B, Qt.KeyboardModifier.ControlModifier)
    assert connections(window.molecule) != original
    QTest.keyClick(window.viewer, Qt.Key.Key_B, Qt.KeyboardModifier.ControlModifier)
    assert set(connections(window.molecule)) == set(original)
    window.structure_tabs.setCurrentIndex(1)
    window.table.editItem(window.table.item(0, 1))
    app.processEvents()
    from PySide6.QtWidgets import QLineEdit

    editor = window.table.findChild(QLineEdit)
    QTest.keyClick(editor, Qt.Key.Key_Delete)
    assert len(window.molecule.atoms) == 3


def test_dihedral_and_undefined_angle_fields(window):
    window.load_molecule(
        Molecule('dihedral', (Atom('C', 1, 0, 0), Atom('C', 0, 0, 0), Atom('C', 0, 1, 0), Atom('C', 0, 1, 1)))
    )
    window.viewer.set_selection([0, 1, 2, 3])
    assert window.measure_fields[3].text() == '-90.00000 °'
    window.load_molecule(
        Molecule('linear', (Atom('C', 0, 0, 0), Atom('C', 1, 0, 0), Atom('C', 2, 0, 0), Atom('C', 2, 1, 0)))
    )
    window.viewer.set_selection([0, 1, 2, 3])
    assert window.measure_fields[3].text() == 'Не определён'


def test_gaussian_charge_and_units_note_refresh(window):
    window.coord_format.setCurrentText('Gaussian')
    window.coord_units.setCurrentIndex(1)
    window.charge.setValue(1)
    window.spin.setValue(2)
    assert window.coord_text.toPlainText().startswith('1 2\n')
    assert 'Units=Bohr' in window.coord_note.text()


def test_invalid_coordinate_blocks_unit_switch(window, monkeypatch):
    errors = []
    monkeypatch.setattr(window, 'error', lambda exc: errors.append(str(exc)))
    window.table.item(0, 1).setText('invalid')
    window.coord_units.setCurrentIndex(1)
    assert errors and window.coord_units.currentIndex() == 0
    assert window.table.item(0, 1).text() == 'invalid'


def test_center_space_keeps_orientation(window, app):
    show_model(window, app)
    view = window.viewer
    view.yaw = 0.7
    view.pitch = 0.2
    view.roll = 0.3
    view.zoom = 2
    view.keep_camera()
    view.setFocus()
    QTest.keyClick(view, Qt.Key.Key_Space)
    assert (view.yaw, view.pitch, view.roll) == (0.7, 0.2, 0.3)
    assert view.zoom == 1 and view.locked_camera is None


def test_perspective_size_and_projection(window):
    window.load_molecule(Molecule('depth', (Atom('C', 1, 0, 2), Atom('C', 1, 0, -2))))
    view = window.viewer
    view.yaw = 0
    view.pitch = 0
    view.roll = 0
    assert view.atom_radius(0) == view.atom_radius(1)
    window.projection.setCurrentIndex(1)
    assert view.atom_radius(0) > view.atom_radius(1)
    assert view.hit_test(view.projected()[0][0]) == 0
    window.projection.setCurrentIndex(0)
    assert not view.perspective


def test_edit_toggle_rotation_and_stretch_undo(window, app):
    show_model(window, app)
    window.viewer.set_selection([0, 1])
    original = window.molecule
    yaw = window.viewer.yaw
    window.rotate_control('y', 1)
    assert window.viewer.yaw != yaw and window.molecule == original
    window.edit_toggle.click()
    assert window.viewer.mode == 'atom' and window.edit_tools.isVisible()
    window.stretch_selected(0.05)
    from math import dist

    assert dist(window.molecule.atoms[0].position, window.molecule.atoms[1].position) == pytest.approx(
        dist(original.atoms[0].position, original.atoms[1].position) + 0.05, abs=1e-7
    )
    window.undo_geometry()
    assert window.molecule == original
    window.edit_toggle.click()
    assert window.viewer.mode == 'view' and not window.edit_tools.isVisible()


def test_axes_and_roll_inverse(window):
    window.axes_button.click()
    assert window.viewer.show_axes
    window.viewer.roll = 0.6
    assert window.viewer.from_view(window.viewer.to_view((1, 2, 3))) == pytest.approx((1, 2, 3))


def test_perspective_drag_tracks_cursor(window, app):
    window.load_molecule(Molecule('depth', (Atom('C', -1, 0, 2), Atom('C', 1, 0, -2))))
    show_model(window, app)
    view = window.viewer
    view.yaw = 0
    view.pitch = 0
    view.roll = 0
    window.projection.setCurrentIndex(1)
    window.build_mode.setCurrentIndex(3)
    before = view.projected()[0][0]
    point = before.toPoint()
    delta = QPoint(35, 15)
    QTest.mousePress(view, Qt.MouseButton.LeftButton, pos=point)
    QTest.mouseMove(view, point + delta, 10)
    QTest.mouseRelease(view, Qt.MouseButton.LeftButton, pos=point + delta)
    after = view.projected()[0][0]
    assert after.x() - before.x() == pytest.approx(35, abs=0.05)
    assert after.y() - before.y() == pytest.approx(15, abs=0.05)


def test_click_selection_without_modifiers_and_right_reset(window, app):
    show_model(window, app)
    points = window.viewer.projected()
    QTest.mouseClick(window.viewer, Qt.MouseButton.LeftButton, pos=points[0][0].toPoint())
    QTest.mouseClick(window.viewer, Qt.MouseButton.LeftButton, pos=points[1][0].toPoint())
    assert window.viewer.selected == [0, 1]
    QTest.mouseClick(window.viewer, Qt.MouseButton.LeftButton, pos=points[0][0].toPoint())
    assert window.viewer.selected == [1]
    QTest.mouseClick(window.viewer, Qt.MouseButton.RightButton, pos=points[1][0].toPoint())
    assert window.viewer.selected == []


def test_projection_buttons_panel_and_hold(window, app):
    show_model(window, app)
    assert not window.sidebar.isVisible()
    assert window.view_panel.isVisible()
    window.panel_toggle.click()
    app.processEvents()
    assert window.sidebar.isVisible()
    assert window.view_panel.isVisible()
    window.projection_buttons[1].click()
    assert window.viewer.perspective and not window.projection_buttons[0].isChecked()
    window.projection_buttons[1].click()  # a second press leaves it on
    assert window.viewer.perspective and window.projection_buttons[1].isChecked()
    assert not window.projection_buttons[0].isChecked()
    b = window.rotation_buttons[1]
    before = window.viewer.pitch
    QTest.mousePress(b, Qt.MouseButton.LeftButton)
    QTest.qWait(420)
    assert window.viewer.pitch != before
    QTest.mouseRelease(b, Qt.MouseButton.LeftButton)
    stopped = window.viewer.pitch
    QTest.qWait(100)
    assert window.viewer.pitch == stopped
    assert not window.undo_history


def test_hold_fragment_one_undo(window, app):
    show_model(window, app)
    window.edit_toggle.click()
    window.viewer.set_selection([0, 1])
    window.panel_toggle.click()
    app.processEvents()
    original = window.molecule
    before = len(window.undo_history)
    b = window.rotation_buttons[1]
    QTest.mousePress(b, Qt.MouseButton.LeftButton)
    QTest.qWait(410)
    # still held after several steps (an empty selection during the reload used to disable the button)
    assert b.isDown() and b.running and b.repeated and window.viewer.selected == [0, 1]
    QTest.mouseRelease(b, Qt.MouseButton.LeftButton)
    assert window.molecule != original
    assert len(window.undo_history) == before + 1
    window.undo_geometry()
    assert window.molecule == original


def test_move_whole_molecule_preserves_distances(window, app):
    from math import dist

    show_model(window, app)
    window.move_button.click()
    window.move_kind.setCurrentIndex(2)
    original = window.molecule
    start = window.viewer.projected()[0][0].toPoint()
    QTest.mousePress(window.viewer, Qt.MouseButton.LeftButton, pos=start)
    QTest.mouseMove(window.viewer, start + QPoint(40, 20))
    QTest.mouseRelease(window.viewer, Qt.MouseButton.LeftButton, pos=start + QPoint(40, 20))
    shifts = [
        tuple(b.position[k] - a.position[k] for k in range(3)) for a, b in zip(original.atoms, window.molecule.atoms)
    ]
    assert dist(shifts[0], (0, 0, 0)) > 0.01
    for shift in shifts:
        assert shift == pytest.approx(shifts[0], abs=1e-7)
    window.undo_geometry()
    assert window.molecule == original


def test_move_one_molecule_of_a_dimer_and_a_chain(window, app):
    # «Молекула целиком» moves only the molecule of the pressed atom (the other water stays);
    # the drag from the empty field turns the view; «Цепочка» moves the methyl of toluene, the ring stays
    from modules.compass.chemistry import library
    from math import dist

    show_model(window, app)
    water = ((0.0, 0.0, 0.0), (0.96, 0.0, 0.0), (-0.24, 0.93, 0.0))
    atoms = tuple(Atom(s, *p) for s, p in zip('OHH', water)) + tuple(Atom(s, x + 3.2, y, z) for s, (x, y, z) in zip('OHH', water))
    dimer = Molecule('dimer', atoms)
    window.load_molecule(dimer)
    window.move_button.click()
    window.move_kind_buttons['molecule'].click()

    def drag(index=None, by=QPoint(30, 25)):
        start = window.viewer.projected()[index][0].toPoint() if index is not None else QPoint(4, window.viewer.height() - 4)
        QTest.mousePress(window.viewer, Qt.MouseButton.LeftButton, pos=start)
        QTest.mouseMove(window.viewer, start + by)
        QTest.mouseRelease(window.viewer, Qt.MouseButton.LeftButton, pos=start + by)

    drag(3)
    moved = [i for i in range(6) if window.molecule.atoms[i].position != pytest.approx(dimer.atoms[i].position, abs=1e-6)]
    assert moved == [3, 4, 5] and window.viewer.selected == [3, 4, 5]  # the moved molecule is selected
    point = window.viewer.projected()[0][0].toPoint()
    QTest.mouseClick(window.viewer, Qt.MouseButton.LeftButton, pos=point)
    assert window.viewer.selected == [0, 1, 2]  # a click selects the whole molecule of the atom
    window.undo_geometry()
    turned = (window.viewer.basis, window.viewer.yaw, window.viewer.pitch)
    drag()  # from the empty field the view turns, the structure stays
    assert all(window.molecule.atoms[i].position == pytest.approx(dimer.atoms[i].position, abs=1e-6) for i in range(6))
    assert (window.viewer.basis, window.viewer.yaw, window.viewer.pitch) != turned
    toluene = library.molecule(next(k for k in library.keys() if k.startswith('Метилбензол')))
    window.load_molecule(toluene)
    window.move_kind_buttons['chain'].click()
    assert window.viewer.move_target == 'chain' and window.move_kind_buttons['chain'].isChecked()
    methyl = next(i for i, a in enumerate(toluene.atoms) if a.symbol == 'C' and sum(
        toluene.atoms[j if k == i else k].symbol == 'H' for k, j, _ in connections(toluene) if i in (k, j)) == 3)
    drag(methyl)
    moved = {i for i in range(len(toluene.atoms))
             if window.molecule.atoms[i].position != pytest.approx(toluene.atoms[i].position, abs=1e-6)}
    assert methyl in moved and len(moved) == 4  # the carbon and its three hydrogens
    # «Вокруг связи»: the two middle carbons of butane selected; dragging an end carbon to the right turns its
    # side about the bond by TWIST_DEG_PER_PX per pixel, the other side stays, the bond lengths stay
    from modules.compass.chemistry import torsion

    butane = library.molecule(next(k for k in library.keys() if k.startswith('Бутан')))
    window.load_molecule(butane)
    carbons = [i for i, a in enumerate(butane.atoms) if a.symbol == 'C']
    nb = {i: {j if k == i else k for k, j, _ in connections(butane) if i in (k, j)} & set(carbons) for i in carbons}
    line = [next(i for i in carbons if len(nb[i]) == 1)]
    while len(line) < 4:
        line.append(next(j for j in nb[line[-1]] if j not in line))
    a, b, c, d = line
    window.move_kind_buttons['twist'].click()
    window.viewer.set_selection([b, c])
    before = torsion.dihedral(butane, a, b, c, d)
    drag(d, QPoint(60, 0))
    turned = (torsion.dihedral(window.molecule, a, b, c, d) - before + 180) % 360 - 180
    assert abs(turned) == pytest.approx(60 * window.viewer.TWIST_DEG_PER_PX, abs=0.5)
    assert window.molecule.atoms[a].position == pytest.approx(butane.atoms[a].position, abs=1e-6)
    for i, j, _ in connections(butane):
        assert dist(window.molecule.atoms[i].position, window.molecule.atoms[j].position) == pytest.approx(
            dist(butane.atoms[i].position, butane.atoms[j].position), abs=1e-6)


def test_drag_fragment_preserves_attachment_and_internal_geometry(window, app):
    from math import dist

    show_model(window, app)
    mol = Molecule('chain', (Atom('C', 0, 0, 0), Atom('C', 1.5, 0, 0), Atom('H', 2.3, 0.8, 0)), ((0, 1, 1), (1, 2, 1)))
    window.load_molecule(mol)
    window.move_button.click()
    window.move_kind.setCurrentIndex(1)
    window.viewer.set_selection([0, 1])
    start = window.viewer.projected()[2][0].toPoint()
    QTest.mousePress(window.viewer, Qt.MouseButton.LeftButton, pos=start)
    QTest.mouseMove(window.viewer, start + QPoint(0, 45))
    QTest.mouseRelease(window.viewer, Qt.MouseButton.LeftButton, pos=start + QPoint(0, 45))
    assert window.molecule.atoms[0] == mol.atoms[0]
    assert window.molecule.atoms[2] != mol.atoms[2]
    for a, b in [(0, 1), (1, 2)]:
        assert dist(window.molecule.atoms[a].position, window.molecule.atoms[b].position) == pytest.approx(
            dist(mol.atoms[a].position, mol.atoms[b].position), abs=1e-7
        )


def test_best_view_and_pan_inverse_screenshot(window, app, tmp_path):
    from PySide6.QtGui import QImage

    show_model(window, app)
    original = window.molecule
    window.viewer.best_view()
    window.viewer.pan_view(25, -15)
    point = (0.3, 0.7, 1.1)
    assert window.viewer.from_view(window.viewer.to_view(point)) == pytest.approx(point)
    assert window.molecule == original
    window.viewer.zoom_view(0.4)
    path = tmp_path / 'view.png'
    window.viewer.screenshot(path)
    image = QImage(str(path))
    assert not image.isNull()
    assert image.width() < window.viewer.width() * window.viewer.devicePixelRatioF()
    window.viewer.center_view()
    assert window.viewer.pan.x() == 0


def test_fragment_mode_allows_selecting_pivot_before_drag(window, app, monkeypatch):
    show_model(window, app)
    window.move_button.click()
    window.move_kind.setCurrentIndex(1)
    errors = []
    monkeypatch.setattr(window, 'error', lambda message: errors.append(message))
    # The central oxygen has two neighbours: selection must not attempt a fragment drag.
    for i in [0, 1]:
        QTest.mouseClick(window.viewer, Qt.MouseButton.LeftButton, pos=window.viewer.projected()[i][0].toPoint())
    assert window.viewer.selected == [0, 1]
    assert not errors


@pytest.mark.parametrize('first', [Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton])
@pytest.mark.parametrize('mode', [0, 1, 3])
def test_both_mouse_buttons_pan_without_edit_or_selection(window, app, first, mode):
    from PySide6.QtCore import QEvent, QPointF
    from PySide6.QtGui import QMouseEvent

    show_model(window, app)
    window.build_mode.setCurrentIndex(mode)
    window.viewer.set_selection([0])
    v = window.viewer
    original = window.molecule
    angles = (v.yaw, v.pitch)
    pan = QPointF(v.pan)
    point = v.projected()[0][0]
    both = Qt.MouseButton.LeftButton | Qt.MouseButton.RightButton
    second = Qt.MouseButton.RightButton if first == Qt.MouseButton.LeftButton else Qt.MouseButton.LeftButton

    def send(kind, button, buttons, pos):
        QApplication.sendEvent(
            v, QMouseEvent(kind, pos, v.mapToGlobal(pos.toPoint()), button, buttons, Qt.KeyboardModifier.NoModifier)
        )

    send(QEvent.Type.MouseButtonPress, first, first, point)
    send(QEvent.Type.MouseButtonPress, second, both, point)
    end = point + QPointF(40, 25)
    send(QEvent.Type.MouseMove, Qt.MouseButton.NoButton, both, end)
    send(QEvent.Type.MouseButtonRelease, first, second, end)
    send(QEvent.Type.MouseButtonRelease, second, Qt.MouseButton.NoButton, end)
    assert v.pan == pan + QPointF(40, 25)
    assert (v.yaw, v.pitch) == angles
    assert window.molecule == original and v.molecule == original
    assert v.selected == [0] and not v.pan_gesture
    assert not window.undo_history


def test_drag_turns_the_near_side_with_the_mouse(window, app):
    # whatever the angles, dragging right moves the near side of the molecule to the right
    show_model(window, app)
    v = window.viewer
    for pitch in (-1.0, 2.5):
        v.yaw, v.pitch, v.roll, v.basis = 0.25, pitch, 0.0, None
        front = v.from_view((0, 0, 1))  # the point nearest to the viewer
        v.rotate_screen(0.2, 0)
        assert v.to_view(front)[0] > 0.1  # moved to the right
        down = v.from_view((0, 0, 1))
        v.rotate_screen(0, 0.2)
        assert v.to_view(down)[1] < -0.1  # dragging down moves it down


def test_right_drag_rotates_without_clearing_selection(window, app):
    show_model(window, app)
    window.move_button.click()
    window.viewer.set_selection([0])
    v = window.viewer
    original = window.molecule
    before = (v.yaw, v.pitch)
    start = v.projected()[0][0].toPoint()
    QTest.mousePress(v, Qt.MouseButton.RightButton, pos=start)
    QTest.mouseMove(v, start + QPoint(30, 20))
    QTest.mouseRelease(v, Qt.MouseButton.RightButton, pos=start + QPoint(30, 20))
    assert (v.yaw, v.pitch) != before
    assert v.selected == [0] and window.molecule == original


@pytest.mark.parametrize('perspective', [False, True])
def test_atoms_scale_past_old_radius_limit(window, app, perspective):
    show_model(window, app)
    v = window.viewer
    v.perspective = perspective
    v.zoom = 2
    before = v.atom_radius(0)
    v.zoom_view(2)
    assert v.atom_radius(0) > 48
    assert v.atom_radius(0) == pytest.approx(before * 2)


@pytest.mark.parametrize('mode', ['ball-stick', 'sticks', 'spacefill'])
def test_display_modes_preserve_geometry_and_capture(window, app, tmp_path, mode):
    show_model(window, app)
    original = window.molecule
    window.viewer.set_selection([0, 1])
    history = len(window.undo_history)
    window.display_mode.setCurrentIndex(window.display_mode.findData(mode))
    app.processEvents()
    assert window.viewer.display_mode == mode
    assert window.molecule == original and window.viewer.selected == [0, 1]
    assert len(window.undo_history) == history
    path = tmp_path / (mode + '.png')
    window.viewer.screenshot(path)
    assert path.stat().st_size > 100
    window.display_mode.setCurrentIndex(0)


def test_display_radii_and_stick_hit_testing(window, app):
    show_model(window, app)
    v = window.viewer
    v.frozen_camera = ((0, 0, 0), 100)
    window.display_mode.setCurrentIndex(0)
    ball = v.atom_radius(0)
    window.display_mode.setCurrentIndex(1)
    assert v.atom_radius(0) < ball
    assert v.hit_test(v.projected()[0][0]) == 0
    window.display_mode.setCurrentIndex(2)
    assert v.atom_radius(0) > ball
    window.display_mode.setCurrentIndex(0)
    v.frozen_camera = None


@pytest.mark.parametrize('order', [1, 2, 3])
def test_bond_halves_follow_element_colors(window, app, order):
    from PySide6.QtGui import QColor
    from modules.compass.view.viewer import COLORS

    show_model(window, app)
    v = window.viewer
    window.load_molecule(Molecule('CO', (Atom('C', -1, 0, 0), Atom('O', 1, 0, 0)), ((0, 1, order),)))
    window.display_mode.setCurrentIndex(0)
    v.yaw = v.pitch = v.roll = 0
    v.basis = None
    v.label_mode = 'none'
    app.processEvents()
    v._motion_until, v.press = 0.0, None  # a full-quality frame, not the fast one of a view just moved
    image = v.grab().toImage()
    ratio = image.devicePixelRatio()
    points = v.projected()
    a, b = points[0][0], points[1][0]
    # the bond thickness is a saved preference («Вид → Связи → Толщина»): take it from the view
    width = max(1, v.bond_width * v.camera()[1] * 0.08)
    offset = (0 - (order - 1) / 2) * width * 1.5
    # the samples lie on the visible bond between the two spheres (at 0.3 and 0.7 of the axis a thin bond of the
    # default thickness was under the shaded edge of the sphere of O — 15 units darker)
    length = ((b.x() - a.x()) ** 2 + (b.y() - a.y()) ** 2) ** 0.5
    ra, rb = v.atom_radius(0), v.atom_radius(1)
    gap = length - ra - rb
    assert gap > 6
    for along, symbol in [((ra + gap * 0.25) / length, 'C'), (1 - (rb + gap * 0.25) / length, 'O')]:
        point = a + (b - a) * along
        expected = QColor(COLORS[symbol])
        # the element colour is the middle strip of the rod (raster.FLAT); light comes from the upper left, so
        # one physical pixel below the axis of a thin rod is already ~15 units darker. round() of the axis picked that
        # pixel whenever the axis fell in the lower half of a pixel: take the pixel holding the axis and its two
        # neighbours across the rod, and compare the one closest to the element colour
        x, y = int(point.x() * ratio), int((point.y() + offset) * ratio)
        colors = [image.pixelColor(x, y + d) for d in (-1, 0, 1)]
        color = min(colors, key=lambda c: abs(c.red() - expected.red()) + abs(c.blue() - expected.blue()))
        # Windows smooths the edge of the half a little more (6 units of red)
        assert abs(color.red() - expected.red()) < 9, (symbol, [c.name() for c in colors], expected.name())
        assert abs(color.blue() - expected.blue()) < 9, (symbol, [c.name() for c in colors], expected.name())


def test_smooth_bond_midpoint_has_blended_color(window, app):
    from modules.compass.view.viewer import COLORS
    from PySide6.QtGui import QColor

    show_model(window, app)
    v = window.viewer
    window.load_molecule(Molecule('CO', (Atom('C', -1, 0, 0), Atom('O', 1, 0, 0)), ((0, 1, 1),)))
    v.yaw = v.pitch = v.roll = 0
    v.basis = None
    v.bond_color = 'smooth'
    v.display_mode = 'ball-stick'
    app.processEvents()
    image = v.grab().toImage()
    a, b = [p[0] for p in v.projected()]
    mid = (a + b) * 0.5
    ratio = image.devicePixelRatio()
    color = image.pixelColor(round(mid.x() * ratio), round(mid.y() * ratio))
    first = QColor(COLORS['C'])
    second = QColor(COLORS['O'])
    assert first.red() + 20 < color.red() < second.red() - 20


def test_bottom_geometry_edit_modes_and_undo(window, app):
    from modules.compass.chemistry.geometry_tools import measurement

    show_model(window, app)
    original = window.molecule
    window.viewer.set_selection([0, 1])
    field = window.measure_fields[3]
    assert not field.isReadOnly() and window.geometry_fragment.isChecked()
    window.geometry_atom.click()
    assert window.geometry_atom.isChecked() and not window.geometry_fragment.isChecked()
    window.geometry_atom.click()
    assert window.geometry_atom.isChecked()
    field.setText('1,25')
    QTest.keyClick(field, Qt.Key.Key_Return)
    assert measurement([window.molecule.atoms[i].position for i in [0, 1]])[1] == pytest.approx(1.25)
    assert window.molecule.atoms[2] == original.atoms[2]
    window.undo_geometry()
    assert window.molecule == original
    assert field.isReadOnly()


def test_bottom_angle_entry(window, app):
    from modules.compass.chemistry.geometry_tools import measurement

    show_model(window, app)
    window.viewer.set_selection([1, 0, 2])
    window.geometry_fragment.click()
    field = window.measure_fields[3]
    field.setText('115°')
    QTest.keyClick(field, Qt.Key.Key_Return)
    assert measurement([window.molecule.atoms[i].position for i in [1, 0, 2]])[1] == pytest.approx(115, abs=1e-6)


def test_click_on_the_empty_field_folds_the_drawer(window, app):
    # a click on the empty field of Compass folds the drawer of the result; ☰ fits the row of the tabs
    show_model(window, app)
    window.opening_tool.demo_optimization()
    app.processEvents()
    assert window.drawer.isVisible() and window.trajectory_button.isChecked()
    # as tall as «Молекула | Координаты» (not taller: the row keeps its height)
    assert window.view_tabs.height() - 4 <= window.trajectory_button.height() <= window.view_tabs.height()
    corner = QPoint(window.viewer.width() - 6, window.viewer.height() - 6)
    assert window.viewer.hit_test(corner) is None
    QTest.mouseClick(window.viewer, Qt.MouseButton.LeftButton, pos=corner)
    assert not window.trajectory_button.isChecked() and not window.browsing


def test_fill_hydrogens_button(window, app):
    show_model(window, app)
    window.new_molecule()
    window.element.setCurrentText('C')  # new_molecule: atom mode
    assert window.viewer.mode == 'atom'
    window.place_on_model((0, 0, 0), None)
    window.place_on_model((0, 0, 0), 0)  # C–C
    assert window.hydrogens_button.isVisible()
    window.hydrogens_button.click()
    window.iupac_button.click()  # the name on demand
    assert window.molecule.formula == 'C2H6' and window.molecule_info.text().startswith('этан')
    window.hydrogens_button.click()
    assert window.molecule.formula == 'C2H6'  # nothing more to add


def test_element_tile_cleanup_and_narrow_panel(window, app):
    show_model(window, app)
    window.new_molecule()
    window.element.setCurrentText('O')
    assert window.element_tile.isVisible() and window.element_tile.symbol == 'O' and not window.choice_label.isVisible()
    assert not window.bond_order.isVisible() and window.view_panel.width() - window.view_panel_gap <= 90  # the spacing
    # inside
    window.place_on_model((0, 0, 0), None)
    window.hydrogens_button.click()
    rough = window.molecule
    atoms = list(rough.atoms)
    atoms[1] = Atom('H', atoms[1].x * 1.3, atoms[1].y * 1.3, atoms[1].z * 1.3)
    window.load_molecule(replace(rough, atoms=tuple(atoms)))
    window.cleanup_button.click()
    from math import dist

    a = window.molecule.atoms
    assert abs(dist(a[0].position, a[1].position) - dist(a[0].position, a[2].position)) < 1e-3
    assert 'Повернуть' in window.rotation_buttons[0].toolTip()


def test_constraints_and_zmatrix(window, app):
    show_model(window, app)
    window.load_molecule(read_xyz(EXAMPLES['Вода · H₂O']))
    window.task.setCurrentIndex(window.task.findText('Оптимизация'))
    window.viewer.set_selection([0, 1])
    window.constraint_tool.toggle()
    assert window.constraints == [('B', (0, 1))] and window.viewer.constraints == [('B', (0, 1))]
    window.model_menu_tool.atom_menu(0)
    window.constraint_tool.toggle([0])
    window.input_tool.refresh_input()
    text = window.preview.toPlainText()
    assert '{ B 0 1 C }' in text and '{ C 0 C }' in text and 'Ограничений оптимизации: 2' in window.state_info.text()
    menu = window.constraint_tool.menu()
    assert any(a.text().strip().startswith('Длина O1–H2') for a in menu.actions())
    window.constraint_tool.toggle([1, 0])
    assert window.constraints == [('C', (0,))]  # the same bond, reversed
    window.structure_tabs.setCurrentIndex(1)
    window.coord_format.setCurrentText('Z-matrix')
    lines = window.coord_text.toPlainText().splitlines()
    assert lines[0].strip() == 'O' and len(lines) == 3
    window.coord_format.setCurrentIndex(0)
    window.structure_tabs.setCurrentIndex(0)
    window.load_molecule(read_xyz(EXAMPLES['Метан · CH₄']))
    assert window.constraints == []


def test_selection_tools(window, app):
    show_model(window, app)
    window.load_molecule(read_xyz(EXAMPLES['Этан · C₂H₆ · перемещение фрагмента']))
    app.processEvents()
    v = window.viewer
    pts = [p for p, _ in v.projected()]
    xs = [p.x() for p in pts]
    ys = [p.y() for p in pts]
    QTest.mousePress(
        v, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ShiftModifier, QPoint(int(min(xs)) - 20, int(min(ys)) - 20)
    )
    QTest.mouseMove(v, QPoint(int(max(xs)) + 20, int(max(ys)) + 20))
    QTest.mouseRelease(
        v, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ShiftModifier, QPoint(int(max(xs)) + 20, int(max(ys)) + 20)
    )
    assert sorted(v.selected) == list(range(8))  # the band took every atom
    window.selection_tool.select_element('C')
    assert v.selected == [0, 1]
    window.selection_tool.invert_selection()
    assert sorted(v.selected) == list(range(2, 8))
    window.selection_tool.select_fragment(0)
    assert sorted(v.selected) == list(range(8))
    v.set_selection([0])
    window.selection_tool.copy_atoms()
    assert QApplication.clipboard().text().startswith('1\n')
    window.selection_tool.paste_atoms()
    assert len(window.molecule.atoms) == 9 and v.selected == [8]
    before = window.molecule.atoms[0].position
    v.set_selection([])
    window.selection_tool.mirror_atoms('x')
    assert window.molecule.atoms[0].x != before[0]
    window.undo_geometry()
    window.undo_geometry()
    assert len(window.molecule.atoms) == 8
    window.move_button.click()
    window.move_kind_buttons['selection'].click()
    assert v.move_target == 'selection'
    v.set_selection([2, 3])
    start = v.projected()[2][0].toPoint()
    old = [window.molecule.atoms[i].position for i in (0, 2, 3)]
    QTest.mousePress(v, Qt.MouseButton.LeftButton, pos=start)
    QTest.mouseMove(v, start + QPoint(30, 0))
    QTest.mouseRelease(v, Qt.MouseButton.LeftButton, pos=start + QPoint(30, 0))
    new = [window.molecule.atoms[i].position for i in (0, 2, 3)]
    assert new[0] == old[0] and new[1] != old[1] and new[2] != old[2]  # only the selection moved
    window.move_button.click()


def test_bottom_row_notice_symmetry_and_next(window, app):
    show_model(window, app)
    window.load_molecule(read_xyz(EXAMPLES['Вода · H₂O']))
    window.symmetry_button.click()  # the first press finds the group, the second symmetrises
    assert window.symmetry_button.isEnabled() and 'C2v' in window.symmetry_button.toolTip()
    assert window.symmetry_button.parent() is window.molecule_info.parent()  # next to the point group
    window.symmetry_button.click()
    a = window.molecule.atoms
    assert abs(a[0].x) < 1e-7 and abs(a[0].y) < 1e-7
    assert window.notice.text().startswith('Симметризовано до C2v') and window.statusBar().isHidden()
    # the message is a pill over the bottom of the model, not a line in the row under it
    assert window.notice.parentWidget() is window.viewer.parentWidget() and window.notice.isVisible()
    assert window.viewer.geometry().contains(window.notice.geometry())
    window.hide_notice()
    assert window.notice.isHidden() and not window.notice.text()
    assert window.next_button.width() > 100 and 'К параметрам расчёта' in window.next_button.text()
    # the colour of the other filled buttons in the theme of the program, whatever the palette says
    window.theme.setCurrentIndex(0)
    corner = window.next_button.grab().toImage().pixelColor(4, 17)
    assert (corner.red(), corner.green(), corner.blue()) == (0x2A, 0x62, 0xB8)
    window.next_button.dark = True  # the same blue in the dark theme (as the button of the language)
    corner = window.next_button.grab().toImage().pixelColor(4, 17)
    assert (corner.red(), corner.green(), corner.blue()) == (0x2A, 0x62, 0xB8)
    window.next_button.dark = False
    QApplication.sendEvent(window.next_button, QEvent(QEvent.Type.Leave))
    QTest.qWait(300)
    assert window.next_button.width() > 100 and 'К параметрам расчёта' in window.next_button.text()  # stays wide
    wide = window.next_button.width()
    window.next_button.full = 'К расчёту кристалла · длиннее'
    assert window.next_button.width() > wide
    window.next_button.full = 'К параметрам расчёта'
    window.next_button.click()
    assert window.stack.currentIndex() == 1
    window.navigate(0)


def test_model_overlays_pictures_and_stable_symmetry(window, app, tmp_path, monkeypatch):
    from modules.compass.actions import pictures

    show_model(window, app)
    dimer = read_xyz('6\nwater dimer\nO 0 0 0\nH 0.96 0 0\nH -0.24 0.93 0\nO 2.9 0 0\nH 3.2 0.9 0\nH 3.2 -0.45 0.78')
    window.load_molecule(dimer)
    assert window.viewer.hydrogen_bonds() == [(1, 3)]
    window.lengths_action.trigger()
    assert window.viewer.show_lengths
    window.viewer.set_selection([])
    assert not window.pin_button.isEnabled()  # the ruler needs 2–4 atoms
    window.viewer.set_selection([1, 0, 2])
    assert window.pin_button.isEnabled() and not window.pin_button.isChecked()
    window.pin_button.click()
    assert window.viewer.pinned == [(1, 0, 2)] and window.pin_button.isChecked()
    app.processEvents()
    window.viewer.repaint()  # draws the tags without errors
    window.viewer.set_selection([2, 0, 1])
    assert window.pin_button.isChecked()  # the same angle
    window.pin_button.click()
    assert window.viewer.pinned == []
    window.lengths_action.trigger()
    chosen = iter(range(100))  # the save dialog answers with new files in tmp_path
    monkeypatch.setattr(
        pictures,
        'ask_picture_path',
        lambda parent, title, name, suffix, prefs=None: tmp_path / f'{next(chosen)}{suffix}',
    )
    from PySide6.QtGui import QImage

    window.picture_tool.save_screenshot(1)
    small = QImage(str(next(tmp_path.glob('*.png'))))
    for f in tmp_path.glob('*.png'):
        f.unlink()
    window.picture_tool.save_screenshot(3)
    big = QImage(str(next(tmp_path.glob('*.png'))))
    assert abs(big.width() / small.width() - 3) < 0.1  # three times the resolution
    path = window.picture_tool.save_rotation_gif()
    assert path.read_bytes()[:6] == b'GIF89a'
    window.load_molecule(read_xyz(EXAMPLES['Вода · H₂O']))
    window.symmetry_button.click()  # finds the group
    window.symmetry_button.click()
    once = window.molecule.atoms
    window.symmetry_button.click()
    assert window.molecule.atoms == once  # a second press changes nothing
    from PySide6.QtGui import QWheelEvent
    from PySide6.QtCore import QPointF

    pan = QPointF(window.viewer.pan)
    event = QWheelEvent(
        QPointF(50, 50),
        QPointF(50, 50),
        QPoint(0, 30),
        QPoint(0, 120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.ScrollUpdate,
        False,
    )
    window.viewer.wheelEvent(event)
    assert window.viewer.pan != pan  # two fingers move the view
    zoom = window.viewer.zoom
    event = QWheelEvent(
        QPointF(50, 50),
        QPointF(50, 50),
        QPoint(0, 0),
        QPoint(0, 120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )
    window.viewer.wheelEvent(event)
    assert window.viewer.zoom > zoom  # a mouse wheel zooms


def test_moving_view_draws_fast_frames_then_full_quality(app):
    # while the view moves, the model is drawn with 4 times fewer pixels (half the
    # resolution on a Retina screen, no supersampling on others); MOTION_REFINE ms after the last
    # movement a full-quality frame follows; snapshots are never fast frames.
    from math import ceil
    from PySide6.QtTest import QTest
    from modules.compass.chemistry import library
    from modules.compass.view.viewer import MoleculeView

    view = MoleculeView()
    view.resize(400, 240)
    view.set_molecule(library.molecule(next(k for k in library.keys() if k.startswith('Бензол'))))
    ratio = view.devicePixelRatioF()

    def work():
        view.grab()
        width, height, supersample = view._model_image[0][:3]
        return width * height * supersample**2

    full = ceil(view.width() * ratio) * ceil(view.height() * ratio) * (1 if ratio >= 2 else 4)
    assert not view.interactive() and work() == full
    view._full_seconds = 1.0  # a slow full frame — the moving frames are fast ones
    view.rotate_screen(0.2, 0.1)
    assert view.interactive() and work() == pytest.approx(full / 4, rel=0.02)
    view._full_seconds = 0.0  # a full frame drawn fast enough (bond_depth.FULL_ENOUGH) — it stays while the view moves
    view.rotate_screen(0.2, 0.1)
    assert view.interactive() and work() == full
    view._full_seconds = 0.06  # a fair full frame — 3/4 of the resolution on a Retina screen (was 1/2)
    view.rotate_screen(0.2, 0.1)
    fair = (ceil(view.width() * ratio * 0.75) * ceil(view.height() * ratio * 0.75)) if ratio >= 1.5 else full / 4
    assert view.interactive() and work() == pytest.approx(fair, rel=0.02)
    view._full_seconds = 1.0
    view.capture = True
    assert not view.interactive()
    view.capture = False
    QTest.qWait(view.MOTION_REFINE + 120)
    assert not view.interactive() and work() == full
    view.zoom_view(1.1)
    assert view.interactive()


def test_bonds_by_distance_are_found_once_per_structure():
    from azimuth.core import read_xyz
    from modules.compass.chemistry import builder

    text = '3\nwater\nO 0 0 0\nH 0.96 0 0\nH -0.24 0.93 0'
    molecule = read_xyz(text)
    first = builder.connections(molecule)
    assert builder.connections(molecule) is first  # the same structure: kept
    other = read_xyz(text.replace('0.96', '2.96'))
    assert builder.connections(other) == ((0, 2, 1),)  # another structure: searched again
    assert builder.connections(molecule) is first


def test_rotation_about_a_bond_window(window, monkeypatch):
    # exact dihedral, turn by an angle, a drag on the turning side, commit / undo, cancel,
    # the conformer scan into the steps drawer and as XYZ frames; a ring bond is refused
    from modules.compass.chemistry import library, torsion
    from modules.compass.chemistry.builder import connections

    butane = library.molecule(next(k for k in library.keys() if k.startswith('Бутан')))
    window.load_molecule(butane)
    carbons = [i for i, a in enumerate(butane.atoms) if a.symbol == 'C']
    nb = {i: {j if k == i else k for k, j, _ in connections(butane) if i in (k, j)} & set(carbons) for i in carbons}
    chain = [next(i for i in carbons if len(nb[i]) == 1)]
    while len(chain) < 4:
        chain.append(next(j for j in nb[chain[-1]] if j not in chain))
    a, b, c, d = chain

    def angle():
        return torsion.dihedral(window.molecule, a, b, c, d)

    start = angle()
    window.viewer.set_selection(chain)
    w = window.compass_dialogs.torsion()
    assert w is not None and (w.a, w.b, w.c, w.d) == (a, b, c, d)
    w.set_target(60.0)
    assert angle() == pytest.approx(60.0, abs=1e-4)
    w.turn_by(15.0)
    assert angle() == pytest.approx(75.0, abs=1e-4)
    assert c in window.viewer.twist_group and b not in window.viewer.twist_group
    window.viewer.twist('start', 0.0)
    window.viewer.twist('move', 30.0)
    window.viewer.twist('end', 30.0)
    assert angle() == pytest.approx(105.0, abs=1e-4)
    window.viewer.grab()
    w.commit()
    assert window.viewer.twist is None and angle() == pytest.approx(105.0, abs=1e-4)
    window.undo_geometry()
    assert angle() == pytest.approx(start, abs=1e-4)
    w = window.compass_dialogs.torsion(b, c)
    w.set_target(0.0)
    w.cancel()
    assert angle() == pytest.approx(start, abs=1e-4)
    w = window.compass_dialogs.torsion(b, c)
    text = w.scan_text(60)
    assert text.count('поворот') == 6 and 'двугранный угол' in text
    scan = w.scan_to_drawer(30)
    assert len(scan.points) == 12 and len(window.drawer.steps) == 12
    window.trajectory_tool.set_trajectory_open(False)
    ring = library.molecule(next(k for k in library.keys() if k.startswith('Циклогексан')))
    window.load_molecule(ring)
    i, j, _ = next(e for e in connections(ring) if ring.atoms[e[0]].symbol == 'C' and ring.atoms[e[1]].symbol == 'C')
    errors = []
    monkeypatch.setattr(window, 'error', lambda exc: errors.append(str(exc)))  # no modal box offscreen
    assert window.compass_dialogs.torsion(i, j) is None  # a ring bond: refused with a message
    assert len(errors) == 1 and errors[0]


def test_display_schemes(window, monkeypatch):
    # a ready scheme sets the model, the labels, the bonds, the colours, the background and
    # the grid at once; an element colour; a user scheme saved and deleted; the user's settings restored
    from PySide6.QtGui import QColor
    from modules.compass.view import schemes
    from modules.compass.actions.scheme_actions import SETTINGS_KEY

    keys = (SETTINGS_KEY, 'atom_scale', 'palette', 'element_colors', 'background', 'grid', 'display_mode',
            'atom_labels', 'bond_color', 'bond_width', 'show_bonds', 'multiple_bonds')
    saved = {k: window.preferences.value(k) for k in keys}
    before = window.scheme_tool.current_scheme()
    try:
        window.scheme_tool.apply_scheme(schemes.BUILTIN['Публикация · белый фон'])
        assert window.viewer.background == 'white' and not window.viewer.grid and window.viewer.label_mode == 'none'
        assert window.viewer.palette['O'] == '#ff0d0d'
        image = window.viewer.grab().toImage()
        assert QColor(image.pixel(3, 3)) == QColor('#ffffff')  # the white background, no grid dot there
        window.scheme_tool.apply_scheme(schemes.BUILTIN['Стержни'])
        assert window.viewer.display_mode == 'sticks' and window.bond_width_actions[1.6].isChecked()
        window.scheme_tool.set_element_color('C', '#ff00ff')
        assert window.viewer.palette['C'] == '#ff00ff' and window.scheme_tool.current_scheme()['colors'] == {'C': '#ff00ff'}
        assert window.scheme_tool.save_scheme('Тест-схема') == 'Тест-схема'
        window.scheme_tool.fill_scheme_menu(window.scheme_menu)
        checked = [a.text() for a in window.scheme_menu.actions() if a.isCheckable() and a.isChecked()]
        assert checked == ['Тест-схема', 'Сетка точек']  # the current look is that scheme (and the grid is on)
        window.load_molecule(window.molecule)
        window.scheme_tool.reset_element_colors()
        assert window.viewer.palette['C'] == schemes.AZIMUTH['C']
        assert window.scheme_tool.delete_scheme('Тест-схема', ask=False) and 'Тест-схема' not in window.user_schemes
        errors = []
        monkeypatch.setattr(window, 'error', lambda exc: errors.append(str(exc)))  # no modal box offscreen
        assert window.scheme_tool.save_scheme('Стержни') is None  # a ready scheme's name
        assert len(errors) == 1 and 'готовая схема' in errors[0]
    finally:
        window.scheme_tool.apply_scheme(before)
        for k, v in saved.items():
            if v is None:
                window.preferences.remove(k)
            else:
                window.preferences.setValue(k, v)


def test_labels_behind_atoms_and_scales_behind_the_molecule(window, app):
    # a label is cut by the atoms in front of its own; the hub's faint scales are not drawn over the model
    from PySide6.QtCore import QRect
    from PySide6.QtGui import QImage, QPainter, QRegion
    from hub.chrome import Ornament
    from azimuth.core import Atom, Molecule

    v = window.viewer
    window.navigate(0)
    v.resize(480, 360)
    v.yaw = v.pitch = v.roll = 0.0
    v.basis = None
    v.set_molecule(Molecule('pair', (Atom('C', 0, 0, 0), Atom('O', 0, 0, 1.0), Atom('N', 3, 0, 0)), ()))
    app.processEvents()
    points = v.projected()
    assert points[1][1] > points[0][1]  # O is nearer than C, straight in front of it
    assert v.label_clip(0).isEmpty()  # C is hidden: no label at all
    assert v.label_clip(1) is None and v.label_clip(2) is None  # nothing in front of O or N
    v.set_molecule(Molecule('pair', (Atom('C', 0, 0, 0), Atom('O', 0.3, 0, 1.0)), ()))
    points, radii = v.projected(), [v.atom_radius(k) for k in range(2)]
    clip = v.label_clip(0)
    c, o = points[0][0], points[1][0]
    assert radii[0] < (o - c).manhattanLength() < radii[0] + radii[1]  # overlapping, centre of C still free
    assert not clip.isEmpty() and not clip.contains(((c + o) / 2).toPoint())  # partly hidden: cut where O is
    assert clip.contains((c - (o - c) * 0.5).toPoint())  # the free side stays
    v.grab()  # draws without errors; the layout of the window may resize the view here, so the atoms are taken again
    c, o = (point for point, _ in v.projected())
    cover = v.ornament_cover()
    assert cover.contains(c.toPoint()) and cover.contains(o.toPoint()) and not cover.contains(QRect(0, 0, 4, 4).center())
    # the scales: none where the molecule is, the usual ones elsewhere
    ornament = Ornament()
    ornament.resize(500, 500)
    ornament.set_section('compass')
    image = QImage(500, 500, QImage.Format.Format_ARGB32_Premultiplied)
    for opaque, painted in ((QRegion(), True), (QRegion(0, 0, 500, 500), False)):
        image.fill(0)
        painter = QPainter(image)
        ornament.paint_layers(painter, QRegion(), opaque)
        painter.end()
        drawn = any(image.pixelColor(x, y).alpha() for x in range(0, 500, 4) for y in range(0, 500, 4))
        assert drawn == painted


def test_undo_during_a_preview_keeps_the_history(window):
    # undo while «Вращение вокруг связи» or the Z-matrix editor shows a preview cancels the preview first;
    # the last real structure is not lost (before: redo brought back the preview and skipped it)
    from modules.compass.chemistry import library
    from modules.compass.chemistry.builder import connections

    butane = library.molecule(next(k for k in library.keys() if k.startswith('Бутан')))
    window.load_molecule(butane)
    first = window.molecule
    window.viewer.set_selection([0])
    window.chem_actions['shake'].trigger()
    shaken = window.molecule
    carbons = [i for i, a in enumerate(butane.atoms) if a.symbol == 'C']
    heavy = {i: [j if k == i else k for k, j, _ in connections(butane) if i in (k, j)] for i in carbons}
    inner = [i for i in carbons if sum(n in carbons for n in heavy[i]) == 2]
    b, c = inner[0], next(n for n in heavy[inner[0]] if n in inner)
    w = window.compass_dialogs.torsion(b, c)
    w.turn_by(40.0)
    assert window.molecule != shaken  # the preview is shown
    window.undo_geometry()
    assert not w.isVisible() and window.molecule == first
    window.redo_geometry()
    assert window.molecule == shaken
    z = window.view_tool.open_zmatrix_editor()
    window.undo_geometry()
    assert not z.isVisible() and window.molecule == first


def test_a_large_structure_opens_draws_and_selects_in_time(window):
    # 1500 atoms (a box of water) — loading, a drawing, selecting all and the labels each in a few seconds
    import time

    atoms = []
    for i in range(8):
        for j in range(8):
            for k in range(8):
                x, y, z = 3.1 * i, 3.1 * j, 3.1 * k
                atoms += [Atom('O', x, y, z), Atom('H', x + 0.96, y, z), Atom('H', x - 0.24, y + 0.93, z)]
    box = Molecule('box', tuple(atoms[:1500]))
    start = time.perf_counter()
    window.load_molecule(box)
    assert len(window.molecule.atoms) == 1500
    loaded = time.perf_counter() - start
    start = time.perf_counter()
    window.viewer.grab()
    drawn = time.perf_counter() - start
    start = time.perf_counter()
    window.viewer.set_selection(list(range(1500)))
    window.viewer.grab()
    selected = time.perf_counter() - start
    print(f'1500 atoms: load {loaded:.2f} s, draw {drawn:.2f} s, select all {selected:.2f} s')
    assert loaded < 5 and drawn < 5 and selected < 5


def test_hide_hydrogens_in_every_display_mode(window):
    # «Скрыть атомы H» — the hydrogens are left out of the drawn scene in every display mode (the same scene
    # feeds the built-in renderer and VTK), their labels, picking and the rubber band; a selected H stays; the
    # structure keeps them
    from modules.compass.view.bond_depth import model_scene

    water = window.molecule  # the window starts from the water
    assert [a.symbol for a in water.atoms].count('H') == 2
    view = window.viewer
    view.set_selection([])
    window.chem_actions['hide_h'].trigger()
    assert view.hide_hydrogens and view.hidden_atoms() == {k for k, a in enumerate(water.atoms) if a.symbol == 'H'}
    # the display mode is remembered in the settings, which the tests of a run share: the last mode of the loop
    # («spacefill») stayed for every window opened later, and a test that counted the drawn bonds found none
    # (test_the_style_and_the_types_of_bonds failed only after this one, 2026-11-23)
    mode = view.display_mode
    try:
        for key, item in window.display_actions.items():
            item.trigger()
            spheres, rods = model_scene(view, view.projected(), view.palette)
            assert len(spheres) == 1 and not rods, key  # only O, no O–H bonds
            view.grab()
    finally:
        window.display_actions[mode].trigger()
    h = next(k for k, a in enumerate(water.atoms) if a.symbol == 'H')
    point = view.projected()[h][0]
    assert view.hit_test(point) in (None, next(k for k, a in enumerate(water.atoms) if a.symbol == 'O'))
    view.set_selection([h])
    spheres, rods = model_scene(view, view.projected(), view.palette)
    assert len(spheres) == 2  # the selected H is drawn
    assert window.molecule == water  # nothing removed from the structure
    window.chem_actions['hide_h'].trigger()
    assert not view.hide_hydrogens and not view.hidden_atoms()


def test_delete_key_in_the_coordinates_table(window):
    # Delete or Backspace in the coordinates table removes the atoms of the selected rows;
    # one undoable step
    start = window.molecule
    assert len(start.atoms) == 3  # the water of the window
    for key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
        window.viewer.set_selection([])
        window.table.clearSelection()
        window.table.selectRow(2)
        window.table.setFocus()
        QTest.keyClick(window.table, key)
        assert len(window.molecule.atoms) == 2, key
        window.undo_geometry()
        assert window.molecule == start, key


def test_the_model_stays_put_when_modes_change_and_steps_are_browsed(window):
    # switching to «Изменение структуры» or «Перемещение» changes the rows above the field;
    # the model keeps its place and size in the window; the step kept when the drawer closes stays as it was shown
    # (the steps keep the coordinates of the file — the table shows what the program wrote).
    import math
    from PySide6.QtCore import QPoint

    from modules.compass.chemistry import formats

    def where(i=0):
        point = window.viewer.projected()[i][0]
        return window.viewer.mapTo(window, QPoint(round(point.x()), round(point.y()))), window.viewer.atom_radius(i)

    window.resize(1280, 800)
    window.show()
    app = QApplication.instance()
    app.processEvents()
    before, radius = where()
    for toggle in (window.edit_toggle, window.edit_toggle, window.move_button, window.move_button):
        toggle.click()
        app.processEvents()
        after, r = where()
        assert abs(after.x() - before.x()) <= 1 and abs(after.y() - before.y()) <= 1, toggle
        assert abs(r - radius) < 0.5
    own = window.molecule
    turned = []
    for k, stretch in enumerate((1.0, 1.02)):
        c, s = math.cos(math.pi / 2 * k), math.sin(math.pi / 2 * k)
        rows = [f'{a.symbol} {c * a.x * stretch - s * a.y * stretch + 3 * k} {s * a.x * stretch + c * a.y * stretch} {a.z}'
                for a in own.atoms]
        turned.append(f'{len(rows)}\nE {-76 - k}\n' + '\n'.join(rows))
    window.trajectory_tool.load_trajectory(formats.xyz_trajectory('\n'.join(turned) + '\n'), 'two orientations')
    window.trajectory_tool.set_trajectory_open(True, 'steps')
    app.processEvents()
    window.drawer.select(1)
    app.processEvents()
    shown = window.viewer.molecule
    assert shown.atoms == window.drawer.steps[1].geometry.atoms  # the coordinates of the file, as they are
    camera = window.viewer.camera()
    window.trajectory_tool.set_trajectory_open(False, keep=True)
    app.processEvents()
    assert window.molecule.atoms == shown.atoms or max(
        math.dist(a.position, b.position) for a, b in zip(window.molecule.atoms, shown.atoms)) < 1e-6
    assert window.viewer.camera()[1] == pytest.approx(camera[1])
    window.undo_geometry()
    assert window.molecule == own


def test_vectors_and_planes_on_the_model(window, app, monkeypatch):
    # a vector, a normal and a plane made from the selection, drawn on
    # the model, their angles, the list as text, kept with the tab
    from math import cos, radians, sin

    from azimuth.core import read_xyz

    monkeypatch.setattr(window, 'confirm_replace', lambda *a, **k: True)
    errors = []
    monkeypatch.setattr(window, 'error', errors.append)
    ring = [(1.39 * cos(radians(60 * k)), 1.39 * sin(radians(60 * k)), 0.0) for k in range(6)]
    tilted = [(x, y * cos(radians(30)), y * sin(radians(30)) + 3.5) for x, y, _ in ring]
    window.load_molecule(read_xyz('12\nrings\n' + '\n'.join(f'C {x} {y} {z}' for x, y, z in ring + tilted)))
    menu = window.chem_menus['guides']
    assert [a.text() for a in menu.actions() if a.text()][:3] == [
        'Вектор между выделенными атомами', 'Нормаль к плоскости выделенных атомов', 'Плоскость через выделенные атомы']
    window.viewer.set_selection(list(range(6)))
    assert window.structure_tool.add_guide('plane')['atoms'] == tuple(range(6))
    window.viewer.set_selection(list(range(6, 12)))
    assert window.structure_tool.add_guide('normal')['kind'] == 'normal'
    window.viewer.set_selection([3, 0])
    assert window.structure_tool.add_guide('vector') == {'kind': 'vector', 'atoms': (3, 0)}
    window.viewer.set_selection([0])
    assert window.structure_tool.add_guide('vector') is None and len(window.viewer.guides) == 3  # one atom: nothing
    text = window.structure_tool.guide_angles_text()
    assert '1. плоскость C1–C6' in text and '3. вектор C4 → C1' in text
    assert 'Угол 1–2: 60.00°' in text and 'Угол 1–3: 0.00°' in text  # the tilted ring's normal; a vector in the plane
    assert not window.viewer.render_image(1, False).isNull()  # drawn with them
    assert window.structure_tool.edit_guides_text('плоскость 7-12\nвектор 1 4') == [
        {'kind': 'plane', 'atoms': tuple(range(6, 12))}, {'kind': 'vector', 'atoms': (0, 3)}]
    assert window.structure_tool.edit_guides_text('стрелка 1 2') is None and errors and len(window.viewer.guides) == 2
    from azimuth import defaults
    from modules.compass.chemistry import guides as made

    assert 'Стиль векторов и плоскостей…' in [a.text() for a in menu.actions()]
    window.chem_actions['guide_style'].trigger()  # its window
    app.processEvents()
    assert window.structure_tool._guide_style_box.isVisible()
    window.structure_tool._guide_style_box.reject()
    kept = {k: defaults.get(k) for k in window.structure_tool.GUIDE_STYLE}
    try:
        window.viewer.guides = [{'kind': 'normal', 'atoms': tuple(range(6))}]
        assert window.structure_tool.guide_style({'guide_normal_color': '#ff00ff', 'guide_width': 6,
                                                  'guide_normal_length': 3.0, 'guide_numbers': False})['guide_width'] == 6
        shape = made.geometry(window.viewer.guides[0], window.molecule)
        assert abs(sum((shape['end'][k] - shape['start'][k]) ** 2 for k in range(3)) ** 0.5 - 3.0) < 1e-9
        image = window.viewer.render_image(1, False).toImage()
        magenta = lambda c: c.red() > 200 and c.blue() > 200 and c.green() < 60  # noqa: E731
        seen = sum(magenta(image.pixelColor(x, y)) for x in range(0, image.width(), 2) for y in range(0, image.height(), 2))
        assert seen > 20  # the normal drawn in the colour chosen
        window.structure_tool.guide_style({'guide_normal_show': False})
        image = window.viewer.render_image(1, False).toImage()
        assert not any(magenta(image.pixelColor(x, y)) for x in range(0, image.width(), 2) for y in range(0, image.height(), 2))
        assert window.structure_tool.guide_style({'guide_plane_color': 'red'})['guide_plane_color'] == ''  # not a colour
    finally:
        window.structure_tool.guide_style(kept)
        window.viewer.guides = [{'kind': 'plane', 'atoms': tuple(range(6, 12))}, {'kind': 'vector', 'atoms': (0, 3)}]
    # kept with the tab; another structure takes them away
    window.new_document()
    assert window.viewer.guides == []
    window.switch_document(window.current_document - 1)
    assert len(window.viewer.guides) == 2
    window.structure_tool.clear_guides()
    assert window.viewer.guides == []


def test_own_display_scheme(window, app, tmp_path, monkeypatch):
    # one window, every change on the model at once, kept as a scheme, a file
    from azimuth.core import read_xyz
    from modules.compass.view import schemes

    monkeypatch.setattr(window, 'confirm_replace', lambda *a, **k: True)
    errors = []
    monkeypatch.setattr(window, 'error', errors.append)
    window.load_molecule(read_xyz('3\nwater\nO 0 0 0\nH 0.96 0 0\nH -0.24 0.93 0'))
    keys = ('display_schemes', 'start_scheme', 'bond_width', 'bond_color', 'atom_scale', 'palette', 'element_colors',
            'background', 'grid', 'show_bonds', 'multiple_bonds', 'atom_labels')
    saved = {k: window.preferences.value(k) for k in keys}
    before, own = window.scheme_tool.current_scheme(), dict(window.user_schemes)
    try:
        assert window.scheme_editor_action.text() == 'Свой вид…'
        editor = window.scheme_tool.open_scheme_editor()
        assert editor.scheme() == before and [editor.element.itemData(k) for k in (0, 1)] == ['H', 'O']  # the model's first
        editor.mode.setCurrentIndex(editor.mode.findData('sticks'))
        editor.bond_width.setValue(1.3)  # any width, not only the three of the menu
        editor.atom_scale.setValue(0.85)
        editor.background.setCurrentIndex(editor.background.findData('white'))
        editor.set_color('O', '#ff00aa')
        assert window.viewer.display_mode == 'sticks' and window.viewer.bond_width == 1.3
        assert window.viewer.atom_scale == 0.85 and window.viewer.background == 'white'
        assert window.viewer.palette['O'] == '#ff00aa' and editor.colors_list.count() == 1
        editor.start_box.setChecked(True)
        assert editor.save('Для статьи') == 'Для статьи' and window.scheme_tool.start_scheme() == 'Для статьи'
        assert schemes.same(window.user_schemes['Для статьи'], editor.scheme())
        target = tmp_path / 'mine.json'
        assert editor.export(str(target)) == len(window.user_schemes)
        # read back: a taken name gets « (2)»
        assert 'Для статьи (2)' in editor.import_file(str(target))
        bad = tmp_path / 'bad.json'
        bad.write_text('{}', encoding='utf-8')
        assert editor.import_file(str(bad)) is None and errors
        editor.set_color('O', None)
        assert 'O' not in editor.colors and window.viewer.palette['O'] != '#ff00aa'
        assert schemes.same(editor.revert(), before) and schemes.same(window.scheme_tool.current_scheme(), before)
        editor.close()
    finally:
        window.user_schemes = own
        for k, v in saved.items():
            if v is None:
                window.preferences.remove(k)
            else:
                window.preferences.setValue(k, v)
        window.scheme_tool.apply_scheme(before)


def test_calculation_menu_of_compass(window, app, tmp_path, monkeypatch):
    # a quick xtb from the
    # model, the charge and multiplicity, the steps as data, the scanned coordinate on the model, the modes of atoms
    from pathlib import Path
    from types import SimpleNamespace

    from azimuth.core import read_xyz
    from modules.compass.chemistry.formats import read_xyz_frames
    from modules.sextant import runner
    from modules.spectrum.readers.orca_scan import Coordinate, Point, Scan
    from modules.spectrum.readers.results import OptimizationStep
    from modules.spectrum.wavefunction import field_tables

    monkeypatch.setattr(window, 'confirm_replace', lambda *a, **k: True)
    errors, started = [], []
    monkeypatch.setattr(window, 'error', errors.append)
    window.load_molecule(read_xyz('3\nwater\nO 0 0 0\nH 0.96 0 0\nH -0.24 0.93 0'))
    menus = window.calc_tool_menus
    assert [a.text() for a in menus['quick_xtb'].actions()] == [
        'Энергия (xtb)', 'Оптимизация (xtb)', 'Оптимизация + частоты (xtb)', 'Оптимизация GFN-FF (xtb)',
        'Скан по выделенным атомам (xtb)…']
    # the quick xtb: whatever program Sextant shows, an xtb job with the charge and multiplicity of the tab
    fake = tmp_path / 'xtb'
    fake = program_script(fake, '')
    monkeypatch.setattr(runner, 'find_program', lambda kind, configured=None, **k: fake if kind == 'xtb' else None)
    monkeypatch.setattr(runner.Job, 'start', lambda self: self)
    monkeypatch.setattr(window.run_tool, 'jobs_root', lambda: tmp_path / 'jobs')
    monkeypatch.setattr(window.run_tool, 'job_started', lambda job, calc, kind, edited, **k: started.append((job, calc, kind)) or job)
    assert window.calculation_tool.set_charge_and_multiplicity(0, 3) == (0, 3)
    job = window.calculation_tool.quick_xtb('Оптимизация')
    assert job is not None and started[-1][2] == 'xtb' and started[-1][1].multiplicity == 3
    assert '--opt' in job.spec.command and '--uhf' in job.spec.command
    assert job.spec.command[job.spec.command.index('--uhf') + 1] == '2'
    window.calculation_tool.set_charge_and_multiplicity(0, 1)
    gfnff = window.calculation_tool.quick_xtb('Оптимизация', 'gfnff')
    assert not errors, errors
    assert '--gfnff' in gfnff.spec.command and '--gfn' not in gfnff.spec.command and '--opt' in gfnff.spec.command
    # the pill over the model with the turning compass; no window; at the end a line of how it went
    from types import SimpleNamespace

    from PySide6.QtTest import QTest

    from azimuth.ui import Spinner

    window.navigate(0)
    running = SimpleNamespace(running=True, code=None)
    timer = window.calculation_tool.follow_quick(running, 'Оптимизация')
    busy = window.busy_pill()
    assert busy is not None and busy.text().startswith('xtb · Оптимизация') and 'Esc — остановить' in busy.text()
    assert busy.findChildren(Spinner) and not window.job_window.isVisible()
    window.notify('Сообщение во время расчёта', 5000)  # a message stands above the pill of the work
    assert window.notice.text() == 'Сообщение во время расчёта'
    assert window.notice.geometry().bottom() < busy.geometry().top()
    running.running, running.code = False, 0
    QTest.qWait(700)
    assert not timer.isActive() and window.notice.text() == 'Быстрый расчёт xtb закончен.'
    assert window.busy_pill() is None and not window.notice.property('busy')
    window.viewer.set_selection([0, 1])
    scan = window.calculation_tool.quick_scan_dialog((1.5, 6))
    control = (Path(scan.spec.folder) / 'xcontrol').read_text(encoding='utf-8')
    assert '$scan\n   1: 0.9600,1.5000,6\n' in control and started[-1][1].task == 'Скан ППЭ с релаксацией'
    window.viewer.set_selection([0])
    assert window.calculation_tool.quick_scan_dialog((1.5, 6)) is None  # one atom: no coordinate
    # the steps of a result: one XYZ, a table, a parameter along them
    steps = tuple(OptimizationStep(k + 1, -5.0 - 0.01 * k, read_xyz(f'3\n\nO 0 0 0\nH {r} 0 0\nH -0.24 0.93 0'))
                  for k, r in enumerate((0.96, 1.10, 1.30)))
    window.drawer.load(steps, 'scan.out')
    xyz = window.calculation_tool.save_steps_xyz(str(tmp_path / 'steps.xyz'))
    assert len(read_xyz_frames(Path(xyz).read_text(encoding='utf-8'))) == 3
    header, rows = field_tables.read_csv(window.calculation_tool.save_steps_table(str(tmp_path / 'steps.csv')))
    assert header[:3] == ['Шаг', 'Атом', 'Элемент'] and len(rows) == 9
    window.viewer.set_selection([0, 1])
    plot = window.calculation_tool.parameter_plot()
    assert [round(v, 6) for _, v, _ in plot.series] == [0.96, 1.1, 1.3]
    assert field_tables.read_csv(plot.save_csv(str(tmp_path / 'plot.csv')))[0][1] == 'r, Å'
    plot.close()
    # a scan being browsed: its coordinate measured on the model
    window.drawer.load(steps, 'scan.out', Scan('relaxed', (Coordinate('bond', (0, 1)),),
                                               tuple(Point(k + 1, (r,), s.energy, s.geometry)
                                                     for k, (r, s) in enumerate(zip((0.96, 1.1, 1.3), steps)))))
    window.trajectory_tool.enter_trajectory()
    window.trajectory_tool.show_trajectory_step(1)
    assert window.viewer.scan_pin == (0, 1)
    window.trajectory_tool.leave_trajectory()
    assert window.viewer.scan_pin is None
    # the modes of the selected atoms
    window.drawer.modes = (SimpleNamespace(index=7, frequency=3700.0, vectors=((0, 0, 0), (0.7, 0, 0), (0, 0, 0))),
                           SimpleNamespace(index=6, frequency=1600.0, vectors=((0.1, 0, 0), (0.3, 0.3, 0), (0.3, -0.3, 0))))
    window.viewer.set_selection([1])
    text = window.calculation_tool.modes_of_selected()
    assert text.index('Мода   7') < text.index('Мода   6') and '100.0 %' in text
    window.drawer.modes = ()
    window.viewer.set_selection([])


def test_uff_in_compass(window, app, monkeypatch):
    # «Правка → Геометрия → Оптимизировать (UFF)»
    # and «Выравнивать по UFF»
    from azimuth.core import read_xyz
    from modules.compass.chemistry import uff

    errors = []
    monkeypatch.setattr(window, 'error', errors.append)
    monkeypatch.setattr(window, 'confirm_replace', lambda *a, **k: True)
    window.load_molecule(read_xyz('9\nethanol\nC 1.1879 -0.3829 0\nC 0 0.5526 0\nO -1.1867 -0.2472 0\n'
                                  'H -1.9237 0.3668 0\nH 0.0471 1.195 0.8823\nH 0.0471 1.195 -0.8823\n'
                                  'H 2.1138 0.1906 0\nH 1.1554 -1.0177 0.8809\nH 1.1554 -1.0177 -0.8809'))
    assert window.uff_action.text() == 'Оптимизировать (UFF)' and window.tidy_uff_action.isCheckable()
    before = uff.energy(uff.build(window.coordinate_tool.table_molecule()),
                        [a.position for a in window.coordinate_tool.table_molecule().atoms])[0]
    result = window.optimize_uff()
    assert not errors and result is not None and result.energy < before
    after = window.coordinate_tool.table_molecule()
    assert uff.energy(uff.build(after), [a.position for a in after.atoms])[0] == pytest.approx(result.energy, abs=1e-6)
    window.undo_geometry()
    assert window.coordinate_tool.table_molecule().atoms[0].position == pytest.approx((1.1879, -0.3829, 0.0))
    # outside the beta (AGENTS.md §0): UFF is checked against RDKit for H, C, N, O, P, S, Cl only — the others are said
    said = []
    monkeypatch.setattr(window.model_menu_tool, 'edit_structure', lambda molecule, text: said.append(text))
    window.load_molecule(read_xyz('3\nzinc\nZn 0 0 0\nCl 2.1 0 0\nCl -2.1 0 0'))
    window.optimize_uff()
    assert said and 'Не проверено: UFF для Zn' in said[-1]


def test_map_of_a_two_dimensional_scan(window, app):
    # the water scan of the two O–H bonds (ORCA 6.0.1, 5 × 5) in the panel of steps — «Карта скана», a click on
    # a point of the map selects it there and the model shows it
    from pathlib import Path

    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest

    from modules.spectrum.readers.outputs import read_any

    text = (Path(__file__).parents[1] / 'data' / 'scan2d' / 'h2o_scan2d_orca.out').read_text(encoding='utf-8')
    window.trajectory_tool.load_trajectory(read_any(text), 'h2o_scan2d_orca.out')
    window.opening_tool.show_trajectory_drawer()
    app.processEvents()
    try:
        assert window.drawer.is_map() and window.drawer.map_button.isVisibleTo(window.drawer)
        assert window.drawer.table.columnCount() == 4  # the point, r(2–1), r(3–1), ΔE
        dialog = window.trajectory_tool.open_scan_map()
        dialog.view.resize(520, 420)
        dialog.view.grab()
        target = dialog.view.to_screen(1.15, 0.95)
        QTest.mouseClick(dialog.view, Qt.MouseButton.LeftButton, pos=QPoint(round(target.x()), round(target.y())))
        point = window.drawer.scan.points[window.drawer.current]
        assert point.values == (1.15, 0.95) and dialog.view.current == window.drawer.current
        window.drawer.select(0)
        assert dialog.view.current == 0
        dialog.close()
    finally:
        window.trajectory_tool.leave_trajectory()
        window.trajectory_tool.set_trajectory_open(False)



def test_protein_ribbon(window, app, monkeypatch):
    # ubiquitin of the PDB as a ribbon; the atoms of the chain hidden,
    # the water of the file stays; off again — the atoms back, no ribbon
    from pathlib import Path

    from modules.compass.chemistry.formats import read_pdb

    errors = []
    monkeypatch.setattr(window, 'error', errors.append)
    monkeypatch.setattr(window, 'confirm_replace', lambda *a, **k: True)
    text = (Path(__file__).parents[1] / 'data' / 'protein' / '1ubq.pdb').read_text(encoding='utf-8')
    window.load_molecule(read_pdb(text))
    window.ribbon_action.setChecked(True)
    try:
        assert not errors and window.viewer.surface['kind'] == 'ribbon'
        hidden = window.viewer.hidden_atoms()
        waters = sum(1 for line in text.splitlines() if line.startswith('HETATM') and ' HOH ' in line)
        assert len(hidden) == len(window.molecule.atoms) - waters  # every atom of the chain, no water
        window.viewer.resize(500, 400)
        window.viewer.grab()
    finally:
        window.ribbon_action.setChecked(False)
    assert window.viewer.surface is None and not window.viewer.hidden_atoms()
    window.load_molecule(read_pdb('ATOM      1  O   HOH A   1       0.000   0.000   0.000  1.00  0.00           O\n'
                                  'ATOM      2  O   HOH A   2       3.000   0.000   0.000  1.00  0.00           O\nEND\n'))
    window.ribbon_action.setChecked(True)
    assert errors and not window.ribbon_action.isChecked()  # no chain: said, the switch off


def test_peptide_builder(window, app, monkeypatch):
    # «Правка → Геометрия → Построить пептид…» — a helix of the sequence; its ribbon is a helix
    errors = []
    monkeypatch.setattr(window, 'error', errors.append)
    monkeypatch.setattr(window, 'confirm_replace', lambda *a, **k: True)
    molecule = window.protein_tool.peptide_dialog(('AEAAAKEAAAKA', 'helix'))
    assert not errors and molecule is not None
    shown = window.coordinate_tool.table_molecule().atoms  # the table keeps 8 decimals of Å
    assert [a.symbol for a in shown] == [a.symbol for a in molecule.atoms]
    assert all(abs(p - q) < 1e-6 for a, b in zip(shown, molecule.atoms) for p, q in zip(a.position, b.position))
    counts = window.protein_tool.show_ribbon(True)
    assert counts['H'] >= 8 and window.viewer.surface['kind'] == 'ribbon'
    window.ribbon_action.setChecked(False)
    window.protein_tool.show_ribbon(False)
    assert window.protein_tool.peptide_dialog(('AXA', 'helix')) is None and errors  # an unknown letter: said


def test_coordination_builder(window, app, monkeypatch):
    # «Правка → Геометрия → Координационный центр…» — [Co(NH3)5Cl]2+ shown, charge and multiplicity set
    errors, notes = [], []
    monkeypatch.setattr(window, 'error', errors.append)
    monkeypatch.setattr(window, 'notify', lambda text, ms=0: notes.append(text))
    monkeypatch.setattr(window, 'confirm_replace', lambda *a, **k: True)
    built = window.coordination_tool.dialog(('Co', 'octahedral', '5 NH3, Cl', 3))
    assert not errors and built is not None and built.charge == 2
    shown = window.coordinate_tool.table_molecule()
    assert [a.symbol for a in shown.atoms] == [a.symbol for a in built.molecule.atoms]
    assert (window.charge.value(), window.spin.value()) == (2, 1)  # Co(III), d6: 92 electrons
    assert window.coordination_action.text() and notes and '[Co(NH3)5Cl]' in notes[-1]
    window.coordination_tool.dialog(('Cu', 'square', 'Cl', 2))  # Cu(II): an odd number of electrons
    assert (window.charge.value(), window.spin.value()) == (-2, 2)
    assert window.coordination_tool.dialog(('Fe', 'octahedral', 'Xy', 2)) is None and errors  # an unknown ligand: said


def test_the_model_stays_when_the_drawer_closes_and_opens_at_once(window, app):
    # the drawer closed and opened again at once — the model ends where it was with the drawer open
    show_model(window, app)
    viewer = window.viewer
    viewer.set_inset(0, animate=False)
    start = viewer.pan.x()
    viewer.set_inset(200)  # opens: half of it to the right, smoothly
    viewer.set_inset(0)  # closed at once
    viewer.set_inset(200)  # and opened again
    motion = viewer._inset_motion
    if motion is not None:
        motion.setCurrentTime(motion.duration())
    app.processEvents()
    assert viewer.pan.x() == pytest.approx(start + 100, abs=0.5)
    viewer.set_inset(0, animate=False)


def test_the_axes_are_carried_when_allowed_and_put_back(window):
    from PySide6.QtCore import QPoint, QPointF, Qt
    from PySide6.QtTest import QTest

    viewer = window.viewer
    viewer.resize(600, 400)
    kept = window.preferences.value('axes_offset', ''), window.preferences.value('axes_movable', 'false')
    try:
        window.reset_axes_place()
        window.allow_axes_moving(False)
        window.axes_button.setChecked(True)
        window.toggle_axes()
        start = viewer.axes_origin()
        assert start == QPointF(600 - 52, 52) and not viewer.near_axes(start)  # not movable: the model is turned
        window.allow_axes_moving(True)
        assert viewer.near_axes(start)
        QTest.mousePress(viewer, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start.toPoint())
        QTest.mouseMove(viewer, QPoint(300, 200))
        QTest.mouseRelease(viewer, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(300, 200))
        assert abs(viewer.axes_origin().x() - 300) <= 1 and abs(viewer.axes_origin().y() - 200) <= 1
        assert window.preferences.value('axes_offset', '')  # kept
        moved = viewer.axes_offset
        viewer.axes_offset = None
        window.restore_axes_place()  # the next start
        assert viewer.axes_offset == moved and viewer.axes_movable
        window.reset_axes_place()
        assert viewer.axes_origin() == start and not window.preferences.value('axes_offset', '')
        # and moving them is off again (the owner, 2026-11-24): the axes no longer follow the mouse
        assert not viewer.axes_movable and not viewer.near_axes(start)
    finally:
        window.preferences.setValue('axes_offset', kept[0])
        window.preferences.setValue('axes_movable', kept[1])
        window.restore_axes_place()


def test_a_copy_by_a_button_is_said(window, monkeypatch):
    from PySide6.QtWidgets import QApplication, QPushButton

    from azimuth.core import read_xyz
    from azimuth.ui import copied

    said = []
    monkeypatch.setattr(window, 'notify', lambda text, ms=8000: said.append(text))
    window.load_molecule(read_xyz('3\nwater\nO 0 0 0.117\nH 0.757 0 -0.469\nH -0.757 0 -0.469\n'), record=False)
    window.coordinate_tool.copy_coordinates()
    assert said and said[-1].startswith('Скопировано: координаты')
    assert QApplication.clipboard().text().strip()
    button = QPushButton('Копировать', window)
    assert copied(button, 'таблица', button) == 'Скопировано: таблица.' and button.text() == '✓ Скопировано'
    assert said[-1] == 'Скопировано: таблица.'


def test_the_colour_picker_is_even_and_ok_is_blue(window):
    from PySide6.QtGui import QColor
    from PySide6.QtWidgets import QColorDialog, QDialog, QDialogButtonBox, QLineEdit, QPushButton, QVBoxLayout

    from azimuth.polish import blue_ok
    from modules.compass.actions.style_form import tidy_colour_dialog

    dialog = QColorDialog(QColor('#788897'), window)
    dialog.setOption(QColorDialog.ColorDialogOption.DontUseNativeDialog, True)
    tidy_colour_dialog(dialog)
    html = next(f for f in dialog.findChildren(QLineEdit) if f.maximumWidth() == f.minimumWidth())
    assert html.isHidden()  # «убери HTML»
    from modules.compass.actions.style_form import basic_colours

    assert QColorDialog.standardColor(0).rgb() == basic_colours()[0].rgb() and QColorDialog.standardColor(47).rgb() == basic_colours()[47].rgb()  # an HSL colour is kept as RGB
    assert basic_colours()[0].lightness() > basic_colours()[5].lightness()  # light at the top of a column
    # the field of hues takes the width of the right column
    from PySide6.QtWidgets import QSizePolicy, QWidget

    picker = next(w for w in dialog.findChildren(QWidget) if w.metaObject().className().endswith('QColorPicker'))
    assert picker.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Expanding
    # as in Chemcraft: the swatches first; «Выбрать вручную» opens the field of hues and the numbers beside them
    shower = next(w for w in dialog.findChildren(QWidget) if w.metaObject().className().endswith('QColorShower'))
    assert dialog.manual_part.isAncestorOf(shower) and dialog.manual_part.isAncestorOf(picker)
    from PySide6.QtWidgets import QGroupBox

    assert sorted(g.title() for g in dialog.findChildren(QGroupBox)) == sorted(['Основные цвета', 'Пользовательские цвета',
                                                                               'Свой цвет'])  # findChildren: the order
                                                                               # made # blocks in frames
    # the buttons are in the window (0.216.7x: in the column of the swatches, not a row of their own under everything)
    box = dialog.findChild(QDialogButtonBox)
    assert dialog.manual_part.isHidden() and box is not None and box.isVisibleTo(dialog)
    from PySide6.QtTest import QTest

    ok = dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Ok)
    dialog.show()
    QTest.qWait(30)
    ok_before = ok.mapTo(dialog, ok.rect().topLeft())
    size = dialog.size()
    dialog.manual_button.click()
    QTest.qWait(30)
    assert not dialog.manual_part.isHidden() and dialog.width() > size.width()
    assert abs(dialog.height() - size.height()) <= 2  # the height stays
    assert ok.mapTo(dialog, ok.rect().topLeft()) == ok_before  # OK and «Отмена» stay where they were
    dialog.manual_button.click()
    QTest.qWait(30)
    assert dialog.manual_part.isHidden() and dialog.size() == size  # the size of before
    dialog.hide()
    blue_ok(dialog)
    ok = dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Ok)
    assert ok.objectName() == 'primary'
    own = QDialog(window)
    layout = QVBoxLayout(own)
    plain, mine = QPushButton('Отмена'), QPushButton('OK')
    layout.addWidget(plain)
    layout.addWidget(mine)
    assert blue_ok(own) == [mine] and plain.objectName() != 'primary'
    dialog.deleteLater()
    own.deleteLater()


def test_the_own_colours_are_one_set_kept_between_starts(window):
    from PySide6.QtGui import QColor
    from PySide6.QtWidgets import QColorDialog

    from azimuth.settings import open_settings
    from modules.compass.actions.style_form import CUSTOM_KEY, keep_custom_colours, load_custom_colours

    kept = open_settings().value(CUSTOM_KEY, '')
    before = QColorDialog.customColor(0)
    try:
        QColorDialog.setCustomColor(0, QColor('#123456'))
        keep_custom_colours()
        QColorDialog.setCustomColor(0, QColor('#ffffff'))
        load_custom_colours()  # the next start
        assert QColorDialog.customColor(0).name() == '#123456'
    finally:
        QColorDialog.setCustomColor(0, before)
        open_settings().setValue(CUSTOM_KEY, kept)


def test_a_copy_on_the_page_of_coordinates_is_seen(window):
    # the pill of the
    # model lies on the field, hidden behind «Координаты» — the message goes to the pill of the page there
    from PySide6.QtTest import QTest

    from azimuth.core import read_xyz

    window.show()
    window.load_molecule(read_xyz('3\nwater\nO 0 0 0.117\nH 0.757 0 -0.469\nH -0.757 0 -0.469\n'), record=False)
    window.structure_tabs.setCurrentIndex(1)
    QTest.qWait(30)
    window.coordinate_tool.copy_coordinates()
    toast = getattr(window, '_page_toast', None)
    seen = toast is not None and toast.isVisible() and toast.text().startswith('Скопировано: координаты')
    window.structure_tabs.setCurrentIndex(0)
    assert seen


def test_check_solvent_and_protons_from_the_menus(window):
    # «Проверить структуру…», «Окружить растворителем…», «Протоны»
    from modules.compass.chemistry import library

    tool = window.structure_tool
    window.load_molecule(library.molecule('Метанол · CH₄O'), record=False)
    window.charge.setValue(0)
    window.spin.setValue(1)
    assert tool.check_structure() == []  # a good methanol: «замечаний нет»
    oxygen = next(k for k, a in enumerate(window.molecule.atoms) if a.symbol == 'O')
    count = len(window.molecule.atoms)
    window.viewer.set_selection([oxygen])
    assert tool.add_proton() and len(window.molecule.atoms) == count + 1 and window.charge.value() == 1
    window.viewer.set_selection([oxygen])
    assert tool.remove_proton() and len(window.molecule.atoms) == count and window.charge.value() == 0
    window.spin.setValue(2)  # 18 electrons — a doublet is wrong
    problems = tool.check_structure()
    assert problems and problems[0].level == 'error'
    window._report_box.reject()
    window.spin.setValue(1)
    assert tool.solvate_dialog('Вода · H₂O', 3, 'around') == 3 and len(window.molecule.atoms) == count + 9
    assert tool.remove_solvent() == 3 and len(window.molecule.atoms) == count
    # «Первая координационная сфера»: as many as it has places — methanol: the two lone pairs of its O and its O–H
    assert tool.solvate_dialog('Вода · H₂O', mode='shell') == 3 and len(window.molecule.atoms) == count + 9


def test_isotopes_of_the_selected_atoms_go_to_the_input(window):
    # 2026-11-19 («изотопы»): D on the two H of water — ORCA writes «M = 2.014102» after them
    from azimuth.core import read_xyz

    window.load_molecule(read_xyz('3\nwater\nO 0 0 0.117\nH 0.757 0 -0.469\nH -0.757 0 -0.469\n'), record=False)
    window.viewer.set_selection([1, 2])
    try:
        assert window.structure_tool.isotope_dialog(2.014102) == {1: 2.014102, 2: 2.014102}
        assert window.calculation().isotopes == '2 H 2.014102; 3 H 2.014102'
        window.viewer.label_mode = 'element'
        assert window.viewer.atom_label(1) == 'D' and window.viewer.atom_label(0) == 'O'  # D on the model
        window.viewer.set_selection([1])
        assert window.structure_tool.isotope_dialog(0.0) == {2: 2.014102}  # the usual H back on one of them
        assert window.viewer.atom_label(1) == 'H'
        # the menu of an atom: «Изотоп» with its isotopes; a choice sets it at once
        menu = window.model_menu_tool.atom_menu(1)
        sub = next(a.menu() for a in menu.actions() if a.menu() is not None and a.text().startswith('Изотоп'))
        next(a for a in sub.actions() if a.text().startswith('T')).trigger()
        assert window.viewer.atom_label(1) == 'T' and '2 H 3.016049' in window.calculation().isotopes
        menu.close()
    finally:
        window._isotopes = ''


def test_the_periodic_table_offers_the_isotopes_of_an_element(window):
    # the right button of an element — its isotopes; the
    # next atoms of it put on the model get the one chosen
    from PySide6.QtCore import QPoint

    from azimuth.core import read_xyz
    from modules.compass.panels.periodic import PeriodicTable

    table = PeriodicTable('C', window)
    got = []
    table.isotope.connect(lambda symbol, mass: got.append((symbol, mass)))
    menu = table.isotope_menu('Pt', table.buttons['Pt'], QPoint(2, 2))
    names = [a.text() for a in menu.actions()]
    assert any(n.startswith('¹⁹⁵Pt') and '%' in n for n in names) and any(n.startswith('Своя масса') for n in names)
    next(a for a in menu.actions() if a.text().startswith('¹⁹⁵Pt')).trigger()
    assert [s for s, _ in got] == ['Pt'] and abs(got[0][1] - 194.964792) < 1e-6  # the table of 194.9647917
    menu.close()
    table.deleteLater()
    window.load_molecule(read_xyz('3\nwater\nO 0 0 0.117\nH 0.757 0 -0.469\nH -0.757 0 -0.469\n'), record=False)
    try:
        window.choose_isotope('H', 2.014102)
        assert window.isotope_on_new([1, 0]) == [1]  # the H only, not the O
        window.viewer.label_mode = 'element'
        assert window.viewer.atom_label(1) == 'D'
        window.choose_element('C')  # an element chosen plainly — the usual mass again for the next atoms
        assert window.isotope_on_new([2]) == []
    finally:
        window._isotopes = ''
        window._pending_isotope = None


def test_the_periodic_table_of_help_shows_an_atom(window):
    from azimuth.element_window import ElementsDialog

    dialog = ElementsDialog(window)
    try:
        assert dialog.card.isHidden()  # the table alone until an element is chosen
        dialog.click('Fe')
        assert not dialog.card.isHidden() and dialog.buttons['Fe'].isChecked()
        assert '#f5e9b8' in dialog.buttons['Fe'].styleSheet()  # coloured as a transition metal
        assert dialog.atom.z == 26 and dialog.atom.a == 56  # the most abundant isotope first
        assert dialog.fact('Электронная конфигурация') == '[Ar] 3d⁶ 4s²'
        assert dialog.fact('Электроны по оболочкам') == 'K2 L8 M14 N2'
        assert dialog.isotopes.rowCount() == 4
        dialog.isotopes.setCurrentCell(0, 0)  # ⁵⁴Fe
        assert dialog.atom.a == 54 and dialog.fact('Нейтронов') == '28'
        assert dialog.show_element('Tc') == 43 and dialog.atom.a == 98  # no natural Tc: its most stable isotope
        assert dialog.isotopes.item(0, 2).text() == 'нет в природе'
        dialog.atom.grab()  # drawn without an error
        dialog.click('Tc')  # the second click on the same element hides its card
        assert dialog.card.isHidden() and not dialog.buttons['Tc'].isChecked()
    finally:
        dialog.deleteLater()
