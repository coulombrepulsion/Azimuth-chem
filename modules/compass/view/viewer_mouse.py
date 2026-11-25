"""The mouse of the Compass view (MoleculeView): a click selects or adds, a drag moves, turns or draws a bond, the
wheel zooms, a double click centres. Methods of MoleculeView (self is the view), kept here to make viewer.py shorter.

Split off modules/compass/view/viewer.py (0.222.29).
"""

from dataclasses import replace
from math import atan2, sqrt
from PySide6.QtCore import Qt, QPointF, QRectF
from azimuth.core import Atom
from modules.compass.chemistry.builder import connections
from modules.compass.chemistry.transforms import angle_fragment, bond_side, rotate_atoms
from modules.compass.chemistry.geometry_tools import cross, dot, sub
from azimuth.i18n import tr
from modules.compass.chemistry.editing import chain, connected
from modules.compass.chemistry import torsion


def _empty_click(self, position):
    """A click on no atom and no bond — on a hydrogen bond it is told (contactClicked), else the field."""
    if self.bond_at(position) is not None:
        return
    found = self.hbond_at(position)
    if found is not None:
        self.contactClicked.emit(*found)
    else:
        self.emptyClicked.emit()


def mousePressEvent(self, event):
    if event.button() == Qt.MouseButton.LeftButton and self.near_axes(event.position()):
        self._axes_drag = event.position() - self.axes_origin()  # the grip within the axes
        self.setCursor(Qt.CursorShape.ClosedHandCursor)
        event.accept()
        return
    if event.button() not in (Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton):
        return
    both = Qt.MouseButton.LeftButton | Qt.MouseButton.RightButton
    if event.buttons() & both == both:
        # Switching from an atom drag to view panning cancels the uncommitted edit.
        if self.original_molecule is not None:
            self.molecule = self.original_molecule
        self.drag_position = None
        self.drag_result = None
        self.aiming = None  # an aimed atom is given up too
        self.aim_snap = None
        self.aim_direction = None
        self.frozen_camera = None
        self.pan_gesture = True
        self.press = event.position()
        self.last = event.position()
        self.dragged = True
        self.setCursor(Qt.CursorShape.SizeAllCursor)
        self.update()
        return
    if self.pan_gesture:
        return
    self.setFocus()
    self.press = event.position()
    self.last = event.position()
    self.dragged = False
    self.press_button = event.button()
    self.press_hit = self.hit_test(self.press)
    self.original_molecule = self.molecule
    self.drag_position = None
    self.drag_result = None
    self.drag_group = []
    self.aiming = None
    self.aim_direction = None
    self.aim_snap = None
    if (
        self.mode in ('atom', 'fragment')
        and self.placement_aim is not None
        and self.press_hit is not None
        and event.button() == Qt.MouseButton.LeftButton
        and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier
    ):
        point, depth = self.projected()[self.press_hit]
        self.frozen_camera = self.camera()  # the view stays while the new atom is aimed
        self.aiming = (self.press_hit, QPointF(point), self.camera()[1] * self.depth_factor(depth))
    if (
        self.twist is not None
        and event.button() == Qt.MouseButton.LeftButton
        and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        and self.press_hit in self.twist_group
    ):
        self._twisting = True
        self.setCursor(Qt.CursorShape.SizeHorCursor)
        self.twist('start', 0.0)
        return
    if event.button() == Qt.MouseButton.LeftButton and event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
        self.band = QRectF(self.press, self.press)
        self.setCursor(Qt.CursorShape.CrossCursor)
        return
    if (
        self.mode == 'move'
        and self.molecule
        and self.molecule.atoms
        and (
            self.press_hit is not None  # «Молекула целиком» from the empty field turns the view
            or (self.move_target == 'selection' and self.selected)
        )
        and event.button() == Qt.MouseButton.LeftButton
    ):
        self.frozen_camera = self.camera()
        self.drag_scale = self.camera()[1] * self.depth_factor(
            self.projected()[self.press_hit][1] if self.press_hit is not None else 0
        )
        if self.move_target in ('molecule', 'chain'):
            # the molecule (the chain) of the pressed atom is selected at once — what will move is seen
            self.set_selection(self.move_group(self.press_hit))
    self.setCursor(Qt.CursorShape.ClosedHandCursor)


def move_group(self, index):
    """The atoms «Молекула целиком» / «Цепочка» move for a press on index (None: the empty field)."""
    molecule = self.original_molecule or self.molecule
    if index is None:
        return []
    return connected(molecule, index) if self.move_target == 'molecule' else chain(molecule, index)


def mouseMoveEvent(self, event):
    if self._axes_drag is not None:
        origin = event.position() - self._axes_drag
        self.axes_offset = (round(self.width() - origin.x()), round(origin.y()))
        self.update()
        return
    if self.press is None:
        hover = self.near_axes(event.position())
        if hover != self._axes_hover:
            self._axes_hover = hover
            if hover:
                self.setCursor(Qt.CursorShape.OpenHandCursor)
            else:
                self.unsetCursor()
        return
    if self._twisting:
        self.dragged = True
        self.twist('move', (event.position() - self.press).x() * self.TWIST_DEG_PER_PX)
        return
    if self.band is not None:
        self.band = QRectF(self.press, event.position()).normalized()
        self.dragged = True
        self.update()
        return
    if self.pan_gesture:
        both = Qt.MouseButton.LeftButton | Qt.MouseButton.RightButton
        if event.buttons() & both == both:
            delta = event.position() - self.last
            self.pan_view(delta.x(), delta.y())
        self.last = event.position()
        return
    if (event.position() - self.press).manhattanLength() > 4:
        self.dragged = True
    if self.aiming is not None:
        if self.dragged:
            self.aim_at(event.position())
        self.last = event.position()
        return
    delta = event.position() - self.last
    if (
        self.dragged
        and self.mode == 'move'
        and self.molecule
        and self.molecule.atoms
        and (
            self.press_hit is not None  # «Молекула целиком» from the empty field turns the view
            or (self.move_target == 'selection' and self.selected)
        )
        and self.press_button == Qt.MouseButton.LeftButton
    ):
        shift = event.position() - self.press
        scale = self.drag_scale
        movement = self.from_view((shift.x() / scale, -shift.y() / scale, 0))
        if self.move_target in ('selection', 'molecule', 'chain'):
            # «Молекула» — the molecule of the pressed atom (one of a dimer), the whole structure
            # when the drag starts in the empty field; «Цепочка» — the unbranched piece (editing.chain)
            if not self.drag_group:
                if self.move_target == 'selection':
                    self.drag_group = list(self.selected)
                else:
                    self.drag_group = self.move_group(self.press_hit)
            chosen = set(self.drag_group)
            self.drag_result = replace(
                self.original_molecule,
                atoms=tuple(
                    Atom(a.symbol, *(a.position[k] + movement[k] for k in range(3))) if i in chosen else a
                    for i, a in enumerate(self.original_molecule.atoms)
                ),
                bonds=connections(self.original_molecule),
            )
        elif self.move_target == 'twist':
            # «Вокруг связи» (as in Chemcraft): two selected bonded atoms are the axis; the side
            # of the pressed atom turns about it, TWIST_DEG_PER_PX per pixel to the right
            if not self.drag_group:
                try:
                    if len(self.selected) != 2:
                        raise ValueError(tr('Выделите два связанных атома — ось вращения, затем тяните атом одной из сторон.'))
                    b, c = self.selected
                    moving = c if self.press_hit in torsion.side(self.original_molecule, b, c, c) else b
                    self.drag_group = torsion.side(self.original_molecule, b, c, moving)
                    if self.press_hit not in self.drag_group:
                        raise ValueError(tr('Тяните атом одной из сторон связи.'))
                    self.drag_axis = (b, c, moving)
                except ValueError as exc:
                    self.press = None
                    self.frozen_camera = None
                    self.drag_group = []
                    self.editError.emit(str(exc))
                    return
            b, c, moving = self.drag_axis
            self.drag_result = torsion.turn(self.original_molecule, b, c, moving, shift.x() * self.TWIST_DEG_PER_PX)
        elif self.move_target == 'fragment':
            if not self.drag_group:
                try:
                    found = None if len(self.selected) == 2 else angle_fragment(self.molecule, self.press_hit)
                    if len(self.selected) == 2:
                        a, b = self.selected
                    elif found is not None:  # the group of the pressed atom turns about its pivot
                        a, b = found[0], None
                    else:
                        b = self.press_hit
                        neighbors = [j if i == b else i for i, j, _ in connections(self.molecule) if b in (i, j)]
                        if len(neighbors) != 1:
                            raise ValueError(
                                tr('Выберите два связанных атома: опору, затем сторону перемещаемого фрагмента.')
                            )
                        a = neighbors[0]
                    self.drag_group = found[1] if b is None else bond_side(self.molecule, a, b)
                    if self.press_hit not in self.drag_group:
                        raise ValueError(tr('Тяните атом со стороны выбранного фрагмента, а не опору.'))
                    self.drag_pivot = self.molecule.atoms[a].position
                except ValueError as exc:
                    self.press = None
                    self.frozen_camera = None
                    self.editError.emit(str(exc))
                    return
            v = sub(self.original_molecule.atoms[self.press_hit].position, self.drag_pivot)
            w = tuple(v[k] + movement[k] for k in range(3))
            axis = cross(v, w)
            length = sqrt(dot(axis, axis))
            self.drag_result = (
                rotate_atoms(
                    self.original_molecule, self.drag_group, self.drag_pivot, axis, atan2(length, dot(v, w))
                )
                if length > 1e-10
                else self.original_molecule
            )
        else:
            atom = self.original_molecule.atoms[self.press_hit]
            self.drag_position = tuple(atom.position[k] + movement[k] for k in range(3))
            atoms = list(self.original_molecule.atoms)
            atoms[self.press_hit] = Atom(atom.symbol, *self.drag_position)
            self.drag_result = replace(self.original_molecule, atoms=tuple(atoms))
        self.molecule = self.drag_result
    elif self.dragged:
        self.rotate_screen(delta.x() * 0.012, delta.y() * 0.012)
    self.last = event.position()
    self.update()


def aim_at(self, point):
    """The new bond from the pressed atom towards the cursor the
    structure with it shown; nearer than AIM_START_PX — none."""
    anchor, origin, scale = self.aiming
    shift = point - origin
    target = self.snap_target(point, anchor) if self.placement_snap is not None else None
    preview = self.placement_snap(anchor, target) if target is not None else None
    if preview is not None:  # over another atom — it is drawn bonded, the element dragged in its place
        self.aim_snap = target
        self.aim_direction = None
        self.molecule = preview
        self.update()
        return
    self.aim_snap = None
    if shift.manhattanLength() < self.AIM_START_PX or scale <= 0:
        self.aim_direction = None
        self.molecule = self.original_molecule
    else:
        v = self.from_view((shift.x() / scale, -shift.y() / scale, 0))
        size = sqrt(dot(v, v))
        direction = tuple(c / size for c in v)
        preview = self.placement_aim(anchor, direction)
        if preview is not None:
            self.aim_direction = direction
            self.molecule = preview
    self.update()


def snap_target(self, point, anchor):
    """The atom of the structure before the drag under the cursor (not anchor), or None."""
    shown = self.molecule
    self.molecule = self.original_molecule
    try:
        hit = self.hit_test(point) if self.molecule else None
    finally:
        self.molecule = shown
    return hit if hit is not None and hit != anchor else None


def mouseReleaseEvent(self, event):
    if self._axes_drag is not None:
        self._axes_drag = None
        self._axes_hover = self.near_axes(event.position())
        if self._axes_hover:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.unsetCursor()
        self.axes_offset = tuple(self.axes_offset) if self.axes_offset else None
        if self.on_axes_moved is not None:
            self.on_axes_moved(self.axes_offset)
        event.accept()
        return
    if self.pan_gesture:
        if not event.buttons() & (Qt.MouseButton.LeftButton | Qt.MouseButton.RightButton):
            self.pan_gesture = False
            self.press = None
            self.last = None
            self.original_molecule = None
            self.set_mode(self.mode)
        return
    if self.press is None:
        return
    if self._twisting:
        self._twisting = False
        angle = (event.position() - self.press).x() * self.TWIST_DEG_PER_PX
        self.press = None
        self.last = None
        self.original_molecule = None
        self.set_mode(self.mode)
        if self.twist is not None:
            self.twist('end', angle)
        return
    if self.band is not None:
        band = self.band
        self.band = None
        hidden = self.hidden_atoms()
        inside = (
            [i for i, (point, _) in enumerate(self.projected()) if band.contains(point) and i not in hidden]
            if band.width() > 3 or band.height() > 3
            else []
        )
        hit = self.hit_test(event.position())
        if not inside and hit is not None:
            inside = [hit]
        self.set_selection(self.selected + [i for i in inside if i not in self.selected])
        self.press = None
        self.last = None
        self.original_molecule = None
        self.set_mode(self.mode)
        self.update()
        return
    if self.aiming is not None and self.press_button == Qt.MouseButton.LeftButton:
        anchor, direction, snap = self.aiming[0], self.aim_direction, self.aim_snap
        self.aiming = None
        self.aim_direction = None
        self.aim_snap = None
        self.molecule = self.original_molecule
        self.press = None
        self.last = None
        self.frozen_camera = None
        self.original_molecule = None
        self.set_mode(self.mode)
        if snap is not None:
            self.placementSnapped.emit(anchor, snap)
        elif direction is not None:
            self.placementAimed.emit(anchor, direction)
        else:  # not drawn away from the atom: a click
            self.placementRequested.emit(self.world_at(event.position()), anchor)
        return
    if self.drag_result is not None and self.move_target != 'atom':
        result = self.drag_result
        self.molecule = self.original_molecule
        self.moleculeMoved.emit(result)
    elif self.drag_position is not None:
        self.molecule = self.original_molecule
        self.atomMoved.emit(self.press_hit, self.drag_position)
    elif not self.dragged and self.press_button == Qt.MouseButton.LeftButton:
        hit = self.hit_test(event.position())
        if self.mode in ('atom', 'fragment', 'molecule'):
            self.placementRequested.emit(self.world_at(event.position()), hit)
        elif self.mode == 'move' and self.move_target in ('molecule', 'chain'):
            self.set_selection(self.move_group(hit) if hit is not None else [])  # a click selects it
            if hit is None:
                self._empty_click(event.position())
        else:
            selected = self.selected.copy()
            if hit is not None:
                if hit in selected:
                    selected.remove(hit)
                else:
                    selected.append(hit)
            self.set_selection(selected)
            if hit is None:
                self._empty_click(event.position())
    elif not self.dragged and self.press_button == Qt.MouseButton.RightButton:
        atom = self.hit_test(event.position())
        if atom is not None:
            self.press = None
            self.last = None
            self.frozen_camera = None
            self.original_molecule = None
            self.drag_result = None
            self.set_selection([])
            self.set_mode(self.mode)
            self.atomMenuRequested.emit(atom, event.globalPosition().toPoint())
            return
        bond = self.bond_at(event.position())
        if bond is not None:
            self.press = None
            self.last = None
            self.frozen_camera = None
            self.original_molecule = None
            self.drag_result = None
            self.set_mode(self.mode)
            self.bondMenuRequested.emit(bond[0], bond[1], event.globalPosition().toPoint())
            return
        self.set_selection([])
    self.press = None
    self.last = None
    self.frozen_camera = None
    self.original_molecule = None
    self.drag_result = None
    self.set_mode(self.mode)


def wheelEvent(self, event):
    """Mouse wheel: zoom. Trackpad (a scroll with phases): two fingers move the view, as both
    mouse buttons do; Cmd/Ctrl + two fingers zoom. A pinch zooms (event())."""
    trackpad = event.phase() != Qt.ScrollPhase.NoScrollPhase
    # the inertia of a two-finger swipe (macOS sends its momentum after the fingers leave) no longer carries the
    # model away
    if event.phase() == Qt.ScrollPhase.ScrollMomentum:
        event.accept()
        return
    if trackpad and not event.modifiers() & (
        Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.MetaModifier
    ):
        d = event.pixelDelta() if not event.pixelDelta().isNull() else event.angleDelta() / 8
        self.pan_view(d.x(), d.y())
        event.accept()
        return
    step = event.angleDelta().y() or event.pixelDelta().y()
    if step:
        self.zoom_view(1.1 if step > 0 else 1 / 1.1)


def mouseDoubleClickEvent(self, event):
    # In editing modes a double click must never reset the camera or insert twice.
    if self.mode == 'view':
        self.reset_view()
    self.press = None
