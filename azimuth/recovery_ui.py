"""Periodic molecular drafts and explicit recovery into new tabs, without changing original files.

Contract: capture() snapshots all molecular tabs every 30 seconds, including the
live form of the selected tab. It never switches tabs or closes the steps drawer.
An invalid form retains that tab's last valid draft and does not stop other tabs.
recover() claims only inactive sessions, validates before adding tabs, and deletes
the source only after the restored tabs have a durable snapshot in this session.
Restored tabs are unsaved copies (Save As); no original path is written implicitly.
Crystal cells, result viewers and undo history are outside the project-draft scope.
A tab saved into its project and unchanged since is not in the snapshot (it is in its file).
The question offers «Удалить копию»; a snapshot that cannot be read goes to «damaged/».
"""

import uuid
import weakref

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QMessageBox

from azimuth.core import Calculation, project_text, read_project, project_constraints, project_labels
from azimuth import quill
from azimuth.i18n import tr
from azimuth.recovery import Session, clean_temporary, recovery_dir, set_aside

INTERVAL_MS = 30_000


def decode_entry(entry):
    """Validate all persisted fields before touching the window; return a fresh Document."""
    from modules.compass.panels.documents import Document

    if not isinstance(entry, dict):
        raise ValueError('Invalid recovery entry')
    for key in ('id', 'title', 'project', 'program', 'origin'):
        if not isinstance(entry.get(key), str):
            raise ValueError('Invalid recovery field: ' + key)
    from modules.sextant.workspace_texts import PROGRAMS

    if entry['program'] not in {key for key, _ in PROGRAMS}:
        raise ValueError('Unknown program: ' + entry['program'][:40])
    edit = entry.get('input_edit')
    if edit is not None and (not isinstance(edit, (list, tuple)) or len(edit) != 2
                             or not all(isinstance(v, str) for v in edit)):
        raise ValueError('Invalid input edit')
    mol, calc = read_project(entry['project'])
    return Document(title=entry['title'], named=bool(entry['title']), molecule=mol,
                    calculation=calc, program=entry['program'], state_formula=mol.formula,
                    constraints=list(project_constraints(entry['project'])),
                    labels=project_labels(entry['project']), input_edit=tuple(edit) if edit else None,
                    dirty=True)


class Recovery(QObject):
    restored = Signal()

    def __init__(self, window, directory=None):
        super().__init__(window)
        self.window = window
        self.directory = recovery_dir() if directory is None else directory
        self.session = None
        self.ids = weakref.WeakKeyDictionary()
        self.previous = {}
        self.last_error = ''
        self.timer = QTimer(self)
        self.timer.setInterval(INTERVAL_MS)
        self.timer.timeout.connect(self.capture)
        self.timer.start()
        self.startup = QTimer(self)
        self.startup.setSingleShot(True)
        self.startup.timeout.connect(self.recover)
        self.startup.start(0)

    def warn(self, exc):
        message = tr('Не удалось обновить аварийную копию. Предыдущая копия сохранена: ') + str(exc)
        if message != self.last_error:
            self.window.notify(message, 15000)
            self.last_error = message

    def capture(self):
        window = self.window
        entries, valid = {}, True
        for doc in window.all_documents():
            if doc.kind != 'molecule':
                continue
            key = self.ids.setdefault(doc, uuid.uuid4().hex)
            try:
                current = doc is window.document()
                mol = window.own_molecule() if current else doc.molecule
                dirty = window.dirty if current else doc.dirty
                edit = window.input_tool.stored_input_edit() if current else doc.input_edit
                if mol is None or (not mol.atoms and not dirty and edit is None):
                    continue
                origin = window.project_path if current else doc.project_path
                if origin and not dirty:  # saved into its project and unchanged since: the file is the copy
                    continue
                # The table can contain a half-entered coordinate. Keep its last valid draft.
                if current and not window.browsing:
                    mol = window.coordinate_tool.table_molecule()
                calc = window.calculation() if current else (doc.calculation or Calculation())
                constraints = window.constraints if current else doc.constraints
                labels = window.viewer.custom_labels if current else doc.labels
                entries[key] = {
                    'id': key, 'title': doc.title if doc.named else mol.title,
                    'project': project_text(mol, calc, constraints, labels),
                    'program': window.program_kind() if current else doc.program,
                    'origin': str(origin or ''), 'input_edit': edit,
                }
            except (ValueError, TypeError, OverflowError) as exc:
                valid = False
                if key in self.previous:
                    entries[key] = self.previous[key]
                self.warn(exc)
        try:
            if self.session is None:
                self.session = Session(self.directory)
            self.session.write(list(entries.values()))
            self.previous = entries
            if valid:
                self.last_error = ''
            return valid
        except (OSError, ValueError, TypeError) as exc:
            self.warn(exc)
            return False

    def recover(self):
        from pathlib import Path

        try:
            clean_temporary(self.directory)
            paths = sorted(Path(self.directory).glob('*.json'))
        except OSError as exc:
            self.warn(exc)
            return
        for path in paths:
            source = Session.claim(path)
            if source is None:
                continue
            keep, damaged = True, None
            try:
                try:
                    docs = [decode_entry(entry) for entry in source.read()]
                except (ValueError, TypeError, KeyError, OverflowError, RecursionError) as exc:
                    damaged = exc  # set aside, not offered (and reported) at every start
                    continue
                if not docs:
                    keep = False
                    continue
                answer = quill.question(
                    self.window, tr('Восстановление вкладок'),
                    tr(f'Найдена аварийная копия молекулярных вкладок ({len(docs)}). Восстановить их в новых вкладках? '
                       'Исходные файлы не изменятся. «Нет» оставит копию на потом, «Удалить копию» — удалит её.'),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Discard,
                    QMessageBox.StandardButton.Yes, 'save',
                    labels={QMessageBox.StandardButton.Discard: tr('Удалить копию')},
                )
                if answer == QMessageBox.StandardButton.Discard:
                    keep = False
                    continue
                if answer != QMessageBox.StandardButton.Yes:
                    continue
                self.window.ensure_molecule_tabs()
                for doc in docs:
                    target = self.window.new_document(doc.title, doc.molecule)
                    target.__dict__.update(doc.__dict__)
                    self.window.restore_document(target)
                self.window.navigate(0)
                keep = not self.capture()
                self.restored.emit()
            except (OSError, ValueError, TypeError, KeyError, OverflowError, RecursionError) as exc:
                self.window.notify(tr('Не удалось восстановить аварийную копию; файл сохранён: ') + str(path)
                                   + '\n' + str(exc), 15000)
            finally:
                try:
                    source.close(keep=keep)
                except OSError as exc:
                    self.warn(exc)
                if damaged is not None:
                    try:
                        moved = set_aside(path)
                        self.window.notify(tr('Аварийную копию не прочитать — она перенесена в ') + str(moved)
                                           + '\n' + str(damaged), 15000)
                    except OSError as exc:
                        self.warn(exc)

    def finish(self, keep=False):
        """Call only after exit was accepted. Cancel leaves both timers and snapshot alive."""
        self.timer.stop()
        self.startup.stop()
        if self.session is not None:
            try:
                self.session.close(keep=keep)
            except OSError as exc:
                self.warn(exc)
