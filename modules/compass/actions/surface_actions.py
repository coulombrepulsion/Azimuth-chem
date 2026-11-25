"""Compass: an orbital, the electron or spin density, or the ESP on the density shown on the model.

§1 THEORY modules/compass/view/surfaces.py §1.
§2 ALGORITHM The orbital window of Spectrum («Показать: на модели Компаса») gives a field on a grid (a CUBE
               of orbitals.py) and the orbital set. The structure of the orbitals is put on the model: if
               the structure in Compass is the same (result_overlay.match: the same elements in the same
               order, RMSD < 0.01 Å after a proper rotation) it stays and the surface is turned onto it; else
               the structure of the file replaces it (asking about unsaved changes). The surfaces are built
               at the level chosen (orbital: ±level, densities: level). The ESP is only that of the
               wavefunction from Multiwfn ('esp-surface', below; the map of the Mulliken point charges is gone).
               «Вид → Поверхность на модели»:
               the level, the opacity, «Убрать поверхность». The surface is drawn only for the structure it
               was built for: an edit hides it, undoing the edit shows it again.
               −∇²ρ ('laplacian') and Δρ ('difference') as ± surfaces like an orbital; show_aim puts the
               critical points and bond paths of modules/spectrum/analysis/density.py on the model in the same frame.
               'nci' and 'iri' from Multiwfn (modules/spectrum/wavefunction/multiwfn.py): the surface of RDG (or IRI),
               coloured by sign(λ₂)ρ of a second grid (color_cube, surfaces.sample, surfaces.nci_colors); «Вид →
               Поверхность на модели → Слабые взаимодействия»: by the wavefunction of the result, by the
               promolecular density of the structure on the model (no calculation needed), IRI; the plot
               RDG — sign(λ₂)ρ (modules/compass/view/nci_plot.py).
               The menu — the pages of the drawer (orbitals, «Поверхности», QTAIM), then «Слабые
               взаимодействия», «Молекулярная поверхность», «Функции на сетке», one «Сетка расчёта» for every field
               (also «Сетка» of the drawer), «Таблицы CSV…» (opens «Файл → Настройки…» at the style of field_tables),
               «Программа Multiwfn…»; the items of Multiwfn are off with a hint when it is not found. The plot of NCI is
               the tab «NCI» of
               Spectrum (show_nci_plot). The domains of an NCI (IRI) surface (nci_domains: modules/spectrum/
               analysis/nci_domains.py, kept in the source for its level, with the QTAIM of Spectrum when it is of the
               same structure — nci_topology) — numbered marks at their centres on the model (nci_markers), the table
               and the numbered spikes of the tab «NCI», «<stem>_nci_domains.csv»; a row chosen marks its domain
               larger (choose_nci_domain); a new level refreshes the tab (refresh_nci_panel). «IGMH между
               молекулами» (multiwfn_igmh: modules/spectrum/wavefunction/multiwfn_igmh.py) — the kind 'igmh', the
               surface δg_inter = 0.005 coloured by sign(λ₂)ρ (WEAK: the kinds with sign(λ₂)ρ and domains), the
               domains with the atom-pair δG indices (source['igmh_pairs']), the plot and the table of the pairs in
               the tab «NCI». The critical points: show_aim / clear_aim keep the buttons «На модель /
               Убрать с модели» of every view of them in step (sync_aim_buttons). SURFACE_GROUPS, surface_choice(key,
               path), surface_choice_title(key) — the page «Поверхности» of the drawer.
§3 APPLICATIONS modules/spectrum/views/orbitals_view.py, modules/spectrum/views/density_view.py, the «Вид» menu
               of Compass.
§4 SPECIFICATION show_surface(cube, kind, orbital_set, level=None) -> bool, kind ∈ KINDS;
               set_surface_level(level); set_surface_opacity(value); clear_surface().
§5 PROCEDURES below.
§6 NOTES LEVELS: the usual isovalues — orbitals 0.02–0.1 (0.05 by default, as GaussView and Avogadro),
               densities 0.001–0.05 (0.002 for the ESP map, close to the van der Waals surface).
§7 TESTS tests/test_gui.py::test_orbital_and_esp_surfaces_in_compass.
§8' ROBUSTNESS a level with no surface: a message, the previous surface stays.
"""

from collections import OrderedDict
from dataclasses import replace

import numpy as np
from PySide6.QtGui import QActionGroup
from PySide6.QtWidgets import QMenu

from modules.compass.view import surfaces
from modules.compass.actions.property_multiwfn import MULTIWFN_HINT as MULTIWFN_HINT_TEXT
from azimuth.i18n import tr
from azimuth.ui import smooth
from modules.compass.actions import surface_aim as _aim
from modules.compass.actions import surface_nci as _nci
from modules.compass.actions.surface_nci import GRIDS, SURFACE_TITLES, WEAK, xyz_key  # noqa: F401 — GRIDS also named from here
from modules.compass.actions import surface_functions as _functions
from modules.compass.actions.surface_functions import FUNCTION_INFO, MAPPED_TITLES

KINDS = ('orbital', 'density', 'spin', 'laplacian', 'difference', 'nci', 'iri', 'esp-surface', 'elf', 'lol', 'excitation',
         'fukui', 'void', 'hirshfeld', 'igmh')  # no 'esp' of
# Mulliken point charges any more — the ESP is that of the wavefunction, from Multiwfn ('esp-surface')
LEVELS = {
    'orbital': (0.02, 0.03, 0.05, 0.08, 0.1),
    'density': (0.001, 0.002, 0.005, 0.01, 0.05),
    'spin': (0.001, 0.002, 0.005, 0.01, 0.02),
    'laplacian': (0.05, 0.1, 0.2, 0.5, 1.0, 2.0),  # ±(−∇²ρ), e/bohr⁵
    'difference': (0.001, 0.002, 0.005, 0.01, 0.02, 0.05),  # ±Δρ, e/bohr³
    'nci': (0.3, 0.4, 0.5, 0.6, 0.7),  # RDG (no unit); 0.5 as in the NCI paper and Multiwfn
    'iri': (0.8, 0.9, 1.0, 1.1, 1.2),  # IRI; 1.0 as Lu & Chen recommend
    'esp-surface': (0.001,),  # the surface of Multiwfn's analysis (Bader's ρ = 0.001 e/bohr³)
    'elf': (0.6, 0.7, 0.75, 0.8, 0.85, 0.9),  # ELF (no unit); 0.8 — the bonds and lone pairs apart
    'lol': (0.4, 0.45, 0.5, 0.55, 0.6, 0.7),  # LOL; 0.5
    'excitation': (0.0005, 0.001, 0.002, 0.005, 0.01),  # the hole and the electron, e/bohr³
    'fukui': (0.001, 0.002, 0.005, 0.01, 0.02, 0.05),  # ±f⁺, f⁻, f⁰, Δf, e/bohr³
    'void': (0.5,),  # the voids of a crystal (crystal_voids) — a field 0–1, the border at ½
    'hirshfeld': (0.5,),  # the weight of the molecule w — the Hirshfeld surface at ½ (crystal_hirshfeld)
    'igmh': (0.002, 0.003, 0.005, 0.008, 0.01),  # δg_inter of IGMH, a.u.; 0.005 as in Lu & Chen 2022
}
UNITS = {'orbital': '', 'laplacian': ' e/бор⁵', 'nci': '', 'iri': '', 'elf': '', 'lol': '', 'void': '', 'hirshfeld': '',
         'igmh': ' а. е.'}  # the rest: e/bohr³
DEFAULT = {'orbital': 0.05, 'density': 0.002, 'spin': 0.005, 'laplacian': 0.2, 'difference': 0.005,
           'nci': 0.5, 'iri': 1.0, 'esp-surface': 0.001, 'elf': 0.8, 'lol': 0.5, 'excitation': 0.002,
           'fukui': 0.005, 'void': 0.5, 'hirshfeld': 0.5, 'igmh': 0.005}
OPACITY = (0.35, 0.55, 0.8, 1.0)
HARTREE_EV = 27.211386245988
# the page «Поверхности» of the drawer of Compass — every surface of Multiwfn by its group; keys:
# ('function', name of multiwfn.FUNCTIONS), ('nci', 'nci' | 'iri'), ('surface', a key of MAPPED_TITLES)
SURFACE_GROUPS = (
    ('Плотность и её производные', (('function', 'rho'), ('function', 'gradient'), ('function', 'laplacian'),
                                    ('function', 'spin'), ('function', 'rdg'))),
    ('Локализация электронов', (('function', 'elf'), ('function', 'lol'), ('function', 'entropy'))),
    ('Энергия', (('function', 'g'), ('function', 'k'), ('function', 'alie'))),
    ('Потенциал', (('function', 'esp'),)),
    ('Слабые взаимодействия', (('nci', 'nci'), ('nci', 'iri'))),
    ('На молекулярной поверхности ρ = 0,001', (('surface', 'esp'), ('surface', 'alie'), ('surface', 'lea'),
                                               ('surface', 'leae'))),
)
SIGNED = {'orbital', 'spin', 'laplacian', 'difference', 'fukui'} | {'f-' + n for n, info in FUNCTION_INFO.items() if info[3]}
TABLE_MODES = {  # kind: (extrema, below, unit) of the table written with a surface
    'orbital': ('both', None, ''), 'density': ('max', None, 'e/бор³'), 'spin': ('both', None, 'e/бор³'),
    'laplacian': ('both', None, 'e/бор⁵'), 'difference': ('both', None, 'e/бор³'), 'elf': ('max', None, ''),
    'lol': ('max', None, ''), 'nci': ('min', 1.0, ''), 'iri': ('min', 1.0, ''), 'fukui': ('both', None, 'e/бор³'),
    'igmh': ('max', None, 'а. е.'),
}
for _name, _info in FUNCTION_INFO.items():
    _kind = 'f-' + _name
    KINDS += (_kind,)
    LEVELS[_kind], DEFAULT[_kind], UNITS[_kind], SURFACE_TITLES[_kind] = _info[1], _info[2], _info[4], _info[0]
    TABLE_MODES[_kind] = (_info[5], _info[6], _info[4].strip())


MESH_CACHE = 12  # the meshes of the last surfaces (each holds its grid alive, so its id stays its own)
_MESHES = OrderedDict()


def field_bytes(value, depth=0):
    """The bytes of the NumPy arrays of a cached field (a cube, a tuple of results, a dataclass), roughly."""
    if isinstance(value, np.ndarray):
        return value.nbytes
    if depth > 3 or value is None or isinstance(value, (str, bytes, int, float)):
        return 0
    if isinstance(value, (tuple, list)):
        return sum(field_bytes(v, depth + 1) for v in value)
    if isinstance(value, dict):
        return sum(field_bytes(v, depth + 1) for v in value.values())
    fields = getattr(value, '__dict__', None) or {}
    return sum(field_bytes(v, depth + 1) for v in fields.values())


class SurfaceTool:
    """Was the mixin SurfaceActions of the window; a part of its own — it reaches the window only through
    the names of PORT (azimuth/window_port.WindowPort)."""

    PORT = (
        'browsing',
        'confirm_replace',
        'coordinate_tool',
        'cores',
        'density_drawer',
        'density_tool',
        'document',
        'documents',
        'error',
        'esp_result',
        'load_molecule',
        'molecule',
        'navigate',
        'nci_panel',
        'nci_result',
        'nci_tab',
        'notify',
        'orbitals_dialog',
        'preferences',
        'project_path',
        'property_tool',
        'quiet_spinner',
        'result_molden_path',
        'result_orbitals',
        'result_tabs',
        'show_settings',
        'surface_menu',
        'surface_source',
        'topology_panel',
        'trajectory_tool',
        'viewer',
    )

    def __init__(self, window):
        from azimuth.window_port import WindowPort

        self.w = WindowPort(window, self.PORT)


    def build_surface_actions(self):
        self.w.surface_source = None
        self.w.surface_menu = smooth(QMenu(tr('Поверхность на модели'), self.w.widget))
        self.w.surface_menu.aboutToShow.connect(lambda: self.fill_surface_menu(self.w.surface_menu))
        from modules.spectrum.wavefunction import field_tables

        field_tables.style = self.csv_style()  # the style of the tables of the settings
        return self.w.surface_menu

    # -- what was built is kept; the drawer computes with a spinner, not a waiting window ------------------------
    FIELD_CACHE = 16  # the fields of Multiwfn kept in the session (cubes, the ESP of the surface)
    FIELD_BYTES = 768_000_000  # and their arrays together at most this

    def field_context(self):
        """What a field computed with the spinner belongs to — the document and its structure."""
        document = self.w.document() if self.w.has('document') and getattr(self.w, 'documents', None) else None
        molecule = self.w.coordinate_tool.table_molecule() if self.w.has('coordinate_tool') else None
        return id(document), xyz_key(molecule)

    def wait_field(self, key, title, work):
        """The result of work(step) for key: from the fields built in this session, else computed — with the waiting
        window, or (when quiet_spinner is set by the drawer of Compass) with the busy cursor and that spinner only.
        The spinner leaves the window usable — when the document or its structure changed
        meanwhile, the field is kept in the cache but not shown (InterruptedError, as after «Отмена»; a second press
        shows it at once)."""
        from collections import OrderedDict

        from azimuth.tasks import run_spinning, run_waiting

        cache = getattr(self, 'field_cache', None)
        if cache is None:
            cache = self.field_cache = OrderedDict()
        if key in cache:
            cache.move_to_end(key)
            return cache[key]
        spinner = getattr(self.w, 'quiet_spinner', None)
        before = self.field_context() if spinner is not None else None
        result = run_spinning(work, spinner, title) if spinner is not None else run_waiting(self.w.widget, title, work)
        cache[key] = result
        sizes = [field_bytes(v) for v in cache.values()]
        while len(cache) > 1 and (len(cache) > self.FIELD_CACHE or sum(sizes) > self.FIELD_BYTES):
            cache.popitem(last=False)
            sizes.pop(0)
        if before is not None and self.field_context() != before:
            if self.w.has('notify'):
                self.w.notify(tr('Пока считалась поверхность, документ сменился — она не показана. Нажмите ещё раз: '
                               'она уже посчитана.'), 8000)
            raise InterruptedError()
        return result

    def surface_changed(self):
        """The drawer of Compass lights the buttons of what is on the model."""
        drawer = getattr(self.w, 'density_drawer', None)
        if drawer is not None and hasattr(drawer, 'refresh_lights'):
            drawer.refresh_lights()

    def show_surface(self, cube, kind, orbital_set, level=None, title='', color_cube=None, esp=None, table=None,
                     table_name=None, mapped=None, go=True):
        """Put the surface of cube on the model (see §2); returns True when it is shown. orbital_set: anything with
        .molecule (the structure of the grid); color_cube: the grid of sign(λ₂)ρ for 'nci' and 'iri'; esp: for
        'esp-surface' the result of multiwfn.run_esp (the vertices with their ESP and the extrema); table:
        (folder, base name) for the table of the extrema (by default the file of the orbitals)."""
        if kind not in KINDS:
            raise ValueError(kind)
        frame = self.structure_frame(orbital_set.molecule, title)
        if frame is None:
            return False
        self.w.surface_source = dict(
            frame,
            cube=cube,
            kind=kind,
            orbitals=orbital_set,
            level=DEFAULT[kind] if level is None else float(level),
            opacity=0.55 if kind in ('orbital', 'laplacian', 'difference', 'fukui') else (
                0.8 if kind in ('nci', 'iri', 'igmh', 'esp-surface') else (1.0 if kind == 'hirshfeld' else 0.45)),
            title=title or tr(SURFACE_TITLES[kind]),
            color_cube=color_cube,
            esp=esp,
        )
        if mapped:  # the property of a Hirshfeld surface ('d_norm', 'd_i', 'd_e') — its colours
            self.w.surface_source['mapped'] = mapped
        if kind == 'igmh' and getattr(self, 'pending_pairs', None):  # the atom pairs of IGMH
            self.w.surface_source['igmh_pairs'] = self.pending_pairs
        if table_name:  # the name of the table of extrema («plus» with the base «fukui» → «fukui_plus_extrema.csv»)
            self.w.surface_source['table_name'] = table_name
        if not self.rebuild_surface():
            self.w.surface_source = None
            return False
        if table is None and self.w.has('property_tool'):
            path = self.w.property_tool.orbitals_file(orbital_set)
            table = (path.parent, path.name.split('.')[0]) if path is not None else None
        if table is not None:
            self.write_surface_table(self.w.surface_source, *table)
        if go and self.w.has('navigate'):  # go=False — a panel of Compass itself (Hirshfeld) stays put
            self.w.navigate(0)
        self.surface_changed()
        return True

    def write_surface_table(self, s, folder, base):
        """The extrema of the field of the surface (for the ESP on the molecular surface: its extrema and its
        summary) as CSV files in the folder of the calculation; the names are said in a notice."""
        from modules.spectrum.wavefunction import field_tables

        kind = s['kind']
        atoms = s['cube'].molecule.atoms
        symbols = [a.symbol for a in atoms]
        try:
            if kind == 'esp-surface':
                tables = field_tables.esp_tables(s['esp'], symbols, atoms)
            elif kind in TABLE_MODES:
                mode, below, unit = TABLE_MODES[kind]
                extrema = field_tables.grid_extrema(s['cube'], mode, below=below)
                extra = None
                if kind in WEAK and s.get('color_cube') is not None:
                    extra = ('sign(λ₂)ρ', list(surfaces.sample(s['color_cube'], [e['position'] for e in extrema]))
                             if extrema else [])
                name = s.get('table_name') or kind.replace('f-', '')
                if kind == 'orbital':  # one table per orbital — «orbital5», «orbital12_beta»
                    import re

                    number = re.search(r'(\d+)', s.get('title', ''))
                    name = 'orbital' + (number.group(1) if number else '') + ('_beta' if 'β' in s.get('title', '') else '')
                tables = {f'{name}_extrema': field_tables.extrema_table(extrema, symbols, unit, extra)}
                domains = self.nci_domains(s) if kind in WEAK else ()
                if domains:  # the weak interactions named, one row per domain
                    from modules.spectrum.analysis import nci_domains

                    tables[f'{name}_domains'] = nci_domains.table(domains, symbols)
            else:
                return []
            written = field_tables.write_tables(folder, base, tables)
        except (OSError, ValueError) as exc:
            self.w.notify(tr('Таблица не записана: ') + str(exc), 8000)
            return []
        self.w.notify(tr('Таблицы — в папке «Анализ» расчёта.'), 8000)
        return written

    def structure_frame(self, source_geometry, title=''):
        """{'rotation', 'from', 'to'} that put the structure of a result on the Compass structure: if it is the same
        (result_overlay.match) it stays, else the structure of the result replaces it (asking about unsaved
        changes; None if the user declines)."""
        from modules.compass.view import result_overlay
        from modules.spectrum.readers.orca_properties import Properties

        if getattr(self.w, 'browsing', False):
            self.w.trajectory_tool.set_trajectory_open(False)
        rotation = result_overlay.match(Properties(source_geometry), self.w.coordinate_tool.table_molecule())
        if rotation is None:
            if not self.w.confirm_replace():
                return None
            self.w.load_molecule(replace(source_geometry, title=source_geometry.title or title))
            rotation = result_overlay.match(Properties(source_geometry), self.w.coordinate_tool.table_molecule())
            if rotation is None:  # cannot happen: the same atoms, rounded to 1e-8 A by the table
                rotation = np.eye(3)
        return {
            'rotation': rotation,
            'from': np.mean([a.position for a in source_geometry.atoms], axis=0),
            'to': np.mean([a.position for a in self.w.molecule.atoms], axis=0),
        }

    show_aim = _aim.show_aim
    keep_contacts = _aim.keep_contacts
    follow_aim_kind = _aim.follow_aim_kind
    unmark_aim = _aim.unmark_aim
    clear_aim = _aim.clear_aim
    aim_panels = _aim.aim_panels
    sync_aim_buttons = _aim.sync_aim_buttons

    def rebuild_surface(self):
        s = self.w.surface_source
        if s is None:
            self.w.viewer.surface = None
            self.w.viewer.update()
            return False
        kind, level = s['kind'], s['level']
        try:
            meshes, limit = self.surface_meshes_for(s, surfaces.TARGET)
        except (ValueError, ImportError, MemoryError) as exc:
            self.w.error(exc)
            return False
        if not meshes:
            self.w.notify(tr(f'На уровне {level:g} поверхности нет — выберите уровень меньше.'), 8000)
            return False
        title = s['title'] + ''.join(' + ' + also[2] for also in s.get('also', ()))  # the orbitals added
        legend = title if kind == 'esp-surface' else title + f' · {level:g}'
        source = dict(s)
        self.w.viewer.surface = {
            'atoms': self.w.molecule.atoms,
            'meshes': meshes,
            'opacity': s['opacity'],
            'legend': legend,
            'limit': limit,
            'scale': 'nci' if kind in WEAK else ('range' if kind == 'esp-surface' and
                                                         s['esp'].get('mapped', 'esp') != 'esp' else None),
            'range': self.surface_range(s),  # (lowest, highest, unit) of a mapped function other than ESP
            'markers': (self.esp_markers(s) if kind == 'esp-surface' else  # the extrema of the ESP
                        self.nci_markers(s) if kind in WEAK else []),  # the domains of NCI
            # the same surface without decimation, built when VTK draws it (viewer.surface_meshes)
            'build': lambda target: self.surface_meshes_for(source, target)[0],
            'fine': None,
        }
        self.w.viewer.update()
        return True

    @staticmethod
    def surface_meshes_for(s, target):
        """(meshes moved onto the Compass structure, ESP limit or None) of the surface source s with at most
        about `target` triangles per mesh; the last MESH_CACHE results are kept (showing a surface again, or
        going back to a level, builds nothing)."""
        key = (id(s['cube']), id(s.get('color_cube')), id(s.get('esp')), s['kind'], float(s['level']), int(target),
               tuple(id(also[0]) for also in s.get('also', ())),
               np.asarray(s['rotation'], float).tobytes(), tuple(np.asarray(s['from'], float)),
               tuple(np.asarray(s['to'], float)))
        found = _MESHES.get(key)
        if found is not None and found[0] is s['cube']:
            _MESHES.move_to_end(key)
            return found[1]
        result = SurfaceTool._meshes(s, target)
        _MESHES[key] = (s['cube'], result)
        while len(_MESHES) > MESH_CACHE:
            _MESHES.popitem(last=False)
        return result

    @staticmethod
    def _meshes(s, target):
        kind, level, cube = s['kind'], s['level'], s['cube']
        if kind in SIGNED:  # ±: spin α blue, β red; −∇²ρ, Δρ: + blue, − red; the signed functions
            meshes = surfaces.orbital_meshes(cube, level, target)
            # the orbitals added by
            # Shift+click (s['also']: (cube, row, title)) at the same level, each with its own pair of colours
            for k, also in enumerate(s.get('also', ()), 1):
                pair = surfaces.ORBITAL_PAIRS[k % len(surfaces.ORBITAL_PAIRS)]
                meshes += surfaces.orbital_meshes(also[0], level, target, colors=pair)
        elif kind in WEAK:  # the RDG / IRI surface coloured by sign(λ₂)ρ (and δg_inter of IGMH)
            mesh = surfaces.isosurface(cube, level, target=target, color='#33c040')
            meshes = []
            if mesh is not None:
                values = surfaces.sample(s['color_cube'], mesh.vertices)
                meshes = [replace(mesh, values=values, colors=surfaces.nci_colors(values))]
        elif kind == 'excitation':  # the hole (blue) and the electron (green) at the same level
            meshes = [m for m in (surfaces.isosurface(cube, level, target=target, color='#2c64c8'),
                                  surfaces.isosurface(s['color_cube'], level, target=target, color='#2e9e5b'))
                      if m is not None]
        elif kind == 'hirshfeld':  # coloured by d_norm, d_i or d_e (a second grid, crystal_hirshfeld)
            mesh = surfaces.isosurface(cube, level, target=target, color='#8fa6bf')
            meshes = []
            if mesh is not None:
                values = surfaces.sample(s['color_cube'], mesh.vertices)
                meshes = [replace(mesh, values=values, colors=surfaces.hirshfeld_colors(values, s.get('mapped', 'd_norm')))]
        elif kind == 'void':  # the voids of a crystal — amber, as the yellow voids of Mercury
            mesh = surfaces.isosurface(cube, level, target=target, color='#e0a030')
            meshes = [mesh] if mesh is not None else []
        elif kind in ('elf', 'lol'):  # one colour, the Lewis picture
            mesh = surfaces.isosurface(cube, level, target=target, color='#3fa7a0' if kind == 'elf' else '#c08a3e')
            meshes = [mesh] if mesh is not None else []
        else:
            mesh = surfaces.isosurface(cube, level, target=target, color='#8fa6bf')
            meshes = [mesh] if mesh is not None else []
        limit = None
        if kind == 'esp-surface' and meshes:  # the ESP of Multiwfn at its vertices onto ours
            esp = s['esp']
            values = surfaces.nearest_values(meshes[0].vertices, esp['points'], esp['esp'])
            if esp.get('mapped', 'esp') == 'esp':
                colors, limit = surfaces.esp_colors(values, float(np.max(np.abs(esp['esp']))))
            else:  # ALIE, LEA, LEAE — from the lowest (blue) to the highest (red) over the surface
                low, high = float(np.min(esp['esp'])), float(np.max(esp['esp']))
                colors = surfaces.range_colors(values, low, high)
            meshes = [replace(meshes[0], values=values, colors=colors)]
        return [surfaces.moved(m, s['rotation'], s['from'], s['to']) for m in meshes], limit

    def set_surface_level(self, level):
        if self.w.surface_source is None:
            return False
        old = self.w.surface_source['level']
        self.w.surface_source['level'] = float(level)
        if not self.rebuild_surface():
            self.w.surface_source['level'] = old
            self.rebuild_surface()
            return False
        if self.w.surface_source['kind'] in WEAK:  # the domains of the new level in the tab «NCI»
            self.refresh_nci_panel()
        return True

    def set_surface_opacity(self, value):
        if self.w.surface_source is None:
            return
        self.w.surface_source['opacity'] = float(value)
        if self.w.viewer.surface:
            self.w.viewer.surface['opacity'] = float(value)
        self.w.viewer.update()

    def clear_surface(self):
        self.w.surface_source = None
        self.w.viewer.surface = None
        self.w.viewer.update()
        self.surface_changed()

    def fill_surface_menu(self, menu):
        """The drawer pages first (orbitals, surfaces, critical points), then the surfaces of Multiwfn by their
        groups, one grid for all of them, the style of the tables, the program; then the surface on the model."""
        menu.clear()
        source = self.w.surface_source
        aim = getattr(self.w.viewer, 'aim', None)
        # the orbitals of the result of this tab; also from an ORCA .gbw, and the density analysis
        orbitals = self.w.result_orbitals() if self.w.has('result_orbitals') else None
        if orbitals is not None:
            for title, tip, tab in (
                (tr('Орбитали и плотность…'), tr('Панель слева: орбитали, их состав, спиновая плотность'), 0),
                (tr('Поверхности…'), tr('Панель слева: лапласиан, ELF, LOL, NCI, ESP и другие'), 1),
                (tr('Критические точки (QTAIM)…'), tr('Панель слева: точки ρ на модели'), 2),
            ):
                item = menu.addAction(title)
                item.setToolTip(tip)
                item.triggered.connect(lambda checked=False, t=tab: self.w.density_tool.open_density_drawer(tab=t))
            menu.addSeparator()
        found = self.w.property_tool.multiwfn_found() if self.w.has('property_tool') else None
        wavefunction = bool(getattr(self.w.property_tool, 'has_wavefunction', lambda: False)()) and found is not None
        self.add_nci_menu(menu, found is not None)
        surface = menu.addMenu(tr('Молекулярная поверхность'))  # ESP, ALIE, LEA, LEAE on ρ = 0.001
        for mapped, (short, title) in MAPPED_TITLES.items():
            item = surface.addAction(tr(title))
            item.setEnabled(wavefunction)
            item.triggered.connect(lambda checked=False, m=mapped: self.multiwfn_esp(mapped=m))
        self.add_function_menu(menu, wavefunction)  # ELF, LOL and the other functions on a grid
        self.add_grid_menu(menu)  # one grid for every field
        self.add_table_menu(menu)
        item = menu.addAction(tr('Программа Multiwfn…'))
        item.setToolTip(tr('Выбрать файл программы Multiwfn') if found is not None
                        else tr('Multiwfn не найден: brew install multiwfn или Multiwfn.exe'))  # a short tooltip (<
                        # 60); the whole hint is the status tip
        item.setStatusTip(str(found) if found is not None else tr(MULTIWFN_HINT_TEXT))
        item.triggered.connect(lambda: self.w.property_tool.choose_multiwfn_program() if self.w.has('property_tool') else None)
        menu.addSeparator()
        if source is None:
            if orbitals is None:
                item = menu.addAction(tr('Нет орбиталей в результате'))
                item.setToolTip(tr('ORCA: .gbw рядом с выводом; или Molden, fchk — «Файл → Открыть…»'))
                item.setEnabled(False)
            if aim:
                menu.addSeparator()
                menu.addAction(tr('Убрать критические точки')).triggered.connect(self.clear_aim)
            return
        kind, level = source['kind'], source['level']
        head = menu.addAction(source['title'])
        head.setEnabled(False)
        menu.addSeparator()
        levels = menu.addMenu(tr('Уровень изоповерхности'))
        group = QActionGroup(levels)
        for value in LEVELS[kind]:
            item = levels.addAction(f'{value:g}' + tr(UNITS.get(kind, ' e/бор³')))
            item.setCheckable(True)
            item.setChecked(abs(value - level) < 1e-12)
            item.triggered.connect(lambda checked=False, v=value: self.set_surface_level(v))
            group.addAction(item)
        opacity = menu.addMenu(tr('Непрозрачность'))
        group = QActionGroup(opacity)
        for value in OPACITY:
            item = opacity.addAction(f'{int(value * 100)} %')
            item.setCheckable(True)
            item.setChecked(abs(value - source['opacity']) < 1e-9)
            item.triggered.connect(lambda checked=False, v=value: self.set_surface_opacity(v))
            group.addAction(item)
        menu.addSeparator()
        menu.addAction(tr('Убрать поверхность')).triggered.connect(self.clear_surface)
        if aim:
            menu.addAction(tr('Убрать критические точки')).triggered.connect(self.clear_aim)

    nci_grid = _nci.nci_grid
    set_nci_grid = _nci.set_nci_grid
    add_grid_menu = _nci.add_grid_menu
    csv_style = _nci.csv_style
    set_csv_style = _nci.set_csv_style
    add_table_menu = _nci.add_table_menu
    add_nci_menu = _nci.add_nci_menu
    multiwfn_nci = _nci.multiwfn_nci
    multiwfn_igmh = _nci.multiwfn_igmh
    nci_topology = _nci.nci_topology
    nci_domains = _nci.nci_domains
    nci_markers = _nci.nci_markers
    choose_nci_domain = _nci.choose_nci_domain
    refresh_nci_panel = _nci.refresh_nci_panel
    show_nci_plot = _nci.show_nci_plot

    # -- Multiwfn: the ESP on the molecular surface -------------------------------------------------------------
    @staticmethod
    def surface_range(s):
        esp = s.get('esp')
        if s['kind'] != 'esp-surface' or esp is None or esp.get('mapped', 'esp') == 'esp':
            return None
        return float(np.min(esp['esp'])) * HARTREE_EV, float(np.max(esp['esp'])) * HARTREE_EV, tr('эВ')

    @staticmethod
    def esp_markers(s):
        """[(xyz Å on the structure, colour, label)] of the extrema of the ESP: minima blue, maxima red; the global
        ones larger; at most 12 of each, the strongest."""
        esp = s['esp']
        out = []
        electron_volts = esp.get('mapped', 'esp') != 'esp'  # ALIE, LEA… in eV, the ESP in kcal/mol
        for name, colour, strongest in (('minima', '#2c64c8', min), ('maxima', '#d7302f', max)):
            units = esp.get(name + '_units') or [(0.0, 0.0)] * len(esp[name])
            pairs = sorted(zip(esp[name], units), key=lambda item: item[0][0], reverse=strongest is max)[:12]
            for (kcal, xyz, top), (_, ev) in pairs:
                place = (np.asarray(xyz, float) - s['from']) @ s['rotation'] + s['to']
                label = f'{ev:.2f}' if electron_volts else f'{kcal:+.1f}'.replace('-', '−')
                out.append((place, colour, label, top))
        return out

    multiwfn_esp = _functions.multiwfn_esp
    add_function_menu = _functions.add_function_menu

    # -- the page «Поверхности» of the drawer -------------------------------------------------------------------
    @staticmethod
    def surface_choice_title(key):
        group, name = key
        if group == 'function':
            if name == 'elf':
                return tr('ELF — функция локализации электронов')
            if name == 'lol':
                return tr('LOL — локатор локализованных орбиталей')
            return tr(FUNCTION_INFO[name][0])
        if group == 'nci':
            return tr('NCI — слабые взаимодействия (RDG)') if name == 'nci' else tr('IRI — связи и слабые взаимодействия')
        return tr(MAPPED_TITLES[name][1])

    surface_choice = _functions.surface_choice
    multiwfn_function = _functions.multiwfn_function
    show_excitation = _functions.show_excitation
