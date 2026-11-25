"""The windows «Стиль подписей…», «Стиль измерений…», «Стиль векторов и плоскостей…»
(modules/compass/actions/style_form.py) and the drawing of what they keep."""

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QAbstractSpinBox

from tests.gui_support import *  # noqa: F401,F403 — the fixtures app, window and the helpers


def test_the_styles_of_labels_measurements_and_guides(window, app, monkeypatch):
    # 2026-11-17
    from PySide6.QtWidgets import QColorDialog, QComboBox

    from azimuth import defaults
    from modules.compass.actions import style_form as sf

    tool = window.structure_tool
    kept = {k: defaults.get(k) for k in tool.LABEL_STYLE + tool.MEASURE_STYLE + tool.GUIDE_STYLE}
    try:
        # the values kept, the wrong ones not
        got = tool.label_style({'label_font': 'Courier', 'label_italic': True, 'label_color': '#112233',
                                'label_place': 'beside', 'label_outline': True, 'measure_size': 20})
        assert got == {'label_font': 'Courier', 'label_italic': True, 'label_color': '#112233',
                       'label_place': 'beside', 'label_outline': True}  # a key of another window is not taken
        assert tool.label_style({'label_place': 'under', 'label_color': 'pink'}) == {'label_place': 'centre',
                                                                                    'label_color': ''}
        assert tool.label_style({'label_font': 'x\n' * 3})['label_font'] == ''  # not a name of a font
        got = tool.measure_style({'measure_color': '#aa0000', 'measure_line_color': '#00aa00', 'measure_plate': False,
                                  'measure_bold': True, 'measure_font': 'Courier'})
        assert got['measure_plate'] is False and got['measure_line_color'] == '#00aa00'
        window.viewer.show_lengths = True
        window.viewer.grab()  # drawn with all of them (the label beside, outlined; the numbers without a plate)
        # the windows: the colours in circles with ↺, the numbers in the middle of their fields
        for open_window, name in ((tool.label_style, '_label_style_box'), (tool.measure_style, '_measure_style_box'),
                                  (tool.guide_style, '_guide_style_box')):
            box = open_window()
            assert getattr(tool, name) is box and box.isVisible()
            # a window with its title bar (application-modal), not a sheet of macOS (window-modal)
            assert box.windowModality() == Qt.WindowModality.ApplicationModal
            dots = box.findChildren(sf.ColourDot)
            assert dots and all(d.circle.width() == d.circle.height() for d in dots)
            for field in box.findChildren(QAbstractSpinBox):
                assert field.alignment() & Qt.AlignmentFlag.AlignCenter
            box.reject()
        assert len(tool.guide_style().findChildren(sf.ColourDot)) == 3
        tool._guide_style_box.reject()
        # the picker of Qt (in the theme of the program), not the dark one of macOS
        asked = []
        # the window is made by pick_colour itself (laid out anew) — its exec answers here, not the user
        from PySide6.QtWidgets import QDialog

        monkeypatch.setattr(QColorDialog, 'exec', lambda self: (
            asked.append(QColorDialog.ColorDialogOption.DontUseNativeDialog
                         if self.testOption(QColorDialog.ColorDialogOption.DontUseNativeDialog) else None),
            QDialog.DialogCode.Accepted)[1])
        monkeypatch.setattr(QColorDialog, 'selectedColor', lambda self: QColor('#123456'))
        dot = sf.ColourDot('', lambda: '#2aa198', 'tip')
        assert not dot.reset.isEnabled() and dot.shown() == '#2aa198'
        dot.choose()
        assert dot.value == '#123456' and dot.reset.isEnabled()
        assert asked == [QColorDialog.ColorDialogOption.DontUseNativeDialog]
        dot.reset.click()  # ↺ — the colour of the program again
        assert dot.value == '' and not dot.reset.isEnabled()
        box = sf.font_box('')
        assert isinstance(box, QComboBox) and sf.family_of(box) == '' and box.count() > 1
    finally:
        tool._keep_styles(kept)


def test_the_style_and_the_types_of_bonds(window, app, monkeypatch):
    # «Стиль связей…», the type and the colour of a bond in its menu, the long bonds dashed
    from dataclasses import replace

    from azimuth import defaults
    from modules.compass.actions import style_form as sf
    from modules.compass.chemistry import library
    from modules.compass.view.bond_depth import model_scene
    from modules.compass.view.viewer import remap_bond_marks

    tool = window.structure_tool
    kept = {k: defaults.get(k) for k in tool.BOND_STYLE}
    view = (window.viewer.bond_color, window.viewer.bond_width, window.viewer.multiple_bonds)
    try:
        window.load_molecule(library.molecule(next(k for k in library.keys() if k.startswith('Бензол'))))
        got = tool.bond_style({'bond_color': 'uniform', 'bond_width': 1.4, 'bond_uniform_color': '#aa5500',
                               'bond_aromatic_style': 'double', 'hbond_style': 'solid', 'label_place': 'beside'})
        assert got == {'bond_uniform_color': '#aa5500', 'bond_aromatic_style': 'double', 'hbond_style': 'solid'}
        assert window.viewer.bond_color == 'uniform' and window.viewer.bond_width == 1.4
        assert window.bond_color_actions['uniform'].isChecked()  # the menu follows
        box = tool.bond_style()
        assert tool._bond_style_box is box and len(box.findChildren(sf.ColourDot)) == 3
        # every group with its heading — the first too — in a frame of its own
        from PySide6.QtWidgets import QGroupBox

        assert [g.title() for g in box.findChildren(QGroupBox)] == ['Все связи', 'Типы связей', 'Водородные связи']
        box.reject()
        # the menu of a bond: aromatic, partial, a colour of its own; over the atoms selected, all their bonds
        from modules.compass.chemistry.builder import connections

        tools = window.model_menu_tool
        a, b = next((i, j) for i, j, _ in connections(window.molecule)
                    if window.molecule.atoms[i].symbol == 'C' and window.molecule.atoms[j].symbol == 'C')
        assert tools.mark_bonds(a, b, kind='aromatic') == [(min(a, b), max(a, b))]
        window.viewer.set_selection([k for k, atom in enumerate(window.molecule.atoms) if atom.symbol == 'C'])
        assert len(tools.mark_bonds(a, b, kind='partial')) == 6  # the ring
        tools.mark_bonds(a, b, color='#00aa00')
        assert all(m == {'kind': 'partial', 'color': '#00aa00'} for m in window.viewer.bond_marks.values())
        monkeypatch.setattr(sf, 'pick_colour', lambda *args: '#0000ff')
        assert tools.colour_bonds(a, b) == '#0000ff'
        window.viewer.resize(500, 400)
        spheres, rods = model_scene(window.viewer, window.viewer.projected(), {}, 1.0)
        assert len(rods) > 12 and window.viewer.grab() is not None  # the ring dashed
        tools.mark_bonds(a, b, kind='', color='')
        assert not window.viewer.bond_marks
        # the marks follow the atoms through an edit; the long bonds dashed
        moved = remap_bond_marks(window.molecule, window.molecule, {(0, 1): {'kind': 'aromatic'}})
        assert moved == {(0, 1): {'kind': 'aromatic'}}
        bonds = len(connections(window.molecule))
        stretched = replace(window.molecule, atoms=tuple(
            replace(atom, x=atom.x * 1.4, y=atom.y * 1.4, z=atom.z * 1.4) for atom in window.molecule.atoms),
            bonds=tuple(connections(window.molecule)))
        window.viewer.set_selection([])
        tool.bond_style({'bond_long_dashed': True, 'bond_long_factor': 1.1, 'bond_color': 'smooth'})
        window.load_molecule(stretched)
        spheres, rods = model_scene(window.viewer, window.viewer.projected(), {}, 1.0)
        assert len(rods) > bonds * 2  # every bond 1.4 times longer: dashed
    finally:
        for key, value in kept.items():
            defaults.put(key, value)
        tool.set_view_option('bond_color', view[0])
        tool.set_view_option('bond_width', view[1])
        tool.set_view_option('multiple_bonds', view[2])
        window.viewer.bond_marks = {}
        window.dirty = False
        for d in window.all_documents():
            d.dirty = False


def test_the_field_slides_as_one_picture(window):
    # while a panel slides, a picture of the field taken at its start
    # lies over it and follows the model; the field itself is drawn again once, when the panel stops
    viewer = window.viewer
    if not viewer.isVisible() or not viewer.molecule or not viewer.molecule.atoms:
        window.show()
        QTest.qWait(50)
    assert viewer.isVisible() and viewer.molecule.atoms
    viewer.begin_glide()
    try:
        cover = viewer._glide_cover
        assert viewer.gliding() and cover is not None and cover.isVisible() and cover.geometry() == viewer.rect()
        viewer.resize(viewer.width() - 40, viewer.height())
        assert cover.geometry() == viewer.rect()  # it follows the field
        cover.grab()  # drawn: the picture moved and scaled to the model
        viewer.begin_glide()  # a second start keeps the first picture
        assert viewer._glide_cover is cover
    finally:
        viewer.end_glide()
    assert not viewer.gliding() and viewer._glide_cover is None
    viewer.end_glide()  # nothing to end: no harm


def test_the_scales_and_the_glyphs_are_not_drawn_anew_while_a_panel_slides(app):
    # the view panel slides smoothly: the ornament and the button glyphs are not redrawn on every frame
    from PySide6.QtCore import QSize
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QWidget

    from azimuth.icons import GlyphEngine
    from azimuth.ui import freeze_ornaments
    from hub.chrome import Ornament

    engine = GlyphEngine('rotate-x-plus')
    first = engine.scaledPixmap(QSize(21, 21), QIcon.Mode.Normal, QIcon.State.Off, 2.0)
    assert engine.scaledPixmap(QSize(21, 21), QIcon.Mode.Normal, QIcon.State.Off, 2.0).cacheKey() == first.cacheKey()
    page = QWidget()
    page.resize(600, 400)
    ornament = Ornament(page)
    ornament.setGeometry(page.rect())
    page.show()
    try:
        freeze_ornaments(page)
        assert ornament._frozen is not None and ornament._frozen[0] == ornament.size()
        ornament.grab()  # drawn from the picture
        freeze_ornaments(page, False)
        assert ornament._frozen is None
    finally:
        page.close()


def test_the_snapshot_and_the_results_stand_in_a_column_at_the_edge_of_the_field(window):
    rail = window.tool_rail
    # the chevron of the view panel and the snapshot button keep their places, with the panel folded too
    inside = [b for b in (window.screenshot_button, window.clear_overlays_button, *window.property_buttons.values())]
    assert all(rail.isAncestorOf(b) for b in inside)
    assert window.compare_button.isHidden()
    window.crystal_tool.update_panel('molecule')
    assert window.compare_button.isHidden()  # not brought back by the panel of the molecule
    def holding(layout):
        if layout.indexOf(window.viewer) >= 0:
            return layout
        for k in range(layout.count()):
            inner = layout.itemAt(k).layout()
            found = holding(inner) if inner is not None else None
            if found is not None:
                return found
        return None

    canvas = holding(window.viewer.parentWidget().layout())
    order = [canvas.itemAt(k).widget() for k in range(canvas.count()) if canvas.itemAt(k).widget() is not None]
    assert order.index(window.viewer) < order.index(window.view_panel) < order.index(rail)  # the panel between
    assert not rail.isAncestorOf(window.view_panel_toggle)
    menus = [a.menu() for a in window.menuBar().actions() if a.menu()]
    assert any(window.compare_menu in [a.menu() for a in m.actions()] for m in menus)  # «Вид → Сравнение структур»


def test_the_user_puts_menu_items_on_the_panels_of_compass(window):
    from modules.compass.actions import custom_bar as cb

    bar = window.custom_bar
    try:
        items = list(bar.items())
        assert items and all('/' in key for key, _, _ in items)
        key, action, _ = next((k, a, s) for k, a, s in items if k.startswith('Вид/') and s is None and a.isEnabled())
        assert bar.key_of(action) == key and bar.find(key)[0] is action
        before = len(bar.groups()[cb.TOP])
        bar.add(key, cb.TOP)  # a group of its own, a line before it
        assert bar.groups()[cb.TOP][-1] == [key] and len(bar.groups()[cb.TOP]) == before + 1
        assert bar.areas[cb.TOP].indexOf(bar.buttons[key]) >= 0
        bar.add(key, cb.RAIL)  # moved: in the column, not in the row
        assert bar.where(key) == cb.RAIL and bar.areas[cb.RAIL].indexOf(bar.buttons[key]) >= 0
        menu_key = next(k for k, a, s in items if s is not None)
        bar.add(menu_key, cb.TOP)  # a submenu as a button
        assert bar.buttons[menu_key].toolTip().endswith('▸')
        bar.remove('default:lock')  # a button from the start taken away
        assert window.lock_button.isHidden() and window.lock_button.property('azimuthAway')
        window.crystal_tool.update_panel('molecule')
        assert window.lock_button.isHidden()  # the panel of the molecule does not bring it back
        bar.remove(key)
        assert key not in bar.buttons and bar.where(key) is None
        bar.add('Нет/такого/пункта', cb.TOP)  # an item gone from the menus: no button, no error
        assert 'Нет/такого/пункта' not in bar.buttons
        for area in bar.areas.values():  # never two lines in a row, none at an end
            shown = [area.itemAt(k).widget() for k in range(area.count())]
            shown = [w for w in shown if w is not None and not w.isHidden()]
            rules = [bool(w.property('azimuthBarRule')) for w in shown]
            assert not (rules and (rules[0] or rules[-1])) and not any(a and b for a, b in zip(rules, rules[1:]))
    finally:
        bar.reset()
    assert not window.lock_button.isHidden() and not bar.buttons
    assert bar.groups()[cb.TOP] == bar.default_groups[cb.TOP]


def test_a_button_is_dragged_into_a_group_or_after_the_last_line(window):
    from PySide6.QtCore import QPoint

    from modules.compass.actions import custom_bar as cb

    bar = window.custom_bar
    try:
        window.show()
        bar.move('default:lock', ('new', cb.RAIL))  # to the end of the column: a group of its own
        assert bar.groups()[cb.RAIL][-1] == ['default:lock']
        bar.move('default:lock', ('into', cb.RAIL, 'default:atoms', 'default:bonds'))  # among the results
        assert bar.groups()[cb.RAIL][-1] == ['default:atoms', 'default:lock', 'default:bonds', 'default:vectors',
                                             'default:clear']
        bar.move('default:clear', ('new', cb.TOP))
        bar.move('default:clear', ('into', cb.RAIL, 'default:atoms', None))  # and back to the end of its group
        rail = bar.groups()[cb.RAIL]
        assert rail[-1][-1] == 'default:clear' and len(rail) == 2  # no group, no line left behind
        app_rail = bar.rail_widget
        below = app_rail.mapTo(bar.card, QPoint(app_rail.width() // 2, app_rail.height() - 5))
        assert bar.slot(below) == ('new', cb.RAIL)  # under the last button: after a new line
        atoms = window.property_buttons['atoms']
        on_atoms = atoms.mapTo(bar.card, QPoint(atoms.width() // 2, 2))
        assert bar.slot(on_atoms) == ('into', cb.RAIL, 'default:atoms', 'default:atoms')
        assert bar.slot(QPoint(-50, -50)) is None
    finally:
        bar.reset()
    assert bar.groups()[cb.RAIL] == bar.default_groups[cb.RAIL]


def test_the_neighbours_move_apart_where_a_dragged_button_will_stand(window):
    # a gap with a pale copy opens at the place, the gap of a place left closes; all gone when the drag ends
    from PySide6.QtTest import QTest

    from modules.compass.actions import custom_bar as cb

    bar = window.custom_bar
    window.show()
    rail = bar.areas[cb.RAIL]
    bonds = window.property_buttons['bonds']
    before = rail.indexOf(bonds)
    bar._ghost_picture = window.lock_button.grab()
    try:
        bar.show_slot(('into', cb.RAIL, 'default:atoms', 'default:bonds'))
        gap = bar._gap[1]
        assert rail.indexOf(gap) == before and rail.indexOf(bonds) == before + 1  # opened right before «Связи»
        # the glide takes GLIDE_MS on a free computer; on a busy one (the full run in six processes) the animation
        # had not moved yet after GLIDE_MS + 100 — the height was 0 twice on 2026-11-22. Waited for, up to 5 s
        import time

        end = time.monotonic() + 5.0
        QTest.qWait(bar.GLIDE_MS + 100)
        while gap.height() <= 20 and time.monotonic() < end:
            QTest.qWait(50)
        assert gap.height() > 20  # grown: the buttons under it moved down
        bar.show_slot(('new', cb.TOP))  # another place: this gap opens, the first closes
        QTest.qWait(bar.GLIDE_MS + 100)
        assert bar.areas[cb.TOP].indexOf(bar._gap[1]) == bar.areas[cb.TOP].count() - 1
        assert rail.indexOf(bonds) == before  # the first gap gone
    finally:
        bar._ghost_picture = None
        bar.show_slot(None, at_once=True)
    assert getattr(bar, '_gap', None) is None
    assert not any(bar.areas[p].itemAt(k).widget().property('azimuthBarGap')
                   for p in (cb.TOP, cb.RAIL) for k in range(bar.areas[p].count()) if bar.areas[p].itemAt(k).widget())


def test_no_gap_where_the_dragged_button_already_stands(window):
    from modules.compass.actions import custom_bar as cb

    bar = window.custom_bar
    window.show()
    bar._ghost_picture = window.lock_button.grab()
    bar._dragged = 'default:bonds'
    try:
        for slot in (('into', cb.RAIL, 'default:atoms', 'default:bonds'),  # right before itself
                     ('into', cb.RAIL, 'default:atoms', 'default:vectors')):  # right after itself
            assert bar.moved('default:bonds', slot) is None
            bar.show_slot(slot)
            assert getattr(bar, '_gap', None) is None
        bar.show_slot(('into', cb.RAIL, 'default:atoms', 'default:clear'))  # elsewhere: the gap opens
        assert bar._gap is not None
    finally:
        bar._ghost_picture = bar._dragged = None
        bar.show_slot(None, at_once=True)


def test_a_line_parts_a_group_and_is_taken_away(window):
    from modules.compass.actions import custom_bar as cb

    bar = window.custom_bar
    try:
        bar.split('default:bonds', False)  # a line before «Связи»
        assert bar.groups()[cb.RAIL] == [['default:snapshot'], ['default:atoms'],
                                         ['default:bonds', 'default:vectors', 'default:clear']]
        bar.split('default:bonds', True)  # and after it: «Связи» stands apart
        assert ['default:bonds'] in bar.groups()[cb.RAIL] and len(bar.groups()[cb.RAIL]) == 4
        bar.join('default:bonds', False)  # the line before it taken away
        assert bar.groups()[cb.RAIL][1] == ['default:atoms', 'default:bonds']
        bar.split('default:snapshot', False)  # nothing to part at the edge of a group
        assert len(bar.groups()[cb.RAIL]) == 3
        lines = [w for w in (bar.areas[cb.RAIL].itemAt(k).widget() for k in range(bar.areas[cb.RAIL].count()))
                 if w is not None and w.property('azimuthBarRule')]
        assert len(lines) == 2
    finally:
        bar.reset()


def test_a_menu_item_is_dragged_onto_a_panel(window, monkeypatch):
    # drag_item — the menus
    # close, the button the item will make is carried; a drop on the row puts it there as a group of its own
    from PySide6.QtCore import Qt

    from modules.compass.actions import custom_bar as cb

    bar = window.custom_bar
    window.show()
    key, action, sub = next((k, a, s) for k, a, s in bar.items() if k.startswith('Вид/') and s is None and a.isEnabled())
    carried = []

    def dropped(drag):
        carried.append(drag.pixmap().isNull())
        assert bar._dragged == key and bar._ghost_picture is not None  # the pale copy for the gap
        bar.move(key, ('new', cb.TOP))
        return Qt.DropAction.CopyAction

    monkeypatch.setattr(bar, 'exec_drag', dropped)
    try:
        bar.drag_item(key, action, sub)
        assert carried == [False] and bar.where(key) == cb.TOP and bar.groups()[cb.TOP][-1] == [key]
        assert bar._dragged is None and bar._ghost_picture is None
    finally:
        bar.reset()


def test_on_macos_an_item_is_carried_by_its_menu_itself(window, monkeypatch):
    # the drag of the system started from a menu reached the column at the right never. On macOS the menu that took the
    # press carries the item: it keeps the mouse, turns invisible, a picture follows the cursor, the gap opens, the
    # release puts the button there and closes the menus; the release triggers no item of the menu
    from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtWidgets import QApplication, QMenu

    from modules.compass.actions import custom_bar as cb

    bar = window.custom_bar
    window.show()
    monkeypatch.setattr(cb.CustomBar, 'CARRY_IN_MENU', True)
    key, action, _ = next((k, a, s) for k, a, s in bar.items() if k.startswith('Вид/') and s is None and a.isEnabled()
                          and not a.isCheckable() and bar.already(k, a) is None)
    fired = []
    action.triggered.connect(lambda *_: fired.append(1))
    menu = QMenu(window)
    menu.addAction(action)
    menu.popup(QPoint(40, 40))
    QApplication.processEvents()
    centre = QPointF(menu.actionGeometry(action).center())
    left = Qt.MouseButton.LeftButton
    rail = bar.rail_widget
    target = rail.mapToGlobal(QPoint(rail.width() // 2, rail.height() - 4))  # the end of the column at the right

    def mouse(kind, local, button, buttons, at=None):
        where = at if at is not None else menu.mapToGlobal(local.toPoint())
        return QMouseEvent(kind, local, QPointF(where), button, buttons, Qt.KeyboardModifier.NoModifier)

    try:
        bar.clicks.eventFilter(menu, mouse(QEvent.Type.MouseButtonPress, centre, left, left))
        assert bar.clicks.eventFilter(menu, mouse(QEvent.Type.MouseMove, centre + QPointF(40, 0), Qt.MouseButton.NoButton,
                                                  left))
        assert bar.carrying(menu) and menu.isVisible() and menu.windowOpacity() == 0.0
        assert bar.clicks.eventFilter(menu, mouse(QEvent.Type.MouseMove, QPointF(-500, 300), Qt.MouseButton.NoButton,
                                                  left, target))
        assert bar._gap is not None and bar._gap[0] == ('new', cb.RAIL)  # the gap opened at the end of the column
        assert bar.clicks.eventFilter(menu, mouse(QEvent.Type.MouseButtonRelease, QPointF(-500, 300), left,
                                                  Qt.MouseButton.NoButton, target))
        assert not bar.carrying() and bar.where(key) == cb.RAIL and not fired
        assert QApplication.activePopupWidget() is None
    finally:
        menu.close()
        bar.reset()


def test_a_line_parts_a_button_put_on_a_panel(window):
    # a button just made is «hidden» to Qt until the event
    # loop shows it — the line before it was taken for a line at the end and hidden; the same at the start, between
    # «Снимок» and the results in the column at the right
    from modules.compass.actions import custom_bar as cb

    bar = window.custom_bar
    window.show()
    key = next(k for k, a, s in bar.items() if k.startswith('Вид/') and s is None and a.isEnabled())
    try:
        bar.add(key, cb.RAIL)
        rail = bar.areas[cb.RAIL]
        entries = [rail.itemAt(k).widget() for k in range(rail.count())]
        entries = [w for w in entries if w is not None]
        at = entries.index(bar.buttons[key])
        assert entries[at - 1].property('azimuthBarRule') and not entries[at - 1].isHidden()
        snapshot = entries.index(bar.defaults['default:snapshot'])
        assert entries[snapshot + 1].property('azimuthBarRule') and not entries[snapshot + 1].isHidden()
    finally:
        bar.reset()


def test_an_item_already_on_a_panel_is_not_added_twice(window, monkeypatch):
    # the same item, or one
    # whose glyph a button of a panel shows (every function has its own glyph), is refused with a message
    from PySide6.QtCore import QEvent, QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtWidgets import QMenu

    from azimuth.button_icons import icon_name
    from modules.compass.actions import custom_bar as cb

    bar = window.custom_bar
    window.show()
    said, dragged = [], []
    monkeypatch.setattr(window, 'notify', lambda text, ms=8000: said.append(text))
    monkeypatch.setattr(bar, 'drag_item', lambda k, a, s: dragged.append(k))
    key, action, _ = next((k, a, s) for k, a, s in bar.items() if k.startswith('Вид/') and s is None and a.isEnabled()
                          and bar.already(k, a) is None)
    try:
        bar.add(key, cb.RAIL)
        assert bar.already(key, action) == (key, cb.RAIL)
        menu = QMenu(window)
        menu.addAction(action)
        menu.ensurePolished()
        menu.adjustSize()
        centre = QPointF(menu.actionGeometry(action).center())
        left = Qt.MouseButton.LeftButton

        def mouse(kind, point, button, buttons):
            return QMouseEvent(kind, point, menu.mapToGlobal(point), button, buttons, Qt.KeyboardModifier.NoModifier)

        bar.clicks.eventFilter(menu, mouse(QEvent.Type.MouseButtonPress, centre, left, left))
        assert bar.clicks.eventFilter(menu, mouse(QEvent.Type.MouseMove, centre + QPointF(40, 0), Qt.MouseButton.NoButton,
                                                  left))
        assert not dragged and said == ['Эта кнопка уже есть в колонке справа']
        # a button from the start with the same glyph: «the same function» — refused as well
        twin = next(((k, a) for k, a, s in bar.items() if s is None and icon_name(a.text().replace('&', ''))
                     in {w.property('quail_icon') for w in bar.defaults.values() if not w.isHidden()}), None)
        if twin is not None:
            assert bar.already(*twin) is not None and bar.already(*twin)[0].startswith('default:')
    finally:
        bar.reset()


def test_the_picture_carried_out_of_a_menu_has_the_square_of_a_button(window, monkeypatch):
    # the picture is that of a button of the panel under the mouse — the square of its hover around the glyph
    from PySide6.QtCore import Qt

    bar = window.custom_bar
    window.show()
    key, action, sub = next((k, a, s) for k, a, s in bar.items() if k.startswith('Вид/') and s is None and a.isEnabled())
    pictures = []
    monkeypatch.setattr(bar, 'exec_drag', lambda drag: pictures.append(drag.pixmap().toImage()) or Qt.DropAction.IgnoreAction)
    try:
        bar.drag_item(key, action, sub)
    finally:
        bar.reset()
    image = pictures[0]
    corner = image.pixelColor(image.width() // 2, 2)  # inside the square, above the glyph
    assert corner.alpha() > 0


def test_the_crystal_has_a_panel_of_its_own(window):
    # «Компас · Кристалл» lays its own groups — the cell, the tools and the Hirshfeld surface, no constraints
    # and no dipole; a button taken off it stays on the molecule panel and the other way round
    from modules.compass.actions import custom_bar as cb

    bar = window.custom_bar
    window.crystal_tool.set_compass_mode('molecule')
    molecule = bar.groups()
    keys = {k for g in molecule[cb.TOP] + molecule[cb.RAIL] for k in g}
    assert 'default:cell' not in keys and not any(k.startswith('default:crystal-') for k in keys)
    try:
        window.show()
        window.crystal_tool.set_compass_mode('crystal')
        assert bar.groups()[cb.TOP] == bar.default_groups[cb.TOP] and bar.layout_key() == cb.LAYOUT + '_crystal'
        assert ['default:crystal-2', 'default:crystal-5', 'default:crystal-3'] in bar.groups()[cb.TOP]
        assert window.hirshfeld_button.isVisibleTo(window) and window.contacts_button.isVisibleTo(window)
        assert not window.lock_button.isVisibleTo(window) and not window.property_buttons['vectors'].isVisibleTo(window)
        bar.remove('default:crystal-3')
        assert not window.powder_button.isVisibleTo(window)
        window.crystal_tool.set_compass_mode('molecule')
        assert bar.groups() == molecule and window.lock_button.isVisibleTo(window)
        assert not window.hirshfeld_button.isVisibleTo(window)
        window.crystal_tool.set_compass_mode('crystal')
        assert bar.where('default:crystal-3') is None and not window.powder_button.isVisibleTo(window)
        bar.reset()
        assert window.powder_button.isVisibleTo(window)
    finally:
        window.crystal_tool.set_compass_mode('crystal')
        bar.reset()
        window.crystal_tool.set_compass_mode('molecule')
    assert bar.groups() == molecule
