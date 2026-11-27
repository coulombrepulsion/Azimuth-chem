"""CompassWorkspace: module-owned pages and operations. Contract: docs/MODULES.md."""

from dataclasses import replace
from math import radians
from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QFrame, QTableWidgetItem
from modules.compass.panels.periodic import PeriodicTable
from azimuth.icons import iconify
from azimuth.controls import HoldButton
from modules.compass.chemistry.transforms import bond_side, rotate_atoms, stretch_bond, set_measurement
from modules.compass.chemistry.geometry_tools import BOHR, measurement
from modules.compass.chemistry.builder import connections, delete_atoms
from modules.compass.chemistry import library
from modules.compass.chemistry.editing import add_hydrogens

from azimuth import i18n
from azimuth.i18n import tr
from modules.compass.panels.layout import StructurePage
from modules.compass.panels.documents import DocumentActions
from modules.compass import workspace_notices as _notices
from modules.compass import workspace_building as _building
from modules.compass import workspace_molecules as _molecules


def LANG_CODE():
    return i18n.LANG


EXAMPLE_TITLES = library.titles()  # the teaching examples and the library
SUBSCRIPTS = str.maketrans('0123456789', '₀₁₂₃₄₅₆₇₈₉')


class CompassWorkspace(
    StructurePage,
    DocumentActions,
):
    """Compass operations shared by the Studio window. Two mixins are left — the layout of the page
    (StructurePage, it builds the widgets of the window) and the tabs of the documents (DocumentActions); every other
    part is a part of its own with a PORT (the properties *_tool below, azimuth/window_port.py); see docs/MODULES.md."""

    _iupac = None  # the IUPAC name of the document (naming_tool reads and writes it, documents.py keeps it)

    def _tool(self, name, module, cls):
        """A part of the window made once from its class (it gets the window and reaches it only through the
        names of its PORT — azimuth/window_port.py)."""
        tool = self.__dict__.get('_' + name)
        if tool is None:
            import importlib

            tool = self.__dict__['_' + name] = getattr(importlib.import_module(module), cls)(self)
        return tool

    picture_tool = property(lambda self: self._tool('picture_tool', 'modules.compass.actions.pictures', 'PictureTool'))
    naming_tool = property(lambda self: self._tool('naming_tool', 'modules.compass.actions.naming_actions', 'NamingTool'))
    symmetry_tool = property(lambda self: self._tool('symmetry_tool', 'modules.compass.actions.symmetry_actions',
                                                     'SymmetryTool'))
    selection_tool = property(lambda self: self._tool('selection_tool', 'modules.compass.actions.selection_actions',
                                                      'SelectionTool'))
    fragment_tool = property(lambda self: self._tool('fragment_tool', 'modules.compass.actions.fragment_actions',
                                                     'FragmentTool'))
    # five more parts of their own — the steps of a result, the overlay for comparison, the display schemes,
    # the crystals, the view (its panel, the standard views, the Z-matrix, the engine)
    trajectory_tool = property(lambda self: self._tool('trajectory_tool', 'modules.compass.actions.trajectory_actions',
                                                       'TrajectoryTool'))
    overlay_tool = property(lambda self: self._tool('overlay_tool', 'modules.compass.actions.overlay_actions',
                                                    'OverlayTool'))
    scheme_tool = property(lambda self: self._tool('scheme_tool', 'modules.compass.actions.scheme_actions', 'SchemeTool'))
    crystal_tool = property(lambda self: self._tool('crystal_tool', 'modules.compass.actions.crystal_actions',
                                                    'CrystalTool'))
    view_tool = property(lambda self: self._tool('view_tool', 'modules.compass.actions.view_actions', 'ViewTool'))
    # and five more — the surfaces and fields, the properties of a result, the opening of files, «Файл»
    # (recent files, saving many), the menus of the structure (as in Chemcraft)
    surface_tool = property(lambda self: self._tool('surface_tool', 'modules.compass.actions.surface_actions', 'SurfaceTool'))
    property_tool = property(lambda self: self._tool('property_tool', 'modules.compass.actions.property_actions',
                                                     'PropertyTool'))
    opening_tool = property(lambda self: self._tool('opening_tool', 'modules.compass.actions.opening_actions', 'OpeningTool'))
    file_tool = property(lambda self: self._tool('file_tool', 'modules.compass.actions.file_actions', 'FileTool'))
    structure_tool = property(lambda self: self._tool('structure_tool', 'modules.compass.actions.structure_actions',
                                                      'StructureTool'))
    # the table of the coordinates, the menus of the model, the panel of the density, the calculation tools
    coordinate_tool = property(lambda self: self._tool('coordinate_tool', 'modules.compass.actions.coordinate_actions',
                                                       'CoordinateTool'))
    model_menu_tool = property(lambda self: self._tool('model_menu_tool', 'modules.compass.actions.menu_actions',
                                                       'ModelMenuTool'))
    density_tool = property(lambda self: self._tool('density_tool', 'modules.compass.panels.density_drawer',
                                                    'DensityDrawerTool'))
    calculation_tool = property(lambda self: self._tool('calculation_tool', 'modules.compass.actions.calculation_tools',
                                                        'CalculationTool'))
    ENGINE_KEY = 'compass_engine'  # as ViewTool.ENGINE_KEY (app.py, the tests read it on the window)

    @property
    def constraint_tool(self):
        """The constraints of optimization — a part of its own (actions/constraint_actions.ConstraintTool)
        with its port, instead of a mixin; made once."""
        tool = self.__dict__.get('_constraint_tool')
        if tool is None:
            from modules.compass.actions.constraint_actions import ConstraintPort, ConstraintTool

            tool = self.__dict__['_constraint_tool'] = ConstraintTool(ConstraintPort(
                items=lambda: self.constraints, selected=lambda: list(self.viewer.selected),
                molecule=lambda: self.molecule, notify=lambda text, ms: self.notify(text, ms),
                changed=lambda: self.constraints_changed(), parent=self))
        return tool

    @property
    def compass_dialogs(self):
        """The openers of the windows of the path, the rotation about a bond and the conformers
        (actions/dialog_openers.DialogOpeners) with their port, instead of three mixins; made once. The
        port calls the methods of the window when it is used (lambda), not the ones bound when it was made — an
        error or a message replaced later (a test, a subclass) is the one called, as with the mixin."""
        tool = self.__dict__.get('_compass_dialogs')
        if tool is None:
            from modules.compass.actions.dialog_openers import DialogOpeners, DialogPort

            tool = self.__dict__['_compass_dialogs'] = DialogOpeners(DialogPort(
                parent=self, molecule=lambda: self.coordinate_tool.table_molecule(), selected=lambda: list(self.viewer.selected),
                browsing=lambda: getattr(self, 'browsing', False), stop_browsing=lambda: self.trajectory_tool.set_trajectory_open(False),
                notify=lambda text, ms: self.notify(text, ms), error=lambda exc: self.error(exc),
                keep=lambda name, window: setattr(self, name, window),
                kept=lambda name: getattr(self, name, None),
                crystal=lambda: getattr(self, 'compass_mode', 'molecule') == 'crystal'))
        return tool

    @property
    def protein_tool(self):
        """The ribbon of a protein and the peptide builder (actions/protein_actions.ProteinTool) with their
        port, instead of a mixin; made once (its actions: ribbon_action, peptide_action of the menus)."""
        tool = self.__dict__.get('_protein_tool')
        if tool is None:
            from modules.compass.actions.protein_actions import ProteinPort, ProteinTool

            tool = self.__dict__['_protein_tool'] = ProteinTool(ProteinPort(
                parent=self, viewer=lambda: self.viewer, molecule=lambda: self.coordinate_tool.table_molecule(),
                notify=lambda text, ms: self.notify(text, ms), error=lambda exc: self.error(exc),
                confirm_replace=lambda: self.confirm_replace() if hasattr(self, 'confirm_replace') else True,
                edit_structure=lambda molecule, note: self.model_menu_tool.edit_structure(molecule, note)))
        return tool

    @property
    def coordination_tool(self):
        """«Координационный центр…» (actions/coordination_actions.CoordinationTool) with its port; made once."""
        tool = self.__dict__.get('_coordination_tool')
        if tool is None:
            from modules.compass.actions.coordination_actions import CoordinationPort, CoordinationTool

            tool = self.__dict__['_coordination_tool'] = CoordinationTool(CoordinationPort(
                parent=self, error=lambda exc: self.error(exc),
                confirm_replace=lambda: self.confirm_replace() if hasattr(self, 'confirm_replace') else True,
                edit_structure=lambda molecule, note: self.model_menu_tool.edit_structure(molecule, note),
                set_state=lambda charge, spin: self.calculation_tool.set_charge_and_multiplicity(charge, spin)))
        return tool

    def constraints_changed(self):
        """The constraints of the document shown, the document changed (the window side of the tool)."""
        self.viewer.constraints = list(self.constraints)
        self.viewer.update()
        self.dirty = True
        if hasattr(self, 'preview'):
            self.input_tool.refresh_input()

    def toggle_move_mode(self):
        if self.move_button.isChecked():
            self.move_kind.setCurrentIndex(0)  # an atom by default
        self.build_mode.setCurrentIndex(3 if self.move_button.isChecked() else 0)

    def choose_view_mode(self):
        """«Обзор / выделение» — the mode of looking and choosing (pressed again, it stays chosen)."""
        self.build_mode.setCurrentIndex(0)
        self.view_button.setChecked(True)

    def toggle_edit_mode(self):
        """The pencil: editing the structure (adding atoms and fragments); the arrows: moving."""
        self.build_mode.setCurrentIndex(1 if self.edit_toggle.isChecked() else 0)

    def toggle_periodic_table(self):
        """Element button: opens the periodic table, a second press closes it."""
        if getattr(self, 'periodic_dialog', None) is not None and self.periodic_dialog.isVisible():
            self.periodic_dialog.close()
            self.element_button.setChecked(self.build_mode.currentData() == 'atom')
            return
        self.build_mode.setCurrentIndex(1)
        self.show_periodic_table()
        self.element_button.setChecked(True)

    def fill_hydrogens(self, indices=None):
        """Hydrogens up to the usual valence: of the given or selected atoms, else of all."""
        if self.browsing:
            return
        if indices is None or isinstance(indices, bool):
            indices = self.viewer.selected or None
        try:
            result, added = add_hydrogens(self.coordinate_tool.table_molecule(), indices)
            if not added:
                self.notify(tr('Все валентности уже заполнены.'), 6000)
                return
            self.model_menu_tool.edit_structure(
                result, tr(f'Добавлено атомов водорода: {added}. Это начальная геометрия, а не оптимизированная.')
            )
        except ValueError as exc:
            self.error(exc)

    def panel_rule(self):
        rule = QFrame()
        rule.setObjectName('panelRule')
        rule.setFixedHeight(1)
        return rule

    @staticmethod
    def tool_rule():
        """A thin grey upright line between groups of tool buttons."""
        rule = QFrame()
        rule.setObjectName('toolRule')
        rule.setFixedSize(1, 22)
        return rule

    def clean_geometry(self, *args):
        """Tidy bond lengths and angles with the simple force field of cleanup.py (selected atoms only, if any)."""
        if self.browsing:
            return
        from modules.compass.chemistry.cleanup import clean

        try:
            molecule = self.coordinate_tool.table_molecule()
            if len(molecule.atoms) < 2:
                return
            result, steps, energy = clean(molecule, self.viewer.selected or None)
            self.model_menu_tool.edit_structure(
                result,
                tr('Геометрия выровнена простым силовым полем — это начальная структура, а не оптимизированная.'),
            )
        except ValueError as exc:
            self.error(exc)

    def optimize_uff(self, *args):
        """«Оптимизировать (UFF)» — the selected atoms (or all) to a minimum of UFF (uff.optimize); the energy
        and its parts in the status (Undo returns the structure)."""
        if self.browsing:
            return None
        from modules.compass.chemistry import uff

        molecule = self.coordinate_tool.table_molecule()
        if len(molecule.atoms) > uff.SIZE_LIMIT:
            self.error(ValueError(tr('UFF в Компасе — до {} атомов; для большей системы — GFN-FF (xtb).').format(uff.SIZE_LIMIT)))
            return None
        try:
            result = uff.optimize(molecule, self.viewer.selected or None)
        except ValueError as exc:
            self.error(exc)
            return None
        parts = result.parts
        text = tr('UFF: {:.2f} ккал/моль ({:.1f} кДж/моль), было {:.2f}; шагов {}. Связи {:.2f}, углы {:.2f}, торсионы {:.2f}, '
                  'инверсии {:.2f}, ван-дер-Ваальс {:.2f}.').format(
            result.energy, result.energy * 4.184, result.start, result.steps, parts['bond'], parts['angle'],
            parts['torsion'], parts['inversion'], parts['vdw'])
        if result.notes:
            text += ' ' + ' '.join(result.notes)
        others = sorted({a.symbol for a in molecule.atoms} - uff.CHECKED_ELEMENTS)
        if others:  # outside the beta (AGENTS.md §0): checked against RDKit for H, C, N, O, P, S, Cl only
            text += ' ' + tr('Не проверено: UFF для {} не сверен с RDKit — геометрию проверьте.').format(', '.join(others))
        self.model_menu_tool.edit_structure(result.molecule, text)
        return result

    def choose_move_kind(self, key):
        self.move_kind.setCurrentIndex(max(0, self.move_kind.findData(key)))
        self.build_mode.setCurrentIndex(3)

    def begin_hold(self):
        self._continuous_active = True
        self._continuous_recorded = False

    def end_hold(self):
        self._continuous_active = False

    def hold_button(self, name, title, step, tick):
        return iconify(HoldButton(step, tick, self.begin_hold, self.end_hold), name, title)

    def toggle_pin(self):
        """The ruler next to r/∠: pin the measurement of the selection on the model (or take it away). With no atom
        selected and measurements on the model — all of them are taken away."""
        sel = tuple(self.viewer.selected)
        if not sel and self.viewer.pinned:
            self.viewer.pinned = []
            self.update_pin_button()
            self.viewer.update()
            return
        if not 2 <= len(sel) <= 4:
            self.pin_button.setChecked(False)
            return
        same = [m for m in self.viewer.pinned if m == sel or m == sel[::-1]]
        if same:
            self.viewer.pinned.remove(same[0])
        else:
            self.viewer.pinned.append(sel)
        self.update_pin_button()
        self.viewer.update()

    def update_pin_button(self):
        sel = tuple(self.viewer.selected)
        ok = 2 <= len(sel) <= 4
        clears = not sel and bool(self.viewer.pinned)  # nothing selected: the button takes all of them away
        self.pin_button.setEnabled(ok or clears)
        self.pin_button.setChecked(ok and any(m == sel or m == sel[::-1] for m in self.viewer.pinned))
        name = 'ruler_clear' if clears else 'ruler'  # a small cross in the corner says what a click will do
        if self.pin_button.property('quail_icon') != name:
            from azimuth.icons import icon

            self.pin_button.setIcon(icon(name))
            self.pin_button.setProperty('quail_icon', name)
        self.pin_button.setToolTip(tr('Убрать с модели все измерения (ни один атом не выделен)') if clears else
                                   tr('Показать на модели: расстояние (2 атома), угол (3) или двугранный угол (4)'))

    def toggle_hbonds(self):
        self.viewer.show_hbonds = self.hbonds_action.isChecked()
        self.preferences.setValue('show_hbonds', self.viewer.show_hbonds)
        self.viewer.update()

    def toggle_lengths(self):
        self.viewer.show_lengths = self.lengths_button.isChecked()
        self.preferences.setValue('show_lengths', self.viewer.show_lengths)
        self.viewer.update()
        if hasattr(self, 'lengths_action'):
            self.lengths_action.setChecked(self.viewer.show_lengths)

    def change_move_target(self):
        self.viewer.move_target = self.move_kind.currentData()
        if self.viewer.move_target in ('molecule', 'chain') and self.viewer.selected and self.molecule.atoms:
            # the selected atoms grow to their molecules (chains) — what a drag will move
            grown = sorted({i for k in self.viewer.selected if k < len(self.molecule.atoms) for i in self.viewer.move_group(k)})
            if grown != sorted(self.viewer.selected):
                self.viewer.set_selection(grown)
        for key, item in self.move_kind_buttons.items():
            item.setChecked(key == self.viewer.move_target)
        self.viewer.update_help()

    def change_display_mode(self, *args):
        self.viewer.display_mode = self.display_mode.currentData()
        self.viewer.locked_camera = None
        self.viewer.update()
        self.preferences.setValue('display_mode', self.viewer.display_mode)
        for key, item in getattr(self, 'display_actions', {}).items():
            item.setChecked(key == self.viewer.display_mode)

    def change_projection(self, *args):
        self.viewer.perspective = self.projection.currentIndex() == 1
        for i, b in enumerate(self.projection_buttons):
            b.setChecked(i == self.projection.currentIndex())
        self.viewer.update()

    def toggle_axes(self):
        self.viewer.show_axes = self.axes_button.isChecked()
        self.viewer.update()

    # the corner axes moved by the mouse — «Разрешить перемещение», «Вернуть оси на место» (the menu of
    # the button «Оси»); the place and the permission are kept (preferences axes_offset, axes_movable)
    def restore_axes_place(self):
        import json

        viewer = self.viewer
        try:
            offset = json.loads(self.preferences.value('axes_offset', '') or 'null')
        except (TypeError, ValueError, AttributeError):
            offset = None
        valid = isinstance(offset, list) and len(offset) == 2 and all(isinstance(v, (int, float)) for v in offset)
        viewer.axes_offset = (int(offset[0]), int(offset[1])) if valid else None
        try:
            movable = str(self.preferences.value('axes_movable', 'false')).lower() in ('true', '1')
        except AttributeError:
            movable = False
        viewer.axes_movable = movable
        viewer.setMouseTracking(True) if movable else None
        viewer.on_axes_moved = self.keep_axes_place

    def keep_axes_place(self, offset):
        import json

        try:
            self.preferences.setValue('axes_offset', json.dumps(list(offset)) if offset else '')
        except AttributeError:
            pass

    def allow_axes_moving(self, on):
        viewer = self.viewer
        viewer.axes_movable = bool(on)
        if on:
            viewer.setMouseTracking(True)
            if not self.axes_button.isChecked():  # the axes to move are shown
                self.axes_button.setChecked(True)
                self.toggle_axes()
            self.notify(tr('Оси можно перетаскивать левой кнопкой мыши; место запомнится.'), 6000)
        elif viewer._axes_hover:
            viewer._axes_hover = False
            viewer.unsetCursor()
        try:
            self.preferences.setValue('axes_movable', bool(on))
        except AttributeError:
            pass
        viewer.update()

    def reset_axes_place(self):
        """«Вернуть оси на место»: the axes back in their corner, and moving them switched off (the owner, 2026-11-24:
        after the return the axes moved under the mouse again)."""
        self.viewer.axes_offset = None
        self.keep_axes_place(None)
        if self.viewer.axes_movable:
            self.allow_axes_moving(False)
        self.viewer.update()

    def fill_axes_menu(self, menu):
        """The items of the axes in the menu of their button (custom_bar.button_menu)."""
        move = menu.addAction(tr('Разрешить перемещение'))
        move.setCheckable(True)
        move.setChecked(self.viewer.axes_movable)
        move.toggled.connect(self.allow_axes_moving)
        back = menu.addAction(tr('Вернуть оси на место'))
        back.setEnabled(self.viewer.axes_offset is not None)
        back.triggered.connect(lambda *_: self.reset_axes_place())
        return menu

    def update_rotation_controls(self):
        editing = self.build_mode.currentData() != 'view'
        for item in self.rotation_buttons:
            item.setEnabled(not editing or len(self.viewer.selected) >= 2)
        self.fragment_controls.setEnabled(len(self.viewer.selected) == 2)

    def commit_fragment_edit(self, result, indices):
        self.viewer.keep_camera()
        record = not getattr(self, '_continuous_active', False) or not getattr(self, '_continuous_recorded', False)
        # the selection is kept through the reload — an empty selection in between disabled the rotation
        # buttons (update_rotation_controls), which released the held button: the smooth turn stopped after a step
        self.load_molecule(result, record=record, preserve_view=True, selection=indices)
        if getattr(self, '_continuous_active', False):
            self._continuous_recorded = True

    def rotate_control(self, axis, direction, step=15):
        if self.build_mode.currentData() == 'view':
            self.viewer.rotate_view(axis, radians(step * direction))
            return
        indices = self.viewer.selected.copy()
        if len(indices) < 2:
            return
        try:
            molecule = self.coordinate_tool.table_molecule()
            if len(indices) == 2 and any({a, b} == set(indices) for a, b, _ in connections(molecule)):
                group = bond_side(molecule, *indices)
                pivot = molecule.atoms[indices[1]].position
            else:
                group = indices
                pivot = tuple(sum(molecule.atoms[i].position[k] for i in group) / len(group) for k in range(3))
            vector = {'x': (1, 0, 0), 'y': (0, 1, 0), 'z': (0, 0, 1)}[axis]
            self.commit_fragment_edit(rotate_atoms(molecule, group, pivot, vector, radians(step * direction)), indices)
        except ValueError as exc:
            self.error(exc)

    def twist_fragment(self, direction, step=15):
        indices = self.viewer.selected.copy()
        if len(indices) != 2:
            return
        try:
            molecule = self.coordinate_tool.table_molecule()
            a, b = indices
            group = bond_side(molecule, a, b)
            pivot = molecule.atoms[a].position
            end = molecule.atoms[b].position
            axis = tuple(end[k] - pivot[k] for k in range(3))
            self.commit_fragment_edit(rotate_atoms(molecule, group, pivot, axis, radians(step * direction)), indices)
        except ValueError as exc:
            self.error(exc)

    def stretch_selected(self, delta):
        indices = self.viewer.selected.copy()
        if len(indices) != 2:
            return
        try:
            self.commit_fragment_edit(stretch_bond(self.coordinate_tool.table_molecule(), *indices, delta), indices)
        except ValueError as exc:
            self.error(exc)

    def select_mode(self, index):
        if self.browsing:
            self.trajectory_tool.set_trajectory_open(False)  # editing starts from the own structure
        self.navigate(0)
        self.structure_tabs.setCurrentIndex(0)
        self.build_mode.setCurrentIndex(index)

    def toggle_bond(self):
        if len(self.viewer.selected) != 2:
            return
        a, b = self.viewer.selected
        exists = any({i, j} == {a, b} for i, j, _ in connections(self.molecule))
        self.apply_bond(remove=exists)

    def apply_measurement(self):
        indices = self.viewer.selected.copy()
        if len(indices) not in (2, 3, 4):
            return
        text = self.measure_fields[3].text().strip().replace('−', '-').replace(',', '.').rstrip('Å°').strip()
        try:
            target = float(text)
            result = set_measurement(self.coordinate_tool.table_molecule(), indices, target, self.geometry_fragment.isChecked())
            if result.atoms != self.molecule.atoms:
                self.commit_fragment_edit(result, indices)
            else:
                self.update_measurements(indices)
        except ValueError as exc:
            self.update_measurements(indices)
            self.error(tr('Введите число для длины (Å) или угла (°). ') + str(exc))

    def update_measurements(self, indices):
        for field in self.measure_fields:
            field.clear()
            field.setToolTip('')
        self.measure_fields[3].setReadOnly(True)
        if len(indices) == 1:
            for field, value in zip(self.measure_fields, self.molecule.atoms[indices[0]].position):
                field.setText(f'{value:.4f}')
                field.setToolTip(f'{value:.10f} Å')
        if len(indices) in (2, 3, 4):
            try:
                name, value = measurement([self.molecule.atoms[i].position for i in indices])
                self.measure_fields[3].setReadOnly(False)
                self.measure_fields[3].setText(f'{value:.5f} ' + ('Å' if len(indices) == 2 else '°'))
                self.measure_fields[3].setToolTip(
                    name
                    + tr(' · введите значение и нажмите Enter · порядок атомов: ')
                    + ' → '.join(str(i + 1) for i in indices)
                )
            except ValueError:
                self.measure_fields[3].setText(tr('Не определён'))
                self.measure_fields[3].setToolTip(tr('Совпадающие атомы или коллинеарная тройка для двугранного угла'))

    FILE_FORMATS = ('MOL', 'SDF', 'MOL2', 'PDB')  # angstrom only, bonds included

    LINE_FORMATS = ('SMILES', 'InChI')  # the structure as a line, without coordinates

    notify = _notices.notify

    NOTE_MS = 60_000  # a message shorter than that joins the pill of the status of Spectrum; a wait replaces it

    busy_status = _notices.busy_status
    busy_pill = _notices.busy_pill
    page_notify = _notices.page_notify
    drop_page_toast = _notices.drop_page_toast
    hide_notice = _notices.hide_notice
    place_notice = _notices.place_notice

    def eventFilter(self, watched, event):
        if watched is getattr(self, 'viewer', None) and event.type() in (QEvent.Type.Resize, QEvent.Type.Move):
            self.drawer.place(self.viewer.geometry())
            self.place_notice()
            self.update_side_quill()  # Quill follows the corner of the field
        if event.type() == QEvent.Type.KeyPress and watched in (
            getattr(self, 'viewer', None),
            getattr(self, 'drawer', None),
            getattr(getattr(self, 'drawer', None), 'table', None),
        ):
            if self.trajectory_tool.trajectory_key(event):
                return True
        return super().eventFilter(watched, event)

    def toggle_label(self, key):
        self.label_mode.setCurrentIndex(self.label_mode.findData('none' if self.viewer.label_mode == key else key))

    def edit_custom_labels(self):
        """«Своя подпись»: the selected atoms get the label written (empty — removed; «#» becomes 1, 2, 3…
        in the order of the selection); without a selection the own labels are shown or hidden."""
        from PySide6.QtWidgets import QInputDialog

        viewer = self.viewer
        selected = [i for i in viewer.selected if viewer.molecule is not None and 0 <= i < len(viewer.molecule.atoms)]
        if not selected:
            if not viewer.custom_labels:
                self.custom_label_button.setChecked(viewer.show_custom)
                self.notify(tr('Выделите атомы и нажмите «Своя подпись», чтобы подписать их.'), 8000)
                return None
            viewer.show_custom = not viewer.show_custom
            self.custom_label_button.setChecked(viewer.show_custom)
            viewer.update()
            return viewer.show_custom
        current = viewer.custom_labels.get(selected[0], '')
        text, ok = QInputDialog.getText(
            self, tr('Своя подпись'),
            tr('Подпись выделенных атомов (пусто — убрать; # — номер по порядку выделения):'), text=current,
        )
        self.custom_label_button.setChecked(viewer.show_custom)
        if not ok:
            return None
        self.set_custom_labels(selected, text)
        return dict(viewer.custom_labels)

    def set_custom_labels(self, atoms, text):
        viewer = self.viewer
        text = text.strip()[:40]
        for k, i in enumerate(atoms, start=1):
            if text:
                viewer.custom_labels[i] = text.replace('#', str(k))
            else:
                viewer.custom_labels.pop(i, None)
        viewer.show_custom = True
        self.custom_label_button.setChecked(True)
        self.dirty = True
        viewer.update()

    def change_labels(self, *args):
        self.viewer.label_mode = self.label_mode.currentData()
        for key, item in getattr(self, 'label_buttons', {}).items():
            item.setChecked(key == self.viewer.label_mode)
        self.preferences.setValue('atom_labels', self.viewer.label_mode)
        self.viewer.update()

    def show_periodic_table(self):
        if hasattr(self, 'periodic_dialog') and self.periodic_dialog.isVisible():
            self.periodic_dialog.raise_()
            return
        self.periodic_dialog = PeriodicTable(self.element.currentText(), self)
        self.periodic_dialog.selected.connect(self.choose_element)
        self.periodic_dialog.isotope.connect(self.choose_isotope)
        self.periodic_dialog.show()

    def choose_isotope(self, symbol, mass):
        """The next atoms of symbol put on the model get the isotope of mass (Calculation.isotopes)."""
        from azimuth.core import isotope_name

        self._pending_isotope = (symbol, float(mass))
        self.notify(tr('Новые атомы {} будут {} (масса {:.4f}); обычный элемент — щелчком в таблице.').format(
            symbol, isotope_name(symbol, float(mass)), float(mass)), 9000)

    def choose_element(self, symbol):
        self._pending_isotope = None  # an element chosen plainly — its usual mass (choose_isotope after)
        self.element.setCurrentText(symbol)
        self.build_mode.setCurrentIndex(1)
        self.update_choice_label()
        self.structure_tabs.setCurrentIndex(0)

    def push_history(self):
        self.undo_history.append(self.molecule)
        self.undo_history = self.undo_history[-100:]
        self.redo_history.clear()

    def update_history_buttons(self):
        self.undo_button.setEnabled(bool(self.undo_history))
        self.redo_button.setEnabled(bool(self.redo_history))
        if hasattr(self, 'undo_action'):
            self.undo_action.setEnabled(bool(self.undo_history))
            self.redo_action.setEnabled(bool(self.redo_history))

    @staticmethod
    def topology(molecule):
        return tuple(a.symbol for a in molecule.atoms), frozenset(
            (min(i, j), max(i, j)) for i, j, _ in connections(molecule)
        )

    def retitled(self, molecule):
        """An edit that changes atoms or bonds of a titled molecule drops the title."""
        old = getattr(self, 'molecule', None)
        if (
            old is not None
            and molecule.title
            and molecule.title == old.title
            and self.topology(molecule) != self.topology(old)
        ):
            return replace(molecule, title='')
        return molecule

    def update_side_quill(self):
        """What the empty field says: how to begin a molecule, or a crystal in «Компас · Кристалл» (0.247.0: the hint
        of Quill with her bubble went; the name stays — the actions of Compass call it)."""
        crystal_mode = getattr(self, 'compass_mode', 'molecule') == 'crystal'
        from modules.compass.view.viewer import CRYSTAL_PARTS, EMPTY_PARTS

        parts = CRYSTAL_PARTS if crystal_mode else EMPTY_PARTS
        if getattr(self.viewer, 'empty_parts', None) != parts:
            self.viewer.empty_parts = parts
            self.viewer.update()
        any_shown = False
        # the molecule's Quill (lower right) and the crystal's (lower left), each in its own subsection
        for hint, mine in ((getattr(self, 'quill_hint', None), not crystal_mode),
                           (getattr(self, 'crystal_hint', None), crystal_mode)):
            if hint is None:
                continue
            if self.molecule.atoms and mine and hint.seen and not hint.dismissed:
                hint.dismiss()  # something was built or opened — she has done her job until the next start
            empty = not self.molecule.atoms and mine
            shown = empty and not hint.dismissed and hint.place(self.viewer.geometry())
            hint.seen = hint.seen or shown
            hint.set_dark(getattr(self.viewer, 'dark', False))
            hint.setVisible(shown)
            any_shown = any_shown or shown
        if getattr(self, 'quill_hint', None) is None and getattr(self, 'crystal_hint', None) is None:
            return
        if getattr(self.viewer, 'hint_shown', None) != any_shown:
            self.viewer.hint_shown = any_shown
            self.viewer.update()

    def molecule_summary(self, molecule):
        """The formula and the number of atoms; a name only after «Назвать» (iupac_button)."""
        if not molecule.atoms:
            return tr('атомов пока нет')
        crystal = getattr(self, 'crystal', None) if getattr(self, 'compass_mode', 'molecule') == 'crystal' else None
        if crystal:  # the formula of the crystal
            formula = self.crystal_formula(crystal[0])
            if formula:
                return tr('{}  /  на модели атомов: {}').format(formula, len(molecule.atoms))
        title = self.naming_tool.iupac_title(molecule, LANG_CODE()) or ''
        formula = molecule.formula.translate(SUBSCRIPTS)  # H₂O: the indices as subscripts
        return (
            tr(f'{title}  /  {formula}  /  атомов: {len(molecule.atoms)}')
            if title
            else tr(f'{formula}  /  атомов: {len(molecule.atoms)}')
        )

    def crystal_formula(self, data):
        """The formula unit of a crystal — the atoms of its cell (one part of a disorder) over their greatest
        common divisor, the indices as subscripts: CsCl, NaCl, C₇H₆O₂; '' when the cell cannot be read."""
        from math import gcd

        from azimuth.core import Atom, Molecule
        from modules.compass.chemistry import crystal as cr

        cached = getattr(self, '_crystal_formula', None)
        if cached is not None and cached[0] is data:
            return cached[1]
        try:
            atoms = [a[0] for a in cr.unit_cell(cr.main_part(data)) if a[0] != 'X']
        except ValueError:
            atoms = []
        counts = {s: atoms.count(s) for s in set(atoms)}
        common = 0
        for n in counts.values():
            common = gcd(common, n)
        unit = [Atom(s, 0, 0, 0) for s, n in counts.items() for _ in range(n // common)] if common else []
        formula = Molecule('', tuple(unit), ()).formula.translate(SUBSCRIPTS) if unit else ''
        self._crystal_formula = (data, formula)
        return formula

    def load_molecule(self, molecule, record=True, preserve_view=False, selection=()):
        molecule = self.retitled(molecule)
        kind_before = bool(self.molecule.atoms)  # an empty project gets the icon of a molecule
        if getattr(self.viewer, 'pinned', None) and [a.symbol for a in molecule.atoms] != [
            a.symbol for a in self.molecule.atoms
        ]:
            self.viewer.pinned = []
        if getattr(self.viewer, 'guides', None) and [a.symbol for a in molecule.atoms] != [
            a.symbol for a in self.molecule.atoms
        ]:
            self.viewer.guides = []  # vectors and planes go with another structure, as the measurements
            self.viewer.user_hidden = frozenset()  # and the atoms hidden by the user
        if getattr(self, 'constraints', None) and [a.symbol for a in molecule.atoms] != [
            a.symbol for a in self.molecule.atoms
        ]:
            self.constraints.clear()
            self.viewer.constraints = []  # the atoms changed: the numbers no longer fit
            self.notify(tr('Состав изменился — ограничения оптимизации сняты.'), 8000)
        if record and molecule != self.molecule:
            self.push_history()
        if not preserve_view:
            self.viewer.locked_camera = None
        self._loading = True
        self.molecule = molecule
        self.table.blockSignals(True)
        self.table.setRowCount(len(molecule.atoms))
        for i, atom in enumerate(molecule.atoms):
            for j, value in enumerate((atom.symbol, *atom.position)):
                self.table.setItem(
                    i,
                    j,
                    QTableWidgetItem(str(value) if j == 0 else f'{value / (BOHR if self._coordinate_bohr else 1):.8f}'),
                )
        self.table.blockSignals(False)
        self.coordinate_tool.table_changed()
        self._loading = False
        self.viewer.set_selection([i for i in selection if 0 <= i < len(molecule.atoms)])
        self.update_history_buttons()
        if kind_before != bool(molecule.atoms) and hasattr(self, 'refresh_project_navigation'):
            self.refresh_project_navigation()

    change_build_mode = _building.change_build_mode
    update_choice_label = _building.update_choice_label
    model_selection_changed = _building.model_selection_changed
    placed = _building.placed
    placement_preview = _building.placement_preview
    snapped = _building.snapped
    snap_preview = _building.snap_preview
    snap_on_model = _building.snap_on_model
    place_on_model = _building.place_on_model
    isotope_on_new = _building.isotope_on_new
    load_edit = _building.load_edit
    hydrogens_live = _building.hydrogens_live
    hydrogens_added = _building.hydrogens_added
    tidy_added = _building.tidy_added
    move_on_model = _building.move_on_model
    apply_bond = _building.apply_bond
    new_molecule_command = _molecules.new_molecule_command
    start_project_molecule = _molecules.start_project_molecule
    structure_as_new_molecule = _molecules.structure_as_new_molecule
    same_project_molecule = _molecules.same_project_molecule
    confirm_duplicate_molecule = _molecules.confirm_duplicate_molecule
    new_molecule = _molecules.new_molecule

    def _settle_before_history(self):
        """Undo and redo work on the structure of the tab. An open preview (rotation about a bond, the
        Z-matrix editor) is cancelled first and a browsed result step is left, so that the shown preview or step is
        not taken for a state of the history (before, undo after a preview skipped the last real state on redo)."""
        for name in ('torsion_window', 'zmatrix_window'):
            window = getattr(self, name, None)
            try:
                if window is not None and window.isVisible():
                    window.cancel()
            except RuntimeError:  # the window is already deleted
                pass
        if getattr(self, 'browsing', False):
            self.trajectory_tool.set_trajectory_open(False)

    def undo_geometry(self):
        self._settle_before_history()
        try:
            self.coordinate_tool.table_molecule()
        except ValueError:
            self.load_molecule(self.molecule, record=False)
            return
        if self.undo_history:
            self.redo_history.append(self.molecule)
            molecule = self.undo_history.pop()
            self.load_molecule(molecule, record=False, preserve_view=True)

    def redo_geometry(self):
        self._settle_before_history()
        if self.redo_history:
            self.undo_history.append(self.molecule)
            molecule = self.redo_history.pop()
            self.load_molecule(molecule, record=False, preserve_view=True)

    def add_atom(self):
        if self.browsing:
            self.trajectory_tool.set_trajectory_open(False)
        self.navigate(0)
        self.structure_tabs.setCurrentIndex(0)
        self.build_mode.setCurrentIndex(1)
        self.show_periodic_table()
        self.notify(tr('Выберите элемент и щёлкните в поле молекулы.'), 10000)

    def add_molecule(self):
        """«Правка → Атомы и фрагменты → Добавить молекулу»: the mode «Молекула» of the building — the molecule chosen
        (a teaching one, of the library or of «Мои молекулы», button «Молекула») is put where the field is clicked."""
        self.select_mode(4)
        self.notify(tr('Щёлкните в свободном месте поля — встанет «{}»; другую молекулу выберите кнопкой «Молекула» над '
                       'моделью.').format(tr(self.molecule_choice)), 10000)

    def remove_atom(self):
        if getattr(self, 'browsing', False):  # a step of a result is not edited (also from the table)
            self.notify(tr('Это результат расчёта — откройте его как новую молекулу, чтобы менять.'))
            return
        indices = self.viewer.selected or sorted({item.row() for item in self.table.selectedIndexes()})
        if not indices:
            return
        try:
            before = self.coordinate_tool.table_molecule()
            self.load_edit(before, delete_atoms(before, indices))
        except ValueError as exc:
            self.error(exc)

    OPEN_FILTER = (
        'Молекула, проект или результат (*.xyz *.qcc *.out *.log *.nwout *.qcout *.gamout *.outp *.mol *.sdf *.sd *.mol2 *.cdxml *.pdb *.ent *.gjf *.com *.gjc *.inp *.molden *.molf *.fchk *.fch *.cif);;'
        'XYZ (*.xyz);;Проект «Азимута» (*.qcc);;Результат расчёта (*.out *.log *.nwout *.qcout *.gamout *.outp);;Molfile / SDF (*.mol *.sdf *.sd);;'
        'MOL2 (*.mol2);;ChemDraw (*.cdxml);;PDB (*.pdb *.ent);;Входной файл Gaussian (*.gjf *.com *.gjc);;Входной файл ORCA (*.inp);;Molden (*.molden *.molf);;Gaussian fchk (*.fchk *.fch);;Кристалл CIF (*.cif);;Все файлы (*)'
    )

    STRUCTURE_KINDS = ('xyz', 'xyz_frames', 'mol', 'mol2', 'pdb', 'orca_input', 'gaussian_input', 'cdxml')

    HYDROGENS_ON_OPEN = 'hydrogens_on_open'  # «Файл → Достраивать водороды у файлов без H» (on by default)

    EXAMPLE_FILTER = 'Примеры (*.out *.log *.xyz *.fchk *.molden *.cif *.json);;Все файлы (*)'
