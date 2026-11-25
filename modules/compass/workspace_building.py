"""Building a structure on the model of Compass: the mode of building, the atom or fragment placed or snapped to an
atom, its preview, the isotopes and hydrogens of the new atoms, the tidying, moving, the bonds. Methods of
CompassWorkspace (self is the window), kept here to make workspace.py shorter.

Split off modules/compass/workspace.py (0.222.30).
"""

from math import dist
from PySide6.QtCore import QItemSelectionModel
from modules.compass.chemistry.builder import (
    connections,
    place_atom,
    place_fragment,
    place_molecule,
    move_atom,
    delete_atoms,
    set_bond,
)
from modules.compass.chemistry.builder import centred, is_centred
from modules.compass.chemistry import library
from modules.compass.chemistry.editing import bond_by_replacing, change_element, hydrogens_for, make_room, substitute
from azimuth.i18n import combo_key, tr


def change_build_mode(self, *args):
    self.viewer.hold_place()  # the tool rows above the field change; the model stays put
    mode = self.build_mode.currentData()
    self.viewer.set_mode(mode)
    editing = mode != 'view'
    self.edit_toggle.setChecked(
        mode in ('atom', 'fragment', 'molecule')
    )  # the pencil: structure; the arrows: moving
    self.move_button.setChecked(mode == 'move')
    if hasattr(self, 'view_button'):
        self.view_button.setChecked(mode == 'view')
    self.add_atom_button.setChecked(mode == 'atom')
    self.add_fragment_button.setChecked(mode == 'fragment')
    self.edit_tools.setVisible(editing)
    self.fragment_controls.setVisible(editing)
    self.rotation_title.setText(tr('Фрагмент · 15°') if editing else tr('Вид · 15°'))
    for b in self.rotation_buttons:
        axis = b.property('quail_icon').split('-')[1].upper()
        b.setToolTip(
            tr(
                f'Повернуть выделенный фрагмент вокруг {axis} · два и больше выделенных атома; щелчок — 15°, удержание — плавно'
            )
            if editing
            else tr(f'Повернуть вид вокруг {axis} · щелчок — 15°, удержание — плавно')
        )
    self.update_rotation_controls()
    structure = mode in ('atom', 'fragment', 'molecule')
    for item in (
        self.element_button,
        self.fragment_button,
        self.molecule_button,
        self.hydrogens_button,
        self.hydrogens_live_button,
        self.cleanup_button,
        self.tidy_live_button,
    ):
        item.setVisible(structure)
    self.element_tile.setVisible(mode == 'atom')
    self.choice_label.setVisible(mode in ('fragment', 'molecule'))
    self.edit_rule.setVisible(structure)
    owner = self.molecule_button if mode == 'molecule' else self.fragment_button
    self.edit_row.removeWidget(self.choice_label)
    self.edit_row.insertWidget(self.edit_row.indexOf(owner) + 1, self.choice_label)
    self.bond_order_title.hide()
    self.bond_order.hide()  # the order of a bond — right click on it
    for item in self.move_kind_buttons.values():
        item.setVisible(mode == 'move')
    self.element_button.setChecked(mode == 'atom')
    self.fragment_button.setChecked(mode == 'fragment')
    self.molecule_button.setChecked(mode == 'molecule')
    self.change_move_target() if mode == 'move' else None
    self.update_choice_label()
    if mode != 'atom' and hasattr(self, 'periodic_dialog'):
        self.periodic_dialog.close()


def update_choice_label(self):
    mode = self.build_mode.currentData()
    if hasattr(self, 'element_tile'):
        self.element_tile.set_symbol(self.element.currentText())
    text = (
        tr(combo_key(self.fragment))
        if mode == 'fragment'
        else (tr(self.molecule_choice) if mode == 'molecule' else '')
    )
    self.choice_label.setText(text)


def model_selection_changed(self, indices):
    if hasattr(self, 'pin_button'):
        self.update_pin_button()
    self.table.blockSignals(True)
    self.table.clearSelection()
    for i in indices:
        self.table.selectionModel().select(
            self.table.model().index(i, 0),
            QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows,
        )
    self.table.blockSignals(False)
    self.bond_button.setEnabled(len(indices) == 2)
    self.unbond_button.setEnabled(len(indices) == 2)
    self.delete_button.setEnabled(bool(indices))
    message = (
        tr('Выбраны: ') + ', '.join(f'{self.molecule.atoms[i].symbol}{i + 1}' for i in indices) if indices else ''
    )
    if len(indices) == 2:
        message += tr(
            f' · расстояние {dist(self.molecule.atoms[indices[0]].position, self.molecule.atoms[indices[1]].position):.3f} Å'
        )
    self.selection_info.setText(message)
    self.update_measurements(indices)
    self.update_rotation_controls()
    if hasattr(self, 'connect_action'):
        self.connect_action.setEnabled(len(indices) == 2)
        self.disconnect_action.setEnabled(len(indices) == 2)


def placed(self, molecule, position, anchor, direction=None):
    """(the structure before, the structure with the atom or the fragment of the field put) — of a click (anchor:
    the atom pressed, or None in the empty field) and of a drag from an atom (direction: the bond aimed, a unit
    vector). A terminal hydrogen dragged from gives its place: the bond is aimed from its neighbour. Not tidied
    (tidy_added) — the caller does."""
    start = molecule
    if (anchor is not None and direction is not None and molecule.atoms[anchor].symbol == 'H'
            and self.model_menu_tool.is_terminal(molecule, anchor)):
        neighbour = next(j if i == anchor else i for i, j, _ in connections(molecule) if anchor in (i, j))
        molecule = delete_atoms(molecule, [anchor])
        anchor = neighbour - (1 if neighbour > anchor else 0)
    operation = place_fragment if self.viewer.mode == 'fragment' else place_atom
    name = combo_key(self.fragment) if self.viewer.mode == 'fragment' else self.element.currentText()
    order = int(self.bond_order.currentText())
    if anchor is not None and self.hydrogens_live():
        # a saturated atom gives up a hydrogen (or two for a double bond) for the new bond
        molecule, anchor = make_room(molecule, anchor, order, toward=direction)
    result = operation(molecule, name, position, anchor, order, self.bond_length.value(), direction=direction)
    return start, self.hydrogens_added(start, result, anchor)


def placement_preview(self, anchor, direction):
    """The structure as it would be with the atom or the fragment aimed from anchor (the drag in the
    field, viewer.placement_aim), or None."""
    if self.viewer.mode not in ('atom', 'fragment') or self.browsing:
        return None
    try:
        return self.placed(self.molecule, None, anchor, direction)[1]
    except (ValueError, IndexError, StopIteration):
        return None


def snapped(self, molecule, anchor, target):
    """The drag from anchor ended on the atom target — target becomes the element chosen and is
    bonded to anchor (its molecule brought to the bond length, editing.bond_by_replacing); the hydrogens made room
    for the bond and filled as for a placed atom. (structure before, structure after)."""
    from math import sqrt

    start = molecule
    if molecule.atoms[anchor].symbol == 'H' and self.model_menu_tool.is_terminal(molecule, anchor):
        neighbour = next(j if i == anchor else i for i, j, _ in connections(molecule) if anchor in (i, j))
        if neighbour == target:
            raise ValueError(tr('Выберите два разных атома.'))
        molecule = delete_atoms(molecule, [anchor])
        neighbour -= 1 if neighbour > anchor else 0
        target -= 1 if target > anchor else 0
        anchor = neighbour
    order = int(self.bond_order.currentText())
    if (molecule.atoms[target].symbol == 'H' and self.model_menu_tool.is_terminal(molecule, target)
            and any({i, j} == {anchor, target} for i, j, _ in connections(molecule))):
        # a hydrogen of the atom itself: the atom dragged takes its place (the click on a hydrogen)
        result = self.tidy_added(molecule, self.hydrogens_added(
            molecule, change_element(molecule, target, self.element.currentText())))
        return start, result
    result = bond_by_replacing(molecule, anchor, target, self.element.currentText(), order, self.bond_length.value())
    if self.hydrogens_live():
        at, to = result.atoms[anchor].position, result.atoms[target].position
        line = tuple(to[k] - at[k] for k in range(3))
        size = sqrt(sum(c * c for c in line)) or 1.0
        toward = tuple(c / size for c in line)

        def index_of(position):
            return next(i for i, a in enumerate(result.atoms) if a.position == position)

        # the bond is made already: order 0 — the hydrogens over the valence go, the nearest to the bond first
        result, _ = make_room(result, index_of(at), 0, toward=toward)
        result, _ = make_room(result, index_of(to), 0, toward=tuple(-c for c in toward))
        before = result
        result = hydrogens_for(result, [index_of(at), index_of(to)])
        action = getattr(self, 'tidy_live_action', None)
        if action is not None and action.isChecked():
            from modules.compass.chemistry.cleanup import tidy_new

            old = {a.position for a in before.atoms}
            new = [i for i, a in enumerate(result.atoms) if a.position not in old]
            if new:
                try:
                    result = tidy_new(result, new)
                except (ValueError, IndexError):
                    pass
    return start, result


def snap_preview(self, anchor, target):
    """The structure as it would be with the drag from anchor ended on target, or None (viewer.placement_snap)."""
    if self.viewer.mode != 'atom' or self.browsing:
        return None
    try:
        return self.snapped(self.molecule, anchor, target)[1]
    except (ValueError, IndexError, StopIteration):
        return None


def snap_on_model(self, anchor, target):
    try:
        start, result = self.snapped(self.coordinate_tool.table_molecule(), anchor, target)
        self.load_edit(start, result)
        self.viewer.set_selection([])
    except (ValueError, IndexError, StopIteration) as exc:
        self.error(exc)


def place_on_model(self, position, anchor, direction=None):
    try:
        molecule = self.coordinate_tool.table_molecule()
        if self.viewer.mode == 'molecule':
            if anchor is not None:
                raise ValueError(tr('Щёлкните в свободном месте поля, чтобы добавить молекулу.'))
            first = len(molecule.atoms)
            self.load_edit(molecule, place_molecule(molecule, library.molecule(self.molecule_choice), position))
            if not first:  # where it was put, at the scale that fits it (the pan stays)
                self.viewer.locked_camera = None
            self.viewer.set_selection([])
            return
        if (direction is None and anchor is not None and molecule.atoms[anchor].symbol == 'H'
                and self.model_menu_tool.is_terminal(molecule, anchor)):
            # a group or an atom put on a hydrogen replaces it
            if self.viewer.mode == 'fragment':
                result = substitute(molecule, anchor, combo_key(self.fragment))
            else:
                result = change_element(molecule, anchor, self.element.currentText())
            result = self.tidy_added(molecule, self.hydrogens_added(molecule, result))
            self.load_edit(molecule, result)
            self.isotope_on_new([anchor])
            self.viewer.set_selection([])
            return
        start, result = self.placed(molecule, position, anchor, direction)
        if anchor is not None and direction is None:
            # a free atom or group in the empty field stays as placed; an aimed one too
            result = self.tidy_added(start, result)
        self.load_edit(start, result)
        self.isotope_on_new([len(start.atoms)])
        self.viewer.set_selection(
            []
        )  # a new atom is not selected, so «Достроить водороды» then fills all atoms
    except ValueError as exc:
        self.error(exc)


def isotope_on_new(self, indices):
    """The atoms just put (indices), of the element of choose_isotope, get its isotope."""
    pending = getattr(self, '_pending_isotope', None)
    if not pending:
        return []
    symbol, mass = pending
    atoms = self.molecule.atoms
    chosen = [k for k in indices if 0 <= k < len(atoms) and atoms[k].symbol == symbol]
    if chosen:
        self.structure_tool.set_isotopes(chosen, mass)
    return chosen


def load_edit(self, before, result, centre=True):
    """An edit of the structure in the field; the view stays. A structure begun in the empty field, or
    one with the origin at its centre, keeps the origin at its centre — the first atom is (0, 0, 0) wherever it
    was put, two atoms have it in the middle of the bond — and the view turns about it; the model does not move
    on the screen (viewer.shift_origin). A structure with other coordinates (a file, a cell) keeps them.
    centre=False — an edit of the coordinates themselves («Начало координат — в выделенный атом», «Сдвинуть и
    повернуть…», the editor of the Z-matrix…): kept as made."""
    self.viewer.keep_camera()
    if centre and result.atoms and (not before.atoms or is_centred(before)):
        result, shift = centred(result)
        self.viewer.shift_origin(shift)
    self.load_molecule(result, preserve_view=True)


def hydrogens_live(self):
    action = getattr(self, 'hydrogens_live_action', None)
    return bool(action is not None and action.isChecked())


def hydrogens_added(self, before, after, anchor=None):
    """«Достраивать водороды при построении» — the new heavy atoms and the atom they were put on
    get their valences filled with hydrogens (extra ones removed)."""
    if not self.hydrogens_live():
        return after
    old = {a.position for a in before.atoms}
    new = [i for i, a in enumerate(after.atoms) if a.position not in old and a.symbol != 'H']
    neighbours = set()
    for i, j, _ in after.bonds or ():
        if i in new:
            neighbours.add(j)
        if j in new:
            neighbours.add(i)
    targets = sorted(set(new) | {j for j in neighbours if after.atoms[j].symbol != 'H'})
    if anchor is not None and 0 <= anchor < len(after.atoms) and after.atoms[anchor].symbol != 'H':
        targets = sorted(set(targets) | {anchor})
    try:
        return hydrogens_for(after, targets) if targets else after
    except (ValueError, IndexError):
        return after


def tidy_added(self, before, after):
    """«Выравнивать при построении» — the new atoms (not at a place of the structure before) tidied
    with the simple force field; the rest stays (cleanup.tidy_new)."""
    action = getattr(self, 'tidy_live_action', None)
    if action is None or not action.isChecked():
        return after
    from modules.compass.chemistry.cleanup import tidy_new

    old = {a.position for a in before.atoms}
    new = [i for i, a in enumerate(after.atoms) if a.position not in old]
    uff_live = getattr(self, 'tidy_uff_action', None)
    field = 'uff' if uff_live is not None and uff_live.isChecked() else 'simple'
    try:
        return tidy_new(after, new, field=field)
    except (ValueError, IndexError):
        return after


def move_on_model(self, index, position):
    try:
        result = move_atom(self.coordinate_tool.table_molecule(), index, position)
        self.viewer.keep_camera()
        self.load_molecule(result, preserve_view=True)
        self.viewer.set_selection([index])
    except ValueError as exc:
        self.viewer.set_molecule(self.molecule)
        self.error(exc)


def apply_bond(self, checked=False, remove=False):
    if len(self.viewer.selected) != 2:
        return
    indices = self.viewer.selected.copy()
    try:
        self.load_molecule(
            set_bond(self.coordinate_tool.table_molecule(), *indices, 0 if remove else int(self.bond_order.currentText())),
            preserve_view=True,
        )
        self.viewer.set_selection(indices)
    except ValueError as exc:
        self.error(exc)
