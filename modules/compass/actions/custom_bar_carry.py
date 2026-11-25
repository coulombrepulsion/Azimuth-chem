"""Carrying an item of the menus onto the panels of Compass: the picture that follows the mouse, the gap that opens
where it would drop, the drop, the place and the slot of a point. Methods of CustomBar (self is the bar), kept here to
make custom_bar.py shorter.

Split off modules/compass/actions/custom_bar.py (0.222.30).
"""

from PySide6.QtCore import QMimeData, QPoint, Qt
from PySide6.QtGui import QDrag
from PySide6.QtWidgets import QApplication, QHBoxLayout, QMenu, QPushButton, QVBoxLayout, QWidget


TOP, RAIL = 'top', 'rail'


MIME = 'application/x-azimuth-bar-key'


class _HoveredButton(QPushButton):
    """A button always drawn as under the mouse — the picture carried out of a menu has the square of the hover, as
    a button of a panel carried under the mouse (WA_UnderMouse alone did not give it on macOS)."""

    def initStyleOption(self, option):
        super().initStyleOption(option)
        from PySide6.QtWidgets import QStyle

        option.state |= QStyle.StateFlag.State_MouseOver


def close_menus():
    """Every open menu closed (the deepest first)."""
    for _ in range(32):
        popup = QApplication.activePopupWidget()
        if popup is None:
            return
        try:
            popup.close()
        except RuntimeError:
            return


# -- dragging -----------------------------------------------------------------------------------------------------
def _carried_picture(self, key, action, sub):
    """The picture of the button the item will make, as a button of a panel under the mouse."""
    preview = self.make_button(key, action, sub, _HoveredButton)
    preview.setParent(self.card)
    preview.hide()
    preview.ensurePolished()
    preview.resize(preview.sizeHint().expandedTo(preview.minimumSize()))
    picture = preview.grab()
    preview.deleteLater()
    return picture


def _begin(self, key, picture):
    """The state of a carry: the key, the pale copy for the gap, the places of the buttons before the gaps move them."""
    self._ghost_picture = _faded(picture, 0.3)
    self._dragged = key
    self._centres = {}
    for name, widget in list(self.defaults.items()) + list(self.buttons.items()):
        if not widget.isHidden():
            centre = widget.mapTo(self.card, widget.rect().center())
            self._centres[name] = (centre.x(), centre.y())


def _end(self):
    self.show_slot(None, at_once=True)
    self._ghost_picture = None
    self._centres = None
    self._dragged = None


def drag_item(self, key, action, sub):
    """An item of the menus dragged onto the panels — the menus close, its button (as it will look) is
    carried, a drop on the row or the column puts it there (move: a key not yet on a panel is added at the slot).
    Windows and Linux; macOS carries it in the menu itself (start_carry)."""
    if self.card is None:
        return
    picture = self._carried_picture(key, action, sub)
    close_menus()
    data = QMimeData()
    data.setData(MIME, str(key).encode('utf-8'))
    drag = QDrag(self.card)
    drag.setMimeData(data)
    drag.setPixmap(picture)
    drag.setHotSpot(QPoint(picture.width() // 2, picture.height() // 2))
    self._begin(key, picture)
    try:
        self.exec_drag(drag)
    finally:
        self._end()


def carrying(self, menu=None):
    carry = getattr(self, '_carry', None)
    return carry is not None and (menu is None or carry['menu'] is menu)


def start_carry(self, menu, key, action, sub):
    if self.card is None:
        return
    picture = self._carried_picture(key, action, sub)
    from PySide6.QtWidgets import QLabel

    follower = QLabel(None, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
    follower.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    follower.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    follower.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
    follower.setStyleSheet('background: transparent; border: none;')
    follower.setPixmap(picture)
    follower.resize(picture.deviceIndependentSize().toSize())
    for popup in [w for w in QApplication.topLevelWidgets()
                  if isinstance(w, QMenu) and w.isVisible() and w.windowType() == Qt.WindowType.Popup]:
        try:
            popup.setWindowOpacity(0.0)  # out of sight, still open: it keeps the mouse
        except RuntimeError:
            pass
    self._begin(key, picture)
    self._carry = {'menu': menu, 'key': key, 'follower': follower}
    from PySide6.QtGui import QCursor

    self.carry_move(QCursor.pos())
    follower.show()


def carry_move(self, point):
    """point: global. The picture follows, the gap opens where a drop would put the button."""
    carry = getattr(self, '_carry', None)
    if carry is None:
        return
    follower = carry['follower']
    follower.move(point - QPoint(follower.width() // 2, follower.height() // 2))
    self.show_slot(self.slot(self.card.mapFromGlobal(point)))


def carry_drop(self, point):
    carry = getattr(self, '_carry', None)
    if carry is None:
        return
    slot = self.slot(self.card.mapFromGlobal(point))
    self._finish_carry()
    if slot is not None:
        self.move(carry['key'], slot)


def carry_cancel(self):
    if getattr(self, '_carry', None) is not None:
        self._finish_carry()


def _finish_carry(self):
    carry, self._carry = self._carry, None
    try:
        carry['follower'].close()
        carry['follower'].deleteLater()
    except RuntimeError:
        pass
    self._end()
    close_menus()


def drag(self, button):
    key = button.property('azimuthBarKey')
    if not key or self.card is None:
        return
    data = QMimeData()
    data.setData(MIME, str(key).encode('utf-8'))
    drag = QDrag(button)
    drag.setMimeData(data)
    picture = button.grab()
    drag.setPixmap(picture)
    drag.setHotSpot(QPoint(button.width() // 2, button.height() // 2))
    button.setDown(False)
    self._ghost_picture = _faded(picture, 0.3)
    self._dragged = key
    self._centres = {}  # the places of the buttons as the drag begins — the gaps move them, not the slots
    for key, widget in list(self.defaults.items()) + list(self.buttons.items()):
        if not widget.isHidden():
            centre = widget.mapTo(self.card, widget.rect().center())
            self._centres[key] = (centre.x(), centre.y())
    try:
        drag.exec(Qt.DropAction.MoveAction)
    finally:
        self.show_slot(None, at_once=True)
        self._ghost_picture = None
        self._centres = None
        self._dragged = None


def _gap_index(self, slot):
    """The index in the layout of the place where the gap of slot opens."""
    area = self.areas[slot[1]]
    groups = self.groups()[slot[1]]

    def widget(key):
        w = self.defaults.get(key) or self.buttons.get(key)
        return w if w is not None and not w.isHidden() and area.indexOf(w) >= 0 else None

    if slot[0] == 'into':
        member, before = slot[2], slot[3]
        if before is not None and widget(before) is not None:
            return area.indexOf(widget(before))
        group = next((g for g in groups if member in g), [])
        last = next((widget(k) for k in reversed(group) if widget(k) is not None), None)
        if last is not None:
            return area.indexOf(last) + 1
    return area.count()


def _make_gap(self, slot):
    place = slot[1]
    vertical = place == RAIL
    box = QWidget()
    box.setProperty('azimuthBarGap', True)
    box.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    layout = QVBoxLayout(box) if vertical else QHBoxLayout(box)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    if slot[0] == 'new' and any(self.areas[place].itemAt(k).widget() is not None
                                for k in range(self.areas[place].count())):
        layout.addWidget(self._rule(place), 0, Qt.AlignmentFlag.AlignCenter)  # the line of a group of its own
    from PySide6.QtWidgets import QLabel

    ghost = QLabel()
    ghost.setPixmap(self._ghost_picture)
    layout.addWidget(ghost, 0, Qt.AlignmentFlag.AlignCenter)
    full = layout.sizeHint().height() if vertical else layout.sizeHint().width()
    area = self.areas[place]
    index = min(self._gap_index(slot), area.count())
    if vertical:
        box.setFixedHeight(0)
        area.insertWidget(index, box, 0, Qt.AlignmentFlag.AlignHCenter)
    else:
        box.setFixedWidth(0)
        area.insertWidget(index, box)
    return box, full


def _size_gap(self, box, start, end, done=None):
    from PySide6.QtCore import QEasingCurve, QVariantAnimation

    vertical = box.property('azimuthBarVertical')
    motion = QVariantAnimation(box)
    motion.setDuration(self.GLIDE_MS)
    motion.setEasingCurve(QEasingCurve.Type.OutCubic)
    motion.setStartValue(float(start))
    motion.setEndValue(float(end))

    def step(value):
        try:
            (box.setFixedHeight if vertical else box.setFixedWidth)(int(round(value)))
        except RuntimeError:
            motion.stop()

    motion.valueChanged.connect(step)
    if done is not None:
        motion.finished.connect(done)
    box._motion = motion
    motion.start()


def _close_gap(self, box, at_once=False):
    def gone():
        try:
            for area in self.areas.values():
                if area.indexOf(box) >= 0:
                    area.removeWidget(box)
            box.hide()
            box.deleteLater()
        except RuntimeError:
            pass

    try:
        if at_once or not box.isVisible():
            gone()
            return
        vertical = box.property('azimuthBarVertical')
        self._size_gap(box, box.height() if vertical else box.width(), 0, gone)
    except RuntimeError:
        pass


def show_slot(self, slot, at_once=False):
    """The gap of slot opened (None: the gap closed)."""
    if self.card is None:
        return
    current = getattr(self, '_gap', None)
    if slot is not None and getattr(self, '_ghost_picture', None) is None:
        slot = None
    dragged = getattr(self, '_dragged', None)
    if slot is not None and dragged is not None and self.moved(dragged, slot) is None:
        slot = None  # brought back to where it stands — no gap, no copy
    if current is not None and current[0] == slot:
        return
    if current is not None:
        self._close_gap(current[1], at_once)
        self._gap = None
    if slot is None:
        return
    box, full = self._make_gap(slot)
    box.setProperty('azimuthBarVertical', slot[1] == RAIL)
    self._gap = (slot, box)
    self._size_gap(box, 0, full)


def place_at(self, point):
    """TOP or RAIL for a point of the card, None elsewhere."""
    card, rail = self.card, self.rail_widget
    if card is None:
        return None
    if rail is not None and rail.isVisible():
        corner = rail.mapTo(card, QPoint(0, 0))
        if corner.x() - 8 <= point.x() <= corner.x() + rail.width() + 8 and point.y() >= corner.y() - 4:
            return RAIL
    if self.row is not None:
        row = self.row.geometry()  # the row above the field, in the coordinates of the card
        left_of_rail = rail is None or point.x() < rail.mapTo(card, QPoint(0, 0)).x() - 8
        if row.top() - 6 <= point.y() <= row.bottom() + 6 and left_of_rail:
            return TOP
    return None


def slot(self, point):
    """Where a drop at point of the card goes: ('into', place, member, before) — among the buttons of a group (or
    at its end, when the point is between its last button and the line after it); ('new', place) — after the last
    button of the place, a group of its own."""
    place = self.place_at(point)
    if place is None:
        return None
    vertical = place == RAIL
    along = (lambda p: p.y()) if vertical else (lambda p: p.x())
    groups = self.groups()[place]
    shown = []  # (key, its group, centre along, its far edge)
    for group in groups:
        for key in group:
            widget = self.defaults.get(key) or self.buttons.get(key)
            if widget is None or widget.isHidden():
                continue
            frozen = getattr(self, '_centres', None)
            if frozen is not None and key in frozen:
                shown.append((key, group, frozen[key][1] if vertical else frozen[key][0]))
                continue  # where it stood before the gaps of the drag moved it
            centre = widget.mapTo(self.card, widget.rect().center())
            shown.append((key, group, along(centre)))
    c = along(point)
    for n, (key, group, centre) in enumerate(shown):
        if c < centre:
            if n and shown[n - 1][1] is not group:  # between two groups: the line decides
                prev_key, prev_group, prev_centre = shown[n - 1]
                line = (prev_centre + centre) / 2
                if c < line:
                    return ('into', place, prev_key, None)  # at the end of the group before the line
            return ('into', place, key, key)
    return ('new', place)


def _faded(picture, opacity):
    """A copy of picture with the given opacity (the pale button at the place it will take)."""
    from PySide6.QtGui import QPainter, QPixmap

    out = QPixmap(picture.size())
    out.setDevicePixelRatio(picture.devicePixelRatio())
    out.fill(Qt.GlobalColor.transparent)
    painter = QPainter(out)
    painter.setOpacity(opacity)
    painter.drawPixmap(0, 0, picture)
    painter.end()
    return out
