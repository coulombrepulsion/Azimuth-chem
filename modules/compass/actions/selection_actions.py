"""Compass: selection, copy/paste and mirroring of atoms (moved from workspace.py)."""

from azimuth.ui import rounded  # menus with rounded corners
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QMenu,
)
from modules.compass.chemistry.editing import (
    connected,
    mirror,
    paste,
    piece_from_text,
    selection_xyz,
)

from azimuth.i18n import tr


class SelectionTool:
    """Was the mixin SelectionActions of the window; a tool of its own — it reaches the window only through the names of
    PORT (azimuth/window_port.WindowPort)."""

    PORT = (
        'browsing',
        'coordinate_tool',
        'copy_action',
        'element_select_menu',
        'error',
        'hbonds_action',
        'invert_action',
        'lengths_action',
        'lengths_button',
        'mirror_menu',
        'model_menu_tool',
        'molecule',
        'notify',
        'paste_action',
        'preferences',
        'select_all_action',
        'select_none_action',
        'toggle_hbonds',
        'toggle_lengths',
        'viewer',
    )

    def __init__(self, window):
        from azimuth.window_port import WindowPort

        self.w = WindowPort(window, self.PORT)


    # -- selection ------------------------------------------------------------------------
    def build_selection_actions(self):
        """Select all / none / inverse, by element, copy and paste, mirror; shortcuts act on the model."""

        def make(title, callback, keys=None):
            item = QAction(title, self.w.widget)
            item.triggered.connect(callback)
            if keys is not None:
                item.setShortcut(QKeySequence(keys))
                item.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
                self.w.viewer.addAction(item)
            return item

        self.w.select_all_action = make(
            tr('Выделить всё'),
            lambda: self.w.viewer.set_selection(list(range(len(self.w.molecule.atoms)))),
            QKeySequence.StandardKey.SelectAll,
        )
        self.w.select_none_action = make(tr('Снять выделение'), lambda: self.w.viewer.set_selection([]), Qt.Key.Key_Escape)
        self.w.invert_action = make(tr('Инвертировать выделение'), self.invert_selection)
        self.w.copy_action = make(tr('Копировать атомы'), self.copy_atoms, QKeySequence.StandardKey.Copy)
        self.w.paste_action = make(tr('Вставить атомы'), self.paste_atoms, QKeySequence.StandardKey.Paste)
        self.w.mirror_menu = rounded(QMenu(tr('Отразить'), self.w.widget))
        for axis, plane in (('z', 'XY'), ('y', 'XZ'), ('x', 'YZ')):
            self.w.mirror_menu.addAction(tr(f'В плоскости {plane}')).triggered.connect(
                lambda checked=False, a=axis: self.mirror_atoms(a)
            )
        # on the model — bond lengths and hydrogen bonds (also in «Вид»)
        on = lambda key, default: str(self.w.preferences.value(key, default)).lower() in ('true', '1')
        self.w.viewer.show_lengths = on('show_lengths', 'false')
        self.w.viewer.show_hbonds = on('show_hbonds', 'true')
        self.w.lengths_button.setChecked(self.w.viewer.show_lengths)
        self.w.lengths_action = make(
            tr('Длины связей на модели'),
            lambda: (self.w.lengths_button.setChecked(self.w.lengths_action.isChecked()), self.w.toggle_lengths()),
        )
        self.w.lengths_action.setCheckable(True)
        self.w.lengths_action.setChecked(self.w.viewer.show_lengths)
        self.w.hbonds_action = make(tr('Водородные связи пунктиром'), self.w.toggle_hbonds)
        self.w.hbonds_action.setCheckable(True)
        self.w.hbonds_action.setChecked(self.w.viewer.show_hbonds)
        self.w.element_select_menu = rounded(QMenu(tr('Выделить по элементу'), self.w.widget))
        self.w.element_select_menu.aboutToShow.connect(self.fill_element_menu)

    def fill_element_menu(self):
        self.w.element_select_menu.clear()
        for symbol in sorted({a.symbol for a in self.w.molecule.atoms}):
            self.w.element_select_menu.addAction(symbol).triggered.connect(
                lambda checked=False, s=symbol: self.select_element(s)
            )

    def select_element(self, symbol):
        self.w.viewer.set_selection([i for i, a in enumerate(self.w.molecule.atoms) if a.symbol == symbol])

    def select_fragment(self, index):
        self.w.viewer.set_selection(connected(self.w.molecule, index))

    def invert_selection(self):
        chosen = set(self.w.viewer.selected)
        self.w.viewer.set_selection([i for i in range(len(self.w.molecule.atoms)) if i not in chosen])

    def copy_atoms(self):
        """The selected atoms (all if none) to the clipboard as XYZ."""
        if not self.w.molecule.atoms:
            return
        QApplication.clipboard().setText(selection_xyz(self.w.molecule, self.w.viewer.selected))
        n = len(self.w.viewer.selected) or len(self.w.molecule.atoms)
        self.w.notify(tr(f'Скопировано атомов: {n} (XYZ).'), 5000)

    def paste_atoms(self):
        if self.w.browsing:
            return
        try:
            result, new = paste(self.w.coordinate_tool.table_molecule(), piece_from_text(QApplication.clipboard().text()))
            self.w.model_menu_tool.edit_structure(result)
            self.w.viewer.set_selection(new)
        except ValueError as exc:
            self.w.notify(str(exc))

    def mirror_atoms(self, axis):
        if self.w.browsing or not self.w.molecule.atoms:
            return
        try:
            indices = self.w.viewer.selected.copy()
            self.w.model_menu_tool.edit_structure(mirror(self.w.coordinate_tool.table_molecule(), indices, axis))
            self.w.viewer.set_selection(indices)
        except ValueError as exc:
            self.w.error(exc)
