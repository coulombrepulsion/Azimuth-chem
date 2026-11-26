"""«Расчёт в Quantum ESPRESSO» of a crystal of Compass.

§1 PURPOSE
    The plan the energy, the relaxation of the atoms and of the cell of a crystal by pw.x.
    A window of its own over the crystal of the tab: the task, the spacing of the k-points, the processes, the input
    (modules/sextant/qe_inputs.pw_input with the SSSP library of modules/sextant/qe_pseudo), the run as a job of this
    computer (runner.Job), its progress (the «!» energies and the pressure of the output so far), the result read by
    modules/spectrum/readers/qe.read: the energy (Ry, hartree, eV per cell and per atom), the pressure, the gap or the
    Fermi level; after a relaxation — «Открыть оптимизированную ячейку» (a new crystal tab).
§4 SPECIFICATION
    QeWindow(owner, crystal, name): task (combo), spacing, processes (spin boxes), preview (text), run_button,
    stop_button, status, summary, open_button; input_text() -> str; start() -> Job | None; poll() -> result | None;
    stop(); open_relaxed() -> bool. folder — the folder of the run (jobs root of the window / qe-<name>-<time>).
    Primitive (check box) — a centred lattice computed in its primitive cell (crystal.primitive), on by default.
    QePanel(owner, crystal, name) — the same controls as a widget (Sextant shows it for the program «Quantum
    ESPRESSO», modules/sextant/crystal_mode.py); set_crystal(crystal, name) puts another crystal in while no job runs;
    top_row — a row over the settings (Sextant puts the program and the crystal there). QeWindow — the dialog of
    «Кристалл» around one QePanel (its attributes are those of the panel).
    The tasks «Зонная структура» and «Плотность состояний» (qe_inputs.STEPS): the files of the steps and run.sh
    (pw.x, pw.x | dos.x one after another, the output of all in pw.out) in one job; path.json — the path of the bands
    (qe_paths); plot_button «Показать зоны» / «Показать плотность состояний» opens QePlotWindow (qe_plots.py), the
    summary gives the gap along the path. steps() -> [(file, program, text)]; show_plot() -> QePlotWindow | None.
    Where (combo, shown when a server profile is ready — remote.load): «Этот компьютер» or «Сервер · …»; on the
    server the folder gets the pseudopotentials of its elements in pseudo/ (pseudo_dir './pseudo'), job.sh of
    remote_job.prepare_qe, and the job is a remote_job.RemoteJob (sent, queued in SLURM, its pw.out copied while it
    grows, azimuth.dos brought back at the end) — the window watches it as a job of this computer. start_server(steps).
§6 NOTES
    Serial pw.x for one process; with more, the mpirun of .tools/qe (Open MPI 5 of the package), OPAL_PREFIX set to its
    prefix. Not on Windows (no build of Quantum ESPRESSO there) — the window says so.
§7 TESTS
    tests/gui/test_gui_files.py::test_crystal_quantum_espresso_window (a fake pw.x printing the real outputs).
"""

import os

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QDialog, QVBoxLayout, QWidget

from azimuth.i18n import tr
from azimuth.ui import action_button
from modules.compass.actions.qe_common import NOTES, task_title
from modules.compass.actions import qe_controls as _controls
from modules.compass.actions import qe_run as _run
from modules.compass.actions import qe_results as _results


def own_library(panel):
    """The PBE library of SSSP is downloaded apart from Quantum ESPRESSO: on Windows (no build of it to install) and
    for a calculation on the server (nothing of it is needed here but the pseudopotentials)."""
    return os.name == 'nt' or (hasattr(panel, 'where') and panel.on_server())


class QePanel(QWidget):
    """compact — the controls laid out in the panel (the dialog of «Кристалл»); False — made, not laid out: the page
    of Sextant (crystal_mode.py) puts them into its cards, as those of a molecule."""

    def __init__(self, owner, crystal, name, parent=None, compact=True, where_in_form=True):
        super().__init__(parent)
        self.owner, self.crystal, self.name = owner, crystal, name
        self.job, self.folder, self.result = None, None, None
        self.external = None  # the pressure on the cell, GPa (set by the batch of crystals)
        self.batch_ident, self.batch_name = None, ''  # the crystal of the project a run of the batch is of
        self.batch = None  # the batch of crystals going on (crystal_batch.CrystalBatch)
        self.input_edited, self._generated = False, ''
        self.program = 'qe'  # or 'cp2k' (set_program)
        self.where_in_form = where_in_form  # Sextant: the switches by «Запустить расчёт» (before the rows are made)
        self.program_listener = None  # called with 'qe' or 'cp2k' after set_program
        self.listeners = []  # callable(event, panel) — 'start', 'progress', 'end' (the job card of Sextant)
        self._make_controls()
        if compact:
            self._compact_layout()
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.poll)
        for combo in (self.task, self.kmode, self.occupations, self.smearing, self.vdw, self.conv, self.basis,
                      self.cp2k_vdw, self.eps_scf, self.functional, self.cp2k_functional, self.order, self.dofree):
            combo.currentIndexChanged.connect(lambda _: self.settings_changed())
        self.program_box.currentIndexChanged.connect(lambda _: self.set_program(self.program_box.currentData()))
        for box in (self.spacing, self.degauss, self.ecutwfc, self.ecutrho, self.magnetization, self.forces, self.pressure,
                    self.cutoff, self.rel_cutoff, self.temperature, self.charge, *self.grid, *self.supercell):
            box.valueChanged.connect(lambda _: self.settings_changed())
        self.hubbard.textChanged.connect(lambda _: self.settings_changed())
        for box in (self.primitive, self.cut_auto, self.spin):
            box.toggled.connect(lambda _: self.settings_changed())
        self.preview.textChanged.connect(self.preview_changed)
        self.set_crystal(crystal, name)

    _make_controls = _controls._make_controls
    rows = _controls.rows
    apply_machine = _controls.apply_machine
    _compact_layout = _controls._compact_layout
    show_rows = _controls.show_rows

    def set_program(self, kind):
        """'qe' or 'cp2k' — its tasks, its rows, its input."""
        from modules.sextant import cp2k_inputs, qe_inputs

        if self.job is not None and self.job.running:
            return False
        kind = 'cp2k' if kind == 'cp2k' else 'qe'
        self.program = kind
        self.program_box.blockSignals(True)
        self.program_box.setCurrentIndex(self.program_box.findData(kind))
        self.program_box.blockSignals(False)
        chosen = self.task.currentData()
        tasks = tuple(cp2k_inputs.TASKS) if kind == 'cp2k' else qe_inputs.ALL_TASKS
        self.task.blockSignals(True)
        self.task.clear()
        for title in tasks:
            self.task.addItem(task_title(title, kind), title)
        self.task.setCurrentIndex(max(0, self.task.findData(chosen)))
        self.task.blockSignals(False)
        self.note.setText(tr(NOTES[kind]))
        self.apply_gamma_supercell()
        self.input_edited = False
        self.edited_note.hide()
        self.reset_button.hide()
        self.result = None
        self.summary.setText('')
        self.plot_button.hide()
        self.aim_button.hide()
        self.charges_button.hide()
        self.settings_changed()
        self.preview.set_language('cp2k' if kind == 'cp2k' else 'qe')  # its colours and Ctrl+/ («#», «!»)
        if self.program_listener is not None:  # the page of Sextant: the title of its input file
            self.program_listener(kind)
        self.show_last_run()
        return True

    def options(self):
        from modules.sextant import hubbard, qe_inputs

        if self.program == 'cp2k':
            from modules.sextant import cp2k_inputs

            return cp2k_inputs.Options(cutoff=self.cutoff.value(), rel_cutoff=self.rel_cutoff.value(),
                                       basis=self.basis.currentData(), vdw=self.cp2k_vdw.currentData(),
                                       occupations=self.occupations.currentData(), temperature=self.temperature.value(),
                                       eps_scf=float(self.eps_scf.currentData()), charge=int(self.charge.value()),
                                       functional=self.cp2k_functional.currentData() or 'PBE',
                                       hubbard=hubbard.parse(self.hubbard.text()),
                                       spin=self.spin.isChecked() and self.order.currentData() == 'fm',
                                       magnetic=self.magnetic_signs(), external=self.external)

        auto = self.cut_auto.isChecked()
        return qe_inputs.Options(
            ecutwfc=None if auto else self.ecutwfc.value(), ecutrho=None if auto else self.ecutrho.value(),
            grid=tuple(b.value() for b in self.grid) if self.kmode.currentData() == 'grid' else None,
            occupations=self.occupations.currentData(), smearing=self.smearing.currentData(), degauss=self.degauss.value(),
            vdw=self.vdw.currentData(), spin=self.spin.isChecked(), magnetization=self.magnetization.value(),
            conv=float(self.conv.currentData()), forces=self.forces.value() or None, pressure=self.pressure.value() or None,
            functional=self.functional.currentData() or '', charge=float(self.charge.value()),
            hubbard=hubbard.parse(self.hubbard.text()), magnetic=self.magnetic_signs(), external=self.external,
            dofree=self.dofree.currentData() or '')

    def magnetic_signs(self):
        """The signs of the antiferromagnetic order of the cell computed (magnetism.afm_signs), otherwise;
        ValueError when the cell cannot hold two sublattices (said in the status, the run waits)."""
        if not self.spin.isChecked() or self.order.currentData() != 'afm' or self.crystal is None:
            return ()
        from modules.sextant import magnetism

        computed, _ = self.computed()
        return magnetism.afm_signs(computed, tuple(b.value() for b in self.supercell))

    def ask_magnetism(self):
        """A crystal of usually magnetic atoms (Ni, Fe, Mn, Co, Cr, V, Cu, the lanthanides, U …) started without spin —
        a question once per crystal: the antiferromagnetic order, the start as it is, or back to the settings. True — go
        on."""
        from modules.compass.chemistry import crystal as cr
        from modules.sextant import magnetism

        if self.spin.isChecked() or self.crystal is None or id(self.crystal) in self.magnetic_asked:
            return True
        if self.program == 'cp2k' and self.cp2k_functional.currentData() == 'GFN1-XTB':
            return True
        found = magnetism.usually_magnetic(a[0] for a in cr.unit_cell(self.crystal))
        if not found:
            return True
        from PySide6.QtWidgets import QMessageBox

        from azimuth import quill

        buttons = QMessageBox.StandardButton
        answer = quill.question(
            self, tr('Магнитные атомы'),
            tr('В ячейке {} — их соединения обычно магнитные (NiO, MnO, FeO, CoO — антиферромагнетики). Без спиновой '
               'поляризации щель, моменты и энергия выйдут неверными, даже с DFT+U.\n\nВключить антиферромагнитный '
               'порядок? Ячейка должна вмещать обе подрешётки — для NiO и MnO в примитивной ячейке нужна суперячейка '
               '2 × 1 × 1.').format(', '.join(found)),
            buttons.Yes | buttons.No | buttons.Cancel, buttons.Yes, 'calc-stopped',
            {buttons.Yes: tr('Включить АФМ'), buttons.No: tr('Считать без спина')})
        if answer == buttons.No:
            self.magnetic_asked.add(id(self.crystal))
            return True
        if answer == buttons.Yes:
            self.order.setCurrentIndex(self.order.findData('afm'))
            self.spin.setChecked(True)  # the settings and the input follow; a cell too small says so in the status
            return self.refresh()  # the order fits the cell — the run goes on
        return False

    def library(self):
        """The SSSP library of the functional chosen (qe_pseudo.LIBRARIES)."""
        from modules.sextant import qe_inputs, qe_pseudo

        return qe_pseudo.LIBRARIES[qe_inputs.library_of(self.functional.currentData() or '')]

    def computed(self):
        """(the crystal computed — primitive and/or supercell —, the rows of its cell in fractions of the cell of the
        file, for the band path)."""
        import numpy as np

        from modules.compass.chemistry import crystal as cr

        primitive = self.primitive.isChecked() and self.primitive_crystal is not self.crystal
        base = self.primitive_crystal if primitive else self.crystal
        n = tuple(b.value() for b in self.supercell)
        basis = cr.primitive_basis(self.crystal) if primitive else None
        if n != (1, 1, 1):
            basis = np.diag(n).astype(float) @ (basis if basis is not None else np.eye(3))
        return cr.supercell(base, n), basis

    GAMMA_LENGTH = 10.0  # Å: the shortest edge of a cell computed at the Γ point alone (CP2K)

    def gamma_supercell(self):
        """The supercell whose edges are all at
        least GAMMA_LENGTH — 3 × 3 × 3 for CsCl, 1 × 1 × 1 for a molecular crystal of 10 Å and more."""
        from math import ceil

        primitive = self.primitive.isChecked() and self.primitive_crystal is not self.crystal
        base = self.primitive_crystal if primitive else self.crystal
        if base is None:
            return (1, 1, 1)
        return tuple(max(1, ceil(self.GAMMA_LENGTH / x - 1e-9)) for x in (base.cell.a, base.cell.b, base.cell.c))

    def apply_gamma_supercell(self):
        """CP2K: the supercell for the Γ point, unless the user chose one; back to 1 × 1 × 1 for Quantum ESPRESSO (its
        k points sample the zone) when it was chosen here. The note under the form says it."""
        now = tuple(b.value() for b in self.supercell)
        auto = getattr(self, '_gamma_cells', None)
        wanted = self.gamma_supercell() if self.program == 'cp2k' else (1, 1, 1)
        if now in ((1, 1, 1), auto) and now != wanted:
            for box, n in zip(self.supercell, wanted):
                box.blockSignals(True)
                box.setValue(n)
                box.blockSignals(False)
        self._gamma_cells = wanted if self.program == 'cp2k' and wanted != (1, 1, 1) else None
        self.note.setText(tr(NOTES[self.program]) + self.gamma_note())

    def gamma_note(self):
        if self.program != 'cp2k' or self.crystal is None:
            return ''
        computed, _ = self.computed()
        short = min(computed.cell.a, computed.cell.b, computed.cell.c)
        if short + 1e-6 >= self.GAMMA_LENGTH:
            return ''
        return ' ' + tr('Осторожно: ребро считаемой ячейки {} Å — для расчёта в Γ-точке нужна суперячейка не меньше '
                        '{} (рёбра от {} Å), иначе энергия и особенно ячейка недостоверны.').format(
            f'{short:.1f}', ' × '.join(str(n) for n in self.gamma_supercell()), f'{self.GAMMA_LENGTH:g}')

    def keep_for_crystal(self, crystal):
        """The settings of one crystal that make no sense for another — the U of elements not in its cell are dropped,
        the charge of the cell goes back to 0. Returns what was dropped."""
        from modules.compass.chemistry import crystal as cr
        from modules.sextant import hubbard

        if crystal is None or not hasattr(self, 'hubbard') or getattr(self, '_kept_for', None) is crystal:
            return ''
        first = getattr(self, '_kept_for', None) is None
        self._kept_for = crystal
        elements = {a[0] for a in cr.unit_cell(crystal)}
        try:
            items = hubbard.parse(self.hubbard.text())
        except ValueError:
            items = None  # a line not understood stays — its error is said
        dropped = []
        if items is not None:
            kept = [i for i in items if i[0] in elements]
            dropped = [i[0] for i in items if i[0] not in elements]
            if dropped:  # the signals go on: the line of «Дополнительные настройки…» follows
                self.hubbard.setText(', '.join(f'{e} {u:g}' if m == hubbard.MANIFOLDS[e] else f'{e}-{m} {u:g}'
                                               for e, m, u in kept))
        if self.charge.value() and not first:
            self.charge.setValue(0)
        return ', '.join(dropped)

    def name_hubbard(self):
        """The placeholder of DFT+U names the d and f elements of this crystal (empty — none)."""
        from modules.compass.chemistry import crystal as cr
        from modules.sextant import hubbard

        found = hubbard.candidates(a[0] for a in cr.unit_cell(self.crystal)) if self.crystal is not None else []
        self.hubbard.setPlaceholderText(tr('U для {}, эВ: например «{} 5»').format(', '.join(found), found[0]) if found
                                        else tr('нет d- и f-элементов — не нужен'))

    def settings_changed(self):
        self.show_rows()
        if hasattr(self, 'pseudo_button'):  # only while the library of the functional is missing
            from modules.sextant import qe_pseudo

            try:
                missing = self.program != 'cp2k' and not qe_pseudo.installed(self.root(), self.library())
            except (OSError, ValueError):
                missing = False
            # the PBE library comes with Quantum ESPRESSO — but on Windows (no build) or for the server it is downloaded
            # by itself (the owner's Windows, 2026-11-24: «Сервер» with Quantum ESPRESSO did nothing)
            self.pseudo_button.setVisible(missing and (self.library() is not qe_pseudo.LIBRARY or own_library(self)))
        if hasattr(self, 'note'):
            self.note.setText(tr(NOTES[self.program]) + self.gamma_note())
        self.refresh()

    def preview_changed(self):
        if getattr(self, '_filling', False):
            return
        edited = self.preview.toPlainText() != self._generated
        if edited != self.input_edited:
            self.input_edited = edited
            self.edited_note.setVisible(edited)
            self.reset_button.setVisible(edited)

    def reset_input(self):
        self.input_edited = False
        self.edited_note.hide()
        self.reset_button.hide()
        self.refresh()

    def set_crystal(self, crystal, name):
        """The crystal to compute (Sextant: the crystal tab chosen); not while a job runs."""
        from modules.compass.chemistry import crystal as cr

        if self.job is not None and self.job.running:
            return False
        self.crystal, self.name = crystal, name
        self.result = None
        self.summary.setText('')
        self.open_button.setEnabled(False)
        self.plot_button.hide()
        self.primitive_crystal = cr.primitive(crystal) if crystal is not None else None
        whole = len(cr.unit_cell(crystal)) if crystal is not None else 0
        small = len(cr.unit_cell(self.primitive_crystal)) if crystal is not None else 0
        self.primitive.blockSignals(True)
        # the cell of the file primitive already (P 21/n): the row says so, not «60 атомов вместо 60»
        self.primitive.setText(tr('примитивная: {} атомов вместо {}').format(small, whole) if small < whole
                               else tr('ячейка файла уже примитивная'))
        self.primitive.setEnabled(small < whole)
        self.primitive.setChecked(small < whole)
        self.primitive.blockSignals(False)
        self._gamma_cells = None  # another crystal: its own supercell for the Γ point
        self.keep_for_crystal(crystal)
        if hasattr(self, 'note'):
            for box in self.supercell:
                box.blockSignals(True)
                box.setValue(1)
                box.blockSignals(False)
            self.apply_gamma_supercell()
        self.name_hubbard()
        self.show_rows()
        self.refresh()
        self.name_auto_occupations()
        if hasattr(self, 'aim_button'):
            self.aim_button.hide()
            self.charges_button.hide()
            self.show_last_run(choose_program=True)  # a crystal opened: the program of its last run
        return True

    def name_auto_occupations(self):
        """2026-11-13 (CsCl showed «авто (металл — размытие)» — read as «a metal»): the item «авто» says what it
        chose for this crystal — an insulator with fixed occupations, or a metal with smearing (crystal_symmetry.
        is_metal: every element a metal)."""
        from modules.compass.chemistry import crystal as cr
        from modules.compass.chemistry import crystal_symmetry as cs

        index = self.occupations.findData('auto')
        if index < 0:
            return None
        if self.crystal is None:
            text = tr('авто (металл — размытие)')
        else:
            species = {a[0] for a in cr.unit_cell(self.crystal) if a[0] != 'X'}
            text = tr('авто: металл — размытие') if cs.is_metal(species) else tr('авто: изолятор — фиксированные')
        self.occupations.setItemText(index, text)
        return text

    def show_last_run(self, choose_program=False):
        """The last finished run of this program in the project of the crystal (crystal_projects runs, the folder kept)
        — its summary and, for CP2K, the file for Multiwfn with «Связи по AIM» and «Заряды»; «Открыть оптимизированную
        ячейку» — its steps (the supercell read back from the first one). False when there is none. choose_program (a
        crystal just put in): with no run of the program chosen, the program of the last run of the project is chosen; a
        program the user picks is kept."""
        from azimuth import crystal_projects

        if self.job is not None and self.job.running:
            return False
        try:
            root = self.jobs_root()
            manifest = root.parent / 'project.qcc'
            if root.name != 'calculations' or not crystal_projects.is_crystal(manifest):
                return False
            every = crystal_projects.info(manifest).get('runs', [])
            runs = [r for r in every if r.get('program', 'qe') == self.program]
        except (OSError, ValueError, AttributeError):
            return False
        # no run of the
        # program chosen — the program of the last run of the project is chosen, and its run shown
        other = next((r.get('program', 'qe') for r in reversed(every)
                      if r.get('program', 'qe') != self.program and (manifest.parent / str(r.get('folder', ''))).is_dir()),
                     None)
        if choose_program and not runs and other in ('qe', 'cp2k') and not getattr(self, '_choosing_program', False):
            self._choosing_program = True
            try:
                self.set_program(other)  # it shows that run (show_last_run again)
            finally:
                self._choosing_program = False
            return bool(self.result)
        cp2k = self.program == 'cp2k'
        for run in reversed(runs):
            folder = manifest.parent / str(run.get('folder', ''))
            output = folder / ('cp2k.out' if cp2k else 'pw.out')
            if not output.is_file():
                continue
            text = output.read_text(encoding='utf-8', errors='replace')
            if cp2k:
                from modules.spectrum.readers import cp2k as reader

                result = reader.read(text, folder)
            else:
                from modules.spectrum.readers import qe

                result = qe.read((qe.runs(text) or [text])[0])
            if result.done and not result.error and result.energy is not None:
                break
        else:
            return False
        self.job, self.folder, self.result = None, folder, result  # not the job of another crystal run here before
        self.open_button.setEnabled(bool(self.optimization_steps()))  # the steps, the supercell read back
        summary = tr('Последний расчёт проекта: {}').format(folder.name) + '<br>' + self.summary_text(result)
        if cp2k:
            summary += self.multiwfn_line()
        self.summary.setText(summary)
        return True

    # -- the input -----------------------------------------------------------------------------------------------
    def root(self):
        from modules.sextant import install_tools

        return install_tools.default_root()

    def server_profile(self):
        """The server profile of «Сервер…» when it is filled in, else None."""
        preferences = getattr(self.owner, 'preferences', None)
        if preferences is None:
            return None
        from modules.sextant import remote

        profile = remote.load(preferences)
        return profile if profile.ready() else None

    def update_where(self):
        """The places to compute: this computer and the server of «Сервер…» when it is set up."""
        if self.job is not None and self.job.running:
            return
        chosen = self.where.currentData()
        self.where.blockSignals(True)
        self.where.clear()
        self.where.addItem(tr('Этот компьютер'), 'local')
        profile = self.server_profile()
        if profile is not None:
            self.where.addItem(tr('Сервер · ') + profile.title(), 'server')
        self.where.setCurrentIndex(max(0, self.where.findData(chosen)))
        self.where.blockSignals(False)
        for item in (self.where_label, self.where):
            # in Sextant the list is not in the panel (where_in_form False: the switches by «Запустить расчёт» stand for
            # it); a widget without a parent shown becomes a window of its own
            if item.parentWidget() is not None:
                item.setVisible(self.where.count() > 1)
        form = getattr(self, 'form', None)  # no empty row «Где считать» without a server
        if form is not None and form.indexOf(self.where) >= 0:
            form.setRowVisible(self.where, self.where.count() > 1)

    def on_server(self):
        return self.where.currentData() == 'server'

    def where_changed(self):
        self.processes.setRange(1, 256 if self.on_server() else max(1, os.cpu_count() or 1))
        self.settings_changed()  # «Скачать псевдопотенциалы» for the server too

    steps = _run.steps
    download_library = _run.download_library
    input_text = _run.input_text
    run_steps = _run.run_steps
    refresh = _run.refresh
    jobs_root = _run.jobs_root
    start = _run.start
    batch_idents = _run.batch_idents
    run_clicked = _run.run_clicked
    set_crystal_for_batch = _run.set_crystal_for_batch
    _start_cp2k = _run._start_cp2k
    output_path = _run.output_path
    _tell = _run._tell
    _started = _run._started
    start_server = _run.start_server
    _write_path = _run._write_path
    reference = _results.reference
    band_data = _results.band_data
    dos_data = _results.dos_data
    phonon_data = _results.phonon_data
    eos_data = _results.eos_data
    series_data = _results.series_data
    states_data = _results.states_data
    states_table = _results.states_table
    series_lines = _results.series_lines
    show_series = _results.show_series
    eos_lines = _results.eos_lines
    show_eos = _results.show_eos
    show_phonons = _results.show_phonons
    show_plot = _results.show_plot
    stop = _run.stop
    progress_parts = _run.progress_parts
    poll = _run.poll
    multiwfn_line = _results.multiwfn_line
    multiwfn_found = _results.multiwfn_found
    show_aim = _results.show_aim
    show_charges = _results.show_charges
    _record = _results._record
    summary_text = _results.summary_text
    file_cell_of = _results.file_cell_of
    open_relaxed = _results.open_relaxed
    computed_as = _results.computed_as
    optimization_steps = _results.optimization_steps


class QeWindow(QDialog):
    """The dialog of «Кристалл → Расчёт в Quantum ESPRESSO…»: one QePanel and «Закрыть»."""

    def __init__(self, owner, crystal, name):
        super().__init__(owner)
        self.setWindowTitle(tr('Quantum ESPRESSO · ') + name)
        layout = QVBoxLayout(self)
        self.panel = QePanel(owner, crystal, name, self)
        self.panel.buttons.addWidget(action_button(tr('Закрыть'), self.reject, 'close'))
        layout.addWidget(self.panel)
        self.resize(1080, 700)

    # QDialog.result() would hide the result of the run
    result = property(lambda self: self.panel.result)

    def __getattr__(self, name):  # the controls, the run and the result are those of the panel
        panel = self.__dict__.get('panel')
        if panel is None:
            raise AttributeError(name)
        return getattr(panel, name)
