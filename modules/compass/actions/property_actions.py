"""Compass: properties of a calculation result on the model — charges, spin populations, Mayer
valences and bond orders, the dipole moment, the forces.

The ORCA output opened in Spectrum (or as optimization steps in Compass) gives Properties of its final
geometry (modules/spectrum/readers/orca_properties.py). The «±» button above the model and «Вид → Свойства из
расчёта» choose what is drawn; it is drawn only while the structure on screen is that geometry (turned
or not), see modules/compass/view/result_overlay.py. «Связи по порядкам Майера» replaces the bonds of the
structure by those of the result (undoable).
«Заряды ADCH и CM5 (Multiwfn)…» runs Multiwfn on the wavefunction of the result
(modules/spectrum/wavefunction/multiwfn.py) in the background and adds the charges to the properties; it is offered
while the result has a wavefunction file.
The items of Multiwfn are off with a hint how to install it when it is not found (multiwfn_found, no file
dialog); «Программа Multiwfn…» of the menu of the surfaces chooses the file (choose_multiwfn_program); an old
Multiwfn (before 3.8) is told once (multiwfn_version_said).
"""


from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QActionGroup
from PySide6.QtWidgets import QMenu

from modules.compass.view import result_overlay
from azimuth.i18n import tr
from azimuth.ui import smooth
from modules.compass.actions import property_multiwfn as _multiwfn
from modules.compass.actions.property_multiwfn import BOND_SETS
from modules.compass.actions import property_queues as _queues
from modules.compass.actions import property_crystal as _crystal


BOND_TITLES = {
    'Mayer': ('Порядки связей Майера', 'Связи по порядкам Майера'),
    'Wiberg': ('Порядки связей Виберга (xtb)', 'Связи по порядкам Виберга'),
    # from the wavefunction; named apart from the Wiberg orders of xtb (two «Виберг» in «±» before)
    'Wiberg-Löwdin': ('Порядки связей Виберга–Лёвдина', 'Связи по порядкам Виберга–Лёвдина'),
    'Fuzzy': ('Нечёткие порядки связей (FBO)', 'Связи по нечётким порядкам'),
    'Laplacian': ('Лапласиановы порядки связей (LBO)', 'Связи по лапласиановым порядкам'),
}


class _VersionNotes(QObject):
    """The version of Multiwfn met in a run (a worker thread) told to the window in its own thread."""

    said = Signal(str, bool)


class PropertyTool:
    """Was the mixin PropertyActions of the window; a part of its own — it reaches the window only through
    the names of PORT (azimuth/window_port.WindowPort)."""

    PORT = (
        '_fukui_fields',
        '_overlay_cache',
        'browsing',
        'compass_mode',
        'cores',
        'crystal',
        'document',
        'density_tool',
        'drawer',
        'error',
        'load_result_orbitals',
        'model_menu_tool',
        'molecule',
        'notify',
        'orbital_files',
        'output_path',
        'overlay_choice',
        'preferences',
        'properties_menu',
        'custom_bar',  # where the buttons of the properties stand (properties_hint)
        'property_buttons',
        'property_menus',
        'result_molden_path',
        'result_properties',
        'result_source',
        'sibling_gbw',
        'sibling_molden',
        'surface_source',
        'surface_tool',
        'trajectory_tool',  # the steps opened for their forces (show_forces_somewhere)
        'viewer',
    )

    def __init__(self, window):
        from azimuth.window_port import WindowPort

        self.w = WindowPort(window, self.PORT)


    def build_property_actions(self):
        self.w.result_properties = None
        self.w.result_source = ''
        self.w.overlay_choice = {'atom': None, 'bonds': False, 'dipole': False, 'forces': False}
        self.w._overlay_cache = (None, None, None)
        self.w.properties_menu = smooth(QMenu(tr('Свойства из расчёта'), self.w.widget))
        self.w.properties_menu.aboutToShow.connect(lambda: self.fill_properties_menu(self.w.properties_menu))
        # the menus of the three buttons above the model («±» split)
        self.w.property_menus = {}
        for part in self.PROPERTY_PARTS:
            box = smooth(QMenu(self.w.widget))
            box.aboutToShow.connect(lambda b=box, p=part: self.fill_properties_menu(b, p))
            self.w.property_menus[part] = box
        self.w.viewer.overlay_source = self.result_overlay
        from modules.spectrum.wavefunction import multiwfn

        self._multiwfn_notes = _VersionNotes(self.w.widget)
        self._multiwfn_notes.said.connect(self.multiwfn_version_said)
        multiwfn.on_version = self._multiwfn_notes.said.emit

    def multiwfn_version_said(self, number, old):
        """An old Multiwfn (before 3.8) is told once: some items of the recipes are missing in it."""
        if old:
            self.w.notify(tr(f'Работает старый Multiwfn {number}: часть анализов в нём не работает. Нужен 3.8 или новее '
                           '(macOS: brew install multiwfn) — «Поверхность на модели → Программа Multiwfn…».'), 15000)

    def set_result_properties(self, props, source='', announce=False):
        """announce: a result just opened or calculated — its properties told once (first_time_told); the
        charges and the orders computed later for it and a tab shown again say nothing. A result just
        opened gets the charges computed for it before (saved_charges)."""
        if announce and props is not None:
            props = self.saved_charges(props)
        self.w.result_properties = props
        self.w.result_source = source
        self.w._overlay_cache = (None, None, None)
        if props is not None and not any(self.w.overlay_choice.values()) and announce and self.first_time_told(props, source):
            self.w.notify(self.properties_hint(), 12000)
        self.w.viewer.update()

    BUTTON_NAMES = (('atoms', 'Атомы'), ('bonds', 'Связи'), ('vectors', 'Диполь и силы'))

    def properties_hint(self):
        """The buttons of the properties named where they stand now (the panels of the model are the
        user's: custom_bar) — above the model, right of it, or both; none on the panels — the menu only."""
        bar = getattr(self.w, 'custom_bar', None) if self.w.has('custom_bar') else None
        places = {}
        for key, name in self.BUTTON_NAMES:
            try:
                # the keys kept by the panels: 'default:atoms' for a button from the start, 'atoms' otherwise
                place = (bar.where('default:' + key) or bar.where(key)) if bar is not None else 'rail'
            except Exception:  # noqa: BLE001 — the panels not known: as they are made
                place = 'rail'
            if place:
                places.setdefault(place, []).append('«' + tr(name) + '»')
        if not places:
            return tr('В результате есть свойства атомов и связей — «Расчёт → Свойства из расчёта».')
        where = {'top': tr('над моделью'), 'rail': tr('справа от модели')}
        parts = []
        for place in ('top', 'rail'):
            if place in places:
                names = ', '.join(places[place])
                word = tr('кнопка') if len(places[place]) == 1 else tr('кнопки')
                parts.append(f'{word} {names} {where[place]}')
        return tr('В результате есть свойства атомов и связей — {} или «Расчёт → Свойства из расчёта».').format(
            '; '.join(parts))

    def saved_charges(self, props):
        """The charges Multiwfn computed before for the orbitals of this result (ADCH and CM5, Hirshfeld and its spins,
        RESP: the outputs kept in «Анализ», field_tables.saved_output — a few KB each, the file of orbitals not read)
        joined to its properties; those it has already stay. AIM too — from the values kept beside its output."""
        from dataclasses import replace

        from modules.spectrum.wavefunction import field_tables, multiwfn, multiwfn_populations, multiwfn_resp

        orbitals = getattr(self.w, 'sibling_molden', None) or getattr(self.w, 'sibling_gbw', None)
        geometry = getattr(props, 'geometry', None)
        if orbitals is None or geometry is None:
            return props
        count = len(geometry.atoms)
        charges, spins = dict(props.charges), dict(props.spins)

        def take(name, parse):
            text = field_tables.saved_output(orbitals, name)
            try:
                return parse(text) if text else None
            except (ValueError, IndexError, KeyError):
                return None

        for key, values in (take('charges', multiwfn.parse_charges) or {}).items():
            if key not in charges and len(values) == count:
                charges[key] = tuple(values)
        hirshfeld = take('hirshfeld', multiwfn_populations.parse_hirshfeld)
        if 'hirshfeld' not in charges and hirshfeld and len(hirshfeld) == count:
            charges['hirshfeld'] = tuple(hirshfeld)
            self.computed_hirshfeld = charges['hirshfeld']  # computed, not printed: it can be computed again
        hirshfeld_spins = take('hirshfeld_spins', multiwfn_populations.parse_fuzzy)
        if 'hirshfeld' not in spins and hirshfeld_spins and len(hirshfeld_spins) == count:
            spins['hirshfeld'] = tuple(hirshfeld_spins)
        resp = take('resp', multiwfn_resp.parse_resp)
        if 'resp' not in charges and resp and len(resp[0]) == count:
            charges['resp'] = tuple(resp[0])
        # the charges and spins of the basins
        # of AIM, kept as values (multiwfn_aim)
        import json

        aim = take('aim_values', json.loads)
        if isinstance(aim, dict):
            values = aim.get('charges') or []
            if 'aim' not in charges and len(values) == count:
                charges['aim'] = tuple(float(v) for v in values)
            values = aim.get('spins') or []
            if 'aim' not in spins and len(values) == count:
                spins['aim'] = tuple(float(v) for v in values)
        if charges == props.charges and spins == props.spins:
            return props
        return replace(props, charges=charges, spins=spins)

    def first_time_told(self, props, source=''):
        """Once for a result.
        a result is its file as it is (its path, size and time) — choosing the molecule again reads it anew, a new
        object of the same result; a result with no file — by the properties read, as before."""
        from pathlib import Path

        told = getattr(self, '_told_properties', None)
        if told is None:
            told = self._told_properties = []
        key = props
        geometry = getattr(props, 'geometry', None)
        if source:  # a name only (the tab keeps the name of its file): the name and the geometry of the result
            key = (str(source), geometry.xyz() if geometry is not None and hasattr(geometry, 'xyz') else '')
        try:
            path = Path(str(source)) if source else None
            if path is not None and path.is_file():
                stat = path.stat()
                key = (str(path.resolve()), stat.st_size, stat.st_mtime_ns)
        except OSError:
            pass
        if any(item is key or (isinstance(key, tuple) and item == key) for item in told):
            return False
        told.append(key)
        del told[:-64]
        return True

    def browsed_step_gradient(self):
        """(geometry, gradient) of the optimization step shown from the drawer, if it has one."""
        drawer = getattr(self.w, 'drawer', None)
        if not getattr(self.w, 'browsing', False) or drawer is None or not 0 <= drawer.current < len(drawer.steps):
            return None
        step = drawer.steps[drawer.current]
        gradient = getattr(step, 'gradient', None)
        return (step.geometry, gradient) if gradient and step.geometry is not None else None

    def steps_have_gradient(self):
        drawer = getattr(self.w, 'drawer', None)
        return drawer is not None and any(getattr(s, 'gradient', None) for s in drawer.steps)

    def result_overlay(self, molecule):
        """What the viewer draws for molecule (cached for the same structure and choice)."""
        if getattr(self.w, 'compass_mode', 'molecule') == 'crystal':
            return self.crystal_overlay(molecule)  # the charges of the crystal on its atoms
        step = self.browsed_step_gradient() if self.w.overlay_choice.get('forces') else None
        if step is not None:  # the forces of the step shown, turned with it like the result's
            from modules.spectrum.readers.orca_properties import Properties

            shown = result_overlay.overlay(Properties(step[0], gradient=step[1]), molecule, {'forces': True})
            return shown
        if self.w.result_properties is None or not any(self.w.overlay_choice.values()):
            return None
        key = (id(self.w.result_properties), tuple(sorted(self.w.overlay_choice.items())))
        cached_molecule, cached_key, shown = self.w._overlay_cache
        if cached_molecule is not molecule or cached_key != key:
            shown = result_overlay.overlay(self.w.result_properties, molecule, self.w.overlay_choice)
            self.w._overlay_cache = (molecule, key, shown)
        return shown

    # three buttons above the model — «Атомы» (the values at the atoms and the analyses that give them), «Связи» (the
    # bond orders), «Диполь и силы»; fill_properties_menu (the menus «Вид» and «Расчёт») has them all, one after another
    PROPERTY_PARTS = ('atoms', 'bonds', 'vectors')

    def show_property_menu(self, part):
        """The menu of a button above the model, filled before it is shown — filled only in aboutToShow it was
        empty at the first press and Qt did not open it (on Windows the buttons worked from the second press); a press
        on the button of the menu open closes it (hub.header.MenuToggle) instead of opening it again."""
        menu, button = self.w.property_menus[part], self.w.property_buttons[part]
        self.fill_properties_menu(menu, part)  # the second press closing it: menu_actions._popup (MenuToggle)
        self.w.model_menu_tool._popup(button, menu)

    def result_open_shell(self):
        """True / False — the result is an open / closed shell; None — not known. The spins of the output, or
        the multiplicity it printed (read once per file)."""
        from pathlib import Path

        props = self.w.result_properties
        if props is not None and props.spins:
            return True
        path = getattr(self.w, 'output_path', None)
        if not path:
            return None
        from azimuth.runtime.provenance import fingerprint

        stamp = fingerprint(path)  # by its content
        if stamp is None:
            return None
        cached = getattr(self, '_open_shell_cache', None)
        if cached is not None and cached[0] == stamp:
            return cached[1]
        from modules.spectrum.analysis.thermo import find_multiplicity

        try:
            text = Path(path).read_text(encoding='utf-8', errors='replace')[:4_000_000]
        except OSError:
            text = ''
        found = find_multiplicity(text) if text else None
        answer = None if found is None else found > 1
        self._open_shell_cache = (stamp, answer)
        return answer

    def fill_properties_menu(self, menu, part=None):
        """The menu of the properties of the result: part ∈ PROPERTY_PARTS — one button's, None — all of them."""
        if getattr(self.w, 'compass_mode', 'molecule') == 'crystal' and part in ('atoms', 'bonds'):
            return self.fill_crystal_menu(menu, part)  # the results of the crystal of the project
        menu.clear()
        menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        menu.setWindowFlags(menu.windowFlags() | Qt.WindowType.FramelessWindowHint)
        menu.setToolTipsVisible(True)
        props = self.w.result_properties
        if props is None:
            item = menu.addAction(tr('Откройте результат ORCA с анализом заселённостей (Спектр → Файл)'))
            item.setEnabled(False)
            if self.has_wavefunction() and part != 'vectors':
                menu.addSeparator()
                if part in (None, 'atoms'):
                    box = smooth(QMenu(tr('Посчитать по волновой функции'), menu))
                    box.setToolTipsVisible(True)
                    self.add_multiwfn_item(box)
                    menu.addMenu(box)
                if part in (None, 'bonds'):
                    self.add_bond_order_items(menu)
            return
        matches = result_overlay.match(props, self.w.molecule) is not None
        head = menu.addAction(tr('Из файла: ') + self.w.result_source if self.w.result_source else tr('Из результата ORCA'))
        head.setEnabled(False)
        if not matches:
            item = menu.addAction(
                tr(
                    'На модели другая структура — возьмите последнюю геометрию результата (Спектр), чтобы увидеть свойства'
                )
            )
            item.setEnabled(False)
        menu.addSeparator()
        if part in (None, 'atoms'):
            self.fill_atom_values(menu, props)
        if part in (None, 'bonds'):
            if part is None:
                menu.addSeparator()
            self.fill_bond_values(menu, props, matches)
        if part in (None, 'vectors'):
            if part is None:
                menu.addSeparator()
            self.fill_vector_values(menu, props)

    # the values at the atoms by their kind, each kind a submenu; the analyses that give more — a submenu of their own
    ATOM_GROUPS = (
        ('Заряды', ('mulliken', 'loewdin', 'hirshfeld', 'cm5', 'adch', 'resp', 'aim', 'apt', 'xtb', 'mopac')),
        ('Спиновые заселённости', ('spin-mulliken', 'spin-loewdin', 'spin-hirshfeld', 'spin-aim')),
        ('Функции Фукуи', ('fukui-plus', 'fukui-minus', 'fukui-zero', 'fukui-dual')),
    )

    def fill_atom_values(self, menu, props):
        """«Атомы» — what is written at the atoms (charges, spins, valences…) and the analyses giving more;
        the kinds as submenus («Заряды», «Спиновые заселённости», «Функции Фукуи»), the analyses of Multiwfn
        in «Посчитать по волновой функции»; a kind whose value is on the model has a «•» in its title."""
        group = QActionGroup(menu)
        group.setExclusive(True)
        keys = result_overlay.available(props)
        chosen = self.w.overlay_choice['atom']

        def item(where, key):
            title = tr('Без подписей у атомов') if key is None else tr(result_overlay.ATOM_VALUES[key][2])
            action = where.addAction(title)
            action.setCheckable(True)
            action.setEnabled(key is None or key in keys)
            action.setChecked(chosen == key)
            action.triggered.connect(lambda checked=False, k=key: self.choose_overlay('atom', k))
            group.addAction(action)
            return action

        item(menu, None)
        grouped = set()
        for title, members in self.ATOM_GROUPS:
            grouped.update(members)
            box = smooth(QMenu(tr(title), menu))
            box.setToolTipsVisible(True)
            for key in members:
                item(box, key)
            if chosen in members:
                box.setTitle(tr(title) + ' •')
            box.setEnabled(any(k in keys for k in members))
            menu.addMenu(box)
        for key in result_overlay.ATOM_VALUES:  # the rest (the valence of Mayer) as they are
            if key not in grouped:
                item(menu, key)
        menu.addSeparator()
        box = smooth(QMenu(tr('Посчитать по волновой функции'), menu))
        box.setToolTipsVisible(True)
        self.add_multiwfn_item(box)
        menu.addMenu(box)

    def fill_bond_values(self, menu, props, matches):
        """«Связи» — the bond orders on the model, the sets of them, taking them as the bonds."""
        name, title, present = 'bonds', tr(BOND_TITLES.get(props.bond_kind, BOND_TITLES['Mayer'])[0]), bool(props.mayer_bonds)
        item = menu.addAction(title)
        item.setCheckable(True)
        item.setEnabled(present)
        item.setChecked(bool(self.w.overlay_choice[name]) and present)
        item.toggled.connect(lambda on, n=name: self.choose_overlay(n, on))
        item = menu.addAction(tr(BOND_TITLES.get(props.bond_kind, BOND_TITLES['Mayer'])[1]))
        item.setEnabled(matches and bool(props.mayer_bonds) and not self.w.browsing)
        item.setToolTip(
            tr('Заменить связи структуры: порядок ≥ 0,5 — связь; 1,25–1,75 в шестичленном цикле — ароматическая')
        )
        item.triggered.connect(self.take_mayer_bonds)
        menu.addSeparator()
        self.add_bond_order_items(menu, props)

    def fill_vector_values(self, menu, props):
        """«Диполь и силы» — the arrows of a result."""
        for name, title, present in (
            ('dipole', tr('Дипольный момент (стрелка от − к +)'), props.dipole is not None),
            ('forces', tr('Силы на атомах (минус градиент)'), props.gradient is not None or self.steps_have_gradient()),
        ):
            item = menu.addAction(title)
            item.setCheckable(True)
            item.setEnabled(present)
            item.setChecked(bool(self.w.overlay_choice[name]) and present)
            if name == 'forces' and not present:
                item.setToolTip(
                    tr(
                        'В файле нет градиента для последней геометрии (после оптимизации он относится к предыдущему шагу)'
                    )
                )
            elif name == 'forces' and props.gradient is None:
                item.setToolTip(tr('Силы есть у шагов оптимизации: они видны, когда шаг выбран в панели шагов'))
            item.toggled.connect(lambda on, n=name: self.choose_overlay(n, on))

    # -- bond orders from the wavefunction ----------------------------------------------------------------------
    def add_bond_order_items(self, menu, props=None):
        # the donor–acceptor bond of a result of the queue «CDA» of Sextant (the complex and its fragments)
        cda = menu.addAction(tr('Донорно-акцепторная связь (CDA)…'))
        enabled, tip = self.multiwfn_ready(tr('Донирование d, обратное донирование b и отталкивание r между двумя '
                                              'фрагментами (Дапприх — Френкинг) по орбиталям комплекса и фрагментов'))
        folder = self.cda_folder()
        cda.setEnabled(enabled and folder is not None)
        cda.setToolTip(tip if folder is not None else tr('Сначала посчитайте в Секстанте задачу «Донорно-акцепторная '
                                                         'связь CDA» — комплекс и два фрагмента на одной геометрии'))
        cda.triggered.connect(lambda *a: self.show_cda(self.cda_folder()))
        menu.addSeparator()
        item = menu.addAction(tr('Порядки связей: Майер, Виберг, FBO, LBO…'))
        enabled, tip = self.multiwfn_ready(tr('Четыре определения порядка связи по волновой функции результата'))
        item.setEnabled(enabled)
        item.setToolTip(tip)
        item.triggered.connect(self.multiwfn_bond_orders)
        sets = getattr(props, 'bond_sets', None) or {}
        if sets:
            group = QActionGroup(menu)
            group.setExclusive(True)
            for kind in (k for _, k in BOND_SETS if k in sets):
                choice = menu.addAction('   ' + tr(BOND_TITLES[kind][0]))
                choice.setCheckable(True)
                choice.setChecked(props.bond_kind == kind)
                choice.triggered.connect(lambda checked=False, k=kind: self.choose_bond_set(k))
                group.addAction(choice)

    def choose_bond_set(self, kind):
        from dataclasses import replace

        props = self.w.result_properties
        if props is None or kind not in props.bond_sets:
            return False
        self.w.result_properties = replace(props, mayer_bonds=tuple(props.bond_sets[kind]), bond_kind=kind)
        self.w.overlay_choice['bonds'] = True
        self.w._overlay_cache = (None, None, None)
        self.w.viewer.update()
        return True

    multiwfn_bond_orders = _multiwfn.multiwfn_bond_orders
    has_wavefunction = _multiwfn.has_wavefunction
    multiwfn_ready = _multiwfn.multiwfn_ready
    add_multiwfn_item = _multiwfn.add_multiwfn_item
    orbital_spins = _multiwfn.orbital_spins
    _population_target = _multiwfn._population_target
    multiwfn_hirshfeld = _multiwfn.multiwfn_hirshfeld
    multiwfn_resp = _multiwfn.multiwfn_resp
    cda_folder = _queues.cda_folder
    show_cda = _queues.show_cda
    cda_orbital = _queues.cda_orbital
    _queue_folder = _queues._queue_folder
    fukui_folder = _queues.fukui_folder
    show_fukui = _queues.show_fukui

    # the fields, not only the atoms
    FUKUI_STEPS = {'low': 0.25, 'medium': 0.15, 'high': 0.10}  # Å, the grid of «Сетка расчёта»
    FUKUI_TITLES = {'plus': 'f⁺ = ρ(N+1) − ρ(N): куда придёт электрон — атака нуклеофила',
                    'minus': 'f⁻ = ρ(N) − ρ(N−1): откуда уйдёт электрон — атака электрофила',
                    'zero': 'f⁰ = (f⁺ + f⁻)/2: атака радикала',
                    'dual': 'Δf = f⁺ − f⁻: синее — электрофильные места, красное — нуклеофильные'}

    fukui_surface = _queues.fukui_surface
    multiwfn_aim = _multiwfn.multiwfn_aim
    multiwfn_found = _multiwfn.multiwfn_found
    multiwfn_program = _multiwfn.multiwfn_program
    choose_multiwfn_program = _multiwfn.choose_multiwfn_program
    multiwfn_source = _multiwfn.multiwfn_source
    remember_orbitals_file = _multiwfn.remember_orbitals_file
    orbitals_file = _multiwfn.orbitals_file
    multiwfn_quiet = _multiwfn.multiwfn_quiet
    multiwfn_for = _multiwfn.multiwfn_for
    multiwfn_charges = _multiwfn.multiwfn_charges

    def clear_model_overlays(self):
        """Everything laid over the structure goes — the values at the atoms, the bond orders, the dipole and
        the forces, the surface (orbital, density, ESP, NCI, Fukui…), the critical points; the structure, its own labels
        and the measurements stay. → what was taken away (titles)."""
        gone = []
        # each by its name
        choice = self.w.overlay_choice
        if choice.get('atom'):
            key = choice['atom']
            source = result_overlay.ATOM_VALUES.get(key) or result_overlay.CRYSTAL_LABELS.get(key)
            title = source[2] if isinstance(source, tuple) else source
            named = tr(title) if title else tr('значения на атомах')
            gone.append(named[:1].lower() + named[1:])  # «заряды Малликена»: the name keeps its capital
        if choice.get('bonds'):
            gone.append(tr('порядки связей'))
        if choice.get('dipole'):
            gone.append(tr('дипольный момент'))
        if choice.get('forces'):
            gone.append(tr('силы на атомах'))
        self.w.overlay_choice = {'atom': None, 'bonds': False, 'dipole': False, 'forces': False}
        self.w._overlay_cache = (None, None, None)
        if getattr(self.w.document(), 'crystal_labels', None):  # the charges of a crystal
            self.w.document().crystal_labels = None
            gone.append(tr('заряды кристалла'))
        if getattr(self.w, 'surface_source', None) is not None and self.w.has('surface_tool'):
            self.w.surface_tool.clear_surface()
            gone.append(tr('поверхность'))
        if getattr(self.w.viewer, 'aim', None) is not None and self.w.has('surface_tool'):
            self.w.surface_tool.clear_aim()
            gone.append(tr('критические точки'))
        self.w.viewer.update()
        self.w.notify(tr('С модели убрано: ') + ', '.join(gone) + '.' if gone else tr('На модели ничего не наложено.'),
                    6000)
        return gone

    def choose_overlay(self, name, value):
        self.w.overlay_choice[name] = value
        self.w.viewer.update()
        if name == 'forces' and value:
            self.show_forces_somewhere()

    def show_forces_somewhere(self):
        """«Силы на атомах» chosen and nothing to draw on the
        model — the result has no gradient of its last geometry (after an optimization it belongs to the step before):
        the steps of the optimization open at the last step with a gradient, and the forces are drawn there; the
        structure of the tab changed since the result — said."""
        props = getattr(self.w, 'result_properties', None)
        if props is not None and props.gradient is not None:
            if result_overlay.overlay(props, self.w.molecule, {'forces': True}) is None:
                self.w.notify(tr('Силы относятся к геометрии результата, а структура на модели с тех пор изменилась.'),
                              9000)
            return None
        if self.browsed_step_gradient() is not None:
            return None
        drawer = getattr(self.w, 'drawer', None)
        if drawer is None or not self.steps_have_gradient():
            return None
        last = max(k for k, step in enumerate(drawer.steps) if getattr(step, 'gradient', None))
        self.w.trajectory_tool.set_trajectory_open(True, 'steps')
        drawer.select(last)
        self.w.notify(tr('Градиент есть у шагов оптимизации, не у последней геометрии: показан шаг {} с силами.').format(
            last + 1), 9000)
        return last

    def take_mayer_bonds(self):
        from dataclasses import replace

        try:
            result = result_overlay.mayer_structure(self.w.result_properties, self.w.molecule)
        except (ValueError, TypeError) as exc:
            self.w.error(exc)
            return
        # a delocalized bond of a six-membered ring (order 1.5) went into the structure as it was —
        # the model draws and the project keeps whole orders only (1, 2, 3): the drawing failed and the project saved
        # with it was refused. It is a single bond with the mark «ароматическая» of «Стиль связей» (bond_marks) now
        aromatic = [(min(i, j), max(i, j)) for i, j, order in result.bonds if order != int(order)]
        result = replace(result, bonds=tuple((i, j, int(order) if order == int(order) else 1)
                                             for i, j, order in result.bonds))
        if getattr(self.w.result_properties, 'bond_kind', 'Mayer') == 'Wiberg':
            self.w.model_menu_tool.edit_structure(result, tr(f'Связи взяты из порядков Виберга: {len(result.bonds)}.'))
        else:
            self.w.model_menu_tool.edit_structure(result, tr(f'Связи взяты из порядков Майера: {len(result.bonds)}.'))
        if aromatic:
            marks = dict(getattr(self.w.viewer, 'bond_marks', {}) or {})
            for key in aromatic:
                marks[key] = {**(marks.get(key) or {}), 'kind': 'aromatic'}
            self.w.viewer.bond_marks = marks
            self.w.viewer.update()


    # -- the results of a crystal in «Компас · Кристалл» -----------------------------------------------------
    # «Атомы» and «Связи» above the model of a crystal, as for a molecule: the charges of Multiwfn (CM5, Hirshfeld) of
    # the last CP2K run of its project as labels on its atoms
    # (crystal_results.model_charges: the supercell computed onto the atoms of the model), the bonds by AIM as a table;
    # computed when asked, kept beside the run (charges.csv, aim-bonds.csv) and shown again from there.
    CRYSTAL_CHARGES = {'cm5': 'Заряды CM5', 'hirshfeld': 'Заряды Хиршфельда'}
    # the labels of the structure (crystal_energetics.model_labels), no calculation needed
    STRUCTURE_LABELS = {'oxidation': 'Степени окисления', 'bvs': 'Суммы валентностей связей',
                        'fractional': 'Дробные координаты', 'site': 'Позиции: метка, кратность, симметрия'}

    crystal_run = _crystal.crystal_run
    fill_crystal_menu = _crystal.fill_crystal_menu
    show_crystal_charges = _crystal.show_crystal_charges
    crystal_overlay = _crystal.crystal_overlay
    compute_crystal_charges = _crystal.compute_crystal_charges
    crystal_field = _crystal.crystal_field
    crystal_charges_table = _crystal.crystal_charges_table
    crystal_aim = _crystal.crystal_aim


