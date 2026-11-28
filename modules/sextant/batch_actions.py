"""Sextant: a queue of calculations for the set of the drawer of Compass (conformers, the structures of a project), and
the series built on queues — Fukui functions, CDA. The pure part: batch.py; a queue on a server: batch_server.py.

§1 PURPOSE
    When the tab has conformers (after a search) or a set of structures, the card of the input file has «Очередь
    расчётов для набора…»: BatchDialog lists them with ΔE, the lowest within 3 kcal/mol checked (batch.default_count),
    «Сколько» checks the first N. The dialog only chooses: the card of the calculation then shows the queue chosen (a band
    «Очередь: N из M · <source>» with «Изменить выбор…» and ✕, the button «Запустить очередь (N)»), the settings can
    still be changed, the button starts it; the choice is forgotten when the rows of the drawer change.
§2 ALGORITHM
    The settings of Sextant are the same for every item; the charge and the multiplicity are those of the tab for
    conformers, guessed from the bonds of each structure of a set (advice.guess_state); an input file edited by hand is
    not used (said). On this computer the items run one after another; a failure does not stop the queue; «Пропустить»
    stops the current one, «Остановить» the queue. The window of the calculation lists them (✓ done, ✗ failed, ▶
    running, · waiting, ⇡ sent) with the reason of a failure (BatchItem.note). At the end: batch_energies.csv in
    «Анализ» of the folder of the queue (E, G with frequencies, ΔE or ΔG, the Boltzmann shares, ΔE of the search) and the
    final geometries on the page «Конформеры» of the drawer, sorted by the new energies. A queue left by closing the
    program is in batch.json of its folder; «Продолжить очередь» takes it up.
    On a server (batch_server.py): the server is opened and the processes asked once (kept in extra['plan']); the queue
    is sent at once — every calculation uploaded, one SLURM job (batch.sh) runs them one after another and leaves
    markers in their folders, Sextant watches them one by one (remote_batch.send_batch, BatchItemJob); a queue that
    searches conformers first is sent item by item, and at the exit «Отправить и выйти» sends what is left, each waiting
    for the one before (remote_job.submit with afterany). At the next start the queue is taken up (unfinished.py),
    nothing is sent again; «Остановить» takes the sent ones off the queue of the server (scancel).
§3 APPLICATIONS modules/sextant/workspace.py (the button, finish_job), modules/sextant/job_window.py (show_batch).
§4 SPECIFICATION BatchDialog(parent, title, rows [(name, ΔE | None)]); .count (QSpinBox), .listing; chosen() -> [index].
    BatchTool (window.batch_tool, a part of the window with a PORT): batch_source() -> (source, [(name, Molecule, ΔE,
    charge, multiplicity)]); open_batch_dialog() -> plan | None; set_batch_plan(indices), clear_batch_plan(),
    show_batch_plan() -> bool, run_batch_plan(); start_batch(indices, place=None) -> Batch | None; start_fukui(place=None)
    -> Batch | None (the task «Функции Фукуи»); fukui_complete(queue) -> bool; start_cda(place=None) -> Batch | None,
    cda_complete(queue) -> bool (the task «CDA»); start_next_batch_item() -> job | None (first takes up the watching of
    an item left running on the server); batch_job_finished(job) -> code; skip_batch_item(); batch_complete() ->
    [Path]; resume_batch(folder=None); batch_qtaim_ready(queue) -> bool; batch_qtaim(folder=None, choose=False) ->
    [Path] (modules/spectrum/wavefunction/batch_qtaim.py); update_batch_buttons().
§7 TESTS tests/sextant/test_batch.py (pure); tests/gui/test_gui_sextant.py (the queue of conformers).
"""

from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QDialog, QHBoxLayout

from azimuth.i18n import tr
from modules.sextant import batch as batches
from modules.sextant.batch_dialog import BatchDialog
from modules.sextant import batch_server as _server
from modules.sextant import batch_results as _results
from modules.sextant.batch_results import OPEN_KEY
from modules.sextant import batch_tasks as _tasks


class BatchTool:
    """Was the mixin BatchActions of the window; a part of its own — it reaches the window only through
    the names of PORT (azimuth/window_port.WindowPort)."""

    PORT = (
        'chain_steps',
        '_batch_browser',
        '_job_done',
        '_project_batch_source',
        'activate_project_tab',
        'apply_calculation',
        'at_place',
        'batch',
        'batch_banner',
        'batch_banner_text',
        'batch_button',
        'batch_finished_here',
        'batch_plan',
        'batch_project_here',
        'bind_project_batch',
        'calculation',
        'calculation_molecule',
        'charge',
        'choose_program_button',
        'compass_mode',
        'cores',
        'crystal_tool',
        'document',
        'documents',
        'drawer',
        'error',
        'follow_queue_window',
        'input_tool',
        'job',
        'job_place',
        'job_window',
        'last_batch',
        'memory',
        'navigate',
        'new_document',
        'new_project_tab',
        'notify',
        'open_output_path',
        'open_project_molecule',
        'open_research_project',
        'opening_tool',
        'preferences',
        'program',
        'program_kind',
        'project_plan_changed',
        'project_queue_row_ended',
        'project_session',
        'project_sessions',
        'property_tool',
        'refresh_project_navigation',
        'research_document_path',
        'research_path',
        'resume_batch_button',
        'run_button',
        'run_tool',
        'save_research_project',
        'set_run_status',
        'show_job_window',
        'show_project_molecules',
        'spin',
        'stop_button',
        'trajectory_tool',
        'where',
    )

    def __init__(self, window):
        from azimuth.window_port import WindowPort

        self.w = WindowPort(window, self.PORT)


    # -- what can be queued ------------------------------------------------------------------------------------------
    def batch_source(self):
        """(source, rows): the conformers of the drawer (the charge and the multiplicity of the tab) or the molecules of
        the project (a set of structures is a project)."""
        drawer = getattr(self.w, 'drawer', None)
        # the conformers kept in the project (loaded on the page from it) are already molecules of the project
        conformer_page = (drawer is not None and drawer.page() == 'conformers' and len(drawer.conformers) > 1
                          and not getattr(drawer, 'conformers_project', None))
        self.w._project_batch_source = False
        if self.w.has('research_document_path') and self.w.research_document_path() and not conformer_page:
            name, rows, records, flat = self.project_batch_rows()
            if len(rows) > 1:
                self.w._project_batch_source = True
                self._project_batch_records = records
                self._project_batch_flat = flat
                return name, rows
        drawer = getattr(self.w, 'drawer', None)
        conformers = tuple(getattr(drawer, 'conformers', ()) or ())
        if len(conformers) > 1 and not getattr(drawer, 'conformers_project', None):
            charge, multiplicity = self.w.charge.value(), self.w.spin.value()
            rows = [(tr(f'Конформер {k}'), molecule, delta, charge, multiplicity)
                    for k, (molecule, energy, delta, share) in enumerate(conformers, 1)]
            return getattr(drawer, 'conformer_source', '') or tr('конформеры'), rows
        return '', []

    def project_batch_rows(self):
        """(name, rows, records, flat) of the molecules of the project a queue takes (projects.queueable) —
        read again only when project.qcc changed (it was read and parsed whole at every refresh of the card); the same
        Molecule objects meanwhile, so the choice of a queue and its records keep their identity."""
        # read from the session of the project — its working state, the edits not saved included
        path = self.w.research_path()
        session = self.w.project_session(path)
        from azimuth import projects as project_files

        key = (str(path), project_files.stamp(path), session.working_key())  # the generation of the database
        cached = getattr(self, '_project_rows_cache', None)
        if cached is not None and cached[0] == key:
            return cached[1]
        rows, records, flat = [], [], []
        for _, name, state, props, is_flat in session.queue_view():
            calc = state.calc
            rows.append((name, state.molecule, None, calc.charge, calc.multiplicity))
            records.append((state.molecule, props, tuple(state.formal)))
            if is_flat:
                flat.append(state.molecule)
        found = (session.name, rows, records, tuple(flat))
        self._project_rows_cache = (key, found)
        return found

    def structure_record(self, document, molecule):
        """(the data items of its file, its formal charges per atom) of a molecule of the set — of the
        project (the records kept with its rows); ({}, ()) for another molecule. document — kept for the callers."""
        records = list(getattr(self, '_project_batch_records', ()))
        if self.w.has('research_document_path') and self.w.research_document_path():
            records += list(self.project_batch_rows()[2])
        for m, props, formal in records:
            if m is molecule:
                return dict(props), tuple(formal)
        return {}, ()

    def structure_rows(self):
        """[(Molecule, name)] — the molecules of the project of the tab a set is made of (the inputs of the
        set, «Сохранить все»), the same objects as the rows of its queue; [] outside a project."""
        if not (self.w.has('research_document_path') and self.w.research_document_path()):
            return []
        return [(molecule, name) for name, molecule, *_ in self.project_batch_rows()[1]]

    def show_saved_batches(self, folder=None):
        """Open a saved package for inspection, without submitting or resuming any calculation."""
        from modules.sextant.batch_browser import BatchBrowser

        dialog = BatchBrowser(self.w.widget, folder)
        self.w._batch_browser = dialog
        dialog.show()
        return dialog

    def batch_structures_to_compass(self, queue):
        """Completed geometries in original order, names/charge/spin preserved; no energy ranking or H completion.

        They open as a new project (its tab and list), with the data items and the formal charges of each
        record; the old manifest is never edited, the current tab is not touched. Failed or geometry-less results are
        left out explicitly."""
        from azimuth import projects

        items = [item for item in queue.items if item.state == 'done' and item.geometry is not None]
        if not items:
            return 0
        if getattr(self.w, 'compass_mode', 'molecule') == 'crystal':
            self.w.crystal_tool.set_compass_mode('molecule')
        path = self.w.new_project_tab(tr('Пакет · ') + queue.folder.name)
        with projects.edit(path) as project:
            for item in items:
                calc = replace(queue.calc, charge=item.charge, multiplicity=item.multiplicity)
                entry = project.add(replace(item.geometry, title=item.name), calc, queue.kind, item.name)
                entry.update(props={k: v for k, v in item.props.items() if k not in ('role', 'task', 'ghosts')},
                             formal=list(item.formal))
            first = project.molecules[0]['id']
        self.w.open_project_molecule(first)
        self.w.refresh_project_navigation()
        self.w.show_project_molecules()
        self.w.input_tool.refresh_input()
        self.w.notify(tr(f'Открыто готовых структур: {len(items)} из {len(queue.items)}. '
                       'Для нового расчёта выберите программу и очередь в Секстанте.'), 10000)
        return len(items)

    def batch_input_to_compass(self, queue, index):
        """Open one original structure in a fresh editable tab with its saved settings, charge and spin.

        No hydrogen completion, result substitution, write to the old package or calculation launch occurs.
        The user can fix the geometry here, then select this tab as the source in the retry editor.
        """
        if type(index) is not int or not 0 <= index < len(queue.items):
            raise ValueError(tr('Неверный номер структуры.'))
        item = queue.items[index]
        if getattr(self.w, 'compass_mode', 'molecule') == 'crystal':
            self.w.crystal_tool.set_compass_mode('molecule')
        document = self.w.new_document(item.name, replace(item.molecule, title=item.name))
        calc = replace(queue.calc, charge=item.charge, multiplicity=item.multiplicity, title=item.name)
        self.w.apply_calculation(calc, queue.kind, item.molecule.formula)
        self.w.navigate(0)
        return document

    def batch_origin(self):
        """The rows the queue is chosen from (the same object while they are not replaced): the conformers of the drawer
        when its page shows them, else the molecules of the project (as batch_source)."""
        drawer = getattr(self.w, 'drawer', None)
        conformers = getattr(drawer, 'conformers', ()) or ()
        if drawer is not None and drawer.page() == 'conformers' and len(conformers) > 1:
            return conformers
        if self.w.has('research_document_path') and self.w.research_document_path():
            _, rows, _, _ = self.project_batch_rows()  # cached by the state of project.qcc
            key = (str(self.w.research_path()), tuple(id(row[1]) for row in rows))
            if getattr(self, '_project_batch_key', None) != key:
                self._project_batch_key, self._project_batch_origin = key, object()
            return self._project_batch_origin
        return conformers if len(conformers) > 1 else ()

    # -- the queue chosen (the dialog chooses, «Запустить очередь» starts) -------------------------------------
    def build_batch_banner(self):
        from PySide6.QtWidgets import QFrame

        from azimuth.ui import icon_button, label

        frame = QFrame()
        frame.setObjectName('queueBanner')
        row = QHBoxLayout(frame)
        row.setContentsMargins(10, 6, 6, 6)
        row.setSpacing(8)
        self.w.batch_banner_text = label('', 'subtitle')
        self.w.batch_banner_text.setWordWrap(True)
        row.addWidget(self.w.batch_banner_text, 1)
        self.batch_change_button = icon_button(tr('Изменить выбор…'), lambda: self.open_batch_dialog(), 'queue')
        row.addWidget(self.batch_change_button, 0, Qt.AlignmentFlag.AlignVCenter)
        self.batch_cancel_button = icon_button(tr('Отменить очередь — один расчёт этой структуры'),
                                               lambda: self.clear_batch_plan(), 'close')
        row.addWidget(self.batch_cancel_button, 0, Qt.AlignmentFlag.AlignVCenter)
        frame.hide()
        return frame

    def set_batch_plan(self, indices, binding=None):
        source, rows = self.batch_source()
        indices = [k for k in indices if 0 <= k < len(rows)]
        self.w.batch_plan = {'origin': self.batch_origin(), 'source': source, 'indices': indices,
                           'names': [rows[k][0] for k in indices], 'total': len(rows),
                           'binding': binding} if indices else None
        if getattr(self.w, '_project_batch_source', False) and self.w.has('project_plan_changed'):
            self.w.project_plan_changed(indices)  # the ticks of the list of the project follow the dialog
        self.show_batch_plan()
        return self.w.batch_plan

    def clear_batch_plan(self):
        self.w.batch_plan = None
        self.show_batch_plan()

    def show_batch_plan(self):
        """The card of the calculation tells the queue chosen: the band «Очередь: …», the button «Запустить очередь (N)»,
        the icon of the queue pressed."""
        plan = getattr(self.w, 'batch_plan', None)
        if plan is not None and plan['origin'] is not self.batch_origin():  # another search, another tab: forgotten
            plan = self.w.batch_plan = None
        n = len(plan['indices']) if plan else 0
        running = self.running_here()
        if running is not None and self.w.has('batch_banner'):
            # the queue that runs here, nothing to start
            counts = running.counts()
            k = next((i for i, item in enumerate(running.items, 1) if item.state in ('running', 'searching', 'sent')),
                     counts['done'])
            text = tr(f'Идёт очередь: {k} из {len(running.items)} · готово {counts["done"]}')
            if counts.get('failed'):
                text += tr(f' · ошибок {counts["failed"]}')
            self.w.batch_banner_text.setText(text + tr(' · новую очередь можно выбрать, когда эта закончится'))
            self.w.batch_banner.setVisible(True)
            for item in (self.batch_change_button, self.batch_cancel_button):
                item.hide()
            if self.w.has('run_button'):
                self.w.run_button.setText(tr('Идёт очередь…'))
            return False
        for item in (getattr(self, 'batch_change_button', None), getattr(self, 'batch_cancel_button', None)):
            if item is not None:
                item.show()
        if self.w.has('batch_banner'):
            self.w.batch_banner.setVisible(bool(plan))
            if plan:
                names = ', '.join(plan['names'][:4]) + (' …' if n > 4 else '')
                text = tr(f'Очередь: {n} из {plan["total"]} · {plan["source"]} — одни настройки, по одному. {names}')
                if plan.get('binding'):
                    from modules.sextant.binding import ion_name

                    b = plan['binding']
                    text += tr(f' · с ионом {ion_name(b["ion"], b["charge"])}: ион, лиганды и комплексы') + (
                        tr(' + BSSE') if b.get('bsse') else '')
                self.w.batch_banner_text.setText(text)
        if self.w.has('batch_button'):
            self.w.batch_button.setChecked(bool(plan))
        if self.w.has('run_button'):
            self.w.run_button.setText(tr(f'Запустить очередь ({n})') if plan else tr('Запустить расчёт'))
        return bool(plan)

    def running_here(self):
        """The queue that runs at the place chosen now (None: none)."""
        try:
            queue = self._batch_runs().get(getattr(self.w, 'where', 'local'))
        except Exception:  # noqa: BLE001 — the window before its run slots are made
            return None
        return queue if queue is not None and not queue.done() else None

    def run_batch_plan(self):
        plan = getattr(self.w, 'batch_plan', None)
        if not plan:
            return None
        queue = self.start_batch(plan['indices'], binding=plan.get('binding'))
        if queue is not None:
            self.clear_batch_plan()
        return queue

    def update_batch_buttons(self):
        if not self.w.has('batch_button'):
            return
        source, rows = self.batch_source()
        self.w.batch_button.setVisible(len(rows) > 1)
        self.show_batch_plan()
        self.w.batch_button.setToolTip(tr(f'Очередь расчётов для набора ({len(rows)}): одни настройки, по одному'))
        folder = self.w.preferences.value(OPEN_KEY, '') if self.w.has('preferences') else ''
        waiting = 0
        if folder and (Path(folder) / batches.FILE).is_file():
            try:
                waiting = batches.Batch.load(folder).counts()['waiting']
            except (OSError, ValueError, KeyError):
                waiting = 0
        running = any(self._batch_runs().get(place) for place in ('local', 'server'))
        self.w.resume_batch_button.setVisible(waiting > 0 and not running)
        self.w.resume_batch_button.setToolTip(tr(f'Продолжить очередь: осталось {waiting}'))

    def open_batch_dialog(self):
        source, rows = self.batch_source()
        if len(rows) < 2:
            self.w.notify(tr('Набора нет: найдите конформеры или откройте в Компасе несколько структур.'), 8000)
            self.show_batch_plan()
            return None
        if self.w.run_tool.job_running():
            self.w.notify(tr('Здесь уже идёт расчёт: дождитесь его конца или остановите.'), 6000)
            self.show_batch_plan()
            return None
        plan = getattr(self.w, 'batch_plan', None)
        conformers = len(getattr(getattr(self.w, 'drawer', None), 'conformers', ()) or ()) > 1
        what = tr('Конформеры') if conformers else tr('Структуры')
        binding = None
        flat = ()
        if not conformers:  # a set of ligands — «Комплексы с ионом»
            binding = {'orca': self.w.program_kind() == 'orca', 'chosen': plan.get('binding') if plan else None}
            document = self.w.document() if self.w.has('document') else None
            flagged = {id(m) for m in (getattr(self, '_project_batch_flat', ()) if getattr(self.w, '_project_batch_source', False)
                                      else getattr(document, 'structure_flat', ()))}
            flat = [k for k, row in enumerate(rows) if id(row[1]) in flagged]
        dialog = BatchDialog(self.w.widget, f'{what}: {len(rows)} · {source}', [(name, delta) for name, _, delta, _, _ in rows],
                             plan['indices'] if plan else None, binding, flat)
        accepted = dialog.exec() == QDialog.DialogCode.Accepted
        if not accepted:
            self.show_batch_plan()  # the icon as it was
            return None
        plan = self.set_batch_plan(dialog.chosen(), dialog.binding())
        if plan:
            self.w.notify(tr(f'Очередь выбрана: {len(plan["indices"])}. Проверьте настройки и нажмите «Запустить очередь».'), 8000)
        return plan

    # -- the queue ------------------------------------------------------------------------------------------------------
    def _batch_runs(self):
        """The queue of each place: {place: queue} — read from the run slots (azimuth/runtime/places.py)."""
        from azimuth.runtime.places import Slotted

        slots = Slotted.slots(self.w.widget)
        return {place: slots.slot(place).batch for place in slots.places()}

    def run_without_edit(self, why):
        """The file edited by hand does not go into a queue, a chain or the files of a plan (they are made
        by the settings) — said before the start, not in a passing notice: True — start without the edit."""
        from PySide6.QtWidgets import QMessageBox

        from azimuth import quill

        answer = quill.question(self.w.widget, tr('Правка входного файла не войдёт в расчёт'),
                                why + ' ' + tr('Запустить по настройкам или вернуться и перенести правку в настройки?'),
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                                QMessageBox.StandardButton.Cancel, 'input-check',
                                {QMessageBox.StandardButton.Yes: tr('Запустить по настройкам')})
        return answer == QMessageBox.StandardButton.Yes

    def start_batch(self, indices, place=None, binding=None):
        """The chosen rows of batch_source as a queue at the place chosen (or place); the first job is started."""

        place = place or getattr(self.w, 'where', 'local')
        if self.w.has('research_path') and self.w.research_path():
            self.w.save_research_project()
        source, rows = self.batch_source()
        project_source = getattr(self.w, '_project_batch_source', False)
        chosen = [rows[k] for k in indices if 0 <= k < len(rows)]
        if not chosen:
            return None
        if self.w.run_tool.job_running(place):
            self.w.notify(tr('Здесь уже идёт расчёт: дождитесь его конца или остановите.'), 6000)
            return None
        kind = self.w.program_kind()
        from modules.sextant.remote_job import REMOTE_KINDS

        if place == 'server' and kind not in REMOTE_KINDS:  # MOPAC too
            self.w.error(tr('На сервере считаются ORCA и MOPAC — выберите одну из них.'))
            return None
        try:
            calc = self.w.calculation()
            if kind == 'xtb':
                calc = replace(calc, dispersion='')
            if self.w.input_tool.edited_input() is not None and not self.run_without_edit(tr('Входной файл, исправленный вручную, в очередь не идёт: файлы собираются по настройкам.')):
                return None
            folder = batches.batch_folder(self.w.run_tool.jobs_root(), chosen[0][1], kind)
        except (ValueError, OSError) as exc:
            self.w.error(exc)
            return None
        document = self.w.document() if self.w.has('document') else None
        if binding:  # the ion, each ligand and its complex
            from modules.sextant import binding as binding_

            ligands = [(name, molecule, charge, multiplicity, *self.structure_record(document, molecule))
                       for name, molecule, delta, charge, multiplicity in chosen]
            try:
                items, extra = binding_.plan(ligands, binding['ion'], binding.get('charge'), binding.get('bsse'), kind)
            except ValueError as exc:
                self.w.error(exc)
                return None
            queue = batches.Batch(kind, calc, items, folder, place, source, purpose='binding', extra=extra)
            if project_source:
                from azimuth import projects

                with projects.edit(self.w.research_path()) as project:
                    queued = projects.queueable(project)
                    original = [queued[k]['id'] for k in indices if 0 <= k < len(rows)]
                    ids = []
                    for k, item in enumerate(items):  # ion, then (ligand, complex) per ligand
                        if item.props.get('role') == 'ligand':
                            ident = original[(k - 1) // 2]
                        else:  # found again on a new run — no copies of the ion and the complexes
                            owner = original[(k - 2) // 2] if item.props.get('role') == 'complex' else ''
                            key = {'role': item.props.get('role'), 'of': owner, 'ion': binding['ion'],
                                   'charge': item.charge}
                            ident = projects.auxiliary_entry(
                                project, item, replace(calc, charge=item.charge, multiplicity=item.multiplicity),
                                kind, key)['id']
                        ids.append(ident)
                projects.attach(queue, self.w.research_path(), ids)
            self.with_conformer_search(queue)
            queue.save()
            return self._run_batch(queue)
        items = [batches.BatchItem(name, molecule, charge, multiplicity, start_delta=delta,
                                   props=self.structure_record(document, molecule)[0],
                                   formal=self.structure_record(document, molecule)[1])
                 for name, molecule, delta, charge, multiplicity in chosen]
        # the purpose said explicitly — the conformers of the drawer or the
        # structures (molecules) of a project; the formula does not decide it
        queue = batches.Batch(kind, calc, items, folder, place, source,
                              purpose='structures' if project_source else 'conformers')
        if project_source:
            from azimuth import projects

            queued = projects.queueable(projects.Project.view(self.w.research_path()))
            if len(queued) == len(rows):
                projects.attach(queue, self.w.research_path(), [queued[k]['id'] for k in indices if 0 <= k < len(rows)])
        self.with_conformer_search(queue)
        queue.save()
        return self._run_batch(queue)

    start_fukui = _tasks.start_fukui
    start_cda = _tasks.start_cda
    start_interaction = _tasks.start_interaction
    start_chain = _tasks.start_chain
    chain_complete = _tasks.chain_complete

    def _run_batch(self, queue):
        if self.w.has('bind_project_batch'):
            try:
                self.w.bind_project_batch(queue)
            except (OSError, ValueError, KeyError) as exc:
                self.w.error(exc)
                return None
        with self.w.at_place(queue.place):
            if queue.place == 'server':
                remote = self._open_batch_server(queue)
                if remote is None:
                    return None
                queue.remote = remote
            else:
                from modules.sextant import runner
                from modules.sextant.workspace_texts import NAMES

                program = runner.find_program(queue.kind, self.w.run_tool.configured_program(queue.kind))
                if program is None:
                    self.w.error(tr(f'{NAMES[queue.kind]} не найдена. Укажите файл программы кнопкой «Указать…».'))
                    return None
                queue.program = program
            queue.stopping = False
            # the tab it was started from: the results go back to its drawer — found by the ids of its molecule
            # (kept in batch.json, so also after a restart), the object only for a tab outside a project
            queue.document = self.w.document() if self.w.has('document') else None
            origin = (getattr(queue.document, 'research_project_id', None), getattr(queue.document, 'research_molecule_id', None))
            if all(origin) and not (queue.extra or {}).get('origin'):
                queue.extra = {**(queue.extra or {}), 'origin': {'project': origin[0], 'molecule': origin[1]}}
            self.w.batch = queue
            self.w.preferences.setValue(OPEN_KEY, str(queue.folder))
            self.update_batch_buttons()
            self.start_next_batch_item()
            return queue

    _open_batch_server = _server._open_batch_server

    @staticmethod
    def queue_under_way(queue):
        """A calculation of the queue has ended already — the next one starts without bringing the window up
        (the first one, started by the user, shows it as before)."""
        return any(item.state in ('done', 'failed', 'stopped', 'skipped') for item in queue.items)

    def start_next_batch_item(self):
        """The next step of the queue of the place chosen (decided by azimuth/runtime/queue_steps.advance over
        the queue as saved; done by _QueueSteps — the start, the watching, the window); at the end — batch_complete."""
        queue = self.w.batch
        if queue is None:
            return None
        from azimuth.runtime.queue_steps import advance

        # the parts of the tool it needs, not the tool itself (a tool reaches the window only through its port)
        return advance(queue, _QueueSteps(
            queue, self.w, send_at_once=self._send_queue_at_once, resume=self._resume_batch_item,
            search_due=self.conformer_search_due, search=self.start_conformer_stage, item_input=self.batch_item_input,
            under_way=self.queue_under_way, show_plan=self.show_batch_plan, cancel_sent=self._cancel_sent,
            complete=self.batch_complete))

    # -- the best conformer of each structure before its calculation (batch_conformers.py) -----------------
    @staticmethod
    def with_conformer_search(queue):
        """The switch of «Настройки → Расчёты» taken into a new queue (its extra keeps it: a queue taken up again searches
        as it was started, whatever the switch is then)."""
        from azimuth import defaults

        if defaults.get('batch_conformers') and queue.purpose not in ('fukui', 'cda', 'interaction', 'chain'):
            queue.extra = {**(queue.extra or {}), 'conformers': {'method': defaults.get('batch_conformer_method')}}
        return queue

    @staticmethod
    def conformer_search_due(queue, item):
        info = (queue.extra or {}).get('conformers')
        role = item.props.get('role')
        return bool(info) and 'conformer' not in item.props and item.start_delta is None \
            and role in (None, 'ligand') and item.molecule is not None and len(item.molecule.atoms) >= 4

    start_conformer_stage = _tasks.start_conformer_stage
    _conformer_tick = _tasks._conformer_tick
    _conformer_step = _tasks._conformer_step

    @staticmethod
    def batch_item_input(queue, item):
        """(calculation, input text | None) of an item: its charge, multiplicity and number; its own task (the
        single points of a binding queue), the complex rebuilt on its optimized ligand, the ghost atoms of BSSE."""
        from azimuth.core import TASKS

        k = queue.position(item)
        base = queue.calc.title or ''
        task = item.props.get('task') if item.props.get('task') in TASKS else queue.calc.task
        calc = replace(queue.calc, charge=item.charge, multiplicity=item.multiplicity, task=task,
                       title=f'{base + "_" if base else ""}{k:02d}')
        text = None
        if queue.purpose == 'binding':
            from modules.sextant import binding

            if binding.prepare(queue, item):
                queue.save()
            if item.props.get('ghosts'):
                text = binding.input_text(queue.kind, item.molecule, calc, item.props['ghosts'])
        elif queue.purpose == 'interaction' and item.props.get('ghosts'):  # the counterpoise single points
            from modules.sextant import binding

            text = binding.input_text(queue.kind, item.molecule, calc, item.props['ghosts'])
        elif queue.purpose == 'chain':  # the geometry of the step before, the changes of this step
            from modules.sextant import chain

            if chain.prepare(queue, item):
                queue.save()
            calc = replace(calc, **{k: v for k, v in (item.props.get('calc') or {}).items() if hasattr(calc, k)})
        return calc, text

    _send_queue_at_once = _server._send_queue_at_once
    _resume_batch_item = _server._resume_batch_item
    _cancel_sent = _server._cancel_sent
    server_queue_left = _server.server_queue_left
    send_rest_before_exit = _server.send_rest_before_exit

    def batch_job_finished(self, job, slot=None):
        """finish_job of a job of the queue: its state and energy, the next one (or the end). In the run slot
        of that job (azimuth/runtime/places.RunSlots.owner_of), not of the place chosen now."""
        from azimuth.runtime.places import Slotted

        slot = slot or Slotted.slots(self.w.widget).owner_of(job, self.w.job_place())
        with self.w.at_place(slot.place):
            return self._batch_job_finished(job, slot)

    def _batch_job_finished(self, job, slot):
        from modules.sextant import runner

        queue = slot.batch
        if getattr(job, '_row_ended', None) is not None:  # this end was taken already — nothing twice
            return job.code
        from azimuth.runtime.lifecycle import row_of

        item = row_of(queue, job)  # the row of this job (its folder), not whichever row runs now
        if item is None:  # nobody's end (row_of) — nothing recorded for another row
            from azimuth.runtime.provenance import note

            note('queue', f'{getattr(job.spec, "folder", "")}: the end of a calculation no row of the queue owns')
            return getattr(job, 'code', None)
        text = job.text()
        spent = runner.duration(job.elapsed())
        self.w._job_done = True
        self.w.run_tool.note_stages(text or job.stdout_text())
        self.w.job_window.finish()
        # the bookkeeping of the end of the row — azimuth/runtime/lifecycle.row_ended (no widget)
        from azimuth.runtime.lifecycle import row_ended

        ended = row_ended(queue, item, job, text, getattr(self.w, 'preferences', None))
        if ended.repeated:  # T11: this row had ended already — shown, not recorded or followed again
            self.w.job_window.show_batch(queue)
            return job.code
        state = ended.state
        if ended.project_warning:
            self.w.notify(tr('Результат сохранён, но запись в проект не обновлена: ') + ended.project_warning, 15000)
        self.w.job_window.show_batch(queue)
        self.show_batch_plan()
        if self.w.has('project_queue_row_ended'):  # its result in Compass and Spectrum while the rest run
            try:
                self.w.project_queue_row_ended()
            except (OSError, ValueError, KeyError) as exc:
                self.w.notify(tr('Результат не показан: ') + str(exc), 8000)
        self.w.set_run_status(tr(f'{item.name if item else ""}: {tr(batches.STATE_NAMES.get(state, state))} за {spent}.'), spent)
        place = queue.place

        def next_one():
            with self.w.at_place(place):
                if self.w.batch is queue:
                    self.start_next_batch_item()

        QTimer.singleShot(300, next_one)
        return job.code

    def skip_batch_item(self):
        """«Пропустить»: the current job is stopped, the queue goes on."""
        stage = getattr(getattr(self.w, 'batch', None), 'stage', None)
        if stage is not None:  # skipped while its conformer is searched
            stage.skip = True
            stage.cancel.set()
            self.w.set_run_status(tr('Пропускаю эту структуру…'))
            return
        if self.w.run_tool.job_running():
            self.w.job.stop()
            self.w.set_run_status(tr('Пропускаю этот расчёт…'))

    def stop_batch(self):
        """«Остановить» while a queue runs: the current job and the rest."""
        queue = self.w.batch
        if queue is None:
            return False
        queue.stopping = True
        stage = getattr(queue, 'stage', None)
        if stage is not None:  # the search of a conformer stops; the stage ends the queue
            stage.cancel.set()
        elif self.w.run_tool.job_running():
            self.w.job.stop()
        else:
            queue.stop_rest()
        self.w.set_run_status(tr('Останавливаю очередь…'))
        return True

    batch_complete = _results.batch_complete

    @staticmethod
    def queue_of_conformers(queue):
        """T22 (PROJECT_RUNTIME_GUIDE.md §2: the same formula alone does not make structures conformers): by the purpose
        of the queue, set when it is made — 'conformers' (the page «Конформеры»
        of the drawer) ranks them; 'structures' (the molecules of a project), binding, Fukui, CDA do not. A queue saved
        before conformers when it is bound to no project, as the queues of the drawer were."""
        purpose = getattr(queue, 'purpose', '') or ''
        if purpose:
            return purpose == 'conformers'
        return not (getattr(queue, 'extra', None) or {}).get('project')

    interaction_complete = _results.interaction_complete
    cda_complete = _results.cda_complete
    fukui_complete = _results.fukui_complete
    batch_results_to_compass = _results.batch_results_to_compass
    batch_qtaim_ready = _results.batch_qtaim_ready
    batch_qtaim = _results.batch_qtaim
    batch_descriptors = _results.batch_descriptors
    check_uncertain_item = _server.check_uncertain_item

    def resume_batch(self, folder=None):
        """«Продолжить очередь»: the queue left in its folder (the jobs not done are run)."""
        folder = folder or self.w.preferences.value(OPEN_KEY, '')
        if not folder:
            return None
        try:
            queue = batches.Batch.load(folder)
        except (OSError, ValueError, KeyError) as exc:
            self.w.error(tr('Очередь не прочитана: ') + str(exc))
            self.w.preferences.remove(OPEN_KEY)
            self.update_batch_buttons()
            return None
        if self.w.run_tool.job_running(queue.place):
            self.w.notify(tr('Здесь уже идёт расчёт: дождитесь его конца или остановите.'), 6000)
            return None
        self.open_queue_project(queue)
        if queue.place == 'server' and getattr(self.w, 'where', 'local') != 'server':
            self.w.run_tool.set_where('server')
        return self._run_batch(queue)

    def open_queue_project(self, queue):
        """The project a queue belongs to (projects.project_of_queue) opened in
        Compass when the queue is taken up — its tab chosen when it is open, else read anew; Sextant stays on screen.
        Returns the path of the project or None (a queue of no project, the project gone)."""
        from azimuth import projects

        path = projects.project_of_queue(queue)
        if path is None or not path.is_file() or not self.w.has('open_research_project'):
            return None
        current = self.w.research_path() if self.w.has('research_path') else None
        if current is not None and Path(current).resolve() == path:
            return path
        sessions = [Path(p).resolve() for p in getattr(self.w, 'project_sessions', ())]
        if path in sessions:
            self.w.activate_project_tab(sessions.index(path))
            return path
        return path if self.w.open_research_project(path, stay=True) is not None else None


class _QueueSteps:
    """What the window does for azimuth/runtime/queue_steps.advance (the bodies of start_next_batch_item before
    it): starting a row here or on the server, watching a row sent before, the conformer stage, the window and the
    plan; the decisions are advance's."""

    def __init__(self, queue, w, **parts):
        self.queue, self.w = queue, w
        self.part = parts  # send_at_once, resume, search_due, search, item_input, under_way, show_plan, cancel_sent, complete
        self._how = {}

    def send_all(self):
        return self.part['send_at_once'](self.queue)  # all of it, one SLURM job runs them

    def watch(self, item):
        return self.part['resume'](self.queue, item)

    def search_due(self, item):
        return self.part['search_due'](self.queue, item)  # its best conformer first

    def search(self, item):
        return bool(self.part['search'](self.queue, item))

    def start(self, item):
        from dataclasses import replace

        from modules.sextant import remote_job, runner

        queue = self.queue
        calc, text = self.part['item_input'](queue, item)
        if queue.place == 'server':
            profile, connection, chosen, setup = queue.remote
            spec = remote_job.prepare_remote(item.molecule, calc, (), queue.folder, chosen, setup, text=text,
                                             kind=queue.kind)
            job = remote_job.RemoteJob(spec, profile, connection).start()
            calc = replace(calc, cores=chosen.processes, memory_mb=chosen.maxcore)
            where = profile.title()
        else:
            mpirun = runner.find_mpirun(queue.program) if queue.kind == 'orca' and calc.cores > 1 else None
            spec = runner.prepare(queue.kind, queue.program, item.molecule, calc, (), queue.folder, mpirun=mpirun,
                                  text=text)
            job = runner.Job(spec).start()
            where = None
        self._how[id(job)] = (calc, where)
        return job

    def started(self, item, job):
        from modules.sextant.workspace_texts import NAMES

        queue = self.queue
        calc, where = self._how.pop(id(job))
        title = tr(f'Очередь {queue.position(item)} из {len(queue.items)}: {item.name} · {NAMES[queue.kind]}')
        self.w.run_tool.job_started(job, calc, queue.kind, None, place=where, title=title,
                                    quiet=self.part['under_way'](queue))
        self.w.job_window.show_batch(queue)
        self.part['show_plan']()  # «Идёт очередь: k из N»

    def failed_to_start(self, item, exc):
        self.w.notify(tr(f'{item.name}: ') + str(exc), 10000)

    def stop_rest(self):
        self.part['cancel_sent'](self.queue)
        self.queue.stop_rest()

    def complete(self):
        self.part['complete']()

