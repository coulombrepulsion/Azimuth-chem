"""The properties computed from a queue of calculations: CDA of a complex and its fragments, the Fukui functions
(N, N+1, N−1) and their surfaces. Methods of PropertyTool (self is the tool; the window only through its port self.w),
kept here to make property_actions.py shorter.

Split off modules/compass/actions/property_actions.py (0.222.30).
"""

from azimuth.i18n import tr


def cda_folder(self):
    """The folder of the queue «CDA» the shown result belongs to (its complex), or None."""
    return self._queue_folder('cda')


def show_cda(self, folder):
    """CDA of the queue in folder — Multiwfn 16 on the Molden files of the complex and its two fragments;
    the table and the output in «Анализ» of the queue, the window."""
    from azimuth.tasks import run_waiting
    from modules.sextant import batch as batches
    from modules.spectrum.wavefunction import field_tables, multiwfn_cda
    from modules.spectrum.views.cda_view import CdaDialog

    if folder is None:
        return None
    try:
        queue = batches.Batch.load(folder)
        if queue.purpose != 'cda' or len(queue.items) != 3 or any(i.state != 'done' for i in queue.items):
            raise ValueError(tr('CDA: не все три расчёта очереди закончились.'))
        paths = [_wavefunction_of(item) for item in queue.items]
    except (OSError, ValueError, KeyError) as exc:
        self.w.error(exc)
        return None
    program = self.multiwfn_program()
    if program is None:
        return None
    cores = self.w.cores.value() if self.w.has('cores') else 1
    try:
        result, text = run_waiting(self.w.widget, tr('CDA: Multiwfn разлагает заряд по орбиталям фрагментов…'),
                                   lambda step: multiwfn_cda.run_cda(program, paths[0], paths[1:], cores, step))
    except InterruptedError:
        return None
    except (OSError, ValueError) as exc:
        self.w.error(exc)
        return None
    field_tables.save_output(paths[0], 'cda', text)
    written = []
    try:
        written = field_tables.write_tables(folder, 'cda', {'orbitals': multiwfn_cda.table(result)})
    except OSError as exc:
        self.w.notify(tr('Таблица CDA не записана: ') + str(exc), 10000)
    formulas = (queue.items[1].molecule.formula, queue.items[2].molecule.formula)
    self.cda_dialog = CdaDialog(self.w.widget, result, formulas, written, orbital=self.cda_orbital)
    self.cda_dialog.show()
    return self.cda_dialog


def cda_orbital(self, number):
    """The complex orbital number (of the table of CDA) on the model — the page «Орбитали» of the panel."""
    drawer = self.w.density_tool.open_density_drawer(tab=0) if self.w.has('density_tool') else None
    if drawer is None or getattr(drawer, 'orbitals_table', None) is None:
        return False
    orbitals = drawer.table_set.orbitals
    row = next((k for k, o in enumerate(orbitals) if o.number == number and o.spin == 'alpha'), number - 1)
    if not 0 <= row < len(orbitals):
        return False
    drawer.orbitals_table.selectRow(row)
    return drawer.show_orbital()


def _queue_folder(self, purpose):
    """The folder of the queue of purpose whose first calculation is the shown result, or None."""
    from pathlib import Path

    from modules.sextant import batch as batches

    path = getattr(self.w, 'output_path', None)
    if not path:
        return None
    folder = Path(path).parent.parent
    try:
        queue = batches.Batch.load(folder)
    except (OSError, ValueError, KeyError):
        return None
    if queue.purpose != purpose or not queue.items or Path(queue.items[0].output).resolve() != Path(path).resolve():
        return None
    return folder


def fukui_folder(self):
    """The folder of the queue «Функции Фукуи» the shown result belongs to (its calculation N), or None."""
    from pathlib import Path

    from modules.sextant import batch as batches

    path = getattr(self.w, 'output_path', None)
    if not path:
        return None
    folder = Path(path).parent.parent
    try:
        queue = batches.Batch.load(folder)
    except (OSError, ValueError, KeyError):
        return None
    if queue.purpose != 'fukui' or not queue.items or Path(queue.items[0].output).resolve() != Path(path).resolve():
        return None
    return folder


def show_fukui(self, folder):
    """The Fukui functions of the queue in folder: the Hirshfeld charges of its three wavefunctions
    (Multiwfn), f⁺, f⁻, f⁰, Δf onto the model of the result N (shown), the table in «Анализ», the window."""
    from dataclasses import replace
    from pathlib import Path

    from azimuth.tasks import run_waiting
    from modules.sextant import batch as batches
    from modules.spectrum.wavefunction import field_tables
    from modules.spectrum.analysis import fukui
    from modules.spectrum.views.fukui_view import FukuiDialog

    if folder is None:
        return None
    try:
        queue = batches.Batch.load(folder)
        if queue.purpose != 'fukui' or len(queue.items) != 3 or any(i.state != 'done' for i in queue.items):
            raise ValueError(tr('Функции Фукуи: не все три расчёта очереди закончились.'))
        wavefunctions = {key: _wavefunction_of(item) for key, item in zip(fukui.STATES, queue.items)}
    except (OSError, ValueError, KeyError) as exc:
        self.w.error(exc)
        return None
    program = self.multiwfn_program()
    if program is None:
        return None
    cores = self.w.cores.value() if self.w.has('cores') else 1
    try:
        charges, texts = run_waiting(self.w.widget, tr('Функции Фукуи: заряды Хиршфельда трёх расчётов…'),
                                     lambda step: fukui.run(program, wavefunctions, cores, step), total=3)
        values = fukui.condensed(charges['n'], charges['anion'], charges['cation'])
        props = self._population_target(wavefunctions['n'])
        if len(values['plus']) != len(props.geometry.atoms):
            raise ValueError(tr('Другое число атомов, чем у результата — функции Фукуи не взяты.'))
    except InterruptedError:
        return None
    except (OSError, ValueError) as exc:
        self.w.error(exc)
        return None
    energies = [item.energy for item in queue.items]
    indices = fukui.global_indices(*energies)
    symbols = [a.symbol for a in props.geometry.atoms]
    for key, text in texts.items():
        field_tables.save_output(wavefunctions[key], 'hirshfeld', text)
    written = []
    try:
        header, rows = fukui.table(symbols, charges, values)
        tables = {'atoms': (header, rows)}
        if indices:
            tables['global'] = ([tr('Индекс'), tr('эВ')], [
                [name, f'{indices[key]:.4f}' if indices.get(key) is not None else '']
                for key, name in (('ip', tr('Потенциал ионизации IP')), ('ea', tr('Сродство к электрону EA')),
                                  ('chi', tr('Электроотрицательность χ')), ('eta', tr('Жёсткость η')),
                                  ('omega', tr('Электрофильность ω')))])
        written = field_tables.write_tables(folder, 'fukui', tables)
    except OSError as exc:
        self.w.notify(tr('Таблица функций Фукуи не записана: ') + str(exc), 10000)
    new = replace(props, charges={**props.charges, 'hirshfeld': tuple(charges['n']), 'fukui+': values['plus'],
                                  'fukui-': values['minus'], 'fukui0': values['zero'], 'dual': values['dual']})
    self.w.overlay_choice['atom'] = 'fukui-plus'
    self.set_result_properties(new, self.w.result_source or Path(wavefunctions['n']).name)
    self.fukui_dialog = FukuiDialog(self.w.widget, symbols, charges, values, indices, written,
                                    surface=lambda key: self.fukui_surface(key, folder))
    self.fukui_dialog.show()
    return self.fukui_dialog


def fukui_surface(self, which, folder=None):
    """F⁺, f⁻, f⁰ or Δf (which ∈ FUKUI_TITLES) of the queue «Функции Фукуи» in folder as a ± surface on the
    model: the densities of its three wavefunctions on one grid (density.fukui_cubes, our own calculation, no
    Multiwfn); the four fields are kept per folder and grid, so another one is shown at once. True when shown."""
    from pathlib import Path

    from azimuth.tasks import run_waiting
    from modules.sextant import batch as batches
    from modules.spectrum.analysis import density
    from modules.spectrum.readers.orbital_files import read_orbitals

    folder = folder if folder is not None else self.fukui_folder()
    if folder is None or which not in self.FUKUI_TITLES:
        return False
    step = self.FUKUI_STEPS.get(self.w.surface_tool.nci_grid() if self.w.has('surface_tool') else 'medium', 0.15)
    key = (str(Path(folder).resolve()), step)
    kept = getattr(self.w, '_fukui_fields', None)
    if kept is None or kept[0] != key:
        try:
            queue = batches.Batch.load(folder)
            if queue.purpose != 'fukui' or len(queue.items) != 3 or any(i.state != 'done' for i in queue.items):
                raise ValueError(tr('Функции Фукуи: не все три расчёта очереди закончились.'))
            sets = []
            for item in queue.items:
                path = _wavefunction_of(item)
                sets.append(read_orbitals(Path(path).read_text(encoding='utf-8-sig', errors='replace')))
            cubes, integrals = run_waiting(
                self.w.widget, tr('Функции Фукуи: плотности трёх расчётов…'),
                lambda progress: density.fukui_cubes(*sets, step=step, progress=progress))
        except InterruptedError:
            return False
        except (OSError, ValueError, MemoryError) as exc:
            self.w.error(exc)
            return False
        self.w._fukui_fields = kept = (key, sets[0], cubes, integrals)
    _, n_set, cubes, integrals = kept
    title = tr(self.FUKUI_TITLES[which])
    shown = self.w.surface_tool.show_surface(cubes[which], 'fukui', n_set, title=title,
                              table=(Path(folder), 'fukui'), table_name=which)
    if shown:
        expected = 0 if which == 'dual' else 1
        self.w.notify(title + tr(f' · ∫ dV = {integrals[which]:+.3f} e (ожидается {expected}; разница — от шага '
                               'сетки, точнее — «Сетка расчёта» в «Файл → Настройки…»)'), 12000)
    return bool(shown)


def _wavefunction_of(item):
    """The Molden file of a calculation of a queue (orca_2mkl wrote <name>.molden.input next to its output)."""
    from pathlib import Path

    output = Path(item.output)
    found = output.with_name(output.stem + '.molden.input')
    if found.is_file():
        return found
    others = sorted(output.parent.glob('*.molden.input'))
    if others:
        return others[0]
    raise ValueError(tr(f'Нет файла орбиталей расчёта «{item.name}» (.molden.input рядом с выводом).'))
