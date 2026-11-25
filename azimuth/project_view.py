"""«История и файлы проекта»: the molecules of the project with their attempts and current results, the history of
the calculations of a molecule, adding molecules from files and a queue folder; nothing is launched on open.
Only that — the tab is the project and its pane holds the list, the modes, the queue and QTAIM,
so the buttons doing the same here (a new or another project, saving, opening a structure, preparing calculations,
QTAIM of the whole project, closing the project, adding the current molecule) are gone, and the window no longer opens
by itself when a project is made or opened."""

from pathlib import Path
import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QDialog, QFileDialog, QHBoxLayout, QHeaderView,
                               QTableWidget, QTableWidgetItem, QVBoxLayout)

from azimuth.core import read_project
from azimuth.i18n import tr
from azimuth.ui import button, label
from azimuth import projects
from modules.sextant.batch import STATE_NAMES



def method_of(attempt):
    """The method of a calculation as it was run — xtb by its GFN (the form kept «B3LYP» for an xtb run:
    «XTB · B3LYP» in the history), MOPAC by its Hamiltonian, the others with their basis."""
    if attempt.get('keywords'):  # a calculation imported (project_import) — its keywords as written
        return str(attempt['keywords'])
    calc = attempt.get('calculation') or {}
    kind = attempt.get('kind', '')
    if kind == 'xtb':
        return {'gfnff': 'GFN-FF', 'gfn1': 'GFN1-xTB', 'gfn0': 'GFN0-xTB'}.get(calc.get('xtb_method') or '', 'GFN2-xTB')
    if kind == 'mopac':
        return str(calc.get('method', ''))
    return f"{calc.get('method', '')} / {calc.get('basis', '')}"

class ProjectDialog(QDialog):
    def __init__(self, owner):
        super().__init__(owner)
        self.owner, self.project = owner, None
        self.setWindowTitle(tr('История и файлы проекта'))
        layout = QVBoxLayout(self)
        self.heading = label('', 'cardtitle')
        self.heading.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.heading)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([tr('Молекула'), tr('Формула'), tr('Попыток'), tr('Актуальный расчёт'),
                                             tr('Энергия / ΔHf'), tr('Последняя попытка')])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        for column in (0, 3, 5):
            self.table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table, 1)
        self.message = label('', 'subtitle')
        self.message.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.message)
        row = QHBoxLayout()
        self.history_button = button(tr('История расчётов молекулы'), self.show_history)
        self.add_files = button(tr('Добавить молекулы из файлов…'), self.import_files)
        self.add_batch = button(tr('Добавить пакет расчётов…'), self.import_batch)
        for widget in (self.history_button, self.add_files, self.add_batch):
            row.addWidget(widget)
        row.addStretch(1)
        row.addWidget(button(tr('Обновить'), self.refresh))
        row.addWidget(button(tr('Закрыть окно'), self.accept))
        layout.addLayout(row)
        self.table.itemSelectionChanged.connect(self.update_buttons)
        self.table.cellDoubleClicked.connect(lambda *_: self.show_history())
        self.resize(1000, 560)
        self.refresh()

    def action(self, callback):
        try:
            result = callback()
            self.refresh()
            return result
        except (OSError, ValueError, KeyError, StopIteration) as exc:
            self.message.setText(str(exc))
            return None

    def refresh(self):
        selected = self.selected()
        self.project = None
        path = self.owner.research_path()
        self.message.clear()
        if path:
            try:
                self.project = projects.refresh(path)
            except (OSError, ValueError, KeyError, StopIteration) as exc:
                self.message.setText(str(exc))
        self.table.setRowCount(0)
        self.heading.setText(self.project.data['name'] if self.project else tr('Проект не выбран.'))
        self.heading.setToolTip(str(path or ''))
        if self.project is not None:
            ready = sum(self.project.current(e) is not None for e in self.project.molecules)
            total = len(self.project.molecules)
            self.message.setText(tr('Молекул: {total} · с готовым результатом: {ready} · без готового результата: {pending}')
                                 .format(total=total, ready=ready, pending=total - ready))
            self.table.setRowCount(total)
            for row, entry in enumerate(self.project.molecules):
                molecule, _ = read_project(json.dumps(entry['structure']))
                current = self.project.current(entry)
                last = entry['attempts'][-1] if entry['attempts'] else None
                method = tr('Нет готового результата')
                if current:
                    method = current['kind'].upper() + ' · ' + method_of(current)
                energy = ''
                if current:
                    energy = (f'{current["energy"]:.8f} Eh' if current.get('energy') is not None else
                              f'ΔHf = {current["heat"]:.4f} ' + tr('ккал/моль') if current.get('heat') is not None else '')
                state = tr(STATE_NAMES.get(last['state'], last['state'])) if last else ''
                if last and last['state'] == 'done' and not last.get('usable'):
                    state += ' · ' + tr('геометрия не прочитана')
                for col, value in enumerate((entry['name'], molecule.formula, str(len(entry['attempts'])), method, energy, state)):
                    cell = QTableWidgetItem(value)
                    cell.setToolTip(value)
                    self.table.setItem(row, col, cell)
            if self.project.molecules:
                row = next((k for k, e in enumerate(self.project.molecules) if e['id'] in selected), 0)
                self.table.selectRow(row)
        self.update_buttons()

    def selected(self):
        if self.project is None:
            return []
        return [self.project.molecules[k]['id'] for k in sorted({i.row() for i in self.table.selectedIndexes()})
                if k < len(self.project.molecules)]

    def update_buttons(self):
        ids = self.selected()
        for widget in (self.add_files, self.add_batch):
            widget.setEnabled(self.project is not None)
        self.history_button.setEnabled(len(ids) == 1)

    def import_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, tr('Добавить молекулы из файлов'), str(Path.home()),
                                               tr('Структуры (*.xyz *.mol *.sdf *.mol2 *.pdb *.qcc *.inp *.gjf);;Все файлы (*)'))
        if paths:
            self.action(lambda: self.owner.import_project_structures(paths))

    def import_batch(self):
        folder = QFileDialog.getExistingDirectory(self, tr('Папка очереди (с batch.json)'), str(Path.home()))
        if folder:
            self.action(lambda: self.owner.import_project_batch(folder))

    def show_history(self, ident=None):
        """ident («История расчётов молекулы» of the menu of the list of the project) — that molecule, else
        the one chosen in this window."""
        ids = [ident] if ident else self.selected()
        if len(ids) != 1:
            return None
        project = projects.refresh(self.owner.research_path())
        entry = project.entry(ids[0])
        dialog = QDialog(self)
        dialog.setWindowTitle(tr('История расчётов молекулы') + ' · ' + entry['name'])
        layout = QVBoxLayout(dialog)
        table = QTableWidget(0, 5)
        table.setHorizontalHeaderLabels([tr('Попытка'), tr('Программа / метод'), tr('Состояние'), tr('Актуальный'), tr('Файл')])
        table.verticalHeader().hide()  # the number is «Попытка»
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        shown = {'entry': entry}

        def fill():
            now = shown['entry']
            table.setRowCount(len(now['attempts']))
            for number, attempt in enumerate(now['attempts']):
                values = (str(number + 1), attempt['kind'].upper() + ' · ' + method_of(attempt),
                          tr(STATE_NAMES.get(attempt['state'], attempt['state'])),
                          '✓' if attempt['id'] == now['current'] else '', attempt['output'])
                for col, value in enumerate(values):
                    table.setItem(number, col, QTableWidgetItem(value))

        fill()
        layout.addWidget(table)
        message = label('', 'subtitle')
        layout.addWidget(message)

        def chosen():
            row = table.currentRow()
            attempts = shown['entry']['attempts']
            return attempts[row] if 0 <= row < len(attempts) else None

        def open_result():
            attempt = chosen()
            if attempt and attempt['output']:
                self.owner.run_tool.open_history_result({'output': str(project.absolute(attempt['output']))})

        def open_queue():
            attempt = chosen()
            if attempt and attempt['batch']:
                self.owner.batch_tool.show_saved_batches(project.absolute(attempt['batch']))
            elif attempt and attempt.get('place') and attempt['state'] in ('running', 'sent', 'waiting'):
                rec = dict(attempt['calculation'], kind=attempt['kind'], place=attempt['place'], title=entry['name'],
                           folder=str(project.absolute(attempt['folder'])), output=str(project.absolute(attempt['output'])))
                self.owner.run_tool.resume_history(rec)
            else:
                message.setText(tr('Одиночный локальный расчёт: новый запуск готовится из списка молекул проекта.'))

        def forget(ask=True):
            """The calculation chosen leaves the history and its
            folder is deleted (when it is its own)."""
            attempt = chosen()
            if attempt is None:
                return False
            number = table.currentRow() + 1
            path = self.owner.research_path()
            # its folder goes too, when no other
            # calculation uses it (projects.attempt_folder)
            folder = projects.attempt_folder(projects.refresh(path), attempt)
            if ask:
                from PySide6.QtWidgets import QMessageBox

                from azimuth import quill

                yes = QMessageBox.StandardButton.Yes
                what = attempt['kind'].upper() + ' · ' + method_of(attempt)
                answer = quill.question(
                    dialog, tr('Удалить расчёт'),
                    (tr('Удалить попытку {} ({}) из истории молекулы вместе с папкой расчёта «{}»? Её не вернуть.').format(
                        number, what, folder.name) if folder is not None else
                     tr('Убрать попытку {} ({}) из истории молекулы? Своей папки у этого расчёта нет — файлы не '
                        'удаляются.').format(number, what)),
                    yes | QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Cancel, 'nothing-found',
                    {yes: tr('Удалить')})
                if answer != yes:
                    return False
            try:
                if hasattr(self.owner, 'save_research_project'):
                    self.owner.save_research_project()
                with projects.edit(path) as edited:
                    edited.forget_attempt(shown['entry']['id'], attempt['id'])
            except (OSError, ValueError, KeyError) as exc:
                message.setText(tr(str(exc)))  # the words of projects.forget_attempt in the language of the program
                return False
            failed = ''
            if folder is not None:
                import shutil

                try:
                    shutil.rmtree(folder)
                except OSError as exc:
                    failed = str(exc)
            shown['entry'] = projects.refresh(path).entry(shown['entry']['id'])
            fill()
            if table.rowCount():
                table.selectRow(min(number - 1, table.rowCount() - 1))
            if failed:
                message.setText(tr('Попытка {} убрана из истории, но её папку удалить не удалось: {}').format(number, failed))
            elif folder is not None:
                message.setText(tr('Попытка {} удалена вместе с папкой расчёта.').format(number))
            else:
                message.setText(tr('Попытка {} убрана из истории.').format(number))
            if hasattr(self.owner, 'refresh_project_navigation'):
                self.owner._project_shown = None
                self.owner.refresh_project_navigation()
            return True

        from PySide6.QtGui import QKeySequence, QShortcut

        for key in (QKeySequence.StandardKey.Delete, QKeySequence(Qt.Key.Key_Backspace)):
            QShortcut(key, table, activated=lambda: forget())

        row = QHBoxLayout()
        row.addWidget(button(tr('Открыть результат'), open_result))
        row.addWidget(button(tr('Открыть очередь / проверить сервер'), open_queue))
        remove = button(tr('Удалить расчёт'), lambda: forget())
        remove.setToolTip(tr('Удалить выбранный расчёт: из истории молекулы и его папку · Delete'))
        row.addWidget(remove)
        row.addStretch(1)
        row.addWidget(button(tr('Закрыть'), dialog.accept))
        layout.addLayout(row)
        if entry['attempts']:
            table.selectRow(len(entry['attempts']) - 1)
        dialog.resize(1000, 450)
        dialog.history_table, dialog.forget = table, forget  # for the tests
        self._history = dialog
        dialog.show()
        return dialog
