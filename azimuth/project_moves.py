"""Molecules moved between projects, removed and restored — a part of ProjectNavigation (azimuth/project_navigation.py),
a mixin of Studio.

§1 PURPOSE
    Dragging molecules to another tab or to a new project, the order of the tabs, removing molecules (their files
    kept until the project is saved) and bringing them back.
§7 TESTS tests/projects/test_project_navigation.py.
"""

from pathlib import Path

from azimuth import projects
from azimuth.i18n import tr
from azimuth.project_widgets import NEW_ROW


class ProjectMoves:
    def project_tab_takes_molecules(self, index):
        """The tab index is of another project of molecules (not the one shown, not a crystal)."""
        from azimuth import crystal_projects

        sessions = getattr(self, 'project_sessions', [])
        path = self.research_path()
        if path is None or not 0 <= index < len(sessions):
            return False
        target = Path(sessions[index])
        try:
            if target.resolve() == Path(path).resolve() or target.resolve() == Path(path).resolve().parent:
                return False
            return not crystal_projects.is_crystal(target)
        except OSError:
            return False

    def molecules_to_project_tab(self, index, ids=None, copy=False):
        """The molecules ids (the
        rows chosen) of the project shown — their structures, settings and names — into the project of the tab index,
        at the end of its list; without copy they leave this project (remove_project_molecules, their calculation
        files kept, «Вернуть удалённые» brings them back). The tab of the other project is shown. Returns the ids of
        the new molecules there, or []."""
        path = self.research_path()
        ids = [i for i in (ids if ids is not None else self.chosen_project_rows()) if i and i != NEW_ROW]
        if path is None or not ids or not self.project_tab_takes_molecules(index):
            return []
        target = self.project_sessions[index]
        self.save_research_project()
        try:
            source = projects.Project.view(path)
            carried = []
            for ident in ids:
                entry = source.entry(ident)
                molecule, calc = source.read_structure(entry['structure'])
                carried.append((entry, molecule, calc))
            made = []
            with projects.edit(target) as project:
                for entry, molecule, calc in carried:
                    name = entry.get('name') or molecule.formula
                    made.append(project.add(molecule, calc, entry.get('kind', 'orca'), name)['id'])
        except (OSError, ValueError, KeyError) as exc:
            self.error(exc)
            return []
        if not copy and not self.remove_project_molecules(ids, delete_files=False):
            copy = True  # refused (a calculation runs): they stay here as well
        names = ', '.join('«{}»'.format(e.get('name') or m.formula) for e, m, _ in carried)
        self._project_shown = None
        self.project_tabs.setCurrentIndex(index)
        self.notify((tr('Скопировано в проект «{}»: {}') if copy else tr('Перенесено в проект «{}»: {}')).format(
            self.project_tabs.tabText(index), names), 8000)
        return made

    def _carry_place(self, point):
        """What is under the global point for molecules carried: ('tab', index) of a project that takes them,
        ('plus', None), ('list', row before which), or (None, None)."""
        from PySide6.QtWidgets import QApplication

        if point is None:
            return None, None
        found = QApplication.widgetAt(point)
        tabs, plus, table = self.project_tabs, getattr(self, 'new_project_plus', None), self.project_molecules
        while found is not None:
            if found is tabs:
                index = tabs.tabAt(tabs.mapFromGlobal(point))
                return ('tab', index) if index >= 0 and self.project_tab_takes_molecules(index) else (None, None)
            if plus is not None and found is plus:
                return 'plus', None
            if found is table.viewport():
                return 'list', table.target_row(table.viewport().mapFromGlobal(point))
            found = found.parentWidget()
        return None, None

    def molecules_hover(self, point):
        """Molecules carried over point (None — no more): the tab that takes them framed, «+» framed."""
        kind, index = self._carry_place(point)
        tabs = self.project_tabs
        target = index if kind == 'tab' else -1
        if tabs.drop_target != target:
            tabs.drop_target = target
            tabs.update()
        lit = getattr(self, '_plus_drops', None)
        if lit is not None:
            lit.light(kind == 'plus')

    def molecules_drop(self, point, rows, copy):
        """Molecules carried (the rows of the list) let go at point: on a tab of another project — into it,
        on «+» — a new project of them, on the list — before the row there; anywhere else — put back."""
        from PySide6.QtCore import Qt

        kind, index = self._carry_place(point)
        table = self.project_molecules
        ids = [table.item(r, 0).data(Qt.ItemDataRole.UserRole) for r in rows if table.item(r, 0) is not None]
        if kind == 'tab':
            self.molecules_to_project_tab(index, ids=ids, copy=copy)
        elif kind == 'plus':
            self.molecules_to_new_project(ids=ids, copy=copy)
        elif kind == 'list':
            self.move_project_molecules(rows, index)
        return kind

    def molecules_to_new_project(self, ids=None, copy=False):
        """The molecules ids (the rows chosen) of the project shown — their structures, settings and names — the
        molecules of a new project (named after the one molecule, else «Новый проект»), its tab shown with the first of
        them; without copy they leave this project (their calculation files kept, «Вернуть удалённые» brings them back).
        Returns the path of the new project, or None."""
        path = self.research_path()
        ids = [i for i in (ids if ids is not None else self.chosen_project_rows()) if i and i != NEW_ROW]
        if path is None or not ids or getattr(self, 'compass_mode', 'molecule') == 'crystal':
            return None
        self.save_research_project()
        try:
            source = projects.Project.view(path)
            carried = []
            for ident in ids:
                entry = source.entry(ident)
                molecule, calc = source.read_structure(entry['structure'])
                carried.append((entry, molecule, calc))
        except (OSError, ValueError, KeyError) as exc:
            self.error(exc)
            return None
        if not copy and not self.remove_project_molecules(ids, delete_files=False):
            copy = True  # refused (a calculation runs): they stay here as well
        names = [e.get('name') or m.formula for e, m, _ in carried]
        new = self.new_project_tab(names[0] if len(names) == 1 else tr('Новый проект'))
        if new is None:
            return None
        try:
            with projects.edit(new) as project:
                made = [project.add(m, c, e.get('kind', 'orca'), n)['id'] for (e, m, c), n in zip(carried, names)]
        except (OSError, ValueError, KeyError) as exc:
            self.error(exc)
            return new
        self._project_shown = None
        if made and hasattr(self, 'open_project_molecule'):
            self.open_project_molecule(made[0], stay=True)
        self.refresh_project_navigation()
        self.notify((tr('Скопировано в новый проект: {}') if copy else tr('Перенесено в новый проект: {}')).format(
            ', '.join('«{}»'.format(n) for n in names)), 8000)
        return new

    def project_molecule_to_new_project(self, ident, move=True):
        """The molecule ident of the project shown — its structure and name — the first molecule of a new
        project (its tab shown); move: it leaves this project (remove_project_molecules, its calculation files kept,
        «Вернуть удалённые» brings it back). Returns the path of the new project, or None."""
        from dataclasses import replace

        path = self.research_path()
        if path is None or not ident or ident == NEW_ROW:
            return None
        self.save_research_project()
        try:
            project = projects.Project.view(path)
            entry = project.entry(ident)
            molecule, _ = project.read_structure(entry['structure'])
        except (OSError, ValueError, KeyError) as exc:
            self.error(exc)
            return None
        name = entry.get('name') or molecule.formula
        if move and not self.remove_project_molecules([ident], delete_files=False):
            return None
        new = self.new_project_tab(name)
        self.load_molecule(replace(molecule, title=name))
        self.attach_project_placeholder()
        self.notify((tr('Молекула «{}» перенесена в новый проект.') if move else
                     tr('Молекула «{}» скопирована в новый проект.')).format(name), 8000)
        return new

    def remove_project_molecules(self, ids=None, delete_files=None):
        """«Удалить из проекта…» (Delete, ⌫ in the list): the molecules ids (the rows chosen) and the molecules a
        binding queue made for them leave the project with the records of their calculations (projects.removal:
        refused while one is calculated). The dialog asks; when they have calculation folders, its tick deletes them
        too (delete_files: True / False without the dialog — the tests). Kept files — «Вернуть удалённые» (Ctrl+Z in the
        list) puts the molecules back; deleted files — no way back, said in the dialog. Their tabs close. Returns the
        ids removed ([] when nothing was)."""
        from PySide6.QtWidgets import QCheckBox, QMessageBox

        path = self.research_path()
        if path is None:
            return []
        ids = list(ids if ids is not None else self.chosen_project_rows())
        if NEW_ROW in ids:  # the empty row of «Новая молекула» — it only goes from the list
            ids = [i for i in ids if i != NEW_ROW]
            self.drop_pending_project_molecule(path)
        if not ids:
            return []
        self.save_research_project()
        project = projects.Project.view(path)
        try:
            taken = projects.removal(project, ids)
        except ValueError as exc:
            self.error(exc)
            return []
        folders = projects.calculation_folders(project, taken)
        names = [e['name'] for e in taken if e['id'] in set(ids)]
        if delete_files is None:
            from azimuth import quill

            box = QMessageBox(self)
            box.setWindowTitle(tr('Удалить из проекта'))
            listed = ', '.join(f'«{n}»' for n in names[:3]) + (tr(' и ещё {}').format(len(names) - 3) if len(names) > 3 else '')
            text = tr('Удалить из проекта {}?').format(listed)
            if len(taken) > len(names):
                text += ' ' + tr('Вместе с ними — {} молекул, сделанных для них очередью связывания.').format(
                    len(taken) - len(names))
            box.setText(text)
            files = None
            if folders:
                size = sum(f.stat().st_size for folder in folders for f in folder.rglob('*') if f.is_file())
                files = QCheckBox(tr('Удалить и файлы их расчётов ({} папок, {:.1f} МБ) — безвозвратно').format(
                    len(folders), size / 1e6))
                box.setCheckBox(files)
                box.setInformativeText(tr('Без галочки файлы расчётов останутся в папке проекта, а молекулы можно '
                                          'будет вернуть (Ctrl+Z / ⌘Z в списке или «Вернуть удалённые» в его меню).'))
            else:
                box.setInformativeText(tr('Расчётов у них нет. Вернуть: Ctrl+Z / ⌘Z в списке или «Вернуть удалённые».'))
            box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
            box.setDefaultButton(QMessageBox.StandardButton.Cancel)
            box.button(QMessageBox.StandardButton.Yes).setText(tr('Удалить'))
            quill.set_icon(box, 'delete', QMessageBox.Icon.Question)  # Quill over the waste basket, as closing a tab
            box.exec()
            clicked = box.clickedButton()
            if clicked is None or box.standardButton(clicked) != QMessageBox.StandardButton.Yes:
                return []
            delete_files = bool(files is not None and files.isChecked())
        gone = {e['id'] for e in taken}
        for index in reversed(range(len(self.documents))):  # their tabs close, unsaved edits of them go with them
            document = self.documents[index]
            if getattr(document, 'research_molecule_id', None) in gone and document.research_project_path and \
                    Path(document.research_project_path).resolve() == Path(path).resolve():
                document.dirty = False
                if index == self.current_document:
                    self.dirty = False
                self.close_document(index)
        try:
            removed = self.project_session(path).remove_molecules(ids)
        except ValueError as exc:
            self.error(exc)
            return []
        failed = []
        if delete_files:
            import shutil

            for folder in folders:
                try:
                    shutil.rmtree(folder)
                except OSError as exc:
                    failed.append(f'{folder.name}: {exc}')
            self._project_removed = None
        else:
            self._project_removed = (path, removed)
        self.refresh_project_navigation()
        self.sync_project_plan()
        message = tr('Удалено из проекта: {}.').format(len(removed))
        if delete_files:
            message += ' ' + tr('Папок расчётов удалено: {}.').format(len(folders) - len(failed))
        elif removed:
            message += ' ' + tr('Вернуть: Ctrl+Z / ⌘Z в списке.')
        if failed:
            message += ' ' + tr('Не удалось удалить: ') + '; '.join(failed[:3])
        self.notify(message, 10000)
        return [e['id'] for _, e in removed]

    def restore_project_molecules(self):
        """The molecules of the last removal (files kept) back in the project, at their places."""
        kept = self._project_removed
        if kept is None or kept[0] != self.research_path():
            return []
        ids = self.project_session(kept[0]).restore_molecules(kept[1])
        self._project_removed = None
        self.refresh_project_navigation()
        self.sync_project_plan()
        self.notify(tr('Молекулы возвращены в проект: {}.').format(len(ids)), 6000)
        return ids

    def project_tab_moved(self, source, target):
        """A tab of a project dragged to another place — the projects in that order; the tab «Новый проект» of
        a loose molecule stays the last."""
        count = len(self.project_sessions)
        bar = self.project_tabs
        if source >= count or target >= count:
            bar.blockSignals(True)
            bar.moveTab(target, source)
            bar.blockSignals(False)
            return
        self.project_sessions.insert(target, self.project_sessions.pop(source))
        shown = getattr(self, '_project_shown', None)
        if shown:  # what the bar shows is in the new order — not made anew in the middle of the drag
            tabs = list(shown[0])
            if source < len(tabs) and target < len(tabs):
                tabs.insert(target, tabs.pop(source))
                self._project_shown = (tuple(tabs),) + tuple(shown[1:])

    def move_project_molecules(self, rows, target):
        """The molecules of the rows dragged before the row target of the list (a molecule with its
        conformers; a conformer stays in its group — the numbers of the conformers are their ranks by energy)."""
        from PySide6.QtCore import Qt

        from azimuth import crystal_projects

        path = self.research_path()
        table = self.project_molecules
        if not path or crystal_projects.is_crystal(path):
            return False
        ids = [table.item(r, 0).data(Qt.ItemDataRole.UserRole) for r in rows if table.item(r, 0) is not None]
        project = projects.Project.view(path)
        order = [e['id'] for e in projects.ordered(project) if not e.get('conformer_of')]
        roots = [i for i in order if i in ids]
        if not roots:
            return False
        target_id = table.item(target, 0).data(Qt.ItemDataRole.UserRole) \
            if 0 <= target < table.rowCount() and table.item(target, 0) is not None else None
        place = len(order)
        if target_id in order:
            place = order.index(target_id)
        else:
            entry = next((e for e in project.molecules if e['id'] == target_id), None)
            root = (entry or {}).get('conformer_of')
            if root in order:
                place = order.index(root) + 1  # dropped among the conformers of a molecule: after its group
        cut = sum(1 for i in order[:place] if i not in roots)
        rest = [i for i in order if i not in roots]
        new = rest[:cut] + roots + rest[cut:]
        if new == order:
            return False
        if self.research_path() is not None and Path(path).resolve() == Path(self.research_path()).resolve():
            self.save_research_project()
        listed = set(order)
        with projects.edit(path) as project:
            by_id = {e['id']: e for e in project.molecules}
            sequence = iter(new)
            project.data['molecules'] = [by_id[next(sequence)] if e['id'] in listed else e
                                         for e in project.molecules]
        self.refresh_project_navigation()
        return True
