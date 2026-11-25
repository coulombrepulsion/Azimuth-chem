"""The results of a crystal calculation in QePanel: the bands, the densities of states, the phonons, QTAIM and the
charges of a CP2K run (their table windows), the summary, the optimized cell and its steps. Methods of QePanel (self
is the panel), kept here to make qe_window.py shorter.

Split off modules/compass/actions/qe_window.py (0.222.29).
"""

from datetime import datetime
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QVBoxLayout
from azimuth.i18n import tr
from azimuth.ui import action_button
from modules.compass.actions.qe_common import RY_EV, phonon_lines


def reference(self, r):
    """E0 of the plots: the highest occupied level (an insulator) or the Fermi level (a metal), eV."""
    return r.highest if r.highest is not None else r.fermi


def band_data(self):
    """(Bands, path dict, E0) of the finished job of the bands, or None."""
    import json

    from modules.spectrum.readers import qe

    if self.folder is None or not (self.folder / 'path.json').is_file() or self.result is None:
        return None
    found = qe.bands((self.folder / 'pw.out').read_text(encoding='utf-8', errors='replace'))
    path = json.loads((self.folder / 'path.json').read_text(encoding='utf-8'))
    if not found.energies or len(found.energies) != len(path['x']):
        return None
    return found, path, self.reference(self.result)


def dos_data(self):
    from modules.spectrum.readers import qe

    if self.folder is None or not (self.folder / 'azimuth.dos').is_file() or self.result is None:
        return None
    found = qe.read_dos((self.folder / 'azimuth.dos').read_text(encoding='utf-8', errors='replace'))
    e0 = self.reference(self.result)
    if e0 is None:
        e0 = found.fermi
    return (found, e0) if found.energies else None


def phonon_data(self):
    """(branches [[ν cm⁻¹] per q], path dict, (ν, g) of the phonon DOS or None) of a finished job of the phonon
    branches (the files of matdyn.x), or None."""
    import json

    from modules.sextant import qe_inputs
    from modules.spectrum.readers import qe

    if self.folder is None or not (self.folder / qe_inputs.FREQ_FILE).is_file() or not (
            self.folder / 'path.json').is_file():
        return None
    branches = qe.read_branches((self.folder / qe_inputs.FREQ_FILE).read_text(encoding='utf-8', errors='replace'))
    path = json.loads((self.folder / 'path.json').read_text(encoding='utf-8'))
    if not branches or len(branches) != len(path['x']):
        return None
    dos = None
    if (self.folder / qe_inputs.PHDOS_FILE).is_file():
        dos = qe.read_phdos((self.folder / qe_inputs.PHDOS_FILE).read_text(encoding='utf-8', errors='replace'))
    return branches, path, dos


def show_phonons(self, found):
    """The phonon branches along the path and, beside, the phonon density of states."""
    from modules.compass.actions import qe_plots

    branches, path, dos = found
    values = [v for row in branches for v in row]
    top = max(values) if values else 1.0
    plot = qe_plots.BandsPlot()
    plot.axis, plot.zero_line = 'ν, см⁻¹', False
    plot.span = (min(0.0, min(values, default=0.0)) - 0.03 * top, 1.08 * top)
    plot.x, plot.energies = path['x'], branches
    plot.ticks, plot.breaks = [tuple(t) for t in path['ticks']], path['breaks']
    rows = [(x, *row) for x, row in zip(plot.x, branches)]
    header = ['q, 1/A'] + [f'nu{n + 1}, cm-1' for n in range(len(branches[0]))]
    window = qe_plots.QePlotWindow(self, tr('Фононные ветви · ') + self.name, plot, rows, header, 'phonons.csv')
    window.note.setText(tr('Отрицательные частоты — мнимые: структура не в минимуме (или мала сетка q). У ионного '
                           'кристалла у Γ видно расщепление LO–TO.'))
    self.plot_window = window
    window.show()
    if dos is not None and dos[0]:
        density = qe_plots.DosPlot()
        density.axis, density.label = 'ν, см⁻¹', 'g(ν), состояний/см⁻¹'
        density.energies, density.dos = dos
        density.span = plot.span
        second = qe_plots.QePlotWindow(self, tr('Фононная плотность состояний · ') + self.name, density,
                                       list(zip(*dos)), ['nu, cm-1', 'g(nu)'], 'phonon_dos.csv')
        self.phdos_window = second
        second.show()
    return window


def show_plot(self):
    """The bands or the density of states of the finished job (qe_plots.QePlotWindow)."""
    from modules.compass.actions import qe_plots

    phonons = self.phonon_data()
    if phonons is not None:
        return self.show_phonons(phonons)
    bands = self.band_data()
    if bands is not None:
        found, path, e0 = bands
        plot = qe_plots.BandsPlot()
        plot.x = path['x']
        plot.energies = [[e - (e0 or 0.0) for e in row] for row in found.energies]
        plot.ticks, plot.breaks = [tuple(t) for t in path['ticks']], path['breaks']
        rows = [(x, *row) for x, row in zip(plot.x, plot.energies)]
        header = ['k, 1/A'] + [f'E{n + 1} - E0, eV' for n in range(len(found.energies[0]))]
        window = qe_plots.QePlotWindow(self, tr('Зонная структура · ') + self.name, plot, rows, header, 'bands.csv')
        if path.get('general'):
            window.note.setText(tr('Для этой решётки путь общий: Γ–X, Γ–Y, Γ–Z вдоль осей обратной ячейки файла.'))
    else:
        dos = self.dos_data()
        if dos is None:
            return None
        found, e0 = dos
        plot = qe_plots.DosPlot()
        plot.energies = [e - (e0 or 0.0) for e in found.energies]
        plot.dos = found.dos
        rows = list(zip(plot.energies, found.dos, found.integrated))
        window = qe_plots.QePlotWindow(self, tr('Плотность состояний · ') + self.name, plot, rows,
                                       ['E - E0, eV', 'DOS, 1/eV', 'integrated'], 'dos.csv')
    window.note.setText((window.note.text() + ' ' if window.note.text() else '') +
                        tr('E₀ — верх валентной зоны (у металла — уровень Ферми) по расчёту scf.'))
    self.plot_window = window
    window.show()
    return window


def multiwfn_line(self):
    """The wave function of the end of a CP2K run made ready for Multiwfn (cp2k.for_multiwfn) — a line of
    the summary: the file, or why there is none."""
    from modules.spectrum.readers import cp2k

    try:
        path, why = cp2k.for_multiwfn(self.folder)
    except (OSError, ValueError) as exc:
        path, why = None, str(exc)
    self.multiwfn_file = path
    self.aim_button.setVisible(path is not None)
    self.charges_button.setVisible(path is not None)
    if path is not None:
        return '<br>' + tr('Волновая функция для Multiwfn: {}').format(path.name)
    return '<br>' + tr('Волновая функция для Multiwfn не подготовлена: {}').format(why) if why else ''


def multiwfn_found(self):
    """Multiwfn of the settings of the program (as for a molecule), or found where it is usually installed."""
    from modules.compass.actions import crystal_analysis

    return crystal_analysis.multiwfn_program(self.owner)


def show_aim(self):
    """the bonds by QTAIM of the CP2K run (crystal_analysis.compute_aim) — a table in its own window, aim-bonds.csv
    in the folder of the run. None when nothing was done."""
    from modules.compass.actions import crystal_analysis
    from modules.compass.chemistry.crystal_results import Run

    if getattr(self, 'multiwfn_file', None) is None or self.folder is None:
        return None
    try:
        rows, meta = crystal_analysis.compute_aim(self, Run(self.folder, 'cp2k'), self.multiwfn_found(),
                                                  self.processes.value(), self.multiwfn_file)
    except InterruptedError:
        return None
    except (OSError, ValueError) as exc:
        self.status.setText(str(exc))
        return None
    self.aim_window = crystal_analysis.aim_window(self, self.name, rows, meta)
    self.aim_window.show()
    return self.aim_window


def show_charges(self):
    """The charges of Hirshfeld and CM5 of the atoms (crystal_analysis.compute_charges) — per element in
    a window, per atom in charges.csv. None when nothing was done."""
    from modules.compass.actions import crystal_analysis
    from modules.compass.chemistry.crystal_results import Run

    if getattr(self, 'multiwfn_file', None) is None or self.folder is None:
        return None
    try:
        symbols, charges, version = crystal_analysis.compute_charges(
            self, Run(self.folder, 'cp2k'), self.multiwfn_found(), self.processes.value(), self.multiwfn_file)
    except InterruptedError:
        return None
    except (OSError, ValueError) as exc:
        self.status.setText(str(exc))
        return None
    self.charges_window = crystal_analysis.charges_window(self, self.name, symbols, charges, version)
    self.charges_window.show()
    return self.charges_window


def _record(self, r):
    """A run in the folder of a crystal project is written into the project (crystal_projects.runs)."""
    from azimuth import crystal_projects

    manifest = self.folder.parent.parent / 'project.qcc' if self.folder is not None else None
    if manifest is None or self.folder.parent.name != 'calculations' or not crystal_projects.is_crystal(manifest):
        return False
    try:
        crystal_projects.record_run(manifest, {
            'folder': f'calculations/{self.folder.name}', 'task': self.task.currentData(),
            'time': datetime.now().isoformat(timespec='seconds'), 'energy_ry': r.energy,
            'energy_eh': getattr(r, 'energy_hartree', None),
            'place': self.where.currentData(), 'program': self.program}, getattr(self, 'crystal_ident', None))
    except (OSError, ValueError) as exc:  # a project open for writing elsewhere: the run stays in its folder
        self.status.setText(self.status.text() + ' · ' + str(exc))
        return False
    return True


def summary_text(self, r):
    n = r.nat or 1
    lines = [tr('Полная энергия ячейки: {} Ry = {} Eh = {} эВ ({} эВ на атом)').format(
        f'{r.energy:.6f}', f'{r.energy_hartree:.6f}', f'{r.energy * RY_EV:.4f}', f'{r.energy * RY_EV / n:.4f}')]
    if r.pressures:
        lines.append(tr('Давление: {} кбар').format(f'{r.pressures[-1]:.2f}'))
    if r.highest is not None and r.lowest is not None:
        lines.append(tr('Щель (по сетке k): {} эВ').format(f'{r.lowest - r.highest:.3f}'))
    elif r.fermi is not None:
        lines.append(tr('Уровень Ферми: {} эВ').format(f'{r.fermi:.4f}'))
    if r.steps:
        lines.append(tr('Шагов оптимизации: {}{}').format(r.steps, '' if r.converged else tr(' (не сошлась)')))
    if r.cell is not None and r.atoms:
        import numpy as np

        lengths = [float(np.linalg.norm(v)) for v in r.cell]
        lines.append(tr('Оптимизированная ячейка: a = {}, b = {}, c = {} Å').format(*(f'{x:.4f}' for x in lengths)))
        file_cell = self.file_cell_of(r.cell)
        if file_cell is not None:  # the primitive cell (Si: 3.87 Å) differs from the CIF cell (5.47 Å)
            lines.append(tr('В ячейке файла (как в CIF): a = {}, b = {}, c = {} Å').format(
                *(f'{x:.4f}' for x in file_cell)))
    if self.program != 'cp2k' and getattr(self, 'folder', None) is not None:
        from modules.spectrum.readers import qe

        found = qe.phonons(self.folder)
        if found is not None:
            lines += phonon_lines(found)
    return '<br>'.join(lines)


def file_cell_of(self, cell):
    """The edges a, b, c (Å) of the cell of the file that the optimized cell computed (primitive and/or a
    supercell, computed()) stands for — the rows of the file cell are B⁻¹ · R; None when the cell of the file was
    computed itself."""
    import numpy as np

    try:
        _crystal, basis = self.computed()
    except (ValueError, AttributeError, TypeError):
        return None
    if basis is None:
        return None
    try:
        rows = np.linalg.inv(np.array(basis, dtype=float)) @ np.array(cell, dtype=float)
    except (np.linalg.LinAlgError, ValueError):
        return None
    return [float(np.linalg.norm(v)) for v in rows]


def open_relaxed(self):
    """The steps of the optimization in the tab
    of this crystal in «Компас · Кристалл» (as the steps of a molecule: the last one shown, the start as a ghost,
    RMSD and the change of the cell) — no CIF of its own, no new project; «Взять эту геометрию» there gives the cell
    of the file in its group when the optimization kept it (crystal_steps.back_to_the_file). Without steps (an
    output of one geometry) the end itself is taken so."""
    from modules.compass.chemistry import crystal_steps

    steps = self.optimization_steps()
    if not steps and self.result is not None and self.result.cell is not None and self.result.atoms:
        steps = crystal_steps.make_steps([(self.result.energy_hartree, self.result.cell, self.result.atoms)],
                                         self.crystal.title or self.name, *self.computed_as())
    if not steps or not hasattr(self.owner, 'trajectory_tool'):
        return False
    program = 'CP2K' if self.program == 'cp2k' else 'Quantum ESPRESSO'
    if getattr(self.owner, 'compass_mode', 'crystal') != 'crystal' and hasattr(self.owner, 'crystal_tool'):
        self.owner.crystal_tool.set_compass_mode('crystal')
    self.owner.trajectory_tool.load_crystal_steps(steps, tr('оптимизация {} · {}').format(program, self.name),
                                                  self.folder)
    return True


def computed_as(self):
    """(the crystal of the file, the supercell computed, whether the primitive cell was) — for crystal_steps."""
    primitive = self.primitive.isChecked() and self.primitive_crystal is not self.crystal
    return self.crystal, tuple(b.value() for b in self.supercell), primitive


def optimization_steps(self):
    """The steps of the optimization just done (crystal_steps.CrystalStep, the start first), when the
    output or its files cannot be read."""
    from modules.compass.chemistry import crystal_steps
    from modules.spectrum.readers import cp2k, qe

    if self.job is None and self.folder is not None:  # a run of the project shown again — its supercell
        try:                                           # read back from its first step (crystal_steps.run_steps)
            return crystal_steps.run_steps(self.folder, self.program, self.crystal, self.crystal.title or self.name)
        except (OSError, ValueError, IndexError):
            return ()
    try:
        if self.program == 'cp2k':
            raw = cp2k.steps(self.folder) if self.folder is not None else []
        else:
            text = self.job.text() if self.job is not None else ''
            raw = qe.steps((qe.runs(text) or [text])[0])
        return crystal_steps.make_steps(raw, self.crystal.title or self.name, *self.computed_as())
    except (OSError, ValueError, IndexError):
        return ()


class TableWindow(QDialog):
    """A table of a result of Multiwfn for a crystal and what its columns mean (the bonds by AIM, the
    charges)."""

    def __init__(self, parent, title, heads, rows, lines):
        from PySide6.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem

        super().__init__(parent)
        self.setWindowTitle(title)
        layout = QVBoxLayout(self)
        self.table = QTableWidget(len(rows), len(heads))
        self.table.setHorizontalHeaderLabels(heads)
        for r, row in enumerate(rows):
            for c, value in enumerate(row):
                self.table.setItem(r, c, QTableWidgetItem(value))
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table, 1)
        self.note = QLabel('<br>'.join(lines))
        self.note.setWordWrap(True)
        layout.addWidget(self.note)
        bottom = QHBoxLayout()
        bottom.addStretch(1)
        bottom.addWidget(action_button(tr('Закрыть'), self.accept, 'close'))
        layout.addLayout(bottom)
        self.resize(900, 420)


class AimWindow(TableWindow):
    """The kinds of bonds of a crystal by QTAIM (crystal_aim)."""

    def __init__(self, parent, name, rows, census, atoms, version=None):
        from modules.spectrum.wavefunction import crystal_aim

        heads = [tr('Связь'), tr('Длина, Å'), tr('Связей у атома'), 'ρ, a.u.', '∇²ρ, a.u.', 'H, a.u.', '|V|/G',
                 tr('Тип взаимодействия')]
        shown = [row[:-1] + (tr(crystal_aim.NATURE[row[-1]]),) for row in rows]
        lines = [tr('Критические точки (3,−1) электронной плотности, найденные Multiwfn в ячейке расчёта ({} атомов); '
                    'одинаковые связи (те же элементы и длина) собраны в строку.').format(atoms),
                 tr('∇²ρ > 0 и H > 0 (|V|/G < 1) — замкнутые оболочки: ионная связь или слабый контакт; ∇²ρ > 0 и H < 0 — '
                    'промежуточная; ∇²ρ < 0 — обобществлённая (ковалентная). Bader, 1990; Cremer, Kraka, 1984; '
                    'Espinosa и др., 2002.')]
        if census['poincare_hopf'] != 0:
            lines.append(tr('Найдены не все критические точки (ядра − связи + кольца − клетки = {}, а должно быть 0): '
                            '«связей у атома» может быть меньше настоящего.').format(census['poincare_hopf']))
        lines.append(tr('Multiwfn {} — T. Lu, F. Chen, J. Comput. Chem. 33, 580 (2012). Таблица — aim-bonds.csv в папке '
                        'расчёта.').format(version or ''))
        super().__init__(parent, tr('Связи по AIM · ') + name, heads, shown, lines)


class ChargesWindow(TableWindow):
    """The charges of Hirshfeld and CM5 of the atoms of a crystal, per element (crystal_aim.charge_rows)."""

    def __init__(self, parent, name, rows, version=None):
        heads = [tr('Элемент'), tr('Атомов в ячейке'), tr('Хиршфельд'), 'CM5', tr('Разброс CM5')]
        lines = [tr('Заряды атомов по разбиению Хиршфельда (на свободные атомы) и CM5 (Хиршфельд с поправкой, '
                    'воспроизводящей дипольные моменты; Marenich и др., 2012) — среднее по атомам элемента в ячейке '
                    'расчёта. Атомы, одинаковые по симметрии, имеют одинаковый заряд; заметный разброс — атомы разные '
                    'или сетка груба.'),
                 tr('Для кристалла Multiwfn не считает ADCH; интегрирование — на равномерной сетке ячейки (шаг 0,4 бохр).'),
                 tr('Multiwfn {} — T. Lu, F. Chen, J. Comput. Chem. 33, 580 (2012). По атомам — charges.csv в папке '
                    'расчёта.').format(version or '')]
        super().__init__(parent, tr('Заряды атомов · ') + name, heads, rows, lines)
