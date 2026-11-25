"""Saving, naming and discarding projects; drafts of new molecules — a part of ProjectNavigation
(azimuth/project_navigation.py), a mixin of Studio.

§1 PURPOSE
    A draft becomes a project folder when saved; an untouched draft is discarded; the name of a project follows the
    formula of its molecule until the user names it; a drawn molecule waits as a draft row.
§7 TESTS tests/projects/test_project_navigation.py.
"""

from pathlib import Path
import shutil

from azimuth import projects
from azimuth.i18n import tr
from azimuth.project_widgets import NEW_ROW


class ProjectSaving:
    def viewed_projects(self):
        """The projects (resolved paths of project.qcc) made by opening files and not changed since."""
        if not hasattr(self, '_viewed_projects'):
            self._viewed_projects = set()
        return self._viewed_projects

    def keep_project(self, path):
        """The project changed (an edit, files added, «Сохранить», a calculation) — it stays in «Проекты»."""
        if path:
            self.viewed_projects().discard(Path(path).resolve())

    def discard_untouched_project(self, path):
        """The folder of a project of files opened only to look at, removed when its tab closes or the program
        ends — nothing was edited, no calculation was made, no name was given (the files themselves stay where they
        are). Its session must be closed first. True when removed."""
        path = Path(path).resolve()
        if path not in self.viewed_projects() and not self.empty_draft(path):
            return False
        self.viewed_projects().discard(path)
        try:
            project = projects.Project.view(path)
        except (OSError, ValueError, KeyError):
            return False
        from azimuth import crystal_projects

        crystal = project.data.get(crystal_projects.KEY)
        if isinstance(crystal, dict):  # a crystal is named by its CIF — kept by a run or a calculation
            calculations = path.parent / 'calculations'
            if crystal.get('runs') or crystal.get('more') or (calculations.is_dir() and any(calculations.iterdir())):
                return False
            document = getattr(self, 'crystal_documents', {}).get(str(path))
            if document is not None and getattr(document, 'dirty', False):
                return False
        elif project.data.get('named') or any(entry.get('attempts') for entry in project.molecules):
            return False
        ident = project.data.get('id')
        if any(getattr(doc, 'research_project_id', None) == ident and doc.dirty for doc in self.all_documents()):
            return False
        try:
            self.session_registry().close(ident, save=False)
        except (OSError, ValueError, KeyError):
            pass
        try:
            shutil.rmtree(path.parent)
        except OSError:
            return False
        return True

    def empty_draft(self, path):
        """A draft of molecules with nothing in it — no molecule, no
        crystal, no name given, nothing in its calculations (a tab «+» left empty, the project of «Новая молекула» not
        drawn in): its folder goes as that of a file only looked at (discard_untouched_project)."""
        try:
            project = projects.Project.view(path)
        except (OSError, ValueError, KeyError):
            return False
        from azimuth import crystal_projects

        if not project.data.get('draft') or project.data.get('named') or project.molecules:
            return False
        if project.data.get(crystal_projects.KEY) is not None:
            return False
        calculations = Path(path).parent / 'calculations'
        return not (calculations.is_dir() and any(calculations.iterdir()))

    def discard_untouched_projects(self):
        """At the end of the program — every project still only looked at; and every empty draft."""
        removed = []
        for path in list(getattr(self, 'project_sessions', ())):
            if Path(path).resolve() in self.viewed_projects() or self.empty_draft(path):
                from azimuth import crystal_projects

                try:
                    if not crystal_projects.is_crystal(path):
                        self.save_research_project(path)  # an edit not yet written keeps it (project_changed)
                    else:
                        self.session_registry().close(projects.Project.view(path).data['id'], save=True)
                except (OSError, ValueError, KeyError):
                    continue
                if self.discard_untouched_project(path):
                    removed.append(Path(path))
                    self.project_sessions.remove(path)
        return removed

    def save_project_tab(self, folder=None, name=None):
        """«Сохранить» of a draft (PROJECT_RUNTIME_GUIDE.md §1): the name is confirmed — the project already has
        its permanent folder, nothing is copied; saving again writes the same folder. folder: «Перенести проект» — the
        folder is moved there whole (the same id), refused while a calculation of the project runs."""
        from PySide6.QtWidgets import QInputDialog
        path = self.ensure_project_tab()
        self.attach_project_placeholder()
        project = projects.Project.view(path)
        if not project.data.get('draft') and folder is None and name is None:
            return self.save_research_project()
        if name is None:
            name, ok = QInputDialog.getText(self, tr('Сохранить проект'), tr('Название проекта'), text=project.data['name'])
            if not ok:
                return None
        name = name.strip()
        if not name:
            return None
        self.keep_project(path)  # saved under a name — kept
        self.save_research_project()
        new_path = self.move_project_tab(folder) if folder is not None else path
        with projects.edit(new_path) as saved:
            saved.data.update(name=name, draft=False, named=True)  # named — molecules added keep it
        for doc in self.all_documents():
            if doc.research_project_id == project.data['id'] and Path(doc.research_project_path).resolve() == new_path:
                doc.dirty = False
        self.dirty = False
        self.remember_recent('molecule', new_path)
        self.refresh_project_navigation()
        return str(new_path)

    AUTO_NAMED = 'auto_named'

    @staticmethod
    def auto_name(molecules):
        """«Вода» for one molecule, «Вода и ещё 2» for three; «H2O · teaching-demo.out» — «H2O»; '' without a name."""
        first = str(molecules[0].get('name') or '').split(' · ')[0].strip() if molecules else ''
        if not first:
            return ''
        return first if len(molecules) == 1 else tr('{} и ещё {}').format(first, len(molecules) - 1)

    def auto_name_project(self, path=None):
        """A project of molecules still called «Новый проект» — never named by the user («Сохранить» sets named), never
        named so before — takes the name of its molecules when it first has some (auto_name), once: the molecules added
        later keep it, and a name the user gives replaces it. A crystal is named by its CIF already. Its folder «Новый
        проект (N)» is renamed after the action under way ends (rename_project_folder): a function that saved the
        project may still hold its path. The name given, or None."""
        from azimuth import crystal_projects

        path = Path(path).resolve() if path else self.research_path()
        if path is None or path != self.research_path():
            return None
        try:
            project = projects.Project.view(path)
        except (OSError, ValueError, KeyError):
            return None
        data = project.data
        if (data.get('named') or data.get(self.AUTO_NAMED) or data.get('name') not in (tr('Новый проект'), '')
                or not project.molecules or crystal_projects.is_crystal(path)):
            return None
        name = self.auto_name(project.molecules)
        if not name:
            return None
        with projects.edit(path) as named:
            named.data.update(name=name, **{self.AUTO_NAMED: True})
        self.refresh_project_navigation()
        from PySide6.QtCore import QTimer

        QTimer.singleShot(0, lambda: self.rename_project_folder(path))
        return name

    FORMULA_NAME = r'(?:[A-Z][a-z]?\d*)+'  # a name that is a formula (C6H14, H2O, C8H10N4O2)

    def name_found(self, name):
        """The name found by «Назвать» (IUPAC, the table of the
        program, PubChem) becomes the name of the molecule of the project shown — when its name was given by the
        program (its formula, «формула · файл») or by an earlier search; a name the user gave stays. A project of that
        one molecule called as it was takes the name too (its folder stays). True when renamed."""
        import re

        document = self.document() if hasattr(self, 'document') else None
        ident = getattr(document, 'research_molecule_id', '') if document is not None else ''
        path = self.research_path() if hasattr(self, 'research_path') else None
        if not name or not ident or ident == NEW_ROW or path is None:
            return False
        try:
            view = projects.Project.view(path)
            entry = view.entry(ident)
            if entry.get('conformer_of'):
                return False
            old = str(entry.get('name') or '')
            molecule, _ = view.read_structure(entry['structure'])
            formula = molecule.formula if molecule.atoms else ''
            given = not (entry.get('name_source') == 'search' or not old or re.fullmatch(self.FORMULA_NAME, old)
                         or (formula and (old == formula or old.startswith(formula + ' · '))))
            if given or old == name:
                return False
            with projects.edit(path) as project:
                target = project.entry(ident)
                target['name'], target['name_source'] = name, 'search'
                if len(project.molecules) == 1 and project.data.get('name') in (old, formula):
                    project.data['name'] = name
        except (OSError, ValueError, KeyError, StopIteration):
            return False
        for each in self.all_documents():
            if getattr(each, 'research_molecule_id', '') == ident and each.title in (old, formula, ''):
                each.title = name
        self.refresh_project_navigation()
        self.notify(tr('Молекула проекта теперь называется «{}».').format(name), 8000)
        return True

    def follow_formula(self, path=None):
        """A molecule called by a formula that is not its own any more takes its formula; a project of one molecule
        called as that molecule was takes its new name too. A name that is not a formula stays.
        The folder of the project stays. The new name of the project, or None."""
        import re

        from azimuth import crystal_projects

        path = Path(path).resolve() if path else self.research_path()
        if path is None or not Path(path).is_file():
            return None
        try:
            if crystal_projects.is_crystal(path):
                return None
            view = projects.Project.view(path)
            renamed = {}
            for entry in view.molecules:
                old = str(entry.get('name') or '')
                if not re.fullmatch(self.FORMULA_NAME, old):
                    continue
                molecule, _ = view.read_structure(entry['structure'])
                formula = molecule.formula if molecule.atoms else ''
                if formula and re.fullmatch(self.FORMULA_NAME, formula) and formula != old:
                    renamed[entry['id']] = (old, formula)
            if not renamed:
                return None
            project_name = None
            with projects.edit(path) as project:
                for entry in project.data.get('molecules', []):
                    if entry.get('id') in renamed:
                        entry['name'] = renamed[entry['id']][1]
                molecules = project.data.get('molecules', [])
                if len(molecules) == 1 and project.data.get('name') == renamed.get(molecules[0].get('id'), ('',))[0]:
                    project.data['name'] = project_name = molecules[0]['name']
        except (OSError, ValueError, KeyError):
            return None
        for document in self.all_documents():
            ident = getattr(document, 'research_molecule_id', '')
            if ident in renamed and document.title == renamed[ident][0]:
                document.title = renamed[ident][1]
        self.refresh_project_navigation()
        return project_name

    def rename_project_folder(self, path):
        """The folder «Новый проект (N)» of the active project named after the project (move_project_tab: the same id,
        the relative paths inside stay); not while a calculation of it runs. The new path or None."""
        import re

        from azimuth.project_folders import folder_name, new_project_folder

        path = Path(path)
        if path != self.research_path() or not path.is_file():
            return None
        name = str(projects.Project.view(path).data.get('name') or '')
        default = folder_name(tr('Новый проект'))
        if not name or name == tr('Новый проект') or not re.fullmatch(re.escape(default) + r'( \(\d+\))?', path.parent.name):
            return None
        target = new_project_folder(path.parent.parent, name)
        try:
            moved = self.move_project_tab(target)
        except (ValueError, OSError):  # a calculation runs, the folder is held: it stays, the name is the project's
            try:
                target.rmdir()
            except OSError:
                pass
            return None
        self.refresh_project_navigation()
        return moved

    def move_project_tab(self, folder):
        """«Перенести проект»: the folder of the active project moved to folder (empty or new; the same id,
        the relative paths inside stay valid). Refused while a calculation of the project runs or is being sent: its
        job writes into the old folder (PROJECT_RUNTIME_GUIDE.md §11)."""
        path = self.research_path()
        target = Path(folder).resolve()
        source = path.parent
        if target == source:
            return path
        if source in target.parents or (target.exists() and any(target.iterdir())):
            raise ValueError(tr('Выберите пустую папку вне исходного проекта.'))
        project = projects.Project.view(path)
        if any(a['state'] in ('running', 'waiting', 'sent', 'searching') for e in project.molecules for a in e['attempts']):
            raise ValueError(tr('Перед переносом проекта завершите или остановите его расчёты.'))
        self.save_research_project()
        self.session_registry().close(project.data['id'], save=False)
        if target.exists():
            target.rmdir()
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(target))
        new_path = target / projects.MANIFEST
        for doc in self.all_documents():
            if doc.research_project_id == project.data['id'] and Path(doc.research_project_path).resolve() == path:
                doc.research_project_path = str(new_path)
        self.project_sessions = [new_path if p == path else p for p in self.project_sessions]
        if path.resolve() in self.viewed_projects():  # the name given by the program moves the folder
            self.viewed_projects().discard(path.resolve())
            self.viewed_projects().add(new_path.resolve())
        self._research_path = new_path
        for key in ('project_last_molecule', 'project_empty_documents'):
            table = getattr(self, key, None)
            if isinstance(table, dict) and str(path) in table:
                table[str(new_path)] = table.pop(str(path))
        return new_path

    def refresh_project_structures(self):
        """Keep the existing structure-set/RDKit interfaces backed by the active project's same records."""
        if not self.research_path():
            return
        # only the flat ones of the project for the molecule shown (no set on «Структуры» of the drawer any
        # more; the queue, «Сделать 3D», the inputs of the set read the project itself)
        project = projects.Project.view(self.research_path())
        self.document().structure_flat = tuple(project.read_structure(entry['structure'])[0]
                                               for entry in project.molecules if entry.get('flat'))

    def make_project_3d(self):
        from azimuth.tasks import run_waiting
        from modules.compass.chemistry import embed3d

        self.save_research_project()
        project = projects.Project.view(self.research_path())
        # only the flat (2D) ones, or the molecule of the tab — never all of them (the optimized geometries and
        # the complexes with an ion, whose ion RDKit would throw anywhere, were made anew)
        current = getattr(self.document(), 'research_molecule_id', '')
        pending = getattr(self, '_pending_3d', None)
        if pending:  # the flat ones of the files just opened
            entries = [e for e in projects.queueable(project) if e['id'] in pending]
        elif project.data.get('mode') == 'batch':  # the flat ones among those with a tick
            chosen = set(self.selected_project_molecules())
            entries = [e for e in projects.queueable(project) if e.get('flat') and e['id'] in chosen]
        else:  # the molecule chosen
            entries = [e for e in projects.queueable(project) if e['id'] == current]
        if not entries:
            self.notify(tr('Плоских (2D) структур в проекте нет — делать объёмными нечего.'), 10000)
            return 0
        python = self.opening_tool.rdkit_python()
        if python is None:
            return 0
        molecules = [project.read_structure(e['structure'])[0] for e in entries]
        charges = [e.get('formal', ()) for e in entries]
        try:
            made = run_waiting(self, tr(f'RDKit: объёмные структуры ({len(molecules)})…'),
                               lambda step: embed3d.run(python, molecules, charges, step=step), len(molecules))
        except InterruptedError:
            return 0
        except (OSError, ValueError) as exc:
            self.error(exc)
            return 0
        changed = {}
        with projects.edit(project.path) as fresh:
            for entry, (molecule, ok, note) in zip(entries, made):
                if not ok:
                    continue
                stored = fresh.entry(entry['id'])
                stored['structure'].update(xyz=molecule.xyz(), bonds=molecule.bonds)
                stored['flat'] = False
                changed[entry['id']] = molecule
        session = self.project_session(project.path)  # an older edit kept there must not come back
        for ident in changed:
            session.discard(ident)
        for document in self.all_documents():
            if (document.research_project_id == project.data['id']
                    and Path(document.research_project_path).resolve() == project.path
                    and document.research_molecule_id in changed):
                molecule = changed[document.research_molecule_id]
                if document is self.document():
                    self.load_molecule(molecule)
                else:
                    document.undo.append(document.molecule)
                document.molecule = molecule
                document.dirty = False
        self.dirty = False
        self.refresh_project_structures()
        self.refresh_project_navigation()
        failures = [note for _, ok, note in made if not ok]
        self.notify(tr(f'RDKit: объёмных структур {len(changed)} из {len(made)}.') +
                    (' ' + '; '.join(failures[:3]) if failures else ''), 15000)
        return len(changed)

    def loose_drawn_documents(self):
        """T03: the tabs of molecules with unsaved edits that belong to no project and to no file of their own
        (a molecule drawn on the empty first tab) — what «Не сохранять» at the exit used to lose."""
        if not hasattr(self, 'documents'):
            return []
        # the tab shown is read from the window as it is: store_document would leave a trajectory being browsed (its
        # own structure back on the model — an edit), so it is not called here
        shown = self.document()
        found = []
        for doc in self.all_documents():
            here = doc is shown
            molecule = self.own_molecule() if here else doc.molecule
            dirty = self.dirty if here else doc.dirty
            own_file = getattr(self, 'project_path', None) if here else getattr(doc, 'project_path', None)
            if (getattr(doc, 'kind', 'molecule') == 'molecule' and dirty and molecule is not None and molecule.atoms
                    and not getattr(doc, 'research_project_id', '') and not own_file):
                found.append(doc)
        return found

    def keep_drawn_as_drafts(self, documents):
        """Scenario T03 (PROJECT_RUNTIME_GUIDE.md §1, §13): each of these tabs, still in no project, becomes a draft
        «Новый проект» in the projects folder — the empty draft that owns the tab when there is one — with the
        molecule as it is now; the last draft is the recent file (shown «· черновик»). Written through the session of
        the project, at once. Returns the paths of the drafts."""
        from azimuth.core import Calculation
        from azimuth.project_folders import new_project_folder
        from azimuth.runtime.session import MoleculeRecord

        shown = self.document() if hasattr(self, 'document') else None
        kept = []
        for doc in documents:
            here = doc is shown
            own_file = getattr(self, 'project_path', None) if here else getattr(doc, 'project_path', None)
            if getattr(doc, 'research_project_id', '') or own_file:
                continue  # saved meanwhile (a file of its own, a project)
            molecule = self.own_molecule() if here else doc.molecule
            if molecule is None or not molecule.atoms:
                continue
            owner = next((Path(key) for key, d in getattr(self, 'project_empty_documents', {}).items()
                          if d is doc and Path(key).is_file()), None)
            if owner is None:
                folder = new_project_folder(self.projects_root('molecule'), tr('Новый проект'))
                project = projects.Project.create(folder)
                project.data.update(name=tr('Новый проект'), draft=True)
                project.save()
                owner = project.path
            calc = self.calculation() if here and hasattr(self, 'calculation') else doc.calculation
            if calc is None:
                calc = Calculation()
            constraints = tuple(getattr(self, 'constraints', ()) or ()) if here else tuple(doc.constraints or ())
            labels = dict(getattr(self.viewer, 'custom_labels', {}) or {}) if here else dict(doc.labels or {})
            kind = self.program_kind() if hasattr(self, 'program_kind') else 'orca'
            formal = tuple(doc.file_formal) if len(getattr(doc, 'file_formal', ()) or ()) == len(molecule.atoms) else ()
            session = self.project_session(owner)
            ident = session.add_molecules([MoleculeRecord(molecule, calc, kind, doc.title or molecule.title,
                                                          constraints, labels, formal,
                                                          False)], naming=False)[0]
            doc.research_project_id, doc.research_molecule_id = session.project_id, ident
            doc.research_project_path = str(owner)
            doc.dirty = False
            if doc is shown:
                self.dirty = False
            kept.append(owner)
        for path in kept:
            self.remember_recent('molecule', path)
        return kept

    # -- «Новая молекула» in a project ------------------------------------------------------------------------
    def _pending_key(self, path):
        """The key of project_new_documents — the id of
        the project, not its path: the folder «Новый проект (N)» is renamed after its first molecule (auto_name_project,
        move_project_tab) while «Новая молекула» waits, and the empty molecule was not found under the new path —
        what was drawn in it was left out of the project."""
        try:
            return projects.Project.view(path).data['id']
        except (OSError, ValueError, KeyError):
            return str(path)

    def pending_project_molecule(self, path=None):
        """The document of «Новая молекула» of the project (the current one when path is None) while nothing is drawn
        in it — a row «Новая молекула» of its list; None when there is none (drawn: it is a molecule of the project)."""
        path = path or self.research_path()
        document = getattr(self, 'project_new_documents', {}).get(self._pending_key(path)) if path else None
        if document is None or document not in getattr(self, 'documents', ()) or document.research_molecule_id:
            return None
        return document

    def new_project_molecule(self):
        """«Файл → Новая молекула» (⌘N) in a tab of a project of molecules — an empty molecule
        of the project: a row «Новая молекула» in its list, chosen, the field empty for building; the molecule shown
        before stays as it was. The row becomes a molecule of the project (project.qcc) with its first atom
        (attach_project_placeholder); left empty, it is not written anywhere. → the document, or None outside a project
        of molecules (the caller then empties the tab, as before)."""
        from azimuth import crystal_projects

        path = self.research_path()
        if path is None or crystal_projects.is_crystal(path) or getattr(self, 'document_kind', 'molecule') != 'molecule':
            return None
        shown = self.document()
        own = Path(getattr(shown, 'research_project_path', '') or '.').resolve() == Path(path).resolve()
        if not own and self.project_empty_documents.get(str(path)) is not shown:
            return None
        self.attach_project_placeholder()  # the molecule drawn in an empty project is its first one
        shown = self.document()
        if not self.own_molecule().atoms and not shown.research_molecule_id:
            document = shown  # the tab is empty already: it is the new molecule (the placeholder of an empty project)
        else:
            self.save_research_project(path)
            document = self.pending_project_molecule(path)
            if document is not None:
                self.switch_document(self.documents.index(document))
            else:
                document = self.new_document(tr('Новая молекула'))
                session = self.project_session(path)
                document.research_project_id, document.research_molecule_id = session.project_id, ''
                document.research_project_path = str(path)
        if self.project_empty_documents.get(str(path)) is not document:
            self.project_new_documents[self._pending_key(path)] = document
        self._research_path = Path(path)
        self.refresh_project_navigation()
        return document

    def drop_pending_project_molecule(self, path=None):
        """The empty molecule of «Новая молекула» leaves the list; its tab closes (a molecule of the project is
        shown instead), or, in a project with no molecule, it stays as its empty tab. True when there was one."""
        path = Path(path or self.research_path())
        document = self.pending_project_molecule(path)
        if document is None:
            return False
        self.project_new_documents.pop(self._pending_key(path), None)
        document.dirty = False
        project = projects.Project.view(path)
        if not project.molecules:
            self.project_empty_documents[str(path)] = document
        else:
            if document is self.document():
                self.dirty = False
                last = self.project_last_molecule.get(str(path))
                ident = last if any(e['id'] == last for e in project.molecules) else project.molecules[0]['id']
                self.open_project_molecule(ident, stay=True)
            if document in self.documents:
                self.close_document(self.documents.index(document))
        self._research_path = path
        self.refresh_project_navigation()
        return True

    def attach_project_placeholder(self):
        """A newly drawn molecule belongs to the empty project tab that owns its document, not to another tab.
        Also the molecule of «Новая молекула» of a project (new_project_molecule)."""
        path = self.research_path()
        if not path or self.document().research_molecule_id or not self.own_molecule().atoms:
            return
        document = self.document()
        pending = self.pending_project_molecule(path) is document
        if not pending and self.project_empty_documents.get(str(path)) is not document:
            return
        new = tr('Новая молекула')
        # its own name (a molecule of the library) or its formula, not «Новая молекула»
        if document.title in ('', new):
            title = self.own_molecule().title
            document.title = title if title not in ('', new) else self.own_molecule().formula
        if pending:
            self.project_new_documents.pop(self._pending_key(path), None)
            self.add_current_to_project()
            self.save_research_project()
            self.refresh_project_navigation()
            return
        self.add_current_to_project()  # the empty project with its first molecule drawn
        self.save_research_project()  # the first molecule of a draft on disk — it names the project
        self.refresh_project_navigation()
