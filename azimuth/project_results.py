"""The results of the molecules of a project: shown in Spectrum, the conformers, a result of other data told, the
rows of a queue ended, preparing the project or its chosen molecules, reading files into a project. Methods of
ProjectNavigation (self is the window), kept here to make project_navigation.py shorter.

Split off azimuth/project_navigation.py (0.222.30).
"""

from pathlib import Path
from azimuth import projects
from azimuth.i18n import tr


def show_project_result(self):
    """Load the selected molecule's current result into Spectrum without replacing its editable input."""
    path = self.research_path()
    if path is None:
        return
    document = self.document()
    project = projects.Project.view(path)
    if document.research_project_id != project.data['id']:
        return
    entry = project.entry(document.research_molecule_id)
    self.load_project_conformers(project, entry)  # its conformers on the page «Конформеры» of ☰
    if entry.get('adopted') and hasattr(self, 'follow_adopted_geometries'):
        self.follow_adopted_geometries()  # its optimization gave it its geometry
    current = project.current(entry)
    # a calculation of the molecule chosen to be looked at (open_output_in_its_project — «Открыть результат» of
    # «История и файлы проекта», a file of it opened) instead of the current one
    chosen = getattr(document, 'shown_attempt', None)
    if chosen:
        current = next((a for a in entry.get('attempts', ()) if a['id'] == chosen and a.get('output')), current)
    if current is None:
        self.clear_result()
        self.result_tabs.setTabVisible(self.topology_tab, True)
        return
    output_path = project.absolute(current['output'])
    if document.output and Path(document.output[3] or '') == output_path:
        self.project_result_properties(document)  # read before, the buttons of Compass get it too
        return
    from azimuth.tasks import run_waiting
    def read(step):
        text = output_path.read_text(encoding='utf-8', errors='replace')
        return self.read_result(text, output_path), text, output_path.name, output_path
    try:
        document.output = run_waiting(self, tr('Чтение результата молекулы…'), read, alone=False)
        self.show_result(document.output)
        self.result_tabs.setTabVisible(self.topology_tab, True)
    except (OSError, ValueError) as exc:
        self.error(exc)
        return
    self.project_result_properties(document)
    self.say_result_mismatch(project, entry, document)
    if hasattr(self, 'trajectory_tool'):  # the steps of the result in the drawer of Compass (☰); the
        # structure of the molecule (its input, editable) stays on the model until a step is chosen
        self.trajectory_tool.load_trajectory(document.output[0], document.output[2])


def load_project_conformers(self, project, entry):
    """The conformers kept in the project under the molecule
    shown (or under the molecule of the conformer shown) go to the page «Конформеры» of the drawer — ☰ offers them
    again after a restart, as it did right after the search. Returns how many."""
    if not hasattr(self, 'trajectory_tool') or not hasattr(self, 'drawer'):
        return 0
    from dataclasses import replace

    try:
        root = projects.conformer_root(project, entry['id'])
        group = projects.conformers_of(project, root)
        if not group:
            return 0
        key = (str(project.path), root, tuple(e['id'] for e in group))
        if getattr(self, '_project_conformers_key', None) == key and len(self.drawer.conformers) == len(group):
            self.drawer.conformers_project = key  # kept by the tab (documents) — still the project's
            return len(group)
        rows = []
        for item in group:
            molecule, _ = project.read_structure(item['structure'])
            info = item.get('conformer') or {}
            rows.append((replace(molecule, title=item['name']), info.get('energy'), info.get('delta'),
                         info.get('share')))
        name = project.entry(root)['name']
    except (OSError, ValueError, KeyError):
        return 0
    self._project_conformers_key = key
    self.trajectory_tool.load_conformers(tuple(rows), tr('конформеры · ') + name)
    self.drawer.conformers_project = key  # a queue of Sextant takes the project's molecules, not these again
    self.trajectory_tool.update_result_button()
    return len(rows)


def say_result_mismatch(self, project, entry, document):
    """T23: the result shown was calculated for other data of the molecule than those of its tab now
    (an edit of the geometry, another charge, multiplicity, method or program) — said, never «fixed»: the result
    stays the one of its attempt. Returns the codes of projects.result_mismatch.
    Not while «Компас · Кристалл» is shown —
    the model there is a crystal, not the molecule of the result (an empty field read as «the geometry changed»);
    what was found before for the molecule is kept."""
    crystal_shown = getattr(self, 'compass_mode', 'molecule') == 'crystal' and self.stack.currentIndex() == 0
    if crystal_shown or getattr(self, 'document_kind', 'molecule') != 'molecule':
        return getattr(document, 'result_mismatch', ()) or ()
    molecule = None
    if document is self.document() and hasattr(self, 'own_molecule'):
        try:
            molecule = self.own_molecule()
        except (AttributeError, ValueError):
            molecule = None
    if molecule is None:
        molecule = getattr(document, 'molecule', None)
    if molecule is not None and not molecule.atoms:
        molecule = None
    differs = projects.result_mismatch(project, entry, molecule, getattr(document, 'calculation', None))
    document.result_mismatch = differs
    if differs:
        self.notify(tr('Результат «{}» посчитан для прежних данных молекулы, изменились: {}. Он остаётся '
                       'результатом своего расчёта; для новых данных запустите расчёт снова.').format(
            entry['name'], projects.mismatch_text(differs)), 12000)
    return differs


def project_result_properties(self, document):
    """the result of a molecule of the project read for Spectrum (show_project_result) gave Spectrum its output and
    files, but not the properties to Compass — the buttons «Атомы», «Связи», «Диполь и силы» stayed empty and
    offered to open a result. Now they get the properties of the result (charges, bond orders, the dipole) and its
    wavefunction for Multiwfn, as for a result opened from a file."""
    record = getattr(document, 'output', None)
    if not record or not hasattr(self, 'property_tool') or document is not self.document():
        return False
    output, _, source, _ = record
    crystal_shown = getattr(self, 'compass_mode', 'molecule') == 'crystal' and self.stack.currentIndex() == 0
    # not told over a crystal — the properties are of the molecule
    self.property_tool.set_result_properties(output.properties, source, announce=not crystal_shown)
    document.properties = (output.properties, source)
    return True


def project_queue_row_ended(self):
    """A row of a queue of the project is
    over (its record is in project.qcc already, Batch.save → projects.sync) — the list follows and the molecule
    shown gets its result in Compass (☰) and in Spectrum when it is the one that ended (show_project_result reads
    nothing again for an output it shows already). Sextant (index 1) is left alone."""
    if not self.research_path():
        return False
    self.refresh_project_navigation()
    index = self.stack.currentIndex()
    if index in (0, 2):
        self.show_project_result()
    return True


def open_project_topology(self):
    self.navigate(2)
    self.result_tabs.setTabVisible(self.topology_tab, True)
    self.result_tabs.setCurrentIndex(self.topology_tab)


def open_project_compass_result(self):
    self.show_project_result()
    if self.document().output:
        output, _, source, _ = self.document().output
        self.trajectory_tool.load_trajectory(output, source)
    self.navigate(0)
    self.project_menu_button.setChecked(False)
    self.slide_project_pane(False)
    self.trajectory_tool.set_trajectory_open(True)


def prepare_whole_project(self):
    path = self.ensure_project_tab()
    self.save_research_project()
    ids = [entry['id'] for entry in projects.queueable(projects.Project.view(path))]  # not the ion, …
    self.navigate(1)
    return self.prepare_project_calculations(ids)


def prepare_selected_project(self):
    ids = self.selected_project_molecules()
    self.navigate(1)
    return self.prepare_project_calculations(ids)


def add_project_files_dialog(self):
    from PySide6.QtWidgets import QFileDialog
    paths, _ = QFileDialog.getOpenFileNames(self, tr('Добавить молекулы в проект'), str(Path.home()), tr(self.OPEN_FILTER))
    if paths:
        return self.open_files_project(paths, append=True)


def open_files_project(self, paths, append=False):
    """Read structure files into one project; failed reads do not remove the previously open project."""
    from azimuth.tasks import held

    if held():  # a work goes on in this document (azimuth.tasks.run_waiting)
        return None
    self.ensure_molecule_tabs()
    paths = [Path(path) for path in paths]
    if append:
        self.ensure_project_tab()
        before = projects.Project.view(self.research_path())
        old_ids = {entry['id'] for entry in before.molecules}
    else:
        name = paths[0].stem if len(paths) == 1 else tr('Новый проект')
        self.new_project_tab(name)
        old_ids = set()
    try:
        self.import_project_structures(paths)
    except (ValueError, OSError) as exc:
        self.error(exc)
        return None
    if hasattr(self, 'file_tool'):  # «Недавние файлы» — the files opened, not the draft of the tab
        for path in reversed(paths):
            if path.is_file():
                self.file_tool.note_recent(path)
    with projects.edit(self.research_path()) as project:
        added = [entry for entry in project.molecules if entry['id'] not in old_ids]
        if append and len(old_ids) == 1 and added and not project.data.get('named'):  # a name chosen stays
            # a name given by the program grows with its molecules («Вода и ещё 2»)
            project.data['name'] = (self.auto_name(project.molecules) if project.data.get(self.AUTO_NAMED)
                                    else tr('Новый проект'))
        elif not append and len(paths) == 1:
            project.data['name'] = paths[0].stem
        # several files — the project takes the name of its molecules (auto_name_project)
    if append:
        self.keep_project(self.research_path())  # files added to a project: a change of it
    elif self.research_path() is not None:
        # a project of files opened only to look at leaves no folder in «Проекты» — discard_untouched_project at its
        # close
        self.viewed_projects().add(self.research_path().resolve())
    if added:
        self.open_project_molecule(added[0]['id'], stay=True)
    self.refresh_project_structures()
    self.refresh_project_navigation()
    self.show_project_molecules()
    flat = sum(bool(entry.get('flat')) for entry in added)
    if flat:
        # «Сделать объёмными» of Quill takes the flat ones just added, whatever the mode of the list
        self._pending_3d = {entry['id'] for entry in added if entry.get('flat')}
        try:
            self.opening_tool.offer_3d(flat, len(added))
        finally:
            self._pending_3d = None
    self.project_section_changed(self.stack.currentIndex())
    return self.research_path()
