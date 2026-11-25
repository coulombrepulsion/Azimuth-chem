"""«Новая молекула» of Compass: a new molecule of the project, a structure from SMILES, a name or the clipboard as a
new molecule, and the check that the project has not the same molecule already. Methods of CompassWorkspace (self is
the window), kept here to make workspace.py shorter.

Split off modules/compass/workspace.py (0.222.30).
"""

from azimuth.core import Molecule
from azimuth.i18n import tr


def new_molecule_command(self):
    """«Файл → Новая молекула» (⌘N). One more molecule of the project — an empty row
    «Новая молекула» in its list, the field empty for building (project_navigation.new_project_molecule); the
    molecule shown before stays. A molecule drawn of no project becomes a project first (a draft «Новый проект», as
    when another tab is chosen). Outside a project of molecules (an empty tab, «Компас · Кристалл») the tab is
    emptied, as before (new_molecule)."""
    if self.start_project_molecule():
        self.structure_tabs.setCurrentIndex(0)
        self.build_mode.setCurrentIndex(1)
        return True
    self.new_molecule()
    return False


def start_project_molecule(self):
    """The project part of «Новая молекула»: a new empty molecule of the project of the tab shown (a molecule drawn
    of no project becomes a project first) — True; False outside a project of molecules."""
    if getattr(self, 'document_kind', 'molecule') != 'molecule' or not hasattr(self, 'new_project_molecule'):
        return False
    from pathlib import Path

    own = getattr(self.document(), 'research_project_path', '') or ''
    if self.research_path() is None and own and Path(own).resolve() in getattr(self, 'project_sessions', ()):
        self._research_path = Path(own).resolve()  # the tab shown is of a project — that one
    if self.research_path() is None and self.own_molecule().atoms and hasattr(self, 'new_project_tab'):
        self.new_project_tab(tr('Новый проект'), include_current=True)
    return self.new_project_molecule() is not None


def structure_as_new_molecule(self, molecule, title=''):
    """A structure from SMILES, a name (PubChem) or the clipboard — a new molecule of the project shown, as «Новая
    молекула», named title (else its formula); outside a project — into this tab when it is empty, else into a new
    tab (no project is made for it). True when it went into a project; None when the person chose not to add a
    molecule the project has already."""
    from dataclasses import replace

    if self.stack.currentIndex() != 0:
        self.navigate(0)
    shaped = replace(molecule, title=title)
    own = getattr(self.document(), 'research_project_path', '') or ''
    in_project = self.research_path() is not None or bool(own)  # a project is open in this tab: no new one made
    if in_project and getattr(self, 'compass_mode', 'molecule') != 'crystal':
        twin = self.same_project_molecule(shaped)
        if twin is not None and not self.confirm_duplicate_molecule(twin):
            return None
    if in_project and getattr(self, 'compass_mode', 'molecule') != 'crystal' and self.start_project_molecule():
        self.load_molecule(shaped)
        self.attach_project_placeholder()
        self.structure_tabs.setCurrentIndex(0)
        return True
    if self.own_molecule().atoms:
        self.new_document()
    self.project_path = None
    self.load_molecule(shaped)
    return False


def same_project_molecule(self, molecule):
    """The name of the molecule of the project shown that is the same molecule (identity: its atoms and
    bonds, whatever the order and the geometry), or None."""
    from azimuth import projects
    from modules.compass.chemistry.identity import find_same

    from pathlib import Path

    path = self.research_path() if hasattr(self, 'research_path') else None
    own = getattr(self.document(), 'research_project_path', '') or ''
    if path is None and own:
        path = Path(own)
    if path is None or not molecule.atoms:
        return None
    candidates = []
    try:
        for entry in projects.Project.view(path).molecules:
            try:
                candidates.append((entry.get('name', ''), projects.Project.view(path).read_structure(entry['structure'])[0]))
            except (OSError, ValueError, KeyError):
                candidates.append((entry.get('name', ''), None))
    except (OSError, ValueError, KeyError):
        pass
    # the molecules of the project open in the
    # tabs too — a new one not yet written into the project is there only
    try:
        home = Path(path).resolve()
        home = home.parent if home.is_file() else home
    except OSError:
        home = None
    for document in getattr(self, 'documents', ()):
        where = getattr(document, 'research_project_path', '') or ''
        if not where or home is None:
            continue
        try:
            there = Path(where).resolve()
        except OSError:
            continue
        if (there.parent if there.is_file() else there) != home:
            continue
        shown = self.own_molecule() if document is self.document() else getattr(document, 'molecule', None)
        if shown is not None and shown.atoms:
            candidates.append((getattr(shown, 'title', '') or '', shown))
    index = find_same(molecule, candidates)
    if index is None:
        return None
    return candidates[index][0] or molecule.formula


def confirm_duplicate_molecule(self, name):
    """True — add it once more."""
    from PySide6.QtWidgets import QMessageBox

    from azimuth import quill

    answer = quill.question(
        self, tr('Эта молекула уже есть в проекте'),
        tr('В проекте уже есть «{}» — те же атомы, связи и геометрия. Добавить её ещё раз?').format(name),
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Cancel,
        'nothing-found', {QMessageBox.StandardButton.Yes: tr('Добавить ещё раз')})
    return answer == QMessageBox.StandardButton.Yes


def new_molecule(self):
    self.crystal_tool.clear_crystal()
    self.load_molecule(Molecule(tr('Новая молекула'), (), ()))
    self.project_path = None
    self.structure_tabs.setCurrentIndex(0)
    self.build_mode.setCurrentIndex(1)
