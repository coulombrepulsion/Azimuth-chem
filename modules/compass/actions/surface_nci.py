"""NCI, IRI and IGMH of Multiwfn on the model of Compass: the grid, the tables (CSV), the menu, the surfaces, their
domains and markers, the plot of the tab «NCI». Methods of SurfaceTool (self is the tool; the window only through its
port self.w), kept here to make surface_actions.py shorter.

Split off modules/compass/actions/surface_actions.py (0.222.30).
"""

import numpy as np
from PySide6.QtGui import QActionGroup
from modules.compass.view import surfaces
from modules.compass.actions.property_multiwfn import MULTIWFN_HINT as MULTIWFN_HINT_TEXT
from azimuth.i18n import tr


WEAK = ('nci', 'iri', 'igmh')  # the surfaces of weak interactions — coloured by sign(λ₂)ρ, with their domains


SURFACE_TITLES = {
    'orbital': 'Орбиталь',
    'density': 'Электронная плотность',
    'spin': 'Спиновая плотность',
    'laplacian': 'Лапласиан −∇²ρ: синее — концентрация заряда, красное — его недостаток',
    'difference': 'Разность плотностей Δρ: синее — электронов прибавилось, красное — убыло',
    'nci': 'Слабые взаимодействия NCI (RDG)',
    'iri': 'Связи и слабые взаимодействия IRI',
    'esp-surface': 'ESP на молекулярной поверхности ρ = 0,001',
    'elf': 'ELF — где электроны парами: связи, неподелённые пары, остовы',
    'lol': 'LOL — локализованные орбитали: связи и неподелённые пары',
    'excitation': 'Возбуждение: дырка (синее) и электрон (зелёное)',
    'fukui': 'Функция Фукуи: синее — больше нуля, красное — меньше',
    'void': 'Пустоты кристалла',
    'hirshfeld': 'Поверхность Хиршфельда',
    'igmh': 'Взаимодействия молекул IGMH (δg_inter)',
}


GRIDS = (('low', 'Грубая сетка (быстро)'), ('medium', 'Средняя сетка'), ('high', 'Точная сетка (долго)'))


def xyz_key(molecule):
    """A key of a structure for the cache of the promolecular NCI."""
    return tuple((a.symbol, round(a.x, 6), round(a.y, 6), round(a.z, 6)) for a in molecule.atoms) if molecule else ()


# -- one grid for every field and the style of the tables --------------------------------------------------
def nci_grid(self):
    settings = getattr(self.w, 'preferences', None)
    grid = settings.value('multiwfn_grid', 'low') if settings is not None else 'low'
    return grid if grid in dict(GRIDS) else 'low'


def set_nci_grid(self, grid):
    """The grid of Multiwfn (low, medium, high) — of the menu and of «Сетка» of the drawer, the same choice."""
    settings = getattr(self.w, 'preferences', None)
    if settings is not None:
        settings.setValue('multiwfn_grid', grid)
    drawer = getattr(self.w, 'density_drawer', None)
    if drawer is not None and hasattr(drawer, 'sync_grid'):
        drawer.sync_grid(grid)  # «Сетка» of every page of the drawer
        if hasattr(drawer, 'rebuild_on_model'):  # what is on the model — again, on the new grid
            drawer.rebuild_on_model()


def add_grid_menu(self, menu):
    sub = menu.addMenu(tr('Сетка расчёта'))
    group = QActionGroup(sub)
    current = self.nci_grid()
    for key, title in GRIDS:
        item = sub.addAction(tr(title))
        item.setCheckable(True)
        item.setChecked(key == current)
        item.triggered.connect(lambda checked=False, k=key: self.set_nci_grid(k))
        group.addAction(item)
    return sub


def csv_style(self):
    settings = getattr(self.w, 'preferences', None)
    chosen = settings.value('csv_style', 'ru') if settings is not None else 'ru'
    from modules.spectrum.wavefunction import field_tables

    return field_tables.valid_style(chosen)  # also a separator and a decimal sign of «Настройки»


def set_csv_style(self, chosen):
    from modules.spectrum.wavefunction import field_tables

    settings = getattr(self.w, 'preferences', None)
    if settings is not None:
        settings.setValue('csv_style', chosen)
    field_tables.style = chosen


def add_table_menu(self, menu):
    """«Таблицы CSV…» opens «Файл → Настройки…» at the tables (the separator and the decimal sign apart;
    was a submenu of two styles here — the user did not find the choice of the separator)."""
    from modules.spectrum.wavefunction import field_tables

    field_tables.style = self.csv_style()
    item = menu.addAction(tr('Таблицы CSV…'))
    item.setToolTip(tr('Разделитель и десятичный знак таблиц — «Файл → Настройки…»'))
    item.triggered.connect(lambda: self.w.show_settings('tables'))
    return item


# -- Multiwfn: NCI and IRI ---------------------------------------------------------------------------------
def add_nci_menu(self, menu, found=True):
    sub = menu.addMenu(tr('Слабые взаимодействия'))
    wavefunction = bool(getattr(self.w.property_tool, 'has_wavefunction', lambda: False)()) and found
    atoms = (bool(self.w.coordinate_tool.table_molecule().atoms) if self.w.has('coordinate_tool') else bool(self.w.molecule.atoms)) and found
    for kind, title, tip, enabled in (
        ('nci', tr('NCI по волновой функции результата'),
         tr('Поверхность RDG = 0,5, цвет — sign(λ₂)ρ: синее — водородные связи, зелёное — ван-дер-ваальсовы, '
            'красное — отталкивание'), wavefunction),
        ('promolecular', tr('NCI по промолекулярной плотности (без расчёта)'),
         tr('Плотность — сумма плотностей свободных атомов: хватает геометрии на модели; грубее, но для '
            'межмолекулярных контактов годится'), atoms),
        ('iri', tr('IRI по волновой функции результата'),
         tr('Одна поверхность (IRI = 1,0) показывает и химические связи, и слабые взаимодействия'), wavefunction),
    ):
        item = sub.addAction(title)
        if not found:
            tip = tr(MULTIWFN_HINT_TEXT)
        elif not enabled:
            tip = tr('У результата нет файла с орбиталями (Molden, fchk или .gbw ORCA)')
        item.setToolTip(tip)
        item.setEnabled(enabled)
        item.triggered.connect(lambda checked=False, k=kind: self.multiwfn_nci(k))
    # IGMH — the molecules of the structure are the fragments
    try:
        from modules.spectrum.wavefunction import multiwfn_igmh

        molecules = len(multiwfn_igmh.fragments(self.w.coordinate_tool.table_molecule() if self.w.has('coordinate_tool')
                                                else self.w.molecule))
    except (AttributeError, TypeError, ValueError):
        molecules = 0
    item = sub.addAction(tr('IGMH между молекулами (по волновой функции)'))
    if not found:
        item.setToolTip(tr(MULTIWFN_HINT_TEXT))
    elif not wavefunction:
        item.setToolTip(tr('У результата нет файла с орбиталями (Molden, fchk или .gbw ORCA)'))
    elif molecules < 2:
        item.setToolTip(tr('Нужно хотя бы две молекулы: фрагменты IGMH — молекулы структуры'))
    else:
        item.setToolTip(tr('Поверхность δg_inter = 0,005 между молекулами, цвет — sign(λ₂)ρ; вклад пар атомов в '
                           'каждое взаимодействие'))
    item.setEnabled(bool(found and wavefunction and molecules >= 2))
    item.triggered.connect(lambda checked=False: self.multiwfn_igmh())
    sub.addSeparator()
    item = sub.addAction(tr('График RDG — sign(λ₂)ρ в Спектре'))  # a tab of Spectrum, not a window
    item.setEnabled(getattr(self.w, 'nci_result', None) is not None)
    item.triggered.connect(lambda: self.show_nci_plot(True))
    return sub


def multiwfn_nci(self, kind, path=None):
    """NCI ('nci', 'promolecular') or IRI ('iri') from Multiwfn onto the model, and the plot in Spectrum.
    path: the file of the orbitals (by default that of the result). True when shown."""
    from pathlib import Path
    from types import SimpleNamespace

    from modules.spectrum.wavefunction import multiwfn

    program = self.w.property_tool.multiwfn_program() if self.w.has('property_tool') else multiwfn.find()
    if program is None:
        return False
    molecule, wavefunction = None, None
    if kind == 'promolecular':
        molecule = self.w.coordinate_tool.table_molecule() if self.w.has('coordinate_tool') else self.w.molecule
    else:
        wavefunction = path or (self.w.result_molden_path() if self.w.has('result_molden_path') else None)
        if wavefunction is None:
            return False
    grid = self.nci_grid()
    cores = self.w.cores.value() if self.w.has('cores') else 1
    what = tr('Расчёт IRI…') if kind == 'iri' else tr('Расчёт NCI…')
    try:
        sign, field, text, number = self.wait_field(
            ('nci', kind, multiwfn._stamp(wavefunction) if wavefunction else xyz_key(molecule), grid), what,
            lambda step: multiwfn.run_nci(program, wavefunction, kind, grid, cores, step, molecule=molecule))
    except InterruptedError:  # «Отмена» — no message
        return False
    except (OSError, ValueError, MemoryError) as exc:
        self.w.error(exc)
        return False
    surface = 'iri' if kind == 'iri' else 'nci'
    title = tr(SURFACE_TITLES[surface]) + (tr(' · промолекулярная плотность') if kind == 'promolecular' else '')
    self.w.nci_result = {'sign': sign, 'field': field, 'kind': surface, 'title': title}
    table = None  # the dips of RDG (IRI) with sign(λ₂)ρ — a CSV next to the file of the orbitals
    if wavefunction is not None:
        table = (Path(wavefunction).parent, Path(wavefunction).name.split('.')[0])
    elif getattr(self.w, 'project_path', None):  # promolecular — next to the saved project
        project = Path(self.w.project_path)
        table = (project.parent, project.stem + '_promolecular')
    if not self.show_surface(field, surface, SimpleNamespace(molecule=field.molecule), title=title, color_cube=sign,
                             table=table):
        return False
    if wavefunction is not None:  # the output, in «Анализ» next to the file of the orbitals
        from modules.spectrum.wavefunction import field_tables

        field_tables.save_output(wavefunction, kind, text)
    self.show_nci_plot()
    return True


def multiwfn_igmh(self, path=None):
    """IGMH from Multiwfn between the molecules of the result (modules/spectrum/wavefunction/multiwfn_igmh.py):
    the surface δg_inter coloured by sign(λ₂)ρ on the model, its domains with the atom-pair δG indices, the plot and
    the tables in the tab «NCI» of Spectrum. True when shown."""
    from pathlib import Path
    from types import SimpleNamespace

    from modules.spectrum.wavefunction import multiwfn, multiwfn_igmh

    program = self.w.property_tool.multiwfn_program() if self.w.has('property_tool') else multiwfn.find()
    wavefunction = path or (self.w.result_molden_path() if self.w.has('result_molden_path') else None)
    if program is None or wavefunction is None:
        return False
    molecule = None
    try:  # the fragments in the order of the atoms of the wavefunction itself
        from modules.spectrum.readers.orbital_files import read_orbitals

        molecule = read_orbitals(Path(wavefunction).read_text(encoding='utf-8', errors='replace')).molecule
    except (OSError, ValueError, AttributeError, IndexError, KeyError):
        molecule = self.w.coordinate_tool.table_molecule() if self.w.has('coordinate_tool') else self.w.molecule
    grid = self.nci_grid()
    cores = self.w.cores.value() if self.w.has('cores') else 1
    try:
        found = self.wait_field(('igmh', multiwfn._stamp(wavefunction), grid), tr('Расчёт IGMH…'),
                                lambda step: multiwfn_igmh.run_igmh(program, wavefunction, molecule, grid, cores, step))
    except InterruptedError:
        return False
    except (OSError, ValueError, MemoryError) as exc:
        self.w.error(exc)
        return False
    title = tr(SURFACE_TITLES['igmh'])
    self.w.nci_result = {'sign': found['sign'], 'field': found['field'], 'kind': 'igmh', 'title': title,
                         'pairs': found['pairs'], 'atoms': found['atoms'], 'fragments': found['fragments']}
    table = (Path(wavefunction).parent, Path(wavefunction).name.split('.')[0])
    self.pending_pairs = found['pairs']  # read by show_surface → nci_domains before the table is written
    try:
        shown = self.show_surface(found['field'], 'igmh', SimpleNamespace(molecule=found['field'].molecule),
                                  title=title, color_cube=found['sign'], table=table)
    finally:
        self.pending_pairs = None
    if not shown:
        return False
    from modules.spectrum.wavefunction import field_tables

    field_tables.save_output(wavefunction, 'igmh', found['text'])
    self.show_nci_plot()
    return True


# -- the domains of NCI — every weak interaction named (modules/spectrum/analysis/nci_domains.py) ---------
def nci_topology(self, molecule):
    """(topology, charge) of the QTAIM of Spectrum when it belongs to this very structure, else (None, 0)."""
    panel = self.w.topology_panel if self.w.has('topology_panel') else None
    topology = getattr(panel, 'topology', None)
    orbital_set = getattr(panel, 'orbital_set', None)
    if topology is None or orbital_set is None:
        return None, 0
    try:
        theirs = orbital_set.molecule.atoms
        mine = molecule.atoms
        same = len(theirs) == len(mine) and all(
            a.symbol == b.symbol and np.allclose(a.position, b.position, atol=1e-3) for a, b in zip(theirs, mine))
    except (AttributeError, TypeError, ValueError):
        return None, 0
    if not same:
        return None, 0
    try:
        charge = round(sum(orbital_set.charges) - float(np.sum(orbital_set.occupied(False)[1])))
    except (AttributeError, TypeError, ValueError):
        charge = 0
    return topology, charge


def nci_domains(self, s):
    """The domains of the NCI (IRI) surface source s at its level (kept in s for that level); () without the grid of
    sign(λ₂)ρ or when they cannot be found."""
    if s is None or s.get('color_cube') is None or s['kind'] not in WEAK:
        return ()
    kept = s.get('domains')
    if kept is not None and kept[0] == s['level']:
        return kept[1]
    from modules.spectrum.analysis import nci_domains

    molecule = s['cube'].molecule
    topology, charge = self.nci_topology(molecule)
    try:
        found = nci_domains.find(s['color_cube'], s['cube'], s['level'], s['kind'], molecule, topology, charge)
        if s.get('igmh_pairs'):  # the atom-pair δG indices of IGMH, summed per domain
            found = nci_domains.attach(found, s['igmh_pairs'], molecule)
    except (ValueError, IndexError, MemoryError):
        found = ()
    s['domains'] = (s['level'], found)
    return found


def nci_markers(self, s):
    """[(xyz Å on the structure, colour, label, larger)] — the centres of the domains numbered as the rows of the
    table of the tab «NCI», coloured by the spike; the one chosen in the table larger."""
    domains = self.nci_domains(s)
    if not domains:
        return []
    colours = surfaces.nci_colors([d.peak for d in domains])
    chosen = s.get('chosen_domain')
    out = []
    for k, (d, rgb) in enumerate(zip(domains, colours)):
        place = (np.asarray(d.centre, float) - s['from']) @ s['rotation'] + s['to']
        colour = '#' + ''.join(f'{int(round(255 * float(c))):02x}' for c in rgb)
        out.append((place, colour, str(k + 1), chosen == k))
    return out


def choose_nci_domain(self, index):
    """A row of the table of the tab «NCI» chosen — its domain marked larger on the model."""
    s = self.w.surface_source
    if s is None or s['kind'] not in WEAK:
        return False
    s['chosen_domain'] = index
    if self.w.viewer.surface:
        self.w.viewer.surface['markers'] = self.nci_markers(s)
        self.w.viewer.update()
    return True


def refresh_nci_panel(self):
    """The plot and the table of the tab «NCI» again (a new level of the surface), without a notice."""
    if getattr(self.w, 'nci_result', None) is not None and getattr(self.w, 'nci_panel', None) is not None:
        self.show_nci_plot(quiet=True)


def show_nci_plot(self, navigate=False, quiet=False):
    """The plot RDG (IRI) — sign(λ₂)ρ is the tab «NCI» of Spectrum (it was a window over the model);
    navigate: open that tab. Returns the panel of the plot or None."""
    result = getattr(self.w, 'nci_result', None)
    panel = getattr(self.w, 'nci_panel', None)
    if result is None or panel is None:
        return None
    level = None
    domains = ()
    source = self.w.surface_source
    if source is not None and source.get('kind') == result['kind']:
        level = source.get('level')
        if source.get('cube') is result['field']:
            domains = self.nci_domains(source)
    symbols = [a.symbol for a in result['field'].molecule.atoms]
    panel.set_result(result['sign'], result['field'], result['kind'], result['title'], level, domains=domains,
                     symbols=symbols, choose=self.choose_nci_domain, pairs=result.get('pairs', ()),
                     atoms=result.get('atoms') or {}, fragments=result.get('fragments', ()))
    if self.w.has('result_tabs'):
        self.w.result_tabs.setTabVisible(self.w.nci_tab, True)
    if navigate:
        if self.w.has('navigate'):
            self.w.navigate(2)
        self.w.result_tabs.setCurrentWidget(panel)
    elif not quiet:
        self.w.notify(tr('График RDG — sign(λ₂)ρ: Спектр, вкладка «NCI».'), 8000)
    return panel
