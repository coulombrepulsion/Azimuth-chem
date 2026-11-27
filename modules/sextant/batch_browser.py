"""Saved calculation packages: reopen the whole queue after a restart, including completed queues.

Contract: folders(root, extras) discovers batch.json at the root and one level below, plus explicitly
remembered folders. Browsing only reads files; it never resumes, submits, rewrites states or connects to a server.
BatchBrowser shows every item in original order, including failures. Resume is an explicit action, separate from
opening results. QTAIM uses the selected package's folder, not the last calculation. Completed geometries can be
opened as a structure set without sorting unrelated molecules by energy or adding hydrogens. Charge and spin
are retained for a subsequent queue while these same structures remain in the document.
Tests: test_batch_browser.py uses 44 records (40 done, 4 failed), an independent filesystem snapshot, and forbidden
server callbacks to check the user's restart scenario. Real server and Multiwfn execution are outside these tests.
"""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QDialog, QFileDialog, QHBoxLayout, QHeaderView,
    QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from azimuth.i18n import tr
from azimuth.ui import button, label
from modules.sextant import batch, history


def folders(root, extras=()):
    """Existing package folders, newest modified first; shallow discovery, no network or writes."""
    root = Path(root)
    candidates = [root, *(Path(p) for p in extras if p)]
    if root.is_dir():
        candidates.extend(p.parent for p in root.glob('*/' + batch.FILE))
    found = {}
    for folder in candidates:
        if folder.name == batch.FILE:
            folder = folder.parent
        try:
            path = folder.resolve()
            manifest = path / batch.FILE
            if manifest.is_file():
                found[path] = manifest.stat().st_mtime_ns
        except OSError:
            continue
    return sorted(found, key=lambda p: (found[p], str(p)), reverse=True)


def qtaim_note(queue):
    """Explain availability in this implementation; do not imply all MOPAC exports are impossible."""
    if queue.kind == 'mopac':
        return tr('Этот пакет рассчитан в MOPAC. Пакетный QTAIM в Азимуте не поддерживает его файлы. '
                  'Откройте готовые структуры в Компасе и подготовьте расчёт, например в ORCA, '
                  'с файлом волновой функции. Затем откройте новый пакет здесь.')
    if queue.purpose in ('fukui', 'cda'):
        return tr('Для пакетов Фукуи и CDA общий QTAIM не предусмотрен.')
    return tr('QTAIM обрабатывает завершённые расчёты всего выбранного пакета через Multiwfn. '
              'Нужны файлы Molden или fchk; таблицы сохраняются в «Анализ» папки пакета.')


def restore_completed_results(queue):
    """Recover missing parsed geometry from existing outputs in memory, without changing states or files.

    A queue can have state done but no parsed geometry. Only those incomplete records are reread;
    the existing parser validates geometry. Failed jobs retain their state and are never promoted.
    """
    for item in queue.items:
        if item.state != 'done' or item.geometry is not None or not item.output:
            continue
        try:
            text = Path(item.output).read_text(encoding='utf-8', errors='replace')
        except OSError:
            continue
        energy, geometry, gibbs, heat = batch.result_of(queue.kind, text, item.output)
        if geometry is not None:
            item.geometry = geometry
            if item.energy is None:
                item.energy = energy
            if item.gibbs is None:
                item.gibbs = gibbs
            if item.heat is None:
                item.heat = heat
        else:
            from modules.spectrum.readers.outputs import read_any

            try:
                read_any(text)
            except (OSError, ValueError, KeyError, IndexError) as exc:
                item.note = str(exc)


class BatchBrowser(QDialog):
    def __init__(self, owner, folder=None):
        super().__init__(owner)
        self.owner, self.queue = owner, None
        self.setWindowTitle(tr('Пакеты расчётов'))
        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        self.packages = QComboBox()
        self.packages.setMinimumContentsLength(36)
        self.packages.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        row.addWidget(self.packages, 1)
        row.addWidget(button(tr('Открыть папку пакета…'), self.choose_folder))
        row.addWidget(button(tr('Обновить'), self.refresh))
        layout.addLayout(row)
        self.summary = label('', 'subtitle')
        self.summary.setTextFormat(Qt.TextFormat.PlainText)
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([tr('Структура'), tr('Состояние'), tr('Заряд'), tr('Мультиплетность'),
                                             tr('Результат'), tr('Примечание')])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        for column in (0, 5):
            self.table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table, 1)
        self.analysis_note = label('', 'subtitle')
        self.analysis_note.setWordWrap(True)
        layout.addWidget(self.analysis_note)
        row = QHBoxLayout()
        self.result_button = button(tr('Открыть результат'), self.open_result)
        self.structures_button = button(tr('Готовые структуры в Компас'), self.open_structures)
        self.resume_button = button(tr('Продолжить очередь'), self.resume)
        self.qtaim_button = button(tr('QTAIM для всего пакета'), self.analyse)
        for widget in (self.result_button, self.structures_button, self.resume_button, self.qtaim_button):
            row.addWidget(widget)
        layout.addLayout(row)
        row = QHBoxLayout()
        self.folder_button = button(tr('Папка'), self.open_folder)
        row.addWidget(self.folder_button)
        row.addStretch(1)
        row.addWidget(button(tr('Закрыть'), self.accept))
        layout.addLayout(row)
        row = QHBoxLayout()
        self.problems_button = button(tr('Выбрать проблемные'), self.select_problems)
        self.inspect_button = button(tr('Диагностика'), self.inspect_selected)
        self.input_button = button(tr('Исходная структура в Компас'), self.open_input_structure)
        self.retry_button = button(tr('Подготовить повтор выбранных…'), self.prepare_selected)
        # a row whose sending is not known — the server asked, nothing sent again
        self.check_button = button(tr('Проверить на сервере'), self.check_selected)
        for widget in (self.problems_button, self.inspect_button, self.input_button, self.retry_button, self.check_button):
            row.addWidget(widget)
        layout.addLayout(row)
        self.packages.currentIndexChanged.connect(self.load_selected)
        self.table.itemSelectionChanged.connect(self.update_buttons)
        self.table.cellDoubleClicked.connect(lambda *_: self.open_result())
        self.resize(1050, 650)
        self.refresh(folder)

    def refresh(self, folder=None):
        selected = str(folder) if folder else self.packages.currentData()
        extras = [selected, self.owner.preferences.value(batch.OPEN_KEY, '')]
        extras.extend(str(Path(r['folder']).parent) for r in history.load(self.owner.preferences) if r.get('folder'))
        self.packages.blockSignals(True)
        self.packages.clear()
        for path in folders(self.owner.run_tool.jobs_root(), extras):
            self.packages.addItem(path.name, str(path))
        if selected:
            index = self.packages.findData(str(Path(selected).resolve()))
            if index >= 0:
                self.packages.setCurrentIndex(index)
        self.packages.blockSignals(False)
        self.load_selected()

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, tr('Папка очереди (с batch.json)'), str(self.owner.run_tool.jobs_root()))
        if folder:
            if not (Path(folder) / batch.FILE).is_file():
                self.owner.notify(tr('В выбранной папке нет batch.json. Выберите общую папку пакета.'), 8000)
                return
            self.refresh(folder)

    def load_selected(self, *_):
        self.queue = None
        self.table.setRowCount(0)
        self.analysis_note.clear()
        folder = self.packages.currentData()
        self.summary.setText(tr('Сохранённых пакетов нет. Можно выбрать папку пакета вручную.'))
        if folder:
            try:
                active = [getattr(self.owner, 'batch', None)]
                if hasattr(self.owner, 'batch_tool'):
                    active.extend(self.owner.batch_tool._batch_runs().values())
                self.queue = next((q for q in active if q is not None and Path(q.folder).resolve() == Path(folder)), None)
                if self.queue is None:
                    self.queue = batch.Batch.load(folder)
                    restore_completed_results(self.queue)
            except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
                self.summary.setText(tr('Очередь не прочитана: ') + str(exc))
        if self.queue is not None:
            queue = self.queue
            counts = queue.counts()
            self.summary.setText(f'{queue.kind.upper()} · {len(queue.items)} · '
                                 + tr(f'готово: {counts["done"]}, с ошибкой: {counts["failed"]}')
                                 + ' · ' + tr(f'геометрий для переноса: {sum(i.state == "done" and i.geometry is not None for i in queue.items)}')
                                 + '\n' + folder)
            self.table.setRowCount(len(queue.items))
            for r, item in enumerate(queue.items):
                energy = (f'{item.energy:.8f} Eh' if item.energy is not None else
                          f'ΔHf = {item.heat:.3f} ' + tr('ккал/моль') if item.heat is not None else '')
                note = item.note
                if item.state == 'uncertain':
                    note = tr('Ответ сервера на отправку потерян: расчёт мог попасть в очередь. Повтор не готовится, '
                              'пока сервер не проверен («Проверить на сервере»).') + (' ' + item.note if item.note else '')
                elif item.state == 'failed' and not note:
                    note = tr('Причина ошибки не сохранена. Откройте вывод расчёта.')
                elif item.state == 'done' and item.geometry is None:
                    note = tr('Геометрия результата не прочитана; в набор готовых структур не включена.') + (
                        ' ' + item.note if item.note else '')
                values = (item.name, tr(batch.STATE_NAMES.get(item.state, item.state)), str(item.charge),
                          str(item.multiplicity), energy, note)
                for c, text in enumerate(values):
                    cell = QTableWidgetItem(text)
                    cell.setToolTip(text)
                    self.table.setItem(r, c, cell)
            self.analysis_note.setText(qtaim_note(queue))
            if queue.items:
                self.table.selectRow(0)
        self.update_buttons()

    def chosen(self):
        row = self.table.currentRow()
        return self.queue.items[row] if self.queue is not None and 0 <= row < len(self.queue.items) else None

    def selected_indices(self):
        return sorted({cell.row() for cell in self.table.selectedIndexes()}) if self.queue is not None else []

    def select_problems(self):
        from PySide6.QtCore import QItemSelectionModel

        self.table.clearSelection()
        if self.queue is None:
            return
        select = QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows
        for k, item in enumerate(self.queue.items):
            if item.state in ('failed', 'stopped') or (item.state == 'done' and item.geometry is None):
                self.table.selectionModel().select(self.table.model().index(k, 0), select)

    def open_input_structure(self):
        indices = self.selected_indices()
        if self.queue is None or len(indices) != 1:
            return None
        result = self.owner.batch_tool.batch_input_to_compass(self.queue, indices[0])
        self.accept()
        return result

    def prepare_selected(self):
        from modules.sextant.batch_retry import retry_dialog

        indices = self.selected_indices()
        if not indices or any(self.queue.items[k].state in batch.NOT_REPEATABLE for k in indices):
            return None
        dialog = retry_dialog(self.owner, self.queue, indices)
        self.owner._batch_retry_dialog = dialog
        dialog.show()
        return dialog

    def inspect_selected(self):
        from PySide6.QtWidgets import QPlainTextEdit
        from modules.sextant.batch_retry import inspect_item

        indices = self.selected_indices()
        if self.queue is None or len(indices) != 1:
            return None
        item = self.queue.items[indices[0]]
        _, diagnostic = inspect_item(item)
        dialog = QDialog(self)
        dialog.setWindowTitle(tr('Диагностика') + ' · ' + item.name)
        layout = QVBoxLayout(dialog)
        text = QPlainTextEdit()
        text.setReadOnly(True)
        parts = [item.name, tr('Формула: ') + item.molecule.formula,
                 tr(f'Заряд: {item.charge}; мультиплетность: {item.multiplicity}'), item.note, diagnostic]
        files = [Path(item.output)] if item.output else []
        if item.folder and Path(item.folder).is_dir():
            files.extend(sorted(Path(item.folder).glob('*.stdout')))
            files.extend(sorted(Path(item.folder).glob('slurm*.out')))
        for path in files:
            if not path.is_file():
                continue
            try:
                with path.open('rb') as file:
                    file.seek(max(0, path.stat().st_size - 65536))
                    tail = file.read(65536).decode('utf-8', errors='replace')
                parts += ['\n' + str(path), tail or tr('(пустой файл)')]
            except OSError as exc:
                parts.append(str(exc))
        text.setPlainText('\n\n'.join(parts))
        layout.addWidget(text)
        layout.addWidget(button(tr('Закрыть'), dialog.accept))
        dialog.resize(900, 600)
        self._inspection = dialog
        dialog.show()
        return dialog

    def update_buttons(self):
        item, queue = self.chosen(), self.queue
        indices = self.selected_indices()
        single = len(indices) == 1
        if single:
            item = queue.items[indices[0]]
        self.result_button.setEnabled(single and item is not None and bool(item.output) and Path(item.output).is_file())
        self.folder_button.setEnabled(queue is not None)
        self.structures_button.setEnabled(queue is not None and any(i.state == 'done' and i.geometry is not None
                                                                    for i in queue.items))
        self.resume_button.setEnabled(queue is not None and not queue.done() and not self.owner.run_tool.job_running(queue.place))
        self.qtaim_button.setEnabled(self.owner.batch_tool.batch_qtaim_ready(queue))
        self.qtaim_button.setToolTip(self.analysis_note.text())
        self.problems_button.setEnabled(queue is not None)
        self.input_button.setEnabled(single)
        self.inspect_button.setEnabled(single)
        self.retry_button.setEnabled(bool(indices) and all(queue.items[k].state not in batch.NOT_REPEATABLE
                                                           for k in indices))
        self.check_button.setEnabled(single and item is not None and item.state == 'uncertain'
                                     and not self.owner.run_tool.job_running(queue.place))
        self.resume_button.setText(tr('Запустить пакет') if queue is not None and queue.items
                                   and all(i.state == 'waiting' for i in queue.items) else tr('Продолжить очередь'))

    def open_result(self):
        indices = self.selected_indices()
        item = self.queue.items[indices[0]] if len(indices) == 1 else None
        if item is not None and item.output and Path(item.output).is_file():
            return self.owner.run_tool.open_history_result({'output': item.output})

    def open_folder(self):
        if self.queue is not None:
            return self.owner.run_tool.open_history_folder({'folder': str(self.queue.folder)})

    def open_structures(self):
        if self.queue is not None:
            result = self.owner.batch_tool.batch_structures_to_compass(self.queue)
            if result:
                self.accept()
            return result

    def check_selected(self):
        indices = self.selected_indices()
        if self.queue is None or len(indices) != 1 or not self.check_button.isEnabled():
            return None
        result = self.owner.batch_tool.check_uncertain_item(str(self.queue.folder), indices[0])
        if result is not None:
            self.accept()
        return result

    def resume(self):
        if self.queue is not None and self.resume_button.isEnabled():
            result = self.owner.batch_tool.resume_batch(str(self.queue.folder))
            if result is not None:
                self.accept()
            return result

    def analyse(self):
        if self.queue is not None and self.qtaim_button.isEnabled():
            return self.owner.batch_tool.batch_qtaim(folder=str(self.queue.folder))
