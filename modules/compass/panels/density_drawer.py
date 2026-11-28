"""Compass: the orbitals and the electron density of the result — pages of the left drawer.

HEADER
    After a calculation whose result has orbitals (a Molden or fchk file next to the output, the orbitals printed in
    it, or an ORCA .gbw), the drawer on the left of the model (☰, modules/compass/panels/trajectory_drawer.py) has three
    pages for them, next to «Оптимизация» and «Частоты»:
      «Орбитали» — the list of the orbitals (ВЗМО, НСМО marked; every value in the middle of its cell), «Орбиталь»,
      «Спин» (open shells) and «Состав» (the Hirshfeld shares of the atoms in every orbital); above the table — the
      canonical orbitals or the localized ones (Pipek–Mezey, its Becke variant, Boys;
      modules/spectrum/wavefunction/multiwfn_lmo.py): the kind of every LMO (core, lone pair, bond, delocalized) and its
      atoms, the file of the LMOs kept in «Анализ» and their surfaces built from it (table_set — the orbitals of the
      table); «Поверхности» (a page of its own) — every surface of Multiwfn for the file of these orbitals by its group
      (surface_actions.SURFACE_GROUPS: ρ, |∇ρ|, ∇²ρ, the spin density, RDG; ELF, LOL, the entropy; G, K, ALIE; the ESP;
      NCI, IRI; ESP, ALIE, LEA, LEAE on the molecular surface) — «Показать» (or a double click), «Убрать»; under it Δρ
      with fragments (our own calculation); «QTAIM» — the short list of the critical points (type, atoms, ρ, ∇²ρ, H) and
      the bond paths (modules/spectrum/views/density_view.py), «На модель» / «Убрать с модели»; the detailed table is
      «Топология ЭП» of Spectrum. The maps in a plane are «Карты и профили» of Spectrum.
    The button of what is on the model is blue (a second press takes it away and it is
    white again), the row of the orbital shown and the line of the surface shown are lit; nothing is computed twice —
    the grids of the orbitals and of the spin density are kept (cubes), the fields of Multiwfn too
    (surface_actions.wait_field), and the meshes (surface_actions.surface_meshes_for); while a field is computed, no
    waiting window: the busy cursor and a turning ring next to the button (azimuth.tasks.run_spinning).
    «Сетка» of the pages is the same choice as «Сетка расчёта» of the menu of the surfaces (the preference
    multiwfn_grid: coarse, medium, fine); the orbitals and the spin density are Multiwfn's when it is installed and
    reads the file of the orbitals, our own grids otherwise.
    The window of Spectrum hands its work over here: a field put «на модели Компаса» there hides the window and opens
    the drawer on these pages with the same orbitals (and the critical points already found).
    Wilkinson convention, sections 1-8.

§2 ALGORITHM
    update_density_button() — after a result is shown or cleared (Spectrum show_result / clear_result, also when the
    tab changes): the three pages are enabled when result_orbitals() is not None or orbitals were given for this
    tab; the content of another tab or another result is dropped. The orbitals are read when one of the pages is
    opened (ensure_density_content) or open_density_drawer(orbital_set=None, source='', tab=0, state=None) is called —
    once per result (an ORCA .gbw is turned into Molden by orca_2mkl first).
§3 APPLICATIONS
    modules/compass/panels/layout.py, trajectory_actions.py (the pages), surface_actions.py («Вид → Поверхность на
    модели»), modules/spectrum/views/orbitals_view.py and density_view.py (the hand-over).
§4 SPECIFICATION
    DensityDrawer(drawer): .panel (DensityPanel or None), .step, .orbitals_table, .source_label, .surfaces_list,
    .orbital_button, .spin_button, .composition_button, .choice_button, .spinners; isVisible(); set_content(orbital_set,
    source, show_surface, show_aim, state=None) -> DensityPanel; clear(); show_orbital(toggle=False) -> bool;
    show_density(spin=False, esp=False, toggle=False) -> bool; show_choice(item=None, toggle=True) -> bool;
    remove_surface(); surfaces_ready() -> (bool, hint); update_surfaces_page() -> bool; refresh_lights();
    .surfaces_list is a QTreeWidget (the groups — branches, the surfaces — leaves with the key in UserRole of
    column 0); surface_items() -> [leaf]; surface_groups() -> [title]; choose_surface(title) -> leaf | None;
    sync_grid(grid).
    TAB_PAGES: the tab numbers of open_density_drawer (0 orbitals, 1 surfaces, 2 QTAIM) -> (page, 0).
    DensityDrawerTool (window.density_tool): density_drawer, density_key, density_owner; build_density_drawer();
    update_density_button(); ensure_density_content(); open_density_drawer(...) -> DensityDrawer | None;
    set_density_open(bool).
§7 TEST CASES tests/test_gui.py::test_density_panel_in_compass, ::test_multiwfn_elf_and_lol_on_the_model.
§8' ROBUSTNESS
    A file of orbitals that cannot be read gives the message of the reader and an empty page.
"""


from collections import OrderedDict

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from azimuth.i18n import tr
from modules.compass.panels import density_orbitals as _orbitals
from modules.compass.panels import density_surfaces as _surfaces

PAGES = ('orbitals', 'surfaces', 'aim')
TAB_PAGES = {0: ('orbitals', 0), 1: ('surfaces', 0), 2: ('aim', 0)}
CUBES = 12  # the grids of orbitals and of the spin density kept for showing them again
LIT = {False: '#2a62b8', True: '#6ea2f0'}  # the blue of the program (light, dark theme)


def light(button, on):
    """The button of what is on the model is lit, white otherwise; 2026-11-17 (the rule of the buttons,
    azimuth/app.py): lit as a switch that is on (property on — a light blue ground, a blue frame), not the blue fill of
    the main action."""
    if bool(button.property('on')) != bool(on):
        button.setProperty('on', bool(on))
        button.style().unpolish(button)
        button.style().polish(button)
        button.update()


def window_of(show_surface):
    """The window whose surface_tool.show_surface was given (the method is of the part SurfaceTool, not of the
    window; the window is its port's widget). None for a function of no window."""
    bound = getattr(show_surface, '__self__', None)
    port = getattr(bound, 'w', None)
    return getattr(port, 'widget', bound)


class DensityDrawer:
    """The content of the pages «Орбитали», «Поверхности» and «QTAIM» of the left drawer."""

    def __init__(self, drawer):
        self.drawer = drawer
        self.panel = None
        self.orbital_set = None
        self.show_surface = None
        self.step = self.orbitals_table = self.source_label = None
        self.tabs = self.aim_tabs = None  # no sub-tabs — three pages of the drawer
        self._boxes = []
        self.shown = None  # what the buttons put on the model: ('orbital', row), ('spin',), ('choice', key), ('density',)
        self.shown_source = None  # the surface_source it became (another surface on the model — nothing lit)
        self.owner = None
        self.surfaces_list = None
        self.grids = []
        self.spinners = {}
        self.cubes = OrderedDict()
        self.busy = False
        self.table_set = None  # the orbitals of the table — the canonical ones or localized (lmos)
        self.lmos = {}  # method -> (OrbitalSet of the LMOs, {number: kind}, {number: text})
        self.orbital_kind = None

    def isVisible(self):
        return self.drawer.isVisible() and self.drawer.page() in PAGES

    def isHidden(self):
        return not self.isVisible()

    # -- content -------------------------------------------------------------------------------------------------
    def clear(self):
        for box, host in self._boxes:
            host.removeWidget(box)
            box.deleteLater()
            host.setStretch(host.count() - 1, 1)  # the empty page: the message at the top again
        self._boxes = []
        self.panel = self.step = self.orbitals_table = self.orbital_set = None
        self.table_set, self.lmos, self.orbital_kind, self.shown_set = None, {}, None, None
        self.source_label = None
        self.surfaces_list = None
        self.grids = []
        self.spinners = {}
        self.cubes = OrderedDict()
        self.shown = self.shown_source = None
        for message in (self.drawer.orbitals_message, self.drawer.surfaces_message, self.drawer.aim_message):
            message.show()
        self.drawer.density_status.clear()

    def _place(self, box, host, message):
        host.insertWidget(0, box, 1)
        # the content takes the whole page — the stretch under the message (for the empty page) shared the
        # height with it, and the table of the orbitals ended in the middle of the drawer
        host.setStretch(host.count() - 1, 0)
        box.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)  # never wider than the drawer
        # shown — the page of QTAIM (and Δρ under the surfaces) came from the hidden tabs of the panel, and a
        # widget hidden there stays hidden in its new place: the page «QTAIM» was empty
        box.show()
        message.hide()
        self._boxes.append((box, host))
        # the combo boxes of a page put into a drawer already shown get the look of the theme (the window styles them
        # only when its own child is shown)
        owner = self._owner()
        try:
            if owner is not None:
                owner.style_new_combos(box)
        except (AttributeError, RuntimeError):
            pass

    def _spinner(self, name):
        from azimuth.controls import Spinner

        spinner = Spinner(16)
        spinner.setToolTip(tr('Считается…'))
        self.spinners[name] = spinner
        return spinner

    def _grid_row(self, column):
        """«Сетка:» — one choice for all the pages (the preference of the menu of the surfaces)."""
        from modules.compass.actions.surface_actions import GRIDS

        row = QHBoxLayout()
        row.setSpacing(6)
        row.addWidget(QLabel(tr('Сетка:')))
        box = QComboBox()
        for (key, _), (step, title) in zip(GRIDS, ((0.25, 'Грубая сетка · 0,25 Å'), (0.15, 'Обычная сетка · 0,15 Å'),
                                                    (0.10, 'Точная сетка · 0,10 Å'))):
            box.addItem(tr(title), step)
        owner = self.owner
        keys = [k for k, _ in GRIDS]
        grid = owner.surface_tool.nci_grid() if owner is not None and hasattr(owner, 'surface_tool') else 'medium'
        box.setCurrentIndex(keys.index(grid) if grid in keys else 1)
        box.currentIndexChanged.connect(lambda index, b=box: self._grid_chosen(b))
        row.addWidget(box, 1)
        column.addLayout(row)
        self.grids.append(box)
        return box

    def _grid_chosen(self, box):
        from modules.spectrum.wavefunction import multiwfn

        grid = multiwfn.grid_for_step(box.currentData())
        owner = self.owner
        if owner is not None and hasattr(owner, 'surface_tool'):
            owner.surface_tool.set_nci_grid(grid)  # it calls sync_grid and rebuild_on_model back
        else:
            self.sync_grid(grid)
            self.rebuild_on_model()

    def rebuild_on_model(self):
        """what the buttons put on the model is built again on the grid chosen now (a grid built before is taken from
        the memory, a new one is computed); False when nothing is on the model or nothing was built."""
        shown = self.on_model()
        if shown is None or self.panel is None or self.busy:
            return False
        if shown[0] == 'orbital':
            if self.orbitals_table is not None and 0 <= shown[1] < self.orbitals_table.rowCount():
                self.orbitals_table.selectRow(shown[1])
            return self.show_orbital(toggle=False)
        if shown[0] in ('density', 'spin'):
            return self.show_density(spin=shown[0] == 'spin', toggle=False)
        if shown[0] == 'choice':
            if tuple(shown[1]) == ('surface', 'esp'):
                return self.show_esp(toggle=False)
            for item in self.surface_items():
                if tuple(item.data(0, Qt.ItemDataRole.UserRole) or ()) == tuple(shown[1]):
                    return self.show_choice(item, toggle=False)
        return False

    def sync_grid(self, grid):
        from modules.compass.actions.surface_actions import GRIDS

        keys = [k for k, _ in GRIDS]
        index = keys.index(grid) if grid in keys else 0
        for box in self.grids:
            if box.currentIndex() != index:
                box.blockSignals(True)
                box.setCurrentIndex(index)
                box.blockSignals(False)
        if self.panel is not None and self.panel.step.currentIndex() != index:
            self.panel.step.setCurrentIndex(index)

    def set_content(self, orbital_set, source, show_surface, show_aim, state=None):
        from modules.spectrum.views.density_view import DensityPanel

        self.clear()
        self.orbital_set = orbital_set
        self.show_surface = show_surface
        drawer = self.drawer
        owner = window_of(show_surface)  # QTAIM is Multiwfn's — it reads the file of these orbitals
        self.owner = owner
        panel = DensityPanel(
            orbital_set, source, lambda cube, kind, orbitals, title: show_surface(cube, kind, orbitals, title=title),
            (lambda topology, orbitals, title, **kw: show_aim(topology, orbitals, title=title, **kw)) if show_aim else None,
            None,
        )
        panel.hide()
        if owner is not None and hasattr(owner, 'property_tool') and owner.property_tool.orbitals_file(orbital_set) is not None:
            panel.set_multiwfn(lambda: owner.property_tool.multiwfn_for(orbital_set))
        else:
            panel.set_multiwfn(None)
        if owner is not None:  # the points found go to the table of Spectrum; the button follows the model
            if hasattr(owner, 'topology_found'):
                panel.on_topology = lambda topology: owner.topology_found(orbital_set, source, topology)
            if hasattr(owner, 'surface_tool'):
                panel.clear_aim = owner.surface_tool.clear_aim
                panel.keep_contacts = owner.surface_tool.keep_contacts
                panel.aim_shown = lambda: getattr(owner.viewer, 'aim', None) is not None
        aim, delta = panel.aim_page, panel.surfaces_page
        while panel.tabs.count():
            panel.tabs.removeTab(0)
        panel.status.hide()
        panel.status = drawer.density_status  # the messages of the pages under them
        self.panel = panel
        self.step = panel.step
        # «Орбитали»
        box = QWidget()
        panel.setParent(box)  # it keeps the widgets of Δρ and the grid alive; itself never shown
        panel.hide()
        column = QVBoxLayout(box)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(6)
        nbasis = sum(s.size for s in orbital_set.shells)
        self.source_label = QLabel(tr(f'{source} · базис: {nbasis} функций · орбиталей: {len(orbital_set.orbitals)}'))
        self.source_label.setObjectName('subtitle')
        self.source_label.setWordWrap(True)
        self.source_label.setToolTip(orbital_set.title or source)
        column.addWidget(self.source_label)
        self._grid_row(column)
        self._orbitals_page(column)
        self._place(box, drawer.orbitals_host, drawer.orbitals_message)
        # «Поверхности»
        page = QWidget()
        column = QVBoxLayout(page)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(6)
        self._grid_row(column)
        self._surfaces_page(column, delta)
        self._place(page, drawer.surfaces_host, drawer.surfaces_message)
        # «QTAIM»
        spinner = self._spinner('aim')
        panel.aim_row.addWidget(spinner)
        panel.spinner = spinner
        aim.setParent(None)
        self._place(aim, drawer.aim_host, drawer.aim_message)
        self.sync_grid(owner.surface_tool.nci_grid() if owner is not None and hasattr(owner, 'surface_tool') else 'medium')
        state = state or {}
        for fragment, name in state.get('fragments', ()):  # the names as the window showed them
            panel.fragments.append(fragment)
            panel.fragment_list.addItem(name)
        if hasattr(panel, 'update_fragment_buttons'):
            panel.update_fragment_buttons()
        if state.get('topology') is not None:
            panel.show_topology(state['topology'])
        elif owner is not None and hasattr(owner, 'property_tool'):
            # the points found before in this file of orbitals (field_tables.load_topology) — not searched again
            from modules.spectrum.wavefunction import field_tables

            try:
                orbitals_file = owner.property_tool.orbitals_file(orbital_set)
            except (AttributeError, OSError, ValueError):
                orbitals_file = None
            saved = field_tables.load_topology(orbitals_file) if orbitals_file is not None else None
            if saved is not None:
                panel.show_topology(saved)
                panel.status.setText(tr('Критические точки — найденные раньше по этому же файлу орбиталей; '
                                        '«Найти» ищет заново.'))
                panel.contacts_to_model()
        if owner is not None and getattr(owner.viewer, 'aim', None) is not None and panel.topology is not None:
            panel.sync_model_button(True)
        self.refresh_lights()
        return panel

    _orbitals_page = _orbitals._orbitals_page
    _fill_table = _orbitals._fill_table
    choose_orbitals = _orbitals.choose_orbitals
    _localize = _orbitals._localize
    _quiet = _orbitals._quiet
    show_composition = _orbitals.show_composition
    _surfaces_page = _surfaces._surfaces_page
    surfaces_ready = _surfaces.surfaces_ready
    update_surfaces_page = _surfaces.update_surfaces_page
    current_choice = _surfaces.current_choice
    surface_items = _surfaces.surface_items
    surface_groups = _surfaces.surface_groups
    choose_surface = _surfaces.choose_surface
    show_choice = _surfaces.show_choice
    remove_surface = _surfaces.remove_surface

    # -- what is on the model ---------------------------------------------------------------------------------------
    def current_orbital(self):
        rows = self.orbitals_table.selectionModel().selectedRows() if self.orbitals_table is not None else []
        return rows[0].row() if rows else None

    def _owner(self):
        return window_of(self.show_surface)

    def on_model(self):
        """What the buttons put on the model and is still there — or an orbital or the spin density of these
        orbitals put there by the window of Spectrum; None otherwise."""
        owner = self._owner()
        source = getattr(owner, 'surface_source', None) if owner is not None else None
        if source is None:
            return None
        if self.shown is not None and source is self.shown_source:
            return self.shown
        if source.get('orbitals') is self.orbital_set:  # handed over: found by its kind and title
            if source.get('kind') == 'spin':
                self.shown, self.shown_source = ('spin',), source
                return self.shown
            if source.get('kind') == 'orbital':
                import re

                title = source.get('title', '')
                number = re.search(r'(\d+)', title)
                spin = 'beta' if 'β' in title else 'alpha'
                for k, o in enumerate(self.orbital_set.orbitals):
                    if number and o.number == int(number.group(1)) and (o.spin == spin or not self.orbital_set.unrestricted):
                        self.shown, self.shown_source = ('orbital', k), source
                        return self.shown
        return None

    def refresh_lights(self):
        """The blue button of what is on the model; the row of the orbital and the line of the surface lit."""
        if self.orbitals_table is None:
            return
        shown = self.on_model()
        if shown is None:
            self.shown = self.shown_source = None
            self.shown_set = None
        dark = self.orbitals_table.palette().base().color().lightness() < 128
        glow = QColor(LIT[dark])
        glow.setAlpha(70)
        orbital_row = shown[1] if shown and shown[0] == 'orbital' and self._same_set() else None
        lit = {orbital_row} | set(self.overlay_rows()) if orbital_row is not None else set()  # and those over it
        # only the rows whose light changed, the table not laid out at each cell: every cell of every row was set
        # anew, and with the columns as wide as their contents each change measured the whole table again — the window
        # stood for 10–15 s at the orbitals of caffeine (≈250 rows) on Windows (the owner, 2026-11-28: «зависло при
        # открытии панели результатов»)
        table = self.orbitals_table
        was = getattr(table, 'lit_rows', None)
        rows = range(table.rowCount()) if was is None or getattr(table, 'lit_glow', None) != glow.rgba() \
            else sorted(set(was) ^ lit)
        if rows:
            from PySide6.QtWidgets import QHeaderView

            header = table.horizontalHeader()
            modes = [header.sectionResizeMode(c) for c in range(table.columnCount())]
            header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)  # measured once, after
            table.setUpdatesEnabled(False)
            blocked = table.blockSignals(True)
            try:
                for r in rows:
                    for c in range(table.columnCount()):
                        item = table.item(r, c)
                        if item is not None:
                            item.setBackground(QBrush(glow) if r in lit else QBrush())
                            font = item.font()
                            font.setBold(r in lit)
                            item.setFont(font)
            finally:
                table.blockSignals(blocked)
                for c, mode in enumerate(modes):
                    header.setSectionResizeMode(c, mode)
                table.setUpdatesEnabled(True)
        table.lit_rows, table.lit_glow = set(lit), glow.rgba()
        light(self.orbital_button, orbital_row is not None and orbital_row == self.current_orbital())
        light(self.spin_button, shown == ('spin',))
        choice = shown[1] if shown and shown[0] == 'choice' else None
        if self.surfaces_list is not None:
            for item in self.surface_items():
                key = item.data(0, Qt.ItemDataRole.UserRole)
                on = choice is not None and tuple(key) == choice
                item.setBackground(0, QBrush(glow) if on else QBrush())
                font = QFont(item.font(0))
                font.setBold(on)
                item.setFont(0, font)
            light(self.choice_button, choice is not None and choice == self.current_choice())

    def _same_set(self):
        """The orbital on the model is of the orbitals the table shows (canonical or localized)."""
        shown_set = getattr(self, 'shown_set', None)
        return shown_set is self.table_set or (shown_set is None and self.table_set is self.orbital_set)

    def _toggled_off(self, key):
        """A second press of the button of what is on the model takes it away; True when it did."""
        if self.on_model() == key and (key[0] != 'orbital' or self._same_set()):
            self.remove_surface()
            return True
        return False

    def _put(self, key, shown):
        if shown:
            owner = self._owner()
            self.shown = key
            self.shown_source = getattr(owner, 'surface_source', None)
            self.shown_set = self.table_set
        self.refresh_lights()
        return shown

    def _cube(self, key, work, title):
        """A grid built before (CUBES kept) or built now with the ring of the page «Орбитали»."""
        if key in self.cubes:
            self.cubes.move_to_end(key)
            return self.cubes[key]
        cube = self._quiet('orbitals', work, title)
        if cube is not None:
            self.cubes[key] = cube
            while len(self.cubes) > CUBES:
                self.cubes.popitem(last=False)
        return cube

    def _orbital_cube(self, index):
        from modules.spectrum.wavefunction import multiwfn

        grid = self.step.currentData()
        owner = self._owner()  # the grid from Multiwfn when it is there, else ours
        quiet = owner.property_tool.multiwfn_quiet(self.table_set) if owner is not None and hasattr(owner, 'property_tool') else None
        return self._cube(('orbital', id(self.table_set), index, grid, quiet is not None),
                          lambda step: multiwfn.field_cube(quiet, self.table_set, 'orbital', index, grid, progress=step),
                          tr('Орбиталь…'))

    def _orbital_title(self, index):
        o = self.table_set.orbitals[index]
        return ((tr(f'Орбиталь {o.number}') if self.table_set is self.orbital_set else tr(f'ЛМО {o.number}'))
                + ('' if o.spin == 'alpha' else ' β'))

    def show_orbital(self, toggle=False):
        index = self.current_orbital()
        if self.panel is None or self.busy:
            return False
        if toggle and self._toggled_off(('orbital', index)):
            return False
        if index is None:
            self.panel.status.setText(tr('Выберите орбиталь в таблице.'))
            return False
        cube = self._orbital_cube(index)
        if cube is None:
            return False
        o = self.table_set.orbitals[index]
        self.panel.status.setText(tr(f'Орбиталь {o.number}: сетка {" × ".join(map(str, cube.values.shape[:3]))}.'))
        return self._put(('orbital', index), bool(self.show_surface(cube, 'orbital', self.table_set,
                                                                    title=self._orbital_title(index))))

    def overlay_rows(self):
        """The rows of the orbitals put over the one on the model (Shift+click)."""
        owner = self._owner()
        source = getattr(owner, 'surface_source', None) if owner is not None else None
        if source is None or source is not self.shown_source or not self._same_set():
            return []
        return [also[1] for also in source.get('also', ())]

    def toggle_overlay(self, row):
        """Shift+click on a row — the
        orbital over the one on the model, each with its own colours; again — it goes. With no orbital of this table on
        the model it is simply shown. Returns the rows over the first one."""
        if self.panel is None or self.busy or not 0 <= row < len(self.table_set.orbitals):
            return []
        shown = self.on_model()
        if not shown or shown[0] != 'orbital' or not self._same_set():
            self.orbitals_table.selectRow(row)
            self.show_orbital(toggle=False)
            return []
        if row == shown[1]:
            return self.overlay_rows()
        owner = self._owner()
        source = owner.surface_source
        also = list(source.get('also', ()))
        if row in [a[1] for a in also]:
            also = [a for a in also if a[1] != row]
        else:
            cube = self._orbital_cube(row)
            if cube is None:
                return self.overlay_rows()
            also.append((cube, row, self._orbital_title(row)))
        source['also'] = tuple(also)
        if not owner.surface_tool.rebuild_surface():
            source['also'] = tuple(a for a in also if a[1] != row)
            owner.surface_tool.rebuild_surface()
        self.refresh_lights()
        return self.overlay_rows()

    def show_esp(self, toggle=True):
        """The ESP of Multiwfn on the surface ρ = 0.001 (a second press takes it away)."""
        owner = self._owner()
        if self.panel is None or owner is None or not hasattr(owner, 'surface_tool'):
            return False
        if toggle and self._toggled_off(('choice', ('surface', 'esp'))):
            return False
        path = owner.property_tool.orbitals_file(self.orbital_set)
        return self._put(('choice', ('surface', 'esp')), bool(path is not None and owner.surface_tool.multiwfn_esp(path)))

    def show_density(self, spin=False, esp=False, toggle=False):
        from modules.spectrum.wavefunction import multiwfn

        if self.panel is None or self.busy:
            return False
        if esp:
            return self.show_esp(toggle)
        key = ('spin',) if spin else ('density',)
        if toggle and self._toggled_off(key):
            return False
        grid = self.step.currentData()
        owner = self._owner()  # Multiwfn's grid when it is there, else ours
        quiet = owner.property_tool.multiwfn_quiet(self.orbital_set) if owner is not None and hasattr(owner, 'property_tool') else None
        cube = self._cube((key[0], grid, quiet is not None),
                          lambda step: multiwfn.field_cube(quiet, self.orbital_set, 'density', None, grid, spin,
                                                           progress=step),
                          tr('Плотность: орбитали…'))
        if cube is None:
            return False
        return self._put(key, bool(self.show_surface(cube, 'spin' if spin else 'density', self.orbital_set,
                                                     title=tr('Спиновая плотность') if spin else tr('Электронная плотность'))))


class DensityDrawerTool:
    """Was the mixin DensityDrawerActions of the window; a part of its own — it reaches the window only through
    the names of PORT (azimuth/window_port.WindowPort)."""

    PORT = (
        'density_drawer',
        'density_key',
        'document',
        'drawer',
        'load_result_orbitals',
        'navigate',
        'notify',
        'result_orbitals',
        'stack',
        'surface_tool',
        'trajectory_tool',
    )

    def __init__(self, window):
        from azimuth.window_port import WindowPort

        self.w = WindowPort(window, self.PORT)


    def build_density_drawer(self, drawer):
        self.w.density_key = None
        self.density_owner = None
        self.w.density_drawer = DensityDrawer(drawer)

    def density_available(self):
        path = self.w.result_orbitals() if self.w.has('result_orbitals') else None
        return path is not None or self.w.density_drawer.panel is not None

    def update_density_button(self):
        if not self.w.has('density_drawer'):
            return
        path = self.w.result_orbitals() if self.w.has('result_orbitals') else None
        owner = self.w.document() if self.w.has('document') else None
        held = self.w.density_drawer.panel is not None
        stale = self.w.density_key is not None and self.w.density_key[0] == 'path' and self.w.density_key != ('path', str(path))
        if held and (owner is not self.density_owner or stale):
            if owner is not self.density_owner:  # another tab — what this one had waits for it
                self.stash_density()
            self.w.density_drawer.clear()  # another tab or another result: its own orbitals, read when asked
            self.w.density_key = None
            held = False
        if not held and owner is not None:
            held = self.restore_density(owner, path)
        available = path is not None or held
        bar = self.w.drawer.tab_bar
        from modules.compass.panels.trajectory_drawer import PAGES as DRAWER_PAGES

        for name in PAGES:
            index = DRAWER_PAGES.index(name)
            bar.setTabEnabled(index, available)
            bar.setTabToolTip(index, '' if available else tr('В результате этой вкладки нет орбиталей'))
        if not available and self.w.drawer.page() in PAGES:
            self.w.drawer.set_page(self.w.drawer.best_page())
        if self.w.has('trajectory_tool'):
            self.w.trajectory_tool.update_result_button()

    STASHED = 6  # the tabs whose orbitals and critical points are kept while another tab is shown

    def stash_density(self):
        """The orbitals, the fragments, the critical points and the kind chosen of the
        tab left are kept in memory — not read from the file again, not searched again when it is shown again."""
        drawer, owner = self.w.density_drawer, self.density_owner
        if owner is None or drawer.panel is None or drawer.orbital_set is None or self.w.density_key is None:
            return False
        panel = drawer.panel
        try:
            state = panel.handover_state()
            kind = panel.kind_filter.currentData()
        except (RuntimeError, AttributeError):
            return False
        stash = getattr(self, '_stashed', None)
        if stash is None:
            stash = self._stashed = {}
        stash.pop(id(owner), None)
        stash[id(owner)] = (owner, self.w.density_key, drawer.orbital_set, panel.source, state, kind)
        while len(stash) > self.STASHED:
            stash.pop(next(iter(stash)))
        return True

    def restore_density(self, owner, path):
        """The tab shown again gets what it had (stash_density) — when its result is still the same."""
        stash = getattr(self, '_stashed', None) or {}
        entry = stash.get(id(owner))
        if entry is None or entry[0] is not owner:
            return False
        _, key, orbital_set, source, state, kind = stash.pop(id(owner))
        if key[0] == 'path' and key != ('path', str(path)):
            return False  # another result in the tab: its own orbitals, read when asked
        drawer = self.w.density_drawer
        panel = drawer.set_content(orbital_set, source, self.w.surface_tool.show_surface,
                                   getattr(self.w.surface_tool, 'show_aim', None), state)
        self.w.density_key = key
        self.density_owner = owner
        if panel is not None and kind:
            panel.follow_kind(kind)
        return True

    def ensure_density_content(self):
        """A page of the orbitals was opened: read the orbitals of the result once."""
        drawer = self.w.density_drawer
        path = self.w.result_orbitals() if self.w.has('result_orbitals') else None
        if path is None or (drawer.panel is not None and self.w.density_key and self.w.density_key[0] == 'given'):
            return drawer if drawer.panel is not None else None  # orbitals given by Spectrum stay
        key = ('path', str(path))
        if key == self.w.density_key and drawer.panel is not None:
            return drawer
        loaded = self.w.load_result_orbitals()
        if loaded is None:
            return None
        orbital_set, source = loaded
        drawer.set_content(orbital_set, source, self.w.surface_tool.show_surface, getattr(self.w.surface_tool, 'show_aim', None))
        self.w.density_key = ('path', str(self.w.result_orbitals()))  # a .gbw became its Molden file
        self.density_owner = self.w.document() if self.w.has('document') else None
        return drawer

    def open_density_drawer(self, orbital_set=None, source='', tab=0, state=None):
        """Open the drawer on the orbitals (or QTAIM) with the orbitals of the result or those given by Spectrum."""
        drawer = self.w.density_drawer
        if orbital_set is not None:
            key = ('given', id(orbital_set))
            if key != self.w.density_key or drawer.panel is None or state:
                drawer.set_content(orbital_set, source, self.w.surface_tool.show_surface, getattr(self.w.surface_tool, 'show_aim', None), state)
                self.w.density_key = key
            self.density_owner = self.w.document() if self.w.has('document') else None
        else:
            if self.w.result_orbitals() is None and drawer.panel is None:
                self.w.notify(tr('В результате этой вкладки нет орбиталей.'), 6000)
                return None
            if state:
                self.w.density_key = None
            if self.ensure_density_content() is None:
                return None
            if state:
                drawer.set_content(drawer.orbital_set, source or drawer.panel.source, self.w.surface_tool.show_surface,
                                   getattr(self.w.surface_tool, 'show_aim', None), state)
        page, sub = TAB_PAGES.get(tab, ('orbitals', 0)) if isinstance(tab, int) else ('orbitals', 0)
        self.update_density_button()
        if self.w.has('navigate') and self.w.stack.currentIndex() != 0:
            self.w.navigate(0)
        self.w.trajectory_tool.set_trajectory_open(True, page)
        drawer.update_surfaces_page()
        drawer.refresh_lights()
        return drawer

    def update_surfaces_page(self):
        """The page «Поверхности» after Multiwfn was chosen (or the result changed)."""
        return self.w.density_drawer.update_surfaces_page()

    def set_density_open(self, opened):
        if opened:
            if self.open_density_drawer() is None:
                return
        elif self.w.drawer.page() in PAGES:
            self.w.trajectory_tool.set_trajectory_open(False)

    def toggle_density_drawer(self):
        self.set_density_open(not self.w.density_drawer.isVisible())
