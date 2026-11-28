"""Project workflow for Studio: portable folders, explicit membership and single/batch attempt recording.

No calculation is started by creating/opening/importing a project or preparing its queue. Existing calculations
are copied on explicit import. A running job's project link is written separately from server job.json, and
metadata failures are reported without re-submission. Project data lives in projects.py, Qt views in project_view.py.
"""

from dataclasses import asdict, replace
import os
from pathlib import Path
from uuid import uuid4

from azimuth.core import read_project, project_constraints, project_labels
from azimuth.i18n import tr
from azimuth import projects
from azimuth.runtime import lifecycle, runs


from azimuth.project_navigation import ProjectNavigation



def attempt_of_link(path, link, job):
    """Lifecycle.Attempt of a calculation of a project from its link (project-link.json)."""
    return lifecycle.Attempt(Path(job.spec.folder), Path(job.spec.output), link.get('kind', 'orca'),
                             link.get('place', ''), Path(path), link['molecule'], link['attempt'], link.get('input'))

class ProjectActions(ProjectNavigation):
    # -- the open project is a ProjectSession --------
    def session_registry(self):
        registry = getattr(self, '_session_registry', None)
        if registry is None:
            from azimuth.runtime.session import SessionRegistry

            registry = self._session_registry = SessionRegistry()
        return registry

    def project_session(self, path=None):
        """The session of the project of path (the active one when None), or None outside a project."""
        path = Path(path) if path else self.research_path()
        if path is None:
            return None
        session = self.session_registry().open(path)
        other = getattr(session, 'read_only', None)
        if other and not getattr(session, '_read_only_said', False) and hasattr(self, 'notify'):
            session._read_only_said = True  # said once — the project is written by another window
            self.notify(tr('Проект открыт для записи в другом окне Азимута ({}, процесс {}). Здесь — только '
                           'просмотр: закройте его там, чтобы менять здесь.').format(other.get('host', '?'),
                                                                                  other.get('pid', '?')), 15000)
        return session

    def push_project_documents(self, session, molecules_only=False):
        """The editors give their state to the session: every document of a molecule of this project — the one on
        screen with what its table holds now. molecules_only: the coordinates only (an export reads, it does not take
        the settings of the window)."""
        self.follow_adopted_geometries(session)  # never give back the structure before an optimization
        with session.held():  # the project looked at once for all the tabs, not once for each
            return self._push_documents(session, molecules_only)

    def _push_documents(self, session, molecules_only):
        shown = self.document() if hasattr(self, 'document') else None
        ids = set(session.ids())
        where = session.path
        for document in self.all_documents():
            ident = getattr(document, 'research_molecule_id', '')
            if (ident not in ids or getattr(document, 'research_project_id', None) != session.project_id
                    or not document.research_project_path
                    or Path(document.research_project_path).resolve() != where):
                continue
            molecule = self.own_molecule() if document is shown else document.molecule
            if molecule is None or not molecule.atoms:
                continue
            if molecules_only:
                session.edit_molecule(ident, molecule=molecule)
                continue
            formal = tuple(document.file_formal) if len(document.file_formal) == len(molecule.atoms) else ()
            changes = dict(molecule=molecule, constraints=tuple(document.constraints or ()), labels=document.labels,
                           formal=formal, flat=any(m.atoms == molecule.atoms for m in document.structure_flat))
            if document.calculation is not None:  # None: the form of Sextant was never stored for it — as saved
                changes['calc'] = document.calculation
            if document.program:
                changes['kind'] = document.program
            session.edit_molecule(ident, **changes)
        return session

    def follow_adopted_geometries(self, session=None):
        """The tabs of the molecules whose optimization gave them its geometry (projects.adopt_geometry) take
        it — the one on screen through the model (Undo gives back the structure before), the others in their document.
        A tab with edits not saved keeps them (told once). Returns the ids taken."""
        from dataclasses import replace as _replace

        session = session or self.project_session()
        if session is None:
            return []
        project = projects.Project.view(session.path)
        shown = self.document() if hasattr(self, 'document') else None
        taken = []
        for document in self.all_documents():
            ident = getattr(document, 'research_molecule_id', '')
            if (not ident or getattr(document, 'research_project_id', None) != session.project_id
                    or not document.research_project_path
                    or Path(document.research_project_path).resolve() != session.path):
                continue
            try:
                entry = project.entry(ident)
            except ValueError:
                continue
            marker = entry.get('adopted')
            if not marker or getattr(document, 'adopted_from', '') == marker:
                continue
            document.adopted_from = marker
            dirty = self.dirty if document is shown else document.dirty
            if dirty:
                self.notify(tr('Оптимизированная геометрия «{}» не подставлена: во вкладке есть несохранённые правки. '
                               'Её можно взять в Спектре — «Взять геометрию из результата».').format(entry['name']), 12000)
                continue
            molecule, _ = project.read_structure(entry['structure'])
            if document is shown:
                if getattr(self, 'browsing', False) and hasattr(self, 'trajectory_tool'):
                    self.trajectory_tool.leave_trajectory()
                own = self.molecule
                if own is not None and [a.symbol for a in own.atoms] == [a.symbol for a in molecule.atoms]:
                    molecule = _replace(molecule, title=own.title, bonds=own.bonds)
                self.load_molecule(molecule, record=True)
                self.dirty = document.dirty = False
            else:
                if document.molecule is not None:
                    document.undo.append(document.molecule)
                document.molecule = _replace(molecule, title=document.molecule.title) if document.molecule else molecule
            session.discard(ident)
            taken.append(ident)
        return taken

    def research_path(self):
        path = getattr(self, '_research_path', None)
        return Path(path) if path and Path(path).is_file() else None

    def research_document_path(self):
        """The open project when the tab in front is one of its molecules, else None: the other tabs keep their own
        .qcc files and jobs folder — opening a project does not draw them into it."""
        path = self.research_path()
        if path is None or not hasattr(self, 'document'):
            return None
        own = getattr(self.document(), 'research_project_path', '')
        return path if own and Path(own).resolve() == path.resolve() else None

    def create_research_project(self, folder=None):
        from PySide6.QtWidgets import QFileDialog

        if folder is None:
            folder = QFileDialog.getExistingDirectory(self, tr('Папка нового проекта'), str(Path.home()))
        if not folder:
            return None
        try:
            from modules.sextant.runner import latin_path

            if not latin_path(folder):
                raise ValueError(tr('Для расчётов в Windows выберите путь из латинских букв.'))
            if self.research_path():
                self.save_research_project()
            project = projects.Project.create(folder)
            self._research_path = project.path
            self.register_project_tab(project.path)
            if self.coordinate_tool.table_molecule().atoms:
                self.add_current_to_project()
            self.remember_recent('molecule', project.path)
            return project.path
        except (OSError, ValueError) as exc:
            self.error(exc)
            return None

    def open_research_project(self, path, stay=False):
        """stay: the section on screen stays (a queue of the project taken up in Sextant)."""
        from azimuth.tasks import held

        if held():  # a work goes on in this document (azimuth.tasks.run_waiting)
            return None
        try:
            from azimuth import crystal_projects

            if crystal_projects.is_crystal(path):  # a crystal project — its tab of «Кристалл»
                target = Path(path) / projects.MANIFEST if Path(path).is_dir() else Path(path)
                if target.resolve() not in self.project_sessions:
                    self.project_sessions.append(target.resolve())
                self.activate_crystal_project(target)
                if hasattr(self, 'file_tool'):  # «Недавние файлы» list the projects of crystals too
                    self.file_tool.note_recent(target, document=False)
                return projects.Project.view(target)
            if self.research_path():
                self.save_research_project()
            project = projects.refresh(path)
            self._research_path = project.path
            self.register_project_tab(project.path)
            if getattr(project, 'skipped', None):
                self.notify(tr('Очереди не прочитаны или связаны с другим проектом — пропущены: ')
                            + ', '.join(project.skipped), 15000)
            self.remember_recent('molecule', project.path)
            if project.molecules:
                self.open_project_molecule(project.molecules[0]['id'], stay=stay)
            self.watch_server_attempts_later(project)
            return project
        except (OSError, ValueError, KeyError, StopIteration) as exc:
            self.error(exc)
            return None

    def watch_server_attempts_later(self, project):
        """The calculations of the
        project sent to a server whose end was not seen are watched again by themselves — after the project is on
        screen (the server may be slow to answer)."""
        found = projects.server_attempts(project, skip=self._server_watched())
        if not found or not hasattr(self, 'run_tool'):
            return
        try:
            from PySide6.QtCore import QTimer
        except ImportError:
            return
        QTimer.singleShot(0, lambda: self.watch_server_attempts(found))

    def _server_watched(self):
        """The folders taken up in this session and
        those watched now."""
        tried = self.__dict__.setdefault('_server_tried', set())
        going = {str(Path(j.spec.folder)) for j in (self.running_jobs() if hasattr(self, 'running_jobs') else [])
                 if getattr(j, 'spec', None) is not None}
        return tried | going

    def watch_server_attempts(self, found):
        """Every calculation of the project on a server whose end was not seen is watched again, the newest in the card
        of Sextant, the others in their own windows aside (run_actions.park_server_job) — the calculations on a server
        go on side by side; only the newest was taken up, the others waited in «История расчётов» (ROADMAP, Sextant
        7). A queue going on on the server is waited for: then they stay there. Returns the jobs taken up."""
        found = [rec for rec in found if rec['folder'] not in self._server_watched()]
        if not found:
            return []
        jobs = []
        # the oldest first: each next one moves the one before aside, the newest stays in the card
        for rec in reversed(found):
            self._server_tried.add(rec['folder'])
            if self.run_tool.job_running('server') and not self.run_tool.can_park_server_job():
                left = len(found) - len(jobs)
                self.notify(tr('Расчётов проекта на сервере, которые ещё не закончены: {} — за ними можно следить из '
                               '«Расчёт → История расчётов…», когда кончится очередь на сервере.').format(left), 12000)
                break
            job = self.run_tool.resume_history(rec, quiet=True)
            if job is not None:
                jobs.append(job)
                taken = rec
        if len(jobs) == 1:
            self.notify(tr('Расчёт «{}» проекта шёл на сервере {} — подключаюсь, чтобы посмотреть, как он идёт.')
                        .format(taken['title'], taken['place']), 10000)
        elif jobs:
            self.notify(tr('Расчётов проекта на сервере: {} — подключаюсь ко всем, чтобы посмотреть, как они идут; '
                           'новый — в окне Секстанта, остальные — в своих окнах (песочные часы вверху).').format(len(jobs)),
                        12000)
        return jobs

    def show_research_project(self):
        """«История и файлы проекта…» (the button of the pane, «Файл → Молекулы и расчёты проекта…»). Only on
        request — it opened by itself when a project was made or opened."""
        from azimuth.project_view import ProjectDialog

        dialog = getattr(self, '_project_dialog', None)
        if dialog is None:
            dialog = ProjectDialog(self)
            self._project_dialog = dialog
        else:
            dialog.refresh()
        dialog.show()
        dialog.raise_()
        return dialog

    def add_current_to_project(self):
        path = self.research_path()
        if path is None:
            raise ValueError(tr('Сначала создайте или откройте проект.'))
        self.store_document()
        document = self.document()
        molecule, calc = self.own_molecule(), self.calculation()
        if not molecule.atoms:
            raise ValueError(tr('Текущая структура пуста.'))
        # through the session of the project — an edit kept there is never written over by an older one
        from azimuth.runtime.session import MoleculeRecord

        session = self.project_session(path)
        formal = tuple(document.file_formal) if len(document.file_formal) == len(molecule.atoms) else ()
        flat = any(m.atoms == molecule.atoms for m in document.structure_flat)
        if (getattr(document, 'research_project_id', None) == session.project_id
                and getattr(document, 'research_molecule_id', '') in session.ids()
                and Path(document.research_project_path).resolve() == session.path):
            ident = document.research_molecule_id
            session.edit_molecule(ident, molecule=molecule, calc=calc, kind=self.program_kind(),
                                  constraints=tuple(self.constraints), labels=self.viewer.custom_labels, formal=formal,
                                  flat=flat)
            session.save()
        else:
            ident = session.add_molecules([MoleculeRecord(molecule, calc, self.program_kind(),
                                                          document.title or molecule.title, tuple(self.constraints),
                                                          self.viewer.custom_labels, formal, flat)], naming=False)[0]
            document.research_project_id = session.project_id
            document.research_molecule_id = ident
        document.research_project_path = str(path)
        return ident

    def project_changed(self, session):
        """A document of the project of session has changes not yet written (its own dirty, or the window's
        for the one on screen)."""
        shown = self.document() if hasattr(self, 'document') else None
        for document in self.all_documents():
            if getattr(document, 'research_project_id', None) != session.project_id:
                continue
            if document.dirty or (document is shown and getattr(self, 'dirty', False)):
                return True
        return False

    def save_research_project(self, path=None):
        """The documents of the project give their state to its session, the session writes it (only the
        molecules changed; what a queue recorded meanwhile stays)."""
        path = Path(path) if path else self.research_path()
        if path is None:
            return None
        shown = self.document() if hasattr(self, 'document') else None
        if (hasattr(self, 'pending_project_molecule') and path == self.research_path() and shown is not None
                and not getattr(shown, 'research_molecule_id', '') and self.own_molecule().atoms
                and (self.pending_project_molecule(path) is shown or self.project_empty_documents.get(str(path)) is shown)):
            # «Новая молекула» drawn; also the molecule drawn in an empty project — a molecule of the project from now
            # on
            self.attach_project_placeholder()
        self.store_document()
        session = self.project_session(path)
        if hasattr(self, 'keep_project') and self.project_changed(session):
            self.keep_project(path)  # a project of files opened only to look at is kept once it changes
        self.push_project_documents(session)
        session.save()
        for document in self.all_documents():
            if (getattr(document, 'research_project_id', None) == session.project_id and document.research_project_path
                    and Path(document.research_project_path).resolve() == session.path
                    and document.molecule and document.molecule.atoms):
                document.dirty = False
        if getattr(self.document(), 'research_project_id', None) == session.project_id:
            self.dirty = False
        if hasattr(self, 'auto_name_project'):
            self.auto_name_project(path)  # a project nobody named takes the name of its molecules
        if hasattr(self, 'follow_formula'):
            self.follow_formula(path)  # a name that is a formula follows the molecule
        return str(path)

    def copy_research_project(self, folder=None):
        from PySide6.QtWidgets import QFileDialog

        if not self.research_path():
            return None
        self.save_research_project()
        if folder is None:
            folder = QFileDialog.getExistingDirectory(self, tr('Папка копии проекта'), str(Path.home()))
        if not folder:
            return None
        source = self.research_path().parent
        project = projects.Project.view(self.research_path())
        if any(a['state'] in ('waiting', 'running', 'sent', 'searching') for e in project.molecules for a in e['attempts']):
            raise ValueError(tr('Перед копированием проекта завершите или остановите его расчёты.'))
        target = Path(folder).resolve()
        if target == source or source in target.parents or (target.exists() and any(target.iterdir())):
            raise ValueError(tr('Выберите пустую папку вне исходного проекта.'))
        # projects.copy_project — a new id, «copied_from», without the writer lock of the original
        manifest = projects.copy_project(self.research_path(), target)
        with projects.edit(manifest) as copied:
            copied.data['name'] = target.name
        return self.open_research_project(manifest)

    def project_from_calculations(self, folder=None, name=None):
        """A folder of calculations of ORCA or Gaussian — each output with the files of its name — becomes a new project
        (project_import.build): its molecules, the records of their calculations with the files copied, the current ones
        with their results; the project is opened. Returns the path of project.qcc or None."""
        from PySide6.QtWidgets import QFileDialog

        from azimuth import project_import
        from azimuth.tasks import held

        if held():
            return None
        if folder is None:
            folder = QFileDialog.getExistingDirectory(self, tr('Папка с расчётами ORCA или Gaussian'),
                                                      str(Path.home()))
        if not folder:
            return None
        root = self.projects_root('molecule') if hasattr(self, 'projects_root') else Path(folder).parent
        try:
            manifest, report = project_import.build(root, name or Path(folder).name, [folder])
        except (OSError, ValueError) as exc:
            self.error(exc)
            return None
        self.open_research_project(manifest)
        done = sum(1 for _, outcome in report if outcome.startswith(tr('готово')))
        left = [f'{Path(o).name}: {outcome}' for o, outcome in report if not outcome.startswith(tr('готово'))]
        self.notify(tr('Проект «{}» из расчётов: {} с результатом из {}; файлы скопированы в папку проекта, исходные не '
                       'тронуты.').format(projects.Project.view(manifest).data.get('name', ''), done, len(report))
                    + (' ' + tr('Не взяты: ') + '; '.join(left[:3]) if left else ''), 15000)
        return manifest

    def open_output_in_its_project(self, path):
        """An output of a calculation of a project (projects.attempt_of_file) opens its project on that
        molecule — its calculations, its result — not a tab of its own (a draft «Новый проект» with the molecule of the
        file at the exit). True when it was such an output."""
        found = projects.attempt_of_file(path)
        if found is None:
            return False
        manifest, ident, attempt = found
        if self.open_research_project(manifest) is None:
            return True  # said why (a work goes on, an error)
        if self.document().research_molecule_id != ident:
            self.open_project_molecule(ident)
        project = projects.Project.view(manifest)
        entry = project.entry(ident)
        current = project.current(entry)
        name = project.data.get('name', '')
        document = self.document()
        if (current is None or current['id'] != attempt['id']) and attempt.get('usable'):
            # it is the current one of the molecule now, until a newer one gives a result
            try:
                with projects.edit(manifest) as edited:
                    chosen = edited.choose(ident, attempt['id'])
            except (OSError, ValueError, KeyError):
                chosen = False
            if chosen:
                number = next((k for k, a in enumerate(entry['attempts'], 1) if a['id'] == attempt['id']), 0)
                document.shown_attempt = None
                document.output = None  # read again: the result of the calculation now current
                if hasattr(self, 'show_project_result'):
                    self.show_project_result()
                if hasattr(self, 'refresh_project_navigation'):
                    self.refresh_project_navigation()
                self.notify(tr('Расчёт № {} — теперь текущий у молекулы проекта «{}»; следующий посчитанный расчёт '
                               'станет текущим сам.').format(number, name), 12000)
                self.navigate(2)
                return True
        if current is not None and current['id'] == attempt['id']:
            document.shown_attempt = None
            self.notify(tr('Это расчёт проекта «{}» — открыт проект, его молекула и этот результат.').format(name), 10000)
        else:
            # that calculation is shown in Spectrum, the current one stays the current one
            document.shown_attempt = attempt['id']
            number = next((k for k, a in enumerate(entry['attempts'], 1) if a['id'] == attempt['id']), 0)
            self.notify(tr('Расчёт № {} молекулы проекта «{}» — показан в Спектре; текущий результат молекулы прежний '
                           '(выбор молекулы в списке вернёт его).').format(number, name), 12000)
        if hasattr(self, 'show_project_result'):
            self.show_project_result()
        self.navigate(2 if document.shown_attempt or self.stack.currentIndex() == 2 else 0)
        return True

    def open_project_molecule(self, ident, stay=False):
        if hasattr(self, 'document'):
            self.document().shown_attempt = None  # the current result again (a calculation looked at)
        project = projects.Project.view(self.research_path())
        entry = project.entry(ident)
        if getattr(self, 'compass_mode', 'molecule') == 'crystal':
            self.crystal_tool.set_compass_mode('molecule')
        for index, document in enumerate(self.documents):
            if (getattr(document, 'research_project_id', None), getattr(document, 'research_molecule_id', None),
                    Path(document.research_project_path).resolve()) == (project.data['id'], ident, project.path):
                self.switch_document(index)
                self._follow_in_list()
                if not stay:
                    self.navigate(0)
                return document
        # the molecule as its session holds it — an edit not saved yet included (its tab was
        # closed, or «Сделать 3D» changed it), not what project.qcc kept
        state = self.project_session(project.path).structure(ident)
        molecule, calc = state.molecule, state.calc
        if not self.own_molecule().atoms and not self.document().research_molecule_id:
            document = self.document()
            document.title, document.named = entry['name'], True
            self.load_molecule(molecule, record=False)
        else:
            document = self.new_document(entry['name'], molecule)
        document.research_project_id, document.research_molecule_id = project.data['id'], ident
        document.research_project_path = str(project.path)
        document.file_formal = tuple(state.formal)
        document.structure_flat = (molecule,) if state.flat else ()
        self.apply_calculation(calc, state.kind, molecule.formula)
        self.constraints = list(state.constraints)
        self.viewer.constraints = list(self.constraints)
        self.viewer.custom_labels = state.labels
        if self.viewer.custom_labels and hasattr(self, 'custom_label_button'):  # the residues of a PDB shown
            self.viewer.show_custom = True
            self.custom_label_button.setChecked(True)
        self.dirty = document.dirty = False
        if entry.get('skeleton') and not self.undo_history:  # Ctrl+Z — the file without the added hydrogens
            from azimuth.core import read_xyz

            try:
                self.undo_history.append(read_xyz(entry['skeleton']))
            except ValueError:
                pass
        self._follow_in_list()
        if not stay:
            self.navigate(0)
        return document

    def _follow_in_list(self):
        """The list of the project shows the
        molecule just opened as its chosen row — opened from anywhere, not only by a click on its row (the row of
        «Новая молекула» stayed chosen, and choosing it again did nothing)."""
        if hasattr(self, 'refresh_project_navigation') and not getattr(self, '_project_refreshing', False):
            self.refresh_project_navigation()

    def import_project_structures(self, paths):
        """Use the current file-import rules: formal charges and optional skeleton hydrogens; preserve originals."""
        import shutil
        from modules.compass.chemistry import embed3d
        from modules.sextant.advice import guess_state

        records = []
        for path in map(Path, paths):
            if path.suffix.lower() == '.qcc':
                text = path.read_text(encoding='utf-8-sig')
                molecule, calc = read_project(text)
                records.append((path, molecule, calc, molecule.title or path.stem,
                                project_constraints(text), project_labels(text), (), False, {}, ''))
            else:
                rows = self.opening_tool.read_structures(path)
                properties = self.opening_tool.structure_properties(path, len(rows))
                residues = {}
                if self.opening_tool.file_kind(path) == 'pdb':  # the residues of a PDB as own labels, kept
                    from modules.compass.chemistry import formats

                    residues = formats.pdb_labels(formats.read_text(path))
                seen_names = {}
                file_kind = self.opening_tool.file_kind(path)
                input_state = None
                if file_kind in ('orca_input', 'gaussian_input'):
                    from modules.compass.chemistry import formats

                    reader = formats.read_orca_input if file_kind == 'orca_input' else formats.read_gaussian_input
                    _, charge, spin = reader(path.read_text(encoding='utf-8-sig'))
                    input_state = (charge, spin)
                for raw, props in zip(rows, properties):
                    molecule, name = raw[:2]
                    formal = tuple(raw[2]) if len(raw) > 2 else ()
                    filled = molecule if input_state else self.opening_tool.opened_with_hydrogens(molecule, formal)[0]
                    state = input_state or self.opening_tool.state_of_file(filled, formal)
                    charge, spin = state if state is not None else guess_state(filled)[:2]
                    formal += (0,) * (len(filled.atoms) - len(formal))
                    if not name:
                        formula = filled.formula.translate(str.maketrans('0123456789', '₀₁₂₃₄₅₆₇₈₉'))
                        seen_names[formula] = seen_names.get(formula, 0) + 1
                        name = formula + (f' · {seen_names[formula]}' if seen_names[formula] > 1 else '')
                    filled = replace(filled, title=name)
                    # the file as it was, when hydrogens were added — Ctrl+Z gives it back
                    skeleton = replace(molecule, title=name).xyz() if len(filled.atoms) != len(molecule.atoms) else ''
                    records.append((path, filled, replace(self.calculation(), charge=charge, multiplicity=spin),
                                    name or filled.formula, (), dict(residues) if len(rows) == 1 else {}, formal,
                                    embed3d.is_flat(molecule, filled), props, skeleton))
        # the files copied into the project, the molecules added by its session (one write, in order)
        from azimuth.runtime.session import MoleculeRecord

        session = self.project_session()
        project = projects.Project.view(session.path)
        sources, made = {}, []
        for path, molecule, calc, name, constraints, labels, formal, flat, props, skeleton in records:
            if path not in sources:
                target = project.root / 'structures' / uuid4().hex[:12] / path.name
                target.parent.mkdir(parents=True)
                shutil.copy2(path, target)
                sources[path] = project.relative(target)
            made.append(MoleculeRecord(molecule, calc, self.program_kind(), name, tuple(constraints), labels,
                                       tuple(formal), bool(flat), dict(props), sources[path], skeleton))
        session.add_molecules(made, naming=False)
        return len(records)

    def import_project_batch(self, folder):
        from azimuth.tasks import run_waiting

        path = self.research_path()
        def work(step):
            with projects.edit(path) as project:
                return project.import_batch(folder)
        return run_waiting(self, tr('Добавление пакета в проект…'), work, alone=False)

    def prepare_project_calculations(self, ids):
        from modules.sextant import batch, batch_retry

        self.save_research_project()
        project = projects.Project.view(self.research_path())
        entries = [project.entry(ident) for ident in ids]
        if any(e['structure'].get('constraints') for e in entries):
            raise ValueError(tr('Для структуры с ограничениями откройте её и запустите одиночный расчёт в Секстанте.'))
        if not entries:
            return None
        items = []
        for entry in entries:
            molecule, calc = project.read_structure(entry['structure'])
            current = project.current(entry)
            items.append(batch.BatchItem(entry['name'], molecule, calc.charge, calc.multiplicity,
                                          output=str(project.absolute(current['output'])) if current else '',
                                          props=dict(entry.get('props', {})), formal=tuple(entry.get('formal', ()))))
        _, calc = project.read_structure(entries[0]['structure'])
        parent = batch.Batch(entries[0]['kind'], calc, items, project.root, purpose='structures',
                             extra={'project': {'manifest': projects.MANIFEST, 'ids': ids}, 'project_selection': True})
        dialog = batch_retry.retry_dialog(self, parent, list(range(len(items))))
        dialog.setWindowTitle(tr('Расчёты выбранных молекул проекта'))
        self._batch_retry_dialog = dialog
        dialog.show()
        return dialog

    def bind_project_batch(self, queue):
        path = self.research_path()
        if path is None or queue.extra.get('project'):
            return
        project = projects.Project.view(path)
        try:
            project.relative(queue.folder)
        except ValueError:
            return  # an external saved queue is imported explicitly, never silently moved
        with projects.edit(path) as project:
            ids = []
            for item in queue.items:
                entry = project.add(item.molecule, replace(queue.calc, charge=item.charge, multiplicity=item.multiplicity),
                                    queue.kind, item.name)
                entry.update(props=dict(item.props), formal=list(item.formal))
                ids.append(entry['id'])
            origin = getattr(self.document(), 'research_molecule_id', '') if queue.purpose == 'conformers' else ''
            if origin and any(e['id'] == origin for e in project.molecules):  # a subgroup of the molecule
                projects.mark_conformers(project, origin, ids, [item.start_delta for item in queue.items])
        projects.attach(queue, path, ids)

    def register_project_job(self, job, calc, kind, place=None):
        """Single jobs only; batches synchronize via batch.json. Resume uses the existing relative link."""
        if getattr(self, 'batch', None) is not None:
            return
        folder = Path(job.spec.folder)
        from azimuth.runtime import records

        link = records.read(folder, 'project-link.json')  # the database of the project, else the file
        if isinstance(link, dict):
            path = (folder / link['manifest']).resolve()
        else:
            path = self.research_document_path()
            if path is None:
                return
            project = projects.Project.view(path)
            try:
                project.relative(folder)
            except ValueError:
                return
            ident = self.add_current_to_project()
            sent = runs.read(folder)  # the attempt of the submission record (remote_job.prepare_remote)
            link = {'manifest': os.path.relpath(path, folder), 'molecule': ident,
                    'attempt': sent.attempt_id if sent is not None else uuid4().hex,
                    'kind': kind, 'calculation': asdict(calc), 'place': place or '',
                    'input': project.structure(self.calculation_molecule(), calc, self.constraints, self.viewer.custom_labels)}
            records.write(folder, 'project-link.json', link)
        job._research_link = (path, link)
        # the explicit context of the attempt and its start — azimuth/runtime/lifecycle.py
        job._attempt = attempt_of_link(path, link, job)
        error = lifecycle.Lifecycle(self.preferences).record_start(job._attempt, calc)
        if error:
            raise ValueError(error)

    def attempt_of_job(self, job):
        """The attempt of a calculation (its project and ids when it is one of a project), else one of its
        folder alone — what azimuth/runtime/single_run.SingleRun.conclude records."""
        attempt = getattr(job, '_attempt', None)
        if attempt is None and getattr(job, '_research_link', None) is not None:
            attempt = attempt_of_link(*job._research_link, job)
        return attempt

    def finish_project_job(self, job, state):
        """The end of the attempt in its project, by its ids (lifecycle.Lifecycle.ended)."""
        attempt = self.attempt_of_job(job)
        if attempt is None:
            return
        ended = lifecycle.Lifecycle(None).ended(attempt, job, state=state, with_history=False)
        if ended.project_error:
            raise ValueError(ended.project_error)

    def project_qtaim(self, ids=None):
        from azimuth.tasks import run_waiting
        from modules.spectrum.wavefunction import batch_qtaim, field_tables

        project = projects.refresh(self.research_path())
        records = project.result_items(ids)
        eligible = [(e, a, i) for e, a, i in records if a['kind'] in batch_qtaim.KINDS]
        if not eligible:
            self.notify(tr('В проекте нет актуальных результатов с поддерживаемыми файлами волновой функции.'), 10000)
            return []
        program = self.property_tool.multiwfn_program()
        if program is None:
            return []
        cores = self.cores.value()
        try:
            results = run_waiting(self, tr('QTAIM результатов проекта…'),
                                  lambda step: batch_qtaim.analyse(program, [i for _, _, i in eligible],
                                                                  cores, step), len(eligible))
            tables = batch_qtaim.tables(results)
            tables['sources'] = ([tr('Молекула'), tr('Программа'), tr('Метод'), tr('Базис'), tr('Попытка'), tr('Файл')],
                                  [[i.name, a['kind'], a['calculation']['method'], a['calculation']['basis'],
                                    a['id'], a['output']] for e, a, i in eligible])
            written = field_tables.write_tables(project.root, 'project_qtaim', tables)
            count = sum(r.topology is not None for r in results)
            self.notify(tr('QTAIM проекта: результатов {ready} из {total}; неподдерживаемых актуальных расчётов: '
                           '{unsupported}. Таблицы в папке «Анализ».').format(
                               ready=count, total=len(eligible), unsupported=len(records) - len(eligible)), 15000)
            return written
        except InterruptedError:
            return []
        except (OSError, ValueError) as exc:
            self.error(exc)
            return []
