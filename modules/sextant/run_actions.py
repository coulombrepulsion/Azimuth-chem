"""RunTool (window.run_tool, a part of the window with a PORT): running a calculation of Sextant — where it runs (this computer or a server), the program
found or chosen, the folder of the calculations, the start, the progress, the end and the result, the history of the
calculations, the installation of the tools. The calculation per place (job, batch, job_window …) stays on
SextantWorkspace (descriptors over its RunSlot)."""

from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog

from azimuth.core import CDA_TASK, FUKUI_TASK, INTERACTION_TASK, TASKS
from azimuth.i18n import combo_key, tr
from azimuth.runtime.places import PLACES  # defined with the run slots
from modules.sextant import remote, runner
from modules.sextant.inputs import NAMES
from modules.sextant.job_window import OutputWindow, subscript



class RunTool:
    """Was the mixin RunActions of the window; a part of its own — it reaches the window only through
    the names of PORT (azimuth/window_port.WindowPort)."""

    PORT = (
        '_job_cycles',
        '_job_done',
        '_job_seen',
        '_job_shown',
        '_show_job_card',
        'apply_machine',
        'at_place',
        'attempt_of_job',
        'batch_finished_here',
        'batch_plan',
        'batch_project_here',
        'batch_tool',
        'calculation',
        'calculation_constraints',
        'calculation_molecule',
        'choose_program_button',
        'coordinate_tool',
        'cores',
        'display_output',
        'doctor_tool',
        'document',
        'documents',
        'error',
        'folder_button',
        'follow_queue_window',
        'history_tool',
        'input_tool',
        'install_job',
        'install_tool',
        'job',
        'job_document',
        'job_follow',
        'job_listener',
        'job_place',
        'job_slot',
        'job_task',
        'job_timer',
        'job_window',
        'jobs_folder_button',
        'last_batch',
        'memory',
        'navigate',
        'notify',
        'open_project_molecule',
        'opening_tool',
        'output',
        'output_window',
        'preferences',
        'program',
        'program_kind',
        'program_tool',
        'read_result',
        'register_project_job',
        'research_document_path',
        'research_path',
        'result_target',
        'run_button',
        'run_spinner',
        'run_time',
        'server_watch_tool',
        'set_run_status',
        'sextant_shown',
        'show_job_window',
        'show_project_molecules',
        'spectral',
        'stop_button',
        'structure_tabs',
        'switch_document',
        'task',
        'trajectory_tool',
        'where',
        'where_buttons',
        'window',
    )

    # what the watching of the server knows lives in ServerWatchTool (server_watch_actions.py); read here
    _server_watch = property(lambda self: self.w.server_watch_tool.watch)
    server_resources = property(lambda self: self.w.server_watch_tool.resources)

    def __init__(self, window):
        from azimuth.window_port import WindowPort

        self.w = WindowPort(window, self.PORT)


    def configured_program(self, kind):
        return self.w.program_tool.configured_program(kind)  # in ProgramTool

    def refresh_program_path(self):
        return self.w.program_tool.refresh_program_path()  # in ProgramTool

    # where the calculation runs -------------------------------------------------------------------
    SERVER_ONLY = 'На сервере пока считаются только ORCA, MOPAC и xtb — {} считается на этом компьютере.'

    def set_where(self, where):
        where = 'server' if where == 'server' else 'local'
        if where == 'server' and self.w.has('program_kind'):
            # «Сервер» pressed for a program a server does not run yet (remote_job.REMOTE_KINDS): the place stays this
            # computer and the status line says why — nothing happened before (the owner's Windows, 2026-11-28: «пусть
            # хотя бы в строке состояния пишет, что эти программы не запускаются пока на сервере»)
            from modules.sextant.remote_job import REMOTE_KINDS

            kind = self.w.program_kind()
            if kind not in REMOTE_KINDS:
                self.w.set_run_status(tr(self.SERVER_ONLY).format(NAMES.get(kind, kind)))
                where = 'local'
        before = getattr(self.w, 'where', where)
        if before != where and self.w.has('job_slot'):
            # the calculation of the place left goes on; its panel leaves the place of the input file
            with self.w.at_place(before):
                jw = self.w.job_window
                if jw is not None and jw.docked:
                    jw.undock()
                    jw.hide()
        self.w.where = where
        self.watch_resource_fields()
        if before != where:  # the processes and memory follow the place: this computer, or the server
            self._server_advised = None
            if where == 'local':
                self._advising = True
                try:
                    self.w.apply_machine()
                finally:
                    self._advising = False
            else:
                self._fields_touched = False  # set by hand from now on — kept, the advice does not replace it
                known = getattr(self, 'server_resources', None)
                if known is not None and known[0] == remote.load(self.w.preferences).title():
                    self.apply_server_resources(remote.load(self.w.preferences), known[1])
        self.w.preferences.setValue(remote.WHERE_KEY, where)
        self.w.where_buttons[where].setChecked(True)
        self.fold_where()
        if self.w.has('job_slot'):
            running = self.run_blocked(where)  # a single calculation on the server does not hold them
            self.w.program.setEnabled(not running)
            self.w.choose_program_button.setEnabled(not running)
            if self.w._job_shown and self.w.sextant_shown():
                self.w.job_follow()
            else:
                self.w._show_job_card(False)
            self.w.run_time.setVisible(self.w.job is not None and bool(self.w.run_time.text()))
        self.refresh_program_path()
        self.w.input_tool.refresh_input()
        return where

    def fold_where(self):
        """Both places only as icons (the chosen one is marked; the names are in the tooltips) — by the wish of
        the user nothing in Sextant unfolds (until 0.71 the chosen place unfolded its name)."""
        for item in self.w.where_buttons.values():
            item.set_expanded(False, animate=False)

    def edit_server(self):
        return self.w.server_watch_tool.edit_server()  # the watching of the server is a part of its own

    def run_on_server(self, beside=False):
        """Open the server, ask what it has, choose the processes, send the calculation (see the header).
        Beside — a calculation runs there already: it is moved aside (its own window) once the new one is
        ready to be sent, not before (a refusal on the way leaves it where it was)."""

        from modules.sextant import cluster, remote_job, server_access

        profile = remote.load(self.w.preferences)
        if not profile.ready():
            self.edit_server()
            return None
        kind = self.w.program_kind()
        if kind not in remote_job.REMOTE_KINDS:  # ORCA, MOPAC, xtb
            self.w.error(tr('На сервере считаются ORCA, MOPAC и xtb — выберите одну из них.'))
            return None
        try:
            calc = self.w.calculation()
            edited = self.w.input_tool.edited_input()
            if edited is not None and not self.w.input_tool.check_edited_input(kind, edited):
                return None
            from azimuth.tasks import run_quietly

            self.w.run_button.setEnabled(False)
            self.w.run_spinner.start()
            try:
                opened = server_access.open_server(self.w.widget, profile, waiting=run_quietly)  # the spinner only
            finally:
                self.w.run_spinner.stop()
                self.w.input_tool.refresh_input()  # the button as it should be
            if opened is None:
                return None
            connection, resources = opened
            self.show_server_state(profile, resources)  # the mark next to the button tells it too
            setup = cluster.server_setup(profile, resources, kind)  # ValueError: the program is not found there
            # the processes and the memory of the panel
            # (advised for the server when it was chosen, apply_server_resources); a server without SLURM: free cores only
            chosen = cluster.server_plan(resources, self.w.cores.value(), self.w.memory.value(), profile.title())
            self.notify_server_plan(resources, chosen)
            spec = remote_job.prepare_remote(
                self.w.calculation_molecule(), calc, self.w.calculation_constraints(), self.jobs_root(), chosen, setup,
                neb=self.w.input_tool.neb_settings(), text=edited, kind=kind,
            )
            job = remote_job.RemoteJob(spec, profile, connection)
        except (ValueError, OSError) as exc:  # ssh.SshError is a ValueError: its message is for the user
            self.w.error(exc)
            return None
        calc = replace(calc, cores=chosen.processes, memory_mb=chosen.maxcore)
        if beside and self.job_running('server'):
            self.park_server_job()
            self.w.notify(tr('Предыдущий расчёт на сервере идёт дальше в своём окне; все такие окна — «Расчёт → Другие '
                             'расчёты на сервере».'), 10000)
        # the attempt is written into the project and the history before the job is sent
        self.job_started(job, calc, kind, edited, place=profile.title())
        return job.start()

    def choose_program(self, kind=None, path=None):
        return self.w.program_tool.choose_program(kind, path)  # in ProgramTool

    def forget_program(self, kind):
        return self.w.program_tool.forget_program(kind)  # in ProgramTool

    def jobs_root(self):
        if self.w.has('research_document_path') and self.w.research_document_path() is not None:
            return self.w.research_document_path().parent / 'calculations'
        saved = self.w.preferences.value('jobs_folder', '')
        if saved and not runner.latin_path(saved):  # Windows — chosen earlier, before the check
            if not getattr(self, '_latin_said', False):
                self._latin_said = True
                self.w.notify(tr('В пути папки расчётов есть не латинские буквы — программы расчёта на Windows не '
                               'открывают в ней файлы. Расчёты идут в ') + str(runner.default_jobs_root()), 12000)
            return runner.default_jobs_root()
        return Path(saved) if saved else runner.default_jobs_root()

    def update_jobs_folder_tip(self):
        if self.w.has('jobs_folder_button'):
            self.w.jobs_folder_button.setToolTip(tr('Папка для расчётов: ') + str(self.jobs_root()) + tr(' · щелчок — выбрать другую'))

    def choose_jobs_folder(self, path=None):
        """Where the folders of the calculations are made (the same as before until changed; kept)."""
        if path is None:
            start = self.jobs_root()
            path = QFileDialog.getExistingDirectory(self.w.widget, tr('Папка для расчётов'), str(start if start.exists() else Path.home()))
        if not path:
            return None
        if not runner.latin_path(path):
            self.w.notify(tr('Выберите папку с латинскими буквами в пути: ORCA, xtb и Gaussian на Windows не открывают '
                           'файлы в папке ') + str(path), 12000)
            return None
        self.w.preferences.setValue('jobs_folder', str(path))
        self.update_jobs_folder_tip()
        self.w.notify(tr('Новые расчёты будут в папке ') + str(path), 6000)
        return Path(path)

    def open_server_files(self):
        return self.w.server_watch_tool.open_server_files()

    def check_server(self):
        return self.w.server_watch_tool.check_server()

    def server_ping(self):
        return self.w.server_watch_tool.server_ping()

    def program_chosen(self, *args):
        return self.w.program_tool.program_chosen(*args)  # in ProgramTool

    def stop_server_watch(self):
        return self.w.server_watch_tool.stop_server_watch()

    def notify_server_plan(self, resources, chosen):
        """What may hold a job of these processes on the server — said in the line over the model, not asked."""
        from modules.sextant import cluster

        notes = []
        if chosen.physical_free == 0:
            notes.append(tr('Свободных ядер на сервере сейчас нет — расчёт встанет в очередь.'))
        elif chosen.processes > chosen.physical_free:
            notes.append(tr(f'Свободно {chosen.physical_free} ядер из {chosen.physical} — расчёт на {chosen.processes} '
                            'процессов подождёт в очереди.'))
        memory = cluster.free_memory(resources)
        if memory and chosen.processes * chosen.maxcore > memory:
            notes.append(tr(f'Памяти на сервере свободно {memory / 1024:.0f} ГБ, а просят '
                            f'{chosen.processes * chosen.maxcore / 1024:.0f} ГБ — уменьшите память на процесс.'))
        if resources.disk_free_mb is not None and resources.disk_free_mb < 20 * 1024:
            notes.append(tr('Мало места на диске сервера — временные файлы ORCA могут его заполнить.'))
        if notes:
            self.w.notify(' '.join(notes), 12000)
        return notes

    def watch_resource_fields(self):
        """A change of the processes or the memory that is not the advice (apply_machine, apply_server_resources) is the
        user's — the advice of the server does not replace it. The fields are watched from the start (not compared with
        their values at the switch to the server: a window started with the server chosen has no such values)."""
        if getattr(self, '_resource_watch', False) or not (self.w.has('cores') and self.w.has('memory')):
            return
        self._resource_watch = True
        for box in (self.w.cores, self.w.memory):
            box.valueChanged.connect(self._resource_edited)

    def _resource_edited(self, *_):
        if not getattr(self, '_advising', False):
            self._fields_touched = True

    def apply_server_resources(self, profile, resources):
        """The processes and the memory per process advised for the server (cluster.plan: the free cores,
        60 % of the free memory) put into the fields of the panel, as apply_machine does for this computer — once for a
        server chosen (the watching of the server does not overwrite what the user set afterwards)."""
        from modules.sextant import cluster

        if getattr(self.w, 'where', 'local') != 'server' or getattr(self, '_server_advised', None) == profile.title():
            return None
        self._server_advised = profile.title()
        self.watch_resource_fields()
        if getattr(self, '_fields_touched', False):
            return None  # set by hand while the server was chosen (also before it was ever switched to): kept
        advised = cluster.plan(resources)
        self._advising = True
        try:
            self.w.cores.setMaximum(max(self.w.cores.maximum(), advised.physical))
            self.w.cores.setValue(advised.processes)
            self.w.memory.setValue(advised.maxcore)
        finally:
            self._advising = False
        summary = cluster.summary(resources, advised, profile.title())
        self.w.cores.setToolTip(summary + '. ' + tr(f'Рекомендуется процессов: {advised.processes}'))
        self.w.memory.setToolTip(summary + '. ' + tr(f'Рекомендуется на процесс: {advised.maxcore} МБ'))
        return advised

    def show_server_state(self, profile, resources, error=''):
        return self.w.server_watch_tool.show_server_state(profile, resources, error)

    def job_running(self, place=None):
        if place is not None:
            with self.w.at_place(place):
                return self.job_running()
        job = getattr(self.w, 'job', None)
        return job is not None and job.running

    def can_park_server_job(self):
        """A single calculation going on on the server (not a queue) can be moved aside for the next one."""
        from azimuth.runtime.places import Slotted

        slot = Slotted.slots(self.w.widget).slot('server')
        job = slot.job
        return (job is not None and job.running and slot.batch is None and not slot.job_done
                and getattr(job, 'remote_dir', None) is not None)

    def park_server_job(self):
        """The calculation of the server goes on in its own window (its slot «server~N», its buttons act on it, its end
        is handled there — RunSlots.owner_of); the card of Sextant is free for the next one. Windows of parked
        calculations that are over and closed are forgotten."""
        from azimuth.runtime.places import Slotted
        from modules.sextant.job_window import JobWindow

        slots = Slotted.slots(self.w.widget)
        for old in slots.parked('server'):
            if old.job_done and old.job_window is not None and not old.job_window.isVisible():
                slots.drop(old.place)
                old.job_window.deleteLater()
        parked = slots.park('server')
        jw = parked.job_window
        hourglass = getattr(jw, 'on_parked', None)
        if jw is not None:
            jw.place = parked.place
            jw.on_parked = None  # the hourglass of the hub is of the calculation of the card
            if jw.docked:
                jw.undock()
            jw.show_window()
        with self.w.at_place('server'):
            self.w.job_window = JobWindow(self.w.widget)
            self.w.job_window.place = 'server'
            self.w.job_window.on_parked = hourglass
            self.w.job = None
        return parked

    def run_blocked(self, place=None):
        """A calculation of the place keeps «Запустить расчёт» from another one — on a server only a queue
        does: a single calculation there is moved aside into its own window for the next (park_server_job)."""
        place = place or getattr(self.w, 'where', 'local')
        if not self.job_running(place):
            return False
        return not (place == 'server' and self.can_park_server_job())

    def run_calculation(self):
        """Start the chosen program on the current molecule; returns the Job or None (message shown)."""
        beside = False
        if self.job_running():
            single = not getattr(self.w, 'batch_plan', None) and combo_key(self.w.task) not in (
                FUKUI_TASK, CDA_TASK, INTERACTION_TASK)
            beside = getattr(self.w, 'where', 'local') == 'server' and single and self.can_park_server_job()
            if not beside:
                self.w.notify(tr('Расчёт уже идёт: дождитесь его конца или остановите.') if getattr(
                    self.w, 'where', 'local') != 'server' else tr('На сервере идёт очередь расчётов: дождитесь её конца или '
                                                                  'остановите. Отдельные расчёты можно запускать один за '
                                                                  'другим, не дожидаясь.'), 8000)
                return None
        from azimuth.tasks import held

        # a local work of the window goes on — this computer waits for it; a server does not
        if getattr(self.w, 'where', 'local') != 'server' and held():
            return None
        if getattr(self.w, 'batch_plan', None):  # a queue is chosen — «Запустить очередь»
            return self.w.batch_tool.run_batch_plan()
        from modules.sextant.chain_steps import CHAIN_ROLE

        chained = self.w.task.currentData(CHAIN_ROLE)  # a chain chosen in «Задача» — all its steps
        if chained:
            return self.w.batch_tool.start_chain(chained)
        if combo_key(self.w.task) == FUKUI_TASK:  # three calculations as a queue
            return self.w.batch_tool.start_fukui()
        if combo_key(self.w.task) == CDA_TASK:  # the complex and its two fragments as a queue
            return self.w.batch_tool.start_cda()
        if combo_key(self.w.task) == INTERACTION_TASK:  # the pair, its parts and the ghosts as a queue
            return self.w.batch_tool.start_interaction()
        if not self.structure_ready():  # what ORCA would refuse is asked about before it is sent
            return None
        # a saddle is looked for from near a saddle — said at the start
        try:
            saddle = bool(getattr(self.w.calculation(), 'ts', False))
        except ValueError:
            saddle = False
        if saddle:
            self.w.notify(tr('Поиск переходного состояния: начинайте со структуры, близкой к седлу (вершина скана, '
                             'середина пути NEB). Из минимума — как у воды — он может не сойтись и за сотни циклов.'),
                          12000)
        if getattr(self.w, 'where', 'local') == 'server':
            return self.run_on_server(beside)
        kind = self.w.program_kind()
        program = self.refresh_program_path()
        try:
            if program is None:
                raise ValueError(
                    tr(f'{NAMES[kind]} не найдена. Укажите файл программы кнопкой «Указать…» (значок папки рядом с программой).')
                )
            calc = self.w.calculation()
            if kind == 'xtb':
                calc = replace(calc, dispersion='')
            edited = self.w.input_tool.edited_input()  # the file as edited, checked first
            if edited is not None and not self.w.input_tool.check_edited_input(kind, edited):
                return None
            if not runner.latin_path(program):  # a warning only — some builds still run
                self.w.notify(tr('Программа лежит в папке с не латинскими буквами в пути — на Windows она может не '
                               'найти свои части. Если расчёт не пойдёт, перенесите её, например, в C:\\ORCA.'), 12000)
            mpirun = runner.find_mpirun(program) if kind == 'orca' and calc.cores > 1 else None
            spec = runner.prepare(
                kind, program, self.w.calculation_molecule(), calc, self.w.calculation_constraints(), self.jobs_root(), mpirun=mpirun,
                neb=self.w.input_tool.neb_settings(), text=edited,
            )
            job = runner.Job(spec).start()
        except (ValueError, OSError) as exc:
            self.w.error(exc)
            return None
        return self.job_started(job, calc, kind, edited)

    def structure_ready(self):
        """«Проверить структуру» of Compass before a
        calculation is started — its errors (atoms on top of each other, a multiplicity the electrons do not allow)
        asked about: «Всё равно запустить?» (no by default); its remarks (! and ·) do not stop it. True — go on."""
        from modules.compass.chemistry import structure_check

        try:
            molecule, calc = self.w.calculation_molecule(), self.w.calculation()
            errors = [p for p in structure_check.check(molecule, calc.charge, calc.multiplicity) if p.level == 'error']
        except (ValueError, KeyError, TypeError, AttributeError):
            return True  # the check is a help: a structure it cannot read is the business of the program
        if not errors:
            return True
        from PySide6.QtWidgets import QMessageBox

        from azimuth import quill

        text = tr('Проверка структуры перед расчётом нашла ошибки — с ними расчёт, скорее всего, не пойдёт:') + '\n\n' + \
            '\n'.join('✕  ' + p.text for p in errors[:6]) + '\n\n' + tr('Всё равно запустить?')
        answer = quill.question(self.w.widget, tr('Проверка структуры'), text,
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                QMessageBox.StandardButton.No, 'calc-stopped',
                                labels={QMessageBox.StandardButton.Yes: tr('Запустить'),
                                        QMessageBox.StandardButton.No: tr('Исправить')})
        return answer == QMessageBox.StandardButton.Yes

    def job_started(self, job, calc, kind, edited, place=None, title=None, remember=True, quiet=False):
        """The window and the buttons for a job just started here or on a server (place: the name of the server).
        Title — of a calculation taken up from the history (not the molecule of the tab); remember — into the
        history of calculations. Quiet — the next calculation of a queue: the window is not brought up
        (follow_queue_window)."""
        was_visible = self.w.job_window.isVisible() and not self.w.job_window.docked
        self.w.job = job
        try:  # what the doctor of the calculation needs at its end — the settings and whether the file was hand-made
            job._calc, job._edited = calc, edited is not None
        except AttributeError:
            pass
        if self.w.has('register_project_job'):
            try:
                self.w.register_project_job(job, calc, kind, place)
            except (OSError, ValueError, KeyError, StopIteration) as exc:
                self.w.notify(tr('Расчёт запущен, но запись в проект не обновлена: ') + str(exc), 15000)
        self.w.batch_finished_here = False
        self.w.batch_project_here = ''
        if remember:
            self.remember_job(job, calc, kind, place)
        self.w._job_done = False
        self.w._job_seen = False
        self.w.job_task = calc.task
        self.w.job_document = self.w.document() if self.w.has('document') else None  # its result goes there
        self.w._job_cycles = None
        for item in (self.w.run_button, self.w.program, self.w.choose_program_button):
            item.setEnabled(False)
        self.w.stop_button.setEnabled(True)
        self.w.folder_button.setEnabled(True)
        # H₂O
        title = title or tr(f'Расчёт: {subscript(self.w.coordinate_tool.table_molecule().formula)} · {NAMES[kind]}')
        if place:
            title += ' · ' + place  # on a server
        what = tr(calc.task or combo_key(self.w.task)) + ('' if kind == 'xtb' else f' · {calc.method}' if kind == 'mopac'
                                               else f' · {calc.method}/{calc.basis}')
        if place:
            what += tr(f' · {calc.cores} проц. × {calc.memory_mb} МБ')
        if edited is not None:
            what += tr(' · файл изменён вручную')
        self.w.job_window.begin(title, what)  # the folder is behind «Папка расчёта»
        if self.w.output_window is not None and self.w.output_window.isVisible():
            self.open_output()  # the open output window follows the new calculation
        self.show_job_progress()
        follow = getattr(job, 'follow', None)
        if follow is not None:
            # the job of the quick xtb follows itself (CalculationTool.follow_quick) — the
            # pill over the model, the sign in the left panel elsewhere; RunTool keeps its names (the bound of the
            # architecture: tests/core/test_architecture_boundaries.py)
            follow(what)
        elif quiet:
            self.w.follow_queue_window(was_visible)
        else:
            self.w.show_job_window()
        self.w.job_timer.start()
        self.tell_job('running')  # the hourglass in the panel of the hub
        if not self.run_blocked(self.w.job_place()):  # on a server the next one can be started at once
            for item in (self.w.run_button, self.w.program, self.w.choose_program_button):
                item.setEnabled(True)
        return job

    # the history of calculations (history.py, history_dialog.py) ---------------------------------------
    def remember_job(self, job, calc, kind, place=None):
        return self.w.history_tool.remember_job(job, calc, kind, place)  # in HistoryTool

    def show_history(self):
        return self.w.history_tool.show_history()  # in HistoryTool

    def open_history_result(self, rec):
        return self.w.history_tool.open_history_result(rec)  # in HistoryTool

    def open_history_folder(self, rec):
        return self.w.history_tool.open_history_folder(rec)  # in HistoryTool

    def forget_history(self, rec):
        return self.w.history_tool.forget_history(rec)  # in HistoryTool

    def resume_history(self, rec, quiet=False):
        """«Проверить на сервере»: the watching of a calculation sent before is taken up (RemoteJob.resume). quiet
        (a project opened takes up its calculations on a server): the window of the calculation is not
        brought up — the sign of the hub follows it, as a queue does."""
        from modules.sextant import history, remote_job, server_access

        from azimuth.project_store import ProjectDatabaseError

        try:
            info = history.remote_info(rec)
        except ProjectDatabaseError as exc:  # said; the job is not taken up from a guess
            self.w.error(exc)
            return None
        profile = next((p for p in remote.load_all(self.w.preferences) if p.title() == rec.get('place')), None)
        if info is None or profile is None:
            self.w.error(tr('Не найдены сведения о расчёте на сервере (job.json) или профиль сервера «')
                       + str(rec.get('place', '')) + '».')
            return None
        beside = False
        with self.w.at_place('server'):
            if self.w.job is not None and self.w.job.running:
                if not self.can_park_server_job():  # a single one is moved aside, a queue is waited for
                    self.w.notify(tr('На сервере идёт очередь расчётов из этого окна — дождитесь её конца.'), 8000)
                    return None
                beside = True
        try:  # T09: a server that does not answer — the watching is taken up all the same and waits for it
            opened = server_access.open_for_watching(self.w.widget, profile)
        except ValueError as exc:
            self.w.error(exc)
            return None
        if opened is None:
            return None
        connection, _, why = opened
        if why:
            self.w.notify(tr(f'Сервер {profile.title()} сейчас не отвечает — слежу за расчётом и проверю его, как только '
                             'связь появится.'), 12000)
        if beside and self.job_running('server'):
            self.park_server_job()
        self.set_where('server')
        job = remote_job.RemoteJob.resume(rec['folder'], rec['output'], profile, connection, info).start()
        kind = rec.get('kind', 'orca')
        return self.job_started(job, history.calculation_of(rec), kind, None, place=profile.title(),
                                title=tr('Расчёт: ') + rec.get('title', ''), remember=False, quiet=quiet)

    def result_tab_of(self, job):
        """The tab the result of job goes to — for a calculation of a
        project the tab of the molecule of its attempt (found by the ids now; opened again when it was closed and its
        project is the active one), else the tab it was started from while it is open; None — a new tab."""
        from azimuth import projects

        project_id = molecule_id = None
        binding = getattr(job, '_research_link', None)
        if binding is not None:
            path, link = binding
            try:
                project_id, molecule_id = projects.Project.view(path).data['id'], link['molecule']
            except (OSError, ValueError, KeyError):
                project_id = molecule_id = None
        return self.tab_for(project_id, molecule_id, getattr(self.w, 'job_document', None))

    def tab_for(self, project_id, molecule_id, started=None):
        """The tab of the molecule (project id, molecule id) now — opened again when it was closed and its
        project is the active one; without ids, started while it is open; None — a new tab (delivery.result_tab)."""
        from azimuth import projects
        from azimuth.runtime.delivery import result_tab

        documents = list(self.w.documents) if self.w.has('documents') else []
        active = None
        try:
            current = self.w.research_path() if self.w.has('research_path') else None
            active = projects.Project.view(current).data['id'] if current else None
        except (OSError, ValueError, KeyError):
            active = None
        document, how = result_tab(documents, project_id, molecule_id, started, active)
        if how == 'open' and self.w.has('open_project_molecule'):
            try:
                document = self.w.open_project_molecule(molecule_id, stay=True)
            except (OSError, ValueError, KeyError):
                document = None
        return document

    def tell_job(self, state, spent=''):
        listener = getattr(self.w, 'job_listener', None)
        if listener is not None:
            listener(state, spent)

    def show_job_progress(self):
        job = self.w.job
        follower = getattr(self, '_job_progress', None)
        if follower is None or follower.spec is not job.spec:
            follower = self._job_progress = runner.OutputProgress(job.spec)  # only what was added
        cycles, energy, stages = follower.update()
        spent = runner.duration(job.elapsed())
        state = getattr(job, 'state', None)  # a calculation on a server — sending, in the queue, no connection
        if state in ('new', 'sending', 'queued', 'offline') and job.message:
            head = job.message
        elif state is not None:
            head = tr('Идёт расчёт на сервере')
        else:
            head = tr('Идёт расчёт')
        parts = [head + ' · ' + spent]
        if 'Opt' in TASKS[self.w.job_task]:
            parts.append(tr(f'циклов оптимизации: {cycles}'))
        if energy is not None:
            parts.append(tr(f'энергия {energy:.8f} Eh'))
        self.w.set_run_status(' · '.join(parts), spent)
        if follower.seen:
            when = runner.duration(job.elapsed())
            for key, name in stages:
                self.w.job_window.add_stage(key, tr(name), when)
        else:  # no output yet: the stages printed elsewhere (Gaussian, Psi4 write their messages apart)
            self.note_stages(job.stdout_text())

    def note_stages(self, text):
        """The stages passed (runner.milestones) appear in the window of the calculation as they come."""
        job = self.w.job
        when = runner.duration(job.elapsed())
        for key, name in runner.milestones(job.spec.kind, text):
            self.w.job_window.add_stage(key, tr(name), when)

    def open_broken_result(self, job, window):
        """A calculation that broke off (an error or «Стоп») with the steps it made — an optimization, a scan,
        an IRC: the output goes to the tab of the calculation as a result (its last geometry is the structure there, the
        steps in the panel ☰), «Перейти в Компас» of the window opens them (the user had to open the .out in Compass).
        Nothing is said when the output cannot be read or has no steps. True when the steps were opened."""
        path = Path(job.spec.output)
        try:
            text = path.read_text(encoding='utf-8', errors='replace')
            output = self.w.read_result(text, str(path))
        except (ValueError, OSError, IndexError, KeyError):
            return False
        steps = [s for s in (getattr(output, 'steps', ()) or ()) if getattr(s, 'geometry', None) is not None]
        scan = getattr(output, 'scan', None)
        if not steps and not (scan is not None and scan.points):
            return False
        self.w.result_target = self.result_tab_of(job)  # by the ids of its attempt
        try:
            self.w.display_output(text, path.name, False, str(path), output)
        except ValueError:
            return False
        finally:
            self.w.result_target = None
        window.show_results(compass=True, spectrum=False)
        return True

    def clear_history(self):
        return self.w.history_tool.clear_history()  # in HistoryTool

    def go_to_result(self, where):
        """«Перейти в Компас» / «Перейти в Спектр» of the window of the calculation."""
        if where == 'compass' and getattr(self.w, 'batch_finished_here', False):  # the conformers of a queue
            target = getattr(getattr(self.w, 'last_batch', None), 'document', None)
            if target is not None and target in getattr(self.w, 'documents', ()) and target is not self.w.document():
                self.w.switch_document(self.w.documents.index(target))
            self.w.navigate(0)
            self.w.structure_tabs.setCurrentIndex(0)
            self.w.trajectory_tool.set_trajectory_open(True, 'conformers')
        elif where == 'compass' and getattr(self.w, 'batch_project_here', ''):
            # a queue of the
            # molecules of a project — its project with the list of its molecules, their results are in them
            last = getattr(self.w, 'last_batch', None)
            if last is not None and self.w.has('batch_tool'):
                self.w.batch_tool.open_queue_project(last)
            self.w.navigate(0)
            if self.w.has('show_project_molecules'):
                self.w.show_project_molecules()
        elif where == 'compass':  # the drawer of the result opens on the page with something in it
            output = getattr(self.w, 'output', None)
            if output is not None and (output.steps or getattr(output, 'scan', None) is not None):
                self.w.opening_tool.show_trajectory_drawer()
            else:
                self.w.navigate(0)
        else:
            self.w.navigate(2)
        top = self.w.window()
        if top.isMinimized():
            top.showNormal()
        top.raise_()
        top.activateWindow()
        return where

    def poll_job(self):
        """Both places are followed; returns the code of the calculation of the place chosen when it is over."""
        from azimuth.runtime.places import Slotted

        going = False
        slots = Slotted.slots(self.w.widget)
        for place in slots.all_places(PLACES):  # and the calculations on the server moved aside
            slot = slots.slot(place)  # the run slot of each place, explicitly
            with self.w.at_place(slot.place):
                job = slot.job
                if job is None or slot.job_done:
                    continue
                if job.poll() is None:
                    self.show_job_progress()
                    going = True
                else:
                    self.finish_job(slot)
        if not going:
            self.w.job_timer.stop()
        job = self.w.job
        return None if job is None or not self.w._job_done else job.code

    def finish_job(self, slot=None):
        """The end of the calculation of a place. In the run slot of that calculation (slot, else the slot
        whose job is self.w.job — azimuth/runtime/places.RunSlots.owner_of), whichever place is chosen now."""
        from azimuth.runtime.places import Slotted

        slot = slot or Slotted.slots(self.w.widget).owner_of(self.w.job, self.w.job_place())
        with self.w.at_place(slot.place):
            return self._finish_job(slot)

    def _finish_job(self, slot):
        job = slot.job
        from azimuth.runtime.lifecycle import row_of

        # of a queue; a job of a row of it (by its folder), whatever row runs now
        if slot.batch is not None and job is not None and row_of(slot.batch, job) is not None:
            return self.w.batch_tool.batch_job_finished(job, slot)
        if slot.batch is not None and job is not None:
            from azimuth.runtime.lifecycle import inside

            if inside(getattr(slot.batch, 'folder', ''), getattr(job.spec, 'folder', '')):
                # a calculation of this queue that no row
                # owns now (the queue replaced, the row removed) — not taken for a single calculation, not for the
                # running row; said in errors.log
                from azimuth.runtime.provenance import note

                note('queue', f'{job.spec.folder}: the end of a calculation no row of the queue owns — not recorded')
                return getattr(job, 'code', None)
        finished_window = self.w.job_window  # the result may be shown later, when another place is chosen
        self.w._job_done = True
        text = job.text()
        spent = runner.duration(job.elapsed())
        self.note_stages(text or job.stdout_text())
        self.w.job_window.finish()
        self.w.stop_button.setEnabled(False)
        for item in (self.w.program, self.w.choose_program_button):
            item.setEnabled(True)
        # what the end means is decided apart, once
        # (azimuth/runtime/single_run.py: the state, the orbitals, the warnings, the records); here it is shown
        from azimuth.runtime import lifecycle
        from azimuth.runtime.single_run import SingleRun

        attempt = (self.w.attempt_of_job(job) if self.w.has('attempt_of_job') else None) or lifecycle.Attempt(
            job.spec.folder, job.spec.output, job.spec.kind)
        outcome = SingleRun(self.w.preferences).conclude(attempt, job, self.w.job_task)
        if 'project_not_updated' in outcome.warnings:
            self.w.notify(tr('Результат сохранён, но запись в проект не обновлена: ')
                          + outcome.notes['project_not_updated'], 15000)
        if outcome.state == 'stopped':
            self.w.job_window.show_picture('calc-stopped')
            self.tell_job('stopped', spent)
            self.w.set_run_status(tr(f'Расчёт остановлен через {spent}.'), spent)
            if 'open_steps' in outcome.actions and self.open_broken_result(job, finished_window):
                self.w.set_run_status(tr(f'Расчёт остановлен через {spent}. Сделанные шаги — во вкладке расчёта: '
                                       '«Перейти в Компас», последняя геометрия уже на модели.'), spent)
            self.w.doctor_tool.offer(job, text, 'stopped')  # «Продолжить с последней геометрии»
        elif outcome.state == 'finished':
            self.w.set_run_status(tr(f'Расчёт завершён за {spent}. Результат открыт; файлы — в папке расчёта.'), spent)
            # ORCA 6 ends «normally» also when the optimization ran out of cycles — said, not hidden
            if 'optimization_unconverged' in outcome.warnings:
                self.w.set_run_status(tr(f'Расчёт завершён за {spent}, но оптимизация не сошлась за отведённые циклы: '
                                       'увеличьте «Предел циклов» или начните с последней геометрии.'), spent)
                self.w.doctor_tool.offer(job, text)  # «Продолжить с последней геометрии…»
            else:  # a minimum with an imaginary frequency — «Сдвинуть по мнимой моде…»
                self.w.doctor_tool.offer(job, text, 'finished')
            if 'orbitals_not_made' in outcome.warnings:  # the orbitals from the .gbw (orca_2mkl)
                self.w.notify(outcome.notes['orbitals_not_made'], 10000)
            self.w.result_target = self.result_tab_of(job)  # the tab of its attempt (the tab it started from)
            # the result goes to its tab, but the section does not change by itself (the user may be reading
            # the Atlas with the window hidden) — «Перейти в Компас» / «Перейти в Спектр» of the window take him there
            def shown():
                # where the result can be looked at; the result is in its tab of all three sections,
                # Spectrum when it has vibrations or spectra (documents.spectral), otherwise Compass. After it is
                # shown — a big output is read in the background
                output = getattr(self.w, 'output', None)
                spectral = output is not None and self.w.spectral(output)
                finished_window.show_results(compass=True, spectrum=spectral)  # of the place that finished
                finished_window.show_picture('calc-done')
                self.tell_job('done', spent)

            self.w.opening_tool.open_example_path(outcome.result, go=False, done=shown)  # a NEB run — its path
            self.w.result_target = None
        else:  # 'failed', or 'uncertain' — the sending not known: said, never sent again
            self.w.job_window.show_picture('calc-failed')
            self.w.job_window.show_problems(list(outcome.problems))
            if outcome.state == 'failed':  # the remedy the doctor knows, as one button
                self.w.doctor_tool.offer(job, text or job.stdout_text())
            self.tell_job('failed', spent)
            server_note = getattr(job, 'message', '') if getattr(job, 'state', None) in ('failed', 'uncertain') else ''
            stepped = 'open_steps' in outcome.actions and self.open_broken_result(job, finished_window)
            self.w.set_run_status(
                (tr('На сервере: ') + server_note + ' ' if server_note else '') + tr(
                    f'Программа завершилась с ошибкой (код {job.code}) через {spent}. Что случилось — в конце вывода («Вывод программы»).'
                ) + (' ' + tr('Сделанные шаги — во вкладке расчёта: «Перейти в Компас», последняя геометрия уже на модели.')
                     if stepped else ''),
                spent,
            )
        self.w.input_tool.refresh_input()
        return job.code

    # installing Open MPI, xtb, CREST into .tools/calc (install_tools.py) -----------------------
    def install_tools_dialog(self, packages=None, chosen=None):
        return self.w.install_tool.install_tools_dialog(packages, chosen)  # in InstallTool

    def start_install(self, packages):
        return self.w.install_tool.start_install(packages)  # in InstallTool

    def poll_install(self):
        return self.w.install_tool.poll_install()  # in InstallTool

    def _start_install(self, packages):
        return self.w.install_tool._start_install(packages)  # in InstallTool

    def _poll_install(self):
        return self.w.install_tool._poll_install()  # in InstallTool

    def stop_calculation(self):
        if self.w.batch_tool.stop_batch():  # «Остановить» in a queue stops the queue
            return
        if self.job_running():
            self.w.job.stop()
            self.w.set_run_status(tr('Останавливаю расчёт…'))

    def open_job_folder(self):
        job = getattr(self.w, 'job', None)
        folder = job.spec.folder if job is not None else self.jobs_root()
        folder.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def open_output(self):
        """«Вывод программы»: the output file of the calculation (or of the installation), followed as it grows."""
        job = self.w.install_job if getattr(self.w, 'install_job', None) is not None else getattr(self.w, 'job', None)
        # an installation that has ended — its log while no calculation was started after it: «Установка не удалась…
        # в «Вывод программы»» answered «Вывода ещё нет» (Windows check 2026-11-24)
        ended = getattr(self.w.install_tool, 'last', None)
        if ended is not None and getattr(self.w, 'install_job', None) is None and (
                job is None or (getattr(job, 'started', None) or 0) < (getattr(ended, 'started', None) or 0)):
            job = ended
        if job is None:
            self.w.notify(tr('Вывода ещё нет: запустите расчёт.'), 5000)
            return None
        if self.w.output_window is None:
            self.w.output_window = OutputWindow(self.w.widget)
        return self.w.output_window.watch((job.spec.output, job.spec.stdout))
