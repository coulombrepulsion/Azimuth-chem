"""«Справка → Поиск»: a search of the menus by a word, as in the Help menu of macOS, pointing to the item found.

§1 PURPOSE
    A field at the top of «Справка» of every section: a word typed — the items of the menus of the section (with their
    submenus) and the buttons of the window whose name or tooltip has it are listed under the field, with their path
    («Кристалл ▸ Межмолекулярные взаимодействия ▸ Поверхность Хиршфельда…»). A result chosen is shown where it is, as
    the Help menu of macOS does: its menus open one after another and the item is highlighted (Enter runs it), or the
    button is framed in blue for a moment with its tooltip. Ctrl+Shift+/ (⌘? on the Mac) opens «Справка» with the field.
§2 ALGORITHM
    entries(header, window): every action of the menus of the header (not separators, not the field itself), with the
    titles of the menus above it; every visible push button of the window that has a tooltip. find(entries, text):
    the words of the text (case and «ё» ignored) all in the name, or else all in the name and the tooltip; the name
    matches first, then by the length of the path; LIMIT at most.
§4 SPECIFICATION
    Entry(path, title, action | None, widget | None, tip); entries(header, window) -> [Entry]; find(entries, text,
    limit)
    -> [Entry]; install(menu, hub) — the field into the menu «Справка»; reveal(header, entry) — the result shown.
§7 TESTS
    tests/hub/test_menu_search.py.
"""

from dataclasses import dataclass, field

from PySide6.QtCore import QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QLineEdit, QPushButton, QWidgetAction

from azimuth.i18n import tr

LIMIT = 12
FIELD = 'Поиск по меню'  # the text of the action of the field (tests/hub/test_hub.py lists it)


@dataclass
class Entry:
    path: tuple  # the titles of the menus above the item (the button of the header first)
    title: str
    action: object = None
    widget: object = None
    tip: str = ''
    enabled: bool = True
    keys: tuple = field(default_factory=tuple)

    def label(self):
        return ' ▸ '.join(self.path + (self.title,))


def _clean(text):
    return (text or '').replace('&', '').replace('ё', 'е').replace('Ё', 'Е').lower()


def _walk(menu, path, out, seen):
    if menu is None or id(menu) in seen:
        return
    seen.add(id(menu))
    for action in menu.actions():
        if action.isSeparator() or isinstance(action, QWidgetAction) or action.property('menuSearchResult'):
            continue
        title = action.text().replace('&', '').strip()
        if not title:
            continue
        sub = action.menu()
        if sub is not None:
            out.append(Entry(path, title, action, None, action.toolTip() if action.toolTip() != action.text() else '',
                             action.isEnabled()))
            _walk(sub, path + (title,), out, seen)
        else:
            tip = action.toolTip() if action.toolTip() and action.toolTip() != action.text() else ''
            out.append(Entry(path, title, action, None, tip, action.isEnabled()))


def entries(header, window=None):
    """The items of the menus of the header (and their submenus) and the buttons of the window with a tooltip."""
    out, seen = [], set()
    for button in getattr(header, 'menu_buttons', ()):
        try:
            menu = button.menu()
            title = button.text().replace('&', '')
        except RuntimeError:
            continue
        _walk(menu, (title,), out, seen)
    if window is not None:
        for widget in window.findChildren(QPushButton):
            try:
                if not widget.isVisibleTo(window) or not widget.toolTip():
                    continue
            except RuntimeError:
                continue
            tip = widget.toolTip()
            title = widget.text().strip() or tip.split(' · ')[0].split('\n')[0]
            out.append(Entry((tr('Кнопка'),), title, None, widget, tip, widget.isEnabled()))
    return out


def find(found, text, limit=LIMIT):
    words = [w for w in _clean(text).split() if w]
    if not words:
        return []
    by_name, by_tip = [], []
    for entry in found:
        name = _clean(entry.title)
        if all(w in name for w in words):
            by_name.append(entry)
        elif all(w in name + ' ' + _clean(entry.tip) + ' ' + _clean(' '.join(entry.path)) for w in words):
            by_tip.append(entry)
    order = lambda e: (e.widget is not None, len(e.path), len(e.title))  # noqa: E731 — the menus first, short first
    unique, labels = [], set()
    for entry in sorted(by_name, key=order) + sorted(by_tip, key=order):
        if entry.label() not in labels:
            labels.add(entry.label())
            unique.append(entry)
    return unique[:limit]


def reveal(header, entry, step=60):
    """The result shown where it is: the menus of its path opened one by one, the item highlighted (not run); a
    button framed for a moment with its tooltip. Returns the last menu opened, or the button."""
    if entry.widget is not None:
        from PySide6.QtWidgets import QToolTip

        widget = entry.widget
        old = widget.styleSheet()
        widget.setStyleSheet(old + 'QPushButton {border: 2px solid #2a62b8; border-radius: 8px;}')
        QToolTip.showText(widget.mapToGlobal(widget.rect().center()), entry.tip or entry.title, widget)
        QTimer.singleShot(2200, lambda: _restore(widget, old))
        return widget
    button = next((b for b in getattr(header, 'menu_buttons', ()) if b.text().replace('&', '') == entry.path[0]), None)
    if button is None:
        return None
    chain = [button.menu()]
    for title in entry.path[1:]:
        parent = chain[-1]
        sub = next((a.menu() for a in parent.actions() if a.menu() is not None
                    and a.text().replace('&', '').strip() == title), None)
        if sub is None:
            return None
        chain.append(sub)
    top = chain[0]
    top.popup(button.mapToGlobal(button.rect().bottomLeft()))

    def open_level(k):
        if k >= len(chain):
            last = chain[-1]
            if entry.action is not None:
                last.setActiveAction(entry.action)
            return
        parent, sub = chain[k - 1], chain[k]
        action = sub.menuAction()
        parent.setActiveAction(action)
        rect = parent.actionGeometry(action)
        sub.popup(parent.mapToGlobal(rect.topRight()))
        QTimer.singleShot(step, lambda: open_level(k + 1))

    QTimer.singleShot(step, lambda: open_level(1))
    return chain[-1]


def _restore(widget, sheet):
    try:
        widget.setStyleSheet(sheet)
    except RuntimeError:
        pass


def install(menu, hub):
    """The field at the top of «Справка»: what is typed lists the results under it (as the Help menu of macOS)."""
    edit = QLineEdit()
    edit.setPlaceholderText(tr('Поиск по меню и кнопкам'))
    edit.setClearButtonEnabled(True)
    edit.setMinimumWidth(300)
    holder = QWidgetAction(menu)
    holder.setText(tr(FIELD))
    holder.setDefaultWidget(edit)
    holder.triggered.connect(lambda: edit.setFocus())  # the item of the field: its text in focus
    first = menu.actions()[0] if menu.actions() else None
    menu.insertAction(first, holder)
    divider = menu.insertSeparator(first) if first is not None else menu.addSeparator()
    state = {'results': []}

    def fill(text):
        for action in state['results']:
            menu.removeAction(action)
            action.deleteLater()
        state['results'] = []
        found = find(entries(hub.header, getattr(hub, 'studio', None)), text)
        if text.strip() and not found:
            none = QAction(tr('Ничего не найдено'), menu)
            none.setEnabled(False)
            found_items = [(none, None)]
        else:
            found_items = [(QAction(entry.label(), menu), entry) for entry in found]
        for item, entry in found_items:
            item.setProperty('menuSearchResult', True)
            menu.insertAction(divider, item)
            if entry is not None:
                if entry.tip:
                    item.setToolTip(entry.tip)
                item.triggered.connect(lambda checked=False, e=entry: QTimer.singleShot(120, lambda: reveal(hub.header, e)))
            state['results'].append(item)
        menu.adjustSize()

    edit.textChanged.connect(fill)
    def first():
        chosen = state['results'][0] if state['results'] else None
        if chosen is not None and chosen.isEnabled():
            menu.close()
            chosen.trigger()

    edit.returnPressed.connect(first)
    menu.aboutToShow.connect(lambda: QTimer.singleShot(0, edit.setFocus))
    # cleared after the item chosen has run (the menu hides before it triggers its action)
    menu.aboutToHide.connect(lambda: QTimer.singleShot(0, edit.clear))
    menu.search_field = edit
    menu.search_results = lambda: list(state['results'])
    return edit


def open_help(header):
    """Ctrl+Shift+/ (⌘?): «Справка» of the section opened, the cursor in its field."""
    button = next((b for b in getattr(header, 'menu_buttons', ()) if hasattr(b.menu(), 'search_field')), None)
    if button is None:
        return None
    menu = button.menu()
    menu.popup(button.mapToGlobal(button.rect().bottomLeft()))
    menu.search_field.setFocus()
    return menu

