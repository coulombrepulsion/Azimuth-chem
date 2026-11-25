"""Sextant: the window «История расчётов» — the calculations of history.py with their state now.

§4 SPECIFICATION
    HistoryDialog(owner): table (when, where, what, state), buttons open_button («Открыть результат»), resume_button
    («Проверить на сервере»), folder_button («Папка»), forget_button («Убрать из списка»), clear_button («Очистить
    список», clear(ask=True) -> the number taken away); refresh(); chosen() -> dict.
    The owner (Sextant) does the work: open_history_result(rec), resume_history(rec), open_history_folder(rec),
    forget_history(rec).
"""

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView, QDialog, QHBoxLayout, QHeaderView, QTableWidget, QTableWidgetItem, QVBoxLayout

from azimuth.i18n import tr
from azimuth.ui import button, label
from modules.sextant import history


class HistoryDialog(QDialog):
    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.setWindowTitle(tr('История расчётов'))
        layout = QVBoxLayout(self)
        note = label(tr('Расчёты, запущенные из Секстанта (последние 60). Расчёт на сервере идёт и без программы — '
                        '«Проверить на сервере» снова следит за ним и скачивает результат.'), 'subtitle')
        note.setWordWrap(True)
        layout.addWidget(note)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels([tr('Когда'), tr('Где'), tr('Что'), tr('Состояние')])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self.update_buttons)
        self.table.cellDoubleClicked.connect(lambda *_: self.open_button.click())
        layout.addWidget(self.table, 1)
        # an empty history says so (it was an empty table)
        self.empty = label(tr('Расчётов ещё нет — здесь появятся расчёты, запущенные из Секстанта.'), 'subtitle')
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty.hide()
        layout.addWidget(self.empty, 1)
        row = QHBoxLayout()
        self.open_button = button(tr('Открыть результат'), lambda: self._do('open_history_result'), True)
        self.resume_button = button(tr('Проверить на сервере'), lambda: self._do('resume_history'))
        self.folder_button = button(tr('Папка'), lambda: self._do('open_history_folder'))
        self.forget_button = button(tr('Убрать из списка'), lambda: self._do('forget_history'))
        # the whole list at once (the folders stay; a calculation going on stays)
        self.clear_button = button(tr('Очистить список'), self.clear)
        for item in (self.open_button, self.resume_button, self.folder_button, self.forget_button, self.clear_button):
            row.addWidget(item)
        row.addStretch(1)
        row.addWidget(button(tr('Пакеты…'), lambda: owner.batch_tool.show_saved_batches()))
        row.addWidget(button(tr('Закрыть'), self.accept))
        layout.addLayout(row)
        self.resize(820, 460)
        self.refresh()

    def refresh(self):
        self.items = history.load(self.owner.preferences)
        going = {str(j.spec.folder) for j in (self.owner.running_jobs() if hasattr(self.owner, 'running_jobs') else [])}
        self.states = ['running' if rec.get('folder') in going else history.state_of(rec) for rec in self.items]
        self.table.setRowCount(len(self.items))
        self.table.setVisible(bool(self.items))
        self.empty.setVisible(not self.items)
        for r, (rec, state) in enumerate(zip(self.items, self.states)):
            try:
                when = datetime.fromisoformat(rec.get('when', '')).strftime('%d.%m.%Y %H:%M')
            except ValueError:
                when = rec.get('when', '')
            what = rec.get('title', '') + ' · ' + tr(rec.get('task', ''))
            for c, text in enumerate((when, rec.get('place') or tr('Этот компьютер'), what, history.describe(state))):
                item = QTableWidgetItem(text)
                item.setToolTip(rec.get('folder', '') if c == 2 else text)
                self.table.setItem(r, c, item)
        if self.items:
            self.table.selectRow(0)
        self.update_buttons()

    def chosen(self):
        rows = {i.row() for i in self.table.selectedIndexes()}
        return (self.items[min(rows)], self.states[min(rows)]) if rows else (None, None)

    def update_buttons(self):
        rec, state = self.chosen()
        self.open_button.setEnabled(state in ('finished', 'failed', 'stopped', 'unknown'))
        self.resume_button.setEnabled(state in history.RESUMABLE)
        self.folder_button.setEnabled(rec is not None and state != 'missing')
        self.forget_button.setEnabled(rec is not None)
        self.clear_button.setEnabled(bool(self.items) and hasattr(self.owner, 'run_tool'))

    def clear(self, ask=True):
        """«Очистить список» — after a question; the folders of the calculations are not touched."""
        if not self.items or not hasattr(self.owner, 'run_tool'):
            return 0
        if ask:
            from PySide6.QtWidgets import QMessageBox

            from azimuth import quill

            answer = quill.question(
                self, tr('История расчётов'),
                tr('Очистить список расчётов?') + '\n' + tr('Папки с файлами расчётов останутся на месте; идущий сейчас '
                                                           'расчёт останется в списке.'),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No, 'delete')
            if answer != QMessageBox.StandardButton.Yes:
                return 0
        taken = self.owner.run_tool.clear_history()
        self.refresh()
        return taken

    def _do(self, name):
        rec, _ = self.chosen()
        if rec is None:
            return None
        result = getattr(self.owner.run_tool, name)(rec)  # the history is of the part run_tool
        if name in ('forget_history',):
            self.refresh()
        elif name == 'resume_history' and result is not None:
            self.accept()
        return result
