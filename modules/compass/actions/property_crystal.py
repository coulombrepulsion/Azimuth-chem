"""The properties of a crystal from its last CP2K run: the charges (CM5, Hirshfeld) on the atoms, the density and
ELF, QTAIM. Methods of PropertyTool (self is the tool; the window only through its port self.w), kept here to make
property_actions.py shorter.

Split off modules/compass/actions/property_actions.py (0.222.30).
"""

from pathlib import Path
from azimuth.i18n import tr


def crystal_run(self):
    """The last CP2K run of the project of the crystal shown, or None."""
    from modules.compass.chemistry import crystal_results

    own = getattr(self.w.document(), 'research_project_path', '')
    if not own:
        return None
    try:
        return crystal_results.last(own, 'cp2k', having='*.molden')  # not a run of the frequencies
    except (OSError, ValueError, KeyError):
        return None


def fill_crystal_menu(self, menu, part):
    from modules.compass.chemistry import crystal_results

    menu.clear()
    menu.setToolTipsVisible(True)
    shown = getattr(self.w.document(), 'crystal_labels', None)
    if part == 'atoms':  # what the structure itself gives, with no calculation
        from modules.compass.chemistry import crystal_energetics

        crystal = getattr(self.w, 'crystal', None)
        try:  # what needs the ionic model, grey
            problem = crystal_energetics.ionic_problem(crystal[0]) if crystal else None
        except (ValueError, TypeError, IndexError):
            problem = None
        for key, title in self.STRUCTURE_LABELS.items():
            item = menu.addAction(tr(title) + tr(' на модели'))
            item.setCheckable(True)
            item.setChecked(bool(shown) and shown[1] == key)
            if problem and key in ('oxidation', 'bvs'):
                item.setEnabled(False)
                item.setToolTip(problem)
            item.triggered.connect(lambda on, k=key: self.show_crystal_charges(k if on else None))
        menu.addSeparator()
    run = self.crystal_run()
    if run is None:
        item = menu.addAction(tr('Нет расчёта CP2K этого кристалла — посчитайте его в Секстанте (CP2K).'))
        item.setEnabled(False)
        return menu
    head = menu.addAction(tr('Расчёт: {}').format(run.folder.name))
    head.setEnabled(False)
    if part == 'atoms':
        kept = crystal_results.read_charges(run.folder)
        for key, title in self.CRYSTAL_CHARGES.items():
            item = menu.addAction(tr(title) + tr(' на модели'))
            item.setCheckable(True)
            item.setChecked(bool(shown) and shown[1] == key)
            item.setEnabled(kept is not None)
            item.triggered.connect(lambda on, k=key: self.show_crystal_charges(k if on else None))
        menu.addSeparator()
        menu.addAction(tr('Посчитать заряды в Multiwfn…') if kept is None else tr('Посчитать заряды заново…'),
                       self.compute_crystal_charges)
        table = menu.addAction(tr('Таблица зарядов…'), self.crystal_charges_table)
        table.setEnabled(kept is not None)
    else:
        kept = crystal_results.read_aim(run.folder)
        menu.addAction(tr('Связи по AIM (Multiwfn)…') if kept is None else tr('Связи по AIM — таблица…'),
                       lambda: self.crystal_aim(compute=kept is None))
        if kept is not None:
            menu.addAction(tr('Посчитать связи заново…'), lambda: self.crystal_aim(compute=True))
        # critical points on the crystal model, as on a molecule
        from modules.compass.actions import crystal_dynamics

        points = menu.addAction(tr('Критические точки на модели'),
                                lambda: crystal_dynamics.show_points(self.w.widget))
        points.setEnabled(crystal_results.read_aim_points(run.folder) is not None)
    return menu


def show_crystal_charges(self, key):
    """key 'cm5' / 'hirshfeld' — the charges of the last CP2K run on the atoms of the crystal; None — taken away."""
    document = self.w.document()
    if key in self.STRUCTURE_LABELS:
        from modules.compass.chemistry import crystal_energetics

        shown = getattr(self.w, 'crystal', None)
        try:
            crystal_energetics.model_labels(shown[0], [], key)  # the ionic model applies (or why not)
        except (ValueError, TypeError, IndexError) as exc:
            self.w.error(exc)
            return None
        document.crystal_labels = (None, key)
        self._crystal_cache = None
        self.w.viewer.update()
        return document.crystal_labels
    run = self.crystal_run()
    document.crystal_labels = (str(run.folder), key) if (run is not None and key) else None
    self._crystal_cache = None
    self.w.viewer.update()
    return document.crystal_labels


def crystal_overlay(self, molecule):
    from modules.compass.chemistry import crystal_results

    choice = getattr(self.w.document(), 'crystal_labels', None)
    shown = getattr(self.w, 'crystal', None)
    if not choice or not shown or molecule is None or not molecule.atoms:
        return None
    folder, key = choice
    cache = getattr(self, '_crystal_cache', None)
    if cache is not None and cache[0] == (id(molecule), folder, key):
        return cache[1]
    result = None
    if folder is None:  # the labels of the structure
        from modules.compass.chemistry import crystal_energetics

        try:
            values = crystal_energetics.model_labels(shown[0], [(a.symbol, a.position) for a in molecule.atoms], key)
        except ValueError:
            values = []
        if any(v is not None for v in values):
            result = {'atom': (key, values), 'bonds': [], 'dipole': None, 'forces': None}
        self._crystal_cache = ((id(molecule), folder, key), result)
        return result
    kept = crystal_results.read_charges(folder)
    path = crystal_results.multiwfn_file(crystal_results.Run(Path(folder), 'cp2k'))
    if kept is not None and path is not None:
        values = crystal_results.model_charges(Path(path).read_text(encoding='utf-8', errors='replace'),
                                               kept[1][key], shown[0].cell.vectors(),
                                               [(a.symbol, a.position) for a in molecule.atoms])
        if any(v is not None for v in values):
            result = {'atom': (key, values), 'bonds': [], 'dipole': None, 'forces': None}
    self._crystal_cache = ((id(molecule), folder, key), result)
    return result


def compute_crystal_charges(self):
    from modules.compass.actions import crystal_analysis

    run = self.crystal_run()
    if run is None:
        return None
    try:
        crystal_analysis.compute_charges(self.w.widget, run, crystal_analysis.multiwfn_program(self.w.widget),
                                         self.w.cores.value() if self.w.has('cores') else 1)
    except InterruptedError:
        return None
    except (OSError, ValueError) as exc:
        self.w.error(exc)
        return None
    self.show_crystal_charges('cm5')
    self.w.notify(tr('Заряды CM5 на атомах кристалла; Хиршфельд и таблица — в «Атомы».'), 8000)
    return True


def crystal_field(self, what='density'):
    """The valence electron density ('density') or the ELF ('elf') of the last CP2K run of the project
    on the model of the crystal (crystal_field: from its Molden file, periodic) — an isosurface of «Поверхность на
    модели»; the grid of one cell kept in crystal-<what>.npz of the run."""
    from types import SimpleNamespace

    import numpy as np

    from azimuth.tasks import run_waiting
    from modules.compass.chemistry import crystal_field
    from modules.spectrum.readers import cp2k

    run = self.crystal_run()
    shown = getattr(self.w, 'crystal', None)
    if run is None or not shown:
        self.w.notify(tr('Нет расчёта CP2K этого кристалла — посчитайте его в Секстанте (CP2K).'), 7000)
        return None
    molden = cp2k.molden_files(run.folder)
    cell = cp2k.last_cell(run.folder)
    if not molden or cell is None:
        self.w.notify(tr('В папке расчёта нет волновой функции (файла Molden) — посчитайте кристалл заново.'), 7000)
        return None
    original = shown[0]
    file_cell = np.array(original.cell.vectors(), dtype=float)
    mapping = crystal_field.mapping_of(original, cell)
    if mapping is None:
        computed = len(cp2k._input_atoms(run.folder / 'azimuth.inp', cell)) if (run.folder / 'azimuth.inp').is_file() \
            else 0
        from modules.compass.chemistry import crystal as cr

        if computed != len(cr.unit_cell(original)):
            self.w.error(ValueError(tr('Ячейка расчёта не составлена из ячеек файла — плотность на модель не '
                                       'перенести.')))
            return None
        mapping = np.eye(3)  # the cell of the file itself, changed by the optimization
    kept = run.folder / f'crystal-{what}.npz'
    stamp = molden[-1].stat().st_mtime
    values = None
    try:
        data = np.load(kept)
        if float(data['stamp']) == stamp and np.allclose(data['file_cell'], file_cell):
            values = data['values']
    except (OSError, KeyError, ValueError):
        values = None
    if values is None:
        title = tr('Электронная плотность кристалла…') if what == 'density' else tr('ELF кристалла…')
        try:
            values = run_waiting(self.w.widget, title, lambda step: crystal_field.compute(
                molden[-1].read_text(encoding='utf-8', errors='replace'), cell, file_cell, mapping, what,
                progress=step))
        except InterruptedError:
            return None
        except (OSError, ValueError) as exc:
            self.w.error(exc)
            return None
        try:
            np.savez_compressed(kept, values=values, file_cell=file_cell, stamp=stamp)
        except OSError:
            pass
    name = tr('Валентная электронная плотность') if what == 'density' else tr('ELF (валентные электроны)')
    cube = crystal_field.model_cube(values, file_cell, self.w.molecule, name)
    shown_on_model = self.w.surface_tool.show_surface(cube, what, SimpleNamespace(molecule=self.w.molecule),
                                                     title=name)
    if shown_on_model:
        self.w.notify(tr('{} по волновой функции CP2K ({}); уровень — в «Поверхность на модели».').format(
            name, run.folder.name), 8000)
    return shown_on_model


def crystal_charges_table(self):
    from modules.compass.actions import crystal_analysis
    from modules.compass.chemistry import crystal_results

    run = self.crystal_run()
    kept = crystal_results.read_charges(run.folder) if run is not None else None
    if kept is None:
        return None
    self._crystal_window = crystal_analysis.charges_window(self.w.widget, run.folder.parent.parent.name, *kept)
    self._crystal_window.show()
    return self._crystal_window


def crystal_aim(self, compute=False):
    from modules.compass.actions import crystal_analysis
    from modules.compass.chemistry import crystal_results

    run = self.crystal_run()
    if run is None:
        return None
    kept = None if compute else crystal_results.read_aim(run.folder)
    if kept is None:
        try:
            kept = crystal_analysis.compute_aim(self.w.widget, run, crystal_analysis.multiwfn_program(self.w.widget),
                                                self.w.cores.value() if self.w.has('cores') else 1)
        except InterruptedError:
            return None
        except (OSError, ValueError) as exc:
            self.w.error(exc)
            return None
    self._crystal_window = crystal_analysis.aim_window(self.w.widget, run.folder.parent.parent.name, *kept)
    self._crystal_window.show()
    return self._crystal_window
