"""The user's own buttons in Compass.
The row above the field (top) and the column at its right edge (rail) are groups of buttons parted by thin lines. Any
item of the menus of the window — a command or a submenu — becomes a button: a right click on it in its menu adds it as
a group of its own at the end of the row or of the column. A right click on a button takes it away, moves it to the
other place, or puts every button back as it was; the buttons that stand there from the start can be taken away too.
A button is dragged with the mouse. Dropped among the buttons of
a group it joins that group; dropped after the last button of the place it stands after a new line, a group of its own.
Kept in the settings as the groups of both places by the Russian path of a menu item («Вид/Отображение связей/Стиль
связей…») or «default:<name>» of a button from the start, so the language of the program does not matter."""

from azimuth.ui import rounded  # menus with rounded corners
import json
import sys

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QMenu, QPushButton, QVBoxLayout, QWidget

from azimuth.i18n import to_source, tr
from modules.compass.actions import custom_bar_carry as _carry
from modules.compass.actions.custom_bar_carry import MIME, RAIL, TOP, close_menus

LAYOUT = 'compass_bar_layout'  # {"top": [[key, …], …], "rail": […], "known": [default keys]}
OLD = {TOP: 'compass_bar_top', RAIL: 'compass_bar_rail'}  # 0.206.0–0.206.2
OLD_HIDDEN = 'compass_bar_hidden'


def _showing(widget):
    """The button will show: not hidden on purpose. A
    button just made, or one of a window not shown yet, is «hidden» to Qt (isHidden) until the event loop shows it — the
    line next to it was taken for a line at an end and hidden for good: no line before a button put on a panel, none
    between «Снимок» and the results in the column at the right."""
    return not (widget.isHidden() and widget.testAttribute(Qt.WidgetAttribute.WA_WState_ExplicitShowHide))


def clean(text):
    return (text or '').replace('&', '').strip()


def walk(menu, path=()):
    """(key, action, submenu or None) of every item of menu and of its submenus; the key is the Russian path."""
    from PySide6.QtWidgets import QWidgetAction

    for action in menu.actions():
        # not the field of «Справка → Поиск» nor its results (hub/menu_search.py) — no button of them
        if action.isSeparator() or isinstance(action, QWidgetAction) or action.property('menuSearchResult'):
            continue
        title = to_source(clean(action.text()))
        if not title:
            continue
        here = path + (title,)
        sub = action.menu()
        yield '/'.join(here), action, sub
        if sub is not None:
            yield from walk(sub, here)


def _json(preferences, name, empty):
    raw = preferences.value(name, None) if preferences is not None else None
    if raw is None:
        return empty
    if isinstance(raw, (list, dict)):
        return raw
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return empty


class _MenuClicks(QObject):
    """A right click on an item of a menu: «Добавить на панель…» (the menus of the window and those they open).
    An item pressed and moved
    with the mouse is dragged out of its menu onto the row above the field or the column at its right."""

    def __init__(self, bar):
        super().__init__()
        self.bar = bar
        self.pressed = None  # (menu, point, action) of a left press on an item

    def _drag(self, obj, event):
        """Left press and move on an item of a menu: True when it became a drag."""
        kind = event.type()
        if self.bar.carrying() and kind in (QEvent.Type.MouseMove, QEvent.Type.MouseButtonRelease):
            point = event.globalPosition().toPoint()
            if kind == QEvent.Type.MouseMove:
                self.bar.carry_move(point)
            else:
                self.bar.carry_drop(point)
            return True
        if kind == QEvent.Type.MouseButtonPress and self.bar.carrying():
            return True
        if kind == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            point = event.position().toPoint()
            self.pressed = (obj, point, obj.actionAt(point))
            return False
        if kind == QEvent.Type.MouseButtonRelease:
            self.pressed = None
            return False
        if kind != QEvent.Type.MouseMove or self.pressed is None or self.pressed[0] is not obj \
                or not event.buttons() & Qt.MouseButton.LeftButton:
            return False
        if (event.position().toPoint() - self.pressed[1]).manhattanLength() < QApplication.startDragDistance():
            return False
        action = self.pressed[2]
        self.pressed = None
        if action is None or action.isSeparator() or not action.isEnabled():
            return False
        key = self.bar.key_of(action)
        if key is None:
            return False
        if self.bar.already(key, action) is not None:  # a second button of the same is not made
            self.bar.refuse(key, action)
            return True
        if self.bar.CARRY_IN_MENU:
            self.bar.start_carry(obj, key, action, action.menu())
        else:
            self.bar.drag_item(key, action, action.menu())
        return True

    def eventFilter(self, obj, event):
        kind = event.type()
        if isinstance(obj, QMenu) and kind in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease,
                                               QEvent.Type.MouseMove):
            try:
                if self._drag(obj, event):
                    return True
            except RuntimeError:
                self.pressed = None
        if kind == QEvent.Type.Hide and isinstance(obj, QMenu) and self.bar.carrying(obj):
            self.bar.carry_cancel()  # Escape, or the menu closed otherwise while its item was carried
            return False
        if kind == QEvent.Type.Show and isinstance(obj, QMenu):
            try:
                for action in obj.actions():
                    sub = action.menu()
                    if sub is not None:
                        self.bar.watch(sub)
            except RuntimeError:
                pass
            return False
        if kind not in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease) or not isinstance(obj, QMenu):
            return False
        if event.button() != Qt.MouseButton.RightButton:
            return False
        if kind == QEvent.Type.MouseButtonPress:
            return obj.actionAt(event.position().toPoint()) is not None  # the release decides
        try:
            action = obj.actionAt(event.position().toPoint())
            if action is None or action.isSeparator():
                return False
            key = self.bar.key_of(action)
            if key is None:
                return False
            self.bar.offer(key, obj.mapToGlobal(event.position().toPoint()))
            return True
        except RuntimeError:
            return False


class _Drags(QObject):
    """A button pressed and moved with the mouse is dragged (its key in the drag); the card of the field takes the
    drop — at the slot of the row or of the column nearest to the cursor."""

    def __init__(self, bar):
        super().__init__()
        self.bar = bar
        self.pressed = None

    def eventFilter(self, obj, event):
        kind = event.type()
        try:
            if kind == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                self.pressed = (obj, event.position().toPoint())
            elif kind == QEvent.Type.MouseButtonRelease:
                self.pressed = None
            elif kind == QEvent.Type.MouseMove and self.pressed is not None and self.pressed[0] is obj \
                    and event.buttons() & Qt.MouseButton.LeftButton:
                if (event.position().toPoint() - self.pressed[1]).manhattanLength() >= QApplication.startDragDistance():
                    self.pressed = None
                    self.bar.drag(obj)
                    return True
            elif kind in (QEvent.Type.DragEnter, QEvent.Type.DragMove) and obj is self.bar.card:
                slot = self.bar.slot(event.position().toPoint()) if event.mimeData().hasFormat(MIME) else None
                if slot is not None:
                    event.acceptProposedAction()
                else:
                    event.ignore()
                self.bar.show_slot(slot)  # where it will stand, shown as it is carried
                return True
            elif kind == QEvent.Type.DragLeave and obj is self.bar.card:
                self.bar.show_slot(None)
                return False
            elif kind == QEvent.Type.Drop and obj is self.bar.card:
                self.bar.show_slot(None, at_once=True)  # the button itself takes the gap
                if event.mimeData().hasFormat(MIME):
                    key = bytes(event.mimeData().data(MIME)).decode('utf-8')
                    slot = self.bar.slot(event.position().toPoint())
                    if slot is not None:
                        event.acceptProposedAction()
                        self.bar.move(key, slot)
                        return True
                event.ignore()
                return True
        except RuntimeError:
            pass
        return False


class CustomBar:
    """The groups of buttons of the row above the field (top) and of the column at its right edge (rail)."""

    def __init__(self, window, top, rail, defaults, modes=None):
        """top, rail: the layouts the groups are laid in; defaults: {TOP: [[key, …], …], RAIL: […]} — the groups of
        the buttons from the start (keys «default:<name>»; register gives their widgets). modes
        {'crystal': defaults of its own} — «Компас · Кристалл» has a panel of its own, kept apart (layout_key)."""
        self.w = window
        self.areas = {TOP: top, RAIL: rail}
        self.mode_defaults = {'molecule': {place: [list(g) for g in groups] for place, groups in defaults.items()}}
        for mode, groups in (modes or {}).items():
            self.mode_defaults[mode] = {place: [list(g) for g in groups[place]] for place in (TOP, RAIL)}
        self.defaults = {}  # key → the button that stands there from the start
        self.buttons = {}  # key → the button made for an item of the menus
        self.rules = []  # the lines between the groups, as laid
        self.clicks = _MenuClicks(self)
        self.drags = _Drags(self)
        self.watched = set()
        self.header_menus = []  # [(title, QMenu)] of the header of the hub — items of their own there too
        self.card = None
        self.rail_widget = None
        self.row = None

    def enable(self, card, rail_widget, row):
        """The drops on the card of the field; row — the layout of the row above the field (where a drop counts)."""
        self.card, self.rail_widget, self.row = card, rail_widget, row
        card.setAcceptDrops(True)
        card.installEventFilter(self.drags)

    def register(self, name, widget):
        key = 'default:' + name
        self.defaults[key] = widget
        widget.setProperty('azimuthBarKey', key)
        widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        widget.customContextMenuRequested.connect(lambda pos, k=key, w=widget: self.button_menu(k, w, pos))
        widget.installEventFilter(self.drags)

    # -- the settings -------------------------------------------------------------------------------------------------
    def mode(self):
        """'crystal' in «Компас · Кристалл» (when it has a panel of its own), else 'molecule'."""
        mode = getattr(self.w, 'compass_mode', 'molecule')
        return mode if mode in self.mode_defaults else 'molecule'

    @property
    def default_groups(self):
        return self.mode_defaults[self.mode()]

    def layout_key(self):
        mode = self.mode()
        return LAYOUT if mode == 'molecule' else f'{LAYOUT}_{mode}'

    def foreign(self):
        """The buttons from the start of the other panels only — not laid on this one (the cell and the tools of a
        crystal in a molecule, the constraints and the dipole in a crystal)."""
        mine = {k for g in self.default_groups[TOP] + self.default_groups[RAIL] for k in g}
        others = {k for groups in self.mode_defaults.values() for g in groups[TOP] + groups[RAIL] for k in g}
        return others - mine

    def groups(self):
        """{TOP: [[key, …], …], RAIL: […]} as kept (those of 0.206.0–0.206.2 carried over), new buttons from the start
        put in their groups; of the panel of the mode shown."""
        preferences = getattr(self.w, 'preferences', None)
        kept = _json(preferences, self.layout_key(), None)
        foreign = self.foreign()
        if isinstance(kept, dict) and isinstance(kept.get(TOP), list) and isinstance(kept.get(RAIL), list):
            out = {place: [[str(k) for k in g if str(k) not in foreign] for g in kept[place] if isinstance(g, list) and g]
                   for place in (TOP, RAIL)}
            out = {place: [g for g in groups if g] for place, groups in out.items()}
            known = set(kept.get('known') or ())
        elif self.mode() != 'molecule':  # a panel of its own not changed yet: as from the start
            out = {place: [list(g) for g in self.default_groups[place]] for place in (TOP, RAIL)}
            known = set(self.defaults)
        else:  # before the buttons from the start minus the hidden ones, the chosen ones a group after them
            hidden = set(_json(preferences, OLD_HIDDEN, []) or [])
            chosen = {place: [str(k) for k in (_json(preferences, OLD[place], []) or [])] for place in (TOP, RAIL)}
            moved = set(chosen[TOP]) | set(chosen[RAIL])
            out = {place: [[k for k in g if k not in hidden and k not in moved] for g in self.default_groups[place]]
                   for place in (TOP, RAIL)}
            for place in (TOP, RAIL):
                out[place] = [g for g in out[place] if g]
                if chosen[place]:
                    out[place].append(chosen[place])
            known = set(self.defaults)
        for place in (TOP, RAIL):  # a button from the start that came with a new version: in its group
            for group in self.default_groups[place]:
                for key in group:
                    if key in known or key not in self.defaults:
                        continue
                    home = next((g for g in out[place] if any(k in group for k in g)), None)
                    if home is None:
                        out[place].append([key])
                    else:
                        home.append(key)
        return out

    def save(self, groups):
        preferences = getattr(self.w, 'preferences', None)
        if preferences is None:
            return
        data = {place: [list(g) for g in groups[place] if g] for place in (TOP, RAIL)}
        data['known'] = sorted(self.defaults)
        preferences.setValue(self.layout_key(), json.dumps(data, ensure_ascii=False))

    def where(self, key, groups=None):
        groups = groups or self.groups()
        return next((place for place in (TOP, RAIL) for g in groups[place] if key in g), None)

    # -- the menus ----------------------------------------------------------------------------------------------------
    def items(self):
        """(key, action, submenu or None) of every item of the menus of the window, then of those of the header of the
        hub that the window has not."""
        bar = self.w.menuBar() if hasattr(self.w, 'menuBar') else None
        seen = set()
        if bar is not None:
            for action in bar.actions():
                if action.menu() is not None:
                    for key, a, sub in walk(action.menu()):
                        seen.add(id(a))
                        yield f'{to_source(clean(action.text()))}/{key}', a, sub
        for title, menu in self.header_menus:
            try:
                found = [(f'{to_source(clean(title))}/{key}', a, sub) for key, a, sub in walk(menu)]
            except RuntimeError:  # a menu of the header already deleted
                continue
            for key, a, sub in found:
                if id(a) not in seen:
                    seen.add(id(a))
                    yield key, a, sub

    def set_header_menus(self, menus):
        """The menus of the header of the hub (made anew for each section): watched, and the buttons laid again — those
        of items found only there come back with the new actions."""
        self.header_menus = list(menus)
        for _title, menu in self.header_menus:
            self.watch(menu)
        self.rebuild()

    def find(self, key):
        return next(((a, sub) for k, a, sub in self.items() if k == key), (None, None))

    def key_of(self, action):
        return next((k for k, a, sub in self.items() if a is action), None)

    def watch(self, menu):
        """Marked on the menu itself, not by its id — the menus of the header of the hub are made anew for each
        section, and a new menu could take the id of one deleted (it was then never watched)."""
        try:
            if menu.property('azimuthBarWatched'):
                return
            menu.setProperty('azimuthBarWatched', True)
        except RuntimeError:
            return
        menu.installEventFilter(self.clicks)

    def start(self):
        """After the menus are made: their right clicks watched, the groups laid."""
        bar = self.w.menuBar()
        for action in bar.actions():
            if action.menu() is not None:
                self.watch(action.menu())
                for _, a, sub in walk(action.menu()):
                    if sub is not None:
                        self.watch(sub)
        self.rebuild()

    # -- laying the groups --------------------------------------------------------------------------------------------
    def _rule(self, place):
        """A line between two groups, with its margins (it is hidden with them)."""
        box = QWidget()
        box.setProperty('azimuthBarRule', True)
        if place == TOP:
            layout = QHBoxLayout(box)
            layout.setContentsMargins(4, 0, 4, 0)
            line = QFrame()
            line.setObjectName('toolRule')
            line.setFixedSize(1, 22)
        else:
            layout = QVBoxLayout(box)
            layout.setContentsMargins(0, 2, 0, 2)
            line = QFrame()
            line.setObjectName('toolRule')
            line.setFixedSize(22, 1)
        layout.addWidget(line, 0, Qt.AlignmentFlag.AlignCenter)
        return box

    def rebuild(self, panel=True):
        """The groups laid anew; panel — the panel of the mode (crystal_actions.update_panel) asked again too (not while
        the page is being built: the tool is not there yet)."""
        groups = self.groups()
        for place, area in self.areas.items():
            while area.count():
                item = area.takeAt(0)
                widget = item.widget()
                if widget is not None and widget.property('azimuthBarKey') not in self.defaults:
                    widget.hide()
                    widget.deleteLater()
        self.buttons, self.rules = {}, []
        placed = set()
        for place, area in self.areas.items():
            first = True
            for group in groups[place]:
                widgets = []
                for key in group:
                    if key in placed:
                        continue
                    if key in self.defaults:
                        widget = self.defaults[key]
                    else:
                        action, sub = self.find(key)
                        if action is None:
                            continue  # an item gone from the menus (renamed, removed): its button quietly not shown
                        widget = self.buttons[key] = self.make_button(key, action, sub)
                    widgets.append((key, widget))
                    placed.add(key)
                if not widgets:
                    continue
                if not first:
                    rule = self._rule(place)
                    area.addWidget(rule)
                    self.rules.append(rule)
                first = False
                for key, widget in widgets:
                    if place == RAIL:
                        area.addWidget(widget, 0, Qt.AlignmentFlag.AlignHCenter)
                    else:
                        area.addWidget(widget)
        for key, widget in self.defaults.items():
            away = key not in placed
            was = bool(widget.property('azimuthAway'))
            widget.setProperty('azimuthAway', away)
            if away:
                widget.hide()
            elif was:
                widget.show()
        crystal = getattr(self.w, 'crystal_tool', None) if panel else None
        if crystal is not None:  # what a crystal hides stays hidden (the tool of the window: its method directly)
            crystal.update_panel(getattr(self.w, 'compass_mode', 'molecule'))
        self.refresh_rules()

    def refresh_rules(self):
        """A line only between two buttons that show — never two lines in a row, none at an end (a crystal hides some
        buttons, a molecule others)."""
        for area in self.areas.values():
            entries = [area.itemAt(k).widget() for k in range(area.count())]
            entries = [w for w in entries if w is not None]
            rule_flags = [bool(w.property('azimuthBarRule')) for w in entries]
            since = False  # a button shown since the last line shown (or the start)
            for k, widget in enumerate(entries):
                if not rule_flags[k]:
                    since = since or _showing(widget)
                    continue
                later = any(_showing(w) for w, r in zip(entries[k + 1:], rule_flags[k + 1:]) if not r)
                show = since and later
                widget.setVisible(show)
                if show:
                    since = False

    def make_button(self, key, action, sub, kind=QPushButton):
        from azimuth.button_icons import icon_name
        from azimuth.icons import GLYPHS, iconify

        text = clean(action.text())
        tip = text + (' ▸' if sub is not None else '')
        button = kind()
        name = icon_name(text) or (action.property('azimuthTextIcon') or None)
        if name in GLYPHS:
            iconify(button, name, tip)
        elif not action.icon().isNull():
            button.setProperty('iconic', True)
            button.setIcon(action.icon())
            button.setToolTip(tip)
        else:  # no glyph for it: its first letters
            button.setText(text[:2])
            button.setToolTip(tip)
            button.setFixedSize(34, 34)
        button.setAccessibleName(text)
        button.setProperty('azimuthBarKey', key)
        if sub is not None:
            button.clicked.connect(lambda: self.popup(button, sub))
        else:
            if action.isCheckable():
                button.setCheckable(True)
                button.setChecked(action.isChecked())
                action.toggled.connect(lambda on, b=button: _set_checked(b, on))
            button.clicked.connect(lambda: self.trigger(action, button))
            action.changed.connect(lambda b=button, a=action: _follow(b, a))
            button.setEnabled(action.isEnabled())
        button.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        button.customContextMenuRequested.connect(lambda pos, k=key, b=button: self.button_menu(k, b, pos))
        button.installEventFilter(self.drags)
        return button

    def popup(self, button, menu):
        tool = getattr(self.w, 'model_menu_tool', None)
        if tool is not None:
            tool._popup(button, menu)
        else:
            from hub.header import MenuToggle

            if not menu.property('azimuthToggle'):
                MenuToggle.watch(button, menu)
                menu.setProperty('azimuthToggle', True)
            menu.exec(button.mapToGlobal(button.rect().bottomLeft()))

    @staticmethod
    def trigger(action, button):
        action.trigger()
        if button.isCheckable():
            _set_checked(button, action.isChecked())

    # -- changing the groups ------------------------------------------------------------------------------------------
    @staticmethod
    def _without(groups, key):
        return {place: [g for g in ([k for k in group if k != key] for group in groups[place]) if g]
                for place in (TOP, RAIL)}

    def add(self, key, place):
        """At the end of place, a group of its own (a new line before it)."""
        groups = self._without(self.groups(), key)
        groups[place].append([key])
        self.save(groups)
        self.rebuild()

    def moved(self, key, slot, groups=None):
        """The groups after key is dropped at slot (see move); None when nothing would change —."""
        groups = groups or self.groups()
        if slot[0] == 'into':
            _, place, member, before = slot
            if before == key:  # dropped right where it is
                group = next((g for g in groups[place] if key in g), None)
                before = group[group.index(key) + 1] if group is not None and group.index(key) + 1 < len(group) else None
            if member == key:
                group = next((g for g in groups[place] if key in g), [])
                others = [k for k in group if k != key]
                if not others:
                    return None  # a group of one dropped on itself
                member = others[0]
            out = self._without(groups, key)
            group = next((g for g in out[place] if member in g), None)
            if group is None:
                out[place].append([key])
            else:
                group.insert(group.index(before) if before in group else len(group), key)
        else:
            place = slot[1]
            out = self._without(groups, key)
            out[place].append([key])
        same = all([list(g) for g in out[p] if g] == [list(g) for g in groups[p] if g] for p in (TOP, RAIL))
        return None if same else out

    def move(self, key, slot):
        """slot: ('new', place) — a group of its own at the end of place; ('into', place, member, before) — into the
        group of member, before the key before (None: at its end)."""
        groups = self.moved(key, slot)
        if groups is None:
            return
        self.save(groups)
        self.rebuild()

    def remove(self, key):
        self.save(self._without(self.groups(), key))
        self.rebuild()

    def reset(self):
        preferences = getattr(self.w, 'preferences', None)
        if preferences is not None:  # the panel of the mode shown only
            for name in ((LAYOUT, OLD[TOP], OLD[RAIL], OLD_HIDDEN) if self.mode() == 'molecule' else (self.layout_key(),)):
                preferences.remove(name)
        self.save({place: [list(g) for g in self.default_groups[place]] for place in (TOP, RAIL)})
        self.rebuild()

    # -- what the user does -------------------------------------------------------------------------------------------
    def already(self, key, action):
        """(key of the button, place) of a button on a panel that is this item — the same key, or a button showing the
        same glyph (every function has a glyph of its own since «Изометрия» is the button of the projection
        from the start) — or None."""
        place = self.where(key)
        if place is not None:
            return key, place
        from azimuth.button_icons import icon_name

        name = icon_name(clean(action.text())) or action.property('azimuthTextIcon')
        if not name:
            return None
        groups = self.groups()
        for other, widget in list(self.defaults.items()) + list(self.buttons.items()):
            try:
                if widget.property('quail_icon') == name and _showing(widget) and not widget.property('azimuthAway'):
                    where = self.where(other, groups)
                    if where is not None:
                        return other, where
            except RuntimeError:
                continue
        return None

    @staticmethod
    def refusal(place):
        return tr('Эта кнопка уже есть на панели над полем') if place == TOP else tr('Эта кнопка уже есть в колонке справа')

    def refuse(self, key, action):
        """An item dragged out of the menus whose button stands on a panel already: the menus close, a message says so
        (it moved silently before — «конформеры» seemed not to go)."""
        twin = self.already(key, action)
        close_menus()
        notify = getattr(self.w, 'notify', None)
        if twin is not None and notify is not None:
            notify(self.refusal(twin[1]), 5000)

    def offer(self, key, at):
        """The menu of a right click on an item of the menus. A choice closes the menus too — the button
        put on the panel is seen at once (the menu it came from stayed open over the field)."""
        menu = rounded(QMenu(self.w))  # rounded corners
        menu.triggered.connect(lambda *_: close_menus())
        action, _sub = self.find(key)
        twin = self.already(key, action) if action is not None else None
        if twin is not None and twin[0] != key:  # the same function stands there as another button: nothing to add
            note = menu.addAction(self.refusal(twin[1]))
            note.setEnabled(False)
            menu.exec(at)
            return
        place = self.where(key)
        if place is not None:  # said first; it can still be moved to the other place or taken away
            note = menu.addAction(self.refusal(place))
            note.setEnabled(False)
            menu.addSeparator()
        if place != TOP:
            menu.addAction(tr('Добавить на панель над полем'), lambda: self.add(key, TOP))
        if place != RAIL:
            menu.addAction(tr('Добавить в колонку справа'), lambda: self.add(key, RAIL))
        if place is not None:
            menu.addAction(tr('Убрать с панели'), lambda: self.remove(key))
        menu.exec(at)

    def button_menu(self, key, button, pos):
        """The menu of a right click on a button of the row or of the column.
        a button with a menu of its own (own_menu(menu) — «Оси») gives its items first, in the same menu."""
        menu = rounded(QMenu(self.w))  # rounded corners
        own = getattr(button, 'own_menu', None)
        if own is not None:
            own(menu)
            menu.addSeparator()
        menu.addAction(tr('Убрать с панели'), lambda: self.remove(key))
        place = self.where(key)
        if place == TOP:
            menu.addAction(tr('Перенести в колонку справа'), lambda: self.add(key, RAIL))
        elif place == RAIL:
            menu.addAction(tr('Перенести на панель над полем'), lambda: self.add(key, TOP))
        # a line put before or after the button (its group parted there), or taken away (two groups one)
        if place is not None:
            groups = self.groups()[place]
            at = next(((n, g.index(key)) for n, g in enumerate(groups) if key in g), None)
            if at is not None:
                n, k = at
                before, after = (tr('сверху'), tr('снизу')) if place == RAIL else (tr('слева'), tr('справа'))
                menu.addSeparator()
                if k > 0:
                    menu.addAction(tr('Отделить чертой ') + before, lambda: self.split(key, False))
                elif n > 0:
                    menu.addAction(tr('Убрать черту ') + before, lambda: self.join(key, False))
                if k < len(groups[n]) - 1:
                    menu.addAction(tr('Отделить чертой ') + after, lambda: self.split(key, True))
                elif n < len(groups) - 1:
                    menu.addAction(tr('Убрать черту ') + after, lambda: self.join(key, True))
        menu.addSeparator()
        menu.addAction(tr('Вернуть кнопки как было'), self.reset)
        menu.exec(button.mapToGlobal(pos))

    def split(self, key, after):
        """The group of key parted by a line right before key (after: right after it)."""
        groups = self.groups()
        place = self.where(key, groups)
        if place is None:
            return
        for n, group in enumerate(groups[place]):
            if key in group:
                cut = group.index(key) + (1 if after else 0)
                if 0 < cut < len(group):
                    groups[place][n:n + 1] = [group[:cut], group[cut:]]
                    self.save(groups)
                    self.rebuild()
                return

    def join(self, key, after):
        """The line right before the group of key (after: right after it) taken away — two groups one."""
        groups = self.groups()
        place = self.where(key, groups)
        if place is None:
            return
        rows = groups[place]
        n = next((n for n, g in enumerate(rows) if key in g), None)
        other = None if n is None else (n + 1 if after else n - 1)
        if other is None or not 0 <= other < len(rows):
            return
        first, second = sorted((n, other))
        rows[first:second + 1] = [rows[first] + rows[second]]
        self.save(groups)
        self.rebuild()

    _carried_picture = _carry._carried_picture
    _begin = _carry._begin
    _end = _carry._end
    drag_item = _carry.drag_item

    # on macOS the drag of the system started from a menu reached the window only now and then — over the column at the
    # right and over the field never a single event, over the row sometimes; the drag from a button of a panel always.
    # There the item is carried by the menu itself: the menu that took the press keeps the mouse (the system sends it
    # every move and the release), turns invisible, a picture of the button follows the cursor, the gap opens as over a
    # drag, the release puts the button and closes the menus. No drag of the system at all.
    CARRY_IN_MENU = sys.platform == 'darwin'

    carrying = _carry.carrying
    start_carry = _carry.start_carry
    carry_move = _carry.carry_move
    carry_drop = _carry.carry_drop
    carry_cancel = _carry.carry_cancel
    _finish_carry = _carry._finish_carry

    @staticmethod
    def exec_drag(drag):
        """The drag of an item of the menus carried until it is dropped (its own method: the tests drop it)."""
        return drag.exec(Qt.DropAction.CopyAction | Qt.DropAction.MoveAction, Qt.DropAction.CopyAction)

    drag = _carry.drag

    # --; 0.206.5 («Сделай раздвижение соседей»): a gap opens at the place the button will take —
    # the neighbours move apart and a pale copy of it stands there (after a new line when it makes a group of its own);
    # the gap of a place left closes ---------------------------------------------------------------------------------
    GLIDE_MS = 120

    _gap_index = _carry._gap_index
    _make_gap = _carry._make_gap
    _size_gap = _carry._size_gap
    _close_gap = _carry._close_gap
    show_slot = _carry.show_slot
    place_at = _carry.place_at
    slot = _carry.slot


def _set_checked(button, on):
    try:
        button.blockSignals(True)
        button.setChecked(bool(on))
    except RuntimeError:
        pass
    finally:
        try:
            button.blockSignals(False)
        except RuntimeError:
            pass


def _follow(button, action):
    try:
        button.setEnabled(action.isEnabled())
    except RuntimeError:
        pass
