"""Saving and opening in Azimuth: a text, the project (Ctrl+S, «Сохранить как…»), the recent files of each kind,
opening a molecule or a project. Methods of Studio (self is the window), kept here to make app.py shorter.

Split off azimuth/app.py (0.222.30).
"""

from pathlib import Path
from PySide6.QtWidgets import QFileDialog
from .core import project_text
from azimuth.i18n import tr
from azimuth.files import atomic_write


def projects_is_draft(path):
    from azimuth.projects import Project

    return bool(Project.view(path).data.get('draft'))


def save_text(self, title, filter_text, text, suggested):
    path, _ = QFileDialog.getSaveFileName(self, title, str(Path.home() / suggested), filter_text)
    if path:
        atomic_write(path, text)
        self.statusBar().showMessage(tr('Сохранено: ') + path, 10000)
    return path


def save_project(self):
    """Ctrl+S («Сохранить»): into the project file of the tab without a question; a tab without one is
    saved as «Сохранить как…». → the path, or None."""
    self.attach_project_placeholder()
    if self.research_document_path() and projects_is_draft(self.research_path()):
        try:
            return self.save_project_tab()
        except (ValueError, OSError) as exc:
            self.error(exc)
            return None
    research = getattr(self.document(), 'research_project_path', '')
    if research:
        try:
            return self.save_research_project(research)
        except (OSError, ValueError, KeyError) as exc:
            self.error(exc)
            return None
    path = getattr(self, 'project_path', None)
    if not (path and str(path).lower().endswith('.qcc') and Path(path).parent.is_dir()):
        return self.save_project_as()
    try:
        atomic_write(path, project_text(self.coordinate_tool.table_molecule(), self.calculation(), getattr(self, 'constraints', ()),
                                        getattr(self.viewer, 'custom_labels', None)))
    except (ValueError, OSError) as exc:
        self.error(exc)
        return None
    self.dirty = False
    self.remember_recent('molecule', path)
    self.statusBar().showMessage(tr('Сохранено: ') + str(path), 10000)
    self.recovery.capture()
    return path


def save_project_as(self):
    """«Сохранить как…» (Ctrl+Shift+S; it was Ctrl+S): the project under a name chosen."""
    try:
        if self.research_document_path() is not None:
            return self.copy_research_project()
        path = self.save_text(
            tr('Сохранить проект'),
            tr('Азимут (*.qcc)'),
            project_text(self.coordinate_tool.table_molecule(), self.calculation(), getattr(self, 'constraints', ()),
                         getattr(self.viewer, 'custom_labels', None)),
            'project.qcc',
        )
        if path:
            self.project_path = path
            self.dirty = False
            self.remember_recent('molecule', path)
            self.recovery.capture()
        return path or None
    except (ValueError, OSError) as exc:
        self.error(exc)
        return None


# -- recent files (the hub home page offers to continue with them) --------------------
def remember_recent(self, kind, path):
    """kind: 'molecule' (XYZ or project), 'crystal' (the project of a crystal) or 'output' (ORCA); the
    last one of each is kept."""
    self.preferences.setValue(f'recent_{kind}', str(Path(path).resolve()))
    if hasattr(self, 'file_tool'):  # and the list of «Файл → Недавние файлы»
        self.file_tool.note_recent(path, document=kind != 'crystal')  # a crystal: the list only


def recent(self, kind):
    """Path of the last file of this kind if it still exists, else None.
    The file kept may be
    gone (a project only looked at is removed at its close, 0.174.0; the projects moved to «Проекты/Молекулы» and
    «Кристаллы») — then the newest of «Недавние файлы» of that kind; a crystal — a project of a crystal."""
    path = self.preferences.value(f'recent_{kind}', '') or ''
    if path and Path(path).is_file():
        return path
    if kind not in ('molecule', 'crystal') or not hasattr(self, 'file_tool'):
        return None
    from azimuth import crystal_projects

    for candidate in self.file_tool.recent_files():
        try:
            crystal = crystal_projects.is_crystal(candidate)
        except (OSError, ValueError):
            continue
        if crystal == (kind == 'crystal') and (kind == 'crystal' or not candidate.lower().endswith('.cif')):
            return candidate
    return None


def recent_list(self, kind, limit=5):  # five, not eight
    """The last files of this kind that still exist, the newest first — recent(kind) first, then
    «Недавние файлы» of that kind (a crystal — a project of a crystal; a molecule — anything else but a CIF)."""
    from azimuth.projects import looked_at_draft

    first = self.recent(kind)
    found = [first] if first and not looked_at_draft(first) else []  # no drafts of files looked at
    if kind not in ('molecule', 'crystal') or not hasattr(self, 'file_tool'):
        return found
    from azimuth import crystal_projects

    seen = {str(Path(p).resolve()) for p in found}
    for candidate in self.file_tool.recent_files():
        if len(found) >= limit:
            break
        if str(Path(candidate).resolve()) in seen:
            continue
        try:
            crystal = crystal_projects.is_crystal(candidate)
        except (OSError, ValueError):
            continue
        if crystal == (kind == 'crystal') and (kind == 'crystal' or not candidate.lower().endswith('.cif')) \
                and not looked_at_draft(candidate):
            found.append(candidate)
            seen.add(str(Path(candidate).resolve()))
    return found


def open_molecule_path(self, path):
    self.opening_tool.open_path(path)  # any structure file (XYZ, molfile, MOL2, PDB, Gaussian input, project)


def open_project(self):
    """The file dialog of the system in the folder of the projects of the
    section shown («Проекты/Кристаллы» in «Компас · Кристалл», else «Молекулы»; the folder of projects when that one
    is not there); a project is its file project.qcc in its folder (a folder dialog would show the files grey)."""
    kind = 'crystal' if getattr(self, 'compass_mode', 'molecule') == 'crystal' else 'molecule'
    start = self.projects_root(kind)
    if not start.is_dir():
        start = self.projects_root() if self.projects_root().is_dir() else Path.home()
    path, _ = QFileDialog.getOpenFileName(self, tr('Открыть проект'), str(start), tr('Азимут (*.qcc)'))
    if not path:
        return None
    return self.open_project_path(path)


def open_project_path(self, path):
    try:
        text = Path(path).read_text(encoding='utf-8-sig')
        from azimuth.projects import FORMAT
        import json

        data = json.loads(text)
        if isinstance(data, dict) and data.get('format') == FORMAT:
            return self.open_research_project(path)
        return self.open_files_project([path])  # an old .qcc of one molecule — its project
    except (ValueError, OSError, UnicodeError) as exc:
        self.error(exc)
