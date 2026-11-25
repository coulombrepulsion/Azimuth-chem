"""«Сервер → Очередь кластера…»:
the jobs of SLURM on the server of the profile, as squeue shows them, with the cancel of the jobs chosen.

§1 PURPOSE
    A calculation sent to the server waits in the queue of SLURM with the jobs of others. What is in the queue, how
    long it has run or why it waits (Resources, Priority…), and the cancel of a job — without a terminal.
§2 RULES
    1. list_command(everyone=False): `squeue -h -o "%i|%j|%u|%T|%M|%l|%D|%C|%R"` — of the user of the connection
       («-u "$USER"») unless everyone; parse(text) -> [Row]: the lines of 9 fields split on «|» (the reason may hold
       «|» no more: it is the last field and keeps the rest); other lines are skipped.
    2. cancel_command(ids): `scancel <id> …` of the numbers alone (a job id is digits, an array task «123_4»); anything
       else raises ValueError — nothing of the table goes to the shell as it is.
    3. ours(row): a job of Azimuth — the name of the job script of Sextant (cluster.job_script: «azimuth…»).
    4. The window reads the queue in a worker (azimuth.tasks.run_waiting), again every REFRESH_S s while it is open
       («Обновлять сам»), and asks before a cancel; its line says how many run and wait.
§4 SPECIFICATION
    Row(id, name, user, state, time, limit, nodes, cpus, reason); list_command(everyone=False) -> str; parse(text) ->
    [Row]; cancel_command(ids) -> str; ours(row) -> bool; counts(rows) -> (running, pending);
    QueueWindow(owner, profile, connection).{refresh(), cancel(confirm=None), rows, table, everyone, auto}.
§7 TESTS
    tests/sextant/test_cluster_queue.py — the parsing and the commands; the window on the fake server of the tests.
"""

import re
from dataclasses import dataclass

from azimuth.i18n import tr

REFRESH_S = 30
FIELDS = 9
STATES = {'RUNNING': 'идёт', 'PENDING': 'ждёт', 'COMPLETING': 'завершается', 'CONFIGURING': 'готовится',
          'SUSPENDED': 'приостановлена', 'CANCELLED': 'отменена', 'FAILED': 'с ошибкой', 'COMPLETED': 'готова',
          'TIMEOUT': 'вышло время', 'NODE_FAIL': 'сбой узла', 'PREEMPTED': 'вытеснена'}


@dataclass(frozen=True)
class Row:
    id: str
    name: str
    user: str
    state: str
    time: str
    limit: str
    nodes: str
    cpus: str
    reason: str


def list_command(everyone=False):
    who = '' if everyone else ' -u "$USER"'
    return f'squeue -h{who} -o "%i|%j|%u|%T|%M|%l|%D|%C|%R" 2>&1'


def parse(text):
    rows = []
    for line in (text or '').splitlines():
        parts = line.strip().split('|', FIELDS - 1)
        if len(parts) != FIELDS or not re.fullmatch(r'\d+(_\[?[\d,\-%]+\]?)?', parts[0].strip()):
            continue
        rows.append(Row(*(p.strip() for p in parts)))
    return rows


def cancel_command(ids):
    ids = [str(i).strip() for i in ids]
    if not ids or any(not re.fullmatch(r'\d+(_\d+)?', i) for i in ids):
        raise ValueError(tr('Номер задачи SLURM — только цифры.'))
    return 'scancel ' + ' '.join(ids)


def ours(row):
    return row.name.lower().startswith('azimuth')


def counts(rows):
    running = sum(1 for r in rows if r.state in ('RUNNING', 'COMPLETING', 'CONFIGURING'))
    pending = sum(1 for r in rows if r.state == 'PENDING')
    return running, pending


def _window_class():
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QColor
    from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QDialog, QHBoxLayout, QHeaderView, QMessageBox,
                                   QTreeWidget, QTreeWidgetItem, QVBoxLayout)

    from azimuth.icons import icon
    from azimuth.ui import button, label

    class QueueWindow(QDialog):
        def __init__(self, owner, profile, connection):
            super().__init__(owner)
            self.profile, self.connection, self.rows = profile, connection, []
            where = f'{profile.user.strip()}@{profile.host.strip()}' if getattr(profile, 'host', '') else ''
            # the name in the bar of the window only
            self.setWindowTitle(' · '.join(t for t in (tr('Очередь кластера (SLURM)'), profile.title(), where) if t))
            column = QVBoxLayout(self)
            column.setContentsMargins(20, 18, 20, 14)
            column.setSpacing(12)
            head = QHBoxLayout()
            head.addStretch(1)
            self.everyone = QCheckBox(tr('Все пользователи'))
            self.everyone.setToolTip(tr('Задачи всех на этом кластере, не только ваши'))
            self.everyone.toggled.connect(lambda *_: self.refresh())
            head.addWidget(self.everyone)
            self.auto = QCheckBox(tr('Обновлять сам'))
            self.auto.setToolTip(tr('Перечитывать очередь каждые {} с').format(REFRESH_S))
            self.auto.setChecked(True)
            head.addWidget(self.auto)
            column.addLayout(head)
            self.table = QTreeWidget()
            self.table.setRootIsDecorated(False)
            self.table.setAlternatingRowColors(True)
            self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
            self.table.setHeaderLabels([tr('Номер'), tr('Задача'), tr('Пользователь'), tr('Состояние'), tr('Идёт'),
                                        tr('Предел'), tr('Узлы'), tr('Ядра'), tr('Узел или причина ожидания')])
            self.table.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
            self.table.header().setSectionResizeMode(8, QHeaderView.ResizeMode.Stretch)
            column.addWidget(self.table, 1)
            self.status = label('', 'subtitle')
            column.addWidget(self.status)
            row = QHBoxLayout()
            refresh = button(tr('Обновить'), self.refresh)
            refresh.setIcon(icon('refresh'))
            row.addWidget(refresh)
            self.cancel_button = button(tr('Отменить выбранные'), lambda: self.cancel())
            self.cancel_button.setIcon(icon('stop'))
            self.cancel_button.setToolTip(tr('scancel: задача снимается с очереди или останавливается; ваши файлы на '
                                             'сервере остаются'))
            row.addWidget(self.cancel_button)
            row.addStretch(1)
            row.addWidget(button(tr('Закрыть'), self.reject))
            column.addLayout(row)
            self.timer = QTimer(self)
            self.timer.setInterval(REFRESH_S * 1000)
            self.timer.timeout.connect(lambda: self.refresh(quiet=True) if self.auto.isChecked() else None)
            self.timer.start()
            self.table.itemSelectionChanged.connect(self._chosen)
            self.resize(1000, 520)
            self.refresh()

        def _remote(self, title, work, quiet=False):
            from azimuth.tasks import run_quietly, run_waiting

            try:
                if quiet:  # the refresh by the timer: no busy cursor over the program
                    return run_quietly(lambda step: work())
                return run_waiting(self, title, lambda step: work(), alone=False)
            except InterruptedError:
                return None
            except Exception as exc:  # noqa: BLE001 — ssh.SshError and the rest: said, the window stays
                self.status.setText(str(exc))
                self.status.setObjectName('error')
                self.status.style().unpolish(self.status)
                self.status.style().polish(self.status)
                return None

        def refresh(self, quiet=False):
            text = self._remote(tr('Читаю очередь кластера…'), lambda: self.connection.text(
                list_command(self.everyone.isChecked()), timeout=60), quiet)
            if text is None:
                return None
            if 'command not found' in text or 'squeue: not found' in text:
                self.show_rows([])
                self.say(tr('На сервере нет SLURM (squeue).'))
                return []
            self.show_rows(parse(text))
            running, pending = counts(self.rows)
            mine = '' if self.everyone.isChecked() else tr('Ваших задач') + ': '
            self.say(mine + tr('{} — идут {}, ждут {}.').format(len(self.rows), running, pending)
                     if self.rows else tr('В очереди нет ваших задач.') if not self.everyone.isChecked()
                     else tr('Очередь пуста.'))
            return self.rows

        def say(self, text):
            self.status.setText(text)
            self.status.setObjectName('subtitle')
            self.status.style().unpolish(self.status)
            self.status.style().polish(self.status)

        def show_rows(self, rows):
            chosen = {i.text(0) for i in self.table.selectedItems()}
            self.rows = list(rows)
            self.table.clear()
            for r in self.rows:
                item = QTreeWidgetItem([r.id, r.name, r.user, tr(STATES.get(r.state, r.state)), r.time, r.limit, r.nodes,
                                        r.cpus, r.reason])
                item.setToolTip(3, r.state)
                if ours(r):
                    item.setForeground(1, QColor('#2a62b8'))
                    item.setToolTip(1, tr('Расчёт Азимута'))
                item.setData(0, Qt.ItemDataRole.UserRole, r)
                self.table.addTopLevelItem(item)
                item.setSelected(r.id in chosen)
            self._chosen()

        def _chosen(self):
            self.cancel_button.setEnabled(bool(self.table.selectedItems()))

        def cancel(self, confirm=None):
            chosen = [i.data(0, Qt.ItemDataRole.UserRole) for i in self.table.selectedItems()]
            if not chosen:
                return 0
            if confirm is None:
                from azimuth import quill

                listed = '\n'.join(f'{r.id} · {r.name} · {tr(STATES.get(r.state, r.state))}' for r in chosen[:12])
                answer = quill.question(self, tr('Отменить задачи'), tr('Отменить задачи SLURM ({})? Идущие '
                                                                       'остановятся, ждущие уйдут из очереди.').format(
                    len(chosen)) + '\n\n' + listed, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No, 'stop-running',
                    labels={QMessageBox.StandardButton.Yes: tr('Отменить задачи'),
                            QMessageBox.StandardButton.No: tr('Не отменять')})
                confirm = answer == QMessageBox.StandardButton.Yes
            if not confirm:
                return 0
            command = cancel_command([r.id for r in chosen])
            if self._remote(tr('Отменяю задачи…'), lambda: self.connection.text(command, timeout=60)) is None:
                return 0
            self.refresh()
            self.say(tr('Отменено задач: {}.').format(len(chosen)) + ' ' + self.status.text())
            return len(chosen)

        def done(self, result):
            self.timer.stop()
            super().done(result)

    return QueueWindow


def __getattr__(name):  # QueueWindow made when first asked: this module imports without Qt (the tests of parse)
    if name == 'QueueWindow':
        cls = _window_class()
        globals()['QueueWindow'] = cls
        return cls
    raise AttributeError(name)
