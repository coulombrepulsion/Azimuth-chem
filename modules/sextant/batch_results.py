"""The end of a queue: the table of its results, the conformers, interaction energies, CDA and Fukui functions, the
results put into Compass, «QTAIM для всех» and «Дескрипторы и logK…». Methods of BatchTool (self is the tool; the
window only through its port self.w), kept here to make batch_actions.py shorter.

Split off modules/sextant/batch_actions.py (0.222.29).
"""

from pathlib import Path
from azimuth.i18n import tr
from modules.sextant import batch as batches


QUANTITY = {'gibbs': 'ΔG', 'energy': 'ΔE', 'heat': 'ΔHf'}  # what the results are sorted by
OPEN_KEY = batches.OPEN_KEY  # the folder of a queue not finished (to take it up after a restart); in batch.py


def batch_complete(self):
    """The table of the queue and its results on the page «Конформеры» of the drawer, sorted by the new energies."""
    from modules.spectrum.wavefunction import field_tables
    from modules.sextant.workspace_texts import NAMES

    queue = self.w.batch
    if queue is None:
        return []
    self.w.preferences.remove(OPEN_KEY)
    written = []
    header, rows = queue.table()
    try:
        written = field_tables.write_tables(queue.folder, 'batch', {'energies': (header, rows)})
    except OSError as exc:
        self.w.notify(tr('Таблица очереди не записана: ') + str(exc), 10000)
    # three charge states, not conformers (nor the complex and its fragments of CDA)
    summary = queue.summary() if queue.purpose not in ('fukui', 'cda', 'binding', 'interaction', 'chain') else []
    if queue.purpose == 'binding':  # ΔE, ΔE(CP), ΔG of binding by ligand
        from modules.sextant import binding

        try:
            written += field_tables.write_tables(queue.folder, 'binding', {'energies': binding.table(queue)})
        except OSError as exc:
            self.w.notify(tr('Таблица связывания не записана: ') + str(exc), 10000)
    if queue.purpose == 'interaction':  # ΔE, BSSE, ΔE(CP)
        from modules.sextant import interaction

        try:
            written += field_tables.write_tables(queue.folder, 'interaction', {'energies': interaction.table(queue)})
        except OSError as exc:
            self.w.notify(tr('Таблица энергии взаимодействия не записана: ') + str(exc), 10000)
    counts = queue.counts()
    # the page «Конформеры» only for the structures of one substance (one formula); different molecules of a project
    # are its molecules — «Перейти в Компас» opens the project
    conformers = bool(summary) and self.queue_of_conformers(queue)
    from azimuth import projects

    project = projects.project_of_queue(queue) if (queue.extra or {}).get('project') else None
    if conformers:
        by = summary[0]['by']
        # the energy column of Compass is in hartree — MOPAC (ΔHf) gives only ΔE and the shares
        results = [((row['item'].geometry or row['item'].molecule), None if by == 'heat' else row[by], row['delta'],
                    row['share']) for row in summary]
        method = {'xtb': '', 'mopac': f' {queue.calc.method}'}.get(queue.kind, f' {queue.calc.method}/{queue.calc.basis}')
        source = tr(f'{NAMES[queue.kind]}{method} · очередь · по {QUANTITY[by]}')
        self.batch_results_to_compass(queue, results, source)
    what = QUANTITY[summary[0]['by']] if summary else 'ΔE'
    if queue.purpose == 'chain':  # the steps of a chain, its last result in Spectrum
        self.chain_complete(queue)
    else:
        self.w.set_run_status(
            tr(f'Очередь закончена: готово {counts["done"]}, с ошибкой {counts["failed"]}, остановлено '
               f'{counts["stopped"] + counts["skipped"]}. ') + (
                tr(f'Конформеры отсортированы по {what} — Компас, панель слева, «Конформеры». ') if conformers else
                tr('Результаты — в молекулах проекта: «Перейти в Компас». ') if project is not None else '')
            + (tr('Таблица: ') + written[0].name if written else ''))
        self.w.job_window.show_batch(queue)
        self.w.job_window.show_results(compass=conformers or project is not None, spectrum=False)
        self.w.job_window.finish()
    self.w.stop_button.setEnabled(False)
    for item in (self.w.program, self.w.choose_program_button):
        item.setEnabled(True)
    self.w.batch_finished_here = conformers  # «Перейти в Компас» opens the page «Конформеры»
    self.w.batch_project_here = '' if conformers or project is None else str(project)  # else the project
    self.w.job_window.show_picture('calc-done' if counts['done'] else 'calc-failed')
    self.w.run_tool.tell_job('done' if counts['done'] else 'failed')
    self.w.batch = None
    self.w.last_batch = queue
    self.show_batch_plan()  # the band of the queue that ran gives way to the choice
    if hasattr(self.w.job_window, 'qtaim_button'):  # the critical points of all of them at once
        self.w.job_window.qtaim_button.setVisible(self.batch_qtaim_ready(queue))
    self.w.input_tool.refresh_input()
    if queue.purpose == 'fukui':
        self.fukui_complete(queue)
    elif queue.purpose == 'cda':
        self.cda_complete(queue)
    elif queue.purpose == 'interaction':
        self.interaction_complete(queue)
    return written


def interaction_complete(self, queue):
    """The energies of the pair told at the end of its queue."""
    from modules.sextant import interaction

    found = interaction.energies(queue)
    if found['dE_cp'] is None:
        self.w.notify(tr('Энергия взаимодействия: не все пять расчётов закончились — см. очередь.'), 12000)
        return None
    text = tr('Энергия взаимодействия: ΔE(CP) = {} ккал/моль').format(f'{found["dE_cp"]:.2f}')
    if found['dE'] is not None:
        text += tr(' (без поправки {}, BSSE {})').format(f'{found["dE"]:.2f}', f'{found["bsse"]:.2f}')
    self.w.notify(text + tr('; таблица — interaction.csv в папке очереди.'), 20000)
    return found


def cda_complete(self, queue):
    """The three calculations done — the result of the complex opened in its tab, then CDA on it."""
    if queue.counts()['done'] != len(queue.items) or not self.w.has('property_tool'):
        self.w.set_run_status(tr('CDA: не все три расчёта закончились — посмотрите их в окне расчёта.'))
        return False
    folder = queue.folder

    def shown():
        self.w.job_window.show_results(compass=True, spectrum=False)
        self.w.property_tool.show_cda(folder)

    self.w.opening_tool.open_example_path(queue.items[0].output, go=False, done=shown)
    return True


def fukui_complete(self, queue):
    """The three calculations done — the result N opened in its tab, then the Fukui functions on it."""
    if queue.counts()['done'] != len(queue.items) or not self.w.has('property_tool'):
        self.w.set_run_status(tr('Функции Фукуи: не все три расчёта закончились — посмотрите их в окне расчёта.'))
        return False
    folder = queue.folder

    def shown():
        self.w.job_window.show_results(compass=True, spectrum=False)
        self.w.property_tool.show_fukui(folder)

    self.w.opening_tool.open_example_path(queue.items[0].output, go=False, done=shown)
    return True


def batch_results_to_compass(self, queue, results, source):
    """The results on the page «Конформеры» of the tab the queue was started from (stored there when it is not
    shown now); a new tab when it is closed or the queue was taken up after a restart."""
    if not self.w.has('trajectory_tool'):
        return None
    origin = (queue.extra or {}).get('origin') or {}
    if self.w.has('run_tool'):  # the tab of the molecule by its ids, whichever it is now
        target = self.w.run_tool.tab_for(origin.get('project'), origin.get('molecule'), getattr(queue, 'document', None))
    else:
        target = getattr(queue, 'document', None)
    documents = list(getattr(self.w, 'documents', ()))
    if target is not None and target is self.w.document():
        self.w.trajectory_tool.load_conformers(results, source)
        return target
    if target is not None and any(d is target for d in documents):
        target.conformers, target.conformer_source = tuple(results), source
        target.conformer_current = -1
        return target
    from dataclasses import replace as _replace

    first = results[0][0]
    made = self.w.new_document(tr('Очередь ') + first.formula, _replace(first, title=''))
    self.w.trajectory_tool.load_conformers(results, source)
    return made


def batch_qtaim_ready(self, queue):
    """A queue whose calculations leave files of orbitals (not MOPAC, not Fukui or CDA), with one done."""
    from modules.spectrum.wavefunction import batch_qtaim

    return (queue is not None and queue.kind in batch_qtaim.KINDS and queue.purpose not in ('fukui', 'cda', 'interaction')
            and queue.counts()['done'] > 0)


def batch_qtaim(self, folder=None, choose=False):
    """«QTAIM для всех»: the critical points of every calculation done of the queue (the last one, or the
    queue of the folder chosen — «Расчёт → QTAIM для очереди…») by Multiwfn, the interactions named; the tables of
    each molecule in its folder and «batch_qtaim_summary.csv», «…_bonds.csv», «…_contacts.csv» in «Анализ» of the
    folder of the queue. choose — the folder is asked even after a queue. Returns the tables written, or []."""
    from PySide6.QtWidgets import QFileDialog

    from azimuth.tasks import run_waiting
    from modules.spectrum.wavefunction import batch_qtaim, field_tables

    queue = None
    last = getattr(self.w, 'last_batch', None)
    if folder is None and not choose and getattr(self.w, 'batch', None) is None:
        queue = last
    if queue is None:
        if folder is None:  # choose — the menu: any queue folder, the last one first
            start = str(last.folder.parent) if last is not None else (
                str(self.w.run_tool.jobs_root()) if self.w.has('run_tool') else '')
            folder = QFileDialog.getExistingDirectory(self.w.widget, tr('Папка очереди (с batch.json)'), start)
            if not folder:
                return []
        try:
            queue = batches.Batch.load(folder)
        except (OSError, ValueError, KeyError) as exc:
            self.w.error(tr('Очередь не прочитана: ') + str(exc))
            return []
    if not self.batch_qtaim_ready(queue):
        from modules.sextant.batch_browser import qtaim_note

        message = qtaim_note(queue) if queue.kind == 'mopac' else tr(
            'QTAIM для очереди: нужны законченные расчёты ORCA, Gaussian, Psi4 или xtb с файлами орбиталей.')
        self.w.notify(message, 15000)
        return []
    program = self.w.property_tool.multiwfn_program() if self.w.has('property_tool') else None
    if program is None:
        return []
    cores = self.w.cores.value() if self.w.has('cores') else 1
    done = queue.counts()['done']
    try:
        results = run_waiting(self.w.widget, tr(f'QTAIM для очереди ({done})…'),
                              lambda step: batch_qtaim.analyse(program, queue.items, cores, step,
                                                               ledger=Path(queue.folder) / field_tables.ANALYSIS),
                              done)
    except InterruptedError:
        return []
    except (OSError, ValueError) as exc:
        self.w.error(exc)
        return []
    try:
        written = field_tables.write_tables(queue.folder, 'batch_qtaim', batch_qtaim.tables(results))
    except OSError as exc:
        self.w.error(tr('Таблицы QTAIM не записаны: ') + str(exc))
        return []
    failed = [r for r in results if r.topology is None]
    self.batch_qtaim_folder = written[0].parent if written else None
    self.w.set_run_status(
        tr(f'QTAIM для очереди: найдены точки {len(results) - len(failed)} из {len(results)}. ')
        + (tr('Без результата: ') + ', '.join(f'{r.name} ({r.error})' for r in failed[:3])
           + ('…' if len(failed) > 3 else '') + '. ' if failed else '')
        + tr('Таблицы — в папке «Анализ» очереди.'))
    return written


def batch_descriptors(self, folder=None, choose=False):
    """«Дескрипторы и logK…» — the window of modules/sextant/descriptor_view.py for the last queue (or the
    queue of the folder chosen — «Расчёт → Дескрипторы и logK очереди…»). Returns the window, or None."""
    from PySide6.QtWidgets import QFileDialog

    from modules.sextant.descriptor_view import DescriptorWindow

    queue = None
    last = getattr(self.w, 'last_batch', None)
    if folder is None and not choose and getattr(self.w, 'batch', None) is None:
        queue = last
    if queue is None:
        if folder is None:
            start = str(last.folder.parent) if last is not None else (
                str(self.w.run_tool.jobs_root()) if self.w.has('run_tool') else '')
            folder = QFileDialog.getExistingDirectory(self.w.widget, tr('Папка очереди (с batch.json)'), start)
            if not folder:
                return None
        try:
            queue = batches.Batch.load(folder, recover=False)
        except (OSError, ValueError, KeyError) as exc:
            self.w.error(tr('Очередь не прочитана: ') + str(exc))
            return None
    if not any(item.state == 'done' for item in queue.items):
        self.w.notify(tr('В очереди нет законченных расчётов — дескрипторам не из чего взяться.'), 10000)
        return None
    extra = None
    if queue.purpose == 'binding':  # the binding energies by ligand
        from modules.sextant import binding

        extra = binding.descriptor_rows(queue)
    window = DescriptorWindow(self.w.widget, queue, extra)
    self._descriptor_window = window
    window.show()
    return window
