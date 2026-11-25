"""The rows of the molecule list of a project: its columns and conformers — a part of ProjectNavigation
(azimuth/project_navigation.py), a mixin of Studio.

§1 PURPOSE
    Which columns are shown and how wide (kept in the settings), the batch mode of the list, the conformers folded
    under their molecule and unfolded.
§7 TESTS tests/projects/test_project_navigation.py.
"""

from pathlib import Path

from azimuth import projects
from azimuth.i18n import tr
from azimuth.project_widgets import COLUMNS, COLUMNS_KEY, FIXED_COLUMNS
from azimuth.ui import rounded


class ProjectRows:
    # -- the columns of the list of the molecules ---------------------------------------------------------
    def project_columns_state(self):
        """{'shown': [keys], 'widths': {key: px}} of the preference COLUMNS_KEY (the defaults of COLUMNS without it)."""
        import json

        try:
            state = json.loads(self.preferences.value(COLUMNS_KEY, '') or '{}')
        except (TypeError, ValueError, AttributeError):
            state = {}
        if not isinstance(state, dict):
            state = {}
        keys = [key for key, _, _ in COLUMNS]
        shown = state.get('shown')
        if not isinstance(shown, list):
            shown = [key for key, _, on in COLUMNS if on]
        shown = [key for key in keys if key in shown or key in FIXED_COLUMNS]
        widths = state.get('widths') if isinstance(state.get('widths'), dict) else {}
        widths = {k: int(v) for k, v in widths.items() if k in keys and isinstance(v, (int, float)) and v > 0}
        return {'shown': shown, 'widths': widths}

    def keep_project_columns(self, state):
        import json

        try:
            self.preferences.setValue(COLUMNS_KEY, json.dumps(state, ensure_ascii=False))
        except AttributeError:
            pass

    def apply_project_columns(self):
        table = self.project_molecules
        shown = self.project_columns_state()['shown']
        for column, (key, _, _) in enumerate(COLUMNS):
            table.setColumnHidden(column, key not in shown)
        self.fit_project_columns()

    def fit_project_columns(self):
        """The columns the user did not size: «Формула» and the others as wide as their texts, «Название» the rest of
        the width of the list (at least 120 px); one sized keeps its width."""
        table = self.project_molecules
        state = self.project_columns_state()
        self._sizing_columns = True
        try:
            others = 0
            for column, (key, title, _) in enumerate(COLUMNS):
                if key in FIXED_COLUMNS or table.isColumnHidden(column):
                    continue
                if key in state['widths']:
                    table.setColumnWidth(column, state['widths'][key])
                else:
                    table.resizeColumnToContents(column)
                    head = table.fontMetrics().horizontalAdvance(tr(title)) + 24
                    table.setColumnWidth(column, max(table.columnWidth(column), head))
                others += table.columnWidth(column)
            name = [key for key, _, _ in COLUMNS].index('name')
            if 'name' in state['widths']:
                table.setColumnWidth(name, state['widths']['name'])
            else:
                from modules.compass.panels.trajectory_drawer import WIDTH

                room = table.viewport().width() if table.viewport().width() > 60 else WIDTH - 32
                table.setColumnWidth(name, max(120, room - others - table.columnWidth(0)))
        finally:
            self._sizing_columns = False

    def project_column_resized(self, column, _old, new):
        """A column dragged wider or narrower by the user keeps its width (the preference COLUMNS_KEY)."""
        if getattr(self, '_sizing_columns', False) or not 0 < column < len(COLUMNS):
            return
        state = self.project_columns_state()
        state['widths'][COLUMNS[column][0]] = int(new)
        self.keep_project_columns(state)

    def project_columns_menu(self, point):
        """The menu of the head of the list: the columns shown (ticks) and «Ширина столбцов по содержимому»."""
        from PySide6.QtWidgets import QMenu

        table = self.project_molecules
        state = self.project_columns_state()
        menu = rounded(QMenu(table))  # rounded corners
        for key, title, _ in COLUMNS:
            if key in FIXED_COLUMNS:
                continue
            action = menu.addAction(tr(title))
            action.setCheckable(True)
            action.setChecked(key in state['shown'])
            action.toggled.connect(lambda on, key=key: self.show_project_column(key, on))
        menu.addSeparator()
        fit = menu.addAction(tr('Ширина столбцов по содержимому'))
        fit.triggered.connect(lambda *_: self.reset_project_column_widths())
        menu.exec(table.horizontalHeader().mapToGlobal(point))
        return menu

    def show_project_column(self, key, on):
        state = self.project_columns_state()
        shown = set(state['shown'])
        (shown.add if on else shown.discard)(key)
        state['shown'] = [k for k, _, _ in COLUMNS if k in shown]
        self.keep_project_columns(state)
        self.apply_project_columns()

    def reset_project_column_widths(self):
        state = self.project_columns_state()
        state['widths'] = {}
        self.keep_project_columns(state)
        self.fit_project_columns()

    def project_batch_mode(self):
        path = self.research_path()
        if path is None:
            return False
        try:
            return projects.Project.view(path).data.get('mode') == 'batch'
        except (OSError, ValueError, KeyError):
            return False

    def set_project_batch_mode(self, batch):
        from azimuth import crystal_projects

        if crystal_projects.is_crystal(self.research_path()):  # the batch of crystals (crystal_batch.py)
            with projects.edit(self.research_path()) as project:
                project.data['mode'] = 'batch' if batch else 'single'
            self.refresh_project_navigation()
            self.notify(tr('Пакетный режим: «Запустить расчёт» Quantum ESPRESSO или CP2K считает все отмеченные '
                           'кристаллы по очереди.') if batch else
                        tr('Одиночный режим: расчёт — для выбранного кристалла.'), 8000)
            return
        path = self.ensure_project_tab()
        with projects.edit(path) as project:
            project.data['mode'] = 'batch' if batch else 'single'
        self.refresh_project_navigation()
        self.notify(tr('Пакетный режим: расчёты и анализ — для всех отмеченных молекул.') if batch
                    else tr('Одиночный режим: расчёты и анализ — для выбранной молекулы.'), 6000)

    # -- the conformers of a molecule as a group of the list --------------------------------------------------
    def unfolded_conformers(self):
        """The ids of the molecules whose conformers the list shows (unfolded by ▸)."""
        if not hasattr(self, '_unfolded'):
            self._unfolded = set()
        return self._unfolded

    def folded_conformers(self):
        """The ids of the molecules whose group was folded by ▾ (a conformer of it shown does not unfold it)."""
        if not hasattr(self, '_folded'):
            self._folded = set()
        return self._folded

    def toggle_conformers(self, ident):
        """▸ / ▾ of a molecule with conformers pressed: its group unfolded or folded. True when it is unfolded now."""
        opened, folded = self.unfolded_conformers(), self.folded_conformers()
        current = getattr(self.document(), 'research_molecule_id', '') if hasattr(self, 'document') else ''
        shown = bool(current) and current != ident and self._conformer_of_shown(ident, current)
        from PySide6.QtCore import Qt

        table = self.project_molecules
        smooth = table.isVisible()  # animate only a table on the screen
        if ident in opened or (shown and ident not in folded):
            opened.discard(ident)
            folded.add(ident)
            rows = self._conformer_rows(ident) if smooth else []
            if rows:  # the rows shrink to nothing, then the list is made without them
                for k in range(table.rowCount()):
                    item = table.item(k, 1)
                    first = table.item(k, 0)
                    if item is not None and first is not None and first.data(Qt.ItemDataRole.UserRole) == ident \
                            and item.text().startswith('▾'):
                        item.setText('▸' + item.text()[1:])
                self._fold_rows(rows, False, self.refresh_project_navigation)
                return False
            self.refresh_project_navigation()
            return False
        opened.add(ident)
        folded.discard(ident)
        self.refresh_project_navigation()
        rows = self._conformer_rows(ident) if smooth else []
        if rows:  # the rows come in at no height and grow
            self._fold_rows(rows, True)
        return True

    FOLD_MS = 200

    def _conformer_rows(self, ident):
        """The rows of the list that show the conformers of the molecule ident."""
        from PySide6.QtCore import Qt

        path = self.research_path()
        if not path:
            return []
        try:
            ids = {e['id'] for e in projects.conformers_of(projects.Project.view(path), ident)}
        except (OSError, ValueError, KeyError):
            return []
        table = self.project_molecules
        return [k for k in range(table.rowCount())
                if table.item(k, 0) is not None and table.item(k, 0).data(Qt.ItemDataRole.UserRole) in ids]

    def _fold_rows(self, rows, opening, done=None):
        """The heights of rows from nothing to full (opening) or back, in FOLD_MS; done after it."""
        from PySide6.QtCore import QEasingCurve, QVariantAnimation

        table = self.project_molecules
        header = table.verticalHeader()
        full = header.defaultSectionSize()
        running = getattr(self, '_fold_motion', None)
        if running is not None:
            self._fold_motion = None
            running.stop()
            for k in range(table.rowCount()):
                header.resizeSection(k, full)
        motion = QVariantAnimation(self)
        motion.setDuration(self.FOLD_MS)
        motion.setEasingCurve(QEasingCurve.Type.OutCubic if opening else QEasingCurve.Type.InOutCubic)
        motion.setStartValue(0.0 if opening else float(full))
        motion.setEndValue(float(full) if opening else 0.0)

        def step(value):
            height = int(round(value))
            for k in rows:
                if k < table.rowCount():
                    header.resizeSection(k, height)

        def finished():
            if self._fold_motion is not motion:
                return
            self._fold_motion = None
            if done is not None:
                done()
            else:
                for k in rows:
                    if k < table.rowCount():
                        header.resizeSection(k, full)

        step(motion.startValue())
        motion.valueChanged.connect(step)
        motion.finished.connect(finished)
        self._fold_motion = motion
        motion.start()

    def _conformer_of_shown(self, ident, current):
        path = self.research_path()
        if not path:
            return False
        try:
            return projects.conformer_root(projects.Project.view(path), current) == ident
        except (OSError, ValueError, KeyError):
            return False

    def add_project_conformers(self, path, ident, found):
        """The conformers of a search (found: [(molecule, energy, delta, share)]) under the molecule ident of the project
        path; the group is unfolded. Returns how many were added."""
        if not path or not ident or not found:
            return 0
        from azimuth import crystal_projects

        path = Path(path).resolve()
        if crystal_projects.is_crystal(path):
            return 0
        if self.research_path() is not None and path == Path(self.research_path()).resolve():
            self.save_research_project()
        try:
            with projects.edit(path) as project:
                added = projects.set_conformers(project, ident, found)
                root = projects.conformer_root(project, ident)
                name = project.entry(root)['name']
        except (OSError, ValueError, KeyError) as exc:
            self.error(exc)
            return 0
        self.unfolded_conformers().add(root)
        self.folded_conformers().discard(root)
        self.refresh_project_navigation()
        self.notify(tr('Конформеры ({}) — в проекте под «{}»: разверните ▸, чтобы выбрать, какие считать.').format(
            len(added), name), 9000)
        return len(added)
