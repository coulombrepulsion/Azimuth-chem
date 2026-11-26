"""Compass: opening a CIF, the «Кристалл» window, the unit cell drawn on the model.

§1 THEORY modules/compass/chemistry/crystal.py §1.
§2 ALGORITHM «Файл → Открыть…» with a .cif file reads the first data block (crystal.parse_cif) and
               opens the window: the title, the formula of the cell content, the space group, the cell
               (a, b, c, alpha, beta, gamma, volume), the number of atoms in the cell and the notes of the
               reader. «Построить» puts the block of n1 x n2 x n3 cells into Compass (with or without the
               atoms on the far faces, edges and corners) as one undoable change, and the viewer draws the
               edges of the block (a red, b green, c blue from the origin, the others grey). «Вид →
               Кристалл…» opens the window again; «Вид → Показывать ячейку» hides or shows the edges. A
               structure from another file removes the crystal.
               «Поверхность (hkl)» — a slab of `layers` planes with vacuum (surface.slab), repeated
               n1 x n2 in the plane, shown with its cell; «Сохранить CIF…» writes the crystal (with its
               symmetry operations) or the slab shown (P1).
§3 APPLICATIONS «Файл → Открыть…» (.cif), «Вид → Кристалл…», «Вид → Показывать ячейку».
§4 SPECIFICATION open_crystal_text(text, name) -> CrystalWindow or None; build_crystal(n, faces) ->
               bool; clear_crystal(); set_cell_shown(on).
§5 PROCEDURES below.
§6 NOTES the cell is drawn in the coordinates of the built block: moving the whole model moves the
               atoms away from it (the edges are not dragged along); rebuilding puts them back.
§7 TESTS tests/compass/test_crystal.py (reading and building); tests/test_gui.py::test_crystal_from_cif.
§8' ROBUSTNESS a damaged CIF or a block above MAX_ATOMS (2000) atoms: a message, the model is unchanged.
"""

from azimuth.ui import rounded  # menus with rounded corners

from modules.compass.chemistry import crystal as cr
from modules.compass.chemistry import crystal_symmetry as cs
from modules.compass.chemistry import surface as sf
from azimuth.i18n import tr
from modules.compass.actions.crystal_window import CrystalWindow
from modules.compass.actions import crystal_side as _side
from modules.compass.actions import crystal_marks as _marks


class CrystalTool:
    """Was the mixin CrystalActions of the window; a part of its own — it reaches the window only through the names
    of PORT (azimuth/window_port.WindowPort)."""

    PORT = (
        'crystal_side',
        'custom_bar',
        'conformers_action',
        'crystal_added_to_project',
        'crystal_project_to_add',
        'hide_notice',
        'notice',
        'cell_action',
        'cell_button',
        'compare_button',
        'compass_mode',
        'compass_mode_listener',
        'confirm_replace',
        'crystal_project_opened',
        'coordinate_tool',
        'crystal',
        'crystal_buttons',
        'crystal_window',
        'dirty',
        'error',
        'follow_compass_kind',
        'iupac_button',
        'load_molecule',
        'lock_button',
        'calc_stack',
        'crystal_mode_tool',
        'document',
        'navigate',
        'new_document',
        'next_button',
        'notify',
        'opening_tool',
        'own_molecule',
        'property_buttons',
        'save_text',
        'show_document_kind',
        'slab',
        'slab_n',
        'stack',
        'structure_tabs',
        'symmetry_tool',
        'sync_view_tabs',
        'update_side_quill',
        'viewer',
    )

    def __init__(self, window):
        from azimuth.window_port import WindowPort

        self.w = WindowPort(window, self.PORT)


    def open_crystal_text(self, text, name, project=None, same_tab=False):
        """project: the crystal project it is read from; None — a new project for it (when the window has
        project tabs). A crystal project shown — the crystal goes into it
        (crystal_projects.add), in its tab; same_tab — another crystal of the project chosen in its list."""
        adding = None
        if project is None and self.w.has('crystal_project_to_add'):
            adding = self.w.crystal_project_to_add()
        try:
            data = cr.parse_cif(text)
            cr.unit_cell(data)
        except ValueError as exc:
            self.w.error(exc)
            return None
        window = CrystalWindow(self.w.widget, data, name)
        self.w.crystal_window = window
        self.crystal_name = name
        self.source = data  # the crystal of the file, all parts of its disorder
        self.set_compass_mode('crystal')  # the hub shows «Компас · Кристалл»
        if getattr(self.w, 'crystal', None) is not None and self.w.has('new_document') and not same_tab \
                and adding is None:
            self.w.new_document(name)  # every crystal file — a tab (and a project) of its own
        # the crystal is built at once — one
        # cell, whole molecules, one part of a disorder (the defaults of the window); the window opens on demand
        if window.build():
            self.w.notify(self.crystal_summary(window) + ' ' + tr('Ячейки, поверхность, контакты, дифрактограмма — '
                                                                  '«Правка → Кристалл…».'), 15000)
            if adding is not None:  # one more crystal of the project shown
                project = self.w.crystal_added_to_project(adding, text, name) or project
            if self.w.has('crystal_project_opened'):  # the crystal as a project with its tab
                self.w.crystal_project_opened(text, name, project)
        else:  # it could not be built as it is (too many atoms…): the panel says why and offers the rest
            self.dock(window)
            window.live = True
        return window

    @staticmethod
    def crystal_summary(window):
        """'NaCl: F m -3 m (№ 225), Z = 4, ρ = 2.164 г/см³; 27 атомов.' for the status bar."""
        data, s = window.data, window.symmetry
        parts = [data.space_group or '']
        if s is not None:
            if s.number:
                parts[0] = (parts[0] + f' (№ {s.number})').strip()
            if s.z:
                parts.append(f'Z = {s.z:g}' if isinstance(s.z, float) else f'Z = {s.z}')
            if s.density:
                parts.append(tr('ρ = {} г/см³').format(f'{s.density:.3f}'))
        text = ', '.join(p for p in parts if p)
        return tr('Кристалл {}: {}.').format(data.title or window.windowTitle(), text) if text else tr('Кристалл {}.').format(
            data.title or window.windowTitle())

    # «Компас · Кристалл»; the open / save buttons over the model are gone (the «Файл» menu has
    # them), the cell switch stands next to the axes (layout.py)
    def toggle_cell_button(self):
        on = self.w.cell_button.isChecked()
        if self.w.has('cell_action'):
            self.w.cell_action.setChecked(on)
        self.set_cell_shown(on)

    def open_cif(self):
        from pathlib import Path

        from PySide6.QtWidgets import QFileDialog

        from azimuth.paths import ROOT

        start = ROOT / 'examples' / '10-crystals'
        path, _ = QFileDialog.getOpenFileName(
            # the projects too
            self.w.widget, tr('Открыть кристалл или проект'), str(start if start.is_dir() else Path.home()),
            tr('Кристалл CIF или проект (*.cif *.qcc);;Кристалл CIF (*.cif);;Проект Азимута (*.qcc);;Все файлы (*)')
        )
        if path:
            self.w.opening_tool.open_path(path)
        return path or None

    def set_compass_mode(self, mode):
        """'molecule' or 'crystal': the crystal tools over the model; the hub follows (compass_mode_listener)."""
        mode = 'crystal' if mode == 'crystal' else 'molecule'
        changed = mode != getattr(self.w, 'compass_mode', 'molecule')
        self.w.compass_mode = mode
        # the message over the model is of the other
        # subsection (a result of a molecule told just before) — it goes when the subsection changes
        if changed and self.w.has('notice') and self.w.has('hide_notice') and self.w.notice.text():
            self.w.hide_notice()
        if self.w.has('show_document_kind'):  # each subsection shows its own tabs
            self.w.show_document_kind(mode)
        if self.w.has('conformers_action'):  # no conformers of a crystal (its buttons follow the item)
            self.w.conformers_action.setEnabled(mode != 'crystal')
            self.w.conformers_action.setToolTip(tr('Для кристалла нет: выделите молекулу и перенесите её во вкладку '
                                                   'молекулы.') if mode == 'crystal' else '')
        if mode != 'crystal':
            self.close_side()  # the panel of the contacts / of the surface is of the crystal
        if mode == 'crystal':
            # the projects are named too («Файл» of «Компас · Кристалл» has «Открыть проект…»)
            self.w.viewer.empty_text = tr('Откройте кристалл: «Файл → Открыть CIF…», проект — «Файл → Открыть проект…»\n'
                                          'или пример из «Файл → Открыть пример…»')
        elif hasattr(self.w.viewer, 'empty_text'):
            del self.w.viewer.empty_text
        self.w.viewer.update()
        if self.w.has('update_side_quill'):
            self.w.update_side_quill()
        if changed and self.w.has('custom_bar'):  # each mode has a panel of its own (it asks update_panel)
            self.w.custom_bar.rebuild()
        else:
            self.update_panel(mode)
        if self.w.has('structure_tabs'):  # «Кристалл | Координаты» in «Компас · Кристалл»
            self.w.structure_tabs.setTabText(0, tr('Кристалл') if mode == 'crystal' else tr('Молекула'))
            if self.w.has('sync_view_tabs'):
                self.w.sync_view_tabs()
        listener = getattr(self.w, 'compass_mode_listener', None)
        if changed and listener is not None:
            listener(mode)
        if changed and self.w.has('follow_compass_kind'):  # the project tab of the tab shown
            self.w.follow_compass_kind(mode)
        # Sextant shown — a tab of the other kind chosen there: the page of a crystal or of a molecule
        if changed and self.w.has('calc_stack') and self.w.stack.currentIndex() == 1:
            crystal = mode == 'crystal' and getattr(self.w, 'crystal', None) is not None
            self.w.crystal_mode_tool.follow(self.w.document() if crystal else None)
        return mode

    # MOLECULE_ONLY: the buttons of «Компас · Молекула» that a crystal does not use the constraints of an optimisation,
    # the properties from a calculation, the overlay of another structure, the IUPAC name
    MOLECULE_ONLY = ('lock_button', 'compare_button', 'iupac_button')

    def update_panel(self, mode=None):
        """The panel of the mode — the crystal tools in «Компас · Кристалл», the molecule ones in «Молекула»;
        the arrow «К параметрам расчёта» becomes «Выделенные молекулы — в Компас · Молекула»."""
        crystal = (mode or getattr(self.w, 'compass_mode', 'molecule')) == 'crystal'
        if self.w.has('cell_button') and not self.w.cell_button.property('azimuthAway'):
            self.w.cell_button.setVisible(crystal)
        for item in self.w.crystal_buttons if self.w.has('crystal_buttons') else ():
            if not item.property('azimuthAway'):  # taken off the panel by the user
                item.setVisible(crystal)
        for name in self.MOLECULE_ONLY:
            if self.w.has(name) and not getattr(self.w, name).property('azimuthAway'):  # taken off the row
                getattr(self.w, name).setVisible(not crystal)
        if self.w.has('property_buttons'):
            # «Атомы» and «Связи» of a crystal
            # too — the charges and the bonds of Multiwfn of its CP2K run; «Диполь и силы» is of a molecule
            for part, item in self.w.property_buttons.items():
                if not item.property('azimuthAway'):  # taken off the panel by the user
                    item.setVisible(not crystal or part in ('atoms', 'bonds'))
        if self.w.has('coordinate_tool'):  # «Дробные (CIF)» among the formats of «Координаты»
            self.w.coordinate_tool.show_fractional_format(crystal)
        if self.w.has('next_button'):
            # the arrow of a crystal leads to its calculation (Quantum ESPRESSO in Sextant)
            text = tr('К расчёту кристалла') if crystal else tr('К параметрам расчёта')
            self.w.next_button.full = text
            self.w.next_button.setToolTip(tr('К расчёту кристалла в Секстанте (Quantum ESPRESSO); с выделенными атомами — '
                                             'их молекулы в Компас · Молекула') if crystal else text)
            self.w.next_button.setAccessibleName(text)
            self.w.next_button.update()
        if self.w.has('custom_bar'):  # the lines between the groups — around what this mode shows
            self.w.custom_bar.refresh_rules()

    def _built(self):
        """A block, a slab or a network just built from the file is not an unsaved change (the table of the
        coordinates, filled again, marked the tab changed — and building again asked «Заменить структуру?»); the
        summary under the model gets the group at once, not after the timer."""
        self.w.dirty = False
        self.network_on = False  # build_network turns it on after this (the lit «Показать сеть»)
        self._update_tints()
        self._update_ring_marks()
        if self.w.has('symmetry_tool'):
            self.w.symmetry_tool.update_symmetry()

    dock = _side.dock
    side_dialog = _side.side_dialog

    # a button that opens a side panel stays checked while the panel is open; a second press or a click outside the
    # panel closes it
    SIDE_KINDS = {'crystal': 'CrystalWindow', 'contacts': 'ContactsWindow', 'hirshfeld': 'HirshfeldWindow',
                  'results': 'ResultsPanel'}
    SIDE_BUTTONS = {'crystal': 0, 'contacts': 2, 'hirshfeld': 4, 'results': 5}  # their places in crystal_buttons

    side_kind = _side.side_kind
    toggle_side = _side.toggle_side
    sync_side_buttons = _side.sync_side_buttons
    empty_field_clicked = _side.empty_field_clicked
    close_side = _side.close_side
    slide_side = _side.slide_side
    _ghost_side = _side._ghost_side
    _drop_side_ghost = _side._drop_side_ghost
    show_contacts_on_model = _side.show_contacts_on_model
    hidden_window = _side.hidden_window
    show_contacts = _side.show_contacts
    show_qe = _side.show_qe
    show_powder = _side.show_powder

    def view_menu(self):
        """The views of the crystal (along a, b, c) and what is drawn over it — the button of the panel."""
        from PySide6.QtWidgets import QMenu

        menu = rounded(QMenu(self.w.viewer))  # rounded corners
        crystal = getattr(self.w, 'crystal', None)
        data = crystal[0] if crystal else None
        for axis, title in (('a', tr('Вдоль a')), ('b', tr('Вдоль b')), ('c', tr('Вдоль c'))):
            item = menu.addAction(title)
            item.setEnabled(data is not None)
            item.triggered.connect(lambda checked=False, k=axis: self.look_along_cell(data, k))
        menu.addSeparator()
        metals = data is not None and any(s.symbol not in cs.NONMETALS for s in data.sites)
        has_adp = data is not None and any(s.u or s.u_iso > 0 for s in data.sites)
        # each item says what it draws and, when grey, why
        for title, state, enabled, change, tip, why in (
            (tr('Элементы симметрии'), 'symmetry_shown', data is not None, self.set_symmetry_shown,
             tr('Оси, плоскости и центры инверсии группы в ячейке: повороты — сплошные, винтовые оси и плоскости '
                'скольжения — пунктир'), ''),
            (tr('Узлы решётки Браве'), 'lattice_shown', data is not None, self.set_lattice_shown,
             tr('Точки решётки: вершины ячейки и узлы центрировки (I, F, C…) — видно, какая решётка у кристалла'), ''),
            (tr('Эллипсоиды смещений (50 %)'), 'ellipsoids_shown', has_adp, self.set_ellipsoids_shown,
             tr('Тепловые колебания атомов из рентгеноструктурного эксперимента: атом с вероятностью 50 % находится '
                'внутри своего эллипсоида'), tr('В файле нет параметров смещения атомов (U или B)')),
            (tr('Координационные полиэдры'), 'polyhedra_shown', metals, self.set_polyhedra_shown,
             tr('Многогранники из ближайших соседей атомов металлов: октаэдр NaCl₆, куб CsCl₈, тетраэдр…'),
             tr('В кристалле нет атомов металлов')),
            (tr('Окраска молекул по симметрии'), 'tints_shown', data is not None, self.set_tints_shown,
             tr('Молекулы, связанные одной операцией симметрии, — одним цветом: видно, как группа размножает молекулу'),
             ''),
            (tr('Кольца, π–π и C–H···π на модели'), 'ring_marks_shown', data is not None, self.set_ring_marks_shown,
             tr('Центры ароматических колец и их стопки: π–π (кольцо над кольцом) и C–H···π (водород над кольцом)'),
             ''),
        ):
            item = menu.addAction(title)
            item.setCheckable(True)
            item.setChecked(bool(getattr(self, state, False)))
            item.setEnabled(enabled)
            item.setToolTip(tip if enabled or not why else why)
            item.toggled.connect(change)
        menu.setToolTipsVisible(True)
        return menu

    def build_crystal(self, data, n=(1, 1, 1), faces=True, whole=False):
        self.set_compass_mode('crystal')  # a crystal is built among the crystal tabs
        self.crystal_range = None  # whole cells, not a range
        packing = None
        try:
            if whole:  # the molecules whole, across the faces of the cells
                molecule, packing = cs.whole_molecules(data, tuple(n))
            else:
                molecule = cr.build(data, n, faces)
        except ValueError as exc:
            self.w.error(exc)
            return False
        if not self.crystal_tab(getattr(self, 'crystal_name', '') or data.title):
            return False
        self.w.crystal = (data, tuple(n), bool(faces), bool(whole))
        self.w.viewer.symmetry_items = self.symmetry_marks(data) if getattr(self, 'symmetry_shown', False) else None
        self.w.viewer.lattice_points = self.lattice_marks(data) if getattr(self, 'lattice_shown', False) else None
        self.w.slab = None
        self.w.load_molecule(molecule)
        self._built()
        self._update_ellipsoids(data)
        self._update_polyhedra()
        self.w.viewer.cell_lines = cr.cell_edges(data.cell, n) if getattr(self, 'cell_shown', True) else None
        self.w.viewer.lattice_planes = None  # the planes (hkl) belong to the block before
        self.w.viewer.update()
        text = tr(f'Кристалл: {len(molecule.atoms)} атомов, ячеек {n[0]}×{n[1]}×{n[2]}. Связи найдены по расстояниям.')
        if packing is not None and packing.text:
            text += ' ' + packing.text + '.'
        self.w.notify(text, 10000)
        return True

    def look_along_cell(self, data, axis):
        """The line of sight along the edge 'a', 'b', 'c' of the cell or the normal to the planes (h, k, l)
        (h a* + k b* + l c*, the reciprocal vectors); the next edge to the right."""
        import numpy as np

        v = np.array(data.cell.vectors(), dtype=float)
        if axis in ('a', 'b', 'c'):
            k = 'abc'.index(axis)
            direction, right = v[k], v[(k + 1) % 3]
        else:
            if not any(axis):
                self.w.notify(tr('Индексы Миллера (0 0 0) не задают плоскость.'), 6000)
                return False
            star = np.linalg.inv(v).T  # rows a*, b*, c* (without 2 pi)
            direction = axis[0] * star[0] + axis[1] * star[1] + axis[2] * star[2]
            right = np.cross(direction, v[2] if abs(np.dot(direction, v[2])) < 0.99 * np.linalg.norm(direction) * np.linalg.norm(v[2]) else v[0])
        done = self.w.viewer.look_along(tuple(float(x) for x in direction), tuple(float(x) for x in right))
        self.w.viewer.update()
        return done

    symmetry_marks = _marks.symmetry_marks
    lattice_marks = _marks.lattice_marks
    contact_clicked = _marks.contact_clicked
    set_lattice_shown = _marks.set_lattice_shown
    set_symmetry_shown = _marks.set_symmetry_shown
    to_calculation = _marks.to_calculation
    selection_to_molecule = _marks.selection_to_molecule
    set_ellipsoids_shown = _marks.set_ellipsoids_shown
    set_polyhedra_shown = _marks.set_polyhedra_shown
    set_ring_marks_shown = _marks.set_ring_marks_shown
    _update_ring_marks = _marks._update_ring_marks
    set_tints_shown = _marks.set_tints_shown
    _update_tints = _marks._update_tints
    build_range = _marks.build_range
    _update_polyhedra = _marks._update_polyhedra
    _update_ellipsoids = _marks._update_ellipsoids
    build_network = _marks.build_network
    build_shell = _marks.build_shell
    show_energy_frame = _marks.show_energy_frame
    show_hirshfeld_model = _marks.show_hirshfeld_model

    def build_surface(self, data, hkl, layers=3, vacuum=15.0, n=(2, 2)):
        """A slab of the crystal; the crystal stays the one of the file, the slab is remembered for
        «Сохранить CIF…»."""
        self.set_compass_mode('crystal')
        try:
            plate = sf.slab(data, hkl, layers, vacuum)
            molecule = cr.build(plate, (n[0], n[1], 1), False)
        except ValueError as exc:
            self.w.error(exc)
            return False
        if not self.crystal_tab(getattr(self, 'crystal_name', '') or data.title):
            return False
        self.w.crystal = (data, (1, 1, 1), True)
        self.w.slab = plate
        self.w.slab_n = (n[0], n[1], 1)
        self.w.viewer.symmetry_items = None  # the elements are those of the crystal, not of the slab
        self.w.viewer.lattice_points = None
        self.w.viewer.ellipsoids = None
        self.w.load_molecule(molecule)
        self._built()
        self._update_polyhedra()
        self.w.viewer.cell_lines = cr.cell_edges(plate.cell, (n[0], n[1], 1)) if getattr(self, 'cell_shown', True) else None
        self.w.viewer.update()
        self.w.notify(plate.notes[0] + tr(f' На модели: {len(molecule.atoms)} атомов ({n[0]}×{n[1]} в плоскости).'), 10000)
        return True

    def save_crystal_cif(self, path=None):
        """Write the slab shown or the crystal of the file as CIF; returns the path or None."""
        plate = getattr(self.w, 'slab', None)
        crystal = getattr(self.w, 'crystal', None)
        data = plate if plate is not None else (crystal[0] if crystal else None)
        if data is None:
            self.w.notify(tr('Откройте файл CIF: «Файл → Открыть…».'), 8000)
            return None
        text = sf.write_cif(data)
        if path is None:
            name = ''.join(ch if ch.isalnum() else '_' for ch in data.title) or 'crystal'
            return self.w.save_text(tr('Сохранить CIF'), tr('Кристалл CIF (*.cif)'), text, name + '.cif') or None
        from azimuth.files import atomic_write

        atomic_write(path, text)
        return path

    def show_lattice_planes(self, hkl):
        """The planes (hkl) in the block shown (lattice_planes) — None takes them away; returns the polygons
        or None (said why)."""
        from modules.compass.chemistry import lattice_planes

        if hkl is None:
            self.w.viewer.lattice_planes = None
            self.w.viewer.update()
            return None
        crystal = getattr(self.w, 'crystal', None)
        if not crystal:
            self.w.notify(tr('Откройте файл CIF: «Файл → Открыть…».'), 8000)
            return None
        n = tuple(int(k) for k in crystal[1]) if len(crystal) > 1 and len(crystal[1]) == 3 else (1, 1, 1)
        try:
            polygons = lattice_planes.planes(crystal[0].cell, hkl, n)
        except ValueError:
            self.w.notify(tr('Плоскостей ({}) в блоке слишком много или индексы нулевые.').format(
                ' '.join(str(x) for x in hkl)), 8000)
            return None
        self.w.viewer.lattice_planes = ('(' + ' '.join(str(x) for x in hkl) + ')', polygons)
        self.w.viewer.update()
        return polygons

    def monolayer(self, vacuum=15.0):
        """«Монослой из слоистого кристалла»: one sheet of the crystal shown (layer.monolayer) opened as a crystal of
        its own, with vacuum — for the calculation of a layer beside its bulk. Returns its crystal or None."""
        from modules.compass.chemistry import layer, surface

        crystal = getattr(self.w, 'crystal', None)
        if not crystal:
            self.w.notify(tr('Откройте файл CIF: «Файл → Открыть…».'), 8000)
            return None
        try:
            made = layer.monolayer(crystal[0], vacuum)
        except ValueError as exc:
            self.w.error(exc)
            return None
        name = (getattr(self, 'crystal_name', '') or 'crystal').rsplit('.', 1)[0] + '_monolayer.cif'
        self.open_crystal_text(surface.write_cif(made), name)
        self.w.notify(tr('Монослой: {} атомов в ячейке, вакуум {:g} Å вдоль c.').format(len(made.sites), vacuum), 8000)
        return made

    def export_crystal(self, kind, path=None):
        """2026-11-13 («Файл → Экспорт кристалла»): the crystal of the file to other programs — 'poscar' (VASP),
        'extxyz' (ASE, OVITO) of its cell, 'block' — the block of cells shown (its n₁ × n₂ × n₃) as CIF in P 1
        (crystal_export); returns the path or None."""
        from modules.compass.chemistry import crystal_export

        crystal = getattr(self.w, 'crystal', None)
        if not crystal:
            self.w.notify(tr('Откройте файл CIF: «Файл → Открыть…».'), 8000)
            return None
        data = crystal[0]
        n = tuple(int(k) for k in crystal[1]) if len(crystal) > 1 and len(crystal[1]) == 3 else (1, 1, 1)
        name = ''.join(ch if ch.isalnum() else '_' for ch in data.title) or 'crystal'
        try:
            if kind == 'poscar':
                text, title, kinds, suggested = (crystal_export.poscar(data), tr('Сохранить POSCAR'),
                                                 tr('POSCAR VASP (POSCAR *.vasp)'), 'POSCAR')
            elif kind == 'extxyz':
                text, title, kinds, suggested = (crystal_export.extended_xyz(data), tr('Сохранить расширенный XYZ'),
                                                 tr('Расширенный XYZ (*.xyz *.extxyz)'), name + '.extxyz')
            else:
                text, title, kinds, suggested = (crystal_export.block_cif(data, n), tr('Сохранить блок ячеек в CIF'),
                                                 tr('Кристалл CIF (*.cif)'), f'{name}_{n[0]}x{n[1]}x{n[2]}_P1.cif')
        except ValueError as exc:
            self.w.error(exc)
            return None
        if path is None:
            return self.w.save_text(title, kinds, text, suggested) or None
        from azimuth.files import atomic_write

        atomic_write(path, text)
        return path

    def reopen_crystal(self, show=True):
        crystal = getattr(self.w, 'crystal', None)
        if crystal is None:
            self.w.notify(tr('Откройте файл CIF: «Файл → Открыть…».'), 8000)
            return None
        data = crystal[0]
        source = getattr(self, 'source', None)  # back to all the parts of a disorder
        if source is not None and source.title == data.title and source.cell == data.cell:
            data = source
        # the panel of the same crystal is kept — its
        # symmetry, molecules and packing are not found again at every press of its button
        window = getattr(self.w, 'crystal_window', None) if self.w.has('crystal_window') else None
        try:
            from shiboken6 import isValid
        except ImportError:  # pragma: no cover
            def isValid(_):
                return True
        if window is None or not isValid(window) or getattr(window, 'data', None) is not data:
            window = CrystalWindow(self.w.widget, data, getattr(self, 'crystal_name', 'CIF'))
        window.live = False  # its boxes take the values of the block shown without building it again
        window.rebuild_timer.stop()
        for box, value in zip(window.counts, crystal[1]):
            box.setValue(value)
        window.faces.setChecked(crystal[2])
        if len(crystal) > 3 and window.whole.isEnabled():
            window.whole.setChecked(crystal[3])
        last = getattr(self, 'crystal_range', None)
        if last:  # the range of the last block
            for pair, a, b in zip(window.range_boxes, *last):
                pair[0].setValue(a)
                pair[1].setValue(b)
            window.by_range.setChecked(True)
        else:
            window.by_range.setChecked(False)
        self.w.crystal_window = window
        if show:
            self.dock(window)  # beside the model, rebuilt as its settings change
            window.live = True
        return window

    def set_cell_shown(self, on):
        self.cell_shown = bool(on)
        if self.w.has('cell_button'):  # the button next to the axes follows the menu
            self.w.cell_button.setChecked(bool(on))
        crystal = getattr(self.w, 'crystal', None)
        plate = getattr(self.w, 'slab', None)
        if plate is not None and on:  # the cell of the slab, n1 x n2 of the model
            self.w.viewer.cell_lines = cr.cell_edges(plate.cell, getattr(self.w, 'slab_n', (1, 1, 1)))
            self.w.viewer.update()
            return
        self.w.viewer.cell_lines = cr.cell_edges(crystal[0].cell, crystal[1]) if (on and crystal) else None
        self.w.viewer.update()

    def crystal_tab(self, title):
        """A crystal goes to its own tab when the shown one holds a molecule; its own tab is rebuilt in place."""
        if self.w.has('new_document') and getattr(self.w, 'crystal', None) is None and self.w.own_molecule().atoms:
            self.w.new_document(title)
            return True
        return self.w.confirm_replace()

    def clear_crystal(self):
        self.close_side()  # the panel of the crystal goes with it
        self.w.crystal = None
        self.w.slab = None
        self.w.viewer.cell_lines = None
        self.w.viewer.symmetry_items = None
        self.w.viewer.lattice_points = None
        self.w.viewer.ellipsoids = None
        self.w.viewer.polyhedra = None
        self.w.viewer.update()
