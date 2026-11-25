"""The menu of the list of molecules of a project: the molecules chosen, their history, the role in a reaction and
its ΔG, the folder of a calculation, the ticks of the batch mode and the queue they choose. Methods of
ProjectNavigation (self is the window), kept here to make project_navigation.py shorter.

Split off azimuth/project_navigation.py (0.222.30).
"""

from azimuth import projects
from azimuth.i18n import tr
from azimuth.project_widgets import NEW_ROW
from azimuth.ui import rounded


def selected_project_molecules(self):
    """The molecules the work is for — in the batch mode those with a tick (in the order of the list), in
    the single mode the one chosen."""
    from PySide6.QtCore import Qt
    if not hasattr(self, 'project_molecules'):
        return []
    table = self.project_molecules
    if self.project_batch_mode():
        # from the project, in the order of its list — the conformers of a folded molecule are no rows
        try:
            project = projects.Project.view(self.research_path())
        except (OSError, ValueError, KeyError, TypeError):
            project = None
        if project is not None:
            queued = {e['id'] for e in projects.queueable(project)}
            excluded = set(project.data.get('excluded', ()))
            return [e['id'] for e in projects.ordered(project) if e['id'] in queued and e['id'] not in excluded]
        return [table.item(row, 0).data(Qt.ItemDataRole.UserRole) for row in range(table.rowCount())
                if table.item(row, 0) is not None and table.item(row, 0).flags() & Qt.ItemFlag.ItemIsUserCheckable
                and table.item(row, 0).checkState() == Qt.CheckState.Checked]
    ident = getattr(self.document(), 'research_molecule_id', '')
    return [ident] if ident else []


# -- the single and the batch mode ------------------------------------------------------------------------
# -- removing molecules from the project -----------------------------------------------------------------
def chosen_project_rows(self):
    """The ids of the rows chosen in the list (the current one when none is selected), in the order of the list."""
    from PySide6.QtCore import Qt

    table = self.project_molecules
    rows = sorted({index.row() for index in table.selectionModel().selectedRows()}) or (
        [table.currentRow()] if table.currentRow() >= 0 else [])
    return [table.item(row, 0).data(Qt.ItemDataRole.UserRole) for row in rows if table.item(row, 0) is not None]


def project_molecules_menu(self, point):
    from PySide6.QtWidgets import QMenu

    table = self.project_molecules
    row = table.rowAt(point.y())
    if row >= 0 and not table.selectionModel().isRowSelected(row, table.rootIndex()):
        table.selectRow(row)
    menu = rounded(QMenu(table))  # rounded corners
    ids = self.chosen_project_rows()
    # the folder of the calculation of the molecule under the mouse (or the one chosen)
    from PySide6.QtCore import Qt

    clicked = table.item(row, 0).data(Qt.ItemDataRole.UserRole) if row >= 0 and table.item(row, 0) else None
    target = clicked or (ids[0] if ids else None)
    folder = self.project_calculation_folder(target) if target else None
    show = menu.addAction(tr('Папка расчёта'))
    show.setEnabled(folder is not None)
    show.setToolTip(str(folder) if folder else tr('У молекулы ещё нет расчёта'))
    show.triggered.connect(lambda *_: self.open_project_calculation_folder(target))
    menu.setToolTipsVisible(True)
    # «История расчётов молекулы» is disabled while the molecule has no calculations
    attempts = self.project_attempt_count(target) if target and target != NEW_ROW else 0
    history = menu.addAction(tr('История расчётов молекулы…'))
    history.setEnabled(attempts > 0)
    history.setToolTip(tr('Расчётов: {}').format(attempts) if attempts else tr('Молекулу ещё не считали'))
    history.triggered.connect(lambda *_: self.show_molecule_history(target))
    self.add_reaction_actions(menu, [i for i in ids if i != NEW_ROW])  # the reaction of the project
    menu.addSeparator()
    single = target if target and target != NEW_ROW else None
    copy = menu.addAction(tr('Копировать в новый проект'))
    copy.setEnabled(single is not None)
    copy.setToolTip(tr('Новый проект с этой структурой; в этом проекте молекула остаётся'))
    copy.triggered.connect(lambda *_: self.project_molecule_to_new_project(single, move=False))
    move = menu.addAction(tr('Перенести в новый проект'))
    move.setEnabled(single is not None)
    move.setToolTip(tr('Новый проект с этой структурой; из этого проекта молекула уходит (её расчёты остаются в его '
                       'папке — «Вернуть удалённые» вернёт её)'))
    move.triggered.connect(lambda *_: self.project_molecule_to_new_project(single, move=True))
    menu.addSeparator()
    remove = menu.addAction(tr('Удалить из проекта…') if len(ids) < 2 else
                            tr('Удалить из проекта ({})…').format(len(ids)))
    remove.setEnabled(bool(ids))
    remove.triggered.connect(lambda *_: self.remove_project_molecules(ids))
    kept = self._project_removed
    if kept is not None and kept[0] == self.research_path():
        back = menu.addAction(tr('Вернуть удалённые ({})').format(len(kept[1])))
        back.triggered.connect(lambda *_: self.restore_project_molecules())
    menu.exec(table.viewport().mapToGlobal(point))
    return menu


def project_attempt_count(self, ident):
    path = self.research_path()
    if path is None:
        return 0
    try:
        entry = projects.Project.view(path).entry(ident)
    except (OSError, ValueError, KeyError, StopIteration):
        return 0
    return len(entry.get('attempts', []))


def show_molecule_history(self, ident):
    """The window «История расчётов молекулы» of that molecule (as from «История и файлы проекта…»)."""
    from azimuth.project_view import ProjectDialog

    dialog = getattr(self, '_project_dialog', None)
    if dialog is None:
        dialog = ProjectDialog(self)
        self._project_dialog = dialog
    try:
        return dialog.show_history(ident)
    except (OSError, ValueError, KeyError, StopIteration) as exc:
        self.error(exc)
        return None


def add_reaction_actions(self, menu, ids):
    """«Роль в реакции» of the molecules chosen (reactant, transition state, product, none; the coefficient) and «ΔG
    реакции…» of the project."""
    from azimuth import project_reaction as pr

    path = self.research_path()
    if path is None:
        return None
    menu.addSeparator()
    roles = menu.addMenu(tr('Роль в реакции'))
    roles.setEnabled(bool(ids))
    try:
        project = projects.Project.view(path)
        current = {pr.role_of(project.entry(i))[0] for i in ids}
        coeff = pr.role_of(project.entry(ids[0]))[1] if len(ids) == 1 else None
    except (OSError, ValueError, KeyError):
        current, coeff = set(), None
    for role in (*pr.ROLES, None):
        action = roles.addAction(tr(pr.NAMES[role]).capitalize() if role else tr('Не участвует'))
        action.setCheckable(True)
        action.setChecked(current == {role})
        action.triggered.connect(lambda checked=False, role=role: self.set_reaction_role(ids, role))
    roles.addSeparator()
    times = roles.addAction(tr('Коэффициент…') + (f' ({coeff})' if coeff and current - {None} else ''))
    times.setEnabled(bool(current - {None}))
    times.triggered.connect(lambda *_: self.ask_reaction_coefficient(ids))
    gibbs = menu.addAction(tr('ΔG реакции…'))
    gibbs.setToolTip(tr('Диаграмма реакции из результатов молекул проекта с ролью: реагенты → переходные состояния → '
                        'продукты; ΔG, барьеры и проверки'))
    gibbs.triggered.connect(lambda *_: self.project_reaction())
    return roles


def set_reaction_role(self, ids, role, coeff=None):
    from azimuth import project_reaction as pr

    path = self.research_path()
    if path is None or not ids:
        return 0
    self.save_research_project()
    changed = pr.set_role(path, ids, role, coeff)
    self._project_shown = None  # the names of the list show the role
    self.refresh_project_navigation()
    return changed


def ask_reaction_coefficient(self, ids, value=None):
    """«Коэффициент…»: how many of the molecule take part (2 A + B → C: 2 at A)."""
    from PySide6.QtWidgets import QInputDialog

    from azimuth import project_reaction as pr

    if value is None:
        value, ok = QInputDialog.getInt(self, tr('Коэффициент в уравнении реакции'),
                                        tr('Сколько молекул участвует в реакции'), 1, 1, pr.MAX_COEFF)
        if not ok:
            return None
    path = self.research_path()
    project = projects.Project.view(path) if path else None
    if project is None:
        return None
    for ident in ids:
        role, _ = pr.role_of(project.entry(ident))
        if role is not None:
            self.set_reaction_role([ident], role, value)
    return value


def project_reaction(self, read=None):
    """«ΔG реакции…»: the window «Диаграмма реакции» with the stages of the reaction of the project (its stages
    before are replaced), ΔG shown; the problems (no result, no frequencies) told. None — not enough roles."""
    from azimuth import project_reaction as pr

    path = self.research_path()
    if path is None:
        return None
    self.save_research_project()
    try:
        found, problems = pr.stages(projects.Project.view(path), read)
    except ValueError as exc:
        self.error(exc)
        return None
    window = self.reaction_diagram()
    window.set_stages(found, quantity='G')
    if problems:
        self.notify(tr('Не всё вошло в диаграмму: ') + '; '.join(problems), 12000)
    return window


def project_calculation_folder(self, ident):
    """The folder of the calculation of the molecule ident of the open project (projects.calculation_folder)."""
    path = self.research_path()
    if path is None or not ident:
        return None
    try:
        project = projects.Project.view(path)
        return projects.calculation_folder(project, project.entry(ident))
    except (OSError, ValueError, KeyError):
        return None


def open_project_calculation_folder(self, ident):
    """«Папка расчёта» of the menu of the list: the folder opened in Finder (Explorer); False when there is none."""
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QDesktopServices

    folder = self.project_calculation_folder(ident)
    if folder is None:
        self.notify(tr('У молекулы ещё нет расчёта — папки нет.'), 6000)
        return False
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
    return True


def project_tick_changed(self, cell):
    """A tick taken off or put back: the molecule left out of the batch, or back in it."""
    from PySide6.QtCore import Qt
    if getattr(self, '_project_refreshing', False) or cell.column() != 0:
        return
    if not cell.flags() & Qt.ItemFlag.ItemIsUserCheckable:
        return
    ident = cell.data(Qt.ItemDataRole.UserRole)
    if isinstance(ident, str) and (ident == 'crystal' or ident.startswith('crystal:')):
        from azimuth import crystal_projects

        crystal_projects.set_in_batch(self.research_path(), ident.split(':', 1)[1] if ':' in ident
                                      else crystal_projects.FIRST, cell.checkState() == Qt.CheckState.Checked)
        return
    with projects.edit(self.research_path()) as project:
        # the tick of a molecule is the tick of its conformers too (unfolded, each can be taken off)
        changed = {ident} | {e['id'] for e in projects.conformers_of(project, ident)}
        excluded = [e for e in project.data.get('excluded', []) if e not in changed]
        if cell.checkState() != Qt.CheckState.Checked:
            excluded.extend(sorted(changed))
        project.data['excluded'] = excluded
    if len(changed) > 1:
        self.refresh_project_navigation()  # the ticks of the conformers shown follow
    self.sync_project_plan()


def project_plan_changed(self, indices):
    """The choice of the queue changed in its dialog («Изменить выбор…»): the ticks follow it."""
    path = self.research_path()
    if path is None or not self.project_batch_mode():
        return
    project = projects.Project.view(path)
    chosen = set(indices)
    excluded = [e['id'] for k, e in enumerate(projects.queueable(project)) if k not in chosen]
    if sorted(project.data.get('excluded', [])) == sorted(excluded):
        return  # nothing changed: project.qcc is not written again
    with projects.edit(path) as fresh:
        fresh.data['excluded'] = excluded
    self.refresh_project_navigation()


def sync_project_plan(self):
    """The batch mode chooses the queue of Sextant (the molecules with a tick; «Запустить очередь (N)»), the single
    mode leaves the molecule of the tab; the button «QTAIM отмеченных молекул» of Spectrum follows."""
    if getattr(self, '_project_syncing', False) or not hasattr(self, 'batch_tool'):
        return
    self._project_syncing = True
    try:
        batch = bool(self.research_document_path()) and self.project_batch_mode()
        if hasattr(self, 'project_qtaim_button'):
            self.project_qtaim_button.setVisible(batch)
        plan = getattr(self, 'batch_plan', None)
        if batch:
            chosen = set(self.selected_project_molecules())
            path = self.research_path()
            queued = [e['id'] for e in projects.queueable(projects.Project.view(path))]
            indices = [k for k, ident in enumerate(queued) if ident in chosen]
            self.batch_tool.set_batch_plan(indices, plan.get('binding') if plan else None)
            if hasattr(self, 'project_qtaim_button'):
                self.project_qtaim_button.setText(tr(f'QTAIM отмеченных молекул ({len(indices)})'))
        elif plan is not None and getattr(self, '_project_batch_source', False):
            self.batch_tool.clear_batch_plan()
    finally:
        self._project_syncing = False
