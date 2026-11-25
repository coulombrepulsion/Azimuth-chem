"""The queues a task makes by itself: the Fukui functions (N, N+1, N−1), CDA, the interaction energy with BSSE, a
chain of calculations and its end, and the search of conformers before a queue. Methods of BatchTool (self is the
tool; the window only through its port self.w), kept here to make batch_actions.py shorter.

Split off modules/sextant/batch_actions.py (0.222.30).
"""

from dataclasses import replace
from pathlib import Path
from PySide6.QtCore import QTimer
from azimuth.i18n import tr
from modules.sextant import batch as batches


def start_fukui(self, place=None):
    """The task «Функции Фукуи (N, N+1, N−1)»: three single points of the molecule of the tab at its geometry — N
    electrons, the anion and the cation (modules/spectrum/analysis/fukui.states) — as a queue; at its end the
    condensed Fukui functions (batch_complete → show_fukui of Compass)."""
    from modules.spectrum.analysis import fukui

    place = place or getattr(self.w, 'where', 'local')
    if self.w.run_tool.job_running(place):
        self.w.notify(tr('Здесь уже идёт расчёт: дождитесь его конца или остановите.'), 6000)
        return None
    kind = self.w.program_kind()
    if kind != 'orca':
        self.w.error(tr('Функции Фукуи считаются с ORCA: нужны файлы орбиталей всех трёх расчётов.'))
        return None
    try:
        calc = replace(self.w.calculation(), task='Энергия')
        molecule = self.w.calculation_molecule()
        if self.w.input_tool.edited_input() is not None and not self.run_without_edit(tr('Входной файл, исправленный вручную, не используется: три файла собираются по настройкам.')):
            return None
        folder = batches.batch_folder(self.w.run_tool.jobs_root(), molecule, kind)
    except (ValueError, OSError) as exc:
        self.w.error(exc)
        return None
    names = {'n': tr('N — молекула'), 'anion': tr('N + 1 — анион'), 'cation': tr('N − 1 — катион')}
    items = [batches.BatchItem(names[key] + tr(f' (заряд {charge:+d}, мультиплетность {multiplicity})'), molecule,
                               charge, multiplicity)
             for key, charge, multiplicity in fukui.states(calc.charge, calc.multiplicity)]
    queue = batches.Batch(kind, calc, items, folder, place, tr('функции Фукуи'), purpose='fukui')
    queue.save()
    return self._run_batch(queue)


def start_cda(self, place=None):
    """The task «Донорно-акцепторная связь CDA»: three single points at the geometry of the tab — the
    complex (fragment 1 first), fragment 1, fragment 2 (modules/spectrum/wavefunction/multiwfn_cda.plan) — as a
    queue; at its end
    the CDA of Multiwfn (batch_complete → show_cda of Compass)."""
    from modules.spectrum.wavefunction import multiwfn_cda

    place = place or getattr(self.w, 'where', 'local')
    if self.w.run_tool.job_running(place):
        self.w.notify(tr('Здесь уже идёт расчёт: дождитесь его конца или остановите.'), 6000)
        return None
    kind = self.w.program_kind()
    if kind != 'orca':
        self.w.error(tr('CDA считается с ORCA: нужны файлы орбиталей комплекса и обоих фрагментов.'))
        return None
    try:
        calc = replace(self.w.calculation(), task='Энергия')
        molecule = self.w.calculation_molecule()
        found = multiwfn_cda.plan(molecule, calc)
        if self.w.input_tool.edited_input() is not None and not self.run_without_edit(tr('Входной файл, исправленный вручную, не используется: три файла собираются по настройкам.')):
            return None
        folder = batches.batch_folder(self.w.run_tool.jobs_root(), molecule, kind)
    except (ValueError, OSError) as exc:
        self.w.error(exc)
        return None
    names = {'complex': tr('комплекс'), 'frag1': tr('фрагмент 1'), 'frag2': tr('фрагмент 2')}
    items = [batches.BatchItem(f'{names[key]} {part.formula}' + tr(f' (заряд {charge:+d}, мультиплетность '
                                                                    f'{multiplicity})'), part, charge, multiplicity)
             for key, part, charge, multiplicity in found['parts']]
    queue = batches.Batch(kind, calc, items, folder, place, tr('CDA'), purpose='cda',
                          extra={'fragments': [list(f) for f in found['fragments']], 'order': list(found['order'])})
    queue.save()
    return self._run_batch(queue)


def start_interaction(self, place=None):
    """The task «Энергия взаимодействия с BSSE»: five single points at the geometry of the tab (the pair,
    each molecule in the basis of the pair, each alone; modules/sextant/interaction.plan) as a queue; at its end
    ΔE, BSSE and ΔE(CP) (batch_complete)."""
    from modules.sextant import interaction

    place = place or getattr(self.w, 'where', 'local')
    if self.w.run_tool.job_running(place):
        self.w.notify(tr('Здесь уже идёт расчёт: дождитесь его конца или остановите.'), 6000)
        return None
    kind = self.w.program_kind()
    if kind != 'orca':
        self.w.error(tr('Энергия взаимодействия с BSSE считается с ORCA: нужны атомы-призраки.'))
        return None
    try:
        calc = replace(self.w.calculation(), task='Энергия')
        molecule = self.w.calculation_molecule()
        items = interaction.plan(molecule, calc)
        if self.w.input_tool.edited_input() is not None and not self.run_without_edit(tr('Входной файл, исправленный вручную, не используется: пять файлов собираются по настройкам.')):
            return None
        folder = batches.batch_folder(self.w.run_tool.jobs_root(), molecule, kind)
    except (ValueError, OSError) as exc:
        self.w.error(exc)
        return None
    queue = batches.Batch(kind, calc, items, folder, place, tr('Энергия взаимодействия'), purpose='interaction')
    queue.save()
    return self._run_batch(queue)


def start_chain(self, key, place=None, custom=None):
    """«Расчёт → Цепочка расчётов»: the steps of a preset (modules/sextant/chain.py) on the molecule of
    the tab with the settings of Sextant, as a queue — each step on the geometry of the one before."""
    from modules.sextant import chain
    from modules.sextant.workspace_texts import NAMES

    place = place or getattr(self.w, 'where', 'local')
    if self.w.run_tool.job_running(place):
        self.w.notify(tr('Здесь уже идёт расчёт: дождитесь его конца или остановите.'), 6000)
        return None
    kind = self.w.program_kind()
    if not chain.available(key, kind):
        self.w.error(tr('В {} нет одного из шагов этой цепочки.').format(NAMES.get(kind, kind)))
        return None
    try:
        calc = self.w.calculation()
        molecule = self.w.calculation_molecule()
        if self.w.input_tool.edited_input() is not None and not self.run_without_edit(tr('Входной файл, исправленный вручную, не используется: шаги цепочки собираются по '
                             'настройкам.')):
            return None
        folder = batches.batch_folder(self.w.run_tool.jobs_root(), molecule, kind)
    except (ValueError, OSError) as exc:
        self.w.error(exc)
        return None
    title = tr(chain.PRESETS[key][0])
    if custom is None and self.w.has('chain_steps'):  # the method and basis of the steps of the form
        custom = self.w.chain_steps.overrides(key)
    queue = batches.Batch(kind, calc, chain.items(key, molecule, calc, custom), folder, place, title, purpose='chain',
                          extra={'chain': key})
    queue.save()
    return self._run_batch(queue)


def chain_complete(self, queue):
    """The end of a chain (batch_complete, which writes its table and frees the queue): the result of its last step
    done opened in Spectrum, the window says how many steps are done."""
    counts = queue.counts()
    done = [item for item in queue.items if item.state == 'done' and item.output]
    opened = None
    if done:
        try:
            self.w.open_output_path(done[-1].output, show=False)  # «Перейти в Спектр» goes there
            opened = done[-1]
        except (OSError, ValueError) as exc:
            self.w.notify(tr('Результат последнего шага не открыт: ') + str(exc), 10000)
    self.w.set_run_status(
        tr('Цепочка закончена: шагов готово {} из {}.').format(counts['done'], len(queue.items))
        + (' ' + tr('В Спектре — «{}»; результаты всех шагов — в папке цепочки.').format(opened.name)
           if opened is not None else ''))
    self.w.job_window.show_batch(queue)
    self.w.job_window.show_results(compass=True, spectrum=opened is not None)
    self.w.job_window.finish()
    return done


def start_conformer_stage(self, queue, item):
    """The search in a worker thread (batch_conformers.best); a timer follows it and puts the conformer found into the
    item, then the queue goes on. False when there is nothing to search (said in the props of the item)."""
    import threading
    import time
    from types import SimpleNamespace

    from modules.sextant import batch_conformers as bc
    from modules.sextant import runner

    method = (queue.extra.get('conformers') or {}).get('method', 'auto')
    chosen = bc.method_for(method, item.molecule)
    if chosen is None:
        item.props['conformer'] = tr('поиск не нужен (жёсткая или маленькая структура)')
        queue.save()
        return False
    programs = bc.Programs()
    if chosen in ('scan', 'abc'):
        programs.xtb = runner.find_program('xtb', self.w.run_tool.configured_program('xtb'))
    elif chosen == 'crest':
        programs.crest = runner.find_program('crest', self.w.run_tool.configured_program('crest'))
    else:
        from modules.compass.chemistry import embed3d

        programs.python = embed3d.find_python(getattr(self.w, 'preferences', None))
    k = queue.position(item)
    root = Path(queue.folder) / 'conformers' / f'{k:02d}'
    cores = self.w.cores.value() if self.w.has('cores') else 1
    stage = SimpleNamespace(cancel=threading.Event(), skip=False, done=False, result=None, error=None, step=(0, 0),
                            method=chosen, started=time.monotonic())

    def step(done, total):
        stage.step = (done, total)
        return not stage.cancel.is_set()

    def work():
        try:
            stage.result = bc.best(chosen, item.molecule, item.charge, item.multiplicity, root, programs,
                                   stage.cancel, step, item.formal, cores)
        except BaseException as exc:  # noqa: BLE001 — told in the window thread
            stage.error = exc
        stage.done = True

    item.state = 'searching'
    queue.stage = stage
    queue.save()
    title = dict((key, tr(name)) for key, name, _ in bc.METHODS)[chosen]
    was_visible = self.w.job_window.isVisible() and not self.w.job_window.docked
    self.w.job_window.begin(tr(f'Очередь {k} из {len(queue.items)}: {item.name} · поиск конформера'), title)
    self.w.job_window.show_batch(queue)
    self.w.job_window.stop_button.setEnabled(True)
    self.w.stop_button.setEnabled(True)
    if self.queue_under_way(queue):  # not brought up for every structure
        self.w.follow_queue_window(was_visible)
    else:
        self.w.show_job_window()
    threading.Thread(target=work, name='azimuth-conformer', daemon=True).start()
    timer = QTimer(self.w.widget)
    timer.setInterval(400)
    timer.timeout.connect(lambda: self._conformer_tick(queue, item, stage, timer, title))
    stage.timer = timer
    timer.start()
    return True


def _conformer_tick(self, queue, item, stage, timer, title):
    """In the run slot of the place of the queue — the status and the list went to the window of the
    place chosen now («Где считать» switched during a search wrote them into the other window)."""
    with self.w.at_place(getattr(queue, 'place', None) or self.w.job_place()):
        return self._conformer_step(queue, item, stage, timer, title)


def _conformer_step(self, queue, item, stage, timer, title):
    import time

    if not stage.done:
        spent = int(time.monotonic() - stage.started)
        done, total = stage.step
        share = tr(f' · {done} из {total}') if total else (tr(f' · шагов {done}') if done else '')
        self.w.job_window.status.setText(f'{title}{share} · {spent // 60}:{spent % 60:02d}')
        return
    timer.stop()
    timer.deleteLater()
    queue.stage = None
    error = stage.error
    if stage.skip:
        item.state = 'skipped'
        item.note = tr('пропущен при поиске конформера')
    elif getattr(queue, 'stopping', False) or isinstance(error, InterruptedError):
        item.state = 'waiting'
    elif error is not None:
        item.state = 'waiting'
        item.props['conformer'] = tr('не найден: ') + (str(error).splitlines()[0] if str(error) else type(error).__name__)[:200]
        self.w.notify(tr(f'{item.name}: поиск конформера не удался — считаю исходную структуру. ') + str(error)[:200], 12000)
    else:
        found, note = stage.result
        item.state = 'waiting'
        item.props['conformer'] = note
        if found is not None:
            item.molecule = replace(found, title=item.molecule.title, bonds=item.molecule.bonds)
    queue.save()
    self.w.job_window.show_batch(queue)
    place = queue.place

    def next_one():
        with self.w.at_place(place):
            if self.w.batch is queue:
                self.start_next_batch_item()

    QTimer.singleShot(100, next_one)
