"""Original editable orthographic view. Geometry edits are emitted to the application."""

from math import sin, cos, dist, hypot
from time import monotonic
from PySide6.QtCore import Qt, QPointF, QTimer, Signal
from PySide6.QtWidgets import QWidget
from modules.compass.chemistry.builder import connections
from modules.compass.chemistry.geometry_tools import dot
from azimuth.i18n import tr
from modules.compass.view.schemes import AZIMUTH
from modules.compass.view.viewer_drawing import BOND_LEGENDS, VDW_RADII, ViewerDrawing  # noqa: F401 — 0.105.11
from modules.compass.view.viewer_surface import FINE_TRIANGLES  # noqa: F401 — named as viewer.FINE_TRIANGLES
from modules.compass.view import viewer_mouse as _mouse
from modules.compass.view import viewer_paint as _painting
from modules.compass.view import viewer_camera as _camera
from modules.compass.view import viewer_motion as _motion

# the colours of the program (moved to modules/compass/view/schemes.py on 2026-10-24; the same dict)
COLORS = AZIMUTH


# the empty field of «Компас · Молекула» says how to begin (was «Выберите «Атом» или «Молекулу»…»);
# only this, with the glyphs of the pencil and the folder (draw_empty)
EMPTY_TEXT = 'Постройте свою молекулу или откройте готовую'


def remap_labels(old, new, labels):
    """The own labels of atoms after the structure changed: by number when the elements in order are the
    same (a geometry changed), else by the atom that stays where it was (an atom added or deleted elsewhere)."""
    if new is None or not labels:
        return {}
    if old is None:
        return {k: v for k, v in labels.items() if k < len(new.atoms)}
    if [a.symbol for a in old.atoms] == [a.symbol for a in new.atoms]:
        return dict(labels)
    place = {}
    for k, a in enumerate(new.atoms):
        place.setdefault((a.symbol, tuple(round(c, 5) for c in a.position)), k)
    found = {}
    for k, text in labels.items():
        if 0 <= k < len(old.atoms):
            a = old.atoms[k]
            target = place.get((a.symbol, tuple(round(c, 5) for c in a.position)))
            if target is not None:
                found[target] = text
    return found


def remap_bond_marks(old, new, marks):
    """The type and the colour of single bonds after the structure changed — their atoms followed as the
    own labels follow (remap_labels); a bond whose atom is gone loses its mark."""
    if new is None or not marks:
        return {}
    ends = sorted({k for pair in marks for k in pair})
    moved = remap_labels(old, new, {k: k for k in ends}) if old is not None else {k: k for k in ends if k < len(new.atoms)}
    where = {was: now for now, was in moved.items()}
    out = {}
    for (i, j), mark in marks.items():
        if i in where and j in where:
            out[(min(where[i], where[j]), max(where[i], where[j]))] = dict(mark)
    return out


class MoleculeView(ViewerDrawing, QWidget):
    placementRequested = Signal(object, object)  # world position, anchor index or None
    placementAimed = Signal(int, object)  # anchor index, the unit direction of the new bond (a drag)
    placementSnapped = Signal(int, int)  # anchor index, the atom the drag ended on (it becomes the new one)
    atomMoved = Signal(int, object)
    moleculeMoved = Signal(object)
    editError = Signal(str)
    emptyClicked = Signal()  # a click on the empty field (no atom, no bond) — Compass folds the drawer
    contactClicked = Signal(int, int)  # a click on the dotted line of a hydrogen bond: (H, acceptor)
    selectionChanged = Signal(object)
    deleteRequested = Signal()
    bondMenuRequested = Signal(int, int, object)  # atoms of the bond under a right click, global position
    atomMenuRequested = Signal(int, object)  # the atom under a right click, global position
    engineFailed = Signal(str)  # VTK could not draw the model; the view went back to 'raster'

    def __init__(self):
        super().__init__()
        self.molecule = None
        self.dark = False
        self.display_mode = 'ball-stick'
        self.bond_color = 'smooth'
        self.bond_width = 1.0
        self.show_bonds = True
        self.multiple_bonds = True
        self.hide_hydrogens = False  # «Скрыть атомы H» (hidden_atoms)
        # «Вид» as in Chemcraft — atoms hidden by the user, dummies hidden, labels of the bonds, labels of the
        # selection only, the van der Waals spheres, the axes on the model ('corner', 'centre', 'origin')
        self.user_hidden = frozenset()
        self.hide_dummies = False
        self.bond_labels = None  # None, 'number', 'order'
        self.labels_selected_only = False
        self.show_vdw = False
        self.axes_place = 'corner'
        # the corner axes carried by the mouse (axes_movable) to axes_offset (from the right, from the top);
        # on_axes_moved(offset) — the window keeps it
        self.axes_offset = None
        self.axes_movable = False
        self.on_axes_moved = None
        self._axes_drag = None
        self._axes_hover = False
        self.label_mode = "element"
        self.custom_labels = {}  # own labels of atoms {index: text}, kept through edits (set_molecule)
        self.bond_marks = {}  # {(i, j): {'kind': 'aromatic' | 'partial', 'color': '#rrggbb'}} of single bonds
        self.guides = []  # vectors and planes on the model (modules/compass/chemistry/guides.py)
        self.show_custom = True
        self.yaw, self.pitch, self.zoom = 0.25, -1.0, 1.0
        self.roll = 0.0
        self.perspective = False
        self.show_axes = False
        self.mode = 'view'
        self.selected = []
        self.move_target = 'atom'
        self.pan = QPointF()
        self.inset = 0.0  # px of the drawer of the result over the left edge of the field
        self._inset_motion = None
        self.basis = None
        self.surface = None  # {'atoms', 'meshes', 'opacity', 'legend', 'limit'} (surface_actions.py)
        self.found_contacts = None  # {'atoms', 'contacts': [(i, j, kind)]} — the weak interactions of QTAIM
        self.aim = None  # {'atoms', 'points': [(kind, xyz Å)], 'paths': [(n, 3) Å]} — QTAIM (show_aim)
        self.capture = False
        self.drag_result = None
        self.drag_group = []
        self.press = None
        self.last = None
        self.dragged = False
        self.press_hit = None
        self.pan_gesture = False
        self.locked_camera = None
        self.frozen_camera = None
        self.original_molecule = None
        self.drag_position = None
        self.setMinimumSize(360, 160)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.pinned = []  # measurements shown on the model: tuples of 2–4 atoms (ruler button)
        self.scan_pin = None  # the atoms of the scanned coordinate while the points of a scan are browsed
        self.show_lengths = False
        self.show_hbonds = True
        from azimuth import defaults

        self.transparent = defaults.get('picture_transparent')  # «Настройки → Снимки»
        self.scale_capture = 1
        self.band = None  # Shift + drag: the rubber band of a selection
        self.constraints = []  # optimization constraints [(kind, atoms)], drawn in orange
        # a drag from an atom with an atom or a fragment chosen aims the new bond — placement_aim(anchor, direction)
        # gives the structure to show (Workspace.placement_preview), the release puts it (placementAimed)
        self.placement_aim = None
        self.aiming = None  # (anchor, its point on the screen, px per Å there) while such a drag goes
        self.aim_direction = None
        # the drag ends on another atom — placement_snap(anchor, target) gives the structure with that atom
        # become the one dragged and bonded to anchor (Workspace.snap_preview), the release makes it (placementSnapped)
        self.placement_snap = None
        self.aim_snap = None
        self.ghost = None  # a reference geometry drawn faintly with dashed bonds (optimization start)
        # Smoothness: while the view moves, the model is drawn at the normal (not Retina)
        # resolution; MOTION_REFINE ms after the last movement it is drawn again in full quality.
        self._motion_until = 0.0
        self._refine = QTimer(self)
        self._refine.setSingleShot(True)
        self._refine.timeout.connect(self.update)
        # the critical point chosen in a table pulses on the model — its ring widens and narrows (a static
        # ring was hard to see among the atoms); the timer runs only while such a point is shown
        self._pulse = QTimer(self)
        self._pulse.setInterval(self.PULSE_INTERVAL)
        self._pulse.timeout.connect(self._pulse_tick)
        self._paint_camera = None  # camera() computed once per frame (it was computed for every atom)
        self._hbonds = (None, ())  # hydrogen bonds of the last structure
        self.overlay_source = None  # molecule -> result_overlay.overlay dict or None
        # Overlay of another structure for comparison (modules/compass/actions/overlay_actions.py):
        # molecule -> (aligned structure in the order of molecule, or None; caption lines)
        self.compare_source = None
        # Rotation about a bond by dragging (modules/compass/actions/torsion_actions.py): while the
        # window is open, a left drag that starts on an atom of twist_group calls twist(stage, degrees)
        # with stage 'start' / 'move' / 'end' and the horizontal travel times TWIST_DEG_PER_PX
        self.twist = None
        self.twist_group = ()
        self._twisting = False
        # Display scheme (modules/compass/view/schemes.py): element colours, size of the atoms,
        # the background ('theme', 'white', 'black') and the dot grid
        self.palette = COLORS
        self.cell_lines = None  # edges of a crystal block [(start, end)], the first three a, b, c
        self.lattice_planes = None  # (label, [polygon of Cartesian corners]) — the planes (hkl) in the block
        self.symmetry_items = None  # [(symbol, kind, Cartesian point | segment | polygon)] of the crystal
        self.lattice_points = None  # the nodes of the Bravais lattice of the block (Cartesian, Å)
        self.ellipsoids = None  # (molecule, [U_cart or None per atom]) of the crystal
        self.ring_marks = None  # (molecule, crystal_rings.model_marks) — centroids, planes, π–π, C–H···π
        self.atom_tints = None  # (molecule, {atom index: colour}) — the molecules coloured by symmetry
        self.polyhedra = None  # (molecule, [(symbol, faces)]) — coordination polyhedra of the crystal
        self.energy_frame = None  # (molecule, [(a, b, width 0–1, attractive)]) — the energy framework
        self.atom_scale = 1.0
        self.background = 'theme'
        self.grid = True
        # who draws the atoms and bonds — 'raster' (modules/compass/view/raster.py, built in) or 'vtk'
        # (modules/compass/view/vtk_model.py); everything else on the field is the same for both
        self.engine = 'raster'
        self.set_mode('view')

    def set_mode(self, mode):
        self.mode = mode
        self.update_help()
        self.setCursor(
            Qt.CursorShape.CrossCursor if mode in ('atom', 'fragment', 'molecule') else Qt.CursorShape.OpenHandCursor
        )
        self.update()

    def set_molecule(self, molecule):
        if self.custom_labels:
            self.custom_labels = remap_labels(self.molecule, molecule, self.custom_labels)
        if self.bond_marks:
            self.bond_marks = remap_bond_marks(self.molecule, molecule, self.bond_marks)
        self.molecule = molecule
        self.selected = [i for i in self.selected if 0 <= i < len(molecule.atoms)]
        self.update()

    def set_selection(self, indices, emit=True):
        self.selected = list(dict.fromkeys(indices))
        if emit:
            self.selectionChanged.emit(self.selected)
        self.update()

    MOTION_REFINE = 200

    def moving(self):
        """The view has just moved: fast frames now, a full-quality frame when the movement stops."""
        self._motion_until = monotonic() + self.MOTION_REFINE / 1000
        self._refine.start(self.MOTION_REFINE + 20)

    def interactive(self):
        """A fast (lower-resolution) frame: a mouse button is held or the view moved a moment ago."""
        return not self.capture and (self.press is not None or monotonic() < self._motion_until)

    # the model fills about half of the field on opening (it was three quarters: «too close»);
    # a small molecule is drawn as if it were FIT_MIN_SPREAD Å across from its centre
    FIT = 0.28
    FIT_MIN_SPREAD = 1.8

    def camera(self):
        if self._paint_camera is not None:
            return self._paint_camera
        if self.frozen_camera is not None:
            return self.frozen_camera
        if self.locked_camera is not None:
            return self.locked_camera[0], self.locked_camera[1] * self.zoom
        if not self.molecule or not self.molecule.atoms:
            return (0.0, 0.0, 0.0), min(self.width(), self.height()) * 0.17 * self.zoom
        atoms = self.molecule.atoms
        center = tuple(sum(a.position[k] for a in atoms) / len(atoms) for k in range(3))
        spread = max(
            self.FIT_MIN_SPREAD,
            max(
                dist(a.position, center) + (VDW_RADII.get(a.symbol, 1.8) if self.display_mode == 'spacefill' else 0)
                for a in atoms
            ),
        )
        return center, min(self.width(), self.height()) * self.FIT / spread * self.zoom

    def keep_camera(self):
        center, scale = self.camera()
        self.locked_camera = (center, scale / self.zoom)

    def to_view(self, position):
        if self.basis is not None:
            position = tuple(dot(position, v) for v in self.basis)
        x, y, z = position
        x, z = cos(self.yaw) * x + sin(self.yaw) * z, -sin(self.yaw) * x + cos(self.yaw) * z
        y, z = cos(self.pitch) * y - sin(self.pitch) * z, sin(self.pitch) * y + cos(self.pitch) * z
        x, y = cos(self.roll) * x - sin(self.roll) * y, sin(self.roll) * x + cos(self.roll) * y
        return x, y, z

    def from_view(self, position):
        x, y, z = position
        x, y = cos(self.roll) * x + sin(self.roll) * y, -sin(self.roll) * x + cos(self.roll) * y
        y, z = cos(self.pitch) * y + sin(self.pitch) * z, -sin(self.pitch) * y + cos(self.pitch) * z
        x, z = cos(self.yaw) * x - sin(self.yaw) * z, sin(self.yaw) * x + cos(self.yaw) * z
        if self.basis is not None:
            return tuple(sum((x, y, z)[j] * self.basis[j][k] for j in range(3)) for k in range(3))
        return x, y, z

    def world_at(self, point):
        center, scale = self.camera()
        delta = self.from_view(
            (
                (point.x() - self.width() / 2 - self.pan.x()) / scale,
                (self.height() / 2 + self.pan.y() - point.y()) / scale,
                0,
            )
        )
        return tuple(center[k] + delta[k] for k in range(3))

    def depth_factor(self, z):
        if not self.perspective:
            return 1.0
        center, scale = self.camera()
        # Derive focal distance from the camera, not the changing geometry during a drag.
        distance = max(8.0, min(self.width(), self.height()) / (scale / self.zoom) * 1.5)
        return distance / max(distance * 0.15, distance - z)

    def projected(self):
        center, scale = self.camera()
        result = []
        if not self.molecule:
            return result
        for atom in self.molecule.atoms:
            x, y, z = self.to_view(tuple(atom.position[k] - center[k] for k in range(3)))
            result.append(
                (
                    QPointF(
                        self.width() / 2 + self.pan.x() + x * scale * self.depth_factor(z),
                        self.height() / 2 + self.pan.y() - y * scale * self.depth_factor(z),
                    ),
                    z,
                )
            )
        return result

    def hidden_atoms(self):
        """The atoms not drawn — with «Скрыть атомы H», every hydrogen that is not selected. The same set in
        every display mode and both engines (bond_depth.model_scene), for labels, picking, the rubber band and the
        silhouette; the structure itself, the table and the calculations keep them."""
        if not self.molecule:
            return frozenset()
        n = len(self.molecule.atoms)
        hidden = {i for i in self.user_hidden if i < n}  # «Скрыть выделенные атомы»
        if self.hide_dummies:
            hidden |= {i for i, a in enumerate(self.molecule.atoms) if a.symbol == 'X'}
        if self.hide_hydrogens:
            chosen = set(self.selected)
            hidden |= {i for i, a in enumerate(self.molecule.atoms) if a.symbol == 'H' and i not in chosen}
        return frozenset(hidden)

    def drawn_bonds(self, hidden=None):
        """The bonds drawn: those of builder.connections without a hidden atom."""
        bonds = connections(self.molecule)
        hidden = self.hidden_atoms() if hidden is None else hidden
        return [b for b in bonds if b[0] not in hidden and b[1] not in hidden] if hidden else bonds

    def atom_radius(self, index):
        center, scale = self.camera()
        z = self.to_view(tuple(self.molecule.atoms[index].position[k] - center[k] for k in range(3)))[2]
        symbol = self.molecule.atoms[index].symbol
        if symbol == 'X':  # a dummy atom — a small grey point with a dashed ring (draw_dummies)
            radius = 0.06 if self.display_mode == 'sticks' else 0.11
        else:
            radius = (
                VDW_RADII.get(symbol, 1.8)
                if self.display_mode == 'spacefill'
                else (0.09 if self.display_mode == 'sticks' else (0.17 if symbol == 'H' else 0.24))
            )
        return max(2, scale * radius * self.atom_scale * self.depth_factor(z))

    def ring_clip(self, i, points, radii, reach):
        """Where the selection ring of atom i may be drawn — the square around it minus the disks of the
        atoms drawn in front of it (view/occlusion.in_front); None when none reaches it."""
        from PySide6.QtGui import QRegion

        from modules.compass.view.occlusion import in_front

        hidden = self.hidden_atoms()
        drawn = [k for k in range(len(points)) if k not in hidden]
        front = in_front(i, [(q.x(), q.y()) for q, _ in points], [z for _, z in points], radii, reach, drawn)
        if not front:
            return None
        c = points[i][0]
        region = QRegion(int(c.x() - reach) - 2, int(c.y() - reach) - 2, int(2 * reach) + 5, int(2 * reach) + 5)
        for j in front:
            q, rj = points[j][0], radii[j]
            region = region.subtracted(QRegion(round(q.x() - rj), round(q.y() - rj), round(2 * rj), round(2 * rj),
                                               QRegion.RegionType.Ellipse))
        return region

    def hit_test(self, point):
        points = self.projected()
        hidden = self.hidden_atoms()
        for i in sorted(range(len(points)), key=lambda i: points[i][1], reverse=True):
            if i in hidden:
                continue
            if hypot(point.x() - points[i][0].x(), point.y() - points[i][0].y()) <= self.atom_radius(i) + 5:
                return i
        return None

    def bond_at(self, point):
        """(i, j) of the drawn bond nearest to point, within a few pixels of its line, else None."""
        if not self.molecule or not self.molecule.atoms or self.display_mode == 'spacefill' or not self.show_bonds:
            return None
        points = self.projected()
        best = None
        for i, j, _ in self.drawn_bonds():
            a, b = points[i][0], points[j][0]
            dx = b.x() - a.x()
            dy = b.y() - a.y()
            length2 = dx * dx + dy * dy
            if length2 < 1:
                continue
            t = ((point.x() - a.x()) * dx + (point.y() - a.y()) * dy) / length2
            if not 0 < t < 1:
                continue
            d = hypot(point.x() - a.x() - t * dx, point.y() - a.y() - t * dy)
            if d <= max(6, self.bond_width * self.camera()[1] * 0.08) and (best is None or d < best[0]):
                best = (d, i, j)
        return None if best is None else best[1:]

    def hbond_at(self, point):
        """(H, acceptor) of the dotted hydrogen bond nearest to point, within a few pixels of its line."""
        if not self.molecule or not self.molecule.atoms or not self.show_hbonds:
            return None
        points = self.projected()
        hidden = self.hidden_atoms()
        best = None
        for h, a in self.hydrogen_bonds():
            if h in hidden:
                continue
            p, q = points[h][0], points[a][0]
            dx, dy = q.x() - p.x(), q.y() - p.y()
            length2 = dx * dx + dy * dy
            if length2 < 1:
                continue
            t = ((point.x() - p.x()) * dx + (point.y() - p.y()) * dy) / length2
            if not 0.1 < t < 0.9:  # not over the balls at its ends
                continue
            d = hypot(point.x() - p.x() - t * dx, point.y() - p.y() - t * dy)
            if d <= 5 and (best is None or d < best[0]):
                best = (d, h, a)
        return None if best is None else best[1:]

    _empty_click = _mouse._empty_click

    def near_axes(self, point):
        """The point is on the corner axes and they may be moved."""
        if not (self.axes_movable and self.show_axes and self.axes_place == 'corner'):
            return False
        centre, radius = self.axes_ring()
        delta = point - centre
        return delta.x() ** 2 + delta.y() ** 2 <= radius ** 2

    mousePressEvent = _mouse.mousePressEvent
    move_group = _mouse.move_group

    TWIST_DEG_PER_PX = 0.5

    mouseMoveEvent = _mouse.mouseMoveEvent

    AIM_START_PX = 14  # the cursor this far from the atom pressed before the new bond has a direction

    aim_at = _mouse.aim_at
    snap_target = _mouse.snap_target
    mouseReleaseEvent = _mouse.mouseReleaseEvent
    wheelEvent = _mouse.wheelEvent

    def event(self, event):
        from PySide6.QtCore import QEvent

        if event.type() == QEvent.Type.NativeGesture and event.gestureType() == Qt.NativeGestureType.ZoomNativeGesture:
            self.zoom_view(max(0.5, min(2.0, 1 + event.value())))
            return True
        return super().event(event)

    mouseDoubleClickEvent = _mouse.mouseDoubleClickEvent
    center_view = _camera.center_view
    best_view = _camera.best_view
    look_along = _camera.look_along
    export_document = _camera.export_document
    zoom_view = _camera.zoom_view
    pan_view = _camera.pan_view
    screenshot = _camera.screenshot
    render_image = _camera.render_image
    rotate_screen = _camera.rotate_screen
    rotate_view = _camera.rotate_view
    reset_view = _camera.reset_view
    set_inset = _camera.set_inset

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            self.center_view()
            event.accept()
            return
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.deleteRequested.emit()
        else:
            super().keyPressEvent(event)

    isotope_source = None  # a callable -> Calculation.isotopes of the window (the atoms shown as D, ¹³C …)

    shown_symbol = _painting.shown_symbol
    atom_label = _painting.atom_label
    paintEvent = _painting.paintEvent
    field_color = _painting.field_color
    _paint = _painting._paint
    _paint_under = _painting._paint_under
    _paint_over = _painting._paint_over
    draw_atom_label = _painting.draw_atom_label
    paint_silhouette = _painting.paint_silhouette
    paint_over_native = _painting.paint_over_native

    # -- QTAIM on the model -------------------------------------------------------------------------------
    AIM_COLOURS = {'bond': '#2e9e5b', 'ring': '#e0882c', 'cage': '#8e5bd0', 'nucleus': '#5a6b7d'}  # nuclei
    INSET_MS = 320  # the model moves aside with the drawer as long as it slides (220 → 320, its curve)
    PULSE_PERIOD = 1.2  # s, one widening and narrowing of the ring of the chosen point
    PULSE_INTERVAL = 45  # ms between the frames
    PULSE_RADII = (6.5, 15.0)  # px, the narrowest and the widest ring

    def pulse_radius(self, now=None):
        """The radius (px) and the opacity (0…1) of the ring of the chosen critical point at the moment now."""
        phase = ((monotonic() if now is None else now) % self.PULSE_PERIOD) / self.PULSE_PERIOD
        grow = 0.5 * (1.0 - cos(2.0 * 3.141592653589793 * phase))
        low, high = self.PULSE_RADII
        return low + (high - low) * grow, 1.0 - 0.55 * grow

    def _pulse_tick(self):
        a = self.aim
        if not a or a.get('selected') is None or not self.isVisible():
            self._pulse.stop()
            return
        self.update()

    # -- VTK straight into the window --------------------------------------------------------------
    def set_native(self, on):
        """Draw the model with VTK in a child OpenGL widget (on) or not; True if it is on. Raises nothing: a
        failure leaves it off and keeps the reason in self.native_error."""
        if on and getattr(self, '_native', None) is None:
            try:
                from modules.compass.view.vtk_view import NativeModel

                self._native = NativeModel(self)
                self.native_error = ''
            except Exception as exc:  # noqa: BLE001 — no OpenGL widget of VTK here: the picture path stays
                self._native = None
                self.native_error = f'{type(exc).__name__}: {exc}'
                return False
            self._native.schedule()
        elif not on and getattr(self, '_native', None) is not None:
            self._native.close()
            self._native = None
        QWidget.update(self)
        return getattr(self, '_native', None) is not None

    def native_active(self):
        n = getattr(self, '_native', None)
        return n is not None and n.active

    def update(self, *args):
        QWidget.update(self, *args)
        if self.gliding():  # under the picture of a sliding panel VTK draws nothing (end_glide draws it)
            return
        n = getattr(self, '_native', None)
        if n is not None and n.active:
            n.schedule()

    hold_place = _motion.hold_place
    _release_place = _motion._release_place
    _settle_place = _motion._settle_place

    def moveEvent(self, event):
        super().moveEvent(event)
        if getattr(self, '_held', None) is not None:
            self._settle_place()
            self._follow_now()
            self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._settle_place()
        cover = getattr(self, '_glide_cover', None)
        if cover is not None:  # a panel slides — the picture follows, the model is drawn when it stops
            cover.setGeometry(self.rect())
            return
        n = getattr(self, '_native', None)
        if n is not None and n.active:
            if getattr(self, '_held', None) is not None or self.in_layout_motion():
                self._follow_now()
            else:
                n.schedule()

    LAYOUT_MOTION = 0.25  # s after the last step of a sliding panel

    layout_motion = _motion.layout_motion
    in_layout_motion = _motion.in_layout_motion
    begin_glide = _motion.begin_glide
    end_glide = _motion.end_glide

    FRAME_WAIT = 200  # ms: the longest the picture waits for the frame of VTK at the end of a slide

    gliding = _motion.gliding
    _follow_now = _motion._follow_now
    _without_native = _motion._without_native

    def view_matrix(self):
        """The linear map of to_view as a 3 x 3 matrix (rows: the images of x, y, z)."""
        import numpy as np

        return np.array([self.to_view(e) for e in ((1, 0, 0), (0, 1, 0), (0, 0, 1))], float)

    SURFACE_VEIL = 0.75  # how much of the dot grid the outline of a surface hides (0 — none, 1 — all)

    def screen(self, position):
        """The point on the widget of a position in angstrom (the projection of projected())."""
        center, scale = self.camera()
        x, y, z = self.to_view(tuple(position[k] - center[k] for k in range(3)))
        f = self.depth_factor(z)
        return QPointF(
            self.width() / 2 + self.pan.x() + x * scale * f, self.height() / 2 + self.pan.y() - y * scale * f
        )

    DIPOLE_LENGTH = 0.6  # A of arrow per debye (water, 1.7 D: about 1 A)
    FORCE_LENGTH = 1.0  # A of the arrow of the largest force

    def shift_origin(self, shift):
        """The coordinates lost shift (the structure was centred, builder.centred): the view now turns
        about the new origin, the centre of the structure, and the model stays where it was in the field."""
        center, scale = self.camera()
        x, y, _ = self.to_view(tuple(shift[k] - center[k] for k in range(3)))
        self.pan += QPointF(x * scale, -y * scale)
        self.locked_camera = ((0.0, 0.0, 0.0), scale / self.zoom)
        self.update()

    def rotate_about(self, point):
        """«Центр вращения — выделенные атомы»: the view turns (and zooms) about this point, which comes to the middle
        of the field; «Центровать» goes back to the centre of the molecule."""
        _, scale = self.camera()
        self.locked_camera = (tuple(point), scale / self.zoom)
        self.pan = QPointF(self.inset / 2, 0)
        self.update()

    GUIDE_INKS = {'vector': ('#2aa198', '#5fd3c8'), 'normal': ('#8e5bd0', '#b996ee'), 'plane': ('#2a62b8', '#6ea2f0')}

    COMPARE_INK = ('#e0559b', '#f07ab8')  # light, dark theme: a colour no element uses

    def update_help(self):
        hints = {
            # in the view mode the field shows no tooltip; the modes of editing keep theirs
            'view': '',
            'atom': tr('Щелчок в поле — новый атом · по атому — присоединить'),
            'fragment': tr('Щелчок в поле — фрагмент · по атому — присоединить за атом 1 фрагмента'),
            'molecule': tr('Щелчок в поле — добавить выбранную молекулу'),
            'move': tr('Тяните атом в плоскости экрана · поверните вид, чтобы изменить глубину'),
        }
        if self.mode == 'move':
            hints['move'] = {
                'selection': tr('Тяните выделенные атомы целиком · Shift + протяжка — выделить рамкой'),
                'atom': tr('Тяните атом · правая протяжка — вращение вида'),
                'fragment': tr('Тяните атом — его группа поворачивается вокруг опоры, меняя угол · опора и сторона — выделите два атома'),
                'molecule': tr('Тяните атом — двигается его молекула целиком · протяжка по пустому месту вращает вид'),
                'chain': tr('Тяните атом — двигается неразветвлённый участок цепи до ближайших разветвлений и колец'),
                'twist': tr('Выделите два связанных атома — ось · тяните атом одной из сторон влево-вправо'),
            }[self.move_target]
        self.setToolTip(hints[self.mode])
