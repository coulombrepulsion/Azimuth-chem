"""Window tests — The look of the window: settings, themes, icons, menus, Quill, the engine of the model (split from
test_gui.py on 2026-11-08)."""

from tests.gui_support import *  # noqa: F401,F403 — the fixtures app, window and the helpers
from tests.fake_programs import program_script


def test_no_log_in_current_directory(window, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    another = Studio()
    assert list(tmp_path.iterdir()) == []
    another.dirty = False
    another.close()


def test_atomic_unicode_save(tmp_path):
    path = tmp_path / 'молекула с пробелами.xyz'
    atomic_write(path, 'тест\n')
    assert path.read_text(encoding='utf-8') == 'тест\n'  # not the locale of Windows (cp1251)
    assert list(tmp_path.iterdir()) == [path]


def test_combo_boxes_of_windows_opened_later_get_the_theme(window, app):
    # the look of the theme reaches the combo boxes of a window opened after the start without a filter
    # of the whole application (with one, the tests of the hub crashed — test_hub.py)
    from PySide6.QtGui import QPalette
    from PySide6.QtWidgets import QComboBox, QDialog, QVBoxLayout

    window.theme.setCurrentIndex(1)
    app.processEvents()
    dialog = QDialog(window)
    combo = QComboBox()
    combo.addItems(['один', 'два'])
    QVBoxLayout(dialog).addWidget(combo)
    try:
        dialog.show()
        app.processEvents()
        assert combo.property('quail_theme') is True and combo.property('quail_list')
        assert combo.view().palette().color(QPalette.ColorRole.Base).lightness() < 80
        page = QComboBox(window.stack.currentWidget())  # one made later inside the window: the section gives it the look
        window.navigate(window.stack.currentIndex())
        assert page.property('quail_theme') is True
        page.deleteLater()
    finally:
        dialog.close()
        dialog.deleteLater()
        window.theme.setCurrentIndex(0)


def test_theme_changes_preserve_structure_and_persist(window, app):
    original = window.molecule
    window.theme.setCurrentIndex(1)
    assert window.viewer.dark and window.preferences.value('theme') == 'dark'
    another = Studio()
    assert another.theme.currentIndex() == 1
    another.dirty = False
    another.close()
    window.theme.setCurrentIndex(0)
    assert not window.viewer.dark and window.molecule == original
    assert window.preferences.value('theme') == 'light'


@pytest.mark.parametrize('theme_index', [0, 1, 0])
def test_popup_contrast_under_dark_system_palette(window, app, theme_index):
    from PySide6.QtGui import QPalette, QColor
    from PySide6.QtWidgets import QComboBox

    original = app.palette()
    dark = QPalette(original)
    for role in (QPalette.ColorRole.Window, QPalette.ColorRole.Base, QPalette.ColorRole.Button):
        dark.setColor(role, QColor('#080808'))
    app.setPalette(dark)
    try:
        window.theme.setCurrentIndex(theme_index)
        window.apply_theme()
        window.show()
        app.processEvents()
        for combo in window.findChildren(QComboBox):
            view = combo.view()
            view.ensurePolished()
            palette = view.palette()
            which = (combo.objectName(), type(combo).__name__, type(combo.parentWidget()).__name__,  # who
                     combo.currentText(), palette.color(QPalette.ColorRole.Base).name())
            assert (
                palette.color(QPalette.ColorRole.Base).lightness() > 200
                if theme_index == 0
                else palette.color(QPalette.ColorRole.Base).lightness() < 80
            ), which
            assert (
                palette.color(QPalette.ColorRole.Text).lightness() < 100
                if theme_index == 0
                else palette.color(QPalette.ColorRole.Text).lightness() > 200
            ), which

            # Readability is the contract: soft selection may use dark text.
            # Compute contrast independently of the application's theme constants.
            def luminance(color):
                channels = [color.redF(), color.greenF(), color.blueF()]
                linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
                return sum(c * weight for c, weight in zip(linear, (0.2126, 0.7152, 0.0722)))

            for text_role, background_role in (
                (QPalette.ColorRole.Text, QPalette.ColorRole.Base),
                (QPalette.ColorRole.HighlightedText, QPalette.ColorRole.Highlight),
            ):
                foreground = luminance(palette.color(text_role))
                background = luminance(palette.color(background_role))
                contrast = (max(foreground, background) + 0.05) / (min(foreground, background) + 0.05)
                assert contrast >= 4.5, (combo.objectName(), text_role, theme_index, contrast)
    finally:
        app.setPalette(original)
        window.theme.setCurrentIndex(0)


def test_popup_uses_list_delegate_and_coordinate_editor_theme(window, app):
    from PySide6.QtWidgets import QListView, QStyledItemDelegate, QLineEdit
    from PySide6.QtGui import QPalette

    window.theme.setCurrentIndex(0)
    window.show()
    window.structure_tabs.setCurrentIndex(1)
    app.processEvents()
    assert isinstance(window.build_mode.view(), QListView)
    assert isinstance(window.build_mode.view().itemDelegate(), QStyledItemDelegate)
    window.table.editItem(window.table.item(0, 1))
    app.processEvents()
    editor = window.table.findChild(QLineEdit)
    assert editor is not None
    for widget in [editor, window.table.viewport(), window.table.horizontalHeader()]:
        assert widget.palette().color(QPalette.ColorRole.Base).lightness() > 200
        assert widget.palette().color(QPalette.ColorRole.Text).lightness() < 100


def test_periodic_table_button_toggles_and_molecule_menu(window, app):
    show_model(window, app)
    window.edit_toggle.click()
    window.element_button.click()
    app.processEvents()
    assert window.periodic_dialog.isVisible() and window.element_button.isChecked()
    window.element_button.click()
    app.processEvents()
    assert not window.periodic_dialog.isVisible() and window.viewer.mode == 'atom'
    from azimuth.core import EXAMPLES

    menu = window.model_menu_tool.molecule_menu()
    from modules.compass.chemistry import library

    actions = menu.actions()  # the teaching examples, a separator, one submenu per library group
    assert [a.text() for a in actions[: len(EXAMPLES)]] == list(EXAMPLES) and actions[len(EXAMPLES)].isSeparator()
    # after the groups — «Мои молекулы» (when there are any) and, under a separator, their tools
    from modules.compass.chemistry import user_molecules

    groups = [a.menu() for a in actions[len(EXAMPLES) + 1 :] if a.menu() is not None]
    groups = [g for g in groups if g.title() != user_molecules.GROUP]
    assert [g.title() for g in groups] == list(library.MOLECULE_GROUPS)
    assert sum(len(g.actions()) for g in groups) == sum(len(k) for k in library.MOLECULE_GROUPS.values())
    benzene = next(a for g in groups for a in g.actions() if a.text() == 'Бензол · C₆H₆')
    benzene.trigger()
    assert window.molecule_choice == 'Бензол · C₆H₆'
    window.model_menu_tool.choose_molecule(next(iter(EXAMPLES)))
    window.load_molecule(read_xyz(EXAMPLES['Вода · H₂O']))
    before = len(window.molecule.atoms)
    menu.actions()[1].trigger()  # Аммиак · NH₃: chosen, added by a click in the field
    assert (
        window.viewer.mode == 'molecule' and window.molecule_button.isChecked() and len(window.molecule.atoms) == before
    )
    window.place_on_model((9, 0, 0), None)
    assert len(window.molecule.atoms) == before + 4 and window.molecule.title == ''
    window.iupac_button.click()  # the name only on demand
    assert window.molecule_info.text().startswith('вода + аммиак  /  ')
    errors = []
    window.error = lambda e: errors.append(str(e))
    window.place_on_model((0, 0, 0), 0)
    assert errors and len(window.molecule.atoms) == before + 4  # not on an atom


def test_hidden_mode_lists_never_become_windows(window, app):
    show_model(window, app)
    window.move_button.click()
    window.edit_toggle.click()
    app.processEvents()
    for combo in (window.move_kind, window.fragment, window.build_mode, window.element):
        assert not combo.isWindow() and not combo.isVisible()


def test_compact_measurements_and_menu_actions(window, app):
    show_model(window, app)
    assert all(f.width() <= 95 for f in window.measure_fields)
    assert not window.undo_button.isVisible() and not window.bond_button.isVisible()
    assert 'Ctrl' in window.connect_action.toolTip()
    assert window.viewer.width() > 600 and window.viewer.height() > 300


def test_move_icon_button_drags_and_toggles(window, app):
    show_model(window, app)
    window.move_button.click()
    assert window.move_button.isChecked() and window.viewer.mode == 'move'
    before = window.molecule.atoms[1].position
    point = window.viewer.projected()[1][0].toPoint()
    QTest.mousePress(window.viewer, Qt.MouseButton.LeftButton, pos=point)
    QTest.mouseMove(window.viewer, point + QPoint(25, 12), 10)
    QTest.mouseRelease(window.viewer, Qt.MouseButton.LeftButton, pos=point + QPoint(25, 12))
    assert window.molecule.atoms[1].position != before
    window.undo_geometry()
    assert window.molecule.atoms[1].position == pytest.approx(before)
    window.move_button.click()
    assert window.viewer.mode == 'view' and not window.move_button.isChecked()


def test_toolbar_icons_transparent_and_named(window, app):
    from PySide6.QtWidgets import QPushButton
    from PySide6.QtCore import QSize
    from PySide6.QtGui import QIcon

    from azimuth.controls import ExpandingButton

    buttons = [b for b in window.findChildren(QPushButton) if b.property('quail_icon')]
    assert len(buttons) >= 15
    for dark in [1, 0]:
        window.theme.setCurrentIndex(dark)
        for b in buttons:
            # an unfolding icon keeps its text (drawn when unfolded); the plain icons have none
            assert b.toolTip() and b.accessibleName() and (bool(b.text()) if isinstance(b, ExpandingButton) else not b.text())
            rendered = b.icon().pixmap(QSize(32, 32), QIcon.Mode.Normal, QIcon.State.Off).toImage()
            assert not rendered.isNull() and rendered.pixelColor(0, 0).alpha() == 0
            assert any(rendered.pixelColor(x, y).alpha() > 0 for x in range(32) for y in range(32))


def test_header_theme_toggle_with_sidebar_hidden(window, app):
    show_model(window, app)
    window.theme.setCurrentIndex(0)
    assert not window.sidebar.isVisible()
    window.theme_toggle.click()
    assert window.viewer.dark
    window.theme_toggle.click()
    assert not window.viewer.dark


def test_view_menu_controls_display_and_bond_color(window, app):
    show_model(window, app)
    original = window.molecule
    assert window.display_mode.isHidden()
    window.display_actions['sticks'].trigger()
    assert window.viewer.display_mode == 'sticks'
    assert window.display_actions['sticks'].isChecked()
    window.bond_color_actions['uniform'].trigger()
    assert window.viewer.bond_color == 'uniform'
    assert window.molecule == original and not window.undo_history
    window.bond_color_actions['smooth'].trigger()
    window.display_actions['ball-stick'].trigger()


def test_theme_icons_and_hover_help(window, app):
    show_model(window, app)
    window.theme.setCurrentIndex(0)
    assert not window.theme_toggle.text() and window.theme_toggle.property('quail_icon') == 'moon'
    window.theme_toggle.click()
    assert window.theme_toggle.property('quail_icon') == 'sun'
    # no tooltip over the field in the view mode
    assert window.viewer.mode != 'view' or not window.viewer.toolTip()
    assert not window.selection_info.text()
    window.theme_toggle.click()


def test_symmetry_in_the_summary_and_menu(window, app):
    show_model(window, app)
    window.confirm_replace = lambda: True
    w = read_xyz(EXAMPLES['Вода · H₂O'])
    bent = Molecule(w.title, (w.atoms[0], Atom('H', 0.7586, 0.01, 0.5043), Atom('H', -0.75, 0, 0.51)))
    window.load_molecule(bent)
    window.symmetry_tool.update_symmetry()
    assert 'C<sub>' not in window.molecule_info.text()  # the group only on demand
    window.symmetry_button.click()
    assert window.molecule_info.text().endswith('  /  C<sub>2v</sub>')
    menu = window.symmetry_tool.symmetry_menu()
    texts = [a.text() for a in menu.actions()]
    assert texts[0].startswith('Точечная группа: C2v') and window.symmetrize_action.isEnabled()
    window.symmetry_tool.apply_symmetry(False)
    from math import dist

    a = window.molecule.atoms
    assert abs(dist(a[0].position, a[1].position) - dist(a[0].position, a[2].position)) < 1e-7
    window.symmetry_tool.apply_symmetry(True)
    a = window.molecule.atoms
    assert abs(a[0].x) < 1e-7 and abs(a[0].y) < 1e-7
    window.undo_geometry()
    window.undo_geometry()
    assert window.molecule.atoms == bent.atoms


def test_library_molecule_fragment_and_examples_menu(window, app):
    # a library molecule keeps its bond orders; a library group replaces a hydrogen
    from modules.compass.chemistry import library

    show_model(window, app)
    window.new_molecule()
    window.edit_toggle.click()
    window.model_menu_tool.choose_molecule('Бензол · C₆H₆')
    window.place_on_model((0, 0, 0), None)
    assert window.molecule.formula == 'C6H6' and sorted(o for _, _, o in window.molecule.bonds).count(2) == 3
    window.load_molecule(read_xyz(EXAMPLES['Метан · CH₄']))
    window.model_menu_tool.choose_fragment('Карбоксил · —COOH')
    window.place_on_model((0, 0, 0), 1)
    window.iupac_button.click()  # the name on demand
    assert window.molecule.formula == 'C2H4O2' and window.molecule_info.text().startswith('этановая')
    groups = [a.menu() for a in window.model_menu_tool.fragment_menu().actions() if a.menu()]
    # the groups first; then «Удалить мой фрагмент» when the user has fragments
    assert [g.title() for g in groups][: len(library.FRAGMENT_GROUPS)] == list(library.FRAGMENT_GROUPS)
    window.dirty = False
    window.opening_tool.load_example_menu('Пиридин · C₅H₅N')  # «Файл → Примеры молекул» reaches the library too
    assert window.molecule.formula == 'C5H5N'


def test_clicks_on_hydrogen_replace_it_and_atom_menu(window, app):
    show_model(window, app)
    window.load_molecule(read_xyz(EXAMPLES['Метан · CH₄']))
    window.edit_toggle.click()
    window.model_menu_tool.choose_fragment('Гидроксил · —OH')
    window.place_on_model((0, 0, 0), 1)  # a group on H1 replaces it
    window.iupac_button.click()  # the name on demand
    assert window.molecule.formula == 'CH4O' and window.molecule_info.text().startswith('метанол')
    window.build_mode.setCurrentIndex(1)
    window.element.setCurrentText('Cl')
    h = next(
        i
        for i, a in enumerate(window.molecule.atoms)
        if a.symbol == 'H'
        and window.model_menu_tool.is_terminal(window.molecule, i)
        and any(0 in (p, q) and i in (p, q) for p, q, _ in window.molecule.bonds)
    )
    window.place_on_model((0, 0, 0), h)
    assert window.molecule.formula == 'CH3ClO'
    menu = window.model_menu_tool.atom_menu(0)
    titles = [a.text() for a in menu.actions()]
    assert 'Сменить элемент' in titles and 'Заменить фрагментом' not in titles  # carbon is not terminal
    assert 'Заменить фрагментом' in [a.text() for a in window.model_menu_tool.atom_menu(h).actions()]
    window.model_menu_tool.replace_element(h, 'Br')
    assert window.molecule.atoms[h].symbol == 'Br'
    window.undo_geometry()
    assert window.molecule.atoms[h].symbol == 'Cl'
    # one molecule on the
    # model — the item is there too (the model is left empty, undone); a water put beside it — «Удалить
    # молекулу» of its oxygen takes the water away, undone
    whole = len(window.molecule.atoms)
    alone = next(a for a in window.model_menu_tool.atom_menu(0).actions() if a.text().startswith('Удалить молекулу'))
    assert alone.text() == f'Удалить молекулу ({whole} атомов)'
    alone.trigger()
    assert not window.molecule.atoms
    window.undo_geometry()
    assert len(window.molecule.atoms) == whole and window.molecule.formula == 'CH3ClO'
    from modules.compass.chemistry.builder import place_molecule

    window.load_molecule(place_molecule(window.molecule, read_xyz(EXAMPLES['Вода · H₂O']), (6.0, 0.0, 0.0)),
                         preserve_view=True)
    oxygen = next(i for i in range(whole, len(window.molecule.atoms)) if window.molecule.atoms[i].symbol == 'O')
    item = next(a for a in window.model_menu_tool.atom_menu(oxygen).actions() if a.text().startswith('Удалить молекулу'))
    assert item.text() == 'Удалить молекулу (3 атомов)'
    item.trigger()
    assert len(window.molecule.atoms) == whole and window.molecule.formula == 'CH3ClO'
    window.undo_geometry()
    assert len(window.molecule.atoms) == whole + 3


def test_choice_stands_next_to_its_button(window, app, monkeypatch):
    show_model(window, app)
    window.edit_toggle.click()
    row = window.edit_row
    assert (
        window.element_button.isChecked() and row.indexOf(window.element_tile) == row.indexOf(window.element_button) + 1
    )
    window.model_menu_tool.choose_fragment('Метил · —CH₃')
    assert (
        window.fragment_button.isChecked()
        and row.indexOf(window.choice_label) == row.indexOf(window.fragment_button) + 1
    )
    window.model_menu_tool.choose_molecule('Аммиак · NH₃')
    assert (
        window.molecule_button.isChecked()
        and row.indexOf(window.choice_label) == row.indexOf(window.molecule_button) + 1
    )
    assert window.choice_label.text() == 'Аммиак · NH₃' and not window.element_tile.isVisible()
    # a click on the name opens the menu of the molecules again (of the fragments in the mode of fragments) — another one
    # is chosen there (the owner, 2026-11-24)
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest

    opened = []
    monkeypatch.setattr(window.model_menu_tool, '_popup', lambda button, menu: opened.append((button, menu)))
    QTest.mouseClick(window.choice_label, Qt.MouseButton.LeftButton, pos=QPoint(4, 4))
    window.model_menu_tool.choose_fragment('Метил · —CH₃')
    QTest.mouseClick(window.choice_label, Qt.MouseButton.LeftButton, pos=QPoint(4, 4))
    assert [b for b, _ in opened] == [window.choice_label] * 2
    titles = [[a.text() for a in m.actions()] for _, m in opened]
    assert titles[0] != titles[1]  # the molecules, then the fragments


def test_expanding_buttons_and_the_way_back_to_compass(window, app):
    # short actions are icons that unfold into icon + text on hover; the arrow next to the input file
    # of Sextant goes back to the molecule in Compass
    from PySide6.QtCore import QEvent
    from PySide6.QtGui import QEnterEvent
    from PySide6.QtCore import QPointF
    import time

    from azimuth.controls import COLLAPSED, ExpandingButton

    window.show()
    window.navigate(1)
    app.processEvents()
    b = window.to_compass_button
    assert isinstance(b, ExpandingButton) and b.width() == COLLAPSED and b.text() == 'К молекуле в Компасе'
    assert b.toolTip() == b.text() and b.property('quail_icon') == 'back'
    # in Sextant the icons do not unfold — the text is in the tooltip
    app.sendEvent(b, QEnterEvent(QPointF(5, 5), QPointF(5, 5), QPointF(5, 5)))
    end = time.monotonic() + 0.4
    while time.monotonic() < end:
        app.processEvents()
        time.sleep(0.01)
    assert not b.unfolded and b.width() == COLLAPSED and not b.foldable
    b.grab()
    app.sendEvent(b, QEvent(QEvent.Type.Leave))
    for item in (window.choose_program_button, window.options_button, window.job_window.stop_button, window.job_window_button):
        assert isinstance(item, ExpandingButton) and item.text() and not item.foldable
    unfolding = ExpandingButton('Текст', None, 'save')  # elsewhere they still unfold
    unfolding.unfold(True)
    assert unfolding.unfolded
    b.click()
    assert window.stack.currentIndex() == 0


def test_vtk_engine_switch_draws_and_falls_back(window, app):
    # «Вид → Трёхмерная графика VTK (проба)» draws the atoms and bonds with VTK where it works,
    # keeps labels and selection on top, remembers the choice; a failure brings back the built-in renderer
    from modules.compass.view import vtk_model

    v = window.viewer
    window.navigate(0)
    v.resize(480, 360)
    v.set_selection([0])
    raster_image = v.grab().toImage()
    ok, why = vtk_model.available()
    remembered = window.preferences.value(window.ENGINE_KEY)  # the user's choice, put back at the end
    try:
        window.engine_action.trigger()
        app.processEvents()
        if not ok:
            assert v.engine == 'raster' and not window.engine_action.isChecked(), why
            return
        assert v.engine == 'vtk' and window.engine_action.isChecked()
        assert str(window.preferences.value(window.ENGINE_KEY)) == 'vtk'
        image = v.grab().toImage()
        assert v.engine == 'vtk'  # no fallback while drawing
        point = v.projected()[0][0]
        x, y = round(point.x()), round(point.y())
        # the oxygen is drawn in both engines with nearly the same colour at its centre
        a, b = image.pixelColor(x, y), raster_image.pixelColor(x, y)
        assert abs(a.red() - b.red()) + abs(a.green() - b.green()) + abs(a.blue() - b.blue()) < 120
        # a failure of VTK while drawing: back to the built-in renderer, the menu unchecked
        window.view_tool.engine_failed('test')
        assert v.engine == 'raster' and not window.engine_action.isChecked()
    finally:
        window.view_tool.set_engine(False, quiet=True)
        assert str(window.preferences.value(window.ENGINE_KEY)) == 'raster'
        if remembered is None:
            window.preferences.remove(window.ENGINE_KEY)
        else:
            window.preferences.setValue(window.ENGINE_KEY, remembered)


def test_overlay_of_the_native_vtk_view(window, app):
    # with VTK drawing straight into the window, the view paints the rest on a transparent overlay; what
    # lies under the model (grid, rings …) is painted into an image whose model pixels are cleared
    from PySide6.QtGui import QImage
    from azimuth.core import Atom, Molecule

    v = window.viewer
    window.navigate(0)
    v.resize(480, 360)
    v.yaw = v.pitch = v.roll = 0.0
    v.basis = None
    v.label_mode = 'none'
    v.grid = True
    v.set_molecule(Molecule('C', (Atom('C', 0, 0, 0),), ()))
    v.set_selection([0])
    image = QImage(v.width(), v.height(), QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(0)
    v.paint_over_native(image)
    centre, r = v.projected()[0][0], v.atom_radius(0)
    inside = [(x, y) for x in range(24, v.width(), 30) for y in range(24, v.height(), 30) if (x - centre.x()) ** 2 + (y - centre.y()) ** 2 < (0.8 * r) ** 2]
    assert inside, 'a grid dot lies under the atom'
    assert all(image.pixelColor(x, y).alpha() == 0 for x, y in inside)  # the grid is not drawn over the atom
    assert image.pixelColor(24, 24).alpha() > 0  # … but on the empty field
    ring = (round(centre.x() + r + 5), round(centre.y()))
    assert any(image.pixelColor(ring[0] + d, ring[1]).alpha() > 0 for d in (-1, 0, 1))  # the selection ring
    assert image.pixelColor(round(centre.x()), round(centre.y())).alpha() == 0  # the model itself is VTK's


def test_vtk_draws_straight_into_the_window(window, app):
    # VTK in a child OpenGL widget; picking, pictures and turning it off. There is no OpenGL on the
    # offscreen platform of the tests: the view refuses there (checked) and the rest is checked in the program.
    from PySide6.QtGui import QGuiApplication

    v = window.viewer
    from modules.compass.view import vtk_view

    if not vtk_view.ENABLED:
        assert v.set_native(True) is False and 'off' in v.native_error and v._native is None
        return
    if QGuiApplication.platformName() in ('offscreen', 'minimal'):
        assert v.set_native(True) is False and 'OpenGL' in v.native_error and v._native is None
        return
    pytest.importorskip('vtkmodules')
    from PySide6.QtCore import Qt

    if not v.set_native(True):
        pytest.skip('VTK cannot draw into a QOpenGLWidget here: ' + v.native_error)
    try:
        n = v._native
        assert n.gl.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        assert n.overlay.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        n.refresh()
        app.processEvents()
        point = v.projected()[0][0]
        assert v.hit_test(point) == 0
        picture = v.render_image()
        assert not picture.isNull() and n.gl.isVisibleTo(v)
    finally:
        v.set_native(False)
    assert v._native is None


def test_building_switches_are_icon_buttons(window, app):
    # «Достраивать водороды при построении» and «Выравнивать при построении» as icon toggles of the structure tools
    show_model(window, app)
    window.edit_toggle.click()
    assert window.tidy_live_button.isVisible() and window.hydrogens_live_button.isVisible()
    assert window.tidy_live_button.isChecked() == window.tidy_live_action.isChecked()
    before = window.hydrogens_live_action.isChecked()
    try:
        window.hydrogens_live_button.click()
        assert window.hydrogens_live_action.isChecked() is not before
        window.hydrogens_live_action.setChecked(True)
        assert window.hydrogens_live_button.isChecked()
        window.new_molecule()
        window.element.setCurrentText('C')
        window.place_on_model((0, 0, 0), None)
        assert window.molecule.formula == 'CH4'
        window.place_on_model((0, 0, 0), 0)  # the saturated carbon gives up a hydrogen
        assert window.molecule.formula == 'C2H6'
    finally:
        window.hydrogens_live_action.setChecked(before)
        window.dirty = False


def test_quill_pictures(window, app, monkeypatch):
    # 0.247.0: the pictures of states in thin lines (azimuth/state_icons.py) instead of Quill, under the same names —
    # sharp at the ratio of the screen, nothing mirrored; the dialogs answer through the replaced QMessageBox.question
    # (no window in the tests); the window of the calculation shows the picture of its state
    from PySide6.QtWidgets import QFrame, QMessageBox

    from azimuth import quill, state_icons

    for name in quill.NAMES:
        picture = quill.pixmap(name, 96, 2.0)
        assert not picture.isNull() and picture.width() == picture.height() == 192, name
        assert picture.devicePixelRatio() == 2.0
        assert state_icons.svg(name), name
    assert quill.pixmap('missing', 96).isNull() and quill.TURNED_LEFT == frozenset()
    image = quill.pixmap('calc-failed', 48, 1.0).toImage()  # thin lines on a clear ground, the red of a failure
    alphas = [image.pixelColor(x, y).alpha() for x in range(48) for y in range(48)]
    assert 0 < sum(a > 0 for a in alphas) < 48 * 48 * 0.3
    assert any(image.pixelColor(x, y).red() > 180 and image.pixelColor(x, y).alpha() > 200 for x in range(48) for y in range(48))
    # the picture at the top of a narrow column at the left over all the rows; no blue edge
    from PySide6.QtWidgets import QCheckBox, QLabel, QWidget

    box = QMessageBox(window)
    quill.headline(box, 'Магнитные атомы', 'В ячейке Ni — их соединения обычно магнитные. ' * 3)
    # the box of Qt does not own a check box given to it: a temporary one was collected by Python and the box, laying
    # itself out again, read freed memory (a segmentation fault of the run of 2026-11-15) — the test keeps it
    check = QCheckBox('больше не спрашивать', box)
    box.setCheckBox(check)
    box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    quill.set_icon(box, 'save', QMessageBox.Icon.Question)
    box.show()
    app.processEvents()
    assert box.findChild(QFrame, 'quillEdge') is None
    grid = box.layout()
    icon, text = box.findChild(QLabel, quill._ICON_LABEL), box.findChild(QLabel, quill._TEXT_LABEL)
    info = box.findChild(QLabel, quill._INFO_LABEL)
    buttons = box.findChild(QWidget, quill._BUTTONS)
    side = box.findChild(QFrame, 'quillSide')
    assert not icon.isVisible() and side is not None and side.isVisible()
    rows = [text, info, box.checkBox(), buttons]
    assert [grid.getItemPosition(grid.indexOf(w))[:2] for w in rows] == [(0, 2), (1, 2), (2, 2), (3, 2)]
    assert grid.getItemPosition(grid.indexOf(side)) == (0, 0, 4, 1) and 'Магнитные атомы' in text.text()
    assert side.sizeHint().height() == 0  # it asks for no height: the text and the buttons decide it
    assert side.width() == quill.SIDE and text.geometry().left() > side.geometry().right()
    assert not side.art().isNull() and side.art().deviceIndependentSize().width() == quill.ICON_SIDE
    side.grab()
    assert 'Ni' in info.text()
    box.close()
    plain = QMessageBox(window)
    quill.set_icon(plain, 'missing', QMessageBox.Icon.Question)
    assert getattr(plain, '_quill_compact', None) is None  # no Quill — the box of Qt as it is
    yes_no = QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    asked = []
    monkeypatch.setattr(  # replaced here (the guard of conftest.py would count a call of its own stub as a window)
        QMessageBox, 'question', staticmethod(lambda *args: asked.append(args[1]) or QMessageBox.StandardButton.No)
    )
    assert quill.question(window, 'T', 'x', yes_no, QMessageBox.StandardButton.No, 'save') == QMessageBox.StandardButton.No
    assert asked == ['T']
    asked.clear()
    monkeypatch.setattr(
        QMessageBox, 'question', staticmethod(lambda *args: asked.append(args[1]) or QMessageBox.StandardButton.Yes)
    )
    dirty = window.dirty
    window.dirty = True
    try:
        assert window.confirm_replace() and len(asked) == 1
    finally:
        window.dirty = dirty

    job_window = window.job_window
    job_window.begin('H₂O')
    # while it runs — the picture of a running calculation (no animation since 0.247.0)
    assert job_window.picture_name == 'calc-running' and not job_window.picture.isHidden()
    assert not job_window.picture.pixmap().isNull() and not job_window.movie_running()
    assert job_window.show_picture('calc-done') and job_window.picture_name == 'calc-done'
    assert not job_window.picture.isHidden()
    assert not job_window.show_picture('missing') and job_window.picture.isHidden()
    job_window.show_picture('calc-done')
    job_window.begin('H₂O')
    assert job_window.picture_name == 'calc-running'
    job_window.finish()
    job_window.hide()

    window.clear_result()
    assert not window.empty_quill.isHidden()
    # Quill and the hint in the card of the frequencies instead of its table; no status and no «Колебания и ИК» without
    # a result
    assert not window.empty_page.isHidden() and window.frequency_table.isHidden() and window.result_summary.isHidden()
    assert not window.result_tabs.isTabVisible(window.vibrations_tab)
    assert not window.show_empty_quill(False) and window.empty_quill.isHidden() and not window.frequency_table.isHidden()
    window.clear_result()


def test_quill_dialogs_and_empty_places(window, app, monkeypatch):
    # the pictures of docs/art/QUAIL_ART_DIALOGS.md — a message with Quill answers through a replaced
    # QMessageBox.warning (no window in the tests); the empty places show her over the text; the error of the program
    # picks the picture from the exception
    from PySide6.QtWidgets import QMessageBox

    from azimuth import quill

    seen = []
    monkeypatch.setattr(QMessageBox, 'warning', staticmethod(lambda *args: seen.append(args[1]) or QMessageBox.StandardButton.Ok))
    assert quill.warning(window, 'T', 'x', 'offline') == QMessageBox.StandardButton.Ok and seen == ['T']
    note = quill.EmptyNote('t', 'no-points')
    assert note.text() == 't' and not note.picture.pixmap().isNull() and not note.picture.isHidden()
    assert note.picture.pixmap().deviceIndependentSize().width() == 72
    assert quill.trimmed_pixmap('sextant-empty', 145).width() == quill.pixmap('sextant-empty', 145).width()
    assert quill.EmptyNote('t', 'missing').picture.isHidden()

    class Offline(ValueError):
        kind = 'connection'

    names = []
    monkeypatch.setattr(quill, 'warning', lambda parent, title, text, name='error': names.append(name))
    found = ValueError('y')
    found.quill = 'nothing-found'
    for exc in (Offline('x'), found, ValueError('z')):
        window.error(exc)
    assert names == ['offline', 'nothing-found', 'error']


def test_crystal_quill_hint(window, app):
    # 0.247.0: no Quill in the empty field of «Компас · Кристалл» — the field says: a CIF file or an example
    from pathlib import Path

    from modules.compass.view.viewer import CRYSTAL_PARTS

    window.dirty = False
    window.resize(1400, 900)
    window.show()
    window.navigate(0)
    window.crystal_tool.set_compass_mode('crystal')
    app.processEvents()
    assert window.crystal_hint is None and window.viewer.empty_parts == CRYSTAL_PARTS
    assert not Path(__file__).resolve().parents[2].joinpath('modules', 'compass', 'view', 'quill_hint.py').exists()
    window.viewer.grab()
    window.crystal_tool.set_compass_mode('molecule')

def test_chemcraft_menu_actions(window):
    # the new actions of the Compass menus change the structure as one undoable step
    acts = window.chem_actions
    start = window.molecule
    window.viewer.set_selection([1])
    acts['origin'].trigger()
    assert window.molecule.atoms[1].position == pytest.approx((0.0, 0.0, 0.0), abs=1e-7)
    window.undo_geometry()
    assert window.molecule == start
    window.viewer.set_selection([0])
    acts['expand'].trigger()
    assert set(window.viewer.selected) == {0, 1, 2}  # the water of the example: O and both H
    window.viewer.set_selection([0, 1])
    acts['all_distances'].trigger()
    assert (0, 1) in window.viewer.pinned
    acts['clear_pins'].trigger()
    assert window.viewer.pinned == []
    acts['masses'].trigger()
    assert 'H2O' in window._report_box.findChild(__import__('PySide6.QtWidgets', fromlist=['QTextBrowser']).QTextBrowser).toPlainText()
    window._report_box.close()


def test_undo_and_redo_of_every_structure_operation_of_the_menus(window):
    # each operation of the Compass menus that changes the structure is one step: undo gives the structure
    # before it, redo the structure after it
    acts = window.chem_actions
    cases = [
        ('dummy', [0, 1]), ('unbond_selected', [0]), ('origin', [1]), ('axes3', [0, 1, 2]),
        ('along_x', [0, 1]), ('along_y', [0, 1]), ('along_z', [0, 1]), ('principal', []), ('invert_xyz', []),
        ('shake', []),
    ]
    for key, chosen in cases:
        before = window.molecule
        window.viewer.set_selection(chosen)
        acts[key].trigger()
        after = window.molecule
        if key in ('principal', 'along_x', 'along_y', 'along_z') and after == before:
            continue  # the example may already lie so: nothing changed, no step
        assert after != before, key
        window.undo_geometry()
        assert window.molecule == before, key
        window.redo_geometry()
        assert window.molecule == after, key
        window.undo_geometry()


def test_settings_window(window, tmp_path):
    # one window for the
    # preferences of the program, applied at once and kept under the old keys
    from PySide6.QtWidgets import QMenu

    from modules.spectrum.wavefunction import field_tables

    keys = ('csv_style', 'multiwfn_grid', 'jobs_folder', window.HYDROGENS_ON_OPEN)
    before = {k: window.preferences.value(k) for k in keys}
    saved_style, theme = field_tables.style, window.theme.currentIndex()
    try:
        assert window.settings_action.text() == 'Настройки…'
        dialog = window.show_settings('tables')
        assert set(dialog.boxes) == {'look', 'files', 'model', 'view', 'pictures', 'spectra', 'units', 'tables', 'jobs',
                                     'programs', 'multiwfn', 'errors', 'all'} and dialog.isVisible()
        assert set(dialog.nav) == set(dialog.boxes) and dialog.nav['spectra'].property('quail_icon') == 'band-width'
        from azimuth import crash_report  # the logs and a report for the author

        assert dialog.log_folder.text() == str(crash_report.log_dir()) and dialog.report_button.isEnabled()
        assert not dialog.language.isEnabled()  # the language is the hub's (here: Studio alone)
        dialog.separator.setCurrentIndex(dialog.separator.findData('\t'))
        assert field_tables.style == window.preferences.value('csv_style') == '\t,'
        assert dialog.sample.text() == 'C1  ⇥  -0,5000  ⇥  1,42'
        dialog.decimal.setCurrentIndex(dialog.decimal.findData('.'))
        assert field_tables.style == '\t.' and window.surface_tool.csv_style() == '\t.'
        dialog.separator.setCurrentIndex(dialog.separator.findData(','))  # the comma between the columns: the point
        assert field_tables.style == 'intl' and dialog.decimal.currentData() == '.'
        assert not dialog.decimal.model().item(0).isEnabled()
        dialog.separator.setCurrentIndex(dialog.separator.findData(';'))
        dialog.decimal.setCurrentIndex(dialog.decimal.findData(','))
        assert field_tables.style == 'ru' and dialog.sample.text() == 'C1;-0,5000;1,42'
        dialog.hydrogens.setChecked(False)
        assert not window.opening_tool.hydrogens_on_open() and not window.hydrogens_open_action.isChecked()
        dialog.hydrogens.setChecked(True)
        assert window.opening_tool.hydrogens_on_open() and window.hydrogens_open_action.isChecked()
        dialog.grid.setCurrentIndex(dialog.grid.findData('medium'))
        assert window.surface_tool.nci_grid() == 'medium'
        assert dialog.choose_jobs_folder(str(tmp_path)) == tmp_path and dialog.jobs_folder.text() == str(tmp_path)
        assert window.run_tool.jobs_root() == tmp_path
        dialog.theme.setCurrentIndex(1 - theme)
        assert window.theme.currentIndex() == 1 - theme
        dialog.theme.setCurrentIndex(theme)
        # «Как в системе» — the
        # theme of the system now and when it changes; a theme chosen by hand ends it
        from azimuth import app_theme as studio_app  # the theme of the system is asked there (0.222.30)

        dark = [theme == 0]
        saved_hint = studio_app.system_prefers_dark
        studio_app.system_prefers_dark = lambda: dark[0]
        try:
            assert dialog.theme.count() == 3
            dialog.theme.setCurrentIndex(2)
            assert window.follows_system_theme() and window.theme.currentIndex() == (1 if dark[0] else 0)
            dark[0] = not dark[0]
            assert window.system_theme_changed() and window.theme.currentIndex() == (1 if dark[0] else 0)
            dialog.theme.setCurrentIndex(theme)
            assert not window.follows_system_theme() and window.theme.currentIndex() == theme
            dark[0] = not dark[0]
            assert not window.system_theme_changed() and window.theme.currentIndex() == theme
        finally:
            studio_app.system_prefers_dark = saved_hint
            window.set_theme_follows_system(False)
        # «Таблицы CSV…» of the menu of the surfaces: the same window, at the tables
        menu = QMenu()
        item = window.surface_tool.add_table_menu(menu)
        assert item.text() == 'Таблицы CSV…' and not item.menu()
        item.trigger()
        assert window.settings_dialog is not dialog and window.settings_dialog.isVisible()
        window.settings_dialog.close()
    finally:
        field_tables.style = saved_style
        window.theme.setCurrentIndex(theme)
        for k, v in before.items():
            if v is None:
                window.preferences.remove(k)
            else:
                window.preferences.setValue(k, v)


def test_settings_of_bonds_pictures_and_spectra(window, tmp_path):
    # bonds by distance and by Mayer orders, one orientation of the steps, pictures, spectra — kept and followed at once
    from azimuth import defaults
    from azimuth.core import Atom, Molecule
    from modules.compass.chemistry import builder

    keys = tuple(defaults.KEYS)
    try:
        dialog = window.show_settings('model')
        assert dialog.bond_factor.value() == 1.22 and dialog.bond_order.value() == 0.5
        assert not dialog.common_orientation.isChecked() and dialog.picture_crop.isChecked()
        pair = Molecule('C2', (Atom('C', 0, 0, 0), Atom('C', 1.8, 0, 0)), None)
        assert builder.connections(pair)
        dialog.bond_factor.setValue(1.10)
        assert float(window.preferences.value('bond_factor')) == 1.10 and not builder.connections(pair)
        dialog.picture_transparent.setChecked(True)
        assert window.viewer.transparent and defaults.get('picture_transparent')
        dialog.picture_scale.setCurrentIndex(dialog.picture_scale.findData(4))
        assert window.picture_tool.snapshot_menu().actions()[1].text().endswith('(×4)')
        dialog.ir_style.setCurrentIndex(1)
        dialog.ir_width.setValue(35)
        assert window.vibrations.ir_style.currentIndex() == 1 and window.vibrations.ir_width.value() == 35
        dialog.uv_fwhm.setValue(0.5)
        assert window.uv_panel.fwhm.value() == 0.5 and window.uv_panel.plot.fwhm == 0.5
        assert dialog.reset('model')['bond_factor'] == 1.22 and dialog.bond_factor.value() == 1.22
        assert builder.connections(pair)
        dialog.reset('pictures')
        assert not window.viewer.transparent and dialog.picture_scale.currentData() == 3
        dialog.reset('spectra')
        assert window.vibrations.ir_style.currentIndex() == 0 and window.uv_panel.fwhm.value() == 0.3
        assert dialog.reset_buttons['spectra'].text() == 'По умолчанию'
        dialog.close()
    finally:
        for k in keys:
            window.preferences.remove(k)
        defaults.load(window.preferences)
        window.viewer.transparent = False


def test_settings_of_units_programs_and_all(window, tmp_path):
    # units, the look of the model, the paths of the
    # programs, all the settings to a file, from a file and back to the installation
    import json

    from azimuth import defaults
    from modules.compass.panels.trajectory_drawer import delta_header
    from modules.sextant import runner

    saved = {k: window.preferences.value(k) for k in window.preferences.allKeys()}
    try:
        dialog = window.show_settings('units')
        assert delta_header() == 'ΔE, ккал/моль'
        dialog.energy_unit.setCurrentIndex(dialog.energy_unit.findData('ev'))
        assert defaults.energy_name() == 'эВ' and delta_header() == 'ΔE, эВ'
        assert window.drawer.table.horizontalHeaderItem(1).text() == 'ΔE, эВ'
        dialog.quick_atoms.setValue(100)
        assert defaults.get('quick_atoms') == 100 and dialog.quick_atoms.specialValueText() == 'никогда'
        assert dialog.start_scheme.itemData(0) == '' and dialog.start_scheme.count() > 2
        dialog.start_scheme.setCurrentIndex(dialog.start_scheme.findData('Стержни'))
        assert window.scheme_tool.start_scheme() == 'Стержни'  # applied at the next start (apply_start_scheme)
        # programs: a file given and forgotten
        program = tmp_path / 'xtb'
        program = program_script(program, '')
        assert dialog.choose_program('xtb', str(program)) == program
        assert window.run_tool.configured_program('xtb') == str(program) and dialog.program_paths['xtb'].text() == str(program)
        assert dialog.program_buttons['xtb'][1].isEnabled()
        dialog.forget_program('xtb')
        assert window.run_tool.configured_program('xtb') is None and not dialog.program_buttons['xtb'][1].isEnabled()
        found = runner.find_program('xtb', None)
        assert dialog.program_paths['xtb'].text() == ('не найдена' if found is None else str(found) + ' · найдена сама')
        # all the settings: to a file (no secret keys), back to the installation, from the file
        window.preferences.setValue('server/password_hint', 'x')
        target = tmp_path / 'settings.json'
        assert dialog.export_settings(str(target)) > 3
        data = json.loads(target.read_text(encoding='utf-8'))
        assert data['azimuth-settings'] == 1 and data['values']['energy_unit'] == 'ev'
        assert 'server/password_hint' not in data['values']
        assert dialog.reset_all(ask=False) and 'energy_unit' not in window.preferences.allKeys()
        assert defaults.get('energy_unit') == 'kcal' and dialog.energy_unit.currentData() == 'kcal'
        assert window.drawer.table.horizontalHeaderItem(1).text() == 'ΔE, ккал/моль'
        assert dialog.import_settings(str(target)) == len(data['values'])
        assert defaults.get('energy_unit') == 'ev' and dialog.energy_unit.currentData() == 'ev'
        bad = tmp_path / 'other.json'
        bad.write_text('{"a": 1}', encoding='utf-8')
        assert dialog.import_settings(str(bad)) is None and dialog.all_note.text() == 'Это не файл настроек Азимута.'
        assert dialog.reset('units')['energy_unit'] == 'kcal'
        dialog.close()
    finally:
        window.preferences.clear()
        for k, v in saved.items():
            window.preferences.setValue(k, v)
        defaults.load(window.preferences)
        window.drawer.relabel_energies()


def test_error_report_window(window, app, tmp_path, monkeypatch):
    # an exception nobody caught goes to errors.log and the window says so once (not again within QUIET s);
    # «Файл → Отчёт об ошибке…» makes the .zip for the author where the user chose
    import sys
    import zipfile

    from PySide6.QtGui import QDesktopServices
    from PySide6.QtWidgets import QFileDialog

    from azimuth import crash_report

    reporter = crash_report.Reporter(app, window)
    shown = []
    monkeypatch.setattr(reporter, '_show', lambda short: shown.append(short))
    try:
        raise ValueError('проверка журнала')
    except ValueError:
        reporter.excepthook(*sys.exc_info())
    app.processEvents()
    log = (crash_report.log_dir() / crash_report.ERRORS).read_text(encoding='utf-8')
    assert 'ValueError: проверка журнала' in log and shown == ['ValueError: проверка журнала']
    try:
        raise KeyError('второй')
    except KeyError:
        reporter.excepthook(*sys.exc_info())
    app.processEvents()
    assert len(shown) == 1 and reporter.count == 2  # written down, but no second window at once
    target = tmp_path / 'report.zip'
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *a, **k: (str(target), ''))
    opened = []
    monkeypatch.setattr(QDesktopServices, 'openUrl', lambda url: opened.append(url) or True)
    assert window.report_action.text() == 'Отчёт об ошибке…'
    assert window.save_error_report() == target and opened
    with zipfile.ZipFile(target) as box:
        assert 'errors.log' in box.namelist() and 'проверка журнала' in box.read('errors.log').decode('utf-8')
    # «Отправить автору…» — the .zip on the Desktop, a letter mailto, the folder of the .zip
    monkeypatch.setattr(crash_report.Path, 'home', lambda: tmp_path)
    (tmp_path / 'Desktop').mkdir()
    opened.clear()
    sent = crash_report.send_report(window)
    assert sent.parent == tmp_path / 'Desktop' and sent.name.startswith('azimuth-report_') and sent.is_file()
    assert opened[0].scheme() == 'mailto' and crash_report.AUTHOR in opened[0].toString()
    assert Path(opened[1].toLocalFile()) == tmp_path / 'Desktop'  # «C:/…» from Qt on Windows
    # no mail program: the address is copied and the window tells where the report is
    from azimuth import quill

    told = []
    monkeypatch.setattr(QDesktopServices, 'openUrl', lambda url: url.scheme() != 'mailto')
    monkeypatch.setattr(quill, 'warning', lambda parent, title, text, name='error': told.append(text))
    crash_report.send_report(window)
    assert app.clipboard().text() == crash_report.AUTHOR and crash_report.AUTHOR in told[0]


def test_property_buttons_open_at_the_first_press_and_grey_what_cannot_be(window, app, monkeypatch):
    # the buttons «Атомы», «Связи», «Диполь и силы» worked from the second press — their
    # menu was filled only in aboutToShow, empty at the first exec; a second press on an open menu opened it again;
    # «Спиновые заселённости по орбиталям» was not grey for a closed shell, where it gives nothing
    from PySide6.QtWidgets import QMenu

    out = Path(__file__).parents[1] / 'data' / 'orca601' / 'h2o_optfreq.out'  # water, a singlet
    shown = []
    monkeypatch.setattr(window.model_menu_tool, '_popup', lambda button, menu: shown.append((button, menu)))  # no QMenu.exec here
    old = (getattr(window, 'output_path', None), window.result_properties)
    window.output_path, window.result_properties = str(out), None
    try:
        menu = window.property_menus['atoms']
        menu.clear()
        window.property_tool.show_property_menu('atoms')
        assert [a for a in menu.actions() if a.text()] and shown[-1][1] is menu  # filled before it is shown
        assert window.property_tool.result_open_shell() is False
        box = QMenu()
        window.property_tool.add_multiwfn_item(box)
        spins = {a.text(): a for a in box.actions()}['Спиновые заселённости по орбиталям (Малликен)']
        assert not spins.isEnabled() and 'Закрытая оболочка' in spins.toolTip()
    finally:
        window.output_path, window.result_properties = old


def test_icons_are_drawn_at_the_pixels_of_the_screen(app):
    # at 150 % Qt asks a pixmap of that scale
    from PySide6.QtCore import QSize
    from PySide6.QtGui import QIcon

    from azimuth.icons import GlyphEngine

    for scale, side in ((1.0, 21), (1.25, 26), (1.5, 32), (2.0, 42)):
        pixmap = GlyphEngine('charges').scaledPixmap(QSize(21, 21), QIcon.Mode.Normal, QIcon.State.Off, scale)
        assert pixmap.width() == side and pixmap.devicePixelRatio() == scale


def test_every_label_icon_is_drawn(app):
    # every glyph whose name starts with «label-» is drawn, «label-style» too, and is not empty
    from PySide6.QtCore import QSize
    from PySide6.QtGui import QIcon

    from azimuth import button_icons
    from azimuth.icons import GlyphEngine

    names = {'label-number', 'label-element', 'label-both', 'label-custom'} | {
        n for n in button_icons.BUTTON_GLYPHS if n.startswith('label-')}
    assert 'label-style' in names
    for name in sorted(names):
        image = GlyphEngine(name).scaledPixmap(QSize(21, 21), QIcon.Mode.Normal, QIcon.State.Off, 1.0).toImage()
        assert any(image.pixelColor(x, y).alpha() for x in range(image.width()) for y in range(image.height())), name


def test_spin_boxes_and_tab_bars_are_retranslated(app):
    # numbers with units and the tab «Новый проект» are translated when the language is switched
    from PySide6.QtWidgets import QSpinBox, QTabBar, QVBoxLayout, QWidget

    from azimuth import i18n

    root = QWidget()
    box = QVBoxLayout(root)
    cores = QSpinBox()
    cores.setSuffix(i18n.tr(' проц.'))
    tabs = QTabBar()
    tabs.addTab(i18n.tr('Новый проект'))
    box.addWidget(cores)
    box.addWidget(tabs)
    try:
        i18n.set_language('en')
        i18n.retranslate(root)
        assert cores.suffix() == i18n.tr(' проц.') != ' проц.' and tabs.tabText(0) == 'New project'
        i18n.set_language('ru')
        i18n.retranslate(root)
        assert cores.suffix() == ' проц.' and tabs.tabText(0) == 'Новый проект'
    finally:
        i18n.set_language('ru')


def test_text_buttons_get_icons(window, app):
    # a button with words gets the
    # glyph of its text when shown (azimuth/polish.py); not a checkable segment, not one with its own icon
    from PySide6.QtWidgets import QDialog, QPushButton, QVBoxLayout

    from azimuth import polish
    from azimuth.i18n import tr

    polish.install(app)
    dialog = QDialog(window)  # the filter is taken off at the end (see polish.uninstall)
    column = QVBoxLayout(dialog)
    save, segment, plain, primary = (QPushButton(tr('Сохранить картинку…')), QPushButton(tr('Спин')),
                                     QPushButton('Квил'), QPushButton(tr('Запустить расчёт')))
    segment.setCheckable(True)
    primary.setObjectName('primary')
    for button in (save, segment, plain, primary):
        column.addWidget(button)
    dialog.show()
    app.processEvents()
    try:
        assert save.property('azimuthTextIcon') == 'image' and not save.icon().isNull()
        assert primary.property('azimuthTextIcon') == 'play'
        assert segment.icon().isNull() and plain.icon().isNull()
    finally:
        dialog.close()
        assert polish.uninstall(app)


def test_menu_items_get_icons(window, app):
    # the items of a menu get their glyphs when it is
    # shown (not the checkable ones, not the submenus)
    from PySide6.QtWidgets import QMenu

    from azimuth import polish
    from azimuth.i18n import tr

    polish.install(app)
    menu = QMenu(window)
    new = menu.addAction(tr('Новая молекула'))
    toggle = menu.addAction(tr('Прозрачный фон'))
    toggle.setCheckable(True)
    sub = menu.addMenu(tr('Примеры молекул'))
    menu.popup(window.mapToGlobal(window.rect().center()))
    app.processEvents()
    try:
        assert new.property('azimuthTextIcon') == 'file-new' and not new.icon().isNull()
        assert toggle.icon().isNull() and sub.menuAction().icon().isNull()
    finally:
        menu.close()
        assert polish.uninstall(app)


def test_file_menu_tabs_clear_paste_and_name(window, app, tmp_path, monkeypatch):
    # «Сохранить» without a question,
    # «Сохранить как…», the tabs closed from the menu, «Очистить», a structure from the clipboard and by a name
    from PySide6.QtWidgets import QApplication

    from modules.compass.chemistry import pubchem

    monkeypatch.setattr(window, 'confirm_replace', lambda *a, **k: True)
    errors = []
    monkeypatch.setattr(window, 'error', errors.append)
    for title in ('Сохранить', 'Сохранить как…', 'Закрыть вкладку', 'Закрыть остальные вкладки', 'Очистить',
                  'Молекула по названию…', 'Вставить структуру из буфера', 'Показать файл в папке'):
        assert any(a.text() == title for a in window.menuBar().actions()[0].menu().actions()), title
    start = len(window.documents)
    window.load_molecule(window.molecule.__class__('w', (), ()))
    assert window.file_tool.paste_structure('O 0 0 0\nH 0.96 0 0\nH -0.24 0.93 0') == 'xyz'
    assert window.molecule.formula == 'H2O' and len(window.documents) == start  # the empty tab took it
    QApplication.clipboard().setText('CCO')
    assert window.file_tool.paste_structure() == 'smiles' and len(window.documents) == start + 1  # a new tab
    assert window.file_tool.paste_structure('not a structure at all') is None and len(errors) == 1
    # «Сохранить»: the first time a name is asked (as «Сохранить как…»), then into the same file
    target = tmp_path / 'ethanol.qcc'
    asked = []
    monkeypatch.setattr(window, 'save_text', lambda *a: (asked.append(a[0]),
                                                          target.write_text(a[2], encoding='utf-8'), str(target))[2])
    assert window.save_project() == str(target) and len(asked) == 1 and not window.dirty
    window.dirty = True
    assert window.save_project() == str(target) and len(asked) == 1 and not window.dirty  # no question
    assert window.file_tool.tab_file() == target
    assert window.save_project_as() == str(target) and len(asked) == 2
    # «Очистить»: the structure and what lies over it
    window.viewer.pinned = [(0, 1)]
    window.viewer.custom_labels = {0: 'X'}
    assert window.file_tool.clear_tab() and not window.molecule.atoms
    assert window.viewer.pinned == [] and window.viewer.custom_labels == {}
    # a name: PubChem answers a SMILES (no 3D record) — the structure built here
    monkeypatch.setattr(pubchem, 'by_name', lambda name, **k: ('smiles', 'CC(=O)C'))
    window.file_tool._name_answer(('acetone', pubchem.by_name('acetone'), None))
    assert window.molecule.formula == 'C3H6O'
    window.file_tool._name_answer(('xyzzy', None, None))  # unknown: a message, nothing changes
    assert window.molecule.formula == 'C3H6O'
    # the tabs: the others closed, then this one
    window.new_document()
    window.dirty = False
    for d in window.documents:
        d.dirty = False
    window.file_tool.close_other_tabs()
    assert len(window.documents) == 1
    assert window.file_tool.close_current_tab() and len(window.documents) == 1 and not window.molecule.atoms  # an empty one


def test_edit_menu_order_transform_planes(window, app, monkeypatch):
    # the whole molecule, the order of the atoms, all bonds off, «Сдвинуть и
    # повернуть…», «Плоскости групп атомов…», «Копировать SMILES» — each an undoable edit of the tab
    from math import dist

    from PySide6.QtWidgets import QApplication

    from azimuth.core import read_xyz

    monkeypatch.setattr(window, 'confirm_replace', lambda *a, **k: True)
    window.load_molecule(read_xyz('6\ntwo waters\nO 0 0 0\nH 0.96 0 0\nH -0.24 0.93 0\nO 5 0 0\nH 5.96 0 0\n'
                                  'H 4.76 0.93 0'))
    acts = window.chem_actions
    for key in ('whole', 'order_selected', 'order_h', 'unbond_all', 'transform', 'planes', 'copy_smiles'):
        assert key in acts and acts[key].text()
    assert [a.text() for a in window.chem_menus['order'].actions()] == ['Выделенные атомы — первыми',
                                                                         'Водороды — после своих атомов']
    window.viewer.set_selection([4])
    acts['whole'].trigger()
    assert window.viewer.selected == [3, 4, 5]
    window.viewer.set_selection([5, 3])  # clicked H6, then O4: they become 1 and 2
    assert window.structure_tool.order_selected_first()
    assert [a.symbol for a in window.molecule.atoms][:3] == ['H', 'O', 'O'] and window.viewer.selected == [0, 1]
    window.undo_geometry()
    assert [a.symbol for a in window.molecule.atoms] == ['O', 'H', 'H', 'O', 'H', 'H']
    before = window.molecule
    window.viewer.set_selection([0, 1, 2])
    assert window.structure_tool.transform_atoms({'shift': (0, 0, 2), 'angle': 45, 'axis': 'x'})
    # the item of the menu opens the window — «triggered» passed False for values
    acts['transform'].trigger()
    app.processEvents()
    assert window.structure_tool._transform_dialog.isVisible()
    window.structure_tool._transform_dialog.reject()
    before_view = (window.viewer.yaw, window.viewer.zoom)
    acts['camera_set'].trigger()  # «Положение камеры…»: its window, the view not changed by a False
    app.processEvents()
    assert (window.viewer.yaw, window.viewer.zoom) == before_view
    from azimuth.i18n import tr as _tr

    camera = [w for w in app.topLevelWidgets() if w.isVisible() and w.windowTitle() == _tr('Положение камеры')]
    assert camera
    for box in camera:
        box.reject()
    acts['planes'].trigger()  # «Плоскости групп атомов…» (the report: 'bool' object is not iterable)
    app.processEvents()
    planes = [w for w in app.topLevelWidgets() if w.isVisible() and w.windowTitle() == _tr('Плоскости групп атомов')]
    assert planes  # its window, not an error
    for box in planes:
        box.reject()
    acts['guide_text'].trigger()  # «Векторы и плоскости текстом…» (the report of 16:44: 'bool' … 'splitlines')
    app.processEvents()
    guides = [w for w in app.topLevelWidgets() if w.isVisible() and w.windowTitle() == _tr('Векторы и плоскости')]
    assert guides
    for box in guides:
        box.close()
    # two items, one checked, the projection
    assert acts['isometry'].isChecked() != acts['perspective'].isChecked()
    acts['perspective'].trigger()
    assert window.viewer.perspective and not acts['isometry'].isChecked()
    acts['isometry'].trigger()
    assert not window.viewer.perspective and not acts['perspective'].isChecked() and window.projection.currentIndex() == 0
    # «Отразить» is an edit of the geometry («Почему функция отразить в копировании расположена?»)
    from hub import menus_sections as _menus  # the menus of the sections (0.222.30)

    assert 'studio.mirror_menu,' in (Path(_menus.__file__).read_text(encoding='utf-8').split("'Геометрия'")[1].split("menu('Копирование'")[0])
    after = window.molecule
    assert abs(dist(after.atoms[0].position, after.atoms[1].position) - 0.96) < 1e-6
    assert after.atoms[3:] == before.atoms[3:]  # the other water stays
    text = window.structure_tool.planes_text([0, 1, 2], [3, 4, 5])
    assert 'Угол между плоскостями: 45.00°' in text and 'Плоскость 2: O4–H6' in text
    assert window.structure_tool.copy_smiles() == QApplication.clipboard().text() and 'O' in window.structure_tool.copy_smiles()
    assert window.structure_tool.remove_all_bonds() and window.molecule.bonds == ()
    window.viewer.set_selection([])


def test_view_menu_as_in_chemcraft(window, app, monkeypatch):
    # labels within the element and of the bonds, labels of the
    # selection only, their style; the centre of rotation; the camera by numbers; the axes on the model; the van der
    # Waals spheres; hidden atoms; the style of the measurements
    from math import degrees

    from azimuth import defaults
    from azimuth.core import read_xyz

    monkeypatch.setattr(window, 'confirm_replace', lambda *a, **k: True)
    window.load_molecule(read_xyz('7\nmethanol and X\nC 0 0 0\nO 1.43 0 0\nH -0.36 1.03 0\nH -0.36 -0.51 0.89\n'
                                  'H -0.36 -0.51 -0.89\nH 1.75 0.9 0\nX 0.7 0 0'))
    v, acts = window.viewer, window.chem_actions
    window.label_mode.setCurrentIndex(window.label_mode.findData('group'))
    assert [v.atom_label(i) for i in range(6)] == ['C1', 'O1', 'H1', 'H2', 'H3', 'H4']
    assert 'Номер в элементе · C1, H1' in [a.text() for a in window.chem_menus['labels'].actions()]
    window.structure_tool.set_bond_labels('order')
    assert v.bond_labels == 'order' and acts['bond_orders'].isChecked() and not acts['bond_numbers'].isChecked()
    acts['labels_selected'].trigger()
    assert v.labels_selected_only
    acts['vdw'].trigger()
    assert v.show_vdw
    window.structure_tool.set_axes_place('centre')
    assert v.axes_place == 'centre' and v.show_axes
    window.viewer.set_selection([1])
    assert window.structure_tool.hide_selected_atoms() == 1 and 1 in v.hidden_atoms() and v.selected == []
    acts['hide_dummies'].trigger()
    assert 6 in v.hidden_atoms()
    assert not v.render_image(1, False).isNull()  # everything drawn together
    window.structure_tool.show_all_atoms()
    assert v.hidden_atoms() == frozenset() and not acts['hide_dummies'].isChecked()
    # the centre of rotation at the oxygen; «Центровать» goes back
    window.viewer.set_selection([1])
    assert window.structure_tool.rotate_about_selection() == (1.43, 0.0, 0.0) and v.camera()[0] == (1.43, 0.0, 0.0)
    acts['center'].trigger()
    assert v.camera()[0] != (1.43, 0.0, 0.0)
    # the camera by numbers, from the axes of the model
    window.structure_tool.set_camera_numbers({'yaw': 30, 'pitch': -15, 'roll': 0, 'zoom': 1.5, 'model_axes': True})
    assert v.basis is None and abs(degrees(v.yaw) - 30) < 1e-9 and v.zoom == 1.5
    # the style of labels and measurements is kept in the settings
    try:
        assert window.structure_tool.measure_style({'measure_size': 14, 'measure_decimals': 2}) == {'measure_size': 14,
                                                                                    'measure_decimals': 2}
        assert int(window.preferences.value('measure_size')) == 14 and defaults.get('measure_decimals') == 2
        assert window.structure_tool.label_style({'label_scale': 1.4})['label_scale'] == 1.4
        v.pinned = [(0, 1), (2, 0, 1)]
        assert not v.render_image(1, False).isNull()
    finally:
        for key in ('measure_size', 'measure_decimals', 'label_scale'):
            window.preferences.remove(key)
        defaults.load(window.preferences)
        v.pinned = []
        window.structure_tool.set_bond_labels(None)
        v.labels_selected_only = v.show_vdw = False
        v.axes_place = 'corner'
        window.axes_button.setChecked(False)
        window.toggle_axes()
        window.label_mode.setCurrentIndex(window.label_mode.findData('element'))
        window.viewer.set_selection([])


def test_compass_tools_internal_size_and_tabs(window, app, tmp_path, monkeypatch):
    # the tools of a structure stay in Compass
    from azimuth.core import read_xyz
    from modules.spectrum.wavefunction import field_tables

    monkeypatch.setattr(window, 'confirm_replace', lambda *a, **k: True)
    window.load_molecule(read_xyz('4\nperoxide\nO 0 0 0\nO 1.45 0 0\nH -0.32 0.94 0\nH 1.77 0 0.94'))
    rows = window.structure_tool.internal_rows()
    assert [r[0] for r in rows] == ['Связь'] * 3 + ['Угол'] * 2 + ['Двугранный']
    assert rows[0][1] == 'O1–O2' and rows[0][2] == '1.4500' and rows[-1][1] == 'H3–O1–O2–H4'
    target = window.structure_tool.save_internal_csv(str(tmp_path / 'ic.csv'))
    header, table = field_tables.read_csv(target)
    assert header[0] == 'Тип' and len(table) == 6
    assert 'Связей: 3, углов: 2, двугранных: 1' in window.structure_tool.show_internal_coordinates()
    text = window.structure_tool.molecular_size_text()
    assert 'Ван-дер-ваальсов объём' in text and 'Å³' in text
    # «Сравнить с вкладкой»: the structure of another tab overlaid with its RMSD
    window.new_document()
    # turned by 90° about z, (x, y, z) → (−y, x, z); the copy before (x ↔ y) was the mirror image of the chiral
    # H2O2 (dihedral 90°), which a proper rotation cannot superimpose (RMSD 0.489 A)
    window.load_molecule(read_xyz('4\nturned\nO 0 0 0\nO 0 1.45 0\nH -0.94 -0.32 0\nH 0 1.77 0.94'))
    from PySide6.QtWidgets import QMenu

    menu = QMenu()
    assert window.structure_tool.fill_compare_tabs(menu) >= 1
    first = window.documents[window.current_document - 1].molecule
    assert window.structure_tool.compare_with_tab(first, 'peroxide') is not False
    assert window.compare_result is not None and window.compare_result.rmsd < 1e-6  # the same molecule, turned
    window.overlay_tool.clear_compare()


def test_recent_files_and_saving_many(window, app, tmp_path, monkeypatch):
    # of Chemcraft — Reopen (the recent files, Ctrl+R) and «Save multiple
    # files» (all the structures of a set at once)
    from PySide6.QtWidgets import QMenu


    monkeypatch.setattr(window, 'confirm_replace', lambda *a, **k: True)
    window.preferences.setValue(window.HYDROGENS_ON_OPEN, 'false')  # CO and H2 as written (no H added to CO)
    window.file_tool.clear_recent()
    first, second = tmp_path / 'water.xyz', tmp_path / 'co.xyz'
    first.write_text('3\nwater\nO 0 0 0.117\nH 0.757 0 -0.469\nH -0.757 0 -0.469\n', encoding='utf-8')
    second.write_text('2\nco\nC 0 0 0\nO 0 0 1.128\n', encoding='utf-8')
    window.opening_tool.open_path(str(first))
    window.opening_tool.open_path(str(second))
    window.opening_tool.open_path(str(first))
    assert window.file_tool.recent_files() == [str(first.resolve()), str(second.resolve())]
    menu = QMenu(window)
    window.file_tool.fill_recent_menu(menu)
    assert [a.text() for a in menu.actions() if a.text()][:2] == ['1. water.xyz', '2. co.xyz']
    first.write_text('2\nh2\nH 0 0 0\nH 0 0 0.74\n', encoding='utf-8')  # the file changed: Ctrl+R reads it again
    assert window.file_tool.reload_file() == str(first.resolve())
    assert len(window.molecule.atoms) == 2
    first.unlink()
    assert window.file_tool.recent_files() == [str(second.resolve())]  # a file gone is not offered

    # a set is a project — two files of it
    (tmp_path / 'вода.xyz').write_text('3\nwater\nO 0 0 0.117\nH 0.757 0 -0.469\nH -0.757 0 -0.469\n', encoding='utf-8')
    (tmp_path / 'CO.xyz').write_text('2\nco\nC 0 0 0\nO 0 0 1.128\n', encoding='utf-8')
    window.open_files_project([tmp_path / 'вода.xyz', tmp_path / 'CO.xyz'])
    app.processEvents()
    assert window.file_tool.save_batch('xyz-one', path=str(tmp_path / 'all.xyz')) == 1
    assert (tmp_path / 'all.xyz').read_text(encoding='utf-8').count('\n') == 9
    out = tmp_path / 'each'
    assert window.file_tool.save_batch('xyz-each', folder=str(out)) == 2
    assert sorted(p.name for p in out.iterdir()) == ['CO.xyz', 'вода.xyz']
    assert window.file_tool.save_batch('png-each', folder=str(out)) == 2
    assert sorted(p.name for p in out.glob('*.png')) == ['CO.png', 'вода.png']
    assert len(window.molecule.atoms) == 3  # the model of the tab is given back


def test_view_panel_folds_away_and_comes_back(window, app):
    # the panel of the view on the right of Compass folds by its chevron, smoothly, and the choice is kept
    import time

    from modules.compass.panels.trajectory_drawer import SLIDE_MS
    from modules.compass.actions.view_actions import EDGE_GAP, VIEW_PANEL_WIDTH

    show_model(window, app)
    try:
        full = window.view_tool.panel_full()
        assert full == VIEW_PANEL_WIDTH + window.view_panel_gap
        assert window.view_tool.view_panel_open() and window.view_panel.width() == full
        window.view_panel_toggle.click()
        widths, edges = [], []
        end = time.monotonic() + 3 * SLIDE_MS / 1000
        while time.monotonic() < end:
            app.processEvents()
            widths.append(window.view_panel.width())
            edges.append(window.view_panel_edge.width() if window.view_panel_edge.isVisible() else 0)
            time.sleep(0.01)
        assert any(0 < w < full for w in widths)
        # the panel goes first, then the box of
        # the line narrows — the field comes up to it
        assert all(e == window.view_tool.edge_full() for w, e in zip(widths, edges) if w > 0)
        assert window.view_tool.edge_full() == window.view_panel_gap + EDGE_GAP
        assert window.view_panel_edge.isHidden()
        assert window.view_panel.isHidden() and not window.view_tool.view_panel_open()
        assert window.view_panel_toggle.toolTip() == 'Показать панель вида'
        assert str(window.preferences.value('view_panel_open')).lower() in ('false', '0')
        window.view_tool.set_view_panel_open(True, animate=False)
        assert window.view_tool.view_panel_open() and window.view_panel.width() == full
    finally:
        window.view_tool.set_view_panel_open(True, animate=False)


def test_sliding_panels_move_the_field_at_each_step(window, app):
    # a step of a sliding panel lays the page out at once and asks the fast frames of the field
    show_model(window, app)
    try:
        x = window.viewer.mapTo(window, window.viewer.rect().topLeft()).x()
        width = window.viewer.width()
        # a step is the width of the panel and of the box of the line together — the field takes
        # all they give up
        edge = window.view_panel_edge
        before = window.view_panel.width() + (edge.width() if edge.isVisible() else 0)
        window.view_tool._view_panel_step(40)
        assert window.viewer.in_layout_motion()
        assert window.viewer.width() == width + before - 40  # at once, not on the next turn of the loop
        assert window.viewer.mapTo(window, window.viewer.rect().topLeft()).x() == x
    finally:
        window.view_tool.set_view_panel_open(True, animate=False)


def test_controls_outside_layouts_are_no_windows_of_their_own(window, app):
    # the controls kept only for their state (20: «Связать», the display mode, «Сохранить входной файл
    # .inp»…) were hidden windows of their own, left after the window was deleted; now children of the window
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QAbstractButton, QAbstractSpinBox, QComboBox, QFrame, QLabel

    loose = [type(w).__name__ + ' ' + w.objectName() for w in app.topLevelWidgets()
             if w.windowType() == Qt.WindowType.Window and not w.windowTitle()
             and isinstance(w, (QAbstractButton, QComboBox, QAbstractSpinBox, QLabel, QFrame))]
    assert not loose, loose
    assert window.export_button.window() is window and window.display_mode.window() is window


def test_the_wheel_scrolls_the_settings_and_changes_no_field(window, app):
    # the settings of his Mac held «Схема при запуске = Презентация», the factor of the bonds 1,08 and the
    # threshold of the orders 0,65 — the wheel over a field changed it while the window was scrolled
    from PySide6.QtCore import QPoint, QPointF
    from PySide6.QtGui import QWheelEvent

    keys = (window.scheme_tool.START_KEY, 'bond_factor')
    before = {k: window.preferences.value(k) for k in keys}
    try:
        dialog = window.show_settings('view')
        app.processEvents()
        dialog.setFocus()
        bar = dialog.scroll.verticalScrollBar()
        bar.setValue(bar.maximum() // 2)
        app.processEvents()
        for field in (dialog.start_scheme, dialog.bond_factor):
            assert field.focusPolicy() == Qt.FocusPolicy.StrongFocus and not field.hasFocus()
            value, place = (field.currentIndex() if hasattr(field, 'currentIndex') else field.value()), bar.value()
            centre = QPointF(field.rect().center())
            for _ in range(3):
                down = QWheelEvent(centre, QPointF(field.mapToGlobal(field.rect().center())), QPoint(0, 0), QPoint(0, -120),
                                   Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase,
                                   False)
                QApplication.sendEvent(field, down)
                app.processEvents()
            now = field.currentIndex() if hasattr(field, 'currentIndex') else field.value()
            assert now == value  # the field kept its value
            assert bar.value() != place or bar.value() == bar.maximum()  # the window scrolled instead
        # a list keeps its
        # value under the wheel even with the focus (clicked); the window scrolls
        dialog.start_scheme.setFocus()
        app.processEvents()
        if dialog.start_scheme.hasFocus():
            index = dialog.start_scheme.currentIndex()
            down = QWheelEvent(QPointF(5, 5), QPointF(dialog.start_scheme.mapToGlobal(QPoint(5, 5))), QPoint(0, 0),
                               QPoint(0, -120), Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
                               Qt.ScrollPhase.NoScrollPhase, False)
            QApplication.sendEvent(dialog.start_scheme, down)
            assert dialog.start_scheme.currentIndex() == index
        dialog.close()
    finally:
        for k, v in before.items():
            if v is None:
                window.preferences.remove(k)
            else:
                window.preferences.setValue(k, v)


def test_my_molecules(window, app, monkeypatch):
    # «Сохранить молекулу в «Мои молекулы»…» — then «Файл → Примеры молекул → Мои
    # молекулы» (into the tab) and «Молекула» of the building
    from modules.compass.actions import fragment_actions
    from modules.compass.chemistry import user_molecules

    before = window.preferences.value(fragment_actions.MOLECULES_KEY)
    saved = dict(user_molecules.USER)
    try:
        window.load_molecule(read_xyz(EXAMPLES['Метан · CH₄']))
        tool = window.fragment_tool
        assert tool.save_molecule(name='Мой метан') == 'Мой метан'
        assert 'Мой метан' in str(window.preferences.value(fragment_actions.MOLECULES_KEY))
        titles = [a.text() for a in window.model_menu_tool.molecule_menu().actions()]
        group = next(a.menu() for a in window.model_menu_tool.molecule_menu().actions() if a.text() == 'Мои молекулы')
        assert [a.text() for a in group.actions()] == ['Мой метан'] and 'Сохранить молекулу в «Мои молекулы»…' in titles
        tool.fill_user_molecules_menu(window.user_molecules_menu)
        assert window.user_molecules_menu.actions()[0].text() == 'Мой метан'
        window.new_molecule()
        window.dirty = False
        assert tool.open_user_molecule('Мой метан') and window.molecule.formula == 'CH4'
        assert any(a.text() == 'Сохранить молекулу в «Мои молекулы»…' for a in window.model_menu_tool.atom_menu(0).actions())
        tool.build_molecule_store()  # read back from the settings
        assert list(user_molecules.USER) == ['Мой метан']
        assert tool.delete_user_molecule('Мой метан', ask=False) and not user_molecules.USER
    finally:
        user_molecules.register(saved)
        if before is None:
            window.preferences.remove(fragment_actions.MOLECULES_KEY)
        else:
            window.preferences.setValue(fragment_actions.MOLECULES_KEY, before)


def test_the_view_mode_has_its_button(window, app):
    show_model(window, app)
    window.choose_view_mode()
    assert window.view_button.isChecked() and window.build_mode.currentData() == 'view'
    assert window.view_button.property('quail_icon') == 'select'
    window.edit_toggle.click()
    assert window.build_mode.currentData() != 'view' and not window.view_button.isChecked()
    window.view_button.click()
    assert window.build_mode.currentData() == 'view' and window.view_button.isChecked() and not window.edit_toggle.isChecked()
    window.view_button.click()  # pressed again: it stays on
    assert window.build_mode.currentData() == 'view' and window.view_button.isChecked()
    window.move_button.click()
    assert window.build_mode.currentData() == 'move' and not window.view_button.isChecked()
    window.choose_view_mode()


def test_the_edit_menu_adds_a_molecule(window, app):
    edit = next(a.menu() for a in window.menuBar().actions() if a.text() == 'Правка')
    titles = [a.text() for a in edit.actions()]
    assert 'Добавить молекулу' in titles and 'Сохранить молекулу в «Мои молекулы»…' in titles
    window.add_molecule()
    assert window.build_mode.currentData() == 'molecule'
    window.choose_view_mode()


def test_the_settings_open_wide_enough_for_their_sections(window):
    dialog = window.show_settings()
    try:
        body = dialog.scroll.widget()
        assert dialog.width() >= max(560, body.sizeHint().width())
    finally:
        dialog.close()


def test_a_second_press_on_a_button_of_compass_closes_its_menu(window):
    # Windows of the owner (2026-11-24): the press that closed a menu of a button above the model reached the button and
    # opened the menu again — menu_actions._popup watches the button (hub.header.MenuToggle)
    from PySide6.QtWidgets import QMenu

    from hub.header import MenuToggle

    class Quiet(QMenu):
        def exec(self, *args):  # not shown: the test has no one to close it
            return None

    menu = Quiet()
    menu.addAction('Метил')
    window.model_menu_tool._popup(window.fragment_button, menu)
    assert menu.property('azimuthToggle')
    menu.aboutToHide.emit()
    assert MenuToggle._filter.just_closed(window.fragment_button)
