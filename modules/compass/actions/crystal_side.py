"""The side panel of Compass beside the model: the crystal window docked in it, the kind shown, its buttons, the panel
sliding out and back in with its picture over it, the folding on a click past the atoms. Methods of CrystalTool (self
is the tool; the window only through its port self.w), kept here to make crystal_actions.py shorter.

Split off modules/compass/actions/crystal_actions.py (0.222.30).
"""

from modules.compass.chemistry import crystal_contacts as cc


KEPT_PANELS = ('CrystalWindow', 'ContactsWindow', 'HirshfeldWindow')  # folded, not deleted (CrystalTool.close_side)


def dock(self, dialog):
    """The window put into the side panel next to the field (layout: crystal_side),
    one at a time — the model stays in sight; its «Закрыть» folds the panel. Without the panel (a test, another
    window) it is shown as a window. Returns the dialog."""
    from PySide6.QtCore import Qt

    side = getattr(self.w, 'crystal_side', None) if self.w.has('crystal_side') else None
    if side is None:
        dialog.show()
        return dialog
    self.close_side(keep=dialog)
    dialog.setParent(side)
    dialog.setWindowFlags(Qt.WindowType.Widget)
    side.layout().addWidget(dialog)
    dialog.finished.connect(lambda *_: self.close_side() if self.side_dialog() is dialog else None)
    dialog.show()
    self._side_dialog = dialog
    self.slide_side(True)
    self.sync_side_buttons()
    return dialog


def side_dialog(self):
    return getattr(self, '_side_dialog', None)


def side_kind(self):
    """The kind of the panel shown beside the model ('crystal', 'contacts'…), or None."""
    dialog = self.side_dialog()
    if dialog is None or dialog.isHidden():
        return None
    name = type(dialog).__name__
    return next((kind for kind, cls in self.SIDE_KINDS.items() if cls == name), None)


def toggle_side(self, kind, opener):
    """The button of a panel: pressed while its panel is shown — the panel folds; else opener() opens it."""
    from azimuth.tasks import held

    if held():  # a work of the panel goes on (the Hirshfeld surface) — a second press waits for it
        return None
    if self.side_kind() == kind:
        self.close_side()
        return None
    try:
        return opener()
    finally:
        self.sync_side_buttons()


def sync_side_buttons(self):
    """The buttons of the panels lit while their panel is shown."""
    buttons = getattr(self.w, 'crystal_buttons', ()) if self.w.has('crystal_buttons') else ()
    shown = self.side_kind()
    for kind, place in self.SIDE_BUTTONS.items():
        if place < len(buttons):
            item = buttons[place]
            if not item.isCheckable():
                item.setCheckable(True)
            item.setChecked(kind == shown)


def empty_field_clicked(self):
    """A click on the field past the atoms folds the panel beside the model."""
    from azimuth.tasks import held

    if self.side_kind() is not None and not held():
        self.close_side()


def close_side(self, keep=None):
    """The panel folded; the window in it (but keep) taken away."""
    side = getattr(self.w, 'crystal_side', None) if self.w.has('crystal_side') else None
    old = self.side_dialog()
    if side is not None and keep is None:
        self._ghost_side()  # the picture that goes back, taken while the window is still in the panel
    if old is not None and old is not keep:
        self._side_dialog = None
        try:
            old.hide()
            old.setParent(None)
            # the «Кристалл» panel is kept (window.crystal_window, the parent of its contacts and
            # powder windows: «Искать снова» of the contacts docked over it asks it again)
            # the contacts and the Hirshfeld surface are kept too — the
            # same panel comes back with what it found (their openers reuse it for the same crystal)
            if type(old).__name__ not in KEPT_PANELS:
                old.deleteLater()
        except RuntimeError:
            pass
    if side is not None and keep is None:
        self.slide_side(False)
    if keep is None:
        self.sync_side_buttons()


def slide_side(self, opened):
    """The side panel comes out and goes back in SLIDE_MS (InOutCubic, even steps, the field slides as one picture —
    as the panel of the molecules of the project, project_navigation.slide_project_pane). A picture of the panel
    slides both ways — opening, the panel is laid out once at its width and drawn into the picture, which covers it
    (opaque: the panel under it is not painted at every step); the scales of the window are pictures too
    (freeze_ornaments), and the slide starts on the next turn of the loop, after the layout and the painting that
    the new panel asked for (the first frames of the curve jumped over them). Folding, the panel is hidden at once.
    Without the box (or the window not shown) — at once."""
    from PySide6.QtCore import QEasingCurve, QTimer, QVariantAnimation

    from azimuth.project_widgets import even_step
    from azimuth.ui import freeze_ornaments
    from modules.compass.panels.trajectory_drawer import SLIDE_MS

    side = self.w.crystal_side
    box = side.parentWidget()
    if box is None or box.objectName() != 'crystalSideSlide':
        side.setVisible(opened)
        return
    motion = getattr(self, '_side_motion', None)
    if motion is not None:
        self._side_motion = None
        motion.stop()
    shown = self.w.widget.isVisible()
    if opened:
        hint = side.sizeHint().width()
        width = max(side.minimumWidth(), min(side.maximumWidth(), hint))
        side.slide_width = width
        side.show()
        box.show()
        box.place()  # the panel at its width (clipped by the box): laid out once, here
        if shown and box.width() != width:
            if side.layout() is not None:
                side.layout().activate()
            self._ghost_side(force=True)
    else:
        width = 0
        if getattr(self, '_side_ghost', None) is None:
            self._ghost_side()
        side.hide()
    viewer = self.w.viewer
    holder = box.parentWidget()

    def settle():
        box.setFixedWidth(width)
        box.setVisible(bool(width))
        if holder is not None and holder.layout() is not None:
            holder.layout().activate()

    if not shown or box.width() == width:
        self._drop_side_ghost()
        settle()
        if hasattr(viewer, 'end_glide'):
            viewer.end_glide()  # a slide stopped half-way began a glide
        if getattr(self, '_side_frozen', False):
            self._side_frozen = False
            freeze_ornaments(self.w.widget, False)
        return
    if hasattr(viewer, 'begin_glide'):
        viewer.begin_glide()
    if not getattr(self, '_side_frozen', False):
        self._side_frozen = True
        freeze_ornaments(self.w.widget)

    def step(value):
        if box.width() == value:
            return
        if hasattr(viewer, 'layout_motion'):
            viewer.layout_motion()
        box.setFixedWidth(value)
        if holder is not None and holder.layout() is not None:
            holder.layout().activate()

    motion = QVariantAnimation(box)
    motion.setDuration(SLIDE_MS)
    motion.setEasingCurve(QEasingCurve.Type.InOutCubic)
    motion.setStartValue(box.width())
    motion.setEndValue(width)
    motion.valueChanged.connect(lambda value: step(even_step(value)))

    def done():
        if self._side_motion is not motion:
            return
        self._side_motion = None
        self._drop_side_ghost()
        settle()
        if getattr(self, '_side_frozen', False):
            self._side_frozen = False
            freeze_ornaments(self.w.widget, False)
        if hasattr(viewer, 'end_glide'):
            viewer.end_glide()

    def begin():
        if self._side_motion is motion:
            motion.start()

    motion.finished.connect(done)
    self._side_motion = motion
    QTimer.singleShot(0, begin)


def _ghost_side(self, force=False):
    """A picture of the side panel over it in its box, opaque (what is under it is not painted while it slides);
    force — also while the box is still folded (the panel opening, laid out at its width)."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QLabel

    self._drop_side_ghost()
    side = self.w.crystal_side
    box = side.parentWidget()
    if box is None or box.objectName() != 'crystalSideSlide' or side.isHidden() or not self.w.widget.isVisible() \
            or not (force or (box.isVisible() and box.width() > 0)):
        return
    try:
        ghost = QLabel(box)
        ghost.setPixmap(side.grab())
        ghost.setAutoFillBackground(True)
        ghost.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        ghost.setGeometry(side.geometry())
        ghost.show()
        ghost.raise_()
        self._side_ghost = ghost
    except RuntimeError:
        self._side_ghost = None


def _drop_side_ghost(self):
    ghost = getattr(self, '_side_ghost', None)
    self._side_ghost = None
    if ghost is not None:
        try:
            ghost.hide()
            ghost.deleteLater()
        except RuntimeError:
            pass


def show_contacts_on_model(self, data, found, kinds=None, select=False):
    """The contacts found drawn on the model (the dashed lines of the QTAIM contacts: hydrogen bonds in
    their style, σ-hole bonds in their colours) where both atoms are on it; select — their atoms selected too.
    Returns the number of lines."""
    molecule = self.w.viewer.molecule
    if molecule is None or not molecule.atoms:
        return 0
    try:
        pairs = cc.model_contacts(molecule, data, found, kinds)
    except (ValueError, IndexError):
        pairs = []
    self.w.viewer.found_contacts = {'atoms': molecule.atoms, 'contacts': pairs} if pairs else None
    if select and pairs:
        self.w.viewer.set_selection(sorted({k for i, j, _ in pairs for k in (i, j)}))
    self.w.viewer.update()
    return len(pairs)


def hidden_window(self):
    """The «Кристалл» window of the shown crystal, not shown — for the buttons of the panel."""
    return self.reopen_crystal(show=False)


def show_contacts(self, normalize=None):
    window = self.hidden_window()
    return window.show_contacts(normalize) if window is not None else None


def show_qe(self):
    window = self.hidden_window()
    return window.show_qe() if window is not None else None


def show_powder(self):
    window = self.hidden_window()
    return window.show_powder() if window is not None else None
