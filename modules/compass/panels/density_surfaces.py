"""The page «Поверхности» of the density panel of Compass: the tree of the surfaces of Multiwfn, the one chosen put
on the model or taken away. Methods of DensityDrawer (self is the panel), kept here to make density_drawer.py shorter.

Split off modules/compass/panels/density_drawer.py (0.222.30).
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QTreeWidget, QTreeWidgetItem
from azimuth.i18n import tr


# -- «Поверхности» --------------------------------------------------------------------------------------------
def _surfaces_page(self, column, delta):
    from modules.compass.actions.surface_actions import SURFACE_GROUPS

    self.surfaces_hint = QLabel()
    self.surfaces_hint.setObjectName('subtitle')
    self.surfaces_hint.setWordWrap(True)
    column.addWidget(self.surfaces_hint)
    # the groups are branches that fold, the surfaces their leaves (was a flat list with bold rows)
    listing = QTreeWidget()
    # a frame of the program (QTreeWidget#surfacesTree, azimuth/app.py), roomier rows, a height of its own
    listing.setObjectName('surfacesTree')
    listing.setHeaderHidden(True)
    listing.setColumnCount(1)
    listing.setIndentation(16)
    # 260 px wanted more than the
    # drawer had with Δρ under it, and the layout laid the buttons over the tree; the tree grows into the room left
    listing.setMinimumHeight(170)
    listing.setUniformRowHeights(True)
    listing.setExpandsOnDoubleClick(True)
    owner = self._owner()
    for group, keys in SURFACE_GROUPS:
        head = QTreeWidgetItem([tr(group)])
        head.setFlags(Qt.ItemFlag.ItemIsEnabled)
        font = head.font(0)
        font.setBold(True)
        head.setFont(0, font)
        for key in keys:
            if key == ('function', 'spin') and not self.orbital_set.unrestricted:
                continue  # no spin density of a closed shell
            title = owner.surface_tool.surface_choice_title(key) if owner is not None and hasattr(owner, 'surface_tool') else key[1]
            item = QTreeWidgetItem([title])
            item.setData(0, Qt.ItemDataRole.UserRole, key)  # no tooltip repeating the row
            head.addChild(item)
        if head.childCount():
            listing.addTopLevelItem(head)
            head.setExpanded(True)
    listing.itemDoubleClicked.connect(lambda item, column=0: self.show_choice(item, toggle=False)
                                      if item.data(0, Qt.ItemDataRole.UserRole) is not None else None)
    listing.currentItemChanged.connect(lambda *a: self.refresh_lights())
    self.surfaces_list = listing
    column.addWidget(listing, 1)
    row = QHBoxLayout()
    row.setSpacing(6)
    self.choice_button = QPushButton(tr('Показать'))
    self.choice_button.setToolTip(tr('Выбранная поверхность на модели · двойной щелчок по строке'))
    self.choice_button.clicked.connect(lambda: self.show_choice(toggle=True))
    remove = QPushButton(tr('Убрать'))
    remove.setToolTip(tr('Убрать поверхность с модели'))
    remove.clicked.connect(self.remove_surface)
    row.addWidget(self.choice_button)
    row.addWidget(remove)
    row.addWidget(self._spinner('surfaces'))
    row.addStretch()
    column.addSpacing(2)
    column.addLayout(row)
    column.addWidget(delta)
    delta.show()  # it was the hidden second tab of the panel
    self.update_surfaces_page()


def surfaces_ready(self):
    """(ready, hint): Multiwfn is found and these orbitals have their file."""
    owner = self._owner()
    if owner is None or not hasattr(owner, 'property_tool'):
        return False, tr('Нужен Multiwfn.')
    if not hasattr(owner, 'property_tool') or owner.property_tool.orbitals_file(self.orbital_set) is None:
        return False, tr('Нужен файл этих орбиталей (Molden, fchk или .gbw ORCA) — откройте результат или файл орбиталей.')
    if owner.property_tool.multiwfn_found() is None:
        from modules.compass.actions.property_multiwfn import MULTIWFN_HINT

        return False, tr(MULTIWFN_HINT)
    return True, tr('Поверхности считает Multiwfn по файлу этих орбиталей; таблицы экстремумов — в папке «Анализ».')


def update_surfaces_page(self):
    if getattr(self, 'surfaces_list', None) is None:
        return False
    ready, hint = self.surfaces_ready()
    self.surfaces_hint.setText(hint)
    self.surfaces_hint.setVisible(not ready)  # a line only when something is missing (Multiwfn, the file)
    self.surfaces_list.setEnabled(ready)
    self.choice_button.setEnabled(ready)
    return ready


def current_choice(self, item=None):
    item = item or self.surfaces_list.currentItem()
    key = item.data(0, Qt.ItemDataRole.UserRole) if item is not None else None
    return tuple(key) if key is not None else None


def surface_items(self):
    """The leaves of the tree of the surfaces (the groups are not chosen)."""
    listing = getattr(self, 'surfaces_list', None)
    if listing is None:
        return []
    return [listing.topLevelItem(g).child(k) for g in range(listing.topLevelItemCount())
            for k in range(listing.topLevelItem(g).childCount())]


def surface_groups(self):
    """The titles of the branches of the tree."""
    listing = getattr(self, 'surfaces_list', None)
    return [listing.topLevelItem(g).text(0) for g in range(listing.topLevelItemCount())] if listing is not None else []


def choose_surface(self, title):
    """The leaf whose title starts with title made current (its branch opened); the item or None."""
    item = next((i for i in self.surface_items() if i.text(0).strip().startswith(title)), None)
    if item is not None:
        item.parent().setExpanded(True)
        self.surfaces_list.setCurrentItem(item)
    return item


def show_choice(self, item=None, toggle=True):
    """The surface chosen in the list on the model (a second press takes it away)."""
    key = self.current_choice(item)
    owner = self._owner()
    if self.panel is None or owner is None or self.busy:
        return False
    if key is None:
        self.panel.status.setText(tr('Выберите поверхность в списке.'))
        return False
    if toggle and self._toggled_off(('choice', key)):
        return False
    if not self.update_surfaces_page():
        return False
    path = owner.property_tool.orbitals_file(self.orbital_set)
    self.busy = True
    owner.quiet_spinner = self.spinners.get('surfaces')  # the ring next to the button, no window
    try:
        shown = bool(owner.surface_tool.surface_choice(key, path))
    finally:
        owner.quiet_spinner = None
        self.busy = False
    return self._put(('choice', key), shown)


def remove_surface(self):
    owner = self._owner()
    self.shown = self.shown_source = None
    if owner is not None and getattr(owner, 'surface_source', None) is not None:
        owner.surface_tool.clear_surface()
    self.refresh_lights()
    if self.panel is not None:
        self.panel.status.setText(tr('Поверхность убрана с модели.'))
