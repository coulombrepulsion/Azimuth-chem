"""SextantWorkspace: the page of a molecular calculation in Sextant and the state of its calculations. Contract:
docs/MODULES.md.

§1 PURPOSE
    The page sets up one calculation of the molecule of the tab: «Программа» (ORCA, Gaussian, Psi4, xtb, MOPAC,
    GAMESS (US), NWChem — workspace_texts.PROGRAMS), «Задача» (inputs.PROGRAM_TASKS; chains of two steps), the method
    and the basis set the program knows (azimuth.core.METHOD_TABLE, BASIS_TABLE, grouped by family), the charge and the
    multiplicity, «Название» (Calculation.title: the first line of the input and the name of its files, core.file_base;
    empty — formula_method_basis[_solvent]). The rarer settings — processes and memory, solvent, dispersion, SCF, the
    limit of the cycles of an optimization (100 by default, 0 — as in the program), properties — are in «Дополнительные
    настройки…» (job_window.OptionsDialog), summed up under the button. The advice of Sextant (advice.py) proposes the
    method, the basis set and the dispersion for the task and the molecule.
§2 ALGORITHM
    The page is built by calculation_page.py (the card of the input file, the card «Запуск расчёта», «Где считать»:
    «Этот компьютер» / «Сервер»); the texts and the defaults are in workspace_texts.py, small widgets in
    workspace_widgets.py, the scan in workspace_scan.py, the molecule of the calculation (charge and multiplicity of its
    structure, basis sets of its elements) in workspace_molecule.py. The work is done by parts of the window with a PORT
    of their own (azimuth/window_port.py), made when first used: run_tool (run_actions — the start, the watching, the
    end and the result, here or on a server), input_tool (input_actions — the input file shown, edited and checked),
    batch_tool (batch_actions — queues, Fukui, CDA), server_watch_tool, program_tool, install_tool, history_tool,
    doctor_tool, crystal_mode_tool (crystal_mode.py — the page of a crystal tab). calculation() is the Calculation of
    the fields; apply_calculation(calc) puts one back into them (a repeat, the doctor, a project).
    One calculation per place (this computer, the server — azimuth/runtime/places.PLACES): job, job_window, batch … are
    descriptors over the RunSlot of the place (_PerPlace); at_place(place) makes another place the current one for a
    block. The calculation is shown as a card in the place of the input file (job_window docked into job_slot; «Входной
    файл» on it brings the file back); in the other sections the hourglass of the hub opens it as a window, and coming
    back to Sextant puts it in its place again (job_follow).
§3 APPLICATIONS azimuth/app.py (Studio — the page «Секстант» of the hub).
§7 TESTS tests/gui/test_gui_sextant.py; tests/sextant/.
"""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QWidget
from azimuth.core import (
    BASIS_TABLE,
    CDA_TASK,
    INTERACTION_TASK,
    IRC_TASK,
    DISPERSION_METHODS,
    METHOD_TABLE,
    NEB_TASK,
    XTB_ORCA,
    Calculation,
    bases_for,
    methods_for,
)

from modules.sextant import inputs
from modules.sextant import advice
from azimuth.runtime.places import Slotted
from modules.sextant.run_actions import PLACES
from azimuth.window_port import part
from azimuth.i18n import KEY_ROLE, combo_key, set_combo_key, tr
from modules.sextant.workspace_texts import (
    NAMES,
    DISPERSION_NAMES,
    TITLES,
    NOTICES,
    DEFAULT_MOPAC_METHOD,
    DEFAULT_METHOD,
    DEFAULT_BASIS,
    COMMENT_SIGNS,
)
from modules.sextant.workspace_widgets import fill_grouped, WrappedNote
from modules.sextant import calculation_page as _page
from modules.sextant import workspace_scan as _scan
from modules.sextant import workspace_molecule as _molecule


class _PerPlace(Slotted):
    """An attribute of Sextant kept for each place of calculation («Этот компьютер», «Сервер»): a calculation on
    this computer and one on a server go on at the same time, each with its own window; the attribute means the one
    of the place chosen now (job_place(); at_place(place) — of another place for a while). A field of the
    explicit RunSlot of that place (azimuth/runtime/places.py); the default is the one of the slot."""

    def __init__(self, default=None):
        super().__init__()


class _PlaceOverride:
    def __init__(self, owner, place):
        self.owner, self.place = owner, place

    def __enter__(self):
        self.before = self.owner.__dict__.get('_place_override')
        self.owner.__dict__['_place_override'] = self.place
        return self.owner

    def __exit__(self, *exc):
        self.owner.__dict__['_place_override'] = self.before
        return False


class SextantWorkspace:
    # the running, the input file and the queues are parts of their own with a PORT (azimuth/window_port.py);
    # the state of a place (job, batch, …) stays here
    run_tool = property(lambda self: part(self, 'run_tool', 'modules.sextant.run_actions', 'RunTool'))
    input_tool = property(lambda self: part(self, 'input_tool', 'modules.sextant.input_actions', 'InputTool'))
    batch_tool = property(lambda self: part(self, 'batch_tool', 'modules.sextant.batch_actions', 'BatchTool'))
    # the watching of the server (its mark, «Проверить подключение», «Файлы на сервере»)
    server_watch_tool = property(lambda self: part(self, 'server_watch_tool', 'modules.sextant.server_watch_actions',
                                                   'ServerWatchTool'))
    # the program shown and chosen (its mark, «Указать…», «Установить…» when it is missing)
    program_tool = property(lambda self: part(self, 'program_tool', 'modules.sextant.program_actions', 'ProgramTool'))
    # «Установить программы для расчёта» (Open MPI, xtb, CREST, MOPAC, Quantum ESPRESSO, CP2K …)
    install_tool = property(lambda self: part(self, 'install_tool', 'modules.sextant.install_actions', 'InstallTool'))
    # «История расчётов» (the rows, the window, «Открыть результат», «Папка», «Очистить список»)
    history_tool = property(lambda self: part(self, 'history_tool', 'modules.sextant.history_actions', 'HistoryTool'))
    # the doctor of a calculation — the repeat with the remedy for what went wrong
    doctor_tool = property(lambda self: part(self, 'doctor_tool', 'modules.sextant.doctor_actions', 'DoctorTool'))
    # the page of the calculation of a crystal tab (Quantum ESPRESSO, CP2K) — crystal_mode.py
    crystal_mode_tool = property(lambda self: part(self, 'crystal_mode_tool', 'modules.sextant.crystal_mode',
                                                   'CrystalModeTool'))
    # one calculation per place (see _PerPlace)
    job = _PerPlace()
    job_window = _PerPlace()
    job_task = _PerPlace()
    job_document = _PerPlace()
    _job_cycles = _PerPlace()
    _job_shown = _PerPlace()
    job_panel_open = _PerPlace()
    _job_done = _PerPlace()
    batch_finished_here = _PerPlace()  # the queue of this place is over, its conformers are in Compass
    batch_project_here = _PerPlace()  # the project of the queue over («Перейти в Компас» opens it)
    last_batch = _PerPlace()
    _job_seen = _PerPlace()  # its result was looked at in Compass or Spectrum — the hourglass is gone
    # the fields of azimuth/runtime/places.RunSlot (their defaults are there)

    @property
    def batch(self):
        """The queue of the place chosen now (the field batch of its RunSlot; on the window, as job — the state of a
        place)."""
        from azimuth.runtime.places import Slotted

        return Slotted.slots(self).slot(self.job_place()).batch

    @batch.setter
    def batch(self, value):
        from azimuth.runtime.places import Slotted

        Slotted.slots(self).slot(self.job_place()).batch = value

    def job_place(self):
        return self.__dict__.get('_place_override') or getattr(self, 'where', 'local')

    def at_place(self, place):
        return _PlaceOverride(self, place)

    @property
    def stop_button(self):
        return self.job_window.stop_button

    @property
    def folder_button(self):
        return self.job_window.folder_button

    @property
    def run_status(self):
        return self.job_window.status

    def all_places(self):
        """This computer, the server and the calculations on the server moved aside (park_server_job)."""
        return Slotted.slots(self).all_places(PLACES)

    def job_windows(self):
        """The windows of the calculations of both places (the hub sets their on_parked)."""
        found = []
        for place in PLACES:
            with self.at_place(place):
                if self.job_window is not None:
                    found.append(self.job_window)
        return found

    def running_jobs(self):
        """The calculations still going on, of both places (of the run slots)."""
        slots = Slotted.slots(self)
        return [slots.slot(place).job for place in self.all_places()
                if slots.slot(place).job is not None and slots.slot(place).job.running]

    def parked_server_jobs(self):
        """[(place, title, running)] of the calculations on the server moved aside, the oldest first."""
        found = []
        for slot in Slotted.slots(self).parked('server'):
            jw = slot.job_window
            title = (jw.heading.text() if jw is not None and hasattr(jw, 'heading') else '') or slot.place
            found.append((slot.place, title, bool(slot.job is not None and slot.job.running)))
        return found

    def show_parked_job(self, place):
        slot = Slotted.slots(self).slot(place)
        return slot.job_window.show_window() if slot.job_window is not None else None

    def slot_of(self, job):
        """The RunSlot of the place whose calculation job is (identity) — not the place chosen now."""
        return Slotted.slots(self).of_job(job)

    calculation_page = _page.calculation_page

    def run_by_key(self):
        """Ctrl+Enter: «Запустить расчёт» when its button can be pressed (the button decides, not the keys)."""
        if self.run_button.isEnabled() and self.run_button.isVisible():
            self.run_button.click()
            return True
        return False

    def stop_by_key(self):
        """Ctrl+.: «Остановить» when a calculation (or a queue) runs here."""
        if self.stop_button.isEnabled():
            self.stop_button.click()
            return True
        return False

    run_card = _page.run_card

    def toggle_input_expanded(self, *args):
        from azimuth.icons import icon

        expanded = self.expand_input_button.isChecked()
        self.calc_card.setVisible(not expanded)
        self.expand_input_button.setText(tr('Свернуть') if expanded else tr('Развернуть'))
        name = 'collapse' if expanded else 'expand'  # the arrows inwards while it is unfolded
        self.expand_input_button.setIcon(icon(name))
        self.expand_input_button.setProperty('quail_icon', name)

    def update_calc_card(self):
        """The card of the molecule in Sextant: the small model and the formula."""
        if not hasattr(self, 'calc_thumb'):
            return
        mol = self.calculation_molecule()
        self.calc_thumb.set_molecule(mol)
        empty = not mol.atoms
        self.calc_thumb.setVisible(not empty)
        self.calc_quill.setVisible(empty and not self.calc_quill.pixmap().isNull())
        viewer = getattr(self, 'viewer', None)
        if viewer is not None:
            self.calc_thumb.set_palette(getattr(viewer, 'palette', {}))
            self.calc_thumb.set_dark(getattr(viewer, 'dark', False))
        formula = mol.formula.translate(str.maketrans('0123456789', '₀₁₂₃₄₅₆₇₈₉')) if mol.atoms else tr('Атомов пока нет')
        self.calc_formula.setText(formula)

    def sextant_shown(self):
        """The page of Sextant is what the user sees now (in the hub: the Studio is the shown section)."""
        return self.isVisible() and self.stack.currentIndex() == 1

    def _show_job_card(self, shown):
        """In Sextant the calculation and the input file share one place of the right column."""
        self.job_slot.setVisible(shown)
        self.preview_card.setVisible(not shown)
        self.job_window_button.setVisible(not shown and self._job_shown)  # «Окно расчёта» brings it back

    def show_job_window(self):
        """The calculation: in Sextant — the card in the place of the input file; elsewhere — its window."""
        jw = self.job_window
        self._job_shown = True
        # nothing run yet — a dash and what to do, not an empty card; not over the installation either — it is a
        # job of the window too (install_tool.begin), only not self.job
        if self.job is None and not getattr(jw, 'used', False):
            jw.show_idle()
        if self.sextant_shown():
            self.job_panel_open = True
            crystal = getattr(self, 'crystal_mode_tool', None)
            if crystal is not None and crystal.active and crystal.page is not None:
                crystal.show_install(jw)  # the page of a crystal: in the place of its input file
                return jw.show_window()
            jw.dock(self.job_slot)
            self._show_job_card(True)
            return jw.show_window()
        jw.undock()
        return jw.show_window()

    def follow_queue_window(self, was_visible):
        """The next calculation of a
        queue does not bring the window up. In Sextant the card takes it as before; elsewhere a window left open stays
        open where it is (not raised, not focused), a hidden one stays hidden behind the hourglass of the hub."""
        self._job_shown = True
        jw = self.job_window
        if self.sextant_shown():  # the card as job_follow leaves it: «Входной файл» chosen stays chosen
            jw.dock(self.job_slot)
            jw.show()
            self._show_job_card(self.job_panel_open)
            jw._set_parked(False)
            return jw
        if not was_visible:
            if jw.docked:
                jw.undock()
            jw.hide()
            jw._set_parked(True)  # begin() took the hourglass away
        return jw

    def show_input_card(self):
        """«Входной файл» on the card of the calculation — the file comes back, the calculation goes on."""
        self.job_panel_open = False
        crystal = getattr(self, 'crystal_mode_tool', None)
        if crystal is not None and crystal.page is not None and crystal.shows_install(self.job_window):
            crystal.show_input()
            return crystal.preview_card
        self._show_job_card(False)
        return self.preview_card

    def result_seen(self):
        """The result of a finished calculation is open in Compass or Spectrum — the mark of the hub (hourglass
        with a tick) is not needed any more (unless another calculation still runs)."""
        if not self.isVisible() or self.stack.currentIndex() not in (0, 2):
            return False
        seen = False
        for place in self.all_places():
            with self.at_place(place):
                if self.job is not None and self._job_done and not self._job_seen:
                    self._job_seen = seen = True
        if seen and not self.running_jobs():
            self.run_tool.tell_job(None)
        return seen

    def job_follow(self):
        """On every change of section or page — the calculation into Sextant, out of it when the user leaves
        (the hourglass of the hub stands for it then; its click opens the window)."""
        self.result_seen()
        if not getattr(self, '_job_shown', False) or not hasattr(self, 'job_window'):
            return None
        jw = self.job_window
        if self.sextant_shown():
            jw.dock(self.job_slot)
            jw.show()
            self._show_job_card(self.job_panel_open)
            jw._set_parked(False)
            return 'docked'
        if jw.docked:
            jw.undock()
            jw.hide()
            jw._set_parked(True)
        return 'away'

    def show_input_help(self):
        """«?» next to the title of the input file — what its lines mean, as a popup at the button."""
        from azimuth.ui import show_help

        button = self.input_help_button
        show_help(button)  # a panel that stays (the tooltip closed at once)
        return button.toolTip()

    def show_options(self):
        self.options_dialog.show()
        self.options_dialog.raise_()
        self.options_dialog.activateWindow()
        return self.options_dialog

    def update_options_summary(self):
        if not hasattr(self, 'options_summary'):
            return
        parts = []  # the solvent and the dispersion are in the form now; the charge and the
        # multiplicity are in the card of the molecule (here they were shown even without a molecule)
        if self.relativistic.currentData():  # the processes are in the form now
            parts.append(self.relativistic.currentText())
        try:
            changed = self.advanced_count()
        except ValueError:
            changed = 0
        if changed:
            parts.append(tr(f'изменено настроек: {changed}'))
        if hasattr(self, 'guess') and self.guess.path() and self.program_kind() == 'orca':  # from the dialog
            parts.append(tr('орбитали: ') + Path(self.guess.path()).name)
        # at the foot of the card the button says what is behind it while nothing was changed
        self.options_summary.setText(' · '.join(parts) or tr('Дополнительно: заряд, SCF, релятивизм, свойства'))

    def set_run_status(self, text, spent=None):
        """The status in the window of the calculation; next to «Запустить расчёт» only the time."""
        self.run_status.setText(text)
        if self.job_place() != getattr(self, 'where', 'local'):
            return  # the time next to the button is of the place chosen
        self.run_time.setToolTip(text)
        if spent is not None:
            self.run_time.setText(spent)
            self.run_time.show()

    def program_kind(self):
        return self.program.currentData() or 'orca'

    def calculation(self):
        return Calculation(
            self.method.currentData() or self.method.currentText(),
            self.basis.currentData() or self.basis.currentText(),
            combo_key(self.task),
            self.charge.value(),
            self.spin.value(),
            self.cores.value(),
            self.memory.value(),
            self.solvent.currentData() or '',
            (self.dispersion.currentData() or '') if self.dispersion.isEnabled() else '',
            # «Дополнительные настройки»
            scf=self.scf_level.currentData() or 'tight',
            grid=self.grid.currentData() or '',
            no_ri=self.no_ri.isChecked(),
            rijcosx=self.rijcosx.isChecked() and self.program_kind() == 'orca',
            ts=self.ts.isChecked(),
            opt_conv=self.opt_conv.currentData() or 'normal',
            max_cycles=self.max_cycles.value(),
            calc_hessian=self.calc_hessian.isChecked(),
            population=self.population.currentData() or 'mulliken',
            orbitals=self.orbitals.isChecked(),
            states=self.states.value(),
            temperature=self.temperature.value(),
            pressure=self.pressure.value(),
            extra=self._extra,  # from a project of an older version; not edited here any more
            title=self.calc_title.text().strip() if hasattr(self, 'calc_title') else '',
            relativistic=self.relativistic.currentData() or '',
            slow_conv=self.slow_conv.currentData() or '',
            auto_aux=self.auto_aux.isChecked() and self.program_kind() == 'orca',
            num_freq=self.num_freq.isChecked(),
            raman=self.raman.isChecked() and self.program_kind() == 'orca',
            couplings=self.couplings.isChecked() and self.program_kind() == 'orca',
            tddft_mode=self.tddft_mode.currentData() or '',
            triplets=self.triplets.isChecked(),
            root=min(self.root.value(), self.states.value()),
            # SMD only where the program has it (ORCA, Gaussian); the stability analysis of an energy
            solvent_model=(self.solvent_model.currentData() or 'cpcm') if self.program_kind() in ('orca', 'gaussian')
            else 'cpcm',
            stability=self.stability.isChecked() and self.program_kind() in ('orca', 'gaussian'),
            scan_index=max(0, self.scan_index.currentData() if self.scan_index.currentData() is not None else 0),
            scan_end=self.scan_end.value(),
            scan_steps=self.scan_steps.value(),
            scan2_index=self.scan2_index.currentData() if self.scan2_index.currentData() is not None else -1,
            scan2_end=self.scan2_end.value(),
            scan2_steps=self.scan2_steps.value(),
            guess=self.guess.path() if self.program_kind() == 'orca' else '',
            nto=self.nto.isChecked() and self.program_kind() == 'orca',
            cda_atoms=self.cda_atoms.text().strip(),
            element_basis=self.element_basis.text().strip(),
            isotopes=getattr(self, '_isotopes', ''),  # «Изотопы выделенных атомов…» of Compass
            cda_charge=self.cda_charge.value(),
            cda_mult1=self.cda_mult1.value(),
            cda_mult2=self.cda_mult2.value(),
        )

    build_advanced = _page.build_advanced

    def solvent_row(self):
        """The solvent and its model (CPCM / SMD) in one row of the form."""
        row = QWidget()
        pair = QHBoxLayout(row)
        pair.setContentsMargins(0, 0, 0, 0)
        pair.setSpacing(6)
        pair.addWidget(self.solvent, 3)
        pair.addWidget(self.solvent_model, 1)
        self.solvent.currentIndexChanged.connect(lambda *_: self.update_solvent_model())
        # «?» — the handbook of the solvents: ε and the name in each program (azimuth/handbook.py)
        from PySide6.QtWidgets import QToolButton

        self.solvent_help = QToolButton()
        self.solvent_help.setObjectName('helpButton')
        self.solvent_help.setText('?')
        self.solvent_help.setFixedSize(22, 22)
        self.solvent_help.setCursor(Qt.CursorShape.PointingHandCursor)
        self.solvent_help.setToolTip(tr('Растворители в справочнике: ε и имя растворителя в каждой программе'))
        self.solvent_help.clicked.connect(self.open_solvent_handbook)
        pair.addWidget(self.solvent_help, 0)
        return row

    def open_solvent_handbook(self):
        from azimuth.handbook_window import open_handbook

        return open_handbook(self, 'solvents')

    def update_solvent_model(self):
        """The model is shown for ORCA and Gaussian and only with a solvent."""
        if hasattr(self, 'solvent_model'):
            self.solvent_model.setVisible(self.program_kind() in ('orca', 'gaussian') and bool(self.solvent.currentData()))

    TASK_ROWS = (  # (caption, keys of inputs.TASK_OPTIONS in the row) — the settings shown under the task;
        # two short fields share a row, so that ORCA's «Оптимизация + частоты» fits the card of a laptop
        ('', ('stability',)),  # under «Энергия»
        ('', ('ts',)), ('Сходимость', ('opt_conv', 'max_cycles')), ('', ('calc_hessian',)),
        ('T и P', ('temperature', 'pressure')), ('', ('num_freq',)), ('', ('raman',)), ('', ('couplings',)),
        ('Состояния', ('states', 'root')), ('Приближение', ('tddft_mode',)), ('', ('triplets',)), ('', ('nto',)),
        ('Координата', ('scan_index',)), ('Конец', ('scan_end', 'scan_steps')),
        ('Вторая координата', ('scan2_index',)), ('Конец 2', ('scan2_end', 'scan2_steps')),
        ('Фрагмент 1', ('cda_atoms', 'cda_pick')), ('Фрагмент 1:', ('cda_charge', 'cda_mult1')),
        ('Фрагмент 2:', ('cda_mult2',)),
    )  # the number of states and the state to optimize share a row — the excited-state optimization had
    # 8 rows and squeezed the whole form

    build_task_box = _page.build_task_box

    def update_task_box(self):
        """Show the rows of inputs.task_options(program, task); returns the keys shown."""
        if not hasattr(self, 'task_rows'):
            return ()
        kind, task = self.program_kind(), combo_key(self.task)
        shown = inputs.task_options(kind, task)
        form = self.main_form
        rows = getattr(self, 'setup_rows', None)
        for widget, keys, caption in self.task_rows:
            self.show_row(widget, any(k in shown for k in keys))
            if len(keys) > 1:
                for key in keys:
                    getattr(self, key).setVisible(key in shown)
                present = [k for k in keys if k in shown]
                captions = {'temperature': 'Температура', 'pressure': 'Давление', 'opt_conv': 'Сходимость',
                            'max_cycles': 'Предел циклов', 'states': 'Состояний', 'root': 'Оптимизируемое состояние',
                            'scan_end': 'Конец', 'scan_steps': 'Точек', 'scan2_end': 'Конец 2', 'scan2_steps': 'Точек',
                            'cda_atoms': 'Фрагмент 1', 'cda_pick': 'Фрагмент 1',
                            'cda_charge': 'Фрагмент 1:', 'cda_mult1': 'Фрагмент 1:'}
                text = caption if len(present) != 1 else captions[present[0]]  # «T и P» with T alone: «Температура»
                if task == IRC_TASK and present == ['max_cycles']:  # MaxIter of %irc
                    text = 'Шагов в каждую сторону'
                caption_label = rows.label(widget) if rows is not None else form.labelForField(widget)
                if caption_label is not None:
                    caption_label.setText(tr(text))
        note = tr('Конец пути и число промежуточных структур задаются в Компасе («Правка → Путь реакции»).') \
            if task == NEB_TASK else tr('Начинайте с переходного состояния (одна мнимая частота), найденного тем же '
                                        'методом и базисом: путь идёт от него вниз в обе стороны, гессиан считается в '
                                        'начале. Профиль энергии и шаги — в Компасе.') \
            if task == IRC_TASK else tr('Частоты считаются на этой геометрии, без оптимизации: она должна быть '
                                        'оптимизирована тем же методом и базисом — иначе это не минимум.') \
            if task == inputs.FREQ_TASK else self.cda_note() if task == CDA_TASK \
            else self.interaction_note() if task == INTERACTION_TASK else ''
        self.task_note.setText(note)
        self.show_row(self.task_note, bool(note))
        self.task_heading.setText(tr('Настройки задачи') + ' · ' + tr(task))
        outside = [w for w, keys, _ in self.task_rows if any(k in shown for k in keys)
                   and (rows is None or rows.is_outside(keys[0]))]  # the heading only over rows in the card
        self.show_row(self.task_box, bool(outside) or bool(note))
        return shown

    def show_row(self, widget, flag):
        """Show or hide a row of «Постановка задачи» wherever it stands — the card or «Дополнительные
        настройки…» (setup_rows)."""
        rows = getattr(self, 'setup_rows', None)
        if rows is not None:
            rows.show(widget, flag)
        elif hasattr(self, 'main_form'):
            self.main_form.setRowVisible(widget, flag)

    def build_setup_rows(self):
        from modules.sextant.setup_rows import SetupRows

        rows = [('calc_title', self.calc_title), ('program', self.program), ('task', self.task),
                ('chain_steps', self.chain_steps), ('method', self.method_picker), ('basis', self.basis_picker),
                ('solvent', self.solvent_widget), ('dispersion', self.dispersion), ('resources', self.resources_widget),
                ('task_box', self.task_box)]
        rows += [(keys[0], widget) for widget, keys, _ in self.task_rows] + [('task_note', self.task_note)]
        self.setup_rows = SetupRows(self, self.main_form, self.options_dialog.forms[-1], rows,
                                    after=self.update_task_box)
        self.update_task_box()
        return self.setup_rows

    def task_form_note(self):
        from modules.sextant.setup_rows import task_form_note

        note = WrappedNote()
        note.setText(task_form_note())
        return note

    def show_setup_fields(self):
        """The menu of «Поля…»: the fields shown in the card."""
        menu = self.setup_rows.menu(self)
        button = self.fields_button
        menu.exec(button.mapToGlobal(button.rect().bottomLeft()))
        return menu

    def show_chain_steps(self):
        """The steps of the chain chosen in «Задача» under it, or none."""
        from modules.sextant.chain_steps import CHAIN_ROLE

        if not hasattr(self, 'chain_steps') or not hasattr(self, 'main_form'):
            return None
        key = self.task.currentData(CHAIN_ROLE) or None
        self.chain_steps.show_for(key)
        self.main_form.setRowVisible(self.chain_steps, key is not None)
        return key

    def fill_tasks(self, kind):
        """The tasks the program kind can do (inputs.tasks_for); the chosen one stays when the program has
        it, else «Оптимизация + частоты» (or the first) — and the user is told. Returns the task now chosen."""
        from azimuth.i18n import TEXT_ROLE
        from modules.sextant import chain
        from modules.sextant.chain_steps import CHAIN_ROLE

        old = combo_key(self.task) if self.task.count() else None
        old_chain = self.task.currentData(CHAIN_ROLE) if self.task.count() else None
        tasks = inputs.tasks_for(kind)
        blocked = self.task.blockSignals(True)
        self.task.clear()
        for key in tasks:
            title = inputs.task_title(kind, key)  # CREST: «Поиск конформеров», its one task
            self.task.addItem(tr(title))
            self.task.setItemData(self.task.count() - 1, key, KEY_ROLE)
            if title != key:
                self.task.setItemData(self.task.count() - 1, title, TEXT_ROLE)
        # the chains the program can do, after a line;
        # their key is the task of their first step (the form and the input file shown are of that step)
        chains = [key for key in chain.PRESETS if chain.available(key, kind)]
        if chains:
            self.task.insertSeparator(self.task.count())
            for key in chains:
                title, steps = chain.PRESETS[key]
                self.task.addItem(tr('Цепочка: ' + title))
                self.task.setItemData(self.task.count() - 1, steps[0][0], KEY_ROLE)
                self.task.setItemData(self.task.count() - 1, 'Цепочка: ' + title, TEXT_ROLE)
                self.task.setItemData(self.task.count() - 1, key, CHAIN_ROLE)
        chosen = old if old in tasks else ('Оптимизация + частоты' if 'Оптимизация + частоты' in tasks else tasks[0])
        place = self.task.findData(old_chain, CHAIN_ROLE) if old_chain in chains else -1
        if place >= 0:
            self.task.setCurrentIndex(place)
        else:
            set_combo_key(self.task, chosen)
        self.task.blockSignals(blocked)
        if old is not None and old != chosen and hasattr(self, 'notify'):
            self.notify(tr(f'В {NAMES[kind]} нет задачи «{tr(old)}» — выбрана «{tr(chosen)}».'), 6000)
        self.update_task_box()
        self.show_chain_steps()
        return chosen

    def advanced_count(self):
        """How many advanced settings differ from the defaults (for the summary next to the button)."""
        default = Calculation()
        calc = self.calculation()
        names = ('scf', 'grid', 'no_ri', 'rijcosx', 'ts', 'opt_conv', 'max_cycles', 'calc_hessian', 'population', 'orbitals',
                 'states', 'temperature', 'pressure', 'extra', 'relativistic', 'slow_conv', 'auto_aux', 'num_freq',
                 'tddft_mode', 'triplets', 'root', 'raman', 'stability', 'element_basis', 'couplings')
        return sum(getattr(calc, n) != getattr(default, n) for n in names)

    def apply_calculation(self, calc, program=None, state_formula=None):
        """Put the settings of a tab (or a project) into the form without marking anything as changed; the
        input file is built once at the end."""
        widgets = (self.program, self.method, self.basis, self.task, self.charge, self.spin, self.cores, self.memory,
                   self.solvent, self.dispersion, self.scf_level, self.grid, self.no_ri, self.rijcosx, self.ts, self.opt_conv,
                   self.max_cycles, self.calc_hessian, self.population, self.orbitals, self.states, self.temperature,
                   self.pressure, self.calc_title, self.relativistic, self.slow_conv, self.auto_aux, self.num_freq,
                   self.tddft_mode, self.triplets, self.root, self.raman, self.couplings,
                   self.solvent_model, self.stability, self.scan_index, self.scan_end, self.scan_steps, self.nto,
                   self.scan2_index, self.scan2_end, self.scan2_steps)
        blocked = [w.blockSignals(True) for w in widgets]
        try:
            if program and self.program.findData(program) >= 0 and program != self.program_kind():
                self.program.setCurrentIndex(self.program.findData(program))
                self.apply_program()
            for widget, value in [(self.method, calc.method), (self.basis, calc.basis)]:
                index = widget.findData(value)
                if index >= 0:
                    widget.setCurrentIndex(index)
            set_combo_key(self.task, calc.task)
            for widget, value in [(self.solvent, calc.solvent), (self.dispersion, calc.dispersion)]:
                widget.setCurrentIndex(max(0, widget.findData(value)))
            for widget, value in [(self.charge, calc.charge), (self.spin, calc.multiplicity), (self.cores, calc.cores),
                                  (self.memory, calc.memory_mb)]:
                widget.setValue(value)
            self.apply_calculation_options(calc)
            self.calc_title.setText(getattr(calc, 'title', ''))
            if state_formula is not None:
                self._state_formula = state_formula
        finally:
            for w, was in zip(widgets, blocked):
                w.blockSignals(was)
        self.input_edited = False  # another tab or project — its own file
        for picker in (getattr(self, 'method_picker', None), getattr(self, 'basis_picker', None)):
            if picker is not None:
                picker.sync()
        self.update_dispersion()
        self.update_options_summary()
        self.input_tool.refresh_input()

    def apply_calculation_options(self, calc):
        """Put the advanced settings of a project into the dialog."""
        for combo, value in ((self.scf_level, calc.scf), (self.grid, calc.grid), (self.opt_conv, calc.opt_conv),
                             (self.population, calc.population), (self.relativistic, calc.relativistic),
                             (self.slow_conv, calc.slow_conv), (self.tddft_mode, calc.tddft_mode)):
            combo.setCurrentIndex(max(0, combo.findData(value)))
        for box, value in ((self.no_ri, calc.no_ri), (self.ts, calc.ts), (self.calc_hessian, calc.calc_hessian),
                           (self.orbitals, calc.orbitals), (self.rijcosx, calc.rijcosx), (self.auto_aux, calc.auto_aux),
                           (self.num_freq, calc.num_freq), (self.triplets, calc.triplets),
                           (self.raman, getattr(calc, 'raman', False)),
                           (self.couplings, getattr(calc, 'couplings', False)),
                           (self.stability, getattr(calc, 'stability', False)),
                           (self.nto, getattr(calc, 'nto', False))):
            box.setChecked(value)
        self.solvent_model.setCurrentIndex(max(0, self.solvent_model.findData(getattr(calc, 'solvent_model', 'cpcm'))))
        self.root.setValue(calc.root)
        self.max_cycles.setValue(calc.max_cycles)
        self.states.setValue(calc.states)
        self.temperature.setValue(calc.temperature)
        self.pressure.setValue(calc.pressure)
        self.scan_end.setValue(getattr(calc, 'scan_end', 0.0))
        self.scan_steps.setValue(getattr(calc, 'scan_steps', 10))
        self._scan_wanted = getattr(calc, 'scan_index', 0)  # chosen again when the list is filled (update_scan_list)
        self.scan2_end.setValue(getattr(calc, 'scan2_end', 0.0))
        self.scan2_steps.setValue(getattr(calc, 'scan2_steps', 5))
        self._scan2_wanted = getattr(calc, 'scan2_index', -1)
        self.guess.set_path(getattr(calc, 'guess', ''), quiet=True)
        self.cda_atoms.setText(getattr(calc, 'cda_atoms', ''))
        self.element_basis.setText(getattr(calc, 'element_basis', ''))
        self.cda_charge.setValue(getattr(calc, 'cda_charge', 0))
        self.cda_mult1.setValue(getattr(calc, 'cda_mult1', 1))
        self.cda_mult2.setValue(getattr(calc, 'cda_mult2', 1))
        self._extra = calc.extra  # the next refresh_input writes it (a project of an older version)
        self._isotopes = getattr(calc, 'isotopes', '')

    def apply_machine(self, probe=True):
        """Processes and memory per process advised for this computer (advice.recommended)."""
        m = advice.machine() if probe else None
        self.machine = m
        if m is None:
            self.cores.setToolTip(tr('Число процессов MPI (%pal, -P)'))
            self.memory.setToolTip(tr('Память на один процесс (%maxcore)'))
            return None
        processes, memory = advice.recommended(m)
        self.cores.setValue(processes)
        self.memory.setValue(memory)
        # what this computer has and what is advised — in the tooltips, next to the fields
        cores = tr(f'{m.physical} ядер') if m.physical else tr(f'{m.logical} потоков')
        ram = tr(f', {m.memory_mb / 1024:.0f} ГБ памяти') if m.memory_mb else ''
        self.cores.setToolTip(tr(f'Компьютер: {cores}{ram}. Рекомендуется процессов: {processes}'))
        self.memory.setToolTip(tr(f'Компьютер: {cores}{ram}. Рекомендуется на процесс: {memory} МБ'))
        return processes, memory

    follow_molecule_state = _molecule.follow_molecule_state
    molecule_state_changed = _molecule.molecule_state_changed
    add_element_basis = _molecule.add_element_basis
    cda_from_selection = _molecule.cda_from_selection
    cda_note = _molecule.cda_note
    interaction_note = _molecule.interaction_note
    calculation_molecule = _molecule.calculation_molecule
    calculation_constraints = _molecule.calculation_constraints

    def current_advice(self):
        try:
            mol = self.calculation_molecule()
        except ValueError:
            return None
        return advice.recommend(mol, combo_key(self.task), self.program_kind(), self.charge.value(), self.spin.value())

    def update_advice(self):
        """The method and the basis set advised for the task — tooltips of the pickers and their first item."""
        found = self.current_advice()
        self.advice = found
        if found is None:
            for picker in (self.method_picker, self.basis_picker):
                picker.recommended = None
                picker.setToolTip(
                    tr('xtb: метод GFN2-xTB — быстрая предварительная оценка геометрии и частот.') if self.program_kind() == 'xtb'
                    else tr('MOPAC: полуэмпирические методы — секунды даже для больших молекул; результат — теплота '
                            'образования, сравнивать её можно только с MOPAC тем же методом. PM7 — новейший.')
                    if self.program_kind() == 'mopac' else ''
                )
            return None
        disp = DISPERSION_NAMES.get(found.dispersion, '')
        method = found.method + (f' + {tr(disp)}' if found.dispersion else '')
        task = self.task.currentText()
        caveat = tr('Рекомендация — разумный учебный старт по правилам, а не гарантия для любой молекулы.')
        self.method_picker.recommended = (found.method, tr('Рекомендуется: ') + method, lambda: self.apply_advice(('method', 'dispersion')))
        # with a Hamiltonian (lanthanides, actinides) the advised basis brings it too
        basis = found.basis + (f' + {found.relativistic}' if found.relativistic else '')
        self.basis_picker.recommended = (found.basis, tr('Рекомендуется: ') + basis,
                                         (lambda: self.apply_advice(('basis',))) if found.relativistic else None)
        self.method_picker.setToolTip(tr(f'Для задачи «{task}» рекомендуется: {method}') + '\n' + found.text + '\n' + caveat)
        self.basis_picker.setToolTip(tr(f'Для задачи «{task}» рекомендуется: {basis}') + '\n' + caveat)
        return found

    # the fields of Calculation set by advice.task_settings and their widgets
    TASK_WIDGETS = {'scf': 'scf_level', 'grid': 'grid', 'opt_conv': 'opt_conv', 'calc_hessian': 'calc_hessian',
                    'num_freq': 'num_freq', 'tddft_mode': 'tddft_mode', 'triplets': 'triplets', 'root': 'root',
                    'states': 'states'}

    def task_chosen(self, *args):
        """The task chosen by the user brings the method, basis set and dispersion advised for it
        (advice.recommend) and its settings (advice.task_settings); a toast says what was set. Returns the advice or
        None (xtb: no choice; MOPAC: PM7 stays)."""
        task = combo_key(self.task)
        for key, value in advice.task_settings(task).items():
            widget = getattr(self, self.TASK_WIDGETS[key])
            if isinstance(widget, QComboBox):
                index = widget.findData(value)
                if index >= 0:
                    widget.setCurrentIndex(index)
            elif isinstance(widget, QCheckBox):
                widget.setChecked(bool(value))
            else:
                widget.setValue(value)
        self.update_advice()
        found = self.advice
        if found is not None:
            self.apply_advice()
            disp = DISPERSION_NAMES.get(found.dispersion, '')
            what = f'{found.method}/{found.basis}' + (f' + {tr(disp)}' if found.dispersion else '') + (
                f', {found.relativistic}' if found.relativistic else '')
            self.notify(tr(f'Для задачи «{tr(task)}»: {what} — рекомендация; метод и базис можно сменить.'), 8000)
        return found

    def apply_advice(self, parts=('method', 'basis', 'dispersion')):
        found = self.advice
        if found is None:
            return False
        if found.relativistic and 'basis' in parts:  # lanthanides, actinides — DKH2 with SARC (ORCA)
            self.relativistic.setCurrentIndex(max(0, self.relativistic.findData(found.relativistic)))
        for combo, value in ((self.method, found.method), (self.basis, found.basis), (self.dispersion, found.dispersion)):
            if (combo is self.method and 'method' not in parts or combo is self.basis and 'basis' not in parts
                    or combo is self.dispersion and 'dispersion' not in parts):
                continue
            index = combo.findData(value)
            if index >= 0:
                combo.setCurrentIndex(index)
        return True

    def program_changed(self, *args):
        kind = self.program.currentData()
        if kind in ('qe', 'cp2k'):  # a program of a crystal (a project of no kind yet) — a CIF is opened
            return self.crystal_mode_tool.crystal_program_chosen(kind, getattr(self, '_program_index', 0))
        self._program_index = self.program.currentIndex()
        if getattr(self, 'input_edited', False):  # the edited file was for the other program
            self.input_edited = False
            self.notify(tr('Правки входного файла сброшены: выбрана другая программа.'), 6000)
        self.preferences.setValue('sextant_program', self.program_kind())
        self.apply_program()
        self.run_tool.refresh_program_path()
        self.settings_changed()

    def apply_program(self):
        kind = self.program_kind()
        if hasattr(self, 'preview') and hasattr(self.preview, 'comment'):  # Ctrl+/ of the editor
            self.preview.comment = COMMENT_SIGNS.get(kind, '#')
            self.preview.set_language(kind)  # the colours of the input of the program
        self.fill_tasks(kind)  # only what the program can do
        self.update_solvent_model()
        if hasattr(self, 'main_form'):  # what the program does not take is not shown
            self.show_row(self.method_picker, kind != 'xtb')
            self.show_row(self.basis_picker, kind not in ('xtb', 'mopac'))
            self.show_row(self.dispersion, kind not in ('xtb', 'mopac'))
            for item in (self.memory, self.memory_times):
                item.setVisible(kind not in ('xtb', 'mopac'))
        if hasattr(self, 'guess'):  # in «Дополнительные настройки…» — ORCA only (MORead)
            self.guess.setEnabled(kind == 'orca')
            self.guess.setToolTip('' if kind == 'orca' else tr('Начальные орбитали прошлого расчёта — только для ORCA'))
        if kind != 'xtb':  # the methods and basis sets of this program; xtb keeps the last ones (off)
            default = DEFAULT_MOPAC_METHOD if kind == 'mopac' else DEFAULT_METHOD
            fill_grouped(self.method, methods_for(kind), METHOD_TABLE, self.method.currentData(), default)
            if kind != 'mopac':  # MOPAC has no basis set — the last one is kept (off), as for xtb
                fill_grouped(self.basis, bases_for(kind), BASIS_TABLE, self.basis.currentData(),
                             'cc-pVDZ' if kind == 'gamess' else DEFAULT_BASIS)  # GAMESS has no def2
        # xtb keeps the last method and MOPAC the last basis set (off) — but at a start with them chosen there
        # was no last one: the empty list was «Метод, базис или задача не поддерживаются» until another program was
        # chosen and back (the user's report); the lists of ORCA stand in, off
        if self.method.count() == 0:
            fill_grouped(self.method, methods_for('orca'), METHOD_TABLE, None, DEFAULT_METHOD)
        if self.basis.count() == 0:
            fill_grouped(self.basis, bases_for('orca'), BASIS_TABLE, None, DEFAULT_BASIS)
        for picker in (getattr(self, 'method_picker', None), getattr(self, 'basis_picker', None)):
            if picker is not None:
                picker.sync()  # the refill does not signal
        for item in (self.method, self.basis, self.memory):
            item.setEnabled(kind != 'xtb')  # GFN2-xTB: its own Hamiltonian, D4 included
        if kind == 'mopac':  # a method without a basis set; MOPAC takes no memory setting
            self.basis.setEnabled(False)
            self.memory.setEnabled(False)
        if hasattr(self, 'rijcosx'):
            self.rijcosx.setEnabled(kind == 'orca' and not self.no_ri.isChecked())
        if hasattr(self, 'auto_aux'):  # what the program does not know is grey
            self.auto_aux.setEnabled(kind == 'orca')
            self.raman.setEnabled(kind == 'orca')
            self.couplings.setEnabled(kind == 'orca')
            self.relativistic.setEnabled(kind in ('orca', 'gaussian'))
            self.slow_conv.setEnabled(kind not in ('xtb', 'mopac'))
            for item in (self.tddft_mode, self.triplets, self.root, self.num_freq):
                item.setEnabled(kind not in ('xtb', 'mopac'))  # nor in MOPAC
            for item in (self.tddft_mode, self.root, self.num_freq):  # not written for GAMESS, NWChem
                if kind in ('gamess', 'nwchem'):
                    item.setEnabled(False)
            if kind == 'gamess':
                self.triplets.setEnabled(False)
        self.update_dispersion()
        self.preview_title.setText(tr(TITLES[kind]))
        self.preview_notice.setText(tr(NOTICES[kind]))
        if hasattr(self, 'input_help_button'):
            from modules.sextant.workspace_texts import input_help

            self.input_help_button.setToolTip(input_help(NOTICES[kind]))
        self.preview.setReadOnly(kind == 'xtb')  # xtb: a command line and its files, not one input file

    def update_dispersion(self):
        """D3(BJ)/D4 only for a functional that takes it (core.DISPERSION_METHODS); off for xtb."""
        method = self.method.currentData() or self.method.currentText()
        fits = self.program_kind() != 'xtb' and method in DISPERSION_METHODS
        if self.program_kind() == 'orca':  # GFN2-xTB through ORCA has no basis set
            self.basis.setEnabled(method != XTB_ORCA)
            self.basis.setToolTip(tr('У GFN2-xTB нет базиса: это полуэмпирический метод со своим набором функций')
                                  if method == XTB_ORCA else '')
        self.dispersion.setEnabled(fits)
        self.dispersion.setToolTip(
            '' if fits else tr('Для этого метода поправка не добавляется: HF, MP2, своя дисперсия (ωB97X-D…) или нет параметров (M06-2X)')
        )

    update_scan_list = _scan.update_scan_list
    update_scan2_list = _scan.update_scan2_list
    scan2_coordinate_chosen = _scan.scan2_coordinate_chosen
    scan_coordinate_chosen = _scan.scan_coordinate_chosen

    def settings_changed(self, *args):
        self.dirty = True
        if hasattr(self, 'dispersion'):
            self.update_dispersion()
            self.update_options_summary()
        self.input_tool.refresh_input()
        self.coordinate_tool.refresh_coordinates()

    # running the program ------------------------------------------------------------------

    # «Проверить подключение» logs in (as the calculation does), shows the free cores and memory and then asks
    # the server again every SERVER_PING_S seconds over the same ssh connection, in the background; the mark follows
    SERVER_PING_S = 5.0
