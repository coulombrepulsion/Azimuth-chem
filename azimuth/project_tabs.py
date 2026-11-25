"""The tabs of the projects: refreshing them, the folder of the projects, a new project (of molecules or of a
crystal), the loose molecule of no project, choosing and closing a tab. Methods of ProjectNavigation (self is the
window), kept here to make project_navigation.py shorter.

Split off azimuth/project_navigation.py (0.222.30).
"""

from pathlib import Path
from PySide6.QtGui import QIcon
from azimuth import projects
from azimuth.i18n import tr
from azimuth.icons import icon
from azimuth.project_widgets import EMPTY_CELLS, NEW_ROW, SUBSCRIPT, column_cells, fit_number_column


def register_project_tab(self, path):
    if not hasattr(self, 'project_tabs'):  # before the navigation is built
        return
    path = Path(path).resolve()
    if path not in self.project_sessions:
        self.project_sessions.append(path)
    self._research_path = path
    self.refresh_project_navigation()


def refresh_project_navigation(self):
    if not hasattr(self, 'project_tabs') or getattr(self, '_project_refreshing', False):
        return
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor
    from PySide6.QtWidgets import QTableWidgetItem

    self._project_refreshing = True
    try:
        path = self.research_path()
        # what the tabs and the list show is gathered first (from the kept view of the project); when it
        # is what they already show, only the current row follows — the list was rebuilt on every refresh (the
        # choice of a molecule, a tick, a save), and its scroll jumped to the top
        from azimuth import crystal_projects

        # a new project with nothing opened in it yet has no icon (project_kind '')
        tabs = []
        for candidate in self.project_sessions:
            project = projects.Project.view(candidate)
            kind = self.project_kind(candidate)
            tip = str(candidate)
            if kind == 'crystal':  # the crystals of the project and the one shown, in the tooltip
                try:
                    found = crystal_projects.crystals(candidate)
                    if len(found) > 1:
                        shown = crystal_projects.info(candidate).get('title', '')
                        tip += '\n' + tr('Кристаллов: {} · показан «{}»').format(len(found), shown)
                except (OSError, ValueError, KeyError):
                    pass
            tabs.append((project.data['name'] + (' •' if project.data.get('draft') else ''), tip, kind))
        rows, batch, caption = [], False, tr('Молекулы')
        current = ''
        stand_in = ''
        hidden_labels = []

        if path and crystal_projects.is_crystal(path):  # one row — the crystal itself
            project = projects.Project.view(path)
            # a row for each crystal of the project (crystal_projects.crystals), the active one chosen
            rows = []
            for n, info in enumerate(crystal_projects.crystals(path), 1):
                formula = info.get('formula')
                if not formula:  # a project of before 2026-11-19, a CIF with no formula: of its cell
                    try:
                        formula = crystal_projects.composition(crystal_projects.cif_text(path, info['id']))[0]
                    except OSError:
                        formula = ''
                formula = (formula or '—').translate(SUBSCRIPT)
                title = info.get('title') or (project.data['name'] if n == 1 else 'CIF')
                try:  # the columns of a crystal too
                    cells = crystal_projects.cells(path, info)
                except (OSError, ValueError, KeyError, TypeError):
                    cells = EMPTY_CELLS
                rows.append((self.crystal_row_id(info['id']), title, formula, None, True, '', str(n), False,
                             cells))
            current = self.crystal_row_id(crystal_projects.active(path))
            # the batch of crystals — each with its tick (crystal_batch.py)
            batch = project.data.get('mode') == 'batch'
            if batch:
                ticked = set(crystal_projects.batch_ids(path))
                rows = [(r[0], r[1], r[2], (r[0].split(':', 1)[1] if ':' in r[0] else crystal_projects.FIRST) in ticked,
                         *r[4:]) for r in rows]
            caption = project.data['name'] + ' · ' + tr('кристалл')
            if len(rows) > 1:  # say which crystal is shown (the tab has the
                shown_title = next((r[1] for r in rows if r[0] == current), '')  # name of the project)
                caption = project.data['name'] + ' · ' + tr('кристаллов: {} · показан «{}»').format(
                    len(rows), shown_title)
            path_is_crystal = True
        else:
            path_is_crystal = False
        if path and not path_is_crystal:
            project = projects.Project.view(path)
            current = getattr(self.document(), 'research_molecule_id', '')
            shown = projects.listed(project)  # the ion and the BSSE parts out of sight
            batch = project.data.get('mode') == 'batch'
            excluded = set(project.data.get('excluded', ()))
            queued = {e['id'] for e in projects.queueable(project)}
            # a molecule with conformers has ▸ / ▾ before its name, its conformers (№ «2.1», «2.2»…)
            # follow it when it is unfolded; the conformer of the tab shown unfolds its group
            opened = self.unfolded_conformers()
            # only a conformer shown
            # unfolds its group — the molecule itself shown kept its group open whatever ▾ said; and a group
            # folded by ▾ stays folded while one of its conformers is shown
            shown_root = projects.conformer_root(project, current) if current else ''
            stand_in = shown_root if shown_root != current else ''  # its row marked while the group is folded
            if shown_root == current or shown_root in self.folded_conformers():
                shown_root = ''
            number = 0
            for entry in projects.ordered(project):
                root = entry.get('conformer_of')
                children = projects.conformers_of(project, entry['id']) if not root else ()
                if root and root not in opened and root != shown_root:
                    # the column «№» as wide as the numbers of the folded conformers too — it narrowed when a
                    # group folded and widened when it unfolded, and the heads of the columns moved
                    hidden_labels.append(f"{number}.{(entry.get('conformer') or {}).get('rank', 0)}")
                    continue
                molecule, calc_of = project.read_structure(entry['structure'])
                formula = molecule.formula.translate(SUBSCRIPT) if molecule.atoms else '—'
                tick = None
                if batch and entry['id'] in queued:  # the tick — in the batch or left out
                    tick = entry['id'] not in excluded
                # T23: the result is of other data (an edit, another charge or method) — marked ≠
                differs = projects.result_mismatch(project, entry)
                if root:
                    info = entry.get('conformer') or {}
                    rank = info.get('rank', 0)
                    name = '    ' + tr('конформер {}').format(rank) + (
                        tr(' · ΔE {} ккал/моль').format(f"{info['delta']:.2f}") if info.get('delta') is not None else '')
                    label = f'{number}.{rank}'
                else:
                    number += 1
                    label = str(number)
                    name = entry['name']
                    if children:
                        unfolded = entry['id'] in opened or entry['id'] == shown_root
                        name = ('▾ ' if unfolded else '▸ ') + name + tr(' · конформеров: {}').format(len(children))
                if not root:  # its role in the reaction of the project («ΔG реакции…»)
                    from azimuth.project_reaction import badge

                    name += badge(entry)
                marked = False
                if not root:
                    from azimuth.project_reaction import role_of

                    marked = role_of(entry)[0] is not None
                try:
                    cells = column_cells(project, entry, molecule, calc_of)
                except (KeyError, TypeError, ValueError, AttributeError):
                    cells = EMPTY_CELLS
                rows.append((entry['id'], name, formula, tick, entry['id'] in queued,
                             projects.mismatch_text(differs) if differs else '', label, marked, cells))
            pending = self.pending_project_molecule(path)  # «Новая молекула», nothing drawn yet
            if pending is not None:
                rows.append((NEW_ROW, tr('Новая молекула'), '—', None, True, '', str(len(rows) + 1), False,
                             EMPTY_CELLS))
                if pending is self.document():
                    current = NEW_ROW
            caption = project.data['name'] + ' · ' + tr(f'молекул: {len(shown)}')
        dim = self.palette().color(self.palette().ColorRole.PlaceholderText).name()
        # no project chosen while others are open — a tab «Новый проект» of its own is the current one (it gets its
        # folder when a molecule is saved into it), not the tab of the last project the tab of a loose molecule
        # stays, whatever tab is chosen
        loose = self.loose_molecule_document() if self.project_sessions else None
        placeholder = bool(self.project_sessions) and (path is None or loose is not None)
        current_placeholder = placeholder and path is None
        if placeholder:
            tabs.append((tr('Новый проект'), tr('Новый проект — папка появится при сохранении'),
                         'molecule' if loose is not None else self.project_kind(None)))
        alone = self.project_kind(None) if not self.project_sessions else None
        shown_now = (tuple(tabs), path, tuple(rows), batch, dim, tr('Новый проект'), alone)
        if shown_now != getattr(self, '_project_shown', None):
            self._project_shown = shown_now
            self.project_tabs.blockSignals(True)
            while self.project_tabs.count():
                self.project_tabs.removeTab(0)
            for name, tip, kind in tabs:
                self.project_tabs.addTab(icon(kind) if kind else QIcon(), name)
                self.project_tabs.setTabToolTip(self.project_tabs.count() - 1, tip)
                self.project_tabs.setTabData(self.project_tabs.count() - 1, kind)
            if not self.project_sessions:
                self.project_tabs.addTab(icon(alone) if alone else QIcon(), tr('Новый проект'))
                self.project_tabs.setTabData(0, alone)
            self.project_tabs.blockSignals(False)
            table = self.project_molecules
            table.blockSignals(True)
            table.clearContents()
            table.setRowCount(len(rows))
            # a fold or an unfold of conformers still moving ends here; every row at its full height
            # (the heights belong to the places of the rows, not to the rows)
            motion, self._fold_motion = getattr(self, '_fold_motion', None), None
            if motion is not None:
                motion.stop()
            rows_header = table.verticalHeader()
            for k in range(len(rows)):
                if rows_header.sectionSize(k) != rows_header.defaultSectionSize():
                    rows_header.resizeSection(k, rows_header.defaultSectionSize())
            for k, (ident, name, formula, tick, in_queue, differs, label, marked, cells) in enumerate(rows):
                for j, text in enumerate((label, name + (' ≠' if differs else ''), formula) + tuple(cells)):
                    cell = QTableWidgetItem(text)
                    if differs:  # no tooltip repeating the row — only what it does not say
                        cell.setToolTip(tr('Результат посчитан для прежних данных молекулы, изменились: ') + differs)
                    if j == 0:
                        cell.setData(Qt.ItemDataRole.UserRole, ident)
                        if tick is not None:
                            cell.setFlags(cell.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                            cell.setCheckState(Qt.CheckState.Checked if tick else Qt.CheckState.Unchecked)
                    if j == 1 and marked:
                        # a molecule with a role in the reaction of the project — its name in the gold
                        # (of the icons: the lighter gold of the frames is too faint for words on white)
                        from hub.branding import STAR_GOLD

                        dark_list = self.palette().color(self.palette().ColorRole.Base).lightness() < 128
                        cell.setForeground(QColor(STAR_GOLD['dark' if dark_list else 'light']))
                    if batch and not in_queue:  # a complex of a binding queue: shown, not queued
                        cell.setForeground(QColor(dim))
                    table.setItem(k, j, cell)
            fit_number_column(table, len(rows), any(r[3] is not None for r in rows),
                              [r[6] for r in rows] + hidden_labels)
            self.fit_project_columns()
        if path in self.project_sessions or current_placeholder:
            self.project_tabs.blockSignals(True)
            self.project_tabs.setCurrentIndex(self.project_sessions.index(path) if not current_placeholder
                                              else self.project_tabs.count() - 1)
            self.project_tabs.blockSignals(False)
        table = self.project_molecules
        table.blockSignals(True)
        row = next((k for k, r in enumerate(rows) if r[0] == current), -1)
        if row < 0 and stand_in:  # the conformer shown is in a folded group — the row of its molecule
            row = next((k for k, r in enumerate(rows) if r[0] == stand_in), -1)
        if table.currentRow() != row:
            table.setCurrentCell(row, 0 if row >= 0 else -1)
        # the batch of a crystal project — the crystals with a tick, by Quantum ESPRESSO or CP2K
        self.project_mode_tabs.setTabToolTip(1, tr('Расчёт Quantum ESPRESSO или CP2K — для всех отмеченных '
                                                   'кристаллов по очереди; снимите галочку, чтобы исключить '
                                                   'кристалл') if path_is_crystal
                                             else tr('Расчёты и анализ — для всех отмеченных молекул; снимите '
                                                     'галочку, чтобы исключить молекулу'))
        if path:
            self.project_mode_tabs.blockSignals(True)
            self.project_mode_tabs.setCurrentIndex(1 if batch else 0)
            self.project_mode_tabs.blockSignals(False)
            self.result_tabs.setTabVisible(self.topology_tab, True)
        self.project_caption.setText(caption)
        self.project_molecules.blockSignals(False)
    finally:
        self.project_tabs.blockSignals(False)
        self.project_molecules.blockSignals(False)
        self._project_refreshing = False
    self.sync_project_plan()
    if hasattr(self, 'calc_stack') and hasattr(self, 'program'):  # Sextant's programs follow the project
        self.crystal_mode_tool.sync_programs()


def projects_root(self, kind=None):
    """Where new projects are made — «Документы/Azimuth/Проекты» or the folder chosen in the settings;
    with kind ('molecule', 'crystal') — its folder there («Молекулы», «Кристаллы»)."""
    from azimuth.project_folders import kind_root, projects_root

    root = projects_root(self.preferences.value('projects_folder', '') or '')
    return kind_root(root, kind) if kind else root


def choose_projects_folder(self, path=None):
    """The root of the new projects (the projects made already stay where they are)."""
    from PySide6.QtWidgets import QFileDialog

    from modules.sextant.runner import latin_path

    if path is None:
        start = self.projects_root()
        path = QFileDialog.getExistingDirectory(self, tr('Папка проектов'), str(start if start.exists() else Path.home()))
    if not path:
        return None
    if not latin_path(path):
        self.notify(tr('Выберите папку с латинскими буквами в пути: ORCA, xtb и Gaussian на Windows не открывают '
                       'файлы в папке ') + str(path), 12000)
        return None
    self.preferences.setValue('projects_folder', str(path))
    self.notify(tr('Новые проекты будут в папке ') + str(path), 6000)
    return Path(path)


def new_project_tab(self, name=None, include_current=False):
    from azimuth.project_folders import new_project_folder

    if getattr(self, 'compass_mode', 'molecule') == 'crystal' and hasattr(self, 'crystal_tool') and not include_current:
        return self.new_crystal_side_project(name)  # «+» in «Компас · Кристалл» stays there
    self.ensure_molecule_tabs()
    if self.research_path():
        self.save_research_project()
    elif self.own_molecule().atoms and not include_current:
        self.new_project_tab(tr('Новый проект'), include_current=True)
    # a draft gets its permanent folder at once — «Проекты/<name>»,
    # « (2)» on a clash — not a temporary folder of the recovery data that «Сохранить» copied (two folders, one id)
    folder = new_project_folder(self.projects_root('molecule'), name or tr('Новый проект'))
    project = projects.Project.create(folder)
    project.data.update(name=name or tr('Новый проект'), draft=True)
    project.save()
    self._research_path = project.path
    if include_current and self.own_molecule().atoms:
        self.add_current_to_project()
    elif self.own_molecule().atoms or getattr(self.document(), 'research_project_id', ''):
        self.new_document()
    if not self.own_molecule().atoms:
        self.project_empty_documents[str(project.path)] = self.document()
    self.register_project_tab(project.path)
    # a draft is not a recent file; the files opened and the projects saved are
    return project.path


def new_crystal_side_project(self, name=None):
    """«+» in «Компас · Кристалл» — a new project of no kind with an empty tab of «Кристалл»; a CIF opened there
    makes it the project of that crystal (crystal_project_opened takes an empty project), a molecule drawn in
    «Молекула» — a project of molecules."""
    from azimuth import crystal_projects
    from azimuth.project_folders import new_project_folder

    current = self.research_path()
    if current and not crystal_projects.is_crystal(current):
        self.save_research_project()
    folder = new_project_folder(self.projects_root('crystal'), name or tr('Новый проект'))
    project = projects.Project.create(folder)
    project.data.update(name=name or tr('Новый проект'), draft=True)
    project.save()
    self._activating_project = True
    try:
        document = self.new_document()  # an empty tab of «Компас · Кристалл»: no crystal in it
    finally:
        self._activating_project = False
    document.research_project_path = str(project.path)
    self._research_path = project.path
    self.project_empty_documents[str(project.path)] = document
    self.register_project_tab(project.path)
    if self.stack.currentIndex() == 1 and hasattr(self, 'crystal_mode_tool'):
        self.crystal_mode_tool.follow(None)  # Sextant: the page of no crystal (its programs of both kinds)
    return project.path


def project_kind(self, path=None):
    """'crystal', 'molecule' or '' — a project (path; None — the new one of no folder yet) with nothing opened
    or drawn in it: no icon on its tab, Sextant offers the programs of both kinds (crystal_mode.sync_programs)."""
    from azimuth import crystal_projects

    if path is not None and crystal_projects.is_crystal(path):
        return 'crystal'
    if path is not None and projects.Project.view(path).molecules:
        return 'molecule'
    if path is not None and Path(path) != self.research_path():
        return ''
    if getattr(self, 'compass_mode', 'molecule') == 'crystal' and getattr(self, 'crystal', None) is not None:
        return 'crystal' if path is None else ''
    try:
        return 'molecule' if self.own_molecule().atoms else ''
    except (AttributeError, IndexError):
        return ''


def ensure_project_tab(self):
    if self.research_path() is None:
        self.new_project_tab(include_current=True)
    return self.research_path()


def loose_molecule_document(self):
    """The tab of «Компас · Молекула» with a molecule of no project (drawn, opened, pasted) — the one shown
    there first; None when there is none."""
    if getattr(self, 'document_kind', 'molecule') == 'molecule':
        docs, index = self.documents, self.current_document
    else:
        docs, index = getattr(self, 'shelved_documents', {}).get('molecule', ([], 0))
    order = ([docs[index]] if 0 <= index < len(docs) else []) + list(docs)
    # the tab shown keeps its molecule in the viewer until it is stored —
    # its own document still had none, and the tab «Новый проект» of the molecule was not shown
    shown = self.document() if getattr(self, 'document_kind', 'molecule') == 'molecule' and hasattr(self, 'document') else None

    def drawn(d):
        if d is shown:
            try:
                return bool(self.own_molecule().atoms)
            except (AttributeError, IndexError):
                pass
        return d.molecule is not None and bool(d.molecule.atoms)

    return next((d for d in order if drawn(d)
                 and not d.research_project_path and not getattr(d, 'research_project_id', '')), None)


def keep_loose_molecule(self):
    """Another tab chosen while the molecule drawn of no project is shown (the tab «Новый проект» of it)
    or while the molecule drawn in an empty new project is not yet in it — the molecule is written into a project
    (a draft «Новый проект», as at the end of the program — keep_drawn_as_drafts), whose tab stays among the tabs:
    a drawn molecule is a change, it is kept. Returns the path of the project or None."""
    if self.research_path() is not None:
        if hasattr(self, 'attach_project_placeholder'):
            self.attach_project_placeholder()  # an empty project with its first molecule drawn
        return None
    document = self.loose_molecule_document()
    if document is None:
        return None
    kept = self.keep_drawn_as_drafts([document])
    if not kept:
        return None
    path = Path(kept[0]).resolve()
    if path not in self.project_sessions:
        self.project_sessions.append(path)
    return path


def activate_loose_tab(self):
    """The tab «Новый проект» of a loose molecule chosen: «Компас · Молекула» with that molecule; Sextant
    shown stays Sextant (its page of a molecule)."""
    document = self.loose_molecule_document()
    if document is None or self.research_path() is None:
        return self.refresh_project_navigation()
    section = self.stack.currentIndex()
    if self.research_path():
        self.save_research_project()
    self._activating_project = True
    try:
        if getattr(self, 'compass_mode', 'molecule') == 'crystal' and hasattr(self, 'crystal_tool'):
            self.crystal_tool.set_compass_mode('molecule')
        if document in self.documents:
            self.switch_document(self.documents.index(document))
    finally:
        self._activating_project = False
    self._research_path = None
    self.navigate(section)
    self.refresh_project_navigation()


def new_project_from_plus(self):
    """«+» of the tabs of the projects. While
    a work goes on in the tab shown, the new project is made and gets its tab, which is not opened — it is
    opened when the work is done (a press on its tab)."""
    from azimuth.tasks import busy

    if not busy():
        return self.new_project_tab()
    from azimuth.project_folders import new_project_folder

    folder = new_project_folder(self.projects_root('molecule'), tr('Новый проект'))
    project = projects.Project.create(folder)
    project.data.update(name=tr('Новый проект'), draft=True)
    project.save()
    path = Path(project.path).resolve()
    if path not in self.project_sessions:
        self.project_sessions.append(path)
    self._project_shown = None
    self.refresh_project_navigation()
    self.notify(tr('Проект создан — его вкладку можно открыть, когда закончится «{}».').format(busy().rstrip('…')),
                6000)
    return path


def activate_project_tab(self, index):
    from azimuth.tasks import held

    if not getattr(self, '_project_refreshing', False) and held():
        # another project is not opened under a work going on — the tab shown stays chosen
        current = self.research_path()
        sessions = [Path(p).resolve() for p in getattr(self, 'project_sessions', ())]
        self.project_tabs.blockSignals(True)
        try:
            if current is not None and Path(current).resolve() in sessions:
                self.project_tabs.setCurrentIndex(sessions.index(Path(current).resolve()))
        finally:
            self.project_tabs.blockSignals(False)
        return None
    if index == len(getattr(self, 'project_sessions', ())) and not getattr(self, '_project_refreshing', False):
        return self.activate_loose_tab()
    if getattr(self, '_project_refreshing', False) or not 0 <= index < len(self.project_sessions):
        return
    target = self.project_sessions[index]
    if target == self.research_path():
        return
    self.keep_loose_molecule()  # the molecule drawn of the tab left stays in a project
    from azimuth import crystal_projects

    if crystal_projects.is_crystal(target):
        return self.activate_crystal_project(target)
    waiting = self.project_empty_documents.get(str(target))
    if waiting is not None and getattr(waiting, 'kind', 'molecule') == 'crystal' and hasattr(self, 'crystal_tool'):
        return self.activate_empty_crystal_tab(target, waiting)
    if getattr(self, 'compass_mode', 'molecule') == 'crystal' and hasattr(self, 'crystal_tool'):
        self._activating_project = True  # a project of molecules: «Компас · Молекула» with its tabs
        try:
            self.crystal_tool.set_compass_mode('molecule')
        finally:
            self._activating_project = False
    if self.research_path():
        self.save_research_project()
    self._research_path = target
    project = projects.Project.view(target)
    ident = self.project_last_molecule.get(str(target))
    if ident and not any(m['id'] == ident for m in project.molecules):
        ident = None  # it was moved away from there
    section = self.stack.currentIndex()
    if project.molecules:
        self.open_project_molecule(ident or project.molecules[0]['id'], stay=True)
    else:
        placeholder = self.project_empty_documents.get(str(target))
        if placeholder in self.documents:
            self.switch_document(self.documents.index(placeholder))
        else:
            self.project_empty_documents[str(target)] = self.new_document()
    if self.stack.currentIndex() != section or section == 2:  # Spectrum of a crystal left for a molecule's
        self.navigate(section)
    self.refresh_project_structures()
    self.project_section_changed(section)
    self.refresh_project_navigation()


def close_project_tab(self, index):
    if not 0 <= index < len(self.project_sessions):
        return False
    target = self.project_sessions[index]
    active = target == self.research_path()
    from azimuth import crystal_projects

    if crystal_projects.is_crystal(target):
        return self.close_crystal_project(index, target, active)
    # Closing a tab saves its draft on disk. It never deletes calculation files or stops a running job.
    if active:
        self.attach_project_placeholder()
    self.save_research_project(target)
    try:  # its session is written and let go; its running jobs record their attempts in the file
        self.session_registry().close(projects.Project.view(target).data['id'], save=True)
    except (OSError, ValueError, KeyError):
        pass
    self.discard_untouched_project(target)  # a project only looked at leaves no folder
    self.project_sessions.pop(index)
    if not active:
        self.refresh_project_navigation()
        return True
    self._research_path = None
    if self.project_sessions:
        self.activate_project_tab(min(index, len(self.project_sessions) - 1))
    else:
        self.new_document()
    self.refresh_project_navigation()
    return True
