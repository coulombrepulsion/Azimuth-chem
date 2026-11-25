"""ModelMenuTool (window.model_menu_tool, a part of the window; was the mixin ModelMenuActions of
CompassWorkspace, split from it on 2026-11-08): the menus of the model of Compass — the menu of an atom, of a
bond, of the choice, the fragments and the molecules — and the edits they make (replace an element, a fragment, delete,
the order of a bond)."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMenu

from modules.compass.chemistry.builder import BASIC_FRAGMENTS, FRAGMENT_GROUPS, connections, delete_atoms, set_bond
from azimuth.core import EXAMPLES
from azimuth.i18n import combo_key, set_combo_key, tr
from modules.compass.panels.periodic import PeriodicTable
from azimuth.ui import smooth
from modules.compass.chemistry import library
from modules.compass.chemistry.editing import change_element, substitute


class ModelMenuTool:
    """Was the mixin ModelMenuActions of the window; a part of its own — it reaches the window only through
    the names of PORT (azimuth/window_port.WindowPort)."""

    PORT = (
        'browsing',
        'build_mode',
        'change_build_mode',
        'compass_dialogs',
        'constraint_tool',
        'constraints',
        'coordinate_tool',
        'dirty',
        'error',
        'fill_hydrogens',
        'fragment',
        'fragment_tool',
        'load_edit',
        'load_molecule',
        'molecule',
        'molecule_choice',
        'notify',
        'scheme_tool',
        'selection_tool',
        'structure_tool',  # the isotope of an atom (its menu)
        'update_choice_label',
        'viewer',
    )

    def __init__(self, window):
        from azimuth.window_port import WindowPort

        self.w = WindowPort(window, self.PORT)


    def choice_menu(self, items, current, callback, groups=None):
        """items first, then one submenu per group {title: [keys]} after a separator."""
        menu = smooth(QMenu(self.w.widget))
        menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        menu.setWindowFlags(menu.windowFlags() | Qt.WindowType.FramelessWindowHint)

        def add(target, key):
            item = target.addAction(tr(key))
            item.setCheckable(True)
            item.setChecked(key == current)
            item.triggered.connect(lambda checked=False, k=key: callback(k))

        for key in items:
            add(menu, key)
        if groups:
            menu.addSeparator()
            for title, keys in groups.items():
                sub = smooth(menu.addMenu(tr(title)))
                sub.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
                sub.setWindowFlags(sub.windowFlags() | Qt.WindowType.FramelessWindowHint)
                for key in keys:
                    add(sub, key)
        return menu

    def fragment_menu(self):
        menu = self.choice_menu(
            BASIC_FRAGMENTS,
            combo_key(self.w.fragment) if self.w.build_mode.currentData() == 'fragment' else None,
            self.choose_fragment,
            FRAGMENT_GROUPS,
        )
        return self.w.fragment_tool.add_fragment_tools(menu)  # the user's own fragments

    def molecule_menu(self):
        from modules.compass.chemistry import user_molecules

        groups = dict(library.MOLECULE_GROUPS)
        if user_molecules.USER:  # «Мои молекулы» — put where the field is clicked, as the library's
            groups[user_molecules.GROUP] = list(user_molecules.USER)
        menu = self.choice_menu(
            EXAMPLES,
            self.w.molecule_choice if self.w.build_mode.currentData() == 'molecule' else None,
            self.choose_molecule,
            groups,
        )
        menu.addSeparator()
        return self.w.fragment_tool.add_molecule_tools(menu)

    def choose_molecule(self, key):
        """The molecule to add by a click in the field; «Файл → Примеры молекул» still replaces."""
        self.w.molecule_choice = key
        self.w.build_mode.setCurrentIndex(4)
        self.w.update_choice_label()

    def bond_menu(self, a, b, where=None):
        """Right click on a bond: its order (single, double, triple) or breaking it."""
        current = next((o for i, j, o in connections(self.w.molecule) if {i, j} == {a, b}), 1)
        mark = (getattr(self.w.viewer, 'bond_marks', {}) or {}).get((min(a, b), max(a, b))) or {}
        menu = smooth(QMenu(self.w.widget))
        menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        menu.setWindowFlags(menu.windowFlags() | Qt.WindowType.FramelessWindowHint)
        for order, title in [(1, tr('Одинарная связь')), (2, tr('Двойная связь')), (3, tr('Тройная связь'))]:
            item = menu.addAction(title)
            item.setCheckable(True)
            item.setChecked(order == current and not mark.get('kind'))
            item.triggered.connect(lambda checked=False, o=order: self.set_bond_order(a, b, o))
        # how the bond is drawn — aromatic (a line and dashes), partial or coordination (dashed) — and a colour of its
        # own; for every bond between the atoms selected when the bond is among them
        for kind, title in (('aromatic', tr('Ароматическая (линия и пунктир)')),
                            ('partial', tr('Частичная / координационная (пунктир)'))):
            item = menu.addAction(title)
            item.setCheckable(True)
            item.setChecked(mark.get('kind') == kind)
            item.triggered.connect(lambda checked=False, k=kind: self.mark_bonds(a, b, kind=k if checked else ''))
        menu.addAction(tr('Цвет связи…')).triggered.connect(lambda: self.colour_bonds(a, b))
        if mark.get('color'):
            menu.addAction(tr('Цвет связи — по умолчанию')).triggered.connect(lambda: self.mark_bonds(a, b, color=''))
        menu.addSeparator()
        fixed = self.w.constraint_tool.find([a, b]) is not None
        menu.addAction(
            tr('Освободить длину связи') if fixed else tr('Закрепить длину связи для оптимизации')
        ).triggered.connect(lambda: self.w.constraint_tool.toggle([a, b]))
        menu.addAction(tr('Разорвать связь')).triggered.connect(lambda: self.set_bond_order(a, b, 0))
        menu.addSeparator()
        menu.addAction(tr('Вращать вокруг этой связи…')).triggered.connect(lambda: self.w.compass_dialogs.torsion(a, b))
        self._bond_menu = menu
        if where is not None:
            menu.popup(where)
        return menu

    @staticmethod
    def is_terminal(molecule, index):
        return sum(1 for i, j, _ in connections(molecule) if index in (i, j)) == 1

    def atom_menu(self, index, where=None):
        """Right click on an atom: element, a group instead of it, hydrogens, deletion."""
        if self.w.browsing or not 0 <= index < len(self.w.molecule.atoms):
            return None
        atom = self.w.molecule.atoms[index]
        menu = smooth(QMenu(self.w.widget))
        menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        menu.setWindowFlags(menu.windowFlags() | Qt.WindowType.FramelessWindowHint)
        head = menu.addAction(f'{atom.symbol}{index + 1}')
        head.setEnabled(False)
        elements = menu.addMenu(tr('Сменить элемент'))
        for symbol in ('H', 'C', 'N', 'O', 'F', 'P', 'S', 'Cl', 'Br', 'I'):
            item = elements.addAction(symbol)
            item.setCheckable(True)
            item.setChecked(symbol == atom.symbol)
            item.triggered.connect(lambda checked=False, s=symbol: self.replace_element(index, s))
        elements.addSeparator()
        elements.addAction(tr('Таблица Менделеева…')).triggered.connect(lambda: self.replace_from_table(index))
        if self.is_terminal(self.w.molecule, index):
            groups = menu.addMenu(tr('Заменить фрагментом'))
            for key in BASIC_FRAGMENTS:
                groups.addAction(tr(key)).triggered.connect(
                    lambda checked=False, k=key: self.replace_with_fragment(index, k)
                )
            groups.addSeparator()
            for title, keys in FRAGMENT_GROUPS.items():
                sub = groups.addMenu(tr(title))
                for key in keys:
                    sub.addAction(tr(key)).triggered.connect(
                        lambda checked=False, k=key: self.replace_with_fragment(index, k)
                    )
        # this atom — or, when it is selected, all the selected atoms of its element
        from azimuth.core import ISOTOPES, isotope_abundance, isotope_masses

        if atom.symbol not in ('X',):
            chosen = sorted(self.w.viewer.selected)
            targets = ([k for k in chosen if self.w.molecule.atoms[k].symbol == atom.symbol]
                       if index in chosen else [index])
            now = isotope_masses(self.w.structure_tool.w._isotopes, self.w.molecule).get(index, 0.0)
            isotopes = menu.addMenu(tr('Изотоп') + (f' ({len(targets)})' if len(targets) > 1 else ''))
            known = False
            for name, mass in [(tr('обычный'), 0.0)] + list(ISOTOPES.get(atom.symbol, [])):
                share = isotope_abundance(atom.symbol, mass) if mass else None
                text = name if not mass else f'{name} · {mass:.4f}' + (
                    f'  ({share * 100:.3g} %)' if share is not None else '  (' + tr('радиоактивный') + ')')
                item = isotopes.addAction(text)
                item.setCheckable(True)
                item.setChecked(abs(now - mass) < 1e-6)
                known = known or abs(now - mass) < 1e-6
                item.triggered.connect(lambda checked=False, m=mass: self.w.structure_tool.set_isotopes(targets, m))
            isotopes.addSeparator()
            # any mass — a rare or radioactive isotope the table has not
            own = isotopes.addAction(tr('Своя масса…') + (f'  ({now:.4f})' if now and not known else ''))
            own.setCheckable(True)
            own.setChecked(bool(now) and not known)
            own.triggered.connect(lambda checked=False: self.w.structure_tool.own_isotope_mass(targets))
        menu.addAction(tr('Выделить фрагмент (всё связанное)')).triggered.connect(lambda: self.w.selection_tool.select_fragment(index))
        menu.addAction(tr(f'Цвет элемента {atom.symbol}…')).triggered.connect(
            lambda: self.w.scheme_tool.set_element_color(atom.symbol)
        )  # display schemes
        item = menu.addAction(tr('Сохранить выделенное как фрагмент…'))
        item.setEnabled(bool(self.w.viewer.selected))
        item.triggered.connect(lambda: self.w.fragment_tool.save_selection_as_fragment())
        # the molecule of this atom (all the atoms bonded to it) into «Мои молекулы»
        from modules.compass.chemistry.editing import connected as _connected

        menu.addAction(tr('Сохранить молекулу в «Мои молекулы»…')).triggered.connect(
            lambda: self.w.fragment_tool.save_molecule(_connected(self.w.molecule, index)))
        menu.addAction(tr(f'Выделить все {atom.symbol}')).triggered.connect(lambda: self.w.selection_tool.select_element(atom.symbol))
        menu.addSeparator()
        item = menu.addAction(tr('Достроить водороды у этого атома'))
        item.triggered.connect(lambda: self.w.fill_hydrogens([index]))
        frozen = ('C', (index,)) in self.w.constraints
        menu.addAction(tr('Освободить атом') if frozen else tr('Закрепить атом для оптимизации')).triggered.connect(
            lambda: self.w.constraint_tool.toggle([index])
        )
        item.setEnabled(atom.symbol != 'H')
        menu.addSeparator()
        menu.addAction(tr('Удалить атом')).triggered.connect(lambda: self.delete_indices([index]))
        # the molecule of the atom — all the atoms bonded to it — goes; the others stay (a dimer, a complex, several
        # molecules on the model). Also when it is the only molecule on the model — then the model is left empty (undone
        # as any edit)
        from modules.compass.chemistry.editing import connected

        own = connected(self.w.molecule, index)
        item = menu.addAction(tr('Удалить молекулу ({} атомов)').format(len(own)))
        item.triggered.connect(lambda: self.delete_molecule(index))
        self._atom_menu = menu
        if where is not None:
            menu.popup(where)
        return menu

    def edit_structure(self, result, message='', centre=False):
        """One undoable edit of the structure; centre=True — an edit of building (an element changed, a group put on a
        hydrogen, atoms deleted): a drawn structure keeps the origin at its centre (Workspace.load_edit)."""
        self.w.load_edit(self.w.molecule, result, centre=centre)
        self.w.dirty = True
        if message:
            self.w.notify(message, 8000)

    def replace_element(self, index, symbol):
        try:
            self.edit_structure(change_element(self.w.coordinate_tool.table_molecule(), index, symbol), centre=True)
        except ValueError as exc:
            self.w.error(exc)

    def replace_from_table(self, index):
        dialog = PeriodicTable(self.w.molecule.atoms[index].symbol, self.w.widget)
        dialog.selected.connect(lambda symbol: (self.replace_element(index, symbol), dialog.close()))
        # an isotope chosen in the table (its right button) — this atom gets it
        dialog.isotope.connect(lambda symbol, mass: self.w.structure_tool.set_isotopes([index], mass))
        self._replace_dialog = dialog
        dialog.show()

    def replace_with_fragment(self, index, key):
        try:
            self.edit_structure(substitute(self.w.coordinate_tool.table_molecule(), index, key), centre=True)
        except ValueError as exc:
            self.w.error(exc)

    def delete_molecule(self, index):
        """The molecule of the atom index (the atoms bonded to it) deleted; undone as any edit."""
        from modules.compass.chemistry.editing import connected

        own = connected(self.w.molecule, index)
        if not own:
            return False
        self.delete_indices(own)
        self.w.notify(tr('Молекула удалена: {} атомов («Правка → Отменить» вернёт её).').format(len(own)), 6000)
        return True

    def delete_indices(self, indices):
        try:
            self.edit_structure(delete_atoms(self.w.coordinate_tool.table_molecule(), indices), centre=True)
        except ValueError as exc:
            self.w.error(exc)

    def marked_bonds(self, a, b):
        """The bonds a type or a colour goes to — the bond a–b, or every bond between the atoms selected
        when a and b are among them."""
        selected = set(getattr(self.w.viewer, 'selected', ()) or ())
        if a in selected and b in selected and len(selected) > 2:
            return [(min(i, j), max(i, j)) for i, j, _ in connections(self.w.molecule) if i in selected and j in selected]
        return [(min(a, b), max(a, b))]

    def mark_bonds(self, a, b, kind=None, color=None):
        """The type (kind: 'aromatic', 'partial', '' — none) or the colour (color: '#rrggbb', '' — by default) of the
        bonds of marked_bonds; returns them."""
        marks = dict(getattr(self.w.viewer, 'bond_marks', {}) or {})
        chosen = self.marked_bonds(a, b)
        for key in chosen:
            mark = dict(marks.get(key) or {})
            if kind is not None:
                mark['kind'] = kind
            if color is not None:
                mark['color'] = color
            mark = {k: v for k, v in mark.items() if v}
            if mark:
                marks[key] = mark
            else:
                marks.pop(key, None)
        self.w.viewer.bond_marks = marks
        self.w.viewer.update()
        return chosen

    def colour_bonds(self, a, b):
        from modules.compass.actions.style_form import pick_colour

        mark = (getattr(self.w.viewer, 'bond_marks', {}) or {}).get((min(a, b), max(a, b))) or {}
        colour = pick_colour(mark.get('color') or '#788897', self.w.widget, tr('Цвет связи'))
        if colour:
            self.mark_bonds(a, b, color=colour)
        return colour

    def set_bond_order(self, a, b, order):
        if order:  # a type of its own gives way to the order chosen
            marks = dict(getattr(self.w.viewer, 'bond_marks', {}) or {})
            mark = dict(marks.get((min(a, b), max(a, b))) or {})
            if mark.pop('kind', None):
                if mark:
                    marks[(min(a, b), max(a, b))] = mark
                else:
                    marks.pop((min(a, b), max(a, b)), None)
                self.w.viewer.bond_marks = marks
        try:
            self.w.viewer.keep_camera()
            self.w.load_molecule(set_bond(self.w.coordinate_tool.table_molecule(), a, b, order), preserve_view=True)
            self.w.dirty = True
        except ValueError as exc:
            self.w.error(exc)

    def choose_fragment(self, key):
        set_combo_key(self.w.fragment, key)
        self.w.build_mode.setCurrentIndex(2)

    def _popup(self, button, menu):
        """The menu of a button above the model or of the panels. A second press on the button closes it: on Windows
        the press that closed the menu reached the button and opened it again (the owner, 2026-11-24) —
        hub.header.MenuToggle swallows a press within its REOPEN_MS after the menu closed."""
        from hub.header import MenuToggle

        if not menu.property('azimuthToggle'):
            MenuToggle.watch(button, menu)
            menu.setProperty('azimuthToggle', True)
        self._open_menu = menu
        menu.exec(self.menu_point(button, menu))
        self.w.change_build_mode()

    @staticmethod
    def menu_point(button, menu):
        """Under the button, opening to the left when there is no room on the right, and above it
        when there is none below."""
        from PySide6.QtCore import QPoint

        point = button.mapToGlobal(button.rect().bottomLeft())
        screen = button.screen()
        if screen is None:
            return point
        room = screen.availableGeometry()
        size = menu.sizeHint()
        x, y = point.x(), point.y()
        if x + size.width() > room.right():
            x = max(room.left(), button.mapToGlobal(button.rect().bottomRight()).x() - size.width())
        if y + size.height() > room.bottom():
            y = max(room.top(), button.mapToGlobal(button.rect().topLeft()).y() - size.height())
        return QPoint(x, y)
