"""Compass: «Файл → Недавние файлы», «Перечитать файл» and «Сохранить несколько файлов».

§1 PURPOSE
    Two parts of the menu «Файл» of Chemcraft: Reopen (the files
    opened last; Ctrl+R opens the last one again — a result still being computed is read anew) and «Save multiple
    files» (all the structures of a set, or all the open tabs, at once: one XYZ, one SDF, a file each, a picture each).
§2 ALGORITHM
    The list of recent files is kept in the settings (RECENT_KEY, JSON, the newest first, at most RECENT_MAX, a path
    once); remember_recent of Studio adds to it — every file opened by «Открыть…», drag and drop, the hub page, a
    result of Spectrum. The submenu is filled when it opens: the files that still exist (name, the folder in the
    tooltip), «Очистить список». «Перечитать файл»: the result of the current tab is read again into the same tab
    (result_target), else the file the tab was opened from, else the newest recent file.
    The structures to save (batch_structures): those of «Структуры» of the drawer when there is a set, else the
    molecules of the open tabs. XYZ and SDF of all in one file; one XYZ a structure in a chosen folder (file names
    from the names, safe for every system, numbered, never overwriting); one PNG a structure — each shown on the
    model and rendered as «Снимок PNG» (×2), then the model is given back.
§4 SPECIFICATION
    push_recent(paths, path, limit) -> list; safe_name(name, taken, suffix='') -> str; FileTool (window.file_tool):
    recent_files(), note_recent(path), clear_recent(), fill_recent_menu(menu), reload_file(), batch_structures(),
    save_batch(kind, folder=None, path=None) -> number of files or None; build_batch_menu() -> QMenu.
§7 TESTS tests/compass/test_file_actions.py; tests/test_gui.py::test_recent_files_and_saving_many.
    «Закрыть вкладку» (Ctrl+W) and «Закрыть остальные вкладки», «Очистить» (Clear of Chemcraft: the structure and
    everything laid over it — properties,
    surfaces, critical points, measurements, own labels, the structure compared), «Молекула по названию…» (PubChem,
    pubchem.by_name, in a worker thread: the 3D record of PubChem, else its SMILES built here), «Вставить структуру из
    буфера» (Ctrl+Shift+V: structure_from_text — a molfile/SDF, XYZ with or without its two first lines, a SMILES),
    «Показать файл в папке» (the file of the tab: the project, the result, the file it was opened from). A structure
    of a name or of the clipboard goes into the tab when it is empty, else into a new tab.
    structure_from_text(text) -> (Molecule, kind ∈ {'mol', 'xyz', 'smiles'}); tab_file() -> Path | None;
    close_current_tab(), close_other_tabs() -> closed; clear_tab() -> bool; molecule_by_name(name=None);
    paste_structure(text=None) -> kind | None; reveal_file() -> Path | None.
    Tests: tests/compass/test_file_actions.py (structure_from_text, pubchem.by_name with a fake server),
    tests/test_gui.py::test_file_menu_tabs_clear_paste_and_name.
"""

import json
import re
from pathlib import Path

from azimuth.i18n import tr

RECENT_KEY = 'recent_files'
RECENT_MAX = 12


def push_recent(paths, path, limit=RECENT_MAX):
    """The list with path first, without its older copy, at most limit long."""
    path = str(path)
    return ([path] + [p for p in paths if p != path])[:limit]


def safe_name(name, taken, suffix=''):
    """A file name (with suffix) of a structure name: no characters forbidden on Windows or macOS, not empty, not one
    of taken — the full file names, compared without case («A.xyz» and «a.xyz» are one file on Windows and macOS);
    the name is added to taken. With the suffix — «CO.xyz» no longer makes the picture «CO_2.png»."""
    base = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', '_', name or '').strip(' .') or 'structure'
    base = base[:80]
    candidate, k = base, 1
    while (candidate + suffix).lower() in taken:
        k += 1
        candidate = f'{base}_{k}'
    taken.add((candidate + suffix).lower())
    return candidate + suffix


XYZ_LINE = re.compile(r'^\s*([A-Za-z]{1,2}\d*|\d{1,3})\s+(-?[\d.]+(?:[eE][-+]?\d+)?)\s+(-?[\d.]+(?:[eE][-+]?\d+)?)'
                      r'\s+(-?[\d.]+(?:[eE][-+]?\d+)?)\s*$')


def structure_from_text(text):
    """A structure in a text (the clipboard): a molfile or an SDF record; XYZ — whole, or only its lines
    «C x y z» (as copied from an output or an article); a SMILES (one word). → (Molecule, kind); ValueError."""
    from azimuth.core import read_xyz

    from modules.compass.chemistry import formats

    text = (text or '').replace('\r\n', '\n').replace('\r', '\n').strip('\n')
    if not text.strip():
        raise ValueError(tr('В буфере обмена пусто.'))
    if 'V2000' in text or 'V3000' in text:
        records = formats.read_sdf_records(text) if '$$$$' in text else [formats.read_mol(text)]
        if records:
            return records[0], 'mol'
    try:
        return read_xyz(text.strip()), 'xyz'
    except ValueError:
        pass
    lines = [line for line in text.strip().split('\n') if line.strip()]
    if lines and all(XYZ_LINE.match(line) for line in lines):
        body = '\n'.join(line.strip() for line in lines)
        return read_xyz(f'{len(lines)}\n\n{body}'), 'xyz'
    word = text.strip()
    if len(lines) == 1 and ' ' not in word and len(word) <= 400:
        return formats.from_smiles(word), 'smiles'
    raise ValueError(tr('В буфере обмена нет структуры: нужны координаты XYZ (строки «C  x  y  z»), молфайл или '
                        'SMILES.'))


class FileTool:
    """Was the mixin FileActions of the window; a part of its own — it reaches the window only through
    the names of PORT (azimuth/window_port.WindowPort)."""

    PORT = (
        'close_document',
        'close_project_tab',
        'confirm_replace',
        'structure_as_new_molecule',
        'current_document',
        'dirty',
        'document',
        'document_kind',
        'documents',
        'error',
        'load_molecule',
        'molecule',
        'navigate',
        'new_document',
        'new_molecule',
        'notify',
        'open_output_path',
        'opening_tool',
        'overlay_tool',
        'own_molecule',
        'preferences',
        'project_empty_documents',
        'project_path',
        'project_session',
        'project_sessions',
        'property_tool',
        'push_project_documents',
        'research_document_path',
        'research_path',
        'result_target',
        'stack',
        'trajectory_tool',
        'viewer',
    )

    def __init__(self, window):
        from azimuth.window_port import WindowPort

        self.w = WindowPort(window, self.PORT)


    # -- recent files -----------------------------------------------------------------------------------------------
    def recent_files(self):
        """The recent files that still exist, the newest first."""
        try:
            paths = json.loads(self.w.preferences.value(RECENT_KEY, '[]') or '[]')
        except (TypeError, ValueError):
            paths = []
        return [p for p in paths if isinstance(p, str) and Path(p).is_file()]

    def note_recent(self, path, document=True):
        """document=False (a project of a crystal) — into the list only; the file of the tab stays."""
        try:
            paths = json.loads(self.w.preferences.value(RECENT_KEY, '[]') or '[]')
        except (TypeError, ValueError):
            paths = []
        paths = push_recent([p for p in paths if isinstance(p, str)], str(Path(path).resolve()))
        self.w.preferences.setValue(RECENT_KEY, json.dumps(paths, ensure_ascii=False))
        if document and getattr(self.w, 'documents', None):
            self.w.document().file_path = str(Path(path).resolve())

    def clear_recent(self):
        self.w.preferences.setValue(RECENT_KEY, '[]')

    def fill_recent_menu(self, menu):
        menu.clear()
        paths = self.recent_files()
        if not paths:
            empty = menu.addAction(tr('Список пуст'))
            empty.setEnabled(False)
            return
        from azimuth.projects import display_name

        for k, path in enumerate(paths):
            name = display_name(path)  # a project by its name, not project.qcc
            item = menu.addAction(f'{k + 1}. {name}' if k < 9 else name)
            item.setToolTip(str(Path(path).parent))
            item.setProperty('azimuthNoIcon', True)
            item.triggered.connect(lambda checked=False, p=path: self.open_recent(p))
        menu.addSeparator()
        menu.addAction(tr('Очистить список')).triggered.connect(self.clear_recent)

    def open_recent(self, path):
        if not Path(path).is_file():
            self.w.notify(tr(f'Файла больше нет: {path}'), 8000)
            return
        self.w.opening_tool.open_path(path)

    def reload_file(self):
        """«Перечитать файл» (Ctrl+R): the result of this tab read again in place, else its file, else the newest."""
        document = self.w.document() if getattr(self.w, 'documents', None) else None
        record = getattr(document, 'output', None)
        path = record[3] if record and len(record) > 3 and record[3] else None
        if path and Path(path).is_file() and self.w.has('open_output_path'):
            self.w.result_target = document
            self.w.open_output_path(path, show=False)
            self.w.notify(tr(f'Перечитан файл: {Path(path).name}'), 5000)
            return path
        path = getattr(document, 'file_path', None)
        if not (path and Path(path).is_file()):
            recent = self.recent_files()
            path = recent[0] if recent else None
        if path is None:
            self.w.notify(tr('Перечитывать нечего: ни один файл ещё не открыт.'), 6000)
            return None
        self.w.opening_tool.open_path(path)
        return path

    # -- many files at once -----------------------------------------------------------------------------------------
    def batch_structures(self):
        """Export the active project's molecules in project order, including unsaved document edits.

        Reading this list never saves the project or closes its trajectory drawer. A single/empty project obeys
        the same boundary as a larger one. Outside a project, only standalone documents are exported; retained
        documents of closed projects may still be used by running jobs and are never included here.
        """
        path = self.w.research_path() if getattr(self.w, 'document_kind', 'molecule') == 'molecule' else None
        if path is not None:
            from azimuth import projects

            # from the session of the project — its molecules in order with the edits not saved yet; the
            # editors give their coordinates to it first (nothing is written, the drawer is not closed)
            session = self.w.push_project_documents(self.w.project_session(path), molecules_only=True)
            project = projects.Project.view(path)
            shown = self.w.document()
            found = [(molecule, name) for _, name, molecule in session.export_snapshot()]
            # A new project's first drawn molecule has no manifest entry until its first save/calculation.
            if (not shown.research_molecule_id
                    and self.w.project_empty_documents.get(str(project.path)) is shown):
                molecule = self.w.own_molecule()
                if molecule.atoms:
                    found.append((molecule, shown.title or molecule.title or molecule.formula))
            return found
        found = []
        for k, document in enumerate(getattr(self.w, 'documents', []) or []):
            if document.research_project_path:
                continue
            molecule = self.w.molecule if k == self.w.current_document else getattr(document, 'molecule', None)
            if molecule is not None and molecule.atoms:
                found.append((molecule, document.title or molecule.formula))
        return found

    def many_files_source(self):
        if getattr(self.w, 'document_kind', 'molecule') == 'molecule' and self.w.research_path() is not None:
            return tr('молекулы активного проекта')
        return tr('молекулы открытых вкладок')

    def save_batch(self, kind, folder=None, path=None):
        """kind: 'xyz-one', 'sdf-one', 'xyz-each', 'png-each'. The folder or the file is asked when not given;
        returns the number of files written, or None (nothing to save, cancelled, failed)."""
        from PySide6.QtWidgets import QFileDialog

        from azimuth.files import atomic_write

        structures = self.batch_structures()
        if not structures:
            self.w.notify(tr('Сохранять нечего: нет ни набора структур, ни молекул во вкладках.'), 8000)
            return None
        try:
            if kind in ('xyz-one', 'sdf-one'):
                suffix = '.xyz' if kind == 'xyz-one' else '.sdf'
                if path is None:
                    title = tr(f'Сохранить все структуры ({len(structures)}) одним файлом')
                    path, _ = QFileDialog.getSaveFileName(self.w.widget, title, str(Path.home() / f'structures{suffix}'),
                                                          'XYZ (*.xyz)' if suffix == '.xyz' else 'SDF (*.sdf)')
                    if not path:
                        return None
                atomic_write(path, self.batch_text(structures, suffix))
                self.w.notify(tr(f'Сохранено структур: {len(structures)} — {path}'), 10000)
                return 1
            if folder is None:
                folder = QFileDialog.getExistingDirectory(self.w.widget, tr('Папка для файлов'), str(Path.home()))
                if not folder:
                    return None
            folder = Path(folder)
            taken = {p.name.lower() for p in folder.iterdir()} if folder.is_dir() else set()
            folder.mkdir(parents=True, exist_ok=True)
            if kind == 'xyz-each':
                for molecule, name in structures:
                    atomic_write(folder / safe_name(name, taken, '.xyz'), self.batch_text([(molecule, name)], '.xyz'))
            elif kind == 'png-each':
                self.batch_pictures(structures, folder, taken)
            else:
                raise ValueError(kind)
            self.w.notify(tr(f'Файлов: {len(structures)} — в папке {folder}'), 10000)
            return len(structures)
        except (OSError, ValueError) as exc:
            self.w.error(exc)
            return None

    @staticmethod
    def batch_text(structures, suffix):
        from dataclasses import replace

        from modules.compass.chemistry import formats
        from modules.compass.chemistry.editing import perceived_orders

        if suffix == '.xyz':
            return ''.join(replace(m, title=name).xyz() for m, name in structures)
        parts = []
        for molecule, name in structures:
            named = replace(molecule, title=name)
            parts.append(formats.write_sdf(named, formats.kekule(len(named.atoms), perceived_orders(named))))
        return ''.join(parts)

    def batch_pictures(self, structures, folder, taken):
        """Each structure on the model, rendered as «Снимок PNG» ×2; the model of the tab is given back."""
        own, ghost = self.w.molecule, self.w.viewer.ghost
        try:
            for molecule, name in structures:
                self.w.viewer.ghost = None
                self.w.viewer.locked_camera = None
                self.w.trajectory_tool.show_molecule(molecule)
                self.w.viewer.keep_camera()
                self.w.viewer.render_image(2, self.w.viewer.transparent).save(str(folder / safe_name(name, taken, '.png')))
        finally:
            self.w.viewer.ghost = ghost
            self.w.trajectory_tool.show_molecule(own)
            self.w.viewer.update()

    def build_batch_menu(self):
        from PySide6.QtWidgets import QMenu

        from azimuth.ui import smooth

        menu = smooth(QMenu(tr('Сохранить несколько файлов'), self.w.widget))
        menu.setToolTipsVisible(True)
        items = (('Все структуры одним XYZ…', 'xyz-one'), ('Все структуры одним SDF…', 'sdf-one'),
                 ('Каждую структуру в свой XYZ…', 'xyz-each'), ('Картинку каждой структуры (PNG)…', 'png-each'))
        actions = []
        for title, kind in items:
            item = menu.addAction(tr(title))
            item.triggered.connect(lambda checked=False, k=kind: self.save_batch(k))
            actions.append(item)

        def refresh():
            count, source = len(self.batch_structures()), self.many_files_source()
            for item in actions:
                item.setEnabled(count > 0)
                item.setToolTip(tr(f'Сохраняются {source}: {count}'))

        menu.aboutToShow.connect(refresh)
        return menu

    # -- tabs, «Очистить», a molecule by its name or from the clipboard, the file of the tab --------------------
    def tab_file(self):
        """The file of the current tab: its project, else the result shown in it, else the file it was opened from.
        the project is also a project of the folder (project.qcc of «Проекты», research_document_path) — only the
        single-file project of before (project_path) was looked for, and a saved project «had no file»."""
        document = self.w.document() if getattr(self.w, 'documents', None) else None
        record = getattr(document, 'output', None)
        folder_project = self.w.research_document_path() if self.w.has('research_document_path') else None
        for path in (getattr(self.w, 'project_path', None), folder_project,
                     record[3] if record and len(record) > 3 and record[3] else None,
                     getattr(document, 'file_path', None)):
            if path and Path(path).is_file():
                return Path(path)
        return None

    def close_current_tab(self):
        if getattr(self.w, 'document_kind', 'molecule') == 'molecule':
            path = self.w.research_path()
            if path in self.w.project_sessions:
                return self.w.close_project_tab(self.w.project_sessions.index(path))
        if getattr(self.w, 'documents', None):
            return self.w.close_document(self.w.current_document)
        return False

    def close_other_tabs(self):
        """Close other project tabs as their crosses do; standalone/crystal documents retain their own commands."""
        if getattr(self.w, 'document_kind', 'molecule') == 'molecule':
            path = self.w.research_path()
            if path in self.w.project_sessions:
                others = [p for p in self.w.project_sessions if p != path]
                for other in others:
                    self.w.close_project_tab(self.w.project_sessions.index(other))
                return len(others)
        keep = self.w.document()
        closed, refused = 0, set()
        while True:
            others = [k for k, d in enumerate(self.w.documents)
                      if d is not keep and id(d) not in refused and not d.research_project_path]
            if not others:
                return closed
            index = others[-1]
            target = self.w.documents[index]
            if self.w.close_document(index):
                closed += 1
            else:
                refused.add(id(target))

    def clear_tab(self):
        """«Очистить» (Clear of Chemcraft): an empty structure in this tab and nothing over the model."""
        if not self.w.confirm_replace():
            return False
        if self.w.has('property_tool'):
            self.w.property_tool.clear_model_overlays()
        if getattr(self.w.viewer, 'compare_source', None) is not None and self.w.has('overlay_tool'):
            self.w.overlay_tool.clear_compare()
        self.w.viewer.pinned = []
        self.w.viewer.custom_labels = {}
        self.w.viewer.bond_marks = {}
        self.w.viewer.guides = []
        self.w.viewer.ghost = None
        self.w.new_molecule()
        self.w.dirty = False
        self.w.notify(tr('Вкладка очищена.'), 4000)
        return True

    def _structure_into_tab(self, molecule, title):
        """A structure of a name or of the clipboard: into this tab when it is empty, else into a new one."""
        # a new molecule of the project shown (Studio.structure_as_new_molecule); None — not added
        return self.w.structure_as_new_molecule(molecule, title)

    def molecule_by_name(self, name=None):
        """«Молекула по названию…»: PubChem in a worker thread, the answer in _name_answer."""
        import threading

        from modules.compass.chemistry import pubchem
        from modules.compass.actions.naming_actions import _Relay

        if name is None:
            from PySide6.QtWidgets import QInputDialog

            name, ok = QInputDialog.getText(self.w.widget, tr('Молекула по названию'),
                                            tr('Название по-английски (aspirin, caffeine, 2-butanol) — '
                                               'структура из PubChem, нужен интернет:'))
            if not ok:
                return None
        name = (name or '').strip()
        if not name:
            return None
        if not hasattr(self, '_name_relay'):
            self._name_relay = _Relay(self.w.widget)
            self._name_relay.done.connect(self._name_answer)
        relay = self._name_relay
        self.w.notify(tr(f'Ищу «{name}» в PubChem…'), 15000)

        def work():
            try:
                relay.done.emit((name, pubchem.by_name(name), None))
            except Exception as exc:  # no network, timeout, server error: said in the message line
                relay.done.emit((name, None, exc))

        threading.Thread(target=work, daemon=True).start()
        return name

    def _name_answer(self, answer):
        from modules.compass.chemistry import formats
        from modules.compass.actions.naming_actions import pubchem_problem

        name, found, error = answer
        if error is not None:
            self.w.notify(pubchem_problem(error), 15000)
            return None
        if not found:
            self.w.notify(tr(f'PubChem не знает вещества «{name}». Попробуйте английское название или SMILES.'), 10000)
            return None
        kind, text = found
        try:
            molecule = formats.read_sdf_records(text)[0] if kind == 'sdf' else formats.from_smiles(text)
        except (ValueError, IndexError) as exc:
            self.w.error(exc)
            return None
        if self._structure_into_tab(molecule, name) is None:
            return None
        self.w.notify(tr('Структура из PubChem: трёхмерная модель PubChem (силовое поле MMFF94), не оптимизированная.')
                    if kind == 'sdf' else
                    tr('Структура построена по SMILES из PubChem — это начальная геометрия, а не оптимизированная.'),
                    12000)
        return kind

    def paste_structure(self, text=None):
        """«Вставить структуру из буфера» (Ctrl+Shift+V) → the kind read, or None."""
        if text is None:
            from PySide6.QtWidgets import QApplication

            text = QApplication.clipboard().text()
        try:
            molecule, kind = structure_from_text(text)
        except ValueError as exc:
            self.w.error(exc)
            return None
        title = molecule.title if kind == 'mol' and molecule.title else ''
        if self._structure_into_tab(molecule, title) is None:
            return None
        self.w.notify({'mol': tr('Вставлен молфайл из буфера.'), 'xyz': tr('Вставлены координаты из буфера.'),
                     'smiles': tr('Структура построена по SMILES из буфера — это начальная геометрия.')}[kind], 8000)
        return kind

    def reveal_file(self):
        """«Показать файл в папке»: Finder (macOS) or Explorer (Windows) with the file selected, else its folder."""
        import subprocess
        import sys

        path = self.tab_file()
        if path is None:
            self.w.notify(tr('У этой вкладки нет файла: сохраните проект или откройте файл.'), 6000)
            return None
        try:
            if sys.platform == 'darwin':
                subprocess.Popen(['open', '-R', str(path)])
            elif sys.platform.startswith('win'):
                subprocess.Popen(['explorer', '/select,', str(path)])
            else:
                from PySide6.QtCore import QUrl
                from PySide6.QtGui import QDesktopServices

                QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.parent)))
        except OSError as exc:
            self.w.error(exc)
            return None
        return path
