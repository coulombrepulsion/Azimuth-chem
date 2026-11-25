"""What «Файлы на сервере» does with files: opening one in Azimuth, F3 view, F4 edit, Shift+F4 a new file, F5 copy,
F6 move, rename, a new folder, F8 delete. Methods of ServerBrowser (self is the window), kept here to make
server_browser.py shorter.

Split off modules/sextant/server_browser.py (0.222.30).
"""

import re
import tempfile
from pathlib import Path
from PySide6.QtWidgets import QDialog, QInputDialog, QMessageBox
from azimuth.i18n import tr
from modules.sextant import server_files as sf
from modules.sextant.server_panes import TextEditor


EDIT_LIMIT = 2_000_000  # bytes: a larger file is not edited here (an output of ORCA can be hundreds of MB)


VIEW_LIMIT = 20_000_000  # bytes: F3 shows a file up to this size (the viewer is read only)


# -- F3 … F8 --------------------------------------------------------------------------------------------------
def cache(self):
    """The folder where server files are downloaded to be opened or edited: «<папка расчётов>/с сервера/<сервер>»."""
    root = Path(self.owner.run_tool.jobs_root()) if hasattr(self.owner, 'run_tool') else Path(tempfile.gettempdir())
    folder = root / 'from-server' / re.sub(r'[^\w.-]+', '_', self.profile.title())
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _fetched(self, entry):
    target = self.cache()
    done = self._remote(tr('Скачиваю {}…').format(entry.name),
                        lambda: self.connection.get([entry.name], self.remote.path, target))
    return None if done is None else target / entry.name


def open_in_azimuth(self, entries=None):
    pane = self.active
    chosen = entries or pane.selected()
    folders = [e for e in chosen if e.kind == 'dir']
    files = [e for e in chosen if e.kind != 'dir']
    if not files:
        if folders and entries is None and len(chosen) == 1:  # Enter on a folder: into it
            self._activated(pane, folders[0])
        return None
    entry = files[0]
    path = Path(pane.path) / entry.name if pane is self.local else self._fetched(entry)
    if path is None or not path.exists():
        return None
    kind = self.owner.opening_tool.file_kind(str(path)) if hasattr(self.owner, 'opening_tool') else ''
    if hasattr(self.owner, 'navigate'):
        self.owner.navigate(2 if kind in ('output', 'gaussian_log') else 0)
    opened = self.owner.view_tool.drop_paths([str(path)]) if hasattr(self.owner, 'view_tool') else None
    self.say(tr('Открыт в Азимуте: {}').format(entry.name))
    return opened


def _text_of(self, pane, entry, limit):
    """(path here, text) of a file of a pane (a server file downloaded first), or None (said why)."""
    if entry.size > limit:
        self.say(tr('Файл больше {} — откройте его в Азимуте (Enter) или скачайте (F5).').format(sf.human(limit)),
                 error=True)
        return None
    path = Path(pane.path) / entry.name if pane is self.local else self._fetched(entry)
    if path is None:
        return None
    try:
        return path, path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        self.say(tr('Это не текстовый файл.'), error=True)
        return None
    except OSError as exc:
        self.say(str(exc), error=True)
        return None


def view(self, show=True):
    """F3 (the Lister of Total Commander): the file in the editor of the program, read only, with its search; the
    text (show=False — without the window: the tests)."""
    pane = self.active
    entry = pane.current() if pane.current() is not None else (pane.selected() or [None])[0]
    if entry is None:
        return None
    if entry.kind == 'dir':
        self._activated(pane, entry)
        return None
    got = self._text_of(pane, entry, VIEW_LIMIT)
    if got is None:
        return None
    if show:
        viewer = TextEditor(f'{entry.name} · {pane.title.text()}', got[1], self, read_only=True)
        viewer.show()
        self.viewer = viewer
    return got[1]


def edit(self, save=None):
    """F4: a text file edited here; save(text) -> text replaces the window (the tests)."""
    pane = self.active
    files = [e for e in pane.selected() if e.kind != 'dir']
    if not files:
        return None
    entry = files[0]
    got = self._text_of(pane, entry, EDIT_LIMIT)
    if got is None:
        return None
    path, text = got
    if save is None:
        editor = TextEditor(f'{entry.name} · {pane.title.text()}', text, self)
        if editor.exec() != QDialog.DialogCode.Accepted:
            return None
        new = editor.edit.toPlainText()
    else:
        new = save(text)
    return self._written(pane, path, entry.name, new)


def _written(self, pane, path, name, text):
    path.write_text(text, encoding='utf-8', newline='\n')  # a file of the server (Linux) keeps its line ends
    if pane is self.remote:
        if self._remote(tr('Сохраняю на сервере…'), lambda: self.connection.put([path], self.remote.path)) is None:
            return None
        self.go_remote(self.remote.path)
    else:
        self.go_local(self.local.path)
    pane.select([name])
    self.say(tr('Сохранён: {}').format(name))
    return path


def new_file(self, name=None, save=None):
    """Shift+F4: a new text file of the active pane, named, then edited (save(text) -> text: the tests)."""
    pane = self.active
    if name is None:
        name, ok = QInputDialog.getText(self, tr('Новый файл'), tr('Имя файла:'), text='input.inp')
        if not ok:
            return None
    name = name.strip()
    if not name or '/' in name or name in ('.', '..'):
        return None
    if any(e.name == name for e in pane.entries):
        pane.select([name])
        return self.edit(save)
    if save is None:
        editor = TextEditor(f'{name} · {pane.title.text()}', '', self)
        if editor.exec() != QDialog.DialogCode.Accepted:
            return None
        text = editor.edit.toPlainText()
    else:
        text = save('')
    path = Path(pane.path) / name if pane is self.local else self.cache() / name
    return self._written(pane, path, name, text)


def copy(self):
    """F5: the selected items to the folder of the other pane."""
    pane = self.active
    chosen = pane.selected()
    if not chosen:
        return 0
    if pane is self.local:
        paths = [Path(self.local.path) / e.name for e in chosen]
        if self._remote(tr('Загружаю на сервер ({})…').format(len(paths)),
                        lambda: self.connection.put(paths, self.remote.path)) is None:
            return 0
        self.go_remote(self.remote.path)
        self.remote.select([e.name for e in chosen])
    else:
        names = [e.name for e in chosen]
        if self._remote(tr('Скачиваю с сервера ({})…').format(len(names)),
                        lambda: self.connection.get(names, self.remote.path, self.local.path)) is None:
            return 0
        self.go_local(self.local.path)
        self.local.select(names)
    self.say(tr('Скопировано: {}').format(len(chosen)))
    return len(chosen)


def move(self, confirm=None):
    """F6: the selected items copied to the other pane, then taken from this one (here — to the Trash; on the
    server — deleted) after a question (confirm: True/False without the window — the tests); their number."""
    pane = self.active
    chosen = pane.selected()
    if not chosen:
        return 0
    names = [e.name for e in chosen]
    if confirm is None:
        from azimuth import quill

        where = tr('на сервер {}').format(self.profile.title()) if pane is self.local else tr('на этот компьютер')
        listed = '\n'.join(names[:12]) + ('\n…' if len(names) > 12 else '')
        answer = quill.question(self, tr('Переместить'), tr('Переместить ({}) {}? Отсюда они уйдут{}.').format(
            len(names), where, tr(' в Корзину') if pane is self.local else '') + '\n\n' + listed,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.Yes, 'save',
            labels={QMessageBox.StandardButton.Yes: tr('Переместить'), QMessageBox.StandardButton.No: tr('Отмена')})
        confirm = answer == QMessageBox.StandardButton.Yes
    if not confirm:
        return 0
    if self.copy() != len(chosen):
        return 0
    if pane is self.local:
        from PySide6.QtCore import QFile

        failed = [n for n in names if not QFile.moveToTrash(str(Path(pane.path) / n))[0]]
        self.go_local(pane.path)
        if failed:
            self.say(tr('Скопировано, но не удалось убрать в Корзину: ') + ', '.join(failed), error=True)
            return len(names) - len(failed)
    else:
        if self._remote(tr('Убираю с сервера…'), lambda: self.connection.text(sf.remove_command(pane.path, names))) \
                is None:
            return 0
        self.go_remote(pane.path)
    self.say(tr('Перемещено: {}').format(len(names)))
    return len(names)


def rename(self, new=None):
    pane = self.active
    chosen = pane.selected()
    if len(chosen) != 1:
        return None
    old = chosen[0].name
    if new is None:
        new, ok = QInputDialog.getText(self, tr('Переименовать'), tr('Новое имя:'), text=old)
        if not ok:
            return None
    new = new.strip()
    if not new or new == old or '/' in new:
        return None
    if pane is self.local:
        try:
            (Path(pane.path) / old).rename(Path(pane.path) / new)
        except OSError as exc:
            self.say(str(exc), error=True)
            return None
        self.go_local(pane.path)
    else:
        if self._remote(tr('Переименовываю…'), lambda: self.connection.text(sf.rename_command(pane.path, old, new))) \
                is None:
            return None
        self.go_remote(pane.path)
    pane.select([new])
    return new


def make_folder(self, name=None):
    pane = self.active
    if name is None:
        name, ok = QInputDialog.getText(self, tr('Новая папка'), tr('Имя папки:'))
        if not ok:
            return None
    name = name.strip()
    if not name or '/' in name:
        return None
    if pane is self.local:
        try:
            (Path(pane.path) / name).mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self.say(str(exc), error=True)
            return None
        self.go_local(pane.path)
    else:
        if self._remote(tr('Создаю папку…'), lambda: self.connection.text(sf.make_command(pane.path, name))) is None:
            return None
        self.go_remote(pane.path)
    pane.select([name])
    return name


def delete(self, confirm=None):
    """F8: the selected items deleted after a question (confirm: True/False without the window — the tests). On
    the server it cannot be undone; here they go to the Trash."""
    pane = self.active
    chosen = pane.selected()
    if not chosen:
        return 0
    names = [e.name for e in chosen]
    if confirm is None:
        listed = '\n'.join(names[:12]) + ('\n…' if len(names) > 12 else '')
        where = tr('на сервере {} — это нельзя отменить').format(self.profile.title()) if pane is self.remote \
            else tr('на этом компьютере — в Корзину')
        from azimuth import quill

        answer = quill.question(self, tr('Удалить'), tr('Удалить ({}) {}?').format(len(names), where) + '\n\n'
                                + listed, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                QMessageBox.StandardButton.No, 'delete',
                                labels={QMessageBox.StandardButton.Yes: tr('Удалить'),
                                        QMessageBox.StandardButton.No: tr('Отмена')})
        confirm = answer == QMessageBox.StandardButton.Yes
    if not confirm:
        return 0
    if pane is self.local:
        from PySide6.QtCore import QFile

        failed = [n for n in names if not QFile.moveToTrash(str(Path(pane.path) / n))[0]]
        if failed:
            self.say(tr('Не удалось переместить в Корзину: ') + ', '.join(failed), error=True)
        self.go_local(pane.path)
        return len(names) - len(failed)
    if self._remote(tr('Удаляю на сервере…'), lambda: self.connection.text(sf.remove_command(pane.path, names))) \
            is None:
        return 0
    self.go_remote(pane.path)
    self.say(tr('Удалено: {}').format(len(names)))
    return len(names)
